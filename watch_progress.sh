#!/bin/bash
# Continuous progress monitoring for SBOM scanning

echo "🔄 Monitoring SBOM Scan Progress (Ctrl+C to stop)"
echo "=================================================="
echo ""

while true; do
    clear
    echo "🕐 $(date)"
    echo "=================================================="
    echo ""
    
    /Users/tian/Develop.localized/2023-oss-in-energy-data/check_progress.sh
    
    echo ""
    echo "📝 Recent log entries:"
    tail -5 /Users/tian/Develop.localized/2023-oss-in-energy-data/scan_output.log 2>/dev/null | grep "✅\|❌\|📊" || echo "  (no recent entries)"
    
    echo ""
    echo "⏸️  Press Ctrl+C to stop monitoring"
    echo "=================================================="
    
    sleep 30  # Update every 30 seconds
done


