"""
Compliance Report Generator
===========================

Generates compliance reports in multiple formats (PDF, HTML, JSON).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import structlog

from .compliance_engine import ComplianceEngine, Framework


class ReportGenerator:
    """
    AMCIS Compliance Report Generator
    =================================
    
    Generates human and machine-readable compliance reports.
    """
    
    def __init__(self, engine: ComplianceEngine) -> None:
        self.engine = engine
        self.logger = structlog.get_logger("amcis.compliance_report")
    
    def generate_json_report(self, framework: Framework) -> str:
        """Generate JSON compliance report."""
        status = self.engine.get_framework_status(framework)
        gaps = self.engine.get_gap_analysis(framework)
        
        report = {
            "report_type": "compliance_assessment",
            "framework": framework.value,
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "overall_score": status["score"],
                "compliance_status": "compliant" if status["score"] >= 80 else "non_compliant",
                "total_controls": status["total_controls"],
                "compliant_controls": status["compliant"]
            },
            "control_details": status["controls"],
            "gap_analysis": gaps
        }
        
        return json.dumps(report, indent=2)
    
    def generate_html_report(self, framework: Framework) -> str:
        """Generate HTML compliance report."""
        status = self.engine.get_framework_status(framework)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - {framework.value}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #1a237e; color: white; padding: 20px; }}
        .score {{ font-size: 48px; font-weight: bold; }}
        .compliant {{ color: green; }}
        .non-compliant {{ color: red; }}
        .partial {{ color: orange; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Compliance Assessment Report</h1>
        <p>Framework: {framework.value.upper()}</p>
        <p>Generated: {datetime.now().isoformat()}</p>
    </div>
    
    <h2>Executive Summary</h2>
    <div class="score">{status['score']:.1f}%</div>
    <p>Overall Compliance Score</p>
    
    <table>
        <tr>
            <th>Status</th>
            <th>Count</th>
        </tr>
        <tr>
            <td>Compliant</td>
            <td class="compliant">{status['compliant']}</td>
        </tr>
        <tr>
            <td>Partial</td>
            <td class="partial">{status['partial']}</td>
        </tr>
        <tr>
            <td>Non-Compliant</td>
            <td class="non-compliant">{status['non_compliant']}</td>
        </tr>
    </table>
</body>
</html>"""
        
        return html
    
    def save_report(self, framework: Framework, output_path: Path, 
                   format: str = "json") -> Path:
        """Save report to file."""
        if format == "json":
            content = self.generate_json_report(framework)
            ext = "json"
        elif format == "html":
            content = self.generate_html_report(framework)
            ext = "html"
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        output_file = output_path / f"compliance_report_{framework.value}.{ext}"
        with open(output_file, 'w') as f:
            f.write(content)
        
        self.logger.info("report_saved", path=str(output_file), format=format)
        return output_file
