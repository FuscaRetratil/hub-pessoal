/**
 * Aplicação principal do Radar de Vagas.
 * Manipula estado local (localStorage), filtros, funil de vagas e renderização de tela.
 */

(function () {
  'use strict';

  /* ---------- Utilidades Básicas ---------- */
  function $(selector) {
    return document.querySelector(selector);
  }

  function esc(str) {
    return String(str || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  window.norm = function (str) {
    return String(str || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  function uniq(arr) {
    var out = [];
    arr.forEach(function (x) {
      if (out.indexOf(x) < 0) out.push(x);
    });
    return out;
  }

  function toggleIn(arr, val) {
    var idx = arr.indexOf(val);
    if (idx < 0) arr.push(val);
    else arr.splice(idx, 1);
  }

  function when(days) {
    if (days === 0) return 'hoje';
    if (days === 1) return 'ontem';
    return 'há ' + days + ' dias';
  }

  function todayISO() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function brDate(iso) {
    if (!iso) return '';
    var p = iso.split('-');
    return p.length >= 3 ? p[2] + '/' + p[1] : iso;
  }

  function dkey(job) {
    return norm(job.company) + '|' + norm(job.title);
  }

  function toast(msg) {
    var el = $('#toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      el.classList.remove('show');
    }, 2200);
  }

  /* ---------- Estado e Persistência Local ---------- */
  var STORE_KEY = 'hub.radar.v1';
  var DEFAULT_SKILLS = 'Testes manuais, Casos de teste, Testes funcionais, Documentação de testes, Selenium, Cypress, Python, JavaScript, React, HTML, CSS, Git, Postman, API REST, SQL, Jira, Scrum, Lógica de programação, Trabalho em equipe, Noções de automação';

  function defaultState() {
    return {
      filters: {
        levels: ['Estágio', 'Júnior'],
        places: ['Recife', 'Remoto'],
        areas: ['QA/Testes', 'Desenvolvimento'],
        customPlaces: [],
        customAreas: []
      },
      skills: DEFAULT_SKILLS,
      engine: 'keywords',
      applications: {},
      discarded: {}
    };
  }

  function hydrate(data) {
    var base = defaultState();
    if (!data || typeof data !== 'object') return base;
    var f = data.filters || {};
    ['levels', 'places', 'areas', 'customPlaces', 'customAreas'].forEach(function (k) {
      if (Array.isArray(f[k])) base.filters[k] = f[k].slice();
    });
    if (typeof data.skills === 'string') base.skills = data.skills;
    if (data.applications && typeof data.applications === 'object') base.applications = data.applications;
    if (data.discarded && typeof data.discarded === 'object') base.discarded = data.discarded;
    return base;
  }

  function loadLocal() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveLocal(data) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(data));
    } catch (e) {}
  }

  var state = hydrate(loadLocal());
  var tab = 'vagas';
  var dirty = false;
  var saveTimer = null;
  var currentResult = null;

  function setPersistStatus(msg) {
    var el = $('#persist');
    if (el) el.textContent = msg;
  }

  function queueSave() {
    dirty = true;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flushSave, 400);
  }

  function flushSave() {
    if (!dirty) return;
    dirty = false;
    saveLocal(state);
    setPersistStatus('Salvo neste navegador');
  }

  /* ---------- Lista de Vagas em Memória ---------- */
  var JOBS = typeof SAMPLE_JOBS !== 'undefined' ? SAMPLE_JOBS : [];
  var IS_SAMPLE = true;

  /* ---------- Opções Dinâmicas e Filtros ---------- */
  function placeOptions() {
    var counts = {};
    JOBS.forEach(function (j) {
      if (j.city !== 'Remoto') {
        counts[j.city] = (counts[j.city] || 0) + 1;
      }
    });
    var top = Object.keys(counts)
      .sort(function (a, b) { return counts[b] - counts[a] || a.localeCompare(b); })
      .slice(0, 12);
    var chosen = state.filters.places.filter(function (p) { return p !== 'Remoto'; });
    return uniq(['Recife', 'Remoto'].concat(top, chosen, state.filters.customPlaces));
  }

  function areaOptions() {
    return uniq(
      JOBS.map(function (j) { return j.area; })
        .sort()
        .concat(state.filters.customAreas)
    );
  }

  function passLevel(job) {
    return state.filters.levels.indexOf(job.level) >= 0;
  }

  function passPlace(job) {
    var loc = job.mode === 'Remoto' ? 'Remoto' : job.city;
    return state.filters.places.indexOf(loc) >= 0;
  }

  function passArea(job) {
    return state.filters.areas.some(function (area) {
      var nArea = norm(area);
      return norm(job.area) === nArea || norm(job.title).indexOf(nArea) >= 0;
    });
  }

  /* ---------- Computação do Funil ---------- */
  var REASONS = [
    { id: 'dup',   label: 'Repetidas', color: '--seg-dup' },
    { id: 'level', label: 'Nível',     color: '--seg-level' },
    { id: 'place', label: 'Local',     color: '--seg-place' },
    { id: 'area',  label: 'Área',      color: '--seg-area' }
  ];

  function compute() {
    var jobs = JOBS.map(function (j) {
      var copy = Object.assign({}, j);
      copy.key = dkey(j);
      copy.alsoIn = [];
      return copy;
    });

    jobs.sort(function (a, b) {
      return SRC_ORDER.indexOf(a.src) - SRC_ORDER.indexOf(b.src);
    });

    var primary = {};
    var cuts = { dup: [], level: [], place: [], area: [] };
    var open = [];
    var sent = [];
    var mine = [];

    jobs.forEach(function (j) {
      if (primary[j.key]) {
        primary[j.key].alsoIn.push(j.src);
        cuts.dup.push({ job: j, why: 'Já veio da ' + (SRC[primary[j.key].src] ? SRC[primary[j.key].src].name : primary[j.key].src) });
        return;
      }
      primary[j.key] = j;

      if (!passLevel(j)) {
        cuts.level.push({ job: j, why: 'Nível: ' + j.level });
        return;
      }
      if (!passPlace(j)) {
        cuts.place.push({ job: j, why: 'Local: ' + (j.mode === 'Remoto' ? 'Remoto' : j.city) });
        return;
      }
      if (!passArea(j)) {
        cuts.area.push({ job: j, why: 'Área: ' + j.area });
        return;
      }
      if (state.applications[j.key]) {
        sent.push(j);
        return;
      }
      if (state.discarded[j.key]) {
        mine.push(j);
        return;
      }
      open.push(j);
    });

    open.forEach(function (j) {
      j.m = runMatch(j, state);
    });

    open.sort(function (a, b) {
      return b.m.pct - a.m.pct || a.days - b.days;
    });

    return {
      total: jobs.length,
      cuts: cuts,
      open: open,
      sent: sent,
      mine: mine
    };
  }

  /* ---------- Renderização ---------- */
  function renderFilters() {
    var f = state.filters;
    var places = placeOptions();
    var areas = areaOptions();

    function renderChips(kind, options, selected) {
      return '<div class="chips">' + options.map(function (opt) {
        var isSelected = selected.indexOf(opt) >= 0;
        return '<button type="button" class="chip' + (isSelected ? ' on' : '') + '" data-chip="' + kind + '" data-v="' + esc(opt) + '" aria-pressed="' + isSelected + '">' + esc(opt) + '</button>';
      }).join('') + '</div>';
    }

    var html =
      '<div style="display:flex;flex-direction:column;gap:16px">' +
        '<fieldset><legend>Nível</legend>' + LEVELS.map(function (lvl) {
          var checked = f.levels.indexOf(lvl) >= 0 ? ' checked' : '';
          return '<label class="check"><input type="checkbox" data-level value="' + esc(lvl) + '"' + checked + '> ' + esc(lvl) + '</label>';
        }).join('') + '</fieldset>' +

        '<fieldset><legend>Local</legend>' +
          renderChips('places', places, f.places) +
          '<form class="adder" data-add="places">' +
            '<input id="add-places" type="text" placeholder="Outra cidade" aria-label="Adicionar cidade">' +
            '<button class="btn" type="submit">Adicionar</button>' +
          '</form>' +
        '</fieldset>' +

        '<fieldset><legend>Área</legend>' +
          renderChips('areas', areas, f.areas) +
          '<form class="adder" data-add="areas">' +
            '<input id="add-areas" type="text" placeholder="Outra área ou palavra do título" aria-label="Adicionar área">' +
            '<button class="btn" type="submit">Adicionar</button>' +
          '</form>' +
        '</fieldset>' +
      '</div>';

    $('#filters-body').innerHTML = html;
  }

  function renderFunnel(res) {
    var cutTotal = REASONS.reduce(function (sum, r) { return sum + res.cuts[r.id].length; }, 0);

    $('#funnel-head').innerHTML =
      '<strong>' + res.total + ' vagas coletadas</strong>' +
      '<span>' + cutTotal + ' cortadas pelos filtros</span>' +
      '<span><b class="mono">' + res.open.length + '</b> para você analisar</span>';

    var segs = REASONS.map(function (r) {
      return { label: r.label, color: r.color, n: res.cuts[r.id].length, goto: 'cortadas' };
    }).concat([
      { label: 'Descartadas por mim', color: '--seg-mine', n: res.mine.length, goto: 'cortadas' },
      { label: 'Já enviadas',         color: '--seg-sent', n: res.sent.length, goto: 'candidaturas' },
      { label: 'Na lista',             color: '--accent',   n: res.open.length, goto: 'vagas' }
    ]);

    $('#bar').innerHTML = segs.filter(function (s) { return s.n > 0; }).map(function (s) {
      return '<span style="flex-grow:' + s.n + ';background:var(' + s.color + ')" title="' + esc(s.label) + ': ' + s.n + '"></span>';
    }).join('');

    $('#legend').innerHTML = segs.map(function (s) {
      return '<li><button type="button" data-goto="' + s.goto + '">' +
        '<span class="sw" style="background:var(' + s.color + ')"></span>' +
        esc(s.label) + ' <b>' + s.n + '</b>' +
      '</button></li>';
    }).join('');
  }

  function meterClass(pct) {
    return pct >= 75 ? 'good' : pct >= 50 ? 'mid' : 'low';
  }

  function jobRow(job) {
    var m = job.m;
    var s = SRC[job.src] || { name: job.src, url: '#' };
    var loc = job.mode === 'Remoto' ? 'Remoto' : job.city + ' · ' + job.mode;
    var also = job.alsoIn.length ? '<span class="also">também em ' + job.alsoIn.map(function (x) { return SRC[x] ? SRC[x].name : x; }).join(', ') + '</span>' : '';

    return '<li class="job" data-key="' + esc(job.key) + '">' +
      '<div>' +
        '<div class="job-title">' + esc(job.title) + '</div>' +
        '<div class="job-meta">' +
          '<span>' + esc(job.company) + '</span>' +
          '<span>' + esc(loc) + '</span>' +
          '<span class="pill">' + esc(job.level) + '</span>' +
          '<span>' + esc(s.name) + '</span>' +
          '<span>' + when(job.days) + '</span>' +
          also +
        '</div>' +
      '</div>' +
      '<div class="match">' +
        '<div class="match-top">' +
          '<b>' + m.pct + '%</b>' +
          '<span>' + m.have.length + ' de ' + m.total + ' requisitos</span>' +
        '</div>' +
        '<div class="meter ' + meterClass(m.pct) + '" role="img" aria-label="Match de ' + m.pct + '%">' +
          '<span style="width:' + m.pct + '%"></span>' +
        '</div>' +
      '</div>' +
      '<div class="reqs">' +
        '<div class="req-row">' +
          '<span class="req-label have">Você tem</span>' +
          (m.have.length ? m.have.map(function (x) { return '<span class="tag have">' + esc(x) + '</span>'; }).join('') : '<span class="hint" style="margin:0">Nenhum requisito encontrado</span>') +
        '</div>' +
        '<div class="req-row">' +
          '<span class="req-label miss">Falta</span>' +
          (m.missing.length ? m.missing.map(function (x) { return '<span class="tag miss">' + esc(x) + '</span>'; }).join('') : '<span class="hint" style="margin:0">Nada faltando</span>') +
        '</div>' +
      '</div>' +
      '<div class="acts">' +
        '<a class="btn" href="' + esc(job.url || s.url) + '" target="_blank" rel="noopener"' + (job.url ? '' : ' title="Vaga de exemplo: abre a página inicial da fonte"') + '>' + (job.url ? 'Abrir vaga' : 'Abrir na ' + esc(s.name)) + '</a>' +
        '<button class="btn" type="button" data-act="copy">Copiar resumo</button>' +
        '<button class="btn primary" type="button" data-act="apply">Marquei como enviada</button>' +
        '<button class="btn quiet" type="button" data-act="discard">Descartar</button>' +
      '</div>' +
    '</li>';
  }

  function renderBoard(res) {
    var apps = Object.keys(state.applications).map(function (k) {
      var a = state.applications[k];
      a.key = k;
      return a;
    }).sort(function (a, b) {
      return a.date < b.date ? 1 : -1;
    });

    var cutTotal = REASONS.reduce(function (sum, r) { return sum + res.cuts[r.id].length; }, 0) + res.mine.length;
    var tabs = [
      { id: 'vagas',        label: 'Vagas',        n: res.open.length },
      { id: 'candidaturas', label: 'Candidaturas', n: apps.length },
      { id: 'cortadas',     label: 'Cortadas',     n: cutTotal }
    ];

    $('#tabs').innerHTML = tabs.map(function (t) {
      return '<button type="button" role="tab" data-tab="' + t.id + '" aria-selected="' + (tab === t.id) + '">' +
        t.label + '<span class="n">' + t.n + '</span>' +
      '</button>';
    }).join('');

    var html = '';
    if (tab === 'vagas') {
      html += '<p class="note">O Radar prepara, você decide. Abra a vaga, envie no site da empresa e marque aqui para ela sair da lista.</p>';
      html += res.open.length
        ? '<ul class="list">' + res.open.map(jobRow).join('') + '</ul>'
        : '<div class="empty"><strong>Nenhuma vaga passou nos filtros</strong>Veja o que foi cortado na aba Cortadas ou amplie nível, local e área ao lado.</div>';
    } else if (tab === 'candidaturas') {
      html += apps.length
        ? '<ul class="list">' + apps.map(function (a) {
            return '<li class="app" data-key="' + esc(a.key) + '">' +
              '<div>' +
                '<div class="job-title" style="font-size:15px">' + esc(a.title) + '</div>' +
                '<div class="job-meta">' +
                  '<span>' + esc(a.company) + '</span>' +
                  '<span>' + esc(SRC[a.src] ? SRC[a.src].name : a.src) + '</span>' +
                  '<span class="mono">enviada em ' + brDate(a.date) + '</span>' +
                '</div>' +
              '</div>' +
              '<div class="sel">' +
                '<label class="lbl" style="margin:0 0 2px" for="st-' + esc(a.key) + '">Situação</label>' +
                '<select id="st-' + esc(a.key) + '" data-status>' +
                  ['Enviada', 'Em processo', 'Entrevista', 'Recusada', 'Oferta'].map(function (opt) {
                    return '<option' + (opt === a.status ? ' selected' : '') + '>' + opt + '</option>';
                  }).join('') +
                '</select>' +
              '</div>' +
              '<button class="btn quiet" type="button" data-act="undo">Desfazer</button>' +
            '</li>';
          }).join('') + '</ul>'
        : '<div class="empty"><strong>Nenhuma candidatura registrada</strong>Quando você enviar uma no site da empresa, marque na aba Vagas. A mesma vaga não volta, mesmo que apareça em outra fonte.</div>';
    } else {
      var hasAnyCut = false;
      REASONS.forEach(function (r) {
        var list = res.cuts[r.id];
        if (!list.length) return;
        hasAnyCut = true;
        html += '<div class="group-h">' +
          '<span><span class="sw" style="background:var(' + r.color + ')"></span>' + r.label + '</span>' +
          '<span class="mono">' + list.length + '</span>' +
        '</div>' +
        '<ul class="list">' +
          list.map(function (c) {
            var srcName = SRC[c.job.src] ? SRC[c.job.src].name : c.job.src;
            return '<li class="cut">' +
              '<div>' +
                '<div class="t">' + esc(c.job.title) + '</div>' +
                '<div class="m">' + esc(c.job.company) + ' · ' + esc(srcName) + '</div>' +
              '</div>' +
              '<span class="why">' + esc(c.why) + '</span>' +
            '</li>';
          }).join('') +
        '</ul>';
      });

      if (res.mine.length) {
        hasAnyCut = true;
        html += '<div class="group-h">' +
          '<span><span class="sw" style="background:var(--seg-mine)"></span>Descartadas por mim</span>' +
          '<span class="mono">' + res.mine.length + '</span>' +
        '</div>' +
        '<ul class="list">' +
          res.mine.map(function (j) {
            var srcName = SRC[j.src] ? SRC[j.src].name : j.src;
            return '<li class="cut" data-key="' + esc(j.key) + '">' +
              '<div>' +
                '<div class="t">' + esc(j.title) + '</div>' +
                '<div class="m">' + esc(j.company) + ' · ' + esc(srcName) + '</div>' +
              '</div>' +
              '<button class="btn" type="button" data-act="restore">Restaurar</button>' +
            '</li>';
          }).join('') +
        '</ul>';
      }

      if (!hasAnyCut) {
        html = '<div class="empty"><strong>Nada foi cortado</strong>Todas as vagas coletadas passaram nos filtros.</div>';
      }
    }

    $('#board-body').innerHTML = html;
  }

  function renderMain() {
    currentResult = compute();
    renderFunnel(currentResult);
    renderBoard(currentResult);
  }

  function renderAll() {
    renderFilters();
    var skillsInput = $('#skills');
    if (skillsInput) skillsInput.value = state.skills;
    renderMain();
  }

  /* ---------- Ações de Cópia e Resumo ---------- */
  function summaryText(job) {
    var m = job.m;
    var s = SRC[job.src] || { name: job.src };
    var loc = job.mode === 'Remoto' ? 'Remoto' : job.city + ' (' + job.mode.toLowerCase() + ')';
    return [
      'Vaga: ' + job.title + ' | ' + job.company,
      'Fonte: ' + s.name + ' · ' + loc + ' · ' + job.level,
      'Match: ' + m.have.length + ' de ' + m.total + ' requisitos (' + m.pct + '%)',
      'Tenho: ' + (m.have.join(', ') || 'nenhum'),
      'Falta: ' + (m.missing.join(', ') || 'nada'),
      'Destacar na candidatura: ' + (m.have.slice(0, 4).join(', ') || 'experiência geral')
    ].join('\n');
  }

  function copyText(text) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
      toast(ok ? 'Resumo copiado' : 'Não deu para copiar. Selecione o texto manualmente.');
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        toast('Resumo copiado');
      }, fallback);
    } else {
      fallback();
    }
  }

  /* ---------- Eventos Globais ---------- */
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-tab],[data-goto],[data-chip],[data-act]');
    if (!el) return;

    if (el.dataset.tab || el.dataset.goto) {
      tab = el.dataset.tab || el.dataset.goto;
      renderMain();
      return;
    }

    if (el.dataset.chip) {
      toggleIn(state.filters[el.dataset.chip], el.dataset.v);
      queueSave();
      renderFilters();
      renderMain();
      return;
    }

    var row = el.closest('[data-key]');
    if (!row) return;

    var key = row.dataset.key;
    var act = el.dataset.act;
    var job = currentResult && currentResult.open.filter(function (j) { return j.key === key; })[0];

    if (act === 'copy' && job) {
      copyText(summaryText(job));
      return;
    }
    if (act === 'apply' && job) {
      state.applications[key] = {
        title: job.title,
        company: job.company,
        src: job.src,
        date: todayISO(),
        status: 'Enviada'
      };
      queueSave();
      renderMain();
      toast('Registrada em Candidaturas');
      return;
    }
    if (act === 'discard') {
      state.discarded[key] = true;
      queueSave();
      renderMain();
      toast('Descartada. Dá para restaurar em Cortadas');
      return;
    }
    if (act === 'restore') {
      delete state.discarded[key];
      queueSave();
      renderMain();
      return;
    }
    if (act === 'undo') {
      delete state.applications[key];
      queueSave();
      renderMain();
      toast('Candidatura desfeita');
      return;
    }
  });

  document.addEventListener('change', function (e) {
    var t = e.target;
    if (t.matches('[data-level]')) {
      var arr = state.filters.levels;
      var idx = arr.indexOf(t.value);
      if (t.checked && idx < 0) arr.push(t.value);
      else if (!t.checked && idx >= 0) arr.splice(idx, 1);
      queueSave();
      renderMain();
      return;
    }
    if (t.matches('[data-status]')) {
      var row = t.closest('[data-key]');
      if (!row) return;
      var key = row.dataset.key;
      if (state.applications[key]) {
        state.applications[key].status = t.value;
        queueSave();
      }
    }
  });

  document.addEventListener('submit', function (e) {
    var form = e.target.closest('form[data-add]');
    if (!form) return;
    e.preventDefault();

    var kind = form.dataset.add;
    var input = form.querySelector('input');
    var val = input.value.trim();
    if (!val) return;

    var customProp = kind === 'places' ? 'customPlaces' : 'customAreas';
    var options = kind === 'places' ? placeOptions() : areaOptions();
    var existing = options.filter(function (opt) { return norm(opt) === norm(val); })[0];
    var canonicalName = existing || val;

    if (!existing) state.filters[customProp].push(canonicalName);
    if (state.filters[kind].indexOf(canonicalName) < 0) state.filters[kind].push(canonicalName);

    queueSave();
    renderFilters();
    renderMain();

    var nextInput = $('#add-' + kind);
    if (nextInput) nextInput.focus();
  });

  var skillsTimer = null;
  var skillsInput = $('#skills');
  if (skillsInput) {
    skillsInput.addEventListener('input', function (e) {
      state.skills = e.target.value;
      queueSave();
      clearTimeout(skillsTimer);
      skillsTimer = setTimeout(renderMain, 250);
    });
  }

  /* ---------- Carga de Dados Reais ---------- */
  function safeUrl(url) {
    return /^https?:\/\//i.test(url || '') ? url : '';
  }

  function toDays(iso) {
    if (!iso) return 0;
    var time = new Date(iso).getTime();
    return isNaN(time) ? 0 : Math.max(0, Math.round((Date.now() - time) / 86400000));
  }

  async function loadRealJobs() {
    try {
      var res = await fetch('data/radar/jobs.json', { cache: 'no-store' });
      if (!res.ok) return;
      var data = await res.json();
      if (!data || !Array.isArray(data.jobs) || !data.jobs.length) return;

      JOBS = data.jobs.map(function (j) {
        return {
          id: String(j.id),
          src: j.source,
          title: j.title,
          company: j.company,
          city: j.city,
          mode: j.mode,
          level: j.level,
          area: j.area,
          days: toDays(j.published_at),
          reqs: j.reqs || [],
          url: safeUrl(j.url)
        };
      }).filter(function (j) {
        return SRC[j.src];
      });

      IS_SAMPLE = false;

      var genDate = data.generated_at ? new Date(data.generated_at) : null;
      var label = genDate && !isNaN(genDate)
        ? genDate.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
        : '';

      var badge = $('#badge');
      if (badge) {
        badge.textContent = 'Coleta de ' + label;
        badge.style.background = 'var(--good-soft)';
        badge.style.color = 'var(--good)';
      }

      renderAll();
    } catch (e) {}
  }

  /* ---------- Inicialização ---------- */
  if (window.matchMedia && window.matchMedia('(max-width:1060px)').matches) {
    var filterDetails = $('#filters');
    if (filterDetails) filterDetails.removeAttribute('open');
  }

  setPersistStatus('Salvo neste navegador');
  renderAll();
  loadRealJobs();
})();
