"""
NIST Cybersecurity Framework 2.0 Implementation
===============================================

Comprehensive mapping and automated assessment for NIST CSF 2.0:
- GOVERN (GV): Organizational context and risk management
- IDENTIFY (ID): Asset and risk understanding  
- PROTECT (PR): Safeguard implementation
- DETECT (DE): Anomaly and event detection
- RESPOND (RS): Incident response capabilities
- RECOVER (RC): Recovery and resilience

Features:
- Automated control assessment
- Evidence collection
- Gap analysis
- Remediation recommendations
- Audit-ready reporting

NIST Reference: https://www.nist.gov/cyberframework
Version: CSF 2.0 (February 2024)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple

import structlog


logger = structlog.get_logger("amcis.compliance.nist_csf")


class CSFFunction(Enum):
    """NIST CSF 2.0 Core Functions."""
    GOVERN = "GV"      # Organizational context and risk management
    IDENTIFY = "ID"    # Asset management and risk assessment
    PROTECT = "PR"     # Protective safeguards
    DETECT = "DE"      # Anomaly detection
    RESPOND = "RS"     # Incident response
    RECOVER = "RC"     # Recovery capabilities


class ImplementationStatus(Enum):
    """Control implementation status."""
    NOT_IMPLEMENTED = auto()
    PARTIALLY_IMPLEMENTED = auto()
    IMPLEMENTED = auto()
    EXCEEDS_REQUIREMENTS = auto()
    NOT_APPLICABLE = auto()


class RiskLevel(Enum):
    """Risk severity levels."""
    CRITICAL = 4
    HIGH = 3
    MODERATE = 2
    LOW = 1
    MINIMAL = 0


@dataclass(frozen=True)
class ControlEvidence:
    """Evidence artifact for control implementation."""
    evidence_id: str
    control_id: str
    evidence_type: str  # "policy", "procedure", "configuration", "log", "test"
    source: str
    timestamp: datetime
    description: str
    data_hash: str  # Integrity verification
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CSFControl:
    """NIST CSF 2.0 Control definition."""
    control_id: str
    function: CSFFunction
    category: str
    subcategory: str
    description: str
    implementation_examples: List[str]
    amcis_modules: List[str]
    
    # Assessment state
    status: ImplementationStatus = ImplementationStatus.NOT_IMPLEMENTED
    evidence: List[ControlEvidence] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    remediation: Optional[str] = None
    score: float = 0.0  # 0.0 to 1.0
    priority: RiskLevel = RiskLevel.MODERATE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "control_id": self.control_id,
            "function": self.function.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "status": self.status.name,
            "score": round(self.score, 2),
            "priority": self.priority.name,
            "evidence_count": len(self.evidence),
            "gaps": self.gaps,
            "remediation": self.remediation,
            "amcis_modules": self.amcis_modules
        }


@dataclass
class CSFAssessment:
    """Complete NIST CSF assessment results."""
    version: str = "2.0"
    assessment_date: datetime = field(default_factory=datetime.utcnow)
    organization: str = "AMCIS"
    assessor: str = "Automated System"
    
    overall_score: float = 0.0
    function_scores: Dict[CSFFunction, float] = field(default_factory=dict)
    controls: List[CSFControl] = field(default_factory=list)
    
    critical_gaps: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metadata": {
                "version": self.version,
                "date": self.assessment_date.isoformat(),
                "organization": self.organization,
                "assessor": self.assessor
            },
            "summary": {
                "overall_score": round(self.overall_score, 2),
                "total_controls": len(self.controls),
                "implemented": sum(1 for c in self.controls 
                                 if c.status == ImplementationStatus.IMPLEMENTED),
                "partial": sum(1 for c in self.controls 
                              if c.status == ImplementationStatus.PARTIALLY_IMPLEMENTED),
                "not_implemented": sum(1 for c in self.controls 
                                      if c.status == ImplementationStatus.NOT_IMPLEMENTED),
                "exceeds": sum(1 for c in self.controls 
                              if c.status == ImplementationStatus.EXCEEDS_REQUIREMENTS)
            },
            "function_scores": {
                func.name: round(score, 2)
                for func, score in self.function_scores.items()
            },
            "critical_gaps": self.critical_gaps,
            "recommendations": self.recommendations
        }


# =============================================================================
# NIST CSF 2.0 CONTROL DEFINITIONS
# =============================================================================

CSF_CONTROLS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # GOVERN Function (GV)
    # =========================================================================
    "GV.OC": {
        "function": CSFFunction.GOVERN,
        "category": "Organizational Context",
        "description": "The organizational mission, objectives, and activities are understood;"
                      " cybersecurity risks are understood in that context.",
        "examples": [
            "Document organizational mission and objectives",
            "Establish cybersecurity strategy aligned with mission",
            "Define risk appetite and tolerance"
        ],
        "modules": ["policy_engine", "risk_portfolio"],
        "priority": RiskLevel.HIGH
    },
    "GV.RM": {
        "function": CSFFunction.GOVERN,
        "category": "Risk Management Strategy",
        "description": "Risk management strategy is established and communicated."
                      " Risk appetite and tolerance are understood.",
        "examples": [
            "Establish risk management framework",
            "Define risk assessment methodology",
            "Implement risk monitoring program"
        ],
        "modules": ["risk_portfolio", "compliance_engine"],
        "priority": RiskLevel.CRITICAL
    },
    "GV.RR": {
        "function": CSFFunction.GOVERN,
        "category": "Roles and Responsibilities",
        "description": "Cybersecurity roles, responsibilities, and authorities are established"
                      " and communicated throughout the organization.",
        "examples": [
            "Define cybersecurity organizational chart",
            "Assign system and data ownership",
            "Establish RACI matrix for security functions"
        ],
        "modules": ["trust_engine", "policy_engine"],
        "priority": RiskLevel.HIGH
    },
    "GV.PO": {
        "function": CSFFunction.GOVERN,
        "category": "Policy",
        "description": "Cybersecurity policy is established, communicated, and enforced."
                      " Policy is reviewed and updated regularly.",
        "examples": [
            "Develop comprehensive security policy",
            "Implement policy management system",
            "Conduct regular policy reviews"
        ],
        "modules": ["policy_engine", "compliance_engine"],
        "priority": RiskLevel.HIGH
    },
    "GV.OV": {
        "function": CSFFunction.GOVERN,
        "category": "Oversight",
        "description": "Cybersecurity risk management strategy is reviewed and adjusted"
                      " to ensure objectives are achieved.",
        "examples": [
            "Establish security metrics and KPIs",
            "Conduct regular risk assessments",
            "Implement continuous monitoring"
        ],
        "modules": ["anomaly_engine", "security_monitor"],
        "priority": RiskLevel.HIGH
    },
    "GV.SC": {
        "function": CSFFunction.GOVERN,
        "category": "Supply Chain Risk Management",
        "description": "Cybersecurity supply chain risk management processes are identified,"
                      " established, and communicated.",
        "examples": [
            "Implement vendor risk assessment",
            "Establish SBOM requirements",
            "Monitor supply chain threats"
        ],
        "modules": ["supply_chain", "threat_intel"],
        "priority": RiskLevel.HIGH
    },
    
    # =========================================================================
    # IDENTIFY Function (ID)
    # =========================================================================
    "ID.AM": {
        "function": CSFFunction.IDENTIFY,
        "category": "Asset Management",
        "description": "Assets are inventoried and managed throughout their lifecycle."
                      " Critical assets are identified and prioritized.",
        "examples": [
            "Maintain asset inventory",
            "Asset classification and labeling",
            "Asset lifecycle management"
        ],
        "modules": ["integrity_monitor", "file_integrity"],
        "priority": RiskLevel.CRITICAL
    },
    "ID.RA": {
        "function": CSFFunction.IDENTIFY,
        "category": "Risk Assessment",
        "description": "Cybersecurity risks are identified, analyzed, and prioritized."
                      " Risk response is planned.",
        "examples": [
            "Conduct threat assessments",
            "Vulnerability scanning and analysis",
            "Risk scoring and prioritization"
        ],
        "modules": ["anomaly_engine", "threat_intel", "risk_portfolio"],
        "priority": RiskLevel.CRITICAL
    },
    "ID.IM": {
        "function": CSFFunction.IDENTIFY,
        "category": "Improvement",
        "description": "Improvements to organizational cybersecurity are identified,"
                      " prioritized, and implemented.",
        "examples": [
            "Security metrics analysis",
            "Lessons learned process",
            "Continuous improvement program"
        ],
        "modules": ["compliance_engine", "security_monitor"],
        "priority": RiskLevel.MODERATE
    },
    
    # =========================================================================
    # PROTECT Function (PR)
    # =========================================================================
    "PR.AA": {
        "function": CSFFunction.PROTECT,
        "category": "Identity Management and Access Control",
        "description": "Identities and credentials are managed and access is authenticated,"
                      " authorized, and audited.",
        "examples": [
            "Multi-factor authentication",
            "Privileged access management",
            "Regular access reviews"
        ],
        "modules": ["trust_engine", "key_manager"],
        "priority": RiskLevel.CRITICAL
    },
    "PR.AT": {
        "function": CSFFunction.PROTECT,
        "category": "Awareness and Training",
        "description": "Personnel are provided with cybersecurity awareness and training."
                      " Training is evaluated and updated.",
        "examples": [
            "Security awareness program",
            "Role-based training",
            "Phishing simulations"
        ],
        "modules": ["compliance_engine"],
        "priority": RiskLevel.MODERATE
    },
    "PR.DS": {
        "function": CSFFunction.PROTECT,
        "category": "Data Security",
        "description": "Data is managed and protected consistent with risk strategy."
                      " Data confidentiality, integrity, and availability are maintained.",
        "examples": [
            "Data classification",
            "Encryption at rest and in transit",
            "Data loss prevention"
        ],
        "modules": ["amcis_encrypt", "hybrid_pqc", "dlp_engine"],
        "priority": RiskLevel.CRITICAL
    },
    "PR.PS": {
        "function": CSFFunction.PROTECT,
        "category": "Platform Security",
        "description": "Hardware, software, and services are configured and maintained"
                      " consistent with risk strategy.",
        "examples": [
            "Secure configuration baselines",
            "Patch management",
            "Endpoint protection"
        ],
        "modules": ["edr", "container_sec", "cloud_sec"],
        "priority": RiskLevel.HIGH
    },
    "PR.IR": {
        "function": CSFFunction.PROTECT,
        "category": "Technology Infrastructure Resilience",
        "description": "Technology infrastructure is protected from cybersecurity threats."
                      " Resilience is designed and implemented.",
        "examples": [
            "Network segmentation",
            "DDoS protection",
            "Backup and recovery"
        ],
        "modules": ["network", "microsegmentation", "resilience"],
        "priority": RiskLevel.HIGH
    },
    
    # =========================================================================
    # DETECT Function (DE)
    # =========================================================================
    "DE.AE": {
        "function": CSFFunction.DETECT,
        "category": "Anomalies and Events",
        "description": "Anomalies, indicators of compromise, and other potentially"
                      " adverse events are detected and analyzed.",
        "examples": [
            "Security event monitoring",
            "Anomaly detection",
            "Threat hunting"
        ],
        "modules": ["anomaly_engine", "threat_detection"],
        "priority": RiskLevel.CRITICAL
    },
    "DE.CM": {
        "function": CSFFunction.DETECT,
        "category": "Continuous Monitoring",
        "description": "Assets are monitored to find anomalies, indicators of compromise,"
                      " and other adverse events.",
        "examples": [
            "Continuous vulnerability scanning",
            "Security control monitoring",
            "Asset tracking"
        ],
        "modules": ["security_monitor", "metrics_collector"],
        "priority": RiskLevel.CRITICAL
    },
    "DE.IM": {
        "function": CSFFunction.DETECT,
        "category": "Improvement",
        "description": "Detection capabilities are continuously improved through"
                      " lessons learned and threat intelligence.",
        "examples": [
            "Detection rule updates",
            "Threat intelligence integration",
            "Security metrics analysis"
        ],
        "modules": ["threat_intel", "compliance_engine"],
        "priority": RiskLevel.MODERATE
    },
    
    # =========================================================================
    # RESPOND Function (RS)
    # =========================================================================
    "RS.MA": {
        "function": CSFFunction.RESPOND,
        "category": "Response Management",
        "description": "Incidents are contained, eradicated, and recovered from."
                      " Response processes are executed.",
        "examples": [
            "Incident response plan",
            "Automated containment",
            "Forensic investigation"
        ],
        "modules": ["response_engine", "soar", "forensics"],
        "priority": RiskLevel.CRITICAL
    },
    "RS.AN": {
        "function": CSFFunction.RESPOND,
        "category": "Analysis",
        "description": "Incidents are analyzed to ensure effective response and"
                      " support forensics and recovery activities.",
        "examples": [
            "Incident timeline creation",
            "Root cause analysis",
            "Impact assessment"
        ],
        "modules": ["forensics", "timeline"],
        "priority": RiskLevel.HIGH
    },
    "RS.CO": {
        "function": CSFFunction.RESPOND,
        "category": "Containment",
        "description": "Activities are performed to prevent or reduce the impact"
                      " of incidents and prevent spread.",
        "examples": [
            "Network isolation",
            "Account lockdown",
            "Malware quarantine"
        ],
        "modules": ["response_engine", "microsegmentation"],
        "priority": RiskLevel.CRITICAL
    },
    "RS.MI": {
        "function": CSFFunction.RESPOND,
        "category": "Mitigation",
        "description": "Activities are performed to resolve incidents and restore"
                      " affected systems and assets.",
        "examples": [
            "Vulnerability remediation",
            "Patch deployment",
            "System restoration"
        ],
        "modules": ["response_engine", "soar"],
        "priority": RiskLevel.HIGH
    },
    "RS.IM": {
        "function": CSFFunction.RESPOND,
        "category": "Improvement",
        "description": "Response capabilities are continuously improved through"
                      " lessons learned and threat intelligence.",
        "examples": [
            "Post-incident reviews",
            "Playbook updates",
            "Training updates"
        ],
        "modules": ["compliance_engine"],
        "priority": RiskLevel.MODERATE
    },
    
    # =========================================================================
    # RECOVER Function (RC)
    # =========================================================================
    "RC.RP": {
        "function": CSFFunction.RECOVER,
        "category": "Response Planning",
        "description": "Recovery planning processes are executed to restore systems"
                      " and assets affected by incidents.",
        "examples": [
            "Disaster recovery plan",
            "Backup restoration",
            "Business continuity"
        ],
        "modules": ["resilience", "backup_recovery"],
        "priority": RiskLevel.HIGH
    },
    "RC.IM": {
        "function": CSFFunction.RECOVER,
        "category": "Improvement",
        "description": "Recovery capabilities are continuously improved through"
                      " lessons learned and threat intelligence.",
        "examples": [
            "Recovery testing",
            "Plan updates",
            "Training exercises"
        ],
        "modules": ["compliance_engine"],
        "priority": RiskLevel.MODERATE
    },
    "RC.CO": {
        "function": CSFFunction.RECOVER,
        "category": "Communications",
        "description": "Communications during recovery activities are coordinated"
                      " with internal and external stakeholders.",
        "examples": [
            "Stakeholder notification",
            "Status updates",
            "Public relations"
        ],
        "modules": ["response_engine"],
        "priority": RiskLevel.MODERATE
    }
}


# =============================================================================
# NIST CSF 2.0 COMPLIANCE ENGINE
# =============================================================================

class NISTCSFEngine:
    """
    NIST CSF 2.0 Compliance Assessment Engine.
    
    Provides automated assessment, evidence collection,
    gap analysis, and reporting for NIST CSF 2.0.
    
    Example:
        >>> engine = NISTCSFEngine()
        >>> assessment = await engine.run_assessment()
        >>> print(f"Overall score: {assessment.overall_score:.1%}")
    """
    
    def __init__(self):
        self.logger = structlog.get_logger("amcis.compliance.nist_csf")
        self.controls: Dict[str, CSFControl] = {}
        self._evidence_collectors: Dict[str, Callable[[], List[ControlEvidence]]] = {}
        self._load_controls()
    
    def _load_controls(self) -> None:
        """Load CSF 2.0 control definitions."""
        for control_id, config in CSF_CONTROLS.items():
            self.controls[control_id] = CSFControl(
                control_id=control_id,
                function=config["function"],
                category=config["category"],
                subcategory=control_id,
                description=config["description"],
                implementation_examples=config["examples"],
                amcis_modules=config["modules"],
                priority=config["priority"]
            )
        
        self.logger.info("nist_csf_controls_loaded", 
                        count=len(self.controls))
    
    def register_evidence_collector(
        self,
        control_id: str,
        collector: Callable[[], List[ControlEvidence]]
    ) -> None:
        """
        Register evidence collector for a control.
        
        Args:
            control_id: CSF control identifier
            collector: Function that returns list of evidence
        """
        self._evidence_collectors[control_id] = collector
        self.logger.debug("evidence_collector_registered", 
                         control_id=control_id)
    
    async def assess_control(self, control_id: str) -> CSFControl:
        """
        Assess implementation of a specific control.
        
        Args:
            control_id: CSF control identifier (e.g., "PR.DS")
            
        Returns:
            CSFControl with assessment results
        """
        control = self.controls.get(control_id)
        if not control:
            raise ValueError(f"Unknown control: {control_id}")
        
        # Collect evidence
        if control_id in self._evidence_collectors:
            try:
                evidence = self._evidence_collectors[control_id]()
                control.evidence.extend(evidence)
            except Exception as e:
                self.logger.error("evidence_collection_failed",
                                control_id=control_id,
                                error=str(e))
        
        # Determine implementation status
        control.status = self._determine_status(control)
        control.score = self._calculate_score(control)
        
        # Identify gaps
        control.gaps = self._identify_gaps(control)
        
        # Generate remediation
        if control.gaps:
            control.remediation = self._generate_remediation(control)
        
        return control
    
    def _determine_status(self, control: CSFControl) -> ImplementationStatus:
        """Determine implementation status from evidence."""
        if not control.evidence:
            return ImplementationStatus.NOT_IMPLEMENTED
        
        # Count evidence by type
        evidence_types = {}
        for e in control.evidence:
            evidence_types[e.evidence_type] = evidence_types.get(e.evidence_type, 0) + 1
        
        # Score based on evidence diversity
        score = 0
        if "policy" in evidence_types:
            score += 0.3
        if "procedure" in evidence_types:
            score += 0.2
        if "configuration" in evidence_types:
            score += 0.3
        if "test" in evidence_types:
            score += 0.2
        
        if score >= 0.9:
            return ImplementationStatus.EXCEEDS_REQUIREMENTS
        elif score >= 0.7:
            return ImplementationStatus.IMPLEMENTED
        elif score >= 0.3:
            return ImplementationStatus.PARTIALLY_IMPLEMENTED
        else:
            return ImplementationStatus.NOT_IMPLEMENTED
    
    def _calculate_score(self, control: CSFControl) -> float:
        """Calculate control implementation score."""
        status_scores = {
            ImplementationStatus.NOT_IMPLEMENTED: 0.0,
            ImplementationStatus.PARTIALLY_IMPLEMENTED: 0.5,
            ImplementationStatus.IMPLEMENTED: 1.0,
            ImplementationStatus.EXCEEDS_REQUIREMENTS: 1.2,
            ImplementationStatus.NOT_APPLICABLE: 1.0
        }
        
        base_score = status_scores.get(control.status, 0.0)
        
        # Cap at 1.0 for calculation
        return min(base_score, 1.0)
    
    def _identify_gaps(self, control: CSFControl) -> List[str]:
        """Identify implementation gaps."""
        gaps = []
        evidence_types = {e.evidence_type for e in control.evidence}
        
        if "policy" not in evidence_types:
            gaps.append(f"No policy documentation for {control.control_id}")
        
        if "procedure" not in evidence_types:
            gaps.append(f"No documented procedures for {control.control_id}")
        
        if "configuration" not in evidence_types:
            gaps.append(f"No configuration evidence for {control.control_id}")
        
        if "test" not in evidence_types:
            gaps.append(f"No testing evidence for {control.control_id}")
        
        return gaps
    
    def _generate_remediation(self, control: CSFControl) -> str:
        """Generate remediation recommendation."""
        # Priority-based recommendations
        priority_actions = {
            RiskLevel.CRITICAL: "Immediate action required",
            RiskLevel.HIGH: "Address within 30 days",
            RiskLevel.MODERATE: "Address within 90 days",
            RiskLevel.LOW: "Address within 180 days"
        }
        
        base_action = priority_actions.get(control.priority, "Address as scheduled")
        
        # Module-specific guidance
        module_guidance = f"Implement AMCIS modules: {', '.join(control.amcis_modules[:3])}"
        
        return f"{base_action}. {module_guidance}. " \
               f"Specific gaps: {'; '.join(control.gaps[:3])}"
    
    async def run_assessment(self) -> CSFAssessment:
        """
        Run complete NIST CSF 2.0 assessment.
        
        Returns:
            CSFAssessment with all results
        """
        self.logger.info("starting_nist_csf_assessment")
        
        assessment = CSFAssessment(
            assessment_date=datetime.utcnow()
        )
        
        # Assess all controls
        for control_id in self.controls:
            control = await self.assess_control(control_id)
            assessment.controls.append(control)
        
        # Calculate function scores
        assessment.function_scores = self._calculate_function_scores(assessment.controls)
        
        # Calculate overall score
        if assessment.function_scores:
            assessment.overall_score = sum(assessment.function_scores.values()) / \
                                      len(assessment.function_scores)
        
        # Identify critical gaps
        assessment.critical_gaps = self._identify_critical_gaps(assessment.controls)
        
        # Generate recommendations
        assessment.recommendations = self._generate_recommendations(assessment)
        
        self.logger.info("nist_csf_assessment_complete",
                        overall_score=assessment.overall_score,
                        controls_assessed=len(assessment.controls))
        
        return assessment
    
    def _calculate_function_scores(
        self,
        controls: List[CSFControl]
    ) -> Dict[CSFFunction, float]:
        """Calculate scores per CSF function."""
        function_scores: Dict[CSFFunction, List[float]] = {
            func: [] for func in CSFFunction
        }
        
        for control in controls:
            function_scores[control.function].append(control.score)
        
        return {
            func: sum(scores) / len(scores) if scores else 0.0
            for func, scores in function_scores.items()
        }
    
    def _identify_critical_gaps(
        self,
        controls: List[CSFControl]
    ) -> List[Dict[str, Any]]:
        """Identify critical compliance gaps."""
        gaps = []
        
        for control in controls:
            if control.priority in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                if control.status in [
                    ImplementationStatus.NOT_IMPLEMENTED,
                    ImplementationStatus.PARTIALLY_IMPLEMENTED
                ]:
                    gaps.append({
                        "control_id": control.control_id,
                        "function": control.function.name,
                        "description": control.description,
                        "status": control.status.name,
                        "priority": control.priority.name,
                        "remediation": control.remediation
                    })
        
        # Sort by priority
        priority_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1}
        gaps.sort(key=lambda x: priority_order.get(RiskLevel[x["priority"]], 99))
        
        return gaps
    
    def _generate_recommendations(self, assessment: CSFAssessment) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []
        
        # Sort functions by score (lowest first)
        sorted_functions = sorted(
            assessment.function_scores.items(),
            key=lambda x: x[1]
        )
        
        for func, score in sorted_functions[:3]:
            if score < 0.7:
                recommendations.append(
                    f"Priority: Improve {func.name} function " \
                    f"(current score: {score:.1%})"
                )
        
        # Add specific control recommendations
        weak_controls = [
            c for c in assessment.controls
            if c.score < 0.5 and c.priority in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
        
        for control in weak_controls[:5]:
            if control.remediation:
                recommendations.append(
                    f"Control {control.control_id}: {control.remediation[:100]}..."
                )
        
        return recommendations
    
    def export_report(
        self,
        assessment: CSFAssessment,
        output_path: Path,
        format: str = "json"
    ) -> None:
        """
        Export assessment report to file.
        
        Args:
            assessment: CSFAssessment to export
            output_path: Output file path
            format: Export format (json, markdown, html)
        """
        if format == "json":
            with open(output_path, "w") as f:
                json.dump(assessment.to_dict(), f, indent=2, default=str)
        
        elif format == "markdown":
            self._export_markdown(assessment, output_path)
        
        elif format == "html":
            self._export_html(assessment, output_path)
        
        self.logger.info("assessment_report_exported",
                        path=str(output_path),
                        format=format)
    
    def _export_markdown(self, assessment: CSFAssessment, path: Path) -> None:
        """Export as Markdown report."""
        lines = [
            "# NIST CSF 2.0 Compliance Assessment Report",
            "",
            f"**Date:** {assessment.assessment_date.isoformat()}",
            f"**Organization:** {assessment.organization}",
            f"**Version:** NIST CSF {assessment.version}",
            "",
            "## Executive Summary",
            "",
            f"**Overall Score:** {assessment.overall_score:.1%}",
            "",
            "### Implementation Status",
            f"- Total Controls: {len(assessment.controls)}",
            f"- Implemented: {sum(1 for c in assessment.controls if c.status == ImplementationStatus.IMPLEMENTED)}",
            f"- Partial: {sum(1 for c in assessment.controls if c.status == ImplementationStatus.PARTIALLY_IMPLEMENTED)}",
            f"- Not Implemented: {sum(1 for c in assessment.controls if c.status == ImplementationStatus.NOT_IMPLEMENTED)}",
            "",
            "## Function Scores",
            ""
        ]
        
        for func, score in assessment.function_scores.items():
            lines.append(f"- **{func.name}:** {score:.1%}")
        
        lines.extend([
            "",
            "## Critical Gaps",
            ""
        ])
        
        for gap in assessment.critical_gaps[:10]:
            lines.append(f"### {gap['control_id']} - {gap['priority']}")
            lines.append(f"- **Description:** {gap['description']}")
            lines.append(f"- **Status:** {gap['status']}")
            lines.append(f"- **Remediation:** {gap['remediation'][:200]}...")
            lines.append("")
        
        lines.extend([
            "",
            "## Recommendations",
            ""
        ])
        
        for i, rec in enumerate(assessment.recommendations, 1):
            lines.append(f"{i}. {rec}")
        
        with open(path, "w") as f:
            f.write("\n".join(lines))
    
    def _export_html(self, assessment: CSFAssessment, path: Path) -> None:
        """Export as HTML report."""
        # Simplified HTML export
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NIST CSF 2.0 Assessment - {assessment.organization}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #003366; color: white; padding: 20px; }}
        .score {{ font-size: 24px; font-weight: bold; }}
        .function {{ margin: 20px 0; }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #003366; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NIST CSF 2.0 Compliance Assessment</h1>
        <p>Organization: {assessment.organization}</p>
        <p>Date: {assessment.assessment_date.strftime('%Y-%m-%d')}</p>
    </div>
    
    <div class="score">
        Overall Score: {assessment.overall_score:.1%}
    </div>
    
    <h2>Function Scores</h2>
    <table>
        <tr><th>Function</th><th>Score</th></tr>
"""
        
        for func, score in assessment.function_scores.items():
            html += f"<tr><td>{func.name}</td><td>{score:.1%}</td></tr>\n"
        
        html += """
    </table>
    
    <h2>Critical Gaps</h2>
    <table>
        <tr><th>Control</th><th>Priority</th><th>Status</th></tr>
"""
        
        for gap in assessment.critical_gaps[:10]:
            css_class = "critical" if gap['priority'] == 'CRITICAL' else "high"
            html += f"<tr class='{css_class}'>"
            html += f"<td>{gap['control_id']}</td>"
            html += f"<td>{gap['priority']}</td>"
            html += f"<td>{gap['status']}</td>"
            html += "</tr>\n"
        
        html += """
    </table>
</body>
</html>
"""
        
        with open(path, "w") as f:
            f.write(html)


# Convenience function
async def run_nist_csf_assessment() -> CSFAssessment:
    """
    Run NIST CSF 2.0 assessment with default configuration.
    
    Returns:
        CSFAssessment with results
    """
    engine = NISTCSFEngine()
    
    # Register AMCIS-specific evidence collectors
    # These would be implemented based on actual AMCIS module capabilities
    
    assessment = await engine.run_assessment()
    return assessment


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def demo():
        print("NIST CSF 2.0 Compliance Assessment Demo")
        print("=" * 60)
        
        engine = NISTCSFEngine()
        
        # Run assessment
        print("\nRunning assessment...")
        assessment = await engine.run_assessment()
        
        # Display results
        print(f"\nOverall Score: {assessment.overall_score:.1%}")
        print(f"Total Controls: {len(assessment.controls)}")
        
        print("\nFunction Scores:")
        for func, score in assessment.function_scores.items():
            print(f"  {func.name}: {score:.1%}")
        
        print(f"\nCritical Gaps: {len(assessment.critical_gaps)}")
        print(f"Recommendations: {len(assessment.recommendations)}")
        
        # Export reports
        engine.export_report(assessment, Path("csf_assessment.json"), "json")
        engine.export_report(assessment, Path("csf_assessment.md"), "markdown")
        engine.export_report(assessment, Path("csf_assessment.html"), "html")
        
        print("\nReports exported to:")
        print("  - csf_assessment.json")
        print("  - csf_assessment.md")
        print("  - csf_assessment.html")
    
    asyncio.run(demo())
