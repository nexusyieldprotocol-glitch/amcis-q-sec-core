"""
Honeypot System
===============

Emulated services and systems to detect and analyze attacker behavior.
"""

import asyncio
import json
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

import structlog


@dataclass
class DeceptionEvent:
    """Event triggered by honeypot interaction."""
    timestamp: float
    honeypot_id: str
    event_type: str  # 'connect', 'login_attempt', 'command', 'file_access'
    source_ip: str
    source_port: int
    data: Dict[str, Any]
    severity: str = "HIGH"
    session_id: str = field(default_factory=lambda: str(int(time.time() * 1000)))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "honeypot_id": self.honeypot_id,
            "event_type": self.event_type,
            "source": f"{self.source_ip}:{self.source_port}",
            "severity": self.severity,
            "data": self.data
        }


class Honeypot:
    """
    AMCIS Honeypot
    ==============
    
    Emulated services to detect and analyze attacker behavior.
    """
    
    def __init__(self, honeypot_id: str, service_type: str = "ssh",
                 bind_host: str = "0.0.0.0", bind_port: int = 2222) -> None:
        self.honeypot_id = honeypot_id
        self.service_type = service_type
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.logger = structlog.get_logger("amcis.honeypot")
        
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._event_handlers: List[Callable[[DeceptionEvent], None]] = []
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Fake credentials that trigger alerts
        self._honey_accounts = {
            "admin": "password123",
            "root": "toor",
            "user": "password",
        }
        
        self.logger.info("honeypot_initialized", id=honeypot_id, service=service_type)
    
    def register_event_handler(self, handler: Callable[[DeceptionEvent], None]) -> None:
        """Register callback for deception events."""
        self._event_handlers.append(handler)
    
    def start(self) -> bool:
        """Start honeypot."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.bind_host, self.bind_port))
            self._socket.listen(5)
            
            self._running = True
            self._server_thread = threading.Thread(target=self._serve, daemon=True)
            self._server_thread.start()
            
            self.logger.info("honeypot_started", host=self.bind_host, port=self.bind_port)
            return True
            
        except Exception as e:
            self.logger.error("honeypot_start_failed", error=str(e))
            return False
    
    def stop(self) -> None:
        """Stop honeypot."""
        self._running = False
        if self._socket:
            self._socket.close()
        self.logger.info("honeypot_stopped")
    
    def _serve(self) -> None:
        """Main server loop."""
        while self._running:
            try:
                self._socket.settimeout(1.0)
                client, addr = self._socket.accept()
                
                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client, addr),
                    daemon=True
                )
                handler_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.logger.error("accept_error", error=str(e))
    
    def _handle_client(self, client: socket.socket, addr: tuple) -> None:
        """Handle client connection."""
        source_ip, source_port = addr
        session_id = f"{source_ip}:{source_port}:{int(time.time())}"
        
        # Log connection
        self._emit_event(DeceptionEvent(
            timestamp=time.time(),
            honeypot_id=self.honeypot_id,
            event_type="connect",
            source_ip=source_ip,
            source_port=source_port,
            data={"service": self.service_type},
            severity="MEDIUM"
        ))
        
        try:
            if self.service_type == "ssh":
                self._emulate_ssh(client, source_ip, source_port, session_id)
            elif self.service_type == "telnet":
                self._emulate_telnet(client, source_ip, source_port, session_id)
            elif self.service_type == "http":
                self._emulate_http(client, source_ip, source_port, session_id)
        except Exception as e:
            self.logger.debug("client_handler_error", error=str(e))
        finally:
            client.close()
    
    def _emulate_ssh(self, client: socket.socket, source_ip: str, 
                    source_port: int, session_id: str) -> None:
        """Emulate SSH service."""
        # Send SSH banner
        banner = b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1\r\n"
        client.send(banner)
        
        # Wait for client version
        try:
            client.settimeout(10.0)
            data = client.recv(1024)
            
            # Request authentication
            client.send(b"Password: ")
            password_data = client.recv(1024)
            
            # Always fail auth but log it
            self._emit_event(DeceptionEvent(
                timestamp=time.time(),
                honeypot_id=self.honeypot_id,
                event_type="login_attempt",
                source_ip=source_ip,
                source_port=source_port,
                data={
                    "service": "ssh",
                    "attempt": password_data.decode('utf-8', errors='ignore').strip()
                },
                severity="HIGH"
            ))
            
            client.send(b"Access denied\r\n")
            
        except socket.timeout:
            pass
    
    def _emulate_telnet(self, client: socket.socket, source_ip: str,
                       source_port: int, session_id: str) -> None:
        """Emulate Telnet service."""
        client.send(b"login: ")
        username = client.recv(1024).decode('utf-8', errors='ignore').strip()
        
        client.send(b"Password: ")
        password = client.recv(1024).decode('utf-8', errors='ignore').strip()
        
        self._emit_event(DeceptionEvent(
            timestamp=time.time(),
            honeypot_id=self.honeypot_id,
            event_type="login_attempt",
            source_ip=source_ip,
            source_port=source_port,
            data={
                "service": "telnet",
                "username": username,
                "password": password[:20] + "..." if len(password) > 20 else password
            },
            severity="HIGH"
        ))
        
        client.send(b"Login incorrect\r\n")
    
    def _emulate_http(self, client: socket.socket, source_ip: str,
                     source_port: int, session_id: str) -> None:
        """Emulate HTTP service."""
        try:
            data = client.recv(4096).decode('utf-8', errors='ignore')
            
            # Parse request
            lines = data.split('\r\n')
            if lines:
                request_line = lines[0]
                
                self._emit_event(DeceptionEvent(
                    timestamp=time.time(),
                    honeypot_id=self.honeypot_id,
                    event_type="http_request",
                    source_ip=source_ip,
                    source_port=source_port,
                    data={"request": request_line},
                    severity="MEDIUM"
                ))
                
                # Send fake admin panel
                response = b"""HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n
                <html><head><title>Admin Panel</title></head>
                <body><h1>System Administration</h1>
                <p>Welcome to the management interface.</p>
                </body></html>"""
                client.send(response)
        except Exception:
            pass
    
    def _emit_event(self, event: DeceptionEvent) -> None:
        """Emit deception event."""
        self.logger.warning("deception_event", 
                           type=event.event_type,
                           source=f"{event.source_ip}:{event.source_port}")
        
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error("event_handler_error", error=str(e))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get honeypot statistics."""
        return {
            "honeypot_id": self.honeypot_id,
            "service_type": self.service_type,
            "running": self._running,
            "bind_address": f"{self.bind_host}:{self.bind_port}",
            "active_sessions": len(self._sessions)
        }
