@echo off
chcp 65001 >nul
title DTA AutoLive v2.3.2 - DTA Studio
color 0B

echo ===============================================================================
echo                DTA AUTOLIVE v2.3.2 - DTA STUDIO
echo    Trung Tam Dieu Khien Live Stream Chuyen Nghiep Cho TikTok Live Studio
echo ===============================================================================
echo  Chu quan: Duc Truong AI
echo  Hotline/Zalo: 0962.775.506
echo  Email: ductruong.onl@gmail.com
echo  Website: https://dta-studio.vercel.app/
echo  Facebook: https://www.facebook.com/phamductruong17/
echo ===============================================================================
echo.

if not exist "node_modules\electron" (
    echo [*] Dang tu dong cai dat goi thu vien...
    call npm install
)

echo [*] Giai phong tien trinh cu va khoi dong DTA AutoLive v2.3.2...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo.

call npm start

if %errorlevel% neq 0 (
    echo.
    echo [THONG BAO] Ung dung da dung [Exit Code: %errorlevel%].
    pause
)
