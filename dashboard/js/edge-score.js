var EdgeScore = (function () {
  var RADIUS = 48;
  var CIRCUMFERENCE = 2 * Math.PI * RADIUS;

  function scoreColor(score) {
    if (score >= 70) return 'var(--accent-green)';
    if (score >= 40) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  }

  function confidenceLabel(score) {
    if (score >= 70) return 'HIGH';
    if (score >= 40) return 'MEDIUM';
    return 'LOW';
  }

  function confidenceClass(score) {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  }

  function recommendationText(score, direction) {
    if (score >= 70) {
      return 'Strong edge detected. Zone aligns with predicted ' + direction + ' movement.';
    }
    if (score >= 40) {
      return 'Moderate edge. Signals mixed — proceed with caution.';
    }
    return 'Weak or opposing edge. This zone does not align with predictions.';
  }

  function render(container, score, direction) {
    var pct = Math.max(0, Math.min(100, score)) / 100;
    var offset = CIRCUMFERENCE * (1 - pct);
    var color = scoreColor(score);
    var conf = confidenceLabel(score);
    var confCls = confidenceClass(score);
    var rec = recommendationText(score, direction || 'price');

    container.innerHTML =
      '<div class="edge-score-section">' +
        '<div class="gauge-wrapper">' +
          '<svg class="gauge-svg" viewBox="0 0 120 120">' +
            '<circle class="gauge-bg" cx="60" cy="60" r="' + RADIUS + '"></circle>' +
            '<circle class="gauge-fill" cx="60" cy="60" r="' + RADIUS + '" ' +
              'stroke="' + color + '" ' +
              'stroke-dasharray="' + CIRCUMFERENCE + '" ' +
              'stroke-dashoffset="' + offset + '">' +
            '</circle>' +
          '</svg>' +
          '<span class="gauge-value" style="color:' + color + '">' + score + '</span>' +
          '<span class="gauge-label">EDGE SCORE</span>' +
        '</div>' +
        '<div class="edge-info">' +
          '<div class="edge-title">Overall Prediction Edge</div>' +
          '<div class="edge-confidence ' + confCls + '">Confidence: ' + conf + '</div>' +
          '<div class="edge-recommendation">' + rec + '</div>' +
        '</div>' +
      '</div>';
  }

  function renderSkeleton(container) {
    container.innerHTML =
      '<div class="edge-score-section">' +
        '<div class="gauge-wrapper">' +
          '<svg class="gauge-svg" viewBox="0 0 120 120">' +
            '<circle class="gauge-bg" cx="60" cy="60" r="' + RADIUS + '"></circle>' +
          '</svg>' +
          '<span class="gauge-value" style="color:var(--text-muted)">--</span>' +
          '<span class="gauge-label">EDGE SCORE</span>' +
        '</div>' +
        '<div class="edge-info">' +
          '<div class="skeleton skeleton-line" style="width:60%"></div>' +
          '<div class="skeleton skeleton-line" style="width:40%"></div>' +
          '<div class="skeleton skeleton-line" style="width:80%"></div>' +
        '</div>' +
      '</div>';
  }

  return {
    render: render,
    renderSkeleton: renderSkeleton
  };
})();
