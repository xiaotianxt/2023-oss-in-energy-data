# Energy Sector Dependency Analyzer

A comprehensive tool for extracting and analyzing dependencies from open-source projects in the energy sector. This tool processes the 1800+ energy-related projects from your research and provides insights into the dependency ecosystem.

## Features

- **Multi-language Support**: Parses dependencies from Python, JavaScript, Java, Rust, Go, R, and PHP projects
- **GitHub Integration**: Automatically fetches repository information and dependency files
- **Comprehensive Analysis**: Provides insights by category, language, and community type
- **SQLite Database**: Efficient local storage with full data export capabilities
- **CLI Interface**: Easy-to-use command-line interface for all operations

## Installation

1. **Clone or create the project directory**:
```bash
mkdir energy-dependency-analyzer
cd energy-dependency-analyzer
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Setup GitHub token** (required for API access):
```bash
python cli.py setup
# Enter your GitHub token when prompted
```

## Quick Start

1. **Extract dependencies from all projects**:
```bash
python cli.py extract
```

2. **Run comprehensive analysis**:
```bash
python cli.py analyze
```

3. **Export results**:
```bash
python cli.py export --format json --output energy_dependencies.json
python cli.py export --format csv --output analysis_results/
```

## Usage

### Basic Commands

- **Extract dependencies**: `python cli.py extract`
- **Show statistics**: `python cli.py stats`
- **Analyze ecosystem**: `python cli.py analyze`
- **Export data**: `python cli.py export`

### Analysis Commands

- **Most popular dependencies**: `python cli.py popular --limit 50`
- **Dependencies by category**: `python cli.py categories`
- **Dependencies by language**: `python cli.py languages`
- **Find project clusters**: `python cli.py clusters --min-shared 5`

### Advanced Options

```bash
# Extract with custom batch size
python cli.py extract --batch-size 25

# Show popular dependencies for specific ecosystem
python cli.py popular --ecosystem pypi --limit 30

# Find clusters with different threshold
python cli.py clusters --min-shared 3

# Export to specific location
python cli.py export --format csv --output /path/to/results/
```

## Data Sources

The analyzer processes projects from:
- `projects.yaml`: Main project catalog (1800+ projects)
- `matched.json`: Community classification data (academic vs commercial)

## Output Files

### Database
- `data/dependencies.db`: SQLite database with all extracted data

### Exports
- `energy_dependencies.json`: Complete dataset in JSON format
- `analysis_output/`: CSV files with detailed analysis
  - `popular_dependencies.csv`
  - `dependencies_by_category.csv`
  - `dependencies_by_language.csv`

## Architecture

### Core Components

1. **GitHub Client** (`github_client.py`): Handles GitHub API interactions
2. **Parsers** (`parsers.py`): Extracts dependencies from various file formats
3. **Database** (`database.py`): SQLite operations and data management
4. **Extractor** (`extractor.py`): Main extraction pipeline
5. **Analyzer** (`analyzer.py`): Analysis and reporting tools
6. **CLI** (`cli.py`): Command-line interface

### Supported Dependency Files

| Language | Files |
|----------|-------|
| Python | `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile`, `conda.yml` |
| JavaScript | `package.json`, `package-lock.json`, `yarn.lock` |
| Java | `pom.xml`, `build.gradle` |
| Rust | `Cargo.toml`, `Cargo.lock` |
| Go | `go.mod`, `go.sum` |
| R | `DESCRIPTION`, `renv.lock` |
| PHP | `composer.json`, `composer.lock` |

## Configuration

Edit `config.py` to customize:
- Rate limiting settings
- Batch processing parameters
- File paths
- Supported dependency files

## Rate Limiting

The tool respects GitHub API rate limits:
- Automatic rate limit checking
- Configurable delays between requests
- Batch processing to optimize API usage

## Analysis Capabilities

### Ecosystem Health Report
- Project coverage statistics
- Language and category distribution
- Dependency concentration analysis
- Top dependencies across all projects

### Category Analysis
- Dependencies by project category (Simulation, Modeling, etc.)
- Category-specific technology stacks
- Cross-category dependency patterns

### Language Analysis
- Language-specific dependency patterns
- Ecosystem distribution by language
- Popular libraries per language

### Community Analysis
- Academic vs commercial project patterns
- Community-specific technology choices
- Collaboration indicators

### Clustering Analysis
- Projects with shared dependencies
- Technology stack similarities
- Potential collaboration opportunities

## Example Output

```
ENERGY SECTOR OPEN SOURCE ECOSYSTEM ANALYSIS
============================================================

OVERVIEW:
  Total projects: 1847
  Projects with dependencies: 1203
  Coverage: 65.1%

TOP PROGRAMMING LANGUAGES:
  python: 978 projects
  javascript: 234 projects
  java: 156 projects
  r: 89 projects
  rust: 67 projects

TOP 15 MOST USED DEPENDENCIES:
  numpy: 456 projects
  pandas: 398 projects
  matplotlib: 287 projects
  scipy: 234 projects
  requests: 198 projects
```

## Troubleshooting

### Common Issues

1. **GitHub API Rate Limit**: Wait for rate limit reset or use multiple tokens
2. **Missing Dependencies**: Install with `pip install -r requirements.txt`
3. **Database Locked**: Ensure no other processes are using the database

### Debug Mode

Run with verbose logging:
```bash
python cli.py --verbose extract
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Research Applications

This tool enables research into:
- Open source ecosystem health in energy sector
- Technology adoption patterns
- Academic vs industry collaboration
- Supply chain risk analysis
- Innovation diffusion patterns

## Citation

If you use this tool in your research, please cite:
```
Energy Sector Dependency Analyzer
https://github.com/your-repo/energy-dependency-analyzer
```

