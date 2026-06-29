import base64
with open('frontend/static/assets/logo_ybc.png', 'rb') as f:
    data = base64.b64encode(f.read()).decode()
with open('frontend/static/assets/logo_ybc_b64.txt', 'w') as f:
    f.write(data)
print('Done! Panjang:', len(data))