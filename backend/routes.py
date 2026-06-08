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


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """
    Manejador perimetral de autenticación segura.
    Valida la existencia de parámetros, ejecuta la lógica DbC y previene la Fijación de Sesión.
    """
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash("Credenciales de acceso incompletas.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

    # Importamos la nueva función robusta con tolerancia a fallos criptográficos
    from auth_utils import verificar_credenciales_robusto
    import economy

    try:
        exito, rol, mensaje = verificar_credenciales_robusto(username, password, economy.USUARIOS_DB)
        
        if exito:
            # CONTRAMEDIDA SESSION FIXATION: Rotación completa de identificadores de sesión
            session.clear()
            
            session['username'] = username.lower()
            session['role'] = rol
            flash(f"Conexión criptográfica establecida. Bienvenido, {username.capitalize()}.", "success")
            return redirect(url_for(INDEX_ENDPOINT))
        
        # Si no tiene éxito, mostramos el motivo exacto (Bloqueo FSM o datos incorrectos)
        flash(mensaje, "error")
            
    except Exception as e:
        flash("Fallo crítico en el procesamiento del contrato lógicos de entrada.", "error")
        return redirect(url_for(INDEX_ENDPOINT))

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
