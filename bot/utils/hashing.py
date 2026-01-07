import hashlib


def sha256_hash(text: str) -> str:
    """Вычисляет SHA256 хеш от нормализованного текста."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

