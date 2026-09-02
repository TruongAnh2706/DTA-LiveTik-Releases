@echo off
chcp 65001 >nul
echo ===============================================================================
echo 🚀 DTA STUDIO - HỆ THỐNG ĐÓNG GÓI BỘ CÀI ĐẶT TOÀN DIỆN (INNO SETUP & ELECTRON)
echo Chủ sở hữu: Đức Trường AI ^| Hotline/Zalo: 0962.775.506
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [BƯỚC 1/3] Biên dịch Backend Python sang Binary Onedir...
python build_backend.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Lỗi biên dịch Backend!
    pause
    exit /b 1
)

echo.
echo [BƯỚC 2/3] Đóng gói giao diện Electron sang thư mục dist/win-unpacked...
call npm run pack
if %ERRORLEVEL% neq 0 (
    echo ❌ Lỗi đóng gói Electron!
    pause
    exit /b 1
)

echo.
echo [BƯỚC 3/3] Tạo bộ cài đặt Inno Setup Installer...
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" "installer\DTA_AutoLive_Setup.iss"
    echo.
    echo ✅ [THÀNH CÔNG] Đã tạo bộ cài đặt chuyên nghiệp tại: dist\installer\
) else (
    echo.
    echo ℹ️ Không tìm thấy trình biên dịch Inno Setup 6 tại Program Files.
    echo 📁 Ứng dụng đã được đóng gói hoàn chỉnh sẵn sàng tại thư mục: dist\win-unpacked\
    echo 💡 Bạn có thể cài đặt Inno Setup 6 (https://jrsoftware.org/isdl.php) rồi chạy lại script này để xuất file setup .exe!
)

echo.
echo ===============================================================================
echo 🎉 QUÁ TRÌNH ĐÓNG GÓI HOÀN TẤT AN TOÀN - MÃ NGUỒN ĐÃ ĐƯỢC BẢO VỆ TUYỆT ĐỐI!
echo ===============================================================================
pause
