@echo off
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -q -r requirements.txt
if not exist uploads mkdir uploads
if not exist .env (
    python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env
    echo Wygenerowano .env z kluczem sesji.
)
python app.py
pause
