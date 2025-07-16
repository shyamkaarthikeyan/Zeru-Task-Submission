#!/usr/bin/env python3
"""
Aave V2 Wallet Credit Scoring System
Generates credit scores (0-1000) for DeFi wallets based on transaction behavior.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict, Counter
import argparse
import sys

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
            print(f"Loaded {len(data)} transactions")
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
    
    def generate_report(self, scores, output_file=None):
        """Generate a detailed scoring report."""
        # Create summary statistics
        score_values = [s['credit_score'] for s in scores.values()]
        
        report = {
            'summary': {
                'total_wallets': len(scores),
                'average_score': round(np.mean(score_values), 2),
                'median_score': round(np.median(score_values), 2),
                'min_score': round(min(score_values), 2),
                'max_score': round(max(score_values), 2),
                'std_score': round(np.std(score_values), 2)
            },
            'wallet_scores': scores
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to {output_file}")
        
        return report
    
    def score_wallets(self, input_file, output_file=None):
        """Main method to score all wallets."""
        print("Loading transaction data...")
        transactions = self.load_data(input_file)
        
        print("Extracting features...")
        wallet_features = self.extract_features(transactions)
        
        print("Calculating score components...")
        component_scores = self.calculate_score_components(wallet_features)
        
        print("Computing final scores...")
        final_scores = self.calculate_final_scores(component_scores)
        
        print("Generating report...")
        report = self.generate_report(final_scores, output_file)
        
        print(f"\nScoring complete! Processed {len(final_scores)} wallets.")
        print(f"Average credit score: {report['summary']['average_score']}")
        
        return final_scores

def main():
    parser = argparse.ArgumentParser(description='Aave V2 Wallet Credit Scoring')
    parser.add_argument('input_file', help='Path to the user-wallet-transactions.json file')
    parser.add_argument('-o', '--output', help='Output file for the scoring report (JSON)')
    
    args = parser.parse_args()
    
    scorer = WalletCreditScorer()
    scores = scorer.score_wallets(args.input_file, args.output)
    
    # Display top 10 scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['credit_score'], reverse=True)
    print("\nTop 10 Highest Scoring Wallets:")
    print("-" * 80)
    for i, (wallet, data) in enumerate(sorted_scores[:10], 1):
        print(f"{i:2d}. {wallet}: {data['credit_score']:6.2f}")

if __name__ == "__main__":
    main()