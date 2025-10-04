#!/usr/bin/env python3
"""
Create Fixed Detailed Scorecard CSV

This script correctly extracts detailed scorecard results with all individual check scores.
Fixed to handle the correct format: check.Check-Name.score: value
"""

import pandas as pd
import re
from typing import Dict, List, Optional


def extract_detailed_scorecard_scores(filename: str) -> List[Dict]:
    """Extract detailed scorecard results with all individual check scores."""
    results = []
    
    # All possible Scorecard checks (as they appear in the data)
    scorecard_checks = [
        'Binary-Artifacts',
        'Branch-Protection', 
        'CI-Tests',
        'CII-Best-Practices',
        'Code-Review',
        'Contributors',
        'Dangerous-Workflow',
        'Dependency-Update-Tool',
        'Fuzzing',
        'License',
        'Maintained',
        'Packaging',
        'Pinned-Dependencies',
        'SAST',
        'Security-Policy',
        'Signed-Releases',
        'Token-Permissions',
        'Vulnerabilities'
    ]
    
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
                aggregate_match = re.search(r'aggregate_score: ([\d.]+)', section)
                aggregate_score = float(aggregate_match.group(1)) if aggregate_match else None
                
                # Extract repo name from URL
                repo_name = repo_url.replace('https://github.com/', '')
                
                # Initialize result dictionary
                result = {
                    'repository_name': repo_name,
                    'repository_url': repo_url,
                    'project_name': project_name,
                    'category': category,
                    'scorecard_aggregate': aggregate_score
                }
                
                # Extract individual check scores using the correct format
                for check_name in scorecard_checks:
                    # Look for the score line for this check: check.Check-Name.score: value
                    check_pattern = rf'check\.{re.escape(check_name)}\.score: ([-\d.]+)'
                    check_match = re.search(check_pattern, section)
                    
                    if check_match:
                        score_value = check_match.group(1)
                        # Convert -1 (not applicable) to None, otherwise to float
                        if score_value == '-1':
                            result[f'scorecard_{check_name.lower().replace("-", "_")}'] = None
                        else:
                            result[f'scorecard_{check_name.lower().replace("-", "_")}'] = float(score_value)
                    else:
                        # If check not found, set to None
                        result[f'scorecard_{check_name.lower().replace("-", "_")}'] = None
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing scorecard section: {e}")
                continue
    
    print(f"Extracted {len(results)} detailed scorecard results")
    return results


def extract_criticality_scores(filename: str) -> List[Dict]:
    """Extract criticality score results."""
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
                    'repository_name': repo_name,
                    'repository_url': repo_url,
                    'criticality_score': criticality_score
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing criticality section: {e}")
                continue
    
    print(f"Extracted {len(results)} criticality results")
    return results


def create_detailed_csv():
    """Create a detailed CSV with all individual scorecard check scores."""
    
    print("=" * 70)
    print("CREATING FIXED DETAILED SCORECARD CSV")
    print("=" * 70)
    
    # Extract data from both files
    print("\n1. Extracting detailed Scorecard data...")
    scorecard_data = extract_detailed_scorecard_scores('scorecard_results.txt')
    
    print("\n2. Extracting Criticality Score data...")
    criticality_data = extract_criticality_scores('criticality_scores.txt')
    
    # Convert to DataFrames
    scorecard_df = pd.DataFrame(scorecard_data)
    criticality_df = pd.DataFrame(criticality_data)
    
    print(f"\n3. Merging datasets...")
    print(f"   Detailed Scorecard: {len(scorecard_df)} repositories")
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
    
    # Define column order for better readability
    basic_columns = [
        'repository_name',
        'repository_url', 
        'project_name',
        'category',
        'scorecard_aggregate',
        'criticality_score'
    ]
    
    # All scorecard check columns
    scorecard_columns = [
        'scorecard_binary_artifacts',
        'scorecard_branch_protection',
        'scorecard_ci_tests',
        'scorecard_cii_best_practices',
        'scorecard_code_review',
        'scorecard_contributors',
        'scorecard_dangerous_workflow',
        'scorecard_dependency_update_tool',
        'scorecard_fuzzing',
        'scorecard_license',
        'scorecard_maintained',
        'scorecard_packaging',
        'scorecard_pinned_dependencies',
        'scorecard_sast',
        'scorecard_security_policy',
        'scorecard_signed_releases',
        'scorecard_token_permissions',
        'scorecard_vulnerabilities'
    ]
    
    # Reorder columns
    final_columns = basic_columns + scorecard_columns
    
    # Only include columns that exist in the dataframe
    existing_columns = [col for col in final_columns if col in merged_df.columns]
    final_df = merged_df[existing_columns].copy()
    
    # Sort by repository name
    final_df = final_df.sort_values('repository_name')
    
    print(f"   Merged: {len(final_df)} repositories")
    print(f"   Columns: {len(final_df.columns)}")
    
    # Save the detailed CSV
    output_filename = 'repository_detailed_scores_fixed.csv'
    final_df.to_csv(output_filename, index=False)
    
    print(f"\n4. Results saved to: {output_filename}")
    
    # Print detailed statistics
    print(f"\n" + "=" * 70)
    print("DETAILED STATISTICS")
    print("=" * 70)
    print(f"Total repositories: {len(final_df)}")
    
    has_scorecard = final_df['scorecard_aggregate'].notna()
    has_criticality = final_df['criticality_score'].notna()
    
    print(f"With Scorecard data: {has_scorecard.sum()}")
    print(f"With Criticality data: {has_criticality.sum()}")
    print(f"With both scores: {(has_scorecard & has_criticality).sum()}")
    
    # Show individual check statistics with more detail
    print(f"\nIndividual Scorecard Check Statistics:")
    print(f"{'Check Name':<30} {'Count':<8} {'Avg':<6} {'Min':<6} {'Max':<6} {'Coverage':<10}")
    print("-" * 70)
    
    for col in scorecard_columns:
        if col in final_df.columns:
            non_null_data = final_df[col].dropna()
            if len(non_null_data) > 0:
                count = len(non_null_data)
                avg_score = non_null_data.mean()
                min_score = non_null_data.min()
                max_score = non_null_data.max()
                coverage = f"{count}/{len(final_df)}"
                
                check_name = col.replace('scorecard_', '').replace('_', '-').title()
                print(f"{check_name:<30} {count:<8} {avg_score:<6.1f} {min_score:<6.0f} {max_score:<6.0f} {coverage:<10}")
    
    # Show sample data with more checks
    print(f"\nSample data (first 3 repositories with all basic info):")
    sample_cols = ['repository_name', 'scorecard_aggregate', 'criticality_score']
    sample_scorecard_cols = [col for col in scorecard_columns[:8] if col in final_df.columns]  # First 8 checks
    display_cols = sample_cols + sample_scorecard_cols
    
    sample_data = final_df[display_cols].head(3)
    print(sample_data.to_string(index=False))
    
    # Check for any completely empty scorecard data
    empty_scorecard = final_df[has_scorecard]
    if len(empty_scorecard) > 0:
        all_checks_null = True
        for col in scorecard_columns:
            if col in final_df.columns and final_df[col].notna().sum() > 0:
                all_checks_null = False
                break
        
        if all_checks_null:
            print(f"\n⚠️  WARNING: All individual check scores are null!")
        else:
            print(f"\n✅ Individual check scores successfully extracted!")
    
    print(f"\n✅ Fixed detailed CSV created successfully!")
    print(f"📁 File: {output_filename}")
    
    return final_df


if __name__ == "__main__":
    create_detailed_csv()
