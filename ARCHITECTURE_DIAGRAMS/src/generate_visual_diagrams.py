"""
Generate visual architecture diagrams using the 'diagrams' library
Creates professional PNG images of system architecture
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.security import Vault
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.onprem.client import Client
from diagrams.generic.storage import Storage
from diagrams.generic.compute import Rack

# Set output directory
output_dir = "."

def generate_system_architecture():
    """Generate high-level system architecture diagram"""
    
    with Diagram(
        "AMCIS System Architecture",
        filename=f"{output_dir}/amcis_system_architecture",
        show=False,
        direction="TB"
    ):
        # User interfaces
        with Cluster("User Interfaces"):
            cli = Client("CLI")
            api = Nginx("REST API")
            dashboard = Client("Dashboard")
        
        # Core layer
        with Cluster("Core Layer"):
            kernel = Rack("AMCIS Kernel")
            trust = Rack("Trust Engine")
            policy = Rack("Policy Engine")
        
        # Security modules
        with Cluster("Security Modules"):
            crypto = Python("Crypto Module")
            edr = Python("EDR/XDR")
            network = Python("Network Security")
            ai_sec = Python("AI Security")
            compliance = Python("Compliance")
            threat = Python("Threat Intel")
            secrets = Python("Secrets Mgr")
            forensics = Python("Forensics")
            soar = Python("SOAR")
        
        # Data layer
        with Cluster("Data Layer"):
            db = PostgreSQL("PostgreSQL")
            cache = Redis("Redis Cache")
            vault = Vault("HashiCorp Vault")
            storage = Storage("Audit Logs")
        
        # Monitoring
        with Cluster("Monitoring"):
            prom = Prometheus("Prometheus")
            graf = Grafana("Grafana")
        
        # Connections - User to Core
        cli >> kernel
        api >> kernel
        dashboard >> kernel
        
        # Core to engines
        kernel >> trust
        kernel >> policy
        
        # Core to security modules
        kernel >> [crypto, edr, network, ai_sec, compliance, threat, secrets, forensics, soar]
        
        # Security modules to data
        crypto >> vault
        edr >> db
        network >> db
        ai_sec >> db
        compliance >> db
        threat >> cache
        secrets >> vault
        forensics >> db
        soar >> db
        
        # Core to storage
        kernel >> storage
        
        # Monitoring
        kernel >> Edge(style="dotted") >> prom
        prom >> graf


def generate_deployment_diagram():
    """Generate Docker deployment architecture"""
    
    with Diagram(
        "AMCIS Docker Deployment",
        filename=f"{output_dir}/amcis_deployment_architecture",
        show=False,
        direction="LR"
    ):
        with Cluster("Docker Compose Stack"):
            
            with Cluster("Application Layer"):
                amcis = Python("amcis-core\n:8080")
            
            with Cluster("Data Layer"):
                postgres = PostgreSQL("postgres\n:5432")
                redis = Redis("redis\n:6379")
                vault = Vault("vault\n:8200")
            
            with Cluster("Monitoring Layer"):
                prom = Prometheus("prometheus\n:9091")
                graf = Grafana("grafana\n:3000")
        
        # Connections
        amcis >> postgres
        amcis >> redis
        amcis >> vault
        
        amcis >> prom
        prom >> graf


def generate_security_modules_diagram():
    """Generate security modules relationship diagram"""
    
    with Diagram(
        "AMCIS Security Modules",
        filename=f"{output_dir}/amcis_security_modules",
        show=False,
        direction="TB"
    ):
        # Central kernel
        kernel = Rack("AMCIS Kernel")
        
        with Cluster("Core Security"):
            crypto = Python("Crypto\nPQC")
            keys = Python("Key Mgr")
            edr = Python("EDR/XDR")
        
        with Cluster("Network & AI"):
            net = Python("Network\nSecurity")
            ai = Python("AI\nSecurity")
            threat = Python("Threat\nIntel")
        
        with Cluster("Operations"):
            compliance = Python("Compliance")
            secrets = Python("Secrets\nManager")
            forensics = Python("Forensics")
            soar = Python("SOAR")
            sc = Python("Supply Chain")
        
        # All connect to kernel
        kernel >> [crypto, keys, edr, net, ai, threat, compliance, secrets, forensics, soar, sc]


def generate_data_flow_diagram():
    """Generate data flow diagram"""
    
    with Diagram(
        "AMCIS Data Flow",
        filename=f"{output_dir}/amcis_data_flow",
        show=False,
        direction="LR"
    ):
        # Input sources
        with Cluster("Input Sources"):
            events = Client("Security Events")
            logs = Client("Log Streams")
            apis = Nginx("API Calls")
        
        # Processing
        with Cluster("Processing Pipeline"):
            ingest = Rack("Ingestion\nNormalize/Enrich")
            detect = Rack("AI Detection\nThreat Analysis")
            respond = Rack("Response\nAlert/Remediate")
        
        # Storage
        with Cluster("Storage"):
            db = PostgreSQL("Database")
            cache = Redis("Cache")
            vault = Vault("Secrets")
            archive = Storage("Archive")
        
        # Flow
        events >> ingest
        logs >> ingest
        apis >> ingest
        
        ingest >> detect
        detect >> respond
        
        respond >> db
        respond >> vault
        detect >> cache
        db >> archive


def main():
    """Generate all visual diagrams"""
    
    print("Generating AMCIS Architecture Diagrams...")
    print("=" * 50)
    
    try:
        print("1. System Architecture...")
        generate_system_architecture()
        print("   ✓ amcis_system_architecture.png")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    try:
        print("2. Deployment Architecture...")
        generate_deployment_diagram()
        print("   ✓ amcis_deployment_architecture.png")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    try:
        print("3. Security Modules...")
        generate_security_modules_diagram()
        print("   ✓ amcis_security_modules.png")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    try:
        print("4. Data Flow...")
        generate_data_flow_diagram()
        print("   ✓ amcis_data_flow.png")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("=" * 50)
    print("Done! Check the ARCHITECTURE_DIAGRAMS folder for PNG files.")


if __name__ == "__main__":
    main()
