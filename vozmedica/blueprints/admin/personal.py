"""Personal: registrar, cambiar de rol o turno, desactivar y reactivar empleados; roles y permisos."""

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso
from ...errores import Advertencia
from ...permisos import agrupados
from ...servicios import citas, personal
from . import bp


@bp.route("/personal", endpoint="personal")
@requiere_permiso("admin_personal")
def personal_vista():
    return render_template("admin/personal.html", empleados=personal.listar(), roles=personal.roles(),
                           pacientes=citas.pacientes_portal(), medicos=personal.medicos(), turnos=personal.TURNOS)


@bp.route("/personal/nuevo", methods=["POST"])
@requiere_permiso("admin_personal")
def registrar_empleado():
    nombre = request.form.get("nombre", "").strip()
    try:
        personal.registrar(nombre, request.form.get("documento", "").strip(), request.form.get("rol", ""),
                           request.form.get("turno", ""))
        flash("%s registrado. Ya puede ingresar a la plataforma." % nombre, "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.personal"))


@bp.route("/personal/<int:eid>/rol", methods=["POST"])
@requiere_permiso("admin_personal")
def cambiar_rol(eid):
    try:
        empleado = personal.cambiar_rol(eid, request.form.get("rol", ""), session["personal_id"])
        flash("Rol de %s actualizado." % empleado["nombre"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.personal"))


@bp.route("/personal/<int:eid>/turno", methods=["POST"])
@requiere_permiso("admin_personal")
def cambiar_turno(eid):
    try:
        empleado = personal.cambiar_turno(eid, request.form.get("turno", ""))
        flash("Turno de %s actualizado." % empleado["nombre"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.personal"))


@bp.route("/personal/<int:eid>/desactivar", methods=["POST"])
@requiere_permiso("admin_personal")
def desactivar_empleado(eid):
    try:
        empleado = personal.desactivar(eid, session["personal_id"])
        flash("%s fue desactivado(a): ya no puede ingresar. Sus registros clínicos se conservan." % empleado["nombre"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.personal"))


@bp.route("/personal/<int:eid>/reactivar", methods=["POST"])
@requiere_permiso("admin_personal")
def reactivar_empleado(eid):
    try:
        empleado = personal.reactivar(eid)
        flash("%s fue reactivado(a)." % empleado["nombre"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.personal"))


@bp.route("/portal/<doc>/profesional", methods=["POST"])
@requiere_permiso("admin_personal")
def asignar_profesional(doc):
    profesional = request.form.get("profesional", "")
    try:
        resultado = personal.asignar_profesional(doc, profesional)
    except Advertencia as e:
        flash(str(e), "advertencia")
    else:
        if resultado:
            paciente, movidas, canceladas = resultado
            texto = "%s ahora está asignado(a) a %s." % (paciente["nombre"], profesional)
            if movidas:
                texto += " %d cita(s) programada(s) pasaron a su nuevo profesional." % movidas
            if canceladas:
                texto += (" %d cita(s) quedaban fuera del turno del nuevo profesional y se cancelaron: "
                          "recepción debe reprogramarlas." % canceladas)
            flash(texto, "advertencia" if canceladas else "exito")
    return redirect(url_for("admin.personal"))


@bp.route("/roles", methods=["GET", "POST"])
@requiere_permiso("admin_personal")
def roles():
    if request.method == "POST":
        # cada casilla se llama "rol:permiso"
        personal.guardar_permisos({tuple(k.split(":", 1)) for k in request.form if ":" in k})
        flash("Permisos guardados. Los cambios aplican de inmediato.", "exito")
        return redirect(url_for("admin.roles"))
    actuales, cuantos = personal.matriz()
    return render_template("admin/roles.html", roles=personal.roles(), grupos=agrupados(),
                           actuales=actuales, cuantos=cuantos)
