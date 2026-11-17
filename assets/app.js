/* Generic Bachat: search, comparison card, savings calculator, sharing, GA4 events. */
(function () {
  'use strict';
  var root = document.documentElement;
  var BASE = root.dataset.base || '';
  var SITE = 'https://chinmaya2310.github.io' + BASE;
  root.classList.add('js');

  function track(name, params) { try { if (window.gtag) window.gtag('event', name, params || {}); } catch (e) {} }
  window.gbTrack = track;
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function rs(v) { return '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(2)); }
  function norm(s) { return s.toLowerCase().replace(/[^a-z0-9]/g, ''); }

  /* theme */
  var tt = document.querySelector('.theme-toggle');
  if (tt) tt.addEventListener('click', function () {
    var dark = (root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark';
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
  });

  /* reveal */
  var rv = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }); }, { rootMargin: '0px 0px -6% 0px' });
    rv.forEach(function (el) { io.observe(el); });
  } else rv.forEach(function (el) { el.classList.add('in'); });

  /* generic click tracking */
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-track]');
    if (el) track(el.dataset.track, { link_url: el.href || '', page_path: location.pathname });
  });

  /* ---------- calculator + share on any comparison card (static or rendered) ---------- */
  function wireCompare(card) {
    if (!card || card.dataset.wired) return;
    card.dataset.wired = '1';
    var bp = parseFloat(card.dataset.brandUnit), gp = parseFloat(card.dataset.genericUnit);
    var sel = card.querySelector('select'), out = card.querySelector('output');
    function upd() {
      var n = parseInt(sel.value, 10), m = (bp - gp) * n * 30;
      out.textContent = m > 0 ? rs(m) + ' a month, or ' + rs(m * 12) + ' a year' : 'nothing';
    }
    if (sel) { sel.addEventListener('change', function () { upd(); track('calculator_use', { per_day: sel.value, brand: card.dataset.brand }); }); upd(); }
    var share = card.querySelector('[data-share]');
    if (share) share.addEventListener('click', function (e) {
      e.preventDefault();
      var pct = Math.min(99, Math.floor(100 * (bp - gp) / bp));
      var url = SITE + card.dataset.path + '?utm_source=whatsapp&utm_medium=share&utm_campaign=savings_share';
      var text = card.dataset.brand + ' costs ' + rs(bp) + ' per ' + card.dataset.unit + '. Jan Aushadhi sells the same salt for ' +
        rs(gp) + (pct > 0 ? ' (' + pct + '% less)' : '') + '. You can check your own medicines here: ' + url;
      track('share', { method: 'whatsapp', content_type: 'savings', item_id: card.dataset.brand, saving_pct: pct });
      window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank', 'noopener');
    });
    var copy = card.querySelector('[data-copy]');
    if (copy) copy.addEventListener('click', function () {
      var url = SITE + card.dataset.path + '?utm_source=copy_link&utm_medium=share&utm_campaign=savings_share';
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () { copy.textContent = 'Link copied ✓'; }, function () { prompt('Copy this link', url); });
      track('share', { method: 'copy_link', content_type: 'savings', item_id: card.dataset.brand });
    });
  }
  document.querySelectorAll('.cmp').forEach(wireCompare);
  var staticCard = document.querySelector('.cmp[data-static]');
  if (staticCard) {
    var bp0 = parseFloat(staticCard.dataset.brandUnit), gp0 = parseFloat(staticCard.dataset.genericUnit);
    track('view_savings', { item_id: staticCard.dataset.brand, saving_pct: Math.round(100 * (bp0 - gp0) / bp0), source: 'brand_page' });
  }

  /* ---------- search ---------- */
  var input = document.getElementById('q');
  if (!input) return;
  var list = document.getElementById('suggest');
  var result = document.getElementById('result');
  var shards = {}, generics = null, items = [], active = -1, lastTracked = '';

  function loadGenerics() {
    if (generics) return Promise.resolve(generics);
    return fetch(BASE + '/data/generics.json').then(function (r) { return r.json(); }).then(function (d) { generics = d; return d; });
  }
  function loadShard(k) {
    if (shards[k]) return Promise.resolve(shards[k]);
    return fetch(BASE + '/data/idx/' + k + '.json').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; })
      .then(function (d) { shards[k] = d; return d; });
  }

  var timer;
  input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(suggest, 120); });
  input.addEventListener('focus', function () { loadGenerics(); if (items.length) list.classList.add('open'); });
  document.addEventListener('click', function (e) { if (!e.target.closest('.search')) list.classList.remove('open'); });
  input.addEventListener('keydown', function (e) {
    if (!list.classList.contains('open')) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      Array.prototype.forEach.call(list.children, function (li, i) { li.setAttribute('aria-selected', i === active); });
    } else if (e.key === 'Enter') { e.preventDefault(); choose(items[active >= 0 ? active : 0]); }
    else if (e.key === 'Escape') list.classList.remove('open');
  });

  function suggest() {
    var q = input.value.trim(), nq = norm(q);
    if (nq.length < 2) { list.classList.remove('open'); items = []; return; }
    Promise.all([loadShard(nq.slice(0, 2)), loadGenerics()]).then(function (res) {
      var shard = res[0], gens = res[1], seen = {};
      var brandHits = [];
      for (var i = 0; i < shard.length && brandHits.length < 8; i++) {
        var e = shard[i], n = norm(e[0]);
        if (n.indexOf(nq) === 0 && !seen[n]) { seen[n] = 1; brandHits.push({ type: 'brand', e: e }); }
      }
      var ql = q.toLowerCase(), genHits = [];
      for (var j = 0; j < gens.length && genHits.length < 4; j++) {
        var g = gens[j], s = g[6].toLowerCase();
        if (s.indexOf(ql) === 0 || s.indexOf(' ' + ql) > -1) genHits.push({ type: 'generic', g: g, gi: j });
      }
      items = brandHits.concat(genHits).slice(0, 10);
      active = -1;
      if (!items.length) {
        list.innerHTML = '<li class="none">No match yet. Try the brand name as printed on the strip, e.g. "Dolo 650"</li>';
        if (nq.length >= 4 && lastTracked !== nq) { lastTracked = nq; track('search', { search_term: q.slice(0, 40), results: 0 }); }
      } else {
        list.innerHTML = items.map(function (it, i) {
          if (it.type === 'brand') return '<li role="option" data-i="' + i + '"><span><b>' + esc(it.e[0]) + '</b></span><small>' + esc(it.e[1]) + '</small></li>';
          return '<li role="option" data-i="' + i + '"><span><span class="tag">Generic</span>' + esc(it.g[6]) + '</span><small>' + esc(it.g[5]) + '</small></li>';
        }).join('');
      }
      list.classList.add('open');
    });
  }
  list.addEventListener('click', function (e) {
    var li = e.target.closest('li[data-i]'); if (li) choose(items[+li.dataset.i]);
  });

  function choose(it) {
    if (!it) return;
    list.classList.remove('open');
    if (it.type === 'generic') {
      track('search', { search_term: input.value.trim().slice(0, 40), results: 1, result_type: 'generic' });
      location.href = BASE + '/medicine/' + it.g[0] + '/';
      return;
    }
    var e = it.e, g = generics[e[4]];
    input.value = e[0];
    track('search', { search_term: e[0], results: 1, result_type: 'brand' });
    render(e, g);
  }

  // e = [brandName, mfr, price, units, genericIndex, brandSlug]
  // g = [slug, name, perUnit, mrp, unitSize, form, saltLabel, units]
  function render(e, g) {
    var bpu = e[2] / e[3], gpu = g[2], unit = g[5], n = e[3];
    var good = bpu > gpu;
    var pct = good ? Math.min(99, Math.floor(100 * (bpu - gpu) / bpu)) : Math.round(100 * (bpu - gpu) / bpu);
    var path = e[5] ? '/brand/' + e[5] + '/' : '/medicine/' + g[0] + '/';
    var same = gpu * n, units = n === 1 ? unit : unit + 's';
    track('view_savings', { item_id: e[0], saving_pct: pct, source: 'search' });
    var summary = good
      ? '<p class="saving">' + n + ' ' + units + ' of the generic would cost <b>' + rs(same) + '</b> instead of ' + rs(e[2]) + '. That\'s <b>' + rs(e[2] - same) + ' less (' + pct + '%)</b>.</p>' +
        '<p>At <select aria-label="' + unit + 's per day"><option>1</option><option selected>2</option><option>3</option><option>4</option></select> ' + unit + 's a day, you\'d save about <output></output>.</p>'
      : '<p class="saving">This brand is already cheaper than the Jan Aushadhi version, by ' + rs(gpu - bpu) + ' per ' + unit + '.</p>';
    result.innerHTML =
      '<div class="cmp" data-brand="' + esc(e[0]) + '" data-brand-unit="' + bpu + '" data-generic-unit="' + gpu + '" data-unit="' + unit + '" data-path="' + path + '"><table>' +
      '<tr><td><b>' + esc(e[0]) + '</b><br><small>' + esc(e[1]) + ' · ' + rs(e[2]) + ' for ' + n + '</small></td><td class="price"><span class="' + (good ? 'struck' : '') + '">' + rs(bpu) + '</span><br><small>per ' + unit + '</small></td></tr>' +
      '<tr class="gen"><td><b>Jan Aushadhi ' + esc(g[6]) + '</b><br><small>' + esc(g[1]) + ' · ' + rs(g[3]) + ' for ' + esc(g[4]) + '</small></td><td class="price">' + rs(gpu) + '<br><small>per ' + unit + '</small></td></tr></table>' +
      '<div class="body">' + summary +
      '<div class="links"><button type="button" data-share>Send this on WhatsApp</button><a href="' + BASE + '/stores/" data-track="find_store_cta">Find a Kendra near you</a>' +
      '<a href="' + BASE + '/medicine/' + g[0] + '/" data-track="open_generic_page">All brands of ' + esc(g[6]) + '</a></div></div>' +
      '<p class="check">Before buying, check that your strip lists <b>' + esc(g[6]) + '</b> and nothing else. If it has an extra ingredient, this isn\'t the same medicine.</p></div>';
    wireCompare(result.querySelector('.cmp'));
    result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // popular chips on the home page: look the brand up and render it
  document.querySelectorAll('[data-pick]').forEach(function (b) {
    b.addEventListener('click', function () {
      var name = b.dataset.pick, nq = norm(name);
      track('popular_click', { item_id: name });
      Promise.all([loadShard(nq.slice(0, 2)), loadGenerics()]).then(function (res) {
        var hit = res[0].filter(function (e) { return norm(e[0]) === nq; })[0] || res[0].filter(function (e) { return norm(e[0]).indexOf(nq) === 0; })[0];
        if (hit) { input.value = hit[0]; render(hit, res[1][hit[4]]); }
      });
    });
  });
})();
