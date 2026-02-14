const state = {
  metadata: null,
  architectures: [],
  architectureId: null,
  entity: null,
  rows: [],
  payload: {},
  selectedIndex: -1,
  draft: null,
  dirty: false,
  sort: { column: 'id', direction: 'asc' },
  expandedCells: new Set(),
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
  const next = history.slice(0, limit);
  localStorage.setItem(keyForHistory(), JSON.stringify(next));
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

function highlight(text, tokens) {
  let result = text;
  tokens.forEach((t) => {
    if (!t) return;
    const re = new RegExp(`(${escapeRegExp(t)})`, 'ig');
    result = result.replace(re, '<mark>$1</mark>');
  });
  return result;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function cellKey(rowId, column) {
  return `${rowId}::${column}`;
}

function isUrl(value) {
  return /^https?:\/\//i.test(value || '');
}

function renderCellContent(row, column, tokens) {
  const value = row[column];
  const rowId = row.id || 'row';

  if (Array.isArray(value)) {
    const hasLong = value.length > 1;
    const key = cellKey(rowId, column);
    const expanded = state.expandedCells.has(key);
    const list = expanded ? value : value.slice(0, 1);
    const links = list
      .map((item) => {
        const text = String(item ?? '');
        if (isUrl(text)) {
          return `<a href="${text}" target="_blank" rel="noreferrer">${highlight(text, tokens)}</a>`;
        }
        return highlight(text, tokens);
      })
      .map((item) => `<div>${item}</div>`)
      .join('');
    const button = hasLong ? `<button type="button" class="small-btn" data-expand="${key}">${expanded ? 'Less' : 'More'}</button>` : '';
    return `<div class="link-list">${links}${button}</div>`;
  }

  const text = stringifyVisibleCell(row, column);
  if (isUrl(text)) {
    return `<a href="${text}" target="_blank" rel="noreferrer">${highlight(text, tokens)}</a>`;
  }
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
      return `<tr class="${selected}" data-row-id="${row.id || ''}">${columns
        .map((c) => `<td>${renderCellContent(row, c, tokens)}</td>`)
        .join('')}</tr>`;
    })
    .join('');
}

function inferFieldType(name, value) {
  if (Array.isArray(value)) return 'array';
  if (value && typeof value === 'object') return 'json';
  return 'text';
}

function createDefaultRow(entity) {
  const meta = getEntityMeta();
  const maxNum = state.rows
    .map((r) => String(r.id || ''))
    .map((id) => id.match(new RegExp(`^${meta.id_prefix}-(\\d+)$`)))
    .filter(Boolean)
    .map((m) => Number(m[1]))
    .reduce((a, b) => Math.max(a, b), 0);
  const nextId = `${meta.id_prefix}-${String(maxNum + 1).padStart(meta.id_width, '0')}`;

  const base = { id: nextId };
  Object.entries(meta.field_help || {}).forEach(([field, message]) => {
    if (!(field in base)) {
      base[field] = `TODO: ${message}`;
    }
  });
  return base;
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
    const row = document.createElement('div');
    row.className = 'field-row';

    const label = document.createElement('label');
    label.textContent = field;
    row.appendChild(label);

    const enumKey = `${meta.entity}.${field}`;
    const enumValues = state.metadata.enums[enumKey] || null;
    const value = draft[field];
    const type = inferFieldType(field, value);

    let input;
    if (field === 'id') {
      input = document.createElement('input');
      input.value = value || '';
      input.readOnly = true;
    } else if (enumValues) {
      input = document.createElement('select');
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = '-- select --';
      input.appendChild(empty);
      enumValues.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        input.appendChild(option);
      });
      input.value = value || '';
    } else if (type === 'array') {
      input = document.createElement('textarea');
      input.rows = 3;
      input.value = (value || []).join('\n');
      input.dataset.kind = 'array';
    } else if (type === 'json') {
      input = document.createElement('textarea');
      input.rows = 4;
      input.value = JSON.stringify(value || {}, null, 2);
      input.dataset.kind = 'json';
    } else {
      input = document.createElement('textarea');
      input.rows = 2;
      input.value = value ?? '';
    }

    input.dataset.field = field;
    input.addEventListener('input', () => {
      state.dirty = true;
      state.draft[field] = parseInputValue(input);
    });

    row.appendChild(input);

    if (meta.field_help[field]) {
      const help = document.createElement('div');
      help.className = 'field-help';
      help.textContent = meta.field_help[field];
      row.appendChild(help);
    }

    el.rowForm.appendChild(row);
  });
}

function parseInputValue(input) {
  const kind = input.dataset.kind;
  if (kind === 'array') {
    return input.value.split('\n').map((x) => x.trim()).filter(Boolean);
  }
  if (kind === 'json') {
    try {
      return JSON.parse(input.value || '{}');
    } catch {
      return {};
    }
  }
  return input.value;
}

async function loadRows() {
  const meta = getEntityMeta();
  const response = await apiGet(`/architectures/${state.architectureId}/spec/${meta.entity}`);
  state.payload = response.data || {};
  state.rows = state.payload[meta.collection_key] || [];
  state.selectedIndex = -1;
  state.draft = null;
  state.dirty = false;
  state.expandedCells.clear();
  renderTable();
  renderForm();
  renderHistory();
}

async function saveCurrent() {
  if (!state.draft) return;
  const meta = getEntityMeta();
  const idx = state.rows.findIndex((r) => r.id === state.draft.id);
  if (idx >= 0) {
    state.rows[idx] = state.draft;
  } else {
    state.rows.push(state.draft);
  }
  state.payload[meta.collection_key] = state.rows;
  await apiPut(`/architectures/${state.architectureId}/spec/${meta.entity}`, { data: state.payload });
  state.dirty = false;
  renderTable();
  alert('Saved.');
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
  updateReadonlyMode();
  await loadRows();
  markEntityActive();
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
  el.newRowBtn.disabled = readOnly;
  el.saveBtn.disabled = readOnly;
}

function bindEvents() {
  el.architectureSelect.addEventListener('change', async (e) => {
    if (!confirmDiscardIfDirty()) {
      e.target.value = state.architectureId;
      return;
    }
    state.architectureId = e.target.value;
    updateReadonlyMode();
    await loadRows();
  });

  el.entityNav.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-entity]');
    if (!btn) return;
    if (btn.dataset.entity === state.entity) return;
    if (!confirmDiscardIfDirty()) return;
    state.entity = btn.dataset.entity;
    state.sort = { column: 'id', direction: 'asc' };
    el.searchInput.value = '';
    markEntityActive();
    await loadRows();
  });

  el.searchInput.addEventListener('input', () => {
    renderTable();
  });
  el.searchInput.addEventListener('change', () => {
    saveSearchHistory(el.searchInput.value);
    renderHistory();
  });

  el.searchHistory.addEventListener('change', () => {
    if (!el.searchHistory.value) return;
    el.searchInput.value = el.searchHistory.value;
    renderTable();
  });

  el.entityTable.addEventListener('click', (e) => {
    const sortTarget = e.target.closest('[data-sort]');
    if (sortTarget) {
      const column = sortTarget.dataset.sort;
      if (state.sort.column === column) {
        state.sort.direction = state.sort.direction === 'asc' ? 'desc' : 'asc';
      } else {
        state.sort = { column, direction: 'asc' };
      }
      renderTable();
      return;
    }

    const expandBtn = e.target.closest('[data-expand]');
    if (expandBtn) {
      const key = expandBtn.dataset.expand;
      if (state.expandedCells.has(key)) state.expandedCells.delete(key);
      else state.expandedCells.add(key);
      renderTable();
      return;
    }

    const tr = e.target.closest('tr[data-row-id]');
    if (!tr) return;
    if (!confirmDiscardIfDirty()) return;
    selectRowById(tr.dataset.rowId);
  });

  el.newRowBtn.addEventListener('click', () => {
    if (!confirmDiscardIfDirty()) return;
    state.draft = createDefaultRow(state.entity);
    state.dirty = true;
    renderTable();
    renderForm();
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
  });
}

initialize().catch((error) => {
  console.error(error);
  alert(`Initialization failed: ${error.message}`);
});
