"""
Create PDF package combining all architecture diagrams
"""

from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
from pathlib import Path

def create_pdf_package():
    """Create comprehensive PDF package"""
    
    output_dir = Path(__file__).parent.parent
    pdf_path = output_dir / "AMCIS_Architecture_Diagrams.pdf"
    
    # Create PDF
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Title Page
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width/2, height - 150, "AMCIS Q-SEC CORE")
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 200, "Architecture Diagrams")
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 250, "Complete Technical Documentation Package")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height - 300, "Version 1.0 | Generated: 2026-03-14")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 350, "Production-Ready Quantum-Secure Security Framework")
    
    # Classification box
    c.setStrokeColorRGB(0.8, 0.2, 0.2)
    c.setLineWidth(2)
    c.rect(width/2 - 150, height - 450, 300, 40)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.8, 0.2, 0.2)
    c.drawCentredString(width/2, height - 435, "INTERNAL / COMMERCIAL")
    
    c.showPage()
    
    # Table of Contents
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Table of Contents")
    
    toc_items = [
        ("1. System Architecture Overview", "High-level component diagram"),
        ("2. Docker Deployment Architecture", "Container orchestration layout"),
        ("3. Security Modules Overview", "All 22 specialized modules"),
        ("4. Data Flow Pipeline", "End-to-end processing flow"),
        ("5. Component Specifications", "Technical details"),
    ]
    
    y_pos = height - 100
    for title, desc in toc_items:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y_pos, title)
        c.setFont("Helvetica", 10)
        c.drawString(90, y_pos - 15, desc)
        y_pos -= 45
    
    c.showPage()
    
    # System Architecture Page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "1. System Architecture Overview")
    
    c.setFont("Helvetica", 10)
    desc = """The AMCIS system follows a layered architecture with clear separation of concerns:
    
• User Interfaces: CLI, REST API, Dashboard, SDK for different user types
• Core Layer: Central orchestration, trust scoring, and policy enforcement
• Security Modules: 22 specialized modules covering all security domains
• Data Layer: PostgreSQL for structured data, Redis for caching, Vault for secrets
• Monitoring: Prometheus and Grafana for observability"""
    
    text_obj = c.beginText(50, height - 100)
    text_obj.setFont("Helvetica", 10)
    for line in desc.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    
    # Add image
    img_path = output_dir / "amcis_system_architecture.png"
    if img_path.exists():
        c.drawImage(str(img_path), 50, 50, width=width-100, height=height-280, preserveAspectRatio=True)
    
    c.showPage()
    
    # Deployment Architecture Page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "2. Docker Deployment Architecture")
    
    c.setFont("Helvetica", 10)
    desc2 = """AMCIS deploys as a Docker Compose stack with 7 containerized services:
    
• amcis-core: Main Python application (API on 8080, metrics on 9090)
• postgres: PostgreSQL 15 database for persistent storage
• redis: Redis 7 cache for session management and rate limiting
• vault: HashiCorp Vault for secrets management
• prometheus: Metrics collection and alerting
• grafana: Visualization dashboards
• mailpit: Email testing for development"""
    
    text_obj = c.beginText(50, height - 100)
    text_obj.setFont("Helvetica", 10)
    for line in desc2.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    
    img_path = output_dir / "amcis_deployment_architecture.png"
    if img_path.exists():
        c.drawImage(str(img_path), 50, 50, width=width-100, height=height-280, preserveAspectRatio=True)
    
    c.showPage()
    
    # Security Modules Page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "3. Security Modules Overview")
    
    c.setFont("Helvetica", 10)
    desc3 = """AMCIS includes 22 specialized security modules organized by function:
    
Core Security: Crypto (PQC), Key Manager, EDR/XDR
Network & AI: Network Security, AI Security, Threat Intelligence
Governance: Compliance (NIST CSF), Secrets Manager, Forensics
Operations: SOAR, Supply Chain, Biometrics
Additional: Cloud Sec, Container Sec, DLP, Deception, Sandbox, WAF"""
    
    text_obj = c.beginText(50, height - 100)
    text_obj.setFont("Helvetica", 10)
    for line in desc3.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    
    img_path = output_dir / "amcis_security_modules.png"
    if img_path.exists():
        c.drawImage(str(img_path), 50, 50, width=width-100, height=height-280, preserveAspectRatio=True)
    
    c.showPage()
    
    # Data Flow Page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "4. Data Flow Pipeline")
    
    c.setFont("Helvetica", 10)
    desc4 = """Security data flows through a 5-stage pipeline:
    
1. INPUT: Security events, logs, API calls, user actions
2. INGESTION: Normalization, enrichment, validation
3. PROCESSING: AI detection, risk analysis, correlation
4. RESPONSE: Alerting, auto-remediation, escalation
5. STORAGE: Encrypted storage, audit trails, archiving"""
    
    text_obj = c.beginText(50, height - 100)
    text_obj.setFont("Helvetica", 10)
    for line in desc4.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    
    img_path = output_dir / "amcis_data_flow.png"
    if img_path.exists():
        c.drawImage(str(img_path), 50, 50, width=width-100, height=height-280, preserveAspectRatio=True)
    
    c.showPage()
    
    # Technical Specifications Page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "5. Technical Specifications")
    
    specs = [
        ("Programming Language", "Python 3.11+"),
        ("Framework", "FastAPI, Click (CLI)"),
        ("Total Python Files", "79+"),
        ("Lines of Code", "18,000+"),
        ("Security Modules", "22"),
        ("Database", "PostgreSQL 15"),
        ("Cache", "Redis 7"),
        ("Secrets Management", "HashiCorp Vault"),
        ("Container Platform", "Docker + Docker Compose"),
        ("Monitoring", "Prometheus + Grafana"),
        ("Cryptography", "NIST FIPS 203/204 (PQC)"),
        ("Compliance", "NIST CSF 2.0, CMMC, FedRAMP"),
        ("AI Agents", "35+ autonomous agents"),
        ("Test Coverage Target", "90%"),
    ]
    
    y_pos = height - 100
    c.setFont("Helvetica-Bold", 11)
    c.drawString(70, y_pos, "Specification")
    c.drawString(350, y_pos, "Value")
    y_pos -= 20
    
    c.setLineWidth(0.5)
    c.line(70, y_pos, 500, y_pos)
    y_pos -= 20
    
    for spec, value in specs:
        c.setFont("Helvetica", 10)
        c.drawString(70, y_pos, spec)
        c.drawString(350, y_pos, value)
        y_pos -= 20
    
    # Port mappings
    y_pos -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, y_pos, "Port Mappings:")
    y_pos -= 25
    
    ports = [
        ("amcis-core API", "8080"),
        ("amcis-core Metrics", "9090"),
        ("PostgreSQL", "5432"),
        ("Redis", "6379"),
        ("Vault UI", "8200"),
        ("Prometheus", "9091"),
        ("Grafana", "3000"),
        ("Mailpit SMTP", "8025"),
        ("Mailpit Web", "8026"),
    ]
    
    for service, port in ports:
        c.setFont("Helvetica", 10)
        c.drawString(90, y_pos, f"{service:<25} :{port}")
        y_pos -= 18
    
    c.showPage()
    
    # Save PDF
    c.save()
    print(f"Created PDF: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        print("Installing reportlab...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab", "-q"])
        from reportlab.pdfgen import canvas
    
    create_pdf_package()
