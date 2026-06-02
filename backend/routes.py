from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import economy
from auth_utils import login_required, role_required
from extensions import limiter

auth_bp = Blueprint('auth', __name__)

INDEX_ENDPOINT = 'auth.index'


@auth_bp.route('/', methods=['GET'])
def index():
    if 'username' in session:
        basicas, bonificadas = economy.actualizar_y_obtener_saldo(session['username'])

        if session['role'] == 'state':
            ciudadanos = [k for k, v in economy.USUARIOS_DB.items() if v['role'] == 'citizen']
            return render_template('state.html',
                                   arcas_basicas=basicas,
                                   ciudadanos=ciudadanos,
                                   global_data=economy.obtener_estado_global())

        if session['role'] == 'commerce':
            return render_template('commerce.html',
                                   balance_basica=basicas,
                                   balance_bonificada=bonificadas)

        from crypto_utils import obtener_clave_publica_pem
        usuarios = [k for k in economy.USUARIOS_DB.keys() if k != session['username']]
        return render_template('citizen.html',
                               balance_basica=basicas,
                               balance_bonificada=bonificadas,
                               usuarios=usuarios,
                               clave_publica=obtener_clave_publica_pem(session['username']))

    return render_template('login.html')


@auth_bp.route('/login/<username>', methods=['GET'])
@limiter.limit("15 per minute")   # ── SEGURIDAD 4: evitar enumeración de usuarios
def login(username):
    """
    ── NOTA DE SEGURIDAD (DEMO ONLY) ─────────────────────────────────────────
    Login por clic sin contraseña, pensado para presentaciones.
    En producción se verificaría: bcrypt.checkpw(pw, user['password_hash'])
    ──────────────────────────────────────────────────────────────────────────
    """
    user = economy.USUARIOS_DB.get(username)
    if user:
        session['username'] = username
        session['role'] = user['role']
        return redirect(url_for(INDEX_ENDPOINT))

    flash("Usuario no encontrado en la base de datos de la demo.", "error")
    return redirect(url_for(INDEX_ENDPOINT))


@auth_bp.route('/transferir', methods=['POST'])
@login_required
@role_required('citizen')
@limiter.limit("20 per minute")   # ── SEGURIDAD 4: limitar transferencias
def transferir():
    destinatario = request.form.get('destinatario')
    tipo_moneda  = request.form.get('tipo_moneda')

    try:
        monto = round(float(request.form.get('monto')), 2)
    except (ValueError, TypeError):
        flash("Monto no válido.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

    # ── SEGURIDAD 7: validación de monto positivo en servidor ─────────────
    if monto <= 0:
        flash("El monto debe ser un valor positivo.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

    exito, mensaje = economy.ejecutar_transferencia(session['username'], destinatario, tipo_moneda, monto)
    flash(mensaje, "success" if exito else "error")
    return redirect(url_for(INDEX_ENDPOINT))


@auth_bp.route('/emitir', methods=['POST'])
@login_required
@role_required('state')
@limiter.limit("20 per minute")
def emitir():
    ciudadano = request.form.get('ciudadano')

    try:
        monto = round(float(request.form.get('monto')), 2)
    except (ValueError, TypeError):
        flash("Monto de emisión no válido.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

    # ── SEGURIDAD 7: validación de monto positivo en servidor ─────────────
    if monto <= 0:
        flash("El monto debe ser un valor positivo.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

    exito, mensaje = economy.emitir_bono_estatal(ciudadano, monto)
    flash(mensaje, "success" if exito else "error")
    return redirect(url_for(INDEX_ENDPOINT))


@auth_bp.route('/api/estado_en_vivo', methods=['GET'])
@login_required
def api_estado_en_vivo():
    # ── SEGURIDAD 6: cada usuario solo ve sus propias transacciones ────────
    username_filtro = None if session['role'] == 'state' else session['username']

    basicas, bonificadas = economy.actualizar_y_obtener_saldo(session['username'])

    datos = {
        "basicas": basicas,
        "bonificadas": bonificadas,
        "transacciones": economy.obtener_ultimas_transacciones(5, username=username_filtro)
    }

    if session['role'] == 'state':
        datos["global_data"] = economy.obtener_estado_global()

    return jsonify(datos)


@auth_bp.route('/liquidar', methods=['POST'])
@login_required
@role_required('commerce')
@limiter.limit("10 per minute")
def liquidar():
    exito, mensaje = economy.liquidar_impuestos(session['username'])
    flash(mensaje, "success" if exito else "error")
    return redirect(url_for(INDEX_ENDPOINT))


@auth_bp.route('/reset', methods=['POST'])
@login_required   # ── SEGURIDAD 3: solo usuarios autenticados pueden resetear
def reset():
    economy.resetear_sistema()
    flash("La demostración ha sido reiniciada.", "success")
    return redirect(url_for(INDEX_ENDPOINT))


@auth_bp.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for(INDEX_ENDPOINT))
