var KronosAPI = (function () {
  var BASE_URL = '/api/v1';
  var TIMEOUT_MS = 10000;
  var controller = null;

  function cancelPending() {
    if (controller) {
      controller.abort();
      controller = null;
    }
  }

  function request(method, path, body) {
    cancelPending();
    controller = new AbortController();
    var signal = controller.signal;
    var timer = setTimeout(function () { controller.abort(); }, TIMEOUT_MS);

    var opts = {
      method: method,
      headers: { 'Accept': 'application/json' },
      signal: signal
    };

    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    return fetch(BASE_URL + path, opts)
      .then(function (res) {
        clearTimeout(timer);
        if (!res.ok) {
          return res.text().then(function (txt) {
            var msg = 'Request failed (' + res.status + ')';
            try { msg = JSON.parse(txt).detail || msg; } catch (_) {}
            throw new Error(msg);
          });
        }
        return res.json();
      })
      .catch(function (err) {
        clearTimeout(timer);
        if (err.name === 'AbortError') {
          throw new Error('Request timed out. Try again.');
        }
        throw err;
      });
  }

  function fetchPrediction() {
    return request('GET', '/prediction');
  }

  function fetchSignals() {
    return request('GET', '/signals');
  }

  function runBacktest(params) {
    return request('POST', '/backtest', params);
  }

  function fetchAll() {
    return Promise.all([
      fetchPrediction(),
      fetchSignals()
    ]).then(function (results) {
      return {
        prediction: results[0],
        signals: results[1]
      };
    });
  }

  return {
    fetchPrediction: fetchPrediction,
    fetchSignals: fetchSignals,
    runBacktest: runBacktest,
    fetchAll: fetchAll,
    cancelPending: cancelPending
  };
})();
