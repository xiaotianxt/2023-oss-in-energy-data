"""Command-line interface for the dependency analyzer."""

import click
import logging
from pathlib import Path
import json
from datetime import datetime

from extractor import DependencyExtractor
from analyzer import DependencyAnalyzer
from database import db
from cve_scanner import CVEScanner
from dependency_resolver import DependencyResolver
from impact_analyzer import ImpactAnalyzer
from sbom_scraper import get_sbom_scraper
from sbom_cve_scanner import get_sbom_cve_scanner
from multi_tier_scanner import get_python_scanner, get_multi_language_scanner


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


@cli.command()
@click.option('--force-refresh', is_flag=True, help='Force refresh CVE data even if cached')
def scan_cves(force_refresh):
    """Scan all dependencies for known CVEs using OSV database."""
    click.echo("Scanning dependencies for CVEs...")
    click.echo("This may take a while depending on the number of unique packages.\n")

    scanner = CVEScanner()
    results = scanner.scan_all_dependencies(force_refresh=force_refresh)

    click.echo("\n" + "="*60)
    click.echo("CVE SCAN RESULTS")
    click.echo("="*60)
    click.echo(f"Total packages scanned: {results['total_packages_scanned']}")
    click.echo(f"Packages with CVEs: {results['packages_with_cves']}")
    click.echo(f"Total CVEs found: {results['total_cves_found']}")

    if results['total_cves_found'] > 0:
        summary = scanner.get_cve_summary()

        click.echo(f"\nSeverity Distribution:")
        for severity, count in summary['severity_distribution'].items():
            click.echo(f"  {severity}: {count}")

        click.echo(f"\nTop 10 Most Vulnerable Packages:")
        for pkg_info in summary['top_vulnerable_packages'][:10]:
            click.echo(f"  {pkg_info['package']}: {pkg_info['cve_count']} CVEs")


@cli.command()
@click.argument('package_name')
@click.argument('ecosystem')
@click.option('--max-depth', default=3, help='Maximum depth for recursive resolution')
def resolve(package_name, ecosystem, max_depth):
    """Resolve transitive dependencies for a specific package."""
    click.echo(f"Resolving dependencies for {package_name} ({ecosystem})...")
    click.echo(f"Maximum depth: {max_depth}\n")

    resolver = DependencyResolver(max_depth=max_depth)
    result = resolver.resolve_recursive(package_name, ecosystem)

    def print_tree(node, indent=0, prefix=""):
        if node.get('already_visited'):
            click.echo("  " * indent + f"{prefix}↻ {node['name']} (already visited)")
            return
        if node.get('max_depth_reached'):
            click.echo("  " * indent + f"{prefix}⋯ {node['name']} (max depth reached)")
            return

        name = node['name']
        eco = node.get('ecosystem', 'unknown')
        version = node.get('version', '')

        if indent == 0:
            click.echo(f"📦 {name} ({eco}) {version}")
        else:
            click.echo("  " * indent + f"{prefix}├─ {name} ({eco}) {version}")

        for dep in node.get('dependencies', []):
            print_tree(dep, indent + 1, "  ")

    print_tree(result)

    click.echo(f"\nDirect dependencies: {result.get('direct_dependencies', 0)}")


@cli.command()
@click.option('--project-id', type=int, help='Analyze specific project by ID')
@click.option('--resolve-transitive/--no-resolve-transitive', default=True,
              help='Resolve transitive dependencies')
@click.option('--scan-cves/--no-scan-cves', default=True,
              help='Scan for CVEs')
@click.option('--output', '-o', type=click.Path(), help='Output JSON report to file')
@click.option('--max-depth', default=2, help='Maximum depth for dependency resolution')
def impact(project_id, resolve_transitive, scan_cves, output, max_depth):
    """Analyze CVE impact for projects including transitive dependencies."""

    analyzer = ImpactAnalyzer(max_depth=max_depth)

    if project_id:
        # Analyze single project
        click.echo(f"Analyzing project ID {project_id}...")
        report = analyzer.analyze_project_full_impact(
            project_id,
            resolve_transitive=resolve_transitive,
            scan_cves=scan_cves
        )

        if 'error' in report:
            click.echo(f"✗ Error: {report['error']}")
            return

        click.echo("\n" + "="*60)
        click.echo(f"IMPACT ANALYSIS: {report['project_name']}")
        click.echo("="*60)

        summary = report['summary']
        click.echo(f"\nDependency Summary:")
        click.echo(f"  Direct dependencies: {summary['direct_dependencies']}")
        click.echo(f"  Total dependencies: {summary['total_dependencies']}")
        click.echo(f"  Transitive dependencies: {summary['transitive_dependencies']}")

        click.echo(f"\nVulnerability Summary:")
        click.echo(f"  Packages with CVEs: {summary['packages_with_cves']}")
        click.echo(f"  Total CVEs: {summary['total_cves']}")

        if summary['total_cves'] > 0:
            click.echo(f"\nSeverity Breakdown:")
            for severity, count in report['severity_breakdown'].items():
                click.echo(f"  {severity}: {count}")

            click.echo(f"\nHigh Risk Dependencies:")
            for dep in report['high_risk_dependencies'][:10]:
                click.echo(f"  {dep['dependency']}")
                click.echo(f"    CVE Count: {dep['cve_count']}")
                click.echo(f"    Max CVSS Score: {dep['max_cvss_score']}")
                click.echo(f"    CVEs: {', '.join(dep['cves'][:5])}")

        if output:
            with open(output, 'w') as f:
                json.dump(report, f, indent=2)
            click.echo(f"\n✓ Report saved to {output}")

    else:
        # Analyze all projects
        click.echo("Analyzing all projects...")
        click.echo("This will take a significant amount of time.\n")

        results = analyzer.analyze_all_projects(
            resolve_transitive=resolve_transitive,
            scan_cves=scan_cves
        )

        click.echo("\n" + "="*60)
        click.echo("OVERALL IMPACT ANALYSIS")
        click.echo("="*60)
        click.echo(f"Total projects: {results['total_projects']}")
        click.echo(f"Projects with CVEs: {results['projects_with_cves']}")
        click.echo(f"Total CVEs found: {results['total_cves_found']}")
        click.echo(f"Average CVEs per project: {results['average_cves_per_project']:.2f}")

        click.echo(f"\nTop 10 Most Vulnerable Projects:")
        for proj in results['projects'][:10]:
            if 'error' not in proj:
                click.echo(f"  {proj['project_name']}: {proj['cve_count']} CVEs "
                          f"({proj['high_risk_count']} high/critical)")

        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
            click.echo(f"\n✓ Results saved to {output}")


@cli.command()
@click.argument('cve_id')
def cve_impact(cve_id):
    """Find all projects affected by a specific CVE."""
    click.echo(f"Finding projects affected by {cve_id}...\n")

    analyzer = ImpactAnalyzer()
    result = analyzer.find_cve_downstream_impact(cve_id)

    if 'error' in result:
        click.echo(f"✗ {result['error']}")
        return

    click.echo("="*60)
    click.echo(f"CVE IMPACT ANALYSIS: {cve_id}")
    click.echo("="*60)

    click.echo(f"\nAffected Package: {result['package']} ({result['ecosystem']})")
    click.echo(f"Severity: {result['severity']}")
    if result['cvss_score']:
        click.echo(f"CVSS Score: {result['cvss_score']}")
    click.echo(f"Description: {result['description'][:200]}...")

    click.echo(f"\nAffected Projects: {result['affected_project_count']}")

    if result['affected_projects']:
        click.echo("\nProject Details:")
        for proj in result['affected_projects']:
            direct = "direct" if proj['is_direct_dependency'] else "transitive"
            click.echo(f"  • {proj['name']}")
            click.echo(f"    URL: {proj['url']}")
            click.echo(f"    Dependency Type: {direct}")
            click.echo(f"    Path: {proj['dependency_path']}")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'csv']), default='json',
              help='Export format')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path')
def export_vulnerabilities(format, output):
    """Export complete vulnerability report."""
    click.echo(f"Exporting vulnerability report to {output}...")

    analyzer = ImpactAnalyzer()
    analyzer.export_report(Path(output), format=format)

    click.echo(f"✓ Report exported successfully")


@cli.command()
@click.option('--github-token', envvar='GITHUB_TOKEN', help='GitHub API token (or set GITHUB_TOKEN env var)')
@click.option('--limit', type=int, help='Limit number of projects to scan')
@click.option('--force-refresh', is_flag=True, help='Force re-fetch SBOM files')
def scan_sbom(github_token, limit, force_refresh):
    """Scan projects using SBOM files (FAST method with exact versions)."""
    click.echo("="*60)
    click.echo("SBOM-BASED CVE SCANNER")
    click.echo("="*60)
    click.echo("This scanner fetches SBOM files (requirements.txt, lockfiles, etc.)")
    click.echo("directly from GitHub repositories for exact version matching.\n")

    if not github_token:
        click.echo("WARNING: No GitHub token provided. API rate limits will be restrictive.")
        click.echo("Set GITHUB_TOKEN environment variable or use --github-token option.\n")

    scanner = get_sbom_cve_scanner(github_token)

    click.echo(f"Starting SBOM scan (limit: {limit or 'all projects'})...\n")

    stats = scanner.scan_all_projects_sbom(limit=limit, force_refresh=force_refresh)

    click.echo("\n" + "="*60)
    click.echo("SBOM SCAN RESULTS")
    click.echo("="*60)
    click.echo(f"Projects scanned: {stats['projects_scanned']}/{stats['total_projects']}")
    click.echo(f"Scan time: {stats['elapsed_time_minutes']:.1f} minutes")
    click.echo(f"Average: {stats['elapsed_time_minutes']/stats['projects_scanned']:.2f} min/project\n")

    click.echo(f"Scan methodology:")
    click.echo(f"  SBOM files found: {stats['sbom_method']} projects ({stats['sbom_method']/stats['projects_scanned']*100:.1f}%)")
    click.echo(f"  Database fallback: {stats['fallback_method']} projects\n")

    click.echo(f"Vulnerability Results:")
    click.echo(f"  Projects with vulnerabilities: {stats['projects_with_cves']} ({stats['projects_with_cves']/stats['projects_scanned']*100:.1f}%)")
    click.echo(f"  Total CVEs found: {stats['total_cves']}")
    click.echo(f"  Unique vulnerable packages: {stats['unique_packages_with_cves']}\n")

    click.echo(f"Severity Breakdown:")
    for severity, count in stats['severity_breakdown'].items():
        if count > 0:
            click.echo(f"  {severity}: {count}")

    # Generate report
    output_dir = Path('sbom_scan_results')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'sbom_scan_report_{timestamp}.json'

    scanner.generate_sbom_report(stats, str(report_path))

    click.echo(f"\nFull report saved to {report_path}")

    # Show top at-risk projects
    click.echo(f"\nTop 10 At-Risk Projects:")
    for result in stats['scan_results'][:10]:
        if result['cve_count'] > 0:
            click.echo(f"  {result['project_name']}: {result['cve_count']} CVEs "
                      f"({result['dependency_count']} deps, method: {result['scan_method']})")


@cli.command()
@click.option('--github-token', envvar='GITHUB_TOKEN', help='GitHub API token')
@click.option('--limit', type=int, help='Limit number of projects')
@click.option('--force-refresh', is_flag=True, help='Force re-fetch SBOM files')
def scrape_sbom(github_token, limit, force_refresh):
    """Scrape SBOM files from all repositories (no CVE scanning)."""
    click.echo("="*60)
    click.echo("SBOM SCRAPER")
    click.echo("="*60)
    click.echo("Fetching SBOM files from GitHub repositories...\n")

    if not github_token:
        click.echo("WARNING: No GitHub token. Rate limits will be restrictive.\n")

    scraper = get_sbom_scraper(github_token)

    stats = scraper.scrape_all_sboms(limit=limit, force_refresh=force_refresh)

    click.echo("\n" + "="*60)
    click.echo("SBOM SCRAPING RESULTS")
    click.echo("="*60)
    click.echo(f"Total projects: {stats['total_projects']}")
    click.echo(f"Projects with SBOM: {stats['projects_with_sbom']}")
    click.echo(f"Projects without SBOM: {stats['projects_without_sbom']}")
    click.echo(f"Coverage: {stats['projects_with_sbom']/stats['total_projects']*100:.1f}%\n")

    click.echo(f"Total dependencies extracted: {stats['total_dependencies']}")
    click.echo(f"Unique packages: {stats['unique_packages']}\n")

    click.echo(f"By ecosystem:")
    for ecosystem, count in stats['by_ecosystem'].items():
        click.echo(f"  {ecosystem}: {count}")

    click.echo(f"\nSBOM data cached in database for fast CVE scanning")


@cli.command()
@click.option('--github-token', envvar='GITHUB_TOKEN', help='GitHub API token')
@click.option('--limit', type=int, help='Limit number of projects to scan')
@click.option('--force-refresh', is_flag=True, help='Force re-fetch all data')
@click.option('--output', '-o', help='Output JSON file path')
def scan_python(github_token, limit, force_refresh, output):
    """
    Multi-tier Python-only CVE scanner with comprehensive fallback.

    Tier 1: GitHub SBOM API (not yet activated - requires API key)
    Tier 2: Raw SBOM file scraping (lockfiles)
    Tier 3: Recursive dependency resolution (Oct 28 methodology)
    Tier 4: Database fallback (cached results)

    This command only scans Python/PyPI projects for focused analysis.
    """
    click.echo("="*60)
    click.echo("MULTI-TIER PYTHON CVE SCANNER")
    click.echo("="*60)
    click.echo("Scanning strategy:")
    click.echo("  1. GitHub SBOM API (not yet activated)")
    click.echo("  2. Raw SBOM files (requirements.txt, lockfiles)")
    click.echo("  3. Recursive dependency resolution")
    click.echo("  4. Database fallback\n")

    if not github_token:
        click.echo("WARNING: No GitHub token provided. Tier 2 (SBOM scraping) will be rate-limited.")
        click.echo("Set GITHUB_TOKEN environment variable or use --github-token option.\n")

    scanner = get_python_scanner(github_token)

    click.echo(f"Starting Python-only scan (limit: {limit or 'all'})...\n")

    results = scanner.scan_all_projects(limit=limit, force_refresh=force_refresh)

    # Save results
    if output:
        output_path = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("multi_tier_scan_results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"python_scan_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Display summary
    click.echo("\n" + "="*60)
    click.echo("PYTHON SCAN RESULTS")
    click.echo("="*60)
    click.echo(f"Scan mode: Python-only")
    click.echo(f"Projects scanned: {results['projects_scanned']}/{results['total_projects']}")
    click.echo(f"Projects with vulnerabilities: {results['projects_with_vulnerabilities']}")
    click.echo(f"Total CVEs found: {results['total_cves_found']}\n")

    click.echo("Tier usage statistics:")
    for tier, count in results['tier_statistics'].items():
        click.echo(f"  {tier}: {count} projects")

    click.echo(f"\nFull report saved to {output_path}")


@cli.command()
@click.option('--github-token', envvar='GITHUB_TOKEN', help='GitHub API token')
@click.option('--limit', type=int, help='Limit number of projects to scan')
@click.option('--force-refresh', is_flag=True, help='Force re-fetch all data')
@click.option('--output', '-o', help='Output JSON file path')
def scan_all_languages(github_token, limit, force_refresh, output):
    """
    Multi-tier multi-language CVE scanner with comprehensive fallback.

    Tier 1: GitHub SBOM API (not yet activated - requires API key)
    Tier 2: Raw SBOM file scraping (lockfiles for all languages)
    Tier 3: Recursive dependency resolution (Oct 28 methodology)
    Tier 4: Database fallback (cached results)

    Supports: Python, JavaScript, Rust, Go, Java, Ruby, and more.
    """
    click.echo("="*60)
    click.echo("MULTI-TIER MULTI-LANGUAGE CVE SCANNER")
    click.echo("="*60)
    click.echo("Scanning strategy:")
    click.echo("  1. GitHub SBOM API (not yet activated)")
    click.echo("  2. Raw SBOM files (all language lockfiles)")
    click.echo("  3. Recursive dependency resolution")
    click.echo("  4. Database fallback\n")
    click.echo("Supported ecosystems:")
    click.echo("  Python (PyPI), JavaScript (npm), Rust (crates),")
    click.echo("  Go (Go modules), Java (Maven), Ruby (RubyGems)\n")

    if not github_token:
        click.echo("WARNING: No GitHub token provided. Tier 2 (SBOM scraping) will be rate-limited.")
        click.echo("Set GITHUB_TOKEN environment variable or use --github-token option.\n")

    scanner = get_multi_language_scanner(github_token)

    click.echo(f"Starting multi-language scan (limit: {limit or 'all'})...\n")

    results = scanner.scan_all_projects(limit=limit, force_refresh=force_refresh)

    # Save results
    if output:
        output_path = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("multi_tier_scan_results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"multi_language_scan_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Display summary
    click.echo("\n" + "="*60)
    click.echo("MULTI-LANGUAGE SCAN RESULTS")
    click.echo("="*60)
    click.echo(f"Scan mode: All languages")
    click.echo(f"Projects scanned: {results['projects_scanned']}/{results['total_projects']}")
    click.echo(f"Projects with vulnerabilities: {results['projects_with_vulnerabilities']}")
    click.echo(f"Total CVEs found: {results['total_cves_found']}\n")

    click.echo("Tier usage statistics:")
    for tier, count in results['tier_statistics'].items():
        click.echo(f"  {tier}: {count} projects")

    click.echo(f"\nFull report saved to {output_path}")


if __name__ == '__main__':
    cli()

