"""
Instancias compartidas de extensiones Flask.
Se inicializan aquí para poder importarlas en app.py y routes.py
sin crear dependencias circulares.
"""
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)
