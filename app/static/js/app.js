// ─── State ───
let state = {
  categories: [], currentCatId: null, settings: {}, events: [],
  lang: {},
  icons: [
    '🎂','🎉','💝','🎄','🎓','✈','💼','🏠','🚗','📅','⭐','❤','🎵','📚','💪','🌟','🎯','🕐','🌸','☀',
    '🎁','🎃','🎆','🌙','⚡','🔥','💧','🌿','🍀','🌻','🐣','🐾','🦋','💎','🎪','🎸','🎮','✏','📷','🔔',
    '🏆','🌍','🚀','⏰','💡','🔑','🎈','🍰','☕','🌈',
  ],
  quoteIntervalId: null, wallpaperTimerId: null, settingsDirty: false,
  pendingWallpaper: null, pendingHeaderBg: null,
  pendingEventImages: [], currentWallpaper: '',
  headerBgFor: 'body',  // 'body' or 'header'
  pageName: 'daysmatter',
  wishes: [], editorSteps: [], editorImages: [], pendingImagePreviews: [],
  dragWishId: null, currentTab: 'all', quillInstance: null,
  memos: [], memoStarFilter: false, currentMemoId: null, memoQuill: null,
};

const WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];

// ─── i18n ───
function t(key, params) {
  let text = state.lang[key] || key;
  if (params) for (const [k,v] of Object.entries(params)) text = text.replace(`{${k}}`, v);
  return text;
}

function translateDOM(root) {
  (root || document).querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.getAttribute('data-i18n')); });
  (root || document).querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.getAttribute('data-i18n-placeholder')); });
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.getAttribute('data-i18n')); });
}

async function loadLang(langCode) {
  try {
    const res = await fetch('/api/lang/zh');
    const zhData = await res.json();
    if (langCode === 'en') {
      // Reverse mapping: Chinese stored text → English display
      state.lang = {};
      for (const [en, zh] of Object.entries(zhData)) {
        state.lang[zh] = en;
      }
    } else {
      state.lang = zhData;
    }
  } catch (e) { state.lang = {}; }
  translateDOM();
}

// ─── Init ───
async function init() {
  state.pageName = document.body.dataset.page || 'daysmatter';
  highlightNav();
  await loadSettings();
  await loadLang(state.settings.language || 'zh');
  if (state.pageName === 'daysmatter') await initDaysmatter();
  if (state.pageName === 'wishlist') await initWishlist();
  if (state.pageName === 'memo') await initMemo();
  if (state.pageName === 'settings') await initSettingsPage();
  initNixieClock(); startClock(); startQuoteRotation(); applyWallpaper(); applyHeaderBg();
}

function highlightNav() {
  document.querySelectorAll('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.page === state.pageName);
  });
}

// ─── Daysmatter Page ───
async function initDaysmatter() {
  await loadCategories();
  const allCat = state.categories.find(c => c.type === 'fixed' && c.name === '全部');
  state.currentCatId = allCat ? String(allCat.id) : '2';
  renderCategories(); await loadEvents();
}
async function loadCategories() { const r = await fetch('/api/categories'); state.categories = await r.json(); }
function renderCategories() {
  const el = document.getElementById('categoryList'); if (!el) return;
  el.innerHTML = state.categories.map(c => {
    const cls = state.currentCatId === String(c.id) ? 'active' : '';
    return `<button class="sidebar-item ${cls}" onclick="selectCategory(${c.id})">${escapeHtml(t(c.name))}</button>`;
  }).join('');
}
function selectCategory(catId) { state.currentCatId = String(catId); renderCategories(); loadEvents(); }

async function loadEvents() {
  const params = new URLSearchParams();
  if (state.currentCatId) params.set('category_id', state.currentCatId);
  const r = await fetch('/api/events?' + params.toString());
  state.events = await r.json();
  renderEvents();
  const title = document.getElementById('contentTitle');
  if (title) {
    const cat = state.categories.find(c => String(c.id) === state.currentCatId);
    title.textContent = cat ? t(cat.name) : t('All');
  }
}

function renderEvents() {
  const el = document.getElementById('eventList'); if (!el) return;
  if (!state.events.length) { el.innerHTML = `<div class="empty-state">${t('No events yet.')}</div>`; return; }
  el.innerHTML = state.events.map(ev => {
    let rowStyle = '';
    if (ev.days < 0) rowStyle = `background:${state.settings.expired_color||'rgb(150,150,150)'};`;
    else if (ev.days <= 30) rowStyle = `background:${state.settings.soon_color||'rgb(255,199,206)'};`;
    else if (ev.days <= 90) rowStyle = `background:${state.settings.mid_color||'rgb(255,217,102)'};`;
    const hl = ev.highlight ? ' highlight' : '';
    const icon = state.icons.includes(ev.icon) ? ev.icon : '📅';
    const note = ev.note ? `<div class="event-card-note">${escapeHtml(ev.note)}</div>` : '';
    const repeatReminder = (ev.days === 0 && ev.repeat_type !== 'none' && ev.repeat_interval > 0)
      ? `<span class="repeat-reminder">提醒:明天将会自动重复该倒数项!</span>` : '';
    return `<div class="event-card${hl}" style="${rowStyle}border-left-color:${ev.color||'#5a7fa0'};" onclick="openEventModal(${ev.id})">
      <div class="event-card-icon">${icon}</div><div class="event-card-info"><div class="event-card-name">${escapeHtml(ev.name)}</div>${note}</div>
      <div class="event-card-days">${ev.days_text}${repeatReminder}</div></div>`;
  }).join('');
}

// ─── Settings Page ───
async function initSettingsPage() {
  document.getElementById('setWallpaperRandom').checked = state.settings.wallpaper_random !== false;
  document.getElementById('setWallpaperInterval').value = state.settings.wallpaper_interval || 1;
  document.getElementById('setQuoteInterval').value = state.settings.quote_interval || 10;
  document.getElementById('setExpiredColor').value = state.settings.expired_color || 'rgb(150,150,150)';
  document.getElementById('setSoonColor').value = state.settings.soon_color || 'rgb(255,199,206)';
  document.getElementById('setMidColor').value = state.settings.mid_color || 'rgb(255,217,102)';
  document.getElementById('setLanguage').value = state.settings.language || 'zh';
  document.getElementById('setDebugLogging').checked = state.settings.debug_logging === true;
  const bgOpacity = state.settings.bg_opacity != null ? state.settings.bg_opacity : 0.6;
  document.getElementById('setBgOpacity').value = bgOpacity;
  document.getElementById('bgOpacityVal').textContent = bgOpacity;
  // bg_type
  document.getElementById('setBgType').value = state.settings.bg_type || 'image';
  document.getElementById('setBgColor').value = state.settings.bg_color || '#f8f6f2';
  onBgTypeChange();
  // header bg
  document.getElementById('setHeaderBgType').value = state.settings.header_bg_type || 'image';
  document.getElementById('setHeaderBgColor').value = state.settings.header_bg_color || '#ffffff';
  onHeaderBgTypeChange();
  try {
    const r = await fetch('/settings/api/quotes');
    const d = await r.json();
    document.getElementById('setQuotes').value = (d.quotes||[]).join('\n\n');
  } catch(e){}
  state.settingsDirty = false; updateSaveButton();
}

function toggleSettingsSection(header) { header.parentElement.classList.toggle('open'); }

function onBgTypeChange() {
  const v = document.getElementById('setBgType').value;
  document.getElementById('bgColorRow').style.display = v === 'color' ? '' : 'none';
}
function onHeaderBgTypeChange() {
  const v = document.getElementById('setHeaderBgType').value;
  document.getElementById('headerBgImageRow').style.display = v === 'image' ? '' : 'none';
  document.getElementById('headerBgColorRow').style.display = v === 'color' ? '' : 'none';
}

function toggleDebugLogging() {
  const cb = document.getElementById('setDebugLogging');
  if (cb.checked) {
    if (!confirm(t('Debug logging warning'))) {
      cb.checked = false;
      return;
    }
  }
  markSettingsDirty();
}

function updateBgOpacityLive() {
  const val = document.getElementById('setBgOpacity').value;
  document.getElementById('bgOpacityVal').textContent = val;
  document.documentElement.style.setProperty('--bg-opacity', val);
}

function applyBgOpacity(opacity) {
  const val = opacity != null ? opacity : 0.6;
  document.documentElement.style.setProperty('--bg-opacity', val);
}

// ─── Settings Load/Save ───
async function loadSettings() {
  try {
    const r = await fetch('/settings/api/settings');
    state.settings = await r.json();
    state.currentWallpaper = state.settings.wallpaper || '';
  } catch(e) {}
}
function markSettingsDirty() { state.settingsDirty = true; updateSaveButton(); }
function updateSaveButton() { const b = document.getElementById('btnSaveSettings'); if (b) b.disabled = !state.settingsDirty; }

async function saveSettings() {
  if (!state.settingsDirty) return;
  const btn = document.getElementById('btnSaveSettings');
  const origText = btn.textContent;
  btn.textContent = t('Saving...');
  btn.disabled = true;

  const data = {
    wallpaper_random: document.getElementById('setWallpaperRandom').checked,
    wallpaper_interval: parseFloat(document.getElementById('setWallpaperInterval').value)||1,
    quote_interval: parseInt(document.getElementById('setQuoteInterval').value)||10,
    expired_color: document.getElementById('setExpiredColor').value,
    soon_color: document.getElementById('setSoonColor').value,
    mid_color: document.getElementById('setMidColor').value,
    language: document.getElementById('setLanguage').value,
    wallpaper: state.currentWallpaper,
    bg_type: document.getElementById('setBgType').value,
    bg_color: document.getElementById('setBgColor').value,
    header_bg_type: document.getElementById('setHeaderBgType').value,
    header_bg: state.settings.header_bg || '',
    header_bg_color: document.getElementById('setHeaderBgColor').value,
    debug_logging: document.getElementById('setDebugLogging').checked,
    bg_opacity: parseFloat(document.getElementById('setBgOpacity').value),
  };

  try {
    const r = await fetch('/settings/api/settings', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
    const d = await r.json();
    if (d.status === 'success') {
      await fetch('/settings/api/quotes', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({texts: document.getElementById('setQuotes').value}) });
      await loadSettings();
      await loadLang(state.settings.language||'zh');
      applyWallpaper(); applyHeaderBg(); startQuoteRotation();
      if (state.pageName === 'daysmatter') { renderCategories(); loadEvents(); }
      // Show success on button
      btn.textContent = t('Saved!');
      btn.classList.add('success');
      setTimeout(() => { btn.textContent = origText; btn.classList.remove('success'); btn.disabled = false; }, 2000);
    } else {
      btn.textContent = origText; btn.disabled = false;
    }
  } catch(e) { btn.textContent = origText; btn.disabled = false; }
  state.settingsDirty = false;
}

// ─── Wallpaper (with localStorage lifecycle) ───
const BG_STORAGE_KEY = 'daysmatter_bg';
const BG_TIME_KEY = 'daysmatter_bg_time';

function wallpaperUrl(fn) { return fn ? `/api/wallpaper-file/${fn}` : ''; }

function getStoredWallpaper() {
  return localStorage.getItem(BG_STORAGE_KEY) || '';
}
function setStoredWallpaper(fn) {
  localStorage.setItem(BG_STORAGE_KEY, fn);
  localStorage.setItem(BG_TIME_KEY, Date.now().toString());
}

function applyWallpaperToDOM() {
  const s = state.settings;
  if (s.bg_type === 'color') {
    document.body.style.backgroundImage = '';
    document.body.style.backgroundColor = s.bg_color || '#f8f6f2';
  } else {
    document.body.style.backgroundColor = '';
    const bg = getStoredWallpaper() || s.wallpaper || '';
    if (bg) {
      document.body.style.backgroundImage = `url('${wallpaperUrl(bg)}')`;
    } else {
      document.body.style.backgroundImage = '';
    }
  }
}

function setWallpaperImage(fn) {
  if (!fn) { document.body.style.backgroundImage = ''; return; }
  document.body.style.backgroundImage = `url('${wallpaperUrl(fn)}')`;
}

function startWallpaperRotation() {
  stopWallpaperRotation();
  checkWallpaper();
  const h = parseFloat(state.settings.wallpaper_interval || 1);
  if (h > 0) state.wallpaperTimerId = setInterval(checkWallpaper, h * 3600 * 1000);
}
function stopWallpaperRotation() {
  if (state.wallpaperTimerId) { clearInterval(state.wallpaperTimerId); state.wallpaperTimerId = null; }
}

async function checkWallpaper() {
  const now = Date.now();
  const lastChange = parseInt(localStorage.getItem(BG_TIME_KEY) || '0');
  const interval = parseFloat(state.settings.wallpaper_interval || 1) * 3600 * 1000;

  if (!lastChange || (now - lastChange) >= interval) {
    await rotateWallpaper();
  } else {
    // Apply stored wallpaper — no rotation needed
    const stored = getStoredWallpaper();
    if (stored) {
      setWallpaperImage(stored);
      state.currentWallpaper = stored;
    }
  }
}

async function rotateWallpaper() {
  try {
    const r = await fetch('/api/backgrounds');
    const files = await r.json();
    if (files.length) {
      const p = files[Math.floor(Math.random() * files.length)];
      setStoredWallpaper(p.filename);
      state.settings.wallpaper = p.filename;
      state.currentWallpaper = p.filename;
      setWallpaperImage(p.filename);
    }
  } catch (e) {}
}

function applyWallpaper() {
  if (state.settings.wallpaper_random !== false) startWallpaperRotation();
  else { stopWallpaperRotation(); checkWallpaper(); }
  applyHeaderBg();
  applyBgOpacity(state.settings.bg_opacity);
}

function setWallpaperFromUI(fn) {
  setStoredWallpaper(fn);
  state.currentWallpaper = fn;
  setWallpaperImage(fn);
}

// Keep UI helpers unchanged
function updateWallpaperPreview() {
  const preview = document.getElementById('wallpaperPreview'); if (!preview) return;
  const wp = state.pendingWallpaper || state.currentWallpaper;
  if (wp) { preview.style.backgroundImage = `url('${wallpaperUrl(wp)}')`; preview.textContent = ''; }
  else { preview.style.backgroundImage = ''; preview.textContent = t('Preview'); }
}
async function loadWallpaperGallery() {
  const el = document.getElementById('wallpaperGallery'); if (!el) return;
  const r = await fetch('/api/backgrounds'); const files = await r.json();
  const cur = state.pendingWallpaper || state.currentWallpaper;
  el.innerHTML = files.map(f => {
    const cls = f.filename === cur ? 'selected' : '';
    return `<div class="wallpaper-gallery-item ${cls}" onclick="selectWallpaper('${escapeHtml(f.filename)}')" title="${escapeHtml(f.filename)}"><img src="${wallpaperUrl(f.filename)}" loading="lazy" /></div>`;
  }).join('');
}
function selectWallpaper(fn) { state.pendingWallpaper = null; state.currentWallpaper = fn; updateWallpaperPreview(); loadWallpaperGallery(); }
async function onWallpaperFileSelected() {
  const f = document.getElementById('wallpaperFile').files[0]; if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  const r = await fetch('/api/upload-wallpaper', { method:'POST', body:fd }); const d = await r.json();
  if (d.filename) { state.pendingWallpaper = d.filename; state.currentWallpaper = d.filename; updateWallpaperPreview(); await loadWallpaperGallery(); }
  document.getElementById('wallpaperFile').value = '';
}
async function clearWallpaper() {
  if (state.currentWallpaper && state.currentWallpaper.startsWith('wp_')) {
    try { await fetch(`/api/wallpaper/${encodeURIComponent(state.currentWallpaper)}`, { method:'DELETE' }); } catch(e){}
  }
  state.currentWallpaper = ''; state.pendingWallpaper = null;
  localStorage.removeItem(BG_STORAGE_KEY); localStorage.removeItem(BG_TIME_KEY);
  updateWallpaperPreview(); loadWallpaperGallery();
}

function applyWallpaperSelection() {
  if (state.headerBgFor === 'header') {
    state.settings.header_bg = state.currentWallpaper;
    state.settings.header_bg_type = 'image';
    applyHeaderBg();
    markSettingsDirty();
    if (state.pageName === 'settings') {
      saveSettings();
    } else {
      fetch('/settings/api/settings', {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({header_bg: state.currentWallpaper, header_bg_type: 'image'})
      });
    }
  } else {
    markSettingsDirty();
    state.settings.wallpaper = state.currentWallpaper;
    state.settings.bg_type = 'image';
    setWallpaperFromUI(state.currentWallpaper);
    if (state.pageName === 'settings') {
      saveSettings();
    } else {
      applyWallpaperToDOM();
      fetch('/settings/api/settings', {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({wallpaper: state.currentWallpaper, bg_type: 'image'})
      }).then(() => loadSettings());
    }
  }
  closeWallpaperManager();
}

function applyHeaderBgSelection() {
  state.settings.header_bg = state.currentWallpaper;
  state.settings.header_bg_type = 'image';
  applyHeaderBg();
  markSettingsDirty();
}

// ─── Header Background ───
function applyHeaderBg() {
  const s = state.settings;
  const header = document.getElementById('header');
  if (!header) return;
  header.classList.remove('with-bg-image', 'with-bg-color');
  header.style.backgroundImage = '';
  header.style.backgroundColor = '';
  if (s.header_bg_type === 'color') {
    header.classList.add('with-bg-color');
    header.style.backgroundColor = s.header_bg_color || '#ffffff';
  } else if (s.header_bg) {
    header.classList.add('with-bg-image');
    header.style.backgroundImage = `url('${wallpaperUrl(s.header_bg)}')`;
  }
  // If image type but no file, keep default transparent/white header
}

function openWallpaperManagerForHeader() {
  state.headerBgFor = 'header';
  state.currentWallpaper = state.settings.header_bg || '';
  state.pendingWallpaper = null;
  updateWallpaperPreview();
  loadWallpaperGallery();
  document.getElementById('wallpaperManagerOverlay').classList.add('show');
  translateDOM();
}

// ─── Event Modal ───
async function openEventModal(evId) {
  document.getElementById('eventModalOverlay').classList.add('show');
  document.getElementById('eventModalTitle').textContent = evId ? t('Edit Event') : t('Add Event');
  document.getElementById('evId').value = evId || ''; state.pendingEventImages = [];
  const sel = document.getElementById('evCategory');
  // Only show custom categories (which includes "默认" id=4)
  sel.innerHTML = state.categories.filter(c=>c.type==='custom').map(c=>`<option value="${c.id}">${escapeHtml(t(c.name))}</option>`).join('');
  if (!evId) sel.value = '4'; // Default to "默认" for new events
  renderIconPicker();
  if (evId) {
    const r = await fetch(`/api/events/${evId}`); const ev = await r.json();
    document.getElementById('evName').value = ev.name||''; document.getElementById('evDate').value = ev.target_date||'';
    document.getElementById('evCategory').value = ev.category_id;
    document.getElementById('evPinned').checked = !!ev.is_pinned; document.getElementById('evShowOnHome').checked = !!ev.show_on_home;
    // Repeat: extract interval and unit
    if (ev.repeat_type && ev.repeat_type !== 'none' && ev.repeat_interval > 0) {
      document.getElementById('evRepeatInterval').value = ev.repeat_interval;
      document.getElementById('evRepeatUnit').value = ev.repeat_type;
    } else {
      document.getElementById('evRepeatInterval').value = 0;
      document.getElementById('evRepeatUnit').value = 'day';
    }
    document.getElementById('evIncludeStart').checked = !!ev.include_start_day; document.getElementById('evHighlight').checked = !!ev.highlight;
    document.getElementById('evColor').value = ev.color||'#4A90D9'; document.getElementById('evIcon').value = ev.icon||'default';
    document.getElementById('evNote').value = ev.note||'';
    state.pendingEventImages = parseImages(ev.image); renderEventPreviews(); selectIcon(ev.icon||'default');
    const cat = state.categories.find(c=>String(c.id)===state.currentCatId);
    const isArchive = cat && cat.name==='归档';
    const ba = document.getElementById('btnArchive'); ba.style.display='inline-block';
    ba.textContent = isArchive ? t('Restore') : t('Archive event'); ba.onclick = isArchive ? unarchiveEvent : archiveEvent;
    document.getElementById('btnDelete').style.display='inline-block';
  } else {
    ['evName','evDate'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('evPinned').checked=false; document.getElementById('evShowOnHome').checked=false;
    document.getElementById('evRepeatInterval').value=0; document.getElementById('evRepeatUnit').value='day';
    document.getElementById('evIncludeStart').checked=false; document.getElementById('evHighlight').checked=false;
    document.getElementById('evColor').value='#4A90D9'; document.getElementById('evIcon').value='default';
    document.getElementById('evNote').value=''; document.getElementById('imagePreview').innerHTML=''; document.getElementById('evImageFile').value='';
    document.getElementById('btnArchive').style.display='none'; document.getElementById('btnDelete').style.display='none';
    selectIcon('default');
  }
  // Show/hide image section based on create vs edit
  const evImgSection = document.getElementById('evImageSection');
  if (evImgSection) evImgSection.style.display = evId ? '' : 'none';
  translateDOM(document.getElementById('eventModal'));
}

function closeEventModal() { document.getElementById('eventModalOverlay').classList.remove('show'); }

function onRepeatChange() {
  const val = parseInt(document.getElementById('evRepeatInterval').value) || 0;
  if (val > 0 && !document.getElementById('evRepeatInterval').dataset.warned) {
    // Just UI feedback — input is self-explanatory
  }
}

function parseImages(v) { if(!v) return[]; try{return JSON.parse(v);}catch(e){return[];} }
function initImagePreview(containerId, images, getUrl) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!images.length) { el.innerHTML = ''; return; }
  const galleryId = 'gallery-' + containerId;
  el.innerHTML = images.map((img, i) => {
    const url = getUrl(img, i);
    return `<div class="preview-item">
      <a href="${url}" class="glightbox-event" data-gallery="${galleryId}"><img src="${url}" loading="lazy" /></a>
      <span class="preview-del" onclick="event.stopPropagation();removePendingEventImage(${i})">✕</span>
    </div>`;
  }).join('');
  setTimeout(() => {
    if (typeof GLightbox !== 'undefined') GLightbox({ selector: '.glightbox-event', touchNavigation: true, loop: false });
  }, 300);
}

function renderEventPreviews() {
  const evId = document.getElementById('evId').value;
  initImagePreview('imagePreview', state.pendingEventImages, (img) => {
    return evId ? `/api/event-image/${evId}/${img}` : `/api/uploads/${img}`;
  });
}
function removePendingEventImage(i) { state.pendingEventImages.splice(i,1); renderEventPreviews(); }
async function uploadEventImage() {
  const fi = document.getElementById('evImageFile'); if(!fi.files.length) return;
  const evId = document.getElementById('evId').value;
  for(const f of fi.files) {
    const fd=new FormData(); fd.append('file',f);
    if (evId) fd.append('event_id', evId);
    const r=await fetch('/api/upload',{method:'POST',body:fd}); const d=await r.json();
    if(d.filename&&!state.pendingEventImages.includes(d.filename)) state.pendingEventImages.push(d.filename);
  }
  fi.value=''; renderEventPreviews();
}

async function saveEvent() {
  const evId=document.getElementById('evId').value; await uploadEventImage();
  const interval = parseInt(document.getElementById('evRepeatInterval').value) || 0;
  const repeatType = interval > 0 ? document.getElementById('evRepeatUnit').value : 'none';
  const data={
    name:document.getElementById('evName').value, target_date:document.getElementById('evDate').value,
    category_id:parseInt(document.getElementById('evCategory').value),
    is_pinned:document.getElementById('evPinned').checked?1:0, show_on_home:document.getElementById('evShowOnHome').checked?1:0,
    repeat_type: repeatType, repeat_interval: interval > 0 ? interval : 1,
    include_start_day:document.getElementById('evIncludeStart').checked?1:0, highlight:document.getElementById('evHighlight').checked?1:0,
    color:document.getElementById('evColor').value, icon:document.getElementById('evIcon').value,
    note:document.getElementById('evNote').value, image:JSON.stringify(state.pendingEventImages),
  };
  if(!data.name.trim()){alert(t('Please enter event name'));return;}
  if(!data.target_date){alert(t('Please select a target date'));return;}
  const url=evId?`/api/events/${evId}`:'/api/events', method=evId?'PUT':'POST';
  await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  closeEventModal(); loadEvents();
}

async function deleteEventConfirm() {
  const evId=document.getElementById('evId').value; if(!evId)return;
  if(!confirm(t('Confirm delete event?')))return;
  if(!confirm(t('Confirm again? This cannot be undone.')))return;
  try {
    const r = await fetch(`/api/events/${evId}`,{method:'DELETE'});
    if (!r.ok) { alert('删除失败'); return; }
  } catch(e) { alert('删除失败'); return; }
  closeEventModal(); loadEvents();
}
async function archiveEvent() {
  const evId=document.getElementById('evId').value; if(!evId||!confirm(t('Confirm archive?')))return;
  await fetch(`/api/events/${evId}/archive`,{method:'POST'}); closeEventModal(); loadEvents();
}
async function unarchiveEvent() {
  const evId=document.getElementById('evId').value; if(!evId||!confirm(t('Confirm restore?')))return;
  await fetch(`/api/events/${evId}/unarchive`,{method:'POST'}); closeEventModal(); loadEvents();
}
document.getElementById('evImageFile')?.addEventListener('change', async()=>{await uploadEventImage();});

// ─── Icon Picker ───
function renderIconPicker() {
  const el=document.getElementById('iconPicker'), cur=document.getElementById('evIcon').value;
  el.innerHTML=state.icons.map(icon=>`<div class="icon-option${icon===cur?' selected':''}" onclick="selectIcon('${icon}')">${icon}</div>`).join('');
}
function selectIcon(icon){document.getElementById('evIcon').value=icon;renderIconPicker();}

// ─── Sub-modals ───
async function openWallpaperManager() {
  state.headerBgFor = 'body';
  state.currentWallpaper = state.settings.wallpaper||''; state.pendingWallpaper=null;
  updateWallpaperPreview(); await loadWallpaperGallery();
  document.getElementById('wallpaperManagerOverlay').classList.add('show');
  // Set modal title
  const title = document.querySelector('#wallpaperManagerOverlay .modal-header h3');
  if (title) title.textContent = t('Wallpaper Management');
  translateDOM();
}
async function openWallpaperManagerForHeader() {
  state.headerBgFor = 'header';
  state.currentWallpaper = state.settings.header_bg || '';
  state.pendingWallpaper = null;
  updateWallpaperPreview();
  loadWallpaperGallery();
  document.getElementById('wallpaperManagerOverlay').classList.add('show');
  const title = document.querySelector('#wallpaperManagerOverlay .modal-header h3');
  if (title) title.textContent = t('Header Background');
  translateDOM();
}
function closeWallpaperManager(){
  document.getElementById('wallpaperManagerOverlay').classList.remove('show');
  state.headerBgFor = 'body';
}
async function openCategoryManager() {
  await loadCategories(); renderCatManager();
  document.getElementById('catManagerOverlay').classList.add('show'); translateDOM();
}
function closeCategoryManager(){document.getElementById('catManagerOverlay').classList.remove('show');}
function renderCatManager() {
  const el=document.getElementById('catManager');
  el.innerHTML=state.categories.filter(c=>c.type==='custom').map(c=>
    `<div class="cat-manager-item"><span class="cat-name">${escapeHtml(t(c.name))}</span><span class="cat-actions">
      <button class="cat-edit-btn" onclick="renameCategory(${c.id},'${escapeHtml(c.name)}')">✎</button>
      <button class="cat-del-btn" onclick="deleteCategoryFromManager(${c.id})">✕</button></span></div>`).join('');
}
async function addCategoryFromManager() {
  const inp=document.getElementById('newCatName'), name=inp.value.trim(); if(!name)return;
  await fetch('/api/categories',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  inp.value=''; await loadCategories(); renderCategories(); renderCatManager(); markSettingsDirty();
}
async function renameCategory(id,cur){const n=prompt(t('Please enter event name'),cur);if(!n||!n.trim())return;
  await fetch(`/api/categories/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n.trim()})});
  await loadCategories(); renderCategories(); renderCatManager(); markSettingsDirty();}
async function deleteCategoryFromManager(id){if(!confirm(t('Confirm delete category?')))return;
  await fetch(`/api/categories/${id}`,{method:'DELETE'}); await loadCategories(); renderCategories(); renderCatManager(); markSettingsDirty();}

// ─── Logout ───
function confirmLogout() {
  document.getElementById('logoutConfirmOverlay').classList.add('show');
  translateDOM(document.getElementById('logoutConfirmOverlay'));
}
function closeLogoutConfirm() {
  document.getElementById('logoutConfirmOverlay').classList.remove('show');
}
function doLogout() {
  // Clear user-related localStorage (keep wallpaper settings)
  localStorage.removeItem('daysmatter_bg');
  localStorage.removeItem('daysmatter_bg_time');
  window.location.href = '/logout';
}

// ─── Backup ───
function downloadBackup(){
  const btn = document.activeElement;
  const origText = btn ? btn.textContent : '';
  if (btn) { btn.textContent = '正在打包中，请稍候...'; btn.disabled = true; }
  const a = document.createElement('a');
  a.href = '/settings/api/backup';
  a.download = '';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => { if (btn) { btn.textContent = origText; btn.disabled = false; } }, 3000);
}

// ─── Nixie Clock ───
function initNixieClock(){const c=document.getElementById('nixieClock');c.innerHTML='';
  for(let i=0;i<2;i++)c.appendChild(crNixie());const s1=document.createElement('span');s1.className='nixie-separator';s1.textContent=':';c.appendChild(s1);
  for(let i=0;i<2;i++)c.appendChild(crNixie());const s2=document.createElement('span');s2.className='nixie-separator';s2.textContent=':';c.appendChild(s2);
  for(let i=0;i<2;i++)c.appendChild(crNixie());}
function crNixie(){const s=document.createElement('span');s.className='nixie-char';s.textContent='0';return s;}
function updateNixieClock(ts){const cs=document.getElementById('nixieClock').querySelectorAll('.nixie-char');
  ts.replace(/:/g,'').split('').forEach((d,i)=>{if(i<cs.length&&cs[i].textContent!==d)cs[i].textContent=d;});}

// ─── Clock & Header ───
function startClock(){updateHeaderDisplay();setInterval(updateHeaderDisplay,1000);}
function updateHeaderDisplay(){
  const now = new Date();
  // Nixie clock — always shown
  updateNixieClock(String(now.getHours()).padStart(2,'0')+String(now.getMinutes()).padStart(2,'0')+String(now.getSeconds()).padStart(2,'0'));
  // Date line: "2026年05月10日 周日 新年还有272天"
  const y = now.getFullYear();
  const m = String(now.getMonth()+1).padStart(2,'0');
  const d = String(now.getDate()).padStart(2,'0');
  const wd = WEEKDAYS[now.getDay()];
  const nextYear = new Date(y+1, 0, 1);
  const daysUntilNewYear = Math.ceil((nextYear - now) / (1000*60*60*24));
  const dateEl = document.getElementById('headerDate');
  if (dateEl) {
    dateEl.textContent = `${y}年${m}月${d}日 ${t(wd)} ${t('{n} days until New Year', {n: daysUntilNewYear})}`;
  }
}

// ─── Quote ───
function startQuoteRotation(){if(state.quoteIntervalId)clearInterval(state.quoteIntervalId);
  updateQuote();state.quoteIntervalId=setInterval(updateQuote,parseInt(state.settings.quote_interval||10)*1000);}
async function updateQuote(){try{const r=await fetch('/settings/api/quotes');const d=await r.json();
  if(d.quotes&&d.quotes.length){const q=d.quotes[Math.floor(Math.random()*d.quotes.length)];const el=document.getElementById('headerQuote');
  el.style.opacity='0';setTimeout(()=>{el.textContent=q;el.style.opacity='1';},400);}}catch(e){}}

// ─── Overlay close ───
['eventModalOverlay','wallpaperManagerOverlay','catManagerOverlay',
 'wishEditorOverlay','journeyManagerOverlay','journeyEntryOverlay','logoutConfirmOverlay'].forEach(id=>{
  const el=document.getElementById(id); if(el) el.addEventListener('click',function(e){if(e.target===this){
    if(id==='eventModalOverlay')closeEventModal();
    else if(id==='wallpaperManagerOverlay')closeWallpaperManager();
    else if(id==='catManagerOverlay')closeCategoryManager();
    else if(id==='wishEditorOverlay')closeWishEditor();
    else if(id==='journeyManagerOverlay')closeJourneyManager();
    else if(id==='journeyEntryOverlay')closeJourneyEntryEditor();
    else if(id==='logoutConfirmOverlay')closeLogoutConfirm();
  }});
});

// ─── Wishlist ───

async function initWishlist() {
  state.currentTab = 'all';
  await loadCountdownOptions();
  await loadWishlist();
  document.getElementById('quickAddInput')?.addEventListener('keydown', onQuickAdd);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeWishDetail(); closeWishEditor(); }
  });
}

function switchTab(tab) {
  state.currentTab = tab;
  document.querySelectorAll('.wish-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  // Apply scroll class for achieved tab
  document.querySelectorAll('.quadrant').forEach(q => {
    q.classList.toggle('achieved-scroll', tab === 'achieved');
  });
  loadWishlist();
}

async function loadCountdownOptions() {
  try {
    const r = await fetch('/api/events?completed=0');
    const events = await r.json();
    const sel = document.getElementById('wishLinkedCountdown');
    if (!sel) return;
    // Keep first option (None)
    sel.innerHTML = '<option value="" data-i18n="None">' + t('None') + '</option>';
    events.forEach(ev => {
      sel.innerHTML += `<option value="${ev.id}">${escapeHtml(ev.name)} (${ev.days_text})</option>`;
    });
  } catch (e) {}
}

function onQuickAdd(e) {
  if (e.key === 'Enter') {
    const val = e.target.value.trim();
    if (!val) return;
    openWishEditor(null, { title: val });
    e.target.value = '';
  }
}

// ─── Wishlist Data ───

async function loadWishlist() {
  try {
    let url = '/wishlist/api/wishes';
    if (state.currentTab && state.currentTab !== 'all') {
      const statusMap = { draft: '0', active: '1', achieved: '2' };
      url += '?status=' + (statusMap[state.currentTab] || state.currentTab);
    }
    const r = await fetch(url);
    state.wishes = await r.json();
  } catch (e) { state.wishes = []; }
  renderMatrix();
  loadStats();
}

async function loadStats() {
  try {
    const r = await fetch('/wishlist/api/wishes/stats/summary');
    const d = await r.json();
    ['north_star','sleeping_giant','sweet_treat','leisure_cloud'].forEach(q => {
      const el = document.getElementById('stat' + q.split('_').map(w => w[0].toUpperCase()+w.slice(1)).join(''));
      if (el) el.textContent = d.quadrants?.[q] || 0;
    });
    const countEl = document.getElementById('achievedCountNum');
    if (countEl) countEl.textContent = d.achieved_count || 0;
  } catch (e) {}
}

// ─── Matrix Rendering ───

function renderMatrix() {
  const quadrants = {
    north_star: document.getElementById('quadrant-north_star'),
    sleeping_giant: document.getElementById('quadrant-sleeping_giant'),
    sweet_treat: document.getElementById('quadrant-sweet_treat'),
    leisure_cloud: document.getElementById('quadrant-leisure_cloud'),
  };
  // Clear all
  Object.values(quadrants).forEach(el => { if (el) el.innerHTML = ''; });

  state.wishes.forEach(w => {
    const q = getQuadrant(w.ripple_score, w.fire_score);
    const container = quadrants[q];
    if (!container) return;
    container.appendChild(createWishCard(w));
  });

  // Show empty states
  Object.entries(quadrants).forEach(([key, el]) => {
    if (el && el.children.length === 0) {
      el.innerHTML = '<div class="empty-state" style="padding:20px;font-size:0.85rem;">' + t('No wishes yet.') + '</div>';
    }
  });
}

function createWishCard(w) {
  const card = document.createElement('div');
  card.className = 'wish-card';
  if (w.status === 2) card.classList.add('achieved');
  card.draggable = true;
  card.dataset.wishId = w.id;
  card.onclick = (e) => {
    if (!card.dataset.wasDragged) openWishDetail(w.id);
    delete card.dataset.wasDragged;
  };

  card.addEventListener('dragstart', onWishDragStart);
  card.addEventListener('dragend', onWishDragEnd);

  const qName = t(getQuadrantDisplayName(getQuadrant(w.ripple_score, w.fire_score)));
  const pct = w.progress || 0;
  const stepInfo = w.steps?.length ? `${w.steps.filter(s=>s.is_completed).length}/${w.steps.length} 步` : '';

  // Countdown badge
  let countdownHtml = '';
  if (w.linked_days !== null && w.linked_days !== undefined) {
    if (w.linked_days >= 0) {
      countdownHtml = `<span class="wish-card-countdown upcoming">📅 ${t('days left', {n: w.linked_days})}</span>`;
    } else {
      countdownHtml = `<span class="wish-card-countdown overdue">📅 ${t('days overdue', {n: Math.abs(w.linked_days)})}</span>`;
    }
  }

  card.innerHTML = `
    <div class="wish-card-header">
      <span class="wish-card-title">${escapeHtml(w.title)}</span>
      <span class="wish-card-priority">⚡${w.priority || calcPriority(w.ripple_score, w.fire_score, w.difficulty)}</span>
    </div>
    ${pct > 0 ? `<div class="wish-card-progress-bar"><div class="wish-card-progress-fill" style="width:${pct}%;background:${getStatusColor(w.status)}"></div></div>` : ''}
    <div class="wish-card-meta">
      <span>${qName}</span>
      ${stepInfo ? `<span>📋 ${stepInfo}</span>` : ''}
      ${w.status === 2 ? '<span>✅</span>' : ''}
      ${countdownHtml}
    </div>
  `;
  return card;
}

function getStatusText(status) {
  const map = { 0: 'Draft', 1: 'Active', 2: 'Achieved' };
  return map[status] || 'Active';
}

function getQuadrant(ripple, fire) {
  ripple = ripple || 50; fire = fire || 50;
  if (ripple >= 50 && fire >= 50) return 'north_star';
  if (ripple >= 50 && fire < 50) return 'sleeping_giant';
  if (ripple < 50 && fire >= 50) return 'sweet_treat';
  return 'leisure_cloud';
}

function getQuadrantDisplayName(q) {
  const map = { north_star: 'North Star', sleeping_giant: 'Sleeping Giant', sweet_treat: 'Sweet Treat', leisure_cloud: 'Leisure Cloud' };
  return map[q] || q;
}

function getQuadrantColor(q) {
  const map = { north_star: '#FF6B6B', sleeping_giant: '#4D96FF', sweet_treat: '#6BCF7F', leisure_cloud: '#95A5A6' };
  return map[q] || '#ccc';
}

function getStatusColor(status) {
  const map = { 0: '#95A5A6', 1: '#4D96FF', 2: '#6BCF7F' };
  return map[status] || '#4D96FF';
}

function calcPriority(ripple, fire, difficulty) {
  ripple = ripple || 50; fire = fire || 50; difficulty = difficulty || 50;
  if (difficulty < 1) difficulty = 1;
  return Math.round((ripple * fire) / difficulty * 10) / 10;
}

// ─── Drag & Drop ───

function onWishDragStart(e) {
  state.dragWishId = parseInt(this.dataset.wishId);
  this.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', this.dataset.wishId);
}

function onWishDragEnd(e) {
  this.classList.remove('dragging');
  this.dataset.wasDragged = '1';
  state.dragWishId = null;
  document.querySelectorAll('.quadrant.drag-over').forEach(q => q.classList.remove('drag-over'));
}

function onMatrixDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const quadrant = e.currentTarget;
  if (!quadrant.classList.contains('drag-over')) {
    quadrant.classList.add('drag-over');
  }
}

async function onMatrixDrop(e, targetQuadrant) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const wishId = state.dragWishId || parseInt(e.dataTransfer.getData('text/plain'));
  if (!wishId) return;

  // Compute new ripple/fire based on quadrant center
  const centers = {
    north_star: { ripple: 75, fire: 75 },
    sleeping_giant: { ripple: 75, fire: 25 },
    sweet_treat: { ripple: 25, fire: 75 },
    leisure_cloud: { ripple: 25, fire: 25 },
  };
  const pos = centers[targetQuadrant] || { ripple: 50, fire: 50 };

  try {
    await fetch(`/wishlist/api/wishes/${wishId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ripple_score: pos.ripple, fire_score: pos.fire }),
    });
    await loadWishlist();
  } catch (e) {}
}

// ─── Wish Editor ───

function openWishEditor(wishId, preset) {
  state.editorSteps = [];
  state.editorImages = [];
  // Clean up any pending blob URLs
  (state.pendingImagePreviews || []).forEach(p => { if (p._tempUrl) URL.revokeObjectURL(p._tempUrl); });
  state.pendingImagePreviews = [];
  document.getElementById('wishId').value = wishId || '';
  document.getElementById('wishEditorTitle').textContent = wishId ? t('Edit Wish') : t('Add Wish');

  document.getElementById('wishTitle').value = preset?.title || '';
  document.getElementById('wishDesc').value = preset?.description || '';
  document.getElementById('wishRipple').value = 50;
  document.getElementById('wishFire').value = 50;
  document.getElementById('wishDifficulty').value = 50;
  document.getElementById('rippleValue').textContent = '50';
  document.getElementById('fireValue').textContent = '50';
  document.getElementById('difficultyValue').textContent = '50';
  document.getElementById('wishLinkedCountdown').value = '';
  document.getElementById('stepList').innerHTML = '';
  document.getElementById('visionGallery').innerHTML = '';
  document.getElementById('newStepInput').value = '';
  document.getElementById('wishBtnDelete').style.display = wishId ? 'inline-block' : 'none';
  document.getElementById('wishBtnCelebrate').style.display = wishId ? 'inline-block' : 'none';
  // Show 附图 + 步骤 + status only in edit mode
  document.getElementById('wishStepsSection').style.display = wishId ? '' : 'none';
  document.getElementById('wishImagesSection').style.display = wishId ? '' : 'none';
  const statusSection = document.getElementById('wishStatusSection');
  if (statusSection) {
    statusSection.style.display = wishId ? '' : 'none';
    // Edit mode: show all statuses; create mode: only 0,1
    const sel = document.getElementById('wishStatusSelect');
    if (wishId) {
      sel.innerHTML = '<option value="0" data-i18n="Draft">草稿</option><option value="1" data-i18n="Active">进行中</option><option value="2" data-i18n="Achieved">已达成</option>';
    } else {
      sel.innerHTML = '<option value="0" data-i18n="Draft">草稿</option><option value="1" data-i18n="Active">进行中</option>';
    }
    sel.value = '0';
  }
  updateROI();

  if (wishId) {
    fetch(`/wishlist/api/wishes/${wishId}`).then(r => r.json()).then(w => {
      document.getElementById('wishStatusSelect').value = String(w.status != null ? w.status : 0);
      document.getElementById('wishTitle').value = w.title || '';
      document.getElementById('wishDesc').value = w.description || '';
      document.getElementById('wishRipple').value = w.ripple_score || 50;
      document.getElementById('wishFire').value = w.fire_score || 50;
      document.getElementById('wishDifficulty').value = w.difficulty || 50;
      document.getElementById('rippleValue').textContent = w.ripple_score || 50;
      document.getElementById('fireValue').textContent = w.fire_score || 50;
      document.getElementById('difficultyValue').textContent = w.difficulty || 50;
      document.getElementById('wishLinkedCountdown').value = w.linked_countdown_id || '';
      state.editorSteps = w.steps || [];
      state.editorImages = w.images || [];
      renderEditorSteps();
      renderEditorImages();
      updateROI();
    });
  }

  document.getElementById('wishEditorOverlay').classList.add('show');
  translateDOM(document.getElementById('wishEditorModal'));
}

function closeWishEditor() {
  document.getElementById('wishEditorOverlay').classList.remove('show');
}

function onScoreSliderChange() {
  const ripple = parseInt(document.getElementById('wishRipple').value);
  const fire = parseInt(document.getElementById('wishFire').value);
  const diff = parseInt(document.getElementById('wishDifficulty').value);
  document.getElementById('rippleValue').textContent = ripple;
  document.getElementById('fireValue').textContent = fire;
  document.getElementById('difficultyValue').textContent = diff;
  updateROI();
}

function updateROI() {
  const ripple = parseInt(document.getElementById('wishRipple').value) || 50;
  const fire = parseInt(document.getElementById('wishFire').value) || 50;
  const diff = parseInt(document.getElementById('wishDifficulty').value) || 50;
  const priority = calcPriority(ripple, fire, diff);
  const q = getQuadrant(ripple, fire);
  document.getElementById('roiScore').textContent = priority.toFixed(1);
  const qEl = document.getElementById('roiQuadrant');
  qEl.textContent = t(getQuadrantDisplayName(q));
  qEl.style.background = getQuadrantColor(q);
}

// ─── Editor Steps ───

function renderEditorSteps() {
  const el = document.getElementById('stepList');
  el.innerHTML = state.editorSteps.map((s, i) => `
    <div class="step-item ${s.is_completed ? 'completed' : ''}">
      <input type="checkbox" ${s.is_completed ? 'checked' : ''} onchange="toggleEditorStep(${i})" />
      <span class="step-content">${escapeHtml(s.content)}</span>
      <button class="step-del" onclick="removeEditorStep(${i})">✕</button>
    </div>
  `).join('');
}

function addStepToEditor() {
  const inp = document.getElementById('newStepInput');
  const content = inp.value.trim();
  if (!content) return;
  state.editorSteps.push({ content, is_completed: 0, target_date: null });
  inp.value = '';
  renderEditorSteps();
}

function toggleEditorStep(idx) {
  state.editorSteps[idx].is_completed = state.editorSteps[idx].is_completed ? 0 : 1;
  renderEditorSteps();
}

function removeEditorStep(idx) {
  state.editorSteps.splice(idx, 1);
  renderEditorSteps();
}

// ─── Editor Images ───

function renderEditorImages() {
  const el = document.getElementById('visionGallery');
  const wishId = document.getElementById('wishId').value;

  const saved = state.editorImages.map((img, i) => ({
    image_url: img.image_url,
    id: img.id || 0,
    url: wishId ? `/wishlist/api/image/${wishId}/${img.image_url}` : `/api/uploads/${img.image_url}`,
    _type: 'saved',
    _idx: i,
  }));

  const pending = (state.pendingImagePreviews || []).map((p, i) => ({
    url: p._tempUrl,
    _type: 'pending',
    _idx: i,
  }));

  const all = [...saved, ...pending];

  el.innerHTML = all.map(item => `
    <div class="vision-item ${item._type === 'pending' ? 'vision-uploading' : ''}">
      <a href="${item.url}" class="glightbox-wish-edit" data-gallery="wish-edit-${wishId || 'new'}"><img src="${item.url}" loading="lazy" style="object-fit:cover;" /></a>
      <span class="vision-del" onclick="event.stopPropagation();removeImageItem('${item._type}', ${item._idx})">✕</span>
    </div>
  `).join('');

  setTimeout(() => {
    if (typeof GLightbox !== 'undefined') GLightbox({ selector: '.glightbox-wish-edit', touchNavigation: true, loop: false });
  }, 300);
}

function removeImageItem(type, idx) {
  if (type === 'pending') {
    // Remove from pending queue and revoke blob URL
    const item = (state.pendingImagePreviews || [])[idx];
    if (item && item._tempUrl) URL.revokeObjectURL(item._tempUrl);
    state.pendingImagePreviews.splice(idx, 1);
  } else {
    // Remove saved image — if it has an id, also delete from server
    const img = state.editorImages[idx];
    if (img && img.id) {
      fetch(`/wishlist/api/wish-images/${img.id}`, { method: 'DELETE' }).catch(() => {});
    }
    state.editorImages.splice(idx, 1);
  }
  renderEditorImages();
}

function removeEditorImage(idx) {
  removeImageItem('saved', idx);
}

async function onWishImageSelected() {
  const fileInput = document.getElementById('wishImageFile');
  const files = Array.from(fileInput.files);
  if (!files.length) return;
  fileInput.value = '';

  const wishId = document.getElementById('wishId').value;
  const totalCount = state.editorImages.length + (state.pendingImagePreviews || []).length;

  if (totalCount + files.length > 30) {
    alert(t('Max 20 images'));
    return;
  }

  // Initialize pending array
  if (!state.pendingImagePreviews) state.pendingImagePreviews = [];

  // Create instant previews
  const newPreviews = files.map(f => ({
    _tempUrl: URL.createObjectURL(f),
    _file: f,
  }));
  state.pendingImagePreviews.push(...newPreviews);

  // Show previews immediately
  renderEditorImages();

  // Upload in background
  for (let i = 0; i < newPreviews.length; i++) {
    const preview = newPreviews[i];
    const fd = new FormData();
    fd.append('file', preview._file);
    if (wishId) fd.append('wish_id', wishId);

    try {
      const r = await fetch('/wishlist/api/upload-image', { method: 'POST', body: fd });
      const d = await r.json();
      if (d.error) { alert(d.error); break; }
      if (d.filename) {
        // Move from pending to saved
        state.editorImages.push({ image_url: d.filename, id: d.id || 0, url: d.url || '' });
        // Remove from pending
        const idx = state.pendingImagePreviews.indexOf(preview);
        if (idx >= 0) state.pendingImagePreviews.splice(idx, 1);
        URL.revokeObjectURL(preview._tempUrl);
      }
    } catch (e) {
      // Remove failed preview
      const idx = state.pendingImagePreviews.indexOf(preview);
      if (idx >= 0) state.pendingImagePreviews.splice(idx, 1);
      URL.revokeObjectURL(preview._tempUrl);
    }
  }

  renderEditorImages();
}

// ─── Save / Delete Wish ───

function showSaveToast() {
  const toast = document.getElementById('saveToastWish');
  if (!toast) return;
  toast.style.display = 'flex';
  toast.style.animation = 'none';
  toast.offsetHeight; // reflow
  toast.style.animation = 'toastIn 0.3s ease, toastOut 0.5s ease 2s forwards';
  setTimeout(() => { toast.style.display = 'none'; }, 2600);
}

async function saveWish() {
  const wishId = document.getElementById('wishId').value;
  const title = document.getElementById('wishTitle').value.trim();
  if (!title) { alert(t('Please enter wish title')); return; }

  // Parse linked_countdown_id as int or null
  const linkedVal = document.getElementById('wishLinkedCountdown').value;
  const linkedId = linkedVal ? parseInt(linkedVal) : null;

  const data = {
    title,
    description: document.getElementById('wishDesc').value,
    ripple_score: parseInt(document.getElementById('wishRipple').value),
    fire_score: parseInt(document.getElementById('wishFire').value),
    difficulty: parseInt(document.getElementById('wishDifficulty').value),
    linked_countdown_id: linkedId,
  };
  // Send status from dropdown (if visible) or default
  const statusSel = document.getElementById('wishStatusSelect');
  if (statusSel && statusSel.style.display !== 'none') {
    data.status = parseInt(statusSel.value);
  } else if (!wishId) {
    data.status = 0;
  }

  const url = wishId ? `/wishlist/api/wishes/${wishId}` : '/wishlist/api/wishes';
  const method = wishId ? 'PUT' : 'POST';

  try {
    // 1. Save main wish data
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const d = await r.json();
    if (r.status >= 400) { alert(d.error || '保存失败'); return; }
    const effectiveWishId = wishId || d.id;

    // 2. Sync steps (delete removed, update existing, add new)
    if (wishId) {
      const w = await fetch(`/wishlist/api/wishes/${wishId}`).then(r => r.json());
      const existingSteps = w.steps || [];
      const keepIds = state.editorSteps.filter(s => s.id).map(s => s.id);
      // Delete removed
      for (const es of existingSteps) {
        if (!keepIds.includes(es.id)) {
          await fetch(`/wishlist/api/steps/${es.id}`, { method: 'DELETE' });
        }
      }
      // Add/update
      for (const s of state.editorSteps) {
        if (!s.id) {
          await fetch(`/wishlist/api/wishes/${wishId}/steps`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: s.content }),
          });
        } else {
          await fetch(`/wishlist/api/steps/${s.id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: s.content, is_completed: s.is_completed }),
          });
        }
      }
    }

    // 3. Sync images — delete removed images from server
    if (wishId) {
      const w = await fetch(`/wishlist/api/wishes/${wishId}`).then(r => r.json());
      const existingImages = w.images || [];
      const keepUrls = state.editorImages.map(img => img.image_url);
      for (const img of existingImages) {
        if (!keepUrls.includes(img.image_url)) {
          await fetch(`/wishlist/api/wish-images/${img.id}`, { method: 'DELETE' }).catch(() => {});
        }
      }
    }

    closeWishEditor();
    await loadWishlist();
    showSaveToast();
  } catch (e) { alert('保存失败'); }
}

async function deleteWishFromEditor() {
  const wishId = document.getElementById('wishId').value;
  if (!wishId) return;
  if (!confirm(t('Confirm delete wish?'))) return;
  await fetch(`/wishlist/api/wishes/${wishId}`, { method: 'DELETE' });
  closeWishEditor();
  loadWishlist();
}

async function celebrateWishFromEditor() {
  const wishId = document.getElementById('wishId').value;
  if (!wishId) return;
  await fetch(`/wishlist/api/wishes/${wishId}/celebrate`, { method: 'POST' });
  // Confetti!
  if (typeof confetti === 'function') {
    confetti({ particleCount: 150, spread: 80, origin: { y: 0.6 } });
    setTimeout(() => confetti({ particleCount: 80, spread: 60, origin: { y: 0.6, x: 0.3 } }), 300);
    setTimeout(() => confetti({ particleCount: 80, spread: 60, origin: { y: 0.6, x: 0.7 } }), 600);
  }
  closeWishEditor();
  loadWishlist();
}

// ─── Detail Sheet ───

async function openWishDetail(wishId) {
  try {
    const r = await fetch(`/wishlist/api/wishes/${wishId}`);
    const w = await r.json();
    const q = getQuadrant(w.ripple_score, w.fire_score);
    const qName = t(getQuadrantDisplayName(q));
    const qColor = getQuadrantColor(q);

    // Journey entries count for preview
    const journeyCount = 0; // Will be replaced by actual count

    // Images for lightbox
    const imageItems = (w.images || []).map(img => {
      const imgUrl = `/wishlist/api/image/${w.id}/${img.image_url}`;
      return `<a href="${imgUrl}" class="glightbox-wish" data-gallery="wish-${w.id}">
        <div class="vision-item"><img src="${imgUrl}" loading="lazy" style="object-fit:cover;" /></div>
      </a>`;
    }).join('');

    document.getElementById('detailTitle').textContent = w.title;
    document.getElementById('detailBody').innerHTML = `
      <div class="detail-section">
        <h4 data-i18n="Description">描述</h4>
        <div class="detail-value">${escapeHtml(w.description || '—')}</div>
      </div>
      <div class="detail-section">
        <h4 data-i18n="Quadrant Stats">象限分布</h4>
        <div class="detail-value">
          <span style="display:inline-block;padding:2px 10px;border-radius:10px;background:${qColor};color:#fff;font-size:0.85rem;">${qName}</span>
        </div>
      </div>
      <div class="detail-section">
        <h4 data-i18n="Priority Score">优先级分值</h4>
        <div class="detail-priority">⚡ ${w.priority || calcPriority(w.ripple_score, w.fire_score, w.difficulty)}</div>
      </div>
      <div class="detail-section">
        <h4>${t('Life Ripple')}: ${w.ripple_score || 50} | ${t("Heart's Fire")}: ${w.fire_score || 50} | ${t('Difficulty')}: ${w.difficulty || 50}</h4>
      </div>
      <div class="detail-section">
        <h4 data-i18n="Steps">步骤拆解</h4>
        <div class="detail-steps">
          ${(w.steps || []).map(s => `
            <div class="step-item ${s.is_completed ? 'completed' : ''}">
              <input type="checkbox" ${s.is_completed ? 'checked' : ''} onchange="toggleDetailStep(${s.id}, this.checked)" />
              <span class="step-content">${escapeHtml(s.content)}</span>
            </div>
          `).join('') || '<span style="color:#bbb;font-size:0.85rem;">—</span>'}
        </div>
      </div>
      <!-- Journey Content -->
      <div class="detail-section">
        <h4 data-i18n="Journey">心路历程</h4>
        <div class="journey-display" id="journeyDisplay"><span style="color:#bbb;">—</span></div>
        <button class="btn-small" onclick="closeWishDetail();openJourneyManager(${w.id})" style="margin-top:8px;" data-i18n="Manage Journey">管理心路历程</button>
      </div>
      ${imageItems ? `
      <div class="detail-section">
        <h4 data-i18n="Vision Board">愿景板</h4>
        <div class="vision-gallery" id="detailVisionGallery">
          ${imageItems}
        </div>
      </div>
      ` : ''}
      ${w.achieved_at ? `
      <div class="detail-section">
        <h4 data-i18n="Achieved on">达成于</h4>
        <div class="detail-value">${w.achieved_at}</div>
      </div>
      ` : ''}
      ${w.linked_event_name ? `
      <div class="detail-section">
        <h4 data-i18n="Linked Countdown">关联倒数日</h4>
        <div class="detail-value">${escapeHtml(w.linked_event_name)}</div>
      </div>
      ` : ''}
      <div class="modal-actions">
        <button class="btn-small" onclick="closeWishDetail();openWishEditor(${w.id})">✎ ${t('Edit Wish')}</button>
        ${w.status !== 2 ? `<button class="btn-archive" onclick="celebrateFromDetail(${w.id})">🎉 ${t('Celebrate!')}</button>` : ''}
      </div>
    `;
    document.getElementById('detailSheetOverlay').classList.add('show');
    translateDOM(document.getElementById('detailSheet'));

    // Init GLightbox for vision gallery
    setTimeout(() => {
      if (typeof GLightbox !== 'undefined') {
        GLightbox({ selector: '.glightbox-wish', touchNavigation: true, loop: false });
      }
    }, 300);

    // Load journey entries for honor wall display
    loadJourneyDisplay(w.id);
  } catch (e) {}
}

async function loadJourneyDisplay(wishId) {
  try {
    const r = await fetch(`/wishlist/api/wishes/${wishId}/journey`);
    const entries = await r.json();
    const display = document.getElementById('journeyDisplay');
    if (!display) return;

    if (!entries.length) {
      display.innerHTML = `<span style="color:#bbb;">${t('No journey yet.')}</span>`;
      return;
    }

    const entryCount = entries.length;
    if (entryCount > 5) {
      const doubled = [...entries, ...entries];
      display.classList.add('honor-wall-scroll');
      display.innerHTML = `<div class="honor-wall-inner">${doubled.map(e => `
        <div class="honor-wall-item">
          <div class="honor-wall-content">${e.content}</div>
          <div class="honor-wall-footer">
            <span class="honor-wall-date">${escapeHtml(e.entry_date || '')}</span>
            <span class="honor-wall-fire">🔥 ${e.fire_score_at_entry != null ? e.fire_score_at_entry : 50}</span>
          </div>
        </div>
      `).join('')}</div>`;
    } else {
      display.classList.remove('honor-wall-scroll');
      display.innerHTML = entries.map(e => `
        <div class="honor-wall-item">
          <div class="honor-wall-content">${e.content}</div>
          <div class="honor-wall-footer">
            <span class="honor-wall-date">${escapeHtml(e.entry_date || '')}</span>
            <span class="honor-wall-fire">🔥 ${e.fire_score_at_entry != null ? e.fire_score_at_entry : 50}</span>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {}
}

function closeWishDetail() {
  document.getElementById('detailSheetOverlay').classList.remove('show');
}

async function toggleDetailStep(stepId, checked) {
  await fetch(`/wishlist/api/steps/${stepId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_completed: checked ? 1 : 0 }),
  });
  loadWishlist();
}

// ─── Journey Manager (Singleton) ───

async function openJourneyManager(wishId) {
  document.getElementById('journeyWishId').value = wishId;
  document.getElementById('journeyManagerOverlay').classList.add('show');
  await loadJourneyEntries(wishId);
  translateDOM(document.getElementById('journeyManagerModal'));
}

function closeJourneyManager() {
  document.getElementById('journeyManagerOverlay').classList.remove('show');
}

async function loadJourneyEntries(wishId) {
  try {
    const r = await fetch(`/wishlist/api/wishes/${wishId}/journey`);
    const entries = await r.json();
    renderJourneyEntries(entries);
  } catch (e) {
    document.getElementById('journeyEntryList').innerHTML = '';
  }
}

function renderJourneyEntries(entries) {
  const el = document.getElementById('journeyEntryList');
  if (!entries.length) {
    el.innerHTML = `<div class="empty-state" style="padding:20px;">${t('No journey yet.')}</div>`;
    return;
  }
  el.innerHTML = entries.map(e => {
    const preview = stripHtml(e.content).substring(0, 80);
    const fireScore = e.fire_score_at_entry != null ? e.fire_score_at_entry : 50;
    return `
    <div class="journey-entry-item">
      <div class="journey-entry-preview">${escapeHtml(preview)}</div>
      <div class="journey-entry-meta">
        <span class="journey-entry-date" onclick="openJourneyEntryEditor(${e.id})">${escapeHtml(e.entry_date || '')}</span>
        <span class="journey-entry-fire">🔥 ${fireScore}</span>
        <div class="journey-entry-actions">
          <button class="edit-btn" onclick="openJourneyEntryEditor(${e.id})" data-i18n="Edit Entry">编辑</button>
          <button class="del-btn" onclick="deleteJourneyEntry(${e.id})" data-i18n="Delete Entry">删除</button>
        </div>
      </div>
    </div>`;
  }).join('');
}

function stripHtml(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html || '';
  return tmp.textContent || tmp.innerText || '';
}

// ─── Journey Entry Editor (Singleton Quill) ───

function openJourneyEntryEditor(entryId) {
  const wishId = document.getElementById('journeyWishId').value;

  // Completely destroy old Quill instance and DOM
  if (state.quillInstance) {
    // Quill doesn't have a destroy(), so we rebuild the container
    state.quillInstance = null;
  }

  // Rebuild editor DOM from scratch to prevent toolbar stacking
  const container = document.getElementById('journeyQuillContainer');
  container.innerHTML = '<div id="journeyQuillEditor" style="min-height:180px;"></div>';

  // Create fresh singleton Quill instance
  state.quillInstance = new Quill('#journeyQuillEditor', {
    theme: 'snow',
    placeholder: '记录心路历程...',
    modules: {
      toolbar: [
        ['bold', 'italic', 'underline'],
        [{ list: 'ordered' }, { list: 'bullet' }],
        ['clean'],
      ],
    },
  });

  document.getElementById('journeyEntryId').value = entryId || '';
  document.getElementById('journeyEntryTitle').textContent = entryId ? t('Edit Entry') : t('New Entry');

  // Init Flatpickr
  const dateField = document.getElementById('journeyEntryDate');
  if (dateField._flatpickr) dateField._flatpickr.destroy();
  flatpickr(dateField, {
    enableTime: true,
    dateFormat: 'Y-m-d H:i',
    locale: 'zh',
    defaultDate: new Date(),
  });

  if (entryId) {
    fetch(`/wishlist/api/wishes/${wishId}/journey`).then(r => r.json()).then(entries => {
      const entry = entries.find(e => e.id === entryId);
      if (entry && state.quillInstance) {
        state.quillInstance.root.innerHTML = entry.content || '';
        dateField._flatpickr.setDate(entry.entry_date || new Date());
      }
    });
  }

  document.getElementById('journeyEntryOverlay').classList.add('show');
}

function closeJourneyEntryEditor() {
  document.getElementById('journeyEntryOverlay').classList.remove('show');
  state.quillInstance = null;
}

async function saveJourneyEntry() {
  const entryId = document.getElementById('journeyEntryId').value;
  const wishId = document.getElementById('journeyWishId').value;
  const content = state.quillInstance ? state.quillInstance.root.innerHTML : '';
  if (!content || content === '<p><br></p>') { alert('内容不能为空'); return; }

  const dateField = document.getElementById('journeyEntryDate');
  const entryDate = dateField._flatpickr
    ? dateField._flatpickr.formatDate(dateField._flatpickr.selectedDates[0], 'Y-m-d H:i')
    : new Date().toISOString().slice(0, 16).replace('T', ' ');

  if (entryId) {
    await fetch(`/wishlist/api/journey/${entryId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, entry_date: entryDate }),
    });
  } else {
    await fetch(`/wishlist/api/wishes/${wishId}/journey`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, entry_date: entryDate }),
    });
  }

  closeJourneyEntryEditor();
  loadJourneyEntries(wishId);
  loadWishlist();
}

async function deleteJourneyEntry(entryId) {
  if (!confirm(t('Confirm delete entry?'))) return;
  const wishId = document.getElementById('journeyWishId').value;
  await fetch(`/wishlist/api/journey/${entryId}`, { method: 'DELETE' });
  loadJourneyEntries(wishId);
  loadWishlist();
}

async function celebrateFromDetail(wishId) {
  await fetch(`/wishlist/api/wishes/${wishId}/celebrate`, { method: 'POST' });
  if (typeof confetti === 'function') {
    confetti({ particleCount: 150, spread: 80, origin: { y: 0.6 } });
    setTimeout(() => confetti({ particleCount: 80, spread: 60, origin: { y: 0.6, x: 0.3 } }), 300);
    setTimeout(() => confetti({ particleCount: 80, spread: 60, origin: { y: 0.6, x: 0.7 } }), 600);
  }
  closeWishDetail();
  loadWishlist();
}

// ─── Utility ───
function escapeHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}

// ─── Memo ───

async function initMemo() {
  state.currentMemoId = null;
  state.memoStarFilter = false;
  await loadMemos();
}

async function loadMemos() {
  try {
    const url = state.memoStarFilter ? '/memo/api/memos?starred=1' : '/memo/api/memos';
    const r = await fetch(url);
    state.memos = await r.json();
  } catch (e) { state.memos = []; }
  renderMemoList();
}

function renderMemoList() {
  const el = document.getElementById('memoList');
  if (!el) return;
  if (!state.memos.length) {
    el.innerHTML = `<div class="empty-state">${t('No memos yet.')}</div>`;
    return;
  }
  el.innerHTML = state.memos.map(m => {
    const time = (m.updated_at || m.created_at || '').replace('T', ' ').substring(0, 16);
    const starCls = m.is_starred ? 'active' : '';
    const hasAtt = m.attachment_count > 0;
    return `
    <div class="memo-item ${m.is_starred ? 'starred' : ''}" onclick="openMemoDetail(${m.id})">
      <span class="memo-star ${starCls}" onclick="event.stopPropagation();toggleStar(${m.id})">★</span>
      <div class="memo-item-body">
        <div class="memo-item-subject">${escapeHtml(m.subject)}</div>
        <div class="memo-item-summary">${escapeHtml(m.summary || t('No content'))}</div>
      </div>
      <div class="memo-item-meta">
        ${hasAtt ? '<span class="memo-attach-icon">📎</span>' : ''}
        <span>${escapeHtml(time)}</span>
      </div>
    </div>`;
  }).join('');
  translateDOM();
}

function filterByStar() {
  state.memoStarFilter = !state.memoStarFilter;
  const btn = document.getElementById('btnStarFilter');
  if (btn) btn.classList.toggle('active-star', state.memoStarFilter);
  loadMemos();
}

async function openMemoDetail(id) {
  state.currentMemoId = id;
  try {
    const r = await fetch(`/memo/api/memos/${id}`);
    const m = await r.json();
    document.getElementById('memoDetailSubject').textContent = m.subject;
    document.getElementById('memoDetailMeta').textContent =
      (m.updated_at || m.created_at || '').replace('T', ' ').substring(0, 16);
    // Server renders content.md → content_html. Just use it directly.
    document.getElementById('memoDetailContent').innerHTML = m.content_html || '<span style="color:#bbb;">—</span>';
    // Star button
    const starBtn = document.getElementById('memoDetailStar');
    starBtn.textContent = m.is_starred ? '★' : '☆';
    starBtn.classList.toggle('active', !!m.is_starred);
    // Attachments
    const attEl = document.getElementById('memoDetailAttachments');
    if (m.attachments && m.attachments.length) {
      attEl.innerHTML = '<h4 data-i18n="Attachments" style="margin-bottom:8px;">附件</h4>' +
        m.attachments.map(a => `
          <a href="/memo/api/attachments/${id}/${a.filename}" class="memo-att-item" target="_blank">
            <img src="/memo/api/attachments/${id}/${a.filename}" loading="lazy" />
          </a>
        `).join('');
    } else {
      attEl.innerHTML = '';
    }
    // Show detail, hide list and editor
    document.getElementById('memoList').style.display = 'none';
    document.getElementById('memoEditor').style.display = 'none';
    document.getElementById('memoDetail').style.display = '';
    translateDOM();
  } catch (e) {}
}

function closeMemoDetail() {
  document.getElementById('memoDetail').style.display = 'none';
  document.getElementById('memoList').style.display = '';
}

async function toggleStar(id) {
  try {
    const r = await fetch(`/memo/api/memos/${id}/star`, { method: 'POST' });
    const d = await r.json();
    // Update in local state
    const memo = state.memos.find(m => m.id === id);
    if (memo) memo.is_starred = d.is_starred;
    // Update detail star button if visible
    const starBtn = document.getElementById('memoDetailStar');
    if (starBtn) {
      starBtn.textContent = d.is_starred ? '★' : '☆';
      starBtn.classList.toggle('active', !!d.is_starred);
    }
    renderMemoList();
  } catch (e) {}
}

async function toggleDetailStar() {
  if (state.currentMemoId) {
    await toggleStar(state.currentMemoId);
  }
}

function editCurrentMemo() {
  openMemoEditor(state.currentMemoId);
}

async function deleteCurrentMemo() {
  if (!state.currentMemoId || !confirm(t('Confirm delete memo?'))) return;
  await fetch(`/memo/api/memos/${state.currentMemoId}`, { method: 'DELETE' });
  closeMemoDetail();
  loadMemos();
}

// ─── Memo Editor (Vditor) ───

function openMemoEditor(id) {
  // Destroy old Vditor instance completely
  if (state.memoQuill) {
    try { state.memoQuill.destroy(); } catch(e) {}
    state.memoQuill = null;
  }
  // Rebuild container to prevent duplicate toolbars
  const container = document.getElementById('memoVditorContainer');
  if (container) container.innerHTML = '<div id="memoVditorEditor"></div>';

  if (!id) {
    // Create flow: prompt for subject first
    const subject = prompt(t('Enter subject'), '');
    if (!subject || !subject.trim()) return;
    openMemoEditorCreate(subject.trim());
    return;
  }

  document.getElementById('memoId').value = id || '';
  state.deletedMemoFiles = [];

  // Init Vditor
  state.memoQuill = new Vditor('memoVditorEditor', {
    height: 380,
    mode: 'ir',
    width: 'auto',
    placeholder: t('Memo content...'),
    cache: { enable: false },
    toolbar: [
      'headings', 'bold', 'italic', 'strike', '|',
      'list', 'ordered-list', 'check', '|',
      'quote', 'code', 'inline-code', '|',
      'link', 'table', '|',
      'undo', 'redo', 'fullscreen', 'outline',
    ],
    upload: {
      url: '/memo/api/vditor-upload',
      fieldName: 'file',
      extraData: { memo_id: String(id) },
      format(files, responseText) {
        try {
          const d = JSON.parse(responseText);
          if (d.code === 0 && d.data && d.data.succMap) {
            return JSON.stringify({ msg: '', code: 0, data: { succMap: d.data.succMap } });
          }
        } catch(e) {}
        return responseText;
      },
    },
    after: () => {
      if (id) {
        fetch(`/memo/api/memos/${id}`).then(r => r.json()).then(m => {
          document.getElementById('memoSubject').value = m.subject || '';
          if (state.memoQuill) state.memoQuill.setValue(m.content_md || m.content_html || '');
          loadMemoAttachments(id);
        });
      } else {
        document.getElementById('memoSubject').value = '';
        if (state.memoQuill) state.memoQuill.setValue('');
        document.getElementById('memoAttachmentList').innerHTML = '';
      }
    },
  });

  document.getElementById('memoList').style.display = 'none';
  document.getElementById('memoDetail').style.display = 'none';
  document.getElementById('memoEditor').style.display = '';
  translateDOM();
}

async function openMemoEditorCreate(subject) {
  try {
    const r = await fetch('/memo/api/memos', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject }),
    });
    const d = await r.json();
    if (d.id) {
      state.currentMemoId = d.id;
      openMemoEditor(d.id);
    }
  } catch(e) { alert('创建失败'); }
}

async function loadMemoAttachments(id) {
  try {
    const r = await fetch(`/memo/api/memos/${id}/attachments`);
    const files = await r.json();
    const el = document.getElementById('memoAttachmentList');
    if (!el) return;
    // Filter out deleted files
    const activeFiles = files.filter(f => !(state.deletedMemoFiles || []).includes(f.filename));
    if (!activeFiles.length) { el.innerHTML = '<span style="color:#bbb;font-size:0.82rem;">—</span>'; return; }
    el.innerHTML = activeFiles.map(f => {
      if (f.is_image) {
        return `<div class="memo-att-thumb" id="att-${f.filename.replace(/[^a-zA-Z0-9]/g,'_')}">
          <a href="${f.url}" class="glightbox-memo" data-gallery="memo-${id}"><img src="${f.url}" loading="lazy" /></a>
          <span class="att-del" onclick="event.stopPropagation();markMemoFileDelete(${id},'${f.filename.replace(/'/g,"\\'")}')">✕</span>
        </div>`;
      } else {
        const fileId = 'att-' + f.filename.replace(/[^a-zA-Z0-9]/g, '_');
        return `<div class="memo-att-thumb" id="${fileId}" style="width:auto;min-width:72px;">
          <a href="${f.url}" class="memo-att-file" target="_blank" title="${f.filename}" style="text-decoration:none;">
            <span class="file-icon">📄</span><span style="font-size:0.7rem;color:#999;max-width:64px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.filename}</span>
          </a>
          <span class="att-del" onclick="event.preventDefault();event.stopPropagation();markMemoFileDelete(${id},'${f.filename.replace(/'/g,"\\'")}')">✕</span>
        </div>`;
      }
    }).join('');
    setTimeout(() => {
      if (typeof GLightbox !== 'undefined') GLightbox({ selector: '.glightbox-memo', touchNavigation: true, loop: false });
    }, 300);
  } catch(e) {}
}

function markMemoFileDelete(memoId, filename) {
  if (!confirm('确定删除此附件吗？')) return;
  if (!state.deletedMemoFiles) state.deletedMemoFiles = [];
  state.deletedMemoFiles.push(filename);
  // Hide from UI immediately
  const el = document.getElementById('att-' + filename.replace(/[^a-zA-Z0-9]/g, '_'));
  if (el) el.style.display = 'none';
}

function cancelMemoEdit() {
  if (state.memoQuill) {
    const val = state.memoQuill.getValue();
    if (val && val.trim()) {
      if (!confirm(t('Cancel edit?'))) return;
    }
  }
  closeMemoEditor();
}

function closeMemoEditor() {
  if (state.memoQuill) {
    try { state.memoQuill.destroy(); } catch(e) {}
    state.memoQuill = null;
  }
  document.getElementById('memoEditor').style.display = 'none';
  document.getElementById('memoList').style.display = '';
  if (state.currentMemoId) openMemoDetail(state.currentMemoId);
}

async function saveMemo() {
  const id = document.getElementById('memoId').value;
  const subject = document.getElementById('memoSubject').value.trim();
  if (!subject) { alert(t('Please enter event name')); return; }

  const content_md = state.memoQuill ? state.memoQuill.getValue() : '';
  // Also generate HTML preview from Vditor
  let content_html = '';
  if (state.memoQuill) {
    content_html = state.memoQuill.getHTML();
  }

  const data = { subject, content_md, content_html };
  // Send marked-for-deletion files
  if (state.deletedMemoFiles && state.deletedMemoFiles.length) {
    data.deleted_files = state.deletedMemoFiles;
    state.deletedMemoFiles = [];
  }
  const url = id ? `/memo/api/memos/${id}` : '/memo/api/memos';
  const method = id ? 'PUT' : 'POST';

  try {
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const d = await r.json();
    if (r.status >= 400) { alert(d.error || '保存失败'); return; }

    const newId = id || d.id;
    state.currentMemoId = parseInt(newId);
    if (state.memoQuill) { try { state.memoQuill.destroy(); } catch(e) {} state.memoQuill = null; }
    document.getElementById('memoEditor').style.display = 'none';
    await loadMemos();
    openMemoDetail(state.currentMemoId);
  } catch (e) { alert('保存失败'); }
}

async function onMemoAttachSelected() {
  const files = document.getElementById('memoAttachFile').files;
  if (!files.length) return;
  const memoId = document.getElementById('memoId').value;

  for (const f of files) {
    const fd = new FormData();
    fd.append('file', f);
    if (memoId) fd.append('memo_id', memoId);
    try {
      await fetch('/memo/api/upload', { method: 'POST', body: fd });
    } catch (e) {}
  }
  document.getElementById('memoAttachFile').value = '';
  if (memoId) loadMemoAttachments(memoId);
}

// ─── SPA Navigation ───
let spaInitialized = false;

function initSPA() {
  if (spaInitialized) return; // Only attach once
  spaInitialized = true;

  // Event delegation on navbar for nav links
  const navbar = document.getElementById('navbar');
  if (navbar) {
    navbar.addEventListener('click', function(e) {
      const link = e.target.closest('.nav-item');
      if (!link) return;
      e.preventDefault();
      const url = link.getAttribute('href');
      if (!url || url === '#') return;
      navigateTo(url);
    });
  }

  // Handle browser back/forward
  window.addEventListener('popstate', function(e) {
    if (e.state && e.state.url) {
      loadPageContent(e.state.url, false);
    }
  });
}

async function navigateTo(url) {
  history.pushState({ url }, '', url);
  await loadPageContent(url, true);
}

async function loadPageContent(url, pushHistory) {
  try {
    const resp = await fetch(url);
    const html = await resp.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // Extract new content
    const newContent = doc.getElementById('app-content');
    if (!newContent) { window.location.href = url; return; }

    // Replace content area
    const currentContent = document.getElementById('app-content');
    currentContent.innerHTML = newContent.innerHTML;

    // Update body data-page
    const newPage = doc.body.dataset.page || '';
    document.body.dataset.page = newPage;
    state.pageName = newPage;

    // Re-bind scripts and re-init page
    highlightNav();
    await initPageContent(newPage);

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'instant' });
  } catch (e) {
    // Fallback: full navigation
    window.location.href = url;
  }
}

async function initPageContent(pageName) {
  // Reset page-specific intervals before re-init
  if (state.quoteIntervalId) { clearInterval(state.quoteIntervalId); state.quoteIntervalId = null; }

  // Dispatch page-specific init
  if (pageName === 'daysmatter') {
    await initDaysmatter();
  } else if (pageName === 'wishlist') {
    await initWishlist();
    // Re-init starfield
    if (typeof StarfieldVFX !== 'undefined' && StarfieldVFX.destroy) {
      StarfieldVFX.destroy();
    }
    if (typeof StarfieldVFX !== 'undefined' && StarfieldVFX.init) {
      StarfieldVFX.init();
    }
  } else if (pageName === 'memo') {
    await initMemo();
  } else if (pageName === 'settings') {
    await initSettingsPage();
  }

  // Re-apply visual settings
  applyBgOpacity(state.settings.bg_opacity);
  // Re-translate new content
  translateDOM();
}

// ─── Start ───
document.addEventListener('DOMContentLoaded', function() {
  init();
  initSPA();
  // Push initial state
  if (!history.state) {
    history.replaceState({ url: location.pathname }, '', location.pathname);
  }
});
