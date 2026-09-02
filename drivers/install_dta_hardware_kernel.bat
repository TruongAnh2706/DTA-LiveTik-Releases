@echo off
:: ======================================================================
:: DTA STUDIO - FULL MEDIA FOUNDATION AND DIRECTSHOW VIRTUAL HARDWARE REGISTRAR
:: Proprietary Virtual Device Engine | Đức Trường (DTA Studio)
:: ======================================================================

echo ======================================================================
echo           DTA STUDIO - FULL MEDIA FOUNDATION AND DIRECTSHOW REGISTRAR
echo ======================================================================

set CAM_CLSID={DTA11000-CAM1-4D01-8D3B-00A0C911CE86}
set AUD_CLSID={DTA11000-AUD1-4D01-8D3B-00A0C911CE86}
set CAM_SYM_LINK=\\?\usb#vid_dta1100^&pid_2026^&mi_00#dta_camera#{e5323777-f976-4f5b-9b55-b94699c46e44}\global
set AUD_SYM_LINK=\\?\usb#vid_dta1100^&pid_2026^&mi_01#dta_audio#{6994ad04-93ef-11d0-a3cc-00a0c9223196}\global

:: 1. DirectShow Video Capture Category Registration ({860BB310-5D01-11D0-BD3B-00A0C911CE86})
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "CLSID" /t REG_SZ /d "%CAM_CLSID%" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "DevicePath" /t REG_SZ /d "%CAM_SYM_LINK%" /f

reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "CLSID" /t REG_SZ /d "%CAM_CLSID%" /f
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "DevicePath" /t REG_SZ /d "%CAM_SYM_LINK%" /f

reg add "HKCU\Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKCU\Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\%CAM_CLSID%" /v "CLSID" /t REG_SZ /d "%CAM_CLSID%" /f

:: 2. Media Foundation KSCATEGORY_VIDEO Interface Registration ({e5323777-f976-4f5b-9b55-b94699c46e44})
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{e5323777-f976-4f5b-9b55-b94699c46e44}\##?#usb#vid_dta1100&pid_2026&mi_00#dta_camera#{e5323777-f976-4f5b-9b55-b94699c46e44}" /v "DeviceInstance" /t REG_SZ /d "USB\VID_DTA1100&PID_2026&MI_00\DTA_CAMERA" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{e5323777-f976-4f5b-9b55-b94699c46e44}\##?#usb#vid_dta1100&pid_2026&mi_00#dta_camera#{e5323777-f976-4f5b-9b55-b94699c46e44}\#" /v "FriendlyName" /t REG_SZ /d "DTA Camera" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{e5323777-f976-4f5b-9b55-b94699c46e44}\##?#usb#vid_dta1100&pid_2026&mi_00#dta_camera#{e5323777-f976-4f5b-9b55-b94699c46e44}\#" /v "SymbolicLink" /t REG_SZ /d "%CAM_SYM_LINK%" /f

:: 3. DirectShow Audio Input Category Registration ({33D9A762-90C8-11D0-BD43-00A0C911CE86})
reg add "HKLM\SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%AUD_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%AUD_CLSID%" /v "CLSID" /t REG_SZ /d "%AUD_CLSID%" /f
reg add "HKLM\SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%AUD_CLSID%" /v "DevicePath" /t REG_SZ /d "%AUD_SYM_LINK%" /f

reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%AUD_CLSID%" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f
reg add "HKLM\SOFTWARE\WOW6432Node\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\%AUD_CLSID%" /v "CLSID" /t REG_SZ /d "%AUD_CLSID%" /f

:: 4. Media Foundation KSCATEGORY_AUDIO Interface Registration ({6994ad04-93ef-11d0-a3cc-00a0c9223196})
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{6994ad04-93ef-11d0-a3cc-00a0c9223196}\##?#usb#vid_dta1100&pid_2026&mi_01#dta_audio#{6994ad04-93ef-11d0-a3cc-00a0c9223196}\#" /v "FriendlyName" /t REG_SZ /d "DTA Audio" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{6994ad04-93ef-11d0-a3cc-00a0c9223196}\##?#usb#vid_dta1100&pid_2026&mi_01#dta_audio#{6994ad04-93ef-11d0-a3cc-00a0c9223196}\#" /v "SymbolicLink" /t REG_SZ /d "%AUD_SYM_LINK%" /f

echo.
echo Full DTA Camera and DTA Audio Media Foundation and DirectShow Registration Finished!
