# CVE Scanning and Recursive Dependency Analysis

This document describes the new features added to the dependency analyzer for CVE detection and recursive dependency resolution.

## Overview

The dependency analyzer has been enhanced with three major new capabilities:

1. **CVE Scanning** - Detect known vulnerabilities in packages using the OSV (Open Source Vulnerabilities) database
2. **Recursive Dependency Resolution** - Explore transitive dependencies (dependencies of dependencies)
3. **Impact Analysis** - Understand which projects are affected by CVEs in their dependency chain

## New Modules

### 1. `cve_scanner.py` - CVE Detection

Scans packages for known vulnerabilities using the OSV API, which aggregates CVE data from multiple sources.

**Key Features:**
- Scans PyPI, npm, Maven, Go, and Rust packages
- Caches CVE data to reduce API calls
- Stores results in new database tables:
  - `package_cves` - CVE information for each package
  - `project_cve_impact` - Links CVEs to affected projects

**Usage:**
```python
from cve_scanner import CVEScanner

scanner = CVEScanner()

# Scan a single package
cves = scanner.scan_package('requests', 'pypi')

# Scan all dependencies in database
results = scanner.scan_all_dependencies()

# Get CVE summary
summary = scanner.get_cve_summary()
```

**CLI Commands:**
```bash
# Scan all dependencies for CVEs
python cli.py scan-cves

# Force refresh cached data
python cli.py scan-cves --force-refresh
```

### 2. `dependency_resolver.py` - Recursive Dependencies

Resolves transitive dependencies by querying package registries (PyPI, npm, etc.) to build a complete dependency tree.

**Key Features:**
- Recursively resolves dependencies up to a configurable depth
- Supports PyPI and npm (Maven and Go stubs included)
- Stores transitive relationships in `transitive_dependencies` table
- Performs reverse lookups to find packages affected by a dependency

**Usage:**
```python
from dependency_resolver import DependencyResolver

resolver = DependencyResolver(max_depth=3)

# Resolve dependencies recursively
dep_tree = resolver.resolve_recursive('requests', 'pypi')

# Get all transitive dependencies for a package
all_deps = resolver.get_all_transitive_dependencies('requests', 'pypi')

# Find packages that depend on a specific package (reverse lookup)
affected = resolver.find_packages_affected_by_dependency('urllib3', 'pypi')
```

**CLI Commands:**
```bash
# Resolve dependencies for a specific package
python cli.py resolve requests pypi

# With custom depth
python cli.py resolve express npm --max-depth 5
```

### 3. `impact_analyzer.py` - Combined Impact Analysis

Combines CVE scanning with dependency resolution to provide comprehensive vulnerability impact analysis.

**Key Features:**
- Analyzes both direct and transitive dependencies
- Identifies dependency paths for vulnerabilities
- Calculates severity breakdowns
- Identifies high-risk dependencies
- Performs reverse CVE impact analysis (find all projects affected by a CVE)

**Usage:**
```python
from impact_analyzer import ImpactAnalyzer

analyzer = ImpactAnalyzer(max_depth=2)

# Analyze a specific project
report = analyzer.analyze_project_full_impact(
    project_id=1,
    resolve_transitive=True,
    scan_cves=True
)

# Analyze all projects
results = analyzer.analyze_all_projects()

# Find projects affected by a specific CVE
impact = analyzer.find_cve_downstream_impact('CVE-2023-1234')

# Export vulnerability report
analyzer.export_report(Path('vulnerabilities.json'), format='json')
```

**CLI Commands:**
```bash
# Analyze a specific project
python cli.py impact --project-id 1

# Analyze with custom options
python cli.py impact --project-id 1 --max-depth 3 --output report.json

# Analyze all projects
python cli.py impact

# Find projects affected by a specific CVE
python cli.py cve-impact CVE-2023-1234

# Export all vulnerabilities
python cli.py export-vulnerabilities --output vulnerabilities.csv --format csv
```

## Database Schema Changes

New tables added to `dependencies.db`:

### `package_cves`
Stores CVE information for packages:
- `package_name` - Name of the package
- `ecosystem` - Package ecosystem (pypi, npm, etc.)
- `cve_id` - CVE or OSV identifier
- `severity` - Severity level (LOW, MEDIUM, HIGH, CRITICAL)
- `cvss_score` - CVSS score if available
- `description` - Vulnerability description
- `published_date` - When the CVE was published
- `affected_versions` - JSON array of affected versions
- `patched_versions` - JSON array of patched versions
- `references` - JSON array of reference URLs
- `checked_at` - When this was last checked

### `transitive_dependencies`
Stores recursive dependency relationships:
- `package_name` - Root package name
- `ecosystem` - Root package ecosystem
- `version_spec` - Version specifier
- `depends_on_package` - Name of dependency
- `depends_on_ecosystem` - Ecosystem of dependency
- `depends_on_version` - Version of dependency
- `dependency_depth` - How deep in the tree (1 = direct)
- `resolved_at` - When this was resolved

### `project_cve_impact`
Links projects to CVEs affecting them:
- `project_id` - Project ID
- `cve_id` - CVE identifier
- `affected_package` - Package with the vulnerability
- `ecosystem` - Package ecosystem
- `is_direct_dependency` - Whether this is a direct dependency
- `dependency_path` - Path from project to vulnerable package
- `severity` - CVE severity
- `cvss_score` - CVSS score
- `detected_at` - When this was detected

## Workflow Examples

### Example 1: Complete Security Audit

```bash
# 1. Scan all dependencies for CVEs
python cli.py scan-cves

# 2. Analyze impact on all projects
python cli.py impact --output security_audit.json

# 3. Export detailed vulnerability report
python cli.py export-vulnerabilities --output vulnerabilities.csv --format csv
```

### Example 2: Investigate a Specific Project

```bash
# 1. Find the project ID
python cli.py stats

# 2. Analyze the project with transitive dependencies
python cli.py impact --project-id 42 --max-depth 3 --output project_42_report.json

# 3. Review the JSON report for vulnerability details
```

### Example 3: Investigate a Specific CVE

```bash
# 1. Find all projects affected by a CVE
python cli.py cve-impact CVE-2023-45853

# This will show:
# - Which package has the vulnerability
# - All projects using that package
# - Whether it's a direct or transitive dependency
# - The dependency path
```

### Example 4: Explore Dependency Tree

```bash
# Resolve and visualize dependency tree for a package
python cli.py resolve requests pypi --max-depth 3

# Output will show:
# 📦 requests (pypi) >=2.0.0
#   ├─ urllib3 (pypi) ^1.26.0
#     ├─ certifi (pypi) >=2020.0.0
#     └─ idna (pypi) >=2.5
#   ├─ charset-normalizer (pypi) ~2.0.0
#   └─ certifi (pypi) >=2017.4.17
#     ↻ certifi (already visited)
```

## API Integration

### OSV (Open Source Vulnerabilities) API

The CVE scanner uses the OSV API which provides:
- Unified vulnerability database across ecosystems
- Free, no API key required
- High-quality data from multiple sources (CVE, GitHub Security Advisories, etc.)
- API documentation: https://osv.dev/

**Rate Limiting:**
- The OSV API has generous rate limits
- Results are cached for 24 hours by default
- Use `--force-refresh` to bypass cache

### Package Registry APIs

The dependency resolver uses official package registries:

**PyPI (Python):**
- API: `https://pypi.org/pypi/{package}/json`
- Returns package metadata including dependencies

**npm (JavaScript):**
- API: `https://registry.npmjs.org/{package}`
- Returns all versions and their dependencies

## Performance Considerations

### Scanning Speed
- CVE scanning: ~1-2 seconds per unique package (with caching)
- For 3,524 dependencies, expect ~1-2 hours for first scan
- Subsequent scans use cache and are much faster

### Dependency Resolution
- Network-intensive operation
- PyPI/npm APIs are generally fast (<1 second per package)
- Recursive resolution with depth=3 can generate many API calls
- Consider using `max_depth=2` for large projects

### Optimizations
- CVE data is cached for 24 hours
- Transitive dependencies are stored in database
- Only unique packages are scanned/resolved
- Concurrent processing where possible

## Troubleshooting

### Issue: Rate limiting from package registries

**Solution:** Add delays or reduce `max_depth`:
```python
import time
resolver = DependencyResolver(max_depth=2)
time.sleep(0.5)  # Add delay between requests
```

### Issue: OSV API timeout

**Solution:** The scanner has built-in retry logic and timeout handling. If persistent:
```bash
python cli.py scan-cves --force-refresh
```

### Issue: Database locked errors

**Solution:** Ensure only one process is accessing the database at a time. SQLite doesn't handle concurrent writes well.

## Future Enhancements

Potential improvements:
1. **Parallel scanning** - Use threading/multiprocessing for faster CVE scans
2. **Maven/Go support** - Complete implementation for these ecosystems
3. **Version compatibility checking** - Determine if installed version is actually vulnerable
4. **Automated remediation suggestions** - Suggest version upgrades to fix CVEs
5. **Continuous monitoring** - Schedule regular scans and alert on new CVEs
6. **Integration with CI/CD** - Fail builds if high-severity CVEs found
7. **SBOM generation** - Export Software Bill of Materials in standard formats

## Contributing

When adding new features:
1. Add appropriate database indexes for query performance
2. Include error handling and logging
3. Add CLI commands with clear help text
4. Update this README with examples
5. Consider rate limiting and caching for external APIs

## References

- [OSV Database](https://osv.dev/)
- [PyPI JSON API](https://warehouse.pypa.io/api-reference/json.html)
- [npm Registry API](https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md)
- [CVSS Scoring](https://www.first.org/cvss/)
- [Common Weakness Enumeration](https://cwe.mitre.org/)
