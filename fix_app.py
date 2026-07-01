with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: pindahkan deklarasi pendingFile ke atas sebelum dipakai
content = content.replace(
    "let pendingAction = null; // 'camera' or 'upload'",
    "let pendingAction = null; // 'camera' or 'upload'\nlet pendingFile = null;"
)

# Hapus deklarasi duplikat yang ada di bawah
content = content.replace(
    "\nlet pendingFile = null;\n\n// ══ KAMERA ══",
    "\n\n// ══ KAMERA ══"
)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed!')