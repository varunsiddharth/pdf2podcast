@echo off
echo Starting PDF to Podcast Generator...
cd /d "D:\project front"
call venv\Scripts\activate
python start_server.py
pause
