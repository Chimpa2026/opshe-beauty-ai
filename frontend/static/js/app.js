'use strict';

let stream = null;
let capturedBlob = null;
let lastResult = null;
let userName = '';
let userPhotoDataUrl = '';
let pendingAction = null; // 'camera' or 'upload'

const $ = id => document.getElementById(id);

const btnCamera     = $('btnCamera');
const btnCapture    = $('btnCapture');
const btnRetake     = $('btnRetake');
const btnAnalyze    = $('btnAnalyze');
const btnReanalyze  = $('btnReanalyze');
const btnDownloadPdf= $('btnDownloadPdf');
const btnNameNext   = $('btnNameNext');
const fileInput     = $('fileInput');
const nameModal     = $('nameModal');
const cameraModal   = $('cameraModal');
const previewModal  = $('previewModal');
const loadingOverlay= $('loadingOverlay');
const dashboard     = $('dashboard');
const videoEl       = $('videoEl');
const previewCanvas = $('previewCanvas');
const progressBar   = $('progressBar');
const loadingStep   = $('loadingStep');
const cameraError   = $('cameraError');
const userNameInput = $('userNameInput');
const nameError     = $('nameError');

// ══ TOMBOL UTAMA → NAMA DULU ══
btnCamera.addEventListener('click', () => {
  pendingAction = 'camera';
  userNameInput.value = userName;
  show(nameModal);
  setTimeout(() => userNameInput.focus(), 100);
});

fileInput.addEventListener('change', e => {
  const file = e.target.files?.[0];
  if (!file) return;
  if (!['image/jpeg','image/png','image/webp'].includes(file.type)) {
    alert('Gunakan format JPEG, PNG, atau WebP.'); return;
  }
  pendingAction = 'upload';
  pendingFile = file;
  userNameInput.value = userName;
  show(nameModal);
  setTimeout(() => userNameInput.focus(), 100);
  fileInput.value = '';
});

let pendingFile = null;

// ══ NAMA MODAL ══
btnNameNext.addEventListener('click', submitName);
userNameInput.addEventListener('keydown', e => { if (e.key === 'Enter') submitName(); });

function submitName() {
  const val = userNameInput.value.trim();
  if (!val) {
    nameError.classList.remove('hidden');
    userNameInput.focus();
    return;
  }
  nameError.classList.add('hidden');
  userName = val;
  hide(nameModal);

  if (pendingAction === 'camera') {
    openCamera();
  } else if (pendingAction === 'upload' && pendingFile) {
    processUploadFile(pendingFile);
    pendingFile = null;
  }
  pendingAction = null;
}

// ══ KAMERA ══
$('closeCamera').addEventListener('click', closeCamera);

async function openCamera() {
  cameraError.textContent = '';
  show(cameraModal);
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 960 } },
    });
    videoEl.srcObject = stream;
  } catch (err) {
    cameraError.textContent = 'Akses kamera ditolak. Izinkan kamera dan coba lagi.';
  }
}

function closeCamera() { stopStream(); hide(cameraModal); }
function stopStream() {
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  videoEl.srcObject = null;
}

btnCapture.addEventListener('click', () => {
  const w = videoEl.videoWidth || 640;
  const h = videoEl.videoHeight || 480;
  const tmp = document.createElement('canvas');
  tmp.width = w; tmp.height = h;
  const ctx = tmp.getContext('2d');
  ctx.save(); ctx.scale(-1,1); ctx.drawImage(videoEl,-w,0,w,h); ctx.restore();
  tmp.toBlob(blob => {
    capturedBlob = blob;
    userPhotoDataUrl = tmp.toDataURL('image/jpeg', 0.85);
    closeCamera();
    showPreview(tmp);
  }, 'image/jpeg', 0.92);
});

// ══ UPLOAD ══
function processUploadFile(file) {
  capturedBlob = file;
  const img = new Image();
  img.onload = () => {
    const tmp = document.createElement('canvas');
    tmp.width = img.width; tmp.height = img.height;
    tmp.getContext('2d').drawImage(img, 0, 0);
    userPhotoDataUrl = tmp.toDataURL('image/jpeg', 0.85);
    showPreview(tmp);
    URL.revokeObjectURL(img.src);
  };
  img.src = URL.createObjectURL(file);
}

// ══ PREVIEW ══
function showPreview(srcCanvas) {
  const ctx = previewCanvas.getContext('2d');
  previewCanvas.width = srcCanvas.width;
  previewCanvas.height = srcCanvas.height;
  ctx.drawImage(srcCanvas, 0, 0);
  show(previewModal);
}
$('closePreview').addEventListener('click', () => hide(previewModal));
btnRetake.addEventListener('click', () => {
  hide(previewModal);
  if (stream) openCamera(); else show(nameModal);
});
btnAnalyze.addEventListener('click', runAnalysis);

// ══ ANALISIS ══
const LOADING_STEPS = [
  { text: 'Mendeteksi landmark wajah...', progress: 15 },
  { text: 'Menyelaraskan dan memproses gambar...', progress: 30 },
  { text: 'Mensegmentasi zona wajah...', progress: 45 },
  { text: 'Menganalisis metrik kulit...', progress: 65 },
  { text: 'Mendeteksi jerawat & pigmentasi...', progress: 78 },
  { text: 'Menghitung skor kesehatan kulit...', progress: 90 },
  { text: 'Membuat rekomendasi personal...', progress: 97 },
];

async function runAnalysis() {
  if (!capturedBlob) return;
  hide(previewModal);
  show(loadingOverlay);
  dashboard.classList.add('hidden');

  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    if (stepIdx < LOADING_STEPS.length) {
      loadingStep.textContent = LOADING_STEPS[stepIdx].text;
      progressBar.style.width = LOADING_STEPS[stepIdx].progress + '%';
      stepIdx++;
    }
  }, 700);

  try {
    const formData = new FormData();
    formData.append('file', capturedBlob, 'skin_capture.jpg');
    const res = await fetch('/analyze', { method: 'POST', body: formData });
    const data = await res.json();
    clearInterval(stepInterval);
    loadingStep.textContent = 'Selesai! ✨';
    progressBar.style.width = '100%';

    if (!res.ok) {
      setTimeout(() => { hide(loadingOverlay); alert(data.detail || 'Analisis gagal. Coba lagi.'); }, 500);
      return;
    }
    lastResult = data;
    setTimeout(() => {
      hide(loadingOverlay);
      renderDashboard(data);
      dashboard.classList.remove('hidden');
      dashboard.scrollIntoView({ behavior: 'smooth' });
    }, 600);
  } catch (err) {
    clearInterval(stepInterval);
    hide(loadingOverlay);
    alert('Koneksi gagal. Periksa koneksi internet Anda.');
  }
}

btnReanalyze.addEventListener('click', () => {
  dashboard.classList.add('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ══ DOWNLOAD PDF ══
btnDownloadPdf.addEventListener('click', () => {
  if (!lastResult) return;
  generatePDF(lastResult);
});

function generatePDF(data) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  const W = 210;
  const pink   = [240, 41, 123];
  const purple = [155, 107, 200];
  const teal   = [46, 196, 196];
  const ink    = [45, 18, 53];
  const muted  = [155, 126, 168];
  const pale   = [255, 232, 243];

  let y = 0;

  // ── Header background pink solid
  doc.setFillColor(240, 41, 123);
  doc.rect(0, 0, W, 48, 'F');

  // ── Logo Opshe kiri
  try { doc.addImage(LOGO_B64, 'PNG', 6, 4, 38, 38); } catch(e) {}

  // ── Judul tengah
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text('LAPORAN ANALISIS KULIT', W / 2, 20, { align: 'center' });
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bolditalic');
  doc.text('Ai - Powered Skin Intelligence Report', W / 2, 30, { align: 'center' });

  // ── Tanggal
  const now = new Date();
  const tgl = now.toLocaleDateString('id-ID', { day:'2-digit', month:'long', year:'numeric' });
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(255, 220, 240);
  doc.text(tgl, W / 2, 40, { align: 'center' });

  y = 58;

  // ── User Profile Section
  doc.setFillColor(255, 232, 243);
  doc.roundedRect(10, y, W - 20, 36, 4, 4, 'F');
  doc.setFillColor(240, 41, 123);
  doc.roundedRect(10, y, 3, 36, 1, 1, 'F');

  // Foto user (lingkaran)
  if (userPhotoDataUrl) {
    try {
      // Gambar foto sebagai lingkaran dengan clip
      doc.addImage(userPhotoDataUrl, 'JPEG', 18, y + 4, 28, 28);
    } catch(e) {}
    // Border lingkaran
    doc.setDrawColor(...pink);
    doc.setLineWidth(0.8);
    doc.circle(32, y + 18, 14);
  }

  // Info user
  const infoX = userPhotoDataUrl ? 52 : 18;
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...teal);
  doc.text('SKIN ANALYSIS REPORT', infoX, y + 10);

  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...ink);
  doc.text(userName || 'Pengguna', infoX, y + 22);

  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...muted);
  doc.text(`Skor: ${data.overall_score}/100  |  Jenis Kulit: ${terjemahSkinType(data.skin_type)}  |  ${tgl}`, infoX, y + 31);

  y += 44;

  // ── Score section
  doc.setFillColor(...pale);
  doc.roundedRect(10, y, W - 20, 32, 4, 4, 'F');
  doc.setFillColor(...pink);
  doc.roundedRect(10, y, 3, 32, 1, 1, 'F');

  doc.setFontSize(28);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...pink);
  doc.text(`${data.overall_score}`, 32, y + 20);
  doc.setFontSize(11);
  doc.setTextColor(...muted);
  doc.text('/100', 32, y + 28);

  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...ink);
  doc.text('Skor Kesehatan Kulit', 60, y + 12);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...muted);
  doc.text(scoreDescription(data.overall_score), 60, y + 20, { maxWidth: 130 });

  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...purple);
  doc.text(`Jenis Kulit: ${terjemahSkinType(data.skin_type)}  |  Warna: ${terjemahSkinTone(data.skin_tone)}  |  Undertone: ${terjemahUndertone(data.undertone)}`, 60, y + 28);

  y += 42;

  // ── Section helper
  function sectionTitle(title) {
    doc.setFillColor(...pink);
    doc.rect(10, y, W - 20, 7, 'F');
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text(title, 14, y + 5);
    y += 11;
  }

  function twoColRow(label, value, isRight = false) {
    const x = isRight ? W / 2 + 5 : 14;
    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...muted);
    doc.text(label, x, y);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...ink);
    doc.text(String(value), x + 45, y);
  }

  // ── Metrik Kulit
  sectionTitle('METRIK KULIT');
  const metrikRows = [
    ['Kadar Minyak', `${Math.round(data.oil_level)}%`],
    ['Kekeringan', `${Math.round(data.dryness)}%`],
    ['Visibilitas Pori', `${Math.round(data.pore_visibility)}%`],
    ['Kemerahan', `${Math.round(data.redness)}%`],
    ['Pigmentasi', `${Math.round(data.pigmentation)}%`],
    ['Bintik Gelap', `${data.dark_spot_count}`],
    ['Tekstur Kulit', terjemahTexture(data.skin_texture)],
    ['Lingkaran Hitam', terjemahLevel(data.dark_circle_level)],
    ['Garis Halus', terjemahLevel(data.fine_lines_level)],
  ];
  for (let i = 0; i < metrikRows.length; i += 2) {
    doc.setFillColor(i % 4 === 0 ? 252 : 255, 248, 252);
    doc.rect(10, y - 4, W - 20, 8, 'F');
    twoColRow(metrikRows[i][0], metrikRows[i][1], false);
    if (metrikRows[i + 1]) twoColRow(metrikRows[i+1][0], metrikRows[i+1][1], true);
    y += 8;
  }
  y += 4;

  // ── Analisis Jerawat
  sectionTitle('ANALISIS JERAWAT & NODA');
  const am = data.acne_metrics || {};
  const acneItems = [
    ['Jerawat', am.acne ?? 0],
    ['Komedo Putih', am.whitehead ?? 0],
    ['Komedo Hitam', am.blackhead ?? 0],
    ['Bekas Jerawat', am.acne_scar ?? 0],
  ];
  for (let i = 0; i < acneItems.length; i += 2) {
    doc.setFillColor(i % 4 === 0 ? 252 : 255, 248, 252);
    doc.rect(10, y - 4, W - 20, 8, 'F');
    twoColRow(acneItems[i][0], acneItems[i][1], false);
    if (acneItems[i+1]) twoColRow(acneItems[i+1][0], acneItems[i+1][1], true);
    y += 8;
  }
  y += 4;

  // ── Zona Wajah
  if (data.zones && data.zones.length > 0) {
    sectionTitle('ANALISIS PER ZONA WAJAH');
    const namaZona = {'Forehead':'Dahi','Nose':'Hidung','Left Cheek':'Pipi Kiri','Right Cheek':'Pipi Kanan','Chin':'Dagu'};
    data.zones.forEach(z => {
      doc.setFontSize(8.5);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...pink);
      doc.text((namaZona[z.zone] || z.zone).toUpperCase(), 14, y);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...ink);
      doc.text(
        `Minyak: ${Math.round(z.oil_level)}%  |  Kering: ${Math.round(z.dryness)}%  |  Pori: ${Math.round(z.pore_visibility)}%  |  Kemerahan: ${Math.round(z.redness)}%  |  Tekstur: ${terjemahTexture(z.texture)}`,
        14, y + 5
      );
      y += 11;
    });
    y += 2;
  }

  // ── Page 2
  doc.addPage();
  y = 15;

  // Mini header page 2
  doc.setFillColor(240, 41, 123);
  doc.rect(0, 0, W, 10, 'F');
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(255,255,255);
  doc.text(`OPSHE Beauty AI — Laporan Analisis Kulit | ${userName}`, 10, 7);
  y = 18;

  // ── Rutinitas Pagi
  sectionTitle('RUTINITAS PAGI');
  (data.morning_routine || []).forEach(s => {
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...pink);
    doc.text(`${s.step}. ${s.product_type}`, 14, y);
    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...muted);
    doc.text(s.why || '', 18, y, { maxWidth: W - 30 });
    y += 5;
    if (s.ingredients && s.ingredients.length) {
      doc.setFontSize(8);
      doc.setTextColor(...purple);
      doc.text('Bahan: ' + s.ingredients.join(', '), 18, y, { maxWidth: W - 30 });
      y += 5;
    }
    if (s.note) {
      doc.setFontSize(7.5);
      doc.setTextColor(...teal);
      doc.text('💡 ' + s.note, 18, y, { maxWidth: W - 30 });
      y += 4;
    }
    y += 2;
  });

  y += 4;

  // ── Rutinitas Malam
  sectionTitle('RUTINITAS MALAM');
  (data.night_routine || []).forEach(s => {
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...pink);
    doc.text(`${s.step}. ${s.product_type}`, 14, y);
    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...muted);
    doc.text(s.why || '', 18, y, { maxWidth: W - 30 });
    y += 5;
    if (s.ingredients && s.ingredients.length) {
      doc.setFontSize(8);
      doc.setTextColor(...purple);
      doc.text('Bahan: ' + s.ingredients.join(', '), 18, y, { maxWidth: W - 30 });
      y += 5;
    }
    y += 2;
  });

  // ── Footer semua halaman
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    const pageH = 297;
    doc.setFillColor(240, 41, 123);
    doc.rect(0, pageH - 20, W, 20, 'F');

    try { doc.addImage(LOGO_B64, 'PNG', 4, pageH - 19, 16, 16); } catch(e) {}

    doc.setFontSize(6);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(255, 255, 255);
    doc.text(
      'Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit.',
      24, pageH - 13, { maxWidth: W - 70 }
    );
    doc.setFontSize(5.5);
    doc.setTextColor(255, 220, 240);
    doc.text('@opshe.id', 24, pageH - 7);

    try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 30, pageH - 19, 26, 16); } catch(e) {}

    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text(`Hal. ${i} / ${pageCount}`, W / 2, pageH - 6, { align: 'center' });
  }

  const filename = `OPSHE_${userName.replace(/\s+/g,'_')}_${now.toISOString().slice(0,10)}.pdf`;
  doc.save(filename);
}

// ══ RENDER DASHBOARD ══
function renderDashboard(data) {
  renderUserProfile();
  renderScore(data);
  renderMetrics(data);
  renderAcne(data);
  renderZones(data.zones || []);
  renderRoutine(data.morning_routine || [], 'tabMorning');
  renderRoutine(data.night_routine || [], 'tabNight');
  renderWeekly(data.recommendations?.weekly_treatments || []);
  renderIngredients(data.recommendations?.ingredients_by_concern || {});
  renderDisclaimer(data.recommendations?.disclaimer);
}

function renderUserProfile() {
  $('userNameDisplay').textContent = userName || '—';
  const avatarImg = $('userAvatarImg');
  if (userPhotoDataUrl) {
    avatarImg.src = userPhotoDataUrl;
    avatarImg.style.display = 'block';
  }
}

function renderScore(data) {
  const score = data.overall_score || 0;
  $('scoreNum').textContent = score;
  setTimeout(() => { $('scoreArc').style.strokeDashoffset = 314 - (score/100)*314; }, 100);
  $('scoreDesc').textContent = scoreDescription(score);
  $('skinTypeBadge').textContent = terjemahSkinType(data.skin_type) || '—';
  $('skinTone').textContent = terjemahSkinTone(data.skin_tone) || '—';
  $('undertone').textContent = terjemahUndertone(data.undertone) || '—';
}

function scoreDescription(score) {
  if (score >= 85) return 'Kesehatan kulit sangat baik — sedikit penyesuaian untuk hasil sempurna.';
  if (score >= 70) return 'Kesehatan kulit baik — perawatan terarah dapat mengatasi beberapa masalah.';
  if (score >= 55) return 'Kesehatan kulit cukup — rutinitas konsisten akan membuat perbedaan nyata.';
  if (score >= 40) return 'Ada beberapa masalah kulit — rutinitas personal sangat direkomendasikan.';
  return 'Beberapa masalah terdeteksi — segera mulai rutinitas perawatan kulit terstruktur.';
}

function terjemahSkinType(v) { return {Oily:'Berminyak',Dry:'Kering',Combination:'Kombinasi',Normal:'Normal'}[v]||v; }
function terjemahSkinTone(v) { return {Fair:'Cerah',Light:'Terang',Medium:'Sedang',Tan:'Tan',Deep:'Gelap'}[v]||v; }
function terjemahUndertone(v) { return {Cool:'Dingin',Warm:'Hangat',Neutral:'Netral'}[v]||v; }
function terjemahTexture(v) { return {Smooth:'Halus',Normal:'Normal',Rough:'Kasar'}[v]||v; }
function terjemahLevel(v) { return {None:'Tidak Ada',Light:'Ringan',Medium:'Sedang',Heavy:'Berat',Mild:'Ringan',Moderate:'Sedang',Severe:'Parah'}[v]||v; }

function renderMetrics(data) {
  const grid = $('metricsGrid');
  grid.innerHTML = '';
  const metrics = [
    { label:'Kadar Minyak',     value:data.oil_level,         unit:'%', bar:true },
    { label:'Kekeringan',        value:data.dryness,           unit:'%', bar:true },
    { label:'Visibilitas Pori',  value:data.pore_visibility,   unit:'%', bar:true },
    { label:'Kemerahan',         value:data.redness,           unit:'%', bar:true },
    { label:'Pigmentasi',        value:data.pigmentation,      unit:'%', bar:true },
    { label:'Bintik Gelap',      value:data.dark_spot_count,   unit:'', bar:false },
    { label:'Tekstur Kulit',     value:terjemahTexture(data.skin_texture), unit:'', bar:false, badge:true },
    { label:'Lingkaran Hitam',   value:terjemahLevel(data.dark_circle_level), unit:'', bar:false, badge:true },
    { label:'Garis Halus',       value:terjemahLevel(data.fine_lines_level), unit:'', bar:false, badge:true },
  ];
  metrics.forEach(m => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    let html = '';
    if (m.bar) {
      const pct = Math.round(m.value||0);
      html = `<div class="metric-value">${pct}${m.unit}</div><div class="metric-bar"><div class="metric-bar-fill" style="width:${pct}%"></div></div>`;
    } else if (m.badge) {
      html = `<div class="metric-value" style="font-size:1.1rem">${m.value||'—'}</div><span class="metric-badge ${badgeClass(m.value)}">${m.value||'—'}</span>`;
    } else {
      html = `<div class="metric-value">${m.value??'—'}${m.unit}</div>`;
    }
    card.innerHTML = `<div class="metric-label">${m.label}</div>${html}`;
    grid.appendChild(card);
  });
}

function badgeClass(val) {
  if (['Halus','Normal','Tidak Ada','Ringan'].includes(val)) return 'badge-good';
  if (['Kasar','Berat','Parah'].includes(val)) return 'badge-bad';
  return 'badge-warn';
}

function renderAcne(data) {
  const am = data.acne_metrics || {};
  $('acneGrid').innerHTML = [
    { icon:'🔴', label:'Jerawat',       count:am.acne??0 },
    { icon:'⚪', label:'Komedo Putih',  count:am.whitehead??0 },
    { icon:'⚫', label:'Komedo Hitam',  count:am.blackhead??0 },
    { icon:'🟤', label:'Bekas Jerawat', count:am.acne_scar??0 },
  ].map(i=>`<div class="acne-card"><div class="acne-icon">${i.icon}</div><div class="acne-count">${i.count}</div><div class="acne-label">${i.label}</div></div>`).join('');
}

function renderZones(zones) {
  const nama = {'Forehead':'Dahi','Nose':'Hidung','Left Cheek':'Pipi Kiri','Right Cheek':'Pipi Kanan','Chin':'Dagu'};
  $('zonesGrid').innerHTML = zones.map(z=>`
    <div class="zone-card">
      <div class="zone-name">${nama[z.zone]||z.zone}</div>
      <div class="zone-row"><span>Minyak</span><span class="zone-val">${Math.round(z.oil_level)}%</span></div>
      <div class="zone-row"><span>Kering</span><span class="zone-val">${Math.round(z.dryness)}%</span></div>
      <div class="zone-row"><span>Pori</span><span class="zone-val">${Math.round(z.pore_visibility)}%</span></div>
      <div class="zone-row"><span>Kemerahan</span><span class="zone-val">${Math.round(z.redness)}%</span></div>
      <div class="zone-row"><span>Tekstur</span><span class="zone-val">${terjemahTexture(z.texture)}</span></div>
    </div>`).join('');
}

function renderRoutine(steps, id) {
  const el = $(id);
  if (!steps.length) { el.innerHTML='<p style="color:var(--muted)">Tidak ada langkah tersedia.</p>'; return; }
  el.innerHTML = `<div class="routine-steps">${steps.map(s=>`
    <div class="routine-step">
      <div class="step-num">${s.step}</div>
      <div class="step-body">
        <div class="step-product">${s.product_type}</div>
        <div class="step-why">${s.why||''}</div>
        <div class="step-ings">${(s.ingredients||[]).map(i=>`<span class="ing-chip">${i}</span>`).join('')}</div>
        ${s.note?`<div class="step-note">💡 ${s.note}</div>`:''}
      </div>
    </div>`).join('')}</div>`;
}

function renderWeekly(treatments) {
  const el = $('tabWeekly');
  if (!treatments.length) { el.innerHTML='<p style="color:var(--muted)">Tidak ada perawatan mingguan yang direkomendasikan.</p>'; return; }
  el.innerHTML = `<div class="weekly-cards">${treatments.map(t=>`
    <div class="weekly-card">
      <div class="weekly-type">${t.product_type}</div>
      <div class="weekly-why">${t.why||''}</div>
      <div class="step-ings">${(t.ingredients||[]).map(i=>`<span class="ing-chip">${i}</span>`).join('')}</div>
    </div>`).join('')}</div>`;
}

function renderIngredients(byConcern) {
  const el = $('tabIngredients');
  const entries = Object.entries(byConcern);
  if (!entries.length) { el.innerHTML='<p style="color:var(--muted)">Tidak ada masalah bahan aktif terdeteksi.</p>'; return; }
  const nama = {oily:'Berminyak',dry:'Kering',combination:'Kombinasi',normal:'Normal',sensitive:'Sensitif',acne:'Jerawat',hyperpigmentation:'Hiperpigmentasi',fine_lines:'Garis Halus',redness:'Kemerahan',dark_circles:'Lingkaran Hitam',dehydrated:'Dehidrasi'};
  el.innerHTML = entries.map(([k,ings])=>`
    <div class="ing-concern-block">
      <div class="concern-title">${nama[k]||k}</div>
      <div class="ing-list">${ings.map(i=>`<span class="ing-chip">${i}</span>`).join('')}</div>
    </div>`).join('');
}

function renderDisclaimer(text) {
  if (text) $('disclaimerText').textContent = text;
}

// ══ TABS ══
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    ['tabMorning','tabNight','tabWeekly','tabIngredients'].forEach(id => {
      const el = $(id); if (el) el.classList.add('hidden');
    });
    const map = {morning:'tabMorning',night:'tabNight',weekly:'tabWeekly',ingredients:'tabIngredients'};
    const target = $(map[tab.dataset.tab]);
    if (target) target.classList.remove('hidden');
  });
});

function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }