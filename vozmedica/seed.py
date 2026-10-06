"""Datos de prueba para la demo. Todas las personas son FICTICIAS.

cargar(db) llena una base recien creada (ver db.crear_base).

Servicio de Medicina Interna, piso 2, con 10 camas (201-210) y 7 pacientes hospitalizados.
Cada turno tiene 3 enfermeras y 3 medicos:
  - Enfermeria: cada enfermera tiene camas asignadas y las entrega a una colega del turno siguiente.
  - Medicos: los de la mañana son los medicos tratantes; los de tarde y noche cubren a esos
    pacientes (entrega medica) y en la mañana se los devuelven a su tratante.
La demo arranca a las 12:40: la entrega de las 07:00 (Noche -> Mañana) ya esta registrada.
"""

from datetime import date, datetime, timedelta

from .utils import nueva_sala

MANANA, TARDE, NOCHE = 0, 1, 2

# Roles del personal: (clave, nombre visible)
ROLES = [
    ("enfermeria", "Enfermería"),
    ("medico", "Médico"),
    ("recepcion", "Recepción"),
    ("admin", "Administración"),
]

# Permisos iniciales de cada rol (el administrador los cambia en /admin/roles)
PERMISOS_POR_ROL = {
    "enfermeria": ["ver_censo", "ver_ficha", "editar_ficha", "administrar_medicamentos", "entrega_turno",
                   "ver_historial_turnos", "usar_recursos"],
    # el medico formula, suspende y da de alta (ordenes_medicas); enfermeria administra (administrar_medicamentos)
    "medico": ["ver_censo", "ver_ficha", "editar_ficha", "ordenes_medicas", "entrega_turno", "ver_historial_turnos",
               "atender_citas"],
    "recepcion": ["agenda_servicio"],
    "admin": ["admin_inventario", "admin_personal"],
}

# Personal: (nombre, documento, rol, turno). Turno None = horario administrativo.
# El orden dentro de cada turno define la "pareja" por defecto en la entrega (1a con 1a, 2a con 2a...).
PERSONAL = [
    ("Enf. Laura Gómez", "43100201", "enfermeria", MANANA),
    ("Enf. Camila Ortiz", "43100204", "enfermeria", MANANA),
    ("Enf. Jhon Ramírez", "71100205", "enfermeria", MANANA),
    ("Enf. Andrés Salazar", "71100202", "enfermeria", TARDE),
    ("Enf. Valentina Mora", "43100206", "enfermeria", TARDE),
    ("Enf. Luis Cárdenas", "71100207", "enfermeria", TARDE),
    ("Enf. Paula Ríos", "43100203", "enfermeria", NOCHE),
    ("Enf. Sofía Arias", "43100208", "enfermeria", NOCHE),
    ("Enf. Mateo Londoño", "71100209", "enfermeria", NOCHE),

    ("Dr. Camilo Rojas", "71200301", "medico", MANANA),
    ("Dra. Natalia Vélez", "43200302", "medico", MANANA),
    ("Dr. Felipe Castaño", "71200303", "medico", MANANA),
    ("Dr. Julián Mesa", "71200304", "medico", TARDE),
    ("Dra. Isabel Franco", "43200305", "medico", TARDE),
    ("Dr. Ricardo Peña", "71200306", "medico", TARDE),
    ("Dra. Sara Henao", "43200307", "medico", NOCHE),
    ("Dr. Esteban Vargas", "71200308", "medico", NOCHE),
    ("Dra. Mónica Zapata", "43200309", "medico", NOCHE),

    ("Rec. Diana Torres", "43300401", "recepcion", None),
    ("Adm. Carolina Mejía", "43400501", "admin", None),
]

# Pacientes hospitalizados
# medico = medico tratante; enfermera = enfermera de la mañana que tiene la cama asignada
# medicamentos de hoy: (hora, nombre, estado, quien lo aplico)  estado: A = administrado, P = pendiente
# novedades: (hora, texto, autor)    pendientes: (texto, hecho)
HOSPITALIZADOS = [
    {"cama": "201", "doc": "21345678", "nombre": "María Restrepo", "medico": "Dr. Camilo Rojas",
     "enfermera": "Enf. Laura Gómez", "edad": 74, "dx": "Neumonía adquirida en la comunidad", "dia": 3,
     "alergias": "PENICILINA", "estado": "vigilancia",
     "signos": "PA 128/76 - FC 96 - FR 22 - T 37.9 - SatO2 91% (11:30)",
     "meds": [("06:00", "Ceftriaxona 1 g IV", "A", "Enf. Paula Ríos"),
              ("08:00", "Enoxaparina 40 mg SC", "A", "Enf. Laura Gómez"),
              ("12:00", "Acetaminofén 1 g VO", "P", ""),
              ("14:00", "Nebulización salbutamol 5 mg", "P", "")],
     "novedades": [("03:10", "Saturación 88%. Se aumenta oxígeno a 3 L.", "Enf. Paula Ríos"),
                   ("10:15", "Pico febril 38.4, se toman hemocultivos.", "Enf. Laura Gómez")],
     "pendientes": [("Reclamar resultado de hemocultivos", 0), ("Rx de tórax de control", 0)]},

    {"cama": "202", "doc": "70123456", "nombre": "Jorge Cardona", "medico": "Dra. Natalia Vélez",
     "enfermera": "Enf. Laura Gómez", "edad": 61, "dx": "Diabetes descompensada", "dia": 2,
     "alergias": "Ninguna", "estado": "estable",
     "signos": "PA 134/82 - FC 82 - FR 18 - T 36.6 - SatO2 96% (11:00)",
     "meds": [("07:00", "Insulina glargina 20 UI SC", "A", "Enf. Laura Gómez"),
              ("12:00", "Insulina cristalina según glucometría", "P", ""),
              ("13:00", "Metformina 850 mg VO", "P", "")],
     "novedades": [("06:30", "Glucometría 245 mg/dl, se aplica esquema.", "Enf. Paula Ríos")],
     "pendientes": [("Glucometría pre-almuerzo", 0), ("Educación en insulina", 1)]},

    {"cama": "205", "doc": "8456123", "nombre": "Hernán Villa", "medico": "Dr. Camilo Rojas",
     "enfermera": "Enf. Camila Ortiz", "edad": 80, "dx": "Insuficiencia cardiaca descompensada", "dia": 5,
     "alergias": "AINES", "estado": "critico",
     "signos": "PA 96/58 - FC 112 - FR 26 - T 36.4 - SatO2 89% (12:10)",
     "meds": [("06:00", "Furosemida 40 mg IV", "A", "Enf. Sofía Arias"),
              ("10:00", "Espironolactona 25 mg VO", "P", ""),
              ("12:00", "Furosemida 40 mg IV", "P", "")],
     "novedades": [("12:10", "Disnea en reposo, se avisa a médico tratante.", "Enf. Camila Ortiz")],
     "pendientes": [("Balance de líquidos c/6h", 0), ("Valoración por cardiología", 0)]},

    {"cama": "207", "doc": "70987654", "nombre": "Carlos Arango", "medico": "Dra. Natalia Vélez",
     "enfermera": "Enf. Jhon Ramírez", "edad": 67, "dx": "ACV isquémico en estudio", "dia": 1,
     "alergias": "Ninguna", "estado": "vigilancia",
     "signos": "PA 152/90 - FC 70 - FR 16 - T 36.5 - SatO2 95% (11:45)",
     "meds": [("08:00", "ASA 100 mg VO", "A", "Enf. Jhon Ramírez"),
              ("21:00", "Atorvastatina 40 mg VO", "P", "")],
     "novedades": [("05:50", "Escala neurológica sin cambios.", "Enf. Mateo Londoño")],
     "pendientes": [("TAC de cráneo de control", 0)]},

    {"cama": "203", "doc": "15678234", "nombre": "Luis Fernando Gil", "medico": "Dr. Felipe Castaño",
     "enfermera": "Enf. Laura Gómez", "edad": 58, "dx": "Celulitis en miembro inferior derecho", "dia": 4,
     "alergias": "Ninguna", "estado": "estable",
     "signos": "PA 124/78 - FC 84 - FR 17 - T 37.2 - SatO2 97% (10:30)",
     "meds": [("06:00", "Cefazolina 1 g IV", "A", "Enf. Paula Ríos"),
              ("14:00", "Cefazolina 1 g IV", "P", ""),
              ("22:00", "Cefazolina 1 g IV", "P", "")],
     "novedades": [("09:40", "Se marca borde del eritema; disminuyó respecto a ayer.", "Enf. Laura Gómez")],
     "pendientes": [("Curación de la herida", 0)]},

    {"cama": "204", "doc": "32456789", "nombre": "Rosa Elena Patiño", "medico": "Dr. Felipe Castaño",
     "enfermera": "Enf. Camila Ortiz", "edad": 69, "dx": "EPOC exacerbado", "dia": 2,
     "alergias": "SULFAS", "estado": "vigilancia",
     "signos": "PA 138/84 - FC 98 - FR 24 - T 36.9 - SatO2 90% (11:50)",
     "meds": [("08:00", "Nebulización bromuro de ipratropio", "A", "Enf. Camila Ortiz"),
              ("12:15", "Prednisolona 40 mg VO", "P", ""),
              ("16:00", "Nebulización bromuro de ipratropio", "P", "")],
     "novedades": [("11:50", "Disnea moderada, se deja oxígeno por cánula a 2 L.", "Enf. Camila Ortiz")],
     "pendientes": [("Gases arteriales de control", 0)]},

    {"cama": "206", "doc": "24987123", "nombre": "Gloria Inés Builes", "medico": "Dr. Felipe Castaño",
     "enfermera": "Enf. Jhon Ramírez", "edad": 82, "dx": "Infección urinaria complicada", "dia": 6,
     "alergias": "Ninguna", "estado": "estable",
     "signos": "PA 118/70 - FC 76 - FR 16 - T 36.7 - SatO2 96% (11:15)",
     "meds": [("06:00", "Ertapenem 1 g IV", "A", "Enf. Mateo Londoño"),
              ("12:30", "Hidratación: lactato de Ringer 500 ml", "P", "")],
     "novedades": [("08:20", "Tolera vía oral. Sin fiebre en 48 h.", "Enf. Jhon Ramírez")],
     "pendientes": [("Urocultivo de control", 1), ("Educación al cuidador para el alta", 0)]},
]

# Entrega de las 07:00 (Noche -> Mañana), ya recibida: (tipo, entrega, recibe, camas, nota general)
ENTREGAS_DE_HOY = [
    ("enfermeria", "Enf. Paula Ríos", "Enf. Laura Gómez", ["201", "202", "203"], "Cama 201 con oxígeno a 3 L."),
    ("enfermeria", "Enf. Sofía Arias", "Enf. Camila Ortiz", ["204", "205"], "Cama 205 con disnea en la madrugada."),
    ("enfermeria", "Enf. Mateo Londoño", "Enf. Jhon Ramírez", ["206", "207"], "-"),
    ("medica", "Dra. Sara Henao", "Dr. Camilo Rojas", ["201", "205"], "Vigilar saturación en la 201."),
    ("medica", "Dr. Esteban Vargas", "Dra. Natalia Vélez", ["202", "207"], "TAC de la 207 pendiente."),
    ("medica", "Dra. Mónica Zapata", "Dr. Felipe Castaño", ["203", "204", "206"], "-"),
]

# Camas del servicio: (numero, ubicacion). Las ocupadas son las de HOSPITALIZADOS.
CAMAS = [("%d" % n, "Medicina Interna - Piso 2") for n in range(201, 211)]

# Recursos hospitalarios: (tipo, nombre, cantidad, minimo, ubicacion)
RECURSOS = [
    ("Medicamento", "Ceftriaxona 1 g ampolla", 24, 10, "Farmacia piso 2"),
    ("Medicamento", "Acetaminofén 500 mg tableta", 120, 50, "Farmacia piso 2"),
    ("Medicamento", "Furosemida 20 mg ampolla", 8, 10, "Farmacia piso 2"),
    ("Medicamento", "Insulina cristalina frasco", 5, 3, "Nevera piso 2"),
    ("Insumo", "Guantes de nitrilo (caja)", 14, 5, "Almacén piso 2"),
    ("Insumo", "Jeringa 5 ml", 60, 40, "Almacén piso 2"),
    ("Insumo", "Catéter periférico N.º 20", 9, 15, "Almacén piso 2"),
    ("Insumo", "Gasas estériles (paquete)", 30, 20, "Almacén piso 2"),
    ("Camilla", "Camillas de transporte disponibles", 2, 1, "Pasillo piso 2"),
]

# Pacientes del portal (atención virtual). Ingresan con su documento.
# (documento, nombre, profesional asignado)
PACIENTES_PORTAL = [
    ("1001", "Luz Marina Ospina", "Dr. Camilo Rojas"),
    ("1002", "Pedro Gaviria", "Dra. Natalia Vélez"),
    ("1003", "Sandra Muñoz", "Dr. Camilo Rojas"),
]

# Citas de ejemplo: (documento, dias desde hoy, hora, motivo, estado)
CITAS = [
    ("1001", 1, "09:00", "Explicación de resultados de laboratorio", "Programada"),
    ("1003", 2, "10:30", "Control después del alta", "Programada"),
]

# Mensajes de ejemplo en el chat de la primera cita: (cita, autor, hora, texto)
MENSAJES = [
    (1, "Luz Marina Ospina", "08:12", "Buenos días doctor, ya tengo los resultados del laboratorio."),
    (1, "Dr. Camilo Rojas", "08:20", "Buenos días. Los reviso y mañana a las 9 los explicamos por videollamada."),
]

# Faltantes reportados por enfermeria: (recurso, hora, usuario, nota)
SOLICITUDES = [
    ("Furosemida 20 mg ampolla", "06:40", "Enf. Paula Ríos", "No alcanza para las dosis de la noche."),
]


def cargar(db, hora_demo=None):
    """Inserta todos los datos de prueba. No hace commit.
    Con hora_demo el reloj del sistema queda fijo en hoy a esa hora."""
    hoy = date.today()
    hoy_txt = hoy.strftime("%d/%m/%Y")
    reloj = datetime.combine(hoy, datetime.strptime(hora_demo, "%H:%M").time()) if hora_demo else None

    for clave, nombre in ROLES:
        db.execute("INSERT INTO roles VALUES (?,?)", (clave, nombre))
        for permiso in PERMISOS_POR_ROL.get(clave, []):
            db.execute("INSERT INTO permisos VALUES (?,?)", (clave, permiso))
    for nombre, documento, rol, turno in PERSONAL:
        db.execute("INSERT INTO personal (nombre, documento, rol, turno, activo) VALUES (?,?,?,?,1)",
                   (nombre, documento, rol, turno))

    ids = {}
    for p in HOSPITALIZADOS:
        ingreso = (hoy - timedelta(days=p["dia"] - 1)).isoformat()
        cur = db.execute("INSERT INTO pacientes (documento,cama,nombre,edad,diagnostico,ingreso,alergias,estado,"
                         "medico,enfermera) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (p["doc"], p["cama"], p["nombre"], p["edad"], p["dx"], ingreso, p["alergias"], p["estado"],
                          p["medico"], p["enfermera"]))
        pid = ids[p["cama"]] = cur.lastrowid
        # "PA ... (11:30)" -> registro de signos de hoy a las 11:30 tomado por su enfermera
        texto, hora = p["signos"].rsplit(" (", 1)
        db.execute("INSERT INTO signos (paciente_id,fecha,hora,texto,autor) VALUES (?,?,?,?,?)",
                   (pid, hoy.isoformat(), hora.rstrip(")"), texto, p["enfermera"]))
        for hora, nombre, estado, quien in p["meds"]:
            registro = "%s %s" % (quien, hora) if estado == "A" else ""
            db.execute("INSERT INTO medicamentos (paciente_id,fecha,hora,nombre,estado,registro,motivo) VALUES (?,?,?,?,?,?,'')",
                       (pid, hoy.isoformat(), hora, nombre, estado, registro))
        for hora, texto, autor in p["novedades"]:
            db.execute("INSERT INTO novedades (paciente_id,fecha,hora,texto,autor) VALUES (?,?,?,?,?)",
                       (pid, hoy.isoformat(), hora, texto, autor))
        for texto, hecho in p["pendientes"]:
            db.execute("INSERT INTO pendientes (paciente_id,texto,hecho,hecho_por) VALUES (?,?,?,?)",
                       (pid, texto, hecho, p["enfermera"] if hecho else ""))

    for tipo, entrega, recibe, camas, nota in ENTREGAS_DE_HOY:
        cur = db.execute("INSERT INTO entregas (tipo,fecha,hora,turno,entrega,recibe,observaciones,estado,recibida) "
                         "VALUES (?,?,?,?,?,?,?,'Recibida','07:05')",
                         (tipo, hoy_txt, "06:50", "Noche → Mañana", entrega, recibe, nota))
        for cama in camas:
            db.execute("INSERT INTO entrega_pacientes (entrega_id,paciente_id,nota) VALUES (?,?,'')", (cur.lastrowid, ids[cama]))

    for numero, ubicacion in CAMAS:
        db.execute("INSERT INTO camas VALUES (?,?)", (numero, ubicacion))
    for r in RECURSOS:
        db.execute("INSERT INTO recursos (tipo,nombre,cantidad,minimo,ubicacion) VALUES (?,?,?,?,?)", r)
    for recurso, h, usuario, nota in SOLICITUDES:
        rid = db.execute("SELECT id FROM recursos WHERE nombre=?", (recurso,)).fetchone()[0]
        db.execute("INSERT INTO solicitudes (recurso_id,fecha,usuario,nota,estado) VALUES (?,?,?,?,'Abierta')",
                   (rid, hoy_txt + " " + h, usuario, nota))

    for doc, nombre, prof in PACIENTES_PORTAL:
        db.execute("INSERT INTO portal VALUES (?,?,?)", (doc, nombre, prof))
    for doc, dias, h, motivo, estado in CITAS:
        prof = db.execute("SELECT profesional FROM portal WHERE documento=?", (doc,)).fetchone()[0]
        db.execute("INSERT INTO citas (documento,profesional,fecha,hora,motivo,estado,sala) VALUES (?,?,?,?,?,?,?)",
                   (doc, prof, (hoy + timedelta(days=dias)).isoformat(), h, motivo, estado, nueva_sala()))
    for m in MENSAJES:
        db.execute("INSERT INTO mensajes (cita_id,autor,hora,texto) VALUES (?,?,?,?)", m)

    db.execute("INSERT INTO config VALUES ('reloj', ?)", (reloj.strftime("%Y-%m-%d %H:%M") if reloj else "",))
