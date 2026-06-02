import time
import threading
from db_utils import init_db, registrar_transaccion, obtener_ultimas_transacciones
import os
import json

# Configuración centralizada (evita "Magic Numbers")
TASA_DEGRADACION = 0.0001

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

# ── SEGURIDAD 5: Lock global para prevenir race conditions ─────────────────
_db_lock = threading.Lock()


def normalizar_datos(data):
    ahora = time.time()
    for user_data in data.values():
        if "basicas" in user_data and isinstance(user_data["basicas"], list):
            for lote in user_data["basicas"]:
                lote["timestamp"] = ahora
    return data


def cargar_configuracion():
    with open(CONFIG_PATH, 'r') as f:
        data = json.load(f)
    return normalizar_datos(data['usuarios'])


USUARIOS_DB = cargar_configuracion()

init_db()


def _inicializar_claves():
    """Genera claves ECDSA para cada usuario si aún no existen."""
    from crypto_utils import KEYS_DIR, generar_claves
    for username in USUARIOS_DB.keys():
        priv = os.path.join(KEYS_DIR, f"{username}_private.pem")
        if not os.path.exists(priv):
            generar_claves(username)


_inicializar_claves()


def resetear_sistema():
    global USUARIOS_DB
    with _db_lock:
        USUARIOS_DB = cargar_configuracion()
        init_db()
    # Las claves persisten entre resets (son identidades, no saldos)


def actualizar_y_obtener_saldo(username):
    user = USUARIOS_DB.get(username)
    if not user or user["role"] == "state":
        return (0.0, 0.0) if not user else (0.0, user["bonificadas"])

    ahora = time.time()
    total_basicas = 0.0

    for lote in user["basicas"]:
        if lote["monto"] <= 0:
            continue
        elapsed = ahora - lote["timestamp"]
        if elapsed > 0:
            monto_original = lote["monto"]
            degradacion = monto_original * (1 - (1 - TASA_DEGRADACION) ** (elapsed / 3))
            lote["monto"] -= degradacion
            lote["timestamp"] = ahora
            USUARIOS_DB["estado"]["bonificadas"] += degradacion
        total_basicas += lote["monto"]

    user["basicas"] = [l for l in user["basicas"] if l["monto"] > 0.0001]
    return round(total_basicas, 2), round(user["bonificadas"], 2)


def obtener_estado_global():
    with _db_lock:
        for username in USUARIOS_DB.keys():
            actualizar_y_obtener_saldo(username)

        estado_sistema = {}
        total_basicas = 0.0
        total_bonificadas = 0.0

        for username, data in USUARIOS_DB.items():
            saldo_basicas = sum(lote["monto"] for lote in data["basicas"])
            saldo_bonificadas = data["bonificadas"]
            estado_sistema[username] = {
                "role": data["role"],
                "basicas": round(saldo_basicas, 2),
                "bonificadas": round(saldo_bonificadas, 2)
            }
            total_basicas += saldo_basicas
            total_bonificadas += saldo_bonificadas

    return {
        "usuarios": estado_sistema,
        "total_basicas": round(total_basicas, 2),
        "total_bonificadas": round(total_bonificadas, 2),
        "total_circulante": round(total_basicas + total_bonificadas, 2)
    }


def ejecutar_transferencia(remitente, destinatario, tipo_moneda, monto):
    if destinatario not in USUARIOS_DB or remitente == destinatario:
        return False, "Destinatario no válido."
    if monto <= 0:
        return False, "El monto debe ser positivo."

    with _db_lock:
        if tipo_moneda == "bonificadas":
            return _transferir_bonificadas(remitente, destinatario, monto)
        return _transferir_basicas(remitente, destinatario, monto)


def _construir_datos_firma(remitente, destinatario, monto, moneda):
    """Construye el diccionario canónico que se firma."""
    return {
        "remitente": remitente,
        "destinatario": destinatario,
        "monto": monto,
        "moneda": moneda
    }


def _transferir_bonificadas(remitente, destinatario, monto):
    from crypto_utils import firmar_transaccion
    if USUARIOS_DB[remitente]["bonificadas"] < monto:
        return False, "Saldo insuficiente."

    datos = _construir_datos_firma(remitente, destinatario, monto, "bonificadas")
    firma = firmar_transaccion(remitente, datos)

    USUARIOS_DB[remitente]["bonificadas"] -= monto
    USUARIOS_DB[destinatario]["basicas"].append({"monto": float(monto), "timestamp": time.time()})

    registrar_transaccion(remitente, destinatario, "TRANSFERENCIA P2P",
                          monto, "bonificadas", 0.0, "Pérdida de firma", firma)
    return True, f"Transferencia completada. {destinatario} recibe {monto} monedas básicas."


def _transferir_basicas(remitente, destinatario, monto):
    from crypto_utils import firmar_transaccion
    saldo_basicas, _ = actualizar_y_obtener_saldo(remitente)
    if saldo_basicas < monto:
        return False, "Saldo insuficiente."

    datos = _construir_datos_firma(remitente, destinatario, monto, "basicas")
    firma = firmar_transaccion(remitente, datos)

    _procesar_fifo(remitente, monto)
    USUARIOS_DB[destinatario]["basicas"].append({"monto": float(monto), "timestamp": time.time()})

    registrar_transaccion(remitente, destinatario, "TRANSFERENCIA P2P",
                          monto, "basicas", 0.0, "Transferencia estándar", firma)
    return True, f"Transferencia de {monto} monedas básicas a {destinatario} firmada ✓"


def _procesar_fifo(remitente, monto):
    monto_restante = monto
    USUARIOS_DB[remitente]["basicas"].sort(key=lambda x: x["timestamp"])
    for lote in USUARIOS_DB[remitente]["basicas"]:
        if monto_restante <= 0:
            break
        if lote["monto"] <= monto_restante:
            monto_restante -= lote["monto"]
            lote["monto"] = 0
        else:
            lote["monto"] -= monto_restante
            monto_restante = 0
    USUARIOS_DB[remitente]["basicas"] = [l for l in USUARIOS_DB[remitente]["basicas"] if l["monto"] > 0]


def emitir_bono_estatal(ciudadano, monto):
    from crypto_utils import firmar_transaccion
    if ciudadano not in USUARIOS_DB or USUARIOS_DB[ciudadano]["role"] != "citizen":
        return False, "El destinatario debe ser un ciudadano válido."
    if monto <= 0:
        return False, "El monto debe ser positivo."

    with _db_lock:
        if USUARIOS_DB["estado"]["bonificadas"] < monto:
            return False, "El Tesoro Público no tiene suficientes monedas para esta emisión."

        datos = _construir_datos_firma("estado", ciudadano, monto, "bonificadas")
        firma = firmar_transaccion("estado", datos)

        actualizar_y_obtener_saldo(ciudadano)
        USUARIOS_DB["estado"]["bonificadas"] -= monto
        USUARIOS_DB[ciudadano]["bonificadas"] += monto

    registrar_transaccion("estado", ciudadano, "EMISIÓN ESTATAL",
                          monto, "bonificadas", 0.0,
                          "Inyección de recompensa por buenas acciones", firma)
    return True, f"Se han transferido {monto} monedas bonificadas a {ciudadano}."


def liquidar_impuestos(comercio):
    from crypto_utils import firmar_transaccion
    if comercio not in USUARIOS_DB or USUARIOS_DB[comercio]["role"] != "commerce":
        return False, "Solo los comercios locales pueden liquidar."

    with _db_lock:
        saldo_actual, _ = actualizar_y_obtener_saldo(comercio)
        if saldo_actual <= 0:
            return False, "No hay tokens básicos en caja para liquidar."

        datos = _construir_datos_firma(comercio, "estado", saldo_actual, "basicas")
        firma = firmar_transaccion(comercio, datos)

        USUARIOS_DB["estado"]["bonificadas"] += saldo_actual
        USUARIOS_DB[comercio]["basicas"] = []

    registrar_transaccion(comercio, "estado", "LIQUIDACIÓN FISCAL",
                          saldo_actual, "basicas", 0.0,
                          "Conversión de depósito básico a tesoro bonificado", firma)
    return True, f"Se han liquidado {saldo_actual} 🪙. El Estado las ha firmado y convertido en su reserva ⭐."
