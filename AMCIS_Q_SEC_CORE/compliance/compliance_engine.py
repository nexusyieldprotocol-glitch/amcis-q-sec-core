"""
Compliance Engine
=================

Maps security controls to compliance frameworks:
- NIST 800-53
- ISO 27001
- SOC 2
- PCI DSS
- GDPR
"""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog


class Framework(Enum):
    NIST_800_53 = "nist_800_53"
    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    HIPAA = "hipaa"


class ControlStatus(Enum):
    COMPLIANT = auto()
    NON_COMPLIANT = auto()
    PARTIAL = auto()
    NOT_APPLICABLE = auto()


@dataclass
class Control:
    """Compliance control."""
    control_id: str
    framework: Framework
    description: str
    requirements: List[str]
    amcis_modules: List[str]
    status: ControlStatus = ControlStatus.NON_COMPLIANT
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "framework": self.framework.value,
            "description": self.description,
            "status": self.status.name,
            "amcis_modules": self.amcis_modules,
            "evidence_count": len(self.evidence)
        }


class ComplianceEngine:
    """
    AMCIS Compliance Engine
    =======================
    
    Maps AMCIS security controls to compliance frameworks.
    """
    
    # Control mappings
    CONTROL_MAPPINGS: Dict[Framework, List[Control]] = {
        Framework.NIST_800_53: [
            Control("AC-2", Framework.NIST_800_53, 
                   "Account Management", 
                   ["Automated system account management"],
                   ["trust_engine", "key_manager"]),
            Control("AU-6", Framework.NIST_800_53,
                   "Audit Review",
                   ["Automated audit review"],
                   ["anomaly_engine", "merkle_log"]),
            Control("IR-4", Framework.NIST_800_53,
                   "Incident Handling",
                   ["Incident response capabilities"],
                   ["response_engine", "forensics"]),
            Control("SC-7", Framework.NIST_800_53,
                   "Boundary Protection",
                   ["Network boundary protection"],
                   ["microsegmentation", "firewall"]),
            Control("SI-7", Framework.NIST_800_53,
                   "Software Integrity",
                   ["Software integrity verification"],
                   ["integrity_monitor", "file_integrity"]),
        ],
        Framework.ISO_27001: [
            Control("A.9.4.1", Framework.ISO_27001,
                   "Information Access Restriction",
                   ["Restrict access to information"],
                   ["trust_engine", "microsegmentation"]),
            Control("A.12.4.1", Framework.ISO_27001,
                   "Event Logging",
                   ["Log user activities and events"],
                   ["merkle_log", "forensics"]),
            Control("A.16.1.1", Framework.ISO_27001,
                   "Incident Management Procedures",
                   ["Establish incident management procedures"],
                   ["response_engine"]),
        ],
        Framework.SOC_2: [
            Control("CC6.1", Framework.SOC_2,
                   "Logical Access Security",
                   ["Logical access to system components"],
                   ["trust_engine", "key_manager"]),
            Control("CC7.1", Framework.SOC_2,
                   "Security Operations Monitoring",
                   ["Monitor system components for anomalies"],
                   ["anomaly_engine", "process_graph"]),
        ],
        Framework.PCI_DSS: [
            Control("Req 10.1", Framework.PCI_DSS,
                   "Audit Trails",
                   ["Implement audit trails"],
                   ["merkle_log", "forensics"]),
            Control("Req 11.4", Framework.PCI_DSS,
                   "Intrusion Detection",
                   ["Use intrusion detection systems"],
                   ["anomaly_engine", "honeypot"]),
        ],
        Framework.GDPR: [
            Control("Art. 32", Framework.GDPR,
                   "Security of Processing",
                   ["Appropriate security measures"],
                   ["crypto", "secrets_manager"]),
        ],
    }
    
    def __init__(self) -> None:
        self.logger = structlog.get_logger("amcis.compliance")
        self._controls: Dict[str, Control] = {}
        self._load_controls()
        
        self.logger.info("compliance_engine_initialized")
    
    def _load_controls(self) -> None:
        """Load control mappings."""
        for framework, controls in self.CONTROL_MAPPINGS.items():
            for control in controls:
                key = f"{framework.value}:{control.control_id}"
                self._controls[key] = control
    
    def assess_control(self, control_id: str, framework: Framework,
                      evidence: List[str]) -> ControlStatus:
        """Assess compliance status of a control."""
        key = f"{framework.value}:{control_id}"
        control = self._controls.get(key)
        
        if not control:
            return ControlStatus.NOT_APPLICABLE
        
        control.evidence = evidence
        
        # Simple assessment logic
        if len(evidence) >= len(control.requirements):
            control.status = ControlStatus.COMPLIANT
        elif evidence:
            control.status = ControlStatus.PARTIAL
        else:
            control.status = ControlStatus.NON_COMPLIANT
        
        return control.status
    
    def get_framework_status(self, framework: Framework) -> Dict[str, Any]:
        """Get compliance status for entire framework."""
        controls = [c for c in self._controls.values() if c.framework == framework]
        
        total = len(controls)
        compliant = sum(1 for c in controls if c.status == ControlStatus.COMPLIANT)
        partial = sum(1 for c in controls if c.status == ControlStatus.PARTIAL)
        non_compliant = sum(1 for c in controls if c.status == ControlStatus.NON_COMPLIANT)
        
        score = (compliant + (partial * 0.5)) / total * 100 if total > 0 else 0
        
        return {
            "framework": framework.value,
            "score": round(score, 2),
            "total_controls": total,
            "compliant": compliant,
            "partial": partial,
            "non_compliant": non_compliant,
            "controls": [c.to_dict() for c in controls]
        }
    
    def get_all_frameworks_status(self) -> Dict[str, Any]:
        """Get status for all frameworks."""
        return {
            framework.value: self.get_framework_status(framework)
            for framework in Framework
        }
    
    def get_gap_analysis(self, framework: Framework) -> List[Dict[str, Any]]:
        """Identify compliance gaps."""
        controls = [c for c in self._controls.values() if c.framework == framework]
        gaps = []
        
        for control in controls:
            if control.status != ControlStatus.COMPLIANT:
                gaps.append({
                    "control_id": control.control_id,
                    "description": control.description,
                    "status": control.status.name,
                    "recommendation": f"Implement AMCIS modules: {', '.join(control.amcis_modules)}"
                })
        
        return gaps
