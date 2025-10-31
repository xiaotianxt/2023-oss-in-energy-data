#!/usr/bin/env python3
"""
Debug script to test OSV API requests and fix the 400 error.
"""

import requests
import json


def test_osv_api():
    """Test OSV API with different request formats."""
    print("🔍 Debugging OSV API 400 Error")
    print("=" * 50)
    
    url = "https://api.osv.dev/v1/query"
    
    # Test cases with different ecosystems and formats
    test_cases = [
        # Correct format
        {
            "name": "PyYAML with PyPI ecosystem",
            "query": {
                "package": {
                    "name": "PyYAML",
                    "ecosystem": "PyPI"  # Capital P
                }
            }
        },
        {
            "name": "pyyaml with PyPI ecosystem", 
            "query": {
                "package": {
                    "name": "pyyaml",
                    "ecosystem": "PyPI"
                }
            }
        },
        # Wrong format (what was causing 400)
        {
            "name": "PyYAML with pypi ecosystem (lowercase)",
            "query": {
                "package": {
                    "name": "PyYAML", 
                    "ecosystem": "pypi"  # lowercase - this causes 400!
                }
            }
        },
        # Test with version
        {
            "name": "PyYAML with version",
            "query": {
                "package": {
                    "name": "PyYAML",
                    "ecosystem": "PyPI"
                },
                "version": "6.0"
            }
        },
        # Test other packages
        {
            "name": "requests with PyPI",
            "query": {
                "package": {
                    "name": "requests",
                    "ecosystem": "PyPI"
                }
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"Query: {json.dumps(test_case['query'], indent=2)}")
        
        try:
            response = requests.post(url, json=test_case['query'], timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                vulns = data.get('vulns', [])
                print(f"✅ SUCCESS - Found {len(vulns)} vulnerabilities")
                
                if vulns:
                    print(f"First vulnerability: {vulns[0].get('id', 'No ID')}")
            else:
                print(f"❌ FAILED - {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                    
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    print("The OSV API requires ecosystem names to be properly capitalized:")
    print("✅ Correct: 'PyPI', 'npm', 'Maven', 'Go', 'crates.io'")
    print("❌ Wrong: 'pypi', 'python', 'pip'")


def test_correct_ecosystems():
    """Test the correct ecosystem names."""
    print("\n🔧 Testing Correct Ecosystem Names")
    print("-" * 40)
    
    url = "https://api.osv.dev/v1/query"
    
    # Correct ecosystem mappings
    ecosystem_mappings = {
        'pypi': 'PyPI',
        'python': 'PyPI', 
        'npm': 'npm',
        'maven': 'Maven',
        'go': 'Go',
        'crates': 'crates.io'
    }
    
    test_packages = [
        ('PyYAML', 'pypi'),
        ('requests', 'pypi'),
        ('numpy', 'pypi'),
        ('react', 'npm'),
    ]
    
    for package_name, old_ecosystem in test_packages:
        correct_ecosystem = ecosystem_mappings.get(old_ecosystem, old_ecosystem)
        
        print(f"\n📦 Package: {package_name}")
        print(f"   Old ecosystem: {old_ecosystem}")
        print(f"   Correct ecosystem: {correct_ecosystem}")
        
        query = {
            "package": {
                "name": package_name,
                "ecosystem": correct_ecosystem
            }
        }
        
        try:
            response = requests.post(url, json=query, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                vulns = data.get('vulns', [])
                print(f"   ✅ SUCCESS - {len(vulns)} vulnerabilities found")
            else:
                print(f"   ❌ FAILED - Status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")


if __name__ == '__main__':
    test_osv_api()
    test_correct_ecosystems()
