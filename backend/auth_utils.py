import bcrypt
import hmac
import hashlib
import icontract
import time
from functools import wraps
from typing import Callable, Any
from flask import session, redirect, url_for, abort

# Secreto del servidor indispensable para validar los hashes de config.json
PEPPER_KEY = b"Clave_Secreta_Del_Sistema_UMA_2026_ISS"
MAX_INTENTOS = 10
TIEMPO_BLOQUEO_SEG = 5

def login_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if 'username' not in session:
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if session.get('role') != required_role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ── CAPA INTEGRADA AVANZADA: MÁQUINA DE ESTADOS, PEPPER Y ANTI-TIMING ATTACKS ──

@icontract.require(lambda username: len(username) >= 3 and len(username) <= 32, "Contrato roto: Longitud inválida.")
@icontract.require(lambda password_plana: len(password_plana) > 0, "Contrato roto: Clave vacía.")
def verificar_credenciales_robusto(username: str, password_plana: str, usuarios_db: dict) -> tuple[bool, str, str]:
    """
    Valida identidades mitigando ataques de canal lateral por tiempo y inyectando enlace Pepper.
    """
    hora_inicio = time.time()
    user_key = username.lower()
    user_entry = usuarios_db.get(user_key)
    
    # Prevenir enumeración de usuarios inyectando un registro fantasma idéntico si no existe
    if not user_entry:
        user_entry = {
            "password_hash": "$2b$12$eImiTxKlq91q91q91q91q9ve8as7d8a7sd8a7sd8a7sd8a7sd8a7s", 
            "role": "guest",
            "failed_attempts": 0,
            "lockout_until": 0.0
        }
    
    user_entry.setdefault("failed_attempts", 0)
    user_entry.setdefault("lockout_until", 0.0)
    
    ahora = time.time()
    
    # Control de bloqueo temporal por fuerza bruta
    if ahora < user_entry["lockout_until"]:
        _ejecutar_retardo_isometrico(hora_inicio, 0.4)
        return False, "guest", f"Cuenta bloqueada temporalmente. Espere {int(user_entry['lockout_until'] - ahora)}s."
    
    stored_hash = user_entry.get("password_hash", "").encode('utf-8')
    
    # INTENTO A: Verificación con el nuevo estándar de protección Pepper (HMAC + Bcrypt)
    password_con_pepper = hmac.new(PEPPER_KEY, password_plana.encode('utf-8'), hashlib.sha256).digest()
    credenciales_validas = bcrypt.checkpw(password_con_pepper, stored_hash)
    
    # INTENTO B: Fallback de migración (Por si el hash fuese el plano antiguo)
    if not credenciales_validas:
        credenciales_validas = bcrypt.checkpw(password_plana.encode('utf-8'), stored_hash)
    
    if credenciales_validas and user_key in usuarios_db:
        user_entry["failed_attempts"] = 0
        user_entry["lockout_until"] = 0.0
        _ejecutar_retardo_isometrico(hora_inicio, 0.4)
        return True, user_entry.get("role", "guest"), "Autenticación correcta."
    else:
        if user_key in usuarios_db:
            usuarios_db[user_key]["failed_attempts"] += 1
            if usuarios_db[user_key]["failed_attempts"] >= MAX_INTENTOS:
                usuarios_db[user_key]["lockout_until"] = ahora + TIEMPO_BLOQUEO_SEG
                usuarios_db[user_key]["failed_attempts"] = 0
        
        _ejecutar_retardo_isometrico(hora_inicio, 0.4)
        return False, "guest", "Acceso denegado: Credenciales inválidas."

def _ejecutar_retardo_isometrico(hora_inicio: float, tiempo_objetivo: float):
    tiempo_transcurrido = time.time() - hora_inicio
    tiempo_restante = tiempo_objetivo - tiempo_transcurrido
    if tiempo_restante > 0:
        time.sleep(tiempo_restante)