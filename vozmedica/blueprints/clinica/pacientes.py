"""Censo, ficha clinica, ingreso y alta de pacientes."""

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso, tiene_permiso as puede, usuario_actual
from ...errores import Advertencia
from ...servicios import camas, pacientes, turnos
from ...servicios.pacientes import ESTADOS
from . import bp


def _texto(campo):
    return request.form.get(campo, "").strip()


def _a_la_ficha(pid):
    # si el paciente ya no esta hospitalizado, la ficha redirige sola al censo
    return redirect(url_for("clinica.ficha", pid=pid))


@bp.route("/pacientes")
@requiere_permiso("ver_censo")
def censo():
    # quien trabaja por turnos (enfermeria y medicos) ve primero sus pacientes; puede cambiar a todo el servicio
    yo = usuario_actual()
    tipo = turnos.tipo_de(yo)
    con_pacientes = yo["turno"] is not None and puede("entrega_turno")
    mis = pacientes.censo(session["nombre"], tipo)[0] if con_pacientes else []
    mios = con_pacientes and request.args.get("ver", "mios") == "mios"
    lista, resumen = pacientes.censo(session["nombre"], tipo) if mios else pacientes.censo()
    return render_template("clinica/censo.html", lista=lista, resumen=resumen, con_pacientes=con_pacientes, mios=mios,
                           total_mios=len(mis), total=len(pacientes.todos()))


@bp.route("/paciente/<int:pid>")
@requiere_permiso("ver_ficha")
def ficha(pid):
    datos = pacientes.ficha(pid)
    if datos is None:
        flash("Ese paciente ya no está hospitalizado.", "advertencia")
        return redirect(url_for("clinica.censo"))
    return render_template("clinica/ficha.html", notas_entrega=turnos.notas_de_entrega(pid), **datos)


@bp.route("/pacientes/nuevo", methods=["GET", "POST"])
@requiere_permiso("editar_ficha")
def registrar_paciente():
    if request.method == "GET":
        return _form_ingreso({})
    try:
        pid = pacientes.registrar(_texto("documento"), _texto("cama"), _texto("nombre"), _texto("edad"),
                                  _texto("diagnostico"), _texto("alergias"), _texto("signos"), _texto("medico"),
                                  _texto("enfermera"), session["nombre"])
    except Advertencia as e:
        flash(str(e), "advertencia")
        return _form_ingreso(request.form)
    flash("Paciente %s registrado en la cama %s." % (_texto("nombre"), _texto("cama")), "exito")
    return _a_la_ficha(pid)


def _form_ingreso(form):
    # quien ingresa queda por defecto como tratante (si es medico) o como enfermera a cargo
    enfermeras = pacientes.enfermeras_de_turno()
    if not form:
        form = {"medico": session["nombre"] if puede("ordenes_medicas") else "",
                "enfermera": session["nombre"] if session["nombre"] in enfermeras else ""}
    return render_template("clinica/paciente_nuevo.html", form=form, camas=camas.disponibles(),
                           medicos=pacientes.medicos_tratantes(), enfermeras=enfermeras)


@bp.route("/paciente/<int:pid>/asumir", methods=["POST"])
@requiere_permiso("ordenes_medicas")
def asumir_paciente(pid):
    try:
        p = pacientes.asumir(pid, session["nombre"])
        flash("Ahora usted es el médico tratante de %s." % p["nombre"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/paciente/<int:pid>/estado", methods=["POST"])
@requiere_permiso("editar_ficha")
def cambiar_estado(pid):
    estado = request.form.get("estado")
    try:
        pacientes.cambiar_estado(pid, estado, session["nombre"])
        flash("Estado actualizado a %s." % ESTADOS[estado], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/paciente/<int:pid>/signos", methods=["POST"])
@requiere_permiso("editar_ficha")
def actualizar_signos(pid):
    try:
        pacientes.actualizar_signos(pid, _texto("signos"), session["nombre"])
        flash("Signos vitales registrados.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/paciente/<int:pid>/alta", methods=["POST"])
@requiere_permiso("ordenes_medicas")
def dar_alta(pid):
    try:
        p = pacientes.dar_alta(pid, session["nombre"])
        flash("%s dado de alta. La cama %s queda libre y su historia clínica se conserva." % (p["nombre"], p["cama"]), "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.censo"))


@bp.route("/paciente/<int:pid>/medicamento", methods=["POST"])
@requiere_permiso("ordenes_medicas")
def agregar_medicamento(pid):
    try:
        n = pacientes.programar_medicamento(pid, _texto("fecha"), _texto("hora"), _texto("nombre"), session["nombre"],
                                            _texto("repetir") or "0", _texto("dias") or "1",
                                            bool(request.form.get("confirmar_alergia")))
        flash("%s formulado: %s." % (_texto("nombre"), "1 dosis a las %s" % _texto("hora") if n == 1
                                     else "%d dosis desde las %s" % (n, _texto("hora"))), "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/medicamento/<int:mid>/registrar", methods=["POST"])
@requiere_permiso("administrar_medicamentos")
def registrar_medicamento(mid):
    pid = pacientes.paciente_de_medicamento(mid)
    try:
        m = pacientes.registrar_medicamento(mid, session["nombre"])
        flash(m["nombre"] + " registrado como administrado.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid) if pid else redirect(url_for("clinica.censo"))


@bp.route("/medicamento/<int:mid>/no-aplicada", methods=["POST"])
@requiere_permiso("administrar_medicamentos")
def no_aplicar_medicamento(mid):
    pid = pacientes.paciente_de_medicamento(mid)
    motivo = _texto("motivo")
    if motivo == "Otro":
        motivo = _texto("detalle")
    try:
        m = pacientes.no_aplicar(mid, session["nombre"], motivo)
        flash("%s registrado como NO aplicado." % m["nombre"], "info")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid) if pid else redirect(url_for("clinica.censo"))


@bp.route("/medicamento/<int:mid>/suspender", methods=["POST"])
@requiere_permiso("ordenes_medicas")
def suspender_medicamento(mid):
    pid = pacientes.paciente_de_medicamento(mid)
    try:
        m, n = pacientes.suspender(mid, session["nombre"], _texto("motivo"))
        flash("%s suspendido (%d dosis)." % (m["nombre"], n), "info")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid) if pid else redirect(url_for("clinica.censo"))


@bp.route("/paciente/<int:pid>/cama", methods=["POST"])
@requiere_permiso("editar_ficha")
def cambiar_cama(pid):
    try:
        anterior = pacientes.cambiar_cama(pid, _texto("cama"), session["nombre"])
        flash("Paciente trasladado de la cama %s a la %s." % (anterior, _texto("cama")), "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/pendiente/<int:did>/marcar", methods=["POST"])
@requiere_permiso("editar_ficha")
def marcar_pendiente(did):
    try:
        return _a_la_ficha(pacientes.alternar_pendiente(did, session["nombre"]))
    except Advertencia as e:
        flash(str(e), "advertencia")
        return redirect(url_for("clinica.censo"))


@bp.route("/paciente/<int:pid>/pendiente", methods=["POST"])
@requiere_permiso("editar_ficha")
def agregar_pendiente(pid):
    try:
        pacientes.agregar_pendiente(pid, _texto("texto"))
        flash("Pendiente agregado.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)


@bp.route("/paciente/<int:pid>/novedad", methods=["POST"])
@requiere_permiso("editar_ficha")
def agregar_novedad(pid):
    try:
        pacientes.agregar_novedad(pid, _texto("texto"), session["nombre"])
        flash("Novedad guardada.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return _a_la_ficha(pid)
