const state = {
  metadata: null,
  architectures: [],
  architectureId: null,
  entity: null,
  rows: [],
  payload: {},
  draft: null,
  dirty: false,
  sort: { column: 'id', direction: 'asc' },
  referenceEntityRowsCache: {},
};

const el = {
  architectureSelect: document.getElementById('architectureSelect'),
  readonlyBadge: document.getElementById('readonlyBadge'),
  entityNav: document.getElementById('entityNav'),
  entityTitle: document.getElementById('entityTitle'),
  searchInput: document.getElementById('searchInput'),
  searchHistory: document.getElementById('searchHistory'),
  entityTable: document.getElementById('entityTable'),
  rowForm: document.getElementById('rowForm'),
  saveBtn: document.getElementById('saveBtn'),
  cancelBtn: document.getElementById('cancelBtn'),
  newRowBtn: document.getElementById('newRowBtn'),
  deleteRowBtn: document.getElementById('deleteRowBtn'),
  buildBtn: document.getElementById('buildBtn'),
};

async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPut(url, data) {
  const r = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function getReferenceCacheKey(architectureId, entity) {
  return `${architectureId}::${entity}`;
}

async function getEntityRowsForReferenceTooltip(architectureId, entity) {
  const cacheKey = getReferenceCacheKey(architectureId, entity);
  if (state.referenceEntityRowsCache[cacheKey]) return state.referenceEntityRowsCache[cacheKey];

  const entityMeta = state.metadata.entities[entity];
  if (!entityMeta) return [];

  const response = await apiGet(`/architectures/${architectureId}/spec/${entityMeta.entity}`);
  const payload = response.data || {};
  const rows = payload[entityMeta.collection_key] || [];
  state.referenceEntityRowsCache[cacheKey] = rows;
  return rows;
}

async function attachReferenceTooltip(refBtn) {
  if (!refBtn) return;
  if (refBtn.dataset.tooltipLoaded === '1') return;

  const refId = refBtn.dataset.refId;
  const targetEntity = refBtn.dataset.refEntity;
  if (!refId || !targetEntity) return;

  const rows = await getEntityRowsForReferenceTooltip(state.architectureId, targetEntity);
  const match = rows.find((row) => String(row.id || '') === String(refId));
  if (match && typeof match.description === 'string' && match.description.trim()) {
    refBtn.title = match.description.trim();
  }

  refBtn.dataset.tooltipLoaded = '1';
}

function buildNavUrl(navState) {
  const params = new URLSearchParams();
  if (navState.architectureId) params.set('arch', navState.architectureId);
  if (navState.entity) params.set('entity', navState.entity);
  if (navState.search) params.set('q', navState.search);
  const query = params.toString();
  return query ? `${window.location.pathname}?${query}` : window.location.pathname;
}

function getCurrentNavState() {
  return {
    architectureId: state.architectureId,
    entity: state.entity,
    search: el.searchInput.value || '',
  };
}

function pushNavHistory(reason = 'nav') {
  const navState = getCurrentNavState();
  const nextUrl = buildNavUrl(navState);
  const currentUrl = `${window.location.pathname}${window.location.search}`;
  if (nextUrl === currentUrl) return;
  window.history.pushState({ ...navState, reason }, '', nextUrl);
}

function parseNavStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return {
    architectureId: params.get('arch') || null,
    entity: params.get('entity') || null,
    search: params.get('q') || '',
  };
}

async function applyNavState(navState) {
  if (!confirmDiscardIfDirty()) return false;

  const hasArch = state.architectures.includes(navState.architectureId);
  const nextArchitectureId = hasArch ? navState.architectureId : state.architectureId;

  const entityOrder = state.metadata.entity_order;
  const hasEntity = entityOrder.includes(navState.entity);
  const nextEntity = hasEntity ? navState.entity : state.entity;

  let reloadNeeded = false;

  if (nextArchitectureId !== state.architectureId) {
    state.architectureId = nextArchitectureId;
    el.architectureSelect.value = nextArchitectureId;
    updateReadonlyMode();
    reloadNeeded = true;
  }

  if (nextEntity !== state.entity) {
    state.entity = nextEntity;
    state.sort = { column: 'id', direction: 'asc' };
    markEntityActive();
    reloadNeeded = true;
  }

  if (reloadNeeded) {
    await loadRows();
  }

  el.searchInput.value = navState.search || '';
  renderTable();
  return true;
}


function triggerBuildDownload() {
  const url = `/architectures/${state.architectureId}/build/download`;
  window.location.href = url;
}

function keyForHistory() {
  return `ad-editor:search:${state.architectureId}:${state.entity}`;
}

function loadSearchHistory() {
  const raw = localStorage.getItem(keyForHistory());
  return raw ? JSON.parse(raw) : [];
}

function saveSearchHistory(term) {
  if (!term.trim()) return;
  const limit = state.metadata.filter_history_limit || 10;
  const history = loadSearchHistory().filter((x) => x !== term);
  history.unshift(term);
  localStorage.setItem(keyForHistory(), JSON.stringify(history.slice(0, limit)));
}

function renderHistory() {
  const history = loadSearchHistory();
  el.searchHistory.innerHTML = '<option value="">History...</option>';
  history.forEach((item) => {
    const opt = document.createElement('option');
    opt.value = item;
    opt.textContent = item;
    el.searchHistory.appendChild(opt);
  });
}

function parseTokens(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean);
}

function getEntityMeta() {
  return state.metadata.entities[state.entity];
}

function stringifyVisibleCell(row, column) {
  const value = row[column];
  if (Array.isArray(value)) return value.join(' | ');
  if (value && typeof value === 'object') return Object.entries(value).map(([k, v]) => `${k}:${v}`).join(' | ');
  return value == null ? '' : String(value);
}

function filterRows(rows) {
  const tokens = parseTokens(el.searchInput.value);
  if (!tokens.length) return rows;
  const columns = getEntityMeta().columns;
  return rows.filter((row) => {
    const visible = columns.map((c) => stringifyVisibleCell(row, c).toLowerCase()).join(' || ');
    return tokens.every((t) => visible.includes(t));
  });
}

function compareValues(a, b) {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  return String(a).localeCompare(String(b), undefined, { sensitivity: 'base' });
}

function sortRows(rows) {
  const { column, direction } = state.sort;
  const list = [...rows];
  list.sort((ra, rb) => {
    const av = stringifyVisibleCell(ra, column);
    const bv = stringifyVisibleCell(rb, column);
    const diff = compareValues(av, bv);
    return direction === 'asc' ? diff : -diff;
  });
  return list;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlight(text, tokens) {
  let result = text;
  tokens.forEach((t) => {
    const re = new RegExp(`(${escapeRegExp(t)})`, 'ig');
    result = result.replace(re, '<mark>$1</mark>');
  });
  return result;
}

function isUrl(value) {
  return /^https?:\/\//i.test(value || '');
}

function isReferenceId(value) {
  return /^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$/.test((value || '').trim());
}

function resolveEntityByReferenceId(value) {
  const normalized = String(value || '').trim().toUpperCase();
  const prefix = normalized.split('-', 1)[0];
  const entries = Object.entries(state.metadata.entities);
  const match = entries.find(([, meta]) => meta.id_prefix.toUpperCase() === prefix);
  return match ? match[0] : null;
}

function renderReferenceLink(value, tokens) {
  const text = String(value || '');
  const targetEntity = resolveEntityByReferenceId(text);
  if (!targetEntity) return highlight(text, tokens);
  return `<button type="button" class="ref-link" data-ref-id="${text}" data-ref-entity="${targetEntity}">${highlight(text, tokens)}</button>`;
}

async function navigateToReference(refId, targetEntity) {
  if (!refId || !targetEntity) return;
  if (!confirmDiscardIfDirty()) return;

  if (state.entity !== targetEntity) {
    state.entity = targetEntity;
    state.sort = { column: 'id', direction: 'asc' };
    markEntityActive();
    await loadRows();
  }

  el.searchInput.value = refId;
  saveSearchHistory(refId);
  renderHistory();
  renderTable();
  pushNavHistory('reference');
}

function renderCellContent(row, column, tokens) {
  const value = row[column];

  if (Array.isArray(value)) {
    const listHtml = value
      .map((item) => {
        const text = String(item ?? '');
        if (isUrl(text)) return `<a href="${text}" target="_blank" rel="noreferrer">${highlight(text, tokens)}</a>`;
        if (isReferenceId(text)) return renderReferenceLink(text, tokens);
        return highlight(text, tokens);
      })
      .map((item) => `<div>${item}</div>`)
      .join('');
    return `<div class="link-list">${listHtml}</div>`;
  }

  const text = stringifyVisibleCell(row, column);
  if (isUrl(text)) return `<a href="${text}" target="_blank" rel="noreferrer">${highlight(text, tokens)}</a>`;
  if (isReferenceId(text)) return renderReferenceLink(text, tokens);
  return highlight(text, tokens);
}

function renderTable() {
  const columns = getEntityMeta().columns;
  const tokens = parseTokens(el.searchInput.value);
  const filtered = sortRows(filterRows(state.rows));

  const thead = el.entityTable.querySelector('thead');
  const tbody = el.entityTable.querySelector('tbody');

  thead.innerHTML = `<tr>${columns
    .map((c) => `<th data-sort="${c}">${c}${state.sort.column === c ? (state.sort.direction === 'asc' ? ' ▲' : ' ▼') : ''}</th>`)
    .join('')}</tr>`;

  tbody.innerHTML = filtered
    .map((row) => {
      const selected = state.draft && row.id === state.draft.id ? 'selected' : '';
      return `<tr class="${selected}" data-row-id="${row.id || ''}">${columns.map((c) => `<td>${renderCellContent(row, c, tokens)}</td>`).join('')}</tr>`;
    })
    .join('');
}

function inferFieldType(value) {
  if (Array.isArray(value)) return 'array';
  if (value && typeof value === 'object') return 'json';
  return 'text';
}

function createDefaultRow() {
  const meta = getEntityMeta();
  const maxNum = state.rows
    .map((r) => String(r.id || ''))
    .map((id) => id.match(new RegExp(`^${meta.id_prefix}-(\\d+)$`)))
    .filter(Boolean)
    .map((m) => Number(m[1]))
    .reduce((a, b) => Math.max(a, b), 0);

  const row = { id: `${meta.id_prefix}-${String(maxNum + 1).padStart(meta.id_width, '0')}` };
  Object.entries(meta.field_help || {}).forEach(([field, msg]) => {
    if (!(field in row)) row[field] = `TODO: ${msg}`;
  });
  return row;
}

function parseInputValue(input) {
  const kind = input.dataset.kind;
  if (kind === 'array') return input.value.split('\n').map((x) => x.trim()).filter(Boolean);
  if (kind === 'json') {
    try {
      return JSON.parse(input.value || '{}');
    } catch {
      return {};
    }
  }
  return input.value;
}

function renderForm() {
  const draft = state.draft;
  const meta = getEntityMeta();
  el.rowForm.innerHTML = '';

  if (!draft) {
    el.rowForm.innerHTML = '<p>Select a row or create a new one.</p>';
    return;
  }

  const keys = Array.from(new Set(['id', ...Object.keys(draft)]));
  keys.forEach((field) => {
    const wrap = document.createElement('div');
    wrap.className = 'field-row';

    const label = document.createElement('label');
    label.textContent = field;
    wrap.appendChild(label);

    const enumKey = `${meta.entity}.${field}`;
    const enumValues = state.metadata.enums[enumKey] || null;
    const value = draft[field];

    let input;
    if (field === 'id') {
      input = document.createElement('input');
      input.value = value || '';
      input.readOnly = true;
    } else if (enumValues) {
      input = document.createElement('select');
      input.innerHTML = '<option value="">-- select --</option>';
      enumValues.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        input.appendChild(option);
      });
      input.value = value || '';
    } else {
      input = document.createElement('textarea');
      const kind = inferFieldType(value);
      input.rows = kind === 'json' ? 4 : kind === 'array' ? 3 : 2;
      if (kind === 'array') {
        input.value = (value || []).join('\n');
        input.dataset.kind = 'array';
      } else if (kind === 'json') {
        input.value = JSON.stringify(value || {}, null, 2);
        input.dataset.kind = 'json';
      } else {
        input.value = value ?? '';
      }
    }

    input.dataset.field = field;
    input.addEventListener('input', () => {
      state.dirty = true;
      state.draft[field] = parseInputValue(input);
      updateActionButtons();
    });

    wrap.appendChild(input);

    if (meta.field_help[field]) {
      const help = document.createElement('div');
      help.className = 'field-help';
      help.textContent = meta.field_help[field];
      wrap.appendChild(help);
    }

    el.rowForm.appendChild(wrap);
  });
}

function updateActionButtons() {
  const readOnly = state.architectureId === '_root';
  const hasSelectedExisting = !!(state.draft && state.rows.some((row) => row.id === state.draft.id));
  el.newRowBtn.disabled = readOnly;
  el.saveBtn.disabled = readOnly;
  el.deleteRowBtn.disabled = readOnly || !hasSelectedExisting;
}

async function loadRows() {
  const meta = getEntityMeta();
  const response = await apiGet(`/architectures/${state.architectureId}/spec/${meta.entity}`);
  state.payload = response.data || {};
  state.rows = state.payload[meta.collection_key] || [];
  state.draft = null;
  state.dirty = false;
  renderTable();
  renderForm();
  renderHistory();
  updateActionButtons();
}

async function saveCurrent() {
  if (!state.draft) return;
  const meta = getEntityMeta();
  const idx = state.rows.findIndex((r) => r.id === state.draft.id);
  if (idx >= 0) state.rows[idx] = state.draft;
  else state.rows.push(state.draft);

  state.payload[meta.collection_key] = state.rows;
  await apiPut(`/architectures/${state.architectureId}/spec/${meta.entity}`, { data: state.payload });
  delete state.referenceEntityRowsCache[getReferenceCacheKey(state.architectureId, meta.entity)];
  state.dirty = false;
  renderTable();
  updateActionButtons();
  alert('Saved.');
}

async function deleteCurrent() {
  if (!state.draft) return;
  const idx = state.rows.findIndex((r) => r.id === state.draft.id);
  if (idx < 0) return;

  const confirmed = confirm(`Delete row with ID ${state.draft.id}?`);
  if (!confirmed) return;

  const meta = getEntityMeta();
  state.rows.splice(idx, 1);
  state.payload[meta.collection_key] = state.rows;
  await apiPut(`/architectures/${state.architectureId}/spec/${meta.entity}`, { data: state.payload });
  delete state.referenceEntityRowsCache[getReferenceCacheKey(state.architectureId, meta.entity)];
  state.draft = null;
  state.dirty = false;
  renderTable();
  renderForm();
  updateActionButtons();
  alert('Deleted.');
}

function confirmDiscardIfDirty() {
  if (!state.dirty) return true;
  return confirm('You have unsaved changes. Continue without saving?');
}

function selectRowById(rowId) {
  const row = state.rows.find((r) => String(r.id) === rowId);
  if (!row) return;
  state.draft = structuredClone(row);
  state.dirty = false;
  renderTable();
  renderForm();
  updateActionButtons();
}

function markEntityActive() {
  Array.from(el.entityNav.querySelectorAll('button')).forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.entity === state.entity);
  });
  el.entityTitle.textContent = state.entity;
}

function updateReadonlyMode() {
  const readOnly = state.architectureId === '_root';
  el.readonlyBadge.classList.toggle('hidden', !readOnly);
  updateActionButtons();
}

function bindEvents() {
  el.buildBtn.addEventListener('click', () => {
    triggerBuildDownload();
  });

  el.architectureSelect.addEventListener('change', async (e) => {
    if (!confirmDiscardIfDirty()) {
      e.target.value = state.architectureId;
      return;
    }
    state.architectureId = e.target.value;
    updateReadonlyMode();
    await loadRows();
    pushNavHistory('architecture');
  });

  el.entityNav.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-entity]');
    if (!btn || btn.dataset.entity === state.entity) return;
    if (!confirmDiscardIfDirty()) return;
    state.entity = btn.dataset.entity;
    state.sort = { column: 'id', direction: 'asc' };
    el.searchInput.value = '';
    markEntityActive();
    await loadRows();
    pushNavHistory('entity');
  });

  el.searchInput.addEventListener('input', renderTable);
  el.searchInput.addEventListener('change', () => {
    saveSearchHistory(el.searchInput.value);
    renderHistory();
    pushNavHistory('search');
  });

  el.searchHistory.addEventListener('change', () => {
    if (!el.searchHistory.value) return;
    el.searchInput.value = el.searchHistory.value;
    renderTable();
    pushNavHistory('history');
  });

  el.entityTable.addEventListener('mouseover', (e) => {
    const refBtn = e.target.closest('[data-ref-id][data-ref-entity]');
    if (!refBtn) return;
    attachReferenceTooltip(refBtn).catch(() => {
      refBtn.dataset.tooltipLoaded = '1';
    });
  });

  el.entityTable.addEventListener('click', (e) => {
    const sortTarget = e.target.closest('[data-sort]');
    if (sortTarget) {
      const column = sortTarget.dataset.sort;
      state.sort = state.sort.column === column
        ? { column, direction: state.sort.direction === 'asc' ? 'desc' : 'asc' }
        : { column, direction: 'asc' };
      renderTable();
      return;
    }

    const refBtn = e.target.closest('[data-ref-id][data-ref-entity]');
    if (refBtn) {
      navigateToReference(refBtn.dataset.refId, refBtn.dataset.refEntity).catch((error) => {
        alert(`Navigation failed: ${error.message}`);
      });
      return;
    }

    const tr = e.target.closest('tr[data-row-id]');
    if (!tr) return;
    if (!confirmDiscardIfDirty()) return;
    selectRowById(tr.dataset.rowId);
  });

  el.newRowBtn.addEventListener('click', () => {
    if (!confirmDiscardIfDirty()) return;
    state.draft = createDefaultRow();
    state.dirty = true;
    renderTable();
    renderForm();
    updateActionButtons();
  });

  el.deleteRowBtn.addEventListener('click', async () => {
    if (state.architectureId === '_root') return;
    if (state.dirty) {
      const proceed = confirm('Unsaved changes will be lost. Continue deleting selected row?');
      if (!proceed) return;
    }
    try {
      await deleteCurrent();
    } catch (error) {
      alert(`Delete failed: ${error.message}`);
    }
  });

  el.saveBtn.addEventListener('click', async () => {
    if (state.architectureId === '_root') return;
    try {
      await saveCurrent();
    } catch (error) {
      alert(`Save failed: ${error.message}`);
    }
  });

  el.cancelBtn.addEventListener('click', () => {
    if (!confirmDiscardIfDirty()) return;
    state.draft = null;
    state.dirty = false;
    renderTable();
    renderForm();
    updateActionButtons();
  });
}

async function initialize() {
  state.metadata = await apiGet('/editor/metadata');
  const arch = await apiGet('/architectures');
  state.architectures = arch.architectures;

  el.architectureSelect.innerHTML = state.architectures.map((id) => `<option value="${id}">${id}</option>`).join('');
  state.architectureId = state.architectures[0];

  el.entityNav.innerHTML = state.metadata.entity_order
    .map((entity) => `<button type="button" data-entity="${entity}">${entity}</button>`)
    .join('');
  state.entity = state.metadata.entity_order[0];

  bindEvents();

  const urlState = parseNavStateFromUrl();
  if (state.architectures.includes(urlState.architectureId)) {
    state.architectureId = urlState.architectureId;
    el.architectureSelect.value = state.architectureId;
  }
  if (state.metadata.entity_order.includes(urlState.entity)) {
    state.entity = urlState.entity;
  }

  updateReadonlyMode();
  await loadRows();
  markEntityActive();

  el.searchInput.value = urlState.search || '';
  renderTable();

  const initialNavState = getCurrentNavState();
  window.history.replaceState({ ...initialNavState, reason: 'init' }, '', buildNavUrl(initialNavState));

  window.addEventListener('popstate', (event) => {
    const targetState = event.state || parseNavStateFromUrl();
    applyNavState(targetState).catch((error) => {
      alert(`History navigation failed: ${error.message}`);
    });
  });
}

initialize().catch((error) => {
  console.error(error);
  alert(`Initialization failed: ${error.message}`);
});
