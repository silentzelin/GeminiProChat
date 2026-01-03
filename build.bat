@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

pyinstaller --noconfirm --onedir --windowed --name Lucky10Visualizer main.py

endlocal
