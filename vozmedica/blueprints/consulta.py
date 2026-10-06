"""Consulta virtual (/cita): chat y videollamada. La usan el paciente y el profesional."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .. import auth
from ..servicios import citas

bp = Blueprint("consulta", __name__, url_prefix="/cita")


@bp.before_request
def exigir_sesion():
    if auth.es_paciente():
        return None
    respuesta = auth.exigir_personal()
    if respuesta:
        return respuesta
    if not auth.tiene_permiso("atender_citas"):
        flash("Su rol no tiene acceso a esa sección. Le llevamos a su pantalla de inicio.", "advertencia")
        return redirect(auth.inicio_personal())
    return None


def _puede_ver(c):
    # confidencialidad: el chat solo lo ven el paciente y el profesional de esa cita
    if c is None:
        return False
    if auth.es_paciente():
        return c["documento"] == session.get("documento")
    return c["profesional"] == session.get("nombre")


@bp.route("/<int:cid>/chat")
def chat(cid):
    c = citas.obtener(cid)
    if not _puede_ver(c):
        flash("No encontramos esa cita.", "advertencia")
        return redirect(url_for("portal.inicio" if auth.es_paciente() else "clinica.citas"))
    return render_template("consulta/chat.html", c=c, mensajes=citas.mensajes(cid))


@bp.route("/<int:cid>/mensaje", methods=["POST"])
def enviar_mensaje(cid):
    if _puede_ver(citas.obtener(cid)):
        citas.enviar_mensaje(cid, session["nombre"], request.form.get("texto", "").strip())
    return redirect(url_for("consulta.chat", cid=cid))
