const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dtaAPI', {
  controlWindow: (action) => ipcRenderer.send('window-control', action),
  openFileDialog: (filters, allowMulti = true, defaultPath = '') => ipcRenderer.invoke('open-file-dialog', filters, allowMulti, defaultPath),
  saveFileDialog: (options) => ipcRenderer.invoke('save-file-dialog', options),
  readFileContent: (filePath) => ipcRenderer.invoke('read-file-content', filePath),
  selectDirectory: (defaultPath = '') => ipcRenderer.invoke('open-directory-dialog', defaultPath),
  scanDirectoryVideos: (dirPath) => ipcRenderer.invoke('scan-directory-videos', dirPath),
  getSystemStats: () => ipcRenderer.invoke('get-system-stats'),
  launchChromeLive: () => ipcRenderer.invoke('launch-chrome-live'),
  launchChromeLoginCdp: () => ipcRenderer.invoke('launch-chrome-login-cdp'),
  openTikTokLoginWindow: () => ipcRenderer.invoke('open-tiktok-login-window'),
  getTikTokCookies: () => ipcRenderer.invoke('get-tiktok-cookies'),
  saveTikTokCookiesManual: (cookieString) => ipcRenderer.invoke('save-tiktok-cookies-manual', cookieString),
  clearTikTokCookies: () => ipcRenderer.invoke('clear-tiktok-cookies'),
  checkAppUpdate: () => ipcRenderer.invoke('check-app-update'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  onTikTokLoginSuccess: (callback) => ipcRenderer.on('tiktok-login-success', (event, data) => callback(data)),
  onSplashStatus: (callback) => ipcRenderer.on('splash-status', (event, data) => callback(data)),
  onOtaUpdateProgress: (callback) => ipcRenderer.on('ota-update-progress', (event, data) => callback(data)),
  appInfo: {
    name: 'DTA AutoLive',
    version: '2.3.1',
    owner: 'Đức Trường AI',
    phone: '0962.775.506',
    email: 'ductruong.onl@gmail.com',
    web: 'https://dta-studio.vercel.app/'
  }
});
