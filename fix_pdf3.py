with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix posisi dan ukuran logo YBC di header
content = content.replace(
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 50, 2, 48, 44); } catch(e) {}",
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 44, 4, 38, 40); } catch(e) {}"
)

# Fix juga logo YBC di footer agar proporsional
content = content.replace(
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 36, pageH - 19, 32, 16); } catch(e) {}",
    "try { doc.addImage(LOGO_YBC_B64, 'PNG', W - 30, pageH - 19, 26, 16); } catch(e) {}"
)

with open('frontend/static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')