#!/usr/bin/env python3
"""
AMCIS Dashboard Launcher
========================
Simple launcher for the AMCIS security dashboard.
Opens the dashboard in your default web browser.
"""

import os
import sys
import webbrowser
from pathlib import Path


def launch_dashboard():
    """Launch the AMCIS dashboard"""
    dashboard_path = Path(__file__).parent / "amcis_dashboard.html"
    
    if not dashboard_path.exists():
        print("Error: Dashboard HTML file not found!")
        print(f"Expected: {dashboard_path}")
        return 1
    
    # Convert to file URL
    file_url = dashboard_path.resolve().as_uri()
    
    print("=" * 60)
    print("🚀 AMCIS Q-SEC CORE - Launching Dashboard")
    print("=" * 60)
    print()
    print(f"📊 Opening: {file_url}")
    print()
    print("Dashboard Features:")
    print("  ✓ Real-time security score (81%)")
    print("  ✓ Test results visualization")
    print("  ✓ Module status monitoring")
    print("  ✓ Alert feed")
    print("  ✓ Cryptographic integrity checks")
    print()
    print("Press Ctrl+C to exit")
    print("=" * 60)
    
    # Open browser
    webbrowser.open(file_url)
    
    # Keep running
    try:
        print("\nDashboard is running...")
        print("(This window will remain open)")
        input()
    except KeyboardInterrupt:
        pass
    
    return 0


if __name__ == "__main__":
    sys.exit(launch_dashboard())
