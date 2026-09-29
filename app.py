# VozMedica - Plataforma web (MVP)
# Proyecto Integrador I - Ingenieria de Sistemas UdeA
#
# Modulos:
#   1. Pacientes y entrega de turno
#   2. Recursos hospitalarios (medicamentos, insumos, camillas)
#   3. Atencion virtual (citas, chat y videollamada)
#
# Para correrlo:  pip install flask   y luego   python app.py
# Abrir en el navegador: http://127.0.0.1:5000

import os
import random
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, g

import datos

app = Flask(__name__)
app.secret_key = "vozmedica-proyecto-integrador"

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vozmedica.db")

# Hora fija para la demo (asi siempre se ven medicamentos atrasados).
# Poner None para usar la hora real del computador.
HORA_DEMO = "12:40"

TURNOS = [("Mañana", "07:00", "13:00"), ("Tarde", "13:00", "19:00"), ("Noche", "19:00", "07:00")]
ESTADOS = {"estable": "Estable", "vigilancia": "Vigilancia", "critico": "CRITICO"}


# =============== BASE DE DATOS ===============

def conectar():
    if "db" not in g:
        g.db = sqlite3.connect(BASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def cerrar(e):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def crear_base():
    """Crea las tablas y carga los datos de prueba (borra lo que hubiera)."""
    db = sqlite3.connect(BASE)
    db.executescript("""
    DROP TABLE IF EXISTS personal;      DROP TABLE IF EXISTS pacientes;
    DROP TABLE IF EXISTS medicamentos;  DROP TABLE IF EXISTS novedades;
    DROP TABLE IF EXISTS pendientes;    DROP TABLE IF EXISTS entregas;
    DROP TABLE IF EXISTS recursos;      DROP TABLE IF EXISTS movimientos;
    DROP TABLE IF EXISTS portal;        DROP TABLE IF EXISTS citas;
    DROP TABLE IF EXISTS mensajes;      DROP TABLE IF EXISTS config;

    CREATE TABLE personal (id INTEGER PRIMARY KEY, nombre TEXT, area TEXT);
    CREATE TABLE pacientes (id INTEGER PRIMARY KEY, cama TEXT, nombre TEXT, edad INTEGER,
        diagnostico TEXT, dia INTEGER, alergias TEXT, estado TEXT, signos TEXT);
    CREATE TABLE medicamentos (id INTEGER PRIMARY KEY, paciente_id INTEGER, hora TEXT,
        nombre TEXT, estado TEXT, registro TEXT);
    CREATE TABLE novedades (id INTEGER PRIMARY KEY, paciente_id INTEGER, hora TEXT, texto TEXT, autor TEXT);
    CREATE TABLE pendientes (id INTEGER PRIMARY KEY, paciente_id INTEGER, texto TEXT, hecho INTEGER);
    CREATE TABLE entregas (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, turno TEXT, entrega TEXT,
        recibe TEXT, pacientes INTEGER, pendientes INTEGER, observaciones TEXT);
    CREATE TABLE recursos (id INTEGER PRIMARY KEY, tipo TEXT, nombre TEXT, cantidad INTEGER,
        minimo INTEGER, ubicacion TEXT);
    CREATE TABLE movimientos (id INTEGER PRIMARY KEY, recurso_id INTEGER, fecha TEXT, cambio INTEGER,
        motivo TEXT, usuario TEXT);
    CREATE TABLE portal (documento TEXT PRIMARY KEY, nombre TEXT, profesional TEXT);
    CREATE TABLE citas (id INTEGER PRIMARY KEY, documento TEXT, profesional TEXT, fecha TEXT, hora TEXT,
        motivo TEXT, estado TEXT, sala TEXT);
    CREATE TABLE mensajes (id INTEGER PRIMARY KEY, cita_id INTEGER, autor TEXT, hora TEXT, texto TEXT);
    CREATE TABLE config (clave TEXT PRIMARY KEY, valor TEXT);
    """)
    for nombre, area in datos.PERSONAL:
        db.execute("INSERT INTO personal (nombre, area) VALUES (?,?)", (nombre, area))

    for p in datos.HOSPITALIZADOS:
        cur = db.execute("INSERT INTO pacientes (cama,nombre,edad,diagnostico,dia,alergias,estado,signos) VALUES (?,?,?,?,?,?,?,?)",
                         (p["cama"], p["nombre"], p["edad"], p["dx"], p["dia"], p["alergias"], p["estado"], p["signos"]))
        pid = cur.lastrowid
        for m in p["meds"]:
            db.execute("INSERT INTO medicamentos (paciente_id,hora,nombre,estado,registro) VALUES (?,?,?,?,?)", (pid,) + m)
        for n in p["novedades"]:
            db.execute("INSERT INTO novedades (paciente_id,hora,texto,autor) VALUES (?,?,?,?)", (pid,) + n)
        for t in p["pendientes"]:
            db.execute("INSERT INTO pendientes (paciente_id,texto,hecho) VALUES (?,?,?)", (pid,) + t)

    for r in datos.RECURSOS:
        db.execute("INSERT INTO recursos (tipo,nombre,cantidad,minimo,ubicacion) VALUES (?,?,?,?,?)", r)

    for doc, nombre, prof in datos.PACIENTES_PORTAL:
        db.execute("INSERT INTO portal VALUES (?,?,?)", (doc, nombre, prof))
    for doc, fecha, hora, motivo, estado in datos.CITAS:
        prof = db.execute("SELECT profesional FROM portal WHERE documento=?", (doc,)).fetchone()[0]
        db.execute("INSERT INTO citas (documento,profesional,fecha,hora,motivo,estado,sala) VALUES (?,?,?,?,?,?,?)",
                   (doc, prof, fecha, hora, motivo, estado, nueva_sala()))
    for m in datos.MENSAJES:
        db.execute("INSERT INTO mensajes (cita_id,autor,hora,texto) VALUES (?,?,?,?)", m)

    db.execute("INSERT INTO entregas (fecha,hora,turno,entrega,recibe,pacientes,pendientes,observaciones) VALUES (?,?,?,?,?,?,?,?)",
               (hoy(), "07:05", "Noche - Mañana", "Enf. Paula Ríos", "Enf. Laura Gómez", 4, 4, "Cama 207 pendiente de TAC."))
    db.execute("INSERT INTO config VALUES ('turno','0')")
    db.execute("INSERT INTO config VALUES ('hora', ?)", (HORA_DEMO or "",))
    db.commit()
    db.close()


def leer_config(clave):
    return conectar().execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()["valor"]


def guardar_config(clave, valor):
    db = conectar()
    db.execute("UPDATE config SET valor=? WHERE clave=?", (str(valor), clave))
    db.commit()


# =============== FUNCIONES DE APOYO ===============

def hoy():
    return datetime.now().strftime("%d/%m/%Y")


def nueva_sala():
    # Nombre de sala para la videollamada (Jitsi Meet es gratis y no necesita cuenta)
    return "VozMedica-%06d" % random.randint(0, 999999)


def hora_actual():
    try:
        h = leer_config("hora")
    except Exception:
        h = ""
    return h or datetime.now().strftime("%H:%M")


def a_minutos(h):
    partes = h.split(":")
    return int(partes[0]) * 60 + int(partes[1])


def estado_medicamento(m):
    """Devuelve (texto, clase css) del medicamento."""
    if m["estado"] == "A":
        return ("Administrado", "verde")
    diferencia = a_minutos(m["hora"]) - a_minutos(hora_actual())
    if -600 < diferencia < 0:
        return ("ATRASADO", "rojo")
    return ("Pendiente", "naranja")


def contar_atrasados(pid):
    meds = conectar().execute("SELECT * FROM medicamentos WHERE paciente_id=? AND estado='P'", (pid,)).fetchall()
    return len([m for m in meds if estado_medicamento(m)[0] == "ATRASADO"])


def contar_pendientes(pid):
    return conectar().execute("SELECT COUNT(*) FROM pendientes WHERE paciente_id=? AND hecho=0", (pid,)).fetchone()[0]


def es_personal():
    return session.get("rol") == "personal"


def es_paciente():
    return session.get("rol") == "paciente"


@app.before_request
def revisar_ingreso():
    # Solo la pagina de ingreso y los estilos se ven sin haber entrado
    libres = ("ingreso", "salir", "static", "reiniciar")
    if request.endpoint in libres:
        return None
    if not session.get("rol"):
        return redirect(url_for("ingreso"))
    rutas_paciente = ("portal", "agendar_cita", "cancelar_cita", "chat", "enviar_mensaje")
    if es_paciente() and request.endpoint not in rutas_paciente:
        return redirect(url_for("portal"))
    return None


@app.context_processor
def variables_globales():
    datos_base = {"ESTADOS": ESTADOS, "rol": session.get("rol"), "nombre": session.get("nombre"), "hora": ""}
    if session.get("rol"):
        t = TURNOS[int(leer_config("turno"))]
        datos_base["turno_txt"] = "%s (%s-%s)" % t
        datos_base["hora"] = hora_actual()
        datos_base["alertas_recursos"] = conectar().execute(
            "SELECT COUNT(*) FROM recursos WHERE cantidad <= minimo").fetchone()[0]
    return datos_base


# =============== INGRESO ===============

@app.route("/", methods=["GET", "POST"])
def ingreso():
    db = conectar()
    if request.method == "POST":
        if request.form.get("tipo") == "personal":
            nombre = request.form.get("personal", "")
            if db.execute("SELECT 1 FROM personal WHERE nombre=?", (nombre,)).fetchone():
                session["rol"] = "personal"
                session["nombre"] = nombre
                return redirect(url_for("censo"))
            flash("ERROR: seleccione su nombre.")
        else:
            doc = request.form.get("documento", "").strip()
            fila = db.execute("SELECT * FROM portal WHERE documento=?", (doc,)).fetchone()
            if fila:
                session["rol"] = "paciente"
                session["nombre"] = fila["nombre"]
                session["documento"] = doc
                return redirect(url_for("portal"))
            flash("ERROR: documento no registrado. Pruebe con 1001, 1002 o 1003.")
    personal = db.execute("SELECT * FROM personal ORDER BY nombre").fetchall()
    return render_template("ingreso.html", personal=personal)


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("ingreso"))


@app.route("/reiniciar", methods=["POST"])
def reiniciar():
    crear_base()
    session.clear()
    flash("Datos de prueba reiniciados.")
    return redirect(url_for("ingreso"))


# =============== MODULO 1: PACIENTES Y ENTREGA DE TURNO ===============

@app.route("/censo")
def censo():
    db = conectar()
    lista = []
    for p in db.execute("SELECT * FROM pacientes ORDER BY cama").fetchall():
        lista.append({"p": p, "atrasados": contar_atrasados(p["id"]), "pendientes": contar_pendientes(p["id"])})

    ficha = None
    sel = request.args.get("p", type=int)
    if sel:
        paciente = db.execute("SELECT * FROM pacientes WHERE id=?", (sel,)).fetchone()
        if paciente:
            meds = db.execute("SELECT * FROM medicamentos WHERE paciente_id=? ORDER BY hora", (sel,)).fetchall()
            ficha = {
                "p": paciente,
                "meds": [(m, estado_medicamento(m)) for m in meds],
                "pend": db.execute("SELECT * FROM pendientes WHERE paciente_id=?", (sel,)).fetchall(),
                "nov": db.execute("SELECT * FROM novedades WHERE paciente_id=? ORDER BY id DESC", (sel,)).fetchall(),
            }
    return render_template("censo.html", lista=lista, ficha=ficha, sel=sel)


@app.route("/paciente/nuevo", methods=["POST"])
def registrar_paciente():
    f = request.form
    cama = f.get("cama", "").strip()
    nombre = f.get("nombre", "").strip()
    db = conectar()
    if not cama or not nombre:
        flash("ERROR: la cama y el nombre son obligatorios.")
        return redirect(url_for("censo"))
    if db.execute("SELECT 1 FROM pacientes WHERE cama=?", (cama,)).fetchone():
        flash("ERROR: la cama %s ya está ocupada." % cama)
        return redirect(url_for("censo"))
    edad = f.get("edad", "0").strip()
    cur = db.execute("INSERT INTO pacientes (cama,nombre,edad,diagnostico,dia,alergias,estado,signos) VALUES (?,?,?,?,1,?,?,?)",
                     (cama, nombre, int(edad) if edad.isdigit() else 0, f.get("diagnostico", "").strip(),
                      f.get("alergias", "").strip() or "Ninguna", "estable", f.get("signos", "").strip() or "Sin registro"))
    # el paciente ocupa una cama libre del servicio
    db.execute("UPDATE recursos SET cantidad = cantidad - 1 WHERE nombre='Camas libres en el servicio' AND cantidad > 0")
    db.commit()
    flash("Paciente %s registrado en la cama %s." % (nombre, cama))
    return redirect(url_for("censo", p=cur.lastrowid))


@app.route("/paciente/<int:pid>/estado", methods=["POST"])
def cambiar_estado(pid):
    nuevo = request.form.get("estado")
    if nuevo in ESTADOS:
        db = conectar()
        db.execute("UPDATE pacientes SET estado=? WHERE id=?", (nuevo, pid))
        db.commit()
        flash("Estado actualizado.")
    return redirect(url_for("censo", p=pid))


@app.route("/paciente/<int:pid>/signos", methods=["POST"])
def actualizar_signos(pid):
    texto = request.form.get("signos", "").strip()
    if texto:
        db = conectar()
        db.execute("UPDATE pacientes SET signos=? WHERE id=?", (texto + " (" + hora_actual() + ")", pid))
        db.commit()
        flash("Signos vitales actualizados.")
    return redirect(url_for("censo", p=pid))


@app.route("/paciente/<int:pid>/alta", methods=["POST"])
def dar_alta(pid):
    db = conectar()
    p = db.execute("SELECT * FROM pacientes WHERE id=?", (pid,)).fetchone()
    for tabla in ("medicamentos", "novedades", "pendientes"):
        db.execute("DELETE FROM %s WHERE paciente_id=?" % tabla, (pid,))
    db.execute("DELETE FROM pacientes WHERE id=?", (pid,))
    db.execute("UPDATE recursos SET cantidad = cantidad + 1 WHERE nombre='Camas libres en el servicio'")
    db.commit()
    flash("%s dado de alta. La cama %s queda libre." % (p["nombre"], p["cama"]))
    return redirect(url_for("censo"))


@app.route("/paciente/<int:pid>/medicamento", methods=["POST"])
def agregar_medicamento(pid):
    h = request.form.get("hora", "").strip()
    nombre = request.form.get("nombre", "").strip()
    if len(h) != 5 or h[2] != ":" or not nombre:
        flash("ERROR: escriba la hora (HH:MM) y el medicamento.")
    else:
        db = conectar()
        db.execute("INSERT INTO medicamentos (paciente_id,hora,nombre,estado,registro) VALUES (?,?,?,'P','')", (pid, h, nombre))
        db.commit()
        flash("Medicamento %s programado a las %s." % (nombre, h))
    return redirect(url_for("censo", p=pid))


@app.route("/medicamento/<int:mid>/registrar", methods=["POST"])
def registrar_medicamento(mid):
    db = conectar()
    m = db.execute("SELECT * FROM medicamentos WHERE id=?", (mid,)).fetchone()
    db.execute("UPDATE medicamentos SET estado='A', registro=? WHERE id=?", (session["nombre"] + " " + hora_actual(), mid))
    db.commit()
    flash(m["nombre"] + " registrado como administrado.")
    return redirect(url_for("censo", p=m["paciente_id"]))


@app.route("/pendiente/<int:did>/marcar", methods=["POST"])
def marcar_pendiente(did):
    db = conectar()
    d = db.execute("SELECT * FROM pendientes WHERE id=?", (did,)).fetchone()
    db.execute("UPDATE pendientes SET hecho=? WHERE id=?", (0 if d["hecho"] else 1, did))
    db.commit()
    return redirect(url_for("censo", p=d["paciente_id"]))


@app.route("/paciente/<int:pid>/pendiente", methods=["POST"])
def agregar_pendiente(pid):
    texto = request.form.get("texto", "").strip()
    if not texto:
        flash("ERROR: escriba el pendiente primero.")
    else:
        db = conectar()
        db.execute("INSERT INTO pendientes (paciente_id,texto,hecho) VALUES (?,?,0)", (pid, texto))
        db.commit()
        flash("Pendiente agregado.")
    return redirect(url_for("censo", p=pid))


@app.route("/paciente/<int:pid>/novedad", methods=["POST"])
def agregar_novedad(pid):
    texto = request.form.get("texto", "").strip()
    if not texto:
        flash("ERROR: escriba la novedad primero.")
    else:
        db = conectar()
        db.execute("INSERT INTO novedades (paciente_id,hora,texto,autor) VALUES (?,?,?,?)",
                   (pid, hora_actual(), texto, session["nombre"]))
        db.commit()
        flash("Novedad guardada.")
    return redirect(url_for("censo", p=pid))


@app.route("/entrega", methods=["GET", "POST"])
def entrega():
    db = conectar()
    turno = int(leer_config("turno"))
    siguiente = (turno + 1) % 3
    pacientes = db.execute("SELECT * FROM pacientes ORDER BY cama").fetchall()
    enfermeras = [r["nombre"] for r in db.execute("SELECT nombre FROM personal WHERE area='Enfermería' AND nombre<>?",
                                                   (session["nombre"],)).fetchall()]

    if request.method == "POST":
        revisados = [p for p in pacientes if request.form.get("rev_%d" % p["id"])]
        recibe = request.form.get("recibe", "")
        obs = request.form.get("obs", "").strip()
        if len(revisados) < len(pacientes):
            flash("ERROR: faltan %d paciente(s) por revisar." % (len(pacientes) - len(revisados)))
        elif recibe not in enfermeras:
            flash("ERROR: seleccione quién recibe el turno.")
        else:
            total = 0
            for p in pacientes:
                total += contar_pendientes(p["id"])
                total += db.execute("SELECT COUNT(*) FROM medicamentos WHERE paciente_id=? AND estado='P'", (p["id"],)).fetchone()[0]
            db.execute("INSERT INTO entregas (fecha,hora,turno,entrega,recibe,pacientes,pendientes,observaciones) VALUES (?,?,?,?,?,?,?,?)",
                       (hoy(), hora_actual(), TURNOS[turno][0] + " - " + TURNOS[siguiente][0],
                        session["nombre"], recibe, len(pacientes), total, obs or "-"))
            db.commit()
            guardar_config("turno", siguiente)
            if leer_config("hora"):
                h = a_minutos(TURNOS[siguiente][1]) + 5
                guardar_config("hora", "%02d:%02d" % (h // 60 % 24, h % 60))
            session["nombre"] = recibe   # ahora trabaja quien recibio el turno
            flash("Entrega registrada. Turno %s activo, a cargo de %s." % (TURNOS[siguiente][0], recibe))
            return redirect(url_for("historial"))

    filas = []
    for p in pacientes:
        queda = []
        for m in db.execute("SELECT * FROM medicamentos WHERE paciente_id=? AND estado='P' ORDER BY hora", (p["id"],)).fetchall():
            queda.append((m["hora"] + " " + m["nombre"], estado_medicamento(m)))
        for d in db.execute("SELECT * FROM pendientes WHERE paciente_id=? AND hecho=0", (p["id"],)).fetchall():
            queda.append((d["texto"], None))
        ultima = db.execute("SELECT * FROM novedades WHERE paciente_id=? ORDER BY id DESC LIMIT 1", (p["id"],)).fetchone()
        filas.append({"p": p, "queda": queda, "ultima": ultima})

    return render_template("entrega.html", filas=filas, actual=TURNOS[turno][0], siguiente=TURNOS[siguiente][0],
                           enfermeras=enfermeras, form=request.form)


@app.route("/historial")
def historial():
    entregas = conectar().execute("SELECT * FROM entregas ORDER BY id DESC").fetchall()
    return render_template("historial.html", entregas=entregas)


# =============== MODULO 2: RECURSOS HOSPITALARIOS ===============

@app.route("/recursos")
def recursos():
    db = conectar()
    tipo = request.args.get("tipo", "")
    if tipo:
        filas = db.execute("SELECT * FROM recursos WHERE tipo=? ORDER BY nombre", (tipo,)).fetchall()
    else:
        filas = db.execute("SELECT * FROM recursos ORDER BY tipo, nombre").fetchall()
    movimientos = db.execute("""SELECT m.*, r.nombre FROM movimientos m JOIN recursos r ON r.id = m.recurso_id
                                ORDER BY m.id DESC LIMIT 10""").fetchall()
    return render_template("recursos.html", filas=filas, tipo=tipo, movimientos=movimientos)


@app.route("/recursos/<int:rid>/movimiento", methods=["POST"])
def mover_recurso(rid):
    db = conectar()
    r = db.execute("SELECT * FROM recursos WHERE id=?", (rid,)).fetchone()
    cantidad = request.form.get("cantidad", "").strip()
    accion = request.form.get("accion")
    motivo = request.form.get("motivo", "").strip() or ("Entrada" if accion == "entrada" else "Salida")
    if not cantidad.isdigit() or int(cantidad) <= 0:
        flash("ERROR: escriba una cantidad válida.")
        return redirect(url_for("recursos"))
    cambio = int(cantidad) if accion == "entrada" else -int(cantidad)
    if r["cantidad"] + cambio < 0:
        flash("ERROR: solo hay %d de %s." % (r["cantidad"], r["nombre"]))
        return redirect(url_for("recursos"))
    db.execute("UPDATE recursos SET cantidad = cantidad + ? WHERE id=?", (cambio, rid))
    db.execute("INSERT INTO movimientos (recurso_id,fecha,cambio,motivo,usuario) VALUES (?,?,?,?,?)",
               (rid, hoy() + " " + hora_actual(), cambio, motivo, session["nombre"]))
    db.commit()
    flash("%s: %+d. Quedan %d." % (r["nombre"], cambio, r["cantidad"] + cambio))
    return redirect(url_for("recursos"))


@app.route("/recursos/nuevo", methods=["POST"])
def nuevo_recurso():
    f = request.form
    nombre = f.get("nombre", "").strip()
    cantidad = f.get("cantidad", "").strip()
    minimo = f.get("minimo", "").strip()
    if not nombre or not cantidad.isdigit() or not minimo.isdigit():
        flash("ERROR: complete nombre, cantidad y mínimo con números.")
    else:
        db = conectar()
        db.execute("INSERT INTO recursos (tipo,nombre,cantidad,minimo,ubicacion) VALUES (?,?,?,?,?)",
                   (f.get("tipo"), nombre, int(cantidad), int(minimo), f.get("ubicacion", "").strip()))
        db.commit()
        flash("Recurso %s agregado." % nombre)
    return redirect(url_for("recursos"))


# =============== MODULO 3: ATENCION VIRTUAL ===============

@app.route("/portal")
def portal():
    db = conectar()
    paciente = db.execute("SELECT * FROM portal WHERE documento=?", (session["documento"],)).fetchone()
    citas = db.execute("SELECT * FROM citas WHERE documento=? ORDER BY fecha, hora", (session["documento"],)).fetchall()
    return render_template("portal.html", paciente=paciente, citas=citas)


@app.route("/portal/agendar", methods=["POST"])
def agendar_cita():
    db = conectar()
    paciente = db.execute("SELECT * FROM portal WHERE documento=?", (session["documento"],)).fetchone()
    fecha = request.form.get("fecha", "")
    h = request.form.get("hora", "")
    motivo = request.form.get("motivo", "").strip()
    if not fecha or not h or not motivo:
        flash("ERROR: complete fecha, hora y motivo.")
    elif db.execute("SELECT 1 FROM citas WHERE profesional=? AND fecha=? AND hora=? AND estado='Programada'",
                    (paciente["profesional"], fecha, h)).fetchone():
        flash("ERROR: %s ya tiene una cita a esa hora. Elija otra." % paciente["profesional"])
    else:
        db.execute("INSERT INTO citas (documento,profesional,fecha,hora,motivo,estado,sala) VALUES (?,?,?,?,?,?,?)",
                   (paciente["documento"], paciente["profesional"], fecha, h, motivo, "Programada", nueva_sala()))
        db.commit()
        flash("Cita agendada con %s el %s a las %s." % (paciente["profesional"], fecha, h))
    return redirect(url_for("portal"))


@app.route("/cita/<int:cid>/cancelar", methods=["POST"])
def cancelar_cita(cid):
    db = conectar()
    db.execute("UPDATE citas SET estado='Cancelada' WHERE id=? AND documento=?", (cid, session.get("documento")))
    db.commit()
    flash("Cita cancelada.")
    return redirect(url_for("portal"))


@app.route("/citas")
def citas_personal():
    db = conectar()
    citas = db.execute("""SELECT c.*, p.nombre AS paciente FROM citas c JOIN portal p ON p.documento = c.documento
                          WHERE c.profesional=? ORDER BY c.fecha, c.hora""", (session["nombre"],)).fetchall()
    todas = db.execute("""SELECT c.*, p.nombre AS paciente FROM citas c JOIN portal p ON p.documento = c.documento
                          ORDER BY c.fecha, c.hora""").fetchall()
    return render_template("citas.html", citas=citas, todas=todas)


@app.route("/cita/<int:cid>/atendida", methods=["POST"])
def cita_atendida(cid):
    db = conectar()
    db.execute("UPDATE citas SET estado='Atendida' WHERE id=?", (cid,))
    db.commit()
    flash("Cita marcada como atendida.")
    return redirect(url_for("citas_personal"))


def puede_ver_cita(c):
    if es_paciente():
        return c["documento"] == session.get("documento")
    return True


@app.route("/cita/<int:cid>/chat")
def chat(cid):
    db = conectar()
    c = db.execute("""SELECT c.*, p.nombre AS paciente FROM citas c JOIN portal p ON p.documento = c.documento
                      WHERE c.id=?""", (cid,)).fetchone()
    if c is None or not puede_ver_cita(c):
        flash("ERROR: esa cita no existe.")
        return redirect(url_for("portal" if es_paciente() else "citas_personal"))
    mensajes = db.execute("SELECT * FROM mensajes WHERE cita_id=? ORDER BY id", (cid,)).fetchall()
    return render_template("chat.html", c=c, mensajes=mensajes)


@app.route("/cita/<int:cid>/mensaje", methods=["POST"])
def enviar_mensaje(cid):
    db = conectar()
    c = db.execute("SELECT * FROM citas WHERE id=?", (cid,)).fetchone()
    texto = request.form.get("texto", "").strip()
    if c and puede_ver_cita(c) and texto:
        db.execute("INSERT INTO mensajes (cita_id,autor,hora,texto) VALUES (?,?,?,?)",
                   (cid, session["nombre"], datetime.now().strftime("%H:%M"), texto))
        db.commit()
    return redirect(url_for("chat", cid=cid))


if __name__ == "__main__":
    if not os.path.exists(BASE):
        crear_base()
    print("VozMedica corriendo en http://127.0.0.1:5000")
    app.run(debug=True)
