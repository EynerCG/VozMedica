"""Pacientes hospitalizados: censo, ficha, medicamentos, signos, pendientes y novedades.

Reglas de la vida real:
- La historia clinica no se borra ni se sobrescribe: signos vitales y novedades se AGREGAN
  con fecha, hora y autor. El alta solo registra la fecha y libera la cama.
- Un paciente (por documento) no puede estar hospitalizado dos veces al mismo tiempo.
- Cada paciente tiene un medico tratante. Mientras el tratante no esta, lo cubre el medico de
  turno que lo recibio en la entrega medica. Solo ellos dos formulan, suspenden y dan de alta.
  "Asumir paciente" es un traslado definitivo: otro medico pasa a ser el tratante.
- Cada paciente tiene la enfermera que tiene su cama asignada en el turno.
- Medicamentos: el medico formula (dosis unica o cada N horas por N dias) y puede suspender
  la orden; enfermeria registra cada dosis como aplicada o NO aplicada (con motivo).
  Margen de 30 minutos: desde 30 min antes ("Toca ahora"); pasados 30 min queda "Atrasado".
- Al formular se cruza el medicamento con las alergias del paciente (incluye familias).
"""

import unicodedata
from datetime import datetime, timedelta

from ..db import conectar
from ..errores import Advertencia
from ..utils import hora_valida
from . import camas, reloj

ESTADOS = {"estable": "Estable", "vigilancia": "Vigilancia", "critico": "Crítico"}
ESTADO_CLASE = {"estable": "exito", "vigilancia": "alerta", "critico": "peligro"}
MARGEN_MINUTOS = 30
FRECUENCIAS = [0, 6, 8, 12, 24]          # 0 = dosis unica
MAX_DIAS = 7
MOTIVOS_NO_APLICADA = ["Paciente rechaza el medicamento", "Paciente en ayuno / NPO",
                       "Medicamento no disponible", "Paciente fuera del servicio (examen o procedimiento)", "Otro"]

# Familias de medicamentos para la alerta de alergias (sin tildes, en minusculas)
FAMILIAS_ALERGIA = {
    "penicilina": ["penicilina", "amoxicilina", "ampicilina", "oxacilina", "dicloxacilina", "piperacilina"],
    "aines": ["ibuprofeno", "naproxeno", "diclofenaco", "ketorolaco", "asa ", "aspirina", "acido acetilsalicilico",
              "meloxicam", "celecoxib", "indometacina"],
    "sulfas": ["sulfametoxazol", "sulfadiazina", "sulfasalazina"],
}

# dia de hospitalizacion calculado con la fecha del reloj del sistema (dia 1 = dia del ingreso)
_SELECT = "SELECT *, CAST(julianday(?) - julianday(ingreso) AS INTEGER) + 1 AS dia FROM pacientes"


def _normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().replace("-", " ").replace("/", " ").split()) + " "


def alerta_alergia(alergias, medicamento):
    """Devuelve la alergia del paciente que choca con el medicamento, o None."""
    med = _normalizar(medicamento)
    for alergia in (alergias or "").split(","):
        clave = _normalizar(alergia).strip()
        if not clave or clave == "ninguna":
            continue
        nombres = FAMILIAS_ALERGIA.get(clave, []) + [clave + " "]
        if any(n in med for n in nombres):
            return alergia.strip()
    return None


def estado_medicamento(m):
    """Devuelve (texto, clase de la etiqueta) de la dosis."""
    if m["estado"] == "A":
        return ("Administrado", "exito")
    if m["estado"] == "N":
        return ("No aplicado", "alerta")
    if m["estado"] == "S":
        return ("Suspendido", "neutro")
    programada = datetime.strptime("%s %s" % (m["fecha"], m["hora"]), "%Y-%m-%d %H:%M")
    minutos = (reloj.ahora() - programada).total_seconds() / 60
    if minutos > MARGEN_MINUTOS:
        return ("Atrasado", "peligro")
    if minutos >= -MARGEN_MINUTOS:
        return ("Toca ahora", "info")
    return ("Programado", "neutro")


def contar_atrasados(pid):
    meds = conectar().execute("SELECT * FROM medicamentos WHERE paciente_id=? AND estado='P'", (pid,)).fetchall()
    return len([m for m in meds if estado_medicamento(m)[0] == "Atrasado"])


def contar_pendientes(pid):
    return conectar().execute("SELECT COUNT(*) FROM pendientes WHERE paciente_id=? AND hecho=0", (pid,)).fetchone()[0]


def todos():
    """Pacientes hospitalizados en este momento (sin alta)."""
    return conectar().execute(_SELECT + " WHERE alta IS NULL ORDER BY cama", (reloj.fecha_iso(),)).fetchall()


def medicos_tratantes():
    """Empleados activos que pueden ser medico tratante (tienen permiso de ordenes medicas)."""
    from .personal import con_permiso   # import local: personal tambien consulta pacientes
    return con_permiso("ordenes_medicas")


def responsable(p, tipo):
    """Quien responde por el paciente: su enfermera, o el medico que lo cubre (si no, su tratante)."""
    return p["enfermera"] if tipo == "enfermeria" else (p["cubre"] or p["medico"])


def censo(nombre=None, tipo=None):
    """Lista de pacientes con sus alertas y un resumen para los indicadores.
    Con nombre y tipo ('medica' / 'enfermeria'), solo los pacientes a cargo de esa persona."""
    pacientes = [p for p in todos() if nombre is None or responsable(p, tipo) == nombre]
    lista = [{"p": p, "atrasados": contar_atrasados(p["id"]), "pendientes": contar_pendientes(p["id"])} for p in pacientes]
    resumen = {
        "pacientes": len(lista),
        "atrasados": sum(f["atrasados"] for f in lista),
        "criticos": len([f for f in lista if f["p"]["estado"] == "critico"]),
        "pendientes": sum(f["pendientes"] for f in lista),
    }
    return lista, resumen


def obtener(pid):
    """Paciente hospitalizado (None si no existe o ya tiene alta)."""
    return conectar().execute(_SELECT + " WHERE id=? AND alta IS NULL", (reloj.fecha_iso(), pid)).fetchone()


def _hospitalizado(pid):
    p = obtener(pid)
    if p is None:
        raise Advertencia("Ese paciente ya no está hospitalizado (fue dado de alta).")
    return p


def _novedad(pid, texto, autor):
    """Agrega una nota a la historia clinica con la fecha y hora del reloj. No hace commit."""
    conectar().execute("INSERT INTO novedades (paciente_id,fecha,hora,texto,autor) VALUES (?,?,?,?,?)",
                       (pid, reloj.fecha_iso(), reloj.hora_actual(), texto, autor))


def _signos(pid, texto, autor):
    conectar().execute("INSERT INTO signos (paciente_id,fecha,hora,texto,autor) VALUES (?,?,?,?,?)",
                       (pid, reloj.fecha_iso(), reloj.hora_actual(), texto, autor))


def ficha(pid):
    """Datos completos de la ficha, o None si el paciente no esta hospitalizado."""
    p = obtener(pid)
    if p is None:
        return None
    db = conectar()
    # dosis pendientes (de cualquier dia) y las demas desde ayer
    meds = db.execute("""SELECT * FROM medicamentos WHERE paciente_id=?
                         AND (estado='P' OR fecha >= date(?, '-1 day')) ORDER BY fecha, hora""",
                      (pid, reloj.fecha_iso())).fetchall()
    return {
        "p": p,
        "meds": [(m, estado_medicamento(m)) for m in meds],
        "hoy_iso": reloj.fecha_iso(),
        "signos": db.execute("SELECT * FROM signos WHERE paciente_id=? ORDER BY id DESC LIMIT 10", (pid,)).fetchall(),
        "pend": db.execute("SELECT * FROM pendientes WHERE paciente_id=? ORDER BY hecho, id", (pid,)).fetchall(),
        "nov": db.execute("SELECT * FROM novedades WHERE paciente_id=? ORDER BY id DESC", (pid,)).fetchall(),
        "camas_libres": camas.disponibles(),
        "frecuencias": FRECUENCIAS, "max_dias": MAX_DIAS, "motivos_no_aplicada": MOTIVOS_NO_APLICADA,
    }


def enfermeras_de_turno():
    """Enfermeras del turno que marca el reloj (a quienes se les puede asignar una cama)."""
    from .turnos import colegas_del_turno, turno_actual   # import local: turnos usa este modulo
    return [e["nombre"] for e in colegas_del_turno(turno_actual(), "enfermeria")]


def registrar(documento, cama, nombre, edad, diagnostico, alergias, signos, medico, enfermera, quien):
    """Ingresa un paciente en una cama disponible, con medico tratante y enfermera a cargo. Devuelve el id."""
    if not documento or not cama or not nombre or not diagnostico or not edad:
        raise Advertencia("Faltan datos obligatorios del ingreso: documento, nombre, edad, diagnóstico y cama.")
    if not edad.isdigit() or int(edad) > 120:
        raise Advertencia("Revise la edad: debe ser un número entre 0 y 120.")
    if medico not in medicos_tratantes():
        raise Advertencia("Seleccione el médico tratante.")
    if enfermera not in enfermeras_de_turno():
        raise Advertencia("Seleccione la enfermera del turno que recibe al paciente.")
    db = conectar()
    ya = db.execute("SELECT cama FROM pacientes WHERE documento=? AND alta IS NULL", (documento,)).fetchone()
    if ya:
        raise Advertencia("El paciente con documento %s ya está hospitalizado en la cama %s." % (documento, ya["cama"]))
    if not camas.esta_disponible(cama):
        raise Advertencia("La cama %s ya no está disponible. Elija otra de la lista." % cama)
    cur = db.execute("""INSERT INTO pacientes (documento,cama,nombre,edad,diagnostico,ingreso,alta,alergias,estado,
                        medico,cubre,enfermera) VALUES (?,?,?,?,?,?,NULL,?,?,?,NULL,?)""",
                     (documento, cama, nombre, int(edad), diagnostico, reloj.fecha_iso(), alergias or "Ninguna",
                      "estable", medico, enfermera))
    pid = cur.lastrowid
    _novedad(pid, "Ingreso al servicio en la cama %s. Médico tratante: %s." % (cama, medico), quien)
    if signos:
        _signos(pid, signos, quien)
    db.commit()
    return pid


def cambiar_estado(pid, estado, quien):
    p = _hospitalizado(pid)
    if estado not in ESTADOS:
        raise Advertencia("Seleccione un estado válido.")
    if estado == p["estado"]:
        return
    db = conectar()
    db.execute("UPDATE pacientes SET estado=? WHERE id=?", (estado, pid))
    _novedad(pid, "Estado: %s → %s." % (ESTADOS[p["estado"]], ESTADOS[estado]), quien)
    db.commit()


def actualizar_signos(pid, texto, quien):
    """Agrega un registro de signos vitales (no reemplaza los anteriores)."""
    _hospitalizado(pid)
    if not texto:
        raise Advertencia("Escriba los signos vitales antes de guardarlos.")
    _signos(pid, texto, quien)
    conectar().commit()


def cambiar_cama(pid, nueva, quien):
    """Traslado a otra cama libre del servicio. Queda en las novedades. Devuelve la cama anterior."""
    p = _hospitalizado(pid)
    if not camas.esta_disponible(nueva):
        raise Advertencia("La cama %s no está disponible. Elija una de la lista." % (nueva or "seleccionada"))
    db = conectar()
    db.execute("UPDATE pacientes SET cama=? WHERE id=?", (nueva, pid))
    _novedad(pid, "Traslado de cama %s → %s." % (p["cama"], nueva), quien)
    db.commit()
    return p["cama"]


def _exigir_tratante(p, quien, accion):
    """Formulan, suspenden y dan de alta el medico tratante y, mientras lo cubre, el medico de turno."""
    if quien not in (p["medico"], p["cubre"]):
        cubre = " o quien lo cubre (%s)" % p["cubre"] if p["cubre"] else ""
        raise Advertencia("Solo el médico tratante (%s)%s puede %s a este paciente. Para recibirlo use la entrega "
                          "de turno; para trasladarlo definitivamente, “Asumir paciente”." % (p["medico"], cubre, accion))


def asumir(pid, quien):
    """Traslado definitivo: otro medico pasa a ser el medico tratante (queda en las novedades)."""
    p = _hospitalizado(pid)
    if quien not in medicos_tratantes():
        raise Advertencia("Solo un médico puede ser médico tratante.")
    if p["medico"] == quien:
        raise Advertencia("Usted ya es el médico tratante de este paciente.")
    db = conectar()
    db.execute("UPDATE pacientes SET medico=?, cubre=NULL WHERE id=?", (quien, pid))
    _novedad(pid, "Asume como médico tratante (antes: %s)." % p["medico"], quien)
    db.commit()
    return p


def dar_alta(pid, quien):
    """Registra el alta (la cama queda libre y se suspenden las dosis pendientes). La historia se conserva."""
    p = _hospitalizado(pid)
    _exigir_tratante(p, quien, "dar de alta")
    db = conectar()
    db.execute("UPDATE pacientes SET alta=? WHERE id=?", (reloj.marca(), pid))
    db.execute("UPDATE medicamentos SET estado='S', registro=?, motivo='Alta médica' WHERE paciente_id=? AND estado='P'",
               ("%s %s" % (quien, reloj.hora_actual()), pid))
    _novedad(pid, "Alta médica.", quien)
    db.commit()
    return p


def programar_medicamento(pid, fecha, hora, nombre, quien, cada_horas="0", dias="1", confirmar_alergia=False):
    """Orden medica: crea la dosis (o las dosis, si se repite cada N horas por N dias). Devuelve cuantas creo."""
    p = _hospitalizado(pid)
    _exigir_tratante(p, quien, "formular")
    if not nombre or not hora_valida(hora):
        raise Advertencia("Para formular indique el medicamento con su dosis y la hora de la primera dosis (HH:MM).")
    if str(cada_horas) not in [str(f) for f in FRECUENCIAS] or not str(dias).isdigit() or not 1 <= int(dias) <= MAX_DIAS:
        raise Advertencia("Revise la frecuencia y la duración del tratamiento.")
    try:
        primera = datetime.strptime("%s %s" % (fecha or reloj.fecha_iso(), hora), "%Y-%m-%d %H:%M")
    except ValueError:
        raise Advertencia("Revise la fecha de la primera dosis.")
    if (reloj.ahora() - primera).total_seconds() / 60 > MARGEN_MINUTOS:
        raise Advertencia("Esa hora ya pasó. La primera dosis debe ser a una hora futura.")
    alergia = alerta_alergia(p["alergias"], nombre)
    if alergia and not confirmar_alergia:
        raise Advertencia("ALERTA DE ALERGIA: %s es alérgico(a) a %s y “%s” puede causar una reacción. Si de todos "
                          "modos debe formularlo, marque “Confirmo que revisé la alergia”." % (p["nombre"], alergia, nombre))
    cada = int(cada_horas)
    total = 1 if cada == 0 else int(dias) * 24 // cada
    db = conectar()
    for i in range(total):
        cuando = primera + timedelta(hours=cada * i)
        db.execute("INSERT INTO medicamentos (paciente_id,fecha,hora,nombre,estado,registro,motivo) VALUES (?,?,?,?,'P','','')",
                   (pid, cuando.date().isoformat(), cuando.strftime("%H:%M"), nombre))
    if alergia:
        _novedad(pid, "Se formula %s pese a la alergia a %s (confirmado por el médico)." % (nombre, alergia), quien)
    db.commit()
    return total


def _dosis(mid):
    m = conectar().execute("SELECT * FROM medicamentos WHERE id=?", (mid,)).fetchone()
    if m is None:
        raise Advertencia("Esa dosis ya no existe.")
    return m


def registrar_medicamento(mid, quien):
    """Enfermeria registra que aplico la dosis. Devuelve la fila."""
    m = _dosis(mid)
    _hospitalizado(m["paciente_id"])
    if m["estado"] != "P":
        raise Advertencia("%s ya estaba registrado (%s): %s." % (m["nombre"], estado_medicamento(m)[0].lower(), m["registro"]))
    if estado_medicamento(m)[0] == "Programado":
        raise Advertencia("Todavía no es hora de %s (programado %s). Se puede registrar desde %d minutos antes."
                          % (m["nombre"], m["hora"], MARGEN_MINUTOS))
    db = conectar()
    db.execute("UPDATE medicamentos SET estado='A', registro=? WHERE id=?", ("%s %s" % (quien, reloj.hora_actual()), mid))
    db.commit()
    return m


def no_aplicar(mid, quien, motivo):
    """Enfermeria documenta que la dosis NO se aplico y por que (deja de contar como atrasada)."""
    m = _dosis(mid)
    _hospitalizado(m["paciente_id"])
    if m["estado"] != "P":
        raise Advertencia("Esa dosis ya estaba registrada como %s." % estado_medicamento(m)[0].lower())
    if not motivo:
        raise Advertencia("Indique por qué no se aplicó la dosis.")
    if estado_medicamento(m)[0] == "Programado":
        raise Advertencia("Todavía no es hora de %s (programado %s)." % (m["nombre"], m["hora"]))
    db = conectar()
    db.execute("UPDATE medicamentos SET estado='N', registro=?, motivo=? WHERE id=?",
               ("%s %s" % (quien, reloj.hora_actual()), motivo, mid))
    _novedad(m["paciente_id"], "No se aplicó %s de las %s: %s." % (m["nombre"], m["hora"], motivo), quien)
    db.commit()
    return m


def suspender(mid, quien, motivo):
    """El medico suspende la orden: esta dosis y las siguientes pendientes del mismo medicamento.
    Devuelve (dosis, cuantas se suspendieron)."""
    m = _dosis(mid)
    _exigir_tratante(_hospitalizado(m["paciente_id"]), quien, "suspender medicamentos")
    if m["estado"] != "P":
        raise Advertencia("Esa dosis ya no está pendiente.")
    db = conectar()
    n = db.execute("""UPDATE medicamentos SET estado='S', registro=?, motivo=?
                      WHERE paciente_id=? AND nombre=? AND estado='P' AND (fecha || ' ' || hora) >= ?""",
                   ("%s %s" % (quien, reloj.hora_actual()), motivo or "Suspendido por el médico",
                    m["paciente_id"], m["nombre"], "%s %s" % (m["fecha"], m["hora"]))).rowcount
    _novedad(m["paciente_id"], "Se suspende %s (%d dosis)%s." % (m["nombre"], n, ": " + motivo if motivo else ""), quien)
    db.commit()
    return m, n


def paciente_de_medicamento(mid):
    m = conectar().execute("SELECT paciente_id FROM medicamentos WHERE id=?", (mid,)).fetchone()
    return m["paciente_id"] if m else None


def alternar_pendiente(did, quien):
    """Marca o desmarca el pendiente, guardando quien lo cumplio. Devuelve el id del paciente."""
    db = conectar()
    d = db.execute("SELECT * FROM pendientes WHERE id=?", (did,)).fetchone()
    if d is None:
        raise Advertencia("Ese pendiente ya no existe.")
    _hospitalizado(d["paciente_id"])
    hecho = 0 if d["hecho"] else 1
    db.execute("UPDATE pendientes SET hecho=?, hecho_por=? WHERE id=?",
               (hecho, "%s %s" % (quien, reloj.hora_actual()) if hecho else "", did))
    db.commit()
    return d["paciente_id"]


def agregar_pendiente(pid, texto):
    _hospitalizado(pid)
    if not texto:
        raise Advertencia("Escriba el pendiente antes de agregarlo.")
    db = conectar()
    db.execute("INSERT INTO pendientes (paciente_id,texto,hecho,hecho_por) VALUES (?,?,0,'')", (pid, texto))
    db.commit()


def agregar_novedad(pid, texto, autor):
    _hospitalizado(pid)
    if not texto:
        raise Advertencia("Escriba la novedad antes de guardarla.")
    _novedad(pid, texto, autor)
    conectar().commit()
