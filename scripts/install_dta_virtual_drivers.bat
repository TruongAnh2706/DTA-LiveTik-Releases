@echo off
chcp 65001 > nul
:: Register DTA Camera Video Capture Filter into Windows Registry
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f > nul 2>&1
reg add "HKCU\Software\Microsoft\DirectShow\Preferred" /v "DTA Camera" /t REG_SZ /d "DTA DirectShow Virtual Camera Filter" /f > nul 2>&1

:: Register DTA Audio Endpoint into Windows Registry
reg add "HKLM\SOFTWARE\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f > nul 2>&1
reg add "HKCU\Software\Microsoft\DirectSound\Preferred" /v "DTA Audio" /t REG_SZ /d "DTA DirectSound Virtual Audio Filter" /f > nul 2>&1

echo [SUCCESS] Registered DTA Camera and DTA Audio into Windows DirectShow Registry!
exit /b 0
