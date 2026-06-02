import os
from flask import Flask
from flask_talisman import Talisman
from extensions import csrf, limiter
from routes import auth_bp

ruta_frontend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, template_folder=ruta_frontend)

# ── SEGURIDAD 1: secret_key estable desde variable de entorno ──────────────
# En producción: export SECRET_KEY="clave-larga-y-aleatoria"
app.secret_key = os.environ.get('SECRET_KEY', 'demo-secret-key-change-in-production-!@#$%')

# ── Cookies: desactivar Secure en local (HTTP), activarlo en producción ────
# Con Secure=True el navegador ignora la cookie en HTTP y la sesión no persiste
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_SECURE']   = IS_PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True           # siempre: JS no puede leer la cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ── SEGURIDAD 2: Protección CSRF en todos los formularios POST ─────────────
csrf.init_app(app)

# ── SEGURIDAD 3: Cabeceras de seguridad HTTP ───────────────────────────────
# force_https=False y strict_transport_security=False para demo local sin TLS
SELF_POLICY = "'self'"
csp = {
    'default-src': "SELF_POLICY",
    'script-src':  ["SELF_POLICY", "'unsafe-inline'"],
    'style-src':   ["SELF_POLICY", "'unsafe-inline'", 'fonts.googleapis.com'],
    'font-src':    ['fonts.gstatic.com', 'fonts.googleapis.com'],
    'img-src':     ["SELF_POLICY", 'data:'],
}
Talisman(
    app,
    force_https=False,
    strict_transport_security=False,
    session_cookie_secure=False,   # sobreescribe el forzado de Talisman para demo local
    content_security_policy=csp,
    referrer_policy='strict-origin-when-cross-origin',
)

# ── SEGURIDAD 4: Rate limiting ─────────────────────────────────────────────
limiter.init_app(app)

app.register_blueprint(auth_bp)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode, port=5000)
