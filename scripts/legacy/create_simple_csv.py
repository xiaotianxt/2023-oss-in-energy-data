#!/usr/bin/env python3
"""
Create Simple CSV with Repository Scores

This script creates a simple CSV file with repository names, URLs, and their scores
from both scorecard and criticality score results.
"""

import pandas as pd
import re
from typing import Dict, List, Optional


def extract_scorecard_scores(filename: str) -> List[Dict]:
    """Extract scorecard results with basic info and aggregate score."""
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
                
                scorecard_score = float(score_match.group(1))
                
                # Extract repo name from URL
                repo_name = repo_url.replace('https://github.com/', '')
                
                result = {
                    'repository_url': repo_url,
                    'repository_name': repo_name,
                    'project_name': project_name,
                    'category': category,
                    'scorecard_score': scorecard_score
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing scorecard section: {e}")
                continue
    
    print(f"Extracted {len(results)} successful scorecard results")
    return results


def extract_criticality_scores(filename: str) -> List[Dict]:
    """Extract criticality score results with basic info."""
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
                
                # Extract repo name from URL
                repo_name = repo_url.replace('https://github.com/', '')
                
                result = {
                    'repository_url': repo_url,
                    'repository_name': repo_name,
                    'criticality_score': criticality_score
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing criticality section: {e}")
                continue
    
    print(f"Extracted {len(results)} successful criticality results")
    return results


def create_simple_merged_csv():
    """Create a simple merged CSV with repository info and scores."""
    
    print("=" * 60)
    print("CREATING SIMPLE REPOSITORY SCORES CSV")
    print("=" * 60)
    
    # Extract data from both files
    print("\n1. Extracting Scorecard data...")
    scorecard_data = extract_scorecard_scores('scorecard_results.txt')
    
    print("\n2. Extracting Criticality Score data...")
    criticality_data = extract_criticality_scores('criticality_scores.txt')
    
    # Convert to DataFrames
    scorecard_df = pd.DataFrame(scorecard_data)
    criticality_df = pd.DataFrame(criticality_data)
    
    print(f"\n3. Merging datasets...")
    print(f"   Scorecard: {len(scorecard_df)} repositories")
    print(f"   Criticality: {len(criticality_df)} repositories")
    
    # Merge on repository URL
    merged_df = pd.merge(
        scorecard_df, 
        criticality_df[['repository_url', 'criticality_score']], 
        on='repository_url', 
        how='outer'
    )
    
    # Fill missing project names and categories for criticality-only repos
    for idx, row in merged_df.iterrows():
        if pd.isna(row['project_name']) and not pd.isna(row['repository_name']):
            # Use repository name as project name if missing
            merged_df.at[idx, 'project_name'] = row['repository_name'].split('/')[-1]
        if pd.isna(row['category']):
            merged_df.at[idx, 'category'] = 'Unknown'
    
    # Reorder columns for clarity
    final_columns = [
        'repository_name',
        'repository_url', 
        'project_name',
        'category',
        'scorecard_score',
        'criticality_score'
    ]
    
    final_df = merged_df[final_columns].copy()
    
    # Sort by repository name
    final_df = final_df.sort_values('repository_name')
    
    print(f"   Merged: {len(final_df)} repositories")
    
    # Add summary columns
    final_df['has_scorecard'] = final_df['scorecard_score'].notna()
    final_df['has_criticality'] = final_df['criticality_score'].notna()
    final_df['has_both_scores'] = final_df['has_scorecard'] & final_df['has_criticality']
    
    # Save the simple CSV
    output_filename = 'repository_scores_simple.csv'
    final_df.to_csv(output_filename, index=False)
    
    print(f"\n4. Results saved to: {output_filename}")
    
    # Print summary statistics
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total repositories: {len(final_df)}")
    print(f"With Scorecard data: {final_df['has_scorecard'].sum()}")
    print(f"With Criticality data: {final_df['has_criticality'].sum()}")
    print(f"With both scores: {final_df['has_both_scores'].sum()}")
    print(f"Scorecard only: {(final_df['has_scorecard'] & ~final_df['has_criticality']).sum()}")
    print(f"Criticality only: {(~final_df['has_scorecard'] & final_df['has_criticality']).sum()}")
    
    # Show score ranges
    scorecard_scores = final_df['scorecard_score'].dropna()
    criticality_scores = final_df['criticality_score'].dropna()
    
    if len(scorecard_scores) > 0:
        print(f"\nScorecard scores range: {scorecard_scores.min():.2f} - {scorecard_scores.max():.2f}")
        print(f"Average scorecard score: {scorecard_scores.mean():.2f}")
    
    if len(criticality_scores) > 0:
        print(f"Criticality scores range: {criticality_scores.min():.4f} - {criticality_scores.max():.4f}")
        print(f"Average criticality score: {criticality_scores.mean():.4f}")
    
    # Show a few examples
    print(f"\nFirst 5 repositories:")
    print(final_df[['repository_name', 'project_name', 'scorecard_score', 'criticality_score']].head().to_string(index=False))
    
    print(f"\n✅ Simple CSV created successfully!")
    print(f"📁 File: {output_filename}")
    
    return final_df


if __name__ == "__main__":
    create_simple_merged_csv()
