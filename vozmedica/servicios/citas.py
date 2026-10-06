"""Atencion virtual: pacientes del portal, citas y mensajes del chat.

Las citas usan la fecha y hora REALES (no el reloj de la demo del hospital).
Reglas:
- Cada medico solo tiene citas dentro de SU turno, cada 30 minutos, hasta una hora antes del cierre
  (la ultima hora es la de la entrega de turno). De noche solo las primeras horas.
- Una cita Programada cuya fecha ya paso sin ser atendida queda Vencida.
- El paciente puede cancelar hasta 2 horas antes; despues debe comunicarse con recepcion.
"""

from datetime import date, datetime, timedelta

from ..db import conectar
from ..errores import Advertencia
from ..utils import formato_fecha, nueva_sala

NOMBRE_TURNO = ["Mañana", "Tarde", "Noche"]
FRANJA_CITAS = {0: ("07:00", "11:30"), 1: ("13:00", "17:30"), 2: ("19:00", "21:30")}
HORAS_MINIMAS_CANCELAR = 2


def _cada_media_hora(inicio, fin):
    hora = datetime.strptime(inicio, "%H:%M")
    ultima = datetime.strptime(fin, "%H:%M")
    horas = []
    while hora <= ultima:
        horas.append(hora.strftime("%H:%M"))
        hora += timedelta(minutes=30)
    return horas


HORARIOS_POR_TURNO = {t: _cada_media_hora(*franja) for t, franja in FRANJA_CITAS.items()}
HORARIOS = [h for t in sorted(HORARIOS_POR_TURNO) for h in HORARIOS_POR_TURNO[t]]   # todas, para la agenda


def turno_de(profesional):
    fila = conectar().execute("SELECT turno FROM personal WHERE nombre=? AND activo=1", (profesional,)).fetchone()
    return fila["turno"] if fila else None


def horarios_de(profesional):
    """Horas en las que ese medico puede tener citas (las de su turno)."""
    return HORARIOS_POR_TURNO.get(turno_de(profesional), [])


def texto_horario(profesional):
    t = turno_de(profesional)
    if t not in FRANJA_CITAS:
        return "sin turno asignado"
    return "turno %s (%s a %s)" % ((NOMBRE_TURNO[t],) + FRANJA_CITAS[t])

_CON_PACIENTE = "SELECT c.*, p.nombre AS paciente FROM citas c JOIN portal p ON p.documento = c.documento"


# ---------- Pacientes del portal ----------

def paciente_portal(documento):
    return conectar().execute("SELECT * FROM portal WHERE documento=?", (documento,)).fetchone()


def pacientes_portal():
    return conectar().execute("SELECT * FROM portal ORDER BY nombre").fetchall()


# ---------- Citas ----------

ABIERTA = "Programada"   # unico estado en el que se puede chatear, cancelar o atender


def vencer_citas():
    """Las citas programadas de dias anteriores que nadie atendio pasan a Vencida."""
    db = conectar()
    if db.execute("UPDATE citas SET estado='Vencida' WHERE estado='Programada' AND fecha < ?",
                  (date.today().isoformat(),)).rowcount:
        db.commit()


def crear(documento, fecha, hora, motivo):
    """Agenda la cita con el profesional asignado al paciente. Devuelve el mensaje de confirmacion."""
    from .personal import medicos   # import local para evitar import circular
    paciente = paciente_portal(documento)
    if paciente is None:
        raise Advertencia("Seleccione el paciente.")
    if not fecha or not hora or not motivo:
        raise Advertencia("Complete la fecha, la hora y el motivo de la cita.")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Advertencia("Revise la fecha de la cita.")
    if paciente["profesional"] not in medicos():
        raise Advertencia("Su profesional asignado no está disponible para citas virtuales. "
                          "Comuníquese con recepción para que le asignen otro.")
    if hora not in horarios_de(paciente["profesional"]):
        raise Advertencia("%s atiende citas en el %s. Elija una hora dentro de su turno."
                          % (paciente["profesional"], texto_horario(paciente["profesional"])))
    if datetime.combine(dia, datetime.strptime(hora, "%H:%M").time()) <= datetime.now():
        raise Advertencia("Esa fecha y hora ya pasaron. Elija un horario futuro.")
    db = conectar()
    if db.execute("SELECT 1 FROM citas WHERE documento=? AND fecha=? AND estado='Programada'", (documento, fecha)).fetchone():
        raise Advertencia("Ya hay una cita programada para ese paciente ese día.")
    if db.execute("SELECT 1 FROM citas WHERE profesional=? AND fecha=? AND hora=? AND estado='Programada'",
                  (paciente["profesional"], fecha, hora)).fetchone():
        raise Advertencia("%s ya tiene una cita ese día a las %s. Elija otra hora." % (paciente["profesional"], hora))
    db.execute("INSERT INTO citas (documento,profesional,fecha,hora,motivo,estado,sala) VALUES (?,?,?,?,?,?,?)",
               (documento, paciente["profesional"], fecha, hora, motivo, "Programada", nueva_sala()))
    db.commit()
    return "Cita agendada con %s el %s a las %s." % (paciente["profesional"], formato_fecha(fecha), hora)


def de_paciente(documento):
    """(proxima cita programada o None, resto de citas)."""
    vencer_citas()
    citas = conectar().execute("SELECT * FROM citas WHERE documento=? ORDER BY fecha, hora", (documento,)).fetchall()
    proxima = next((c for c in citas if c["estado"] == "Programada"), None)
    return proxima, [c for c in citas if proxima is None or c["id"] != proxima["id"]]


def de_profesional(nombre):
    vencer_citas()
    return conectar().execute(_CON_PACIENTE + " WHERE c.profesional=? ORDER BY c.estado <> 'Programada', c.fecha, c.hora",
                              (nombre,)).fetchall()


def agenda(solo_programadas=True):
    vencer_citas()
    sql = _CON_PACIENTE + (" WHERE c.estado='Programada'" if solo_programadas else "")
    return conectar().execute(sql + " ORDER BY c.fecha, c.hora").fetchall()


def obtener(cid):
    vencer_citas()
    return conectar().execute(_CON_PACIENTE + " WHERE c.id=?", (cid,)).fetchone()


def cancelar(cid, documento=None):
    """Cancela una cita programada. Con documento (el paciente cancela su propia cita) aplica
    la regla de las 2 horas; recepcion puede cancelar en cualquier momento."""
    c = obtener(cid)
    if c is None or c["estado"] != ABIERTA or (documento is not None and c["documento"] != documento):
        raise Advertencia("Esa cita ya no se puede cancelar.")
    if documento is not None:
        inicio = datetime.strptime("%s %s" % (c["fecha"], c["hora"]), "%Y-%m-%d %H:%M")
        if inicio - datetime.now() < timedelta(hours=HORAS_MINIMAS_CANCELAR):
            raise Advertencia("Faltan menos de %d horas para la cita. Para cancelarla comuníquese con recepción."
                              % HORAS_MINIMAS_CANCELAR)
    db = conectar()
    db.execute("UPDATE citas SET estado='Cancelada' WHERE id=?", (cid,))
    db.commit()


def marcar_atendida(cid, profesional):
    """Solo el profesional de la cita, y no antes del dia de la cita."""
    c = obtener(cid)
    if c is None or c["profesional"] != profesional:
        raise Advertencia("Esa cita no está a su nombre.")
    if c["estado"] != ABIERTA:
        raise Advertencia("La cita está %s; ya no se puede marcar como atendida." % c["estado"].lower())
    if c["fecha"] > date.today().isoformat():
        raise Advertencia("La cita es el %s. Se marca como atendida el día de la consulta." % formato_fecha(c["fecha"]))
    db = conectar()
    db.execute("UPDATE citas SET estado='Atendida' WHERE id=?", (cid,))
    db.commit()


# ---------- Chat ----------

def mensajes(cid):
    return conectar().execute("SELECT * FROM mensajes WHERE cita_id=? ORDER BY id", (cid,)).fetchall()


def enviar_mensaje(cid, autor, texto):
    """Solo se escribe en citas programadas; las cerradas quedan de solo lectura."""
    c = obtener(cid)
    if not texto or c is None or c["estado"] != ABIERTA:
        return
    db = conectar()
    db.execute("INSERT INTO mensajes (cita_id,autor,hora,texto) VALUES (?,?,?,?)",
               (cid, autor, datetime.now().strftime("%H:%M"), texto))
    db.commit()
