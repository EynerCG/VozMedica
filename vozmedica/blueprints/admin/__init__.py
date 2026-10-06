"""Portal de administracion (/admin): inventario, personal, roles y permisos."""

from flask import Blueprint

from ...auth import exigir_personal

bp = Blueprint("admin", __name__, url_prefix="/admin")
bp.before_request(exigir_personal)

# Los modulos registran sus rutas en bp al importarse
from . import inventario, personal  # noqa: E402,F401
