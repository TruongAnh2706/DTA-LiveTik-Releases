; ===============================================================================
; 🛠️ DTA STUDIO - PROFESSIONAL INNO SETUP SCRIPT
; Tên phần mềm: DTA AutoLive - Professional Live Automation Studio
; Đơn vị phát triển: DTA Studio
; Chủ sở hữu: Đức Trường AI
; Hotline / Zalo: 0962.775.506
; Website: https://dta-studio.vercel.app/
; ===============================================================================

#define MyAppName "DTA AutoLive"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "DTA Studio - Đức Trường AI"
#define MyAppURL "https://dta-studio.vercel.app/"
#define MyAppExeName "DTA AutoLive.exe"
#define MyAppId "{{77AC6413-6665-4C77-B8B3-C39733730A73}"

[Setup]
; Thông tin định danh ứng dụng
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL=https://github.com/TruongAnh2706/DTA-LiveTik-Releases/releases

; Cấu hình đường dẫn thư mục cài đặt mặc định
DefaultDirName={autopf}\DTA Studio\{#MyAppName}
DefaultGroupName=DTA Studio\{#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=

; Cấu hình xuất file cài đặt
OutputDir=..\dist\installer
OutputBaseFilename=DTA_AutoLive_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} (Phát triển bởi DTA Studio)

; Nén dữ liệu chuẩn cao cấp nhất (Khởi động và cài đặt siêu tốc)
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Giao diện chuyên nghiệp
WizardImageFile=
WizardSmallImageFile=
DisableProgramGroupPage=auto
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "vi"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
vi.InstallingDrivers=Đang cấu hình trình điều khiển DTA Virtual Camera & Audio...
vi.CreatingStorage=Đang khởi tạo cấu trúc thư mục lưu trữ Data, Models, Logs...
vi.LaunchApp=Khởi chạy DTA AutoLive ngay bây giờ
vi.CreateDesktopIcon=Tạo biểu tượng trên màn hình chính (Desktop)
vi.CreateQuickLaunchIcon=Tạo biểu tượng trên thanh Quick Launch

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; Khởi tạo sẵn cấu trúc thư mục phân tầng chuyên nghiệp
Name: "{app}\data"; Permissions: users-full
Name: "{app}\models"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\config"; Permissions: users-full
Name: "{app}\resources\backend"; Permissions: users-full

[Files]
; Copy toàn bộ bản build win-unpacked vào thư mục {app}
Source: "..\dist\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; File icon và assets nhận diện thương hiệu
Source: "..\assets\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Gỡ cài đặt {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{group}\Trang chủ DTA Studio"; Filename: "{#MyAppURL}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\logo.ico"

[Registry]
; Đăng ký DTA Virtual Camera vào Windows DirectShow Subsystem
Root: HKCU; Subkey: "Software\Classes\CLSID\{{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"; ValueType: string; ValueName: "FriendlyName"; ValueData: "DTA Camera"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\CLSID\{{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"; ValueType: string; ValueName: "CLSID"; ValueData: "{{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"; Flags: uninsdeletekey

; Đăng ký DTA Virtual Audio vào Windows DirectShow Audio Subsystem
Root: HKCU; Subkey: "Software\Classes\CLSID\{{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}"; ValueType: string; ValueName: "FriendlyName"; ValueData: "DTA Audio"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\CLSID\{{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}"; ValueType: string; ValueName: "CLSID"; ValueData: "{{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}"; Flags: uninsdeletekey

[Run]
; Khởi chạy ứng dụng sau khi cài đặt hoàn tất
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs\*"
Type: files; Name: "{app}\*.log"

[Code]
// Hàm kiểm tra và đóng tiến trình cũ trước khi cài đè nâng cấp (Hỗ trợ Auto-Update)
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  // Dừng tiến trình cũ nếu đang chạy
  ShellExec('open', 'taskkill.exe', '/F /IM "DTA AutoLive.exe" /T', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  ShellExec('open', 'taskkill.exe', '/F /IM "dta_backend.exe" /T', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
end;
