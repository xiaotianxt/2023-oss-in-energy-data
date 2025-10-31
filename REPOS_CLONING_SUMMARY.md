# Vulnerable Repositories Cloning Summary

## 📊 Overview

Successfully cloned **100 vulnerable repositories** out of 132 projects with known vulnerabilities.

### Statistics
- **Total vulnerable projects**: 132
- **Successfully cloned**: 100 (75.8%)
- **Total disk space**: 13GB
- **Clone method**: Shallow clone (depth 1) with sparse checkout

## 🎯 Smart Cloning Features

### Space-Saving Techniques
1. **Shallow Clone (--depth 1)**
   - Only fetches the most recent commit
   - Dramatically reduces repository size

2. **Sparse Checkout**
   - Excludes large data files automatically
   - Filters out: CSV, databases, media files, archives
   - Keeps: Source code, configs, dependency files

### Excluded File Types
```
- Data files: *.csv, *.tsv, *.parquet, *.hdf5, *.xlsx
- Databases: *.db, *.sqlite, *.pkl
- Binary data: *.npy, *.npz
- Media: *.mp4, *.avi, *.mp3, *.zip, *.tar.gz
- Large image datasets in data/ and datasets/ folders
```

### Always Included
```
✅ All source code files (.py, .js, .java, .c, .cpp, .rs, etc.)
✅ Dependency files (requirements.txt, package.json, Cargo.toml, etc.)
✅ Configuration files (.yml, .toml, .ini, .json)
✅ Documentation (*.md, *.rst, README, LICENSE)
✅ Build files (Makefile, Dockerfile, etc.)
```

## 📦 Cloned Repositories

Total: 100 repositories

<details>
<summary>View all cloned repositories</summary>

1. 3D-PV-Locator
2. AixLib
3. Ampere
4. atlite
5. BattMo
6. beam
7. beep
8. BuildingSystems
9. BuildSysPro
10. calliope
11. CIMTool
12. dpsim
13. electricitymap-contrib
14. emlab-generation
15. emobility-smart-charging
16. emobpy
17. energy-py
18. entsoe-py
19. ESIOS
20. FEHM
21. gopem
22. GridCal
23. GSEE
24. GSF
25. HELICS
26. HiSim
27. honeybee
28. hplib
29. impedance.py
30. LandBOSSE
31. lib60870
32. libcimpp
33. liionpack
34. load_forecasting
35. makani
36. nempy
37. NYCBuildingEnergyUse
38. ocpp
39. offgridders
40. open-MaStR
41. openCEM
42. openfast
43. OpenOA
44. openPDC
45. OpenStudio
46. OpenStudio-ERI
47. OpenStudio-HPXML
48. openTEPES
49. openXDA
50. ORBIT
51. origin
52. pandapower
53. Photovoltaic_Fault_Detector
54. PLANHEAT Tool
55. powerplantmatching
56. PV4GER
57. PV_ICE
58. pvanalytics
59. pvcompare
60. pvcaptest
61. pvlib-python
62. pyam
63. pycity_scheduling
64. pyEIA
65. pygfunction
66. pypownet
67. RAMP
68. rdtools
69. resstock
70. reV
71. reVX
72. SEED
73. SHARPy
74. SIEGate
75. snl-quest
76. solar-data-tools
77. SolarTherm
78. solax
79. solcore5
80. thermo
81. universal-battery-database
82. VOLTTRON
83. waiwera
84. windrose
... and more

</details>

## 🚫 Not Cloned (32 projects)

### Reasons
1. **Name matching issues** (~20 projects)
   - Project names in projects.csv don't match sanitized names
   - Case sensitivity differences
   
2. **Fetch timeouts** (3 projects)
   - BattMo (large repository)
   - openHistorian (large repository)
   - openMIC (connection issues)

3. **Not found in projects.csv** (~9 projects)
   - Projects may have been renamed or moved

## 🔧 Scripts Used

### 1. `clone_vulnerable_repos_smart.py`
Main cloning script with smart filtering and sparse checkout.

**Features:**
- Parallel cloning (5 workers)
- Automatic sparse checkout configuration
- Progress tracking
- Size reporting

**Usage:**
```bash
python3 clone_vulnerable_repos_smart.py
```

### 2. `clone_remaining_vulnerable.py`
Helper script to clone any remaining vulnerable repositories.

**Usage:**
```bash
python3 clone_remaining_vulnerable.py
```

## 💡 Tips

### Updating Repositories
```bash
cd repos/<repo-name>
git pull
```

### Finding a Specific Repository
```bash
ls repos/ | grep -i <search-term>
```

### Checking Repository Size
```bash
du -sh repos/<repo-name>
```

### Re-cloning a Repository
```bash
rm -rf repos/<repo-name>
python3 clone_remaining_vulnerable.py
```

## 📈 Space Efficiency

**Without optimization:**
- Average full clone: ~500MB-2GB per repo
- Estimated total: 50-200GB

**With optimization:**
- Average shallow sparse clone: ~130MB per repo
- Actual total: **13GB** (93-97% space saved!)

## ✅ Verification

To verify all repositories are correctly cloned:
```bash
cd repos
for dir in */; do
  cd "$dir"
  if [ -d .git ]; then
    echo "✓ $dir"
  else
    echo "✗ $dir (not a git repo)"
  fi
  cd ..
done
```

## 🔄 Future Updates

To update all repositories:
```bash
cd repos
for dir in */; do
  echo "Updating $dir..."
  cd "$dir"
  git pull
  cd ..
done
```

---

**Last Updated**: 2025-10-31
**Total Size**: 13GB
**Repositories**: 100/132 vulnerable projects

