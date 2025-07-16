#!/usr/bin/env python3
"""
Analysis and Visualization Script for Aave V2 Wallet Credit Scores
Generates distribution graphs and detailed behavioral analysis.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import sys

def load_scoring_results(file_path):
    """Load the wallet scoring results from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading scoring results: {e}")
        sys.exit(1)

def analyze_score_distribution(wallet_scores):
    """Analyze the distribution of credit scores across ranges."""
    scores = [data['credit_score'] for data in wallet_scores.values()]
    
    # Define score ranges
    ranges = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500), 
              (500, 600), (600, 700), (700, 800), (800, 900), (900, 1000)]
    
    distribution = {}
    total_wallets = len(scores)
    
    for start, end in ranges:
        count = len([s for s in scores if start <= s < end])
        percentage = (count / total_wallets) * 100
        distribution[f"{start}-{end}"] = {
            'count': count,
            'percentage': percentage
        }
    
    return distribution, scores

def analyze_behavioral_patterns(wallet_scores):
    """Analyze behavioral patterns by score range."""
    ranges = {
        'high_risk': (0, 400),
        'moderate_risk': (400, 600),
        'good_credit': (600, 800),
        'elite': (800, 1000)
    }
    
    patterns = {}
    
    for range_name, (min_score, max_score) in ranges.items():
        wallets_in_range = {
            wallet: data for wallet, data in wallet_scores.items()
            if min_score <= data['credit_score'] < max_score
        }
        
        if wallets_in_range:
            # Calculate averages for this range
            components = defaultdict(list)
            for wallet_data in wallets_in_range.values():
                for component, value in wallet_data['components'].items():
                    if isinstance(value, (int, float)) and component != 'total_transactions':
                        components[component].append(value)
            
            avg_components = {comp: np.mean(values) for comp, values in components.items()}
            
            patterns[range_name] = {
                'count': len(wallets_in_range),
                'avg_components': avg_components,
                'sample_wallets': list(wallets_in_range.keys())[:5]
            }
    
    return patterns

def create_visualizations(distribution, scores, patterns):
    """Create distribution graphs and save them."""
    # Set up the plotting style
    plt.style.use('seaborn-v0_8')
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Score Distribution Histogram
    plt.subplot(2, 3, 1)
    plt.hist(scores, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    plt.title('Credit Score Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Credit Score')
    plt.ylabel('Number of Wallets')
    plt.axvline(np.mean(scores), color='red', linestyle='--', label=f'Mean: {np.mean(scores):.1f}')
    plt.legend()
    
    # 2. Score Range Bar Chart
    plt.subplot(2, 3, 2)
    ranges = list(distribution.keys())
    counts = [distribution[r]['count'] for r in ranges]
    colors = ['red', 'orange', 'yellow', 'lightgreen', 'green', 'blue', 'purple', 'pink', 'brown', 'gray']
    
    bars = plt.bar(ranges, counts, color=colors, alpha=0.7)
    plt.title('Wallets by Score Range', fontsize=14, fontweight='bold')
    plt.xlabel('Score Range')
    plt.ylabel('Number of Wallets')
    plt.xticks(rotation=45)
    
    # Add percentage labels on bars
    for bar, range_key in zip(bars, ranges):
        height = bar.get_height()
        percentage = distribution[range_key]['percentage']
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{percentage:.1f}%', ha='center', va='bottom')
    
    # 3. Box Plot by Risk Categories
    plt.subplot(2, 3, 3)
    risk_categories = []
    risk_scores = []
    
    for score in scores:
        if score < 400:
            risk_categories.append('High Risk\n(0-400)')
            risk_scores.append(score)
        elif score < 600:
            risk_categories.append('Moderate Risk\n(400-600)')
            risk_scores.append(score)
        elif score < 800:
            risk_categories.append('Good Credit\n(600-800)')
            risk_scores.append(score)
        else:
            risk_categories.append('Elite\n(800-1000)')
            risk_scores.append(score)
    
    df_risk = pd.DataFrame({'Category': risk_categories, 'Score': risk_scores})
    sns.boxplot(data=df_risk, x='Category', y='Score')
    plt.title('Score Distribution by Risk Category', fontsize=14, fontweight='bold')
    plt.ylabel('Credit Score')
    
    # 4. Component Analysis Heatmap
    plt.subplot(2, 3, 4)
    component_data = []
    for range_name, data in patterns.items():
        if 'avg_components' in data:
            row = [data['avg_components'].get(comp, 0) for comp in 
                   ['transaction_volume', 'repayment_behavior', 'portfolio_diversity', 
                    'activity_consistency', 'risk_management', 'wallet_maturity']]
            component_data.append(row)
    
    if component_data:
        heatmap_data = pd.DataFrame(component_data, 
                                   index=['High Risk', 'Moderate Risk', 'Good Credit', 'Elite'],
                                   columns=['Volume', 'Repayment', 'Diversity', 'Consistency', 'Risk Mgmt', 'Maturity'])
        sns.heatmap(heatmap_data, annot=True, cmap='RdYlGn', center=50)
        plt.title('Average Component Scores by Risk Category', fontsize=14, fontweight='bold')
    
    # 5. Cumulative Distribution
    plt.subplot(2, 3, 5)
    sorted_scores = np.sort(scores)
    y = np.arange(1, len(sorted_scores) + 1) / len(sorted_scores) * 100
    plt.plot(sorted_scores, y, linewidth=2)
    plt.title('Cumulative Score Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Credit Score')
    plt.ylabel('Cumulative Percentage')
    plt.grid(True, alpha=0.3)
    
    # Add percentile markers
    percentiles = [25, 50, 75, 90, 95]
    for p in percentiles:
        score_at_p = np.percentile(scores, p)
        plt.axvline(score_at_p, color='red', linestyle=':', alpha=0.7)
        plt.text(score_at_p, p + 2, f'P{p}', rotation=90, ha='center')
    
    # 6. Score Statistics Summary
    plt.subplot(2, 3, 6)
    plt.axis('off')
    
    stats_text = f"""
    SCORE STATISTICS
    
    Total Wallets: {len(scores):,}
    
    Mean Score: {np.mean(scores):.1f}
    Median Score: {np.median(scores):.1f}
    Std Deviation: {np.std(scores):.1f}
    
    Min Score: {np.min(scores):.1f}
    Max Score: {np.max(scores):.1f}
    
    PERCENTILES
    25th: {np.percentile(scores, 25):.1f}
    50th: {np.percentile(scores, 50):.1f}
    75th: {np.percentile(scores, 75):.1f}
    90th: {np.percentile(scores, 90):.1f}
    95th: {np.percentile(scores, 95):.1f}
    """
    
    plt.text(0.1, 0.9, stats_text, transform=plt.gca().transAxes, 
             fontsize=11, verticalalignment='top', fontfamily='monospace')
    
    plt.tight_layout()
    plt.savefig('wallet_score_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Visualization saved as 'wallet_score_analysis.png'")

def generate_detailed_analysis(distribution, scores, patterns, wallet_scores):
    """Generate detailed textual analysis."""
    total_wallets = len(scores)
    
    print("\n" + "="*80)
    print("DETAILED WALLET SCORING ANALYSIS")
    print("="*80)
    
    print(f"\nDataset Overview:")
    print(f"- Total Wallets Analyzed: {total_wallets:,}")
    print(f"- Average Credit Score: {np.mean(scores):.1f}")
    print(f"- Median Credit Score: {np.median(scores):.1f}")
    print(f"- Standard Deviation: {np.std(scores):.1f}")
    
    print(f"\nScore Distribution:")
    print("-" * 50)
    for range_key, data in distribution.items():
        print(f"{range_key:>10}: {data['count']:>5} wallets ({data['percentage']:>5.1f}%)")
    
    # Risk category analysis
    high_risk = len([s for s in scores if s < 400])
    moderate_risk = len([s for s in scores if 400 <= s < 600])
    good_credit = len([s for s in scores if 600 <= s < 800])
    elite = len([s for s in scores if s >= 800])
    
    print(f"\nRisk Category Summary:")
    print("-" * 50)
    print(f"High Risk (0-400):     {high_risk:>5} wallets ({high_risk/total_wallets*100:>5.1f}%)")
    print(f"Moderate Risk (400-600): {moderate_risk:>5} wallets ({moderate_risk/total_wallets*100:>5.1f}%)")
    print(f"Good Credit (600-800):   {good_credit:>5} wallets ({good_credit/total_wallets*100:>5.1f}%)")
    print(f"Elite (800-1000):       {elite:>5} wallets ({elite/total_wallets*100:>5.1f}%)")
    
    # Top and bottom performers
    sorted_wallets = sorted(wallet_scores.items(), key=lambda x: x[1]['credit_score'], reverse=True)
    
    print(f"\nTop 10 Performing Wallets:")
    print("-" * 50)
    for i, (wallet, data) in enumerate(sorted_wallets[:10], 1):
        print(f"{i:>2}. {wallet}: {data['credit_score']:>6.1f}")
    
    print(f"\nBottom 10 Performing Wallets:")
    print("-" * 50)
    for i, (wallet, data) in enumerate(sorted_wallets[-10:], 1):
        print(f"{i:>2}. {wallet}: {data['credit_score']:>6.1f}")

def main():
    """Main analysis function."""
    print("Loading wallet scoring results...")
    
    # Load the scoring results
    try:
        results = load_scoring_results('wallet_scores_report.json')
        wallet_scores = results['wallet_scores']
        print(f"Loaded scores for {len(wallet_scores)} wallets")
    except:
        print("Error: Could not load wallet_scores_report.json")
        print("Please run the scoring script first: python wallet_credit_scorer.py user-wallet-transactions.json -o wallet_scores_report.json")
        return
    
    # Perform analysis
    print("Analyzing score distribution...")
    distribution, scores = analyze_score_distribution(wallet_scores)
    
    print("Analyzing behavioral patterns...")
    patterns = analyze_behavioral_patterns(wallet_scores)
    
    print("Creating visualizations...")
    create_visualizations(distribution, scores, patterns)
    
    print("Generating detailed analysis...")
    generate_detailed_analysis(distribution, scores, patterns, wallet_scores)
    
    print("\nAnalysis complete! Check 'wallet_score_analysis.png' for visualizations.")

if __name__ == "__main__":
    main()