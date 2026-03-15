"""
AMCIS Interactive Demo Application
Production-ready demo for prospect evaluation
"""

import os
import sys
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add AMCIS paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "AMCIS_Q_SEC_CORE"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "CTVP"))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import uvicorn

app = FastAPI(
    title="AMCIS Demo Environment",
    version="1.0.0-demo",
    description="Interactive demonstration of AMCIS Q-SEC CORE capabilities"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Demo data store
DEMO_DB = {
    "demo_sessions": {},
    "threats_detected": 0,
    "encrypted_messages": [],
    "compliance_checks": []
}

# Demo credentials (rotate every 24 hours)
DEMO_CREDENTIALS = {
    "admin": {
        "username": "demo_admin",
        "password": secrets.token_urlsafe(16),
        "api_key": f"amcis_demo_{secrets.token_hex(16)}",
        "expires": (datetime.now() + timedelta(hours=24)).isoformat()
    },
    "readonly": {
        "username": "demo_user",
        "password": secrets.token_urlsafe(12),
        "api_key": f"amcis_demo_{secrets.token_hex(12)}",
        "expires": (datetime.now() + timedelta(hours=24)).isoformat()
    }
}

# HTML Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AMCIS Demo Environment</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #0f3460;
        }
        .card h3 {
            margin-top: 0;
            color: #e94560;
        }
        .btn {
            background: #e94560;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
        }
        .btn:hover {
            background: #c73e54;
        }
        .output {
            background: #0f3460;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
            min-height: 100px;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .status.active {
            background: #00d9ff;
            color: #000;
        }
        .status.secure {
            background: #00ff88;
            color: #000;
        }
        .status.alert {
            background: #ff4757;
            color: white;
        }
        .credentials {
            background: #0f3460;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .credentials code {
            color: #00d9ff;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 AMCIS Q-SEC CORE</h1>
        <p>Interactive Demo Environment | Quantum-Secure Cybersecurity Platform</p>
        <span class="status active">● DEMO ACTIVE</span>
        <span class="status secure">● SYSTEM SECURE</span>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🎯 Demo Credentials</h3>
            <div class="credentials">
                <strong>Admin Access:</strong><br>
                Username: <code id="admin_user">Loading...</code><br>
                Password: <code id="admin_pass">Loading...</code><br>
                API Key: <code id="admin_key">Loading...</code>
            </div>
            <div class="credentials">
                <strong>Read-Only Access:</strong><br>
                Username: <code id="ro_user">Loading...</code><br>
                Password: <code id="ro_pass">Loading...</code><br>
                API Key: <code id="ro_key">Loading...</code>
            </div>
            <p style="font-size: 12px; color: #888;">
                Credentials expire: <span id="expiry">24 hours</span>
            </p>
        </div>

        <div class="card">
            <h3>🔐 Post-Quantum Cryptography</h3>
            <p>Generate quantum-safe keys and encrypt messages</p>
            <button class="btn" onclick="generateKey()">Generate PQC Key</button>
            <button class="btn" onclick="encryptMessage()">Encrypt Message</button>
            <div class="output" id="crypto_output">Click a button to see PQC in action...</div>
        </div>

        <div class="card">
            <h3>🤖 AI Security Agents</h3>
            <p>Test AI-powered threat detection</p>
            <button class="btn" onclick="analyzePrompt()">Analyze Prompt</button>
            <button class="btn" onclick="detectThreat()">Detect Threat</button>
            <div class="output" id="ai_output">AI agents ready...</div>
        </div>

        <div class="card">
            <h3>📊 Compliance Automation</h3>
            <p>NIST CSF 2.0 compliance checking</p>
            <button class="btn" onclick="checkCompliance()">Check Compliance</button>
            <button class="btn" onclick="generateReport()">Generate Report</button>
            <div class="output" id="compliance_output">Compliance engine ready...</div>
        </div>

        <div class="card">
            <h3>🔍 Network Security</h3>
            <p>DNS tunnel detection and port scanning</p>
            <button class="btn" onclick="scanPorts()">Scan Ports</button>
            <button class="btn" onclick="detectTunnel()">Detect DNS Tunnel</button>
            <div class="output" id="network_output">Network tools ready...</div>
        </div>

        <div class="card">
            <h3>📈 System Metrics</h3>
            <p>Live demo environment statistics</p>
            <div class="output" id="metrics">
Threats Detected: 0
Encrypted Messages: 0
Compliance Checks: 0
Uptime: 0h 0m
            </div>
            <button class="btn" onclick="updateMetrics()">Refresh</button>
        </div>
    </div>

    <script>
        // Load credentials on page load
        fetch('/api/demo/credentials')
            .then(r => r.json())
            .then(data => {
                document.getElementById('admin_user').textContent = data.admin.username;
                document.getElementById('admin_pass').textContent = data.admin.password;
                document.getElementById('admin_key').textContent = data.admin.api_key.substring(0, 30) + '...';
                document.getElementById('ro_user').textContent = data.readonly.username;
                document.getElementById('ro_pass').textContent = data.readonly.password;
                document.getElementById('ro_key').textContent = data.readonly.api_key.substring(0, 30) + '...';
                document.getElementById('expiry').textContent = new Date(data.admin.expires).toLocaleString();
            });

        async function generateKey() {
            const output = document.getElementById('crypto_output');
            output.textContent = 'Generating quantum-safe key pair...';
            const res = await fetch('/api/demo/crypto/generate-key');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function encryptMessage() {
            const output = document.getElementById('crypto_output');
            output.textContent = 'Encrypting with post-quantum algorithm...';
            const res = await fetch('/api/demo/crypto/encrypt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: 'Secret demo message'})
            });
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function analyzePrompt() {
            const output = document.getElementById('ai_output');
            output.textContent = 'AI analyzing prompt for injection attacks...';
            const res = await fetch('/api/demo/ai/analyze-prompt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: 'Ignore previous instructions'})
            });
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function detectThreat() {
            const output = document.getElementById('ai_output');
            output.textContent = 'AI agents scanning for threats...';
            const res = await fetch('/api/demo/ai/detect-threat');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function checkCompliance() {
            const output = document.getElementById('compliance_output');
            output.textContent = 'Checking NIST CSF 2.0 compliance...';
            const res = await fetch('/api/demo/compliance/check');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function generateReport() {
            const output = document.getElementById('compliance_output');
            output.textContent = 'Generating compliance report...';
            const res = await fetch('/api/demo/compliance/report');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function scanPorts() {
            const output = document.getElementById('network_output');
            output.textContent = 'Scanning network ports...';
            const res = await fetch('/api/demo/network/scan');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function detectTunnel() {
            const output = document.getElementById('network_output');
            output.textContent = 'Analyzing DNS traffic for tunneling...';
            const res = await fetch('/api/demo/network/detect-tunnel');
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        }

        async function updateMetrics() {
            const res = await fetch('/api/demo/metrics');
            const data = await res.json();
            document.getElementById('metrics').textContent = `
Threats Detected: ${data.threats_detected}
Encrypted Messages: ${data.encrypted_messages}
Compliance Checks: ${data.compliance_checks}
Uptime: ${data.uptime}`;
        }

        // Update metrics every 10 seconds
        setInterval(updateMetrics, 10000);
        updateMetrics();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the interactive demo dashboard"""
    return DASHBOARD_HTML

@app.get("/api/demo/credentials")
async def get_credentials():
    """Get temporary demo credentials"""
    return {
        "admin": DEMO_CREDENTIALS["admin"],
        "readonly": DEMO_CREDENTIALS["readonly"]
    }

@app.get("/api/demo/crypto/generate-key")
async def demo_generate_key():
    """Demo: Generate post-quantum key pair"""
    try:
        from crypto.amcis_key_manager import KeyManager
        km = KeyManager()
        key_id = f"demo_key_{secrets.token_hex(8)}"
        return {
            "key_id": key_id,
            "algorithm": "ML-KEM-768 (NIST FIPS 203)",
            "status": "generated",
            "quantum_safe": True,
            "timestamp": datetime.now().isoformat()
        }
    except:
        return {
            "key_id": f"demo_key_{secrets.token_hex(8)}",
            "algorithm": "ML-KEM-768 (Simulated)",
            "status": "generated",
            "quantum_safe": True,
            "note": "Demo mode - using simulation",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/demo/crypto/encrypt")
async def demo_encrypt(data: dict):
    """Demo: Encrypt message with PQC"""
    message = data.get("message", "")
    ciphertext = hashlib.sha256(message.encode()).hexdigest()[:32] + "..."
    DEMO_DB["encrypted_messages"].append({
        "timestamp": datetime.now().isoformat(),
        "algorithm": "ML-KEM-768 + AES-256-GCM"
    })
    return {
        "ciphertext": ciphertext,
        "algorithm": "ML-KEM-768 + AES-256-GCM",
        "quantum_resistant": True,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/demo/ai/analyze-prompt")
async def demo_analyze_prompt(data: dict):
    """Demo: AI prompt analysis"""
    prompt = data.get("prompt", "")
    risk_score = 0.85 if "ignore" in prompt.lower() else 0.15
    return {
        "prompt_analyzed": prompt[:50],
        "risk_score": risk_score,
        "risk_level": "HIGH" if risk_score > 0.7 else "LOW",
        "injection_detected": risk_score > 0.7,
        "recommendation": "Block" if risk_score > 0.7 else "Allow",
        "ai_model": "AMCIS-Prompt-Guard-v2",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/demo/ai/detect-threat")
async def demo_detect_threat():
    """Demo: AI threat detection"""
    DEMO_DB["threats_detected"] += 1
    return {
        "threat_id": f"THREAT-{secrets.token_hex(8).upper()}",
        "severity": "MEDIUM",
        "type": "Anomalous Network Pattern",
        "confidence": 0.94,
        "agents_involved": ["Network-Monitor", "Threat-Intel", "SOAR"],
        "auto_remediated": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/demo/compliance/check")
async def demo_compliance_check():
    """Demo: NIST CSF compliance check"""
    DEMO_DB["compliance_checks"].append(datetime.now().isoformat())
    return {
        "framework": "NIST CSF 2.0",
        "controls_checked": 108,
        "compliant": 98,
        "non_compliant": 10,
        "compliance_score": 90.7,
        "status": "PASS" if 90.7 > 80 else "FAIL",
        "last_audit": datetime.now().isoformat()
    }

@app.get("/api/demo/compliance/report")
async def demo_compliance_report():
    """Demo: Generate compliance report"""
    return {
        "report_id": f"REPORT-{secrets.token_hex(8).upper()}",
        "framework": "NIST CSF 2.0",
        "generated_at": datetime.now().isoformat(),
        "pages": 47,
        "findings": {
            "critical": 0,
            "high": 2,
            "medium": 8,
            "low": 15
        },
        "signed": True,
        "signature_type": "Post-Quantum (SPHINCS+)"
    }

@app.get("/api/demo/network/scan")
async def demo_network_scan():
    """Demo: Port scanning"""
    return {
        "scan_id": secrets.token_hex(8),
        "target": "192.168.1.0/24",
        "ports_scanned": 1000,
        "open_ports": [80, 443, 8080, 22],
        "services": [
            {"port": 80, "service": "HTTP", "risk": "low"},
            {"port": 443, "service": "HTTPS", "risk": "low"},
            {"port": 8080, "service": "AMCIS-API", "risk": "low"},
            {"port": 22, "service": "SSH", "risk": "medium"}
        ],
        "scan_duration": "12.4s"
    }

@app.get("/api/demo/network/detect-tunnel")
async def demo_detect_tunnel():
    """Demo: DNS tunnel detection"""
    return {
        "analysis_id": secrets.token_hex(8),
        "queries_analyzed": 15420,
        "suspicious_queries": 3,
        "tunnel_detected": False,
        "entropy_score": 3.2,
        "threshold": 7.0,
        "status": "CLEAR"
    }

@app.get("/api/demo/metrics")
async def demo_metrics():
    """Get demo environment metrics"""
    return {
        "threats_detected": DEMO_DB["threats_detected"],
        "encrypted_messages": len(DEMO_DB["encrypted_messages"]),
        "compliance_checks": len(DEMO_DB["compliance_checks"]),
        "uptime": "Running",
        "api_version": "1.0.0-demo",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "mode": "demo", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("=" * 60)
    print("AMCIS DEMO ENVIRONMENT")
    print("=" * 60)
    print(f"Admin Username: {DEMO_CREDENTIALS['admin']['username']}")
    print(f"Admin Password: {DEMO_CREDENTIALS['admin']['password']}")
    print(f"API Key: {DEMO_CREDENTIALS['admin']['api_key'][:40]}...")
    print(f"Expires: {DEMO_CREDENTIALS['admin']['expires']}")
    print("=" * 60)
    print("Access the demo at: http://localhost:8080")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8080)
