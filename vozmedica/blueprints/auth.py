"""Ingreso, salida y reinicio de los datos de prueba."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .. import auth, db
from ..servicios import citas, personal

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET", "POST"])
def ingreso():
    if auth.es_paciente():
        return redirect(url_for("portal.inicio"))
    if auth.usuario_actual():
        return redirect(auth.inicio_personal())

    if request.method == "POST":
        if request.form.get("tipo") == "personal":
            fila = personal.obtener(request.form.get("personal_id", type=int))
            if fila and fila["activo"]:
                auth.iniciar_sesion_personal(fila)
                return redirect(auth.inicio_personal())
            flash("Seleccione su nombre en la lista para ingresar.", "advertencia")
        else:
            fila = citas.paciente_portal(request.form.get("documento", "").strip())
            if fila:
                auth.iniciar_sesion_paciente(fila)
                return redirect(url_for("portal.inicio"))
            flash("No encontramos ese documento. Para la demo use 1001, 1002 o 1003.", "advertencia")

    clinicos, admins = personal.para_ingreso()
    return render_template("auth/ingreso.html", clinicos=clinicos, admins=admins)


@bp.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("auth.ingreso"))


@bp.route("/reiniciar", methods=["POST"])
def reiniciar():
    db.crear_base()
    session.clear()
    flash("Datos de prueba reiniciados.", "exito")
    return redirect(url_for("auth.ingreso"))


@bp.route("/sin-acceso")
def sin_acceso():
    respuesta = auth.exigir_personal()
    if respuesta:
        return respuesta
    return render_template("auth/sin_acceso.html")
