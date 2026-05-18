var KronosAPI = (function () {
  var BASE_URL = '/api/v1';
  var TIMEOUT_MS = 30000;
  var MAX_RETRIES = 3;
  var CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
  var RETRY_DELAYS = [1000, 3000, 6000]; // exponential-ish backoff

  // ── Cache Layer (localStorage) ──────────────────────────
  var cache = {
    _prefix: 'kronos_cache_',

    set: function (key, data) {
      try {
        var entry = {
          data: data,
          timestamp: Date.now(),
          version: 1
        };
        localStorage.setItem(this._prefix + key, JSON.stringify(entry));
      } catch (e) {
        // localStorage full or unavailable - clear old entries
        this.clear();
      }
    },

    get: function (key) {
      try {
        var raw = localStorage.getItem(this._prefix + key);
        if (!raw) return null;
        var entry = JSON.parse(raw);
        if (!entry || !entry.data) return null;
        // Return stale data too (caller checks freshness)
        return entry;
      } catch (e) {
        return null;
      }
    },

    isFresh: function (entry) {
      if (!entry || !entry.timestamp) return false;
      return (Date.now() - entry.timestamp) < CACHE_TTL_MS;
    },

    clear: function () {
      try {
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && k.indexOf(this._prefix) === 0) keys.push(k);
        }
        for (var j = 0; j < keys.length; j++) {
          localStorage.removeItem(keys[j]);
        }
      } catch (e) { /* noop */ }
    }
  };

  // ── Request with retry ─────────────────────────────────
  function request(method, path, body, retryCount) {
    retryCount = retryCount || 0;

    var controller = new AbortController();
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
            var err = new Error(msg);
            err.status = res.status;
            throw err;
          });
        }
        return res.json();
      })
      .catch(function (err) {
        clearTimeout(timer);

        // Don't retry 4xx client errors (except 429 rate-limit)
        if (err.status && err.status >= 400 && err.status < 500 && err.status !== 429) {
          throw err;
        }

        // Retry on timeout, network error, or 5xx
        if (retryCount < MAX_RETRIES) {
          var delay = RETRY_DELAYS[retryCount] || 6000;
          return new Promise(function (resolve) {
            setTimeout(resolve, delay);
          }).then(function () {
            return request(method, path, body, retryCount + 1);
          });
        }

        // All retries exhausted
        if (err.name === 'AbortError') {
          throw new Error('Server not responding after ' + (MAX_RETRIES + 1) + ' attempts. The server may be slow or unreachable.');
        }
        throw err;
      });
  }

  // ── Cached + stale-while-revalidate fetch ──────────────
  function fetchWithCache(key, apiPath) {
    var cached = cache.get(key);

    // Return structure: { data, fromCache, isStale, refreshPromise }
    var result = {
      data: cached ? cached.data : null,
      fromCache: !!cached,
      isStale: cached ? !cache.isFresh(cached) : true,
      refreshPromise: null
    };

    // Always kick off a network request
    result.refreshPromise = request('GET', apiPath)
      .then(function (data) {
        cache.set(key, data);
        result.data = data;
        result.fromCache = false;
        result.isStale = false;
        return data;
      });

    return result;
  }

  // ── Public API ─────────────────────────────────────────
  function fetchPrediction() {
    return request('GET', '/prediction');
  }

  function fetchSignals() {
    return request('GET', '/signals');
  }

  function runBacktest(params) {
    return request('POST', '/backtest', params);
  }

  /**
   * Fetch all data with caching and stale-while-revalidate.
   * Returns immediately with cached data if available,
   * then refreshes in background.
   *
   * Usage:
   *   var result = KronosAPI.fetchAllCached();
   *   // result.prediction.data = cached prediction (or null)
   *   // result.prediction.isStale = true if cache is old
   *   // result.prediction.refreshPromise = Promise for fresh data
   *   // result.signals.data = cached signals (or null)
   *   // result.allSettled = Promise that resolves when both refresh
   *   //   attempts complete (success or failure)
   */
  function fetchAllCached() {
    var predResult = fetchWithCache('prediction', '/prediction');
    var sigResult = fetchWithCache('signals', '/signals');

    return {
      prediction: predResult,
      signals: sigResult,

      // Promise that settles when both refreshes complete (regardless of success/failure)
      allSettled: Promise.allSettled([
        predResult.refreshPromise,
        sigResult.refreshPromise
      ]).then(function (results) {
        return {
          prediction: results[0].status === 'fulfilled' ? results[0].value : null,
          signals: results[1].status === 'fulfilled' ? results[1].value : null,
          predictionError: results[0].status === 'rejected' ? results[0].reason : null,
          signalsError: results[1].status === 'rejected' ? results[1].reason : null
        };
      })
    };
  }

  /**
   * Legacy fetchAll for backward compatibility.
   * Uses Promise.allSettled so partial data is returned even if one fails.
   */
  function fetchAll() {
    return Promise.allSettled([
      fetchPrediction(),
      fetchSignals()
    ]).then(function (results) {
      var pred = results[0].status === 'fulfilled' ? results[0].value : null;
      var sig = results[1].status === 'fulfilled' ? results[1].value : null;
      var errors = [];
      if (results[0].status === 'rejected') errors.push('Prediction: ' + results[0].reason.message);
      if (results[1].status === 'rejected') errors.push('Signals: ' + results[1].reason.message);

      if (!pred && !sig) {
        throw new Error(errors.join('; ') || 'All API requests failed');
      }

      return {
        prediction: pred,
        signals: sig,
        _errors: errors.length > 0 ? errors : null
      };
    });
  }

  return {
    fetchPrediction: fetchPrediction,
    fetchSignals: fetchSignals,
    runBacktest: runBacktest,
    fetchAll: fetchAll,
    fetchAllCached: fetchAllCached,
    cache: cache
  };
})();
