#!/usr/bin/env python3
"""
Advanced Analysis of Final Merged Results

This script performs comprehensive analysis of the merged scorecard and criticality data,
generating insights, visualizations, and actionable recommendations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set style for better plots
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)


def load_and_prepare_data(filename: str) -> pd.DataFrame:
    """Load and prepare the merged dataset."""
    df = pd.read_csv(filename)
    
    # Convert boolean columns
    bool_cols = ['has_scorecard', 'has_criticality', 'has_both']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)
    
    # Convert date columns
    date_cols = ['repo_created_at', 'repo_updated_at']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    print(f"Loaded dataset with {len(df)} repositories")
    print(f"Columns: {len(df.columns)}")
    
    return df


def analyze_score_correlation(df: pd.DataFrame) -> Dict:
    """Analyze correlation between scorecard and criticality scores."""
    both_scores = df[df['has_both']].copy()
    
    if len(both_scores) < 10:
        return {"error": "Not enough data for correlation analysis"}
    
    correlation = both_scores['scorecard_aggregate'].corr(both_scores['criticality_score'])
    
    # Perform statistical tests
    scorecard_scores = both_scores['scorecard_aggregate'].dropna()
    criticality_scores = both_scores['criticality_score'].dropna()
    
    # Spearman correlation (rank-based, more robust)
    spearman_corr, spearman_p = stats.spearmanr(scorecard_scores, criticality_scores)
    
    # Kendall's tau
    kendall_corr, kendall_p = stats.kendalltau(scorecard_scores, criticality_scores)
    
    return {
        "sample_size": len(both_scores),
        "pearson_correlation": correlation,
        "spearman_correlation": spearman_corr,
        "spearman_p_value": spearman_p,
        "kendall_correlation": kendall_corr,
        "kendall_p_value": kendall_p,
        "interpretation": "weak" if abs(correlation) < 0.3 else "moderate" if abs(correlation) < 0.7 else "strong"
    }


def identify_top_repositories(df: pd.DataFrame) -> Dict:
    """Identify top repositories by various criteria."""
    both_scores = df[df['has_both']].copy()
    
    results = {}
    
    # Top by scorecard (security)
    top_scorecard = both_scores.nlargest(10, 'scorecard_aggregate')[
        ['repo_name', 'project_name', 'category', 'scorecard_aggregate', 'criticality_score']
    ]
    results['top_security'] = top_scorecard.to_dict('records')
    
    # Top by criticality (importance)
    top_criticality = both_scores.nlargest(10, 'criticality_score')[
        ['repo_name', 'project_name', 'category', 'scorecard_aggregate', 'criticality_score']
    ]
    results['top_criticality'] = top_criticality.to_dict('records')
    
    # Best balanced (high in both)
    both_scores['combined_score'] = (
        (both_scores['scorecard_aggregate'] / 10) * 0.5 + 
        both_scores['criticality_score'] * 0.5
    )
    top_balanced = both_scores.nlargest(10, 'combined_score')[
        ['repo_name', 'project_name', 'category', 'scorecard_aggregate', 'criticality_score', 'combined_score']
    ]
    results['top_balanced'] = top_balanced.to_dict('records')
    
    # Most concerning (high criticality, low security)
    concerning = both_scores[
        (both_scores['criticality_score'] > both_scores['criticality_score'].quantile(0.75)) &
        (both_scores['scorecard_aggregate'] < both_scores['scorecard_aggregate'].quantile(0.25))
    ].sort_values('criticality_score', ascending=False)[
        ['repo_name', 'project_name', 'category', 'scorecard_aggregate', 'criticality_score']
    ]
    results['most_concerning'] = concerning.to_dict('records')
    
    return results


def analyze_by_category(df: pd.DataFrame) -> Dict:
    """Analyze repositories by category."""
    category_stats = {}
    
    for category in df['category'].unique():
        if pd.isna(category):
            continue
            
        cat_data = df[df['category'] == category]
        
        stats_dict = {
            'count': len(cat_data),
            'with_both_scores': cat_data['has_both'].sum(),
            'scorecard_mean': cat_data['scorecard_aggregate'].mean() if 'scorecard_aggregate' in cat_data else None,
            'criticality_mean': cat_data['criticality_score'].mean() if 'criticality_score' in cat_data else None,
        }
        
        # Add top repository in this category
        both_scores_cat = cat_data[cat_data['has_both']]
        if len(both_scores_cat) > 0:
            top_repo = both_scores_cat.loc[both_scores_cat['scorecard_aggregate'].idxmax()]
            stats_dict['top_security_repo'] = {
                'name': top_repo['repo_name'],
                'scorecard': top_repo['scorecard_aggregate'],
                'criticality': top_repo['criticality_score']
            }
        
        category_stats[category] = stats_dict
    
    return category_stats


def create_visualizations(df: pd.DataFrame):
    """Create comprehensive visualizations."""
    both_scores = df[df['has_both']].copy()
    
    # Create a large figure with multiple subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Scatter plot: Scorecard vs Criticality
    ax1 = plt.subplot(3, 3, 1)
    scatter = ax1.scatter(both_scores['criticality_score'], both_scores['scorecard_aggregate'], 
                         alpha=0.6, s=50, c=both_scores['repo_stars'], cmap='viridis')
    ax1.set_xlabel('Criticality Score')
    ax1.set_ylabel('Scorecard Score')
    ax1.set_title('Security vs Criticality Scores')
    plt.colorbar(scatter, ax=ax1, label='GitHub Stars')
    
    # Add trend line
    z = np.polyfit(both_scores['criticality_score'], both_scores['scorecard_aggregate'], 1)
    p = np.poly1d(z)
    ax1.plot(both_scores['criticality_score'], p(both_scores['criticality_score']), "r--", alpha=0.8)
    
    # 2. Distribution of Scorecard scores
    ax2 = plt.subplot(3, 3, 2)
    ax2.hist(df['scorecard_aggregate'].dropna(), bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    ax2.axvline(df['scorecard_aggregate'].mean(), color='red', linestyle='--', 
                label=f'Mean: {df["scorecard_aggregate"].mean():.2f}')
    ax2.set_xlabel('Scorecard Score')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Security Scores')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Distribution of Criticality scores
    ax3 = plt.subplot(3, 3, 3)
    ax3.hist(df['criticality_score'].dropna(), bins=30, alpha=0.7, color='lightcoral', edgecolor='black')
    ax3.axvline(df['criticality_score'].mean(), color='red', linestyle='--', 
                label=f'Mean: {df["criticality_score"].mean():.4f}')
    ax3.set_xlabel('Criticality Score')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Distribution of Criticality Scores')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Category analysis
    ax4 = plt.subplot(3, 3, 4)
    category_counts = df['category'].value_counts().head(10)
    category_counts.plot(kind='bar', ax=ax4, color='lightgreen', alpha=0.7)
    ax4.set_title('Top 10 Categories by Repository Count')
    ax4.set_xlabel('Category')
    ax4.set_ylabel('Count')
    ax4.tick_params(axis='x', rotation=45)
    
    # 5. Risk assessment distribution
    ax5 = plt.subplot(3, 3, 5)
    risk_counts = df['risk_assessment'].value_counts()
    colors = ['green', 'yellow', 'orange', 'red', 'gray']
    wedges, texts, autotexts = ax5.pie(risk_counts.values, labels=risk_counts.index, 
                                       autopct='%1.1f%%', colors=colors[:len(risk_counts)])
    ax5.set_title('Risk Assessment Distribution')
    
    # 6. Language analysis
    ax6 = plt.subplot(3, 3, 6)
    lang_counts = df['repo_language'].value_counts().head(10)
    lang_counts.plot(kind='barh', ax=ax6, color='purple', alpha=0.7)
    ax6.set_title('Top 10 Programming Languages')
    ax6.set_xlabel('Count')
    
    # 7. Stars vs Scores
    ax7 = plt.subplot(3, 3, 7)
    valid_stars = both_scores[both_scores['repo_stars'].notna() & (both_scores['repo_stars'] > 0)]
    if len(valid_stars) > 0:
        ax7.scatter(np.log10(valid_stars['repo_stars']), valid_stars['scorecard_aggregate'], 
                   alpha=0.6, color='orange')
        ax7.set_xlabel('Log10(GitHub Stars)')
        ax7.set_ylabel('Scorecard Score')
        ax7.set_title('Popularity vs Security Score')
    
    # 8. Timeline analysis
    ax8 = plt.subplot(3, 3, 8)
    df_with_dates = df[df['repo_created_at'].notna()].copy()
    if len(df_with_dates) > 0:
        df_with_dates['creation_year'] = df_with_dates['repo_created_at'].dt.year
        yearly_counts = df_with_dates['creation_year'].value_counts().sort_index()
        yearly_counts.plot(kind='line', ax=ax8, marker='o', color='teal')
        ax8.set_title('Repository Creation Timeline')
        ax8.set_xlabel('Year')
        ax8.set_ylabel('Repositories Created')
    
    # 9. Security check analysis
    ax9 = plt.subplot(3, 3, 9)
    security_checks = [col for col in df.columns if col.startswith('scorecard_') and col != 'scorecard_aggregate']
    if security_checks:
        check_means = df[security_checks].mean().sort_values(ascending=True)
        check_means.plot(kind='barh', ax=ax9, color='red', alpha=0.7)
        ax9.set_title('Average Scores by Security Check')
        ax9.set_xlabel('Average Score')
        # Clean up check names for display
        ax9.set_yticklabels([label.get_text().replace('scorecard_', '').replace('_', ' ').title() 
                            for label in ax9.get_yticklabels()])
    
    plt.tight_layout()
    plt.savefig('comprehensive_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("✓ Saved comprehensive analysis visualization: comprehensive_analysis.png")


def generate_recommendations(df: pd.DataFrame, top_repos: Dict, correlation_analysis: Dict) -> List[str]:
    """Generate actionable recommendations based on analysis."""
    recommendations = []
    
    both_scores = df[df['has_both']]
    
    # Security recommendations
    low_security = both_scores[both_scores['scorecard_aggregate'] < 4]
    if len(low_security) > 0:
        recommendations.append(
            f"🔒 SECURITY PRIORITY: {len(low_security)} repositories have security scores below 4/10. "
            f"Focus on improving basic security practices like branch protection, code review, and dependency management."
        )
    
    # Criticality recommendations
    high_criticality_low_security = both_scores[
        (both_scores['criticality_score'] > both_scores['criticality_score'].quantile(0.8)) &
        (both_scores['scorecard_aggregate'] < both_scores['scorecard_aggregate'].quantile(0.4))
    ]
    if len(high_criticality_low_security) > 0:
        recommendations.append(
            f"⚠️ HIGH RISK: {len(high_criticality_low_security)} critical repositories have poor security scores. "
            f"These should be immediate priorities for security improvements."
        )
    
    # Category-specific recommendations
    category_stats = analyze_by_category(df)
    worst_category = min(category_stats.items(), 
                        key=lambda x: x[1]['scorecard_mean'] if x[1]['scorecard_mean'] else 0)
    if worst_category[1]['scorecard_mean']:
        recommendations.append(
            f"📂 CATEGORY FOCUS: '{worst_category[0]}' category has the lowest average security score "
            f"({worst_category[1]['scorecard_mean']:.2f}). Consider category-wide security initiatives."
        )
    
    # Correlation insights
    if correlation_analysis.get('pearson_correlation'):
        corr = correlation_analysis['pearson_correlation']
        if abs(corr) < 0.2:
            recommendations.append(
                f"📊 INSIGHT: Very weak correlation ({corr:.3f}) between criticality and security scores suggests "
                f"that important projects aren't necessarily more secure. Security efforts should be independent of project importance."
            )
        elif corr < -0.3:
            recommendations.append(
                f"📊 CONCERNING: Negative correlation ({corr:.3f}) suggests more critical projects might be less secure. "
                f"This requires immediate attention to critical infrastructure security."
            )
    
    # Success stories
    if top_repos.get('top_balanced'):
        top_balanced = top_repos['top_balanced'][0]
        recommendations.append(
            f"🏆 SUCCESS MODEL: '{top_balanced['project_name']}' ({top_balanced['repo_name']}) "
            f"achieves both high security ({top_balanced['scorecard_aggregate']:.1f}/10) and high criticality "
            f"({top_balanced['criticality_score']:.3f}). Study their practices as a model."
        )
    
    # Data completeness
    missing_data = len(df) - len(both_scores)
    if missing_data > 0:
        recommendations.append(
            f"📈 DATA IMPROVEMENT: {missing_data} repositories lack complete data. "
            f"Prioritize data collection for comprehensive risk assessment."
        )
    
    return recommendations


def main():
    """Main analysis function."""
    print("=" * 70)
    print("COMPREHENSIVE ANALYSIS OF MERGED SECURITY & CRITICALITY DATA")
    print("=" * 70)
    
    # Load data
    print("\n1. Loading merged dataset...")
    df = load_and_prepare_data('final_merged_results.csv')
    
    # Basic statistics
    print("\n2. Computing basic statistics...")
    print(f"   • Total repositories: {len(df)}")
    print(f"   • With both scores: {df['has_both'].sum()}")
    print(f"   • Average security score: {df['scorecard_aggregate'].mean():.2f}/10")
    print(f"   • Average criticality score: {df['criticality_score'].mean():.4f}")
    
    # Correlation analysis
    print("\n3. Analyzing score correlations...")
    correlation_analysis = analyze_score_correlation(df)
    if 'error' not in correlation_analysis:
        print(f"   • Pearson correlation: {correlation_analysis['pearson_correlation']:.3f}")
        print(f"   • Spearman correlation: {correlation_analysis['spearman_correlation']:.3f}")
        print(f"   • Relationship strength: {correlation_analysis['interpretation']}")
    
    # Top repositories
    print("\n4. Identifying top repositories...")
    top_repos = identify_top_repositories(df)
    print(f"   • Top security: {top_repos['top_security'][0]['project_name']} ({top_repos['top_security'][0]['scorecard_aggregate']:.1f}/10)")
    print(f"   • Top criticality: {top_repos['top_criticality'][0]['project_name']} ({top_repos['top_criticality'][0]['criticality_score']:.4f})")
    if top_repos['most_concerning']:
        print(f"   • Most concerning: {len(top_repos['most_concerning'])} high-criticality, low-security repos")
    
    # Category analysis
    print("\n5. Analyzing by category...")
    category_stats = analyze_by_category(df)
    print(f"   • Categories analyzed: {len(category_stats)}")
    
    # Create visualizations
    print("\n6. Creating visualizations...")
    create_visualizations(df)
    
    # Generate recommendations
    print("\n7. Generating recommendations...")
    recommendations = generate_recommendations(df, top_repos, correlation_analysis)
    
    # Save detailed analysis
    analysis_results = {
        'summary_statistics': {
            'total_repositories': len(df),
            'repositories_with_both_scores': int(df['has_both'].sum()),
            'average_security_score': float(df['scorecard_aggregate'].mean()),
            'average_criticality_score': float(df['criticality_score'].mean()),
        },
        'correlation_analysis': correlation_analysis,
        'top_repositories': top_repos,
        'category_analysis': category_stats,
        'recommendations': recommendations
    }
    
    with open('detailed_analysis_results.json', 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    
    print("✓ Saved detailed analysis: detailed_analysis_results.json")
    
    # Print recommendations
    print("\n" + "=" * 70)
    print("🎯 KEY RECOMMENDATIONS")
    print("=" * 70)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    print(f"\n✅ Analysis completed successfully!")
    print(f"📊 Generated files:")
    print(f"   • comprehensive_analysis.png - Visual analysis")
    print(f"   • detailed_analysis_results.json - Complete analysis data")
    print(f"   • final_merged_results.csv - Full dataset")
    print(f"   • repositories_with_both_scores.csv - Complete data subset")


if __name__ == "__main__":
    main()
