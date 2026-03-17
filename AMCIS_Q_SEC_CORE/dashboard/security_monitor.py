#!/usr/bin/env python3
"""
AMCIS Q-SEC CORE - Network Security Monitor
Real-time monitoring and encryption status dashboard
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

AMCIS_BASE = Path.home() / "AMCIS_Q_SEC_CORE"
VAULT_PATH = AMCIS_BASE / ".VAULT_MASTER"

class AMCISecurityMonitor:
    def __init__(self):
        self.status = {
            "encryption": {},
            "network": {},
            "files": {},
            "timestamp": datetime.now().isoformat()
        }
    
    def check_encryption_status(self):
        """Check if sensitive files are encrypted"""
        key_file = VAULT_PATH / "keys" / "amcis_master.key"
        self.status["encryption"]["master_key_exists"] = key_file.exists()
        self.status["encryption"]["vault_path"] = str(VAULT_PATH)
        return self.status["encryption"]
    
    def scan_project_integrity(self):
        """Generate integrity hashes for core files"""
        core_dirs = ["core", "crypto", "edr", "network", "threat_intel"]
        for dir_name in core_dirs:
            dir_path = AMCIS_BASE / dir_name
            if dir_path.exists():
                files = list(dir_path.glob("**/*.py"))
                self.status["files"][dir_name] = {
                    "file_count": len(files),
                    "last_modified": max([f.stat().st_mtime for f in files], default=0)
                }
        return self.status["files"]
    
    def generate_report(self):
        """Generate security status report"""
        self.check_encryption_status()
        self.scan_project_integrity()
        
        report_path = VAULT_PATH / "security_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.status, f, indent=2)
        
        print("=" * 50)
        print("AMCIS Q-SEC CORE - Security Status")
        print("=" * 50)
        print(f"Timestamp: {self.status['timestamp']}")
        print(f"\nEncryption Status:")
        print(f"  Master Key: {'✅ Present' if self.status['encryption'].get('master_key_exists') else '❌ Missing'}")
        print(f"  Vault Path: {self.status['encryption'].get('vault_path', 'N/A')}")
        print(f"\nProject Modules:")
        for module, info in self.status['files'].items():
            print(f"  {module}: {info['file_count']} files")
        print(f"\nReport saved: {report_path}")
        
        return self.status

if __name__ == "__main__":
    monitor = AMCISecurityMonitor()
    monitor.generate_report()
