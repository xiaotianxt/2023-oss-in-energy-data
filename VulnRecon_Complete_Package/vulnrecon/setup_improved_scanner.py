#!/usr/bin/env python3
"""
Setup script for the improved VulnRecon scanner.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Success")
            return True
        else:
            print(f"  ❌ Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} is supported")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} is not supported. Need Python 3.8+")
        return False


def install_python_dependencies():
    """Install required Python packages."""
    print("📦 Installing Python dependencies...")
    
    # Core dependencies for enhanced parsing
    core_deps = [
        "packaging>=21.0",
        "requests>=2.25.0",
        "click>=8.0.0",
    ]
    
    # Professional security tools
    security_tools = [
        "bandit[toml]",
        "safety",
        "pip-audit",
        "semgrep",
    ]
    
    # Install core dependencies
    for dep in core_deps:
        if not run_command(f"pip install '{dep}'", f"Installing {dep}"):
            return False
    
    # Install security tools (optional)
    print("\n🔒 Installing professional security tools...")
    print("  (These are optional but highly recommended)")
    
    for tool in security_tools:
        run_command(f"pip install '{tool}'", f"Installing {tool}")
    
    return True


def install_trivy():
    """Install Trivy scanner."""
    print("\n🛡️  Installing Trivy scanner...")
    
    # Check if Trivy is already installed
    result = subprocess.run("trivy --version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("  ✅ Trivy is already installed")
        return True
    
    # Try to install Trivy based on OS
    import platform
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        if run_command("brew --version", "Checking Homebrew"):
            return run_command("brew install trivy", "Installing Trivy via Homebrew")
    elif system == "linux":
        # Try different package managers
        if run_command("which apt", "Checking apt"):
            return run_command(
                "sudo apt-get update && sudo apt-get install -y wget apt-transport-https gnupg lsb-release && "
                "wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add - && "
                "echo 'deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main' | sudo tee -a /etc/apt/sources.list.d/trivy.list && "
                "sudo apt-get update && sudo apt-get install -y trivy",
                "Installing Trivy via apt"
            )
        elif run_command("which yum", "Checking yum"):
            return run_command(
                "sudo yum install -y wget && "
                "wget https://github.com/aquasecurity/trivy/releases/latest/download/trivy_Linux-64bit.rpm && "
                "sudo rpm -ivh trivy_Linux-64bit.rpm",
                "Installing Trivy via yum"
            )
    
    print("  ⚠️  Could not install Trivy automatically. Please install manually:")
    print("     https://aquasecurity.github.io/trivy/latest/getting-started/installation/")
    return False


def create_config_file():
    """Create configuration file for the improved scanner."""
    config_content = """# Enhanced VulnRecon Scanner Configuration

# Professional Tools Settings
professional_tools:
  enabled: true
  timeout_seconds: 120
  
  bandit:
    enabled: true
    confidence_level: "high"
    severity_level: "low"
  
  safety:
    enabled: true
    ignore_ids: []  # Add CVE IDs to ignore
  
  pip_audit:
    enabled: true
    format: "json"
  
  semgrep:
    enabled: true
    config: "auto"  # or specify custom rules
  
  trivy:
    enabled: true
    security_checks: ["vuln"]

# Enhanced Version Parsing
version_parsing:
  strict_mode: true
  normalize_names: true
  extract_exact_versions: true
  
  # Package name aliases
  aliases:
    yaml: "pyyaml"
    pil: "pillow"

# Vulnerability Detection
vulnerability_detection:
  confidence_threshold: 0.7
  include_info_level: false
  
  # PyYAML specific settings
  pyyaml:
    vulnerable_before: "5.4"
    safe_versions: ["5.4", "6.0", "6.0.1", "6.0.2"]
    
# Reporting
reporting:
  include_safe_findings: true
  detailed_metadata: true
  confidence_scores: true
  
# Database Settings
database:
  connection_timeout: 30
  query_limit: 1000
"""
    
    config_path = Path(__file__).parent / "config_improved.yaml"
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        print(f"  ✅ Configuration file created: {config_path}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create config file: {e}")
        return False


def verify_installation():
    """Verify that everything is installed correctly."""
    print("\n🔍 Verifying installation...")
    
    # Check Python imports
    try:
        import packaging
        import requests
        import click
        print("  ✅ Core Python dependencies are working")
    except ImportError as e:
        print(f"  ❌ Missing Python dependency: {e}")
        return False
    
    # Check professional tools
    tools = {
        "bandit": "bandit --version",
        "safety": "safety --version", 
        "pip-audit": "pip-audit --version",
        "semgrep": "semgrep --version",
        "trivy": "trivy --version"
    }
    
    available_tools = []
    for tool, cmd in tools.items():
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            available_tools.append(tool)
            print(f"  ✅ {tool} is available")
        else:
            print(f"  ⚠️  {tool} is not available")
    
    print(f"\n📊 Available professional tools: {len(available_tools)}/5")
    
    if len(available_tools) >= 2:
        print("  ✅ Sufficient tools available for enhanced scanning")
        return True
    else:
        print("  ⚠️  Consider installing more professional tools for better results")
        return True  # Still functional with custom scanner


def main():
    """Main setup function."""
    print("🚀 VulnRecon Enhanced Scanner Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Install Trivy (optional)
    install_trivy()
    
    # Create configuration file
    create_config_file()
    
    # Verify installation
    if verify_installation():
        print("\n" + "=" * 50)
        print("✅ Setup completed successfully!")
        print("\n🎯 Next steps:")
        print("1. Run the test script: python test_improved_parsing.py")
        print("2. Try the improved scanner: python improved_scanner.py --help")
        print("3. Scan your database: python improved_scanner.py -d path/to/dependencies.db")
        print("\n📚 Documentation:")
        print("  • Enhanced version parsing reduces false positives")
        print("  • Professional tools provide comprehensive coverage")
        print("  • Detailed reports include confidence scores")
    else:
        print("\n❌ Setup completed with warnings")
        print("  The scanner will still work but with limited functionality")


if __name__ == '__main__':
    main()
