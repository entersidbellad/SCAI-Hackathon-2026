"""
Benchmark Visualization Script
Generates comparison charts for Opus vs Gemini judge evaluations
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

def load_latest_results(csv_path):
    """Load CSV and filter for latest Opus and Gemini runs only."""
    df = pd.read_csv(csv_path)
    
    # Convert timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Filter for Opus and Gemini judges only (exclude Minimax)
    judges_to_include = ['anthropic/claude-opus-4.5', 'google/gemini-3-flash-preview']
    df = df[df['Judge_Model'].isin(judges_to_include)]
    
    # Keep only latest entry for each (Case, Summarizer, Judge) combination
    df = df.sort_values('Timestamp')
    df = df.drop_duplicates(subset=['Case', 'Summarizer_Model', 'Judge_Model'], keep='last')
    
    # Shorten model names for readability
    df['Summarizer_Short'] = df['Summarizer_Model'].apply(lambda x: x.split('/')[-1].split(':')[0])
    df['Judge_Short'] = df['Judge_Model'].apply(lambda x: x.split('/')[-1].split(':')[0] if isinstance(x, str) else 'Unknown')
    
    return df

def plot_overall_comparison(df, output_dir):
    """Plot 1: Overall Average Scores by Judge and Summarizer (Judge-specific metrics only)"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Benchmark Comparison: Opus vs Gemini Judges', fontsize=16, fontweight='bold')
    
    # Only show judge-specific metrics (Composite and Judge Score)
    metrics = ['Composite_Score', 'Judge_Score']
    metric_names = ['Composite Score (Weighted)', 'Judge Score (LLM Evaluation)']
    
    for idx, (metric, name) in enumerate(zip(metrics, metric_names)):
        ax = axes[idx]
        
        # Group by Summarizer and Judge
        grouped = df.groupby(['Summarizer_Short', 'Judge_Short'])[metric].mean().reset_index()
        
        # Pivot for grouped bar chart
        pivot = grouped.pivot(index='Summarizer_Short', columns='Judge_Short', values=metric)
        
        pivot.plot(kind='bar', ax=ax, width=0.7)
        ax.set_title(f'{name}', fontweight='bold', fontsize=12)
        ax.set_xlabel('Summarization Model', fontweight='bold')
        ax.set_ylabel('Score', fontweight='bold')
        ax.set_ylim(0, 1.0)
        ax.legend(title='Judge Model', loc='lower right')
        ax.grid(axis='y', alpha=0.3)
        
        # Rotate x labels
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'benchmark_comparison_overall.png', dpi=300, bbox_inches='tight')
    print(f"Saved: benchmark_comparison_overall.png")
    plt.close()

def plot_per_case_heatmap(df, output_dir):
    """Plot 2: Per-Case Composite Score Heatmap"""
    for judge in df['Judge_Short'].unique():
        judge_data = df[df['Judge_Short'] == judge]
        
        # Pivot: rows=cases, columns=summarizers, values=composite_score
        pivot = judge_data.pivot(index='Case', columns='Summarizer_Short', values='Composite_Score')
        
        # Sort cases numerically
        def case_sort_key(case_name):
            try:
                return int(case_name.split()[0])
            except:
                return 999
        
        pivot = pivot.sort_index(key=lambda x: x.map(case_sort_key))
        
        # Use actual data range for better color differentiation
        vmin = pivot.min().min()
        vmax = pivot.max().max()
        
        fig, ax = plt.subplots(figsize=(12, 10))
        sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', vmin=vmin, vmax=vmax, 
                    cbar_kws={'label': 'Composite Score'}, ax=ax)
        ax.set_title(f'Per-Case Performance - {judge} Judge', fontweight='bold', fontsize=14)
        ax.set_xlabel('Summarization Model', fontweight='bold')
        ax.set_ylabel('Case', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_dir / f'heatmap_{judge}.png', dpi=300, bbox_inches='tight')
        print(f"Saved: heatmap_{judge}.png")
        plt.close()

def plot_pillar_breakdown(df, output_dir):
    """Plot 3: Pillar Score Breakdown (Stacked or Side-by-side)"""
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    fig.suptitle('Score Breakdown by Pillar', fontsize=16, fontweight='bold')
    
    for idx, judge in enumerate(df['Judge_Short'].unique()):
        ax = axes[idx]
        judge_data = df[df['Judge_Short'] == judge]
        
        # Group by summarizer
        grouped = judge_data.groupby('Summarizer_Short')[['NLI_Score', 'Judge_Score', 'Coverage_Score']].mean()
        
        grouped.plot(kind='bar', ax=ax, width=0.7)
        ax.set_title(f'{judge} Judge - Pillar Breakdown', fontweight='bold')
        ax.set_xlabel('Summarization Model')
        ax.set_ylabel('Average Score')
        ax.set_ylim(0, 1.0)
        ax.legend(title='Pillar', labels=['NLI (35%)', 'Judge (40%)', 'Coverage (25%)'])
        ax.grid(axis='y', alpha=0.3)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'pillar_breakdown.png', dpi=300, bbox_inches='tight')
    print(f"Saved: pillar_breakdown.png")
    plt.close()

def plot_ranking_comparison(df, output_dir):
    """Plot 4: Model Rankings by Judge"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Calculate average composite score for each (Summarizer, Judge) pair
    rankings = df.groupby(['Summarizer_Short', 'Judge_Short'])['Composite_Score'].mean().reset_index()
    
    # Pivot
    pivot = rankings.pivot(index='Summarizer_Short', columns='Judge_Short', values='Composite_Score')
    
    # Sort by average across judges
    pivot['Average'] = pivot.mean(axis=1)
    pivot = pivot.sort_values('Average', ascending=False)
    pivot = pivot.drop('Average', axis=1)
    
    pivot.plot(kind='barh', ax=ax, width=0.7)
    ax.set_title('Model Rankings: Composite Score Comparison', fontweight='bold', fontsize=14)
    ax.set_xlabel('Average Composite Score', fontweight='bold')
    ax.set_ylabel('Summarization Model', fontweight='bold')
    ax.set_xlim(0, 1.0)
    ax.legend(title='Judge Model', loc='lower right')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'ranking_comparison.png', dpi=300, bbox_inches='tight')
    print(f"Saved: ranking_comparison.png")
    plt.close()

def plot_per_case_bar_composite(df, output_dir):
    """Plot 5: Per-Case Composite Score Grouped Bar Chart"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    fig.suptitle('Per-Case Composite Score Comparison by Judge', fontsize=16, fontweight='bold')
    
    summarizers = sorted(df['Summarizer_Short'].unique())
    
    for idx, summarizer in enumerate(summarizers):
        ax = axes[idx]
        summarizer_data = df[df['Summarizer_Short'] == summarizer]
        
        # Pivot for grouped bar
        pivot = summarizer_data.pivot(index='Case', columns='Judge_Short', values='Composite_Score')
        
        # Sort by case number
        def case_sort_key(case_name):
            try:
                return int(case_name.split()[0])
            except:
                return 999
        pivot = pivot.sort_index(key=lambda x: x.map(case_sort_key))
        
        # Shorten case names for x-axis
        pivot.index = pivot.index.map(lambda x: x.split()[0] if len(x.split()) > 0 else x)
        
        pivot.plot(kind='bar', ax=ax, width=0.75)
        ax.set_title(f'{summarizer}', fontweight='bold', fontsize=12)
        ax.set_xlabel('Case Number', fontweight='bold')
        ax.set_ylabel('Composite Score', fontweight='bold')
        ax.legend(title='Judge Model', loc='lower right')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 1.0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'per_case_composite_comparison.png', dpi=300, bbox_inches='tight')
    print(f"Saved: per_case_composite_comparison.png")
    plt.close()

def plot_per_case_bar_judge(df, output_dir):
    """Plot 6: Per-Case Judge Score Grouped Bar Chart"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    fig.suptitle('Per-Case Judge Score Comparison by Judge', fontsize=16, fontweight='bold')
    
    summarizers = sorted(df['Summarizer_Short'].unique())
    
    for idx, summarizer in enumerate(summarizers):
        ax = axes[idx]
        summarizer_data = df[df['Summarizer_Short'] == summarizer]
        
        # Pivot for grouped bar
        pivot = summarizer_data.pivot(index='Case', columns='Judge_Short', values='Judge_Score')
        
        # Sort by case number
        def case_sort_key(case_name):
            try:
                return int(case_name.split()[0])
            except:
                return 999
        pivot = pivot.sort_index(key=lambda x: x.map(case_sort_key))
        
        # Shorten case names for x-axis
        pivot.index = pivot.index.map(lambda x: x.split()[0] if len(x.split()) > 0 else x)
        
        pivot.plot(kind='bar', ax=ax, width=0.75)
        ax.set_title(f'{summarizer}', fontweight='bold', fontsize=12)
        ax.set_xlabel('Case Number', fontweight='bold')
        ax.set_ylabel('Judge Score', fontweight='bold')
        ax.legend(title='Judge Model', loc='lower right')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 1.0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'per_case_judge_comparison.png', dpi=300, bbox_inches='tight')
    print(f"Saved: per_case_judge_comparison.png")
    plt.close()

def generate_summary_stats(df, output_dir):
    """Generate a summary statistics table"""
    summary = df.groupby(['Judge_Short', 'Summarizer_Short']).agg({
        'Composite_Score': ['mean', 'std'],
        'NLI_Score': 'mean',
        'Judge_Score': 'mean',
        'Coverage_Score': 'mean'
    }).round(3)
    
    summary.to_csv(output_dir / 'benchmark_summary_stats.csv')
    print(f"Saved: benchmark_summary_stats.csv")
    print("\nSummary Statistics:")
    print(summary)

def main():
    csv_path = Path('outputs/evaluation_log.csv')
    output_dir = Path('outputs/visualizations')
    output_dir.mkdir(exist_ok=True)
    
    print("Loading evaluation data...")
    df = load_latest_results(csv_path)
    
    print(f"\nDataset: {len(df)} evaluations")
    print(f"Cases: {df['Case'].nunique()}")
    print(f"Judges: {df['Judge_Short'].unique()}")
    print(f"Summarizers: {df['Summarizer_Short'].unique()}")
    
    print("\nGenerating visualizations...")
    plot_overall_comparison(df, output_dir)
    plot_per_case_heatmap(df, output_dir)
    plot_pillar_breakdown(df, output_dir)
    plot_ranking_comparison(df, output_dir)
    plot_per_case_bar_composite(df, output_dir)
    plot_per_case_bar_judge(df, output_dir)
    generate_summary_stats(df, output_dir)
    
    print(f"\n✓ All visualizations saved to: {output_dir}")

if __name__ == "__main__":
    main()
