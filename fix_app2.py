with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Cek posisi pendingFile
idx1 = content.find("let pendingFile")
idx2 = content.find("pendingFile = file")
print(f"Deklarasi pendingFile di karakter: {idx1}")
print(f"Pertama dipakai di karakter: {idx2}")
print(f"Masalah: {'YA - dipakai sebelum deklarasi' if idx2 < idx1 else 'TIDAK - sudah benar'}")
print()

# Fix - pastikan pendingFile dideklarasikan di awal
if idx2 < idx1:
    # Hapus semua deklarasi lama
    content = content.replace("let pendingFile = null;\n", "")
    content = content.replace("let pendingFile = null;", "")
    
    # Sisipkan di baris ke-3 setelah 'use strict'
    content = content.replace(
        "'use strict';\n\nlet stream",
        "'use strict';\n\nlet stream"
    )
    # Tambah di awal variabel state
    content = content.replace(
        "let stream = null;\nlet capturedBlob = null;",
        "let stream = null;\nlet capturedBlob = null;\nlet pendingFile = null;"
    )
    
    with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIXED!")
else:
    print("Tidak perlu fix, sudah benar.")