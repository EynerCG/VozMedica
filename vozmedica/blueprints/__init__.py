"""Vistas HTTP agrupadas por portal. Cada vista lee el formulario, llama a un servicio y responde."""

from flask import redirect, request, url_for


def volver(defecto, **valores):
    """Regresa a la pagina desde donde se envio el formulario, solo si es de este mismo sitio."""
    origen = request.referrer or ""
    if origen.startswith(request.host_url):
        return redirect(origen)
    return redirect(url_for(defecto, **valores))
