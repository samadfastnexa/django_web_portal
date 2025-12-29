(function () {
  if (window.__salesOrderLoaderInjected) return;
  window.__salesOrderLoaderInjected = true;

  function createOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'salesorder-loading-overlay active';
    overlay.innerHTML = [
      '<div class="salesorder-loading-card">',
      '  <div class="salesorder-spinner" aria-hidden="true"></div>',
      '  <div class="salesorder-loading-title">Loading Sales Order…</div>',
      '  <div class="salesorder-loading-sub">Preparing form and data</div>',
      '</div>'
    ].join('');
    document.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay() {
    if (!window.__salesOrderOverlay) {
      window.__salesOrderOverlay = createOverlay();
    }
    window.__salesOrderOverlay.classList.add('active');
  }

  function hideOverlay() {
    if (window.__salesOrderOverlay) {
      window.__salesOrderOverlay.classList.remove('active');
    }
  }

  // Show early on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showOverlay);
  } else {
    showOverlay();
  }

  // Hide once full page (assets/forms) loaded
  window.addEventListener('load', function () {
    setTimeout(hideOverlay, 100);
  });

  // Simplified and faster form readiness detection
  function isFormFullyReady() {
    const form = document.querySelector('form');
    if (!form || form.offsetHeight === 0) return false;
    
    // Just check if form has some visible content
    const visibleElements = form.querySelectorAll('*:not([style*="display: none"]):not([hidden])');
    if (visibleElements.length < 5) return false;
    
    return true;
  }

  // Extended safety timeout
  let safetyTimeout = setTimeout(hideOverlay, 20000);

  // Very frequent checks (every 30ms) for instant response
  let checkInterval = setInterval(function () {
    if (isFormFullyReady()) {
      clearInterval(checkInterval);
      clearTimeout(safetyTimeout);
      hideOverlay();
    }
  }, 30);

  // Re-show overlay when navigating to a Sales Order entry from list or toolbars
  function bindLinkLoading(selector) {
    document.querySelectorAll(selector).forEach(function (el) {
      if (el.__salesOrderLoaderBound) return;
      el.__salesOrderLoaderBound = true;
      el.addEventListener('click', function () {
        clearInterval(checkInterval);
        clearTimeout(safetyTimeout);
        showOverlay();
        // Reset timers for new page load
        safetyTimeout = setTimeout(hideOverlay, 20000);
        checkInterval = setInterval(function () {
          if (isFormFullyReady()) {
            clearInterval(checkInterval);
            clearTimeout(safetyTimeout);
            hideOverlay();
          }
        }, 30);
      });
    });
  }

  function bindFormLoading(selector) {
    document.querySelectorAll(selector).forEach(function (form) {
      if (form.__salesOrderLoaderBound) return;
      form.__salesOrderLoaderBound = true;
      form.addEventListener('submit', function () {
        clearInterval(checkInterval);
        clearTimeout(safetyTimeout);
        showOverlay();
        // Reset timers for new page load
        safetyTimeout = setTimeout(hideOverlay, 20000);
        checkInterval = setInterval(function () {
          if (isFormFullyReady()) {
            clearInterval(checkInterval);
            clearTimeout(safetyTimeout);
            hideOverlay();
          }
        }, 30);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindLinkLoading('.results a'); // changelist rows
    bindLinkLoading('.object-tools a'); // add button
    bindLinkLoading('.paginator a'); // pagination
    bindFormLoading('form'); // change/add form submits
  });
})();