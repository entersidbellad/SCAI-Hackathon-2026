"""
Pillar 1: NLI Contradiction Detection
Uses DeBERTa-v3-large-mnli to detect contradictions between ground truth and LLM summaries.
"""

import json
import logging
from pathlib import Path

import nltk
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

# Ensure punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class NLIEvaluator:
    """Evaluates summaries using Natural Language Inference for contradiction detection."""
    
    LABELS = ["contradiction", "neutral", "entailment"]
    
    def __init__(self, model_name: str = "microsoft/deberta-v3-large-mnli"):
        """
        Initialize the NLI evaluator.
        
        Args:
            model_name: HuggingFace model identifier for NLI
        """
        logger.info(f"Loading NLI model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        # Use GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"NLI model loaded on {self.device}")
    
    def classify_pair(self, premise: str, hypothesis: str) -> dict:
        """
        Classify the NLI relationship between premise and hypothesis.
        
        Args:
            premise: The text to check against (LLM summary)
            hypothesis: The claim to verify (ground truth sentence)
            
        Returns:
            Dict with label and probabilities
        """
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0]
        
        label_idx = probs.argmax().item()
        
        return {
            "label": self.LABELS[label_idx],
            "probabilities": {
                label: probs[i].item() 
                for i, label in enumerate(self.LABELS)
            },
        }
    
    def evaluate_summary(
        self,
        ground_truth: str,
        llm_summary: str,
    ) -> dict:
        """
        Evaluate an LLM summary against ground truth using NLI.
        
        For each sentence in the ground truth, checks if the LLM summary
        contradicts, entails, or is neutral to it.
        
        Args:
            ground_truth: The reference summary (Oyez)
            llm_summary: The LLM-generated summary
            
        Returns:
            Dict with sentence-level results and aggregate statistics
        """
        # Split ground truth into sentences
        gt_sentences = nltk.sent_tokenize(ground_truth)
        
        results = []
        contradicted_gt_sentences = 0
        
        # Split LLM summary into sentences once
        summary_sentences = nltk.sent_tokenize(llm_summary)
        
        for gt_sent in gt_sentences:
            gt_sent = gt_sent.strip()
            if len(gt_sent) < 10:  # Skip very short sentences
                continue
            
            is_contradicted = False
            best_match_probs = None
            
            # Check against ALL summary sentences
            for sum_sent in summary_sentences:
                classification = self.classify_pair(
                    premise=sum_sent,  # Summary is the premise for contradiction check
                    hypothesis=gt_sent, # GT is the hypothesis we are verifying
                )
                
                # If ANY summary sentence contradicts this GT sentence
                if classification["label"] == "contradiction":
                    is_contradicted = True
                    best_match_probs = classification["probabilities"]
                    break # Stop checking other summary sentences for this GT fact
            
            if is_contradicted:
                contradicted_gt_sentences += 1
                
            results.append({
                "sentence": gt_sent,
                "label": "contradiction" if is_contradicted else "neutral/entailment",
                "probabilities": best_match_probs
            })
            
        total_gt = len(results)
        contradiction_rate = contradicted_gt_sentences / total_gt if total_gt > 0 else 0
        nli_score = 1.0 - contradiction_rate

        return {
            "sentence_results": results,
            "counts": {"contradiction": contradicted_gt_sentences},
            "total_sentences": total_gt,
            "contradiction_rate": contradiction_rate,
            "nli_score": nli_score,
        }


def evaluate_all_nli(
    evaluator: NLIEvaluator,
    ground_truths: dict[str, str],
    llm_summaries: dict[str, dict[str, Path]],
    output_dir: Path,
) -> dict:
    """
    Run NLI evaluation on all cases and models.
    
    Args:
        evaluator: NLIEvaluator instance
        ground_truths: Dict mapping case names to ground truth text
        llm_summaries: Nested dict {case: {model: summary_path}}
        output_dir: Directory to save results
        
    Returns:
        Results dictionary
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_results = {}
    
    for case_name, gt_text in ground_truths.items():
        logger.info(f"NLI evaluation for case: {case_name}")
        all_results[case_name] = {}
        
        for model, summary_path in llm_summaries.get(case_name, {}).items():
            if summary_path is None:
                logger.warning(f"No summary for {case_name} / {model}")
                continue
            
            summary_text = Path(summary_path).read_text(encoding="utf-8")
            
            result = evaluator.evaluate_summary(gt_text, summary_text)
            all_results[case_name][model] = result
            
            # Save individual result
            model_short = model.split("/")[-1].split(":")[0]
            result_path = output_dir / f"{case_name}_{model_short}_nli.json"
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            
            logger.info(
                f"  {model_short}: contradiction_rate={result['contradiction_rate']:.2%}, "
                f"nli_score={result['nli_score']:.2f}"
            )
    
    return all_results
