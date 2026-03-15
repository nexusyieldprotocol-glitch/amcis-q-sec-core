#!/bin/bash
# AMCIS Dashboard Launcher for Flatpak

export PYTHONPATH="/app/share/amcis:$PYTHONPATH"
export AMCIS_HOME="$HOME/.var/app/com.amcis.SecurityPlatform/data/amcis"

exec python3 /app/share/amcis/dashboard/launch_dashboard.py "$@"
