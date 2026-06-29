# Baca base64 logo
with open('frontend/static/assets/logo_b64.txt', 'r') as f:
    b64 = f.read().strip()

# Baca app.js
with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Sisipkan konstanta logo di baris pertama
logo_line = f"const LOGO_B64 = 'data:image/png;base64,{b64}';\n\n"

if 'const LOGO_B64' not in content:
    content = logo_line + content

# Ganti placeholder logo di generatePDF
old = "// ── Logo placeholder circle\n  doc.setFillColor(255, 255, 255);\n  doc.circle(20, 21, 10, 'F');\n  doc.setFontSize(7);\n  doc.setTextColor(...pink);\n  doc.setFont('helvetica', 'bold');\n  doc.text('OPSHE', 20, 23, { align: 'center' });"

new = "// ── Logo\n  try { doc.addImage(LOGO_B64, 'PNG', 10, 5, 32, 32); } catch(e) {}"

content = content.replace(old, new)

# Ganti juga logo kecil di footer
old2 = "// Logo circle\n    doc.setFillColor(255,255,255);\n    doc.circle(15, pageH - 9, 5, 'F');\n    doc.setFontSize(4.5);\n    doc.setTextColor(...pink);\n    doc.setFont('helvetica', 'bold');\n    doc.text('OPSHE', 15, pageH - 8, { align: 'center' });"

new2 = "// Logo footer\n    try { doc.addImage(LOGO_B64, 'PNG', 5, pageH - 16, 10, 10); } catch(e) {}"

content = content.replace(old2, new2)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Logo berhasil disisipkan ke app.js!')