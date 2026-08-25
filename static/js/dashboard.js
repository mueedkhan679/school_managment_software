/* Teacher QR Check-in: live polling, auto-refresh, toast notifications.
 *
 * The dashboard renders a compact Teacher QR Check-in card. This script polls
 * the lightweight latest-scan API every few seconds and, when a brand-new QR
 * check-in is detected:
 *   - refreshes both the mini and large QR images (cache-busted),
 *   - flashes a toast ("Teacher [Name] checked in at [time]"),
 *   - updates the live present counter and the Today's Attendance tile.
 */
(function () {
  'use strict';

  var POLL_INTERVAL = 4000; // every 4 seconds
  var endpoints = [
    '/api/v1/teacher/attendance/latest-scan/',
    '/api/v1/teachers/attendance/latest-scan/',
  ];
  var endpointIndex = 0;
  var lastScanId = null;
  var toastTimer = null;

  function qrcUrl() {
    return window.DASHBOARD_QR_URL || '/teachers/attendance/qr.png';
  }

  function refreshQrImages() {
    ['qrImgMini', 'qrImgLarge'].forEach(function (id) {
      var img = document.getElementById(id);
      if (img) {
        img.src = qrcUrl() + '?t=' + Date.now();
      }
    });
  }

  function showToast(message) {
    var existing = document.getElementById('qrToast');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.id = 'qrToast';
    toast.textContent = message;
    toast.style.cssText =
      'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);' +
      'z-index:1100;background:#16a34a;color:#fff;padding:12px 20px;' +
      'border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.3);' +
      'font-size:14px;font-weight:600;max-width:90vw;';
    document.body.appendChild(toast);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.remove(); }, 4000);
  }

  function updatePresentCount(source) {
    var present = source !== null && source !== undefined
      ? source.present : null;
    var slot = document.getElementById('qrPresentCount');
    if (slot && present !== null) slot.textContent = present;
    var modal = document.getElementById('qrModalPresent');
    if (modal && present !== null) {
      modal.textContent = present + ' present';
    }
  }

  function updateTodayTile(pct) {
    var tile = document.getElementById('tileTodayPct');
    if (tile && pct !== null && pct !== undefined) {
      tile.textContent = pct + '%';
    }
  }

  function poll() {
    var url = endpoints[endpointIndex % endpoints.length];
    endpointIndex++;
    fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || data.status !== 'success' || !data.payload) return;
        var latest = data.payload.latest;
        if (latest && latest.source === 'QR' && latest.id !== lastScanId) {
          lastScanId = latest.id;
          refreshQrImages();
          if (latest.name && latest.label) {
            showToast('Teacher ' + latest.name + ' checked in at ' + latest.label);
          }
        }
        var stats = data.payload.teacher_stats;
        updatePresentCount(stats);
        var st = data.payload.student_today;
        updateTodayTile(st ? st.percentage : null);
      })
      .catch(function () { /* transient network errors are ignored */ });
  }

  window.DashboardQR = {
    refresh: refreshQrImages,
    expand: function () {
      var overlay = document.getElementById('qrExpandOverlay');
      if (overlay) overlay.style.display = 'flex';
    },
    close: function () {
      var overlay = document.getElementById('qrExpandOverlay');
      if (overlay) overlay.style.display = 'none';
    },
  };

  // Kick off immediately and keep polling.
  poll();
  setInterval(poll, POLL_INTERVAL);
})();
