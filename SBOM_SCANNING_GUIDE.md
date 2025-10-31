# SBOM Scanning Guide

## Overview
This guide documents the SBOM (Software Bill of Materials) scanning setup for the 388 open-source energy projects.

## Tools Used
- **Syft** (v1.36.0) - Installed via Homebrew for generating SBOMs
- **Git** - For cloning repositories (shallow clones only)
- **Python 3** - For orchestration scripts

## Directory Structure
```
2023-oss-in-energy-data/
├── projects.csv              # Source data with 388 projects
├── repos/                    # Cloned repositories (shallow clones)
├── sbom/                     # Generated SBOM JSON files
├── clone_and_scan.py         # Main parallel processing script
├── check_progress.sh         # Progress monitoring script
└── SBOM_SCANNING_GUIDE.md    # This file
```

## Key Features

### Efficient Cloning
- **Shallow clone**: `--depth 1` ensures only HEAD commit is fetched
- **Single branch**: `--single-branch` skips all other branches
- **Result**: Minimal disk usage and faster cloning

### Parallel Processing
- **6 concurrent workers** for clone + scan operations
- Thread-safe logging to prevent output corruption
- Automatic skip of already-processed projects

### SBOM Generation
- Uses Syft to analyze each repository
- Outputs in JSON format (SPDX/CycloneDX compatible)
- Quiet mode (`-q`) to reduce output noise

## Scripts

### clone_and_scan.py
Main script that:
1. Reads projects from `projects.csv`
2. Clones repositories in parallel (if not already cloned)
3. Scans each repo with Syft
4. Generates SBOM JSON files

**Usage:**
```bash
python3 clone_and_scan.py
```

**Features:**
- Automatic resume: Skips already cloned repos and existing SBOMs
- Progress tracking: Shows updates every 20 projects
- Comprehensive stats: Reports clone and scan success/failure rates

### check_progress.sh
Quick status checker showing:
- Number of repositories cloned
- Number of SBOMs generated
- Total disk usage
- Whether the main script is running

**Usage:**
```bash
./check_progress.sh
```

## Output Format

Each SBOM is saved as: `sbom/{sanitized-project-name}.json`

Example: `PyBaMM` → `sbom/pybamm.json`

## Monitoring Long-Running Process

The script can run for several hours depending on:
- Number of projects (388 total)
- Repository sizes
- Network speed
- Available CPU cores

Check progress anytime with:
```bash
./check_progress.sh
```

Or view real-time logs if running in foreground.

## Error Handling

The script handles:
- **Clone failures**: Network issues, missing repos, access denied
- **Timeouts**: 5 minutes for clone, 3 minutes for scan
- **Scan failures**: Logged but don't stop other projects

All results are categorized in the final summary.

## Example Output

```
📈 Final Summary:
   Total projects: 388

📥 Clone Statistics:
   cloned: 150
   exists: 200
   clone_failed: 30
   clone_timeout: 8

🔍 Scan Statistics:
   scan_success: 320
   scan_exists: 50
   scan_failed: 10
   skipped: 8

✅ Total SBOMs generated: 370
```

## Notes

- Some repositories may no longer exist (404 errors)
- Some may require authentication (private repos)
- Large monorepos may take longer to scan
- The `repos/` directory can be deleted after scanning to save space

## Clean Up

To remove cloned repositories after scanning:
```bash
rm -rf repos/
```

SBOMs in `sbom/` directory are the final deliverables and should be kept.


