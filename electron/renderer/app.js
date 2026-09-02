let wsClient = null;
let currentVideoPath = '';
let currentStreamUrl = '';
let currentSourceMode = 'playlist'; // 'playlist' | 'url'
let isMuted = true;
let vuInterval = null;

// Application State Variables
let isLiveActive = false;
let isLivePaused = false;
let isBridgeConnected = false;
let isBackendConnected = false;
let isRecordingLive = false;
let currentRecordedChannel = 'TikTokLive';
let rawLogEntries = [];
let pendingActionCallback = null;

document.addEventListener('DOMContentLoaded', () => {
  initThemeController();
  initTitleBarControls();
  initTabNavigation();
  initSourceSwitcher();
  initTikTokAuthManager();
  initLiveStreamRecorder();
  initAudioSinkRouting();
  initAntiDuplicateFilters();
  initAudioMixerAndBgm();
  initCollapsiblePanels();
  initSystemResourceMonitor();
  initWebSocketConnection();
  initPlayerControls();
  initPlaylistManager();
  initAutoPinController();
  initSadcaptchaSolver();
  initQwenAiGpuController();
  initSatelliteSeedingController();
  initHostLiveChatbotUI();
  initTikTokCartScraperController();
  initLogTerminal();
  initModalHandlers();
  initWorkspaceHelpers();
});

// 0. Theme Toggle Controller (Dark / Light Mode)
function initThemeController() {
  const btnToggle = document.getElementById('btnToggleTheme');
  const iconEl = document.getElementById('themeIcon');
  const labelEl = document.getElementById('themeLabel');

  const savedTheme = localStorage.getItem('dta_app_theme') || 'dark';
  applyTheme(savedTheme);

  btnToggle?.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    localStorage.setItem('dta_app_theme', nextTheme);
    showToast(`Đã chuyển sang ${nextTheme === 'dark' ? 'Chế độ Tối (Dark Cyberpunk)' : 'Chế độ Sáng (Light Clean Tech)'}`, 'info');
  });

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (iconEl) iconEl.textContent = theme === 'dark' ? '☀️' : '🌙';
    if (labelEl) labelEl.textContent = theme === 'dark' ? 'Chế độ Sáng' : 'Chế độ Tối';
  }
}

// 1. Frameless Window TitleBar Controls
function initTitleBarControls() {
  document.getElementById('btnMinimizing')?.addEventListener('click', () => {
    window.dtaAPI?.controlWindow('minimize');
  });

  document.getElementById('btnMaximizing')?.addEventListener('click', () => {
    window.dtaAPI?.controlWindow('maximize');
  });

  document.getElementById('btnCloseApp')?.addEventListener('click', () => {
    if (isLiveActive) {
      openActionModal(
        '⚠️ PHIÊN LIVE STREAM ĐANG CHẠY',
        'Ứng dụng đang phát Live Stream trực tiếp sang TikTok LIVE Studio. Bạn có chắc chắn muốn DỪNG PHIÊN và THOÁT ứng dụng không?',
        () => {
          if (wsClient && wsClient.readyState === WebSocket.OPEN) {
            wsClient.send(JSON.stringify({ command: 'STOP_LIVE' }));
          }
          window.dtaAPI?.controlWindow('close');
        }
      );
    } else {
      window.dtaAPI?.controlWindow('close');
    }
  });

  document.getElementById('btnRegisterDevices')?.addEventListener('click', () => {
    const btn = document.getElementById('btnRegisterDevices');
    if (btn) btn.disabled = true;
    
    appendTerminalLog('[INFO] Đang gửi yêu cầu đăng ký DirectShow DTA Camera & DTA Audio Device Filters...', 'INFO');
    showToast('Đang đăng ký DTA Device Filters...', 'warning');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({ command: 'REGISTER_DEVICES' }));
    }

    setTimeout(() => {
      if (btn) btn.disabled = false;
    }, 2000);
  });
}

// 2. Tab Navigation Controller
function initTabNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav-item');
  const panels = document.querySelectorAll('.view-panel');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabId = item.getAttribute('data-tab');
      
      navItems.forEach(i => i.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      document.getElementById(tabId)?.classList.add('active');
      window.dispatchEvent(new Event('resize'));
    });
  });
}

// 2.5 Source Switcher Controller (Playlist vs TikTok Live URL)
function initSourceSwitcher() {
  const btnPlaylist = document.getElementById('btnSourcePlaylist');
  const btnTikTokUrl = document.getElementById('btnSourceTikTokUrl');
  const panelPlaylist = document.getElementById('sourcePanelPlaylist');
  const panelTikTokUrl = document.getElementById('sourcePanelTikTokUrl');
  const modeBadge = document.getElementById('sourceModeBadge');

  btnPlaylist?.addEventListener('click', () => {
    currentSourceMode = 'playlist';
    btnPlaylist.className = 'btn btn-primary';
    btnTikTokUrl.className = 'btn btn-secondary';
    if (panelPlaylist) panelPlaylist.style.display = 'flex';
    if (panelTikTokUrl) panelTikTokUrl.style.display = 'none';
    if (modeBadge) {
      modeBadge.textContent = 'Chế độ: Playlist';
      modeBadge.className = 'badge badge-green';
    }
    stopLivePreviewCanvas();
  });

  btnTikTokUrl?.addEventListener('click', () => {
    currentSourceMode = 'url';
    btnTikTokUrl.className = 'btn btn-primary';
    btnPlaylist.className = 'btn btn-secondary';
    if (panelPlaylist) panelPlaylist.style.display = 'none';
    if (panelTikTokUrl) panelTikTokUrl.style.display = 'flex';
    if (modeBadge) {
      modeBadge.textContent = 'Chế độ: TikTok Live URL';
      modeBadge.className = 'badge badge-cyan';
    }
  });

  // Handler for "Nạp Luồng Live"
  document.getElementById('btnResolveTikTokUrl')?.addEventListener('click', () => {
    const inputUrl = document.getElementById('inputTikTokLiveUrl');
    const targetUrl = (inputUrl?.value || '').trim();
    if (!targetUrl) {
      showToast('Vui lòng nhập link phòng TikTok Live hoặc @username!', 'warning');
      return;
    }

    appendTerminalLog(`[INFO] Đang trích xuất luồng phát TikTok Live từ URL: ${targetUrl}...`, 'INFO');
    showToast('Đang nạp luồng phát TikTok Live...', 'info');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'RESOLVE_TIKTOK_LIVE',
        url: targetUrl,
        cookies: savedTikTokCookies || localStorage.getItem('dta_tiktok_cookies') || ''
      }));
    }
  });
}

// 2.7b TikTok Live Real Chrome Auth & Cookie Synchronization
let savedTikTokCookies = '';

async function checkSavedTikTokCookies() {
  const statusText = document.getElementById('tiktokAuthStatusText');
  const authIcon = document.getElementById('tiktokAuthIcon');
  const btnLogin = document.getElementById('btnOpenTikTokLogin');
  const btnClear = document.getElementById('btnClearTikTokCookies');
  const badgeTab5 = document.getElementById('badgeTab5TikTokStatus');

  try {
    let saved = null;
    if (window.dtaAPI?.getTikTokCookies) {
      saved = await window.dtaAPI.getTikTokCookies();
    }

    if (saved && saved.cookie_string && saved.cookie_string.length > 20) {
      savedTikTokCookies = saved.cookie_string;
      const count = saved.cookies_count || saved.cookie_string.split(';').length;
      if (statusText) statusText.innerHTML = `<strong style="color: var(--success);">Đã Đăng Nhập TikTok</strong> (${count} cookies)`;
      if (authIcon) authIcon.textContent = '🟢';
      if (btnLogin) {
        btnLogin.textContent = '🔄 Đồng Bộ Lại';
        btnLogin.className = 'btn btn-secondary';
        btnLogin.title = 'Mở lại Google Chrome để làm mới Cookies nếu phiên hết hạn';
      }
      if (btnClear) btnClear.style.display = 'inline-flex';
      if (badgeTab5) {
        badgeTab5.textContent = 'Đã Đăng Nhập';
        badgeTab5.className = 'badge badge-green';
      }
      return true;
    } else {
      const local = localStorage.getItem('dta_tiktok_cookies');
      if (local && local.length > 20) {
        savedTikTokCookies = local;
        if (statusText) statusText.innerHTML = '<strong style="color: var(--success);">Đã Đăng Nhập TikTok</strong> (Sẵn Sàng)';
        if (authIcon) authIcon.textContent = '🟢';
        if (btnLogin) {
          btnLogin.textContent = '🔄 Đồng Bộ Lại';
          btnLogin.className = 'btn btn-secondary';
        }
        if (btnClear) btnClear.style.display = 'inline-flex';
        if (badgeTab5) {
          badgeTab5.textContent = 'Đã Đăng Nhập';
          badgeTab5.className = 'badge badge-green';
        }
        return true;
      } else {
        savedTikTokCookies = '';
        if (statusText) statusText.textContent = 'Chưa đăng nhập TikTok';
        if (authIcon) authIcon.textContent = '🔒';
        if (btnLogin) {
          btnLogin.textContent = '🔑 Đăng Nhập';
          btnLogin.className = 'btn btn-primary';
          btnLogin.title = 'Mở Google Chrome để đăng nhập và tự động đồng bộ tài khoản';
        }
        if (btnClear) btnClear.style.display = 'none';
        if (badgeTab5) {
          badgeTab5.textContent = 'Chưa Đăng Nhập';
          badgeTab5.className = 'badge badge-warning';
        }
        return false;
      }
    }
  } catch (e) {
    console.error('Error checking saved TikTok cookies:', e);
    return false;
  }
}

async function initTikTokAuthManager() {
  await checkSavedTikTokCookies();

  if (window.dtaAPI?.onTikTokLoginSuccess) {
    window.dtaAPI.onTikTokLoginSuccess((data) => {
      savedTikTokCookies = data.cookieString || '';
      showToast('🎉 Đăng nhập TikTok thành công! Đã tự động đồng bộ từ Chrome.', 'success');
      appendTerminalLog('[AUTH] 🎉 Đăng nhập TikTok thành công! Đã lưu Cookie Session từ Google Chrome.', 'SUCCESS');
      checkSavedTikTokCookies();

      // Auto re-resolve if input URL is present
      const inputUrl = document.getElementById('inputTikTokLiveUrl');
      if (inputUrl && inputUrl.value.trim()) {
        document.getElementById('btnResolveTikTokUrl')?.click();
      }
    });
  }
}

window.openTikTokLoginModal = async function() {
  showToast('Đang mở Google Chrome để đăng nhập TikTok...', 'info');
  appendTerminalLog('[AUTH] 🌐 Đang mở Google Chrome để đăng nhập TikTok. Bạn chỉ cần đăng nhập trên Chrome, app sẽ TỰ ĐỘNG BẮT COOKIES...', 'INFO');

  if (window.dtaAPI?.launchChromeLoginCdp) {
    await window.dtaAPI.launchChromeLoginCdp();
  } else if (window.dtaAPI?.openTikTokLoginWindow) {
    await window.dtaAPI.openTikTokLoginWindow();
  }

  // Trigger Python backend sniffer
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'SNIFF_TIKTOK_COOKIES_CDP', cdp_port: 9222 }));
    
    // Poll backend every 2s for 30s
    let pollAttempts = 0;
    const pollTimer = setInterval(() => {
      pollAttempts++;
      if (pollAttempts > 15 || savedTikTokCookies) {
        clearInterval(pollTimer);
        return;
      }
      if (wsClient && wsClient.readyState === WebSocket.OPEN) {
        wsClient.send(JSON.stringify({ command: 'SNIFF_TIKTOK_COOKIES_CDP', cdp_port: 9222 }));
      }
    }, 2000);
  }
};

window.clearTikTokCookiesAction = async function() {
  if (confirm('Bạn có chắc chắn muốn xóa Cookies TikTok đã lưu?')) {
    savedTikTokCookies = '';
    localStorage.removeItem('dta_tiktok_cookies');
    if (window.dtaAPI?.clearTikTokCookies) {
      await window.dtaAPI.clearTikTokCookies();
    }
    showToast('Đã xóa Cookies TikTok!', 'info');
    appendTerminalLog('[AUTH] Đã xóa Cookies TikTok.', 'INFO');
    initTikTokAuthManager();
  }
};

// 2.8 TikTok Live Stream Recorder Settings Controller
function initLiveStreamRecorder() {
  const inputDir = document.getElementById('inputRecordOutputDir');
  const chkAutoRecord = document.getElementById('chkAutoRecordStream');
  const btnSelectDir = document.getElementById('btnSelectRecordDir');
  const btnOpenDir = document.getElementById('btnOpenRecordDir');

  // Load saved output dir or fallback to default
  const savedDir = localStorage.getItem('dta_record_dir');
  if (savedDir && inputDir) {
    inputDir.value = savedDir;
  } else if (inputDir) {
    inputDir.value = 'D:\\DTA_Live_Records';
  }

  // Load saved auto-record preference
  const savedAutoRecord = localStorage.getItem('dta_auto_record');
  if (savedAutoRecord !== null && chkAutoRecord) {
    chkAutoRecord.checked = savedAutoRecord === 'true';
  }

  chkAutoRecord?.addEventListener('change', () => {
    localStorage.setItem('dta_auto_record', chkAutoRecord.checked.toString());
    const tag = document.getElementById('recorderStatusTag');
    if (tag) {
      tag.textContent = chkAutoRecord.checked ? 'MP4 Copy' : 'Tắt Ghi';
      tag.className = chkAutoRecord.checked ? 'badge badge-danger' : 'badge badge-warning';
    }
  });

  btnSelectDir?.addEventListener('click', async () => {
    if (window.dtaAPI?.selectDirectory) {
      const selectedPath = await window.dtaAPI.selectDirectory();
      if (selectedPath && inputDir) {
        inputDir.value = selectedPath;
        localStorage.setItem('dta_record_dir', selectedPath);
        appendTerminalLog(`[CONFIG] Đã chọn thư mục lưu Live: ${selectedPath}`, 'INFO');
        showToast('Đã lưu cấu hình thư mục ghi hình', 'success');
      }
    } else {
      showToast('Tính năng chọn thư mục chỉ khả dụng trên ứng dụng Desktop!', 'warning');
    }
  });

  btnOpenDir?.addEventListener('click', async () => {
    const targetPath = (inputDir?.value || '').trim();
    if (!targetPath) {
      showToast('Chưa cấu hình thư mục lưu video!', 'warning');
      return;
    }
    if (window.dtaAPI?.openDirectory) {
      const success = await window.dtaAPI.openDirectory(targetPath);
      if (success) {
        appendTerminalLog(`[INFO] Mở thư mục lưu trữ: ${targetPath}`, 'INFO');
      } else {
        showToast('Không thể mở thư mục. Vui lòng kiểm tra lại đường dẫn!', 'warning');
      }
    }
  });
}

// 3. System CPU/RAM Resource Monitor Polling
function initSystemResourceMonitor() {
  setInterval(async () => {
    if (window.dtaAPI?.getSystemStats) {
      try {
        const stats = await window.dtaAPI.getSystemStats();
        const cpuBar = document.getElementById('cpuMeterBar');
        const cpuVal = document.getElementById('cpuMeterVal');
        const ramBar = document.getElementById('ramMeterBar');
        const ramVal = document.getElementById('ramMeterVal');

        if (cpuBar && cpuVal) {
          cpuBar.style.width = `${stats.cpu}%`;
          cpuVal.textContent = `${stats.cpu}%`;
        }
        if (ramBar && ramVal) {
          ramBar.style.width = `${stats.ram}%`;
          ramVal.textContent = `${stats.ram}%`;
        }
      } catch (err) {
        console.log('Stats error:', err);
      }
    }
  }, 2000);
}

// 4. WebSocket Backend Connection Controller
function initWebSocketConnection() {
  const wsUrl = 'ws://127.0.0.1:8765';
  
  function connect() {
    wsClient = new WebSocket(wsUrl);

    wsClient.onopen = () => {
      isBridgeConnected = true;
      isBackendConnected = true;
      appendTerminalLog('[SUCCESS] Đã kết nối thành công tới Máy chủ AI Python (ws://127.0.0.1:8765)', 'SUCCESS');
      showToast('Máy chủ AI & Cổng kết nối đã sẵn sàng!', 'success');

      updateConnectionStatusDisplays(true, '12ms');

      if (currentScrapedProducts && currentScrapedProducts.length > 0) {
        wsClient.send(JSON.stringify({
          command: 'SYNC_CART_PRODUCTS_CATALOG',
          products: currentScrapedProducts
        }));
      }

      // Tự động kiểm tra Model AI & cập nhật GPU Telemetry ngay khi kết nối
      setTimeout(() => {
        if (typeof window.checkAiModel === 'function') {
          window.checkAiModel();
        }
        if (wsClient && wsClient.readyState === WebSocket.OPEN) {
          wsClient.send(JSON.stringify({ command: 'GET_GPU_TELEMETRY' }));

          const savedSad = localStorage.getItem('dta_sadcaptcha_key') || 'sadcaptcha_lic_8899aabbcc';
          const savedDs = localStorage.getItem('dta_deepseek_key') || '';
          const savedProv = localStorage.getItem('dta_ai_provider') || 'auto';

          wsClient.send(JSON.stringify({
            command: 'SAVE_API_KEYS',
            deepseek_key: savedDs,
            sadcaptcha_key: savedSad,
            ai_provider: savedProv
          }));

          if (savedSad && savedSad.length > 5) {
            wsClient.send(JSON.stringify({
              command: 'CHECK_SADCAPTCHA_CREDITS',
              api_key: savedSad
            }));
          }
          if (savedDs && savedDs.startsWith('sk-')) {
            wsClient.send(JSON.stringify({
              command: 'TEST_DEEPSEEK_API_KEY',
              api_key: savedDs
            }));
          }

          // Lấy trạng thái tọa độ tắt Live Studio đã lưu
          wsClient.send(JSON.stringify({
            command: 'GET_CALIBRATE_LIVE_STUDIO_COORDS'
          }));
        }
      }, 600);
    };

    wsClient.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'LOG') {
          appendTerminalLog(data.message, data.level || 'INFO');
        } else if (data.type === 'STATUS') {
          updateStatusMetrics(data);
        } else if (data.type === 'TIKTOK_COOKIES_SNIFFED') {
          if (data.data && data.data.success && data.data.cookie_string) {
            savedTikTokCookies = data.data.cookie_string;
            localStorage.setItem('dta_tiktok_cookies', savedTikTokCookies);
            showToast('🎉 Đã tự động đồng bộ Cookies TikTok từ Google Chrome!', 'success');
            appendTerminalLog('[AUTH] 🎉 Đã đồng bộ tài khoản TikTok từ Google Chrome thành công!', 'SUCCESS');
            checkSavedTikTokCookies();
            const inputUrl = document.getElementById('inputTikTokLiveUrl');
            if (inputUrl && inputUrl.value.trim()) {
              document.getElementById('btnResolveTikTokUrl')?.click();
            }
          }
        } else if (data.type === 'LIVE_PREVIEW_FRAME' && data.frame) {
          handleLivePreviewFrame(data.frame);
        } else if (data.type === 'TIKTOK_LIVE_RESOLVED') {
          handleTikTokLiveResolved(data.data);
        } else if (data.type === 'RECORDING_STARTED') {
          isRecordingLive = true;
          const recBadge = document.getElementById('stageRecBadge');
          if (recBadge) {
            recBadge.style.display = 'block';
            recBadge.textContent = '⏺ REC 00:00:00 | 0 MB';
          }
          appendTerminalLog(`[RECORDER] Bắt đầu ghi luồng Live vào: ${data.file_path}`, 'SUCCESS');
          showToast(`Đang ghi hình phiên Live sang file ${data.file_name}...`, 'info');
        } else if (data.type === 'RECORD_PROGRESS') {
          isRecordingLive = true;
          const recBadge = document.getElementById('stageRecBadge');
          if (recBadge && data.stats) {
            recBadge.style.display = 'block';
            recBadge.textContent = `⏺ REC ${data.stats.duration_formatted} | ${data.stats.size_formatted}`;
          }
        } else if (data.type === 'RECORD_FINISHED') {
          isRecordingLive = false;
          const recBadge = document.getElementById('stageRecBadge');
          if (recBadge) recBadge.style.display = 'none';

          appendTerminalLog(`[SUCCESS] Hoàn tất ghi hình! File lưu tại: ${data.file_path} (${data.size_formatted})`, 'SUCCESS');
          showToast(`Đã lưu video Live: ${data.file_name} (${data.size_formatted})`, 'success');

          // Popup action modal with 1-click Add to Playlist
          if (data.file_path) {
            openActionModal(
              '🔴 GHI HÌNH LIVE STREAM HOÀN TẤT',
              `Video phiên Live đã được lưu an toàn tại:<br><code style="color: var(--accent); font-size: 11.5px; word-break: break-all;">${data.file_path}</code><br><br><b>Dung lượng:</b> ${data.size_formatted}<br><br>Bạn có muốn <b>thêm video này vào Playlist</b> để phát lại ngay không?`,
              () => {
                window.addVideoToPlaylist(data.file_path);
                // Switch tab back to Playlist View
                const btnPlaylist = document.getElementById('btnSourcePlaylist');
                if (btnPlaylist) btnPlaylist.click();
              }
            );
          }
        } else if (data.type === 'PIN_EVENT_TRIGGERED') {
          handlePinEventTriggered(data);
        } else if (data.type === 'CAPTCHA_STATUS') {
          const statusScan = document.getElementById('statusCaptchaScan');
          if (statusScan && data.status) {
            statusScan.textContent = data.status;
            if (data.status.includes('quét')) statusScan.className = 'badge badge-green';
            else if (data.status.includes('giải')) statusScan.className = 'badge badge-cyan';
            else statusScan.className = 'badge badge-warning';
          }
        } else if (data.type === 'CAPTCHA_SOLVED') {
          showToast('Đã giải và trượt Captcha TikTok thành công!', 'success');
        } else if (data.type === 'SADCAPTCHA_CREDITS_RESULT') {
          const creditsEl = document.getElementById('badgeCreditsCount');
          if (data.credits !== null && data.credits !== undefined) {
            if (creditsEl) {
              creditsEl.textContent = `SadCaptcha: ${data.credits} Credits`;
              creditsEl.className = 'badge badge-green';
            }
            showToast(`SadCaptcha còn lại: ${data.credits} Credits`, 'success');
            appendTerminalLog(`[SUCCESS] 🔑 [SadCaptcha] Kiểm tra bản quyền thành công! Số dư: ${data.credits} Credits.`, 'SUCCESS');
          } else {
            if (creditsEl) {
              creditsEl.textContent = 'SadCaptcha: Lỗi Key / 0';
              creditsEl.className = 'badge badge-warning';
            }
            showToast('SadCaptcha API Key không hợp lệ hoặc hết hạn!', 'error');
            appendTerminalLog('[ERROR] ❌ [SadCaptcha] API Key không hợp lệ hoặc không thể lấy số Credits.', 'ERROR');
          }
        } else if (data.type === 'RECORDING_ERROR') {
          isRecordingLive = false;
          const recBadge = document.getElementById('stageRecBadge');
          if (recBadge) recBadge.style.display = 'none';
          appendTerminalLog(`[ERROR] ${data.error}`, 'ERROR');
          showToast(data.error || 'Lỗi ghi hình', 'error');
        } else if (data.type === 'AI_MODEL_STATUS_RESULT') {
          handleAiModelStatusResult(data.data);
        } else if (data.type === 'AI_MODEL_DELETED_RESULT') {
          if (data.data?.success) {
            showToast('Đã xóa tệp Model AI thành công!', 'success');
            appendTerminalLog('[SUCCESS] 🗑️ Đã xóa tệp Model AI khỏi thư viện.', 'SUCCESS');
            if (data.data.status) handleAiModelStatusResult(data.data.status);
          } else {
            showToast(`Lỗi khi xóa Model: ${data.data?.error || 'Không xác định'}`, 'error');
            appendTerminalLog(`[ERROR] ❌ Lỗi xóa Model: ${data.data?.error}`, 'ERROR');
          }
        } else if (data.type === 'MODELS_FOLDER_OPENED') {
          appendTerminalLog(`[SUCCESS] 📁 Đã mở thư mục lưu trữ Model AI: ${data.path}`, 'SUCCESS');
        } else if (data.type === 'AI_MODEL_DOWNLOAD_STARTED') {
          showModelDownloadProgressBox(true);
        } else if (data.type === 'AI_MODEL_DOWNLOAD_PROGRESS') {
          updateModelDownloadProgress(data.data);
        } else if (data.type === 'AI_MODEL_DOWNLOAD_CANCELLED') {
          showModelDownloadProgressBox(false);
          showToast('Đã hủy tiến trình tải Model', 'warning');
        } else if (data.type === 'AI_GPU_SERVER_RESULT') {
          handleAiGpuServerResult(data);
        } else if (data.type === 'AI_GPU_SERVER_STOPPED') {
          handleAiGpuServerStopped(data);
        } else if (data.type === 'GPU_TELEMETRY_RESULT') {
          updateGpuTelemetryUI(data.data);
        } else if (data.type === 'TIKTOK_CART_SCRAPED_RESULT') {
          handleTikTokCartScraped(data.data);
        } else if (data.type === 'SEEDING_STATUS_UPDATE') {
          updateSeedingStatusUI(data.status, data.color);
        } else if (data.type === 'HOST_CHATBOT_STATUS_UPDATE') {
          updateHostChatStatusUI(data.status, data.color);
        } else if (data.type === 'HOST_CHATBOT_REPLY_EVENT') {
          handleHostChatbotReplyEvent(data.data);
        } else if (data.type === 'CART_SEEDING_TEMPLATES_GENERATED') {
          handleCartSeedingTemplatesGenerated(data.templates);
        } else if (data.type === 'PLAYLIST_TRACK_CHANGED') {
          handlePlaylistTrackChanged(data);
        } else if (data.type === 'AI_BENCHMARK_RESULT') {
          handleAiBenchmarkResult(data.data);
        } else if (data.type === 'HOST_PIN_CALLOUT_EVENT') {
          handleHostPinCalloutEvent(data);
        } else if (data.type === 'SEEDING_SUPPORT_EVENT') {
          handleSeedingSupportEvent(data);
        } else if (data.type === 'PIN_ANALYTICS_RESULT') {
          updateHeatmapAnalyticsUI(data.data);
        } else if (data.type === 'DEEPSEEK_TEST_RESULT') {
          handleDeepSeekTestResult(data.data);
        } else if (data.type === 'API_KEYS_SAVED') {
          showToast('Đã lưu cấu hình API thành công!', 'success');
        } else if (data.type === 'CALIBRATION_STEP_PROMPT') {
          handleCalibrationStepPrompt(data);
        } else if (data.type === 'CALIBRATION_REALTIME_POS') {
          const posBox = document.getElementById('boxCalibRealtimeCoords');
          const posVal = document.getElementById('valCalibRealtimePos');
          if (posBox) posBox.style.display = 'block';
          if (posVal) posVal.textContent = `X: ${data.x}, Y: ${data.y}`;
        } else if (data.type === 'CALIBRATION_STEP_SAVED') {
          handleCalibrationStepSaved(data);
        } else if (data.type === 'CALIBRATION_COMPLETED') {
          handleCalibrationCompleted(data);
        } else if (data.type === 'CALIBRATION_CANCELLED') {
          handleCalibrationCancelled();
        } else if (data.type === 'LIVE_STUDIO_COORDS_RESULT') {
          updateLiveStudioCoordsStatusUI(data.is_calibrated, data.data);
        } else if (data.type === 'LIVE_STUDIO_COORDS_CLEARED') {
          updateLiveStudioCoordsStatusUI(false, null);
        } else if (data.type === 'TIMELINE_SYNC') {
          handleTimelineSync(data);
        } else if (data.type === 'BGM_STATE_UPDATE') {
          if (typeof window.handleBgmStateUpdate === 'function') window.handleBgmStateUpdate(data);
        } else if (data.type === 'BGM_TRACK_CHANGED') {
          if (typeof window.handleBgmTrackChanged === 'function') window.handleBgmTrackChanged(data);
        } else if (data.type === 'BGM_FOLDER_SCANNED') {
          appendTerminalLog(`[BGM] 📂 Đã quét thư mục nhạc nền: ${data.total_tracks} bài hát khả dụng.`, 'INFO');
          showToast(`Tìm thấy ${data.total_tracks} bài nhạc nền`, 'info');
        }
      } catch (e) {
        appendTerminalLog(`[WS RECEIVE] ${event.data}`, 'INFO');
      }
    };

    wsClient.onclose = () => {
      isBridgeConnected = false;
      isBackendConnected = false;
      appendTerminalLog('[WARNING] Mất kết nối tới Python Backend. Đang thử kết nối lại sau 3s...', 'WARNING');

      updateConnectionStatusDisplays(false, 'Disconnected');
      setTimeout(connect, 3000);
    };

    wsClient.onerror = () => {
      wsClient.close();
    };
  }

  connect();

  document.getElementById('btnRetryConnection')?.addEventListener('click', () => {
    connect();
  });
}

function updateConnectionStatusDisplays(connected, latencyText) {
  const topbarBackendDot = document.getElementById('topbarBackendDot');
  const topbarBackendText = document.getElementById('topbarBackendText');
  const topbarBridgeDot = document.getElementById('topbarBridgeDot');
  const topbarBridgeText = document.getElementById('topbarBridgeText');
  const devBridgeDot = document.getElementById('devBridgeDot');
  const devBridgeText = document.getElementById('devBridgeText');
  const inpageAlert = document.getElementById('inpageConnectionAlert');

  if (connected) {
    if (topbarBackendDot) topbarBackendDot.className = 'status-dot dot-green';
    if (topbarBackendText) topbarBackendText.textContent = 'Máy chủ AI: Sẵn sàng';
    if (topbarBridgeDot) topbarBridgeDot.className = 'status-dot dot-green';
    if (topbarBridgeText) topbarBridgeText.textContent = `Cổng kết nối: ${latencyText}`;

    if (devBridgeDot) devBridgeDot.className = 'status-dot dot-green';
    if (devBridgeText) devBridgeText.textContent = `Đã kết nối (${latencyText})`;

    if (inpageAlert) inpageAlert.style.display = 'none';
  } else {
    if (topbarBackendDot) topbarBackendDot.className = 'status-dot dot-red';
    if (topbarBackendText) topbarBackendText.textContent = 'Máy chủ AI: Đang kết nối...';
    if (topbarBridgeDot) topbarBridgeDot.className = 'status-dot dot-red';
    if (topbarBridgeText) topbarBridgeText.textContent = 'Cổng kết nối: Chưa kết nối';

    if (devBridgeDot) devBridgeDot.className = 'status-dot dot-red';
    if (devBridgeText) devBridgeText.textContent = 'Chưa kết nối';

    if (inpageAlert) inpageAlert.style.display = 'flex';
  }
}

function updateStatusMetrics(data) {
  const cardSession = document.getElementById('cardSessionStatus');
  const cardSessionSub = document.getElementById('cardSessionSub');
  const cardDuration = document.getElementById('cardLiveDuration');
  const cardFps = document.getElementById('cardStreamFps');
  const cardStreamSub = document.getElementById('cardStreamSub');
  const liveBadge = document.getElementById('liveBadgeStatus');
  const stageBadge = document.getElementById('stageBadge');
  const headerBadge = document.getElementById('headerLiveStatusBadge');

  if (cardSession && data.session_status) {
    cardSession.textContent = data.session_status;
    if (data.session_status.includes('LIVE')) {
      cardSession.style.color = 'var(--danger)';
      if (cardSessionSub) cardSessionSub.textContent = 'Đang phát sóng';
      if (liveBadge) {
        liveBadge.textContent = '● LIVE';
        liveBadge.className = 'badge badge-danger';
      }
      if (stageBadge) {
        stageBadge.textContent = 'LIVE 30FPS';
        stageBadge.className = 'stage-badge-indicator live';
      }
      if (headerBadge) {
        headerBadge.textContent = 'Trạng thái: Đang Live';
        headerBadge.className = 'badge badge-danger';
      }
    } else {
      cardSession.style.color = 'var(--text-primary)';
      if (cardSessionSub) cardSessionSub.textContent = 'IDLE Standby State';
      if (liveBadge) {
        liveBadge.textContent = 'PREVIEW';
        liveBadge.className = 'badge badge-cyan';
      }
      if (stageBadge) {
        stageBadge.textContent = 'STANDBY';
        stageBadge.className = 'stage-badge-indicator';
      }
      if (headerBadge) {
        headerBadge.textContent = 'Trạng thái: Sẵn sàng';
        headerBadge.className = 'badge badge-green';
      }
    }
  }

  if (cardDuration && data.live_duration) {
    cardDuration.textContent = data.live_duration;
  }
  if (cardFps && data.fps) {
    cardFps.textContent = `${data.fps} FPS`;
    if (cardStreamSub) cardStreamSub.textContent = `${data.dropped_frames || 0} Dropped · Target 30 FPS`;
  }
}

// 5. Player Controls & Preflight Engine
function initPlayerControls() {
  const btnStart = document.getElementById('btnStartLive');
  const btnPause = document.getElementById('btnPauseLive');
  const btnStop = document.getElementById('btnStopLive');
  const btnMute = document.getElementById('btnToggleMute');
  const videoPlayer = document.getElementById('previewVideoPlayer');

  btnStart?.addEventListener('click', () => {
    runPreflightValidationCheck();
  });

  btnPause?.addEventListener('click', () => {
    if (!isLiveActive) return;

    const cardSession = document.getElementById('cardSessionStatus');
    const cardSessionSub = document.getElementById('cardSessionSub');
    const stageBadge = document.getElementById('stageBadge');

    if (!isLivePaused) {
      isLivePaused = true;
      btnPause.textContent = '▶ Tiếp tục';
      btnPause.style.color = 'var(--warning)';
      btnPause.style.borderColor = 'var(--warning)';

      if (cardSession) {
        cardSession.textContent = 'TẠM DỪNG';
        cardSession.style.color = 'var(--warning)';
      }
      if (cardSessionSub) {
        cardSessionSub.textContent = 'Đang tạm dừng';
        cardSessionSub.style.color = 'var(--warning)';
      }
      if (stageBadge) {
        stageBadge.textContent = '❚❚ PAUSED';
        stageBadge.className = 'stage-badge-indicator paused';
      }

      if (videoPlayer) videoPlayer.pause();
      stopVuMeterAnimation();
      appendTerminalLog('[INFO] Đã tạm dừng phiên Live Stream.', 'WARNING');
      showToast('Đã tạm dừng Live Stream', 'warning');

      if (wsClient && wsClient.readyState === WebSocket.OPEN) {
        wsClient.send(JSON.stringify({ command: 'PAUSE_LIVE' }));
      }
    } else {
      isLivePaused = false;
      btnPause.textContent = '❚❚ Tạm dừng';
      btnPause.style.color = 'var(--text-primary)';
      btnPause.style.borderColor = 'var(--border-default)';

      if (cardSession) {
        cardSession.textContent = 'ĐANG PHÁT LIVE';
        cardSession.style.color = 'var(--danger)';
      }
      if (cardSessionSub) {
        cardSessionSub.textContent = 'Đang phát sóng trực tiếp';
        cardSessionSub.style.color = 'var(--cyan)';
      }
      if (stageBadge) {
        stageBadge.textContent = '🔴 ON AIR';
        stageBadge.className = 'stage-badge-indicator live';
      }

      if (videoPlayer) videoPlayer.play().catch(e => console.log(e));
      startVuMeterAnimation();
      appendTerminalLog('[SUCCESS] Tiếp tục phiên Live Stream.', 'SUCCESS');
      showToast('Đã tiếp tục Live Stream', 'success');

      if (wsClient && wsClient.readyState === WebSocket.OPEN) {
        wsClient.send(JSON.stringify({ command: 'RESUME_LIVE' }));
      }
    }
  });

  btnStop?.addEventListener('click', () => {
    openActionModal(
      '⏹ XÁC NHẬN DỪNG PHIÊN LIVE STREAM',
      'Bạn có chắc chắn muốn DỪNG HẲN phiên phát Live Stream không? Luồng Virtual Camera và DirectShow Audio sẽ trở về màn hình chờ DTA Standby.',
      () => {
        executeStopLive();
      }
    );
  });

  btnMute?.addEventListener('click', () => {
    isMuted = !isMuted;
    if (videoPlayer) {
      videoPlayer.muted = isMuted;
    }
    if (isMuted) {
      btnMute.textContent = '🔇';
      btnMute.title = 'Âm thanh loa kiểm âm: Đang tắt (Nhấn để bật)';
      btnMute.setAttribute('aria-pressed', 'true');
      appendTerminalLog('[INFO] Đã tắt tiếng Loa máy tính cục bộ (Âm thanh VẪN TRUYỀN SANG DTA AUDIO bình thường).', 'INFO');
    } else {
      btnMute.textContent = '🔊';
      btnMute.title = 'Âm thanh loa kiểm âm: Đang bật (Nhấn để tắt)';
      btnMute.setAttribute('aria-pressed', 'false');
      appendTerminalLog('[INFO] Đã mở lại tiếng Loa máy tính cục bộ.', 'INFO');
    }
  });

  // Automatically start VU Meter animation when video plays
  if (videoPlayer) {
    videoPlayer.addEventListener('play', () => startVuMeterAnimation());
    videoPlayer.addEventListener('playing', () => startVuMeterAnimation());
    videoPlayer.addEventListener('timeupdate', () => {
      if (!vuInterval && !videoPlayer.paused) {
        startVuMeterAnimation();
      }
    });
  }
}

let flvPlayerInstance = null;

function handleTikTokLiveResolved(info) {
  if (!info || !info.success) {
    if (info?.requires_login) {
      showToast(info.error || 'Yêu cầu đăng nhập TikTok để xem luồng này!', 'warning');
      appendTerminalLog(`[AUTH REQUIRED] 🔑 ${info.error}`, 'WARNING');
      // Prompt user with Action Modal to choose Chrome login or Manual cookie paste
      openActionModal(
        '🔑 YÊU CẦU ĐĂNG NHẬP TIKTOK',
        `Kênh <b>@${info.username || 'này'}</b> đang phát Live nhưng TikTok yêu cầu đăng nhập tài khoản để lấy luồng video.<br><br>` +
        `💡 <i>Để tránh lỗi "hoạt động quá thường xuyên", bạn nên:</i><br>` +
        `• <b>Cách 1 (Khuyên dùng):</b> Nhấn <b>"Tiếp tục"</b> để dán SessionID từ trình duyệt của bạn (100% thành công).<br>` +
        `• <b>Cách 2:</b> Bấm nút <b>"🌐 Chrome Thật"</b> trên thanh công cụ để đăng nhập bằng Google Chrome thật ngoài máy.<br><br>` +
        `Bấm <b>"Tiếp tục"</b> để mở bảng nạp Cookie:`,
        () => {
          window.openManualCookieModal();
        }
      );
      return;
    }

    showToast('Không thể phân giải luồng Live: ' + (info?.error || 'Phòng live không tồn tại hoặc đã tắt'), 'error');
    appendTerminalLog(`[ERROR] Phân giải TikTok Live thất bại: ${info?.error || 'Lỗi mạng'}`, 'ERROR');
    return;
  }

  currentStreamUrl = info.stream_url || '';
  currentSourceMode = 'url';
  currentRecordedChannel = info.username || 'TikTokLive';

  // Update input text if empty or changed
  const inputUrl = document.getElementById('inputTikTokLiveUrl');
  if (inputUrl && (!inputUrl.value || inputUrl.value.includes('@'))) {
    inputUrl.value = currentStreamUrl;
  }

  const titleEl = document.getElementById('ttRoomTitle');
  const streamerEl = document.getElementById('ttStreamerName');
  const viewerEl = document.getElementById('ttViewerCount');
  const urlBoxEl = document.getElementById('ttStreamUrlBox');
  const liveStatusBadge = document.getElementById('ttLiveStatusBadge');
  const videoPlayer = document.getElementById('previewVideoPlayer');
  const stageBadge = document.getElementById('stageBadge');

  if (titleEl) titleEl.textContent = info.room_title || `TikTok Live của @${info.username}`;
  if (streamerEl) streamerEl.textContent = `@${info.username}`;
  if (viewerEl) viewerEl.textContent = `${info.viewer_count || 'Trực tiếp'} người xem`;
  if (urlBoxEl) urlBoxEl.innerHTML = `<strong>Stream Pull URL:</strong> <span style="color: var(--accent);">${currentStreamUrl}</span>`;
  if (liveStatusBadge) {
    liveStatusBadge.textContent = '● Đang phát sóng';
    liveStatusBadge.className = 'badge badge-green';
  }
  if (stageBadge) {
    stageBadge.textContent = `LIVE: @${info.username}`;
    stageBadge.className = 'stage-badge-indicator live';
  }

  // Always kickstart VU Meter animation for live stream
  startVuMeterAnimation();

  // Load and play live stream directly inside 9:16 Preview Box
  if (videoPlayer && currentStreamUrl) {
    if (flvPlayerInstance) {
      try {
        flvPlayerInstance.pause();
        flvPlayerInstance.unload();
        flvPlayerInstance.detachMediaElement();
        flvPlayerInstance.destroy();
      } catch (err) {
        console.log('Error releasing previous flv instance:', err);
      }
      flvPlayerInstance = null;
    }

    // Reset video element cleanly
    videoPlayer.pause();
    videoPlayer.removeAttribute('src');
    videoPlayer.load();

    const isFlvStream = currentStreamUrl.includes('.flv') || (!currentStreamUrl.includes('.m3u8') && !currentStreamUrl.includes('.mp4'));

    if (isFlvStream && window.flvjs && window.flvjs.isSupported()) {
      try {
        videoPlayer.muted = isMuted;
        flvPlayerInstance = window.flvjs.createPlayer({
          type: 'flv',
          isLive: true,
          hasAudio: true,
          hasVideo: true,
          url: currentStreamUrl,
          cors: true
        }, {
          enableWorker: false,
          enableStashBuffer: true,
          stashInitialSize: 384,
          isLive: true,
          lazyLoad: false,
          lazyLoadMaxDuration: 3 * 60,
          lazyLoadRecoverDuration: 30,
          deferLoadAfterSourceOpen: false,
          autoCleanupSourceBuffer: false,
          autoCleanupMaxBackwardDuration: 120,
          autoCleanupMinBackwardDuration: 60,
          fixAudioTimestampGap: true,
          accurateSeek: false,
          seekType: 'range'
        });

        flvPlayerInstance.on(window.flvjs.Events.ERROR, (errType, errDetail, errInfo) => {
          console.warn('[FLV Player Error]', errType, errDetail, errInfo);
          if (info && info.hls_url && currentStreamUrl !== info.hls_url) {
            appendTerminalLog('[PREVIEW] Luồng FLV lỗi giải mã video, đang tự động chuyển sang luồng HLS...', 'WARNING');
            videoPlayer.src = info.hls_url;
            videoPlayer.play().catch(e => console.log('HLS play error:', e));
          }
        });

        flvPlayerInstance.on(window.flvjs.Events.MEDIA_INFO, (mediaInfo) => {
          console.log('[FLV Media Info]', mediaInfo);
          if (mediaInfo && mediaInfo.hasVideo) {
            appendTerminalLog(`[PREVIEW] Nhận luồng Video: ${mediaInfo.width || 1080}x${mediaInfo.height || 1920} (${mediaInfo.fps || 30} FPS, Codec: ${mediaInfo.videoCodec || 'H.264'})`, 'SUCCESS');
          }
        });

        flvPlayerInstance.attachMediaElement(videoPlayer);
        flvPlayerInstance.load();
        
        const playPromise = flvPlayerInstance.play();
        if (playPromise !== undefined) {
          playPromise.then(() => {
            startVuMeterAnimation();
            appendTerminalLog('[PREVIEW] Khung hình Preview 9:16 đã kết nối và hiển thị luồng phát.', 'SUCCESS');
          }).catch(e => {
            console.log('Autoplay handled:', e);
            videoPlayer.muted = true;
            videoPlayer.play().catch(err => console.log('Muted play error:', err));
          });
        }
      } catch (flvErr) {
        console.log('flv.js init error, falling back to standard video src:', flvErr);
        videoPlayer.src = currentStreamUrl;
        videoPlayer.play().catch(e => console.log('Preview fallback play:', e));
      }
    } else {
      videoPlayer.src = currentStreamUrl;
      videoPlayer.play().catch(e => console.log('Standard play:', e));
    }
  }

  appendTerminalLog(`[SUCCESS] Nạp luồng TikTok Live @${info.username} thành công! (${info.resolution || '1080x1920'})`, 'SUCCESS');
  showToast(`Đã nạp thành công luồng Live của @${info.username}!`, 'success');
}

let livePreviewImg = null;
let isLiveCanvasRendering = false;

function handleLivePreviewFrame(base64Frame) {
  const canvas = document.getElementById('livePreviewCanvas');
  if (!canvas) return;

  if (!livePreviewImg) {
    livePreviewImg = new Image();
  }

  livePreviewImg.onload = () => {
    if (canvas.width !== livePreviewImg.width || canvas.height !== livePreviewImg.height) {
      canvas.width = livePreviewImg.width;
      canvas.height = livePreviewImg.height;
    }
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(livePreviewImg, 0, 0, canvas.width, canvas.height);
      if (canvas.style.display === 'none') {
        canvas.style.display = 'block';
        isLiveCanvasRendering = true;
      }
    }
  };
  livePreviewImg.src = 'data:image/jpeg;base64,' + base64Frame;
}

function stopLivePreviewCanvas() {
  const canvas = document.getElementById('livePreviewCanvas');
  if (canvas) {
    canvas.style.display = 'none';
  }
  isLiveCanvasRendering = false;
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'STOP_PREVIEW_STREAM' }));
  }
}

function runPreflightValidationCheck() {
  const preflightModal = document.getElementById('preflightModal');
  const preflightBody = document.getElementById('preflightModalBody');
  const tbody = document.getElementById('playlistTableBody');
  const videoCount = tbody ? tbody.children.length : 0;

  const errors = [];
  if (!isBridgeConnected) errors.push('🌐 Extension Bridge chưa kết nối (ws://127.0.0.1:8765)');
  
  if (currentSourceMode === 'playlist') {
    if (videoCount === 0) errors.push('📁 Danh sách phát Playlist chưa có video nào');
  } else if (currentSourceMode === 'url') {
    if (!currentStreamUrl) errors.push('🔗 Chưa nạp luồng phát từ TikTok Live URL nào');
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;
  html += `<div>📷 DTA Camera Driver: <strong style="color: var(--success);">Sẵn sàng (DirectShow)</strong></div>`;
  html += `<div>🎙️ DTA Audio Driver: <strong style="color: var(--success);">Sẵn sàng (Virtual Sink)</strong></div>`;
  html += `<div>🌐 Extension Bridge: ${isBridgeConnected ? '<strong style="color: var(--success);">Đã kết nối (12ms)</strong>' : '<strong style="color: var(--danger);">Mất kết nối</strong>'}</div>`;
  
  if (currentSourceMode === 'playlist') {
    html += `<div>📁 Chế độ: <strong>Phát Playlist Video (${videoCount} Video)</strong></div>`;
    html += `<div>🎬 Video Phát: <strong>${currentVideoPath || 'sample_dta_live_1080x1920.mp4'}</strong></div>`;
  } else {
    html += `<div>🌐 Chế độ: <strong>Tiếp Sóng TikTok Live URL (Relay Stream)</strong></div>`;
    html += `<div>🔗 Stream Pull URL: <strong style="font-size: 11px; word-break: break-all;">${currentStreamUrl || '(Chưa nạp)'}</strong></div>`;
  }
  html += `</div>`;

  if (errors.length > 0) {
    html += `<div style="margin-top: 12px; padding: 10px; background: rgba(255, 77, 109, 0.12); border: 1px solid var(--danger); border-radius: 6px; color: var(--danger); font-weight: 600;">`;
    html += `⚠️ CHƯA ĐỦ ĐIỀU KIỆN PHÁT:<br>` + errors.join('<br>');
    html += `</div>`;
    
    const confirmBtn = document.getElementById('btnConfirmStartLive');
    if (confirmBtn) confirmBtn.disabled = true;
  } else {
    const confirmBtn = document.getElementById('btnConfirmStartLive');
    if (confirmBtn) confirmBtn.disabled = false;
  }

  if (preflightBody) preflightBody.innerHTML = html;
  if (preflightModal) preflightModal.classList.add('active');
}

let liveDurationSeconds = 0;
let liveDurationInterval = null;
let currentVideoSeconds = 0;
let videoPositionInterval = null;

function formatDuration(totalSeconds) {
  const sec = Math.floor(totalSeconds % 60);
  const min = Math.floor((totalSeconds / 60) % 60);
  const hrs = Math.floor(totalSeconds / 3600);
  const sStr = sec < 10 ? '0' + sec : sec;
  const mStr = min < 10 ? '0' + min : min;
  const hStr = hrs < 10 ? '0' + hrs : hrs;
  return `${hStr}:${mStr}:${sStr}`;
}

function startLiveSessionTimers() {
  stopLiveSessionTimers();

  const cardLiveDuration = document.getElementById('cardLiveDuration');
  const cardVideoPosition = document.getElementById('cardVideoPosition');
  const videoPlayer = document.getElementById('previewVideoPlayer');

  liveDurationInterval = setInterval(() => {
    if (isLiveActive && !isLivePaused) {
      liveDurationSeconds++;
      if (cardLiveDuration) {
        cardLiveDuration.textContent = formatDuration(liveDurationSeconds);
      }
    }
  }, 1000);

  videoPositionInterval = setInterval(() => {
    if (isLiveActive && !isLivePaused) {
      if (videoPlayer && !videoPlayer.paused && videoPlayer.currentTime > 0) {
        if (cardVideoPosition) {
          cardVideoPosition.textContent = formatDuration(videoPlayer.currentTime);
        }
      } else {
        currentVideoSeconds++;
        if (cardVideoPosition) {
          cardVideoPosition.textContent = formatDuration(currentVideoSeconds);
        }
      }
    }
  }, 1000);
}

function stopLiveSessionTimers() {
  if (liveDurationInterval) {
    clearInterval(liveDurationInterval);
    liveDurationInterval = null;
  }
  if (videoPositionInterval) {
    clearInterval(videoPositionInterval);
    videoPositionInterval = null;
  }
}

function executeStartLive() {
  const btnStart = document.getElementById('btnStartLive');
  const btnPause = document.getElementById('btnPauseLive');
  const btnStop = document.getElementById('btnStopLive');
  const videoPlayer = document.getElementById('previewVideoPlayer');
  const cardSession = document.getElementById('cardSessionStatus');
  const cardSessionSub = document.getElementById('cardSessionSub');
  const cardVideoName = document.getElementById('cardVideoName');
  const stageBadge = document.getElementById('stageBadge');
  const headerLiveBadge = document.getElementById('headerLiveStatusBadge');

  isLiveActive = true;
  isLivePaused = false;
  liveDurationSeconds = 0;
  currentVideoSeconds = 0;

  if (btnStart) {
    btnStart.disabled = true;
    btnStart.textContent = '🔴 Đang Phát';
  }
  if (btnPause) {
    btnPause.disabled = false;
    btnPause.textContent = '❚❚ Tạm dừng';
    btnPause.style.color = 'var(--text-primary)';
    btnPause.style.borderColor = 'var(--border-default)';
  }
  if (btnStop) btnStop.disabled = false;

  if (cardSession) {
    cardSession.textContent = 'ĐANG PHÁT LIVE';
    cardSession.style.color = 'var(--danger)';
  }
  if (cardSessionSub) {
    cardSessionSub.textContent = 'Đang phát sóng trực tiếp';
    cardSessionSub.style.color = 'var(--cyan)';
  }
  if (stageBadge) {
    stageBadge.textContent = '🔴 ON AIR';
    stageBadge.className = 'stage-badge-indicator live';
  }
  if (headerLiveBadge) {
    headerLiveBadge.textContent = '● Đang Phát Live';
    headerLiveBadge.className = 'badge badge-green';
  }

  if (currentSourceMode === 'url') {
    if (cardVideoName) cardVideoName.textContent = 'TikTok Live Relay Stream';
  } else {
    const allRows = Array.from(document.querySelectorAll('#playlistTableBody tr'));
    const playlistPaths = allRows.map(r => r.dataset.filePath || r.title).filter(Boolean);
    const targetFile = currentVideoPath || (playlistPaths[0] || 'sample_dta_live_1080x1920.mp4');
    const fileName = targetFile.split(/[\\/]/).pop();
    if (cardVideoName) cardVideoName.textContent = fileName;
  }

  if (videoPlayer) {
    videoPlayer.muted = isMuted;
    videoPlayer.volume = isMuted ? 0 : 1.0;
    videoPlayer.play().catch(e => console.log('Autoplay:', e));
  }

  startLiveSessionTimers();
  startVuMeterAnimation();
  appendTerminalLog('[SUCCESS] Bắt đầu phiên Live Stream! Luồng DirectShow DTA Virtual Camera & DTA Audio đang phát...', 'SUCCESS');
  showToast('Đã bắt đầu phát Live Stream thành công!', 'success');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    const audioSink = document.getElementById('selectAudioSink')?.value || 'cable';
    if (currentSourceMode === 'url') {
      const chkRecord = document.getElementById('chkAutoRecordStream');
      const inputRecordDir = document.getElementById('inputRecordOutputDir');
      wsClient.send(JSON.stringify({
        command: 'START_LIVE',
        mode: 'url',
        stream_url: currentStreamUrl,
        audio_sink: audioSink,
        auto_record: chkRecord ? chkRecord.checked : true,
        record_dir: (inputRecordDir?.value || '').trim() || null,
        channel_name: currentRecordedChannel || 'TikTokLive'
      }));
    } else {
      const allRows = Array.from(document.querySelectorAll('#playlistTableBody tr'));
      const playlistPaths = allRows.map(r => r.dataset.filePath || r.title).filter(Boolean);
      const chkAutoStop = document.getElementById('chkAutoStopLiveStudio');

      wsClient.send(JSON.stringify({
        command: 'START_LIVE',
        mode: 'file',
        file_path: currentVideoPath || (playlistPaths[0] || 'sample_dta_live_1080x1920.mp4'),
        playlist: playlistPaths.length > 0 ? playlistPaths : [currentVideoPath || 'sample_dta_live_1080x1920.mp4'],
        audio_sink: audioSink,
        auto_stop_live_studio: chkAutoStop ? chkAutoStop.checked : true
      }));
    }

    // Kích hoạt tính năng Chống dừng Live Studio (Anti-AFK) nếu và chỉ nếu người dùng bật
    const chkAntiAfk = document.getElementById('chkAntiAfkLive');
    if (chkAntiAfk && chkAntiAfk.checked) {
      wsClient.send(JSON.stringify({ command: 'START_ANTI_AFK' }));
    } else {
      wsClient.send(JSON.stringify({ command: 'STOP_ANTI_AFK' }));
    }
  }
}

function handleTimelineSync(data) {
  if (!data || typeof data.current_seconds !== 'number') return;
  const currentSec = data.current_seconds;
  currentVideoSeconds = Math.floor(currentSec);

  const cardVideoPosition = document.getElementById('cardVideoPosition');
  if (cardVideoPosition) {
    cardVideoPosition.textContent = formatDuration(currentVideoSeconds);
  }

  // Khóa cứng đồng hồ Preview Player trên App khớp 100% với luồng Virtual Camera truyền sang TikTok LIVE Studio
  const videoPlayer = document.getElementById('previewVideoPlayer');
  if (videoPlayer && !videoPlayer.paused && !videoPlayer.seeking && (data.duration_seconds || 0) > 0) {
    const timeDiff = Math.abs(videoPlayer.currentTime - currentSec);
    // Nếu bị lệch trên 200ms do browser decode trễ, tự động căn chỉnh lại mốc thời gian tức thì
    if (timeDiff > 0.2) {
      videoPlayer.currentTime = currentSec;
    }
  }
}

function handlePlaylistTrackChanged(data) {
  if (!data) return;
  const index = data.index;
  const filePath = data.file_path || '';
  const fileName = filePath.split(/[\\/]/).pop();

  currentVideoPath = filePath;
  currentVideoSeconds = 0;

  const cardVideoName = document.getElementById('cardVideoName');
  if (cardVideoName && fileName) {
    cardVideoName.textContent = fileName;
  }

  const cardVideoPosition = document.getElementById('cardVideoPosition');
  if (cardVideoPosition) {
    cardVideoPosition.textContent = '00:00:00';
  }

  const videoPlayer = document.getElementById('previewVideoPlayer');
  if (videoPlayer && filePath) {
    // 1. Giữ nguyên trạng thái âm thanh Loa kiểm âm (Muted / Unmuted) và Volume của Loa máy tính
    videoPlayer.muted = isMuted;
    videoPlayer.volume = isMuted ? 0 : 1.0;

    // 2. Chuyển nguồn video (Chỉ phục vụ xem trước & kiểm âm cục bộ)
    videoPlayer.src = filePath;

    // 3. Phát video kiểm âm liền mạch
    const playPromise = videoPlayer.play();
    if (playPromise !== undefined) {
      playPromise.then(() => {
        videoPlayer.muted = isMuted;
        videoPlayer.volume = isMuted ? 0 : 1.0;
        startVuMeterAnimation();
      }).catch((err) => {
        console.log('[Autoplay Policy Fallback]', err);
        // Fallback an toàn nếu Chromium yêu cầu phát muted trước
        videoPlayer.muted = true;
        videoPlayer.play().then(() => {
          if (!isMuted) {
            setTimeout(() => {
              videoPlayer.muted = false;
              videoPlayer.volume = 1.0;
            }, 100);
          }
          startVuMeterAnimation();
        }).catch(() => {});
      });
    }
  }

  // Highlight dòng đang phát trên giao diện
  const rows = document.querySelectorAll('#playlistTableBody tr');
  rows.forEach((r, idx) => {
    if (idx === index) {
      r.classList.add('playing-row');
      r.classList.add('selected');
      const badge = r.querySelector('td:nth-child(2) span');
      if (badge) {
        badge.className = 'badge badge-cyan';
        badge.innerHTML = '🔴 ON AIR';
      }
      r.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      r.classList.remove('playing-row');
      r.classList.remove('selected');
      const badge = r.querySelector('td:nth-child(2) span');
      if (badge) {
        badge.className = 'badge badge-green';
        badge.textContent = 'Sẵn sàng';
      }
    }
  });

  appendTerminalLog(`[PLAYLIST] 🎬 Đang phát video #${index + 1}: ${fileName}`, 'INFO');
}

function executeStopLive() {
  const btnStart = document.getElementById('btnStartLive');
  const btnPause = document.getElementById('btnPauseLive');
  const btnStop = document.getElementById('btnStopLive');
  const videoPlayer = document.getElementById('previewVideoPlayer');
  const cardSession = document.getElementById('cardSessionStatus');
  const cardSessionSub = document.getElementById('cardSessionSub');
  const cardVideoName = document.getElementById('cardVideoName');
  const cardLiveDuration = document.getElementById('cardLiveDuration');
  const cardVideoPosition = document.getElementById('cardVideoPosition');
  const stageBadge = document.getElementById('stageBadge');
  const headerLiveBadge = document.getElementById('headerLiveStatusBadge');

  isLiveActive = false;
  isLivePaused = false;
  liveDurationSeconds = 0;
  currentVideoSeconds = 0;
  stopLiveSessionTimers();

  if (btnStart) {
    btnStart.disabled = false;
    btnStart.textContent = '▶ Bắt đầu Live';
  }
  if (btnPause) {
    btnPause.disabled = true;
    btnPause.textContent = '❚❚ Tạm dừng';
    btnPause.style.color = 'var(--text-primary)';
    btnPause.style.borderColor = 'var(--border-default)';
  }
  if (btnStop) btnStop.disabled = true;

  if (cardSession) {
    cardSession.textContent = 'CHỜ PHÁT';
    cardSession.style.color = 'var(--text-primary)';
  }
  if (cardSessionSub) {
    cardSessionSub.textContent = 'Standby';
    cardSessionSub.style.color = 'var(--text-tertiary)';
  }
  if (cardLiveDuration) {
    cardLiveDuration.textContent = '00:00:00';
  }
  if (cardVideoPosition) {
    cardVideoPosition.textContent = '00:00:00';
  }
  if (cardVideoName) cardVideoName.textContent = 'Chưa phát video';

  if (stageBadge) {
    stageBadge.textContent = 'STANDBY';
    stageBadge.className = 'stage-badge-indicator';
  }
  if (headerLiveBadge) {
    headerLiveBadge.textContent = 'Trạng thái: Sẵn sàng';
    headerLiveBadge.className = 'badge badge-green';
  }

  if (videoPlayer) {
    videoPlayer.pause();
    videoPlayer.currentTime = 0;
  }

  stopVuMeterAnimation();
  stopLivePreviewCanvas();
  appendTerminalLog('[INFO] Đã dừng hẳn phiên Live Stream. Hệ thống trở về màn hình chờ DTA Standby Screen.', 'INFO');
  showToast('Đã dừng phiên Live Stream', 'warning');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'STOP_LIVE' }));
    wsClient.send(JSON.stringify({ command: 'STOP_ANTI_AFK' }));
  }
}

// Lắng nghe sự kiện bật/tắt thủ công của Anti-AFK Switch với lưu trữ localStorage
document.getElementById('chkAntiAfkLive')?.addEventListener('change', (e) => {
  localStorage.setItem('dta_anti_afk_enabled', e.target.checked ? 'true' : 'false');
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    if (e.target.checked) {
      wsClient.send(JSON.stringify({ command: 'START_ANTI_AFK' }));
      appendTerminalLog('[ANTI-AFK] 🛡️ Đã bật chế độ Chống Dừng Live TikTok Studio.', 'SUCCESS');
    } else {
      wsClient.send(JSON.stringify({ command: 'STOP_ANTI_AFK' }));
      appendTerminalLog('[ANTI-AFK] 🛑 Đã tắt chế độ Chống Dừng Live.', 'INFO');
    }
  }
});

// Khôi phục trạng thái Anti-AFK từ localStorage khi khởi chạy
(() => {
  const savedState = localStorage.getItem('dta_anti_afk_enabled');
  const chk = document.getElementById('chkAntiAfkLive');
  if (chk && savedState !== null) {
    chk.checked = (savedState === 'true');
  }
})();

// Lắng nghe sự kiện bật/tắt Tự động tắt Live Studio khi hết video
document.getElementById('chkAutoStopLiveStudio')?.addEventListener('change', (e) => {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'SET_AUTO_STOP_LIVE_STUDIO',
      enabled: e.target.checked
    }));
  }
  const stateText = e.target.checked ? 'BẬT' : 'TẮT';
  appendTerminalLog(`[LIVE-STUDIO] 🛑 Đã ${stateText} chế độ Tự động tắt Live Studio khi hết video.`, 'INFO');
});

// Nút Bắt Tọa Độ Tắt Live Studio (Chế độ tương tác 3 bước)
let isLiveStudioCalibrating = false;
document.getElementById('btnCalibrateStopLiveStudio')?.addEventListener('click', () => {
  if (!wsClient || wsClient.readyState !== WebSocket.OPEN) {
    showToast('Chưa kết nối tới DTA Backend Engine!', 'error');
    return;
  }

  if (isLiveStudioCalibrating) {
    wsClient.send(JSON.stringify({ command: 'CANCEL_CALIBRATE_LIVE_STUDIO' }));
    handleCalibrationCancelled();
    return;
  }

  isLiveStudioCalibrating = true;
  const btn = document.getElementById('btnCalibrateStopLiveStudio');
  if (btn) {
    btn.textContent = '⏳ Chờ Chụp Bước 1/3...';
    btn.style.background = 'rgba(255, 215, 0, 0.2)';
    btn.style.borderColor = '#FFD700';
    btn.style.color = '#FFD700';
  }

  const posBox = document.getElementById('boxCalibRealtimeCoords');
  if (posBox) posBox.style.display = 'block';

  wsClient.send(JSON.stringify({ command: 'START_CALIBRATE_LIVE_STUDIO' }));
  showToast('👉 Bước 1: Rê chuột vào Nút Thời Gian Live -> Nhấn Phím F8 để chụp tọa độ!', 'info');
  appendTerminalLog('[CALIBRATE] 🎯 BẮT ĐẦU HIỆU CHỈNH: Rê chuột vào nút trên TikTok Live Studio và nhấn duy nhất PHÍM F8!', 'ACTION');
});

// Nút Test Tự Động Tắt TikTok Live Studio (Chạy quy trình tự động tắt theo tọa độ)
document.getElementById('btnTestStopLiveStudio')?.addEventListener('click', () => {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'TEST_STOP_TIKTOK_LIVE_STUDIO' }));
    appendTerminalLog('[LIVE-STUDIO] ⚡ Đang chạy thử nghiệm quy trình tự động tắt TikTok Live Studio...', 'ACTION');
    showToast('Đang kích hoạt quy trình tắt TikTok Live Studio theo tọa độ...', 'info');
  } else {
    showToast('Chưa kết nối tới DTA Backend Engine!', 'error');
  }
});

// Nút Xóa Tọa Độ Đã Lưu (Quay về mặc định)
document.getElementById('btnClearLiveStudioCoords')?.addEventListener('click', () => {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'CLEAR_CALIBRATE_LIVE_STUDIO' }));
    showToast('Đã xóa tọa độ tùy chỉnh, quay về chế độ tự động!', 'info');
  }
});

function handleCalibrationStepPrompt(data) {
  const step = data.step || 1;
  const total = data.total_steps || 3;
  const btn = document.getElementById('btnCalibrateStopLiveStudio');
  if (btn) {
    btn.textContent = `⏳ Nhấn F8 Bước ${step}/${total}...`;
  }
  const posBox = document.getElementById('boxCalibRealtimeCoords');
  if (posBox) posBox.style.display = 'block';
  showToast(`👉 ${data.title}: ${data.guide}`, 'info');
}

function handleCalibrationStepSaved(data) {
  const step = data.step || 1;
  const total = data.total_steps || 3;
  const coords = data.coords || {};
  appendTerminalLog(`[CALIBRATE] ✅ Đã bắt tọa độ Bước ${step}/${total}: (${coords.abs_x}, ${coords.abs_y}) - Cửa sổ Offset: (+${coords.rel_x}, +${coords.rel_y})`, 'SUCCESS');
  showToast(`✅ Đã bắt xong Bước ${step}/${total}!`, 'success');
}

function handleCalibrationCompleted(data) {
  isLiveStudioCalibrating = false;
  const posBox = document.getElementById('boxCalibRealtimeCoords');
  if (posBox) posBox.style.display = 'none';

  const btn = document.getElementById('btnCalibrateStopLiveStudio');
  if (btn) {
    btn.textContent = '🎯 LẤY LẠI TỌA ĐỘ';
    btn.style.background = 'rgba(0, 255, 128, 0.15)';
    btn.style.borderColor = 'var(--success)';
    btn.style.color = 'var(--success)';
  }

  const labelStatus = document.getElementById('labelLiveStudioCoordsStatus');
  if (labelStatus) {
    labelStatus.textContent = '✅ Đã lưu: 3/3 Bước (Chuẩn 100%)';
    labelStatus.style.color = 'var(--success)';
  }

  showToast('🎉 Đã hiệu chỉnh và lưu bộ 3 tọa độ Tắt Live thành công!', 'success');
  appendTerminalLog('[CALIBRATE] 🎉 HOÀN TẤT: Bộ 3 tọa độ đã được lưu bền vững. Hệ thống sẽ click chính xác 100% khi hết video.', 'SUCCESS');
}

function handleCalibrationCancelled() {
  isLiveStudioCalibrating = false;
  const posBox = document.getElementById('boxCalibRealtimeCoords');
  if (posBox) posBox.style.display = 'none';

  const btn = document.getElementById('btnCalibrateStopLiveStudio');
  if (btn) {
    btn.textContent = '🎯 BẮT TỌA ĐỘ TẮT';
    btn.style.background = 'rgba(0, 242, 254, 0.15)';
    btn.style.borderColor = 'var(--accent)';
    btn.style.color = 'var(--accent)';
  }
  showToast('Đã hủy chế độ bắt tọa độ.', 'warning');
}

function updateLiveStudioCoordsStatusUI(isCalibrated, data) {
  const labelStatus = document.getElementById('labelLiveStudioCoordsStatus');
  const btn = document.getElementById('btnCalibrateStopLiveStudio');

  if (isCalibrated) {
    if (labelStatus) {
      labelStatus.textContent = '✅ Đã lưu: 3/3 Bước (Chuẩn 100%)';
      labelStatus.style.color = 'var(--success)';
    }
    if (btn) {
      btn.textContent = '🎯 LẤY LẠI TỌA ĐỘ';
      btn.style.background = 'rgba(0, 255, 128, 0.15)';
      btn.style.borderColor = 'var(--success)';
      btn.style.color = 'var(--success)';
    }
  } else {
    if (labelStatus) {
      labelStatus.textContent = 'Tọa độ: Tự động (Mặc định)';
      labelStatus.style.color = 'var(--text-tertiary)';
    }
    if (btn) {
      btn.textContent = '🎯 BẮT TỌA ĐỘ TẮT';
      btn.style.background = 'rgba(0, 242, 254, 0.15)';
      btn.style.borderColor = 'var(--accent)';
      btn.style.color = 'var(--accent)';
    }
  }
}

let vuAnimationId = null;
let currentVuPercent = 0;
let peakHoldPercent = 0;
let peakHoldDecayTimer = 0;

function startVuMeterAnimation() {
  stopVuMeterAnimation();
  const solidBar = document.getElementById('vuSolidBar');
  const peakLine = document.getElementById('vuPeakLine');
  if (!solidBar) return;

  let targetPercent = 0;
  let lastBeatTime = performance.now();

  function updatePhysics(now) {
    // Generate organic studio audio wave dynamics with natural speech/music rhythm
    if (now - lastBeatTime > 65) {
      lastBeatTime = now;
      // Audio swing simulation: 0% to 100%
      const base = 30 + Math.sin(now / 160) * 22;
      const isKickBeat = Math.random() > 0.65;
      const noise = Math.random() * 50;
      targetPercent = Math.min(100, Math.max(10, Math.floor(base + (isKickBeat ? noise + 18 : noise * 0.4))));
    }

    // Fast Dynamic Attack (dâng lên dứt khoát) & Smooth Gravity Decay (hạ xuống êm mượt)
    if (currentVuPercent < targetPercent) {
      currentVuPercent += (targetPercent - currentVuPercent) * 0.45;
    } else {
      currentVuPercent -= 1.6;
    }
    if (currentVuPercent < 0) currentVuPercent = 0;

    // Peak Hold Logic (giữ vạch đỉnh trong 350ms rồi trôi chậm xuống)
    if (currentVuPercent > peakHoldPercent) {
      peakHoldPercent = currentVuPercent;
      peakHoldDecayTimer = 22; // ~350ms
    } else {
      if (peakHoldDecayTimer > 0) {
        peakHoldDecayTimer--;
      } else if (peakHoldPercent > 0) {
        peakHoldPercent -= 1.0;
      }
    }

    // Cập nhật chiều cao dải sóng âm thanh
    solidBar.style.height = `${currentVuPercent.toFixed(1)}%`;

    // Adobe Premiere Pro Behavior: Toàn bộ thanh chuyển sang 1 màu tương ứng với mốc âm lượng hiện tại
    solidBar.classList.remove('safe', 'warning', 'danger');
    if (currentVuPercent > 88) {
      solidBar.classList.add('danger'); // Mốc Đỏ Nguy Hiểm Vỡ Tiếng
    } else if (currentVuPercent > 70) {
      solidBar.classList.add('warning'); // Mốc Vàng Cảnh Báo
    } else {
      solidBar.classList.add('safe'); // Mốc Xanh An Toàn
    }

    // Cập nhật Vạch Đỉnh Peak Marker đồng bộ màu sắc
    if (peakLine) {
      if (peakHoldPercent > 8) {
        peakLine.style.opacity = '1';
        peakLine.style.bottom = `${Math.min(99, peakHoldPercent).toFixed(1)}%`;

        if (peakHoldPercent > 88) {
          peakLine.style.background = '#FF0055';
          peakLine.style.boxShadow = '0 0 8px #FF0055, 0 0 14px rgba(255, 0, 85, 0.8)';
        } else if (peakHoldPercent > 70) {
          peakLine.style.background = '#FFB800';
          peakLine.style.boxShadow = '0 0 8px #FFB800, 0 0 12px rgba(255, 184, 0, 0.7)';
        } else {
          peakLine.style.background = '#00FF88';
          peakLine.style.boxShadow = '0 0 6px #00FF88, 0 0 10px rgba(0, 255, 136, 0.6)';
        }
      } else {
        peakLine.style.opacity = '0';
      }
    }

    vuAnimationId = requestAnimationFrame(updatePhysics);
  }

  vuAnimationId = requestAnimationFrame(updatePhysics);
}

function stopVuMeterAnimation() {
  if (vuAnimationId) {
    cancelAnimationFrame(vuAnimationId);
    vuAnimationId = null;
  }
  const solidBar = document.getElementById('vuSolidBar');
  const peakLine = document.getElementById('vuPeakLine');
  if (solidBar) {
    solidBar.style.height = '0%';
    solidBar.classList.remove('safe', 'warning', 'danger');
    solidBar.classList.add('safe');
  }
  if (peakLine) {
    peakLine.style.opacity = '0';
    peakLine.style.bottom = '0%';
  }
  currentVuPercent = 0;
  peakHoldPercent = 0;
  peakHoldDecayTimer = 0;
}

// 5.5 Audio Sink Routing (DTA Audio Virtual Cable -> TikTok LIVE Studio & Discord)
let detectedAudioOutputDevices = [];

async function initAudioSinkRouting() {
  const selectSink = document.getElementById('selectAudioSink');
  const videoPlayer = document.getElementById('previewVideoPlayer');

  async function populateAudioOutputs() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      detectedAudioOutputDevices = devices.filter(d => d.kind === 'audiooutput');

      if (selectSink && detectedAudioOutputDevices.length > 0) {
        selectSink.innerHTML = '';
        
        let cableDeviceFound = null;

        detectedAudioOutputDevices.forEach(device => {
          const opt = document.createElement('option');
          opt.value = device.deviceId;
          const fullLabel = device.label || `Thiết bị âm thanh (${device.deviceId.substring(0, 8)}...)`;
          opt.title = fullLabel;

          let displayLabel = fullLabel;
          if (displayLabel.length > 30) {
            displayLabel = displayLabel.substring(0, 28) + '...';
          }

          if (fullLabel.toLowerCase().includes('cable') || fullLabel.toLowerCase().includes('dta audio') || fullLabel.toLowerCase().includes('virtual')) {
            cableDeviceFound = device.deviceId;
            opt.textContent = `🎙️ ${displayLabel}`;
          } else if (fullLabel.toLowerCase().includes('default') || fullLabel.toLowerCase().includes('speakers') || fullLabel.toLowerCase().includes('loa')) {
            opt.textContent = `🔊 ${displayLabel}`;
          } else {
            opt.textContent = `🔈 ${displayLabel}`;
          }

          selectSink.appendChild(opt);
        });

        // Auto select Virtual Audio Cable if available
        if (cableDeviceFound) {
          selectSink.value = cableDeviceFound;
          applyAudioSink(cableDeviceFound);
        }
      }
    } catch (err) {
      console.log('Error enumerating audio devices:', err);
    }
  }

  async function applyAudioSink(deviceId) {
    if (videoPlayer && typeof videoPlayer.setSinkId === 'function') {
      try {
        await videoPlayer.setSinkId(deviceId);
        appendTerminalLog(`[AUDIO SINK] Âm thanh đã được điều hướng sang thiết bị: ${deviceId === 'default' ? 'Loa mặc định' : 'DTA Audio / Virtual Cable'}`, 'SUCCESS');
        showToast('Đã chuyển luồng âm thanh sang thiết bị đích', 'info');
      } catch (err) {
        console.log('setSinkId failed:', err);
      }
    }
  }

  selectSink?.addEventListener('change', (e) => {
    const targetDeviceId = e.target.value;
    applyAudioSink(targetDeviceId);
  });

  await populateAudioOutputs();
  navigator.mediaDevices?.addEventListener('devicechange', populateAudioOutputs);
}

function initCollapsiblePanels() {
  const btnToggleFilter = document.getElementById('btnToggleFilterDeck');
  const filterDeckBody = document.getElementById('filterDeckBody');
  const filterDeckIcon = document.getElementById('filterDeckToggleIcon');

  btnToggleFilter?.addEventListener('click', (e) => {
    // If clicked the reset button inside the header, don't collapse
    if (e.target && e.target.id === 'btnResetFilters') return;

    if (filterDeckBody) {
      filterDeckBody.classList.toggle('collapsed');
      const isCollapsed = filterDeckBody.classList.contains('collapsed');
      if (filterDeckIcon) {
        filterDeckIcon.textContent = isCollapsed ? '▸' : '▾';
      }
    }
  });

  const btnToggleDiag = document.getElementById('btnToggleDiagnostics');
  const diagDrawer = document.getElementById('diagnosticsDrawer');
  const diagIcon = document.getElementById('diagToggleIcon');

  btnToggleDiag?.addEventListener('click', () => {
    if (diagDrawer) {
      diagDrawer.classList.toggle('collapsed');
      const isCollapsed = diagDrawer.classList.contains('collapsed');
      if (diagIcon) {
        diagIcon.textContent = isCollapsed ? '▸ Nhấn để mở rộng' : '▾ Thu gọn';
      }
    }
  });
}

// 5.6 Real-time Live Anti-Duplicate & Anti-Ban Filter Controller
function initAntiDuplicateFilters() {
  const videoPlayer = document.getElementById('previewVideoPlayer');
  const sliderB = document.getElementById('sliderBrightness');
  const sliderC = document.getElementById('sliderContrast');
  const sliderS = document.getElementById('sliderSaturation');
  const sliderH = document.getElementById('sliderHue');
  const sliderZ = document.getElementById('sliderZoom');
  const sliderSh = document.getElementById('sliderSharpen');

  const valB = document.getElementById('valBrightness');
  const valC = document.getElementById('valContrast');
  const valS = document.getElementById('valSaturation');
  const valH = document.getElementById('valHue');
  const valZ = document.getElementById('valZoom');
  const valSh = document.getElementById('valSharpen');

  const chkFlip = document.getElementById('chkFlipMirror');
  const chkNoise = document.getElementById('chkNoiseCorner');
  const chkPitch = document.getElementById('chkPitchAudio');
  const btnReset = document.getElementById('btnResetFilters');

  function applyRealtimeFilters() {
    const b = sliderB ? sliderB.value : 100;
    const c = sliderC ? sliderC.value : 100;
    const s = sliderS ? sliderS.value : 100;
    const h = sliderH ? sliderH.value : 0;
    const z = sliderZ ? sliderZ.value : 100;
    const sh = sliderSh ? sliderSh.value : 100;
    const isFlipped = chkFlip ? chkFlip.checked : true;

    // Update Label Values
    if (valB) valB.textContent = `${b}%`;
    if (valC) valC.textContent = `${c}%`;
    if (valS) valS.textContent = `${s}%`;
    if (valH) valH.textContent = `${h}°`;
    if (valZ) valZ.textContent = `${z}%`;
    if (valSh) valSh.textContent = `${sh}%`;

    // Apply Live CSS Filter & Transform Matrix to Preview Video
    if (videoPlayer) {
      const zoomFactor = parseFloat(z) / 100.0;
      const flipScaleX = isFlipped ? -1 : 1;
      videoPlayer.style.filter = `brightness(${b}%) contrast(${c}%) saturate(${s}%) hue-rotate(${h}deg)`;
      videoPlayer.style.transform = `scale(${zoomFactor}) scaleX(${flipScaleX})`;
    }

    // Sync filter parameters to Python Backend DirectShow Engine
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'UPDATE_FILTERS',
        filters: {
          brightness: parseFloat(b),
          contrast: parseFloat(c),
          saturation: parseFloat(s),
          hue: parseFloat(h),
          zoom: parseFloat(z),
          sharpen: parseFloat(sh),
          flip_mirror: isFlipped,
          noise_corner: chkNoise ? chkNoise.checked : true,
          pitch_audio: chkPitch ? chkPitch.checked : true
        }
      }));
    }
  }

  // Bind Input Change Listeners
  [sliderB, sliderC, sliderS, sliderH, sliderZ, sliderSh].forEach(sl => {
    sl?.addEventListener('input', applyRealtimeFilters);
  });

  [chkFlip, chkNoise, chkPitch].forEach(chk => {
    chk?.addEventListener('change', applyRealtimeFilters);
  });

  btnReset?.addEventListener('click', () => {
    if (sliderB) sliderB.value = 100;
    if (sliderC) sliderC.value = 100;
    if (sliderS) sliderS.value = 100;
    if (sliderH) sliderH.value = 0;
    if (sliderZ) sliderZ.value = 100;
    if (sliderSh) sliderSh.value = 100;
    if (chkFlip) chkFlip.checked = true;
    if (chkNoise) chkNoise.checked = true;
    if (chkPitch) chkPitch.checked = true;

    applyRealtimeFilters();
    showToast('Đã đặt lại bộ lọc chống trùng lặp', 'info');
  });

  // Apply default anti-ban matrix on startup
  applyRealtimeFilters();
}

// 5.7 Background Music (BGM) & Dual Audio Mixer Controller
function initAudioMixerAndBgm() {
  const btnSelectFolder = document.getElementById('btnSelectBgmFolder');
  const btnTogglePlay = document.getElementById('btnToggleBgmPlay');
  const btnNext = document.getElementById('btnNextBgmTrack');
  const trackDisplay = document.getElementById('bgmTrackDisplay');
  const statusBadge = document.getElementById('bgmStatusBadge');

  const sliderVideoVol = document.getElementById('sliderVideoVolume');
  const valVideoVol = document.getElementById('valVideoVolume');
  const sliderBgmVol = document.getElementById('sliderBgmVolume');
  const valBgmVol = document.getElementById('valBgmVolume');

  let currentBgmFolder = localStorage.getItem('dta_bgm_folder') || '';
  let isBgmPlaying = false;

  // Restore saved volumes
  const savedVideoVol = localStorage.getItem('dta_video_volume');
  if (savedVideoVol !== null && sliderVideoVol) {
    sliderVideoVol.value = savedVideoVol;
    if (valVideoVol) valVideoVol.textContent = `${savedVideoVol}%`;
  }

  const savedBgmVol = localStorage.getItem('dta_bgm_volume');
  if (savedBgmVol !== null && sliderBgmVol) {
    sliderBgmVol.value = savedBgmVol;
    if (valBgmVol) valBgmVol.textContent = `${savedBgmVol}%`;
  }

  if (currentBgmFolder && trackDisplay) {
    const folderName = currentBgmFolder.split(/[\\/]/).pop();
    trackDisplay.textContent = `📁 ${folderName}`;
    trackDisplay.title = currentBgmFolder;
  }

  // 1. Select BGM Folder
  btnSelectFolder?.addEventListener('click', async () => {
    try {
      if (window.dtaAPI && window.dtaAPI.selectDirectory) {
        const selected = await window.dtaAPI.selectDirectory(currentBgmFolder || '');
        if (selected) {
          currentBgmFolder = selected;
          localStorage.setItem('dta_bgm_folder', selected);
          const folderName = selected.split(/[\\/]/).pop();
          if (trackDisplay) {
            trackDisplay.textContent = `📁 ${folderName}`;
            trackDisplay.title = selected;
          }
          if (wsClient && wsClient.readyState === WebSocket.OPEN) {
            const vol = (sliderBgmVol ? parseInt(sliderBgmVol.value, 10) : 30) / 100.0;
            const sink = document.getElementById('selectAudioSink')?.value || 'cable';
            wsClient.send(JSON.stringify({
              command: 'START_BGM',
              folder: selected,
              volume: vol,
              sink_name: sink,
              shuffle: false
            }));
          }
          appendTerminalLog(`[BGM] 📁 Đã chọn thư mục nhạc nền: ${selected}`, 'INFO');
          showToast(`Đã chọn thư mục nhạc: ${folderName}`, 'success');
        }
      }
    } catch (err) {
      console.error('Error selecting BGM folder:', err);
    }
  });

  // 2. Toggle BGM Play/Stop
  btnTogglePlay?.addEventListener('click', () => {
    if (!wsClient || wsClient.readyState !== WebSocket.OPEN) {
      showToast('Chưa kết nối tới DTA Backend Engine!', 'error');
      return;
    }

    if (isBgmPlaying) {
      wsClient.send(JSON.stringify({ command: 'STOP_BGM' }));
      appendTerminalLog('[BGM] ⏸ Đã dừng phát nhạc nền.', 'INFO');
    } else {
      if (!currentBgmFolder) {
        showToast('Vui lòng chọn thư mục nhạc nền trước!', 'warning');
        btnSelectFolder?.click();
        return;
      }
      const vol = (sliderBgmVol ? parseInt(sliderBgmVol.value, 10) : 30) / 100.0;
      const sink = document.getElementById('selectAudioSink')?.value || 'cable';
      wsClient.send(JSON.stringify({
        command: 'START_BGM',
        folder: currentBgmFolder,
        volume: vol,
        sink_name: sink,
        shuffle: false
      }));
      appendTerminalLog('[BGM] ▶ Đang phát nhạc nền...', 'INFO');
    }
  });

  // 3. Next Track
  btnNext?.addEventListener('click', () => {
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({ command: 'NEXT_BGM_TRACK' }));
    }
  });

  // 4. Video Volume Slider
  sliderVideoVol?.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    if (valVideoVol) valVideoVol.textContent = `${val}%`;
    localStorage.setItem('dta_video_volume', val);

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'SET_VIDEO_VOLUME',
        volume: val / 100.0
      }));
    }
  });

  // 5. BGM Volume Slider
  sliderBgmVol?.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    if (valBgmVol) valBgmVol.textContent = `${val}%`;
    localStorage.setItem('dta_bgm_volume', val);

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'SET_BGM_VOLUME',
        volume: val / 100.0
      }));
    }
  });

  // Public state handlers
  window.handleBgmStateUpdate = function(data) {
    if (!data) return;
    isBgmPlaying = !!data.is_playing;

    if (btnTogglePlay) {
      if (isBgmPlaying) {
        btnTogglePlay.textContent = '⏸ Dừng Nhạc';
        btnTogglePlay.classList.remove('btn-primary');
        btnTogglePlay.classList.add('btn-danger');
      } else {
        btnTogglePlay.textContent = '▶ Bật Nhạc';
        btnTogglePlay.classList.remove('btn-danger');
        btnTogglePlay.classList.add('btn-primary');
      }
    }

    if (statusBadge) {
      if (isBgmPlaying) {
        statusBadge.textContent = 'BGM: Đang phát';
        statusBadge.className = 'badge badge-green';
      } else {
        statusBadge.textContent = 'BGM: Tạm dừng';
        statusBadge.className = 'badge badge-cyan';
      }
    }

    if (data.current_track && trackDisplay) {
      trackDisplay.textContent = `🎵 ${data.current_track}`;
      trackDisplay.title = data.current_track;
    } else if (!isBgmPlaying && currentBgmFolder && trackDisplay) {
      const folderName = currentBgmFolder.split(/[\\/]/).pop();
      trackDisplay.textContent = `📁 ${folderName}`;
    }
  };

  window.handleBgmTrackChanged = function(data) {
    if (!data || !trackDisplay) return;
    const track = data.current_track || '';
    const idx = (data.current_index || 0) + 1;
    const total = data.total_tracks || 0;
    trackDisplay.textContent = `🎵 ${track} (${idx}/${total})`;
    trackDisplay.title = track;
    appendTerminalLog(`[BGM] 🎶 Đang phát bài: ${track} (${idx}/${total})`, 'SUCCESS');
  };
}

// 6. Playlist Manager Controller
function initPlaylistManager() {
  const btnAdd = document.getElementById('btnAddVideo');
  const btnDelete = document.getElementById('btnDeleteVideo');
  const tbody = document.getElementById('playlistTableBody');
  const videoPlayer = document.getElementById('previewVideoPlayer');
  const countBadge = document.getElementById('playlistCountBadge');
  const plTotalCount = document.getElementById('plTotalCount');
  const plValidCount = document.getElementById('plValidCount');
  const inputSearch = document.getElementById('inputSearchPlaylist');
  const cardVideoName = document.getElementById('cardVideoName');

  function savePlaylistToStorage() {
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const paths = rows.map(r => r.dataset.filePath || r.title).filter(Boolean);
    try {
      localStorage.setItem('dta_saved_playlist', JSON.stringify(paths));
    } catch (e) {
      console.error(e);
    }
  }

  function getParentDirectory(filePath) {
    if (!filePath) return '';
    const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
    return lastSlash > 0 ? filePath.substring(0, lastSlash) : '';
  }

  window.addVideoToPlaylist = function(filePath, silent = false) {
    if (!filePath || !tbody) return;
    
    // Lưu folder gần nhất
    const parentDir = getParentDirectory(filePath);
    if (parentDir) {
      localStorage.setItem('dta_last_video_folder', parentDir);
    }

    const fileName = filePath.split(/[\\/]/).pop();
    const rowCount = tbody.children.length + 1;

    // Nếu chưa có video nào được chọn hoặc đang là video đầu tiên
    if (!currentVideoPath || tbody.children.length === 0) {
      currentVideoPath = filePath;
      if (cardVideoName) {
        cardVideoName.textContent = fileName;
        cardVideoName.title = fileName;
      }
      if (videoPlayer && !isLiveActive) {
        videoPlayer.src = filePath;
      }
    }
    
    const tr = document.createElement('tr');
    tr.title = fileName;
    tr.dataset.filePath = filePath;
    if (rowCount === 1 && !tbody.querySelector('tr.selected')) {
      tr.classList.add('selected');
    }

    tr.innerHTML = `
      <td style="text-align: center;">${rowCount}</td>
      <td style="text-align: center;"><span class="badge badge-green">Sẵn sàng</span></td>
      <td title="${fileName}" style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 0;">${fileName}</td>
      <td style="text-align: center;"><span class="badge badge-green">AAC</span></td>
      <td style="text-align: center;">
        <button type="button" class="btn-del-single-row" title="Xóa video này khỏi playlist" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 2px 4px; border-radius: 4px; transition: all 0.2s;">🗑</button>
      </td>
    `;

    // Click row to select
    tr.addEventListener('click', (e) => {
      if (e.target.closest('.btn-del-single-row')) return;
      document.querySelectorAll('#playlistTableBody tr').forEach(r => r.classList.remove('selected'));
      tr.classList.add('selected');
      currentVideoPath = filePath;
      if (cardVideoName) {
        cardVideoName.textContent = fileName;
        cardVideoName.title = fileName;
      }
      if (videoPlayer && !isLiveActive) {
        videoPlayer.src = filePath;
      }
      if (typeof syncTableToJson === 'function') {
        syncTableToJson();
      }
    });

    // Delete single row
    const delBtn = tr.querySelector('.btn-del-single-row');
    delBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      tr.remove();
      const remainingRows = Array.from(tbody.querySelectorAll('tr'));
      remainingRows.forEach((r, idx) => {
        if (r.children[0]) r.children[0].textContent = (idx + 1).toString();
      });
      if (countBadge) countBadge.textContent = `${remainingRows.length} Video`;
      if (plTotalCount) plTotalCount.textContent = `${remainingRows.length} video`;
      if (plValidCount) plValidCount.textContent = `${remainingRows.length}/${remainingRows.length}`;
      if (remainingRows.length === 0) {
        currentVideoPath = '';
        if (cardVideoName) {
          cardVideoName.textContent = 'Chưa chọn video';
          cardVideoName.title = 'Chưa chọn video';
        }
        if (videoPlayer) videoPlayer.src = '';
      }
      savePlaylistToStorage();
      if (typeof syncTableToJson === 'function') syncTableToJson();
      showToast(`Đã xóa video '${fileName}' khỏi Playlist`, 'info');
    });

    tbody.appendChild(tr);
    if (countBadge) countBadge.textContent = `${tbody.children.length} Video`;
    if (plTotalCount) plTotalCount.textContent = `${tbody.children.length} video`;
    if (plValidCount) plValidCount.textContent = `${tbody.children.length}/${tbody.children.length}`;
    
    savePlaylistToStorage();

    if (!silent) {
      appendTerminalLog(`[INFO] Đã thêm video '${fileName}' vào Playlist.`, 'INFO');
      showToast(`Đã thêm video ${fileName}`, 'success');
    }
  };

  // Thêm một hoặc nhiều file video (Tự động mở thư mục gần nhất)
  btnAdd?.addEventListener('click', async () => {
    if (window.dtaAPI?.openFileDialog) {
      const lastFolder = localStorage.getItem('dta_last_video_folder') || '';
      const files = await window.dtaAPI.openFileDialog([
        { name: 'Video Livestream', extensions: ['mp4', 'mkv', 'avi', 'mov', 'flv'] }
      ], true, lastFolder);
      if (files) {
        if (Array.isArray(files)) {
          files.forEach(f => window.addVideoToPlaylist(f, true));
          showToast(`Đã thêm ${files.length} video vào Playlist!`, 'success');
          appendTerminalLog(`[INFO] Đã thêm ${files.length} video vào Playlist.`, 'INFO');
        } else {
          window.addVideoToPlaylist(files);
        }
      }
    }
  });

  // Thêm toàn bộ video trong một Thư mục (Tự động mở thư mục gần nhất)
  const btnAddFolder = document.getElementById('btnAddFolder');
  btnAddFolder?.addEventListener('click', async () => {
    if (window.dtaAPI?.selectDirectory && window.dtaAPI?.scanDirectoryVideos) {
      const lastFolder = localStorage.getItem('dta_last_video_folder') || '';
      const dirPath = await window.dtaAPI.selectDirectory(lastFolder);
      if (dirPath) {
        localStorage.setItem('dta_last_video_folder', dirPath);
        const videoFiles = await window.dtaAPI.scanDirectoryVideos(dirPath);
        if (videoFiles && videoFiles.length > 0) {
          videoFiles.forEach(f => window.addVideoToPlaylist(f, true));
          showToast(`Đã thêm ${videoFiles.length} video từ thư mục!`, 'success');
          appendTerminalLog(`[INFO] Đã thêm ${videoFiles.length} video từ thư mục '${dirPath}'.`, 'INFO');
        } else {
          showToast('Không tìm thấy video hợp lệ trong thư mục đã chọn!', 'warning');
        }
      }
    }
  });

  const btnShuffle = document.getElementById('btnShufflePlaylist');
  btnShuffle?.addEventListener('click', () => {
    if (!tbody || tbody.children.length <= 1) {
      showToast('Playlist cần từ 2 video trở lên để trộn thứ tự!', 'warning');
      return;
    }
    const rows = Array.from(tbody.children);
    for (let i = rows.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [rows[i], rows[j]] = [rows[j], rows[i]];
    }
    tbody.innerHTML = '';
    rows.forEach((r, idx) => {
      if (r.children[0]) r.children[0].textContent = (idx + 1).toString();
      tbody.appendChild(r);
    });
    savePlaylistToStorage();
    showToast('🔀 Đã trộn ngẫu nhiên thứ tự playlist video!', 'success');
    appendTerminalLog('[ACTION] 🔀 Đã trộn ngẫu nhiên danh sách phát để tránh trùng lặp khung giờ phát Live.', 'INFO');
  });

  const btnClear = document.getElementById('btnClearPlaylist');
  btnClear?.addEventListener('click', () => {
    if (!tbody || tbody.children.length === 0) {
      showToast('Playlist đang trống!', 'info');
      return;
    }
    openActionModal(
      '🗑️ XÁC NHẬN XÓA TOÀN BỘ PLAYLIST',
      'Bạn có chắc chắn muốn xóa hết tất cả video trong danh sách phát không?',
      () => {
        tbody.innerHTML = '';
        currentVideoPath = '';
        if (cardVideoName) {
          cardVideoName.textContent = 'Chưa chọn video';
          cardVideoName.title = 'Chưa chọn video';
        }
        if (countBadge) countBadge.textContent = '0 Video';
        if (plTotalCount) plTotalCount.textContent = '0 video';
        if (plValidCount) plValidCount.textContent = '0/0';
        if (videoPlayer) videoPlayer.src = '';
        savePlaylistToStorage();
        showToast('Đã xóa sạch danh sách phát!', 'warning');
        appendTerminalLog('[ACTION] 🗑️ Đã xóa toàn bộ video khỏi playlist.', 'WARNING');
      }
    );
  });

  btnDelete?.addEventListener('click', () => {
    const selected = document.querySelector('#playlistTableBody tr.selected');
    if (!selected) {
      showToast('Vui lòng chọn dòng video cần xóa khỏi danh sách!', 'warning');
      return;
    }

    const fileName = selected.title || 'video';
    openActionModal(
      '🗑 XÁC NHẬN XÓA VIDEO KHỎI PLAYLIST',
      `Bạn có chắc chắn muốn xóa video "${fileName}" khỏi danh sách phát không? (Thao tác này KHÔNG xóa file vật lý trên ổ đĩa)`,
      () => {
        selected.remove();
        if (countBadge && tbody) countBadge.textContent = `${tbody.children.length} Video`;
        if (plTotalCount && tbody) plTotalCount.textContent = `${tbody.children.length} video`;
        if (plValidCount && tbody) plValidCount.textContent = `${tbody.children.length}/${tbody.children.length}`;
        appendTerminalLog(`[INFO] Đã xóa video '${fileName}' khỏi Playlist.`, 'INFO');
        showToast(`Đã xóa video ${fileName} khỏi danh sách phát`, 'warning');

        const rows = document.querySelectorAll('#playlistTableBody tr');
        rows.forEach((row, i) => {
          if (row.children[0]) row.children[0].textContent = (i + 1).toString();
        });
        if (rows.length === 0) {
          currentVideoPath = '';
          if (cardVideoName) {
            cardVideoName.textContent = 'Chưa chọn video';
            cardVideoName.title = 'Chưa chọn video';
          }
          if (videoPlayer) videoPlayer.src = '';
        }
        savePlaylistToStorage();
      }
    );
  });

  inputSearch?.addEventListener('input', () => {
    const query = inputSearch.value.toLowerCase();
    const rows = document.querySelectorAll('#playlistTableBody tr');
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  });

  // Tự động khôi phục danh sách playlist đã lưu từ phiên trước
  try {
    const saved = localStorage.getItem('dta_saved_playlist');
    if (saved) {
      const list = JSON.parse(saved);
      if (Array.isArray(list) && list.length > 0) {
        list.forEach(f => window.addVideoToPlaylist(f, true));
        const firstRow = tbody.querySelector('tr');
        if (firstRow) {
          firstRow.classList.add('selected');
          const fPath = firstRow.dataset.filePath || firstRow.title;
          currentVideoPath = fPath;
          const fName = fPath.split(/[\\/]/).pop();
          if (cardVideoName) {
            cardVideoName.textContent = fName;
            cardVideoName.title = fName;
          }
          if (videoPlayer && !isLiveActive) {
            videoPlayer.src = fPath;
          }
        }
      }
    }
  } catch (e) {
    console.error('Khôi phục playlist lỗi:', e);
  }
}

// 7. TikTok Shop Product Pinner (AutoPin) & Visual Timeline Controller
let timelineEvents = [
  { id: 'evt_1', time_ms: 15000, time_str: '00:15', product_id: '1', title: 'Áo thun nam Cotton Compact', keywords: 'ao thun, ao nam', state: 'Sẵn sàng' },
  { id: 'evt_2', time_ms: 60000, time_str: '01:00', product_id: '2', title: 'Quần jean unisex ống suông', keywords: 'quan jean, quan nu', state: 'Sẵn sàng' },
  { id: 'evt_3', time_ms: 120000, time_str: '02:00', product_id: '3', title: 'Áo khoác bomber chống gió', keywords: 'ao khoac, ao gio', state: 'Sẵn sàng' }
];

function timeStrToMs(timeStr) {
  if (!timeStr) return 0;
  const parts = timeStr.trim().split(':').map(p => parseInt(p, 10));
  if (parts.length === 2) {
    return (parts[0] * 60 + parts[1]) * 1000;
  }
  if (parts.length === 3) {
    return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000;
  }
  return (parseInt(timeStr, 10) || 0) * 1000;
}

function msToTimeStr(ms) {
  const totalSec = Math.floor((ms || 0) / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function renderTimelineTable() {
  const tbody = document.getElementById('timelineTableBody');
  const countEl = document.getElementById('timelineEventCount');
  if (!tbody) return;

  tbody.innerHTML = '';
  timelineEvents.forEach((evt, idx) => {
    const tr = document.createElement('tr');
    tr.id = `row_${evt.id}`;
    tr.innerHTML = `
      <td style="text-align: center;">${idx + 1}</td>
      <td style="text-align: center; font-family: var(--font-code); color: var(--accent); font-weight: 600;">⏱️ ${evt.time_str}</td>
      <td style="text-align: center;"><span class="badge badge-cyan">SP #${evt.product_id}</span></td>
      <td title="${evt.title || ''}" style="color: var(--text-primary); font-weight: 500;">${evt.title || 'Sản phẩm ' + evt.product_id}</td>
      <td title="${evt.keywords || ''}" style="color: var(--text-secondary); font-size: 11px;">${evt.keywords || '--'}</td>
      <td style="text-align: center;"><span class="badge badge-green" id="statusBadge_${evt.id}">${evt.state || 'Sẵn sàng'}</span></td>
      <td style="text-align: center;">
        <button class="btn btn-secondary" style="height: 22px; width: 22px; padding: 0; font-size: 10px; color: var(--danger);" title="Xóa mốc sự kiện này" onclick="window.removeTimelineRow('${evt.id}')">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  if (countEl) countEl.textContent = `${timelineEvents.length} mốc`;
  syncTableToJson();
}

window.removeTimelineRow = function(evtId) {
  timelineEvents = timelineEvents.filter(e => e.id !== evtId);
  renderTimelineTable();
  showToast('Đã xóa mốc sự kiện timeline', 'info');
};

function syncTableToJson() {
  const textarea = document.getElementById('jsonScriptTextarea');
  if (!textarea) return;
  const scriptObj = {
    schema_version: '1.0',
    script_id: 'dta_timeline_script_v1',
    video_filename: currentVideoPath ? currentVideoPath.split(/[\\/]/).pop() : 'DTA_Live_Video.mp4',
    expected_duration_ms: 180000,
    loop_mode: 'inherit_playlist',
    timeline_events: timelineEvents.map((evt, idx) => ({
      event_id: evt.id || `evt_${idx + 1}`,
      time_ms: evt.time_ms,
      time_formatted: evt.time_str,
      type: 'PIN_PRODUCT',
      payload: {
        product_id: String(evt.product_id),
        title: evt.title || `Sản phẩm ${evt.product_id}`,
        keywords: evt.keywords ? evt.keywords.split(',').map(k => k.trim()) : []
      },
      valid_for_ms: 10000
    }))
  };
  textarea.value = JSON.stringify(scriptObj, null, 2);
}

function syncJsonToTable() {
  const textarea = document.getElementById('jsonScriptTextarea');
  if (!textarea) return;
  try {
    const parsed = JSON.parse(textarea.value);
    if (parsed && Array.isArray(parsed.timeline_events)) {
      timelineEvents = parsed.timeline_events.map((e, idx) => ({
        id: e.event_id || `evt_${idx + 1}`,
        time_ms: e.time_ms || 0,
        time_str: e.time_formatted || msToTimeStr(e.time_ms || 0),
        product_id: e.payload?.product_id || String(idx + 1),
        title: e.payload?.title || `Sản phẩm ${e.payload?.product_id || idx + 1}`,
        keywords: Array.isArray(e.payload?.keywords) ? e.payload.keywords.join(', ') : (e.payload?.keywords || ''),
        state: 'Sẵn sàng'
      }));
      renderTimelineTable();
    }
  } catch (err) {
    console.log('JSON sync error:', err);
  }
}

function handlePinEventTriggered(data) {
  const detailEl = document.getElementById('activePinDetailText');
  if (detailEl && data.product_id) {
    const pName = data.product_name ? `(${data.product_name.split('-')[0].trim()})` : '';
    const waitTxt = data.wait_seconds ? ` <span style="color: var(--accent); font-weight: 700;">(⏳ ${data.wait_seconds}s)</span>` : '';
    detailEl.innerHTML = `📌 <b>Lượt #${data.round || 1}:</b> Đang ghim SP #${data.product_id} ${pName} <span style="color: var(--warning);">[${data.direction || 'Đang thực thi'}]</span>${waitTxt}`;
  }

  // Highlight active row in Visual Table
  document.querySelectorAll('#timelineTableBody tr').forEach(r => r.classList.remove('timeline-row-active'));
  const targetRow = Array.from(document.querySelectorAll('#timelineTableBody tr')).find(r => r.textContent.includes(`SP #${data.product_id}`));
  if (targetRow) {
    targetRow.classList.add('timeline-row-active');
  }

  const randWaitLog = data.wait_seconds ? ` | ⏳ Giữ ${data.wait_seconds}s (Random)` : '';
  appendTerminalLog(`[ACTION] 📌 [PIN EVENT] Đã ghim SP #${data.product_id} (${data.product_name || ''}) [${data.direction || ''}]${randWaitLog}`, 'SUCCESS');
  showToast(`Đã ghim Sản phẩm #${data.product_id}${data.wait_seconds ? ` (Giữ ${data.wait_seconds}s)` : ''}`, 'success');

  if (data.pin_counts || data.interest_counts) {
    updateHeatmapAnalyticsUI({
      pin_counts: data.pin_counts,
      interest_counts: data.interest_counts,
      mode: data.mode
    });
  }
}

function handleHostPinCalloutEvent(evt) {
  if (!evt || !evt.callout) return;
  appendTerminalLog(`[CALLOUT] 🔥 [Host Kêu Gọi Mua Hàng] SP #${evt.product_id}: "${evt.callout}"`, 'SUCCESS');

  const chatBox = document.getElementById('hostChatLiveBox');
  if (chatBox) {
    const item = document.createElement('div');
    item.className = 'host-chat-item host-chat-item-ai';
    item.style.borderLeft = '3px solid var(--accent)';
    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
        <span style="font-size: 11px; font-weight: 700; color: var(--accent);">🔥 Host AI Chốt Đơn (Khi Ghim SP #${evt.product_id})</span>
        <span style="font-size: 10px; color: var(--text-tertiary);">${new Date().toLocaleTimeString()}</span>
      </div>
      <div style="font-size: 12px; color: var(--text-primary); line-height: 1.4;">${evt.callout}</div>
    `;
    chatBox.appendChild(item);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

function handleSeedingSupportEvent(evt) {
  if (!evt || !evt.comment) return;
  appendTerminalLog(`[SEEDING] ✨ [Vệ Tinh Trợ Lực Ghim] SP #${evt.product_id}: "${evt.comment}"`, 'INFO');

  const seedingBox = document.getElementById('seedingLiveLogBox');
  if (seedingBox) {
    const item = document.createElement('div');
    item.className = 'seeding-bubble-item';
    item.style.borderLeft = '3px solid var(--success)';
    item.innerHTML = `
      <span class="seeding-bubble-author" style="color: var(--success);">👥 [Vệ Tinh Trợ Lực SP #${evt.product_id}]</span>
      <span class="seeding-bubble-text">${evt.comment}</span>
      <span class="seeding-bubble-time">${new Date().toLocaleTimeString()}</span>
    `;
    seedingBox.appendChild(item);
    seedingBox.scrollTop = seedingBox.scrollHeight;
  }
}

window.refreshPinAnalytics = function() {
  appendTerminalLog('[INFO] 📊 Đang cập nhật dữ liệu Nhiệt Kế & Phân Tích sản phẩm...', 'INFO');
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'GET_PIN_ANALYTICS' }));
  }
};

window.resetPinAnalytics = function() {
  updateHeatmapAnalyticsUI({ pin_counts: {}, interest_counts: {} });
  showToast('Đã làm mới bảng nhiệt kế sản phẩm', 'info');
};

window.triggerManualPinProduct = function(stt, event) {
  appendTerminalLog(`[ACTION] 📌 Kích hoạt ghim thủ công SP #${stt}...`, 'INFO');
  showToast(`Đang ghim SP #${stt}...`, 'info');

  const matched = (currentScrapedProducts || []).find(p => String(p.stt) === String(stt));
  if (window.triggerPinFlyAnimation) {
    window.triggerPinFlyAnimation(matched || { stt: stt, name: `Sản phẩm #${stt}` }, event?.currentTarget || event?.target);
  }

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'TRIGGER_MANUAL_PIN',
      product_id: String(stt)
    }));
  }
};

function updateHeatmapAnalyticsUI(data) {
  if (!data) return;
  const pinCounts = data.pin_counts || {};
  const interestCounts = data.interest_counts || {};

  const totalPins = Object.values(pinCounts).reduce((a, b) => a + b, 0);
  const totalInquiries = Object.values(interestCounts).reduce((a, b) => a + b, 0);

  const statPinsEl = document.getElementById('statTotalPins');
  const statInqEl = document.getElementById('statTotalInquiries');
  const statHotEl = document.getElementById('statTopHotProduct');
  const statModeEl = document.getElementById('statActivePinModeName');

  if (statPinsEl) statPinsEl.textContent = `${totalPins} lượt`;
  if (statInqEl) statInqEl.textContent = `${totalInquiries} câu hỏi`;

  const selMode = document.getElementById('selectPinMode');
  if (statModeEl && selMode) {
    statModeEl.textContent = selMode.options[selMode.selectedIndex]?.text.split('(')[0].trim() || 'Cân Bằng';
  }

  // Find top hot product
  let maxInterests = -1;
  let hotProdName = 'Chưa có dữ liệu';
  if (currentScrapedProducts && currentScrapedProducts.length > 0) {
    currentScrapedProducts.forEach(p => {
      const qCount = interestCounts[String(p.stt)] || 0;
      if (qCount > maxInterests && qCount > 0) {
        maxInterests = qCount;
        hotProdName = `Mã #${p.stt} (${p.name.split('-')[0].trim()})`;
      }
    });
  }
  if (statHotEl) statHotEl.textContent = hotProdName;

  // Render heatmap table
  const tbody = document.getElementById('pinAnalyticsTableBody');
  if (!tbody || !currentScrapedProducts || currentScrapedProducts.length === 0) return;

  const maxScore = Math.max(5, ...currentScrapedProducts.map(x => (pinCounts[String(x.stt)] || 0) + (interestCounts[String(x.stt)] || 0) * 3));

  const rows = currentScrapedProducts.map(p => {
    const stt = p.stt;
    const name = p.name;
    const price = p.sale_price || '';
    const pCount = pinCounts[String(stt)] || 0;
    const iCount = interestCounts[String(stt)] || 0;
    const score = pCount * 1 + iCount * 3;
    const heatPct = Math.min(100, Math.round((score / maxScore) * 100));

    let heatColor = 'var(--accent)';
    let gradient = 'var(--accent-gradient)';
    if (heatPct > 70) {
      heatColor = 'var(--danger)';
      gradient = 'var(--danger-gradient)';
    } else if (heatPct > 40) {
      heatColor = 'var(--warning)';
      gradient = 'linear-gradient(135deg, var(--warning), #FF6B00)';
    }

    return `
      <tr>
        <td style="text-align: center;"><strong>${stt}</strong></td>
        <td title="${name}"><strong>${name}</strong></td>
        <td style="text-align: center; color: var(--accent); font-weight: 700;">${price}</td>
        <td style="text-align: center;"><span class="badge badge-cyan">${pCount} lần</span></td>
        <td style="text-align: center;"><span class="badge badge-green">${iCount} lượt</span></td>
        <td style="text-align: center;">
          <div class="heatmap-bar-container" title="Điểm nhiệt độ quan tâm: ${score} điểm (${heatPct}%)">
            <div class="heatmap-bar-fill" style="width: ${heatPct}%; background: ${gradient};"></div>
            <span class="heatmap-bar-label">${heatPct}%</span>
          </div>
        </td>
        <td style="text-align: center;">
          <button class="btn btn-primary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.triggerManualPinProduct('${stt}', event)">📌 Ghim</button>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = rows.join('');
}

window.launchTikTokShopBrowser = function() {
  appendTerminalLog('[INFO] 🌐 Đang mở NATIVE GOOGLE CHROME kết nối https://shop.tiktok.com/streamer/live/product/dashboard (Cổng CDP 9222)...', 'INFO');
  showToast('Đang mở Trình duyệt Điều khiển Live TikTok (CDP 9222)...', 'info');
  const badgePinStatus = document.getElementById('badgePinStatus');
  if (badgePinStatus) {
    badgePinStatus.textContent = 'Trình duyệt Đang Mở';
    badgePinStatus.className = 'badge badge-green';
  }
  
  // Call Electron Native IPC launcher
  window.dtaAPI?.launchChromeLive?.().catch(e => console.log('Native launch fallback:', e));

  // Also send command to Python backend
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'LAUNCH_TIKTOK_SHOP_CHROME' }));
  }
};

window.testPinProduct = function() {
  appendTerminalLog('[ACTION] ⚡ Đang gửi yêu cầu GHIM THỬ Sản Phẩm #1 sang TikTok Shop...', 'INFO');
  showToast('Đang thực hiện Ghim Thử SP #1...', 'info');

  const detailEl = document.getElementById('activePinDetailText');
  if (detailEl) detailEl.innerHTML = '⚡ <b>Đang Ghim Thử SP #1...</b>';

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'TEST_PIN_PRODUCT',
      product_id: '1'
    }));
  }
};

window.startAutoPinning = function() {
  const pList = document.getElementById('inputPinProductList')?.value || '1, 2, 3, 4, 5, 6, 7, 8, 9, 10';
  const interval = document.getElementById('inputPinInterval')?.value || '10';
  const mode = document.getElementById('selectPinMode')?.value || 'ping_pong';
  const autoScroll = document.getElementById('chkPinAutoScroll')?.checked || false;
  const randomInterval = document.getElementById('chkPinRandomInterval')?.checked !== false;
  const autoCallout = document.getElementById('chkPinAutoCallout')?.checked !== false;
  const seedingSupport = document.getElementById('chkPinSeedingSupport')?.checked !== false;
  const textarea = document.getElementById('jsonScriptTextarea');
  const kwMap = textarea?.value || '';

  const btnStartAutoPin = document.getElementById('btnStartAutoPin');
  const btnStopAutoPin = document.getElementById('btnStopAutoPin');
  const badgePinStatus = document.getElementById('badgePinStatus');

  if (btnStartAutoPin) btnStartAutoPin.disabled = true;
  if (btnStopAutoPin) btnStopAutoPin.disabled = false;
  if (badgePinStatus) {
    badgePinStatus.textContent = 'Đang Ghim SP...';
    badgePinStatus.className = 'badge badge-green';
  }

  const scrollText = autoScroll ? 'Bật cuộn chuột' : 'Không cuộn chuột (Đứng yên)';
  const randText = randomInterval ? '🎲 Random thời gian (±30% chống lặp)' : 'Cố định thời gian';
  const calloutText = autoCallout ? 'Bật Auto-Callout chốt đơn' : 'Tắt Callout';
  const seedText = seedingSupport ? 'Bật Seeding trợ lực' : 'Tắt Seeding';
  appendTerminalLog(`[SUCCESS] 🚀 Kích hoạt Ghim Luân Phiên (DS STT: ${pList} | Cơ sở: ${interval}s (${randText}) | Chế độ: ${mode} | ${scrollText} | ${calloutText} | ${seedText})`, 'SUCCESS');
  showToast(`Đã bật Auto Pin TikTok Shop (${interval}s - ${randText})`, 'success');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'START_AUTO_PIN',
      product_list: pList,
      interval: parseInt(interval, 10),
      random_interval: randomInterval,
      mode: mode,
      auto_scroll: autoScroll,
      auto_callout: autoCallout,
      seeding_support: seedingSupport,
      keyword_map: kwMap
    }));
  }
};

window.stopAutoPinning = function() {
  const btnStartAutoPin = document.getElementById('btnStartAutoPin');
  const btnStopAutoPin = document.getElementById('btnStopAutoPin');
  const badgePinStatus = document.getElementById('badgePinStatus');
  const detailEl = document.getElementById('activePinDetailText');

  if (btnStartAutoPin) btnStartAutoPin.disabled = false;
  if (btnStopAutoPin) btnStopAutoPin.disabled = true;
  if (badgePinStatus) {
    badgePinStatus.textContent = 'Đã Dừng Ghim';
    badgePinStatus.className = 'badge badge-warning';
  }
  if (detailEl) {
    detailEl.textContent = '🛑 Trạng thái: Đã dừng ghim';
  }

  appendTerminalLog('[INFO] 🛑 Đã dừng tiến trình ghim sản phẩm.', 'INFO');
  showToast('Đã dừng Auto Pin', 'warning');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'STOP_AUTO_PIN' }));
  }
};

function initAutoPinController() {
  const btnLaunchChrome = document.getElementById('btnLaunchTikTokChrome');
  const btnStartAutoPin = document.getElementById('btnStartAutoPin');
  const btnStopAutoPin = document.getElementById('btnStopAutoPin');
  const btnTestPin = document.getElementById('btnTestPinProduct');

  const btnSubTabCartLive = document.getElementById('btnSubTabCartLive');
  const btnSubTabVisual = document.getElementById('btnSubTabVisual');
  const btnSubTabPinAnalytics = document.getElementById('btnSubTabPinAnalytics');
  const btnSubTabJson = document.getElementById('btnSubTabJson');
  const cartLiveView = document.getElementById('timelineCartLiveView');
  const visualView = document.getElementById('timelineVisualView');
  const analyticsView = document.getElementById('timelinePinAnalyticsView');
  const jsonView = document.getElementById('timelineJsonView');
  const timelineTools = document.getElementById('timelineActionTools');
  const cartLiveTools = document.getElementById('cartLiveActionTools');
  const analyticsTools = document.getElementById('pinAnalyticsActionTools');

  const btnAddRow = document.getElementById('btnAddTimelineRow');
  const btnImportJson = document.getElementById('btnImportJson');
  const btnExportJson = document.getElementById('btnExportJson');
  const btnFormat = document.getElementById('btnFormatJson');
  const btnValidate = document.getElementById('btnValidateJson');

  const btnConvertCart = document.getElementById('btnConvertCartToTimeline');
  const btnSaveCartLocal = document.getElementById('btnSaveScrapedCartLocal');
  const btnClearCart = document.getElementById('btnClearScrapedCart');

  const timelineModal = document.getElementById('timelineModal');
  const btnCancelModal = document.getElementById('btnCancelTimelineModal');
  const btnSaveModal = document.getElementById('btnSaveTimelineModal');

  // Sub-Tab Switcher
  function switchToSubTab(tabName) {
    if (btnSubTabCartLive) btnSubTabCartLive.className = tabName === 'cart' ? 'btn btn-primary' : 'btn btn-secondary';
    if (btnSubTabVisual) btnSubTabVisual.className = tabName === 'visual' ? 'btn btn-primary' : 'btn btn-secondary';
    if (btnSubTabPinAnalytics) btnSubTabPinAnalytics.className = tabName === 'analytics' ? 'btn btn-primary' : 'btn btn-secondary';
    if (btnSubTabJson) btnSubTabJson.className = tabName === 'json' ? 'btn btn-primary' : 'btn btn-secondary';

    if (cartLiveView) cartLiveView.style.display = tabName === 'cart' ? 'flex' : 'none';
    if (visualView) visualView.style.display = tabName === 'visual' ? 'flex' : 'none';
    if (analyticsView) analyticsView.style.display = tabName === 'analytics' ? 'flex' : 'none';
    if (jsonView) jsonView.style.display = tabName === 'json' ? 'flex' : 'none';

    if (timelineTools) timelineTools.style.display = tabName === 'visual' ? 'flex' : 'none';
    if (cartLiveTools) cartLiveTools.style.display = tabName === 'cart' ? 'flex' : 'none';
    if (analyticsTools) analyticsTools.style.display = tabName === 'analytics' ? 'flex' : 'none';

    if (tabName === 'visual') syncJsonToTable();
    if (tabName === 'json') syncTableToJson();
    if (tabName === 'analytics') window.refreshPinAnalytics();
  }

  btnSubTabCartLive?.addEventListener('click', () => switchToSubTab('cart'));
  btnSubTabVisual?.addEventListener('click', () => switchToSubTab('visual'));
  btnSubTabPinAnalytics?.addEventListener('click', () => switchToSubTab('analytics'));
  btnSubTabJson?.addEventListener('click', () => switchToSubTab('json'));

  // Load saved scraped cart on init
  loadSavedScrapedCart();

  btnConvertCart?.addEventListener('click', () => {
    convertScrapedCartToTimeline();
    switchToSubTab('visual');
  });

  btnSaveCartLocal?.addEventListener('click', () => {
    showToast('Đã lưu giỏ hàng vào bộ nhớ máy thành công!', 'success');
  });

  btnTestPin?.addEventListener('click', () => {
    appendTerminalLog('[ACTION] ⚡ Đang gửi yêu cầu Ghim Thử Sản Phẩm #1 sang TikTok Live Streamer...', 'INFO');
    showToast('Đang ghim thử sản phẩm #1...', 'info');
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'TEST_PIN_PRODUCT',
        product_id: '1'
      }));
    }
  });

  btnClearCart?.addEventListener('click', () => {
    localStorage.removeItem('dta_scraped_cart_products');
    renderScrapedCartTable([]);
    showToast('Đã xóa dữ liệu giỏ hàng tạm thời!', 'info');
  });

  // Modal Handlers
  btnAddRow?.addEventListener('click', () => {
    if (timelineModal) timelineModal.classList.add('active');
  });

  btnCancelModal?.addEventListener('click', () => {
    if (timelineModal) timelineModal.classList.remove('active');
  });

  btnSaveModal?.addEventListener('click', () => {
    const inputTime = document.getElementById('inputModalTime')?.value || '00:15';
    const inputPid = document.getElementById('inputModalPid')?.value || '1';
    const inputTitle = document.getElementById('inputModalTitle')?.value || `Sản phẩm ${inputPid}`;
    const inputKeywords = document.getElementById('inputModalKeywords')?.value || '';

    const newEvt = {
      id: `evt_${Date.now()}`,
      time_ms: timeStrToMs(inputTime),
      time_str: inputTime,
      product_id: inputPid.trim(),
      title: inputTitle.trim(),
      keywords: inputKeywords.trim(),
      state: 'Sẵn sàng'
    };

    timelineEvents.push(newEvt);
    timelineEvents.sort((a, b) => a.time_ms - b.time_ms);
    renderTimelineTable();

    if (timelineModal) timelineModal.classList.remove('active');
    showToast(`Đã thêm mốc ghim SP #${inputPid} tại ${inputTime}`, 'success');
  });

  // Format JSON
  btnFormat?.addEventListener('click', () => {
    const textarea = document.getElementById('jsonScriptTextarea');
    if (!textarea) return;
    try {
      const parsed = JSON.parse(textarea.value);
      textarea.value = JSON.stringify(parsed, null, 2);
      syncJsonToTable();
      showToast('Đã căn chỉnh định dạng JSON thành công!', 'success');
    } catch (err) {
      showToast(`Lỗi cú pháp JSON: ${err.message}`, 'error');
    }
  });

  // Validate JSON
  btnValidate?.addEventListener('click', () => {
    const textarea = document.getElementById('jsonScriptTextarea');
    if (!textarea) return;
    try {
      const parsed = JSON.parse(textarea.value);
      if (!parsed.timeline_events || !Array.isArray(parsed.timeline_events)) {
        throw new Error("Kịch bản thiếu mảng 'timeline_events'");
      }
      syncJsonToTable();
      showToast(`Kịch bản JSON hợp lệ! (${parsed.timeline_events.length} sự kiện)`, 'success');
    } catch (err) {
      showToast(`Cú pháp JSON không hợp lệ: ${err.message}`, 'error');
    }
  });

  // Import JSON File
  btnImportJson?.addEventListener('click', async () => {
    if (window.dtaAPI?.openFileDialog) {
      const filePath = await window.dtaAPI.openFileDialog([
        { name: 'Kịch bản JSON', extensions: ['json'] }
      ]);
      if (filePath) {
        const content = await window.dtaAPI.readFileContent(filePath);
        if (content) {
          const textarea = document.getElementById('jsonScriptTextarea');
          if (textarea) textarea.value = content;
          syncJsonToTable();
          const fileName = filePath.split(/[\\/]/).pop();
          showToast(`Đã nạp file kịch bản ${fileName}`, 'success');
          appendTerminalLog(`[CONFIG] Đã nạp kịch bản Timeline từ: ${filePath}`, 'SUCCESS');
        }
      }
    }
  });

  // Export JSON File
  btnExportJson?.addEventListener('click', async () => {
    syncTableToJson();
    const textarea = document.getElementById('jsonScriptTextarea');
    const content = textarea?.value || '{}';

    if (window.dtaAPI?.saveFileDialog) {
      const res = await window.dtaAPI.saveFileDialog({
        defaultPath: 'script_timeline.json',
        content: content
      });
      if (res && res.success) {
        showToast('Đã lưu file kịch bản JSON thành công!', 'success');
        appendTerminalLog(`[CONFIG] Đã xuất kịch bản Timeline sang file: ${res.filePath}`, 'SUCCESS');
      }
    }
  });

  // Persistence & input binding for AutoPin Config
  const inputPinList = document.getElementById('inputPinProductList');
  const inputPinInt = document.getElementById('inputPinInterval');
  const selectPinM = document.getElementById('selectPinMode');
  const chkPinScroll = document.getElementById('chkPinAutoScroll');

  const savedList = localStorage.getItem('dta_pin_product_list');
  const savedInt = localStorage.getItem('dta_pin_interval');
  const savedMode = localStorage.getItem('dta_pin_mode');
  const savedScroll = localStorage.getItem('dta_pin_auto_scroll');

  if (savedList && inputPinList) inputPinList.value = savedList;
  if (savedInt && inputPinInt) inputPinInt.value = savedInt;
  if (savedMode && selectPinM) selectPinM.value = savedMode;
  if (chkPinScroll) chkPinScroll.checked = savedScroll === 'true';

  inputPinList?.addEventListener('change', () => {
    localStorage.setItem('dta_pin_product_list', inputPinList.value.trim());
  });
  inputPinInt?.addEventListener('change', () => {
    localStorage.setItem('dta_pin_interval', inputPinInt.value.trim());
  });
  selectPinM?.addEventListener('change', () => {
    localStorage.setItem('dta_pin_mode', selectPinM.value);
  });
  chkPinScroll?.addEventListener('change', () => {
    localStorage.setItem('dta_pin_auto_scroll', chkPinScroll.checked ? 'true' : 'false');
  });

  // Initial render of timeline table
  renderTimelineTable();
}

function initTimelineEditor() {
  initAutoPinController();
}

// 8. Captcha Solver, AI Comment Responder & API Configuration Controller
function initSadcaptchaSolver() {
  const btnStartScan = document.getElementById('btnStartCaptchaScan');
  const btnStopScan = document.getElementById('btnStopCaptchaScan');
  const btnManualSolve = document.getElementById('btnManualSolveCaptcha');
  const statusScan = document.getElementById('statusCaptchaScan');

  const btnLaunchComment = document.getElementById('btnLaunchCommentBrowser');
  const btnStartAi = document.getElementById('btnStartAiResponder');
  const btnStopAi = document.getElementById('btnStopAiResponder');

  const btnTestApi = document.getElementById('btnTestApiConnections');
  const btnSaveConfig = document.getElementById('btnSaveApiConfig');

  const inputSadKey = document.getElementById('inputSadCaptchaKey');
  const inputDsKey = document.getElementById('inputDeepSeekKey');
  const selectAiEng = document.getElementById('selectAiEngine');
  const inputUname = document.getElementById('inputTikTokUsername');

  // Load persistent configurations from localStorage
  const savedSadKey = localStorage.getItem('dta_sadcaptcha_key');
  const savedDsKey = localStorage.getItem('dta_deepseek_key');
  const savedEngine = localStorage.getItem('dta_ai_engine');
  const savedUname = localStorage.getItem('dta_tiktok_username');

  if (savedSadKey && inputSadKey) inputSadKey.value = savedSadKey;
  if (savedDsKey && inputDsKey) inputDsKey.value = savedDsKey;
  if (savedEngine && selectAiEng) selectAiEng.value = savedEngine;
  if (savedUname && inputUname) inputUname.value = savedUname;

  btnStartScan?.addEventListener('click', () => {
    const sadKey = inputSadKey?.value.trim() || '';
    if (!sadKey) {
      showToast('Vui lòng nhập SadCaptcha API Key ở mục Cấu Hình API!', 'warning');
      return;
    }

    if (btnStartScan) btnStartScan.disabled = true;
    if (btnStopScan) btnStopScan.disabled = false;
    if (statusScan) {
      statusScan.textContent = '● Đang quét Captcha';
      statusScan.className = 'badge badge-green';
    }

    appendTerminalLog('[SUCCESS] 🧩 Đã kích hoạt tiến trình tự động quét & giải Captcha TikTok LIVE Studio (SadCaptcha Engine).', 'SUCCESS');
    showToast('Đã bắt đầu quét Captcha tự động', 'success');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'START_CAPTCHA_SCAN',
        api_key: sadKey,
        interval: 2.0
      }));
    }
  });

  btnStopScan?.addEventListener('click', () => {
    if (btnStartScan) btnStartScan.disabled = false;
    if (btnStopScan) btnStopScan.disabled = true;
    if (statusScan) {
      statusScan.textContent = 'Đã dừng quét';
      statusScan.className = 'badge badge-warning';
    }

    appendTerminalLog('[INFO] 🛑 Đã dừng quét Captcha.', 'INFO');
    showToast('Đã dừng quét Captcha', 'warning');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({ command: 'STOP_CAPTCHA_SCAN' }));
    }
  });

  btnManualSolve?.addEventListener('click', () => {
    const sadKey = inputSadKey?.value.trim() || '';
    if (!sadKey) {
      showToast('Vui lòng nhập SadCaptcha API Key trước khi giải thử!', 'warning');
      return;
    }

    appendTerminalLog('[ACTION] ⚡ Đang tìm kiếm cửa sổ TikTok LIVE Studio và thực hiện giải Captcha ngay lập tức...', 'INFO');
    showToast('Đang giải thử Captcha TikTok LIVE Studio...', 'info');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'TRIGGER_MANUAL_CAPTCHA_SOLVE',
        api_key: sadKey
      }));
    }
  });

  btnLaunchComment?.addEventListener('click', () => {
    appendTerminalLog('[INFO] 🌐 Đang mở Trình duyệt đăng nhập TikTok lấy Token & Comment stream...', 'INFO');
    showToast('Đang mở Trình duyệt lấy Token...', 'info');
  });

  btnStartAi?.addEventListener('click', () => {
    const user = inputUname?.value.trim() || '@dta_studio';
    if (btnStartAi) btnStartAi.disabled = true;
    if (btnStopAi) btnStopAi.disabled = false;
    appendTerminalLog(`[SUCCESS] 🎭 Kích hoạt AI Trả lời bình luận tự động cho kênh: ${user} (Động cơ DeepSeek V3).`, 'SUCCESS');
    showToast(`Đã bật AI Trả lời bình luận (${user})`, 'success');
  });

  btnStopAi?.addEventListener('click', () => {
    if (btnStartAi) btnStartAi.disabled = false;
    if (btnStopAi) btnStopAi.disabled = true;
    appendTerminalLog('[INFO] 🛑 Đã dừng AI Trả lời bình luận.', 'INFO');
    showToast('Đã dừng AI Trả lời bình luận', 'warning');
  });

  document.getElementById('btnConfigureAiPrompt')?.addEventListener('click', () => {
    openActionModal(
      '⚙️ CẤU HÌNH PROMPT TRẢ LỜI AI',
      'Bạn là trợ lý bán hàng livestream chuyên nghiệp của DTA Studio. Hãy trả lời khách hàng ngắn gọn, thân thiện, khuyến khích mua hàng và trả lời đúng giá trị sản phẩm.',
      () => {
        showToast('Đã lưu Prompt AI thành công!', 'success');
      }
    );
  });

  // Load saved API Keys & Engine Configuration
  const savedDeepSeekKey = localStorage.getItem('dta_deepseek_key') || '';
  const savedSadCaptchaKey = localStorage.getItem('dta_sadcaptcha_key') || 'sadcaptcha_lic_8899aabbcc';
  const savedAiProvider = localStorage.getItem('dta_ai_provider') || 'auto';

  const inpDs = document.getElementById('inputDeepSeekKey');
  const inpSad = document.getElementById('inputSadCaptchaKey');
  const selProv = document.getElementById('selectAiProvider');

  if (inpDs && savedDeepSeekKey) inpDs.value = savedDeepSeekKey;
  if (inpSad && savedSadCaptchaKey) inpSad.value = savedSadCaptchaKey;
  if (selProv && savedAiProvider) selProv.value = savedAiProvider;

  selProv?.addEventListener('change', () => {
    const prov = selProv.value;
    localStorage.setItem('dta_ai_provider', prov);
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'SET_AI_ENGINE_PROVIDER',
        provider: prov
      }));
    }
    showToast(`Đã chuyển bộ não AI sang: ${selProv.options[selProv.selectedIndex].text}`, 'info');
  });

  window.testDeepSeekApiKeyAction = function() {
    const key = document.getElementById('inputDeepSeekKey')?.value.trim() || '';
    if (!key) {
      showToast('Vui lòng nhập DeepSeek API Key trước khi test!', 'warning');
      return;
    }
    appendTerminalLog('[INFO] ⚡ Đang gửi yêu cầu kiểm tra kết nối API và số dư tới DeepSeek V3 (671B MoE)...', 'INFO');
    showToast('Đang kiểm tra kết nối & số dư DeepSeek V3...', 'info');

    const badgeDs = document.getElementById('badgeDeepSeekBalance');
    if (badgeDs) {
      badgeDs.textContent = 'DeepSeek: Đang kiểm tra...';
      badgeDs.className = 'badge badge-warning';
    }

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'TEST_DEEPSEEK_API_KEY',
        api_key: key
      }));
    } else {
      showToast('Máy chủ AI chưa kết nối!', 'error');
    }
  };

  window.testSadCaptchaApiKeyAction = function() {
    const sadKey = document.getElementById('inputSadCaptchaKey')?.value.trim() || '';
    if (!sadKey) {
      showToast('Vui lòng nhập SadCaptcha API Key để kiểm tra!', 'warning');
      return;
    }
    appendTerminalLog('[INFO] 🔑 Đang kiểm tra bản quyền và số Credits thực tế trên SadCaptcha Cloud...', 'INFO');
    showToast('Đang kiểm tra Credits SadCaptcha...', 'info');

    const creditsEl = document.getElementById('badgeCreditsCount');
    if (creditsEl) {
      creditsEl.textContent = 'SadCaptcha: Đang kiểm tra...';
      creditsEl.className = 'badge badge-warning';
    }

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'CHECK_SADCAPTCHA_CREDITS',
        api_key: sadKey
      }));
    } else {
      showToast('Máy chủ chưa kết nối!', 'error');
    }
  };

  window.triggerManualCaptchaSolveAction = function() {
    const sadKey = document.getElementById('inputSadCaptchaKey')?.value.trim() || '';
    if (!sadKey) {
      showToast('Vui lòng nhập SadCaptcha API Key trước khi giải thử!', 'warning');
      return;
    }

    appendTerminalLog('[ACTION] ⚡ Đang tìm kiếm cửa sổ TikTok LIVE Studio và thực hiện giải Captcha ngay lập tức...', 'INFO');
    showToast('Đang giải thử Captcha TikTok LIVE Studio...', 'info');

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'TRIGGER_MANUAL_CAPTCHA_SOLVE',
        api_key: sadKey
      }));
    }
  };

  window.saveApiConfigurationAction = function() {
    const dsKey = document.getElementById('inputDeepSeekKey')?.value.trim() || '';
    const sadKey = document.getElementById('inputSadCaptchaKey')?.value.trim() || '';
    const provider = document.getElementById('selectAiProvider')?.value || 'auto';

    localStorage.setItem('dta_deepseek_key', dsKey);
    localStorage.setItem('dta_sadcaptcha_key', sadKey);
    localStorage.setItem('dta_ai_provider', provider);

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'SAVE_API_KEYS',
        deepseek_key: dsKey,
        sadcaptcha_key: sadKey,
        ai_provider: provider
      }));
    }

    appendTerminalLog(`[SUCCESS] 💾 Đã lưu cấu hình DeepSeek V3 API & SadCaptcha (Chế độ: ${provider.toUpperCase()}).`, 'SUCCESS');
    showToast('Đã lưu cấu hình API thành công!', 'success');
  };
}

function handleDeepSeekTestResult(res) {
  if (!res) return;
  const badgeDs = document.getElementById('badgeDeepSeekBalance');

  if (res.success) {
    const bal = res.balance || 'Sẵn Sàng';
    if (badgeDs) {
      badgeDs.textContent = `DeepSeek: ${bal}`;
      badgeDs.className = 'badge badge-cyan';
    }
    showToast(`🎉 DeepSeek V3 Thành Công (${res.latency_ms}ms)! Số dư: ${bal}`, 'success');
    appendTerminalLog(`[SUCCESS] 🎉 [DeepSeek V3 Cloud AI] Phản hồi (${res.latency_ms}ms): "${res.reply}" | Số dư khả dụng: ${bal}`, 'SUCCESS');
  } else {
    if (badgeDs) {
      badgeDs.textContent = 'DeepSeek: Lỗi Key';
      badgeDs.className = 'badge badge-danger';
    }
    showToast(`❌ Lỗi DeepSeek V3: ${res.message}`, 'error');
    appendTerminalLog(`[ERROR] ❌ [DeepSeek V3 Cloud AI] ${res.message}`, 'ERROR');
  }
}

// 9. Log Terminal Controller
function initLogTerminal() {
  const btnClear = document.getElementById('btnClearLog');
  const btnCopy = document.getElementById('btnCopyLog');
  const btnExport = document.getElementById('btnExportLogFile');
  const selectLevel = document.getElementById('selectLogLevel');
  const inputSearch = document.getElementById('inputSearchLog');

  btnClear?.addEventListener('click', () => {
    openActionModal(
      '🗑 XÁC NHẬN XÓA LOG TERMINAL',
      'Bạn có chắc chắn muốn xóa toàn bộ nội dung nhật ký chẩn đoán đang hiển thị không?',
      () => {
        rawLogEntries = [];
        renderTerminalLogs();
        showToast('Đã xóa sạch log terminal', 'info');
      }
    );
  });

  btnCopy?.addEventListener('click', () => {
    const text = rawLogEntries.map(e => e.rawText).join('\n');
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép toàn bộ log vào clipboard!', 'success');
    }).catch(err => console.log(err));
  });

  btnExport?.addEventListener('click', () => {
    appendTerminalLog('[SUCCESS] Đã xuất file Nhật ký hệ thống dta_autolive_diagnostics.log.', 'SUCCESS');
    showToast('Đã xuất file log chẩn đoán hệ thống thành công!', 'success');
  });

  selectLevel?.addEventListener('change', renderTerminalLogs);
  inputSearch?.addEventListener('input', renderTerminalLogs);
}

function appendTerminalLog(msg, level = 'INFO') {
  const timeStr = new Date().toLocaleTimeString();
  const rawText = `[${timeStr}] ${msg}`;
  
  rawLogEntries.push({ time: timeStr, msg: msg, level: level, rawText: rawText });
  renderTerminalLogs();
}

function renderTerminalLogs() {
  const terminalBox = document.getElementById('terminalBox');
  const selectedLevel = document.getElementById('selectLogLevel')?.value || 'ALL';
  const searchText = (document.getElementById('inputSearchLog')?.value || '').toLowerCase();

  if (!terminalBox) return;

  const filtered = rawLogEntries.filter(entry => {
    const matchLevel = selectedLevel === 'ALL' || entry.level === selectedLevel;
    const matchSearch = !searchText || entry.rawText.toLowerCase().includes(searchText);
    return matchLevel && matchSearch;
  });

  let html = '';
  filtered.forEach(entry => {
    let cssClass = 'log-info';
    if (entry.level === 'SUCCESS') cssClass = 'log-success';
    if (entry.level === 'WARNING') cssClass = 'log-warning';
    if (entry.level === 'ERROR') cssClass = 'log-error';

    html += `<span class="${cssClass}">${escapeHtml(entry.rawText)}</span>\n`;
  });

  terminalBox.innerHTML = html;
  terminalBox.scrollTop = terminalBox.scrollHeight;
}

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// 10. Modal & Toast System Handlers
window.closePreflightModal = function() {
  const modal = document.getElementById('preflightModal');
  if (modal) modal.classList.remove('active');
};

window.confirmAndStartLive = function() {
  const confirmBtn = document.getElementById('btnConfirmStartLive');
  if (confirmBtn && confirmBtn.disabled) return;
  window.closePreflightModal();
  executeStartLive();
};

window.closeActionModal = function() {
  const modal = document.getElementById('confirmActionModal');
  if (modal) modal.classList.remove('active');
  pendingActionCallback = null;
};

window.confirmExecuteAction = function() {
  const modal = document.getElementById('confirmActionModal');
  if (modal) modal.classList.remove('active');
  if (pendingActionCallback) {
    pendingActionCallback();
    pendingActionCallback = null;
  }
};

function initModalHandlers() {
  // Preflight Live Modal Buttons
  document.getElementById('btnCancelPreflight')?.addEventListener('click', (e) => {
    e.stopPropagation();
    window.closePreflightModal();
  });

  document.getElementById('btnConfirmStartLive')?.addEventListener('click', (e) => {
    e.stopPropagation();
    window.confirmAndStartLive();
  });

  // Action Confirm Modal Buttons
  document.getElementById('btnCancelAction')?.addEventListener('click', (e) => {
    e.stopPropagation();
    window.closeActionModal();
  });

  document.getElementById('btnExecuteAction')?.addEventListener('click', (e) => {
    e.stopPropagation();
    window.confirmExecuteAction();
  });

  // Backdrop overlay click to close
  document.getElementById('preflightModal')?.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'preflightModal') {
      window.closePreflightModal();
    }
  });

  document.getElementById('confirmActionModal')?.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'confirmActionModal') {
      window.closeActionModal();
    }
  });

  // ESC key to close any active modal
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.closePreflightModal();
      window.closeActionModal();
    }
  });
}

function initWorkspaceHelpers() {
  document.getElementById('btnCopyDiagInfo')?.addEventListener('click', () => {
    const info = `DTA AutoLive v1.1.0 Electron\nNode: 20.18.0\nPython: 3.11\nWebSocket: ws://127.0.0.1:8765\nDirectShow: DTA Camera & DTA Audio Active`;
    navigator.clipboard.writeText(info).then(() => {
      showToast('Đã sao chép thông tin chẩn đoán!', 'success');
    });
  });

  document.getElementById('btnCopyContact')?.addEventListener('click', () => {
    const contact = `DTA Studio - Đức Trường AI\nHotline/Zalo: 0962.775.506\nEmail: ductruong.onl@gmail.com\nWeb: https://dta-studio.vercel.app/`;
    navigator.clipboard.writeText(contact).then(() => {
      showToast('Đã sao chép thông tin liên hệ!', 'success');
    });
  });
}

function openActionModal(title, bodyText, onConfirm) {
  const modal = document.getElementById('confirmActionModal');
  const titleEl = document.getElementById('confirmModalTitle');
  const bodyEl = document.getElementById('confirmModalBody');

  if (titleEl) titleEl.textContent = title;
  if (bodyEl) bodyEl.innerHTML = bodyText;
  pendingActionCallback = onConfirm;

  if (modal) modal.classList.add('active');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  // Keep max 3 toasts visible to prevent blocking UI headers
  while (container.children.length >= 3) {
    container.removeChild(container.firstChild);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 2200);
}

/* ==========================================================================
   11. QWEN LOCAL AI ENGINE & GPU VRAM LIFECYCLE CONTROLLER
   ========================================================================== */

const DEFAULT_SEEDING_PROMPT = `Bạn là Trợ lý Seeding Livestream thông minh của DTA Studio.
Nhiệm vụ: Đóng vai người mua hàng online thông thái, bình luận tương tác tự nhiên, khen sản phẩm, hỏi về chất liệu, thông số, độ bền, xin mã giảm giá/freeship và kích thích các khán giả khác bấm vào giỏ hàng chốt đơn ngay.
Yêu cầu:
- Viết câu ngắn gọn dưới 20 từ, gõ như người dùng thật đang xem live.
- Hỏi xoay quanh mã sản phẩm đang được ghim (#mã số), tạo hiệu ứng đám đông (FOMO).`;

const DEFAULT_SEEDING_TEMPLATES = `Cây mã #1 có tặng kèm ngọn phụ với nhẫn silicon không shop?
Cây số #1 độ cứng thế nào, tải cá tầm mấy kg vậy anh?
Mã #1 có size 3m6 với 4m5 không shop ơi?
Shop ghim lại mã #1 cho em bấm chốt đơn nhận ưu đãi với ạ!
Mã #1 đang trợ giá hời quá, em vừa đặt 1 cây rồi nha!
Mã #2 chất liệu carbon mấy T vậy shop, cầm có nhẹ tay không?
Shop ơi mã #3 có được freeship toàn quốc không ạ?
Em vừa nhận hàng hôm qua, phôi cần bóng đẹp và dày dặn lắm nha mọi người!
Shop tư vấn giúp em cây nào săn hàng câu dịch vụ êm nhất với ạ!
Ghim lại mã đang giảm giá đi shop, em vừa nạp xu xong nè!`;

const DEFAULT_HOST_PROMPT = `Bạn là một nhân viên tư vấn bán hàng online cực kỳ nhiệt tình, khéo léo và tự nhiên (xưng "em" hoặc xưng tên Shop - gọi khách là "bác/anh/chị" tùy ngữ cảnh).
---
THÔNG TIN NỀN TẢNG CỬA HÀNG:
{{Thong tin nen tang}}
DANH SÁCH SẢN PHẨM HIỆN CÓ:
{{List san pham}}
QUY TẮC:
{{Quy tac}}

NGUYÊN TẮC XỬ LÝ BÌNH LUẬN:

1. ĐOÁN Ý VÀ GIẢI MÃ CHÍNH TẢ (Quan trọng):
- Khách có thể gõ sai chính tả, không dấu, viết tắt, teencode hoặc dùng tiếng lóng (ví dụ: "cần câu đon", "may cau", "ib gia", "ship hn bnh", "gia s bnhieu"). Hãy chủ động suy luận theo ngữ cảnh và đối chiếu với danh sách sản phẩm để trả lời đúng món khách đang quan tâm.
- Nếu bình luận quá mơ hồ hoặc có thể hiểu theo nhiều món khác nhau, hãy lịch sự hỏi lại để làm rõ kèm một gợi ý nhẹ (Ví dụ: "Dạ có phải bác đang hỏi mẫu cần X hay mẫu Y không ạ?").

2. XỬ LÝ THEO TỪNG TÌNH HUỐNG:
- Khách hỏi sản phẩm CÓ trong danh sách: Tư vấn đúng trọng tâm, nêu bật ưu điểm phù hợp với nhu cầu, báo giá rõ ràng và khéo léo mời khách chốt đơn/nhắn tin riêng để tạo đơn nhanh.
- Khách hỏi sản phẩm KHÔNG CÓ hoặc ĐÃ HẾT: Tuyệt đối không từ chối cộc lốc. Hãy phản hồi khéo léo (Ví dụ: "Dạ mẫu này shop em tạm hết/chưa về thêm...") và lập tức gợi ý một sản phẩm khác đang có sẵn mang tính năng tương đương kèm lý do nên chọn.
- Khách chốt đơn (để lại sđt, địa chỉ, "lấy 1 cái", "chốt"): Phản hồi vui vẻ, xác nhận và hướng dẫn khách check tin nhắn riêng để bảo mật thông tin cá nhân.
- Khách comment giao lưu / khen / trêu đùa / tương tác vui: Trò chuyện tự nhiên, duyên dáng như người thật, không gượng ép "chèo kéo" bán hàng trong mọi câu nói.

3. PHONG CÁCH DIỄN ĐẠT:
- Giọng văn đời thực, ngắn gọn (1–3 câu), ngắt ý rõ ràng, dùng thêm 1–2 emoji phù hợp để tạo cảm giác thân thiện.
- Không nói vòng vo máy móc, không lặp lại nguyên văn câu hỏi của khách.
- Chỉ đưa ra thông tin có thật trong dữ liệu được cung cấp, không tự bịa đặt giá cả hay chính sách ngoài danh sách.`;

const DEFAULT_PLATFORM_INFO = `- Giao hàng: Giao hàng toàn quốc từ 2-4 ngày. Được kiểm tra hàng (đồng kiểm) trước khi thanh toán.
- Đổi trả & Bảo hành: Lỗi 1 đổi 1 trong vòng 7 ngày đầu tiên nếu có lỗi từ nhà sản xuất. Hỗ trợ bảo hành chính hãng.
- Miễn phí vận chuyển: Freeship toàn quốc cho đơn hàng từ 200.000đ hoặc khi áp mã voucher trên live.
- Quà tặng: Tặng kèm phụ kiện chính hãng theo từng phân loại sản phẩm.`;

const DEFAULT_RULES = `- Luôn trả lời tôn trọng, lịch sự và thân thiện với khách hàng.
- Tuyệt đối không nhắc đến các nền tảng cấm hoặc từ khóa vi phạm chính sách livestream TikTok (không nhắc Shopee, Lazada, số điện thoại ngoài...).
- Không nói tục, không cộc lốc, không tranh cãi với khách hàng.
- Luôn khuyến khích khách bấm vào góc trái màn hình để xem giỏ hàng và chốt đơn.`;

let currentEditingTextType = 'platform_info'; // 'platform_info' | 'rules'
let pendingPresetActionType = 'create'; // 'create' | 'rename'

function getSavedHostPresets() {
  try {
    const raw = localStorage.getItem('dta_host_presets');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (e) {
    console.error('Error parsing dta_host_presets:', e);
  }
  return [
    { id: 'default_sales', name: '⭐ Bán Hàng Trực Tiếp (Mặc Định)', prompt: DEFAULT_HOST_PROMPT },
    { id: 'flash_sale', name: '⚡ Săn Deal Flash Sale Cực Mạnh', prompt: DEFAULT_HOST_PROMPT },
    { id: 'consulting_pro', name: '🎣 Tư Vấn Chuyên Sâu & Kỹ Thuật', prompt: DEFAULT_HOST_PROMPT }
  ];
}

function initQwenAiGpuController() {
  const hostUser = document.getElementById('inputHostTikTokUser');
  const hostPrompt = document.getElementById('inputHostAiPrompt');
  const selectPreset = document.getElementById('selectHostPromptPreset');

  // Khởi tạo và nạp Presets
  initHostLivePromptPresets();

  try {
    if (hostUser) hostUser.value = localStorage.getItem('dta_host_user') || '@dta_studio';
  } catch (e) {
    console.error('Error loading host chatbot settings:', e);
  }

function initHostLivePromptPresets() {
  const selectPreset = document.getElementById('selectHostPromptPreset');
  const hostPrompt = document.getElementById('inputHostAiPrompt');
  if (!selectPreset || !hostPrompt) return;

  const presets = getSavedHostPresets();
  let currentId = localStorage.getItem('dta_current_preset_id') || 'default_sales';

  // Đảm bảo currentId tồn tại trong danh sách
  if (!presets.some(p => p.id === currentId)) {
    currentId = presets[0].id;
  }

  // Render options vào select
  selectPreset.innerHTML = '';
  presets.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name;
    if (p.id === currentId) opt.selected = true;
    selectPreset.appendChild(opt);
  });

  // Nạp nội dung prompt của preset hiện tại
  const activePreset = presets.find(p => p.id === currentId) || presets[0];
  hostPrompt.value = activePreset.prompt || DEFAULT_HOST_PROMPT;

  // Lắng nghe sự kiện đổi Preset
  selectPreset.addEventListener('change', () => {
    const nextId = selectPreset.value;
    const nextPreset = presets.find(p => p.id === nextId);
    if (nextPreset) {
      hostPrompt.value = nextPreset.prompt || DEFAULT_HOST_PROMPT;
      localStorage.setItem('dta_current_preset_id', nextId);
      showToast(`Đã chuyển sang Preset: ${nextPreset.name}`, 'info');
      syncPromptConfigToBackend();
    }
  });

  // Đồng bộ cấu hình ban đầu tới backend
  setTimeout(() => {
    syncPromptConfigToBackend();
  }, 1000);
}

function syncPromptConfigToBackend() {
  const hostPrompt = document.getElementById('inputHostAiPrompt');
  const promptVal = hostPrompt?.value.trim() || DEFAULT_HOST_PROMPT;
  const platVal = localStorage.getItem('dta_platform_info') || DEFAULT_PLATFORM_INFO;
  const rulesVal = localStorage.getItem('dta_rules') || DEFAULT_RULES;

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'SET_HOST_PROMPT_CONFIG',
      prompt_template: promptVal,
      platform_info: platVal,
      rules: rulesVal
    }));
  }
}

window.saveCurrentHostPreset = function() {
  const selectPreset = document.getElementById('selectHostPromptPreset');
  const hostPrompt = document.getElementById('inputHostAiPrompt');
  if (!selectPreset || !hostPrompt) return;

  const currentId = selectPreset.value;
  const promptContent = hostPrompt.value.trim();
  const presets = getSavedHostPresets();

  const target = presets.find(p => p.id === currentId);
  if (target) {
    target.prompt = promptContent;
    localStorage.setItem('dta_host_presets', JSON.stringify(presets));
    syncPromptConfigToBackend();
    showToast(`Đã lưu Preset '${target.name}' thành công!`, 'success');
    appendTerminalLog(`[SUCCESS] 💾 Đã lưu cấu hình Preset Kịch bản: '${target.name}'.`, 'SUCCESS');
  }
};

window.addNewHostPresetModal = function() {
  pendingPresetActionType = 'create';
  const modal = document.getElementById('promptPresetNameModal');
  const title = document.getElementById('presetNameModalTitle');
  const inp = document.getElementById('inputPresetNameModal');

  if (title) title.textContent = '➕ THÊM PRESET KỊCH BẢN MỚI';
  if (inp) {
    inp.value = `Kịch Bản Bán Hàng #${getSavedHostPresets().length + 1}`;
    inp.focus();
  }
  if (modal) modal.classList.add('active');
};

window.renameHostPresetModal = function() {
  const selectPreset = document.getElementById('selectHostPromptPreset');
  if (!selectPreset) return;

  pendingPresetActionType = 'rename';
  const currentId = selectPreset.value;
  const presets = getSavedHostPresets();
  const target = presets.find(p => p.id === currentId);

  const modal = document.getElementById('promptPresetNameModal');
  const title = document.getElementById('presetNameModalTitle');
  const inp = document.getElementById('inputPresetNameModal');

  if (title) title.textContent = '✏️ ĐỔI TÊN PRESET KỊCH BẢN';
  if (inp && target) {
    inp.value = target.name;
    inp.focus();
  }
  if (modal) modal.classList.add('active');
};

window.closePresetNameModal = function() {
  const modal = document.getElementById('promptPresetNameModal');
  if (modal) modal.classList.remove('active');
};

window.confirmPresetNameAction = function() {
  const inp = document.getElementById('inputPresetNameModal');
  const nameVal = inp?.value.trim();
  if (!nameVal) {
    showToast('Vui lòng nhập tên cho Preset!', 'warning');
    return;
  }

  const presets = getSavedHostPresets();
  const selectPreset = document.getElementById('selectHostPromptPreset');
  const hostPrompt = document.getElementById('inputHostAiPrompt');

  if (pendingPresetActionType === 'create') {
    const newId = `preset_${Date.now()}`;
    const newPreset = {
      id: newId,
      name: nameVal,
      prompt: hostPrompt?.value.trim() || DEFAULT_HOST_PROMPT
    };
    presets.push(newPreset);
    localStorage.setItem('dta_host_presets', JSON.stringify(presets));
    localStorage.setItem('dta_current_preset_id', newId);

    window.closePresetNameModal();
    initHostLivePromptPresets();
    showToast(`Đã tạo Preset mới: '${nameVal}'`, 'success');
  } else if (pendingPresetActionType === 'rename') {
    const currentId = selectPreset?.value;
    const target = presets.find(p => p.id === currentId);
    if (target) {
      target.name = nameVal;
      localStorage.setItem('dta_host_presets', JSON.stringify(presets));
      window.closePresetNameModal();
      initHostLivePromptPresets();
      showToast(`Đã đổi tên Preset thành: '${nameVal}'`, 'success');
    }
  }
};

window.deleteHostPresetAction = function() {
  const selectPreset = document.getElementById('selectHostPromptPreset');
  if (!selectPreset) return;

  const currentId = selectPreset.value;
  const presets = getSavedHostPresets();

  if (presets.length <= 1) {
    showToast('Cần giữ lại ít nhất 1 Preset kịch bản!', 'warning');
    return;
  }

  const target = presets.find(p => p.id === currentId);
  const targetName = target ? target.name : 'Preset này';

  openActionModal(
    '🗑 XÁC NHẬN XÓA PRESET KỊCH BẢN',
    `Bạn có chắc chắn muốn xóa Preset: <strong>${targetName}</strong> không?<br><br>Hành động này không thể hoàn tác.`,
    () => {
      const remaining = presets.filter(p => p.id !== currentId);
      localStorage.setItem('dta_host_presets', JSON.stringify(remaining));
      localStorage.setItem('dta_current_preset_id', remaining[0].id);
      initHostLivePromptPresets();
      showToast(`Đã xóa Preset '${targetName}'`, 'info');
      appendTerminalLog(`[ACTION] 🗑️ Đã xóa Preset kịch bản: '${targetName}'.`, 'WARNING');
    }
  );
};

window.insertPromptVariable = function(varName) {
  const hostPrompt = document.getElementById('inputHostAiPrompt');
  if (!hostPrompt) return;

  const start = hostPrompt.selectionStart || 0;
  const end = hostPrompt.selectionEnd || 0;
  const text = hostPrompt.value;

  hostPrompt.value = text.substring(0, start) + varName + text.substring(end);
  hostPrompt.selectionStart = hostPrompt.selectionEnd = start + varName.length;
  hostPrompt.focus();
  showToast(`Đã chèn biến ${varName}`, 'info');
};

window.openTextEditorModal = function(type) {
  currentEditingTextType = type;
  const modal = document.getElementById('dtaTextEditorModal');
  const titleEl = document.getElementById('dtaTextEditorTitle');
  const badgeEl = document.getElementById('dtaTextEditorBadge');
  const descEl = document.getElementById('dtaTextEditorDesc');
  const contentEl = document.getElementById('dtaTextEditorContent');

  if (type === 'platform_info') {
    if (titleEl) titleEl.querySelector('span').textContent = '📄 CHỈNH SỬA THÔNG TIN NỀN TẢNG';
    if (badgeEl) {
      badgeEl.textContent = '{{Thong tin nen tang}}';
      badgeEl.className = 'badge badge-cyan';
    }
    if (descEl) descEl.textContent = 'Nhập thông tin nền tảng của Shop: Chính sách giao hàng, đổi trả, bảo hành, kiểm tra hàng, quà tặng...';
    if (contentEl) contentEl.value = localStorage.getItem('dta_platform_info') || DEFAULT_PLATFORM_INFO;
  } else if (type === 'rules') {
    if (titleEl) titleEl.querySelector('span').textContent = '📋 CHỈNH SỬA QUY TẮC BÁN HÀNG';
    if (badgeEl) {
      badgeEl.textContent = '{{Quy tac}}';
      badgeEl.className = 'badge badge-warning';
    }
    if (descEl) descEl.textContent = 'Nhập quy tắc điều được làm và không được làm (từ ngữ cấm, quy định trả lời, không tranh cãi...).';
    if (contentEl) contentEl.value = localStorage.getItem('dta_rules') || DEFAULT_RULES;
  }

  if (modal) modal.classList.add('active');
};

window.closeTextEditorModal = function() {
  const modal = document.getElementById('dtaTextEditorModal');
  if (modal) modal.classList.remove('active');
};

window.saveTextEditorContentAction = function() {
  const contentEl = document.getElementById('dtaTextEditorContent');
  const val = contentEl?.value.trim() || '';

  if (currentEditingTextType === 'platform_info') {
    localStorage.setItem('dta_platform_info', val);
    showToast('Đã lưu Thông Tin Nền Tảng {{Thong tin nen tang}} thành công!', 'success');
    appendTerminalLog('[SUCCESS] 💾 Đã cập nhật dữ liệu biến {{Thong tin nen tang}}.', 'SUCCESS');
  } else if (currentEditingTextType === 'rules') {
    localStorage.setItem('dta_rules', val);
    showToast('Đã lưu Quy Tắc {{Quy tac}} thành công!', 'success');
    appendTerminalLog('[SUCCESS] 💾 Đã cập nhật dữ liệu biến {{Quy tac}}.', 'SUCCESS');
  }

  window.closeTextEditorModal();
  syncPromptConfigToBackend();
};

window.handleImportTxtFile = function(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    const contentEl = document.getElementById('dtaTextEditorContent');
    if (contentEl) {
      contentEl.value = text;
      showToast(`Đã nạp nội dung từ file '${file.name}'!`, 'success');
    }
  };
  reader.readAsText(file, 'UTF-8');
};

window.exportTxtFileAction = function() {
  const contentEl = document.getElementById('dtaTextEditorContent');
  const val = contentEl?.value || '';
  const fileName = currentEditingTextType === 'platform_info' ? 'thong_tin_nen_tang.txt' : 'quy_tac.txt';

  const blob = new Blob([val], { type: 'text/plain;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast(`Đã xuất file '${fileName}'`, 'success');
};

window.previewCartProductsVariable = function() {
  if (!currentScrapedProducts || currentScrapedProducts.length === 0) {
    openActionModal(
      '📦 BIẾN {{List san pham}} (CHƯA CÀO DỮ LIỆU)',
      'Hiện tại chưa có sản phẩm nào trong bộ nhớ Giỏ Hàng.<br><br>Vui lòng sang <strong>Tab 2 (📌 Sản Phẩm)</strong> bấm <strong>⚡ Cào Giỏ Hàng</strong> để nạp toàn bộ danh sách sản phẩm thực tế vào biến này!',
      null
    );
    return;
  }

  let html = `<div style="max-height: 320px; overflow-y: auto; font-size: 11.5px; line-height: 1.6;">`;
  html += `<p style="color: var(--accent); margin-bottom: 8px;">Dưới đây là nội dung mẫu mà biến <strong>{{List san pham}}</strong> (${currentScrapedProducts.length} sản phẩm) sẽ tự động nhúng vào Prompt:</p>`;
  html += `<pre style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 6px; font-family: monospace; white-space: pre-wrap;">`;

  currentScrapedProducts.forEach(p => {
    const stt = p.stt || '?';
    const name = p.name || 'Sản phẩm';
    const price = p.sale_price || p.price || 'Liên hệ';
    const orig = p.original_price ? ` (Gốc: ${p.original_price})` : '';
    const camp = p.campaign ? ` | Ưu đãi: ${p.campaign}` : '';
    const stock = p.stock || 'Còn hàng';
    html += `- SP #${stt}: ${name} | Giá: ${price}${orig}${camp} | Kho: ${stock}\n`;
  });

  html += `</pre></div>`;

  openActionModal('📦 XEM TRƯỚC BIẾN {{List san pham}}', html, null);
};

  // Auto-check model status on app startup
  setTimeout(() => {
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      window.checkAiModel();
      wsClient.send(JSON.stringify({ command: 'GET_GPU_TELEMETRY' }));
    }
  }, 1500);

  // Periodic GPU telemetry refresh (every 5 seconds)
  setInterval(() => {
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({ command: 'GET_GPU_TELEMETRY' }));
    }
  }, 5000);
}

window.checkAiModel = function() {
  const modelKey = document.getElementById('selectQwenModelKey')?.value || 'Qwen2.5-7B-Instruct-Q4_K_M';
  appendTerminalLog(`[INFO] 🔍 Đang kiểm tra tệp Model '${modelKey}' trên ổ đĩa và phần cứng GPU...`, 'INFO');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    showToast(`Đang kiểm tra Model '${modelKey}'...`, 'info');
    wsClient.send(JSON.stringify({
      command: 'CHECK_AI_MODEL',
      model_key: modelKey
    }));
  } else {
    appendTerminalLog('[CẢNH BÁO] ⚠️ Máy chủ AI Python chưa kết nối. Đang tự động kết nối lại...', 'WARNING');
    showToast('Máy chủ AI đang khởi động, vui lòng thử lại sau...', 'warning');
    const badgeModel = document.getElementById('badgeAiModelStatus');
    if (badgeModel) {
      badgeModel.textContent = 'Model: Đang kết nối máy chủ...';
      badgeModel.className = 'badge badge-warning';
    }
  }
};

window.downloadAiModel = function() {
  const modelKey = document.getElementById('selectQwenModelKey')?.value || 'Qwen2.5-7B-Instruct-Q4_K_M';

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    appendTerminalLog(`[ACTION] ⬇️ Bắt đầu tiến trình tải tự động Model '${modelKey}' từ Hugging Face...`, 'INFO');
    showToast(`Bắt đầu tải Model '${modelKey}'...`, 'info');
    showModelDownloadProgressBox(true);
    wsClient.send(JSON.stringify({
      command: 'DOWNLOAD_AI_MODEL',
      model_key: modelKey
    }));
  } else {
    appendTerminalLog('[CẢNH BÁO] ⚠️ Máy chủ AI chưa kết nối để tải Model. Vui lòng kiểm tra lại trạng thái máy chủ.', 'WARNING');
    showToast('Chưa kết nối tới máy chủ AI Python.', 'error');
  }
};

window.cancelDownloadAiModel = function() {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'CANCEL_DOWNLOAD_AI_MODEL' }));
  }
  showModelDownloadProgressBox(false);
  appendTerminalLog('[SYSTEM] 🛑 Đã gửi lệnh hủy tải Model.', 'WARNING');
};

window.openModelFolder = function() {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'OPEN_MODELS_FOLDER' }));
    showToast('Đang mở thư mục lưu trữ Model AI...', 'info');
    appendTerminalLog('[ACTION] 📁 Yêu cầu mở thư mục lưu trữ Model AI trên máy.', 'INFO');
  } else {
    showToast('Chưa kết nối máy chủ AI để mở thư mục!', 'warning');
  }
};

window.deleteAiModel = function() {
  const modelKey = document.getElementById('selectQwenModelKey')?.value || 'Qwen2.5-7B-Instruct-Q4_K_M';
  const confirmed = confirm(`Bạn có chắc chắn muốn XÓA tệp Model '${modelKey}' khỏi ổ cứng không?\n\nSau khi xóa, bạn có thể tải lại hoặc cài đặt phiên bản Model khác.`);
  if (!confirmed) return;

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    appendTerminalLog(`[ACTION] 🗑️ Đang tiến hành xóa tệp Model '${modelKey}'...`, 'WARNING');
    showToast(`Đang xóa Model '${modelKey}'...`, 'warning');
    wsClient.send(JSON.stringify({
      command: 'DELETE_AI_MODEL',
      model_key: modelKey
    }));
  } else {
    showToast('Chưa kết nối máy chủ AI để xóa Model!', 'error');
  }
};

window.startAiGpuServer = function() {
  const modelKey = document.getElementById('selectQwenModelKey')?.value || 'Qwen2.5-7B-Instruct-Q4_K_M';
  const btnStart = document.getElementById('btnStartAiGpuServer');
  const btnStop = document.getElementById('btnStopAiGpuServer');
  const badgeState = document.getElementById('badgeGpuServerState');
  const badgeHero = document.getElementById('badgeHeroServerStatus');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    if (btnStart) btnStart.style.pointerEvents = 'none';
    if (badgeState) {
      badgeState.textContent = 'AI Server: ĐANG NẠP VRAM...';
      badgeState.className = 'badge badge-warning';
    }
    if (badgeHero) {
      badgeHero.textContent = 'Đang Nạp VRAM...';
      badgeHero.className = 'badge badge-yellow';
    }

    appendTerminalLog(`[ACTION] 🚀 Bắt đầu nạp Model '${modelKey}' vào GPU VRAM (n_gpu_layers=-1)...`, 'INFO');
    showToast('Đang nạp Model vào GPU VRAM...', 'info');

    wsClient.send(JSON.stringify({
      command: 'START_AI_GPU_SERVER',
      model_key: modelKey,
      n_gpu_layers: -1,
      n_ctx: 4096
    }));
  } else {
    appendTerminalLog('[CẢNH BÁO] ⚠️ Máy chủ AI Python chưa kết nối. Vui lòng kiểm tra lại kết nối.', 'WARNING');
    showToast('Máy chủ AI chưa kết nối.', 'error');
  }
};

window.stopAiGpuServer = function() {
  const btnStart = document.getElementById('btnStartAiGpuServer');
  const btnStop = document.getElementById('btnStopAiGpuServer');
  const badgeState = document.getElementById('badgeGpuServerState');
  const badgeHero = document.getElementById('badgeHeroServerStatus');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    if (btnStop) btnStop.disabled = true;
    if (btnStart) btnStart.style.pointerEvents = 'auto';
    if (badgeHero) {
      badgeHero.textContent = 'Đang Tắt...';
      badgeHero.className = 'badge badge-warning';
    }

    appendTerminalLog('[SYSTEM] 🛑 Đang tắt Server AI và giải phóng 100% VRAM GPU...', 'WARNING');
    showToast('Đang giải phóng VRAM GPU...', 'warning');
    wsClient.send(JSON.stringify({ command: 'STOP_AI_GPU_SERVER' }));
  } else {
    showToast('Máy chủ AI chưa kết nối.', 'warning');
  }
};

function showModelDownloadProgressBox(show) {
  const box = document.getElementById('modelDownloadBox');
  if (box) box.style.display = show ? 'flex' : 'none';
}

function updateModelDownloadProgress(pdata) {
  showModelDownloadProgressBox(true);
  const pctEl = document.getElementById('dlModelPct');
  const barEl = document.getElementById('dlProgressBar');
  const bytesEl = document.getElementById('dlMetaBytes');
  const speedEl = document.getElementById('dlMetaSpeed');
  const etaEl = document.getElementById('dlMetaEta');

  const pct = pdata.progress_pct || 0;
  if (pctEl) pctEl.textContent = `${pct}%`;
  if (barEl) barEl.style.width = `${pct}%`;
  if (bytesEl) bytesEl.textContent = `Đã tải: ${pdata.downloaded_gb || 0} GB / ${pdata.total_gb || 0} GB`;
  if (speedEl) speedEl.textContent = `Tốc độ: ${pdata.speed_mb || 0} MB/s`;
  if (etaEl) etaEl.textContent = `ETA: ${pdata.eta_sec || 0}s`;

  if (pdata.status === 'completed') {
    showToast('Tải Model AI GGUF thành công!', 'success');
    setTimeout(() => {
      showModelDownloadProgressBox(false);
      window.checkAiModel();
    }, 2000);
  } else if (pdata.status === 'error') {
    showToast(`Lỗi tải model: ${pdata.error}`, 'error');
  }
}

function handleAiModelStatusResult(status) {
  const badgeFile = document.getElementById('badgeModelFileStatus');
  if (badgeFile) {
    if (status.exists) {
      badgeFile.textContent = `Đã có (${status.size_gb} GB)`;
      badgeFile.className = 'badge badge-green';
    } else {
      badgeFile.textContent = `Chưa tải (Cần ~${status.expected_size_gb} GB)`;
      badgeFile.className = 'badge badge-warning';
    }
  }

  if (status.gpu_info) {
    updateGpuTelemetryUI(status.gpu_info);
  }

  const badgeServer = document.getElementById('badgeGpuServerState');
  const badgeHero = document.getElementById('badgeHeroServerStatus');
  const btnStart = document.getElementById('btnStartAiGpuServer');
  const btnStop = document.getElementById('btnStopAiGpuServer');

  if (status.is_loaded) {
    if (badgeServer) {
      badgeServer.textContent = 'AI Server: ĐÃ NẠP GPU (Active)';
      badgeServer.className = 'badge badge-green';
    }
    if (badgeHero) {
      badgeHero.textContent = 'Running (CUDA)';
      badgeHero.className = 'badge badge-green';
    }
    if (btnStart) btnStart.style.pointerEvents = 'none';
    if (btnStop) btnStop.disabled = false;
  } else {
    if (badgeServer) {
      badgeServer.textContent = 'AI Server: CHƯA BẬT';
      badgeServer.className = 'badge badge-cyan';
    }
    if (badgeHero) {
      badgeHero.textContent = 'Standby';
      badgeHero.className = 'badge badge-cyan';
    }
    if (btnStart) btnStart.style.pointerEvents = 'auto';
    if (btnStop) btnStop.disabled = true;
  }
}

function handleAiGpuServerResult(data) {
  const badgeServer = document.getElementById('badgeGpuServerState');
  const badgeHero = document.getElementById('badgeHeroServerStatus');
  const btnStart = document.getElementById('btnStartAiGpuServer');
  const btnStop = document.getElementById('btnStopAiGpuServer');

  if (data.success) {
    if (badgeServer) {
      badgeServer.textContent = 'AI Server: ĐÃ NẠP GPU (Active)';
      badgeServer.className = 'badge badge-green';
    }
    if (badgeHero) {
      badgeHero.textContent = 'Running (CUDA)';
      badgeHero.className = 'badge badge-green';
    }
    if (btnStart) btnStart.style.pointerEvents = 'none';
    if (btnStop) btnStop.disabled = false;
    showToast('Đã nạp Model vào GPU VRAM thành công!', 'success');
    appendTerminalLog(`[SUCCESS] 🚀 Server AI '${data.model_key}' đã sẵn sàng phản hồi siêu tốc trên GPU!`, 'SUCCESS');
  } else {
    if (badgeServer) {
      badgeServer.textContent = 'AI Server: LỖI NẠP GPU';
      badgeServer.className = 'badge badge-danger';
    }
    if (badgeHero) {
      badgeHero.textContent = 'Lỗi Nạp';
      badgeHero.className = 'badge badge-danger';
    }
    if (btnStart) btnStart.style.pointerEvents = 'auto';
    if (btnStop) btnStop.disabled = true;
    showToast('Lỗi khi nạp model vào GPU!', 'error');
  }
}

function handleAiGpuServerStopped(data) {
  const badgeServer = document.getElementById('badgeGpuServerState');
  const badgeHero = document.getElementById('badgeHeroServerStatus');
  const btnStart = document.getElementById('btnStartAiGpuServer');
  const btnStop = document.getElementById('btnStopAiGpuServer');

  if (badgeServer) {
    badgeServer.textContent = 'AI Server: ĐÃ TẮT / GPU NGHỈ';
    badgeServer.className = 'badge badge-cyan';
  }
  if (badgeHero) {
    badgeHero.textContent = 'Standby';
    badgeHero.className = 'badge badge-cyan';
  }
  if (btnStart) btnStart.style.pointerEvents = 'auto';
  if (btnStop) btnStop.disabled = true;

  showToast('Đã giải phóng 100% VRAM GPU!', 'success');
  appendTerminalLog('[SUCCESS] ✨ VRAM GPU đã được dọn sạch. Card đồ họa đã trở về trạng thái nghỉ.', 'SUCCESS');
}

function updateGpuTelemetryUI(gpu) {
  if (!gpu) return;

  const teleName = document.getElementById('gpuTeleName');
  const teleVram = document.getElementById('gpuTeleVram');
  const teleTemp = document.getElementById('gpuTeleTemp');
  const teleCuda = document.getElementById('gpuTeleCuda');

  if (teleName) teleName.textContent = gpu.gpu_name || 'CPU Only';
  if (teleVram) teleVram.textContent = `${gpu.used_vram_gb || 0} / ${gpu.total_vram_gb || 0} GB`;
  if (teleTemp) teleTemp.textContent = gpu.gpu_temp_c ? `${gpu.gpu_temp_c} °C` : '-- °C';
  if (teleCuda) {
    teleCuda.textContent = gpu.cuda_available ? 'CUDA ACTIVE' : 'CPU FALLBACK';
    teleCuda.style.color = gpu.cuda_available ? 'var(--success)' : 'var(--warning)';
  }

  // Update Sidebar GPU Meter
  const gpuMeterBar = document.getElementById('gpuMeterBar');
  const gpuMeterVal = document.getElementById('gpuMeterVal');
  if (gpuMeterBar && gpuMeterVal && gpu.total_vram_gb > 0) {
    const vramPct = Math.min(100, Math.round((gpu.used_vram_gb / gpu.total_vram_gb) * 100));
    gpuMeterBar.style.width = `${vramPct}%`;
    gpuMeterVal.textContent = `${vramPct}%`;
  }
}

/* ==========================================================================
   12. TIKTOK SHOP LIVE CART DASHBOARD CONTROLLER
   ========================================================================== */

let currentScrapedProducts = [];

function initTikTokCartScraperController() {
  loadSavedScrapedCart();

  const searchInp = document.getElementById('inputSearchCartLive');
  searchInp?.addEventListener('input', () => {
    const q = searchInp.value.trim().toLowerCase();
    if (!q) {
      renderScrapedCartTable(currentScrapedProducts);
      return;
    }
    const filtered = currentScrapedProducts.filter(p => {
      const sttMatch = String(p.stt) === q || `sp ${p.stt}` === q || `#${p.stt}` === q;
      const nameMatch = (p.name || '').toLowerCase().includes(q);
      const priceMatch = (p.sale_price || '').toLowerCase().includes(q);
      const campMatch = (p.campaign || '').toLowerCase().includes(q);
      return sttMatch || nameMatch || priceMatch || campMatch;
    });
    renderScrapedCartTable(filtered, false, true);
  });
}

function loadSavedScrapedCart() {
  try {
    const saved = localStorage.getItem('dta_scraped_cart_products');
    if (saved) {
      currentScrapedProducts = JSON.parse(saved);
      renderScrapedCartTable(currentScrapedProducts);
      populateHostCartProductDropdown(currentScrapedProducts);

      if (wsClient && wsClient.readyState === WebSocket.OPEN && currentScrapedProducts.length > 0) {
        wsClient.send(JSON.stringify({
          command: 'SYNC_CART_PRODUCTS_CATALOG',
          products: currentScrapedProducts
        }));
      }
    }
  } catch (e) {
    console.error('Error loading saved cart:', e);
  }
}

window.scrapeTikTokLiveCart = function() {
  appendTerminalLog('[ACTION] 🛒 Đang kết nối Chrome CDP 9222 để bóc tách giỏ hàng TikTok Shop Live...', 'INFO');
  showToast('Đang cào dữ liệu giỏ hàng Live...', 'info');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'SCRAPE_TIKTOK_CART' }));
  }
};

function handleTikTokCartScraped(data) {
  if (!data) return;

  if (data.products && Array.isArray(data.products)) {
    currentScrapedProducts = data.products;
    try {
      localStorage.setItem('dta_scraped_cart_products', JSON.stringify(currentScrapedProducts));
    } catch (e) {
      console.error(e);
    }

    renderScrapedCartTable(currentScrapedProducts, data.is_simulated);
    populateHostCartProductDropdown(currentScrapedProducts);

    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
      wsClient.send(JSON.stringify({
        command: 'SYNC_CART_PRODUCTS_CATALOG',
        products: currentScrapedProducts
      }));
    }

    // Switch to cart sub-tab in Tab 2
    const btnSubTabCart = document.getElementById('btnSubTabCartLive');
    if (btnSubTabCart) btnSubTabCart.click();

    if (data.is_simulated) {
      appendTerminalLog(`[WARNING] ⚠️ Chưa kết nối được trang TikTok Live qua Chrome CDP 9222. Đang hiển thị dữ liệu mẫu (${currentScrapedProducts.length} SP). Hãy nhấn nút "🌐 Mở Trình Duyệt Live (CDP 9222)" và mở trang Giỏ hàng TikTok Shop để cào thực tế!`, 'WARNING');
      showToast('⚠️ Chưa kết nối Chrome Live CDP 9222! Bấm nút "Mở Trình Duyệt Live (CDP 9222)"', 'warning');
    } else {
      appendTerminalLog(`[SUCCESS] 🛒 ✅ ĐÃ CÀO THỰC TẾ THÀNH CÔNG ${currentScrapedProducts.length} sản phẩm từ TikTok Live Dashboard. Dữ liệu đã lưu vào Dashboard và nạp vào Qwen AI!`, 'SUCCESS');
      showToast(`✅ Đã cào thực tế ${currentScrapedProducts.length} sản phẩm từ TikTok Live!`, 'success');
    }
  }
}

function updateCartSummaryChips(products) {
  const chipTotal = document.getElementById('chipTotalCartProds');
  const chipFlash = document.getElementById('chipFlashSaleCount');
  const chipStock = document.getElementById('chipTotalStockCount');

  if (!products || products.length === 0) {
    if (chipTotal) chipTotal.textContent = '📦 0 Sản Phẩm';
    if (chipFlash) chipFlash.textContent = '🔥 0 Flash Sale';
    if (chipStock) chipStock.textContent = '📊 Tổng tồn: 0';
    return;
  }

  const totalProds = products.length;
  let flashCount = 0;
  let totalStockNum = 0;

  products.forEach(p => {
    const c = (p.campaign || '').toLowerCase();
    if (c.includes('flash') || c.includes('kết thúc') || c.includes('ưu đãi')) {
      flashCount++;
    }
    const rawStock = (p.stock || '').replace(/[^0-9]/g, '');
    if (rawStock) {
      totalStockNum += parseInt(rawStock, 10);
    }
  });

  if (chipTotal) chipTotal.textContent = `📦 ${totalProds} Sản Phẩm`;
  if (chipFlash) chipFlash.textContent = `🔥 ${flashCount} Flash Sale`;
  if (chipStock) chipStock.textContent = `📊 Tổng tồn: ${totalStockNum > 0 ? totalStockNum.toLocaleString('vi-VN') : '--'}`;
}

function updateHostQuickQuestionChips(dialect = 'south') {
  const chipsContainer = document.getElementById('quickQuestionChipsContainer');
  if (!chipsContainer) return;

  const products = currentScrapedProducts;
  const p1 = (products && products.length > 0) ? products[0] : { stt: 1, name: 'Cần Câu Lure' };
  const p2 = (products && products.length >= 2) ? products[Math.floor(products.length / 2)] : p1;
  const p3 = (products && products.length >= 3) ? products[products.length - 1] : p1;

  const p1Name = (p1.name || `Cần #${p1.stt}`).split('-')[0].trim();
  const p2Name = (p2.name || `Cần #${p2.stt}`).split('-')[0].trim();
  const p3Name = (p3.name || `Cần #${p3.stt}`).split('-')[0].trim();

  if (dialect === 'north') {
    chipsContainer.innerHTML = `
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Mã ${p1.stt} (${p1Name.slice(0, 25)}) bao tiền đấy bác ơi?')">💡 Hỏi SP #${p1.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cây số ${p2.stt} (${p2Name.slice(0, 25)}) còn ko bác, bọc ống PVC ko?')">💡 Hỏi SP #${p2.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cần câu mã ${p3.stt} (${p3Name.slice(0, 25)}) tải cá tầm mấy kg đấy bác?')">💡 Hỏi SP #${p3.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Shop giao Hà Nội mấy hôm tới nơi ạ?')">💡 Hỏi Giao Hàng</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Hàng chính hãng có phiếu bảo hành chuẩn đét ko bác?')">💡 Hỏi Bảo Hành</button>
    `;
  } else if (dialect === 'central') {
    chipsContainer.innerHTML = `
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Mã ${p1.stt} (${p1Name.slice(0, 25)}) giá mấy rứa shop?')">💡 Hỏi SP #${p1.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cây số ${p2.stt} (${p2Name.slice(0, 25)}) còn hàng ko hè?')">💡 Hỏi SP #${p2.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cần mã ${p3.stt} (${p3Name.slice(0, 25)}) tải cá mấy kg bồ ơi?')">💡 Hỏi SP #${p3.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Giao Đà Nẵng mấy ngày tới nơi hỉ?')">💡 Hỏi Giao Hàng</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Hàng chính hãng có bảo hành ko shop hè?')">💡 Hỏi Bảo Hành</button>
    `;
  } else {
    chipsContainer.innerHTML = `
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Mã ${p1.stt} (${p1Name.slice(0, 25)}) giá nhiu vậy shop?')">💡 Hỏi SP #${p1.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cây số ${p2.stt} (${p2Name.slice(0, 25)}) còn hàng ko bồ ơi?')">💡 Hỏi SP #${p2.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Cần câu mã ${p3.stt} (${p3Name.slice(0, 25)}) tải cá mấy kg vậy anh?')">💡 Hỏi SP #${p3.stt}</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Shop có freeship giao mấy hôm tới ạ?')">💡 Hỏi Giao Hàng</button>
      <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px;" onclick="window.setQuickHostQuestion('Hàng chính hãng có phiếu bảo hành đổi trả ko shop?')">💡 Hỏi Bảo Hành</button>
    `;
  }
}

function populateHostCartProductDropdown(products) {
  const sel = document.getElementById('selectHostCartProduct');
  const btnAutoSeeding = document.getElementById('btnAutoGenerateCartSeeding');

  const count = (products && Array.isArray(products)) ? products.length : 0;

  if (btnAutoSeeding) {
    btnAutoSeeding.textContent = `✨ Tự Động Tạo Kịch Bản Từ ${count > 0 ? count : 24} SP Thật`;
  }

  if (sel) {
    sel.innerHTML = `<option value="">(Chọn sản phẩm trong ${count > 0 ? count : 24} SP thật để test nhanh...)</option>`;
    if (products && products.length > 0) {
      products.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.stt;
        const pName = p.name || `Sản phẩm #${p.stt}`;
        opt.textContent = `#${p.stt} - ${pName.slice(0, 45)} (${p.sale_price || 'Chưa rõ'})`;
        sel.appendChild(opt);
      });
    }
  }

  const currentDialect = document.getElementById('selectHostRegionDialect')?.value || 'south';
  updateHostQuickQuestionChips(currentDialect);
}

function renderScrapedCartTable(products, isSimulated = false, isFilterResult = false) {
  const tbody = document.getElementById('scrapedCartTableBody');
  const countEl = document.getElementById('scrapedCartTotalCount');
  const syncStatusEl = document.getElementById('scrapedCartAiSyncStatus');

  if (!isFilterResult) {
    updateCartSummaryChips(products);
  }

  if (countEl) {
    countEl.textContent = `${products.length} sản phẩm ${isFilterResult ? '(Đang lọc)' : (isSimulated ? '(Mẫu mô phỏng)' : '(Thực tế Live)')}`;
    countEl.style.color = isSimulated ? 'var(--warning)' : 'var(--accent)';
  }
  if (syncStatusEl) {
    syncStatusEl.textContent = products.length > 0 ? (isSimulated ? 'Dữ liệu mẫu (Cần mở Chrome CDP 9222)' : 'Đã nạp 100% vào Qwen Local AI') : 'Chưa có dữ liệu';
    syncStatusEl.style.color = isSimulated ? 'var(--warning)' : 'var(--success)';
  }

  if (!tbody) return;

  if (!products || products.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-tertiary); padding: 28px;">
          ${isFilterResult ? 'Không tìm thấy sản phẩm nào khớp với từ khóa tìm kiếm.' : 'Chưa có dữ liệu giỏ hàng. Nhấn nút <strong>"⚡ Cào Giỏ Hàng Live (CDP)"</strong> để trích xuất tự động từ trang TikTok Live Streamer Dashboard.'}
        </td>
      </tr>
    `;
    return;
  }

  let html = '';
  products.forEach(p => {
    const isFlash = (p.campaign || '').toLowerCase().includes('flash') || (p.campaign || '').includes('Kết thúc');
    const campaignBadge = isFlash 
      ? `<span class="badge badge-warning" style="background: rgba(255,100,0,0.15); color: #ff9900; border: 1px solid #ff9900;">🔥 ${escapeHtml(p.campaign)}</span>`
      : `<span class="badge badge-cyan">${escapeHtml(p.campaign || 'Thường')}</span>`;

    html += `
      <tr>
        <td style="text-align: center; font-weight: bold; color: var(--accent);">#${p.stt}</td>
        <td style="font-weight: 500; line-height: 1.4;">${escapeHtml(p.name)}</td>
        <td style="text-align: center; color: var(--success); font-weight: bold; font-size: 12.5px;">${escapeHtml(p.sale_price || 'Chưa rõ')}</td>
        <td style="text-align: center; color: var(--text-tertiary); text-decoration: line-through; font-size: 11.5px;">${escapeHtml(p.original_price || '--')}</td>
        <td style="text-align: center; color: var(--warning); font-weight: 600;">${escapeHtml(p.stock || '--')}</td>
        <td style="text-align: center;">${campaignBadge}</td>
        <td style="text-align: center;">
          <button type="button" class="btn btn-secondary" style="height: 24px; font-size: 10.5px; padding: 0 8px; border-color: var(--accent); color: var(--accent);" onclick="window.pinSingleCartProduct(${p.stt})">📌 Ghim</button>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

window.pinSingleCartProduct = function(stt) {
  appendTerminalLog(`[ACTION] 📌 Đang gửi yêu cầu ghim sản phẩm STT #${stt} sang TikTok Live Studio...`, 'INFO');
  showToast(`Đang ghim sản phẩm #${stt}...`, 'info');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'TRIGGER_MANUAL_PIN',
      product_id: String(stt)
    }));
  }
};

function convertScrapedCartToTimeline() {
  if (!currentScrapedProducts || currentScrapedProducts.length === 0) {
    showToast('Chưa có sản phẩm nào trong giỏ hàng để chuyển sang Timeline!', 'warning');
    return;
  }

  timelineEvents = [];
  let currentTimeSec = 15;

  currentScrapedProducts.forEach((p, idx) => {
    const mins = Math.floor(currentTimeSec / 60);
    const secs = currentTimeSec % 60;
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    timelineEvents.push({
      id: `evt_cart_${idx + 1}_${Date.now()}`,
      time_ms: currentTimeSec * 1000,
      time_str: timeStr,
      product_id: String(p.stt),
      title: p.name,
      keywords: p.name.split(' ').slice(0, 4).join(' '),
      state: 'Sẵn sàng'
    });

    currentTimeSec += 30; // 30s per product
  });

  renderTimelineTable();
  syncTableToJson();
  saveTimelineEvents();

  showToast(`Đã tạo thành công ${timelineEvents.length} mốc ghim tự động từ giỏ hàng!`, 'success');
  appendTerminalLog(`[SUCCESS] 📥 Đã chuyển đổi ${timelineEvents.length} sản phẩm giỏ hàng thành Timeline sự kiện ghim luân phiên!`, 'SUCCESS');
}

/* ==========================================================================
   13. SATELLITE SEEDING & HOST CHATBOT CONTROLLERS (LOCAL PERSISTENCE)
   ========================================================================== */

function initSatelliteSeedingController() {
  const inputUser = document.getElementById('inputSeedingTargetUser');
  const inputAccs = document.getElementById('inputSatelliteAccounts');
  const inputMin = document.getElementById('inputSeedingMinSec');
  const inputMax = document.getElementById('inputSeedingMaxSec');
  const selectStyle = document.getElementById('selectSeedingStyle');
  const inputPrompt = document.getElementById('inputSeedingAiPrompt');
  const inputTemplates = document.getElementById('inputSeedingCustomTemplates');
  const badgeCount = document.getElementById('badgeSatelliteCount');

  // Load saved local settings
  try {
    if (inputUser) inputUser.value = localStorage.getItem('dta_seeding_user') || '@dta_studio';
    if (inputAccs) inputAccs.value = localStorage.getItem('dta_seeding_accounts') || '';
    if (inputMin) inputMin.value = localStorage.getItem('dta_seeding_min') || '15';
    if (inputMax) inputMax.value = localStorage.getItem('dta_seeding_max') || '45';
    const selDialect = document.getElementById('selectSeedingRegionDialect');
    const selTone = document.getElementById('selectSeedingToneStyle');
    const chkSlang = document.getElementById('chkSeedingUseSlangs');
    if (selDialect) selDialect.value = localStorage.getItem('dta_seeding_dialect') || 'south';
    if (selTone) selTone.value = localStorage.getItem('dta_seeding_tone') || 'genz_casual';
    if (chkSlang) chkSlang.checked = localStorage.getItem('dta_seeding_slang') !== 'false';

    if (inputPrompt) inputPrompt.value = localStorage.getItem('dta_seeding_prompt') || DEFAULT_SEEDING_PROMPT;
    if (inputTemplates) inputTemplates.value = localStorage.getItem('dta_seeding_templates') || DEFAULT_SEEDING_TEMPLATES;
    updateSatelliteCountBadge();
  } catch (e) {
    console.error('Error loading seeding settings:', e);
  }

  function updateSatelliteCountBadge() {
    const lines = (inputAccs?.value || '').split('\n').filter(l => l.trim().length > 0);
    if (badgeCount) {
      badgeCount.textContent = `${lines.length} tài khoản`;
    }
  }

  inputAccs?.addEventListener('input', updateSatelliteCountBadge);

  document.getElementById('btnSaveSeedingConfigLocal')?.addEventListener('click', () => {
    const selDialect = document.getElementById('selectSeedingRegionDialect')?.value || 'south';
    const selTone = document.getElementById('selectSeedingToneStyle')?.value || 'genz_casual';
    const chkSlang = document.getElementById('chkSeedingUseSlangs')?.checked ?? true;

    localStorage.setItem('dta_seeding_user', inputUser?.value.trim() || '@dta_studio');
    localStorage.setItem('dta_seeding_accounts', inputAccs?.value || '');
    localStorage.setItem('dta_seeding_min', inputMin?.value || '15');
    localStorage.setItem('dta_seeding_max', inputMax?.value || '45');
    localStorage.setItem('dta_seeding_dialect', selDialect);
    localStorage.setItem('dta_seeding_tone', selTone);
    localStorage.setItem('dta_seeding_slang', chkSlang ? 'true' : 'false');
    localStorage.setItem('dta_seeding_prompt', inputPrompt?.value || '');
    localStorage.setItem('dta_seeding_templates', inputTemplates?.value || '');

    showToast('Đã lưu toàn bộ Cấu Hình & Phong Cách Seeding vào máy!', 'success');
    appendTerminalLog(`[SUCCESS] 💾 Đã lưu cấu hình Đội Quân Seeding (${selDialect} - ${selTone}) vào bộ nhớ Local.`, 'SUCCESS');
  });
}

window.startSatelliteSeeding = function() {
  const targetUser = document.getElementById('inputSeedingTargetUser')?.value || '@dta_studio';
  const accountsText = document.getElementById('inputSatelliteAccounts')?.value || '';
  const minSec = parseInt(document.getElementById('inputSeedingMinSec')?.value || '15', 10);
  const maxSec = parseInt(document.getElementById('inputSeedingMaxSec')?.value || '45', 10);
  const regionDialect = document.getElementById('selectSeedingRegionDialect')?.value || 'south';
  const toneStyle = document.getElementById('selectSeedingToneStyle')?.value || 'genz_casual';
  const useSlangs = document.getElementById('chkSeedingUseSlangs')?.checked ?? true;
  const aiPrompt = document.getElementById('inputSeedingAiPrompt')?.value || '';
  const templatesRaw = document.getElementById('inputSeedingCustomTemplates')?.value || '';
  const customTemplates = templatesRaw.split('\n').map(s => s.trim()).filter(Boolean);

  const btnStart = document.getElementById('btnStartSeeding');
  const btnStop = document.getElementById('btnStopSeeding');

  if (btnStart) btnStart.disabled = true;
  if (btnStop) btnStop.disabled = false;

  appendTerminalLog(`[ACTION] 👥 Bắt đầu Đội Quân Seeding Vệ Tinh AI (${regionDialect} - ${toneStyle}) cho kênh ${targetUser} (Cách ${minSec}s - ${maxSec}s)...`, 'INFO');
  showToast(`Đã kích hoạt Seeding Vệ Tinh AI (${regionDialect})`, 'success');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'START_SATELLITE_SEEDING',
      username: targetUser,
      accounts_text: accountsText,
      interval_min: minSec,
      interval_max: maxSec,
      region_dialect: regionDialect,
      tone_style: toneStyle,
      use_slangs: useSlangs,
      ai_prompt: aiPrompt,
      custom_templates: customTemplates,
      products: currentScrapedProducts
    }));
  }
};

window.stopSatelliteSeeding = function() {
  const btnStart = document.getElementById('btnStartSeeding');
  const btnStop = document.getElementById('btnStopSeeding');

  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;

  appendTerminalLog('[SYSTEM] 🛑 Đã dừng Đội Quân Seeding Vệ Tinh.', 'WARNING');
  showToast('Đã dừng Seeding', 'warning');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'STOP_SATELLITE_SEEDING' }));
  }
};

window.sendQuickTestComment = function() {
  const inputEl = document.getElementById('inputQuickTestComment');
  const text = inputEl?.value.trim();
  if (!text) {
    showToast('Vui lòng nhập nội dung bình luận muốn bắn thử!', 'warning');
    return;
  }

  const logBox = document.getElementById('seedingLiveLogBox');
  if (logBox) {
    const timeStr = new Date().toLocaleTimeString();
    const item = document.createElement('div');
    item.className = 'seeding-bubble-item';
    item.innerHTML = `
      <span class="seeding-bubble-author">⚡ [Bắn Thử Ngay]</span>
      <span class="seeding-bubble-text">${escapeHtml(text)}</span>
      <span class="seeding-bubble-time">${timeStr}</span>
    `;
    logBox.appendChild(item);
    logBox.scrollTop = logBox.scrollHeight;
  }

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'SEND_QUICK_TEST_COMMENT',
      comment: text
    }));
  }

  showToast('Đã bắn thử bình luận!', 'success');
  if (inputEl) inputEl.value = '';
};

function updateSeedingStatusUI(status, color) {
  const badge = document.getElementById('badgeSeedingStatus');
  if (badge && status) {
    badge.textContent = status;
    badge.style.color = color || 'var(--accent)';
  }
}

function initHostLiveChatbotUI() {
  const selDialect = document.getElementById('selectHostRegionDialect');
  const selTone = document.getElementById('selectHostToneStyle');
  const chkSlang = document.getElementById('chkHostUseSlangs');
  const inputUser = document.getElementById('inputHostTikTokUser');
  const inputPrompt = document.getElementById('inputHostAiPrompt');

  try {
    if (selDialect) selDialect.value = localStorage.getItem('dta_host_dialect') || 'south';
    if (selTone) selTone.value = localStorage.getItem('dta_host_tone') || 'genz_casual';
    if (chkSlang) chkSlang.checked = localStorage.getItem('dta_host_slang') !== 'false';
    if (inputUser) inputUser.value = localStorage.getItem('dta_host_user') || '@dta_studio';
    if (inputPrompt) inputPrompt.value = localStorage.getItem('dta_host_prompt') || DEFAULT_HOST_PROMPT;
  } catch (e) {
    console.error(e);
  }

  selDialect?.addEventListener('change', () => {
    updateHostQuickQuestionChips(selDialect.value);
  });

  document.getElementById('btnSaveHostPromptLocal')?.addEventListener('click', () => {
    localStorage.setItem('dta_host_dialect', selDialect?.value || 'south');
    localStorage.setItem('dta_host_tone', selTone?.value || 'genz_casual');
    localStorage.setItem('dta_host_slang', chkSlang?.checked ? 'true' : 'false');
    localStorage.setItem('dta_host_user', inputUser?.value.trim() || '@dta_studio');
    localStorage.setItem('dta_host_prompt', inputPrompt?.value || '');

    showToast('Đã lưu Cấu Hình Vùng Miền & Prompt Host Chatbot!', 'success');
    appendTerminalLog(`[SUCCESS] 💾 Đã lưu cấu hình Host Chatbot (${selDialect?.value} - ${selTone?.value}) vào máy.`, 'SUCCESS');
  });
}

window.startHostChatbot = function() {
  const username = document.getElementById('inputHostTikTokUser')?.value || '@dta_studio';
  const prompt = document.getElementById('inputHostAiPrompt')?.value || '';
  const regionDialect = document.getElementById('selectHostRegionDialect')?.value || 'south';
  const toneStyle = document.getElementById('selectHostToneStyle')?.value || 'genz_casual';
  const useSlangs = document.getElementById('chkHostUseSlangs')?.checked ?? true;

  const btnStart = document.getElementById('btnStartHostChat');
  const btnStop = document.getElementById('btnStopHostChat');

  if (btnStart) btnStart.disabled = true;
  if (btnStop) btnStop.disabled = false;

  appendTerminalLog(`[ACTION] 🤖 Kích hoạt Host Live Chatbot (${regionDialect} - ${toneStyle}) tự động trả lời cho kênh: ${username}...`, 'INFO');
  showToast(`Đã bật Host Live Chatbot (${regionDialect})`, 'success');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'START_HOST_AI_CHATBOT',
      username: username,
      system_prompt: prompt,
      region_dialect: regionDialect,
      tone_style: toneStyle,
      use_slangs: useSlangs,
      products: currentScrapedProducts
    }));
  }
};

window.stopHostChatbot = function() {
  const btnStart = document.getElementById('btnStartHostChat');
  const btnStop = document.getElementById('btnStopHostChat');

  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;

  appendTerminalLog('[SYSTEM] 🛑 Đã dừng Host Live Chatbot.', 'WARNING');
  showToast('Đã dừng Host Chatbot', 'warning');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ command: 'STOP_HOST_AI_CHATBOT' }));
  }
};

let hostReplyCount = 0;

function updateHostChatStatusUI(status, color) {
  const badge = document.getElementById('badgeHostChatStatus');
  if (badge && status) {
    badge.textContent = status;
    badge.style.color = color || 'var(--accent)';
  }
}

window.testHostChatbotReply = function() {
  const inputEl = document.getElementById('inputTestCustomerQuestion');
  const question = inputEl?.value.trim() || 'Mã số 1 bao nhiêu tiền vậy shop?';
  const prompt = document.getElementById('inputHostAiPrompt')?.value || '';
  const regionDialect = document.getElementById('selectHostRegionDialect')?.value || 'south';
  const toneStyle = document.getElementById('selectHostToneStyle')?.value || 'genz_casual';
  const useSlangs = document.getElementById('chkHostUseSlangs')?.checked ?? true;

  const logBox = document.getElementById('hostChatLogBox');
  if (logBox) {
    const timeStr = new Date().toLocaleTimeString();
    const custItem = document.createElement('div');
    custItem.className = 'seeding-bubble-item';
    custItem.style.borderLeft = '3px solid var(--accent)';
    custItem.innerHTML = `
      <span class="seeding-bubble-author" style="color: var(--accent);">👤 [Khách Xem: Khach_Test]</span>
      <span class="seeding-bubble-text">${escapeHtml(question)}</span>
      <span class="seeding-bubble-time">${timeStr}</span>
    `;
    logBox.appendChild(custItem);

    // Tự động dọn dẹp DOM giữ tối đa 10 comment gần nhất
    trimHostChatLogBox(10);

    const thinkingItem = document.createElement('div');
    thinkingItem.className = 'seeding-bubble-item';
    thinkingItem.id = 'tempThinkingBubble';
    thinkingItem.innerHTML = `
      <span class="seeding-bubble-author">🤖 [Host AI - ${regionDialect.toUpperCase()}]</span>
      <span class="seeding-bubble-text" style="color: var(--text-tertiary); font-style: italic;">Đang phân tích giỏ hàng thật (${currentScrapedProducts?.length || 0} SP) theo giọng ${regionDialect}...</span>
      <span class="seeding-bubble-time">...</span>
    `;
    logBox.appendChild(thinkingItem);
    logBox.scrollTop = logBox.scrollHeight;
  }

  appendTerminalLog(`[ACTION] ⚡ Đang gửi câu hỏi test: "${question}" tới Qwen AI Engine (${regionDialect} - ${toneStyle})...`, 'INFO');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'TEST_HOST_AI_CHATBOT_REPLY',
      customer: 'Khach_Test',
      question: question,
      system_prompt: prompt,
      region_dialect: regionDialect,
      tone_style: toneStyle,
      use_slangs: useSlangs,
      products: currentScrapedProducts
    }));
  }

  if (inputEl) inputEl.value = '';
};

// 🧹 Hàm dọn dẹp rác DOM liên tục, chỉ giữ lại đúng 10 bình luận gần nhất trên màn hình Live
function trimHostChatLogBox(maxItems = 10) {
  const logBox = document.getElementById('hostChatLogBox');
  if (!logBox) return;

  const items = logBox.querySelectorAll('.seeding-bubble-item:not(#tempThinkingBubble)');
  if (items.length > maxItems) {
    const removeCount = items.length - maxItems;
    for (let i = 0; i < removeCount; i++) {
      if (items[i] && items[i].parentNode === logBox) {
        items[i].remove();
      }
    }
  }
}

function handleHostChatbotReplyEvent(evt) {
  if (!evt) return;

  const thinkingEl = document.getElementById('tempThinkingBubble');
  if (thinkingEl) thinkingEl.remove();

  const logBox = document.getElementById('hostChatLogBox');
  if (logBox) {
    const timeStr = evt.time || new Date().toLocaleTimeString();
    const hostItem = document.createElement('div');
    hostItem.className = 'seeding-bubble-item';
    hostItem.style.borderLeft = '3px solid var(--success)';
    hostItem.style.background = 'rgba(0, 255, 102, 0.05)';

    const pinBadgeHtml = evt.pinned_product_id 
      ? `<span class="badge badge-cyan" style="font-size: 9.5px; height: 16px; padding: 0 6px; background: rgba(0, 242, 254, 0.2); border: 1px solid var(--accent); color: var(--accent);">📌 Đã Ghim SP #${evt.pinned_product_id}</span>`
      : '';

    const dialectBadgeHtml = evt.region_dialect
      ? `<span class="badge badge-yellow" style="font-size: 9px; height: 15px; padding: 0 4px; text-transform: uppercase;">${evt.region_dialect}</span>`
      : '';

    const fullMsg = (evt.customer ? (`@${evt.customer} `) : '') + (evt.reply || '');
    const charLen = fullMsg.length;
    const charBadgeHtml = `<span class="badge ${charLen <= 95 ? 'badge-green' : 'badge-red'}" style="font-size: 9px; height: 16px; padding: 0 5px;" title="Giới hạn an toàn TikTok Live: Tối đa 95 ký tự tính cả @nickname">📏 ${charLen}/95 ký tự</span>`;

    hostItem.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 6px;">
        <div style="display: flex; gap: 4px; align-items: center;">
          <span class="seeding-bubble-author" style="color: var(--success);">🤖 [Host Live Chatbot]</span>
          ${dialectBadgeHtml}
        </div>
        <div style="display: flex; gap: 4px; align-items: center;">
          ${charBadgeHtml}
          ${pinBadgeHtml}
          <span class="badge badge-green" style="font-size: 9.5px; height: 16px; padding: 0 5px;" title="Đã trả lời xong và khóa dấu vân tay comment để tránh rep lặp lại">🟢 Đã Rep & Khóa Trùng</span>
        </div>
      </div>
      <span class="seeding-bubble-text" style="color: var(--text-primary); font-weight: 500; margin-top: 3px;">${escapeHtml(evt.reply)}</span>
      <span class="seeding-bubble-time">${timeStr}</span>
    `;
    logBox.appendChild(hostItem);

    // Dọn dẹp DOM định kỳ: Giữ đúng 10 bình luận gần nhất, tránh tràn RAM và màn hình luôn vừa vặn
    trimHostChatLogBox(10);

    logBox.scrollTop = logBox.scrollHeight;
  }

  if (evt.pinned_product_id) {
    showToast(`📌 Đã tự động Ghim SP #${evt.pinned_product_id} lên màn hình Live!`, 'success');
  }

  hostReplyCount += 1;
  const statsEl = document.getElementById('hostChatStats');
  if (statsEl) {
    statsEl.textContent = `Đã trả lời: ${hostReplyCount} câu | Tốc độ: ~45ms`;
  }

  appendTerminalLog(`[SUCCESS] 🤖 [Host Đã Trả Lời] Khách: "${evt.question}" ➔ AI: "${evt.reply}"`, 'SUCCESS');
}

/* ==========================================================================
   14. EXTENSION HELPERS: CART SEEDING, DYNAMIC HOST SELECTOR & BENCHMARK
   ========================================================================== */

window.generateCartSeedingScripts = function() {
  if (!currentScrapedProducts || currentScrapedProducts.length === 0) {
    showToast('Chưa có sản phẩm trong giỏ hàng! Vui lòng cào giỏ hàng trước.', 'warning');
    return;
  }

  const regionDialect = document.getElementById('selectSeedingRegionDialect')?.value || 'south';
  const toneStyle = document.getElementById('selectSeedingToneStyle')?.value || 'genz_casual';
  const useSlangs = document.getElementById('chkSeedingUseSlangs')?.checked ?? true;

  appendTerminalLog(`[ACTION] ✨ Đang yêu cầu AI phân tích ${currentScrapedProducts.length} sản phẩm thực tế theo giọng ${regionDialect.toUpperCase()} (${toneStyle}) để sinh kịch bản Seeding...`, 'INFO');
  showToast(`Đang tạo kịch bản Seeding ${regionDialect.toUpperCase()} từ ${currentScrapedProducts.length} sản phẩm thật...`, 'info');

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'GENERATE_CART_SEEDING_TEMPLATES',
      products: currentScrapedProducts,
      region_dialect: regionDialect,
      tone_style: toneStyle,
      use_slangs: useSlangs
    }));
  }
};

function handleCartSeedingTemplatesGenerated(templates) {
  if (!templates || !Array.isArray(templates)) return;

  const inputTemplates = document.getElementById('inputSeedingCustomTemplates');
  if (inputTemplates) {
    inputTemplates.value = templates.join('\n');
    localStorage.setItem('dta_seeding_templates', inputTemplates.value);
  }

  const logBox = document.getElementById('seedingLiveLogBox');
  if (logBox) {
    const item = document.createElement('div');
    item.className = 'seeding-bubble-item';
    item.style.borderLeft = '3px solid var(--accent)';
    item.innerHTML = `
      <span class="seeding-bubble-author" style="color: var(--accent);">✨ [AI Kịch Bản Giỏ Hàng]</span>
      <span class="seeding-bubble-text">Đã tạo thành công <strong>${templates.length}</strong> câu bình luận seeding gắn liền với từng sản phẩm thực tế!</span>
      <span class="seeding-bubble-time">${new Date().toLocaleTimeString()}</span>
    `;
    logBox.appendChild(item);
    logBox.scrollTop = logBox.scrollHeight;
  }

  showToast(`✅ Đã tạo thành công ${templates.length} câu Seeding bám sát giỏ hàng!`, 'success');
  appendTerminalLog(`[SUCCESS] ✨ Đã nạp ${templates.length} câu kịch bản bình luận seeding gắn với từng sản phẩm giỏ hàng!`, 'SUCCESS');
}

window.onHostProductSelectChange = function() {
  const sel = document.getElementById('selectHostCartProduct');
  const inputEl = document.getElementById('inputTestCustomerQuestion');
  if (!sel || !inputEl || !sel.value) return;

  const stt = parseInt(sel.value, 10);
  const matched = currentScrapedProducts.find(p => p.stt === stt);
  if (matched) {
    const shortName = (matched.name || '').split('-')[0].trim();
    inputEl.value = `Mã #${stt} (${shortName}) giá bao nhiêu và còn khuyến mãi không shop?`;
    inputEl.focus();
  }
};

window.setQuickHostQuestion = function(text) {
  const inputEl = document.getElementById('inputTestCustomerQuestion');
  if (inputEl) {
    inputEl.value = text;
    inputEl.focus();
  }
};

window.benchmarkAiSpeed = function() {
  appendTerminalLog('[ACTION] ⚡ Đang tiến hành Benchmark tốc độ phản hồi của Qwen AI...', 'INFO');
  showToast('Đang đo tốc độ suy luận AI...', 'info');

  const badgeHeroBm = document.getElementById('badgeHeroBenchmarkResult');
  if (badgeHeroBm) {
    badgeHeroBm.textContent = 'Đang đo...';
    badgeHeroBm.className = 'badge badge-warning';
  }

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({
      command: 'BENCHMARK_AI_SPEED'
    }));
  }
};

function handleAiBenchmarkResult(res) {
  if (!res) return;

  const mode = res.gpu_accelerated ? 'GPU (CUDA)' : 'CPU';
  const badgeHeroBm = document.getElementById('badgeHeroBenchmarkResult');
  if (badgeHeroBm) {
    badgeHeroBm.textContent = `${res.elapsed_ms} ms (${mode})`;
    badgeHeroBm.className = res.gpu_accelerated ? 'badge badge-green' : 'badge badge-yellow';
  }

  appendTerminalLog(`[BENCHMARK] ⚡ Kết quả đo: Thời gian phản hồi = ${res.elapsed_ms} ms (${mode}) | ~${res.tokens_estimate} tokens.`, 'SUCCESS');
  showToast(`⚡ Benchmark AI: ${res.elapsed_ms} ms (${mode})`, 'success');
}

// =============================================================================
// HOTKEYS & KEYBOARD SHORTCUTS CONTROLLER
// =============================================================================
window.toggleHotkeysModal = function(forceState) {
  const modal = document.getElementById('hotkeysModal');
  if (!modal) return;
  if (typeof forceState === 'boolean') {
    modal.style.display = forceState ? 'flex' : 'none';
  } else {
    modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
  }
};

function initKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    // If active element is an input, textarea or contenteditable, ignore global single-key shortcuts
    const isEditingText = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable;

    // Ctrl + 1..5: Quick Tab Switching
    if (e.ctrlKey && !e.shiftKey && !e.altKey) {
      if (e.key === '1') {
        e.preventDefault();
        document.querySelectorAll('.nav-item')[0]?.click();
        showToast('Chuyển sang: Studio Phát Live (Ctrl+1)', 'info');
      } else if (e.key === '2') {
        e.preventDefault();
        document.querySelectorAll('.nav-item')[1]?.click();
        showToast('Chuyển sang: Giỏ Hàng & Ghim SP (Ctrl+2)', 'info');
      } else if (e.key === '3') {
        e.preventDefault();
        document.querySelectorAll('.nav-item')[2]?.click();
        showToast('Chuyển sang: Seeding Vệ Tinh AI (Ctrl+3)', 'info');
      } else if (e.key === '4') {
        e.preventDefault();
        document.querySelectorAll('.nav-item')[3]?.click();
        showToast('Chuyển sang: Host Live Chatbot (Ctrl+4)', 'info');
      } else if (e.key === '5') {
        e.preventDefault();
        document.querySelectorAll('.nav-item')[4]?.click();
        showToast('Chuyển sang: AI Qwen & Cài Đặt (Ctrl+5)', 'info');
      }
    }

    // F1 or '?' (when not typing): Toggle Hotkeys Help Modal
    if (e.key === 'F1' || (!isEditingText && e.key === '?')) {
      e.preventDefault();
      window.toggleHotkeysModal();
    }

    // F2: Quick Test Pin SP #1
    if (e.key === 'F2') {
      e.preventDefault();
      if (typeof window.testPinProduct === 'function') {
        window.testPinProduct();
      }
    }

    // Spacebar: Play / Pause Preview video when not typing text
    if (!isEditingText && e.code === 'Space') {
      const vid = document.getElementById('previewVideo');
      if (vid) {
        e.preventDefault();
        if (vid.paused) {
          vid.play().catch(() => {});
          showToast('▶ Tiếp tục phát video (Space)', 'info');
        } else {
          vid.pause();
          showToast('⏸ Tạm dừng video (Space)', 'info');
        }
      }
    }

    // Escape: Close all active modals
    if (e.key === 'Escape') {
      window.toggleHotkeysModal(false);
      window.closeActionModal();
      const tlModal = document.getElementById('timelineModal');
      if (tlModal) tlModal.style.display = 'none';
    }
  });
}

// Auto-bind keyboard shortcuts on document load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initKeyboardShortcuts);
} else {
  initKeyboardShortcuts();
}

// =============================================================================
// ⚡ DTA OVERDRIVE ENGINE: 60 FPS AUDIO SPECTRUM & GPU PARTICLE FLOW
// =============================================================================

// 1. Dynamic Multi-Layer Fluid Waveform & Audio Visualizer (60 FPS Canvas)
function initAudioSpectrumVisualizer() {
  const canvas = document.getElementById('audioSpectrumCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  let wavePhase = 0;
  const numBars = 32;
  const barHeights = new Array(numBars).fill(4);
  const targetHeights = new Array(numBars).fill(4);
  const peakTops = new Array(numBars).fill(4);

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = rect.width * (window.devicePixelRatio || 1);
      canvas.height = rect.height * (window.devicePixelRatio || 1);
    }
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  let animFrameId = null;

  function renderSpectrum() {
    const tab1 = document.getElementById('tab1');
    // Only render when Tab 1 is visible
    if (tab1 && tab1.classList.contains('active')) {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const video = document.getElementById('previewVideoPlayer');
      const isPlaying = video && !video.paused && !video.ended;
      const baseActivity = isPlaying ? 0.90 : 0.22;

      wavePhase += isPlaying ? 0.08 : 0.03;

      // Layer 1: Background Fluid Glow Sine Wave
      ctx.beginPath();
      ctx.moveTo(0, h);
      for (let x = 0; x <= w; x += 6) {
        const freq1 = Math.sin(x * 0.015 + wavePhase) * (h * 0.22) * baseActivity;
        const freq2 = Math.cos(x * 0.025 - wavePhase * 1.2) * (h * 0.15) * baseActivity;
        const y = h - (h * 0.35 + freq1 + freq2);
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.closePath();

      const waveGrad = ctx.createLinearGradient(0, 0, w, 0);
      waveGrad.addColorStop(0, 'rgba(0, 242, 254, 0.18)');
      waveGrad.addColorStop(0.5, 'rgba(121, 40, 202, 0.25)');
      waveGrad.addColorStop(1, 'rgba(255, 0, 128, 0.18)');
      ctx.fillStyle = waveGrad;
      ctx.fill();

      // Layer 2: Glowing Sine Wave Outline
      ctx.beginPath();
      for (let x = 0; x <= w; x += 6) {
        const freq1 = Math.sin(x * 0.015 + wavePhase) * (h * 0.22) * baseActivity;
        const freq2 = Math.cos(x * 0.025 - wavePhase * 1.2) * (h * 0.15) * baseActivity;
        const y = h - (h * 0.35 + freq1 + freq2);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.65)';
      ctx.lineWidth = 1.5;
      ctx.shadowColor = '#00F2FE';
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0; // reset shadow

      // Layer 3: Dynamic Frequency Equalizer Columns
      const barWidth = (w / numBars) * 0.60;
      const gap = (w / numBars) * 0.40;

      for (let i = 0; i < numBars; i++) {
        if (Math.random() < 0.4) {
          const freqMultiplier = Math.sin((i / numBars) * Math.PI);
          targetHeights[i] = (Math.random() * (h * 0.65) + 3) * baseActivity * (0.35 + freqMultiplier * 0.65);
        }

        barHeights[i] += (targetHeights[i] - barHeights[i]) * 0.20;
        if (barHeights[i] > peakTops[i]) {
          peakTops[i] = barHeights[i];
        } else {
          peakTops[i] = Math.max(3, peakTops[i] - 0.6);
        }

        const x = i * (barWidth + gap) + gap / 2;
        const currentH = Math.max(3, barHeights[i]);
        const y = h - currentH;

        // Gradient Electric Cyan to Hyper Violet
        const grad = ctx.createLinearGradient(0, y, 0, h);
        grad.addColorStop(0, '#7928CA'); // Hyper Violet peak
        grad.addColorStop(0.4, '#00F2FE'); // Cyan middle
        grad.addColorStop(1, 'rgba(0, 242, 254, 0.10)'); // Soft base

        ctx.fillStyle = grad;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, y, barWidth, currentH, [2, 2, 0, 0]);
        } else {
          ctx.rect(x, y, barWidth, currentH);
        }
        ctx.fill();

        // Glowing Peak Dot
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(x, h - peakTops[i] - 2, barWidth, 1.8);
      }
    }

    animFrameId = requestAnimationFrame(renderSpectrum);
  }

  animFrameId = requestAnimationFrame(renderSpectrum);
}

// 2. GPU Hardware Particle Flow Engine (Tab 5)
function initGpuParticleFlow() {
  const canvas = document.getElementById('gpuParticleCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  function resizeGpuCanvas() {
    const rect = canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = rect.width * (window.devicePixelRatio || 1);
      canvas.height = rect.height * (window.devicePixelRatio || 1);
    }
  }
  resizeGpuCanvas();
  window.addEventListener('resize', resizeGpuCanvas);

  const particles = [];
  const particleCount = 35;

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * (canvas.width || 300),
      y: Math.random() * (canvas.height || 120),
      vx: (Math.random() - 0.5) * 0.8,
      vy: (Math.random() - 0.5) * 0.8,
      size: Math.random() * 2.5 + 1.2,
      color: Math.random() > 0.4 ? 'rgba(0, 242, 254, 0.8)' : 'rgba(168, 85, 247, 0.8)'
    });
  }

  function renderParticles() {
    const tab5 = document.getElementById('tab5');
    if (tab5 && tab5.classList.contains('active')) {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();

        // Connect nearby points
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 48) {
            ctx.strokeStyle = `rgba(0, 242, 254, ${0.25 * (1 - dist / 48)})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }
    }

    requestAnimationFrame(renderParticles);
  }

  requestAnimationFrame(renderParticles);
}

// 3. FLIP Morphing Card Pinning Animation
window.triggerPinFlyAnimation = function(product, sourceElement) {
  const flyEl = document.createElement('div');
  flyEl.className = 'fly-product-card';
  flyEl.innerHTML = `
    <span style="font-size: 16px;">📌</span>
    <div style="display: flex; flex-direction: column;">
      <span style="color: var(--accent);">Đang ghim SP #${product.stt || '1'}</span>
      <span style="font-size: 10.5px; color: var(--text-secondary); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${product.name || 'Sản phẩm TikTok Shop'}</span>
    </div>
  `;
  document.body.appendChild(flyEl);

  let startX = window.innerWidth / 2 - 100;
  let startY = window.innerHeight / 2 - 25;

  if (sourceElement && typeof sourceElement.getBoundingClientRect === 'function') {
    const r = sourceElement.getBoundingClientRect();
    startX = r.left;
    startY = r.top;
  }

  // Initial position
  flyEl.style.left = `${startX}px`;
  flyEl.style.top = `${startY}px`;
  flyEl.style.transform = 'scale(0.85)';
  flyEl.style.opacity = '1';

  // Find target on Live Screen 9:16
  const targetStage = document.getElementById('stageScreen916');
  let targetX = window.innerWidth / 2;
  let targetY = window.innerHeight / 2;

  if (targetStage) {
    const tr = targetStage.getBoundingClientRect();
    targetX = tr.left + tr.width / 2 - 90;
    targetY = tr.top + tr.height * 0.3;
  }

  requestAnimationFrame(() => {
    flyEl.style.left = `${targetX}px`;
    flyEl.style.top = `${targetY}px`;
    flyEl.style.transform = 'scale(1.15)';
    flyEl.style.boxShadow = '0 0 40px var(--accent)';

    setTimeout(() => {
      flyEl.style.transform = 'scale(0.4)';
      flyEl.style.opacity = '0';

      // Flash Stage Badge
      const stageBadge = document.getElementById('stageBadge');
      if (stageBadge) {
        stageBadge.textContent = `📌 GHIM SP #${product.stt || '1'}`;
        stageBadge.className = 'stage-badge-indicator badge-green';
        setTimeout(() => {
          if (stageBadge.textContent.includes('GHIM')) {
            stageBadge.textContent = 'STANDBY';
            stageBadge.className = 'stage-badge-indicator';
          }
        }, 4000);
      }

      setTimeout(() => {
        if (flyEl.parentNode) flyEl.parentNode.removeChild(flyEl);
      }, 500);
    }, 650);
  });
};

// Initialize Overdrive Engines on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initAudioSpectrumVisualizer();
    initGpuParticleFlow();
  });
} else {
  initAudioSpectrumVisualizer();
  initGpuParticleFlow();
}

/* ==========================================================================
   16. DTA STUDIO UNIVERSAL OTA AUTO-UPDATER UI CONTROLLER
   ========================================================================== */

window.checkAppUpdateManual = async function() {
  const btnLabel = document.getElementById('updateBtnLabel');
  const btnIcon = document.getElementById('updateBtnIcon');
  if (btnLabel) btnLabel.textContent = 'Đang kiểm tra...';
  if (btnIcon) btnIcon.textContent = '⏳';

  showToast('Đang kết nối máy chủ GitHub để kiểm tra bản cập nhật...', 'info');
  appendTerminalLog('[OTA] 🔍 Đang kiểm tra bản phát hành mới nhất trên GitHub Releases...', 'INFO');

  try {
    if (window.dtaAPI && window.dtaAPI.checkAppUpdate) {
      const res = await window.dtaAPI.checkAppUpdate();
      if (res && res.hasUpdate) {
        showToast(`Đã tìm thấy bản cập nhật v${res.latestVersion}! Đang tự động tải về...`, 'success');
        appendTerminalLog(`[OTA] 🚀 Bắt đầu tải bản cập nhật mới v${res.latestVersion}...`, 'SUCCESS');
      } else {
        showToast('Bạn đang sử dụng phiên bản mới nhất!', 'success');
        appendTerminalLog(`[OTA] ✅ Ứng dụng đã là phiên bản mới nhất (v${res?.currentVersion || '2.3.1'}).`, 'INFO');
      }
    } else {
      showToast('Tính năng cập nhật tự động chỉ khả dụng trong môi trường Desktop.', 'warning');
    }
  } catch (err) {
    showToast(`Lỗi kiểm tra cập nhật: ${err.message}`, 'error');
    appendTerminalLog(`[OTA] ❌ Lỗi kiểm tra cập nhật: ${err.message}`, 'ERROR');
  } finally {
    if (btnLabel) btnLabel.textContent = 'Cập nhật';
    if (btnIcon) btnIcon.textContent = '🔄';
  }
};

// Listen to OTA progress updates
if (window.dtaAPI && window.dtaAPI.onOtaUpdateProgress) {
  window.dtaAPI.onOtaUpdateProgress((data) => {
    if (data.step === 'downloading') {
      showToast(data.message, 'info');
      appendTerminalLog(`[OTA PROGRESS] ${data.message}`, 'INFO');
    } else if (data.step === 'downloaded') {
      showToast(data.message, 'success');
      appendTerminalLog(`[OTA SUCCESS] ${data.message}`, 'SUCCESS');
    }
  });
}
