"""Reloj del sistema.

En la demo (config.HORA_DEMO) la fecha y hora quedan fijas en la tabla config y solo avanzan
con la entrega de turno; asi siempre hay medicamentos atrasados para mostrar.
Sin HORA_DEMO se usa la hora real del computador.
"""

from datetime import datetime

from flask import g

from ..db import guardar_config, leer_config

FORMATO = "%Y-%m-%d %H:%M"


def es_demo():
    try:
        return bool(leer_config("reloj"))
    except Exception:
        return False


def ahora():
    if "ahora" not in g:
        valor = leer_config("reloj") if es_demo() else ""
        g.ahora = datetime.strptime(valor, FORMATO) if valor else datetime.now().replace(second=0, microsecond=0)
    return g.ahora


def hora_actual():
    return ahora().strftime("%H:%M")


def fecha_iso():
    return ahora().date().isoformat()


def marca():
    """Fecha y hora para los registros: '06/10/2026 12:40'."""
    return ahora().strftime("%d/%m/%Y %H:%M")


def hoy_texto():
    return ahora().strftime("%d/%m/%Y")


def fijar(momento):
    """Solo en la demo: mueve el reloj a ese datetime."""
    if es_demo():
        guardar_config("reloj", momento.strftime(FORMATO))
        g.pop("ahora", None)
