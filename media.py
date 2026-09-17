import os
import uuid
import mimetypes
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, Response, abort
)
from flask_login import login_required, current_user
from models import db, Media
from utils import validate_file, generate_filename, format_size

media_bp = Blueprint('media', __name__)

CHUNK_SIZE = 65536


@media_bp.route('/regulamin')
def regulamin():
    return render_template('regulamin.html')


@media_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str).strip()
    sort = request.args.get('sort', 'date', type=str)
    query = Media.query.filter_by(is_public=True)
    if search:
        query = query.filter(Media.title.ilike(f'%{search}%'))
    if sort == 'name':
        query = query.order_by(Media.title.asc())
    else:
        query = query.order_by(Media.created_at.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False
    )
    return render_template(
        'index.html', media_list=pagination.items, pagination=pagination,
        search=search, sort=sort, format_size=format_size
    )


@media_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title or len(title) > 200:
            flash('Tytul jest wymagany (maks. 200 znakow).', 'error')
            return render_template('upload.html', title=title)
        file = request.files.get('file')
        if not file or not file.filename:
            flash('Plik jest wymagany.', 'error')
            return render_template('upload.html', title=title)
        valid, ext = validate_file(
            file,
            current_app.config['ALLOWED_EXTENSIONS'],
            current_app.config['ALLOWED_MIME_TYPES']
        )
        if not valid:
            flash('Nieprawidlowy format pliku.', 'error')
            return render_template('upload.html', title=title)
        media_type = 'video' if ext in current_app.config['VIDEO_EXTENSIONS'] else 'audio'
        filename = generate_filename(ext)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        is_public = request.form.get('is_public') == '1'
        try:
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            media = Media(
                filename=filename,
                original_name=file.filename,
                title=title,
                user_id=current_user.id,
                is_public=is_public,
                media_type=media_type,
                file_size=file_size
            )
            db.session.add(media)
            db.session.commit()
        except Exception:
            if os.path.isfile(filepath):
                os.remove(filepath)
            flash('Blad podczas zapisywania pliku.', 'error')
            return render_template('upload.html', title=title)
        return redirect(url_for('media.player', media_id=media.id))
    return render_template('upload.html', title='')


@media_bp.route('/watch/<int:media_id>')
def player(media_id):
    media_item = Media.query.get_or_404(media_id)
    if not media_item.is_public:
        is_owner = current_user.is_authenticated and current_user.id == media_item.user_id
        is_admin = current_user.is_authenticated and current_user.is_admin
        if not is_owner and not is_admin:
            abort(403)
    mime = mimetypes.guess_type(media_item.filename)[0] or ''
    return render_template('player.html', media=media_item, format_size=format_size, mime=mime, share_token=None)


@media_bp.route('/stream/<int:media_id>')
def stream(media_id):
    media_item = Media.query.get_or_404(media_id)
    token = request.args.get('token', '')
    if not media_item.is_public:
        is_owner = current_user.is_authenticated and current_user.id == media_item.user_id
        is_admin = current_user.is_authenticated and current_user.is_admin
        has_token = token and media_item.share_token and token == media_item.share_token
        if not is_owner and not is_admin and not has_token:
            abort(403)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], media_item.filename)
    if not os.path.isfile(filepath):
        abort(404)
    file_size = os.path.getsize(filepath)
    mime = mimetypes.guess_type(media_item.filename)[0] or 'application/octet-stream'
    download = request.args.get('download') == '1'
    range_header = request.headers.get('Range')
    if range_header:
        try:
            ranges = range_header.replace('bytes=', '').split('-')
            byte_start = int(ranges[0]) if ranges[0] else 0
            byte_end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
        except (ValueError, IndexError):
            return Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})
        if byte_start >= file_size or byte_end >= file_size or byte_start > byte_end:
            return Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})
        content_length = byte_end - byte_start + 1

        def generate_range():
            with open(filepath, 'rb') as f:
                f.seek(byte_start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        response = Response(generate_range(), status=206, mimetype=mime)
        response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
        response.headers['Content-Length'] = content_length
    else:
        def generate_full():
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk

        response = Response(generate_full(), mimetype=mime)
        response.headers['Content-Length'] = file_size
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'private, max-age=3600'
    if download:
        response.headers['Content-Disposition'] = f'attachment; filename="{media_item.original_name}"'
    return response


@media_bp.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    pagination = Media.query.filter_by(user_id=current_user.id).order_by(
        Media.created_at.desc()
    ).paginate(page=page, per_page=current_app.config['ITEMS_PER_PAGE'], error_out=False)
    return render_template(
        'dashboard.html', media_list=pagination.items,
        pagination=pagination, format_size=format_size
    )


@media_bp.route('/delete/<int:media_id>', methods=['POST'])
@login_required
def delete(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.user_id != current_user.id:
        abort(403)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], media_item.filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
    db.session.delete(media_item)
    db.session.commit()
    flash('Plik zostal usuniety.', 'info')
    return redirect(url_for('media.dashboard'))


@media_bp.route('/toggle/<int:media_id>', methods=['POST'])
@login_required
def toggle_visibility(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.user_id != current_user.id:
        abort(403)
    media_item.is_public = not media_item.is_public
    if not media_item.is_public:
        media_item.share_token = None
    db.session.commit()
    status = 'publiczny' if media_item.is_public else 'prywatny'
    flash(f'Plik jest teraz {status}.', 'info')
    return redirect(url_for('media.dashboard'))


@media_bp.route('/share/<int:media_id>', methods=['POST'])
@login_required
def share(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.user_id != current_user.id:
        abort(403)
    if media_item.share_token:
        media_item.share_token = None
        flash('Link udostepniania wylaczony.', 'info')
    else:
        media_item.share_token = uuid.uuid4().hex
        flash('Link udostepniania aktywny.', 'info')
    db.session.commit()
    return redirect(url_for('media.dashboard'))


@media_bp.route('/s/<share_token>')
def shared(share_token):
    media_item = Media.query.filter_by(share_token=share_token).first_or_404()
    mime = mimetypes.guess_type(media_item.filename)[0] or ''
    return render_template('player.html', media=media_item, format_size=format_size, mime=mime, share_token=share_token)
