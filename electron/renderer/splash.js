// DTA AutoLive v1.1.0 - Real Gatekeeper Splash Screen Controller

document.addEventListener('DOMContentLoaded', () => {
  const progressBar = document.getElementById('progressBar');
  const statusText = document.getElementById('statusText');

  if (window.dtaAPI && window.dtaAPI.onSplashStatus) {
    window.dtaAPI.onSplashStatus((data) => {
      if (progressBar && data.percent !== undefined) {
        progressBar.style.width = data.percent + '%';
      }
      if (statusText && data.text) {
        statusText.textContent = data.text;
      }
    });
  } else {
    // Fallback animation
    let pct = 20;
    const interval = setInterval(() => {
      pct += 20;
      if (progressBar) progressBar.style.width = pct + '%';
      if (pct >= 100) clearInterval(interval);
    }, 400);
  }
});
