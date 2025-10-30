# Open Source Software in Energy - Security Analysis

A comprehensive tool for analyzing dependencies and security vulnerabilities in open-source energy sector software projects.

## 🎯 Project Overview

This project provides automated analysis of **357 open-source energy sector projects**, including:
- **Dependency analysis** across multiple ecosystems (Python, Rust, Go, JavaScript, Ruby, Java)
- **CVE (Common Vulnerabilities and Exposures) detection** using OSV database
- **SBOM (Software Bill of Materials) scraping** from GitHub repositories
- **Security scoring** using OpenSSF Scorecard and Criticality Score
- **Impact analysis** to identify which projects are affected by specific vulnerabilities

### Key Statistics
- **357 projects** analyzed
- **2,576 CVEs** discovered
- **144 projects** (40.3%) have known vulnerabilities
- **87% SBOM coverage** for direct vulnerability scanning

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.8+ required
pip install -r dependency_analyzer/requirements.txt
```

### Option 1: Fast SBOM-Based Scan (Recommended)
```bash
cd dependency_analyzer

# Quick test (10 projects, ~2-5 minutes)
python cli.py scan-sbom --limit 10

# Full scan (357 projects, ~30-60 minutes)
# Recommended: Set GitHub token first for better rate limits
export GITHUB_TOKEN="ghp_your_token_here"
python cli.py scan-sbom
```

### Option 2: Comprehensive Deep Scan
```bash
cd dependency_analyzer

# Full 4-step analysis (~4 hours)
python run_full_analysis.py
```

## 📁 Project Structure

```
2023-oss-in-energy-data/
├── dependency_analyzer/          # Main analysis package
│   ├── cli.py                   # Command-line interface
│   ├── sbom_scraper.py          # SBOM file scraper (NEW)
│   ├── sbom_cve_scanner.py      # SBOM-based CVE scanner (NEW)
│   ├── cve_scanner.py           # CVE detection using OSV API
│   ├── dependency_resolver.py   # Dependency resolution with DP optimization
│   ├── impact_analyzer.py       # Impact analysis engine
│   ├── run_full_analysis.py     # Comprehensive 4-step scanner
│   ├── analyzer.py              # Dependency pattern analysis
│   ├── database.py              # SQLite database manager
│   ├── extractor.py             # Dependency extractor
│   ├── config.py                # Configuration
│   ├── requirements.txt         # Python dependencies
│   └── data/
│       └── dependencies.db      # SQLite database (357 projects, 3,524 dependencies)
│
├── docs/                        # Documentation
│   ├── SBOM_QUICKSTART.md      # Quick start for SBOM scanner
│   ├── SBOM_IMPLEMENTATION_SUMMARY.md  # Technical details of SBOM approach
│   ├── COMPLETE_GUIDE.md       # Complete user guide
│   ├── HOW_TO_RUN_FULL_SCAN.md # Step-by-step full scan guide
│   ├── DP_VISUAL_COMPARISON.md # Dynamic programming explanation
│   ├── OPTIMIZATION_SUMMARY.md  # Performance optimizations
│   └── ...                     # Additional documentation
│
├── results/                     # Analysis results
│   └── archived_scans/         # Historical scan data
│       ├── CVE_ANALYSIS_REPORT.json
│       ├── cve_scan_results.json
│       ├── projects.csv
│       ├── scorecard_results.txt
│       └── ...
│
├── scripts/                     # Utility scripts
│   └── legacy/                 # Legacy analysis scripts
│       ├── batch_criticality_score.py
│       ├── batch_scorecard.py
│       ├── analyze_final_results.py
│       └── ...
│
├── data/                        # Core data files
│   ├── dependencies.db         # Main dependency database
│   └── projects.yaml           # Project metadata
│
└── notebooks/                   # Jupyter notebooks
    └── analyze.ipynb           # Exploratory analysis
```

## 🔧 Features

### 1. SBOM-Based CVE Scanner (NEW - Recommended)
**10x faster** than traditional methods by fetching lockfiles directly from GitHub.

**Key Advantages:**
- ✅ **Fast**: 30-60 minutes for 357 projects (vs 4 hours traditional)
- ✅ **Exact versions**: Uses pinned versions from lockfiles
- ✅ **Multi-ecosystem**: Python, Rust, Go, npm, Ruby, Java
- ✅ **Smart caching**: 24-hour persistent cache with DP optimization
- ✅ **Hybrid fallback**: Falls back to database if no SBOM found

**Supported SBOM Formats:**
- Python: `requirements.txt`, `Pipfile.lock`, `poetry.lock`
- JavaScript: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- Rust: `Cargo.lock`
- Go: `go.sum`, `go.mod`
- Ruby: `Gemfile.lock`

**Usage:**
```bash
cd dependency_analyzer
export GITHUB_TOKEN="ghp_your_token"
python cli.py scan-sbom
```

**Output:** JSON report with CVE details, severity breakdown, and methodology stats

### 2. Traditional CVE Scanner
Comprehensive 4-step analysis with transitive dependency resolution.

**Features:**
- Deep transitive dependency resolution
- Checkpointed progress (resumable)
- Comprehensive impact analysis
- Multi-format exports (JSON, CSV)

**Usage:**
```bash
cd dependency_analyzer
python run_full_analysis.py
```

### 3. Dynamic Programming Optimization
All scanners use **dynamic programming** to avoid repeated computation:

**Three-Level Caching:**
1. **In-memory cache**: O(1) lookup during session
2. **Database cache**: 24-hour persistent storage
3. **Content-hash cache**: Identical files parsed once

**Result:** Each unique package queried **exactly once** from APIs.

### 4. Security Scoring
Integration with industry-standard security metrics:
- **OpenSSF Scorecard**: 10+ automated security checks
- **Criticality Score**: Importance metrics for OSS projects
- Historical data available in `results/archived_scans/`

## 📊 Available Commands

### SBOM Scanner
```bash
# Scan with SBOM files (fast)
python cli.py scan-sbom [--limit N] [--github-token TOKEN] [--force-refresh]

# Just scrape SBOM files (no CVE scanning)
python cli.py scrape-sbom [--limit N]
```

### Traditional Scanner
```bash
# Scan all dependencies for CVEs
python cli.py scan-cves [--force-refresh]

# Resolve transitive dependencies
python cli.py resolve PACKAGE [--ecosystem pypi] [--max-depth 5]

# Analyze project impact
python cli.py impact PROJECT_ID [--resolve-transitive] [--scan-cves]

# Reverse CVE lookup
python cli.py cve-impact CVE_ID

# Export reports
python cli.py export-vulnerabilities --format json --output report.json
```

### Analysis Commands
```bash
# View statistics
python cli.py stats

# Export data
python cli.py export --format csv --output results.csv

# Analyze patterns
python cli.py analyze
```

## 🔑 GitHub Token Setup

**Why you need it:**
- Without token: 60 requests/hour (very slow)
- With token: 5,000 requests/hour (recommended)

**How to get one:**
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select `public_repo` scope
4. Copy token (starts with `ghp_`)

**Set token:**
```bash
# Option 1: Environment variable
export GITHUB_TOKEN="ghp_your_token_here"

# Option 2: .env file
echo "GITHUB_TOKEN=ghp_your_token_here" > .env

# Option 3: Command line
python cli.py scan-sbom --github-token ghp_your_token_here
```

## 📈 Performance Comparison

| Method | Time (357 projects) | Version Accuracy | Cache Persistence | Ecosystems |
|--------|---------------------|------------------|-------------------|------------|
| **SBOM Scanner** | 30-60 min | 100% (exact) | 24 hours | 7+ |
| **Traditional Scanner** | ~4 hours | Partial | Per-run | PyPI only |

**Recommendation:** Use SBOM scanner for speed and accuracy. Use traditional scanner for comprehensive transitive analysis.

## 🗃️ Database Schema

### Core Tables
- `projects`: 357 energy sector projects
- `dependencies`: 3,524 direct dependencies
- `sbom_files`: Cached SBOM files (24-hour expiration)
- `sbom_dependencies`: Parsed dependencies from SBOMs
- `package_cves`: CVE data per package
- `transitive_dependencies`: Resolved dependency trees
- `project_cve_impact`: CVE impact per project

## 📚 Documentation

- **[SBOM_QUICKSTART.md](docs/SBOM_QUICKSTART.md)**: Quick start for SBOM scanner
- **[SBOM_IMPLEMENTATION_SUMMARY.md](docs/SBOM_IMPLEMENTATION_SUMMARY.md)**: Technical implementation details
- **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)**: Comprehensive user guide
- **[HOW_TO_RUN_FULL_SCAN.md](docs/HOW_TO_RUN_FULL_SCAN.md)**: Step-by-step full scan guide
- **[DP_VISUAL_COMPARISON.md](docs/DP_VISUAL_COMPARISON.md)**: Dynamic programming optimization explained

## 🎯 Use Cases

### Security Researchers
```bash
# Find all projects affected by specific CVE
cd dependency_analyzer
python cli.py cve-impact CVE-2024-12345

# Scan for new vulnerabilities
python cli.py scan-sbom --force-refresh
```

### Project Maintainers
```bash
# Check your project's vulnerabilities
cd dependency_analyzer
python cli.py impact YOUR_PROJECT_ID --scan-cves

# Export report for security review
python cli.py export-vulnerabilities --format csv --output security_report.csv
```

### Data Analysts
```bash
# Analyze dependency patterns
cd dependency_analyzer
python cli.py analyze

# Export data for visualization
python cli.py export --format csv --output dependencies.csv
```

## 🐛 Troubleshooting

**"Rate limit exceeded"**
→ Set GITHUB_TOKEN environment variable

**"No module named 'github'"**
→ Run: `pip install -r dependency_analyzer/requirements.txt`

**"No SBOM found for project X"**
→ Expected behavior - scanner falls back to database automatically

**"Ecosystem X not supported by OSV API"**
→ Logged as warning, scan continues for other packages

## 🤝 Contributing

This project analyzes open-source energy sector software. To add new projects:

1. Add repository to `data/projects.yaml`
2. Run: `python cli.py extract`
3. Scan for CVEs: `python cli.py scan-sbom`

## 📄 License

This analysis tool is provided for research and security purposes. Refer to individual project licenses for the analyzed software.

## 🔗 Related Resources

- **OSV Database**: https://osv.dev/
- **OpenSSF Scorecard**: https://github.com/ossf/scorecard
- **GitHub Security**: https://github.com/security

## 📧 Contact

For questions or contributions, please open an issue on GitHub.

---

**Last Updated**: October 2025

**Key Finding**: 40.3% of energy sector OSS projects have known vulnerabilities. Regular security scanning is critical for this infrastructure.
