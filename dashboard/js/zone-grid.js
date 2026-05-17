var ZoneGrid = (function () {
  var ZONES_PER_SIDE = 5;
  var ZONE_WIDTH_PCT = 1.0;

  function classify(score) {
    if (score >= 70) return 'recommended';
    if (score >= 40) return 'caution';
    return 'avoid';
  }

  function scoreColor(score) {
    if (score >= 70) return 'var(--accent-green)';
    if (score >= 40) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  }

  function directionArrow(direction) {
    if (direction === 'up') return '↑';
    if (direction === 'down') return '↓';
    return '→';
  }

  function formatPrice(val) {
    return '$' + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function computeZones(currentPrice, prediction, overallEdge) {
    var step = currentPrice * (ZONE_WIDTH_PCT / 100);
    var zones = [];
    var forecastDir = 'flat';
    var forecastPrice = currentPrice;

    if (prediction && prediction.predicted_price) {
      forecastPrice = prediction.predicted_price;
      forecastDir = forecastPrice > currentPrice * 1.0005 ? 'up' : forecastPrice < currentPrice * 0.9995 ? 'down' : 'flat';
    }

    for (var i = ZONES_PER_SIDE; i >= 1; i--) {
      var low = currentPrice + step * (i - 1);
      var high = currentPrice + step * i;
      var dist = i;
      var dir = 'up';
      var dirBonus = dir === forecastDir ? 10 : dir !== 'flat' ? -5 : 0;
      var score = Math.max(0, Math.min(100, (overallEdge || 50) - dist * 8 + dirBonus));

      zones.push({
        id: 'plus' + i,
        label: '+' + i + '%',
        low: low,
        high: high,
        direction: dir,
        score: score,
        cls: classify(score)
      });
    }

    for (var j = 1; j <= ZONES_PER_SIDE; j++) {
      var lowB = currentPrice - step * j;
      var highB = currentPrice - step * (j - 1);
      var distB = j;
      var dirB = 'down';
      var dirBonusB = dirB === forecastDir ? 10 : dirB !== 'flat' ? -5 : 0;
      var scoreB = Math.max(0, Math.min(100, (overallEdge || 50) - distB * 8 + dirBonusB));

      zones.push({
        id: 'minus' + j,
        label: '-' + j + '%',
        low: lowB,
        high: highB,
        direction: dirB,
        score: scoreB,
        cls: classify(scoreB)
      });
    }

    return zones;
  }

  function renderZone(zone) {
    var badgeHtml = '';
    if (zone.cls === 'recommended') {
      badgeHtml = '<span class="badge recommended-badge">BEST</span>';
    } else if (zone.cls === 'avoid') {
      badgeHtml = '<span class="badge avoid-badge">AVOID</span>';
    }

    return '<div class="zone ' + zone.cls + '" data-zone-id="' + zone.id + '">' +
      badgeHtml +
      '<span class="direction">' + directionArrow(zone.direction) + '</span>' +
      '<span class="range">' + formatPrice(zone.low) + '–' + formatPrice(zone.high) + '</span>' +
      '<span class="score" style="color:' + scoreColor(zone.score) + '">' + zone.score + '</span>' +
      '</div>';
  }

  function render(container, currentPrice, prediction, overallEdge) {
    var zones = computeZones(currentPrice, prediction, overallEdge);
    var above = zones.slice(0, ZONES_PER_SIDE);
    var below = zones.slice(ZONES_PER_SIDE);

    var html = '';

    html += '<div class="zone-label">Above current price</div>';
    html += '<div class="zone-grid">';
    for (var i = 0; i < above.length; i++) {
      html += renderZone(above[i]);
    }
    html += '</div>';

    html += '<div class="price-line">';
    html += '<span class="price-line-value">' + formatPrice(currentPrice) + '</span>';
    html += '</div>';

    html += '<div class="zone-label">Below current price</div>';
    html += '<div class="zone-grid">';
    for (var j = 0; j < below.length; j++) {
      html += renderZone(below[j]);
    }
    html += '</div>';

    container.innerHTML = html;
  }

  function renderSkeleton(container) {
    var html = '';
    html += '<div class="zone-label">Above current price</div>';
    html += '<div class="zone-grid">';
    for (var i = 0; i < ZONES_PER_SIDE; i++) {
      html += '<div class="skeleton skeleton-zone"></div>';
    }
    html += '</div>';
    html += '<div class="price-line"><span class="price-line-value">Loading...</span></div>';
    html += '<div class="zone-label">Below current price</div>';
    html += '<div class="zone-grid">';
    for (var j = 0; j < ZONES_PER_SIDE; j++) {
      html += '<div class="skeleton skeleton-zone"></div>';
    }
    html += '</div>';
    container.innerHTML = html;
  }

  return {
    render: render,
    renderSkeleton: renderSkeleton,
    computeZones: computeZones
  };
})();
