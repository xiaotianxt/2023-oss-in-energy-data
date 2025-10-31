# Fix for Missing Repository URLs in vulnerability-data.json

## Problem Identified

The `vulnerability-data.json` file had **87 out of 375 projects** (23%) with empty `repo_url` fields. This was caused by inconsistent project name matching between:
- CSV scan filenames (e.g., `a-global-inventory-of-commerical-industrial...csv`)
- Project names in `projects.csv` (e.g., `A Global Inventory of Commerical-, Industrial-...`)
- Repository names from URLs (e.g., `solar-pv-global-inventory`)

## Root Cause

The `load_projects_metadata()` function in `analyze_vulnerabilities.py` was using a simplistic matching strategy that only looked at the repository name from the URL (last segment). This failed for projects where:

1. **Long descriptive names** were shortened in repo URLs
   - CSV: `a-global-inventory-of-commerical-industrial-and-utility-scale-photovoltaic-solar-generating-units`
   - Repo: `solar-pv-global-inventory`

2. **Special characters** (dots, underscores) were handled inconsistently
   - CSV: `anymodjl` (from scan)
   - Project: `AnyMOD.jl` (from projects.csv)
   - Repo: `AnyMOD.jl` (from URL)

3. **Case sensitivity and punctuation**
   - CSV: `open_bea` (with underscore)
   - Project: `open_BEA` (with uppercase)
   - Repo: `openbea` (no underscore)

## Solution Implemented

Enhanced the `load_projects_metadata()` function to create **multiple lookup keys** for each project:

### 1. Created `normalize_project_name()` function
```python
def normalize_project_name(name):
    """Normalize project name for consistent matching."""
    import re
    name = name.lower()
    # Replace underscores and spaces with hyphens first
    name = name.replace('_', '-').replace(' ', '-')
    # Remove special characters but keep alphanumeric and hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    # Remove multiple consecutive hyphens
    name = re.sub(r'-+', '-', name)
    # Strip leading/trailing hyphens
    name = name.strip('-')
    return name
```

### 2. Store metadata under 4 different keys per project
- **Original repo name from URL**: `solar-pv-global-inventory`
- **Normalized repo name**: `solar-pv-global-inventory` (same in this case)
- **Lowercase project name**: `a global inventory of commerical-, industrial-...`
- **Normalized project name**: `a-global-inventory-of-commerical-industrial...`

### 3. Added null-safety checks
- Handled cases where `.get()` returns `None`
- Added `or ''` fallbacks for empty string fields

## Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Empty `repo_url` fields | **87** | **0** | ✅ **100% fixed** |
| Projects with metadata | 375 | 558 | +183 (includes variations) |
| Match rate | 77% | 100% | +23% |

### Verified Examples

✅ **Fixed Projects:**
- `a-global-inventory-of-commerical-industrial-...` → `https://github.com/Lkruitwagen/solar-pv-global-inventory`
- `anymodjl` → `https://github.com/leonardgoeke/AnyMOD.jl`
- `open_bea` → `https://gitlab.lrz.de/open-ees-ses/openbea`
- `pycity_base` → `https://github.com/RWTH-EBC/pyCity`

## Files Modified

1. **`/Users/tian/Develop.localized/2023-oss-in-energy-data/analyze_vulnerabilities.py`**
   - Added `normalize_project_name()` function
   - Enhanced `load_projects_metadata()` with multi-key lookup
   - Added null-safety checks in `analyze_vulnerabilities()`

## How to Re-generate Data

```bash
cd /Users/tian/Develop.localized/2023-oss-in-energy-data
python3 analyze_vulnerabilities.py
```

This will regenerate `/energy-security-viz/public/vulnerability-data.json` with all repository URLs properly populated.

## Impact on Visualization

All project cards in the dashboard now have clickable repository links, improving user experience and navigation to source code. The "Project Explorer" tab can now display complete metadata for all projects.

---
**Fixed on:** October 31, 2025  
**Script:** `analyze_vulnerabilities.py`  
**Result:** 100% of projects now have valid repository URLs

