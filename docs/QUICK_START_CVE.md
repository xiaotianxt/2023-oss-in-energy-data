# Quick Start: CVE Scanning and Impact Analysis

## What's New

Your dependency analyzer now has powerful CVE detection capabilities:

✅ **Recursive dependency resolution** - Find dependencies of dependencies
✅ **Dynamic programming optimization** - Shared dependencies resolved only once
✅ **CVE scanning** - Detect known vulnerabilities using OSV database
✅ **Impact analysis** - Know which projects are affected by any CVE
✅ **Reverse lookup** - Find all downstream packages impacted by a vulnerability
✅ **Three-level caching** - In-memory, database, and API caching for maximum speed

## Quick Commands

### 1. Scan All Dependencies for CVEs

```bash
cd dependency_analyzer
python cli.py scan-cves
```

This will:
- Scan all 3,524 dependencies in your database
- Query the OSV (Open Source Vulnerabilities) database
- Store results in the database
- Show summary of vulnerabilities found

**Output example:**
```
CVE SCAN RESULTS
============================================================
Total packages scanned: 1,234
Packages with CVEs: 45
Total CVEs found: 127

Severity Distribution:
  CRITICAL: 5
  HIGH: 23
  MEDIUM: 67
  LOW: 32

Top 10 Most Vulnerable Packages:
  django (pypi): 8 CVEs
  axios (npm): 6 CVEs
  ...
```

### 2. Analyze Impact on a Specific Project

```bash
# Find project ID first
python cli.py stats

# Then analyze that project
python cli.py impact --project-id 1
```

This will:
- Get all direct dependencies for the project
- Resolve transitive (indirect) dependencies
- Scan all dependencies for CVEs
- Show which vulnerabilities affect this project

**Output example:**
```
IMPACT ANALYSIS: Project Name
============================================================
Dependency Summary:
  Direct dependencies: 15
  Total dependencies: 67
  Transitive dependencies: 52

Vulnerability Summary:
  Packages with CVEs: 3
  Total CVEs: 7

Severity Breakdown:
  HIGH: 2
  MEDIUM: 5

High Risk Dependencies:
  django (pypi)
    CVE Count: 3
    Max CVSS Score: 8.5
    CVEs: CVE-2023-1234, CVE-2023-5678
```

### 3. Find Projects Affected by a Specific CVE

```bash
python cli.py cve-impact CVE-2023-45853
```

This will show:
- Which package has the vulnerability
- All projects in your database using that package
- Whether it's a direct or transitive dependency
- The dependency path

### 4. Explore Dependency Tree for a Package

```bash
python cli.py resolve requests pypi
```

Shows the complete dependency tree:
```
📦 requests (pypi)
  ├─ urllib3 (pypi) >=1.21.1
    ├─ certifi (pypi)
    └─ idna (pypi)
  ├─ charset-normalizer (pypi)
  └─ certifi (pypi)
    ↻ certifi (already visited)
```

### 5. Export Vulnerability Report

```bash
# As JSON
python cli.py export-vulnerabilities -o vulnerabilities.json --format json

# As CSV (for Excel)
python cli.py export-vulnerabilities -o vulnerabilities.csv --format csv
```

## Common Workflows

### Security Audit of All Projects

```bash
# 1. Scan for CVEs (takes ~1-2 hours for first run, then cached)
python cli.py scan-cves

# 2. Generate impact analysis for all projects
python cli.py impact -o full_security_report.json

# 3. Export to CSV for sharing
python cli.py export-vulnerabilities -o vulnerabilities.csv --format csv
```

### Investigate a Specific Project

```bash
# Detailed analysis with dependency tree
python cli.py impact --project-id 42 --max-depth 3 -o project_42.json

# Open project_42.json to see:
# - All dependencies (direct and transitive)
# - All CVEs affecting the project
# - Dependency paths showing how vulnerabilities are introduced
# - Severity breakdown
```

### Check if Your Database Needs Cleaning

```bash
# Get stats
python cli.py stats

# View CVE summary
python cli.py scan-cves

# If you see outdated or incorrect data, you can:
# 1. Re-scan with fresh data
python cli.py scan-cves --force-refresh

# 2. Or start fresh by deleting and rebuilding
rm dependencies.db
python cli.py extract
python cli.py scan-cves
```

## Understanding the Output

### Severity Levels

- **CRITICAL** - Immediate action required. Likely exploitable.
- **HIGH** - Should be addressed soon. Significant risk.
- **MEDIUM** - Plan to address. Moderate risk.
- **LOW** - Good to fix. Minor risk.
- **UNKNOWN** - Severity not yet assessed.

### Dependency Types

- **Direct** - Your project explicitly lists this dependency
- **Transitive** - A dependency of one of your dependencies
- **Depth** - How many levels deep (1 = direct, 2 = dependency of dependency, etc.)

### Dependency Paths

Shows how a vulnerability reaches your project:

- `urllib3` - Direct dependency
- `requests → urllib3` - Transitive via requests
- `app → requests → urllib3` - Two levels deep

## Database Tables

New tables created in `dependencies.db`:

1. **`package_cves`** - CVE information for each package
2. **`transitive_dependencies`** - Recursive dependency relationships
3. **`project_cve_impact`** - Links projects to affecting CVEs

You can query these directly:

```bash
# Using Python
python -c "import sqlite3; conn = sqlite3.connect('dependencies.db'); \
  cursor = conn.cursor(); \
  cursor.execute('SELECT COUNT(*) FROM package_cves'); \
  print('Total CVEs:', cursor.fetchone()[0])"
```

## Performance Tips

### First Run is Slow
- First CVE scan: ~1-2 hours (queries OSV API for each package)
- Subsequent scans: Much faster (uses 24-hour cache)

### Speed Up Scans
```bash
# Reduce dependency depth for faster analysis
python cli.py impact --project-id 1 --max-depth 1

# Skip transitive dependency resolution
python cli.py impact --project-id 1 --no-resolve-transitive

# Skip CVE scanning (just resolve dependencies)
python cli.py impact --project-id 1 --no-scan-cves
```

### Only Scan New Packages
The scanner automatically caches CVE data for 24 hours. If you add new projects:

```bash
# Extract new project dependencies
python cli.py extract --resume

# Scan only new packages (old ones use cache)
python cli.py scan-cves
```

## Troubleshooting

### "No module named 'requests'"
```bash
pip install requests
```

### "OSV API timeout"
Network issue or rate limiting. Try again:
```bash
python cli.py scan-cves --force-refresh
```

### "Database is locked"
Only one process can write to SQLite at a time:
```bash
# Make sure no other cli.py commands are running
# Check with: ps aux | grep cli.py (Linux/Mac)
# Or Task Manager (Windows)
```

### "Too many API requests"
```python
# Edit dependency_resolver.py and add delays:
import time
time.sleep(1)  # Add 1 second delay between requests
```

## Next Steps

1. **Run your first scan:**
   ```bash
   python cli.py scan-cves
   ```

2. **Pick a project to analyze:**
   ```bash
   python cli.py impact --project-id 1 -o report.json
   ```

3. **Review the report:**
   - Open `report.json`
   - Look at `vulnerabilities` section
   - Check `high_risk_dependencies`

4. **Take action:**
   - Update vulnerable packages
   - Consider alternatives
   - Document accepted risks

## Need Help?

- Check `README_CVE_FEATURES.md` for detailed documentation
- Review the CLI help: `python cli.py --help`
- Check individual command help: `python cli.py scan-cves --help`

## Example: Real-World Usage

```bash
# Morning security check
cd dependency_analyzer

# Quick scan (uses cache from yesterday)
python cli.py scan-cves

# Check for new critical/high severity issues
python cli.py impact | grep -E "CRITICAL|HIGH"

# If issues found, investigate specific projects
python cli.py impact --project-id 42 -o project_42_analysis.json

# Share results with team
python cli.py export-vulnerabilities -o security_report.csv --format csv
```

Good luck with your security analysis!
