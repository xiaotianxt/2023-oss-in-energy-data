# Batch Scorecard Calculator

This script calculates OpenSSF Scorecard scores for multiple repositories in parallel using multiple GitHub tokens.

## Prerequisites

1. **Install Scorecard**: You mentioned you already installed it via Homebrew:
   ```bash
   brew install scorecard
   ```

2. **Verify Installation**:
   ```bash
   scorecard --version
   ```

## Setup

1. **GitHub Tokens**: Create a `tokens.env` file with your GitHub tokens:
   ```
   GITHUB_AUTH_TOKEN=ghp_your_token_here
   # or multiple tokens for higher rate limits
   GITHUB_AUTH_TOKEN=token1,token2,token3
   ```

2. **Repository List**: Use your existing `projects.csv` file or create a new one with columns:
   - `Category`: Project category
   - `Project`: Project name  
   - `Repository URL`: GitHub repository URL

## Usage

### Basic Usage
```bash
python3 batch_scorecard.py
```

### Advanced Usage
```bash
python3 batch_scorecard.py [csv_file] [max_workers] [timeout_seconds]
```

**Parameters:**
- `csv_file`: CSV file with repositories (default: `projects.csv`)
- `max_workers`: Number of parallel workers (default: 4)
- `timeout_seconds`: Timeout per repository in seconds (default: 300)

### Examples
```bash
# Use default settings
python3 batch_scorecard.py

# Custom CSV file with 8 workers
python3 batch_scorecard.py my_repos.csv 8

# Custom settings with 2-minute timeout
python3 batch_scorecard.py projects.csv 6 120
```

## Output

The script generates:

1. **Console Output**: Real-time progress and summary statistics
2. **scorecard_results.txt**: Detailed results for each repository

### Sample Output Format
```
================================================================================
Repository: https://github.com/pybamm-team/PyBaMM
Project: PyBaMM
Category: Batteries
Status: SUCCESS
--------------------------------------------------------------------------------
repo.name: github.com/pybamm-team/PyBaMM
repo.commit: abc123...
aggregate_score: 7.2
total_checks: 16
check.Binary-Artifacts.score: 10
check.Binary-Artifacts.reason: no binaries found in the repo
check.Branch-Protection.score: 8
check.Branch-Protection.reason: branch protection is not maximal
...
```

## Features

### 🚀 **Performance**
- **Parallel Processing**: Multiple repositories processed simultaneously
- **Token Rotation**: Distributes requests across multiple GitHub tokens
- **Configurable Workers**: Adjust parallelism based on your system

### 🛡️ **Reliability**
- **Graceful Shutdown**: Handles Ctrl+C interrupts and saves partial results
- **Error Handling**: Continues processing even if individual repositories fail
- **Timeout Protection**: Prevents hanging on problematic repositories

### 📊 **Comprehensive Results**
- **Aggregate Scores**: Overall security score (0-10)
- **Individual Check Scores**: Detailed breakdown of all security checks
- **Status Tracking**: SUCCESS, ERROR, TIMEOUT, etc.
- **Summary Statistics**: Success rates, score distributions, top/bottom performers

## Scorecard Checks

The script captures all standard Scorecard checks:

| Check | Description | Risk Level |
|-------|-------------|------------|
| Binary-Artifacts | Free of checked-in binaries | High |
| Branch-Protection | Uses branch protection | High |
| CI-Tests | Runs tests in CI | Low |
| CII-Best-Practices | Has OpenSSF Best Practices badge | Low |
| Code-Review | Practices code review | High |
| Contributors | Contributors from multiple orgs | Low |
| Dangerous-Workflow | Avoids dangerous workflows | Critical |
| Dependency-Update-Tool | Uses dependency update tools | High |
| Fuzzing | Uses fuzzing tools | Medium |
| License | Declares a license | Low |
| Maintained | Recently maintained | High |
| Packaging | Publishes packages from CI/CD | Medium |
| Pinned-Dependencies | Pins dependencies | Medium |
| SAST | Uses static analysis | Medium |
| Security-Policy | Has security policy | Medium |
| Signed-Releases | Signs releases | High |
| Token-Permissions | Uses read-only tokens | High |
| Vulnerabilities | No unfixed vulnerabilities | High |

## Troubleshooting

### Common Issues

1. **"scorecard command not found"**
   ```bash
   brew install scorecard
   # or
   go install github.com/ossf/scorecard/v2/cmd/scorecard@latest
   ```

2. **Rate Limit Errors**
   - Add more GitHub tokens to `tokens.env`
   - Reduce `max_workers` parameter
   - Increase timeout for slower repositories

3. **Permission Errors**
   - Ensure GitHub tokens have appropriate permissions
   - Use Personal Access Tokens with `public_repo` scope

4. **Memory Issues**
   - Reduce `max_workers` parameter
   - Process repositories in smaller batches

### Performance Tips

1. **Optimal Worker Count**: Start with 4-6 workers, adjust based on your system
2. **Token Strategy**: Use multiple tokens for higher rate limits
3. **Timeout Settings**: 300 seconds works for most repos, increase for large projects
4. **Batch Processing**: For very large datasets, process in smaller chunks

## Integration with Analysis

After running the batch scorecard, you can analyze the results similar to your criticality score analysis:

```python
# Load and analyze scorecard results
import pandas as pd
import re

def extract_scorecard_data(filename):
    repos = []
    scores = []
    
    with open(filename, 'r') as f:
        content = f.read()
    
    sections = content.split('=' * 80)
    
    for section in sections:
        if 'Repository:' in section and 'aggregate_score:' in section:
            repo_match = re.search(r'Repository: (https://github\.com/[^\n]+)', section)
            score_match = re.search(r'aggregate_score: ([\d.]+)', section)
            
            if repo_match and score_match:
                repos.append(repo_match.group(1))
                scores.append(float(score_match.group(1)))
    
    return repos, scores

# Create DataFrame and analyze
repos, scores = extract_scorecard_data('scorecard_results.txt')
df = pd.DataFrame({'repository': repos, 'scorecard_score': scores})
```

## Comparison with Criticality Score

| Metric | Criticality Score | Scorecard |
|--------|------------------|-----------|
| **Purpose** | Measures project importance/influence | Measures security practices |
| **Scale** | 0-1 (higher = more critical) | 0-10 (higher = more secure) |
| **Focus** | Ecosystem impact | Security best practices |
| **Use Case** | Prioritize security attention | Assess security posture |

Both tools complement each other:
- **High Criticality + Low Scorecard** = High priority for security improvements
- **High Criticality + High Scorecard** = Well-secured critical projects
- **Low Criticality + Low Scorecard** = Lower priority but still needs attention
