"""Funciones pequeñas sin acceso a la base de datos."""

import random
from datetime import datetime

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def nueva_sala():
    # Nombre de sala para la videollamada (Jitsi Meet es gratis y no necesita cuenta)
    return "VozMedica-%06d" % random.randint(0, 999999)


def formato_fecha(texto):
    """'2026-10-02' -> 'vie 2 oct 2026'. Se usa como filtro |fecha en las plantillas."""
    try:
        d = datetime.strptime(texto, "%Y-%m-%d")
    except (ValueError, TypeError):
        return texto
    return "%s %d %s %d" % (DIAS[d.weekday()], d.day, MESES[d.month - 1], d.year)


def iniciales(nombre):
    palabras = [w for w in (nombre or "").replace(".", " ").split() if w not in ("Enf", "Dr", "Dra", "Rec", "Adm")]
    return "".join(w[0] for w in palabras[:2]).upper()


def es_numero(texto, minimo=0):
    texto = (texto or "").strip()
    return texto.isdigit() and int(texto) >= minimo


def hora_valida(texto):
    try:
        datetime.strptime(texto or "", "%H:%M")
    except ValueError:
        return False
    return len(texto) == 5
