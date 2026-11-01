#!/bin/bash
# Double-click this file on a Mac to start Job Finder.
# (On Linux, run it from a terminal with:  ./start.command)
#
# First time: it creates a private Python folder (.venv) and installs the
# libraries. After that it starts the app right away.

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python is not installed. Get it from https://www.python.org/downloads/"
    read -r -p "Press Enter to close..."
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "First time setup, this takes a minute..."
    if ! python3 -m venv .venv; then
        echo "Could not create the .venv folder."
        read -r -p "Press Enter to close..."
        exit 1
    fi
fi

# Install the libraries only if requirements.txt changed since last time
if ! cmp -s requirements.txt .venv/installed-requirements.txt; then
    echo "Installing libraries..."
    if .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt; then
        cp requirements.txt .venv/installed-requirements.txt
    else
        echo "Installing failed. Check your internet connection and try again."
        read -r -p "Press Enter to close..."
        exit 1
    fi
fi

.venv/bin/python job_finder.py
echo
read -r -p "Press Enter to close..."
