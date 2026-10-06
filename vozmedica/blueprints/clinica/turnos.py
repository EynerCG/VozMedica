"""Entrega de turno (cada quien entrega sus pacientes y quien recibe confirma con su usuario) e historial."""

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso, usuario_actual
from ...errores import Advertencia
from ...servicios import reloj, turnos
from .. import volver
from . import bp


@bp.route("/entrega", methods=["GET", "POST"])
@requiere_permiso("entrega_turno")
def entrega():
    yo = usuario_actual()
    if request.method == "POST":
        f = request.form
        revisados = {int(k[4:]) for k in f if k.startswith("rev_") and k[4:].isdigit()}
        receptor_de = {int(k[9:]): v for k, v in f.items() if k.startswith("receptor_") and k[9:].isdigit()}
        nota_de = {int(k[5:]): v.strip() for k, v in f.items() if k.startswith("nota_") and k[5:].isdigit()}
        try:
            reciben = turnos.entregar(yo, revisados, receptor_de, nota_de, f.get("obs", "").strip())
        except Advertencia as e:
            flash(str(e), "advertencia")
        else:
            flash("Turno entregado a %s. Queda pendiente hasta que lo reciba%s con su usuario."
                  % (" y ".join(reciben), "n" if len(reciben) > 1 else ""), "exito")
            return redirect(url_for("clinica.entrega"))
    return render_template("clinica/entrega.html", form=request.form, **turnos.preparar(yo))


@bp.route("/entrega/<int:eid>/recibir", methods=["POST"])
@requiere_permiso("entrega_turno")
def recibir_turno(eid):
    try:
        e = turnos.recibir(eid, session["nombre"])
        flash("Recibió el turno de %s. Esos pacientes ahora están a su cargo." % e["entrega"], "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.entrega"))


@bp.route("/entrega/<int:eid>/anular", methods=["POST"])
@requiere_permiso("entrega_turno")
def anular_entrega(eid):
    try:
        turnos.anular(eid, session["nombre"])
        flash("Entrega anulada. Esos pacientes siguen a su cargo.", "info")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.entrega"))


@bp.route("/historial")
@requiere_permiso("ver_historial_turnos")
def historial():
    return render_template("clinica/historial.html", entregas=turnos.historial())


@bp.route("/reloj/adelantar", methods=["POST"])
def adelantar_reloj():
    """Solo para la demo: en la vida real el tiempo pasa solo."""
    if reloj.es_demo():
        destino = turnos.siguiente_hito()
        reloj.fijar(destino)
        flash("Reloj de la demo adelantado a las %s (turno %s)." % (destino.strftime("%H:%M"),
                                                                    turnos.nombre_turno(turnos.turno_de(destino))), "info")
    return volver("clinica.censo")
