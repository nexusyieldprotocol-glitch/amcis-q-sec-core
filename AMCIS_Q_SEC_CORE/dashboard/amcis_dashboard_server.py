#!/usr/bin/env python3
"""
AMCIS Q-SEC CORE - Dashboard Server
====================================
Web-based dashboard for AMCIS security monitoring with real-time updates.
"""

import asyncio
import json
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from aiohttp import web
import structlog

from dashboard.alert_manager import AlertManager, AlertSeverity, AlertStatus
from dashboard.metrics_collector import MetricsCollector

logger = structlog.get_logger("amcis.dashboard")


class AMCISDashboard:
    """AMCIS Web Dashboard Server"""
    
    def __init__(self, host: str = "localhost", port: int = 8443):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.alert_manager = AlertManager()
        self.metrics_collector = MetricsCollector()
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get("/", self.index_handler)
        self.app.router.add_get("/api/status", self.api_status)
        self.app.router.add_get("/api/alerts", self.api_alerts)
        self.app.router.add_get("/api/metrics", self.api_metrics)
        self.app.router.add_get("/api/test-results", self.api_test_results)
        self.app.router.add_static("/static", Path(__file__).parent, name="static")
        
    async def index_handler(self, request: web.Request) -> web.Response:
        """Serve main dashboard HTML"""
        dashboard_html = Path(__file__).parent / "amcis_dashboard.html"
        if dashboard_html.exists():
            return web.FileResponse(dashboard_html)
        return web.Response(text="Dashboard not found", status=404)
    
    async def api_status(self, request: web.Request) -> web.Response:
        """Get system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational",
            "security_score": 81,
            "tests_passed": 26,
            "tests_failed": 4,
            "tests_errors": 2,
            "modules_active": 12,
            "log_entries": 68,
            "alerts_active": 24,
            "version": "1.0.0"
        }
        return web.json_response(status)
    
    async def api_alerts(self, request: web.Request) -> web.Response:
        """Get current alerts"""
        alerts = self.alert_manager.get_alerts()
        return web.json_response({
            "alerts": [alert.to_dict() for alert in alerts[:50]],
            "statistics": self.alert_manager.get_statistics()
        })
    
    async def api_metrics(self, request: web.Request) -> web.Response:
        """Get security metrics"""
        summary = self.metrics_collector.get_dashboard_summary()
        return web.json_response(summary)
    
    async def api_test_results(self, request: web.Request) -> web.Response:
        """Get latest test results"""
        results = {
            "timestamp": "2026-02-26T21:37:00",
            "summary": {
                "total": 32,
                "passed": 26,
                "failed": 4,
                "errors": 2,
                "success_rate": 81
            },
            "modules": {
                "crypto": {
                    "tests": [
                        {"name": "ML-KEM Key Generation", "status": "passed"},
                        {"name": "ML-KEM Encapsulation", "status": "failed", "error": "Shared secret mismatch"},
                        {"name": "ML-DSA Key Generation", "status": "passed"},
                        {"name": "ML-DSA Signature Verify", "status": "failed", "error": "False positive on wrong message"},
                        {"name": "Key Manager", "status": "passed"},
                        {"name": "Key Rotation", "status": "passed"},
                        {"name": "Merkle Log Append", "status": "passed"},
                        {"name": "Merkle Log Verify", "status": "passed"},
                        {"name": "Merkle Log Inclusion Proof", "status": "passed"},
                    ]
                },
                "kernel": {
                    "tests": [
                        {"name": "Singleton Pattern", "status": "passed"},
                        {"name": "Initial State", "status": "passed"},
                        {"name": "Secure Boot", "status": "passed"},
                        {"name": "Module Registration", "status": "passed"},
                        {"name": "Event Emission", "status": "passed"},
                        {"name": "Health Check", "status": "passed"},
                    ]
                },
                "trust_engine": {
                    "tests": [
                        {"name": "Trust Evaluation", "status": "passed"},
                        {"name": "Trust Factors", "status": "passed"},
                        {"name": "Suspicious Pattern Detection", "status": "failed", "error": "TrustException raised"},
                        {"name": "Strict Mode", "status": "passed"},
                        {"name": "Threshold Update", "status": "passed"},
                    ]
                },
                "edr": {
                    "tests": [
                        {"name": "Process Scan", "status": "passed"},
                        {"name": "Process Lineage", "status": "passed"},
                        {"name": "Graph Update", "status": "failed", "error": "Slow scan timeout"},
                        {"name": "Memory Inspector", "status": "passed"},
                        {"name": "File Integrity Monitor", "status": "error", "error": "ModuleNotFoundError"},
                    ]
                }
            }
        }
        return web.json_response(results)
    
    async def start(self):
        """Start dashboard server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(
            "dashboard_server_started",
            host=self.host,
            port=self.port,
            url=f"https://{self.host}:{self.port}"
        )
        
        # Open browser
        webbrowser.open(f"http://{self.host}:{self.port}")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


def main():
    """Main entry point"""
    print("=" * 60)
    print("AMCIS Q-SEC CORE - Security Dashboard")
    print("=" * 60)
    print()
    print("Starting dashboard server...")
    print()
    
    dashboard = AMCISDashboard(host="localhost", port=8443)
    
    try:
        asyncio.run(dashboard.start())
    except KeyboardInterrupt:
        print("\n\nShutting down dashboard...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
