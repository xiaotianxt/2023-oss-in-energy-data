# Quick Reference Guide

## 🚀 Most Common Commands

### Fast SBOM Scan (Recommended)
```bash
cd dependency_analyzer
export GITHUB_TOKEN="ghp_your_token"
python cli.py scan-sbom --limit 10      # Test with 10 projects
python cli.py scan-sbom                 # Full scan (all 357 projects)
```

### Traditional Deep Scan
```bash
cd dependency_analyzer
python run_full_analysis.py
```

### View Specific Project's Vulnerabilities
```bash
cd dependency_analyzer
python cli.py impact PROJECT_ID --scan-cves
```

### Find All Projects Affected by CVE
```bash
cd dependency_analyzer
python cli.py cve-impact CVE-2024-12345
```

## 📊 Output Locations

| Scan Type | Output Location | Time |
|-----------|----------------|------|
| SBOM scan | `dependency_analyzer/sbom_scan_results/` | 30-60 min |
| Full scan | `dependency_analyzer/full_analysis_results/` | ~4 hours |
| Exports | User-specified path | Varies |

## 🔑 GitHub Token

**Get token:** https://github.com/settings/tokens (select `public_repo` scope)

**Set token:**
```bash
export GITHUB_TOKEN="ghp_your_token_here"
# OR
echo "GITHUB_TOKEN=ghp_your_token" > .env
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `dependency_analyzer/cli.py` | Main command-line interface |
| `dependency_analyzer/sbom_scraper.py` | SBOM file scraper |
| `dependency_analyzer/sbom_cve_scanner.py` | Fast CVE scanner |
| `data/dependencies.db` | Main database (357 projects) |
| `data/projects.yaml` | Project metadata |

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Rate limit exceeded | Set GITHUB_TOKEN |
| Module not found | `pip install -r dependency_analyzer/requirements.txt` |
| No SBOM found | Normal - falls back to database automatically |
| Very slow | Use GitHub token for 5,000 req/hr (vs 60/hr) |

## 📚 Documentation

- **Quick Start**: [docs/SBOM_QUICKSTART.md](docs/SBOM_QUICKSTART.md)
- **Technical Details**: [docs/SBOM_IMPLEMENTATION_SUMMARY.md](docs/SBOM_IMPLEMENTATION_SUMMARY.md)
- **Full Guide**: [docs/COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)
- **Performance**: [docs/DP_VISUAL_COMPARISON.md](docs/DP_VISUAL_COMPARISON.md)

## 💡 Tips

1. **Always use GitHub token** for production scans (5,000 req/hr)
2. **Start with `--limit 10`** to test before full scan
3. **SBOM scanner is 4-8x faster** than traditional method
4. **Results are cached** for 24 hours - re-runs are fast
5. **Check `dependency_analyzer/data/dependencies.db`** for raw data

## 📈 Performance

| Projects | SBOM Scanner | Traditional |
|----------|--------------|-------------|
| 10 | ~2-3 min | ~10-15 min |
| 50 | ~10-15 min | ~45-60 min |
| 357 | ~30-60 min | ~4 hours |

---

**Need help?** Check the full [README.md](README.md) or documentation in [docs/](docs/)
