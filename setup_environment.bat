@echo off
echo Setting up PDF to Podcast Generator environment...
cd /d "D:\project front"

echo Removing old virtual environment...
if exist venv rmdir /s /q venv

echo Creating new virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete! You can now run: python start_server.py
pause
