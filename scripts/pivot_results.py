import pandas as pd
from pathlib import Path
import sys

# Add parent dir to sys.path
sys.path.append(str(Path(__file__).parent.parent))
import config

def generate_pivot_csv():
    input_csv = Path("outputs/evaluation_log.csv")
    output_csv = Path("outputs/evaluation_pivot.csv")

    if not input_csv.exists():
        print(f"Error: {input_csv} not found.")
        return

    print(f"Reading {input_csv}...")
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Filter for the latest run ID or just use all unique (Case, Summarizer, Judge)
    # Since we appended multiple times, we want the LATEST entry for each combination.
    # Group by [Case, Summarizer_Model, Judge_Model] and take the last one based on Timestamp
    
    # Ensure Timestamp is datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Sort by Timestamp ascending
    df = df.sort_values('Timestamp')
    
    # Deduplicate: Keep LAST occurrence of each (Case, Summarizer_Model, Judge_Model)
    latest_df = df.drop_duplicates(subset=['Case', 'Summarizer_Model', 'Judge_Model'], keep='last')
    
    print(f"Found {len(latest_df)} unique evaluation records.")

    # Pivot the table based on User Request
    # Rows: Case
    # Columns: Summarizer_Model + Judge_Model + Metric
    
    # We want valid columns like:
    # {Summarizer}_{Judge}_Composite
    # {Summarizer}_{Judge}_NLI
    # {Summarizer}_{Judge}_Judge
    # {Summarizer}_{Judge}_Coverage
    
    # Create a 'Configuration' column
    # Shorten model names for cleaner headers
    latest_df['Summarizer_Short'] = latest_df['Summarizer_Model'].apply(lambda x: x.split('/')[-1].split(':')[0])
    latest_df['Judge_Short'] = latest_df['Judge_Model'].apply(lambda x: x.split('/')[-1].split(':')[0])
    
    latest_df['Config'] = latest_df['Summarizer_Short'] + "_" + latest_df['Judge_Short']
    
    # Metrics to pivot
    metrics = ['Composite_Score', 'NLI_Score', 'Judge_Score', 'Coverage_Score']
    
    # Pivot
    pivot_df = latest_df.pivot(index='Case', columns='Config', values=metrics)
    
    # Flatten MultiIndex columns
    # New columns will be: Composite_Score_Gemini_Opus, etc.
    pivot_df.columns = [f"{col[1]}_{col[0]}" for col in pivot_df.columns]
    
    # Reset index to make Case a column
    pivot_df = pivot_df.reset_index()
    
    print(f"Pivot table shape: {pivot_df.shape}")
    print(f"Saving to {output_csv}...")
    pivot_df.to_csv(output_csv, index=False)
    print("Done.")

if __name__ == "__main__":
    generate_pivot_csv()
