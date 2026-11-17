/* Store finder: nearest Jan Aushadhi Kendras by GPS or PIN code, shown on a Leaflet map. */
(function () {
  'use strict';
  var BASE = document.documentElement.dataset.base || '';
  var track = window.gbTrack || function () {};
  var listEl = document.getElementById('store-list');
  var msg = document.getElementById('store-msg');
  var pinIn = document.getElementById('pin');
  var stores = null, map = null, layer = null;

  // stores.json rows: [lat, lng, pin, address, district, state, storeCode]
  function load() {
    if (stores) return Promise.resolve(stores);
    msg.textContent = 'Loading 21,000+ stores…';
    return fetch(BASE + '/data/stores.json').then(function (r) { return r.json(); }).then(function (d) { stores = d; return d; });
  }
  function initMap() {
    if (map || !window.L) return;
    map = L.map('map', { scrollWheelZoom: false }).setView([22.5, 79], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    layer = L.layerGroup().addTo(map);
  }
  function km(a, b, c, d) {
    var R = 6371, x = (c - a) * Math.PI / 180, y = (d - b) * Math.PI / 180;
    var h = Math.sin(x / 2) * Math.sin(x / 2) + Math.cos(a * Math.PI / 180) * Math.cos(c * Math.PI / 180) * Math.sin(y / 2) * Math.sin(y / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function show(rows, origin, label) {
    initMap();
    layer && layer.clearLayers();
    if (!rows.length) { listEl.innerHTML = ''; msg.textContent = 'No Kendra found for that search. Try a nearby PIN code or use your location.'; return; }
    msg.textContent = label;
    listEl.innerHTML = rows.map(function (r, i) {
      var dir = 'https://www.google.com/maps/dir/?api=1&destination=' + r.s[0] + ',' + r.s[1];
      return '<li class="store"><b>Jan Aushadhi Kendra ' + esc(r.s[6]) + '</b><div class="meta">' + esc(r.s[4]) + ', ' + esc(r.s[5]) + ' · PIN ' + r.s[2] +
        (r.d != null ? ' · ' + (r.d < 1 ? Math.round(r.d * 1000) + ' m' : r.d.toFixed(1) + ' km') + ' away' : '') + '</div>' + esc(r.s[3]) +
        '<br><a href="' + dir + '" target="_blank" rel="noopener" data-dir="' + i + '">Get directions →</a></li>';
    }).join('');
    if (map) {
      var pts = [];
      rows.forEach(function (r) { var p = [r.s[0], r.s[1]]; pts.push(p); L.circleMarker(p, { radius: 8, color: '#0b6e4f', fillColor: '#13906a', fillOpacity: .85, weight: 2 }).bindPopup('<b>' + esc(r.s[6]) + '</b><br>' + esc(r.s[3])).addTo(layer); });
      if (origin) { pts.push(origin); L.circleMarker(origin, { radius: 9, color: '#a15c07', fillColor: '#f59e0b', fillOpacity: 1, weight: 3 }).bindPopup('You').addTo(layer); }
      map.fitBounds(pts, { padding: [30, 30], maxZoom: 14 });
    }
  }
  listEl.addEventListener('click', function (e) { if (e.target.dataset.dir != null) track('store_directions', { rank: +e.target.dataset.dir + 1 }); });

  document.getElementById('use-loc').addEventListener('click', function () {
    if (!navigator.geolocation) { msg.textContent = 'Your browser does not support location. Search by PIN code instead.'; return; }
    msg.textContent = 'Finding your location…';
    navigator.geolocation.getCurrentPosition(function (pos) {
      var la = pos.coords.latitude, lo = pos.coords.longitude;
      load().then(function (d) {
        var rows = d.map(function (s) { return { s: s, d: km(la, lo, s[0], s[1]) }; }).sort(function (a, b) { return a.d - b.d; }).slice(0, 10);
        track('find_store', { method: 'geolocation', nearest_km: Math.round(rows[0].d) });
        show(rows, [la, lo], 'The 10 nearest Jan Aushadhi Kendras to you:');
      });
    }, function () { msg.textContent = 'Location permission was denied. Search by PIN code instead.'; track('find_store_error', { reason: 'denied' }); }, { timeout: 10000 });
  });

  document.getElementById('pin-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var pin = pinIn.value.replace(/\D/g, '');
    if (pin.length !== 6) { msg.textContent = 'Enter a 6-digit PIN code.'; return; }
    load().then(function (d) {
      var p = +pin;
      var exact = d.filter(function (s) { return s[2] === p; });
      var near = exact.length >= 5 ? exact : d.filter(function (s) { return String(s[2]).slice(0, 3) === pin.slice(0, 3); })
        .sort(function (a, b) { return Math.abs(a[2] - p) - Math.abs(b[2] - p); });
      var rows = near.slice(0, 15).map(function (s) { return { s: s, d: null }; });
      track('find_store', { method: 'pin', results: rows.length });
      show(rows, null, exact.length ? exact.length + ' Kendra(s) in PIN ' + pin + (near !== exact ? ', plus nearby PIN codes:' : ':') : 'No Kendra in PIN ' + pin + '. The closest PIN codes in the area:');
    });
  });

  var params = new URLSearchParams(location.search);
  if (params.get('pin')) { pinIn.value = params.get('pin'); document.getElementById('pin-form').requestSubmit(); }
  initMap();
})();
