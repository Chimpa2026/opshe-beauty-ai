with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_routine = """  // ── Rutinitas Pagi
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
  });"""

new_routine = """  // ── Helper: render routine step with auto height
  function renderRoutineStep(s) {
    const pageH = 297;
    const marginBottom = 25; // footer space

    // Check if we need a new page
    if (y > pageH - marginBottom - 40) {
      doc.addPage();
      // Mini header
      doc.setFillColor(240, 41, 123);
      doc.rect(0, 0, W, 10, 'F');
      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(255,255,255);
      doc.text('OPSHE Beauty AI — Laporan Analisis Kulit | ' + (userName || ''), 10, 7);
      y = 18;
    }

    // Step number + product type
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...pink);
    doc.text(s.step + '. ' + s.product_type, 14, y);
    y += 5;

    // Why text - calculate actual height
    if (s.why) {
      doc.setFontSize(8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...muted);
      const whyLines = doc.splitTextToSize(s.why, W - 32);
      doc.text(whyLines, 18, y);
      y += whyLines.length * 4.5;
    }

    // Ingredients
    if (s.ingredients && s.ingredients.length) {
      doc.setFontSize(7.5);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...purple);
      const ingText = 'Bahan: ' + s.ingredients.join(', ');
      const ingLines = doc.splitTextToSize(ingText, W - 32);
      doc.text(ingLines, 18, y);
      y += ingLines.length * 4.5;
    }

    // Note
    if (s.note && s.note !== 'null' && s.note !== null) {
      doc.setFontSize(7.5);
      doc.setFont('helvetica', 'italic');
      doc.setTextColor(...teal);
      const noteLines =