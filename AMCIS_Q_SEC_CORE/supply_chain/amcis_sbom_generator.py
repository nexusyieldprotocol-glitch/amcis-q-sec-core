"""
AMCIS SBOM Generator
====================

Software Bill of Materials (SBOM) generation in multiple formats:
- SPDX (ISO/IEC 5962)
- CycloneDX
- SWID

Features:
- Multi-format SBOM generation
- Dependency tree extraction
- Hash verification
- License identification

NIST Alignment: SP 800-161 (Supply Chain Risk Management), NTIA SBOM
"""

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog


class SBOMFormat(Enum):
    """SBOM output formats."""
    SPDX_JSON = "spdx-json"
    SPDX_TAG_VALUE = "spdx-tv"
    CYCLONE_DX_JSON = "cyclonedx-json"
    CYCLONE_DX_XML = "cyclonedx-xml"
    SWID = "swid"


class ComponentType(Enum):
    """Component types."""
    APPLICATION = "application"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    CONTAINER = "container"
    OPERATING_SYSTEM = "operating-system"
    DEVICE = "device"
    FIRMWARE = "firmware"
    FILE = "file"


@dataclass
class Hash:
    """File hash."""
    algorithm: str
    value: str


@dataclass
class License:
    """License information."""
    id: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Component:
    """SBOM component."""
    name: str
    version: str
    type: ComponentType
    supplier: Optional[str] = None
    hashes: List[Hash] = field(default_factory=list)
    licenses: List[License] = field(default_factory=list)
    cpe: Optional[str] = None
    purl: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    description: Optional[str] = None
    download_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.type.value,
            "supplier": self.supplier,
            "hashes": [{"alg": h.algorithm, "value": h.value} for h in self.hashes],
            "licenses": [{"id": l.id, "name": l.name} for l in self.licenses],
            "cpe": self.cpe,
            "purl": self.purl,
            "dependencies": self.dependencies,
            "description": self.description
        }


@dataclass
class SBOM:
    """Software Bill of Materials."""
    name: str
    version: str
    created: datetime
    components: List[Component]
    creator: str
    format: SBOMFormat
    namespace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "created": self.created.isoformat(),
            "creator": self.creator,
            "format": self.format.value,
            "namespace": self.namespace,
            "component_count": len(self.components),
            "components": [c.to_dict() for c in self.components]
        }


class SBOMGenerator:
    """
    AMCIS SBOM Generator
    ====================
    
    Multi-format Software Bill of Materials generator supporting
    Python, JavaScript, Java, and generic projects.
    """
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize SBOM generator.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.sbom_generator")
        
        self.logger.info("sbom_generator_initialized")
    
    def generate_from_path(
        self,
        project_path: Path,
        format: SBOMFormat = SBOMFormat.SPDX_JSON,
        name: Optional[str] = None,
        version: str = "1.0.0"
    ) -> SBOM:
        """
        Generate SBOM from project path.
        
        Args:
            project_path: Path to project
            format: Output format
            name: Project name
            version: Project version
            
        Returns:
            Generated SBOM
        """
        name = name or project_path.name
        
        # Detect project type
        components = []
        
        if (project_path / "requirements.txt").exists() or \
           (project_path / "pyproject.toml").exists() or \
           (project_path / "setup.py").exists():
            components = self._extract_python_dependencies(project_path)
        
        elif (project_path / "package.json").exists():
            components = self._extract_npm_dependencies(project_path)
        
        elif (project_path / "pom.xml").exists() or \
             (project_path / "build.gradle").exists():
            components = self._extract_java_dependencies(project_path)
        
        elif (project_path / "Cargo.toml").exists():
            components = self._extract_rust_dependencies(project_path)
        
        elif (project_path / "go.mod").exists():
            components = self._extract_go_dependencies(project_path)
        
        else:
            components = self._scan_generic_files(project_path)
        
        sbom = SBOM(
            name=name,
            version=version,
            created=datetime.utcnow(),
            components=components,
            creator="AMCIS-SBOM-Generator-1.0",
            format=format,
            namespace=f"https://amcis.security/sbom/{name}/{version}"
        )
        
        self.logger.info(
            "sbom_generated",
            name=name,
            component_count=len(components),
            format=format.value
        )
        
        return sbom
    
    def _extract_python_dependencies(self, project_path: Path) -> List[Component]:
        """Extract Python dependencies."""
        components = []
        
        # Try pip freeze first
        try:
            result = subprocess.run(
                ["pip", "freeze"],
                capture_output=True,
                text=True,
                cwd=project_path
            )
            
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    name, version = line.split('==', 1)
                    components.append(Component(
                        name=name.strip(),
                        version=version.strip(),
                        type=ComponentType.LIBRARY,
                        purl=f"pkg:pypi/{name.strip()}@{version.strip()}"
                    ))
        except Exception as e:
            self.logger.warning("pip_freeze_failed", error=str(e))
        
        # Parse requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse requirement specifier
                        if '==' in line:
                            name, version = line.split('==', 1)
                            if not any(c.name == name.strip() for c in components):
                                components.append(Component(
                                    name=name.strip(),
                                    version=version.strip().split(';')[0],
                                    type=ComponentType.LIBRARY,
                                    purl=f"pkg:pypi/{name.strip()}@{version.strip()}"
                                ))
        
        return components
    
    def _extract_npm_dependencies(self, project_path: Path) -> List[Component]:
        """Extract npm dependencies."""
        components = []
        
        package_file = project_path / "package.json"
        if not package_file.exists():
            return components
        
        try:
            with open(package_file) as f:
                package_data = json.load(f)
            
            deps = package_data.get("dependencies", {})
            deps.update(package_data.get("devDependencies", {}))
            
            for name, version in deps.items():
                # Clean version string
                version_clean = version.lstrip('^~>=<')
                
                components.append(Component(
                    name=name,
                    version=version_clean,
                    type=ComponentType.LIBRARY,
                    purl=f"pkg:npm/{name}@{version_clean}"
                ))
        
        except Exception as e:
            self.logger.warning("npm_parse_failed", error=str(e))
        
        return components
    
    def _extract_java_dependencies(self, project_path: Path) -> List[Component]:
        """Extract Java dependencies."""
        components = []
        
        # Try Maven
        pom_file = project_path / "pom.xml"
        if pom_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(pom_file)
                root = tree.getroot()
                
                # Find dependencies
                ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
                for dep in root.findall('.//m:dependency', ns):
                    group = dep.find('m:groupId', ns)
                    artifact = dep.find('m:artifactId', ns)
                    version = dep.find('m:version', ns)
                    
                    if group is not None and artifact is not None:
                        name = f"{group.text}:{artifact.text}"
                        ver = version.text if version is not None else "unknown"
                        
                        components.append(Component(
                            name=name,
                            version=ver,
                            type=ComponentType.LIBRARY,
                            purl=f"pkg:maven/{group.text}/{artifact.text}@{ver}"
                        ))
            except Exception as e:
                self.logger.warning("maven_parse_failed", error=str(e))
        
        return components
    
    def _extract_rust_dependencies(self, project_path: Path) -> List[Component]:
        """Extract Rust dependencies."""
        components = []
        
        cargo_file = project_path / "Cargo.toml"
        if not cargo_file.exists():
            return components
        
        try:
            import tomllib
            with open(cargo_file, 'rb') as f:
                cargo_data = tomllib.load(f)
            
            deps = cargo_data.get("dependencies", {})
            for name, version in deps.items():
                if isinstance(version, str):
                    components.append(Component(
                        name=name,
                        version=version.lstrip('^'),
                        type=ComponentType.LIBRARY,
                        purl=f"pkg:cargo/{name}@{version.lstrip('^')}"
                    ))
        except Exception as e:
            self.logger.warning("cargo_parse_failed", error=str(e))
        
        return components
    
    def _extract_go_dependencies(self, project_path: Path) -> List[Component]:
        """Extract Go dependencies."""
        components = []
        
        # Try to use go list
        try:
            result = subprocess.run(
                ["go", "list", "-m", "-json", "all"],
                capture_output=True,
                text=True,
                cwd=project_path
            )
            
            # Parse JSON output (multiple JSON objects)
            for line in result.stdout.split('\n'):
                if line.strip():
                    try:
                        mod = json.loads(line)
                        components.append(Component(
                            name=mod.get("Path", "unknown"),
                            version=mod.get("Version", "unknown"),
                            type=ComponentType.LIBRARY,
                            purl=f"pkg:golang/{mod.get('Path')}@{mod.get('Version')}"
                        ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.logger.warning("go_list_failed", error=str(e))
        
        return components
    
    def _scan_generic_files(self, project_path: Path) -> List[Component]:
        """Generic file scanning for unknown project types."""
        components = []
        
        # Find binary files
        for ext in ['.so', '.dll', '.dylib', '.exe']:
            for file_path in project_path.rglob(f"*{ext}"):
                try:
                    hashes = self._hash_file(file_path)
                    components.append(Component(
                        name=file_path.name,
                        version="unknown",
                        type=ComponentType.LIBRARY,
                        hashes=hashes
                    ))
                except Exception:
                    continue
        
        return components
    
    def _hash_file(self, file_path: Path) -> List[Hash]:
        """Calculate file hashes."""
        hashes = []
        
        try:
            with open(file_path, 'rb') as f:
                sha256_hash = hashlib.sha256()
                sha1_hash = hashlib.sha1()
                md5_hash = hashlib.md5()
                
                while chunk := f.read(8192):
                    sha256_hash.update(chunk)
                    sha1_hash.update(chunk)
                    md5_hash.update(chunk)
                
                hashes.append(Hash("SHA-256", sha256_hash.hexdigest()))
                hashes.append(Hash("SHA-1", sha1_hash.hexdigest()))
                hashes.append(Hash("MD5", md5_hash.hexdigest()))
        except Exception:
            pass
        
        return hashes
    
    def export_sbom(
        self,
        sbom: SBOM,
        output_path: Path,
        format: Optional[SBOMFormat] = None
    ) -> Path:
        """
        Export SBOM to file.
        
        Args:
            sbom: SBOM to export
            output_path: Output file path
            format: Export format (defaults to SBOM format)
            
        Returns:
            Output path
        """
        format = format or sbom.format
        
        if format == SBOMFormat.SPDX_JSON:
            content = self._export_spdx_json(sbom)
        elif format == SBOMFormat.CYCLONE_DX_JSON:
            content = self._export_cyclonedx_json(sbom)
        else:
            # Default to SPDX JSON
            content = self._export_spdx_json(sbom)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)
        
        self.logger.info("sbom_exported", path=str(output_path), format=format.value)
        
        return output_path
    
    def _export_spdx_json(self, sbom: SBOM) -> str:
        """Export as SPDX JSON."""
        spdx = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": sbom.name,
            "documentNamespace": sbom.namespace,
            "creationInfo": {
                "created": sbom.created.isoformat(),
                "creators": [f"Tool: {sbom.creator}"]
            },
            "packages": []
        }
        
        for i, comp in enumerate(sbom.components):
            package = {
                "SPDXID": f"SPDXRef-Package-{i}",
                "name": comp.name,
                "versionInfo": comp.version,
                "downloadLocation": comp.download_url or "NOASSERTION",
                "filesAnalyzed": False,
                "checksums": [{"algorithm": h.algorithm, "checksumValue": h.value} for h in comp.hashes],
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": comp.licenses[0].id if comp.licenses else "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": []
            }
            
            if comp.purl:
                package["externalRefs"].append({
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": comp.purl
                })
            
            spdx["packages"].append(package)
        
        return json.dumps(spdx, indent=2)
    
    def _export_cyclonedx_json(self, sbom: SBOM) -> str:
        """Export as CycloneDX JSON."""
        cyclonedx = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{hashlib.sha256(sbom.name.encode()).hexdigest()[:32]}",
            "version": 1,
            "metadata": {
                "timestamp": sbom.created.isoformat(),
                "tools": [{"name": sbom.creator}]
            },
            "components": []
        }
        
        for comp in sbom.components:
            component = {
                "type": comp.type.value,
                "name": comp.name,
                "version": comp.version,
                "purl": comp.purl,
                "hashes": [{"alg": h.algorithm, "content": h.value} for h in comp.hashes],
                "licenses": [{"license": {"id": l.id}} for l in comp.licenses if l.id]
            }
            cyclonedx["components"].append(component)
        
        return json.dumps(cyclonedx, indent=2)
