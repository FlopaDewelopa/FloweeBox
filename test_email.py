import requests
import re
import sqlite3

BASE = 'http://127.0.0.1:5000'
s = requests.Session()
passed = 0
failed = 0

def csrf(url):
    r = s.get(url)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else None, r

def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f'  OK  {name}')
    else:
        failed += 1
        print(f'  FAIL {name}')

print('[1] Rejestracja z emailem')
tk, _ = csrf(f'{BASE}/register')
r = s.post(f'{BASE}/register', data={'csrf_token': tk, 'username': 'user_email', 'email': 'test@example.com', 'password': 'password123'})
check('Registered and logged in', 'Wyloguj' in r.text)
s.get(f'{BASE}/logout')

print('[2] Logowanie i przechwycenie weryfikacji')
tk, _ = csrf(f'{BASE}/login')
r = s.post(f'{BASE}/login', data={'csrf_token': tk, 'login_id': 'test@example.com', 'password': 'password123'})
check('Przekierowano na verify', 'Weryfikacja dwuetapowa' in r.text)

print('[3] Odczytanie pinu z bazy')
conn = sqlite3.connect('C:\\Users\\swiat\\Desktop\\MediaBox\\mediabox.db')
c = conn.cursor()
c.execute("SELECT otp_code FROM users WHERE email='test@example.com'")
otp = c.fetchone()[0]
conn.close()
check('Wygenerowano OTP', otp is not None and len(otp) == 6)

print('[4] Weryfikacja kodem')
tk, _ = csrf(f'{BASE}/verify-otp')
r = s.post(f'{BASE}/verify-otp', data={'csrf_token': tk, 'otp': otp})
check('Pomyslnie zalogowano po OTP', 'Wyloguj' in r.text)
s.get(f'{BASE}/logout')

print('[5] Logowanie na stare konto bez emaila (jesli takie by bylo)')
tk, _ = csrf(f'{BASE}/register')
s.post(f'{BASE}/register', data={'csrf_token': tk, 'username': 'noemailuser', 'email': 'noemail@example.com', 'password': 'password123'})
s.get(f'{BASE}/logout')

print(f'\nWynik: {passed}/{passed+failed}')
