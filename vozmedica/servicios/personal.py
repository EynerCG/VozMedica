"""Personal de salud y administrativo, roles y permisos.

Quien firmo registros clinicos nunca se borra: se DESACTIVA (no puede ingresar ni aparece en
las listas de entrega, tratantes o profesionales) y se puede reactivar.
"""

from ..db import conectar
from ..errores import Advertencia
from ..permisos import CLAVES

_CON_ROL = "SELECT p.*, r.nombre AS rol_nombre FROM personal p LEFT JOIN roles r ON r.clave = p.rol"


# ---------- Empleados ----------

def obtener(eid):
    return conectar().execute(_CON_ROL + " WHERE p.id=?", (eid,)).fetchone()


def listar():
    return conectar().execute(_CON_ROL + " ORDER BY p.activo DESC, r.nombre, COALESCE(p.turno, 9), p.nombre").fetchall()


TURNOS = ["Mañana", "Tarde", "Noche"]


def grupo(p):
    """'Enfermería · Mañana', 'Recepción', ..."""
    return p["rol_nombre"] + (" · " + TURNOS[p["turno"]] if p["turno"] is not None else "")


def para_ingreso():
    """(personal clinico agrupado [(grupo, [empleados])], administradores) para la pantalla de ingreso."""
    filas = conectar().execute(_CON_ROL + " WHERE p.activo = 1 ORDER BY r.nombre, COALESCE(p.turno, 9), p.id").fetchall()
    grupos = []
    for p in filas:
        if p["rol"] == "admin":
            continue
        if not grupos or grupos[-1][0] != grupo(p):
            grupos.append((grupo(p), []))
        grupos[-1][1].append(p)
    return grupos, [p for p in filas if p["rol"] == "admin"]


def _turno(valor):
    """'' -> None; '0'..'2' -> int. Otro valor -> Advertencia."""
    if valor in ("", None):
        return None
    if str(valor) not in ("0", "1", "2"):
        raise Advertencia("Seleccione un turno válido.")
    return int(valor)


def registrar(nombre, documento, rol, turno=""):
    db = conectar()
    if not nombre or not documento or not existe_rol(rol):
        raise Advertencia("Para registrar al empleado complete nombre, documento y rol.")
    if db.execute("SELECT 1 FROM personal WHERE nombre=?", (nombre,)).fetchone():
        raise Advertencia("Ya hay un empleado registrado como %s." % nombre)
    otro = db.execute("SELECT nombre FROM personal WHERE documento=?", (documento,)).fetchone()
    if otro:
        raise Advertencia("El documento %s ya está registrado a nombre de %s." % (documento, otro["nombre"]))
    db.execute("INSERT INTO personal (nombre, documento, rol, turno, activo) VALUES (?,?,?,?,1)",
               (nombre, documento, rol, _turno(turno)))
    db.commit()


def cambiar_rol(eid, rol, quien_cambia):
    """Devuelve el empleado. Nadie puede quitarse a si mismo el acceso a Personal."""
    empleado = obtener(eid)
    if empleado is None or not existe_rol(rol):
        raise Advertencia("Seleccione un rol válido.")
    if eid == quien_cambia and "admin_personal" not in permisos_de_rol(rol):
        raise Advertencia("No puede quitarse a sí mismo el acceso a Personal. Pida a otro administrador que lo haga.")
    nuevos = permisos_de_rol(rol)
    if "atender_citas" not in nuevos or "ordenes_medicas" not in nuevos:
        _sin_pacientes_a_cargo(empleado["nombre"], "cambiar el rol de")
    db = conectar()
    db.execute("UPDATE personal SET rol=? WHERE id=?", (rol, eid))
    db.commit()
    return empleado


def desactivar(eid, quien_desactiva):
    """Retira al empleado (renuncia, licencia...). No se desactiva si tiene citas o pacientes a cargo."""
    empleado = obtener(eid)
    if empleado is None:
        raise Advertencia("Ese empleado no existe.")
    if eid == quien_desactiva:
        raise Advertencia("No puede desactivar su propio usuario.")
    if not empleado["activo"]:
        raise Advertencia("%s ya estaba desactivado(a)." % empleado["nombre"])
    _sin_pacientes_a_cargo(empleado["nombre"], "desactivar a")
    db = conectar()
    db.execute("UPDATE personal SET activo=0 WHERE id=?", (eid,))
    db.commit()
    return empleado


def reactivar(eid):
    empleado = obtener(eid)
    if empleado is None:
        raise Advertencia("Ese empleado no existe.")
    db = conectar()
    db.execute("UPDATE personal SET activo=1 WHERE id=?", (eid,))
    db.commit()
    return empleado


def _sin_pacientes_a_cargo(nombre, accion):
    db = conectar()
    citas = db.execute("SELECT COUNT(*) FROM citas WHERE profesional=? AND estado='Programada'", (nombre,)).fetchone()[0]
    asignados = db.execute("SELECT COUNT(*) FROM portal WHERE profesional=?", (nombre,)).fetchone()[0]
    if citas or asignados:
        raise Advertencia("No se puede %s %s: tiene %d cita(s) programada(s) y %d paciente(s) asignado(s). "
                          "Reasigne primero sus pacientes en la parte de abajo." % (accion, nombre, citas, asignados))
    tratante = db.execute("SELECT COUNT(*) FROM pacientes WHERE medico=? AND alta IS NULL", (nombre,)).fetchone()[0]
    if tratante:
        raise Advertencia("No se puede %s %s: es médico tratante de %d paciente(s) hospitalizado(s). "
                          "Otro médico debe asumirlos primero desde la ficha." % (accion, nombre, tratante))
    _sin_turno_en_curso(nombre, accion)


def _sin_turno_en_curso(nombre, accion):
    """Quien tiene pacientes a su cargo en el turno, o entregas sin cerrar, primero debe entregarlos."""
    db = conectar()
    a_cargo = db.execute("SELECT COUNT(*) FROM pacientes WHERE alta IS NULL AND (enfermera=? OR cubre=?)",
                         (nombre, nombre)).fetchone()[0]
    entregas = db.execute("SELECT COUNT(*) FROM entregas WHERE estado='Pendiente' AND (entrega=? OR recibe=?)",
                          (nombre, nombre)).fetchone()[0]
    if a_cargo or entregas:
        raise Advertencia("No se puede %s %s: tiene %d paciente(s) a su cargo en este turno o una entrega sin cerrar. "
                          "Primero debe entregar el turno." % (accion, nombre, a_cargo))


def cambiar_turno(eid, turno):
    """Cambia el turno asignado. Quien tiene pacientes a su cargo primero entrega el turno."""
    empleado = obtener(eid)
    if empleado is None:
        raise Advertencia("Ese empleado ya no existe.")
    nuevo = _turno(turno)
    if nuevo != empleado["turno"]:
        _sin_turno_en_curso(empleado["nombre"], "cambiar el turno de")
        db = conectar()
        db.execute("UPDATE personal SET turno=? WHERE id=?", (nuevo, eid))
        db.commit()
    return empleado


def con_permiso(permiso):
    """Nombres de los empleados activos cuyo rol tiene ese permiso."""
    return [r["nombre"] for r in conectar().execute("""SELECT p.nombre FROM personal p
            JOIN permisos x ON x.rol = p.rol AND x.permiso = ? WHERE p.activo = 1 ORDER BY p.nombre""",
                                                    (permiso,)).fetchall()]


def medicos():
    """Empleados que pueden atender citas virtuales."""
    return con_permiso("atender_citas")


def asignar_profesional(documento, profesional):
    """Cambia el profesional del paciente del portal. Sus citas programadas pasan al nuevo profesional
    si caen en su turno; las demas se cancelan para que recepcion las reprograme.
    Devuelve (paciente, citas movidas, citas canceladas) o None si no hubo cambio."""
    from .citas import horarios_de   # import local: citas tambien consulta personal
    db = conectar()
    paciente = db.execute("SELECT * FROM portal WHERE documento=?", (documento,)).fetchone()
    if paciente is None or profesional not in medicos():
        raise Advertencia("Seleccione un profesional de la lista.")
    if profesional == paciente["profesional"]:
        return None
    db.execute("UPDATE portal SET profesional=? WHERE documento=?", (profesional, documento))
    horas = horarios_de(profesional)
    movidas = canceladas = 0
    for c in db.execute("SELECT * FROM citas WHERE documento=? AND estado='Programada'", (documento,)).fetchall():
        if c["hora"] in horas:
            db.execute("UPDATE citas SET profesional=? WHERE id=?", (profesional, c["id"]))
            movidas += 1
        else:
            db.execute("UPDATE citas SET estado='Cancelada' WHERE id=?", (c["id"],))
            canceladas += 1
    db.commit()
    return paciente, movidas, canceladas


# ---------- Roles y permisos ----------

def roles():
    return conectar().execute("SELECT * FROM roles ORDER BY nombre").fetchall()


def existe_rol(clave):
    return conectar().execute("SELECT 1 FROM roles WHERE clave=?", (clave,)).fetchone() is not None


def permisos_de_rol(rol):
    return {f["permiso"] for f in conectar().execute("SELECT permiso FROM permisos WHERE rol=?", (rol,)).fetchall()}


def matriz():
    """(conjunto de pares (rol, permiso) activos, empleados por rol)."""
    db = conectar()
    activos = {(f["rol"], f["permiso"]) for f in db.execute("SELECT * FROM permisos").fetchall()}
    cuantos = {r["clave"]: 0 for r in roles()}
    for f in db.execute("SELECT rol, COUNT(*) AS n FROM personal GROUP BY rol").fetchall():
        cuantos[f["rol"]] = f["n"]
    return activos, cuantos


def guardar_permisos(marcados):
    """marcados: conjunto de pares (rol, permiso). El rol admin siempre conserva admin_personal."""
    db = conectar()
    db.execute("DELETE FROM permisos")
    for r in roles():
        for clave in CLAVES:
            if (r["clave"], clave) in marcados or (r["clave"] == "admin" and clave == "admin_personal"):
                db.execute("INSERT INTO permisos VALUES (?,?)", (r["clave"], clave))
    db.commit()
