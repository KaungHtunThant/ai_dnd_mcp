/* Claude DnD - visual novel front end (read-only view of the active campaign). */
(() => {
const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let S = null, lastSeq = 0, tab = 'inv', lastDlgKey = '', typing = null, queue = [], busy = false, mapKey = '';
let abType = 'speak', dmUnread = 0, lastOocLen = -1;
const LS = { get(k, d){ try { const v = localStorage.getItem('cdnd.'+k); return v==null ? d : JSON.parse(v); } catch(e){ return d; } },
             set(k, v){ try { localStorage.setItem('cdnd.'+k, JSON.stringify(v)); } catch(e){} } };
let voiceOn = false, volume = 0.9, sfxOn = true, textSpeed = 'normal';

// ---------- rendering urls ----------
function norm(r){ if(!r) return null; if(Array.isArray(r)) return {layers:r}; if(typeof r==='string') return {layers:[r]}; return r; }
function stable(o){ if(Array.isArray(o)) return '['+o.map(stable).join(',')+']'; if(o && typeof o==='object') return '{'+Object.keys(o).sort().map(k=>JSON.stringify(k)+':'+stable(o[k])).join(',')+'}'; return JSON.stringify(o); }
function rurl(recipe, expr, theme){ const r = norm(recipe); if(!r || !(r.layers||[]).length) return null;
  const th = theme || S?.campaign?.theme || '_'; return `/r/${th}.svg?r=${encodeURIComponent(stable(r))}` + (expr?`&e=${encodeURIComponent(expr)}`:''); }
function purl(ref, colors, theme){ if(!ref) return null; const th = theme || S?.campaign?.theme || '_';
  return `/part/${th}/${encodeURIComponent(ref)}.svg` + (colors?`?c=${encodeURIComponent(stable(colors))}`:''); }
function img(src, cls){ const i = el('img', cls); if(src) i.src = src; i.alt=''; return i; }
const term = (k, d) => (S?.theme?.terms||{})[k] || d;

// ---------- data ----------
async function fetchState(){ const r = await fetch('/api/state'); S = await r.json(); syncSettings(); render(); }
function syncSettings(){ const c = S?.control || {}; voiceOn = !!c.voice; volume = c.volume ?? .9; sfxOn = c.sfx !== false; textSpeed = c.text_speed || 'normal'; }
async function fetchEvents(run = true){ const r = await fetch('/api/events?since='+lastSeq); const d = await r.json();
  if (lastSeq === 0) { lastSeq = d.seq; return; }
  for (const e of d.events){ if (e.seq > lastSeq){ lastSeq = e.seq; queue.push(e); } } if (run) pump(); }
const DLG_EVENTS = new Set(['narrate','say','action','previously']);
const dialoguePending = () => busyDlg || queue.some(e => DLG_EVENTS.has(e.type));
let busyDlg = false;
function connect(){
  const es = new EventSource('/api/stream');
  es.onopen = () => $('#conn').classList.add('on');
  es.onerror = () => $('#conn').classList.remove('on');
  let t = null;
  es.onmessage = () => { clearTimeout(t); t = setTimeout(async () => { await fetchEvents(false); await fetchState(); pump(); }, 60); };
}

// ---------- theme ----------
const FONTS = {pixel:"'Pixelify Sans', monospace", serif:"'Cormorant Garamond', Georgia, serif", mono:"'VT323', monospace", sans:"'Inter', system-ui, sans-serif"};
function applyTheme(){
  const u = S?.theme?.ui || {}; const r = document.documentElement.style;
  for (const [k,v] of Object.entries({accent:'--accent',bg:'--bg',panel:'--panel',text:'--text',panel2:'--panel2',line:'--line',muted:'--muted'})) if (u[k]) r.setProperty(v,u[k]);
  r.setProperty('--font-body', FONTS[u.font] || FONTS.pixel);
  r.setProperty('--font-title', FONTS[u.title_font || u.font] || FONTS.pixel);
}

// ---------- main render ----------
function render(){
  const c = S?.campaign;
  if (window.Menu) Menu.onState(S);
  if (!c) return;
  applyTheme();
  document.title = c.name + ' - Claude DnD';
  $('#camp-name').textContent = c.name;
  const w = c.world || {};
  $('#loc').innerHTML = w.location ? `<img src="${purl('tpl:ic_pin')}">${esc(w.location)}` : '';
  const tIcon = /night|midnight|dusk|evening/i.test(w.time||'') ? 'tpl:ic_moon' : 'tpl:ic_sun';
  $('#clock').innerHTML = (w.time||w.weather) ? `<img src="${purl(tIcon)}">${esc([w.time,w.weather].filter(Boolean).join(' · '))}` : '';
  $('#turn').textContent = c.status==='setup' ? 'Setup' : `Turn ${c.turn}`;
  renderPC(); renderParty(); renderStage(); if (!dialoguePending()) renderDialogue(); renderTabs(); renderShowcase(); renderCombat();
  renderControls(); renderActionBar();
}

function resBars(actor, compact){
  const out = el('div','bars'); const defs = S.theme?.resources || [];
  const res = actor.resources || {};
  const keys = defs.length ? defs : Object.keys(res).map(k=>({key:k,name:k}));
  for (const d of keys){ const r = res[d.key]; if(!r) continue;
    const pct = r.max ? Math.max(0, Math.min(100, 100*r.cur/r.max)) : 0;
    const b = el('div','bar', `<div class="lb"><span>${d.icon&&!compact?`<img src="${purl(d.icon)}">`:''}${esc(d.name)}</span><span>${r.cur}/${r.max}</span></div><div class="tr"><i style="width:${pct}%;background:${d.color||'var(--bad)'}"></i></div>`);
    out.append(b); }
  return out;
}
const mod = v => { const m = Math.floor((v-10)/2); return (m>=0?'+':'')+m; };
function conds(list){ const box = el('div','conds'); const map = S.theme?.conditions || {};
  for (const c of list||[]){ const d = el('div','cond', `${map[c]?`<img src="${purl(map[c])}">`:''}${esc(c)}`); box.append(d); } return box; }

function renderPC(){
  const c = S.campaign, ch = c.character || {}, pc = $('#pc'); pc.innerHTML='';
  const head = el('div','pc-head');
  head.append(img(rurl(ch.portrait, 'neutral')), el('div','', `<div class="pc-name">${esc(ch.name||'???')}</div><div class="pc-sub">${esc(ch.archetype||'')}${ch.level?` · Lv ${ch.level}`:''}${ch.pronouns?` · ${esc(ch.pronouns)}`:''}</div>`));
  pc.append(head, resBars(ch));
  if (ch.xp != null) pc.append(el('div','muted', `XP ${ch.xp}`));
  const cur = S.theme?.currency; if (cur) pc.append(el('div','money', `<img src="${purl(cur.icon||'tpl:ic_coin')}">${ch.currency||0} ${esc(cur.name||'')}`));
  const stats = el('div','stats');
  for (const s of S.theme?.stats || []){ const v = (ch.stats||{})[s.key]; if (v==null) continue;
    stats.append(el('div','st', `<div class="a">${esc(s.abbr||s.key)}</div><div class="v">${v}</div><div class="m">${mod(v)}</div>`)); }
  if (stats.children.length) pc.append(stats);
  if ((ch.conditions||[]).length) pc.append(conds(ch.conditions));
  if ((ch.abilities||[]).length){ pc.append(el('div','sect','Abilities'));
    for (const a of ch.abilities){ const t = typeof a==='string'?{name:a}:a; const d = el('div','muted', `• ${esc(t.name)}${t.uses!=null?` (${t.uses})`:''}`); tip(d, t.name, t.desc); pc.append(d); } }
}
function renderParty(){
  const p = $('#party'); p.innerHTML=''; const party = S.campaign.party || [];
  if (party.length){ p.append(el('div','sect', term('party','Party')));
    for (const m of party){ const d = el('div','comp'); d.append(img(rurl(m.portrait, m.expression||'neutral')));
      const info = el('div',''); info.style.flex='1'; info.append(el('div','n', esc(m.name)), resBars(m, true));
      if ((m.conditions||[]).length) info.append(conds(m.conditions)); d.append(info); p.append(d); } }
  const lg = S.campaign.legacy || [];
  if (lg.length){ p.append(el('div','sect','Legacy')); lg.forEach(x => p.append(el('div','legacy','✦ '+esc(x)))); }
  const runs = S.campaign.runs || [];
  if (runs.length > 1){ p.append(el('div','sect','Fallen')); runs.filter(r=>r.ended).forEach(r => p.append(el('div','legacy', `☠ ${esc(r.character)} — ${esc(r.cause||'')}`))); }
}

// ---------- stage ----------
const MOOD = {warm:'rgba(255,140,40,.12)', cold:'rgba(60,120,255,.14)', eerie:'rgba(90,255,160,.10)', danger:'rgba(255,30,30,.16)', calm:'rgba(120,200,255,.06)', dark:'rgba(0,0,0,.45)'};
const TIME = {night:'rgba(20,30,90,.35)', midnight:'rgba(10,15,60,.45)', dusk:'rgba(255,100,60,.18)', evening:'rgba(120,60,140,.2)', dawn:'rgba(255,160,180,.14)'};
function renderStage(){
  const c = S.campaign, s = c.scene || {}, mode = c.status==='setup' ? 'setup' : (s.mode||'scene');
  $('#scene-layer').classList.toggle('hidden', mode!=='scene' && mode!=='title');
  $('#map-layer').classList.toggle('hidden', mode!=='map');
  $('#setup-layer').classList.toggle('hidden', mode!=='setup');
  $('#stage-title').textContent = mode==='setup' ? '' : (s.title||'');
  const w = c.world||{};
  $('#tint').style.background = [MOOD[s.mood], TIME[(w.time||'').toLowerCase()]].filter(Boolean).map(x=>`linear-gradient(${x},${x})`).join(',') || 'none';
  $('#weather').className = ({rain:'rain',storm:'storm',snow:'snow',fog:'fog',mist:'fog',blizzard:'snow'})[(w.weather||'').toLowerCase()] || '';
  if (mode==='setup') return renderSetup();
  if (mode==='map') return renderMap();
  renderScene();
}

function renderScene(){
  const L = $('#scene-layer'), s = S.campaign.scene;
  const bd = s.backdrop || S.map?.backdrop || {layers:['tpl:bd_void']};
  let b = L.querySelector('.backdrop'); const src = rurl(bd);
  if (!b){ b = img(src,'backdrop'); L.append(b); } else if (b.getAttribute('src') !== src) b.src = src;
  const keep = new Set();
  const speaking = s.dialogue?.speaker_id;
  for (const e of s.entities||[]){ if (e.hidden) continue; keep.add(e.id);
    let a = L.querySelector(`.actor[data-id="${CSS.escape(e.id)}"]`);
    if (!a){ a = el('div','actor'); a.dataset.id = e.id; a.append(el('div','nm'), el('div','hpbar', '<i></i>'), img(null,'spr')); a.style.opacity=0; L.append(a); requestAnimationFrame(()=>a.style.opacity=1); }
    a.className = `actor ${e.side||''} ${speaking===e.id?'speaking':''}`;
    a.style.left = (e.slot ?? 50) + '%';
    a.querySelector('.nm').textContent = e.name || '';
    const hb = a.querySelector('.hpbar'); hb.style.display = e.hp ? '' : 'none';
    if (e.hp) hb.firstChild.style.width = Math.max(0, 100*e.hp.cur/e.hp.max)+'%';
    const spr = a.querySelector('img.spr'); const u = rurl({...norm(e.sprite)||{layers:[]}, flip: !!e.flip});
    if (spr.getAttribute('src') !== u) spr.src = u;
    a.style.height = `${40*(e.scale||1)}%`;
  }
  L.querySelectorAll('.actor').forEach(a => { if (!keep.has(a.dataset.id)) { a.style.opacity=0; setTimeout(()=>a.remove(),500); } });
}

function renderMap(){
  const L = $('#map-layer'), m = S.map, c = S.campaign; if (!m){ L.innerHTML='<div class="muted">No map</div>'; return; }
  const key = c.theme+'/'+m.id+'/'+m.mtime;
  let wrap = $('#map-wrap');
  if (!wrap || mapKey !== key){ L.innerHTML=''; wrap = el('div'); wrap.id='map-wrap'; L.append(wrap);
    wrap.append(img(`/map/${c.theme}/${m.id}.svg?v=${m.mtime}`,'mapimg'), el('canvas'), el('div','overlay')); mapKey = key; }
  // size to fit
  const st = $('#stage').getBoundingClientRect(); const scale = Math.max(1, Math.floor(Math.min(st.width/(m.w*16), (st.height-8)/(m.h*16))*4)/4);
  const W = m.w*16*scale, H = m.h*16*scale; wrap.style.width=W+'px'; wrap.style.height=H+'px';
  const tile = 16*scale;
  // fog
  const cv = wrap.querySelector('canvas'); cv.width = m.w; cv.height = m.h; const g = cv.getContext('2d');
  const ms = (c.world.maps||{})[m.id] || {}; const ex = new Set((ms.explored||[]).map(p=>p[0]+','+p[1]));
  g.clearRect(0,0,m.w,m.h);
  for (let y=0;y<m.h;y++) for (let x=0;x<m.w;x++){ if (ex.has(x+','+y)) continue;
    let near = false; for (const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]) if (ex.has((x+dx)+','+(y+dy))) near = true;
    g.fillStyle = near ? 'rgba(7,6,10,.72)' : 'rgba(7,6,10,.97)'; g.fillRect(x,y,1,1); }
  cv.style.imageRendering = 'auto';
  // tokens
  const ov = wrap.querySelector('.overlay'); ov.innerHTML='';
  const place = (node, x, y) => { node.style.left = ((x+.5)*tile)+'px'; node.style.top = ((y+1)*tile)+'px'; ov.append(node); };
  for (const mk of ms.markers||[]){ const d = el('div','mk'); d.append(img(purl(mk.icon||'tpl:ic_pin'))); d.firstChild.style.width = tile*.8+'px';
    if (mk.label) d.append(el('span','',esc(mk.label))); d.style.left=((mk.x+.5)*tile)+'px'; d.style.top=((mk.y+.5)*tile)+'px'; ov.append(d); }
  for (const e of c.scene.entities||[]){ if (e.hidden || e.x==null) continue; if (!ex.has(e.x+','+e.y)) continue;
    const t = el('div','tok'); t.dataset.id = e.id; const i = img(rurl({...norm(e.sprite)||{layers:[]}, flip: !!e.flip})); i.style.height = (tile*1.35*(e.scale||1))+'px'; t.append(i); place(t, e.x, e.y); }
  if (c.world.pos){ const t = el('div','tok player'); t.dataset.id = 'player'; const i = img(rurl(c.character.sprite)); i.style.height = (tile*1.4)+'px'; t.append(i); place(t, c.world.pos[0], c.world.pos[1]); }
}

function renderSetup(){
  const L = $('#setup-layer'), ch = S.campaign.character || {}; L.innerHTML='';
  L.append(el('div','setup-title', 'Character Creation'));
  const fig = el('div','setup-fig');
  const sp = rurl(ch.sprite), pt = rurl(ch.portrait, 'neutral');
  if (pt) fig.append(img(pt,'pt'));
  if (sp) fig.append(img(sp,'sp'));
  if (!sp && !pt) fig.append(el('div','empty-fig','?'));
  const card = el('div','setup-card');
  card.innerHTML = `<h2>${esc(ch.name||'Unnamed')}</h2><div class="sub">${esc([ch.pronouns, ch.archetype].filter(Boolean).join(' · ')||'Awaiting details...')}</div>`;
  const stats = el('div','stats');
  for (const s of S.theme?.stats || []){ const v = (ch.stats||{})[s.key];
    stats.append(el('div','st', `<div class="a">${esc(s.abbr||s.key)}</div><div class="v">${v??'–'}</div><div class="m">${v!=null?mod(v):''}</div>`)); }
  card.append(stats);
  if (ch.backstory) card.append(el('div','bs', esc(ch.backstory)));
  const hk = (ch.hooks||[]).filter(h => h && String(h).trim()); if (hk.length) card.append(el('div','bs', hk.map(h=>'✦ '+esc(h)).join('<br>')));
  if (S.theme) card.append(el('div','muted', `Theme: ${esc(S.theme.name)}`));
  L.append(fig, card);
}

function renderCombat(){
  const cb = S.campaign.combat || {}, bar = $('#combat-bar'); bar.innerHTML='';
  if (!cb.active) return; bar.append(el('div','rnd', `Round ${cb.round}`));
  cb.order.forEach((o,i) => bar.append(el('div','ini'+(i===cb.turn_index?' cur':''), `${esc(o.name)} <span class="muted">${o.init}</span>`)));
}

// ---------- dialogue (paged, voiced) ----------
function pagesOf(t){
  t = String(t||''); if (t.length <= 300) return [t];
  const parts = t.match(/[^.!?…]+[.!?…]+["')\]]*\s*|[^.!?…]+$/g) || [t]; const out = []; let cur = '';
  for (const p of parts){ if ((cur + p).length > 300 && cur){ out.push(cur.trim()); cur = ''; } cur += p; }
  if (cur.trim()) out.push(cur.trim()); return out;
}
function dlgKey(d){ return d ? (d.speaker||'')+'|'+d.text+'|'+(d.expression||'') : ''; }
function setDlgFrame(d){
  const box = $('#dialogue');
  box.className = 'panel ' + (d ? (d.player ? 'speech player' : d.act ? 'act' : d.speaker ? 'speech' : 'narration '+(d.style||'')) : '');
  const nm = $('#dlg-name'); nm.textContent = d?.speaker || '';
  if (d?.player && (d.manner && d.manner!=='normal' || d.target)) nm.append(el('span','mn', `(${esc(d.manner||'normal')}${d.target?' → '+esc(d.target):''})`));
  const p = $('#dlg-portrait'); p.innerHTML='';
  if (d?.portrait && norm(d.portrait).layers?.length) p.append(img(rurl(d.portrait, d.expression||'neutral')));
}
function renderDialogue(){
  const d = S.campaign.scene?.dialogue; const key = dlgKey(d);
  if (key === lastDlgKey) return; lastDlgKey = key; setDlgFrame(d);
  const pg = pagesOf(d?.text || ''); typeText(pg[pg.length-1]);
}
function typeText(t, instant){
  const box = $('#dlg-text'); clearInterval(typing); box.textContent='';
  if (instant){ box.textContent = t; return Promise.resolve(); }
  if (textSpeed === 'instant'){ box.textContent = t; return Promise.resolve(); }
  let i = 0; const speed = ({slow:1, normal:2, fast:4})[textSpeed] * (t.length > 240 ? 1.5 : 1) || 2;
  return new Promise(res => { typing = setInterval(() => { i += speed; box.textContent = t.slice(0,i); box.scrollTop = box.scrollHeight;
    if (i >= t.length){ clearInterval(typing); typing = null; res(); } }, 22); box._finish = () => { clearInterval(typing); box.textContent = t; res(); }; });
}
let advance = null;   // resolves "click to continue"
function waitClick(){ $('#dlg-more').classList.remove('hidden'); return new Promise(r => { advance = () => { advance = null; $('#dlg-more').classList.add('hidden'); r(); }; }); }
function onDialogueClick(){ const b = $('#dlg-text'); if (typing && b._finish) { b._finish(); } if (advance) advance(); if (curAudio && curAudio._skip) curAudio._skip(); }

// voice engine
let actx = null, curAudio = null;
function ensureCtx(){ if (!actx){ try { actx = new (window.AudioContext||window.webkitAudioContext)(); } catch(e){} } if (actx && actx.state==='suspended') actx.resume(); }
function fxChain(audio, fx){
  if (!actx || !fx) return;
  try {
    const src = actx.createMediaElementSource(audio); let node = src; const out = actx.destination;
    if (fx === 'radio'){ const hp = actx.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=500; const lp = actx.createBiquadFilter(); lp.type='lowpass'; lp.frequency.value=2800;
      const ws = actx.createWaveShaper(); const k = new Float32Array(256).map((_,i)=>{ const x=i/128-1; return Math.tanh(2.5*x); }); ws.curve = k; node.connect(hp); hp.connect(lp); lp.connect(ws); ws.connect(out); }
    else if (fx === 'robot'){ const ring = actx.createGain(); ring.gain.value = 0; const osc = actx.createOscillator(); osc.frequency.value = 55; osc.connect(ring.gain); osc.start();
      const dry = actx.createGain(); dry.gain.value = .35; node.connect(ring); node.connect(dry); ring.connect(out); dry.connect(out); audio.addEventListener('ended', ()=>osc.stop()); }
    else if (fx === 'echo'){ const d = actx.createDelay(); d.delayTime.value = .19; const fb = actx.createGain(); fb.gain.value = .33; node.connect(out); node.connect(d); d.connect(fb); fb.connect(d); d.connect(out); }
    else node.connect(out);
  } catch(e){ console.warn(e); }
}
function speak(text, v){
  return new Promise(res => {
    if (!voiceOn || !v || !text){ return res(false); }
    const u = `/tts?v=${encodeURIComponent(v.voice)}&r=${encodeURIComponent(v.rate||'+0%')}&p=${encodeURIComponent(v.pitch||'+0Hz')}&t=${encodeURIComponent(text)}`;
    const a = new Audio(); a.crossOrigin = 'anonymous'; a.src = u; a.volume = volume; curAudio = a;
    if (v.fx === 'deep'){ a.preservesPitch = false; a.playbackRate = 0.86; } else fxChain(a, v.fx);
    let done = false; const fin = ok => { if (done) return; done = true; curAudio = null; res(ok); };
    a._skip = () => { a.pause(); fin(true); };
    a.onended = () => fin(true);
    a.onerror = () => { // fallback: browser voice
      try { const s = new SpeechSynthesisUtterance(text); s.volume = volume; s.onend = () => fin(true); s.onerror = () => fin(false); speechSynthesis.speak(s); a._skip = () => { speechSynthesis.cancel(); fin(true); }; } catch(e){ fin(false); } };
    a.play().catch(() => fin(false));
  });
}
async function showLine(d){
  busyDlg = true; lastDlgKey = dlgKey(d); setDlgFrame(d);
  const pages = pagesOf(d.text);
  if (voiceOn && d.voice){
    const p = speak(d.text, d.voice); let ended = false; p.then(()=>ended=true);
    const total = d.text.length || 1; let shown = 0;
    for (let i=0;i<pages.length;i++){
      await typeText(pages[i]); shown += pages[i].length;
      if (i < pages.length-1){ // wait until audio reaches this page's end (or click)
        await new Promise(r => { const iv = setInterval(()=>{ const a = curAudio;
          if (ended || !a || (a.duration && a.currentTime/a.duration >= shown/total)) { clearInterval(iv); r(); } }, 150); advance = () => { advance=null; clearInterval(iv); r(); }; });
      }
    }
    await p; await sleep(250);
  } else {
    for (let i=0;i<pages.length;i++){ await typeText(pages[i]); if (i < pages.length-1) await waitClick(); }
    await sleep(Math.min(1800, 300 + d.text.length*8));
  }
  busyDlg = false;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------- tabs ----------
function renderTabs(){
  const tabs = [['inv', term('inventory','Items')], ['quests', term('quests','Quests')], ['journal', term('journal','Journal')], ['log', term('log','Story')], ['dm','DM']];
  const ooc = S.campaign.ooc || [];
  if (lastOocLen >= 0 && ooc.length > lastOocLen && tab !== 'dm') dmUnread += ooc.slice(lastOocLen).filter(o=>o.from==='dm').length;
  lastOocLen = ooc.length; if (tab === 'dm') dmUnread = 0;
  const nav = $('#tabs'); nav.innerHTML='';
  for (const [k,label] of tabs){ const b = el('button', tab===k?'on':'', esc(label) + (k==='dm' && dmUnread ? `<span class="badge">${dmUnread}</span>` : ''));
    b.onclick = () => { tab = k; if (k==='dm') dmUnread = 0; renderTabs(); }; nav.append(b); }
  const body = $('#tab-body'); body.innerHTML=''; const c = S.campaign, ch = c.character||{};
  if (tab==='inv'){
    const inv = ch.inventory||[]; if (!inv.length) body.append(el('div','muted','Empty.'));
    const g = el('div','inv');
    for (const it of inv){ const d = el('div','it'+(it.equipped?' eq':'')); d.append(img(purl(it.icon||'tpl:item_bag', it.colors))); if ((it.qty||1)>1) d.append(el('span','q','×'+it.qty));
      tip(d, it.name + (it.equipped?' (equipped)':''), it.desc); g.append(d); }
    body.append(g);
    const eq = ch.equipment||{}; if (Object.keys(eq).length){ body.append(el('div','sect','Equipped')); for (const [k,v] of Object.entries(eq)) body.append(el('div','muted', `${esc(k)}: ${esc(typeof v==='string'?v:v.name)}`)); }
  } else if (tab==='quests'){
    const qs = (c.quests||[]).filter(q=>q.status!=='hidden'); if (!qs.length) body.append(el('div','muted','No quests yet.'));
    qs.sort((a,b)=>(a.status==='active'?0:1)-(b.status==='active'?0:1));
    for (const q of qs){ const d = el('div','q-item '+q.status, `<div class="qt">${q.status==='done'?'✓ ':q.status==='failed'?'✗ ':'◆ '}${esc(q.title)}</div>${q.desc?`<div class="qd">${esc(q.desc)}</div>`:''}`);
      if ((q.objectives||[]).length){ const ul = el('ul'); q.objectives.forEach(o => ul.append(el('li', o.done?'d':'', (o.done?'☑ ':'☐ ')+esc(o.text)))); d.append(ul); } body.append(d); }
  } else if (tab==='journal'){
    const js = (c.journal||[]).slice().reverse(); if (!js.length) body.append(el('div','muted','Nothing written yet.'));
    for (const j of js) body.append(el('div','jr', `${j.title?`<b>${esc(j.title)}</b>`:''}${esc(j.text)}`));
  } else if (tab==='dm'){
    body.append(el('div','muted','Out-of-character chat with the DM. Nothing here changes the story.'));
    for (const o of ooc) body.append(el('div','ooc '+o.from, `<b>${o.from==='dm'?'DM':'You'}</b>${esc(o.text)}`));
    const pend = (S.pending||[]).filter(a=>a.type==='dm'); for (const a of pend) body.append(el('div','ooc player', `<b>You · waiting</b>${esc(a.text)}`));
    body.scrollTop = body.scrollHeight;
  } else {
    const lg = (c.log||[]).slice(-120).reverse();
    for (const l of lg){ let h = esc(l.text); if (l.kind==='speech') h = `<b>${esc(l.speaker)}:</b> ${h}`; body.append(el('div','lg '+l.kind, h)); }
  }
}
function tip(node, title, desc){
  node.onmouseenter = e => { const t = $('#tooltip'); t.innerHTML = `<b>${esc(title||'')}</b>${desc?'<br>'+esc(desc):''}`; t.classList.remove('hidden'); };
  node.onmousemove = e => { const t = $('#tooltip'); t.style.left = (e.clientX+14)+'px'; t.style.top = (e.clientY+10)+'px'; };
  node.onmouseleave = () => $('#tooltip').classList.add('hidden');
}

// ---------- showcase ----------
function renderShowcase(){
  const sc = S.campaign.scene?.showcase, box = $('#showcase');
  if (!sc || !(sc.items||[]).length){ box.classList.add('hidden'); return; }
  box.classList.remove('hidden'); box.innerHTML = `<h3>${esc(sc.title||'Choose')}</h3>`;
  const g = el('div','sc-grid'); g.style.gridTemplateColumns = `repeat(${sc.columns||4}, 1fr)`;
  for (const it of sc.items){ const d = el('div','sc-item');
    if (it.sprite) d.append(img(rurl(it.sprite)));
    if (it.portrait) d.append(img(rurl(it.portrait, it.expression||'neutral')));
    if (it.part) { const i = img(purl(it.part, it.colors), 'icon'); d.append(i); }
    d.append(el('div','lbl', esc(it.label||'')));
    if (it.text) d.append(el('div','txt', esc(it.text)));
    g.append(d); }
  box.append(g);
}

// ---------- events (animations) ----------
function pump(){ if (busy || !queue.length) return; const e = queue.shift(); busy = true;
  const done = () => { busy = false; pump(); };
  try { handle(e, done); } catch(err){ console.error(err); done(); } }
function handle(e, done){
  const d = e.data || {};
  switch (e.type){
    case 'roll': return showRoll(d, done);
    case 'effect': return effect(d, done);
    case 'title': titleCard(d.text, d.sub); return setTimeout(done, 1500);
    case 'toast': toast(d.text, d.icon); return done();
    case 'reload': lastDlgKey=''; return fetchState().then(done);
    case 'narrate': return showLine({text:d.text, style:d.style, voice:d.voice}).then(done);
    case 'say': return showLine(d).then(done);
    case 'action': {
      const ch = S?.campaign?.character || {};
      if (d.type === 'speak') return showLine({speaker: ch.name||'You', portrait: ch.portrait, text: d.text, expression: 'neutral', player: true, manner: d.manner, target: d.target}).then(done);
      if (d.type === 'do') return showLine({text: '\u25b6 ' + d.text, style: 'act', act: true}).then(done);
      return done(); }
    case 'dm_reply': toast('DM replied (DM tab)', 'tpl:ic_scroll'); return done();
    case 'previously': return showPrevious(d).then(done);
    default: return done();
  }
}
function toast(text, icon){ const t = el('div','toast'); if (icon) t.append(img(purl(icon))); t.append(el('span','',esc(text))); $('#toasts').append(t); setTimeout(()=>t.remove(), 4200); }
function titleCard(text, sub){ const t = $('#titlecard'); t.innerHTML = `<div class="t">${esc(text)}</div>${sub?`<div class="s">${esc(sub)}</div>`:''}`; t.classList.remove('hidden'); t.style.animation='none'; t.offsetHeight; t.style.animation=''; clearTimeout(t._h); t._h = setTimeout(()=>t.classList.add('hidden'), 2000); }
function targetPos(target){
  const st = $('#stage').getBoundingClientRect();
  const a = target && document.querySelector(`.actor[data-id="${CSS.escape(target)}"] img.spr, .tok[data-id="${CSS.escape(target)}"]`);
  if (a){ const r = a.getBoundingClientRect(); return [r.left - st.left + r.width/2, r.top - st.top + r.height*0.25, a]; }
  return [st.width/2, st.height*0.45, null];
}
function floater(text, color, target){ const [x,y,node] = targetPos(target); const f = el('div','floater', esc(text)); f.style.left=x+'px'; f.style.top=y+'px'; f.style.color = color||'#fff'; $('#floaters').append(f); setTimeout(()=>f.remove(), 1700);
  if ((!target || target==='player') && /damage/.test(color||'')) {} return node; }
function effect(d, done){
  const stage = $('#stage');
  switch (d.kind){
    case 'shake': stage.classList.remove('shake'); stage.offsetHeight; stage.classList.add('shake'); break;
    case 'flash': stage.classList.remove('flash'); stage.offsetHeight; stage.classList.add('flash'); setTimeout(()=>stage.classList.remove('flash'), 600); break;
    case 'damage': { const n = floater(d.text, '#ff5a4a', d.target); if (n){ n.classList.remove('hurt'); n.offsetHeight; n.classList.add('hurt'); }
      if (!d.target || d.target==='player'){ const p = $('#pc'); p.classList.remove('hurt'); p.offsetHeight; p.classList.add('hurt'); } break; }
    case 'heal': floater(d.text, '#6ad08a', d.target); break;
    case 'float': floater(d.text, d.color || '#fff', d.target); break;
    case 'levelup': titleCard(d.text || 'Level Up!', d.sub); break;
    case 'title': titleCard(d.text, d.sub); break;
    case 'toast': toast(d.text, d.icon); break;
    case 'fade': stage.animate([{opacity:1},{opacity:0},{opacity:1}], {duration:1400}); break;
  }
  setTimeout(done, (d.kind==='title'||d.kind==='levelup') ? 1600 : 150);
}
function showRoll(r, done){
  const ui = S?.theme?.ui || {}; const ds = ui.dice || {};
  Dice.show(r, {style: {color: ds.color, ink: ds.ink, edge: ds.edge, style: ds.style, font: ds.font}, volume: sfxOn ? volume : 0,
    playerName: S?.campaign?.character?.name}).then(done);
}

async function showPrevious(d){
  const card = $('#prevcard'); card.innerHTML = `<h3>Previously…</h3><p>${esc(d.text)}</p><div class="x">click to continue</div>`; card.classList.remove('hidden');
  let closed; const click = new Promise(r => closed = r); card.onclick = () => { if (curAudio && curAudio._skip) curAudio._skip(); closed(); };
  const said = speak(d.text, d.voice); await Promise.race([click, said.then(()=>sleep(voiceOn?1500:600000))]); card.classList.add('hidden');
}

// ---------- controls ----------
async function saveSettings(ch){ try { await post('/api/settings', ch); } catch(e){ toast(e.message); } }
async function post(path, body){
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({...body, token: S?.token})});
  let d = {}; try { d = await r.json(); } catch(e){} if (!r.ok) throw new Error(d.error || r.statusText); return d;
}
function renderControls(){
  const ctl = S.control || {mode:'live', paused:false}, dm = S.dm || {status:'idle'};
  const bm = $('#btn-mode'); bm.textContent = ctl.mode === 'live' ? 'Live' : 'Nudge'; bm.classList.toggle('on', ctl.mode==='live');
  const bp = $('#btn-pause'); bp.textContent = ctl.paused ? 'Resume DM' : 'Pause DM'; bp.classList.toggle('on', ctl.paused);
  const bv = $('#btn-voice'); bv.textContent = voiceOn ? 'Voice: on' : 'Voice: off'; bv.classList.toggle('on', voiceOn);
  $('#vol').value = volume;
  const st = $('#dmstat'); const age = Date.now()/1000 - (dm.t||0);
  let cls = 'idle', txt = 'DM idle';
  if (ctl.paused) { txt = 'DM paused'; }
  else if (dm.status === 'listening' && age < 330) { cls = 'listening'; txt = '<span class="pulse"></span> DM listening'; }
  else if (dm.status === 'thinking' && age < 600) { cls = 'thinking'; txt = '<span class="pulse"></span> DM thinking…'; }
  else if (ctl.mode === 'nudge' || dm.status === 'idle') { txt = "DM idle · type 'go' in chat"; }
  st.className = 'chip ' + cls; st.innerHTML = txt;
}
function initControls(){
  $('#btn-mode').onclick = () => post('/api/control', {mode: (S.control?.mode==='live') ? 'nudge' : 'live'}).then(fetchState).catch(e=>toast(e.message));
  $('#btn-pause').onclick = () => post('/api/control', {paused: !S.control?.paused}).then(fetchState).catch(e=>toast(e.message));
  $('#btn-voice').onclick = () => { voiceOn = !voiceOn; ensureCtx(); if (!voiceOn && curAudio && curAudio._skip) curAudio._skip(); renderControls(); saveSettings({voice: voiceOn}); };
  let vt = null; $('#vol').oninput = e => { volume = parseFloat(e.target.value); if (curAudio) curAudio.volume = volume; clearTimeout(vt); vt = setTimeout(() => saveSettings({volume}), 300); };
  $('#btn-menu').onclick = () => window.Menu && Menu.openInGame();
  $('#dialogue').onclick = onDialogueClick;
  document.addEventListener('keydown', e => {
    const typingIn = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||'');
    if (e.altKey && ['1','2','3'].includes(e.key)) { setAbType(['speak','do','dm'][+e.key-1]); e.preventDefault(); return; }
    if (!typingIn && (e.key===' ' || e.key==='Enter') && (advance || typing || curAudio)) { onDialogueClick(); e.preventDefault(); return; }
    if (!typingIn && ['1','2','3'].includes(e.key)) { setAbType(['speak','do','dm'][+e.key-1]); $('#ab-text').focus(); e.preventDefault(); }
  });
}

// ---------- action bar ----------
const PH = {speak:'What do you say?', do:'What do you do?', dm:'Ask the DM anything (out of character - no effect on the story)'};
function setAbType(t){ abType = t; document.querySelectorAll('.ab-tabs button').forEach(b => b.classList.toggle('on', b.dataset.t===t));
  $('#ab-speak-opts').classList.toggle('hidden', t!=='speak'); $('#actionbar').className = 'panel mode-'+t; $('#ab-text').placeholder = PH[t]; renderActionBar(); }
function initActionBar(){
  document.querySelectorAll('.ab-tabs button').forEach(b => b.onclick = () => { setAbType(b.dataset.t); $('#ab-text').focus(); });
  const m = $('#ab-manner'); m.onchange = () => { $('#ab-manner-custom').classList.toggle('hidden', m.value!=='__custom'); if (m.value==='__custom') $('#ab-manner-custom').focus(); };
  $('#ab-send').onclick = send;
  $('#ab-text').addEventListener('keydown', e => { if (e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } });
  setAbType('speak');
}
function abStatus(txt, err){ const s = $('#ab-status'); s.textContent = txt||''; s.className = err ? 'err' : ''; }
async function send(){
  const text = $('#ab-text').value.trim(); if (!text) return;
  const body = {type: abType, text};
  if (abType==='speak'){ const m = $('#ab-manner').value; body.manner = m==='__custom' ? ($('#ab-manner-custom').value.trim()||'normal') : m; body.target = $('#ab-target').value.trim(); }
  $('#ab-send').disabled = true;
  try { await post('/api/action', body); $('#ab-text').value=''; if (abType==='speak'){ $('#ab-manner').value='normal'; $('#ab-manner-custom').classList.add('hidden'); }
    abStatus(S.control?.mode==='nudge' ? "Queued - type 'go' in chat" : 'Sent'); await fetchState(); }
  catch(e){ abStatus(e.message, true); }
  finally { $('#ab-send').disabled = false; }
}
function renderActionBar(){
  if (!S?.campaign) return;
  const m = $('#ab-manner'); if (!m.options.length){ for (const x of (S.manners||['normal'])) m.append(new Option(x, x)); m.append(new Option('custom…','__custom')); m.value='normal'; }
  const names = new Set(); for (const e of S.campaign.scene?.entities||[]) if (e.name) names.add(e.name); for (const p of S.campaign.party||[]) if (p.name) names.add(p.name);
  const dl = $('#ab-targets'); const want = [...names].join('|'); if (dl.dataset.k !== want){ dl.innerHTML=''; names.forEach(n => dl.append(new Option(n))); dl.dataset.k = want; }
  const inp = S.dm?.input || {enabled:true}; const setup = S.campaign.status === 'setup';
  const lockStory = abType!=='dm' && (!inp.enabled || setup);
  $('#ab-text').disabled = lockStory; $('#ab-send').disabled = lockStory;
  if (lockStory) abStatus(setup ? 'The DM is preparing your story - use the DM tab for questions' : (inp.hint || 'Input locked by the DM'));
  else if ($('#ab-status').textContent.startsWith('The DM is preparing') || $('#ab-status').textContent === (inp.hint||'\u0000')) abStatus('');
  const box = $('#ab-pending'); box.innerHTML='';
  for (const a of S.pending||[]){ if (!['speak','do'].includes(a.type)) continue;
    const d = el('div','pend', `<span>${S.control?.mode==='nudge'?"Queued (type 'go' in chat)":'Waiting for DM'}: <b>${esc(a.type)}</b>${a.manner&&a.manner!=='normal'?' ('+esc(a.manner)+')':''}${a.target?' → '+esc(a.target):''} — ${esc(a.text.slice(0,90))}</span>`);
    const b = el('button','', 'cancel'); b.onclick = () => post('/api/action/cancel', {id: a.id}).then(() => { $('#ab-text').value = a.text; fetchState(); }).catch(e=>abStatus(e.message,true)); d.append(b); box.append(d); }
}

window.addEventListener('resize', () => { if (S?.campaign?.scene?.mode==='map') renderMap(); });
window.CD = { get S(){ return S; }, $, el, esc, img, rurl, purl, norm, post, toast, fetchState, saveSettings, tip, ensureCtx, speak,
  get voiceOn(){ return voiceOn; }, set voiceOn(v){ voiceOn = v; }, get volume(){ return volume; }, set volume(v){ volume = v; }, applyTheme, renderControls };
initControls(); initActionBar();
fetchState().then(()=>fetchEvents()).then(connect).catch(()=>setTimeout(()=>location.reload(), 3000));
setInterval(() => { if (S?.campaign) renderControls(); }, 5000);
})();
