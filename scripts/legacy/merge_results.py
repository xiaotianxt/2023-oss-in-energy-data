#!/usr/bin/env python3
"""
Merge Scorecard and Criticality Score Results

This script combines the results from both scorecard_results.txt and criticality_scores.txt,
filtering out failed/timeout entries and creating a comprehensive dataset.
"""

import pandas as pd
import re
import json
from typing import Dict, List, Tuple, Optional
import numpy as np


def extract_scorecard_data(filename: str) -> List[Dict]:
    """Extract successful scorecard results."""
    results = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by repository sections
    sections = content.split('=' * 80)
    
    for section in sections:
        if 'Repository:' in section and 'Status: SUCCESS' in section:
            try:
                # Extract basic info
                repo_match = re.search(r'Repository: (https://github\.com/[^\n]+)', section)
                project_match = re.search(r'Project: ([^\n]+)', section)
                category_match = re.search(r'Category: ([^\n]+)', section)
                
                if not repo_match:
                    continue
                
                repo_url = repo_match.group(1)
                project_name = project_match.group(1) if project_match else 'Unknown'
                category = category_match.group(1) if category_match else 'Unknown'
                
                # Extract aggregate score
                score_match = re.search(r'aggregate_score: ([\d.]+)', section)
                if not score_match:
                    continue
                
                aggregate_score = float(score_match.group(1))
                
                # Extract individual check scores
                checks = {}
                check_patterns = [
                    'Binary-Artifacts', 'Branch-Protection', 'CI-Tests', 'CII-Best-Practices',
                    'Code-Review', 'Contributors', 'Dangerous-Workflow', 'Dependency-Update-Tool',
                    'Fuzzing', 'License', 'Maintained', 'Packaging', 'Pinned-Dependencies',
                    'SAST', 'Security-Policy', 'Signed-Releases', 'Token-Permissions', 'Vulnerabilities'
                ]
                
                for check_name in check_patterns:
                    check_score_match = re.search(rf'check\.{re.escape(check_name)}\.score: ([-\d.]+)', section)
                    if check_score_match:
                        score_value = check_score_match.group(1)
                        # Handle -1 scores (not applicable)
                        checks[f'scorecard_{check_name.lower().replace("-", "_")}'] = float(score_value) if score_value != '-1' else None
                
                result = {
                    'repository': repo_url,
                    'project_name': project_name,
                    'category': category,
                    'scorecard_aggregate': aggregate_score,
                    **checks
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing scorecard section: {e}")
                continue
    
    print(f"Extracted {len(results)} successful scorecard results")
    return results


def extract_criticality_data(filename: str) -> List[Dict]:
    """Extract successful criticality score results."""
    results = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by repository sections
    sections = content.split('=' * 80)
    
    for section in sections:
        if 'Repository:' in section and 'Status: SUCCESS' in section:
            try:
                # Extract basic info
                repo_match = re.search(r'Repository: (https://github\.com/[^\n]+)', section)
                if not repo_match:
                    continue
                
                repo_url = repo_match.group(1)
                
                # Extract criticality score
                score_match = re.search(r'default_score: ([\d.]+)', section)
                if not score_match:
                    continue
                
                criticality_score = float(score_match.group(1))
                
                # Extract additional metrics
                metrics = {}
                metric_patterns = [
                    'created_since', 'updated_since', 'contributor_count', 'org_count',
                    'commit_frequency', 'recent_release_count', 'updated_issues_count',
                    'closed_issues_count', 'issue_comment_frequency', 'github_mention_count'
                ]
                
                for metric in metric_patterns:
                    metric_match = re.search(rf'legacy\.{metric}: ([\d.]+)', section)
                    if metric_match:
                        metrics[f'criticality_{metric}'] = float(metric_match.group(1))
                
                # Extract repo metadata
                language_match = re.search(r'repo\.language: ([^\n]+)', section)
                license_match = re.search(r'repo\.license: ([^\n]+)', section)
                star_match = re.search(r'repo\.star_count: (\d+)', section)
                created_match = re.search(r'repo\.created_at: ([^\n]+)', section)
                updated_match = re.search(r'repo\.updated_at: ([^\n]+)', section)
                
                result = {
                    'repository': repo_url,
                    'criticality_score': criticality_score,
                    'repo_language': language_match.group(1) if language_match else None,
                    'repo_license': license_match.group(1) if license_match else None,
                    'repo_stars': int(star_match.group(1)) if star_match else None,
                    'repo_created_at': created_match.group(1) if created_match else None,
                    'repo_updated_at': updated_match.group(1) if updated_match else None,
                    **metrics
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing criticality section: {e}")
                continue
    
    print(f"Extracted {len(results)} successful criticality results")
    return results


def merge_datasets(scorecard_data: List[Dict], criticality_data: List[Dict]) -> pd.DataFrame:
    """Merge scorecard and criticality datasets."""
    
    # Convert to DataFrames
    scorecard_df = pd.DataFrame(scorecard_data)
    criticality_df = pd.DataFrame(criticality_data)
    
    print(f"Scorecard DataFrame shape: {scorecard_df.shape}")
    print(f"Criticality DataFrame shape: {criticality_df.shape}")
    
    # Merge on repository URL
    merged_df = pd.merge(
        scorecard_df, 
        criticality_df, 
        on='repository', 
        how='outer',
        suffixes=('_scorecard', '_criticality')
    )
    
    print(f"Merged DataFrame shape: {merged_df.shape}")
    
    # Clean up duplicate columns
    if 'project_name_scorecard' in merged_df.columns and 'project_name_criticality' in merged_df.columns:
        merged_df['project_name'] = merged_df['project_name_scorecard'].fillna(merged_df['project_name_criticality'])
        merged_df.drop(['project_name_scorecard', 'project_name_criticality'], axis=1, inplace=True)
    
    if 'category_scorecard' in merged_df.columns and 'category_criticality' in merged_df.columns:
        merged_df['category'] = merged_df['category_scorecard'].fillna(merged_df['category_criticality'])
        merged_df.drop(['category_scorecard', 'category_criticality'], axis=1, inplace=True)
    
    # Add derived columns
    merged_df['repo_name'] = merged_df['repository'].str.extract(r'github\.com/([^/]+/[^/]+)')
    merged_df['repo_owner'] = merged_df['repository'].str.extract(r'github\.com/([^/]+)/')
    merged_df['repo_project'] = merged_df['repository'].str.extract(r'github\.com/[^/]+/([^/]+)')
    
    # Add data availability flags
    merged_df['has_scorecard'] = merged_df['scorecard_aggregate'].notna()
    merged_df['has_criticality'] = merged_df['criticality_score'].notna()
    merged_df['has_both'] = merged_df['has_scorecard'] & merged_df['has_criticality']
    
    return merged_df


def create_summary_stats(df: pd.DataFrame) -> Dict:
    """Create summary statistics."""
    stats = {
        'total_repositories': len(df),
        'repositories_with_scorecard': df['has_scorecard'].sum(),
        'repositories_with_criticality': df['has_criticality'].sum(),
        'repositories_with_both': df['has_both'].sum(),
        'scorecard_only': (df['has_scorecard'] & ~df['has_criticality']).sum(),
        'criticality_only': (~df['has_scorecard'] & df['has_criticality']).sum(),
    }
    
    # Score statistics
    if 'scorecard_aggregate' in df.columns:
        scorecard_scores = df['scorecard_aggregate'].dropna()
        if len(scorecard_scores) > 0:
            stats['scorecard_mean'] = scorecard_scores.mean()
            stats['scorecard_median'] = scorecard_scores.median()
            stats['scorecard_std'] = scorecard_scores.std()
            stats['scorecard_min'] = scorecard_scores.min()
            stats['scorecard_max'] = scorecard_scores.max()
    
    if 'criticality_score' in df.columns:
        criticality_scores = df['criticality_score'].dropna()
        if len(criticality_scores) > 0:
            stats['criticality_mean'] = criticality_scores.mean()
            stats['criticality_median'] = criticality_scores.median()
            stats['criticality_std'] = criticality_scores.std()
            stats['criticality_min'] = criticality_scores.min()
            stats['criticality_max'] = criticality_scores.max()
    
    return stats


def categorize_repositories(df: pd.DataFrame) -> pd.DataFrame:
    """Add repository categorization based on scores."""
    df = df.copy()
    
    # Scorecard categories (0-10 scale)
    def scorecard_category(score):
        if pd.isna(score):
            return 'No Data'
        elif score >= 8:
            return 'Excellent (8-10)'
        elif score >= 6:
            return 'Good (6-8)'
        elif score >= 4:
            return 'Fair (4-6)'
        elif score >= 2:
            return 'Poor (2-4)'
        else:
            return 'Very Poor (0-2)'
    
    # Criticality categories (0-1 scale)
    def criticality_category(score):
        if pd.isna(score):
            return 'No Data'
        elif score >= 0.8:
            return 'Critical (0.8-1.0)'
        elif score >= 0.6:
            return 'High (0.6-0.8)'
        elif score >= 0.4:
            return 'Medium (0.4-0.6)'
        elif score >= 0.2:
            return 'Low (0.2-0.4)'
        else:
            return 'Very Low (0-0.2)'
    
    df['scorecard_category'] = df['scorecard_aggregate'].apply(scorecard_category)
    df['criticality_category'] = df['criticality_score'].apply(criticality_category)
    
    # Combined risk assessment
    def risk_assessment(row):
        if pd.isna(row['scorecard_aggregate']) or pd.isna(row['criticality_score']):
            return 'Insufficient Data'
        
        scorecard = row['scorecard_aggregate']
        criticality = row['criticality_score']
        
        if criticality >= 0.6 and scorecard < 4:
            return 'High Risk (Critical + Poor Security)'
        elif criticality >= 0.6 and scorecard >= 6:
            return 'Well Secured Critical'
        elif criticality >= 0.4 and scorecard < 4:
            return 'Medium Risk'
        elif criticality < 0.2 and scorecard < 4:
            return 'Low Priority'
        else:
            return 'Standard'
    
    df['risk_assessment'] = df.apply(risk_assessment, axis=1)
    
    return df


def main():
    """Main function to merge and analyze the datasets."""
    print("=" * 60)
    print("MERGING SCORECARD AND CRITICALITY SCORE RESULTS")
    print("=" * 60)
    
    # Extract data from both files
    print("\n1. Extracting Scorecard data...")
    scorecard_data = extract_scorecard_data('scorecard_results.txt')
    
    print("\n2. Extracting Criticality Score data...")
    criticality_data = extract_criticality_data('criticality_scores.txt')
    
    print("\n3. Merging datasets...")
    merged_df = merge_datasets(scorecard_data, criticality_data)
    
    print("\n4. Adding categorizations...")
    final_df = categorize_repositories(merged_df)
    
    print("\n5. Creating summary statistics...")
    stats = create_summary_stats(final_df)
    
    # Save results
    print("\n6. Saving results...")
    
    # Save full dataset
    final_df.to_csv('final_merged_results.csv', index=False)
    print(f"✓ Saved full dataset: final_merged_results.csv ({len(final_df)} repositories)")
    
    # Save only repositories with both scores
    both_scores_df = final_df[final_df['has_both']].copy()
    both_scores_df.to_csv('repositories_with_both_scores.csv', index=False)
    print(f"✓ Saved repositories with both scores: repositories_with_both_scores.csv ({len(both_scores_df)} repositories)")
    
    # Save high-priority repositories (high criticality, low security)
    high_risk_df = final_df[final_df['risk_assessment'] == 'High Risk (Critical + Poor Security)'].copy()
    if len(high_risk_df) > 0:
        high_risk_df.to_csv('high_risk_repositories.csv', index=False)
        print(f"✓ Saved high-risk repositories: high_risk_repositories.csv ({len(high_risk_df)} repositories)")
    
    # Save summary statistics
    with open('merge_summary.json', 'w') as f:
        # Convert numpy types to native Python types for JSON serialization
        json_stats = {}
        for key, value in stats.items():
            if isinstance(value, (np.integer, np.floating)):
                json_stats[key] = value.item()
            else:
                json_stats[key] = value
        json.dump(json_stats, f, indent=2)
    print("✓ Saved summary statistics: merge_summary.json")
    
    # Print summary
    print("\n" + "=" * 60)
    print("MERGE SUMMARY")
    print("=" * 60)
    print(f"Total repositories: {stats['total_repositories']}")
    print(f"With Scorecard data: {stats['repositories_with_scorecard']}")
    print(f"With Criticality data: {stats['repositories_with_criticality']}")
    print(f"With both datasets: {stats['repositories_with_both']}")
    print(f"Scorecard only: {stats['scorecard_only']}")
    print(f"Criticality only: {stats['criticality_only']}")
    
    if 'scorecard_mean' in stats:
        print(f"\nScorecard Statistics:")
        print(f"  Mean: {stats['scorecard_mean']:.2f}")
        print(f"  Median: {stats['scorecard_median']:.2f}")
        print(f"  Range: {stats['scorecard_min']:.2f} - {stats['scorecard_max']:.2f}")
    
    if 'criticality_mean' in stats:
        print(f"\nCriticality Statistics:")
        print(f"  Mean: {stats['criticality_mean']:.4f}")
        print(f"  Median: {stats['criticality_median']:.4f}")
        print(f"  Range: {stats['criticality_min']:.4f} - {stats['criticality_max']:.4f}")
    
    # Show category distributions
    print(f"\nRisk Assessment Distribution:")
    risk_counts = final_df['risk_assessment'].value_counts()
    for category, count in risk_counts.items():
        percentage = (count / len(final_df)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")
    
    print(f"\n✅ Merge completed successfully!")
    print(f"📁 Check the generated CSV files for detailed analysis")


if __name__ == "__main__":
    main()
