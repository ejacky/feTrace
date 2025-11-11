import { fetchNames, fetchPerson } from './api.js';
import { state, setPersonData, setCurrentIndex, setPlayTimer, setLoadingState } from './state.js';

// DOM 引用集中
const DOM = {
  eventsList: document.getElementById('eventsList'),
  slider: document.getElementById('slider'),
  playBtn: document.getElementById('play'),
  yearLabel: document.getElementById('yearLabel'),
  status: document.getElementById('mapStatus'),
  personTitle: document.getElementById('personTitle'),
  infoOverlay: document.getElementById('infoOverlay'),
  searchInput: document.getElementById('personSearch'),
  suggestEl: document.getElementById('searchList'),
};

// 常量与配置
const SUGGEST_LIMIT = 60;
const PLAY_INTERVAL_MS = 1800;

// 地图初始化（保持原逻辑）
function initMap() {
  DOM.status.textContent = '初始化地图...';
  state.map = L.map('map', { zoomControl: false });
  state.map.setView([34, 110], 4);
  const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  });
  tiles.addTo(state.map);
  DOM.status.textContent = '地图加载成功';
}

function getMarkerIcon(selected = false) {
  const color = (state.personStyles[state.currentPerson]?.markerColor) || '#8B5CF6';
  const selectedClass = selected ? ' selected' : '';
  return L.divIcon({ className: 'marker-icon', html: `<span class="marker-dot${selectedClass}" style="--mc:${color}"></span>`, iconSize: [16, 16], iconAnchor: [8, 8] });
}

function refreshSelectedMarker(index = state.currentIndex) {
  state.markers.forEach((m, i) => {
    m.setIcon(getMarkerIcon(i === index));
  });
}

function fitToEvents() {
  const coords = state.events.map(e => [e.lat, e.lon]);
  if (!coords.length) return;
  if (coords.length === 1) { state.map.setView(coords[0], 10); return; }
  const bounds = L.latLngBounds(coords);
  try { state.map.fitBounds(bounds, { padding: [60, 60], maxZoom: 8 }); } catch (_) { }
}

function drawMarkersAndLine() {
  // 清理旧图层
  state.markers.forEach(m => { try { state.map.removeLayer(m); } catch (_) { } });
  state.markers = [];
  if (state.polyline) { try { state.map.removeLayer(state.polyline); } catch (_) { } state.polyline = null; }

  if (!state.events.length) { return; }
  const path = state.events.map(e => [e.lat, e.lon]);
  const color = (state.personStyles[state.currentPerson]?.lineColor) || '#A78BFA';
  state.polyline = L.polyline(path, { color, weight: 4, opacity: 0.85, dashArray: '6 6' }).addTo(state.map);

  state.events.forEach((e, idx) => {
    const m = L.marker([e.lat, e.lon], { icon: getMarkerIcon(false) }).addTo(state.map);
    m.on('click', () => selectIndex(idx));
    state.markers.push(m);
  });
  refreshSelectedMarker();
  fitToEvents();
}

function updateInfoOverlay(e) {
  DOM.infoOverlay.innerHTML = `<div style="min-width:220px">
    <strong>${e.year} · ${e.title}</strong>
    <div class="small" style="margin-top:6px">${e.place} · 年龄：${e.age}</div>
    <div style="margin-top:8px">${e.detail}</div>
  </div>`;
}

function updateUI(index) {
  if (index < 0 || index >= state.events.length) return;
  const e = state.events[index];
  DOM.yearLabel.textContent = e.year;
  document.querySelectorAll('.event-card').forEach(el => el.classList.remove('active'));
  const active = document.querySelector(`.event-card[data-idx='${index}']`);
  if (active) active.classList.add('active');
  refreshSelectedMarker(index);
  updateInfoOverlay(e);
  DOM.slider.value = index;
  setCurrentIndex(index);
}

function renderList() {
  const frag = document.createDocumentFragment();
  if (!state.events.length) {
    const div = document.createElement('div');
    div.className = 'event-card';
    div.innerHTML = `<div style="font-weight:600">暂无事件数据</div>
                     <div class="event-meta">请从搜索框选择人物或补充数据</div>`;
    frag.appendChild(div);
    DOM.yearLabel.textContent = '—';
    DOM.infoOverlay.textContent = '暂无事件数据';
  } else {
    state.events.forEach((e, idx) => {
      const div = document.createElement('div');
      div.className = 'event-card';
      div.dataset.idx = idx;
      div.innerHTML = `<div style="font-weight:600">${e.year} · ${e.title}</div>
                       <div class="event-meta">${e.place} · 年龄：${e.age}</div>
                       <div style="color:#333">${e.detail}</div>`;
      frag.appendChild(div);
    });
  }
  DOM.eventsList.innerHTML = '';
  DOM.eventsList.appendChild(frag);
}

function selectIndex(idx) {
  updateUI(idx);
  stopPlay();
}

function startPlay() {
  if (state.playTimer) return;
  DOM.playBtn.textContent = '暂停';
  DOM.playBtn.classList.add('pause');
  const timer = setInterval(() => {
    let next = state.currentIndex + 1;
    if (next >= state.events.length) next = 0;
    setCurrentIndex(next);
    updateUI(next);
  }, PLAY_INTERVAL_MS);
  setPlayTimer(timer);
}

function stopPlay() {
  if (state.playTimer) {
    clearInterval(state.playTimer);
    setPlayTimer(null);
    DOM.playBtn.textContent = '播放';
    DOM.playBtn.classList.remove('pause');
  }
}

function handleEventListClick(e) {
  const card = e.target.closest('.event-card');
  if (!card) return;
  const idx = Number(card.dataset.idx);
  selectIndex(idx);
}

function bindUIEvents() {
  DOM.eventsList.addEventListener('click', handleEventListClick);
  DOM.slider.addEventListener('input', (ev) => {
    const idx = Number(ev.target.value);
    updateUI(idx);
    stopPlay();
  });
  DOM.playBtn.addEventListener('click', () => {
    if (state.playTimer) stopPlay(); else startPlay();
  });
}

// 搜索建议逻辑
function renderSuggestions(list) {
  if (!list.length) { DOM.suggestEl.style.display = 'none'; DOM.suggestEl.innerHTML = ''; return; }
  DOM.suggestEl.style.display = 'block';
  DOM.suggestEl.innerHTML = list.map((n, i) => `<div class="suggest-item${i===state.activeSuggestIndex?' active':''}" data-name="${n}">${n}</div>`).join('');
  DOM.suggestEl.querySelectorAll('.suggest-item').forEach(item => {
    item.addEventListener('click', () => selectPerson(item.dataset.name));
  });
}

function filterAndShow(q) {
  const typed = (q || '').trim();
  const term = typed.toLowerCase();
  let matches = state.allNames
    .filter(n => n.toLowerCase().includes(term))
    .slice(0, SUGGEST_LIMIT);
  // 如果输入非空且不与已有名称完全匹配，则把输入项置于首位，便于点击提交查询
  const existsExact = state.allNames.some(n => n.toLowerCase() === term);
  if (typed && !existsExact) {
    // 避免重复插入（若列表首项已等于输入则不需重复）
    if (!matches.length || matches[0].toLowerCase() !== term) {
      matches = [typed, ...matches];
    }
  }
  state.filteredNames = matches;
  state.activeSuggestIndex = -1;
  renderSuggestions(state.filteredNames);
}

// 轻量加载横幅与禁用控件
function setControlsDisabled(disabled) {
  if (DOM.searchInput) DOM.searchInput.disabled = !!disabled;
  if (DOM.playBtn) DOM.playBtn.disabled = !!disabled;
}

function showLoadingBanner(name) {
  let el = document.getElementById('loading-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'loading-banner';
    document.body.appendChild(el);
  }
  el.textContent = `正在加载 “${name}” 的人物轨迹… 当前显示为上次结果`;
  document.body.classList.add('is-loading');
  document.body.setAttribute('aria-busy', 'true');
  setControlsDisabled(true);
}

function hideLoadingBanner() {
  const el = document.getElementById('loading-banner');
  if (el) el.remove();
  document.body.classList.remove('is-loading');
  document.body.removeAttribute('aria-busy');
  setControlsDisabled(false);
}

async function loadPerson(name) {
  try {
    // 避免重复同名加载；设置加载态与横幅
    if (state.isLoading && state.pendingName === name) return;
    setLoadingState(true, name);
    showLoadingBanner(name);
    DOM.personTitle.textContent = `${name}的一生轨迹示例`;
    // 如果缓存为空（没有键）或为长度为 0 的数组，则强制重新请求，避免“同名重试不发请求”问题
    const cached = state.peopleCache[name];
    const shouldRefetch = !cached || (Array.isArray(cached) && cached.length === 0);
    if (shouldRefetch) {
      const p = await fetchPerson(name);
      setPersonData(name, p.events || [], p.style);
    } else {
      setPersonData(name, state.peopleCache[name], state.personStyles[name]);
    }
    DOM.slider.max = Math.max(0, state.events.length - 1);
    renderList();
    drawMarkersAndLine();
    if (state.events.length) updateUI(0); else {
      DOM.infoOverlay.textContent = '暂无事件数据';
    }
  } catch (e) {
    console.error('加载人物失败：', e);
    if (DOM.status) DOM.status.textContent = `加载 ${name} 失败`;
  } finally {
    setLoadingState(false, null);
    hideLoadingBanner();
  }
}

function selectPerson(name) {
  DOM.searchInput.value = name;
  DOM.suggestEl.style.display = 'none';
  loadPerson(name);
}

function bindSuggestEvents() {
  DOM.searchInput.addEventListener('input', (ev) => filterAndShow(ev.target.value));
  // 兼容中文输入法：在合成结束时刷新下拉，确保“未匹配输入”出现
  DOM.searchInput.addEventListener('compositionend', (ev) => filterAndShow(ev.target.value));
  DOM.searchInput.addEventListener('focus', (ev) => filterAndShow(ev.target.value));
  DOM.searchInput.addEventListener('keydown', (ev) => {
    if (ev.key === 'ArrowDown') {
      state.activeSuggestIndex = Math.min(state.filteredNames.length - 1, state.activeSuggestIndex + 1);
      renderSuggestions(state.filteredNames);
      ev.preventDefault();
    } else if (ev.key === 'ArrowUp') {
      state.activeSuggestIndex = Math.max(0, state.activeSuggestIndex - 1);
      renderSuggestions(state.filteredNames);
      ev.preventDefault();
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      let name = '';
      if (state.activeSuggestIndex >= 0) {
        name = state.filteredNames[state.activeSuggestIndex] || '';
      } else {
        const typed = (DOM.searchInput.value || '').trim();
        if (typed) name = typed; else if (state.filteredNames.length > 0) name = state.filteredNames[0];
      }
      if (name) {
        selectPerson(name);
        DOM.suggestEl.style.display = 'none';
      }
    } else if (ev.key === 'Escape') {
      DOM.suggestEl.style.display = 'none';
    }
  });
  document.addEventListener('click', (ev) => {
    if (!DOM.suggestEl.contains(ev.target) && ev.target !== DOM.searchInput) DOM.suggestEl.style.display = 'none';
  });
}

async function init() {
  initMap();
  bindUIEvents();
  bindSuggestEvents();

  // 加载搜索建议（后端 names）
  state.allNames = Array.from(new Set(await fetchNames()));
  const defaultName = state.allNames.includes(state.currentPerson) ? state.currentPerson : (state.allNames[0] || '毛泽东');
  await loadPerson(defaultName);
  filterAndShow('');
}

init();