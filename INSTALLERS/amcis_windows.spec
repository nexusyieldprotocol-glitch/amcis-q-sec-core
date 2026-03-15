# -*- mode: python ; coding: utf-8 -*-
"""
AMCIS Windows Installer Spec
PyInstaller configuration for building AMCIS Windows .exe installer
"""

import sys
import os

block_cipher = None

# Define all data files to include
data_files = [
    ('..\AMCIS_Q_SEC_CORE\*.py', 'amcis'),
    ('..\AMCIS_Q_SEC_CORE\*\*.py', 'amcis'),
    ('..\AMCIS_Q_SEC_CORE\compliance\*.json', 'amcis\compliance'),
    ('..\AMCIS_Q_SEC_CORE\dashboard\*.html', 'amcis\dashboard'),
    ('..\requirements.txt', '.'),
    ('..\.env.example', '.'),
]

# Hidden imports for all AMCIS modules
hidden_imports = [
    'core.amcis_kernel',
    'core.amcis_trust_engine',
    'core.amcis_response_engine',
    'core.amcis_anomaly_engine',
    'core.amcis_integrity_monitor',
    'crypto.amcis_encrypt',
    'crypto.amcis_key_manager',
    'crypto.amcis_hybrid_pqc',
    'crypto.amcis_cert_generator',
    'compliance.compliance_engine',
    'compliance.nist_csf',
    'edr.amcis_file_integrity',
    'edr.amcis_memory_inspector',
    'edr.amcis_process_graph',
    'network.amcis_microsegmentation',
    'network.amcis_dns_tunnel_detector',
    'ai_security.amcis_prompt_firewall',
    'ai_security.amcis_output_validator',
    'threat_intel.ioc_matcher',
    'threat_intel.stix_parser',
    'dashboard.amcis_dashboard_server',
    'secrets_mgr.secrets_manager',
    'supply_chain.amcis_sbom_generator',
    'forensics.evidence_collector',
    'deception.honeypot',
    'waf.waf_engine',
    'cryptography',
    'cryptography.hazmat',
    'pydantic',
    'fastapi',
    'uvicorn',
    'sqlalchemy',
    'redis',
    'prometheus_client',
    'psutil',
    'yaml',
    'requests',
    'aiohttp',
    'asyncio',
    'numpy',
    'pandas',
]

a = Analysis(
    ['..\AMCIS_Q_SEC_CORE\cli\amcis_main.py'],
    pathex=['C:\\Users\\L337B\\AMCIS_UNIFIED\\AMCIS_Q_SEC_CORE'],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'unittest',
        'pytest',
        'mypy',
        'pylint',
        'black',
        'flake8',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AMCIS-Security-Platform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='..\assets\amcis_icon.ico',
    version='version.txt',
    manifest='amcis.manifest',
)

# Build command reference:
# pyinstaller amcis_windows.spec --clean --noconfirm
