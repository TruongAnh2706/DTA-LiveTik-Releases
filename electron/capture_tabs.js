const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const artifactDir = 'C:\\Users\\Admin\\.gemini\\antigravity\\brain\\f80ee00a-de60-4508-aa54-1706482353d2';

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1366,
    height: 768,
    show: false,
    frame: false,
    backgroundColor: '#070A0F',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  await win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  await new Promise(r => setTimeout(r, 1000));

  const tabs = ['tab1', 'tab2', 'tab3', 'tab4', 'tab5'];

  for (let i = 0; i < tabs.length; i++) {
    const tabId = tabs[i];
    await win.webContents.executeJavaScript(`
      document.querySelectorAll('.sidebar-nav-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
      const activeNav = document.querySelector('[data-tab="${tabId}"]');
      if (activeNav) activeNav.classList.add('active');
      const activePanel = document.getElementById('${tabId}');
      if (activePanel) activePanel.classList.add('active');
    `);
    await new Promise(r => setTimeout(r, 500));

    const image = await win.webContents.capturePage();
    const savePath = path.join(artifactDir, `redesign_${tabId}.png`);
    fs.writeFileSync(savePath, image.toPNG());
    console.log(`Saved screenshot for ${tabId}: ${savePath}`);
  }

  app.quit();
});
