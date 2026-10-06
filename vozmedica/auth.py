"""Sesion, permisos y control de acceso.

- exigir_personal / exigir_paciente: se usan como before_request de cada blueprint.
- @requiere_permiso("..."): protege cada vista del personal segun su rol.
"""

import functools

from flask import flash, g, redirect, request, session, url_for

from . import permisos
from .servicios import personal, recursos, reloj, turnos
from .servicios.reloj import hora_actual
from .utils import iniciales


def es_paciente():
    return session.get("rol") == "paciente"


def usuario_actual():
    """Fila del empleado que inicio sesion (None si es paciente o no hay sesion)."""
    if session.get("rol") != "personal":
        return None
    if "usuario" not in g:
        fila = personal.obtener(session.get("personal_id"))
        g.usuario = fila if fila and fila["activo"] else None   # un usuario desactivado pierde el acceso
    return g.usuario


def permisos_usuario():
    # Se leen en cada peticion: si el administrador cambia un permiso, aplica de inmediato
    if "permisos" not in g:
        u = usuario_actual()
        g.permisos = personal.permisos_de_rol(u["rol"]) if u else set()
    return g.permisos


def tiene_permiso(permiso):
    return permiso in permisos_usuario()


def inicio_personal():
    """URL de la primera pantalla a la que el empleado tiene acceso."""
    for ruta, permiso in permisos.INICIOS:
        if tiene_permiso(permiso):
            return url_for(ruta)
    return url_for("auth.sin_acceso")


def iniciar_sesion_personal(fila):
    session.clear()
    session["rol"] = "personal"
    session["personal_id"] = fila["id"]
    session["nombre"] = fila["nombre"]
    g.pop("usuario", None)
    g.pop("permisos", None)


def iniciar_sesion_paciente(fila):
    session.clear()
    session["rol"] = "paciente"
    session["nombre"] = fila["nombre"]
    session["documento"] = fila["documento"]


# ---------- Guardas ----------

def exigir_personal():
    """before_request de los blueprints del personal (clinica y admin)."""
    if es_paciente():
        return redirect(url_for("portal.inicio"))
    if not session.get("rol"):
        return redirect(url_for("auth.ingreso"))
    if usuario_actual() is None:
        session.clear()
        flash("Su usuario no está activo. Consulte con administración.", "advertencia")
        return redirect(url_for("auth.ingreso"))
    return None


def exigir_paciente():
    """before_request del portal del paciente."""
    if es_paciente():
        return None
    if usuario_actual():
        return redirect(inicio_personal())
    return redirect(url_for("auth.ingreso"))


def requiere_permiso(permiso):
    def decorador(vista):
        @functools.wraps(vista)
        def envoltura(*args, **kwargs):
            if not tiene_permiso(permiso):
                flash("Su rol no tiene acceso a esa sección. Le llevamos a su pantalla de inicio.", "advertencia")
                return redirect(inicio_personal())
            return vista(*args, **kwargs)
        return envoltura
    return decorador


# ---------- Variables para las plantillas ----------

def variables_globales():
    v = {"rol": session.get("rol"), "nombre": session.get("nombre"), "hora": "",
         "puede": tiene_permiso, "iniciales": iniciales}
    u = usuario_actual()
    if u:
        portal = "admin" if request.blueprint == "admin" else "clinica"
        propio, otro = ((permisos.MENU_ADMIN, permisos.MENU_CLINICA) if portal == "admin"
                        else (permisos.MENU_CLINICA, permisos.MENU_ADMIN))
        destinos = [m[0] for m in otro if tiene_permiso(m[4])]
        v.update({
            "portal": portal,
            "usuario": u,
            "menu": [m[:4] for m in propio if tiene_permiso(m[4])],
            "activo": permisos.ACTIVO.get(request.endpoint, request.endpoint),
            "otro_portal": url_for(destinos[0]) if destinos else None,
            "turno_txt": turnos.texto_turno(),
            "hora": hora_actual(),
            "turno_usuario": turnos.nombre_turno(u["turno"]) if u["turno"] is not None else None,
            "reloj_demo": reloj.es_demo(),
        })
        if tiene_permiso("entrega_turno"):
            v["entregas_por_recibir"] = turnos.por_recibir(u["nombre"])
        if tiene_permiso("admin_inventario"):
            v["alertas_recursos"], v["solicitudes_abiertas"] = recursos.contar_alertas()
    return v


def init_app(app):
    app.context_processor(variables_globales)
