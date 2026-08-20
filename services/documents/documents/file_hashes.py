import hashlib


def sha256_uploaded_file(uploaded):
    digest = hashlib.sha256()
    if hasattr(uploaded, "chunks"):
        for chunk in uploaded.chunks():
            digest.update(chunk)
    else:
        digest.update(uploaded.read())
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)
    return digest.hexdigest()
