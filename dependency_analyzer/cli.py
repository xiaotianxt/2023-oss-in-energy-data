"""Command-line interface for the dependency analyzer."""

import click
import logging
from pathlib import Path

from extractor import DependencyExtractor
from analyzer import DependencyAnalyzer
from database import db


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Energy Sector Dependency Analyzer - Extract and analyze dependencies from open source energy projects."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.option('--resume', is_flag=True, default=True, help='Resume from where extraction left off')
@click.option('--batch-size', default=50, help='Number of projects to process in each batch')
def extract(resume, batch_size):
    """Extract dependencies from all projects in the YAML file."""
    click.echo("Starting dependency extraction...")
    
    extractor = DependencyExtractor()
    results = extractor.extract_all_projects(resume=resume)
    
    if results['status'] == 'complete':
        click.echo(f"\n✓ Extraction completed successfully!")
        click.echo(f"  Processed: {results['total_projects']} projects")
        click.echo(f"  Successful: {results['successful']}")
        click.echo(f"  No dependencies: {results['no_dependencies']}")
        click.echo(f"  Errors: {results['errors']}")
    else:
        click.echo(f"✗ Extraction failed: {results.get('message', 'Unknown error')}")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def export(format, output):
    """Export extracted data."""
    if format == 'json':
        output_path = Path(output) if output else Path('energy_dependencies.json')
        db.export_to_json(output_path)
        click.echo(f"✓ Data exported to {output_path}")
    elif format == 'csv':
        output_dir = Path(output) if output else Path('csv_export')
        analyzer = DependencyAnalyzer()
        analyzer.export_analysis_to_csv(output_dir)
        click.echo(f"✓ Analysis exported to {output_dir}/")


@cli.command()
def analyze():
    """Run comprehensive dependency analysis."""
    click.echo("Running dependency analysis...")
    
    analyzer = DependencyAnalyzer()
    report = analyzer.generate_ecosystem_health_report()
    
    click.echo("\n" + "="*60)
    click.echo("ENERGY SECTOR OPEN SOURCE ECOSYSTEM ANALYSIS")
    click.echo("="*60)
    
    click.echo(f"\nOVERVIEW:")
    click.echo(f"  Total projects: {report['overview']['total_projects']}")
    click.echo(f"  Projects with dependencies: {report['overview']['projects_with_dependencies']}")
    click.echo(f"  Coverage: {report['overview']['coverage_percentage']:.1f}%")
    
    click.echo(f"\nTOP PROGRAMMING LANGUAGES:")
    for lang_data in report['language_distribution'][:10]:
        click.echo(f"  {lang_data['language']}: {lang_data['count']} projects")
    
    click.echo(f"\nTOP PROJECT CATEGORIES:")
    for cat_data in report['category_distribution'][:10]:
        click.echo(f"  {cat_data['category']}: {cat_data['count']} projects")
    
    click.echo(f"\nECOSYSTEM DISTRIBUTION:")
    for eco_data in report['ecosystem_distribution']:
        click.echo(f"  {eco_data['ecosystem']}: {eco_data['count']} dependencies")
    
    click.echo(f"\nTOP 15 MOST USED DEPENDENCIES:")
    for dep_data in report['top_dependencies'][:15]:
        click.echo(f"  {dep_data['name']}: {dep_data['count']} projects")
    
    click.echo(f"\nDEPENDENCY CONCENTRATION:")
    click.echo(f"  Score: {report['dependency_concentration']['score']:.3f}")
    click.echo(f"  {report['dependency_concentration']['interpretation']}")


@cli.command()
@click.option('--limit', default=20, help='Number of top dependencies to show')
@click.option('--ecosystem', help='Filter by ecosystem (pypi, npm, maven, etc.)')
def popular(limit, ecosystem):
    """Show most popular dependencies."""
    analyzer = DependencyAnalyzer()
    deps = analyzer.get_most_popular_dependencies(limit=limit, ecosystem=ecosystem)
    
    title = f"TOP {limit} DEPENDENCIES"
    if ecosystem:
        title += f" ({ecosystem.upper()})"
    
    click.echo(f"\n{title}")
    click.echo("="*len(title))
    
    for i, dep in enumerate(deps, 1):
        click.echo(f"{i:2d}. {dep['name']} ({dep['ecosystem']})")
        click.echo(f"    Used by {dep['project_count']} projects")


@cli.command()
def categories():
    """Analyze dependencies by project category."""
    analyzer = DependencyAnalyzer()
    analysis = analyzer.analyze_by_category()
    
    click.echo("\nDEPENDENCIES BY PROJECT CATEGORY")
    click.echo("="*40)
    
    for category, data in analysis.items():
        click.echo(f"\n{category.upper()}:")
        click.echo(f"  Total dependencies: {data['total_dependencies']}")
        click.echo(f"  Top dependencies:")
        for dep in data['top_dependencies'][:5]:
            click.echo(f"    - {dep['name']}: {dep['count']} uses")


@cli.command()
def languages():
    """Analyze dependencies by programming language."""
    analyzer = DependencyAnalyzer()
    analysis = analyzer.analyze_by_language()
    
    click.echo("\nDEPENDENCIES BY PROGRAMMING LANGUAGE")
    click.echo("="*40)
    
    for language, data in analysis.items():
        click.echo(f"\n{language.upper()}:")
        click.echo(f"  Total dependencies: {data['total_dependencies']}")
        click.echo(f"  Top dependencies:")
        for dep in data['top_dependencies'][:5]:
            click.echo(f"    - {dep['name']}: {dep['count']} uses")


@cli.command()
@click.option('--min-shared', default=3, help='Minimum shared dependencies for clustering')
def clusters(min_shared):
    """Find clusters of projects with shared dependencies."""
    analyzer = DependencyAnalyzer()
    clusters = analyzer.find_dependency_clusters(min_shared_deps=min_shared)
    
    click.echo(f"\nPROJECT CLUSTERS (min {min_shared} shared dependencies)")
    click.echo("="*50)
    
    for i, cluster in enumerate(clusters[:10], 1):
        click.echo(f"\nCluster {i} ({cluster['cluster_size']} projects):")
        click.echo(f"  Shared dependencies: {', '.join(cluster['shared_dependencies'][:10])}")
        click.echo(f"  Projects:")
        for project in cluster['projects']:
            click.echo(f"    - {project['name']} ({project['category']})")


@cli.command()
def stats():
    """Show basic statistics."""
    stats = db.get_dependency_stats()
    
    click.echo("\nDATABASE STATISTICS")
    click.echo("="*30)
    click.echo(f"Total projects: {stats['total_projects']}")
    click.echo(f"Projects with dependencies: {stats['projects_with_dependencies']}")
    click.echo(f"Coverage: {(stats['projects_with_dependencies']/stats['total_projects']*100):.1f}%")
    
    click.echo(f"\nEcosystem distribution:")
    for ecosystem, count in stats['ecosystem_distribution']:
        click.echo(f"  {ecosystem}: {count}")


@cli.command()
@click.option('--github-token', prompt=True, hide_input=True, help='GitHub API token')
def setup(github_token):
    """Setup the analyzer with GitHub token."""
    env_file = Path('.env')
    
    with open(env_file, 'w') as f:
        f.write(f"GITHUB_TOKEN={github_token}\n")
    
    click.echo(f"✓ GitHub token saved to {env_file}")
    click.echo("You can now run extraction with: python cli.py extract")


if __name__ == '__main__':
    cli()

