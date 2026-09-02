const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const net = require('net');
const os = require('os');

// Catch any unhandled process errors gracefully
process.on('uncaughtException', (err) => {
  console.error('[Electron Main Uncaught Exception]:', err);
});

// Prevent GPU cache file lock conflicts on Windows & enable smooth video decode
app.commandLine.appendSwitch('disable-gpu-shader-disk-cache');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('enable-features', 'PlatformHEVCDecoderSupport');

let splashWindow = null;
let mainWindow = null;
let pythonProcess = null;

// Send progress update to splash screen
function updateSplashStatus(percent, text) {
  if (splashWindow && !splashWindow.isDestroyed() && splashWindow.webContents) {
    splashWindow.webContents.send('splash-status', { percent, text });
  }
}

// Check if Backend Port 8765 is listening with a clean HTTP probe
function checkBackendPort(port = 8765, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(400);
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.on('error', () => {
      resolve(false);
    });
    socket.connect(port, host);
  });
}

// Ensure Modular Directory Architecture (Data, Models, Logs, Config) exists
function ensureAppDirectories() {
  const isPackaged = app.isPackaged;
  const appRootDir = isPackaged ? path.dirname(process.execPath) : path.join(__dirname, '..');
  const userAppDataDir = path.join(app.getPath('userData'), 'dta_storage');

  const targetDirs = [
    path.join(appRootDir, 'data'),
    path.join(appRootDir, 'models'),
    path.join(appRootDir, 'logs'),
    path.join(appRootDir, 'config'),
    path.join(userAppDataDir, 'data'),
    path.join(userAppDataDir, 'models'),
    path.join(userAppDataDir, 'logs'),
    path.join(userAppDataDir, 'config')
  ];

  targetDirs.forEach((dir) => {
    try {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    } catch (e) {
      console.warn('[DTA Storage] Không thể tạo thư mục cục bộ:', dir, e.message);
    }
  });

  return { appRootDir, userAppDataDir };
}

// Locate source directory across Dev & Packaged (app.asar.unpacked / resources) environments
function getAppSourcePaths() {
  ensureAppDirectories();
  const isPackaged = app.isPackaged;
  let rootDir = path.join(__dirname, '..');
  let srcDir = path.join(rootDir, 'src');

  if (isPackaged && process.resourcesPath) {
    const unpackedSrc = path.join(process.resourcesPath, 'app.asar.unpacked', 'src');
    const directResourceSrc = path.join(process.resourcesPath, 'src');
    const directAppSrc = path.join(process.resourcesPath, 'app', 'src');

    if (fs.existsSync(unpackedSrc)) {
      rootDir = path.join(process.resourcesPath, 'app.asar.unpacked');
      srcDir = unpackedSrc;
    } else if (fs.existsSync(directResourceSrc)) {
      rootDir = process.resourcesPath;
      srcDir = directResourceSrc;
    } else if (fs.existsSync(directAppSrc)) {
      rootDir = path.join(process.resourcesPath, 'app');
      srcDir = directAppSrc;
    }
  }

  return { rootDir, srcDir };
}

// Smart Python Executable Resolver for Windows & Packaged environments
function resolvePythonExecutable() {
  if (process.env.PYTHON_PATH && fs.existsSync(process.env.PYTHON_PATH)) {
    return process.env.PYTHON_PATH;
  }

  const rootDir = path.join(__dirname, '..');
  const candidatePaths = [];

  // 1. Virtual environments in project root or app resources
  candidatePaths.push(path.join(rootDir, '.venv', 'Scripts', 'python.exe'));
  candidatePaths.push(path.join(rootDir, 'venv', 'Scripts', 'python.exe'));
  candidatePaths.push(path.join(rootDir, '..', '.venv', 'Scripts', 'python.exe'));

  // 2. Packaged resources path
  if (process.resourcesPath) {
    candidatePaths.push(path.join(process.resourcesPath, 'python', 'python.exe'));
    candidatePaths.push(path.join(process.resourcesPath, 'backend', 'python.exe'));
    candidatePaths.push(path.join(process.resourcesPath, 'app', '.venv', 'Scripts', 'python.exe'));
  }

  // 3. User local Python installations
  const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
  candidatePaths.push(path.join(localAppData, 'Programs', 'Python', 'Python311', 'python.exe'));
  candidatePaths.push(path.join(localAppData, 'Programs', 'Python', 'Python312', 'python.exe'));
  candidatePaths.push(path.join(localAppData, 'Programs', 'Python', 'Python310', 'python.exe'));
  candidatePaths.push(path.join(localAppData, 'Programs', 'Python', 'Python39', 'python.exe'));

  // 4. System Python installations
  candidatePaths.push('C:\\Program Files\\Python311\\python.exe');
  candidatePaths.push('C:\\Program Files\\Python312\\python.exe');
  candidatePaths.push('C:\\Python311\\python.exe');
  candidatePaths.push('C:\\Python312\\python.exe');

  for (const candidate of candidatePaths) {
    try {
      if (fs.existsSync(candidate)) {
        console.log('[Electron Main] Đã tìm thấy môi trường Python:', candidate);
        return candidate;
      }
    } catch (e) {}
  }

  return process.platform === 'win32' ? 'python' : 'python3';
}

// Resolve Backend Launcher: Prefer bundled standalone executable if available, fallback to Python script
function resolveBackendLauncher() {
  const isPackaged = app.isPackaged;
  const rootDir = path.join(__dirname, '..');

  // Check bundled standalone backend executable (compiled with PyInstaller)
  if (isPackaged && process.resourcesPath) {
    const candidateExeList = [
      path.join(process.resourcesPath, 'backend', 'dta_backend.exe'),
      path.join(process.resourcesPath, 'backend', 'dta_backend', 'dta_backend.exe'),
      path.join(process.resourcesPath, 'dta_backend.exe')
    ];
    for (const exePath of candidateExeList) {
      if (fs.existsSync(exePath)) {
        console.log('[Electron Main] Sử dụng máy chủ nhúng độc lập (Standalone Exe):', exePath);
        return {
          command: exePath,
          args: [],
          cwd: path.dirname(exePath),
          env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
        };
      }
    }
  }

  // Check local dist/dta_backend in dev
  const devDistExe = path.join(rootDir, 'dist', 'dta_backend', 'dta_backend.exe');
  if (fs.existsSync(devDistExe)) {
    console.log('[Electron Main] Sử dụng bản build backend cục bộ:', devDistExe);
    return {
      command: devDistExe,
      args: [],
      cwd: path.dirname(devDistExe),
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
    };
  }

  // Fallback to Python module execution
  const pythonExecutable = resolvePythonExecutable();
  const { rootDir: effectiveRoot, srcDir } = getAppSourcePaths();

  return {
    command: pythonExecutable,
    args: ['-m', 'dta_autolive.launcher.backend_service'],
    cwd: effectiveRoot,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1',
      PYTHONPATH: `${srcDir};${process.env.PYTHONPATH || ''}`
    }
  };
}

// Launch Python Backend Service Process
async function startPythonBackend() {
  console.log('[Electron Main] Đang kiểm tra trạng thái máy chủ AI Python (Port 8765)...');
  updateSplashStatus(15, '[1/4] Kiểm tra phần cứng & Trình điều khiển DTA...');

  const isAlreadyRunning = await checkBackendPort(8765);
  if (isAlreadyRunning) {
    console.log('[Electron Main] Máy chủ Python Backend đang chạy sẵn trên cổng 8765.');
    updateSplashStatus(60, '[2/4] Đã kết nối máy chủ AI (Port 8765)...');
    return;
  }

  updateSplashStatus(35, '[2/4] Đang khởi tạo máy chủ Python & AI Qwen...');
  const launcher = resolveBackendLauncher();

  try {
    pythonProcess = spawn(launcher.command, launcher.args, {
      cwd: launcher.cwd,
      env: launcher.env
    });

    pythonProcess.on('error', (err) => {
      console.warn('[Electron Main] Lưu ý khi khởi chạy Backend (' + err.message + '). Backend có thể khởi chạy qua file batch hoặc dịch vụ nền.');
      pythonProcess = null;
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Python Backend]: ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Backend Error]: ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Electron Main] Tiến trình Python Backend đã đóng với mã ${code}`);
      pythonProcess = null;
    });
  } catch (err) {
    console.warn('[Electron Main] Bỏ qua ngoại lệ spawn Backend:', err.message);
    pythonProcess = null;
  }
}

function getAppIcon() {
  const icoPath = path.join(__dirname, 'renderer', 'assets', 'logo.ico');
  const pngPath = path.join(__dirname, 'renderer', 'assets', 'logo.png');
  return process.platform === 'win32' ? icoPath : pngPath;
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 320,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    show: false,
    icon: getAppIcon(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  splashWindow.loadFile(path.join(__dirname, 'renderer', 'splash.html'));

  splashWindow.once('ready-to-show', () => {
    splashWindow.show();
  });
}

const { screen } = require('electron');

// Quản lý lưu và khôi phục vị trí & kích thước cửa sổ
const windowStateFile = path.join(app.getPath('userData'), 'dta_window_state.json');

function loadWindowState() {
  const defaultState = {
    width: 1440,
    height: 900,
    x: undefined,
    y: undefined,
    isMaximized: false
  };

  try {
    if (fs.existsSync(windowStateFile)) {
      const data = JSON.parse(fs.readFileSync(windowStateFile, 'utf-8'));
      // Xác thực xem tọa độ có còn nằm trên màn hình hiển thị không
      if (data.x !== undefined && data.y !== undefined) {
        const displays = screen.getAllDisplays();
        const isVisibleOnAnyScreen = displays.some((display) => {
          const { x, y, width, height } = display.bounds;
          return data.x >= x && data.x < x + width && data.y >= y && data.y < y + height;
        });

        if (isVisibleOnAnyScreen) {
          return { ...defaultState, ...data };
        }
      }
      return { ...defaultState, width: data.width || 1440, height: data.height || 900, isMaximized: !!data.isMaximized };
    }
  } catch (e) {
    console.warn('[DTA WindowState] Không thể tải trạng thái cửa sổ cũ:', e.message);
  }

  return defaultState;
}

let saveWindowStateTimer = null;
function saveWindowState() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  clearTimeout(saveWindowStateTimer);
  saveWindowStateTimer = setTimeout(() => {
    try {
      if (!mainWindow || mainWindow.isDestroyed()) return;
      const isMaximized = mainWindow.isMaximized();
      const bounds = mainWindow.getNormalBounds ? mainWindow.getNormalBounds() : mainWindow.getBounds();
      const state = {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        isMaximized
      };
      fs.writeFileSync(windowStateFile, JSON.stringify(state, null, 2), 'utf-8');
    } catch (e) {
      console.warn('[DTA WindowState] Không thể lưu trạng thái cửa sổ:', e.message);
    }
  }, 300);
}

function createMainWindow() {
  const windowState = loadWindowState();

  const windowOptions = {
    width: windowState.width,
    height: windowState.height,
    minWidth: 420,
    minHeight: 520,
    frame: false,
    backgroundColor: '#090910',
    show: false,
    icon: getAppIcon(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  };

  if (windowState.x !== undefined && windowState.y !== undefined) {
    windowOptions.x = windowState.x;
    windowOptions.y = windowState.y;
  }

  mainWindow = new BrowserWindow(windowOptions);

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    if (windowState.isMaximized) {
      mainWindow.maximize();
    }
    mainWindow.show();
  });

  // Lắng nghe sự kiện di chuyển và co giãn kích thước cửa sổ để tự động ghi nhớ
  mainWindow.on('resize', saveWindowState);
  mainWindow.on('move', saveWindowState);
  mainWindow.on('close', saveWindowState);
}

// Auto-create Desktop Shortcut on first run (Portable / Packaged)
function createDesktopShortcutIfNotExists() {
  if (process.platform !== 'win32' || !app.isPackaged) return;
  try {
    const desktopDir = app.getPath('desktop');
    const shortcutPath = path.join(desktopDir, 'DTA AutoLive.lnk');
    if (fs.existsSync(shortcutPath)) return;

    const exePath = process.execPath;
    const icoPath = path.join(process.resourcesPath, 'assets', 'logo.ico');
    const vbsScript = `
      Set WshShell = WScript.CreateObject("WScript.Shell")
      Set shortcut = WshShell.CreateShortcut("${shortcutPath.replace(/\\/g, '\\\\')}")
      shortcut.TargetPath = "${exePath.replace(/\\/g, '\\\\')}"
      shortcut.WorkingDirectory = "${path.dirname(exePath).replace(/\\/g, '\\\\')}"
      shortcut.Description = "DTA AutoLive - Developed by DTA Studio"
      If "${fs.existsSync(icoPath)}" = "True" Then
        shortcut.IconLocation = "${icoPath.replace(/\\/g, '\\\\')}, 0"
      End If
      shortcut.Save
    `;
    const tempVbs = path.join(os.tmpdir(), `dta_create_shortcut_${Date.now()}.vbs`);
    fs.writeFileSync(tempVbs, vbsScript, 'utf-8');
    spawn('cscript.exe', ['//Nologo', tempVbs], { detached: true, stdio: 'ignore' }).unref();
    setTimeout(() => {
      try { if (fs.existsSync(tempVbs)) fs.unlinkSync(tempVbs); } catch (e) {}
    }, 5000);
    console.log('[DTA Studio] Đã tự động tạo Shortcut trên Desktop:', shortcutPath);
  } catch (err) {
    console.warn('[DTA Studio] Không thể tạo Desktop Shortcut tự động:', err.message);
  }
}

// App Lifecycle
app.whenReady().then(async () => {
  if (process.platform === 'win32') {
    app.setAppUserModelId('dtastudio.autolive.2.0');
    createDesktopShortcutIfNotExists();
  }
  const { session } = require('electron');
  if (session.defaultSession) {
    session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
      if (details.url.includes('tiktokcdn.com') || details.url.includes('tiktok.com') || details.url.includes('douyin.com')) {
        details.requestHeaders['Referer'] = 'https://www.tiktok.com/';
        details.requestHeaders['Origin'] = 'https://www.tiktok.com';
        details.requestHeaders['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';
      }
      callback({ cancel: false, requestHeaders: details.requestHeaders });
    });
  }

  createSplashWindow();
  await startPythonBackend();

  // Wait for Backend daemon to respond on port 8765
  let ready = false;
  let attempts = 0;
  while (!ready && attempts < 15) {
    attempts++;
    ready = await checkBackendPort(8765);
    if (!ready) {
      await new Promise(r => setTimeout(r, 400));
    }
  }

  updateSplashStatus(85, '[3/4] Khởi tạo Hệ thống Ghim SP & Tương tác Live...');
  await new Promise(r => setTimeout(r, 300));

  // -------------------------------------------------------------
  // DTA STUDIO UNIVERSAL OTA AUTO-UPDATER GATEWAY (Direct GitHub)
  // -------------------------------------------------------------
  let updateResult = null;
  try {
    const otaUpdater = require('./ota_updater');
    const currentVer = app.getVersion() || '2.3.0';
    updateResult = await otaUpdater.checkAndApplyUpdate({
      currentVersion: currentVer,
      onStatus: (status) => {
        updateSplashStatus(status.percent || 90, status.message);
      }
    });

    if (updateResult && updateResult.hasUpdate && updateResult.downloaded) {
      console.log('[DTA OTA Updater] Đang thực hiện cài đặt và khởi động lại phiên bản mới...');
      return; // Giữ splash window và để updater.bat tự restart app
    }
  } catch (otaErr) {
    console.warn('[DTA OTA Updater Error]:', otaErr.message);
  }

  updateSplashStatus(100, '[4/4] DTA AutoLive đã sẵn sàng phát sóng!');
  await new Promise(r => setTimeout(r, 400));
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  });
});

function terminateChromeLiveProcess() {
  console.log('[Electron Main] Đang dọn dẹp và tắt tiến trình Chrome Live (CDP :9222)...');
  try {
    const { execSync } = require('child_process');
    if (process.platform === 'win32') {
      // 1. Tắt các tiến trình Chrome/Edge khởi chạy theo profile hoặc cổng debug 9222 của DTA
      try {
        execSync('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like \'*--remote-debugging-port=9222*\' -or $_.CommandLine -like \'*dta_live_chrome_profile*\' -or $_.CommandLine -like \'*dta_live_browser_profile*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"', { timeout: 3000 });
      } catch (e) {}

      // 2. Dự phòng tắt theo kết nối cổng 9222
      try {
        execSync('powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"', { timeout: 2000 });
      } catch (e) {}
    }
  } catch (err) {
    console.log('[Cleanup Chrome Error]:', err.message);
  }
}

app.on('window-all-closed', () => {
  terminateChromeLiveProcess();
  if (pythonProcess) {
    console.log('[Electron Main] Terminating Python Backend process...');
    pythonProcess.kill();
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  terminateChromeLiveProcess();
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

app.on('will-quit', () => {
  terminateChromeLiveProcess();
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

// IPC Communication Handlers
ipcMain.on('window-control', (event, action) => {
  if (!mainWindow) return;
  if (action === 'minimize') mainWindow.minimize();
  if (action === 'maximize') {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
  if (action === 'close') {
    terminateChromeLiveProcess();
    mainWindow.close();
  }
});

ipcMain.handle('open-file-dialog', async (event, filters, allowMulti = true, defaultPath = '') => {
  const properties = allowMulti ? ['openFile', 'multiSelections'] : ['openFile'];
  const dialogOptions = {
    properties,
    filters: filters || [
      { name: 'Video Livestream', extensions: ['mp4', 'mkv', 'avi', 'mov'] },
      { name: 'Kịch bản JSON', extensions: ['json'] }
    ]
  };
  if (defaultPath && fs.existsSync(defaultPath)) {
    dialogOptions.defaultPath = defaultPath;
  }
  const result = await dialog.showOpenDialog(mainWindow, dialogOptions);
  if (result.canceled || !result.filePaths || result.filePaths.length === 0) return null;
  return allowMulti ? result.filePaths : (result.filePaths[0] || null);
});

ipcMain.handle('open-directory-dialog', async (event, defaultPath = '') => {
  const dialogOptions = {
    properties: ['openDirectory']
  };
  if (defaultPath && fs.existsSync(defaultPath)) {
    dialogOptions.defaultPath = defaultPath;
  }
  const result = await dialog.showOpenDialog(mainWindow, dialogOptions);
  return (result.filePaths && result.filePaths[0]) ? result.filePaths[0] : null;
});

ipcMain.handle('scan-directory-videos', async (event, dirPath) => {
  if (!dirPath || !fs.existsSync(dirPath)) return [];
  try {
    const files = fs.readdirSync(dirPath);
    const validExts = ['.mp4', '.mkv', '.avi', '.mov', '.flv'];
    return files
      .filter(f => validExts.includes(path.extname(f).toLowerCase()))
      .map(f => path.join(dirPath, f));
  } catch (e) {
    return [];
  }
});

ipcMain.handle('save-file-dialog', async (event, options) => {
  const fs = require('fs');
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: options?.defaultPath || 'script_timeline.json',
    filters: options?.filters || [{ name: 'Kịch bản JSON', extensions: ['json'] }]
  });
  if (result.canceled || !result.filePath) return { success: false };
  try {
    fs.writeFileSync(result.filePath, options?.content || '', 'utf-8');
    return { success: true, filePath: result.filePath };
  } catch (err) {
    console.error('Failed to save file:', err);
    return { success: false, error: err.message };
  }
});

ipcMain.handle('read-file-content', async (event, filePath) => {
  const fs = require('fs');
  if (!filePath || !fs.existsSync(filePath)) return null;
  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch (err) {
    console.error('Failed to read file:', err);
    return null;
  }
});

let prevCpuTimes = null;

ipcMain.handle('get-system-stats', () => {
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const ramUsage = Math.round(((totalMem - freeMem) / totalMem) * 100);
  const cpus = os.cpus();
  let idleTime = 0, totalTime = 0;
  cpus.forEach(cpu => {
    for (let type in cpu.times) totalTime += cpu.times[type];
    idleTime += cpu.times.idle;
  });

  let cpuUsage = 15;
  if (prevCpuTimes) {
    const diffTotal = totalTime - prevCpuTimes.totalTime;
    const diffIdle = idleTime - prevCpuTimes.idleTime;
    if (diffTotal > 0) {
      cpuUsage = Math.round(100 - (diffIdle / diffTotal) * 100);
    }
  }
  prevCpuTimes = { totalTime, idleTime };

  return {
    cpu: Math.min(100, Math.max(1, cpuUsage)),
    ram: ramUsage,
    free_mem_gb: (freeMem / (1024 ** 3)).toFixed(1),
    total_mem_gb: (totalMem / (1024 ** 3)).toFixed(1)
  };
});

ipcMain.handle('launch-chrome-live', async () => {
  const fs = require('fs');
  const userProfileDir = path.join(app.getPath('userData'), 'dta_live_chrome_profile');
  if (!fs.existsSync(userProfileDir)) {
    fs.mkdirSync(userProfileDir, { recursive: true });
  }

  const possibleChrome = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    path.join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'
  ];

  let chromeExe = 'chrome.exe';
  for (const p of possibleChrome) {
    if (fs.existsSync(p)) {
      chromeExe = p;
      break;
    }
  }

  const targetUrl = 'https://shop.tiktok.com/streamer/live/product/dashboard';
  const args = [
    `--remote-debugging-port=9222`,
    `--user-data-dir=${userProfileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    targetUrl
  ];

  spawn(chromeExe, args, { detached: true, stdio: 'ignore' }).unref();
  return { success: true, path: chromeExe };
});

// =============================================================================
// TIKTOK LIVE IN-APP LOGIN & COOKIES BRIDGE
// =============================================================================
let tiktokLoginWindow = null;

function getTikTokCookiesPath() {
  const dataDir = path.join(__dirname, '..', 'data');
  if (!fs.existsSync(dataDir)) {
    try { fs.mkdirSync(dataDir, { recursive: true }); } catch (e) {}
  }
  return path.join(dataDir, 'tiktok_cookies.json');
}

const CHROME_STEALTH_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';

function saveTikTokCookies(cookieString, cookiesList = []) {
  try {
    let cleanCookieStr = (cookieString || '').trim();
    // Auto-normalize if user only pasted sessionid value
    if (cleanCookieStr && !cleanCookieStr.includes('=')) {
      cleanCookieStr = `sessionid=${cleanCookieStr}`;
    }

    const filePath = getTikTokCookiesPath();
    const payload = {
      cookie_string: cleanCookieStr,
      updated_at: new Date().toISOString(),
      cookies_count: cookiesList.length || cleanCookieStr.split(';').length
    };
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), 'utf-8');
    
    // Also save in userData
    const userPath = path.join(app.getPath('userData'), 'tiktok_cookies.json');
    fs.writeFileSync(userPath, JSON.stringify(payload, null, 2), 'utf-8');
    return true;
  } catch (err) {
    console.error('Error saving TikTok cookies:', err);
    return false;
  }
}

function readSavedTikTokCookies() {
  const filePath = getTikTokCookiesPath();
  const userPath = path.join(app.getPath('userData'), 'tiktok_cookies.json');
  
  for (const p of [filePath, userPath]) {
    if (fs.existsSync(p)) {
      try {
        const raw = fs.readFileSync(p, 'utf-8');
        return JSON.parse(raw);
      } catch (e) {}
    }
  }
  return null;
}

ipcMain.handle('get-tiktok-cookies', () => {
  return readSavedTikTokCookies();
});

ipcMain.handle('save-tiktok-cookies-manual', (event, cookieString) => {
  const success = saveTikTokCookies(cookieString);
  return { success };
});

ipcMain.handle('clear-tiktok-cookies', () => {
  try {
    const p1 = getTikTokCookiesPath();
    const p2 = path.join(app.getPath('userData'), 'tiktok_cookies.json');
    if (fs.existsSync(p1)) fs.unlinkSync(p1);
    if (fs.existsSync(p2)) fs.unlinkSync(p2);
    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
});

// CDP Cookie Sniffer from External Chrome
async function sniffCookiesFromCdpPort(port = 9222) {
  const http = require('http');
  try {
    const listRes = await new Promise((resolve) => {
      const req = http.get(`http://127.0.0.1:${port}/json`, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch (e) { resolve(null); }
        });
      });
      req.on('error', () => resolve(null));
      req.setTimeout(800, () => { req.destroy(); resolve(null); });
    });

    if (!listRes || !Array.isArray(listRes) || !listRes.length) return null;
    const page = listRes.find(p => p.type === 'page' && p.webSocketDebuggerUrl) || listRes[0];
    if (!page || !page.webSocketDebuggerUrl) return null;

    if (typeof WebSocket === 'undefined') return null;

    return new Promise((resolve) => {
      const wsConn = new WebSocket(page.webSocketDebuggerUrl);
      wsConn.onopen = () => {
        wsConn.send(JSON.stringify({
          id: 991,
          method: 'Network.getCookies',
          params: { urls: ['https://www.tiktok.com', 'https://webcast.tiktok.com', 'https://shop.tiktok.com'] }
        }));
      };
      wsConn.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.id === 991 && msg.result && msg.result.cookies) {
            const cookies = msg.result.cookies;
            const hasSession = cookies.some(c => c.name === 'sessionid' || c.name === 'sessionid_ss');
            const cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');
            wsConn.close();
            if (hasSession && cookieString.length > 20) {
              resolve({ success: true, cookieString, cookies });
              return;
            }
          }
        } catch (e) {}
        resolve(null);
      };
      wsConn.onerror = () => resolve(null);
      setTimeout(() => {
        try { wsConn.close(); } catch (e) {}
        resolve(null);
      }, 1500);
    });
  } catch (err) {
    return null;
  }
}

ipcMain.handle('open-tiktok-login-window', async () => {
  return await launchChromeLoginCdpProcess();
});

async function launchChromeLoginCdpProcess() {
  const userProfileDir = path.join(app.getPath('userData'), 'dta_live_chrome_profile');
  if (!fs.existsSync(userProfileDir)) {
    try { fs.mkdirSync(userProfileDir, { recursive: true }); } catch (e) {}
  }

  const possibleChrome = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    path.join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'
  ];

  let chromeExe = 'chrome.exe';
  for (const p of possibleChrome) {
    if (fs.existsSync(p)) {
      chromeExe = p;
      break;
    }
  }

  const targetUrl = 'https://www.tiktok.com/';
  const args = [
    `--remote-debugging-port=9222`,
    `--user-data-dir=${userProfileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    targetUrl
  ];

  spawn(chromeExe, args, { detached: true, stdio: 'ignore' }).unref();

  // Start background sniffer for 90 seconds
  let sniffCount = 0;
  const snifferTimer = setInterval(async () => {
    sniffCount++;
    if (sniffCount > 60) {
      clearInterval(snifferTimer);
      return;
    }
    const res = await sniffCookiesFromCdpPort(9222);
    if (res && res.success) {
      clearInterval(snifferTimer);
      saveTikTokCookies(res.cookieString, res.cookies);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('tiktok-login-success', {
          cookieString: res.cookieString,
          cookiesCount: res.cookies.length
        });
      }
    }
  }, 1500);

  return { success: true, path: chromeExe };
}

// Launch Real External Chrome with Remote Debugging & Auto Sniff Cookies
ipcMain.handle('launch-chrome-login-cdp', async () => {
  return await launchChromeLoginCdpProcess();
});

// OTA Auto-Updater Manual Check & Upgrade Trigger
ipcMain.handle('check-app-update', async () => {
  const otaUpdater = require('./ota_updater');
  const currentVer = app.getVersion() || '2.3.0';
  return await otaUpdater.checkAndApplyUpdate({
    currentVersion: currentVer,
    isManual: true,
    onStatus: (status) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ota-update-progress', status);
      }
    }
  });
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion() || '2.3.0';
});
