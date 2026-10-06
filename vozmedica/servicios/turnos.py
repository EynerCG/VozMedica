"""Turnos y entrega de turno, como en un servicio de hospitalizacion.

- El turno actual lo marca el reloj: Mañana 07-13, Tarde 13-19, Noche 19-07.
- Cada empleado clinico tiene un turno asignado (personal.turno).
- Enfermeria: cada enfermera tiene camas asignadas (pacientes.enfermera) y las entrega a una
  colega del turno siguiente.
- Medicos: el responsable de un paciente es quien lo cubre (pacientes.cubre) o, si nadie lo cubre,
  su medico tratante. En la entrega medica el paciente pasa a ser cubierto por el medico del
  turno siguiente; si quien recibe es el tratante, el paciente vuelve a el (cubre = NULL).
- La entrega se hace en la ultima hora del turno (o hasta 3 horas despues si se extiende) y
  tiene dos firmas: queda Pendiente hasta que quien recibe la confirma con su usuario.
"""

from datetime import timedelta

from ..db import conectar
from ..errores import Advertencia
from . import pacientes, reloj

TURNOS = [("Mañana", "07:00", "13:00"), ("Tarde", "13:00", "19:00"), ("Noche", "19:00", "07:00")]
MINUTOS_ANTES = 60      # se puede entregar desde 1 hora antes del fin del turno
MINUTOS_DESPUES = 180   # ... y hasta 3 horas despues (si el turno se extiende)


# ---------- Reloj y turnos ----------

def turno_de(momento):
    return 0 if 7 <= momento.hour < 13 else 1 if 13 <= momento.hour < 19 else 2


def turno_actual():
    return turno_de(reloj.ahora())


def texto_turno(t=None):
    t = turno_actual() if t is None else t
    return "%s (%s-%s)" % TURNOS[t]


def nombre_turno(t):
    return TURNOS[t][0] if t is not None else "Sin turno"


def _fin_de_turno_cercano(t):
    """Fin del turno t dentro de la ventana de entrega respecto a ahora, o None."""
    ahora = reloj.ahora()
    h, m = (int(x) for x in TURNOS[t][2].split(":"))
    for dias in (-1, 0, 1):
        fin = ahora.replace(hour=h, minute=m) + timedelta(days=dias)
        if fin - timedelta(minutes=MINUTOS_ANTES) <= ahora <= fin + timedelta(minutes=MINUTOS_DESPUES):
            return fin
    return None


def siguiente_hito():
    """Para la demo: la proxima hora interesante del reloj (cierre del turno o inicio del siguiente)."""
    ahora = reloj.ahora()
    h, m = (int(x) for x in TURNOS[turno_actual()][2].split(":"))
    fin = ahora.replace(hour=h, minute=m)
    if fin <= ahora:
        fin += timedelta(days=1)
    return fin - timedelta(minutes=20) if fin - ahora > timedelta(minutes=MINUTOS_ANTES) else fin


# ---------- Quien es responsable de que ----------

def tipo_de(empleado):
    """'medica' si el rol formula (ordenes_medicas), si no 'enfermeria'."""
    from .personal import permisos_de_rol
    return "medica" if "ordenes_medicas" in permisos_de_rol(empleado["rol"]) else "enfermeria"


def pacientes_a_cargo(nombre, tipo):
    return [p for p in pacientes.todos() if pacientes.responsable(p, tipo) == nombre]


def colegas_del_turno(turno, tipo):
    """Empleados de ese turno y profesion que pueden entregar/recibir turno, en orden."""
    signo = "" if tipo == "medica" else "NOT"
    return conectar().execute("""SELECT p.* FROM personal p
        WHERE p.turno = ? AND p.activo = 1
          AND EXISTS (SELECT 1 FROM permisos x WHERE x.rol = p.rol AND x.permiso = 'entrega_turno')
          AND %s EXISTS (SELECT 1 FROM permisos x WHERE x.rol = p.rol AND x.permiso = 'ordenes_medicas')
        ORDER BY p.id""" % signo, (turno,)).fetchall()


def _pareja(empleado, tipo, receptores):
    """Colega del turno siguiente que le corresponde por defecto (1a con 1a, 2a con 2a...)."""
    if not receptores:
        return None
    mios = [c["nombre"] for c in colegas_del_turno(empleado["turno"], tipo)]
    i = mios.index(empleado["nombre"]) if empleado["nombre"] in mios else 0
    return receptores[i % len(receptores)]["nombre"]


# ---------- Entregas ----------

def _en_entrega_pendiente(tipo):
    """Pacientes que ya estan en una entrega sin recibir del mismo tipo (enfermeria y medica van por separado)."""
    return {f["paciente_id"] for f in conectar().execute(
        """SELECT ep.paciente_id FROM entrega_pacientes ep JOIN entregas e ON e.id = ep.entrega_id
           WHERE e.estado = 'Pendiente' AND e.tipo = ?""", (tipo,)).fetchall()}


def preparar(empleado):
    """Todo lo que necesita la pantalla de entrega para este empleado."""
    tipo = tipo_de(empleado)
    t = empleado["turno"]
    datos = {"tipo": tipo, "turno": t, "filas": [], "receptores": [], "ventana": False,
             "siguiente": None, "por_recibir": por_recibir(empleado["nombre"]),
             "enviadas": enviadas_pendientes(empleado["nombre"])}
    if t is None:
        return datos
    receptores = colegas_del_turno((t + 1) % 3, tipo)
    nombres = [r["nombre"] for r in receptores]
    pareja = _pareja(empleado, tipo, receptores)
    ocupados = _en_entrega_pendiente(tipo)
    db = conectar()
    for p in pacientes_a_cargo(empleado["nombre"], tipo):
        if p["id"] in ocupados:
            continue
        queda = [(m["hora"] + " " + m["nombre"], pacientes.estado_medicamento(m)) for m in db.execute(
            "SELECT * FROM medicamentos WHERE paciente_id=? AND estado='P' ORDER BY fecha, hora", (p["id"],)).fetchall()]
        queda += [(d["texto"], None) for d in db.execute(
            "SELECT * FROM pendientes WHERE paciente_id=? AND hecho=0", (p["id"],)).fetchall()]
        ultima = db.execute("SELECT * FROM novedades WHERE paciente_id=? ORDER BY id DESC LIMIT 1", (p["id"],)).fetchone()
        # en la entrega medica de la noche, cada paciente vuelve por defecto a su tratante
        defecto = p["medico"] if tipo == "medica" and p["medico"] in nombres else pareja
        datos["filas"].append({"p": p, "queda": queda, "ultima": ultima, "defecto": defecto})
    datos.update(receptores=nombres, siguiente=nombre_turno((t + 1) % 3), ventana=_fin_de_turno_cercano(t) is not None)
    return datos


def entregar(empleado, revisados, receptor_de, nota_de, observaciones):
    """Paso 1. revisados: ids marcados; receptor_de / nota_de: {paciente_id: texto}.
    Crea una entrega Pendiente por cada persona que recibe. Devuelve los nombres de quienes reciben."""
    datos = preparar(empleado)
    t = datos["turno"]
    if t is None:
        raise Advertencia("No tiene turno asignado. Consulte con administración.")
    if not datos["ventana"]:
        raise Advertencia("Su turno (%s) todavía no está por terminar. La entrega se hace desde una hora antes "
                          "del cierre." % texto_turno(t))
    if not datos["filas"]:
        raise Advertencia("No tiene pacientes a su cargo pendientes de entregar.")
    faltan = [f["p"] for f in datos["filas"] if f["p"]["id"] not in revisados]
    if faltan:
        raise Advertencia("Falta revisar %d paciente%s antes de entregar: cama %s."
                          % (len(faltan), "s" if len(faltan) > 1 else "", ", ".join(p["cama"] for p in faltan)))
    grupos = {}
    for f in datos["filas"]:
        quien = receptor_de.get(f["p"]["id"], "")
        if quien not in datos["receptores"]:
            raise Advertencia("Seleccione quién del turno %s recibe la cama %s." % (datos["siguiente"], f["p"]["cama"]))
        grupos.setdefault(quien, []).append(f["p"]["id"])

    db = conectar()
    for quien, ids in grupos.items():
        cur = db.execute("""INSERT INTO entregas (tipo,fecha,hora,turno,entrega,recibe,observaciones,estado,recibida)
                            VALUES (?,?,?,?,?,?,?,'Pendiente','')""",
                         (datos["tipo"], reloj.hoy_texto(), reloj.hora_actual(),
                          "%s → %s" % (nombre_turno(t), datos["siguiente"]), empleado["nombre"], quien, observaciones or "-"))
        for pid in ids:
            db.execute("INSERT INTO entrega_pacientes (entrega_id,paciente_id,nota) VALUES (?,?,?)",
                       (cur.lastrowid, pid, nota_de.get(pid, "")))
    db.commit()
    return sorted(grupos)


def _con_pacientes(entregas):
    db = conectar()
    resultado = []
    for e in entregas:
        filas = db.execute("""SELECT ep.nota, p.* FROM entrega_pacientes ep JOIN pacientes p ON p.id = ep.paciente_id
                              WHERE ep.entrega_id = ? ORDER BY p.cama""", (e["id"],)).fetchall()
        resultado.append({"e": e, "pacientes": filas})
    return resultado


def por_recibir(nombre):
    return _con_pacientes(conectar().execute(
        "SELECT * FROM entregas WHERE estado='Pendiente' AND recibe=? ORDER BY id", (nombre,)).fetchall())


def enviadas_pendientes(nombre):
    return _con_pacientes(conectar().execute(
        "SELECT * FROM entregas WHERE estado='Pendiente' AND entrega=? ORDER BY id", (nombre,)).fetchall())


def recibir(eid, quien):
    """Paso 2: quien recibe confirma con su usuario y los pacientes quedan a su cargo."""
    db = conectar()
    e = db.execute("SELECT * FROM entregas WHERE id=? AND estado='Pendiente'", (eid,)).fetchone()
    if e is None or e["recibe"] != quien:
        raise Advertencia("No tiene esa entrega de turno pendiente por recibir.")
    for f in db.execute("SELECT paciente_id FROM entrega_pacientes WHERE entrega_id=?", (eid,)).fetchall():
        p = pacientes.obtener(f["paciente_id"])
        if p is None:
            continue   # le dieron de alta mientras tanto
        if e["tipo"] == "enfermeria":
            db.execute("UPDATE pacientes SET enfermera=? WHERE id=?", (quien, p["id"]))
        else:
            db.execute("UPDATE pacientes SET cubre=? WHERE id=?", (None if p["medico"] == quien else quien, p["id"]))
    db.execute("UPDATE entregas SET estado='Recibida', recibida=? WHERE id=?", (reloj.hora_actual(), eid))
    db.commit()
    return e


def anular(eid, quien):
    """Quien entrego puede anular mientras no la hayan recibido."""
    db = conectar()
    e = db.execute("SELECT * FROM entregas WHERE id=? AND estado='Pendiente'", (eid,)).fetchone()
    if e is None or e["entrega"] != quien:
        raise Advertencia("No tiene esa entrega pendiente para anular.")
    db.execute("DELETE FROM entrega_pacientes WHERE entrega_id=?", (eid,))
    db.execute("DELETE FROM entregas WHERE id=?", (eid,))
    db.commit()


def notas_de_entrega(pid):
    """La ultima entrega medica y la ultima de enfermeria de este paciente (para la ficha)."""
    notas = []
    for tipo in ("medica", "enfermeria"):
        f = conectar().execute("""SELECT e.*, ep.nota FROM entrega_pacientes ep JOIN entregas e ON e.id = ep.entrega_id
                                  WHERE ep.paciente_id = ? AND e.tipo = ? ORDER BY e.id DESC LIMIT 1""", (pid, tipo)).fetchone()
        if f:
            notas.append(f)
    return notas


def historial():
    return conectar().execute("""SELECT e.*, (SELECT COUNT(*) FROM entrega_pacientes ep WHERE ep.entrega_id = e.id) AS pacientes
                                 FROM entregas e ORDER BY e.id DESC LIMIT 200""").fetchall()
