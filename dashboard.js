/* dashboard.js — Pitch Tendency Dashboard
   Requires outputs/data.js to be loaded first (sets window.PITCH_DATA).
   Served via VS Code Live Server from the project root.
*/
(function () {
  'use strict';

  // ── Guard: check data loaded ─────────────────────────────────────────────
  const banner = document.getElementById('error-banner');
  const rawData = window.PITCH_DATA;
  const D = {
    pitchers: Array.isArray(rawData && rawData.pitchers) ? rawData.pitchers : [],
    allCounts: Array.isArray(rawData && rawData.allCounts) ? rawData.allCounts : [],
    dataLong: Array.isArray(rawData && rawData.dataLong) ? rawData.dataLong : [],
    teamTrends: Array.isArray(rawData && rawData.teamTrends) ? rawData.teamTrends : [],
    researchContext: Array.isArray(rawData && rawData.researchContext) ? rawData.researchContext : [],
    heatmapFiles: rawData && rawData.heatmapFiles && typeof rawData.heatmapFiles === 'object' ? rawData.heatmapFiles : {}
  };

  if (!rawData || !D.dataLong.length) {
    banner.style.display = 'block';
    banner.innerHTML =
      '<strong>⚠ Dashboard data is missing.</strong><br>' +
      'Generate it with <code>python3 parser.py --all --live</code> (or <code>python parser.py --all --live</code>), then redeploy/refresh.';
  }

  // ── Tab switching ────────────────────────────────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
      btn.classList.add('active');
      document.getElementById(btn.dataset.target).classList.add('active');
    });
  });

  // ── Utility ──────────────────────────────────────────────────────────────
  function fillSelect(sel, values) {
    values.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    });
  }

  function setTable(tableId, headers, rowsHtml) {
    var t = document.getElementById(tableId);
    t.querySelector('thead').innerHTML =
      '<tr>' + headers.map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr>';
    t.querySelector('tbody').innerHTML = rowsHtml.join('');
  }

  function fmt(val) {
    return val != null ? val.toFixed(1) + '%' : '—';
  }

  // ── Pitcher Profiles ─────────────────────────────────────────────────────
  function renderProfiles() {
    var search = document.getElementById('pitcher-search').value.toLowerCase().trim();
    var count  = document.getElementById('count-filter').value;

    var rows = D.dataLong.filter(function (r) {
      return (!search || r.Pitcher.toLowerCase().includes(search)) &&
             (!count  || r.Count === count);
    });

    var pitchTypes = [];
    rows.forEach(function (r) {
      if (pitchTypes.indexOf(r.PitchType) === -1) pitchTypes.push(r.PitchType);
    });
    pitchTypes.sort();

    // Group by pitcher + count
    var map = {};
    rows.forEach(function (r) {
      var key = r.Pitcher + '|||' + r.Count;
      if (!map[key]) map[key] = { Pitcher: r.Pitcher, Count: r.Count, Total: r.TotalPitchesAtCount, types: {} };
      map[key].types[r.PitchType] = r.ProbabilityPct;
    });

    var sorted = Object.values(map).sort(function (a, b) {
      return a.Pitcher.localeCompare(b.Pitcher) ||
             D.allCounts.indexOf(a.Count) - D.allCounts.indexOf(b.Count);
    });

    var headers = ['Pitcher', 'Count', 'Pitches'].concat(pitchTypes);
    var tableRows = sorted.map(function (g) {
      var cells = pitchTypes.map(function (pt) {
        var v = g.types[pt];
        return v != null ? '<td class="pct">' + v.toFixed(1) + '%</td>' : '<td>—</td>';
      });
      return '<tr>' +
        '<td class="pitcher-name">' + g.Pitcher + '</td>' +
        '<td><span class="count-cell">' + g.Count + '</span></td>' +
        '<td>' + g.Total + '</td>' +
        cells.join('') +
        '</tr>';
    });

    if (!tableRows.length) {
      tableRows = ['<tr><td colspan="' + headers.length + '" style="color:#888;padding:20px">No results match your filter.</td></tr>'];
    }
    setTable('profiles-table', headers, tableRows);
  }

  // ── Heatmaps ─────────────────────────────────────────────────────────────
  function renderHeatmaps() {
    var search = document.getElementById('heatmap-search').value.toLowerCase().trim();
    var grid   = document.getElementById('heatmap-grid');
    grid.innerHTML = '';

    var entries = Object.entries(D.heatmapFiles).filter(function (e) {
      return !search || e[0].toLowerCase().includes(search);
    });

    if (!entries.length) {
      grid.innerHTML = '<p class="empty">No heatmaps match your search.</p>';
      return;
    }

    entries.forEach(function (e) {
      var pitcher = e[0], path = e[1];
      var card = document.createElement('div');
      card.className = 'heatmap-card';
      card.innerHTML = '<h3>' + pitcher + '</h3><img src="' + path + '" alt="' + pitcher + ' heatmap" loading="lazy" />';
      grid.appendChild(card);
    });
  }

  // ── Team Trends ──────────────────────────────────────────────────────────
  function renderTeam() {
    var count = document.getElementById('team-count-filter').value;
    var rows  = D.teamTrends.filter(function (r) { return !count || r.Count === count; });

    if (!rows.length) {
      setTable('team-table', [], ['<tr><td style="color:#888;padding:20px">No data available.</td></tr>']);
      return;
    }

    var headers   = ['Count', 'Pitch Type', 'Pitches', 'Total at Count', 'Probability %'];
    var cols      = ['Count', 'PitchType', 'PitchCount', 'TotalPitchesAtCount', 'ProbabilityPct'];
    var tableRows = rows.map(function (r) {
      return '<tr>' + cols.map(function (c, i) {
        var v = r[c] != null ? r[c] : '—';
        return i === 4 ? '<td class="pct">' + (typeof v === 'number' ? v.toFixed(1) + '%' : v) + '</td>'
                       : '<td>' + v + '</td>';
      }).join('') + '</tr>';
    });

    setTable('team-table', headers, tableRows);
  }

  // ── Strategy Context ─────────────────────────────────────────────────────
  var LEV_STYLE = {
    Hitter:  { bg: '#d4edda', fg: '#155724' },
    Pitcher: { bg: '#f8d7da', fg: '#721c24' },
    Neutral: { bg: '#fff3cd', fg: '#856404' },
    Full:    { bg: '#cce5ff', fg: '#004085' }
  };

  function renderStrategy() {
    var pitcher  = document.getElementById('strategy-pitcher').value;
    var leverage = document.getElementById('strategy-leverage').value;

    var rows = D.researchContext.filter(function (r) {
      return (!pitcher  || r.Pitcher === pitcher) &&
             (!leverage || r.CountLeverage === leverage);
    });

    if (!rows.length) {
      setTable('strategy-table', [],
        ['<tr><td colspan="8" style="color:#888;padding:20px">No data available. Try running with more files or a lower sample threshold.</td></tr>']);
      return;
    }

    var headers = ['Pitcher', 'Count', 'Leverage', 'Pitch Family', 'Their %', 'Baseline %', 'Delta', 'Interpretation'];
    var tableRows = rows.map(function (r) {
      var delta  = r.DeltaVsCountBaselinePct;
      var dStr   = (delta > 0 ? '+' : '') + (delta != null ? delta.toFixed(1) : '—') + '%';
      var dClass = delta >= 0 ? 'pos' : 'neg';
      var s      = LEV_STYLE[r.CountLeverage] || { bg: '#eee', fg: '#333' };
      return '<tr>' +
        '<td class="pitcher-name">' + r.Pitcher + '</td>' +
        '<td><span class="count-cell">' + r.Count + '</span></td>' +
        '<td><span class="badge" style="background:' + s.bg + ';color:' + s.fg + '">' + r.CountLeverage + '</span></td>' +
        '<td>' + r.PitchFamily + '</td>' +
        '<td class="pct">' + fmt(r.PitcherFamilyProbabilityPct) + '</td>' +
        '<td class="pct">' + fmt(r.BaselineProbabilityPct) + '</td>' +
        '<td class="' + dClass + '">' + dStr + '</td>' +
        '<td class="interp">' + r.StrategyInterpretation + '</td>' +
        '</tr>';
    });

    setTable('strategy-table', headers, tableRows);
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  (function init() {
    // Populate selects
    fillSelect(document.getElementById('count-filter'),        D.allCounts);
    fillSelect(document.getElementById('team-count-filter'),   D.allCounts);
    fillSelect(document.getElementById('strategy-pitcher'),    D.pitchers);

    var levs = [];
    D.researchContext.forEach(function (r) {
      if (r.CountLeverage && levs.indexOf(r.CountLeverage) === -1) levs.push(r.CountLeverage);
    });
    levs.sort();
    fillSelect(document.getElementById('strategy-leverage'), levs);

    // Wire events
    document.getElementById('pitcher-search').addEventListener('input',  renderProfiles);
    document.getElementById('count-filter').addEventListener('change',   renderProfiles);
    document.getElementById('heatmap-search').addEventListener('input',  renderHeatmaps);
    document.getElementById('team-count-filter').addEventListener('change', renderTeam);
    document.getElementById('strategy-pitcher').addEventListener('change',  renderStrategy);
    document.getElementById('strategy-leverage').addEventListener('change', renderStrategy);

    // Initial render
    renderProfiles();
    renderHeatmaps();
    renderTeam();
    renderStrategy();
  })();

})();
