
import time
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
import sys

# Setup paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OPUS_DIR = OUTPUT_DIR / "judge_results" / "claude-opus-4.5"
CSV_PATH = OUTPUT_DIR / "evaluation_log_live.csv"

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("sync_opus")

def get_existing_run_ids(csv_path):
    run_ids = set()
    if not csv_path.exists():
        return run_ids
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                run_ids.add(row.get("Run_ID"))
    except Exception:
        pass
    return run_ids

def sync_results():
    if not OPUS_DIR.exists():
        logger.info(f"Waiting for {OPUS_DIR} to be created...")
        return

    # CSV Header
    fieldnames = [
        "Timestamp", "Run_ID", "Case", "Summarizer_Model", "Judge_Model",
        "Composite_Score", "NLI_Score", "Judge_Score", "Coverage_Score",
        "Factual_Accuracy", "Completeness", "Summarizer_Prompt", "Judge_Prompt"
    ]

    while True:
        try:
            existing_ids = get_existing_run_ids(CSV_PATH)
            
            # Find JSON files
            json_files = sorted(OPUS_DIR.glob("*.json"))
            new_entries = []
            
            for json_file in json_files:
                if json_file.name.startswith("_"): continue
                
                # Check modification time to avoid re-reading old files immediately? 
                # Actually simpler to check if Run_ID exists.
                
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    
                    # Generate a unique Run_ID for this specific file/result
                    # We use mtime + filename to ensure uniqueness but stability
                    mtime = json_file.stat().st_mtime
                    timestamp = datetime.fromtimestamp(mtime).isoformat()
                    case_name = data.get("_metadata", {}).get("case_name", "unknown")
                    model = data.get("_metadata", {}).get("summarizer_model", "unknown")
                    
                    # Create a deterministic ID for this result instance
                    # If we re-run, mtime changes, so we get a new row. Perfect.
                    run_id = f"opus_bucket_{mtime}_{case_name}_{model}"
                    
                    if run_id in existing_ids:
                        continue
                        
                    # Extract Data
                    judge_model = "anthropic/claude-opus-4.5"
                    judge_prompt = data.get("_prompt_used", "Bucket Scoring Prompt")
                    judge_score = data.get("judge_score", 0)
                    factual_acc = data.get("factual_accuracy", "")
                    completeness = data.get("completeness", "")
                    
                    entry = {
                        "Timestamp": timestamp,
                        "Run_ID": run_id,
                        "Case": case_name,
                        "Summarizer_Model": model,
                        "Judge_Model": judge_model,
                        "Composite_Score": "0.0000",
                        "NLI_Score": "0.0000",
                        "Judge_Score": f"{judge_score:.4f}",
                        "Coverage_Score": "0.0000",
                        "Factual_Accuracy": str(factual_acc),
                        "Completeness": str(completeness),
                        "Summarizer_Prompt": "See src/summarizer.py",
                        "Judge_Prompt": judge_prompt,
                    }
                    new_entries.append(entry)
                    
                except Exception as e:
                    logger.error(f"Error reading {json_file}: {e}")

            if new_entries:
                # Retry logic for file locking issues
                for attempt in range(3):
                    try:
                        file_exists = CSV_PATH.exists()
                        with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            if not file_exists:
                                writer.writeheader()
                            writer.writerows(new_entries)
                        logger.info(f"Synced {len(new_entries)} new Opus results to CSV.")
                        break
                    except PermissionError:
                        logger.warning(f"File locked, retrying in 2s (attempt {attempt+1}/3)...")
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Write error: {e}")
                        break
            
        except Exception as e:
            logger.error(f"Sync loop error: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    logger.info("Starting Opus CSV Live Sync...")
    sync_results()
