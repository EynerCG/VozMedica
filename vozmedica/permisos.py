"""Catalogo de permisos y menus de cada portal.

Que permisos tiene cada rol se guarda en la tabla `permisos` y lo edita el administrador.
Aqui solo se define que permisos existen y que pantalla abre cada uno.
"""

# (clave, nombre, descripcion, grupo)
PERMISOS = [
    ("ver_censo", "Ver censo", "Lista de pacientes hospitalizados", "Pacientes"),
    ("ver_ficha", "Ver ficha clínica", "Signos, alergias, medicamentos y novedades", "Pacientes"),
    ("editar_ficha", "Editar ficha clínica", "Ingresos, signos, novedades, pendientes, estado y cambio de cama", "Pacientes"),
    ("administrar_medicamentos", "Administrar medicamentos", "Registrar dosis aplicadas o no aplicadas", "Pacientes"),
    ("ordenes_medicas", "Órdenes médicas", "Formular y suspender medicamentos, dar de alta", "Pacientes"),
    ("entrega_turno", "Entregar turno", "Hacer la entrega de turno", "Turnos"),
    ("ver_historial_turnos", "Ver historial de turnos", "Consultar entregas anteriores", "Turnos"),
    ("usar_recursos", "Usar recursos", "Ver disponibilidad, registrar uso y reportar faltantes", "Recursos"),
    ("atender_citas", "Atender citas virtuales", "Sus citas, chat y videollamada", "Citas"),
    ("agenda_servicio", "Gestionar agenda", "Ver todas las citas, agendar y cancelar por el paciente", "Citas"),
    ("admin_inventario", "Administrar inventario", "Entradas, mínimos, ubicaciones y solicitudes", "Administración"),
    ("admin_personal", "Administrar personal", "Empleados, roles y permisos", "Administración"),
]
CLAVES = [p[0] for p in PERMISOS]

# Menus: (ruta, texto, texto corto para celular, icono, permiso)
MENU_CLINICA = [
    ("clinica.censo", "Pacientes", "Pacientes", "pacientes", "ver_censo"),
    ("clinica.entrega", "Entrega de turno", "Turno", "turno", "entrega_turno"),
    ("clinica.historial", "Historial de turnos", "Historial", "historial", "ver_historial_turnos"),
    ("clinica.recursos", "Recursos", "Recursos", "paquete", "usar_recursos"),
    ("clinica.citas", "Mis citas virtuales", "Citas", "video", "atender_citas"),
    ("clinica.agenda", "Agenda del servicio", "Agenda", "calendario", "agenda_servicio"),
]
MENU_ADMIN = [
    ("admin.resumen", "Resumen", "Resumen", "panel", "admin_inventario"),
    ("admin.recursos", "Inventario", "Inventario", "paquete", "admin_inventario"),
    ("admin.movimientos", "Movimientos", "Movim.", "flechas", "admin_inventario"),
    ("admin.solicitudes", "Solicitudes", "Solicitudes", "bandeja", "admin_inventario"),
    ("admin.personal", "Personal", "Personal", "pacientes", "admin_personal"),
    ("admin.roles", "Roles y permisos", "Roles", "escudo", "admin_personal"),
]

# Pantallas que se marcan en el menu como parte de otra
ACTIVO = {"clinica.ficha": "clinica.censo", "clinica.registrar_paciente": "clinica.censo",
          "consulta.chat": "clinica.citas"}

# Orden en que se busca la pantalla de inicio de cada empleado
INICIOS = [
    ("clinica.censo", "ver_censo"),
    ("clinica.citas", "atender_citas"),
    ("clinica.agenda", "agenda_servicio"),
    ("clinica.entrega", "entrega_turno"),
    ("clinica.recursos", "usar_recursos"),
    ("clinica.historial", "ver_historial_turnos"),
    ("admin.resumen", "admin_inventario"),
    ("admin.personal", "admin_personal"),
]


def agrupados():
    """[(grupo, [(clave, nombre, descripcion), ...]), ...] para la matriz de permisos."""
    grupos = []
    for clave, nombre, descripcion, grupo in PERMISOS:
        if not grupos or grupos[-1][0] != grupo:
            grupos.append((grupo, []))
        grupos[-1][1].append((clave, nombre, descripcion))
    return grupos
