"""Recursos vistos por el personal clinico: disponibilidad, registrar uso y reportar faltantes."""

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso
from ...errores import Advertencia
from ...servicios import camas, recursos
from . import bp


@bp.route("/recursos", endpoint="recursos")
@requiere_permiso("usar_recursos")
def recursos_vista():
    tipo = request.args.get("tipo", "Medicamento")
    if tipo not in dict(recursos.TIPOS_RECURSO):
        tipo = "Medicamento"
    filas = recursos.todos()
    conteo = recursos.contar_por_tipo(filas)
    conteo["Camilla"] += 1   # la tarjeta de camas libres
    return render_template("clinica/recursos.html", filas=filas, tipo=tipo, tipos=recursos.TIPOS_RECURSO,
                           conteo=conteo, abiertas=recursos.ids_con_solicitud_abierta(),
                           camas_libres=camas.disponibles())


@bp.route("/recursos/<int:rid>/uso", methods=["POST"])
@requiere_permiso("usar_recursos")
def usar_recurso(rid):
    tipo = None
    try:
        r, cambio, _ = recursos.mover(rid, request.form.get("cantidad", ""), False,
                                      request.form.get("motivo", "").strip() or "Uso en el servicio",
                                      session["nombre"])
        tipo = r["tipo"]
        flash("Uso registrado: %d de %s. Quedan %d." % (-cambio, r["nombre"], r["cantidad"] + cambio), "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
        r = recursos.obtener(rid)
        tipo = r["tipo"] if r else None
    return redirect(url_for("clinica.recursos", tipo=tipo))


@bp.route("/recursos/<int:rid>/faltante", methods=["POST"])
@requiere_permiso("usar_recursos")
def reportar_faltante(rid):
    try:
        r, creada = recursos.reportar_faltante(rid, session["nombre"], request.form.get("nota", "").strip())
    except Advertencia as e:
        flash(str(e), "advertencia")
        return redirect(url_for("clinica.recursos"))
    if creada:
        flash("Faltante de %s reportado a administración." % r["nombre"], "exito")
    else:
        flash("Ya hay un reporte abierto de %s. Administración ya está avisada." % r["nombre"], "info")
    return redirect(url_for("clinica.recursos", tipo=r["tipo"]))
