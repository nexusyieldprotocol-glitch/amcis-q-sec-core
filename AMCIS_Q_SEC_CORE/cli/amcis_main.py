"""
AMCIS Main CLI Entrypoint
==========================

Command-line interface for AMCIS_Q_SEC_CORE security framework.

Commands:
- init: Initialize AMCIS security framework
- secure-run: Execute command with security monitoring
- verify-logs: Verify Merkle log integrity
- scan-surface: Scan local attack surface
- trust-report: Generate trust report
- rotate-keys: Rotate cryptographic keys
- forensic-export: Export forensic bundle
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import click
import structlog

# Import AMCIS modules - handle both module and direct execution
try:
    # Try relative imports first (when running as module)
    from ..core.amcis_kernel import AMCISKernel, SecurityEvent
    from ..core.amcis_trust_engine import TrustEngine, ExecutionContext
    from ..crypto.amcis_key_manager import KeyManager
    from ..crypto.amcis_merkle_log import MerkleLog
    from ..network.amcis_port_surface_mapper import PortSurfaceMapper
    from ..supply_chain.amcis_sbom_generator import SBOMGenerator, SBOMFormat
    from ..supply_chain.amcis_dependency_validator import DependencyValidator
except ImportError:
    # Fall back to absolute imports (when running directly)
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.amcis_kernel import AMCISKernel, SecurityEvent
    from core.amcis_trust_engine import TrustEngine, ExecutionContext
    from crypto.amcis_key_manager import KeyManager
    from crypto.amcis_merkle_log import MerkleLog
    from network.amcis_port_surface_mapper import PortSurfaceMapper
    from supply_chain.amcis_sbom_generator import SBOMGenerator, SBOMFormat
    from supply_chain.amcis_dependency_validator import DependencyValidator


# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """
    AMCIS Quantum-Secure Terminal Security Framework
    
    A modular, production-grade, quantum-secure security framework
    for terminal environments.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config'] = config
    
    if verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10)
        )


@cli.command()
@click.option('--enable-tpm', is_flag=True, help='Enable TPM hardware backing')
@click.option('--hsm-library', help='Path to HSM PKCS#11 library')
@click.pass_context
def init(ctx: click.Context, enable_tpm: bool, hsm_library: Optional[str]) -> None:
    """
    Initialize AMCIS security framework.
    
    Sets up the kernel, generates initial keys, establishes baselines,
    and prepares the system for secure operation.
    """
    click.echo("Initializing AMCIS Security Framework...")
    
    # Create directories
    base_dir = Path("/var/lib/amcis")
    for subdir in ['keys', 'logs', 'certs', 'forensics', 'provenance']:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    # Initialize kernel
    kernel = AMCISKernel(
        config_path=Path("/etc/amcis/kernel.conf"),
        enable_tpm=enable_tpm
    )
    
    # Run secure boot
    success = asyncio.run(kernel.secure_boot())
    
    if not success:
        click.echo("ERROR: Secure boot failed. Check logs for details.", err=True)
        sys.exit(1)
    
    # Initialize key manager
    key_manager = KeyManager(
        enable_tpm=enable_tpm,
        enable_hsm=hsm_library is not None,
        hsm_library=hsm_library
    )
    
    # Generate initial keys
    click.echo("Generating cryptographic keys...")
    from ..crypto.amcis_key_manager import KeyType
    key_manager.generate_key(KeyType.SYMMETRIC_AES_256, storage=key_manager.KeyStorage.FILE)
    key_manager.generate_key(KeyType.HMAC_SHA256, storage=key_manager.KeyStorage.FILE)
    
    # Initialize Merkle log
    merkle_log = MerkleLog()
    merkle_log.append({"event": "amcis_init", "version": "1.0.0"})
    
    click.echo("AMCIS initialized successfully.")
    click.echo(f"Kernel state: {kernel.get_state().name}")
    click.echo(f"Log entries: {merkle_log.get_entry_count()}")


@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.option('--strict', is_flag=True, help='Use strict trust evaluation')
@click.option('--sandbox', is_flag=True, help='Run in sandboxed environment')
@click.pass_context
def secure_run(ctx: click.Context, command: tuple, strict: bool, sandbox: bool) -> None:
    """
    Execute command with AMCIS security monitoring.
    
    Runs the specified command with trust evaluation, anomaly detection,
    and automatic response capabilities.
    """
    cmd_str = ' '.join(command)
    
    click.echo(f"Executing: {cmd_str}")
    
    # Initialize kernel
    kernel = AMCISKernel()
    
    if kernel.get_state().name != "OPERATIONAL":
        # Try to boot
        success = asyncio.run(kernel.secure_boot())
        if not success:
            click.echo("ERROR: Kernel not operational", err=True)
            sys.exit(1)
    
    # Initialize trust engine
    trust_engine = TrustEngine(kernel=kernel)
    
    # Create execution context
    exec_context = ExecutionContext(
        command=command[0],
        arguments=list(command[1:]),
        working_directory=Path.cwd(),
        environment=dict(os.environ),
        user_id=os.getuid() if hasattr(os, 'getuid') else 0,
        session_id=f"cli_{int(time.time())}"
    )
    
    # Evaluate trust
    click.echo("Evaluating trust...")
    trust_score = asyncio.run(trust_engine.evaluate(exec_context, strict_mode=strict))
    
    click.echo(f"Trust score: {trust_score.overall_score:.2f} (threshold: {trust_score.threshold:.2f})")
    
    if not trust_score.passed:
        click.echo("ERROR: Trust evaluation failed. Command blocked.", err=True)
        click.echo(f"Details: {json.dumps(trust_score.details, indent=2)}")
        sys.exit(1)
    
    # Execute command
    click.echo("Trust evaluation passed. Executing command...")
    
    import subprocess
    result = subprocess.run(command)
    sys.exit(result.returncode)


@cli.command()
@click.option('--start-index', default=0, help='Start verification from index')
@click.pass_context
def verify_logs(ctx: click.Context, start_index: int) -> None:
    """
    Verify Merkle log integrity.
    
    Verifies the cryptographic integrity of the append-only log,
    detecting any tampering or corruption.
    """
    click.echo("Verifying Merkle log integrity...")
    
    merkle_log = MerkleLog()
    
    valid, errors = merkle_log.verify_log()
    
    if valid:
        click.echo("OK Log integrity verified successfully.")
        click.echo(f"  Total entries: {merkle_log.get_entry_count()}")
        click.echo(f"  Root hash: {merkle_log.get_root_hash()[:16]}...")
    else:
        click.echo("FAIL Log integrity verification FAILED!")
        for error in errors[:10]:
            click.echo(f"  - {error}")
        sys.exit(1)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to scan')
@click.option('--ports', help='Comma-separated ports (default: common ports)')
@click.pass_context
def scan_surface(ctx: click.Context, host: str, ports: Optional[str]) -> None:
    """
    Scan local attack surface.
    
    Identifies open ports, exposed services, and potential
    vulnerabilities on the local system.
    """
    click.echo(f"Scanning attack surface on {host}...")
    
    mapper = PortSurfaceMapper()
    
    port_list = None
    if ports:
        port_list = [int(p) for p in ports.split(',')]
    
    report = mapper.scan_host(host, ports=port_list)
    
    click.echo(f"\nScan Results:")
    click.echo(f"  Open ports: {len(report.open_ports)}")
    click.echo(f"  Risk score: {report.risk_score}/100")
    
    if report.open_ports:
        click.echo(f"\n  Open Services:")
        for service in report.open_ports[:10]:
            click.echo(f"    {service.port}/{service.protocol}: {service.service_name or 'unknown'} ({service.risk_level.name})")
    
    if report.critical_services:
        click.echo(f"\n  [!] CRITICAL Services:")
        for service in report.critical_services:
            click.echo(f"    Port {service.port}: {', '.join(service.risk_reasons)}")
    
    if report.recommendations:
        click.echo(f"\n  Recommendations:")
        for rec in report.recommendations:
            click.echo(f"    - {rec}")


@cli.command()
@click.pass_context
def trust_report(ctx: click.Context) -> None:
    """
    Generate trust evaluation report.
    
    Displays current trust engine status, verified signatures,
    and baseline statistics.
    """
    click.echo("Generating trust report...")
    
    trust_engine = TrustEngine()
    report = trust_engine.get_trust_report()
    
    click.echo("\nTrust Engine Report:")
    click.echo(f"  Current threshold: {report['threshold']}")
    click.echo(f"  Verified signatures: {report['verified_signatures_count']}")
    click.echo(f"  Command history: {report['command_history_size']}")
    click.echo(f"  Baseline commands: {report['baseline_commands']}")


@cli.command()
@click.option('--key-id', help='Specific key to rotate (default: all)')
@click.pass_context
def rotate_keys(ctx: click.Context, key_id: Optional[str]) -> None:
    """
    Rotate cryptographic keys.
    
    Generates new keys and expires old ones, maintaining
    secure key lifecycle.
    """
    click.echo("Rotating cryptographic keys...")
    
    key_manager = KeyManager()
    
    if key_id:
        new_key = key_manager.rotate_key(key_id)
        if new_key:
            click.echo(f"OK Rotated key: {key_id} -> {new_key.key_id}")
        else:
            click.echo(f"FAIL Failed to rotate key: {key_id}")
            sys.exit(1)
    else:
        # Rotate all keys needing rotation
        keys_to_rotate = key_manager.check_rotation_needed()
        
        if not keys_to_rotate:
            click.echo("No keys require rotation at this time.")
            return
        
        for key in keys_to_rotate:
            new_key = key_manager.rotate_key(key.key_id)
            if new_key:
                click.echo(f"OK Rotated: {key.key_id} -> {new_key.key_id}")


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def forensic_export(ctx: click.Context, output: Optional[str]) -> None:
    """
    Export forensic bundle.
    
    Creates a tamper-evident bundle of security logs,
    process snapshots, and system state for investigation.
    """
    click.echo("Exporting forensic bundle...")
    
    from ..core.amcis_response_engine import ResponseEngine
    
    response_engine = ResponseEngine()
    
    action = response_engine.ResponseAction(
        action_type=response_engine.ResponseActionType.EXPORT_FORENSICS,
        severity=response_engine.ResponseSeverity.LOW
    )
    
    result = asyncio.run(response_engine.execute_action(action))
    
    if result.success:
        click.echo(f"OK Forensic bundle created: {result.details.get('bundle_path')}")
        click.echo(f"  Bundle size: {result.details.get('bundle_size', 0)} bytes")
    else:
        click.echo(f"FAIL Export failed: {result.message}")
        sys.exit(1)


@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--format', 'output_format', default='spdx-json', 
              type=click.Choice(['spdx-json', 'cyclonedx-json']))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def generate_sbom(ctx: click.Context, project_path: str, output_format: str, output: Optional[str]) -> None:
    """
    Generate SBOM for project.
    
    Creates a Software Bill of Materials in SPDX or CycloneDX format.
    """
    click.echo(f"Generating SBOM for {project_path}...")
    
    generator = SBOMGenerator()
    
    fmt = SBOMFormat.SPDX_JSON if output_format == 'spdx-json' else SBOMFormat.CYCLONE_DX_JSON
    
    sbom = generator.generate_from_path(
        project_path=Path(project_path),
        format=fmt
    )
    
    if output:
        output_path = generator.export_sbom(sbom, Path(output))
        click.echo(f"OK SBOM exported: {output_path}")
    else:
        click.echo(json.dumps(sbom.to_dict(), indent=2))


@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.pass_context
def validate_deps(ctx: click.Context, project_path: str) -> None:
    """
    Validate project dependencies.
    
    Scans for known vulnerabilities and compliance issues
    in project dependencies.
    """
    click.echo(f"Validating dependencies for {project_path}...")
    
    validator = DependencyValidator()
    report = validator.validate_project(Path(project_path))
    
    click.echo(f"\nValidation Results:")
    click.echo(f"  Total packages: {report.total_packages}")
    click.echo(f"  Vulnerable packages: {report.vulnerable_packages}")
    click.echo(f"  Critical: {report.critical_count}")
    click.echo(f"  High: {report.high_count}")
    click.echo(f"  Medium: {report.medium_count}")
    click.echo(f"  Low: {report.low_count}")
    
    click.echo(f"\n  {report.summary}")
    
    if report.issues:
        click.echo(f"\n  Top Issues:")
        for issue in report.issues[:5]:
            click.echo(f"    - [{issue.severity.value}] {issue.package_name}: {issue.details[:50]}...")
    
    if report.critical_count > 0:
        sys.exit(1)


@cli.command()
@click.pass_context
def compliance_report(ctx: click.Context) -> None:
    """
    Generate compliance report.
    
    Maps AMCIS security controls to NIST, ISO 27001, SOC 2, and PCI DSS.
    """
    click.echo("Generating compliance report...")
    
    try:
        from compliance.compliance_engine import ComplianceEngine, Framework
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from compliance.compliance_engine import ComplianceEngine, Framework
    
    engine = ComplianceEngine()
    
    # Add sample evidence
    engine.assess_control("AC-2", Framework.NIST_800_53, ["trust_engine_active", "key_rotation_enabled"])
    engine.assess_control("AU-6", Framework.NIST_800_53, ["anomaly_detection_active", "log_integrity_verified"])
    engine.assess_control("SC-7", Framework.NIST_800_53, ["microsegmentation_enabled", "firewall_rules_active"])
    
    click.echo("\nCompliance Status by Framework:")
    click.echo("-" * 50)
    
    for framework in [Framework.NIST_800_53, Framework.ISO_27001, Framework.SOC_2]:
        status = engine.get_framework_status(framework)
        click.echo(f"\n{framework.value.upper()}:")
        click.echo(f"  Score: {status['score']:.1f}%")
        click.echo(f"  Controls: {status['compliant']}/{status['total_controls']} compliant")
        
        if status['partial'] > 0:
            click.echo(f"  Partial: {status['partial']}")
        if status['non_compliant'] > 0:
            click.echo(f"  Non-compliant: {status['non_compliant']}")


@cli.command()
@click.pass_context
def threat_intel(ctx: click.Context) -> None:
    """
    Display threat intelligence status.
    
    Shows IOC database, threat actors, and recent matches.
    """
    click.echo("Loading threat intelligence...")
    
    try:
        from threat_intel.threat_feed import ThreatFeed
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from threat_intel.threat_feed import ThreatFeed
    
    feed = ThreatFeed()
    stats = feed.get_statistics()
    
    click.echo("\nThreat Intelligence Statistics:")
    click.echo(f"  Total IOCs: {stats['total_iocs']}")
    click.echo(f"  Threat Actors: {stats['threat_actors']}")
    
    if stats['by_type']:
        click.echo("\n  IOCs by Type:")
        for ioc_type, count in stats['by_type'].items():
            click.echo(f"    {ioc_type}: {count}")
    
    # Show threat actors
    click.echo("\nTracked Threat Actors:")
    for name in ["APT28", "APT29", "Lazarus Group"]:
        actor = feed.get_actor_profile(name)
        if actor:
            click.echo(f"  {actor.name} ({actor.country or 'Unknown'})")
            click.echo(f"    Targets: {', '.join(actor.targets[:3])}")


@cli.command()
@click.argument('text')
@click.pass_context
def check_dlp(ctx: click.Context, text: str) -> None:
    """
    Check text for sensitive data (DLP).
    
    Detects PII, PHI, PCI, and other sensitive information.
    """
    try:
        from dlp.dlp_engine import DLPEngine
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from dlp.dlp_engine import DLPEngine
    
    engine = DLPEngine()
    violations = engine.inspect_content(text)
    
    if violations:
        click.echo(f"Found {len(violations)} DLP violations:")
        for v in violations:
            click.echo(f"  [{v.data_type.value}] Confidence: {v.confidence}%")
            click.echo(f"    Action: {v.action_taken.name}")
            click.echo(f"    Snippet: {v.snippet[:30]}...")
        
        # Show masked version
        masked = engine.mask_content(text, violations)
        click.echo(f"\nMasked content: {masked}")
    else:
        click.echo("No sensitive data detected.")


@cli.command()
@click.pass_context
def waf_test(ctx: click.Context) -> None:
    """
    Test WAF rules against sample requests.
    
    Demonstrates OWASP Top 10 protection.
    """
    try:
        from waf.waf_engine import WAFEngine, HTTPRequest
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from waf.waf_engine import WAFEngine, HTTPRequest
    
    waf = WAFEngine()
    
    test_requests = [
        ("Normal Request", HTTPRequest("GET", "/api/users", {}, {}, "", "192.168.1.1", "Mozilla/5.0")),
        ("SQL Injection", HTTPRequest("GET", "/search", {"q": ["' OR 1=1 --"]}, {}, "", "192.168.1.2", "Mozilla/5.0")),
        ("XSS Attempt", HTTPRequest("POST", "/comment", {}, {}, "<script>alert('xss')</script>", "192.168.1.3", "Mozilla/5.0")),
        ("Path Traversal", HTTPRequest("GET", "/download", {"file": ["../../../etc/passwd"]}, {}, "", "192.168.1.4", "Mozilla/5.0")),
    ]
    
    click.echo("WAF Rule Testing:\n")
    
    for name, req in test_requests:
        decision = waf.inspect_request(req)
        status = "ALLOWED" if decision.allowed else "BLOCKED"
        click.echo(f"{name:20} -> {status}")
        if decision.matched_rules:
            click.echo(f"  Rules: {', '.join(r.rule_id for r in decision.matched_rules[:2])}")


@cli.command()
@click.pass_context
def dashboard(ctx: click.Context) -> None:
    """
    Display security dashboard summary.
    
    Shows security score, alerts, and metrics.
    """
    try:
        from dashboard.metrics_collector import MetricsCollector
        from dashboard.alert_manager import AlertManager, AlertSeverity
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from dashboard.metrics_collector import MetricsCollector
        from dashboard.alert_manager import AlertManager, AlertSeverity
    
    metrics = MetricsCollector()
    alerts = AlertManager()
    
    # Generate sample alerts
    alerts.create_alert(
        "Suspicious Login Attempt",
        "Multiple failed login attempts detected from unusual IP",
        AlertSeverity.HIGH,
        "auth_system"
    )
    
    # Display dashboard
    click.echo("="*60)
    click.echo("AMCIS Security Dashboard")
    click.echo("="*60)
    
    summary = metrics.get_dashboard_summary()
    click.echo(f"\nSecurity Score: {summary['security_score']}/100")
    click.echo(f"Threats Detected (1h): {summary['threats_detected_1h']}")
    click.echo(f"Attacks Blocked (1h): {summary['attacks_blocked_1h']}")
    
    alert_stats = alerts.get_statistics()
    click.echo(f"\nActive Alerts: {alert_stats['open_alerts']}")
    if alert_stats['by_severity']:
        click.echo("By Severity:")
        for sev, count in alert_stats['by_severity'].items():
            click.echo(f"  {sev}: {count}")


def main() -> None:
    """Main entrypoint."""
    cli()


if __name__ == '__main__':
    main()
