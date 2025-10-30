# VulnRecon - Automated Vulnerability Reconnaissance Test Suite

## Overview

VulnRecon is an automated security testing framework designed for authorized penetration testing and security research of open-source energy sector projects. It performs static analysis and safe vulnerability detection without exploiting systems.

## Features

- **Automated Vulnerability Detection**: Scans for known CVE patterns in dependencies
- **PyYAML Deserialization Scanner**: Detects unsafe `yaml.load()` usage
- **Django Security Scanner**: Identifies insecure Django configurations
- **Static Code Analysis**: Pattern matching for dangerous code patterns
- **Risk Scoring**: Calculates exploitability scores based on multiple factors
- **Comprehensive Reporting**: JSON, HTML, and Markdown reports

## Use Cases

- Authorized penetration testing engagements
- Security audits of energy infrastructure projects
- CTF competitions and security research
- Defensive security assessments
- CVE impact analysis

## Installation

```bash
cd vulnrecon
pip install -r requirements.txt
```

## Usage

### Basic Scan

```bash
python -m vulnrecon.scanner --target https://github.com/example/repo
```

### Scan with Database Integration

```bash
python -m vulnrecon.scanner --database ../dependency_analyzer/data/dependencies.db --output results/
```

### Scan All Projects from Database

```bash
python -m vulnrecon.scanner --database ../dependency_analyzer/data/dependencies.db --scan-all --output results/
```

### Generate Reports

```bash
python -m vulnrecon.scanner --target https://github.com/example/repo --format html,json,md
```

## Configuration

Edit `config.yaml` to customize:
- Severity thresholds
- Detector modules to enable/disable
- Risk scoring weights
- Output formats

## Detectors

### PyYAML Detector
Identifies:
- Unsafe `yaml.load()` usage
- Missing `yaml.safe_load()` implementations
- Deserialization vulnerabilities
- User input handling in YAML parsing

### Django Detector
Identifies:
- DEBUG=True in production
- Insecure SECRET_KEY configurations
- Missing security middleware
- SQL injection patterns

### Pillow Detector
Identifies:
- Vulnerable Pillow versions
- Image processing on user uploads
- Missing input validation

### Requests Detector
Identifies:
- SSRF vulnerabilities
- Disabled SSL verification
- Unvalidated redirects

## Risk Scoring

Risk scores are calculated based on:
- CVE count and severity
- Code pattern analysis
- Dependency exposure
- Exploitability assessment

**Risk Levels:**
- **CRITICAL** (9.0-10.0): Immediate action required
- **HIGH** (7.0-8.9): Urgent remediation needed
- **MEDIUM** (4.0-6.9): Remediation recommended
- **LOW** (0.1-3.9): Monitor and update
- **INFO** (0.0): Informational findings

## Output

Results are saved to the `results/` directory:
- `{repo_name}_report.json` - Machine-readable results
- `{repo_name}_report.html` - Human-readable HTML report
- `{repo_name}_report.md` - Markdown summary

## Ethical Usage

**IMPORTANT:** This tool is for authorized security testing only.

- Only scan systems you own or have written permission to test
- Follow responsible disclosure practices
- Comply with all applicable laws and regulations
- Do not use for malicious purposes
- Respect rate limits and terms of service

## Architecture

```
Scanner
├── Dependency Analyzer (reads from SQLite)
├── Static Code Analyzer (pattern matching)
├── Vulnerability Detectors (modular plugins)
│   ├── PyYAML Detector
│   ├── Django Detector
│   ├── Pillow Detector
│   └── Requests Detector
├── Risk Calculator (scoring engine)
└── Reporters (output generation)
```

## Example Output

```
=== VulnRecon Security Scan Report ===
Repository: https://github.com/NREL/REopt_Lite_API
Scan Date: 2025-10-30

Total Vulnerabilities Found: 32
Risk Score: 8.5 (HIGH)

Critical Findings:
[CRITICAL] PyYAML unsafe deserialization detected
  - File: config/parser.py:45
  - Pattern: yaml.load(user_input)
  - CVEs: 8 related CVEs
  - Remediation: Use yaml.safe_load() instead

[HIGH] Django DEBUG=True detected
  - File: settings.py:12
  - Risk: Information disclosure
  - Remediation: Set DEBUG=False in production
```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Detectors

1. Create a new detector in `vulnrecon/detectors/`
2. Inherit from `BaseDetector`
3. Implement `detect()` method
4. Register in `scanner.py`

Example:

```python
from vulnrecon.detectors.base import BaseDetector

class MyDetector(BaseDetector):
    def detect(self, code_path, dependencies):
        findings = []
        # Your detection logic here
        return findings
```

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Disclaimer

This tool is provided for educational and authorized security testing purposes only. Users are responsible for ensuring they have proper authorization before scanning any systems. The authors are not responsible for misuse or damage caused by this tool.

## Support

For questions or issues:
- Open an issue on GitHub
- Email: security@vulnrecon.example.com

## Roadmap

- [ ] Add more vulnerability detectors
- [ ] Implement dynamic analysis capabilities
- [ ] Add exploit difficulty scoring
- [ ] Integration with MITRE ATT&CK framework
- [ ] CI/CD pipeline integration
- [ ] Real-time monitoring mode
- [ ] API endpoint for integration
