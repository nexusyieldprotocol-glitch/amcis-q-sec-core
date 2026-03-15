"""
Generate visual diagrams using PIL/Pillow (no external dependencies)
Creates simple but professional architecture diagrams as PNG images
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Constants
WIDTH = 1400
HEIGHT = 1000
BG_COLOR = (30, 30, 40)
BOX_COLOR = (60, 80, 120)
BOX_HIGHLIGHT = (80, 120, 180)
TEXT_COLOR = (255, 255, 255)
LINE_COLOR = (150, 150, 150)
ACCENT_COLOR = (100, 200, 150)

def get_font(size=14):
    """Get a font (fallback to default if specific font not available)"""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()

def draw_rounded_rect(draw, xy, fill, radius=10):
    """Draw a rounded rectangle"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=LINE_COLOR, width=2)

def draw_text_centered(draw, text, xy, font, fill=TEXT_COLOR):
    """Draw centered text"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (xy[0] + xy[2]) // 2 - text_width // 2
    y = (xy[1] + xy[3]) // 2 - text_height // 2
    draw.text((x, y), text, font=font, fill=fill)

def draw_connection(draw, start, end, color=LINE_COLOR):
    """Draw a line connection between two points"""
    draw.line([start, end], fill=color, width=2)
    # Draw arrowhead
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = (dx**2 + dy**2) ** 0.5
    if length > 0:
        ux, uy = dx/length, dy/length
        arrow_size = 8
        p1 = (end[0] - arrow_size*ux + arrow_size*uy*0.5, 
              end[1] - arrow_size*uy - arrow_size*ux*0.5)
        p2 = (end[0] - arrow_size*ux - arrow_size*uy*0.5,
              end[1] - arrow_size*uy + arrow_size*ux*0.5)
        draw.polygon([end, p1, p2], fill=color)

def generate_system_architecture():
    """Generate high-level system architecture"""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    font_small = get_font(12)
    font_title = get_font(24)
    
    # Title
    draw.text((WIDTH//2 - 250, 20), "AMCIS Q-SEC CORE - System Architecture", 
              font=font_title, fill=ACCENT_COLOR)
    
    # Layer 1: User Interfaces (Top)
    y_user = 80
    draw.text((20, y_user), "USER INTERFACES", font=font, fill=ACCENT_COLOR)
    
    boxes_user = [
        (100, y_user + 30, 250, y_user + 80, "CLI Interface"),
        (350, y_user + 30, 500, y_user + 80, "REST API"),
        (600, y_user + 30, 750, y_user + 80, "Dashboard"),
        (850, y_user + 30, 1000, y_user + 80, "SDK/Plugins"),
    ]
    for x1, y1, x2, y2, text in boxes_user:
        draw_rounded_rect(draw, (x1, y1, x2, y2), BOX_COLOR)
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Layer 2: Core Layer
    y_core = 180
    draw.text((20, y_core), "CORE LAYER", font=font, fill=ACCENT_COLOR)
    
    boxes_core = [
        (200, y_core + 30, 400, y_core + 100, "AMCIS Kernel\n(Orchestrator)"),
        (500, y_core + 30, 700, y_core + 100, "Trust Engine\n(Verification)"),
        (800, y_core + 30, 1000, y_core + 100, "Policy Engine\n(Rules)"),
    ]
    for x1, y1, x2, y2, text in boxes_core:
        draw_rounded_rect(draw, (x1, y1, x2, y2), BOX_HIGHLIGHT)
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Connections from user to core
    for x1, _, x2, _, _ in boxes_user:
        draw_connection(draw, ((x1+x2)//2, y_user + 80), ((x1+x2)//2, y_core + 30))
    
    # Layer 3: Security Modules
    y_modules = 310
    draw.text((20, y_modules), "SECURITY MODULES (22 Specialized Modules)", font=font, fill=ACCENT_COLOR)
    
    module_boxes = [
        (50, y_modules + 35, 180, y_modules + 85, "Crypto\n(PQC)"),
        (200, y_modules + 35, 330, y_modules + 85, "EDR/XDR"),
        (350, y_modules + 35, 480, y_modules + 85, "Network\nSecurity"),
        (500, y_modules + 35, 630, y_modules + 85, "AI Security"),
        (650, y_modules + 35, 780, y_modules + 85, "Compliance"),
        (800, y_modules + 35, 930, y_modules + 85, "Threat\nIntel"),
        (950, y_modules + 35, 1080, y_modules + 85, "Secrets\nManager"),
        (1100, y_modules + 35, 1230, y_modules + 85, "Forensics"),
        (200, y_modules + 100, 330, y_modules + 150, "SOAR"),
        (350, y_modules + 100, 480, y_modules + 150, "Supply Chain"),
        (500, y_modules + 100, 630, y_modules + 150, "Biometrics"),
        (650, y_modules + 100, 780, y_modules + 150, "Cloud Sec"),
        (800, y_modules + 100, 930, y_modules + 150, "WAF"),
    ]
    for x1, y1, x2, y2, text in module_boxes:
        draw_rounded_rect(draw, (x1, y1, x2, y2), BOX_COLOR)
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Connections from core to modules
    for _, _, cx2, cy2 in [(200, y_core + 30, 400, y_core + 100)]:
        for x1, y1, x2, y2, _ in module_boxes[:8]:
            draw_connection(draw, (300, cy2), ((x1+x2)//2, y1))
    
    # Layer 4: Data Layer
    y_data = 500
    draw.text((20, y_data), "DATA & STORAGE LAYER", font=font, fill=ACCENT_COLOR)
    
    data_boxes = [
        (150, y_data + 35, 350, y_data + 100, "PostgreSQL\n(Structured Data)"),
        (400, y_data + 35, 600, y_data + 100, "Redis\n(Cache)"),
        (650, y_data + 35, 850, y_data + 100, "HashiCorp Vault\n(Secrets)"),
        (900, y_data + 35, 1100, y_data + 100, "Audit Logs\n(Immutable)"),
    ]
    for x1, y1, x2, y2, text in data_boxes:
        draw_rounded_rect(draw, (x1, y1, x2, y2), (80, 100, 80))
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Layer 5: Monitoring
    y_monitor = 630
    draw.text((20, y_monitor), "MONITORING & OBSERVABILITY", font=font, fill=ACCENT_COLOR)
    
    monitor_boxes = [
        (300, y_monitor + 35, 500, y_monitor + 90, "Prometheus\n(Metrics)"),
        (600, y_monitor + 35, 800, y_monitor + 90, "Grafana\n(Dashboards)"),
        (900, y_monitor + 35, 1100, y_monitor + 90, "Alerting\n(PagerDuty)"),
    ]
    for x1, y1, x2, y2, text in monitor_boxes:
        draw_rounded_rect(draw, (x1, y1, x2, y2), (120, 80, 80))
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Legend
    y_legend = 750
    draw.text((20, y_legend), "LEGEND:", font=font, fill=ACCENT_COLOR)
    draw_rounded_rect(draw, (120, y_legend, 220, y_legend + 30), BOX_COLOR)
    draw.text((230, y_legend + 5), "Security Module", font=font_small, fill=TEXT_COLOR)
    draw_rounded_rect(draw, (380, y_legend, 480, y_legend + 30), BOX_HIGHLIGHT)
    draw.text((490, y_legend + 5), "Core Component", font=font_small, fill=TEXT_COLOR)
    draw_rounded_rect(draw, (640, y_legend, 740, y_legend + 30), (80, 100, 80))
    draw.text((750, y_legend + 5), "Data Store", font=font_small, fill=TEXT_COLOR)
    
    # Footer
    draw.text((WIDTH//2 - 200, HEIGHT - 40), 
              "AMCIS Q-SEC CORE v1.0 | Production-Ready Quantum-Secure Security Framework",
              font=font_small, fill=LINE_COLOR)
    
    img.save("amcis_system_architecture.png", "PNG")
    print("Generated: amcis_system_architecture.png")


def generate_deployment_diagram():
    """Generate Docker deployment architecture"""
    img = Image.new('RGB', (WIDTH, 800), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    font_small = get_font(12)
    font_title = get_font(24)
    
    # Title
    draw.text((WIDTH//2 - 250, 20), "AMCIS Docker Deployment Architecture", 
              font=font_title, fill=ACCENT_COLOR)
    
    # Docker Network
    y_net = 70
    draw_rounded_rect(draw, (50, y_net, 1350, 700), (40, 40, 50), radius=20)
    draw.text((70, y_net + 10), "DOCKER NETWORK: amcis-network (172.20.0.0/16)", 
              font=font, fill=ACCENT_COLOR)
    
    # Application Layer
    y_app = 120
    draw.text((70, y_app), "APPLICATION LAYER", font=font, fill=(200, 200, 100))
    draw_rounded_rect(draw, (100, y_app + 30, 400, y_app + 120), BOX_HIGHLIGHT)
    draw_text_centered(draw, "amcis-core\n(Main API)\nPorts: 8080, 9090", 
                       (100, y_app + 30, 400, y_app + 120), font_small)
    
    # Data Layer
    y_data = 280
    draw.text((70, y_data), "DATA LAYER", font=font, fill=(200, 200, 100))
    
    data_services = [
        (100, y_data + 30, 350, y_data + 110, "postgres\nPostgreSQL\nPort: 5432"),
        (400, y_data + 30, 650, y_data + 110, "redis\nRedis Cache\nPort: 6379"),
        (700, y_data + 30, 950, y_data + 110, "vault\nHashiCorp Vault\nPort: 8200"),
    ]
    for x1, y1, x2, y2, text in data_services:
        draw_rounded_rect(draw, (x1, y1, x2, y2), (80, 100, 80))
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Connections to data
    for x1, _, x2, _, _ in data_services:
        draw_connection(draw, (250, y_app + 120), ((x1+x2)//2, y_data + 30))
    
    # Monitoring Layer
    y_mon = 430
    draw.text((70, y_mon), "MONITORING LAYER", font=font, fill=(200, 200, 100))
    
    mon_services = [
        (300, y_mon + 30, 550, y_mon + 100, "prometheus\nMetrics\nPort: 9091"),
        (600, y_mon + 30, 850, y_mon + 100, "grafana\nDashboards\nPort: 3000"),
        (900, y_mon + 30, 1150, y_mon + 100, "mailpit\nEmail Testing\nPorts: 8025-8026"),
    ]
    for x1, y1, x2, y2, text in mon_services:
        draw_rounded_rect(draw, (x1, y1, x2, y2), (120, 80, 80))
        draw_text_centered(draw, text, (x1, y1, x2, y2), font_small)
    
    # Connections monitoring
    draw_connection(draw, (250, y_app + 75), (425, y_mon + 30))
    draw_connection(draw, (725, y_mon + 100), (725, y_mon + 130), color=LINE_COLOR)
    
    # Port table
    y_table = 560
    draw.text((70, y_table), "EXTERNAL PORT MAPPINGS:", font=font, fill=ACCENT_COLOR)
    
    ports = [
        ("amcis-core", "8080", "API Access"),
        ("amcis-core", "9090", "Metrics"),
        ("postgres", "5432", "Database"),
        ("redis", "6379", "Cache"),
        ("vault", "8200", "Secrets UI"),
        ("prometheus", "9091", "Monitoring"),
        ("grafana", "3000", "Dashboards"),
        ("mailpit", "8025/8026", "Email Testing"),
    ]
    
    y_pos = y_table + 35
    for service, port, desc in ports:
        draw.text((100, y_pos), f"{service:20} :{port:10} -> {desc}", 
                  font=font_small, fill=TEXT_COLOR)
        y_pos += 22
    
    img.save("amcis_deployment_architecture.png", "PNG")
    print("Generated: amcis_deployment_architecture.png")


def generate_security_modules():
    """Generate security modules overview"""
    img = Image.new('RGB', (WIDTH, 900), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    font_small = get_font(12)
    font_title = get_font(24)
    
    # Title
    draw.text((WIDTH//2 - 200, 20), "AMCIS Security Modules Overview", 
              font=font_title, fill=ACCENT_COLOR)
    
    # Central Kernel
    y_kernel = 100
    draw_rounded_rect(draw, (550, y_kernel, 850, y_kernel + 60), BOX_HIGHLIGHT)
    draw_text_centered(draw, "AMCIS KERNEL (Central Orchestrator)", 
                       (550, y_kernel, 850, y_kernel + 60), font)
    
    # Module categories
    categories = [
        ("CORE SECURITY", 50, 200, [
            ("Crypto\n(PQC)", "Post-quantum cryptography"),
            ("Key Manager", "Quantum-safe key lifecycle"),
            ("EDR/XDR", "Endpoint detection & response"),
        ]),
        ("NETWORK & AI", 380, 200, [
            ("Network\nSecurity", "DNS, microsegmentation"),
            ("AI Security", "Prompt firewall, validation"),
            ("Threat Intel", "Intelligence aggregation"),
        ]),
        ("GOVERNANCE", 710, 200, [
            ("Compliance", "NIST CSF 2.0 automation"),
            ("Secrets Mgr", "Vault integration"),
            ("Forensics", "Timeline reconstruction"),
        ]),
        ("OPERATIONS", 1040, 200, [
            ("SOAR", "Security orchestration"),
            ("Supply Chain", "SBOM, dependency scan"),
            ("Biometrics", "Behavioral analysis"),
        ]),
    ]
    
    for cat_name, x_start, y_start, modules in categories:
        # Category label
        draw.text((x_start, y_start), cat_name, font=font, fill=ACCENT_COLOR)
        
        # Module boxes
        y_mod = y_start + 35
        for mod_name, mod_desc in modules:
            draw_rounded_rect(draw, (x_start, y_mod, x_start + 180, y_mod + 70), BOX_COLOR)
            draw_text_centered(draw, mod_name, (x_start, y_mod, x_start + 180, y_mod + 45), font_small)
            # Description below
            words = mod_desc.split()
            mid = len(words) // 2
            line1 = ' '.join(words[:mid])
            line2 = ' '.join(words[mid:])
            draw.text((x_start + 10, y_mod + 48), line1, font=font_small, fill=(180, 180, 180))
            draw.text((x_start + 10, y_mod + 62), line2, font=font_small, fill=(180, 180, 180))
            
            # Connection to kernel
            draw_connection(draw, (x_start + 90, y_mod), (700, y_kernel + 60))
            
            y_mod += 90
    
    # Additional modules row
    y_extra = 550
    draw.text((50, y_extra), "ADDITIONAL MODULES:", font=font, fill=ACCENT_COLOR)
    
    extra_modules = [
        "Cloud Security", "Container Security", "DLP", 
        "Deception/Honeypot", "Sandbox", "WAF"
    ]
    
    x_pos = 50
    for mod in extra_modules:
        draw_rounded_rect(draw, (x_pos, y_extra + 30, x_pos + 150, y_extra + 70), BOX_COLOR)
        draw_text_centered(draw, mod, (x_pos, y_extra + 30, x_pos + 150, y_extra + 70), font_small)
        x_pos += 170
    
    # Stats
    y_stats = 680
    draw.text((50, y_stats), "STATISTICS:", font=font, fill=ACCENT_COLOR)
    
    stats = [
        ("Total Modules", "22"),
        ("Python Files", "79+"),
        ("Lines of Code", "18,000+"),
        ("Test Coverage", "Target: 90%"),
    ]
    
    x_stat = 50
    for label, value in stats:
        draw_rounded_rect(draw, (x_stat, y_stats + 30, x_stat + 180, y_stats + 90), (60, 60, 80))
        draw.text((x_stat + 20, y_stats + 40), label, font=font_small, fill=(180, 180, 180))
        draw.text((x_stat + 20, y_stats + 60), value, font=font, fill=ACCENT_COLOR)
        x_stat += 200
    
    img.save("amcis_security_modules.png", "PNG")
    print("Generated: amcis_security_modules.png")


def generate_data_flow():
    """Generate data flow diagram"""
    img = Image.new('RGB', (WIDTH, 700), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    font_small = get_font(12)
    font_title = get_font(24)
    
    # Title
    draw.text((WIDTH//2 - 150, 20), "AMCIS Data Flow Pipeline", 
              font=font_title, fill=ACCENT_COLOR)
    
    # Pipeline stages (horizontal)
    stages = [
        ("INPUT", 50, 100, [
            "Security Events",
            "Log Streams",
            "API Calls",
            "User Actions"
        ]),
        ("INGESTION", 300, 100, [
            "Normalize",
            "Enrich",
            "Validate"
        ]),
        ("PROCESSING", 550, 100, [
            "AI Detection",
            "Risk Analysis",
            "Correlation"
        ]),
        ("RESPONSE", 800, 100, [
            "Alert",
            "Auto-Remediate",
            "Escalate"
        ]),
        ("STORAGE", 1050, 100, [
            "Encrypt & Store",
            "Audit Trail",
            "Archive"
        ]),
    ]
    
    for stage_name, x, y, items in stages:
        # Stage header
        draw.text((x, y), stage_name, font=font, fill=ACCENT_COLOR)
        
        # Items
        y_item = y + 30
        for item in items:
            draw_rounded_rect(draw, (x, y_item, x + 180, y_item + 40), BOX_COLOR)
            draw_text_centered(draw, item, (x, y_item, x + 180, y_item + 40), font_small)
            y_item += 50
        
        # Arrow to next stage
        if x < 1000:
            draw.line([(x + 190, y + 100), (x + 240, y + 100)], 
                     fill=ACCENT_COLOR, width=3)
            # Arrowhead
            draw.polygon([(x + 240, y + 95), (x + 240, y + 105), (x + 250, y + 100)], 
                        fill=ACCENT_COLOR)
    
    # Processing details below
    y_detail = 350
    draw.text((50, y_detail), "DETAILED PROCESSING:", font=font, fill=ACCENT_COLOR)
    
    # Threat detection flow
    y_flow = y_detail + 40
    
    # Event in
    draw_rounded_rect(draw, (50, y_flow, 200, y_flow + 50), (80, 80, 100))
    draw_text_centered(draw, "Raw Event", (50, y_flow, 200, y_flow + 50), font_small)
    
    # Arrow
    draw.line([(200, y_flow + 25), (280, y_flow + 25)], fill=LINE_COLOR, width=2)
    
    # Normalization
    draw_rounded_rect(draw, (280, y_flow, 430, y_flow + 50), BOX_COLOR)
    draw_text_centered(draw, "Normalize", (280, y_flow, 430, y_flow + 50), font_small)
    
    # Arrow
    draw.line([(430, y_flow + 25), (510, y_flow + 25)], fill=LINE_COLOR, width=2)
    
    # AI Detection
    draw_rounded_rect(draw, (510, y_flow, 660, y_flow + 50), BOX_HIGHLIGHT)
    draw_text_centered(draw, "AI Detection", (510, y_flow, 660, y_flow + 50), font_small)
    
    # Decision diamond
    y_decision = y_flow + 80
    diamond_points = [(585, y_decision), (660, y_decision + 40), 
                      (585, y_decision + 80), (510, y_decision + 40)]
    draw.polygon(diamond_points, fill=(100, 100, 60), outline=LINE_COLOR)
    draw_text_centered(draw, "Threat?", (510, y_decision, 660, y_decision + 80), font_small)
    
    # Yes/No paths
    draw.text((670, y_decision + 30), "YES", font=font_small, fill=ACCENT_COLOR)
    draw.text((450, y_decision + 30), "NO", font=font_small, fill=(150, 150, 150))
    
    # Alert path
    draw.line([(660, y_decision + 40), (750, y_decision + 40)], fill=ACCENT_COLOR, width=2)
    draw_rounded_rect(draw, (750, y_decision + 15, 900, y_decision + 65), (120, 80, 80))
    draw_text_centered(draw, "Alert SOC", (750, y_decision + 15, 900, y_decision + 65), font_small)
    
    # Store path
    draw.line([(585, y_decision + 80), (585, y_decision + 130)], fill=LINE_COLOR, width=2)
    draw_rounded_rect(draw, (485, y_decision + 130, 685, y_decision + 180), (80, 100, 80))
    draw_text_centered(draw, "Store & Archive", (485, y_decision + 130, 685, y_decision + 180), font_small)
    
    img.save("amcis_data_flow.png", "PNG")
    print("Generated: amcis_data_flow.png")


def main():
    """Generate all diagrams"""
    print("=" * 60)
    print("GENERATING AMCIS ARCHITECTURE DIAGRAMS")
    print("=" * 60)
    print()
    
    try:
        print("1. System Architecture...")
        generate_system_architecture()
    except Exception as e:
        print(f"   Error: {e}")
    
    try:
        print("2. Deployment Architecture...")
        generate_deployment_diagram()
    except Exception as e:
        print(f"   Error: {e}")
    
    try:
        print("3. Security Modules...")
        generate_security_modules()
    except Exception as e:
        print(f"   Error: {e}")
    
    try:
        print("4. Data Flow...")
        generate_data_flow()
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("=" * 60)
    print("DIAGRAM GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
