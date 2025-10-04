"""Analysis tools for dependency data."""

import logging
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import json
from pathlib import Path

import pandas as pd

from database import db

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Analyzer for dependency data and ecosystem insights."""
    
    def __init__(self):
        self.db = db
    
    def get_most_popular_dependencies(self, limit: int = 50, 
                                    ecosystem: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get most popular dependencies across all projects."""
        query = """
            SELECT dependency_name, ecosystem, COUNT(*) as usage_count,
                   COUNT(DISTINCT project_id) as project_count
            FROM dependencies
        """
        params = []
        
        if ecosystem:
            query += " WHERE ecosystem = ?"
            params.append(ecosystem)
        
        query += """
            GROUP BY dependency_name, ecosystem
            ORDER BY usage_count DESC
            LIMIT ?
        """
        params.append(limit)
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
        
        return [
            {
                'name': row[0],
                'ecosystem': row[1],
                'usage_count': row[2],
                'project_count': row[3]
            }
            for row in results
        ]
    
    def analyze_by_category(self) -> Dict[str, Any]:
        """Analyze dependency patterns by project category."""
        query = """
            SELECT p.category, d.dependency_name, d.ecosystem, COUNT(*) as usage_count
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            WHERE p.category IS NOT NULL
            GROUP BY p.category, d.dependency_name, d.ecosystem
            ORDER BY p.category, usage_count DESC
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
        
        # Group by category
        category_analysis = defaultdict(lambda: defaultdict(int))
        category_ecosystems = defaultdict(Counter)
        
        for category, dep_name, ecosystem, count in results:
            category_analysis[category][dep_name] += count
            category_ecosystems[category][ecosystem] += count
        
        # Format results
        analysis = {}
        for category in category_analysis:
            top_deps = sorted(
                category_analysis[category].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            analysis[category] = {
                'top_dependencies': [{'name': name, 'count': count} for name, count in top_deps],
                'ecosystem_distribution': dict(category_ecosystems[category]),
                'total_dependencies': sum(category_analysis[category].values())
            }
        
        return analysis
    
    def analyze_by_language(self) -> Dict[str, Any]:
        """Analyze dependency patterns by programming language."""
        query = """
            SELECT p.language, d.dependency_name, d.ecosystem, COUNT(*) as usage_count
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            WHERE p.language IS NOT NULL AND p.language != 'unknown'
            GROUP BY p.language, d.dependency_name, d.ecosystem
            ORDER BY p.language, usage_count DESC
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
        
        # Group by language
        language_analysis = defaultdict(lambda: defaultdict(int))
        language_ecosystems = defaultdict(Counter)
        
        for language, dep_name, ecosystem, count in results:
            language_analysis[language][dep_name] += count
            language_ecosystems[language][ecosystem] += count
        
        # Format results
        analysis = {}
        for language in language_analysis:
            top_deps = sorted(
                language_analysis[language].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            analysis[language] = {
                'top_dependencies': [{'name': name, 'count': count} for name, count in top_deps],
                'ecosystem_distribution': dict(language_ecosystems[language]),
                'total_dependencies': sum(language_analysis[language].values())
            }
        
        return analysis
    
    def analyze_community_patterns(self) -> Dict[str, Any]:
        """Analyze dependency patterns by community type (academic vs commercial)."""
        # First, we need to load the community data from matched.json
        matched_data = self._load_community_data()
        if not matched_data:
            return {'error': 'Community data not available'}
        
        # Create URL to community type mapping
        url_to_community = {}
        for project in matched_data:
            url_to_community[project['url']] = project['category']
        
        # Get projects with their dependencies
        query = """
            SELECT p.url, d.dependency_name, d.ecosystem, COUNT(*) as usage_count
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            GROUP BY p.url, d.dependency_name, d.ecosystem
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
        
        # Group by community type
        community_analysis = defaultdict(lambda: defaultdict(int))
        community_ecosystems = defaultdict(Counter)
        
        for url, dep_name, ecosystem, count in results:
            community_type = url_to_community.get(url, 'UNKNOWN')
            community_analysis[community_type][dep_name] += count
            community_ecosystems[community_type][ecosystem] += count
        
        # Format results
        analysis = {}
        for community_type in community_analysis:
            top_deps = sorted(
                community_analysis[community_type].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            analysis[community_type] = {
                'top_dependencies': [{'name': name, 'count': count} for name, count in top_deps],
                'ecosystem_distribution': dict(community_ecosystems[community_type]),
                'total_dependencies': sum(community_analysis[community_type].values())
            }
        
        return analysis
    
    def _load_community_data(self) -> Optional[List[Dict[str, Any]]]:
        """Load community classification data from matched.json."""
        try:
            matched_path = Path(__file__).parent.parent / "matched.json"
            if matched_path.exists():
                with open(matched_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading community data: {e}")
        return None
    
    def find_dependency_clusters(self, min_shared_deps: int = 3) -> List[Dict[str, Any]]:
        """Find clusters of projects that share many dependencies."""
        # Get project dependencies
        query = """
            SELECT p.id, p.name, p.url, p.category, 
                   GROUP_CONCAT(d.dependency_name) as dependencies
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            GROUP BY p.id
            HAVING COUNT(d.dependency_name) >= ?
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (min_shared_deps,))
            results = cursor.fetchall()
        
        # Build dependency sets for each project
        projects = []
        for row in results:
            project_id, name, url, category, deps_str = row
            dependencies = set(deps_str.split(',')) if deps_str else set()
            projects.append({
                'id': project_id,
                'name': name,
                'url': url,
                'category': category,
                'dependencies': dependencies
            })
        
        # Find clusters based on shared dependencies
        clusters = []
        processed = set()
        
        for i, project1 in enumerate(projects):
            if project1['id'] in processed:
                continue
            
            cluster = [project1]
            processed.add(project1['id'])
            
            for j, project2 in enumerate(projects[i+1:], i+1):
                if project2['id'] in processed:
                    continue
                
                shared_deps = project1['dependencies'] & project2['dependencies']
                if len(shared_deps) >= min_shared_deps:
                    cluster.append(project2)
                    processed.add(project2['id'])
            
            if len(cluster) > 1:
                # Calculate shared dependencies for the cluster
                all_deps = [p['dependencies'] for p in cluster]
                shared = set.intersection(*all_deps) if all_deps else set()
                
                clusters.append({
                    'projects': [{'name': p['name'], 'category': p['category']} for p in cluster],
                    'shared_dependencies': list(shared),
                    'cluster_size': len(cluster)
                })
        
        return sorted(clusters, key=lambda x: x['cluster_size'], reverse=True)
    
    def generate_ecosystem_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive ecosystem health report."""
        # Basic statistics
        stats = self.db.get_dependency_stats()
        
        # Language distribution
        query = """
            SELECT language, COUNT(*) as project_count
            FROM projects
            WHERE language IS NOT NULL AND language != 'unknown'
            GROUP BY language
            ORDER BY project_count DESC
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            language_dist = cursor.fetchall()
        
        # Dependency concentration (Gini coefficient approximation)
        dep_counts = [count for _, count in stats['top_dependencies']]
        concentration_score = self._calculate_concentration(dep_counts) if dep_counts else 0
        
        # Category distribution
        query = """
            SELECT category, COUNT(*) as project_count
            FROM projects
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY project_count DESC
        """
        
        with sqlite3.connect(str(self.db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            category_dist = cursor.fetchall()
        
        return {
            'overview': {
                'total_projects': stats['total_projects'],
                'projects_with_dependencies': stats['projects_with_dependencies'],
                'coverage_percentage': (stats['projects_with_dependencies'] / stats['total_projects'] * 100) if stats['total_projects'] > 0 else 0
            },
            'language_distribution': [{'language': lang, 'count': count} for lang, count in language_dist],
            'category_distribution': [{'category': cat, 'count': count} for cat, count in category_dist],
            'ecosystem_distribution': [{'ecosystem': eco, 'count': count} for eco, count in stats['ecosystem_distribution']],
            'dependency_concentration': {
                'score': concentration_score,
                'interpretation': self._interpret_concentration(concentration_score)
            },
            'top_dependencies': [{'name': name, 'count': count} for name, count in stats['top_dependencies'][:20]]
        }
    
    def _calculate_concentration(self, values: List[int]) -> float:
        """Calculate concentration score (simplified Gini coefficient)."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = sum((i + 1) * val for i, val in enumerate(sorted_values))
        return (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n
    
    def _interpret_concentration(self, score: float) -> str:
        """Interpret concentration score."""
        if score < 0.3:
            return "Low concentration - diverse ecosystem"
        elif score < 0.5:
            return "Moderate concentration - balanced ecosystem"
        elif score < 0.7:
            return "High concentration - some dominant dependencies"
        else:
            return "Very high concentration - ecosystem dominated by few dependencies"
    
    def export_analysis_to_csv(self, output_dir: Path) -> None:
        """Export various analyses to CSV files."""
        output_dir.mkdir(exist_ok=True)
        
        # Most popular dependencies
        popular_deps = self.get_most_popular_dependencies(100)
        df_popular = pd.DataFrame(popular_deps)
        df_popular.to_csv(output_dir / "popular_dependencies.csv", index=False)
        
        # Category analysis
        category_analysis = self.analyze_by_category()
        category_rows = []
        for category, data in category_analysis.items():
            for dep in data['top_dependencies']:
                category_rows.append({
                    'category': category,
                    'dependency': dep['name'],
                    'usage_count': dep['count']
                })
        df_category = pd.DataFrame(category_rows)
        df_category.to_csv(output_dir / "dependencies_by_category.csv", index=False)
        
        # Language analysis
        language_analysis = self.analyze_by_language()
        language_rows = []
        for language, data in language_analysis.items():
            for dep in data['top_dependencies']:
                language_rows.append({
                    'language': language,
                    'dependency': dep['name'],
                    'usage_count': dep['count']
                })
        df_language = pd.DataFrame(language_rows)
        df_language.to_csv(output_dir / "dependencies_by_language.csv", index=False)
        
        logger.info(f"Analysis exported to {output_dir}")


def main():
    """Main function for running analysis."""
    logging.basicConfig(level=logging.INFO)
    
    analyzer = DependencyAnalyzer()
    
    # Generate comprehensive report
    report = analyzer.generate_ecosystem_health_report()
    
    print("="*60)
    print("ENERGY SECTOR OPEN SOURCE ECOSYSTEM ANALYSIS")
    print("="*60)
    
    print(f"\nOVERVIEW:")
    print(f"  Total projects: {report['overview']['total_projects']}")
    print(f"  Projects with dependencies: {report['overview']['projects_with_dependencies']}")
    print(f"  Coverage: {report['overview']['coverage_percentage']:.1f}%")
    
    print(f"\nTOP PROGRAMMING LANGUAGES:")
    for lang_data in report['language_distribution'][:10]:
        print(f"  {lang_data['language']}: {lang_data['count']} projects")
    
    print(f"\nTOP PROJECT CATEGORIES:")
    for cat_data in report['category_distribution'][:10]:
        print(f"  {cat_data['category']}: {cat_data['count']} projects")
    
    print(f"\nECOSYSTEM DISTRIBUTION:")
    for eco_data in report['ecosystem_distribution']:
        print(f"  {eco_data['ecosystem']}: {eco_data['count']} dependencies")
    
    print(f"\nTOP 15 MOST USED DEPENDENCIES:")
    for dep_data in report['top_dependencies'][:15]:
        print(f"  {dep_data['name']}: {dep_data['count']} projects")
    
    print(f"\nDEPENDENCY CONCENTRATION:")
    print(f"  Score: {report['dependency_concentration']['score']:.3f}")
    print(f"  {report['dependency_concentration']['interpretation']}")
    
    # Export detailed analysis
    output_dir = Path("analysis_output")
    analyzer.export_analysis_to_csv(output_dir)
    print(f"\nDetailed analysis exported to {output_dir}/")


if __name__ == "__main__":
    main()
