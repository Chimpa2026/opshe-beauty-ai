with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Logo YBC lebih besar dan rapat ke kanan
content = content.replace(
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 46, 6, 40, 36); } catch(e) {}",
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 50, 2, 48, 44); } catch(e) {}"
)

# Fix 2: Ganti teks footer
content = content.replace(
    "doc.text('opshe.id | @opshe.id', 24, pageH - 7);",
    "doc.text('@opshe.id', 24, pageH - 7);"
)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')