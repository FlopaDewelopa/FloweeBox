import requests, re, sqlite3

s = requests.Session()
def csrf(url):
    r = s.get(url)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1), r

tk, _ = csrf('http://127.0.0.1:5000/register')
s.post('http://127.0.0.1:5000/register', data={'csrf_token': tk, 'username': 'test99', 'email': 'test99@ex.com', 'password': 'password123'})
s.get('http://127.0.0.1:5000/logout')

tk, _ = csrf('http://127.0.0.1:5000/login')
s.post('http://127.0.0.1:5000/login', data={'csrf_token': tk, 'login_id': 'test99', 'password': 'password123'})

conn = sqlite3.connect('mediabox.db')
c = conn.cursor()
c.execute("SELECT otp_code FROM users WHERE username='test99'")
otp = c.fetchone()[0]

tk, _ = csrf('http://127.0.0.1:5000/verify-otp')
r = s.post('http://127.0.0.1:5000/verify-otp', data={'csrf_token': tk, 'otp': otp})

print(r.url)
print('Wyloguj' in r.text)
if 'Wyloguj' not in r.text:
    print(r.text)
