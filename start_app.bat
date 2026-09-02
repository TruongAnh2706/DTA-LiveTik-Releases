@echo off
chcp 65001 >nul
title DTA AutoLive v2.3.2 - DTA Studio Broadcast Control Center
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

echo [1/4] Kiem tra moi truong Node.js va Python...
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Node.js! Vui long cai dat Node.js de chay ung dung.
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python 3.11+.
    pause
    exit /b 1
)

echo [2/4] Kiem tra thu vien Electron...
if not exist "node_modules\electron" goto :INSTALL_DEPS
goto :PORT_CHECK

:INSTALL_DEPS
echo [!] Phat hien chua co goi thu vien can thiet [node_modules].
echo [*] Dang tu dong cai dat thu vien qua npm install...
echo [*] Qua trinh nay chi chay 1 lan dau tien, vui long cho trong giay lat...
echo -------------------------------------------------------------------------------
call npm install
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Cai dat goi npm that bai! Vui long kiem tra ket noi mang.
    pause
    exit /b 1
)
echo -------------------------------------------------------------------------------
echo [OK] Cai dat thu vien thanh cong!
echo.

:PORT_CHECK
echo [3/4] Giai phong tien trinh cu tren cong WebSocket 8765...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [4/4] Dang khoi dong DTA AutoLive Electron va Python Backend...
echo [*] Ung dung dang chay. Vui long khong tat cua so nay trong khi Live Stream.
echo.
echo -------------------------------------------------------------------------------

call npm start

if %errorlevel% neq 0 (
    echo.
    echo [THONG BAO] Ung dung da dung hoac gap loi [Exit Code: %errorlevel%].
    pause
)
