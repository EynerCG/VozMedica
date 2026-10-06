"""Portal clinico (/clinica): enfermeria, medicos y recepcion."""

from flask import Blueprint

from ...auth import exigir_personal

bp = Blueprint("clinica", __name__, url_prefix="/clinica")
bp.before_request(exigir_personal)

# Los modulos registran sus rutas en bp al importarse
from . import citas, pacientes, recursos, turnos  # noqa: E402,F401
