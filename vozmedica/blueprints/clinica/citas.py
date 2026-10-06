"""Citas virtuales del medico y agenda del servicio (recepcion)."""

from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from ...auth import requiere_permiso
from ...errores import Advertencia
from ...servicios import citas
from . import bp


@bp.route("/citas", endpoint="citas")
@requiere_permiso("atender_citas")
def citas_vista():
    return render_template("clinica/citas.html", citas=citas.de_profesional(session["nombre"]))


@bp.route("/cita/<int:cid>/atendida", methods=["POST"])
@requiere_permiso("atender_citas")
def cita_atendida(cid):
    try:
        citas.marcar_atendida(cid, session["nombre"])
        flash("Cita marcada como atendida.", "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.citas"))


@bp.route("/agenda")
@requiere_permiso("agenda_servicio")
def agenda():
    ver = request.args.get("ver", "programadas")
    return render_template("clinica/agenda.html", citas=citas.agenda(solo_programadas=(ver == "programadas")),
                           ver=ver, horarios=citas.HORARIOS, pacientes=citas.pacientes_portal(),
                           horario_de={p["profesional"]: citas.texto_horario(p["profesional"]) for p in citas.pacientes_portal()},
                           hoy_iso=date.today().isoformat())


@bp.route("/agenda/agendar", methods=["POST"])
@requiere_permiso("agenda_servicio")
def agenda_agendar():
    f = request.form
    try:
        flash(citas.crear(f.get("documento", ""), f.get("fecha", ""), f.get("hora", ""), f.get("motivo", "").strip()), "exito")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.agenda"))


@bp.route("/agenda/<int:cid>/cancelar", methods=["POST"])
@requiere_permiso("agenda_servicio")
def agenda_cancelar(cid):
    try:
        citas.cancelar(cid)
        flash("Cita cancelada.", "info")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("clinica.agenda"))
