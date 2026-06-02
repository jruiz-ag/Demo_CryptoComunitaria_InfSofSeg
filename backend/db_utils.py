import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'ledger.db')


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS transacciones')
        c.execute('''
            CREATE TABLE transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                remitente TEXT NOT NULL,
                destinatario TEXT NOT NULL,
                operacion TEXT NOT NULL,
                monto REAL NOT NULL,
                moneda TEXT NOT NULL,
                impuesto REAL DEFAULT 0,
                detalles TEXT,
                firma TEXT,
                firma_valida INTEGER
            )
        ''')
        conn.commit()


def registrar_transaccion(remitente, destinatario, operacion, monto, moneda,
                          impuesto, detalles, firma=None):
    """
    Registra una transacción en el ledger SQLite.
    Si se proporciona firma, la verifica antes de guardar y almacena el resultado.
    """
    firma_valida = None
    if firma:
        from crypto_utils import verificar_firma
        datos = {
            "remitente": remitente,
            "destinatario": destinatario,
            "monto": monto,
            "moneda": moneda
        }
        firma_valida = 1 if verificar_firma(remitente, datos, firma) else 0

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO transacciones
                (remitente, destinatario, operacion, monto, moneda,
                 impuesto, detalles, firma, firma_valida)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (remitente, destinatario, operacion, monto, moneda,
              impuesto, detalles, firma, firma_valida))
        conn.commit()


def obtener_ultimas_transacciones(limite=5, username=None):
    """
    ── SEGURIDAD 6: Filtrado de transacciones por usuario ────────────────────
    Cada usuario solo ve sus propias transacciones.
    El Estado (username=None) tiene acceso global para auditoría.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if username is None:
            c.execute('''
                SELECT fecha, remitente, destinatario, operacion,
                       monto, moneda, firma_valida
                FROM transacciones
                ORDER BY id DESC LIMIT ?
            ''', (limite,))
        else:
            c.execute('''
                SELECT fecha, remitente, destinatario, operacion,
                       monto, moneda, firma_valida
                FROM transacciones
                WHERE remitente = ? OR destinatario = ?
                ORDER BY id DESC LIMIT ?
            ''', (username, username, limite))

        return [dict(row) for row in c.fetchall()]
