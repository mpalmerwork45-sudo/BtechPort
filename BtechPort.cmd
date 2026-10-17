@echo off
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pyw -3 "%~dp0BtechPort.pyw" %*
) else (
    start "" pythonw "%~dp0BtechPort.pyw" %*
)
