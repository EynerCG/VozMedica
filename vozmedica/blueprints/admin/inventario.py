"""Inventario: resumen, existencias, movimientos y solicitudes de enfermeria."""

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso
from ...errores import Advertencia
from ...servicios import recursos
from .. import volver
from . import bp


@bp.route("/")
@requiere_permiso("admin_inventario")
def resumen():
    return render_template("admin/resumen.html", **recursos.resumen())


@bp.route("/recursos", endpoint="recursos")
@requiere_permiso("admin_inventario")
def recursos_vista():
    tipo = request.args.get("tipo", "")
    solo_bajos = request.args.get("bajos") == "1"
    return render_template("admin/recursos.html", filas=recursos.todos(tipo, solo_bajos), tipo=tipo,
                           solo_bajos=solo_bajos, tipos=recursos.TIPOS_RECURSO)


@bp.route("/recursos/<int:rid>/movimiento", methods=["POST"])
@requiere_permiso("admin_inventario")
def mover(rid):
    entrada = request.form.get("accion") == "entrada"
    try:
        r, cambio, cerradas = recursos.mover(rid, request.form.get("cantidad", ""), entrada,
                                             request.form.get("motivo", "").strip(), session["nombre"])
        texto = "%s: %+d. Quedan %d." % (r["nombre"], cambio, r["cantidad"] + cambio)
        if cerradas:
            texto += " La solicitud de enfermería quedó atendida."
        flash(texto, "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return volver("admin.recursos")


@bp.route("/recursos/<int:rid>/editar", methods=["POST"])
@requiere_permiso("admin_inventario")
def editar_recurso(rid):
    try:
        recursos.editar(rid, request.form.get("minimo", ""), request.form.get("ubicacion", "").strip())
        flash("Recurso actualizado.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return volver("admin.recursos")


@bp.route("/recursos/nuevo", methods=["POST"])
@requiere_permiso("admin_inventario")
def nuevo_recurso():
    f = request.form
    nombre = f.get("nombre", "").strip()
    try:
        recursos.crear(f.get("tipo"), nombre, f.get("cantidad", ""), f.get("minimo", ""), f.get("ubicacion", "").strip())
        flash("Recurso %s agregado." % nombre, "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("admin.recursos"))


@bp.route("/movimientos")
@requiere_permiso("admin_inventario")
def movimientos():
    tipo = request.args.get("tipo", "")
    return render_template("admin/movimientos.html", movimientos=recursos.movimientos(tipo), tipo=tipo,
                           tipos=recursos.TIPOS_RECURSO)


@bp.route("/solicitudes")
@requiere_permiso("admin_inventario")
def solicitudes():
    return render_template("admin/solicitudes.html", solicitudes=recursos.solicitudes())


@bp.route("/solicitudes/<int:sid>/atendida", methods=["POST"])
@requiere_permiso("admin_inventario")
def solicitud_atendida(sid):
    recursos.marcar_solicitud_atendida(sid)
    flash("Solicitud marcada como atendida.", "exito")
    return volver("admin.solicitudes")
