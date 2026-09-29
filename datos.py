# Datos de prueba para la demo. Todas las personas son FICTICIAS.

# Personal de salud que puede ingresar a la plataforma
PERSONAL = [
    ("Enf. Laura Gómez", "Enfermería"),
    ("Enf. Andrés Salazar", "Enfermería"),
    ("Enf. Paula Ríos", "Enfermería"),
    ("Dr. Camilo Rojas", "Medicina interna"),
    ("Dra. Natalia Vélez", "Medicina general"),
]

# Pacientes hospitalizados
# medicamentos: (hora, nombre, estado, registro)  estado: A = administrado, P = pendiente
# novedades: (hora, texto, autor)
# pendientes: (texto, hecho)
HOSPITALIZADOS = [
    {"cama": "201", "nombre": "María Restrepo", "edad": 74, "dx": "Neumonía adquirida en la comunidad", "dia": 3,
     "alergias": "PENICILINA", "estado": "vigilancia",
     "signos": "PA 128/76 - FC 96 - FR 22 - T 37.9 - SatO2 91% (11:30)",
     "meds": [("06:00", "Ceftriaxona 1 g IV", "A", "Enf. Paula Ríos"),
              ("08:00", "Enoxaparina 40 mg SC", "A", "Enf. Laura Gómez"),
              ("12:00", "Acetaminofén 1 g VO", "P", ""),
              ("14:00", "Nebulización salbutamol 5 mg", "P", "")],
     "novedades": [("03:10", "Saturación 88%. Se aumenta oxígeno a 3 L.", "Enf. Paula Ríos"),
                   ("10:15", "Pico febril 38.4, se toman hemocultivos.", "Enf. Laura Gómez")],
     "pendientes": [("Reclamar resultado de hemocultivos", 0), ("Rx de tórax de control", 0)]},

    {"cama": "202", "nombre": "Jorge Cardona", "edad": 61, "dx": "Diabetes descompensada", "dia": 2,
     "alergias": "Ninguna", "estado": "estable",
     "signos": "PA 134/82 - FC 82 - FR 18 - T 36.6 - SatO2 96% (11:00)",
     "meds": [("07:00", "Insulina glargina 20 UI SC", "A", "Enf. Laura Gómez"),
              ("12:00", "Insulina cristalina según glucometría", "P", ""),
              ("13:00", "Metformina 850 mg VO", "P", "")],
     "novedades": [("06:30", "Glucometría 245 mg/dl, se aplica esquema.", "Enf. Paula Ríos")],
     "pendientes": [("Glucometría pre-almuerzo", 0), ("Educación en insulina", 1)]},

    {"cama": "205", "nombre": "Hernán Villa", "edad": 80, "dx": "Insuficiencia cardiaca descompensada", "dia": 5,
     "alergias": "AINES", "estado": "critico",
     "signos": "PA 96/58 - FC 112 - FR 26 - T 36.4 - SatO2 89% (12:10)",
     "meds": [("06:00", "Furosemida 40 mg IV", "A", "Enf. Paula Ríos"),
              ("10:00", "Espironolactona 25 mg VO", "P", ""),
              ("12:00", "Furosemida 40 mg IV", "P", "")],
     "novedades": [("12:10", "Disnea en reposo, se avisa a médico de turno.", "Enf. Laura Gómez")],
     "pendientes": [("Balance de líquidos c/6h", 0), ("Valoración por cardiología", 0)]},

    {"cama": "207", "nombre": "Carlos Arango", "edad": 67, "dx": "ACV isquémico en estudio", "dia": 1,
     "alergias": "Ninguna", "estado": "vigilancia",
     "signos": "PA 152/90 - FC 70 - FR 16 - T 36.5 - SatO2 95% (11:45)",
     "meds": [("08:00", "ASA 100 mg VO", "A", "Enf. Laura Gómez"),
              ("21:00", "Atorvastatina 40 mg VO", "P", "")],
     "novedades": [("05:50", "Escala neurológica sin cambios.", "Enf. Paula Ríos")],
     "pendientes": [("TAC de cráneo de control", 0)]},
]

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
    ("Camilla", "Camas libres en el servicio", 3, 2, "Medicina interna"),
]

# Pacientes del portal (atención virtual). Ingresan con su documento.
# (documento, nombre, profesional asignado)
PACIENTES_PORTAL = [
    ("1001", "Luz Marina Ospina", "Dr. Camilo Rojas"),
    ("1002", "Pedro Gaviria", "Dra. Natalia Vélez"),
    ("1003", "Sandra Muñoz", "Dr. Camilo Rojas"),
]

# Citas de ejemplo: (documento, fecha, hora, motivo, estado)
CITAS = [
    ("1001", "2026-10-02", "09:00", "Explicación de resultados de laboratorio", "Programada"),
    ("1003", "2026-10-01", "15:30", "Control después del alta", "Programada"),
]

# Mensajes de ejemplo en el chat de la primera cita: (cita, autor, hora, texto)
MENSAJES = [
    (1, "Luz Marina Ospina", "08:12", "Buenos días doctor, ya tengo los resultados del laboratorio."),
    (1, "Dr. Camilo Rojas", "08:20", "Buenos días. Los reviso y el jueves a las 9 los explicamos por videollamada."),
]
