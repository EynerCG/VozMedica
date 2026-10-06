"""Recursos hospitalarios: inventario, movimientos y solicitudes de faltantes."""

from ..db import conectar
from ..errores import Advertencia
from ..utils import es_numero
from . import camas, reloj

TIPOS_RECURSO = [("Medicamento", "Medicamentos"), ("Insumo", "Insumos"), ("Camilla", "Camas y camillas")]


def todos(tipo=None, solo_bajos=False):
    sql, args = "SELECT * FROM recursos WHERE 1=1", []
    if tipo in dict(TIPOS_RECURSO):
        sql += " AND tipo=?"
        args.append(tipo)
    if solo_bajos:
        sql += " AND cantidad <= minimo"
    return conectar().execute(sql + " ORDER BY tipo, nombre", args).fetchall()


def obtener(rid):
    return conectar().execute("SELECT * FROM recursos WHERE id=?", (rid,)).fetchone()


def contar_por_tipo(filas):
    return {clave: len([r for r in filas if r["tipo"] == clave]) for clave, _ in TIPOS_RECURSO}


def contar_alertas():
    """(recursos bajo el minimo, solicitudes abiertas)."""
    db = conectar()
    return (db.execute("SELECT COUNT(*) FROM recursos WHERE cantidad <= minimo").fetchone()[0],
            db.execute("SELECT COUNT(*) FROM solicitudes WHERE estado='Abierta'").fetchone()[0])


# ---------- Movimientos ----------

def mover(rid, cantidad, entrada, motivo, usuario):
    """Registra una entrada o salida. Si la entrada deja el recurso por encima del minimo,
    cierra las solicitudes abiertas. Devuelve (recurso, cambio, solicitudes cerradas)."""
    r = obtener(rid)
    if r is None:
        raise Advertencia("Ese recurso ya no existe.")
    if not es_numero(cantidad, 1):
        raise Advertencia("Indique la cantidad con un número mayor que cero.")
    if not entrada and not motivo:
        raise Advertencia("Indique el motivo de la salida (por ejemplo: vencimiento, daño, traslado a otro servicio).")
    cambio = int(cantidad) if entrada else -int(cantidad)
    if r["cantidad"] + cambio < 0:
        raise Advertencia("Solo hay %d disponibles de %s. Revise la cantidad." % (r["cantidad"], r["nombre"]))
    db = conectar()
    db.execute("UPDATE recursos SET cantidad = cantidad + ? WHERE id=?", (cambio, rid))
    db.execute("INSERT INTO movimientos (recurso_id,fecha,cambio,motivo,usuario) VALUES (?,?,?,?,?)",
               (rid, reloj.marca(), cambio, motivo or "Entrada", usuario))
    cerradas = 0
    if entrada and r["cantidad"] + cambio > r["minimo"]:
        cerradas = db.execute("UPDATE solicitudes SET estado='Atendida' WHERE recurso_id=? AND estado='Abierta'",
                              (rid,)).rowcount
    db.commit()
    return r, cambio, cerradas


def movimientos(tipo=None, limite=200):
    sql, args = "SELECT m.*, r.nombre, r.tipo FROM movimientos m JOIN recursos r ON r.id = m.recurso_id", []
    if tipo in dict(TIPOS_RECURSO):
        sql += " WHERE r.tipo=?"
        args.append(tipo)
    return conectar().execute(sql + " ORDER BY m.id DESC LIMIT ?", args + [limite]).fetchall()


# ---------- Administracion del inventario ----------

def crear(tipo, nombre, cantidad, minimo, ubicacion):
    if tipo not in dict(TIPOS_RECURSO) or not nombre or not es_numero(cantidad) or not es_numero(minimo):
        raise Advertencia("Para agregar el recurso complete tipo, nombre, cantidad y mínimo (con números).")
    db = conectar()
    if db.execute("SELECT 1 FROM recursos WHERE lower(nombre)=lower(?)", (nombre,)).fetchone():
        raise Advertencia("Ya existe un recurso llamado %s. Registre una entrada en lugar de crearlo de nuevo." % nombre)
    db.execute("INSERT INTO recursos (tipo,nombre,cantidad,minimo,ubicacion) VALUES (?,?,?,?,?)",
               (tipo, nombre, int(cantidad), int(minimo), ubicacion))
    db.commit()


def editar(rid, minimo, ubicacion):
    if obtener(rid) is None:
        raise Advertencia("Ese recurso ya no existe.")
    if not es_numero(minimo):
        raise Advertencia("El mínimo debe ser un número (0 o más).")
    db = conectar()
    db.execute("UPDATE recursos SET minimo=?, ubicacion=? WHERE id=?", (int(minimo), ubicacion, rid))
    db.commit()


def resumen():
    """Datos del tablero de administracion."""
    db = conectar()
    bajos = todos(solo_bajos=True)
    abiertas = solicitudes(solo_abiertas=True)
    return {
        "bajos": bajos,
        "solicitudes": abiertas,
        "movimientos": movimientos(limite=6),
        "kpi": {
            "bajos": len(bajos),
            "camas": camas.contar_libres(),
            "solicitudes": len(abiertas),
            "mov_hoy": db.execute("SELECT COUNT(*) FROM movimientos WHERE fecha LIKE ?", (reloj.hoy_texto() + "%",)).fetchone()[0],
        },
    }


# ---------- Solicitudes de faltantes ----------

def solicitudes(solo_abiertas=False):
    sql = """SELECT s.*, r.nombre, r.cantidad, r.minimo FROM solicitudes s JOIN recursos r ON r.id = s.recurso_id"""
    if solo_abiertas:
        return conectar().execute(sql + " WHERE s.estado='Abierta' ORDER BY s.id DESC").fetchall()
    return conectar().execute(sql + " ORDER BY s.estado = 'Atendida', s.id DESC LIMIT 100").fetchall()


def ids_con_solicitud_abierta():
    return {s["recurso_id"] for s in conectar().execute("SELECT recurso_id FROM solicitudes WHERE estado='Abierta'").fetchall()}


def reportar_faltante(rid, usuario, nota):
    """Crea la solicitud. Devuelve (recurso, creada); creada es False si ya habia una abierta."""
    r = obtener(rid)
    if r is None:
        raise Advertencia("Ese recurso ya no existe.")
    db = conectar()
    if db.execute("SELECT 1 FROM solicitudes WHERE recurso_id=? AND estado='Abierta'", (rid,)).fetchone():
        return r, False
    db.execute("INSERT INTO solicitudes (recurso_id,fecha,usuario,nota,estado) VALUES (?,?,?,?,'Abierta')",
               (rid, reloj.marca(), usuario, nota))
    db.commit()
    return r, True


def marcar_solicitud_atendida(sid):
    db = conectar()
    db.execute("UPDATE solicitudes SET estado='Atendida' WHERE id=?", (sid,))
    db.commit()
