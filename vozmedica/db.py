"""Conexion a SQLite y creacion de la base de datos."""

import os
import sqlite3

import click
from flask import current_app, g

from . import seed

# Subir este numero cuando cambie schema.sql: las bases viejas se recrean solas al iniciar
VERSION_ESQUEMA = "6"


def conectar():
    """Conexion de la peticion actual (se cierra sola al terminar)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def cerrar(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def crear_base():
    """Crea las tablas y carga los datos de prueba (borra lo que hubiera)."""
    cerrar()
    db = sqlite3.connect(current_app.config["DATABASE"])
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    seed.cargar(db, current_app.config.get("HORA_DEMO"))
    db.execute("INSERT INTO config VALUES ('version', ?)", (VERSION_ESQUEMA,))
    db.commit()
    db.close()


def base_actualizada():
    """True si la base existe y tiene el esquema actual."""
    ruta = current_app.config["DATABASE"]
    if not os.path.exists(ruta):
        return False
    db = sqlite3.connect(ruta)
    try:
        fila = db.execute("SELECT valor FROM config WHERE clave='version'").fetchone()
    except sqlite3.Error:
        fila = None
    db.close()
    return fila is not None and fila[0] == VERSION_ESQUEMA


def leer_config(clave):
    return conectar().execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()["valor"]


def guardar_config(clave, valor):
    db = conectar()
    db.execute("UPDATE config SET valor=? WHERE clave=?", (str(valor), clave))
    db.commit()


@click.command("init-db")
def init_db_command():
    """flask --app vozmedica init-db : crea la base con los datos de prueba."""
    crear_base()
    click.echo("Base de datos creada en %s" % current_app.config["DATABASE"])


def init_app(app):
    app.teardown_appcontext(cerrar)
    app.cli.add_command(init_db_command)
