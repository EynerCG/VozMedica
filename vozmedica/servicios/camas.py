"""Camas del servicio. Una cama esta ocupada si hay un paciente sin alta en ella."""

from ..db import conectar

_LIBRES = """SELECT c.* FROM camas c
             WHERE NOT EXISTS (SELECT 1 FROM pacientes p WHERE p.cama = c.numero AND p.alta IS NULL)
             ORDER BY c.numero"""


def disponibles():
    return conectar().execute(_LIBRES).fetchall()


def contar_libres():
    return len(disponibles())


def esta_disponible(numero):
    return any(c["numero"] == numero for c in disponibles())
