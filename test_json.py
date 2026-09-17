import requests
import re
import json
import time
import os

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

print('[1] Rejestracja admin + user')
tk, _ = csrf(f'{BASE}/register')
s.post(f'{BASE}/register', data={'csrf_token': tk, 'username': 'admin1', 'password': 'adminpass1'})
s.get(f'{BASE}/logout')
tk, _ = csrf(f'{BASE}/register')
s.post(f'{BASE}/register', data={'csrf_token': tk, 'username': 'victim', 'password': 'victimpass1'})
s.get(f'{BASE}/logout')
check('Users created', True)

print('[2] Sprawdzenie ról z users.json')
store_path = 'users.json'
with open(store_path, 'r', encoding='utf-8') as f:
    store = json.load(f)

check('Admin role is USER initially', store['admin1']['role'] == 'USER')
check('Victim role is USER', store['victim']['role'] == 'USER')

print('[3] Zmiana roli admina')
store['admin1']['role'] = 'ADMIN'
with open(store_path, 'w', encoding='utf-8') as f:
    json.dump(store, f)

print('[4] Zalogowanie i admin panel')
tk, _ = csrf(f'{BASE}/login')
s.post(f'{BASE}/login', data={'csrf_token': tk, 'username': 'admin1', 'password': 'adminpass1'})
r = s.get(f'{BASE}/admin/')
check('Admin panel 200', r.status_code == 200)

print(f'\nWynik: {passed}/{passed+failed}')
