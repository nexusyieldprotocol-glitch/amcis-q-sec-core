"""
AMCIS Port Surface Mapper
==========================

Local attack surface scanning and port mapping for identifying
exposed services and potential vulnerabilities.

Features:
- Local port scanning
- Service fingerprinting
- Exposure analysis
- Risk scoring

NIST Alignment: SP 800-53 (RA-5 Vulnerability Scanning)
"""

import socket
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

try:
    from core.amcis_exceptions import NetworkException, ErrorCode
    from core.amcis_error_utils import safe_method, retry, timing_context
except ImportError:
    from ..core.amcis_exceptions import NetworkException, ErrorCode
    from ..core.amcis_error_utils import safe_method, retry, timing_context


class PortState(Enum):
    """Port states."""
    OPEN = auto()
    CLOSED = auto()
    FILTERED = auto()
    UNKNOWN = auto()


class ServiceRisk(Enum):
    """Service risk levels."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class PortService:
    """Port service information."""
    port: int
    protocol: str
    state: PortState
    service_name: Optional[str]
    version: Optional[str]
    banner: Optional[str]
    process_name: Optional[str]
    process_pid: Optional[int]
    risk_level: ServiceRisk
    risk_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "port": self.port,
            "protocol": self.protocol,
            "state": self.state.name,
            "service_name": self.service_name,
            "version": self.version,
            "banner": self.banner[:100] if self.banner else None,
            "process_name": self.process_name,
            "process_pid": self.process_pid,
            "risk_level": self.risk_level.name,
            "risk_reasons": self.risk_reasons
        }


@dataclass
class SurfaceReport:
    """Attack surface report."""
    total_ports_scanned: int
    open_ports: List[PortService]
    listening_interfaces: List[str]
    risk_score: float
    critical_services: List[PortService]
    recommendations: List[str]
    scan_duration_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_ports_scanned": self.total_ports_scanned,
            "open_count": len(self.open_ports),
            "listening_interfaces": self.listening_interfaces,
            "risk_score": self.risk_score,
            "critical_count": len(self.critical_services),
            "recommendations": self.recommendations,
            "scan_duration_ms": self.scan_duration_ms
        }


class PortSurfaceMapper:
    """
    AMCIS Port Surface Mapper
    =========================
    
    Local attack surface scanner for identifying exposed
    services and potential security risks.
    """
    
    # Common ports to scan
    COMMON_PORTS = [
        21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
        1433, 1521, 3306, 3389, 5432, 5900, 5985, 6379, 8080,
        8443, 9200, 27017
    ]
    
    # High-risk services
    HIGH_RISK_SERVICES = {
        23: "Telnet (unencrypted)",
        21: "FTP (often unencrypted)",
        3389: "RDP (exposed remote desktop)",
        5900: "VNC (often unencrypted)",
        445: "SMB (potential vulnerability)",
        135: "RPC (potential vulnerability)",
        5985: "WinRM (potential vulnerability)",
    }
    
    # Service fingerprints
    SERVICE_BANNERS = {
        b"SSH-": "SSH",
        b"220": "FTP/SMTP",
        b"HTTP/": "HTTP",
        b"MySQL": "MySQL",
        b"redis": "Redis",
    }
    
    def __init__(self, kernel=None) -> None:
        """
        Initialize port surface mapper.
        
        Args:
            kernel: AMCIS kernel reference
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.port_surface_mapper")
        
        # Scan results cache
        self._last_scan: Optional[SurfaceReport] = None
        self._scan_history: List[SurfaceReport] = []
        
        self.logger.info("port_surface_mapper_initialized")
    
    @safe_method(default=None, error_code=ErrorCode.NETWORK_ERROR)
    def scan_host(
        self,
        host: str = "127.0.0.1",
        ports: Optional[List[int]] = None,
        timeout: float = 1.0,
        max_workers: int = 50
    ) -> SurfaceReport:
        """
        Scan host for open ports.
        
        Args:
            host: Host to scan
            ports: Ports to scan (default: common ports)
            timeout: Connection timeout
            max_workers: Thread pool size
            
        Returns:
            Scan report
        """
        import time
        start_time = time.time()
        
        ports = ports or self.COMMON_PORTS
        open_ports = []
        
        with timing_context("port_scan", threshold_ms=5000):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._check_port, host, port, timeout): port
                    for port in ports
                }
                
                for future in as_completed(futures):
                    port = futures[future]
                    try:
                        service = future.result()
                        if service and service.state == PortState.OPEN:
                            open_ports.append(service)
                            self.logger.debug("port_open", port=port, service=service.service_name)
                    except NetworkException:
                        raise
                    except Exception as e:
                        self.logger.debug("scan_error", port=port, error=str(e))
        
        # Analyze services
        for service in open_ports:
            self._analyze_service_risk(service)
        
        # Get listening interfaces
        interfaces = self._get_listening_interfaces()
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(open_ports)
        
        # Get critical services
        critical = [s for s in open_ports if s.risk_level == ServiceRisk.CRITICAL]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(open_ports)
        
        duration = (time.time() - start_time) * 1000
        
        report = SurfaceReport(
            total_ports_scanned=len(ports),
            open_ports=open_ports,
            listening_interfaces=interfaces,
            risk_score=risk_score,
            critical_services=critical,
            recommendations=recommendations,
            scan_duration_ms=duration
        )
        
        self._last_scan = report
        self._scan_history.append(report)
        
        self.logger.info(
            "scan_complete",
            host=host,
            open_count=len(open_ports),
            risk_score=risk_score
        )
        
        return report
    
    @retry(max_retries=2, delay=0.05, exceptions=(NetworkException,))
    def _check_port(self, host: str, port: int, timeout: float) -> Optional[PortService]:
        """Check if port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                
                if result == 0:
                    # Port is open, try to get banner
                    banner = self._grab_banner(sock, port)
                    service_name = self._identify_service(port, banner)
                    
                    return PortService(
                        port=port,
                        protocol="tcp",
                        state=PortState.OPEN,
                        service_name=service_name,
                        version=None,
                        banner=banner,
                        process_name=None,
                        process_pid=None,
                        risk_level=ServiceRisk.LOW
                    )
                elif result == 111 or result == 10061:  # ECONNREFUSED (Linux/Windows)
                    return PortService(
                        port=port,
                        protocol="tcp",
                        state=PortState.CLOSED,
                        service_name=None,
                        version=None,
                        banner=None,
                        process_name=None,
                        process_pid=None,
                        risk_level=ServiceRisk.LOW
                    )
                else:
                    return PortService(
                        port=port,
                        protocol="tcp",
                        state=PortState.CLOSED,
                        service_name=None,
                        version=None,
                        banner=None,
                        process_name=None,
                        process_pid=None,
                        risk_level=ServiceRisk.LOW
                    )
        except socket.timeout:
            return PortService(
                port=port,
                protocol="tcp",
                state=PortState.FILTERED,
                service_name=None,
                version=None,
                banner=None,
                process_name=None,
                process_pid=None,
                risk_level=ServiceRisk.LOW
            )
        except socket.error as e:
            error_code = ErrorCode.CONNECTION_REFUSED if e.errno == 111 else ErrorCode.NETWORK_ERROR
            raise NetworkException(
                f"Socket error while checking port {port}: {str(e)}",
                error_code=error_code,
                details={'host': host, 'port': port, 'errno': e.errno}
            ) from e
        except Exception as e:
            self.logger.debug("port_check_unexpected_error", host=host, port=port, error=str(e))
            return None
    
    @safe_method(default=None, error_code=ErrorCode.NETWORK_ERROR)
    def _grab_banner(self, sock: socket.socket, port: int) -> Optional[str]:
        """Try to grab service banner."""
        with timing_context("grab_banner", threshold_ms=500):
            try:
                # Send appropriate probe
                if port == 80 or port == 8080:
                    sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                else:
                    sock.send(b"\r\n")
                
                banner = sock.recv(1024)
                return banner.decode('utf-8', errors='ignore').strip()
            except socket.timeout:
                self.logger.debug("banner_grab_timeout", port=port)
                return None
    
    def _identify_service(self, port: int, banner: Optional[str]) -> Optional[str]:
        """Identify service from port and banner."""
        # Common port mappings
        common_services = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            993: "IMAPS",
            995: "POP3S",
            1433: "MSSQL",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            5900: "VNC",
            6379: "Redis",
            8080: "HTTP-Proxy",
            27017: "MongoDB",
        }
        
        # Check banner first
        if banner:
            banner_bytes = banner.encode()
            for signature, service in self.SERVICE_BANNERS.items():
                if signature in banner_bytes:
                    return service
        
        return common_services.get(port)
    
    def _analyze_service_risk(self, service: PortService) -> None:
        """Analyze service risk level."""
        reasons = []
        
        # Check for high-risk port
        if service.port in self.HIGH_RISK_SERVICES:
            service.risk_level = ServiceRisk.HIGH
            reasons.append(f"High-risk service: {self.HIGH_RISK_SERVICES[service.port]}")
        
        # Check for outdated service (based on banner)
        if service.banner:
            if "SSH-1." in service.banner:
                service.risk_level = ServiceRisk.CRITICAL
                reasons.append("Outdated SSH version 1")
        
        # Check for unencrypted services
        unencrypted = [21, 23, 25, 110, 143, 5900]
        if service.port in unencrypted:
            service.risk_level = max(service.risk_level, ServiceRisk.MEDIUM)
            reasons.append("Unencrypted protocol")
        
        # Elevate to critical for certain combinations
        if service.port in [23, 3389, 5900] and service.state == PortState.OPEN:
            service.risk_level = ServiceRisk.CRITICAL
        
        service.risk_reasons = reasons
    
    def _get_listening_interfaces(self) -> List[str]:
        """Get list of listening network interfaces."""
        interfaces = []
        
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["ip", "addr", "show"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        parts = line.strip().split()
                        for i, part in enumerate(parts):
                            if part == 'inet':
                                interfaces.append(parts[i + 1])
            else:
                # Get hostname IPs
                interfaces.append("127.0.0.1")
                try:
                    interfaces.append(socket.gethostbyname(socket.gethostname()))
                except socket.gaierror as e:
                    self.logger.debug("hostname_resolution_failed", error=str(e))
                except Exception as e:
                    self.logger.debug("interface_detection_error", error=str(e))
        except subprocess.SubprocessError as e:
            self.logger.debug("interface_detection_subprocess_error", error=str(e))
        except Exception as e:
            self.logger.debug("interface_detection_error", error=str(e))
        
        return interfaces
    
    def _calculate_risk_score(self, open_ports: List[PortService]) -> float:
        """Calculate overall risk score (0-100)."""
        if not open_ports:
            return 0.0
        
        risk_values = {
            ServiceRisk.LOW: 10,
            ServiceRisk.MEDIUM: 30,
            ServiceRisk.HIGH: 60,
            ServiceRisk.CRITICAL: 100
        }
        
        total_risk = sum(risk_values.get(p.risk_level, 10) for p in open_ports)
        avg_risk = total_risk / len(open_ports)
        
        # Boost for multiple critical services
        critical_count = sum(1 for p in open_ports if p.risk_level == ServiceRisk.CRITICAL)
        if critical_count > 0:
            avg_risk = min(100, avg_risk * (1 + critical_count * 0.3))
        
        return round(avg_risk, 2)
    
    def _generate_recommendations(self, open_ports: List[PortService]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        critical = [p for p in open_ports if p.risk_level == ServiceRisk.CRITICAL]
        high = [p for p in open_ports if p.risk_level == ServiceRisk.HIGH]
        
        if critical:
            ports = ", ".join(str(p.port) for p in critical)
            recommendations.append(
                f"CRITICAL: Immediately review critical services on ports: {ports}"
            )
        
        if high:
            ports = ", ".join(str(p.port) for p in high)
            recommendations.append(
                f"HIGH: Review high-risk services on ports: {ports}"
            )
        
        if len(open_ports) > 10:
            recommendations.append(
                f"Consider reducing attack surface - {len(open_ports)} open ports detected"
            )
        
        return recommendations
    
    def get_last_report(self) -> Optional[SurfaceReport]:
        """Get last scan report."""
        return self._last_scan
    
    def compare_scans(self, index1: int = -2, index2: int = -1) -> Dict[str, Any]:
        """
        Compare two scans.
        
        Args:
            index1: First scan index
            index2: Second scan index
            
        Returns:
            Comparison results
        """
        if len(self._scan_history) < 2:
            return {"error": "Not enough scan history"}
        
        try:
            scan1 = self._scan_history[index1]
            scan2 = self._scan_history[index2]
        except IndexError:
            return {"error": "Invalid scan index"}
        
        ports1 = {p.port for p in scan1.open_ports}
        ports2 = {p.port for p in scan2.open_ports}
        
        return {
            "new_ports": list(ports2 - ports1),
            "closed_ports": list(ports1 - ports2),
            "risk_change": scan2.risk_score - scan1.risk_score
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mapper statistics."""
        return {
            "scan_history_size": len(self._scan_history),
            "last_scan_risk": self._last_scan.risk_score if self._last_scan else None
        }
