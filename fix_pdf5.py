with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Kembalikan logo Opshe di header (hilang karena inject_logo.py tidak jalan ulang)
# Fix 2: Hapus lingkaran merah muda & perbaiki rasio foto user

old_profile = """  // ── User Profile Section
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

  y += 44;"""

new_profile = """  // ── User Profile Section
  const profileH = 42;
  doc.setFillColor(255, 232, 243);
  doc.roundedRect(10, y, W - 20, profileH, 4, 4, 'F');
  doc.setFillColor(240, 41, 123);
  doc.roundedRect(10, y, 3, profileH, 1, 1, 'F');

  // Foto user — proporsional persegi, tanpa lingkaran
  const photoSize = 34;
  const photoX = 17;
  const photoY = y + (profileH - photoSize) / 2;
  if (userPhotoDataUrl) {
    try {
      // Clip persegi dengan sudut rounded
      doc.setFillColor(240, 41, 123);
      doc.roundedRect(photoX - 1, photoY - 1, photoSize + 2, photoSize + 2, 3, 3, 'F');
      // Foto proporsional 1:1
      doc.addImage(userPhotoDataUrl, 'JPEG', photoX, photoY, photoSize, photoSize, undefined, 'FAST');
    } catch(e) {}
  }

  // Info user
  const infoX = userPhotoDataUrl ? photoX + photoSize + 8 : 18;
  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...teal);
  doc.text('✦ SKIN ANALYSIS REPORT', infoX, y + 10);

  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...ink);
  doc.text(userName || 'Pengguna', infoX, y + 23);

  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...muted);
  doc.text(`Skor: ${data.overall_score}/100  |  Jenis Kulit: ${terjemahSkinType(data.skin_type)}  |  ${tgl}`, infoX, y + 33);

  y += profileH + 8;"""

content = content.replace(old_profile, new_profile)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Profile fix done!')