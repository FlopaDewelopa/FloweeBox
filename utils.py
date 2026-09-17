import uuid


def check_magic_bytes(header):
    if len(header) < 4:
        return False
    if header[:3] == b'ID3':
        return True
    if header[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return True
    if header[:4] == b'\x1a\x45\xdf\xa3':
        return True
    if header[:4] == b'RIFF':
        return True
    if header[:4] == b'OggS':
        return True
    if header[:4] == b'fLaC':
        return True
    if len(header) >= 8 and header[4:8] == b'ftyp':
        return True
    return False


def validate_file(file_storage, allowed_extensions, allowed_mimes):
    filename = file_storage.filename
    if not filename or '.' not in filename:
        return False, None
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, None
    mime = file_storage.content_type or ''
    if mime and mime != 'application/octet-stream' and mime not in allowed_mimes:
        return False, None
    header = file_storage.read(16)
    file_storage.seek(0)
    if not check_magic_bytes(header):
        return False, None
    return True, ext


def generate_filename(ext):
    return f"{uuid.uuid4().hex}.{ext}"


def format_size(size_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
