@echo off
cd /d "C:\Users\81908\Documents\vscode\bath_system"
echo [%date% %time%] サーバー起動中... >> startup.log
python server.py >> server_stdout.log 2>&1
