#!/bin/bash

source .venv/bin/activate
pyinstaller --clean --noconfirm --windowed --icon=img/divine_echo.ico divine_echo.py
