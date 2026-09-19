/* Claude DnD - main menu, New Game wizard, Continue, Settings, in-game menu, loading bar. */
(() => {
const CD = window.CD; const { $, el, esc, img, rurl, post, toast } = CD;
const root = $('#menu');
let M = null, page = 'main', inGame = false, wiz = null, saveT = null, lastMenuKey = '', stateCampaign = null, booted = false;

// ======================= boot loader =======================
const bootSteps = { total: 4, done: 0 };
function bootTick(label){ bootSteps.done++; const b = $('#boot'); if (!b) return;
  b.querySelector('.ld-bar i').style.width = Math.min(100, 100*bootSteps.done/bootSteps.total) + '%';
  if (label) b.querySelector('.ld-sub').textContent = label;
  if (bootSteps.done >= bootSteps.total && !booted){ booted = true; setTimeout(() => { b.classList.add('gone'); setTimeout(() => b.remove(), 600); }, 250); } }
bootTick('Loading fonts…');
(document.fonts ? document.fonts.ready : Promise.resolve()).then(() => bootTick('Connecting…'));
setTimeout(() => { while (!booted) bootTick(); }, 6000);   // never hang on the boot screen

// ======================= loading overlay =======================
let localBusy = null;
function dmConnected(dm){ if (!dm) return false; const age = Date.now()/1000 - (dm.t||0);
  return (dm.status === 'listening' && age < 70) || (dm.status === 'thinking' && age < 900); }
function renderLoading(){
  const S = CD.S || {}; const dm = (S.campaign ? S.dm : (M && M.dm)) || S.dm || {}; const ld = localBusy || dm.loading;
  const box = $('#loading');
  if (!ld){ box.classList.add('hidden'); return; }
  box.classList.remove('hidden');
  box.querySelector('.ld-label').textContent = ld.label || 'Loading…';
  const bar = box.querySelector('.ld-bar'); const pct = ld.percent;
  bar.classList.toggle('indet', pct == null); bar.querySelector('i').style.width = pct == null ? '' : Math.max(3, Math.min(100, pct)) + '%';
  const sub = box.querySelector('.ld-sub');
  const ctl = (M && M.control) || S.control || {};
  if (localBusy) sub.textContent = '';
  else if (!dmConnected(dm)) sub.innerHTML = `The DM isn't connected. Type <b>go</b> in the Claude chat to bring them in.`;
  else sub.textContent = pct == null ? 'The DM is working…' : `${Math.round(pct)}%`;
  const act = box.querySelector('.ld-actions'); act.innerHTML = '';
  const d = (M && M.draft) || {};
  if (!localBusy && d.theme_status === 'building'){ const b = el('button','mbtn small','Cancel request'); b.onclick = () => post('/api/wizard/cancel_build',{}).then(refresh); act.append(b); }
  if (!localBusy && S.campaign && S.campaign.status !== 'setup'){ const b = el('button','mbtn small ghost','Hide'); b.onclick = () => box.classList.add('hidden'); act.append(b); }
}
async function busy(label, fn){ localBusy = {label, percent: null}; renderLoading();
  try { return await fn(); } finally { localBusy = null; renderLoading(); } }

// ======================= state hook =======================
async function refresh(){ try { const r = await fetch('/api/menu'); M = await r.json(); } catch(e){ return; } if (!booted) bootTick('Ready'); renderLoading();
  if (!root.classList.contains('hidden') && page !== 'new' && !(page === 'settings' && root.contains(document.activeElement) && document.activeElement.tagName === 'INPUT')) renderPage(); }
function onState(S){
  const has = !!S.campaign;
  if (!booted && bootSteps.done < 3) bootTick('Loading menu…');
  if (!has){ inGame = false; if (root.classList.contains('hidden')) { page = 'main'; show(); } if (page !== 'new') resetTheme(); refresh(); }
  else if (!inGame && !root.classList.contains('hidden')) hide();
  else if (!M) refresh();
  if (stateCampaign !== S.active){ stateCampaign = S.active; }
  renderLoading();
}
function show(){ root.classList.remove('hidden'); renderPage(); }
function hide(){ root.classList.add('hidden'); inGame = false; }
function resetTheme(){ const r = document.documentElement.style; ['--accent','--bg','--panel','--text','--panel2','--line','--muted'].forEach(v => r.removeProperty(v)); }
function go(p){ page = p; if (p !== 'new' && !CD.S?.campaign) resetTheme(); renderPage(); root.scrollTop = 0; }

// ======================= pages =======================
function renderPage(){
  if (!M){ root.innerHTML = '<div class="mm-wrap"><div class="mm-title">Claude DnD</div></div>'; return; }
  const key = page + '|' + (page === 'new' ? (wiz && wiz.page) : '');
  root.className = 'menu page-' + page + (inGame ? ' ingame' : '');
  if (page === 'main') return renderMain();
  if (page === 'continue') return renderContinue();
  if (page === 'settings') return renderSettings();
  if (page === 'new') return renderWizard();
  if (page === 'ingame') return renderInGame();
}
function bgRecipe(){
  const s = M.saves && M.saves[0];
  if (s && s.backdrop) return rurl(s.backdrop, null, s.theme);
  return rurl({layers:[{part:'tpl:bd_void', params:{seed:5}}]}, null, '_');
}
function frame(inner, cls=''){
  return `<div class="mm-bg" style="background-image:url('${bgRecipe()}')"></div><div class="mm-veil"></div><div class="mm-wrap ${cls}">${inner}</div>`;
}
function dmLine(){ const ok = dmConnected(M.dm);
  return `<div class="mm-dm ${ok?'on':''}"><span class="dot2"></span>${ok ? 'DM connected' : "DM offline — type <b>go</b> in the Claude chat"}</div>`; }

function renderMain(){
  const n = (M.saves||[]).length, draft = M.draft && M.draft.page;
  root.innerHTML = frame(`
    <div class="mm-title">Claude DnD</div><div class="mm-sub">a roguelike tabletop visual novel</div>
    <div class="mm-buttons">
      <button class="mbtn big" data-go="new">New Game${draft ? '<small>resume setup</small>' : ''}</button>
      <button class="mbtn big" data-go="continue" ${n ? '' : 'disabled'}>Continue${n ? `<small>${n} save${n>1?'s':''}</small>` : ''}</button>
      <button class="mbtn big" data-go="settings">Settings</button>
    </div>
    ${dmLine()}`, 'main');
  root.querySelectorAll('[data-go]').forEach(b => b.onclick = () => { if (b.dataset.go === 'new') startWizard(); go(b.dataset.go); });
}
function backBtn(to='main'){ return `<button class="mbtn back" data-back="${to}">← Back</button>`; }
function wireBack(){ root.querySelectorAll('[data-back]').forEach(b => b.onclick = () => go(b.dataset.back)); }
function ago(iso){ if (!iso) return ''; const s = (Date.now() - new Date(iso).getTime())/1000; if (s < 90) return 'just now';
  if (s < 3600) return Math.round(s/60) + ' min ago'; if (s < 86400) return Math.round(s/3600) + ' h ago'; return Math.round(s/86400) + ' days ago'; }

// ---------- continue ----------
function renderContinue(){
  const cards = (M.saves||[]).map(s => {
    const pt = rurl(s.character.portrait, 'neutral', s.theme);
    return `<div class="save" data-id="${esc(s.id)}">
      <div class="sv-pt">${pt ? `<img src="${pt}">` : '<div class="sv-empty">?</div>'}</div>
      <div class="sv-info"><div class="sv-name">${esc(s.name)}</div>
        <div class="sv-ch">${esc(s.character.name || '—')}${s.character.archetype ? ' · ' + esc(s.character.archetype) : ''}${s.character.level ? ' · Lv ' + s.character.level : ''}</div>
        <div class="sv-meta"><span>${esc(s.theme_name)}</span><span>Turn ${s.turn}</span><span>Run ${s.runs || 1}${s.deaths ? ' · ' + '☠'.repeat(Math.min(s.deaths,5)) : ''}</span>
          <span class="st ${esc(s.status)}">${esc(s.status)}</span></div>
        <div class="sv-loc">${s.location ? esc(s.location) + ' · ' : ''}${ago(s.updated)}</div></div>
      <div class="sv-act"><button class="mbtn" data-load>Load</button><button class="mbtn ghost danger" data-del>Delete</button></div></div>`; }).join('');
  root.innerHTML = frame(`<div class="mm-head">${backBtn()}<h2>Continue</h2></div><div class="saves">${cards || '<div class="muted">No saves yet.</div>'}</div>${dmLine()}`, 'wide');
  wireBack();
  root.querySelectorAll('.save').forEach(c => {
    c.querySelector('[data-load]').onclick = () => busy('Loading save…', async () => { await post('/api/load', {id: c.dataset.id}); await CD.fetchState(); });
    c.querySelector('[data-del]').onclick = e => { const b = e.target;
      if (b.dataset.armed){ post('/api/delete_save', {id: c.dataset.id}).then(refresh).catch(x => toast(x.message)); }
      else { b.dataset.armed = 1; b.textContent = 'Confirm delete'; setTimeout(() => { b.textContent = 'Delete'; delete b.dataset.armed; }, 3500); } };
  });
}

// ---------- settings ----------
function renderSettings(){
  const c = M.control || {}; const locked = !!M.active;
  root.innerHTML = frame(`<div class="mm-head">${backBtn(inGame ? 'ingame' : 'main')}<h2>Settings</h2></div>
   <div class="set">
    <div class="set-row"><label>Voice narration</label><button class="tog ${c.voice?'on':''}" data-k="voice">${c.voice?'On':'Off'}</button></div>
    <div class="set-row"><label>Volume</label><input type="range" min="0" max="1" step="0.05" value="${c.volume ?? .9}" data-k="volume"><button class="mbtn small ghost" data-test>Test voice</button></div>
    <div class="set-row"><label>Sound effects (dice)</label><button class="tog ${c.sfx!==false?'on':''}" data-k="sfx">${c.sfx!==false?'On':'Off'}</button></div>
    <div class="set-row"><label>Text speed</label><select data-k="text_speed">${['slow','normal','fast','instant'].map(s => `<option ${ (c.text_speed||'normal')===s?'selected':''}>${s}</option>`).join('')}</select></div>
    <div class="set-row"><label>Play mode</label><div class="seg">${['live','nudge'].map(m => `<button data-mode="${m}" class="${(c.mode||'live')===m?'on':''}">${m==='live'?'Live':'Nudge'}</button>`).join('')}</div>
      <div class="hint">${(c.mode||'live')==='live' ? 'The DM waits for your browser input (small idle cost).' : "Queue actions, then type 'go' in chat (no idle cost)."}</div></div>
    <div class="danger ${locked?'locked':''}"><h3>Danger zone</h3>${locked ? '<div class="hint">Only available from the main menu. Save &amp; quit first.</div>' : ''}
      <div class="set-row"><div><label>Regenerate images &amp; sprites</label><div class="hint">Clears image and voice caches, redraws every theme asset preview and rebuilds the template catalog. Your art is kept.</div></div>
        <button class="mbtn" data-regen ${locked?'disabled':''}>Regenerate</button></div>
      <div class="set-row"><div><label>Format everything</label><div class="hint">Deletes ALL themes, saves, characters, assets, caches and settings. Cannot be undone. Type FORMAT to confirm.</div></div>
        <input class="fmt" placeholder="FORMAT" ${locked?'disabled':''}><button class="mbtn danger" data-format ${locked?'disabled':''}>Format</button></div>
    </div></div>`, 'wide');
  wireBack();
  const save = ch => CD.saveSettings(ch).then(refresh).then(() => CD.fetchState());
  root.querySelectorAll('.tog').forEach(b => b.onclick = () => { CD.ensureCtx(); save({[b.dataset.k]: !b.classList.contains('on')}); });
  root.querySelector('[data-k=volume]').onchange = e => save({volume: parseFloat(e.target.value)});
  root.querySelector('[data-k=text_speed]').onchange = e => save({text_speed: e.target.value});
  root.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => save({mode: b.dataset.mode}));
  root.querySelector('[data-test]').onclick = () => { CD.ensureCtx(); const was = CD.voiceOn; CD.voiceOn = true; CD.volume = c.volume ?? .9;
    CD.speak('The dice are cast. Let the story begin.', {voice:'en-US-GuyNeural', rate:'-4%', pitch:'-2Hz'}).then(ok => { CD.voiceOn = was; if (!ok) toast('Voice failed - check internet / rerun setup.bat'); }); };
  const rg = root.querySelector('[data-regen]'); if (rg) rg.onclick = e => { const b = e.target;
    if (!b.dataset.armed){ b.dataset.armed = 1; b.textContent = 'Click again to confirm'; return; }
    busy('Regenerating images & sprites…', () => post('/api/regenerate', {voice: true})).then(r => { toast(`Regenerated ${r.assets_rerendered} assets, ${r.templates} templates`); refresh(); }).catch(x => toast(x.message)); };
  const fb = root.querySelector('[data-format]'); if (fb) fb.onclick = () => { const v = root.querySelector('.fmt').value.trim();
    if (v !== 'FORMAT'){ toast('Type FORMAT to confirm'); return; }
    busy('Formatting…', () => post('/api/format', {confirm: 'FORMAT'})).then(() => { wiz = null; toast('Everything was formatted.'); go('main'); refresh(); CD.fetchState(); }).catch(x => toast(x.message)); };
}

// ---------- in-game menu ----------
function openInGame(){ inGame = true; page = 'ingame'; refresh().then(() => { root.classList.remove('hidden'); renderPage(); }); }
function renderInGame(){
  root.innerHTML = `<div class="mm-veil solid"></div><div class="mm-wrap main">
    <div class="mm-title small">Menu</div>
    <div class="mm-buttons"><button class="mbtn big" data-r>Resume</button><button class="mbtn big" data-s>Settings</button><button class="mbtn big" data-q>Save &amp; Quit to Main Menu</button></div></div>`;
  root.querySelector('[data-r]').onclick = hide;
  root.querySelector('[data-s]').onclick = () => go('settings');
  root.querySelector('[data-q]').onclick = () => busy('Saving…', () => post('/api/quit', {})).then(() => { inGame = false; page = 'main'; CD.fetchState(); });
}

// ======================= NEW GAME WIZARD =======================
const PAGES = ['Theme', 'Rules', 'Identity', 'Stats', 'Look', 'Story & Party', 'Begin'];
const TONES = ['Grim','Heroic','Pulpy','Noir','Horror','Mystery','Action','Comedic','Political','Romantic','Survival','Weird'];
const LIMITS = ['Graphic violence','Gore','Body horror','Torture','Drug use','Sexual content','Animal harm','Harm to children','Self-harm','Slurs','Spiders','Insects'];
const SKIN = ['#f3d2b3','#e8b890','#d9a37a','#c98e62','#a86b45','#8d5a3b','#6b4630','#4a3022','#9fb89a','#b38fd0','#8fb4d9','#c95a5a'];
const HAIR = ['#1b1410','#3a2a1a','#5a3a22','#8a5a2a','#b8452a','#d9a441','#e8d8a8','#dddddd','#777777','#e04a8a','#3aa0ff','#3aff9a','#8a3aff','#ff7a2a'];
const CLOTH = ['#2a2a33','#4a4358','#3d6fa8','#2f5f4a','#6b4a2e','#7a3a2a','#8a2a3a','#4a3a8a','#c9a24a','#d8d0c0','#1a1a1a','#5a6a7a','#e04a8a','#3ad0ff','#ff8a3a','#9aa4b1'];
const EYES = ['#2a2233','#3a6aa8','#3a8a4a','#7a4a2a','#8a8a8a','#c0303a','#e0b030','#3ad0ff'];
const HAIRS = {short:['hair_short','p_hair_short'], long:['hair_long','p_hair_long',true], spiky:['hair_spiky','p_hair_spiky'], bun:['hair_bun','p_hair_bun'],
  ponytail:['hair_ponytail','p_hair_bob'], mohawk:['hair_mohawk','p_hair_mohawk'], curly:['hair_curly','p_hair_curly'], bob:['hair_long','p_hair_bob'], slick:['hair_short','p_hair_slick'], bald:[null,null]};
const OUTFITS = {shirt:['top_shirt','p_outfit_shirt'], coat:['top_coat','p_outfit_coat'], robe:['top_robe','p_outfit_robe'], armor:['top_armor','p_outfit_armor'],
  jacket:['top_jacket','p_outfit_coat'], hoodie:['top_jacket','p_outfit_hoodie'], vest:['top_vest','p_outfit_shirt'], uniform:['top_jacket','p_outfit_uniform'], rags:['top_shirt','p_outfit_rags']};
const HATS = {none:[null,null], hood:['hat_hood','p_hat_hood'], helmet:['hat_helmet','p_hat_helmet'], cap:['hat_cap','p_hat_cap'], wizard:['hat_wizard','p_hat_wizard'],
  wide:['hat_wide','p_hat_wide'], crown:['crown','p_crown'], headband:[null,'p_headband']};
const EXTRAS = {beard:['beard','p_beard'], mustache:[null,'p_mustache'], glasses:[null,'p_glasses'], goggles:['goggles','p_visor'], eyepatch:['eyepatch','p_eyepatch'],
  scar:[null,'p_scar'], mask:['mask','p_mask'], marks:[null,'p_marks'], 'pointed ears':['ears_pointy','p_ears_pointy'], earring:[null,'p_earring'], horns:['horns','p_horns']};
const HELD = ['none','sword','staff','dagger','gun','rifle','bow','axe','torch'], OFF = ['none','shield','lantern','book'], BACK = ['none','cloak','wings','tail'];
const EXPR = ['neutral','happy','angry','sad','surprised','smirk','determined','scared'];
const STY_SPRITE = {layers:['tpl:body','tpl:legs_pants','tpl:boots','tpl:top_jacket','tpl:hair_short','tpl:held_gun'],
  colors:{skin:'#c98e62', hair:'#8a3aff', top:'#2b3a6b', accent:'#ff8a3a', metal:'#9aa4b1', glow:'#2ff0ff'}};
const STY_PORTRAIT = {layers:['tpl:p_base','tpl:p_face_determined','tpl:p_outfit_coat','tpl:p_hair_short'],
  colors:{skin:'#c98e62', hair:'#8a3aff', top:'#2b3a6b', accent:'#ff8a3a'}};
const COST = {8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9};
const ARRAY = [15,14,13,12,10,8];

function newDraft(){ return { page: 1, theme: null, rules: { tone: [], content_limits: [], difficulty: 'standard', permadeath: 'strict', session_length: 'medium' },
  character: { name: '', pronouns: 'they/them', archetype: '', stats_method: 'array', stats: {}, rolled: [], assign: {},
    look: { build:'normal', skin:'#d9a37a', hair:'short', hair_color:'#3a2a1a', eyes:'#2a2233', jaw:'normal', outfit:'shirt', top:'#3d6fa8', accent:'#c9a24a',
            legs:'pants', legs_color:'#4a4358', boots:true, boots_color:'#5b3a26', hat:'none', extras:[], held:'none', offhand:'none', back:'none', theme_parts:[] },
    backstory: '', hooks: ['', '', ''] }, party: { mode: 'solo', notes: '' }, campaign_name: '', style: null }; }
function startWizard(){ wiz = (M.draft && M.draft.page) ? mergeDraft(newDraft(), M.draft) : newDraft(); }
function mergeDraft(a, b){ for (const k in b){ if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object') mergeDraft(a[k], b[k]); else a[k] = b[k]; } return a; }
function saveDraft(){ clearTimeout(saveT); saveT = setTimeout(() => { buildRecipes(); post('/api/draft', {draft: wiz}).catch(()=>{}); }, 500); }
function theme(){ return (M.themes||[]).find(t => t.slug === wiz.theme); }

function buildRecipes(){
  const L = wiz.character.look; const colors = {skin:L.skin, hair:L.hair_color, eyes:L.eyes, top:L.top, accent:L.accent, legs:L.legs_color, boots:L.boots_color};
  const sp = [], pt = [];
  if (L.back !== 'none') sp.push('tpl:' + (L.back === 'cloak' ? 'cloak' : L.back));
  sp.push('tpl:body'); sp.push('tpl:legs_' + (L.legs === 'skirt' ? 'skirt' : 'pants')); if (L.boots) sp.push('tpl:boots');
  const o = OUTFITS[L.outfit] || OUTFITS.shirt; sp.push('tpl:' + o[0]);
  const h = HAIRS[L.hair] || HAIRS.short; if (h[0]) sp.push('tpl:' + h[0]);
  const hat = HATS[L.hat] || HATS.none; if (hat[0]) sp.push('tpl:' + hat[0]);
  for (const x of L.extras){ const e = EXTRAS[x]; if (e && e[0]) sp.push('tpl:' + e[0]); }
  if (L.held !== 'none') sp.push('tpl:held_' + L.held); if (L.offhand !== 'none') sp.push('tpl:offhand_' + L.offhand);
  if (h[2]) pt.push('tpl:p_hair_back'); pt.push({part:'tpl:p_base', params:{jaw: L.jaw}}); pt.push('tpl:p_face_{expr}'); pt.push('tpl:' + o[1]);
  if (h[1]) pt.push('tpl:' + h[1]); for (const x of L.extras){ const e = EXTRAS[x]; if (e && e[1]) pt.push('tpl:' + e[1]); } if (hat[1]) pt.push('tpl:' + hat[1]);
  wiz.character.sprite = {layers: sp, colors, params: {build: L.build}};
  wiz.character.portrait = {layers: pt, colors};
}

function diceStyle(){ const T = theme(); const d = (T && T.ui && T.ui.dice) || {}; return {color: d.color, ink: d.ink, style: d.style, font: d.font}; }
function applyThemeUI(T){ const r = document.documentElement.style; resetTheme(); if (!T) return; const u = T.ui || {};
  for (const [k,v] of Object.entries({accent:'--accent',bg:'--bg',panel:'--panel',text:'--text',panel2:'--panel2',line:'--line',muted:'--muted'})) if (u[k]) r.setProperty(v, u[k]); }
function renderWizard(){
  if (!wiz) startWizard();
  const p = wiz.page, T = theme(); applyThemeUI(T);
  const steps = PAGES.map((n, i) => `<div class="wz-step ${i+1===p?'on':''} ${i+1<p?'done':''}" data-p="${i+1}"><span>${i+1}</span>${n}</div>`).join('');
  root.innerHTML = frame(`<div class="mm-head">${backBtn()}<h2>New Game</h2><div class="wz-theme">${T ? esc(T.name) : ''}</div></div>
    <div class="wz-steps">${steps}<div class="wz-prog"><i style="width:${(p-1)/(PAGES.length-1)*100}%"></i></div></div>
    <div class="wz-body" id="wzb"></div>
    <div class="wz-nav"><button class="mbtn" data-prev ${p===1?'disabled':''}>← Previous</button><div class="wz-err" id="wzerr"></div>
      ${p < PAGES.length ? `<button class="mbtn primary" data-next>Next →</button>` : `<button class="mbtn primary big-begin" data-begin>Begin the adventure</button>`}</div>`, 'wide wizard');
  wireBack();
  root.querySelectorAll('.wz-step').forEach(s => s.onclick = () => { const t = +s.dataset.p; if (t < p || valid(p, true)) { wiz.page = Math.min(t, maxReach()); saveDraft(); renderPage(); } });
  root.querySelector('[data-prev]').onclick = () => { wiz.page--; saveDraft(); renderPage(); };
  const nx = root.querySelector('[data-next]'); if (nx) nx.onclick = () => { if (valid(p)) { wiz.page++; saveDraft(); renderPage(); root.scrollTop = 0; } };
  const bg = root.querySelector('[data-begin]'); if (bg) bg.onclick = begin;
  const body = $('#wzb');
  [null, pgTheme, pgRules, pgIdentity, pgStats, pgLook, pgStory, pgReview][p](body);
}
function maxReach(){ let m = 1; while (m < PAGES.length && valid(m, true)) m++; return m; }
function err(t){ const e = $('#wzerr'); if (e) e.textContent = t || ''; return !t; }
function valid(p, quiet){
  const say = t => quiet ? false : err(t);
  if (p === 1){ if (!wiz.theme || !theme()) return say('Pick a theme, or build a new one.'); if (wiz.theme_status === 'building') return say('Wait for the DM to finish the theme.'); }
  if (p === 3){ if (!wiz.character.name.trim()) return say('Your character needs a name.'); if (!wiz.character.archetype.trim()) return say('Choose an archetype (or type your own).'); }
  if (p === 4){ const T = theme(); const need = (T && T.stats || []).map(s => s.key); if (need.some(k => wiz.character.stats[k] == null)) return say('Assign every stat.'); }
  return quiet ? true : err('');
}

// ---- page 1: theme
function pgTheme(b){
  const cards = (M.themes||[]).map(t => `<div class="th ${wiz.theme===t.slug?'on':''}" data-slug="${esc(t.slug)}">
      <div class="th-bg" style="background-image:url('${rurl(t.backdrop || {layers:['tpl:bd_void']}, null, t.slug)}')"></div>
      <div class="th-in"><div class="th-name">${esc(t.name)}</div><div class="th-desc">${esc(t.description||'')}</div>
      <div class="th-meta">${(t.archetypes||[]).length} archetypes · ${t.assets} assets · ${t.maps} maps</div>
      <div class="th-act"><button class="mbtn small" data-pick>${wiz.theme===t.slug?'Selected ✓':'Select'}</button><button class="mbtn small ghost" data-mod>Modify…</button></div>
      <div class="th-modbox hidden"><textarea placeholder="What should the DM change or add? (e.g. add a hacker archetype, make it darker, rename Health to Integrity)"></textarea><button class="mbtn small" data-send>Ask the DM</button></div></div></div>`).join('');
  const st = wiz.theme_status === 'failed' ? `<div class="wz-note bad">The DM couldn't build that theme: ${esc(wiz.theme_note||'')}</div>` :
             wiz.theme_status === 'ready' && wiz.theme_note ? `<div class="wz-note">${esc(wiz.theme_note)}</div>` : '';
  b.innerHTML = `${st}<h3>Choose a world</h3><div class="themes">${cards || '<div class="muted">No themes yet — create your first one below.</div>'}</div>
    <h3>…or create a new one</h3><div class="newth">
      <textarea id="nt-desc" placeholder="Describe the world in your own words: genre, setting, mood, what kind of stories you want. e.g. 'Cyberpunk megacity, rain and neon, corporate espionage and street samurai.'">${esc((wiz.new_theme||{}).description||'')}</textarea>
      <input id="nt-mood" placeholder="Optional mood words (e.g. noir, hopeful, brutal)" value="${esc((wiz.new_theme||{}).mood||'')}">
      <button class="mbtn primary" id="nt-go">Build this theme</button>
      <div class="hint">The DM designs the stats, resources, archetypes, colours and narrator voice. Takes about a minute and needs the DM connected.</div></div>
    ${pgStyleBlock()}`;
  wireStyle(b);
  b.querySelectorAll('.th').forEach(c => {
    c.querySelector('[data-pick]').onclick = () => { wiz.theme = c.dataset.slug; wiz.theme_status = null; saveDraft(); renderPage(); };
    c.querySelector('[data-mod]').onclick = () => c.querySelector('.th-modbox').classList.toggle('hidden');
    c.querySelector('[data-send]').onclick = () => { const t = c.querySelector('textarea').value.trim(); if (!t) return;
      wiz.theme = c.dataset.slug; wiz.theme_status = 'building'; saveDraft();
      post('/api/wizard/build_theme', {description: t, base: c.dataset.slug, style: curStyle()}).then(refresh).catch(x => err(x.message)); };
  });
  $('#nt-desc').oninput = e => { wiz.new_theme = {...(wiz.new_theme||{}), description: e.target.value}; saveDraft(); };
  $('#nt-mood').oninput = e => { wiz.new_theme = {...(wiz.new_theme||{}), mood: e.target.value}; saveDraft(); };
  $('#nt-go').onclick = () => { const d = (wiz.new_theme||{}); if (!(d.description||'').trim()) return err('Describe the theme first.');
    wiz.theme_status = 'building'; saveDraft();
    post('/api/wizard/build_theme', {description: d.description, mood: d.mood, style: curStyle()}).then(refresh).catch(x => err(x.message)); };
}
function curStyle(){ const T = theme(); return wiz.style || (T && T.style) || M.default_style || 'classic'; }
function pgStyleBlock(){
  const cur = curStyle();
  const cards = (M.styles||[]).map(x => `<div class="sty ${x.id===cur?'on':''}" data-sty="${esc(x.id)}" title="${esc(x.blurb)}">
      <div class="sty-fig"><img src="${rurl(STY_PORTRAIT,'determined',wiz.theme,x.id)}" alt=""><img class="sp" src="${rurl(STY_SPRITE,null,wiz.theme,x.id)}" alt=""></div>
      <div class="sty-name">${esc(x.name)}</div><div class="sty-blurb">${esc(x.blurb)}</div></div>`).join('');
  return `<h3>Art style</h3><div class="hint hint-top">Chosen before anything is drawn. It restyles every sprite,
    portrait, tile and backdrop in the game &mdash; no new artwork, the same parts rendered differently.</div>
    <div class="styles">${cards}</div>`;
}
function wireStyle(b){
  b.querySelectorAll('.sty').forEach(c => c.onclick = () => { wiz.style = c.dataset.sty; saveDraft(); renderPage(); });
}
// ---- page 2: rules
function chips(list, sel, key){ return list.map(x => `<button class="chip2 ${sel.includes(x)?'on':''}" data-${key}="${esc(x)}">${esc(x)}</button>`).join(''); }
function seg(name, opts, cur){ return `<div class="seg" data-seg="${name}">${opts.map(([v,l]) => `<button data-v="${v}" class="${cur===v?'on':''}">${l}</button>`).join('')}</div>`; }
function pgRules(b){
  const R = wiz.rules;
  b.innerHTML = `<h3>Tone</h3><div class="chips">${chips(TONES, R.tone, 'tone')}</div><input id="r-tone" placeholder="Anything else about the tone?" value="${esc(R.tone_note||'')}">
    <h3>Content limits <span class="hint">(selected = kept off-screen or left out)</span></h3><div class="chips">${chips(LIMITS, R.content_limits, 'lim')}</div>
    <input id="r-lim" placeholder="Other lines or veils" value="${esc(R.limits_note||'')}">
    <div class="grid3"><div><h3>Difficulty</h3>${seg('difficulty', [['story','Story'],['standard','Standard'],['brutal','Brutal']], R.difficulty)}
        <div class="hint">${{story:'Forgiving; failure rarely kills.', standard:'Fair risks, real consequences.', brutal:'Smart enemies, scarce resources.'}[R.difficulty]}</div></div>
      <div><h3>Permadeath</h3>${seg('permadeath', [['strict','Strict'],['lenient','Lenient']], R.permadeath)}
        <div class="hint">${R.permadeath==='strict' ? 'Death ends the run.' : 'One costly revival per run.'}</div></div>
      <div><h3>Session length</h3>${seg('session_length', [['short','~30 min'],['medium','~1 hour'],['long','2h+']], R.session_length)}</div></div>`;
  b.querySelectorAll('[data-tone]').forEach(c => c.onclick = () => { tog(R.tone, c.dataset.tone); saveDraft(); renderPage(); });
  b.querySelectorAll('[data-lim]').forEach(c => c.onclick = () => { tog(R.content_limits, c.dataset.lim); saveDraft(); renderPage(); });
  b.querySelectorAll('[data-seg]').forEach(s => s.querySelectorAll('button').forEach(x => x.onclick = () => { R[s.dataset.seg] = x.dataset.v; saveDraft(); renderPage(); }));
  $('#r-tone').oninput = e => { R.tone_note = e.target.value; saveDraft(); }; $('#r-lim').oninput = e => { R.limits_note = e.target.value; saveDraft(); };
}
function tog(arr, v){ const i = arr.indexOf(v); if (i >= 0) arr.splice(i, 1); else arr.push(v); }
// ---- page 3: identity
function pgIdentity(b){
  const C = wiz.character, T = theme();
  const arch = (T && T.archetypes || []).map(a => `<div class="arch ${C.archetype_id===a.id?'on':''}" data-id="${esc(a.id)}"><div class="an">${esc(a.name)}</div><div class="ad">${esc(a.desc||'')}</div>
     ${a.stat_bonus ? `<div class="ab">${Object.entries(a.stat_bonus).map(([k,v]) => `${esc(k.toUpperCase())} ${v>0?'+':''}${v}`).join(' · ')}</div>` : ''}</div>`).join('');
  b.innerHTML = `<div class="grid2"><div><h3>Name</h3><input id="c-name" maxlength="40" value="${esc(C.name)}" placeholder="Your character's name"></div>
     <div><h3>Pronouns</h3><div class="row">${seg('pronouns', [['he/him','he/him'],['she/her','she/her'],['they/them','they/them']], C.pronouns)}<input id="c-pro" placeholder="custom" value="${esc(['he/him','she/her','they/them'].includes(C.pronouns)?'':C.pronouns)}"></div></div></div>
     <h3>Archetype</h3><div class="archs">${arch || '<div class="muted">This theme has no archetypes yet — type one below.</div>'}</div>
     <input id="c-arch" placeholder="…or a custom archetype" value="${esc(C.archetype_id ? '' : C.archetype)}">`;
  $('#c-name').oninput = e => { C.name = e.target.value; saveDraft(); };
  b.querySelectorAll('[data-seg=pronouns] button').forEach(x => x.onclick = () => { C.pronouns = x.dataset.v; saveDraft(); renderPage(); });
  $('#c-pro').oninput = e => { if (e.target.value.trim()) { C.pronouns = e.target.value.trim(); saveDraft(); } };
  b.querySelectorAll('.arch').forEach(a => a.onclick = () => { const A = T.archetypes.find(x => x.id === a.dataset.id); C.archetype_id = A.id; C.archetype = A.name; saveDraft(); renderPage(); });
  $('#c-arch').oninput = e => { C.archetype_id = null; C.archetype = e.target.value; saveDraft(); b.querySelectorAll('.arch').forEach(a => a.classList.remove('on')); };
}
// ---- page 4: stats
function bonus(){ const T = theme(); const A = T && (T.archetypes||[]).find(a => a.id === wiz.character.archetype_id); return (A && A.stat_bonus) || {}; }
function pgStats(b){
  const C = wiz.character, T = theme(), stats = (T && T.stats) || [], B = bonus();
  const mod = v => { const m = Math.floor((v-10)/2); return (m>=0?'+':'')+m; };
  const method = C.stats_method;
  let pool = method === 'array' ? ARRAY : method === 'roll' ? C.rolled : null;
  const spent = method === 'point' ? stats.reduce((s, st) => s + (COST[C.assign[st.key] ?? 8] ?? 0), 0) : 0;
  const rows = stats.map(st => {
    let ctl = '';
    if (method === 'point'){ const v = C.assign[st.key] ?? 8; ctl = `<div class="pb"><button data-dec="${st.key}">−</button><b>${v}</b><button data-inc="${st.key}">+</button></div>`; }
    else { const used = Object.entries(C.assign).filter(([k]) => k !== st.key).map(([,i]) => i);
      ctl = `<select data-as="${st.key}"><option value="">—</option>${(pool||[]).map((v,i) => `<option value="${i}" ${C.assign[st.key]===i?'selected':''} ${used.includes(i)?'disabled':''}>${v}</option>`).join('')}</select>`; }
    const base = method === 'point' ? (C.assign[st.key] ?? 8) : (C.assign[st.key] != null && pool ? pool[C.assign[st.key]] : null);
    const fin = base == null ? null : base + (B[st.key]||0);
    return `<div class="strow"><div class="stn"><b>${esc(st.abbr||st.key)}</b> ${esc(st.name||'')}</div>${ctl}<div class="stb">${B[st.key] ? (B[st.key]>0?'+':'')+B[st.key] : ''}</div><div class="stf">${fin ?? '–'}</div><div class="stm">${fin!=null?mod(fin):''}</div></div>`; }).join('');
  b.innerHTML = `<h3>How do you want your stats?</h3>${seg('method', [['array','Standard array'],['roll','Roll 4d6 drop lowest'],['point','Point-buy (27)']], method)}
    ${method === 'roll' ? `<div class="rollbar"><button class="mbtn primary" id="st-roll">${C.rolled.length ? 'Reroll all' : 'Roll the dice'}</button><div class="rolled">${C.rolled.map(v => `<span>${v}</span>`).join('')}</div></div>` : ''}
    ${method === 'point' ? `<div class="hint">Points spent: <b>${spent}</b> / 27</div>` : ''}
    <div class="stats2">${rows}</div><div class="hint">Archetype bonuses are added automatically.</div>`;
  b.querySelectorAll('[data-seg=method] button').forEach(x => x.onclick = () => { C.stats_method = x.dataset.v; C.assign = {}; C.stats = {}; saveDraft(); renderPage(); });
  b.querySelectorAll('[data-as]').forEach(s => s.onchange = () => { if (s.value === '') delete C.assign[s.dataset.as]; else C.assign[s.dataset.as] = +s.value; finalize(); renderPage(); });
  b.querySelectorAll('[data-inc],[data-dec]').forEach(x => x.onclick = () => { const k = x.dataset.inc || x.dataset.dec; const v = C.assign[k] ?? 8;
    const nv = x.dataset.inc ? Math.min(15, v+1) : Math.max(8, v-1); const newSpent = spent - COST[v] + COST[nv]; if (newSpent > 27) return err('Not enough points.');
    C.assign[k] = nv; finalize(); renderPage(); });
  if (method === 'point') stats.forEach(st => { if (C.assign[st.key] == null) C.assign[st.key] = 8; });
  finalize();
  const rb = $('#st-roll'); if (rb) rb.onclick = rollStats;
  function finalize(){ C.stats = {}; for (const st of stats){ const base = method === 'point' ? (C.assign[st.key] ?? 8) : (C.assign[st.key] != null && pool ? pool[C.assign[st.key]] : null);
    if (base != null) C.stats[st.key] = base + (B[st.key]||0); } saveDraft(); }
}
async function rollStats(){
  const C = wiz.character, T = theme(); const n = ((T && T.stats) || []).length || 6; C.rolled = []; C.assign = {}; C.stats = {};
  const host = $('#menu-dice'); host.classList.remove('hidden');
  for (let i = 0; i < n; i++){
    const r = await post('/api/roll', {expr: '4d6kh3'});
    r.reason = `Stat ${i+1} of ${n}`; await Dice.show(r, {host, hold: 1100, style: diceStyle(), volume: (M.control?.sfx !== false) ? (M.control?.volume ?? .8) : 0, playerName: C.name || 'You'});
    C.rolled.push(r.total);
  }
  host.classList.add('hidden'); saveDraft(); renderPage();
}
// ---- page 5: look
function swatches(list, cur, key){ return `<div class="sw">${list.map(c => `<button style="background:${c}" class="${cur===c?'on':''}" data-sw="${key}" data-c="${c}"></button>`).join('')}<input type="color" value="${cur}" data-swc="${key}"></div>`; }
function opts(list, cur, key){ return `<div class="opts">${list.map(x => `<button class="${cur===x?'on':''}" data-opt="${key}" data-v="${esc(x)}">${esc(x)}</button>`).join('')}</div>`; }
let lookTab = 'body', lookExpr = 'neutral';
function pgLook(b){
  const L = wiz.character.look; buildRecipes();
  const C = wiz.character;
  const tabs = {body:'Body', hair:'Hair', face:'Face', outfit:'Outfit', head:'Headwear', gear:'Gear'};
  let panel = '';
  if (lookTab === 'body') panel = `<h4>Build</h4>${opts(['slim','normal','broad'], L.build, 'build')}<h4>Skin</h4>${swatches(SKIN, L.skin, 'skin')}<h4>Jaw</h4>${opts(['narrow','normal','square'], L.jaw, 'jaw')}<h4>Back</h4>${opts(BACK, L.back, 'back')}`;
  if (lookTab === 'hair') panel = `<h4>Style</h4>${opts(Object.keys(HAIRS), L.hair, 'hair')}<h4>Colour</h4>${swatches(HAIR, L.hair_color, 'hair_color')}`;
  if (lookTab === 'face') panel = `<h4>Eyes</h4>${swatches(EYES, L.eyes, 'eyes')}<h4>Extras</h4><div class="opts">${Object.keys(EXTRAS).map(x => `<button class="${L.extras.includes(x)?'on':''}" data-ex="${esc(x)}">${esc(x)}</button>`).join('')}</div>`;
  if (lookTab === 'outfit') panel = `<h4>Outfit</h4>${opts(Object.keys(OUTFITS), L.outfit, 'outfit')}<h4>Main colour</h4>${swatches(CLOTH, L.top, 'top')}<h4>Accent colour</h4>${swatches(CLOTH, L.accent, 'accent')}
     <h4>Legs</h4>${opts(['pants','skirt'], L.legs, 'legs')}${swatches(CLOTH, L.legs_color, 'legs_color')}<h4>Boots</h4>${opts(['on','off'], L.boots?'on':'off', 'boots')}${swatches(CLOTH, L.boots_color, 'boots_color')}`;
  if (lookTab === 'head') panel = `<h4>Headwear</h4>${opts(Object.keys(HATS), L.hat, 'hat')}<div class="hint">Headwear uses the accent colour.</div>`;
  if (lookTab === 'gear') panel = `<h4>Main hand</h4>${opts(HELD, L.held, 'held')}<h4>Off hand</h4>${opts(OFF, L.offhand, 'offhand')}`;
  b.innerHTML = `<div class="look"><div class="look-prev">
      <div class="lp-pt"><img src="${rurl(C.portrait, lookExpr, wiz.theme)}"></div>
      <div class="opts ex">${EXPR.map(e => `<button class="${lookExpr===e?'on':''}" data-expr="${e}">${e}</button>`).join('')}</div>
      <div class="lp-sp"><img src="${rurl(C.sprite, null, wiz.theme)}"></div>
      <button class="mbtn" id="lk-rand">🎲 Randomize</button></div>
    <div class="look-ctl"><div class="ltabs">${Object.entries(tabs).map(([k,l]) => `<button class="${lookTab===k?'on':''}" data-lt="${k}">${l}</button>`).join('')}</div><div class="lpanel">${panel}</div></div></div>`;
  const upd = () => { saveDraft(); renderPage(); };
  b.querySelectorAll('[data-lt]').forEach(x => x.onclick = () => { lookTab = x.dataset.lt; renderPage(); });
  b.querySelectorAll('[data-expr]').forEach(x => x.onclick = () => { lookExpr = x.dataset.expr; renderPage(); });
  b.querySelectorAll('[data-sw]').forEach(x => x.onclick = () => { L[x.dataset.sw] = x.dataset.c; upd(); });
  b.querySelectorAll('[data-swc]').forEach(x => x.onchange = () => { L[x.dataset.swc] = x.value; upd(); });
  b.querySelectorAll('[data-opt]').forEach(x => x.onclick = () => { const k = x.dataset.opt; L[k] = k === 'boots' ? x.dataset.v === 'on' : x.dataset.v; upd(); });
  b.querySelectorAll('[data-ex]').forEach(x => x.onclick = () => { tog(L.extras, x.dataset.ex); upd(); });
  $('#lk-rand').onclick = () => { const pick = a => a[Math.floor(Math.random()*a.length)];
    Object.assign(L, { build: pick(['slim','normal','broad']), skin: pick(SKIN.slice(0,8)), hair: pick(Object.keys(HAIRS)), hair_color: pick(HAIR), eyes: pick(EYES),
      jaw: pick(['narrow','normal','square']), outfit: pick(Object.keys(OUTFITS)), top: pick(CLOTH), accent: pick(CLOTH), legs: pick(['pants','pants','skirt']),
      legs_color: pick(CLOTH), boots: Math.random() < .85, boots_color: pick(CLOTH), hat: Math.random() < .5 ? 'none' : pick(Object.keys(HATS)),
      extras: Object.keys(EXTRAS).filter(() => Math.random() < .12), held: pick(HELD), offhand: Math.random() < .6 ? 'none' : pick(OFF), back: Math.random() < .7 ? 'none' : pick(BACK) }); upd(); };
}
// ---- page 6: story & party
function pgStory(b){
  const C = wiz.character, P = wiz.party;
  b.innerHTML = `<h3>Backstory</h3><textarea id="s-bs" rows="5" placeholder="Where does ${esc(C.name||'your character')} come from? What do they want? What haunts them?">${esc(C.backstory)}</textarea>
    <h3>Hooks <span class="hint">(1–3 threads the DM can pull on)</span></h3>
    ${[0,1,2].map(i => `<input class="hook" data-i="${i}" value="${esc(C.hooks[i]||'')}" placeholder="${['A debt, a secret, a rival…','A person you are looking for…','Something you swore to do…'][i]}">`).join('')}
    <h3>Party</h3>${seg('party', [['solo','Solo'],['one','+1 companion'],['two','+2 companions']], P.mode)}
    <textarea id="s-party" rows="2" placeholder="Optional: who would you like at your side? (the DM designs and plays them)">${esc(P.notes||'')}</textarea>`;
  $('#s-bs').oninput = e => { C.backstory = e.target.value; saveDraft(); };
  b.querySelectorAll('.hook').forEach(h => h.oninput = () => { C.hooks[+h.dataset.i] = h.value; saveDraft(); });
  b.querySelectorAll('[data-seg=party] button').forEach(x => x.onclick = () => { P.mode = x.dataset.v; saveDraft(); renderPage(); });
  $('#s-party').oninput = e => { P.notes = e.target.value; saveDraft(); };
}
// ---- page 7: review
function pgReview(b){
  buildRecipes(); const C = wiz.character, T = theme(), R = wiz.rules;
  b.innerHTML = `<div class="review"><div class="rv-fig"><img class="pt" src="${rurl(C.portrait,'determined',wiz.theme)}"><img class="sp" src="${rurl(C.sprite,null,wiz.theme)}"></div>
    <div class="rv-info"><h2>${esc(C.name)}</h2><div class="muted">${esc(C.pronouns)} · ${esc(C.archetype)} · ${esc(T ? T.name : '')}</div>
      <div class="rv-stats">${((T&&T.stats)||[]).map(s => `<div><b>${esc(s.abbr||s.key)}</b>${C.stats[s.key] ?? '–'}</div>`).join('')}</div>
      <div class="rv-line"><b>Tone</b> ${esc([...R.tone, R.tone_note].filter(Boolean).join(', ') || 'DM decides')}</div>
      <div class="rv-line"><b>Limits</b> ${esc([...R.content_limits, R.limits_note].filter(Boolean).join(', ') || 'none')}</div>
      <div class="rv-line"><b>Rules</b> ${esc(R.difficulty)} · permadeath ${esc(R.permadeath)} · ${esc(R.session_length)} sessions</div>
      <div class="rv-line"><b>Party</b> ${esc({solo:'Solo',one:'+1 companion',two:'+2 companions'}[wiz.party.mode])}${wiz.party.notes ? ' — ' + esc(wiz.party.notes) : ''}</div>
      ${C.backstory ? `<div class="rv-bs">${esc(C.backstory)}</div>` : ''}
      <h3>Campaign name <span class="hint">(optional)</span></h3><input id="rv-name" value="${esc(wiz.campaign_name||'')}" placeholder="The Tale of ${esc(C.name)}">
      <div class="hint">The DM writes a secret scenario from this, then the story begins. Needs the DM connected.</div></div></div>`;
  $('#rv-name').oninput = e => { wiz.campaign_name = e.target.value; saveDraft(); };
}
async function begin(){
  for (let p = 1; p < PAGES.length; p++) if (!valid(p, true)){ wiz.page = p; renderPage(); valid(p); return; }
  buildRecipes();
  wiz.style = curStyle();
  try { await busy('Creating your campaign…', () => post('/api/wizard/begin', {draft: wiz})); wiz = null; await CD.fetchState(); }
  catch(e){ err(e.message); }
}

// sync DM-driven wizard changes (theme built / failed)
const _refresh = refresh;
async function refreshSync(){ await _refresh(); if (wiz && M && M.draft){ const d = M.draft;
  if (d.theme_status && d.theme_status !== wiz.theme_status){ wiz.theme_status = d.theme_status; wiz.theme_note = d.theme_note;
    if (d.theme_status === 'ready' && d.theme){ wiz.theme = d.theme; if (wiz.page === 1) wiz.page = 2; } if (page === 'new') renderPage(); } } }
refresh = refreshSync;

window.Menu = { onState, openInGame, show, hide, refresh: () => refresh(), busy };
})();
