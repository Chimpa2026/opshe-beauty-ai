with open('frontend/static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines[:80], 1):
    print(f'{i}: {l}', end='')