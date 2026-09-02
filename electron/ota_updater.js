/**
 * DTA Studio - Universal OTA Auto-Updater Engine.
 * Direct GitHub Releases Integration with Hot-Swap Support.
 * 
 * Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
 */

const { app } = require('electron');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

const GITHUB_OWNER = 'TruongAnh2706';
const GITHUB_REPO = 'DTA-LiveTik-Releases';

function parseSemver(vStr) {
  if (!vStr) return [0, 0, 0];
  const cleaned = vStr.replace(/^v/i, '').trim();
  const parts = cleaned.split('.').map(n => parseInt(n, 10) || 0);
  while (parts.length < 3) parts.push(0);
  return parts;
}

function isNewer(latestStr, currentStr) {
  const [lMaj, lMin, lPat] = parseSemver(latestStr);
  const [cMaj, cMin, cPat] = parseSemver(currentStr);

  if (lMaj > cMaj) return true;
  if (lMaj === cMaj && lMin > cMin) return true;
  if (lMaj === cMaj && lMin === cMin && lPat > cPat) return true;
  return false;
}

function fetchLatestReleaseInfo() {
  return new Promise((resolve, reject) => {
    const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`;
    const options = {
      headers: {
        'User-Agent': 'DTA-Studio-AutoUpdater/2.3.0',
        'Accept': 'application/vnd.github.v3+json'
      }
    };

    https.get(url, options, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        return fetchRedirect(res.headers.location).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`GitHub API HTTP ${res.statusCode}`));
      }

      let rawData = '';
      res.on('data', chunk => { rawData += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(rawData);
          resolve(parsed);
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

function fetchRedirect(redirectUrl) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'DTA-Studio-AutoUpdater/2.3.0',
        'Accept': 'application/vnd.github.v3+json'
      }
    };
    https.get(redirectUrl, options, (res) => {
      let rawData = '';
      res.on('data', chunk => { rawData += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(rawData));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

function downloadFileWithProgress(fileUrl, targetPath, onProgress) {
  return new Promise((resolve, reject) => {
    const followRedirectAndDownload = (url) => {
      const options = {
        headers: {
          'User-Agent': 'DTA-Studio-AutoUpdater/2.3.0'
        }
      };

      https.get(url, options, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 307) {
          return followRedirectAndDownload(res.headers.location);
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`Tải file thất bại với mã lỗi HTTP ${res.statusCode}`));
        }

        const totalBytes = parseInt(res.headers['content-length'] || '0', 10);
        let downloadedBytes = 0;
        let lastReportTime = Date.now();

        const fileStream = fs.createWriteStream(targetPath);

        res.on('data', chunk => {
          downloadedBytes += chunk.length;
          fileStream.write(chunk);

          const now = Date.now();
          if (now - lastReportTime > 200 || downloadedBytes === totalBytes) {
            lastReportTime = now;
            const percent = totalBytes > 0 ? Math.round((downloadedBytes / totalBytes) * 100) : 0;
            if (onProgress) {
              onProgress({
                percent,
                downloadedMb: (downloadedBytes / (1024 * 1024)).toFixed(1),
                totalMb: (totalBytes / (1024 * 1024)).toFixed(1)
              });
            }
          }
        });

        res.on('end', () => {
          fileStream.end();
          fileStream.on('finish', () => resolve(targetPath));
        });

        res.on('error', err => {
          fileStream.close();
          try { fs.unlinkSync(targetPath); } catch (e) {}
          reject(err);
        });
      }).on('error', reject);
    };

    followRedirectAndDownload(fileUrl);
  });
}

async function checkAndApplyUpdate({ onStatus, currentVersion = '2.3.0', isManual = false }) {
  try {
    if (onStatus) onStatus({ step: 'checking', message: 'Đang kiểm tra bản cập nhật mới từ máy chủ DTA...', percent: 88 });

    const release = await fetchLatestReleaseInfo();
    const latestTag = release.tag_name || '';
    const latestVersion = latestTag.replace(/^v/i, '');

    console.log(`[DTA OTA Updater] Current: v${currentVersion} | Latest: v${latestVersion}`);

    if (!isNewer(latestVersion, currentVersion)) {
      console.log('[DTA OTA Updater] Ứng dụng đã là phiên bản mới nhất.');
      return { hasUpdate: false, currentVersion, latestVersion };
    }

    console.log(`[DTA OTA Updater] 🚀 Phát hiện bản cập nhật mới: v${latestVersion}!`);
    if (onStatus) onStatus({
      step: 'available',
      message: `Phát hiện bản mới (v${latestVersion})! Đang tự động tải về...`,
      percent: 90,
      version: latestVersion,
      notes: release.body
    });

    // Find best asset (prioritize Setup installer .exe or Portable .zip)
    const assets = release.assets || [];
    let targetAsset = assets.find(a => a.name.endsWith('.exe') && (a.name.includes('Setup') || a.name.includes('Installer') || a.name.includes('DTA')));
    if (!targetAsset) {
      targetAsset = assets.find(a => a.name.endsWith('.exe'));
    }
    if (!targetAsset) {
      targetAsset = assets.find(a => a.name.endsWith('.zip') && (a.name.includes('Portable') || a.name.includes('DTA')));
    }
    if (!targetAsset) {
      targetAsset = assets.find(a => a.name.endsWith('.zip'));
    }

    if (!targetAsset) {
      throw new Error('Không tìm thấy tệp cài đặt hợp lệ trên máy chủ bản phát hành GitHub.');
    }

    const tempDir = path.join(os.tmpdir(), 'dta_autolive_update');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const downloadTarget = path.join(tempDir, targetAsset.name);
    console.log(`[DTA OTA Updater] Bắt đầu tải tệp: ${targetAsset.name} (${targetAsset.browser_download_url})...`);

    await downloadFileWithProgress(targetAsset.browser_download_url, downloadTarget, (progress) => {
      if (onStatus) {
        onStatus({
          step: 'downloading',
          percent: Math.min(99, 90 + Math.floor(progress.percent / 10)),
          downloadPercent: progress.percent,
          message: `Đang tải bản cập nhật v${latestVersion}: ${progress.percent}% (${progress.downloadedMb}MB / ${progress.totalMb}MB)...`
        });
      }
    });

    console.log(`[DTA OTA Updater] ✅ Đã tải xong bản cập nhật: ${downloadTarget}`);
    if (onStatus) onStatus({ step: 'downloaded', message: `Đã tải xong v${latestVersion}! Đang tự động cài đặt và khởi động lại...`, percent: 100 });

    // Execute Hot-Swap or Silent Setup Installer
    executeInstallAndRestart(downloadTarget);
    return { hasUpdate: true, latestVersion, downloaded: true };
  } catch (err) {
    console.warn('[DTA OTA Updater] Bỏ qua lỗi cập nhật:', err.message);
    return { hasUpdate: false, error: err.message };
  }
}

function executeInstallAndRestart(downloadedFilePath) {
  const currentPid = process.pid;
  const currentExe = process.execPath;
  const isExe = downloadedFilePath.endsWith('.exe');

  const updaterBatPath = path.join(os.tmpdir(), `dta_updater_${Date.now()}.bat`);

  let batScript = '';
  if (isExe) {
    // Run Setup Installer with full process termination to release Windows File Locks
    batScript = `
@echo off
chcp 65001 >nul
echo [DTA Studio] Đang dọn dẹp các tiến trình cũ trước khi cài đặt...
taskkill /F /PID ${currentPid} >nul 2>&1
taskkill /F /IM "DTA AutoLive.exe" /T >nul 2>&1
taskkill /F /IM "dta_backend.exe" /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo [DTA Studio] Đang khởi chạy bộ cài đặt phiên bản mới...
start "" "${downloadedFilePath}"
exit
    `;
  } else {
    // Portable ZIP Hot-Swap
    const appDir = path.dirname(currentExe);
    batScript = `
@echo off
chcp 65001 >nul
echo [DTA Studio] Đang đóng các tiến trình cũ để cập nhật...
taskkill /F /PID ${currentPid} >nul 2>&1
taskkill /F /IM "DTA AutoLive.exe" /T >nul 2>&1
taskkill /F /IM "dta_backend.exe" /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo [DTA Studio] Đang giải nén cập nhật đè bản mới...
powershell -Command "Expand-Archive -Path '${downloadedFilePath}' -DestinationPath '${appDir}' -Force"
del /f /q "${downloadedFilePath}" >nul 2>&1
start "" "${currentExe}"
exit
    `;
  }

  fs.writeFileSync(updaterBatPath, batScript, 'utf-8');

  // Spawn updater detached and quit current app immediately
  const child = spawn('cmd.exe', ['/c', updaterBatPath], {
    detached: true,
    stdio: 'ignore'
  });
  child.unref();

  setTimeout(() => {
    app.quit();
  }, 500);
}

module.exports = {
  checkAndApplyUpdate,
  fetchLatestReleaseInfo,
  isNewer,
  executeInstallAndRestart
};
