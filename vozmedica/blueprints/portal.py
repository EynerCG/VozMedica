"""Portal del paciente (/portal): sus citas y agendar una nueva."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..auth import exigir_paciente
from ..errores import Advertencia
from ..servicios import citas

bp = Blueprint("portal", __name__, url_prefix="/portal")
bp.before_request(exigir_paciente)


@bp.route("/")
def inicio():
    proxima, otras = citas.de_paciente(session["documento"])
    return render_template("portal/inicio.html", paciente=citas.paciente_portal(session["documento"]),
                           proxima=proxima, otras=otras)


@bp.route("/agendar", methods=["GET", "POST"])
def agendar():
    form = request.form
    if request.method == "POST":
        try:
            flash(citas.crear(session["documento"], form.get("fecha", ""), form.get("hora", ""),
                              form.get("motivo", "").strip()), "exito")
            return redirect(url_for("portal.inicio"))
        except Advertencia as e:
            flash(str(e), "advertencia")
    paciente = citas.paciente_portal(session["documento"])
    return render_template("portal/agendar.html", paciente=paciente, horarios=citas.horarios_de(paciente["profesional"]),
                           horario_txt=citas.texto_horario(paciente["profesional"]), form=form,
                           hoy_iso=date.today().isoformat())


@bp.route("/cita/<int:cid>/cancelar", methods=["POST"])
def cancelar_cita(cid):
    try:
        citas.cancelar(cid, documento=session["documento"])
        flash("Cita cancelada.", "info")
    except Advertencia as e:
        flash(str(e), "advertencia")
    return redirect(url_for("portal.inicio"))
