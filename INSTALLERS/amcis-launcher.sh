#!/bin/bash
# AMCIS Flatpak Launcher

export PYTHONPATH="/app/share/amcis:$PYTHONPATH"
export AMCIS_HOME="$HOME/.var/app/com.amcis.SecurityPlatform/data/amcis"
export AMCIS_CONFIG_PATH="$HOME/.var/app/com.amcis.SecurityPlatform/config/amcis"

mkdir -p "$AMCIS_HOME"
mkdir -p "$AMCIS_CONFIG_PATH"

exec python3 /app/share/amcis/cli/amcis_main.py "$@"
