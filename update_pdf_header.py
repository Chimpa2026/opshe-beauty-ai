# Baca kedua base64
with open('frontend/static/assets/logo_b64.txt', 'r') as f:
    b64_opshe = f.read().strip()

with open('frontend/static/assets/logo_ybc_b64.txt', 'r') as f:
    b64_ybc = f.read().strip()

# Baca app.js
with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Tambah konstanta YBC jika belum ada
if 'const LOGO_YBC_B64' not in content:
    insert = f"const LOGO_YBC_B64 = 'data:image/png;base64,{b64_ybc}';\n"
    content = insert + content

# Ganti fungsi generatePDF — cari blok header lama dan ganti
old_header = """  // ── Header background
  doc.setFillColor(...pink);
  doc.rect(0, 0, W, 42, 'F');

  // ── Gradient overlay (purple strip)
  doc.setFillColor(...purple);
  doc.rect(W - 60, 0, 60, 42, 'F');

  // ── Logo
  try { doc.addImage(LOGO_B64, 'PNG', 10, 5, 32, 32); } catch(e) {}

  // ── Header title
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(20);
  doc.setFont('helvetica', 'bold');
  doc.text('OPSHE Beauty AI', 48, 17);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text('Laporan Analisis Kulit Virtual', 48, 25);

  // ── Date
  const now = new Date();
  const tgl = now.toLocaleDateString('id-ID', { day:'2-digit', month:'long', year:'numeric' });
  doc.setFontSize(8);
  doc.text(`Tanggal: ${tgl}`, 48, 33);"""

new_header = """  // ── Header background pink solid
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

  // ── Logo Your Beauty Choices kanan
  try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 46, 6, 40, 36); } catch(e) {}"""

content = content.replace(old_header, new_header)

# Ganti footer juga
old_footer = """    // Footer bar
    doc.setFillColor(...pink);
    doc.rect(0, pageH - 18, W, 18, 'F');

    // Logo footer
    try { doc.addImage(LOGO_B64, 'PNG', 5, pageH - 16, 10, 10); } catch(e) {}

    // Disclaimer text
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(255,255,255);
    doc.text(
      'Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit.',
      25, pageH - 11, { maxWidth: W - 40 }
    );

    // Page number
    doc.setFontSize(7);
    doc.text(`Hal. ${i} / ${pageCount}`, W - 12, pageH - 5, { align: 'right' });"""

new_footer = """    // Footer bar pink
    doc.setFillColor(240, 41, 123);
    doc.rect(0, pageH - 20, W, 20, 'F');

    // Logo Opshe kecil kiri
    try { doc.addImage(LOGO_B64, 'PNG', 4, pageH - 19, 16, 16); } catch(e) {}

    // Disclaimer text
    doc.setFontSize(6);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(255, 255, 255);
    doc.text(
      'Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit.',
      24, pageH - 13, { maxWidth: W - 70 }
    );
    doc.setFontSize(5.5);
    doc.setTextColor(255, 220, 240);
    doc.text('opshe.id | @opshe.id', 24, pageH - 7);

    // Logo YBC kanan footer
    try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 36, pageH - 19, 32, 16); } catch(e) {}

    // Page number
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text(`Hal. ${i} / ${pageCount}`, W / 2, pageH - 6, { align: 'center' });"""

content = content.replace(old_footer, new_footer)

# Ganti juga tinggi y setelah header (dari 52 ke 58)
content = content.replace('\n  y = 52;\n', '\n  y = 58;\n')

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Header & footer PDF berhasil diupdate!')