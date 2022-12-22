@echo off
if not exist "%~dp0venv\" (
    echo Creating virtual environment...+
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe -m pip install virtualenv
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe -m virtualenv venv
)

%~dp0\venv\Scripts\python.exe -m pip install -r requirements.txt
%~dp0\venv\Scripts\python.exe -m pip install git+https://github.com/shahriyardx/easy-pil@3.11
cls
%~dp0\venv\Scripts\python.exe main.py %*
pause