with open('frontend/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    'id="nameModal"',
    'id="btnCamera"',
    'id="btnNameNext"',
    'id="userNameInput"',
    'id="fileInput"',
    'id="cameraModal"',
    'id="previewModal"',
    'id="loadingOverlay"',
]

for c in checks:
    found = content.count(c)
    print(f"{'OK' if found > 0 else 'MISSING'} ({found}x): {c}")