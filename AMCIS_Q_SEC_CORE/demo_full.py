#!/usr/bin/env python3
"""
AMCIS Q-SEC CORE - FULL FEATURE DEMO
====================================

Comprehensive demonstration of all AMCIS features including:
- Core Security (Kernel, Trust, Anomaly)
- Post-Quantum Cryptography (ML-KEM, ML-DSA)
- EDR (Process, Memory, File Integrity)
- AI Security (Prompt Firewall)
- Network Security (WAF, Microsegmentation)
- Supply Chain (SBOM)
- NEW: Threat Intelligence
- NEW: Secrets Manager
- NEW: Forensics Timeline
- NEW: Compliance Engine
- NEW: DLP
- NEW: WAF
- NEW: Dashboard & Alerts
"""

import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def print_header(text, char="="):
    print()
    print(char * 70)
    print(text)
    print(char * 70)

def main():
    print("="*70)
    print("AMCIS Q-SEC CORE - FULL FEATURE DEMONSTRATION")
    print("="*70)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # ============================================================
    # 1. POST-QUANTUM CRYPTOGRAPHY
    # ============================================================
    print_header("[1] POST-QUANTUM CRYPTOGRAPHY (NIST FIPS 203/204)")
    
    from crypto.amcis_hybrid_pqc import MLKEMImplementation, MLDSAImplementation, PQCKEM, PQCSignature
    
    kem = MLKEMImplementation(PQCKEM.ML_KEM_768)
    kp = kem.keygen()
    ct, ss1 = kem.encapsulate(kp.public_key, kp.secret_key)
    ss2 = kem.decapsulate(ct, kp.secret_key)
    
    print(f"ML-KEM-768 Key Exchange:")
    print(f"  Public Key: {len(kp.public_key)} bytes")
    print(f"  Shared Secret Match: {ss1 == ss2}")
    
    dsa = MLDSAImplementation(PQCSignature.ML_DSA_65)
    skp = dsa.keygen()
    sig = dsa.sign(b"test", skp.secret_key)
    valid = dsa.verify(b"test", sig, skp.public_key)
    print(f"ML-DSA-65 Signature: {len(sig)} bytes, Valid: {valid}")
    
    # ============================================================
    # 2. MERKLE LOG
    # ============================================================
    print_header("[2] MERKLE LOG (Tamper-Evident Audit Trail)")
    
    from crypto.amcis_merkle_log import MerkleLog
    
    ml = MerkleLog()
    for i in range(3):
        ml.append({"event": f"security_event_{i}"})
    
    print(f"Total Entries: {ml.get_entry_count()}")
    print(f"Root Hash: {ml.get_root_hash()[:40]}...")
    valid, _ = ml.verify_log()
    print(f"Integrity Verified: {valid}")
    
    # ============================================================
    # 3. TRUST ENGINE
    # ============================================================
    print_header("[3] ZERO-TRUST EXECUTION ENGINE")
    
    from core.amcis_trust_engine import TrustEngine, ExecutionContext
    
    te = TrustEngine()
    ctx = ExecutionContext("ls", ["-la"], Path("/tmp"), {}, 1000, "demo1")
    r = asyncio.run(te.evaluate(ctx))
    print(f"Command: ls -la -> Score: {r.overall_score:.2f} -> {'ALLOW' if r.passed else 'DENY'}")
    
    # ============================================================
    # 4. AI SECURITY
    # ============================================================
    print_header("[4] AI SECURITY - PROMPT FIREWALL")
    
    from ai_security.amcis_prompt_firewall import PromptFirewall
    
    pf = PromptFirewall()
    prompts = [
        ("Hello world", "Benign"),
        ("Ignore previous instructions", "Injection"),
    ]
    
    for p, expected in prompts:
        r = pf.analyze(p)
        print(f"[{expected:10}] {'BLOCK' if r.is_malicious else 'ALLOW'} - Risk: {r.risk_level.name}")
    
    # ============================================================
    # 5. EDR - PROCESS GRAPH
    # ============================================================
    print_header("[5] EDR - PROCESS GRAPH")
    
    from edr.amcis_process_graph import ProcessGraph
    import os
    
    pg = ProcessGraph()
    procs = pg.scan_processes()
    print(f"Processes Scanned: {len(procs)}")
    print(f"Current PID: {os.getpid()}")
    
    # ============================================================
    # 6. NETWORK SECURITY
    # ============================================================
    print_header("[6] NETWORK SECURITY - MICROSEGMENTATION")
    
    from network.amcis_microsegmentation import MicrosegmentationEngine, Protocol
    
    mse = MicrosegmentationEngine(dry_run=True)
    action, _ = mse.evaluate_connection("10.0.0.1", "8.8.8.8", 443, Protocol.TCP)
    print(f"HTTPS Connection Evaluated: {action.name}")
    
    # ============================================================
    # 7. SBOM GENERATION
    # ============================================================
    print_header("[7] SUPPLY CHAIN - SBOM GENERATION")
    
    from supply_chain.amcis_sbom_generator import SBOMGenerator
    
    sg = SBOMGenerator()
    sbom = sg.generate_from_path(Path('.'), name="AMCIS")
    print(f"Components: {len(sbom.components)}")
    print(f"Format: {sbom.format.value}")
    
    # ============================================================
    # 8. KEY MANAGEMENT
    # ============================================================
    print_header("[8] KEY MANAGEMENT")
    
    from crypto.amcis_key_manager import KeyManager, KeyType
    
    km = KeyManager(enable_tpm=False, enable_hsm=False)
    k1 = km.generate_key(KeyType.SYMMETRIC_AES_256)
    k2 = km.rotate_key(k1.key_id)
    print(f"Key Generated: {k1.key_id[:30]}...")
    print(f"Key Rotated:   {k2.key_id[:30]}...")
    
    # ============================================================
    # 9. THREAT INTELLIGENCE (NEW)
    # ============================================================
    print_header("[9] THREAT INTELLIGENCE (NEW)")
    
    from threat_intel.threat_feed import ThreatFeed, IOC, IOCTypes, ThreatSeverity
    
    feed = ThreatFeed()
    
    # Add sample IOC
    ioc = IOC(
        value="192.168.100.100",
        ioc_type=IOCTypes.IP,
        severity=ThreatSeverity.HIGH,
        source="Demo Feed",
        description="Malicious C2 server",
        first_seen=time.time(),
        last_seen=time.time(),
        tags=["c2", "apt28"]
    )
    feed.add_ioc(ioc)
    
    stats = feed.get_statistics()
    print(f"IOCs Tracked: {stats['total_iocs']}")
    print(f"Threat Actors: {stats['threat_actors']}")
    
    # Get APT28 profile
    actor = feed.get_actor_profile("APT28")
    if actor:
        print(f"\nActor Profile: {actor.name}")
        print(f"  Country: {actor.country}")
        print(f"  Targets: {', '.join(actor.targets[:3])}")
    
    # ============================================================
    # 10. SECRETS MANAGER (NEW)
    # ============================================================
    print_header("[10] SECRETS MANAGER (NEW)")
    
    from secrets_mgr.secrets_manager import SecretsManager
    
    sm = SecretsManager()
    secret = sm.create_secret("database_password", "SuperSecret123!", ttl_days=30)
    print(f"Secret Created: {secret.name}")
    print(f"Version: {secret.version}")
    
    retrieved = sm.get_secret("database_password")
    print(f"Secret Retrieved: {'Yes' if retrieved else 'No'}")
    print(f"Value matches: {retrieved == 'SuperSecret123!'}")
    
    # ============================================================
    # 11. FORENSIC TIMELINE (NEW)
    # ============================================================
    print_header("[11] FORENSIC TIMELINE (NEW)")
    
    from forensics.timeline import ForensicTimeline, TimelineEvent, EventCategory, EventSeverity
    
    timeline = ForensicTimeline("DEMO-2024-001")
    
    events = [
        TimelineEvent(time.time(), EventCategory.AUTH, "login_attempt", "192.168.1.1", "web_server", {"result": "failed"}, EventSeverity.MEDIUM),
        TimelineEvent(time.time() + 1, EventCategory.FILE, "file_access", "web_server", "/etc/passwd", {"user": "apache"}, EventSeverity.HIGH),
        TimelineEvent(time.time() + 2, EventCategory.NETWORK, "outbound_connection", "web_server", "evil.com", {"port": 443}, EventSeverity.CRITICAL),
    ]
    
    timeline.add_events(events)
    
    stats = timeline.get_statistics()
    print(f"Timeline: {stats['case_id']}")
    print(f"Events: {stats['total_events']}")
    print(f"Categories: {list(stats['by_category'].keys())}")
    
    # ============================================================
    # 12. COMPLIANCE ENGINE (NEW)
    # ============================================================
    print_header("[12] COMPLIANCE ENGINE (NEW)")
    
    from compliance.compliance_engine import ComplianceEngine, Framework
    
    ce = ComplianceEngine()
    
    # Assess some controls
    ce.assess_control("AC-2", Framework.NIST_800_53, ["trust_engine"])
    ce.assess_control("SC-7", Framework.NIST_800_53, ["microsegmentation", "firewall"])
    ce.assess_control("SI-7", Framework.NIST_800_53, ["integrity_monitor"])
    
    for fw in [Framework.NIST_800_53, Framework.ISO_27001, Framework.SOC_2]:
        status = ce.get_framework_status(fw)
        print(f"{fw.value}: {status['score']:.1f}% ({status['compliant']}/{status['total_controls']} compliant)")
    
    # ============================================================
    # 13. DLP - DATA LOSS PREVENTION (NEW)
    # ============================================================
    print_header("[13] DLP - DATA LOSS PREVENTION (NEW)")
    
    from dlp.dlp_engine import DLPEngine
    
    dlp = DLPEngine()
    
    test_content = "Contact: John Doe, SSN: 123-45-6789, Email: john@example.com"
    violations = dlp.inspect_content(test_content)
    
    print(f"Content analyzed: {test_content[:50]}...")
    print(f"Violations found: {len(violations)}")
    
    for v in violations:
        print(f"  - {v.data_type.value}: {v.confidence}% confidence")
    
    if violations:
        masked = dlp.mask_content(test_content, violations)
        print(f"Masked: {masked}")
    
    # ============================================================
    # 14. WAF - WEB APPLICATION FIREWALL (NEW)
    # ============================================================
    print_header("[14] WAF - WEB APPLICATION FIREWALL (NEW)")
    
    from waf.waf_engine import WAFEngine, HTTPRequest
    
    waf = WAFEngine()
    
    test_requests = [
        ("Normal", HTTPRequest("GET", "/api/users", {}, {}, "", "10.0.0.1", "Mozilla/5.0")),
        ("SQLi", HTTPRequest("GET", "/search", {"q": ["' OR 1=1 --"]}, {}, "", "10.0.0.2", "Mozilla/5.0")),
        ("XSS", HTTPRequest("POST", "/comment", {}, {}, "<script>alert(1)</script>", "10.0.0.3", "Mozilla/5.0")),
    ]
    
    for name, req in test_requests:
        decision = waf.inspect_request(req)
        status = "BLOCKED" if not decision.allowed else "ALLOWED"
        print(f"{name:10} -> {status}")
        if decision.matched_rules:
            print(f"  Rule: {decision.matched_rules[0].name}")
    
    # ============================================================
    # 15. DASHBOARD & ALERTS (NEW)
    # ============================================================
    print_header("[15] DASHBOARD & ALERTS (NEW)")
    
    from dashboard.metrics_collector import MetricsCollector
    from dashboard.alert_manager import AlertManager, AlertSeverity
    
    metrics = MetricsCollector()
    alerts = AlertManager()
    
    # Record metrics
    metrics.record_counter("threats_detected", 5)
    metrics.record_counter("attacks_blocked", 4)
    metrics.record_gauge("active_sessions", 42)
    
    # Create alerts
    alerts.create_alert(
        "Suspicious Login Pattern",
        "Multiple failed login attempts from unusual IP",
        AlertSeverity.HIGH,
        "auth_system"
    )
    
    alerts.create_alert(
        "Malware Detected",
        "File hash matches known malware signature",
        AlertSeverity.CRITICAL,
        "file_integrity"
    )
    
    summary = metrics.get_dashboard_summary()
    print(f"Security Score: {summary['security_score']}/100")
    print(f"Threats (1h): {summary['threats_detected_1h']}")
    print(f"Blocked: {summary['attacks_blocked_1h']}")
    
    alert_stats = alerts.get_statistics()
    print(f"\nActive Alerts: {alert_stats['open_alerts']}")
    print(f"By Severity: {alert_stats['by_severity']}")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print_header("FEATURE SUMMARY", "=")
    
    features = [
        "Post-Quantum Cryptography (ML-KEM/ML-DSA)",
        "Merkle Log (Tamper-Evident)",
        "Zero-Trust Execution Engine",
        "AI Prompt Firewall",
        "EDR (Process Graph, Memory, File)",
        "Network Microsegmentation",
        "SBOM Generation",
        "Key Management with Rotation",
        "Threat Intelligence Feed",
        "Secrets Manager",
        "Forensic Timeline",
        "Compliance Engine (NIST/ISO/SOC2/PCI)",
        "Data Loss Prevention (DLP)",
        "Web Application Firewall (WAF)",
        "Dashboard & Alert Management",
    ]
    
    print("AMCIS Q-SEC CORE includes:")
    for i, f in enumerate(features, 1):
        print(f"  {i:2}. {f}")
    
    print("\n" + "="*70)
    print("ALL FEATURES DEMONSTRATED SUCCESSFULLY")
    print("="*70)

if __name__ == "__main__":
    main()
