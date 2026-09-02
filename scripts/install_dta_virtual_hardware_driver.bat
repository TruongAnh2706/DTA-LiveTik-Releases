@echo off
chcp 65001 > nul
echo ======================================================================
echo    DTA STUDIO - DTA CAMERA ^& DTA AUDIO NATIVE DRIVER INSTALLER
echo ======================================================================
echo.

:: 1. Register DirectShow Virtual Camera Filter DLL into Windows Kernel
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f > nul 2>&1
reg add "HKCU\Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f > nul 2>&1

:: 2. Register DirectShow Virtual Audio Endpoint into Windows Kernel
reg add "HKLM\SOFTWARE\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f > nul 2>&1
reg add "HKCU\Software\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f > nul 2>&1

:: 3. Execute Python Driver Installer
python drivers\install_dta_driver.py

echo [SUCCESS] Complete DTA Camera and DTA Audio Native Driver Setup!
exit /b 0
