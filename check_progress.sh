#!/bin/bash
# Quick progress checker for the clone and scan operation

echo "📊 Progress Check"
echo "=================="
echo ""

REPOS_DIR="/Users/tian/Develop.localized/2023-oss-in-energy-data/repos"
SBOM_DIR="/Users/tian/Develop.localized/2023-oss-in-energy-data/sbom"

if [ -d "$REPOS_DIR" ]; then
    REPO_COUNT=$(find "$REPOS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
    echo "📁 Repositories cloned: $REPO_COUNT"
else
    echo "📁 Repositories cloned: 0"
fi

if [ -d "$SBOM_DIR" ]; then
    SBOM_COUNT=$(find "$SBOM_DIR" -name "*.json" | wc -l)
    echo "💾 SBOMs generated: $SBOM_COUNT"
    
    # Show size
    SBOM_SIZE=$(du -sh "$SBOM_DIR" 2>/dev/null | cut -f1)
    echo "📦 SBOM directory size: $SBOM_SIZE"
else
    echo "💾 SBOMs generated: 0"
fi

echo ""
echo "🎯 Total projects in CSV: 388"
echo ""

# Check if process is running
if pgrep -f "clone_and_scan.py" > /dev/null; then
    echo "✅ Script is currently running"
else
    echo "⏸️  Script is not running"
fi


