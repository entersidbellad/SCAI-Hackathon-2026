"""
LLM Summarization Module
Generates summaries of court opinions using multiple LLMs.
"""

import json
import logging
from pathlib import Path

from .openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

SUMMARIZATION_PROMPT = """You are a legal expert summarizing Supreme Court cases for educational purposes.

Summarize the following court opinion. Your summary MUST cover these three sections:

1. **Facts of the Case**: What happened? Who are the parties? What led to this case reaching the Supreme Court?

2. **Legal Question(s)**: What specific constitutional or legal question(s) did the Court address?

3. **Conclusion/Holding**: How did the Court rule? What was the reasoning? What is the precedent set?

IMPORTANT INSTRUCTIONS:
- Be factual and comprehensive
- Do NOT add information not present in the source document
- Do NOT speculate or make assumptions
- Use clear, professional legal language
- Include specific details, parties, and legal citations mentioned in the opinion

---

COURT OPINION:

{opinion_text}

---

Provide your summary below:"""


def get_model_short_name(model: str) -> str:
    """Convert model ID to a short filename-safe name."""
    # e.g., "openai/gpt-oss-120b:free" -> "gpt-oss-120b"
    name = model.split("/")[-1]  # Remove provider prefix
    name = name.split(":")[0]     # Remove :free suffix
    return name


def summarize_case(
    client: OpenRouterClient,
    model: str,
    opinion_text: str,
) -> str:
    """
    Generate a summary of a court opinion using the specified model.
    
    Args:
        client: OpenRouter client instance
        model: Model identifier
        opinion_text: Full text of the court opinion
        
    Returns:
        Generated summary text
    """
    prompt = SUMMARIZATION_PROMPT.format(opinion_text=opinion_text)
    
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    return client.chat_completion(model=model, messages=messages)


def summarize_all_cases(
    client: OpenRouterClient,
    models: list[str],
    extracted_texts: dict[str, Path],
    output_dir: Path,
    delay_between_requests: float = 10.0,
) -> dict[str, dict[str, Path]]:
    """
    Generate summaries for all cases using all models.
    
    Args:
        client: OpenRouter client instance
        models: List of model identifiers
        extracted_texts: Dict mapping case names to extracted text file paths
        output_dir: Directory to save summaries
        delay_between_requests: Seconds to wait between API calls (default 10s for free tier)
        
    Returns:
        Nested dict: {case_name: {model_name: summary_path}}
    """
    import time
    
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    metadata_path = output_dir / "summaries_metadata.json"
    
    # Load existing metadata if resuming
    if metadata_path.exists():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
            for case, models_dict in existing.items():
                results[case] = {
                    model: Path(path) if path else None
                    for model, path in models_dict.items()
                }
            logger.info(f"Loaded existing metadata with {len(results)} cases")
        except Exception as e:
            logger.warning(f"Could not load existing metadata: {e}")
    
    total = len(extracted_texts) * len(models)
    current = 0
    
    for case_name, text_path in extracted_texts.items():
        logger.info(f"Processing case: {case_name}")
        opinion_text = text_path.read_text(encoding="utf-8")
        
        if case_name not in results:
            results[case_name] = {}
        
        for model in models:
            current += 1
            model_short = get_model_short_name(model)
            
            # Skip if already completed
            output_path = output_dir / f"{case_name}_{model_short}.txt"
            if output_path.exists():
                # Use local path even if metadata was stale/missing
                results[case_name][model] = output_path
                logger.info(f"[{current}/{total}] Skipping {model_short} - already exists")
                continue
            
            logger.info(f"[{current}/{total}] Summarizing with {model_short}")
            
            try:
                summary = summarize_case(client, model, opinion_text)
                
                # Save summary IMMEDIATELY
                output_path.write_text(summary, encoding="utf-8")
                results[case_name][model] = output_path
                logger.info(f"Saved summary to: {output_path.name}")
                
                # Update metadata IMMEDIATELY after each successful response
                metadata = {
                    case: {m: str(path) if path else None for m, path in models_dict.items()}
                    for case, models_dict in results.items()
                }
                metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                logger.info(f"Updated metadata")
                
            except Exception as e:
                logger.error(f"Failed to summarize {case_name} with {model}: {e}")
                results[case_name][model] = None
            
            # Wait before next request (for free tier rate limits)
            if current < total:
                logger.info(f"Waiting {delay_between_requests}s before next request...")
                time.sleep(delay_between_requests)
    
    return results

