"""
Evidence Collector
==================

Collects and preserves digital evidence for forensic analysis.
"""

import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class EvidenceItem:
    """Single evidence item."""
    item_id: str
    item_type: str  # 'file', 'memory', 'network', 'log'
    source_path: str
    collected_at: float
    hashes: Dict[str, str]  # algorithm -> hash
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "type": self.item_type,
            "source": self.source_path,
            "collected_at": datetime.fromtimestamp(self.collected_at).isoformat(),
            "hashes": self.hashes
        }


class EvidenceCollector:
    """
    AMCIS Evidence Collector
    ========================
    
    Collects and preserves forensic evidence with chain of custody.
    """
    
    def __init__(self, case_id: str, storage_path: Optional[Path] = None) -> None:
        self.case_id = case_id
        self.storage_path = storage_path or Path(f"/var/lib/amcis/evidence/{case_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger("amcis.evidence")
        
        self._evidence: List[EvidenceItem] = []
        self._chain_of_custody: List[Dict[str, Any]] = []
        
        self.logger.info("evidence_collector_created", case_id=case_id)
    
    def collect_file(self, file_path: Path, description: str = "") -> Optional[EvidenceItem]:
        """Collect file as evidence."""
        if not file_path.exists():
            return None
        
        # Calculate hashes
        hashes = self._calculate_hashes(file_path)
        
        # Copy to evidence storage
        dest = self.storage_path / "files" / file_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        
        # Create evidence item
        item = EvidenceItem(
            item_id=f"EVID-{len(self._evidence):04d}",
            item_type="file",
            source_path=str(file_path),
            collected_at=time.time(),
            hashes=hashes,
            metadata={"description": description}
        )
        
        self._evidence.append(item)
        self._add_custody_record(item, "collected")
        
        self.logger.info("evidence_collected", item_id=item.item_id, file=file_path.name)
        return item
    
    def _calculate_hashes(self, file_path: Path) -> Dict[str, str]:
        """Calculate file hashes."""
        hashes = {}
        
        with open(file_path, 'rb') as f:
            data = f.read()
            hashes["md5"] = hashlib.md5(data).hexdigest()
            hashes["sha1"] = hashlib.sha1(data).hexdigest()
            hashes["sha256"] = hashlib.sha256(data).hexdigest()
        
        return hashes
    
    def _add_custody_record(self, item: EvidenceItem, action: str) -> None:
        """Add chain of custody record."""
        self._chain_of_custody.append({
            "timestamp": item.collected_at,
            "item_id": item.item_id,
            "action": action,
            "hashes": item.hashes.copy()
        })
    
    def create_evidence_package(self) -> Path:
        """Create packaged evidence for transfer."""
        package_path = self.storage_path / f"{self.case_id}_evidence.zip"
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add evidence files
            files_dir = self.storage_path / "files"
            if files_dir.exists():
                for file in files_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, f"files/{file.name}")
            
            # Add manifest
            manifest = {
                "case_id": self.case_id,
                "created_at": datetime.now().isoformat(),
                "evidence_count": len(self._evidence),
                "items": [e.to_dict() for e in self._evidence],
                "chain_of_custody": self._chain_of_custody
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        self.logger.info("evidence_package_created", path=str(package_path))
        return package_path
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get evidence statistics."""
        by_type = {}
        for item in self._evidence:
            by_type[item.item_type] = by_type.get(item.item_type, 0) + 1
        
        return {
            "case_id": self.case_id,
            "total_evidence": len(self._evidence),
            "by_type": by_type,
            "custody_records": len(self._chain_of_custody)
        }


# Add missing import
import time
