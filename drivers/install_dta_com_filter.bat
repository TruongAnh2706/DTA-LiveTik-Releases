@echo off
:: ======================================================================
:: DTA STUDIO - DIRECTSHOW NATIVE COM FILTER DRIVER REGISTRAR
:: Proprietary Virtual Camera and Audio COM Server Setup
:: ======================================================================

echo ======================================================================
echo       DTA STUDIO - REGISTERING DTA CAMERA AND DTA AUDIO NATIVE COM FILTER
echo ======================================================================

:: 1. Define CLSID & Paths for DTA Camera DirectShow Source Filter
set DTA_CAM_CLSID={DTA11000-CAM1-4D01-8D3B-00A0C911CE86}
set DTA_AUD_CLSID={DTA11000-AUD1-4D01-8D3B-00A0C911CE86}

:: 2. Register COM InprocServer32 DLL Entries into System Registry (HKLM & HKCU)
reg add "HKLM\SOFTWARE\Classes\CLSID\%DTA_CAM_CLSID%" /ve /t REG_SZ /d "DTA Camera Filter" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\%DTA_CAM_CLSID%\InprocServer32" /ve /t REG_SZ /d "%~dp0dta_camera_filter64.dll" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\%DTA_CAM_CLSID%\InprocServer32" /v "ThreadingModel" /t REG_SZ /d "Both" /f

reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%DTA_CAM_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%DTA_CAM_CLSID%" /v "CLSID" /t REG_SZ /d "%DTA_CAM_CLSID%" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%DTA_CAM_CLSID%" /v "FilterData" /t REG_BINARY /d "02000000000040000100000000000000300000000100000000000000000000000100000000000000" /f

:: WOW6432Node for 32-bit Applications & OBS/TikTok Studio Bridge
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%DTA_CAM_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%DTA_CAM_CLSID%" /v "CLSID" /t REG_SZ /d "%DTA_CAM_CLSID%" /f

:: 3. Register DTA Audio into Audio Input Devices (CLSID_{33D9A762-90C8-11D0-BD43-00A0C911CE86})
reg add "HKLM\SOFTWARE\Classes\CLSID\%DTA_AUD_CLSID%" /ve /t REG_SZ /d "DTA Audio Filter" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%DTA_AUD_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%DTA_AUD_CLSID%" /v "CLSID" /t REG_SZ /d "%DTA_AUD_CLSID%" /f

reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%DTA_AUD_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%DTA_AUD_CLSID%" /v "CLSID" /t REG_SZ /d "%DTA_AUD_CLSID%" /f

echo.
echo Complete DTA Camera and DTA Audio COM Filter Registration Finished!
