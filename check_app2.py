with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Cek fungsi-fungsi kritis
checks = [
    "btnCamera.addEventListener",
    "fileInput.addEventListener",
    "btnNameNext.addEventListener",
    "function submitName",
    "function openCamera",
    "function processUploadFile",
    "show(nameModal)",
    "hide(nameModal)",
    "id='nameModal'",
    'id="nameModal"',
    "id='btnCamera'",
    'id="btnCamera"',
]

for c in checks:
    found = content.count(c)
    print(f"{'OK' if found > 0 else 'MISSING'} ({found}x): {c}")