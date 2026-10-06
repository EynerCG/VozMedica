"""Punto de entrada para desarrollo.

    pip install -r requirements.txt
    python run.py

Abrir en el navegador: http://127.0.0.1:5000
"""

from vozmedica import create_app
from vozmedica.db import base_actualizada, crear_base

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        if not base_actualizada():
            crear_base()
            print("Base de datos creada con los datos de prueba.")
    print("VozMedica corriendo en http://127.0.0.1:5000")
    app.run(debug=True)
