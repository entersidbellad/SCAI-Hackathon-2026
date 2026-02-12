"""
Pillar 3: Embedding-based Coverage Evaluation
Uses sentence embeddings to measure how well the LLM summary covers ground truth content.
"""

import json
import logging
from pathlib import Path

import nltk
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Ensure punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class CoverageEvaluator:
    """Evaluates summary coverage using sentence embeddings and cosine similarity."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.5,
    ):
        """
        Initialize the coverage evaluator.
        
        Args:
            model_name: SentenceTransformer model identifier
            threshold: Cosine similarity threshold below which content is flagged as omitted
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        
        # Use GPU if available
        if torch.cuda.is_available():
            self.model = self.model.to(torch.device("cuda"))
        
        logger.info(f"Embedding model loaded, threshold={threshold}")
    
    def compute_similarity(self, embedding1, embedding2) -> float:
        """Compute cosine similarity between two embeddings."""
        return float(torch.nn.functional.cosine_similarity(
            torch.tensor(embedding1).unsqueeze(0),
            torch.tensor(embedding2).unsqueeze(0),
        ))
    
    def evaluate_summary(
        self,
        ground_truth: str,
        llm_summary: str,
    ) -> dict:
        """
        Evaluate coverage of ground truth by the LLM summary.
        
        For each sentence in the ground truth, finds the best matching
        sentence in the LLM summary and flags omissions below threshold.
        
        Args:
            ground_truth: The reference summary (Oyez)
            llm_summary: The LLM-generated summary
            
        Returns:
            Dict with coverage analysis results
        """
        # Split into sentences
        gt_sentences = [s.strip() for s in nltk.sent_tokenize(ground_truth) if len(s.strip()) > 10]
        summary_sentences = [s.strip() for s in nltk.sent_tokenize(llm_summary) if len(s.strip()) > 10]
        
        if not gt_sentences or not summary_sentences:
            logger.warning("No sentences to compare")
            return {
                "coverage_percentage": 0,
                "coverage_score": 0,
                "sentence_results": [],
                "omissions": [],
            }
        
        # Compute embeddings
        gt_embeddings = self.model.encode(gt_sentences, convert_to_numpy=True)
        summary_embeddings = self.model.encode(summary_sentences, convert_to_numpy=True)
        
        results = []
        omissions = []
        covered_count = 0
        
        for i, (gt_sent, gt_emb) in enumerate(zip(gt_sentences, gt_embeddings)):
            # Find best matching summary sentence
            best_similarity = -1
            best_match = None
            
            for j, (sum_sent, sum_emb) in enumerate(zip(summary_sentences, summary_embeddings)):
                similarity = self.compute_similarity(gt_emb, sum_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = sum_sent
            
            is_covered = best_similarity >= self.threshold
            
            if is_covered:
                covered_count += 1
            else:
                omissions.append({
                    "sentence": gt_sent,
                    "best_similarity": best_similarity,
                    "best_match": best_match,
                })
            
            results.append({
                "ground_truth_sentence": gt_sent,
                "best_match": best_match,
                "similarity": best_similarity,
                "is_covered": is_covered,
            })
        
        coverage_pct = (covered_count / len(gt_sentences)) * 100 if gt_sentences else 0
        
        return {
            "sentence_results": results,
            "omissions": omissions,
            "total_gt_sentences": len(gt_sentences),
            "covered_sentences": covered_count,
            "coverage_percentage": coverage_pct,
            "coverage_score": coverage_pct / 100,  # Normalized 0-1
            "threshold": self.threshold,
        }


def evaluate_all_coverage(
    evaluator: CoverageEvaluator,
    ground_truths: dict[str, str],
    llm_summaries: dict[str, dict[str, Path]],
    output_dir: Path,
) -> dict:
    """
    Run coverage evaluation on all cases and models.
    
    Args:
        evaluator: CoverageEvaluator instance
        ground_truths: Dict mapping case names to ground truth text
        llm_summaries: Nested dict {case: {model: summary_path}}
        output_dir: Directory to save results
        
    Returns:
        Results dictionary
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_results = {}
    
    for case_name, gt_text in ground_truths.items():
        logger.info(f"Coverage evaluation for case: {case_name}")
        all_results[case_name] = {}
        
        for model, summary_path in llm_summaries.get(case_name, {}).items():
            if summary_path is None:
                continue
            
            summary_text = Path(summary_path).read_text(encoding="utf-8")
            
            result = evaluator.evaluate_summary(gt_text, summary_text)
            all_results[case_name][model] = result
            
            # Save individual result
            model_short = model.split("/")[-1].split(":")[0]
            result_path = output_dir / f"{case_name}_{model_short}_coverage.json"
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            
            logger.info(
                f"  {model_short}: coverage={result['coverage_percentage']:.1f}%, "
                f"omissions={len(result['omissions'])}"
            )
    
    return all_results
