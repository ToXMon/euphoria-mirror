var App = (function () {
  var state = {
    loading: false,
    error: null,
    data: null
  };

  var els = {};

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

    showLoading();
    refresh();
  }

  function refresh() {
    if (state.loading) return;
    state.loading = true;
    state.error = null;
    setRefreshing(true);
    hideError();

    KronosAPI.fetchAll()
      .then(function (data) {
        state.data = data;
        state.loading = false;
        setRefreshing(false);
        render(data);
        updateTimestamp();
      })
      .catch(function (err) {
        state.loading = false;
        state.error = err.message || 'Failed to fetch data';
        setRefreshing(false);
        showError(state.error);
      });
  }

  function setRefreshing(val) {
    els.refreshBtn.disabled = val;
    els.refreshSpinner.style.display = val ? 'inline-block' : 'none';
    els.refreshText.textContent = val ? 'Refreshing...' : 'Refresh';
  }

  function updateTimestamp() {
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

    var html = '<div class="panel-title"><span class="icon">🔮</span> Kronos Forecast</div>';

    for (var i = 0; i < horizons.length; i++) {
      var h = horizons[i];
      var forecastPrice = pred[h.key] || currentPrice;
      var diff = ((forecastPrice - currentPrice) / currentPrice) * 100;
      var dir = diff > 0.01 ? 'up' : diff < -0.01 ? 'down' : 'flat';
      var arrow = dir === 'up' ? '↑' : dir === 'down' ? '↓' : '→';
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
    var html = '<div class="panel-title"><span class="icon">🔮</span> Kronos Forecast</div>';
    for (var i = 0; i < 3; i++) {
      html += '<div class="forecast-item">' +
        '<div class="skeleton skeleton-line" style="width:30%"></div>' +
        '<div class="skeleton skeleton-line" style="width:40%"></div>' +
      '</div>';
    }
    container.innerHTML = html;
  }

  function showError(msg) {
    if (els.errorState) {
      els.errorState.innerHTML =
        '<div class="error-state">' +
          '<div class="error-icon">⚠️</div>' +
          '<div class="error-message">' + escapeHtml(msg) + '</div>' +
          '<button class="error-retry" id="error-retry" onclick="App.retry()">Retry</button>' +
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
