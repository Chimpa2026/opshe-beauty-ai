with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Hapus baris duplikat "let pendingFile = null;" yang ada di baris 58
new_lines = []
pendingfile_count = 0
for line in lines:
    if line.strip() == 'let pendingFile = null;':
        pendingfile_count += 1
        if pendingfile_count == 1:
            new_lines.append(line)  # keep yang pertama
        # skip yang kedua
    else:
        new_lines.append(line)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Fixed! Ditemukan {pendingfile_count} deklarasi pendingFile, duplikat dihapus.')