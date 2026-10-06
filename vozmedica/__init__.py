"""VozMedica - Plataforma web (MVP)
Proyecto Integrador I - Ingenieria de Sistemas UdeA

Tres portales sobre la misma base de datos, cada uno es un blueprint:
  - clinica  (/clinica)  pacientes, entrega de turno, recursos, citas y agenda
  - admin    (/admin)    inventario, personal, roles y permisos
  - portal   (/portal)   portal del paciente
  - consulta (/cita)     chat y videollamada, compartido por paciente y profesional
  - auth     (/)         ingreso y salida
"""

import os

from flask import Flask

from config import Config


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    from . import auth, db
    from .iconos import icono
    from .servicios.pacientes import ESTADO_CLASE, ESTADOS
    from .utils import formato_fecha

    db.init_app(app)
    auth.init_app(app)
    app.jinja_env.globals.update(icono=icono, ESTADOS=ESTADOS, ESTADO_CLASE=ESTADO_CLASE)
    app.jinja_env.filters["fecha"] = formato_fecha

    from .blueprints import admin, clinica, consulta, portal
    from .blueprints import auth as auth_bp
    app.register_blueprint(auth_bp.bp)
    app.register_blueprint(clinica.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(portal.bp)
    app.register_blueprint(consulta.bp)
    return app
