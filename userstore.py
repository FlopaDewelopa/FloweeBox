import json
import os
from datetime import datetime, timezone

STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')


def load_store():
    if not os.path.isfile(STORE_PATH):
        return {}
    with open(STORE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_store(data):
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_user(username, ip):
    data = load_store()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    data[username] = {
        "role": "USER",
        "last_ip": ip or "unknown",
        "registered": now,
        "last_login": now
    }
    save_store(data)


def update_login(username, ip):
    data = load_store()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    if username in data:
        data[username]["last_ip"] = ip or "unknown"
        data[username]["last_login"] = now
    else:
        data[username] = {
            "role": "USER",
            "last_ip": ip or "unknown",
            "registered": now,
            "last_login": now
        }
    save_store(data)


def get_role(username):
    data = load_store()
    entry = data.get(username, {})
    return entry.get("role", "USER").upper()


def is_admin_or_owner(username):
    return get_role(username) in ("ADMIN", "OWNER")


def delete_user_data(username):
    data = load_store()
    if username in data:
        del data[username]
        save_store(data)
