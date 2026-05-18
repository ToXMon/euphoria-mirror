var App = (function () {
  var state = {
    loading: false,
    error: null,
    data: null,
    hasEverLoaded: false,
    refreshAttempts: 0
  };

  var AUTO_REFRESH_MS = 2 * 60 * 1000; // 2 minutes
  var els = {};
  var refreshTimer = null;

  function $(id) { return document.getElementById(id); }

  function init() {
    els.refreshBtn = $('refresh-btn');
    els.refreshSpinner = $('refresh-spinner');
    els.refreshText = $('refresh-text');
    els.lastUpdated = $('last-updated');
    els.priceValue = $('price-value');
    els.priceChange = $('price-change');
    els.zoneGrid = $('zone-grid');
    els.edgeScore = $('edge-score');
    els.signalsPanel = $('signals-panel');
    els.forecastPanel = $('forecast-panel');
    els.errorState = $('error-state');
    els.appContainer = $('app-container');

    els.refreshBtn.addEventListener('click', function () {
      refresh();
    });

    var retryBtn = $('error-retry');
    if (retryBtn) {
      retryBtn.addEventListener('click', function () {
        refresh();
      });
    }

    // Initial load - use cached data + background refresh
    loadWithCache();
  }

  function loadWithCache() {
    var result = KronosAPI.fetchAllCached();

    // Phase 1: Show cached data immediately if available
    var cachedPred = result.prediction.data;
    var cachedSig = result.signals.data;

    if (cachedPred || cachedSig) {
      render({
        prediction: cachedPred,
        signals: cachedSig
      });
      updateTimestamp('Cached data');
      state.hasEverLoaded = true;

      // Show "refreshing" indicator
      if (els.lastUpdated) {
        els.lastUpdated.textContent = 'Cached — refreshing...';
      }
    } else {
      // No cache - show loading skeleton
      showLoading();
      setRefreshing(true);
      els.lastUpdated.textContent = 'Connecting to server (high-latency mode)...';
    }

    // Phase 2: Wait for fresh data
    result.allSettled.then(function (fresh) {
      state.loading = false;
      setRefreshing(false);

      var hasFreshData = fresh.prediction || fresh.signals;

      if (hasFreshData) {
        render({
          prediction: fresh.prediction || cachedPred,
          signals: fresh.signals || cachedSig
        });
        state.hasEverLoaded = true;
        state.error = null;
        hideError();
        updateTimestamp();

        // Show partial failure warnings
        var warnings = [];
        if (fresh.predictionError && !fresh.prediction) warnings.push('Prediction data unavailable');
        if (fresh.signalsError && !fresh.signals) warnings.push('Signal data unavailable');
        if (warnings.length > 0) {
          showWarning(warnings.join('. ') + ' — showing cached data');
        }
      } else if (!cachedPred && !cachedSig) {
        // No cache AND no fresh data
        state.error = fresh.predictionError
          ? fresh.predictionError.message
          : 'Server unreachable. Check your connection and try again.';
        showError(state.error);
      }
      // If we had cache but fresh failed, keep showing cached data (already rendered)

      scheduleAutoRefresh();
    });
  }

  function refresh() {
    if (state.loading) return;
    state.loading = true;
    state.error = null;
    setRefreshing(true);
    hideError();
    hideWarning();

    if (els.lastUpdated) {
      els.lastUpdated.textContent = 'Refreshing...';
    }

    KronosAPI.fetchAll()
      .then(function (data) {
        state.data = data;
        state.loading = false;
        state.hasEverLoaded = true;
        setRefreshing(false);
        render(data);
        updateTimestamp();

        if (data._errors && data._errors.length > 0) {
          showWarning('Partial data: ' + data._errors.join('; '));
        }

        scheduleAutoRefresh();
      })
      .catch(function (err) {
        state.loading = false;
        state.error = err.message || 'Failed to fetch data';
        setRefreshing(false);

        // Only show full error if we've never loaded data
        if (!state.hasEverLoaded) {
          showError(state.error);
        } else {
          // We have data already - show non-blocking warning
          showWarning('Refresh failed: ' + state.error + ' — showing last known data');
        }
      });
  }

  function scheduleAutoRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(function () {
      refresh();
    }, AUTO_REFRESH_MS);
  }

  function setRefreshing(val) {
    els.refreshBtn.disabled = val;
    els.refreshSpinner.style.display = val ? 'inline-block' : 'none';
    els.refreshText.textContent = val ? 'Refreshing...' : 'Refresh';
  }

  function updateTimestamp(label) {
    if (label) {
      els.lastUpdated.textContent = label;
      return;
    }
    var now = new Date();
    var h = String(now.getHours()).padStart(2, '0');
    var m = String(now.getMinutes()).padStart(2, '0');
    var s = String(now.getSeconds()).padStart(2, '0');
    els.lastUpdated.textContent = 'Updated ' + h + ':' + m + ':' + s;
  }

  function showLoading() {
    if (els.priceValue) els.priceValue.textContent = '---';
    if (els.priceChange) els.priceChange.textContent = '';
    if (els.zoneGrid) ZoneGrid.renderSkeleton(els.zoneGrid);
    if (els.edgeScore) EdgeScore.renderSkeleton(els.edgeScore);
    if (els.signalsPanel) Signals.renderSkeleton(els.signalsPanel);
    if (els.forecastPanel) renderForecastSkeleton(els.forecastPanel);
  }

  function render(data) {
    var pred = data.prediction || {};
    var sig = data.signals || {};
    var price = pred.current_price || pred.eth_price || 0;
    var change = pred.price_change_24h || 0;
    var edgeScore = pred.edge_score || sig.edge_score || 62;
    var direction = pred.direction || (change >= 0 ? 'up' : 'down');

    renderPrice(price, change);
    ZoneGrid.render(els.zoneGrid, price, pred, edgeScore);
    EdgeScore.render(els.edgeScore, edgeScore, direction);
    Signals.render(els.signalsPanel, sig.sources || sig);
    renderForecast(els.forecastPanel, price, pred);
  }

  function renderPrice(price, change) {
    els.priceValue.textContent = formatUSD(price);

    var pct = change.toFixed(2);
    var sign = change >= 0 ? '+' : '';
    els.priceChange.textContent = sign + pct + '% (24h)';

    els.priceChange.className = 'price-change ' +
      (change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral');
  }

  function renderForecast(container, currentPrice, pred) {
    var horizons = [
      { label: '5 min', key: 'predicted_5m' },
      { label: '15 min', key: 'predicted_15m' },
      { label: '1 hour', key: 'predicted_1h' }
    ];

    var html = '<div class="panel-title"><span class="icon">&#x1F52E;</span> Kronos Forecast</div>';

    for (var i = 0; i < horizons.length; i++) {
      var h = horizons[i];
      var forecastPrice = pred[h.key] || currentPrice;
      var diff = ((forecastPrice - currentPrice) / currentPrice) * 100;
      var dir = diff > 0.01 ? 'up' : diff < -0.01 ? 'down' : 'flat';
      var arrow = dir === 'up' ? '\u2191' : dir === 'down' ? '\u2193' : '\u2192';
      var changeStr = (diff >= 0 ? '+' : '') + diff.toFixed(2) + '%';

      html += '<div class="forecast-item">' +
        '<span class="forecast-horizon">' + h.label + '</span>' +
        '<div class="forecast-value">' +
          '<span class="forecast-price">' + formatUSD(forecastPrice) + '</span>' +
          '<span class="forecast-arrow ' + dir + '">' + arrow + '</span>' +
          '<span class="forecast-change ' + dir + '">' + changeStr + '</span>' +
        '</div>' +
      '</div>';
    }

    container.innerHTML = html;
  }

  function renderForecastSkeleton(container) {
    var html = '<div class="panel-title"><span class="icon">&#x1F52E;</span> Kronos Forecast</div>';
    for (var i = 0; i < 3; i++) {
      html += '<div class="forecast-item">' +
        '<div class="skeleton skeleton-line" style="width:30%"></div>' +
        '<div class="skeleton skeleton-line" style="width:40%"></div>' +
      '</div>';
    }
    container.innerHTML = html;
  }

  function showWarning(msg) {
    var existing = document.getElementById('warning-banner');
    if (existing) existing.remove();

    var banner = document.createElement('div');
    banner.id = 'warning-banner';
    banner.setAttribute('role', 'status');
    banner.style.cssText = 'background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);' +
      'color:#f59e0b;padding:8px 16px;border-radius:8px;font-size:13px;margin:8px 0;text-align:center;';
    banner.textContent = msg;

    if (els.appContainer) {
      els.appContainer.insertBefore(banner, els.appContainer.firstChild);
    }

    // Auto-dismiss after 10s
    setTimeout(function () {
      if (banner.parentNode) banner.remove();
    }, 10000);
  }

  function hideWarning() {
    var existing = document.getElementById('warning-banner');
    if (existing) existing.remove();
  }

  function showError(msg) {
    if (els.errorState) {
      els.errorState.innerHTML =
        '<div class="error-state">' +
          '<div class="error-icon">\u26A0\uFE0F</div>' +
          '<div class="error-message">' + escapeHtml(msg) + '</div>' +
          '<div class="error-hint" style="color:var(--text-muted);font-size:13px;margin-top:8px;">' +
            'The server is in Australia and may be slow from your location. ' +
            'Data will load automatically when available.' +
          '</div>' +
          '<button class="error-retry" id="error-retry" onclick="App.retry()">Retry Now</button>' +
        '</div>';
      els.errorState.style.display = 'block';
    }
  }

  function hideError() {
    if (els.errorState) {
      els.errorState.style.display = 'none';
    }
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function formatUSD(val) {
    return '$' + Number(val).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  return {
    init: init,
    retry: refresh
  };
})();

document.addEventListener('DOMContentLoaded', function () {
  App.init();
});
