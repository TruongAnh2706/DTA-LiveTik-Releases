@echo off
chcp 65001 >nul
echo ===============================================================================
echo 🚀 DTA STUDIO - BIÊN DỊCH BACKEND PYTHON SANG BINARY ONEDIR
echo Chủ sở hữu: Đức Trường AI ^| Hotline/Zalo: 0962.775.506
echo ===============================================================================

python build_backend.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ [HOÀN THÀNH] Backend đã được đóng gói an toàn tại dist/dta_backend/
) else (
    echo.
    echo ❌ [THẤT BẠI] Quá trình đóng gói gặp lỗi. Vui lòng kiểm tra lại.
)
pause
