/* Claude DnD - polyhedral dice renderer + roll animation.  window.Dice.show(roll, opts) -> Promise */
(() => {
let uid = 0;
const P = pts => pts.map(p => p.join(',')).join(' ');
const shadeFill = a => a >= 0 ? `fill="#fff" fill-opacity="${a}"` : `fill="#000" fill-opacity="${-a}"`;

// facets: [points, shade(+white/-black)] ; face = the numbered front face ; num = text anchor + size
function geom(sides){
  if (sides === 4) return { outline:[[50,5],[95,88],[5,88]], face:[[50,27],[78,78],[22,78]], num:[50,66,26],
    facets:[[[[50,5],[50,27],[22,78],[5,88]], .16], [[[50,5],[95,88],[78,78],[50,27]], -.22], [[[5,88],[22,78],[78,78],[95,88]], -.38]] };
  if (sides === 6) return { outline:[[10,10],[90,10],[90,90],[10,90]], face:[[22,22],[78,22],[78,78],[22,78]], num:[50,62,34], round:true,
    facets:[[[[10,10],[90,10],[78,22],[22,22]], .28], [[[10,10],[22,22],[22,78],[10,90]], .1], [[[90,10],[90,90],[78,78],[78,22]], -.24], [[[10,90],[22,78],[78,78],[90,90]], -.4]] };
  if (sides === 8) return { outline:[[50,4],[93,50],[50,96],[7,50]], face:[[50,20],[79,63],[21,63]], num:[50,54,24],
    facets:[[[[7,50],[50,4],[50,20],[21,63]], .22], [[[50,4],[93,50],[79,63],[50,20]], -.04], [[[7,50],[21,63],[50,96]], -.24], [[[21,63],[79,63],[50,96]], -.34], [[[79,63],[93,50],[50,96]], -.46]] };
  if (sides === 10 || sides === 100) return { outline:[[50,4],[94,44],[50,96],[6,44]], face:[[50,17],[74,47],[50,69],[26,47]], num:[50,53,sides===100?19:23],
    facets:[[[[6,44],[50,4],[50,17],[26,47]], .22], [[[50,4],[94,44],[74,47],[50,17]], -.05], [[[6,44],[26,47],[50,69],[50,96]], -.26], [[[74,47],[94,44],[50,96],[50,69]], -.42]] };
  if (sides === 12){ const o=[], i=[]; for (let k=0;k<5;k++){ const a=(-90+72*k)*Math.PI/180; o.push([50+46*Math.cos(a), 53+46*Math.sin(a)]); i.push([50+25*Math.cos(a), 53+25*Math.sin(a)]); }
    const sh=[.28,-.08,-.38,-.26,.14]; const f=[]; for (let k=0;k<5;k++){ const n=(k+1)%5; f.push([[o[k],o[n],i[n],i[k]], sh[k]]); }
    return { outline:o, face:i, num:[50,61,24], facets:f }; }
  if (sides === 20) return { outline:[[50,3],[92,27],[92,73],[50,97],[8,73],[8,27]], face:[[50,22],[77,67],[23,67]], num:[50,57,23],
    facets:[[[[8,27],[50,3],[50,22]], .26], [[[50,3],[92,27],[50,22]], .34], [[[8,27],[50,22],[23,67]], .12], [[[92,27],[77,67],[50,22]], -.02],
            [[[8,27],[23,67],[8,73]], -.14], [[[92,27],[92,73],[77,67]], -.3], [[[8,73],[23,67],[50,97]], -.26], [[[92,73],[50,97],[77,67]], -.42],
            [[[23,67],[77,67],[50,97]], -.34]] };
  return null; // coin
}

function svg(sides, value, o = {}){
  const id = 'dg' + (++uid); const g = geom(sides);
  const txt = value == null ? '' : String(value);
  const fsz = g ? g.num[2] * (txt.length > 2 ? .72 : txt.length > 1 ? .9 : 1) : 30;
  let body = '';
  const defs = `<defs><radialGradient id="${id}h" cx="32%" cy="24%" r="75%"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".45" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></radialGradient>
    <filter id="${id}s" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="5" stdDeviation="3.5" flood-color="#000" flood-opacity=".55"/></filter>
    ${o.glow ? `<filter id="${id}g" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>` : ''}</defs>`;
  if (!g){
    body = `<circle cx="50" cy="50" r="44" fill="var(--die)"/><circle cx="50" cy="50" r="44" fill="url(#${id}h)"/><circle cx="50" cy="50" r="34" fill="none" stroke="#000" stroke-opacity=".25" stroke-width="2"/>`;
    body += `<text x="50" y="61" text-anchor="middle" class="dnum" font-size="${fsz}">${txt}</text>`;
  } else {
    const rx = g.round ? ' stroke-linejoin="round"' : '';
    body += `<polygon points="${P(g.outline)}" fill="var(--die)"${rx}/>`;
    for (const [pts, a] of g.facets) body += `<polygon points="${P(pts)}" ${shadeFill(a)}/>`;
    body += `<polygon points="${P(g.face)}" fill="#fff" fill-opacity=".06"/>`;
    body += `<polygon points="${P(g.outline)}" fill="url(#${id}h)"/>`;
    // edges
    const edges = new Set(); for (const [pts] of g.facets) for (let k=0;k<pts.length;k++){ const a=pts[k], b=pts[(k+1)%pts.length]; edges.add(P([a,b])); }
    for (const e of edges){ const [a,b] = e.split(' '); body += `<line x1="${a.split(',')[0]}" y1="${a.split(',')[1]}" x2="${b.split(',')[0]}" y2="${b.split(',')[1]}" stroke="var(--die-edge)" stroke-width="1.1" stroke-opacity=".55"/>`; }
    body += `<polygon points="${P(g.outline)}" fill="none" stroke="var(--die-edge)" stroke-width="2.2"${rx}/>`;
    body += `<polyline points="${P(g.outline.slice(0, Math.ceil(g.outline.length/2)+ (sides===4?0:0)))}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.2"/>`;
    const [nx, ny] = g.num;
    body += `<text x="${nx}" y="${ny}" text-anchor="middle" class="dnum" font-size="${fsz}"${o.glow?` filter="url(#${id}g)"`:''}>${txt}</text>`;
    if ((sides === 6 || sides === 8 || sides === 10 || sides === 12 || sides === 20) && (txt === '6' || txt === '9')) body += `<rect x="${nx-7}" y="${ny+3}" width="14" height="2.4" fill="var(--die-ink)"/>`;
  }
  return `<svg viewBox="0 0 100 100" class="dsvg" aria-label="d${sides} showing ${txt}">${defs}<g filter="url(#${id}s)">${body}</g></svg>`;
}

// ---------- sound (synthesised clacks, no assets) ----------
let ac = null;
function clack(vol, t0 = 0, thunk = false){
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)(); if (ac.state === 'suspended') ac.resume();
    const len = thunk ? .09 : .035, buf = ac.createBuffer(1, Math.floor(ac.sampleRate * len), ac.sampleRate), d = buf.getChannelData(0);
    for (let i=0;i<d.length;i++) d[i] = (Math.random()*2-1) * Math.pow(1 - i/d.length, thunk ? 3 : 6);
    const src = ac.createBufferSource(); src.buffer = buf;
    const f = ac.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = thunk ? 900 : 2200 + Math.random()*1800; f.Q.value = thunk ? 1.2 : 3;
    const g = ac.createGain(); g.gain.value = vol * (thunk ? .9 : .55);
    src.connect(f); f.connect(g); g.connect(ac.destination); src.start(ac.currentTime + t0);
  } catch(e){}
}

// ---------- roll presentation ----------
function sidesOf(p){ const m = /d(\d+)/.exec(p.dice || ''); return m ? parseInt(m[1]) : 20; }

function show(r, opts = {}){
  const box = opts.host || document.getElementById('dice');
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  box.innerHTML = ''; box.className = 'dice-overlay'; box.classList.remove('hidden');
  const st = opts.style || {};
  box.style.setProperty('--die', st.color || getComputedStyle(document.documentElement).getPropertyValue('--accent') || '#c9a24a');
  box.style.setProperty('--die-ink', st.ink || '#1a1523'); box.style.setProperty('--die-edge', st.edge || 'rgba(20,14,30,.9)');
  if (st.font) box.style.setProperty('--die-font', st.font);
  const glow = st.style === 'neon';
  const tray = document.createElement('div'); tray.className = 'dtray' + (glow ? ' neon' : '');
  const head = document.createElement('div'); head.className = 'dhead';
  head.innerHTML = `<div class="dwho">${esc(r.who && r.who !== 'player' ? r.who : (opts.playerName || 'You'))}</div><div class="dreason">${esc(r.reason || 'Roll')}</div>` +
    (r.mode ? `<div class="dmode ${r.mode.startsWith('adv')?'adv':'dis'}">${r.mode.startsWith('adv') ? 'Advantage' : 'Disadvantage'}</div>` : '');
  const row = document.createElement('div'); row.className = 'drow';
  const dice = [];   // {el, sides, final, kept}
  let mod = 0;
  for (const p of r.parts || []){
    if (p.mod != null){ mod += p.mod; continue; }
    const sides = sidesOf(p);
    const vals = p.adv_pair ? p.adv_pair : p.rolls;
    const kept = [...p.kept];
    vals.forEach(v => { const k = kept.indexOf(v); const isKept = k >= 0; if (isKept) kept.splice(k,1);
      dice.push({sides, final: v, kept: isKept, neg: p.sign < 0}); });
  }
  const many = dice.length > 6;
  dice.forEach((d, i) => {
    const w = document.createElement('div'); w.className = 'die tumble' + (many ? ' small' : '');
    w.style.animationDuration = (0.95 + Math.random()*.45) + 's'; w.style.animationDelay = (i*0.07) + 's';
    w.style.setProperty('--rx', (Math.random()*60-30) + 'px'); w.style.setProperty('--spin', (540 + Math.random()*540) * (Math.random()<.5?-1:1) + 'deg');
    w.innerHTML = svg(d.sides, 1 + Math.floor(Math.random()*d.sides), {glow}) + `<div class="dlbl">d${d.sides}</div>`;
    d.el = w; row.append(w);
  });
  const res = document.createElement('div'); res.className = 'dresult';
  tray.append(head, row, res); box.append(tray);
  const vol = opts.sound === false ? 0 : (opts.volume ?? .8);
  if (vol) for (let k=0;k<Math.min(10, 3 + dice.length*2);k++) clack(vol, .05 + Math.random()*0.9);
  // number flicker
  const iv = setInterval(() => dice.forEach(d => { if (d.el.classList.contains('tumble')) d.el.firstElementChild.outerHTML = svg(d.sides, 1 + Math.floor(Math.random()*d.sides), {glow}); }), 70);
  return new Promise(resolve => {
    let landed = 0;
    dice.forEach(d => d.el.addEventListener('animationend', () => {
      d.el.classList.remove('tumble'); d.el.classList.add('land');
      d.el.firstElementChild.outerHTML = svg(d.sides, d.final, {glow});
      if (!d.kept) d.el.classList.add('dropped');
      if (d.sides === 20 && d.kept && d.final === 20) d.el.classList.add('nat20');
      if (d.sides === 20 && d.kept && d.final === 1) d.el.classList.add('nat1');
      if (vol) clack(vol, 0, true);
      if (++landed === dice.length) finish();
    }, {once: true}));
    if (!dice.length) finish();
    function finish(){
      clearInterval(iv);
      const keptSum = dice.filter(d => d.kept).reduce((s, d) => s + (d.neg ? -d.final : d.final), 0);
      const math = (dice.filter(d=>d.kept).length > 1 || mod) ? `<span class="dm">${keptSum}${mod ? (mod > 0 ? ' + ' + mod : ' − ' + (-mod)) : ''} =</span>` : '';
      let html = `<div class="dtotal">${math}<b>${r.total}</b></div>`;
      if (r.dc != null) html += `<div class="ddc">vs DC <b>${r.dc}</b></div>`;
      let banner = '', cls = '';
      if (r.crit){ banner = 'NATURAL 20'; cls = 'crit'; } else if (r.fumble){ banner = 'NATURAL 1'; cls = 'fumble'; }
      if (r.dc != null){ html += `<div class="dbanner ${r.success ? 'ok' : 'no'}">${r.success ? 'SUCCESS' : 'FAILURE'}</div>`; }
      if (banner) html += `<div class="dbanner ${cls}">${banner}</div>`;
      res.innerHTML = html; res.classList.add('in');
      if (r.crit) burst(tray, '#ffe36a'); if (r.fumble) { tray.classList.add('crack'); }
      if (r.crit) tray.classList.add('critglow');
      const hold = opts.hold || (r.crit || r.fumble ? 3800 : 2800);
      let t = setTimeout(close, hold);
      box.onclick = () => { clearTimeout(t); close(); };
      function close(){ box.onclick = null; box.classList.add('out'); setTimeout(() => { box.classList.add('hidden'); box.classList.remove('out'); resolve(); }, 260); }
    }
  });
}
function burst(host, color){
  for (let i=0;i<28;i++){ const s = document.createElement('i'); s.className = 'spark'; const a = Math.random()*Math.PI*2, d = 90 + Math.random()*140;
    s.style.setProperty('--dx', Math.cos(a)*d + 'px'); s.style.setProperty('--dy', Math.sin(a)*d + 'px'); s.style.background = color; s.style.animationDelay = (Math.random()*.15)+'s'; host.append(s); }
}
window.Dice = { svg, show, clack };
})();
