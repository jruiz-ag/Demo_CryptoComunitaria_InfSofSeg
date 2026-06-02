"""
Utilidades criptográficas para firma y verificación de transacciones.
Usa ECDSA con curva SECP256R1 (equivalente a lo que usa Ethereum/Bitcoin modernos).
"""
import base64
import json
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

KEYS_DIR = os.path.join(os.path.dirname(__file__), 'keys')
os.makedirs(KEYS_DIR, exist_ok=True)


def generar_claves(username: str) -> None:
    """Genera par de claves ECDSA para un usuario y las guarda en disco."""
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

    priv_path = os.path.join(KEYS_DIR, f"{username}_private.pem")
    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

    pub_path = os.path.join(KEYS_DIR, f"{username}_public.pem")
    with open(pub_path, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ))


def cargar_clave_privada(username: str):
    path = os.path.join(KEYS_DIR, f"{username}_private.pem")
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def cargar_clave_publica(username: str):
    path = os.path.join(KEYS_DIR, f"{username}_public.pem")
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def obtener_clave_publica_pem(username: str) -> str:
    """Devuelve la clave pública en formato PEM como string (para mostrar en UI)."""
    pub = cargar_clave_publica(username)
    return pub.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def firmar_transaccion(username: str, datos: dict) -> str:
    """
    Firma un diccionario de datos con la clave privada del usuario.
    Devuelve la firma codificada en base64.
    Los datos se serializan con sort_keys=True para garantizar determinismo.
    """
    private_key = cargar_clave_privada(username)
    mensaje = json.dumps(datos, sort_keys=True).encode()
    firma_bytes = private_key.sign(mensaje, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(firma_bytes).decode()


def verificar_firma(username: str, datos: dict, firma_b64: str) -> bool:
    """
    Verifica que la firma corresponde al usuario y a los datos exactos.
    Devuelve True si es válida, False en cualquier otro caso.
    """
    try:
        public_key = cargar_clave_publica(username)
        mensaje = json.dumps(datos, sort_keys=True).encode()
        firma_bytes = base64.b64decode(firma_b64)
        public_key.verify(firma_bytes, mensaje, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
