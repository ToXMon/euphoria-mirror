var Signals = (function () {
  var SOURCES = ['reddit', 'hackernews', 'polymarket'];
  var LABELS = {
    reddit: 'Reddit',
    hackernews: 'Hacker News',
    polymarket: 'Polymarket'
  };
  var WEIGHTS = {
    reddit: 30,
    hackernews: 25,
    polymarket: 25
  };

  function sentimentFromScore(score) {
    if (score >= 60) return 'bullish';
    if (score <= 40) return 'bearish';
    return 'neutral';
  }

  function sentimentBadge(sentiment) {
    if (sentiment === 'bullish') return 'bullish';
    if (sentiment === 'bearish') return 'bearish';
    return 'neutral-signal';
  }

  function sentimentLabel(sentiment) {
    if (sentiment === 'bullish') return 'Bullish';
    if (sentiment === 'bearish') return 'Bearish';
    return 'Neutral';
  }

  function renderSignal(source, data) {
    var score = (data && typeof data.score === 'number') ? data.score : 50;
    var weight = WEIGHTS[source] || 20;
    var sentiment = sentimentFromScore(score);
    var badgeCls = sentimentBadge(sentiment);
    var label = sentimentLabel(sentiment);
    var name = LABELS[source] || source;
    var pct = Math.max(0, Math.min(100, score));

    return '<div class="signal-item">' +
      '<div class="signal-header">' +
        '<span class="signal-source">' + name + '</span>' +
        '<div class="signal-meta">' +
          '<span class="signal-score" style="color:' +
            (sentiment === 'bullish' ? 'var(--accent-green)' :
             sentiment === 'bearish' ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' +
            score +
          '</span>' +
          '<span class="signal-badge ' + badgeCls + '">' + label + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="signal-bar">' +
        '<div class="signal-bar-fill ' + badgeCls + '" style="width:' + pct + '%"></div>' +
      '</div>' +
      '<div class="signal-weight">Weight: ' + weight + '%</div>' +
    '</div>';
  }

  function render(container, signalsData) {
    var data = signalsData || {};
    var html = '<div class="panel-title"><span class="icon">📡</span> Signal Breakdown</div>';

    for (var i = 0; i < SOURCES.length; i++) {
      var src = SOURCES[i];
      html += renderSignal(src, data[src]);
    }

    container.innerHTML = html;
  }

  function renderSkeleton(container) {
    var html = '<div class="panel-title"><span class="icon">📡</span> Signal Breakdown</div>';
    for (var i = 0; i < SOURCES.length; i++) {
      html += '<div class="signal-item">' +
        '<div class="signal-header">' +
          '<div class="skeleton skeleton-line" style="width:30%"></div>' +
          '<div class="skeleton skeleton-line" style="width:20%"></div>' +
        '</div>' +
        '<div class="skeleton skeleton-bar"></div>' +
      '</div>';
    }
    container.innerHTML = html;
  }

  return {
    render: render,
    renderSkeleton: renderSkeleton
  };
})();
