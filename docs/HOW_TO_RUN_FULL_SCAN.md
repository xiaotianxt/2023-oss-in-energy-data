# How to Run the Full Deep CVE Scan

This guide shows you how to run a **complete, comprehensive analysis** of all your dependencies - not just a sample.

---

## 🎯 Quick Start: Run Full Analysis Now

```bash
cd dependency_analyzer

# Full deep scan - analyzes ALL 1,559 packages and ALL 357 projects
python run_full_analysis.py --full
```

**Expected Time:** 3-5 hours (run overnight or during lunch)
**What It Does:** Scans every package, resolves all dependencies, analyzes all projects

---

## 📊 What's the Difference?

### Sample Scan (What I Just Did)
- ✅ Scanned: 20 most-used packages
- ✅ Time: ~2 minutes
- ✅ Found: 59 CVEs
- ✅ Good for: Quick check, testing

### Full Deep Scan (What You Want)
- ✅ Scans: **ALL 1,559 unique packages**
- ✅ Resolves: Transitive dependencies for **all 357 projects**
- ✅ Analyzes: Complete CVE impact per project
- ✅ Time: 3-5 hours
- ✅ Good for: Production security audit

---

## 🚀 Running Options

### 1. Full Analysis (Recommended for Production)

```bash
python run_full_analysis.py --full
```

**This will:**
1. Scan all 1,559 packages for CVEs (~1-2 hours)
2. Resolve transitive dependencies for all projects (~30-60 min)
3. Analyze CVE impact for all projects (~1-2 hours)
4. Generate comprehensive reports (~5 min)

**Output Files:**
- `full_analysis_results/EXECUTIVE_SUMMARY.json` - High-level findings
- `full_analysis_results/vulnerability_matrix.csv` - Excel-ready matrix
- `full_analysis_results/cve_summary.csv` - All CVEs with details
- `full_analysis_results/FULL_ANALYSIS_REPORT.json` - Complete data
- `full_analysis_results/full_analysis.log` - Detailed log

### 2. Test with Sample (Quick Validation)

```bash
# Test with 20 projects (10-15 minutes)
python run_full_analysis.py --sample 20
```

Good for:
- Testing the script before full run
- Quick validation
- Demo purposes

### 3. Force Refresh (Bypass Cache)

```bash
# Force re-scan everything, ignore cache
python run_full_analysis.py --full --force-refresh
```

Use when:
- You want fresh CVE data
- New vulnerabilities announced
- Running weekly security audit

### 4. Run Individual Steps

```bash
# Step 1 only: Scan all packages for CVEs
python run_full_analysis.py --step1-only

# Step 2 only: Resolve transitive dependencies
python run_full_analysis.py --step2-only

# Step 3 only: Impact analysis
python run_full_analysis.py --step3-only

# Step 4 only: Generate reports
python run_full_analysis.py --step4-only
```

Good for:
- Resume interrupted analysis
- Re-run specific step
- Debug issues

---

## 📋 Complete 4-Step Process

### Step 1: Scan ALL Packages for CVEs (1-2 hours)

```bash
python run_full_analysis.py --step1-only
```

**What it does:**
- Queries OSV API for every unique package (1,559 packages)
- Finds all known CVEs
- Stores results in database
- Caches for 24 hours

**Progress updates every 50 packages:**
```
Progress: 50/1559 (3.2%) - ETA: 87.3 minutes
Progress: 100/1559 (6.4%) - ETA: 82.1 minutes
...
```

**Output:** `step1_all_packages_cves.json`

### Step 2: Resolve Transitive Dependencies (30-60 min)

```bash
python run_full_analysis.py --step2-only
```

**What it does:**
- For each project, explores complete dependency tree
- Uses dynamic programming (no redundant work!)
- Resolves dependencies of dependencies (up to 3 levels deep)
- Identifies shared dependencies

**Progress updates every 10 projects:**
```
Progress: 10/357 - ETA: 45.2 min
[10/357] Resolving temoa...
  Direct dependencies: 191
  Total with transitive: 287
```

**Output:** `step2_transitive_dependencies.json`

### Step 3: Full Impact Analysis (1-2 hours)

```bash
python run_full_analysis.py --step3-only
```

**What it does:**
- Combines CVE data with dependency trees
- Identifies which CVEs affect which projects
- Calculates severity breakdowns
- Finds high-risk dependencies
- Shows dependency paths for vulnerabilities

**Progress updates every 10 projects:**
```
[50/357] Analyzing CityEnergyAnalyst...
  ⚠️  36 CVEs found!
  - CRITICAL: 2
  - HIGH: 12
  - MEDIUM: 18
  - LOW: 4
```

**Output:** `step3_full_impact_analysis.json`

### Step 4: Generate Reports (5 min)

```bash
python run_full_analysis.py --step4-only
```

**What it does:**
- Creates executive summary
- Exports CSV files for Excel
- Generates vulnerability matrix (Project × CVE)
- Compiles comprehensive JSON report

**Output Files:**
- `EXECUTIVE_SUMMARY.json`
- `FULL_ANALYSIS_REPORT.json`
- `cve_summary.csv`
- `vulnerability_matrix.csv`
- `cve_summary_detailed.json`

---

## 🎬 Real-World Example

### Scenario: Running Full Analysis

```bash
# 1. Navigate to directory
cd dependency_analyzer

# 2. Start full analysis
python run_full_analysis.py --full

# You'll see:
# ==================================================================
# STARTING FULL DEEP CVE ANALYSIS
# ==================================================================
# Configuration:
#   - Force refresh: False
#   - Sample projects: ALL
#   - Max dependency depth: 3
#   - Output directory: full_analysis_results
#
# ==================================================================
# STEP 1: Scanning ALL packages for CVEs
# ==================================================================
# Total unique packages to scan: 1559
# Estimated time: 38.9 minutes
#
# Progress: 50/1559 (3.2%) - ETA: 87.3 minutes
#   ⚠️  numpy (pypi): 16 CVEs
#   ⚠️  requests (pypi): 12 CVEs
# Progress: 100/1559 (6.4%) - ETA: 82.1 minutes
# ...
```

### After Completion (3-5 hours later)

```bash
# ==================================================================
# 🎉 FULL ANALYSIS COMPLETE!
# ==================================================================
# All results saved to: full_analysis_results/
#
# Next steps:
#   1. Review EXECUTIVE_SUMMARY.json for high-level findings
#   2. Check vulnerability_matrix.csv in Excel
#   3. Prioritize projects with highest CVE counts
#   4. Create remediation plan for high-severity CVEs
```

---

## 📁 Output Structure

After running, you'll have:

```
full_analysis_results/
├── EXECUTIVE_SUMMARY.json          ← Start here!
├── FULL_ANALYSIS_REPORT.json       ← Complete data
├── vulnerability_matrix.csv        ← Open in Excel
├── cve_summary.csv                 ← All CVEs, Excel-ready
├── cve_summary_detailed.json       ← Detailed CVE info
├── step1_all_packages_cves.json    ← All package CVEs
├── step2_transitive_dependencies.json  ← Dependency trees
├── step3_full_impact_analysis.json     ← Impact analysis
└── full_analysis.log               ← Detailed execution log
```

### Key Files Explained

#### EXECUTIVE_SUMMARY.json
```json
{
  "overview": {
    "total_projects": 357,
    "projects_with_vulnerabilities": 82,
    "percentage_affected": 23.0,
    "total_cves_found": 450,
    "unique_packages_with_cves": 45
  },
  "top_risks": [
    {
      "project_name": "pudl",
      "cve_count": 47,
      "url": "https://github.com/..."
    }
  ]
}
```

#### vulnerability_matrix.csv
```csv
project_name,url,cve_count,cves
pudl,https://github.com/catalyst-cooperative/pudl,47,"CVE-2023-1234,CVE-2023-5678,..."
temoa,https://github.com/TemoaProject/temoa,43,"CVE-2023-9012,..."
```

---

## 🔍 Monitoring Progress

### Check Progress in Real-Time

```bash
# In another terminal, watch the log file
tail -f full_analysis_results/full_analysis.log

# Or check how many CVEs found so far
grep "CVEs found" full_analysis_results/full_analysis.log | wc -l
```

### Resume After Interruption

The scanner caches results, so if interrupted:

```bash
# Just run again - it will use cached data
python run_full_analysis.py --full

# Or skip steps that completed
python run_full_analysis.py --step3-only  # Resume at step 3
```

---

## ⏱️ Time Estimates

Based on your database (357 projects, 1,559 packages):

| Step | Estimated Time | What's Happening |
|------|----------------|------------------|
| **Step 1** | 1-2 hours | Querying OSV API for 1,559 packages |
| **Step 2** | 30-60 min | Resolving dependencies for 357 projects |
| **Step 3** | 1-2 hours | Analyzing CVE impact per project |
| **Step 4** | 5 min | Generating reports |
| **TOTAL** | **3-5 hours** | Complete deep analysis |

**Tips to speed up:**
- Run overnight or during lunch
- First run is slowest (API calls)
- Second run is much faster (uses cache)
- Can run steps individually

---

## 💡 Pro Tips

### 1. Test First with Sample

```bash
# Test with 10 projects (5 minutes)
python run_full_analysis.py --sample 10

# Review results, then run full
python run_full_analysis.py --full
```

### 2. Run in Background

```bash
# Linux/Mac
nohup python run_full_analysis.py --full > analysis.out 2>&1 &

# Windows PowerShell
Start-Process python -ArgumentList "run_full_analysis.py --full" -NoNewWindow
```

### 3. Schedule Weekly Scans

```bash
# Add to cron (Linux/Mac)
0 2 * * 0 cd /path/to/dependency_analyzer && python run_full_analysis.py --full --force-refresh

# Or Windows Task Scheduler
schtasks /create /tn "CVE Scan" /tr "python C:\...\run_full_analysis.py --full" /sc weekly /d SUN /st 02:00
```

### 4. Compare Results Over Time

```bash
# Rename output directory with date
mv full_analysis_results full_analysis_2025-10-27

# Run new scan
python run_full_analysis.py --full

# Now you have both for comparison
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install requests python-dotenv pandas
```

### "Database is locked"
Make sure no other scripts are accessing the database.

### "OSV API timeout"
Network issue. Just run again - cached results are preserved.

### Out of memory
```bash
# Reduce max depth
# Edit run_full_analysis.py line 38:
self.resolver = DependencyResolverOptimized(max_depth=2)  # Was 3
```

### Takes too long
```bash
# Run steps separately over multiple days
python run_full_analysis.py --step1-only  # Day 1
python run_full_analysis.py --step2-only  # Day 2
python run_full_analysis.py --step3-only  # Day 3
python run_full_analysis.py --step4-only  # Day 4
```

---

## 📊 What You'll Learn

After the full scan completes, you'll know:

✅ **Every CVE** affecting your 357 projects
✅ **Exact dependency paths** showing how vulnerabilities reach your code
✅ **Severity levels** (CRITICAL, HIGH, MEDIUM, LOW) for prioritization
✅ **Most at-risk projects** that need immediate attention
✅ **Most vulnerable packages** to avoid or update
✅ **Transitive vulnerabilities** from dependencies-of-dependencies
✅ **Complete impact analysis** for informed decision making

---

## 🚀 Ready to Run?

### Start the Full Analysis Now:

```bash
cd dependency_analyzer
python run_full_analysis.py --full
```

Then grab a coffee (or 3) ☕☕☕ - this will take a few hours!

---

## 📞 Need Help?

- **Check the log:** `full_analysis_results/full_analysis.log`
- **Resume interrupted scan:** Just run the command again
- **Questions:** Review the documentation in `README_CVE_FEATURES.md`

---

**Remember:** The sample scan I did was just the top 20 packages. The full scan will give you **complete, production-grade security intelligence** across your entire project portfolio!
