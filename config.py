"""Configuracion de la aplicacion. Los valores sensibles se leen de variables de entorno."""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # En produccion definir la variable de entorno VOZMEDICA_SECRET_KEY
    SECRET_KEY = os.environ.get("VOZMEDICA_SECRET_KEY", "vozmedica-desarrollo")
    # La base de datos vive en instance/, fuera del codigo fuente (no se sube a git)
    DATABASE = os.environ.get("VOZMEDICA_DB", os.path.join(BASE_DIR, "instance", "vozmedica.db"))
    # Hora fija para la demo (asi siempre se ven medicamentos atrasados).
    # Poner None para usar la hora real del computador y luego "Reiniciar datos de prueba".
    HORA_DEMO = "12:40"


class TestConfig(Config):
    TESTING = True
