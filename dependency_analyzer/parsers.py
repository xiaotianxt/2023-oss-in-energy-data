"""Parsers for different dependency file formats."""

import re
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

try:
    import toml
except ImportError:
    toml = None

logger = logging.getLogger(__name__)


class DependencyParser:
    """Base class for dependency parsers."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Parse dependency file content and return list of dependencies."""
        raise NotImplementedError


class PipRequirementsParser(DependencyParser):
    """Parser for pip requirements.txt files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        dependencies = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Skip -e (editable) installs and other pip options
            if line.startswith('-'):
                continue
            
            # Parse package name and version
            dependency = self._parse_requirement_line(line)
            if dependency:
                dependencies.append(dependency)
        
        return dependencies
    
    def _parse_requirement_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single requirement line."""
        # Remove inline comments
        line = line.split('#')[0].strip()
        
        # Common version specifiers
        version_pattern = r'^([a-zA-Z0-9\-_.]+)([><=!~]+.*)?$'
        match = re.match(version_pattern, line)
        
        if match:
            name = match.group(1)
            version_spec = match.group(2) if match.group(2) else ""
            
            return {
                'name': name,
                'version': version_spec,
                'type': 'runtime',
                'ecosystem': 'pypi'
            }
        
        return None


class PackageJsonParser(DependencyParser):
    """Parser for package.json files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        dependencies = []
        
        try:
            data = json.loads(content)
            
            # Parse runtime dependencies
            if 'dependencies' in data:
                for name, version in data['dependencies'].items():
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'runtime',
                        'ecosystem': 'npm'
                    })
            
            # Parse dev dependencies
            if 'devDependencies' in data:
                for name, version in data['devDependencies'].items():
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'dev',
                        'ecosystem': 'npm'
                    })
            
            # Parse peer dependencies
            if 'peerDependencies' in data:
                for name, version in data['peerDependencies'].items():
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'peer',
                        'ecosystem': 'npm'
                    })
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json: {e}")
        
        return dependencies


class PyProjectTomlParser(DependencyParser):
    """Parser for pyproject.toml files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        if not toml:
            logger.warning("toml package not available, skipping pyproject.toml parsing")
            return []
        
        dependencies = []
        
        try:
            data = toml.loads(content)
            
            # Poetry dependencies
            if 'tool' in data and 'poetry' in data['tool']:
                poetry_data = data['tool']['poetry']
                
                if 'dependencies' in poetry_data:
                    for name, version_spec in poetry_data['dependencies'].items():
                        if name == 'python':  # Skip Python version requirement
                            continue
                        
                        version = version_spec if isinstance(version_spec, str) else str(version_spec)
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'type': 'runtime',
                            'ecosystem': 'pypi'
                        })
                
                if 'dev-dependencies' in poetry_data:
                    for name, version_spec in poetry_data['dev-dependencies'].items():
                        version = version_spec if isinstance(version_spec, str) else str(version_spec)
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'type': 'dev',
                            'ecosystem': 'pypi'
                        })
            
            # PEP 621 dependencies
            if 'project' in data:
                project_data = data['project']
                
                if 'dependencies' in project_data:
                    for dep in project_data['dependencies']:
                        parsed = self._parse_pep621_dependency(dep)
                        if parsed:
                            dependencies.append(parsed)
                
                if 'optional-dependencies' in project_data:
                    for group, deps in project_data['optional-dependencies'].items():
                        for dep in deps:
                            parsed = self._parse_pep621_dependency(dep)
                            if parsed:
                                parsed['type'] = f'optional-{group}'
                                dependencies.append(parsed)
        
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
        
        return dependencies
    
    def _parse_pep621_dependency(self, dep_string: str) -> Optional[Dict[str, Any]]:
        """Parse PEP 621 dependency string."""
        # Simple regex for package name and version
        match = re.match(r'^([a-zA-Z0-9\-_.]+)([><=!~].*)?', dep_string)
        if match:
            return {
                'name': match.group(1),
                'version': match.group(2) if match.group(2) else "",
                'type': 'runtime',
                'ecosystem': 'pypi'
            }
        return None


class PomXmlParser(DependencyParser):
    """Parser for Maven pom.xml files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        dependencies = []
        
        try:
            root = ET.fromstring(content)
            
            # Handle XML namespaces
            namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            if root.tag.startswith('{'):
                # Extract namespace from root tag
                namespace = root.tag[1:root.tag.index('}')]
                namespaces['maven'] = namespace
            
            # Find dependencies
            deps_elements = root.findall('.//maven:dependencies/maven:dependency', namespaces)
            if not deps_elements:
                # Try without namespace
                deps_elements = root.findall('.//dependencies/dependency')
            
            for dep in deps_elements:
                group_id = self._get_element_text(dep, 'groupId', namespaces)
                artifact_id = self._get_element_text(dep, 'artifactId', namespaces)
                version = self._get_element_text(dep, 'version', namespaces)
                scope = self._get_element_text(dep, 'scope', namespaces) or 'compile'
                
                if group_id and artifact_id:
                    dependencies.append({
                        'name': f"{group_id}:{artifact_id}",
                        'version': version or "",
                        'type': scope,
                        'ecosystem': 'maven'
                    })
        
        except ET.ParseError as e:
            logger.error(f"Error parsing pom.xml: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing pom.xml: {e}")
        
        return dependencies
    
    def _get_element_text(self, parent, tag_name, namespaces):
        """Get text content of an XML element."""
        element = parent.find(f'maven:{tag_name}', namespaces)
        if element is None:
            element = parent.find(tag_name)
        return element.text if element is not None else None


class CargoTomlParser(DependencyParser):
    """Parser for Cargo.toml files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        if not toml:
            logger.warning("toml package not available, skipping Cargo.toml parsing")
            return []
        
        dependencies = []
        
        try:
            data = toml.loads(content)
            
            # Runtime dependencies
            if 'dependencies' in data:
                for name, version_spec in data['dependencies'].items():
                    version = version_spec if isinstance(version_spec, str) else str(version_spec.get('version', ''))
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'runtime',
                        'ecosystem': 'crates'
                    })
            
            # Dev dependencies
            if 'dev-dependencies' in data:
                for name, version_spec in data['dev-dependencies'].items():
                    version = version_spec if isinstance(version_spec, str) else str(version_spec.get('version', ''))
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'dev',
                        'ecosystem': 'crates'
                    })
        
        except Exception as e:
            logger.error(f"Error parsing Cargo.toml: {e}")
        
        return dependencies


class GoModParser(DependencyParser):
    """Parser for go.mod files."""
    
    def parse(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        dependencies = []
        
        lines = content.split('\n')
        in_require_block = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('require ('):
                in_require_block = True
                continue
            elif line == ')' and in_require_block:
                in_require_block = False
                continue
            elif line.startswith('require ') and not in_require_block:
                # Single require statement
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    version = parts[2]
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'runtime',
                        'ecosystem': 'go'
                    })
            elif in_require_block and line and not line.startswith('//'):
                # Dependency in require block
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    version = parts[1]
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'type': 'runtime',
                        'ecosystem': 'go'
                    })
        
        return dependencies


class DependencyParserFactory:
    """Factory for creating appropriate dependency parsers."""
    
    _parsers = {
        'pip_requirements': PipRequirementsParser,
        'pip_requirements_dev': PipRequirementsParser,
        'pip_requirements_test': PipRequirementsParser,
        'python_pyproject': PyProjectTomlParser,
        'npm': PackageJsonParser,
        'maven': PomXmlParser,
        'cargo': CargoTomlParser,
        'go_mod': GoModParser,
    }
    
    @classmethod
    def get_parser(cls, file_type: str) -> Optional[DependencyParser]:
        """Get appropriate parser for file type."""
        parser_class = cls._parsers.get(file_type)
        return parser_class() if parser_class else None
    
    @classmethod
    def parse_dependencies(cls, content: str, file_type: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Parse dependencies using appropriate parser."""
        parser = cls.get_parser(file_type)
        if parser:
            return parser.parse(content, file_path)
        else:
            logger.warning(f"No parser available for file type: {file_type}")
            return []

