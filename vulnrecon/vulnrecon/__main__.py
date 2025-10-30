"""CLI entry point for VulnRecon scanner."""

import argparse
import sys
from pathlib import Path

from .scanner import VulnReconScanner


BANNER = """
╦  ╦╦ ╦╦  ╔╗╔╦═╗╔═╗╔═╗╔═╗╔╗╔
╚╗╔╝║ ║║  ║║║╠╦╝║╣ ║  ║ ║║║║
 ╚╝ ╚═╝╩═╝╝╚╝╩╚═╚═╝╚═╝╚═╝╝╚╝
Automated Vulnerability Reconnaissance
Version 0.1.0 - For Authorized Testing Only
"""

DISCLAIMER = """
===============================================================================
                             LEGAL DISCLAIMER
===============================================================================

This tool is provided for AUTHORIZED SECURITY TESTING ONLY.

By using this tool, you agree that:

1. You have explicit written permission to test the target systems
2. You will follow responsible disclosure practices
3. You comply with all applicable laws and regulations
4. You will not use this tool for malicious purposes
5. You understand that unauthorized testing may be illegal

The authors are not responsible for misuse or damage caused by this tool.

Press CTRL+C to cancel, or ENTER to acknowledge and continue...
===============================================================================
"""


def print_banner():
    """Print the tool banner."""
    print(BANNER)


def show_disclaimer():
    """Show legal disclaimer and require acknowledgment."""
    print(DISCLAIMER)
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n[!] Canceled by user")
        sys.exit(0)


def main():
    """Main CLI entry point."""
    print_banner()

    parser = argparse.ArgumentParser(
        description="VulnRecon - Automated Vulnerability Reconnaissance Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--target",
        help="Path to target repository to scan",
        type=str,
    )

    parser.add_argument(
        "--database",
        help="Path to SQLite dependency database",
        type=str,
    )

    parser.add_argument(
        "--project",
        help="Specific project name to scan from database",
        type=str,
    )

    parser.add_argument(
        "--scan-all",
        help="Scan all projects from database",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Output directory for results (default: results/)",
        default="results",
        type=str,
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file (default: config.yaml)",
        default="config.yaml",
        type=str,
    )

    parser.add_argument(
        "--no-disclaimer",
        help="Skip disclaimer (for automated use)",
        action="store_true",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.target and not args.database:
        parser.error("Either --target or --database must be specified")

    # Show disclaimer unless skipped
    if not args.no_disclaimer:
        show_disclaimer()

    # Initialize scanner
    print(f"[*] Initializing VulnRecon scanner...")
    print(f"[*] Config file: {args.config}\n")

    try:
        scanner = VulnReconScanner(config_path=args.config)
    except Exception as e:
        print(f"[!] Error initializing scanner: {e}")
        sys.exit(1)

    # Run scan
    try:
        if args.database:
            # Scan from database
            results = scanner.scan_from_database(
                db_path=args.database,
                project_name=args.project,
                output_dir=args.output,
            )

            print(f"\n{'='*60}")
            print(f"[+] Scan complete!")
            print(f"[+] Scanned {len(results)} projects")
            print(f"[+] Results saved to: {args.output}/")

        elif args.target:
            # Scan local repository
            if not Path(args.target).exists():
                print(f"[!] Error: Target path does not exist: {args.target}")
                sys.exit(1)

            result = scanner.scan_repository(
                repo_path=args.target,
                repo_url=None,
            )

            # Save result
            import json
            import os
            os.makedirs(args.output, exist_ok=True)
            output_file = os.path.join(args.output, "scan_result.json")

            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"\n{'='*60}")
            print(f"[+] Scan complete!")
            print(f"[+] Found {result['summary']['total_findings']} issues")
            print(f"[+] Risk Score: {result['summary']['risk_score']} ({result['summary']['risk_level']})")
            print(f"[+] Results saved to: {output_file}")

            # Print summary
            print(f"\n[*] Findings by severity:")
            for severity, count in result['summary']['by_severity'].items():
                if count > 0:
                    print(f"    {severity}: {count}")

    except KeyboardInterrupt:
        print("\n\n[!] Scan interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error during scan: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
