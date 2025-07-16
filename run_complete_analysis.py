#!/usr/bin/env python3
"""
Complete Aave V2 Wallet Credit Scoring System
One-command execution for scoring, analysis, and visualization.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from collections import defaultdict, Counter
import argparse
import sys
import os

class WalletCreditScorer:
    def __init__(self):
        self.weights = {
            'transaction_volume': 0.20,
            'repayment_behavior': 0.25,
            'portfolio_diversity': 0.15,
            'activity_consistency': 0.15,
            'risk_management': 0.15,
            'wallet_maturity': 0.10
        }
    
    def load_data(self, file_path):
        """Load and parse the JSON transaction data."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print(f"✓ Loaded {len(data)} transactions")
            return data
        except Exception as e:
            print(f"Error loading data: {e}")
            sys.exit(1)
    
    def extract_features(self, transactions):
        """Extract features for each wallet from transaction data."""
        wallet_features = defaultdict(lambda: {
            'transactions': [],
            'deposits': 0, 'borrows': 0, 'repays': 0, 'redeems': 0, 'liquidations': 0,
            'total_deposit_amount': 0, 'total_borrow_amount': 0, 'total_repay_amount': 0,
            'assets': set(), 'first_tx': None, 'last_tx': None,
            'tx_timestamps': [], 'amounts': []
        })
        
        for tx in transactions:
            wallet = tx['userWallet']
            action = tx['action']
            timestamp = tx['timestamp']
            
            # Extract amount and convert to float
            try:
                amount = float(tx['actionData']['amount'])
                asset = tx['actionData']['assetSymbol']
                price_usd = float(tx['actionData'].get('assetPriceUSD', 0))
                amount_usd = amount * price_usd / (10**18)  # Assuming 18 decimals
            except:
                amount = 0
                amount_usd = 0
                asset = 'UNKNOWN'
            
            features = wallet_features[wallet]
            features['transactions'].append(tx)
            features['tx_timestamps'].append(timestamp)
            features['amounts'].append(amount_usd)
            features['assets'].add(asset)
            
            # Update first and last transaction times
            if features['first_tx'] is None or timestamp < features['first_tx']:
                features['first_tx'] = timestamp
            if features['last_tx'] is None or timestamp > features['last_tx']:
                features['last_tx'] = timestamp
            
            # Count action types and amounts
            if action == 'deposit':
                features['deposits'] += 1
                features['total_deposit_amount'] += amount_usd
            elif action == 'borrow':
                features['borrows'] += 1
                features['total_borrow_amount'] += amount_usd
            elif action == 'repay':
                features['repays'] += 1
                features['total_repay_amount'] += amount_usd
            elif action == 'redeemunderlying':
                features['redeems'] += 1
            elif action == 'liquidationcall':
                features['liquidations'] += 1
        
        return wallet_features
    
    def calculate_score_components(self, wallet_features):
        """Calculate individual scoring components for each wallet."""
        scores = {}
        
        for wallet, features in wallet_features.items():
            total_txs = len(features['transactions'])
            if total_txs == 0:
                continue
            
            # 1. Transaction Volume Score (0-100)
            volume_score = min(100, np.log1p(total_txs) * 20)
            
            # 2. Repayment Behavior Score (0-100)
            if features['borrows'] > 0:
                repay_ratio = features['repays'] / features['borrows']
                repayment_score = min(100, repay_ratio * 80 + 20)
            else:
                # No borrows = neutral score
                repayment_score = 70
            
            # 3. Portfolio Diversity Score (0-100)
            num_assets = len(features['assets'])
            diversity_score = min(100, num_assets * 25)
            
            # 4. Activity Consistency Score (0-100)
            if len(features['tx_timestamps']) > 1:
                timestamps = sorted(features['tx_timestamps'])
                intervals = np.diff(timestamps)
                consistency = 100 - min(100, np.std(intervals) / np.mean(intervals) * 50)
            else:
                consistency = 50
            
            # 5. Risk Management Score (0-100)
            liquidation_penalty = features['liquidations'] * 20
            risk_score = max(0, 100 - liquidation_penalty)
            
            # Bonus for balanced activity (deposits vs withdrawals)
            if features['deposits'] > 0 and features['redeems'] > 0:
                balance_ratio = min(features['deposits'], features['redeems']) / max(features['deposits'], features['redeems'])
                risk_score *= (0.8 + 0.4 * balance_ratio)
            
            # 6. Wallet Maturity Score (0-100)
            if features['first_tx'] and features['last_tx']:
                wallet_age_days = (features['last_tx'] - features['first_tx']) / 86400  # Convert to days
                maturity_score = min(100, wallet_age_days / 30 * 100)  # 30+ days = full score
            else:
                maturity_score = 0
            
            scores[wallet] = {
                'transaction_volume': volume_score,
                'repayment_behavior': repayment_score,
                'portfolio_diversity': diversity_score,
                'activity_consistency': consistency,
                'risk_management': risk_score,
                'wallet_maturity': maturity_score,
                'total_transactions': total_txs,
                'total_volume_usd': sum(features['amounts']),
                'assets_count': num_assets
            }
        
        return scores
    
    def calculate_final_scores(self, component_scores):
        """Calculate final credit scores using weighted components."""
        final_scores = {}
        
        for wallet, components in component_scores.items():
            weighted_score = sum(
                components[component] * self.weights[component]
                for component in self.weights.keys()
            )
            
            # Scale to 0-1000 range
            final_score = max(0, min(1000, weighted_score * 10))
            
            final_scores[wallet] = {
                'credit_score': round(final_score, 2),
                'components': components
            }
        
        return final_scores
    
    def score_wallets(self, input_file):
        """Main method to score all wallets."""
        print("🔄 Loading transaction data...")
        transactions = self.load_data(input_file)
        
        print("🔄 Extracting features...")
        wallet_features = self.extract_features(transactions)
        
        print("🔄 Calculating score components...")
        component_scores = self.calculate_score_components(wallet_features)
        
        print("🔄 Computing final scores...")
        final_scores = self.calculate_final_scores(component_scores)
        
        print(f"✓ Scoring complete! Processed {len(final_scores)} wallets.")
        
        return final_scores

class AnalysisGenerator:
    def __init__(self, scores):
        self.scores = scores
        self.score_values = [s['credit_score'] for s in scores.values()]
    
    def create_visualizations(self):
        """Create comprehensive visualizations."""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Aave V2 Wallet Credit Score Analysis', fontsize=16, fontweight='bold')
        
        # 1. Score Distribution Histogram
        axes[0, 0].hist(self.score_values, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('Credit Score Distribution')
        axes[0, 0].set_xlabel('Credit Score')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].axvline(np.mean(self.score_values), color='red', linestyle='--', label=f'Mean: {np.mean(self.score_values):.1f}')
        axes[0, 0].legend()
        
        # 2. Score Range Distribution
        ranges = ['0-100', '100-200', '200-300', '300-400', '400-500', 
                 '500-600', '600-700', '700-800', '800-900', '900-1000']
        range_counts = []
        for i, r in enumerate(ranges):
            lower = i * 100
            upper = (i + 1) * 100
            count = sum(1 for score in self.score_values if lower <= score < upper)
            range_counts.append(count)
        
        bars = axes[0, 1].bar(ranges, range_counts, alpha=0.7, color='lightcoral')
        axes[0, 1].set_title('Wallets by Score Range')
        axes[0, 1].set_xlabel('Score Range')
        axes[0, 1].set_ylabel('Number of Wallets')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Add count labels on bars
        for bar, count in zip(bars, range_counts):
            if count > 0:
                axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                               str(count), ha='center', va='bottom')
        
        # 3. Component Analysis (sample of wallets)
        sample_wallets = list(self.scores.keys())[:100]  # Sample for readability
        components = ['transaction_volume', 'repayment_behavior', 'portfolio_diversity', 
                     'activity_consistency', 'risk_management', 'wallet_maturity']
        
        component_data = []
        for wallet in sample_wallets:
            for comp in components:
                component_data.append({
                    'Component': comp.replace('_', ' ').title(),
                    'Score': self.scores[wallet]['components'][comp]
                })
        
        df_components = pd.DataFrame(component_data)
        sns.boxplot(data=df_components, x='Component', y='Score', ax=axes[1, 0])
        axes[1, 0].set_title('Score Components Distribution (Sample)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. Risk Category Distribution
        risk_categories = {
            'High Risk (0-400)': sum(1 for s in self.score_values if s < 400),
            'Moderate Risk (400-600)': sum(1 for s in self.score_values if 400 <= s < 600),
            'Good Credit (600-800)': sum(1 for s in self.score_values if 600 <= s < 800),
            'Elite (800-1000)': sum(1 for s in self.score_values if s >= 800)
        }
        
        labels = list(risk_categories.keys())
        sizes = list(risk_categories.values())
        colors = ['#ff9999', '#ffcc99', '#99ccff', '#99ff99']
        
        axes[1, 1].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('Risk Category Distribution')
        
        plt.tight_layout()
        plt.savefig('wallet_score_analysis.png', dpi=300, bbox_inches='tight')
        print("✓ Visualizations saved as 'wallet_score_analysis.png'")
        
        return risk_categories, range_counts, ranges
    
    def generate_summary_stats(self):
        """Generate summary statistics."""
        return {
            'total_wallets': len(self.scores),
            'average_score': round(np.mean(self.score_values), 2),
            'median_score': round(np.median(self.score_values), 2),
            'min_score': round(min(self.score_values), 2),
            'max_score': round(max(self.score_values), 2),
            'std_score': round(np.std(self.score_values), 2)
        }
    
    def save_results(self):
        """Save scoring results and analysis."""
        # Save detailed results
        summary_stats = self.generate_summary_stats()
        
        report = {
            'summary': summary_stats,
            'wallet_scores': self.scores
        }
        
        with open('wallet_scores_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("✓ Detailed results saved to 'wallet_scores_report.json'")
        
        return summary_stats

def main():
    parser = argparse.ArgumentParser(description='Complete Aave V2 Wallet Credit Scoring Analysis')
    parser.add_argument('input_file', help='Path to the user-wallet-transactions.json file')
    parser.add_argument('--no-viz', action='store_true', help='Skip visualization generation')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 AAVE V2 WALLET CREDIT SCORING SYSTEM")
    print("=" * 80)
    
    # Step 1: Score wallets
    scorer = WalletCreditScorer()
    scores = scorer.score_wallets(args.input_file)
    
    # Step 2: Generate analysis and visualizations
    print("\n🔄 Generating analysis and visualizations...")
    analyzer = AnalysisGenerator(scores)
    
    if not args.no_viz:
        risk_categories, range_counts, ranges = analyzer.create_visualizations()
    
    # Step 3: Save results
    summary_stats = analyzer.save_results()
    
    # Step 4: Display summary
    print("\n" + "=" * 80)
    print("📊 ANALYSIS COMPLETE - SUMMARY RESULTS")
    print("=" * 80)
    print(f"Total Wallets Analyzed: {summary_stats['total_wallets']:,}")
    print(f"Average Credit Score: {summary_stats['average_score']}")
    print(f"Median Credit Score: {summary_stats['median_score']}")
    print(f"Score Range: {summary_stats['min_score']} - {summary_stats['max_score']}")
    print(f"Standard Deviation: {summary_stats['std_score']}")
    
    if not args.no_viz:
        print("\n📈 Risk Category Breakdown:")
        print("-" * 40)
        total_wallets = summary_stats['total_wallets']
        for category, count in risk_categories.items():
            percentage = (count / total_wallets) * 100
            print(f"{category:25s}: {count:5,} ({percentage:5.1f}%)")
    
    # Display top and bottom performers
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['credit_score'], reverse=True)
    
    print("\n🏆 Top 10 Highest Scoring Wallets:")
    print("-" * 80)
    for i, (wallet, data) in enumerate(sorted_scores[:10], 1):
        print(f"{i:2d}. {wallet}: {data['credit_score']:6.2f}")
    
    print("\n⚠️  Bottom 10 Scoring Wallets:")
    print("-" * 80)
    for i, (wallet, data) in enumerate(sorted_scores[-10:], 1):
        print(f"{i:2d}. {wallet}: {data['credit_score']:6.2f}")
    
    print("\n" + "=" * 80)
    print("✅ All files generated successfully!")
    print("📄 wallet_scores_report.json - Detailed scoring results")
    if not args.no_viz:
        print("📊 wallet_score_analysis.png - Visualization charts")
    print("=" * 80)

if __name__ == "__main__":
    main()
