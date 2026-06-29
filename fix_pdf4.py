with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Hapus logo YBC dari header
content = content.replace(
    "  // ── Logo Your Beauty Choices kanan\n  try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 44, 4, 38, 40); } catch(e) {}",
    ""
)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')