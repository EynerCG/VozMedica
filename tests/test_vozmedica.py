"""Pruebas de punta a punta con el cliente de pruebas de Flask.

Ejecutar desde la carpeta del proyecto:
    python -m unittest -v
Cada prueba usa una base de datos temporal; no toca instance/vozmedica.db.
La demo arranca hoy a las 12:40 (config.HORA_DEMO), en la ultima hora del turno Mañana.
Ids de pacientes (orden de seed.HOSPITALIZADOS): 1=cama 201, 2=202, 3=205, 4=207, 5=203, 6=204, 7=206.
"""

import os
import re
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

from config import TestConfig
from vozmedica import create_app
from vozmedica.db import crear_base

DR = "Dr. Camilo Rojas"
ENF = "Enf. Laura Gómez"          # mañana, camas 201, 202 y 203 (pacientes 1, 2 y 5)
ENF_TARDE = "Enf. Andrés Salazar"  # su pareja en la tarde
DR_TARDE = "Dr. Julián Mesa"       # pareja del Dr. Rojas en la tarde
EQUIPO = [  # [enfermeras, medicos] por turno: Mañana, Tarde, Noche
    ["Enf. Laura Gómez", "Enf. Camila Ortiz", "Enf. Jhon Ramírez", "Dr. Camilo Rojas", "Dra. Natalia Vélez", "Dr. Felipe Castaño"],
    ["Enf. Andrés Salazar", "Enf. Valentina Mora", "Enf. Luis Cárdenas", "Dr. Julián Mesa", "Dra. Isabel Franco", "Dr. Ricardo Peña"],
    ["Enf. Paula Ríos", "Enf. Sofía Arias", "Enf. Mateo Londoño", "Dra. Sara Henao", "Dr. Esteban Vargas", "Dra. Mónica Zapata"],
]
MANANA = (date.today() + timedelta(days=1)).isoformat()
FUTURO = (date.today() + timedelta(days=30)).isoformat()


class BaseVozMedica(unittest.TestCase):
    def setUp(self):
        fd, self.ruta_db = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        class Config(TestConfig):
            DATABASE = self.ruta_db

        self.app = create_app(Config)
        with self.app.app_context():
            crear_base()
        self.c = self.app.test_client()
        self.ids = dict(self.sql("SELECT nombre, id FROM personal"))

    def tearDown(self):
        os.remove(self.ruta_db)

    # ---------- ayudas ----------
    def sql(self, consulta, *args):
        db = sqlite3.connect(self.ruta_db)
        filas = db.execute(consulta, args).fetchall()
        db.close()
        return filas

    def entrar(self, nombre):
        self.c.get("/salir")
        return self.c.post("/", data={"tipo": "personal", "personal_id": self.ids[nombre]})

    def entrar_paciente(self, documento):
        self.c.get("/salir")
        return self.c.post("/", data={"tipo": "paciente", "documento": documento})

    def post(self, url, **datos):
        return self.c.post(url, data=datos, follow_redirects=True).get_data(as_text=True)

    def texto(self, respuesta):
        return respuesta.get_data(as_text=True)

    def assertRedirige(self, url, destino):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 302, url)
        self.assertTrue(r.headers["Location"].endswith(destino), "%s -> %s" % (url, r.headers["Location"]))


class TestIngreso(BaseVozMedica):
    def test_cada_rol_llega_a_su_inicio(self):
        casos = {"Enf. Laura Gómez": "/clinica/pacientes", "Dr. Camilo Rojas": "/clinica/pacientes",
                 "Rec. Diana Torres": "/clinica/agenda", "Adm. Carolina Mejía": "/admin/"}
        for nombre, destino in casos.items():
            self.assertTrue(self.entrar(nombre).headers["Location"].endswith(destino), nombre)
        self.assertTrue(self.entrar_paciente("1001").headers["Location"].endswith("/portal/"))

    def test_documento_invalido_es_advertencia(self):
        t = self.texto(self.entrar_paciente("999"))
        self.assertIn("aviso-advertencia", t)
        self.assertNotIn("ERROR", t)

    def test_sin_sesion_vuelve_al_ingreso(self):
        for url in ("/clinica/pacientes", "/admin/", "/portal/", "/cita/1/chat"):
            self.assertRedirige(url, "/")


class TestPacientes(BaseVozMedica):
    def setUp(self):
        super().setUp()
        self.entrar("Enf. Laura Gómez")

    def test_pantallas_cargan(self):
        for url in ["/clinica/pacientes", "/clinica/paciente/1", "/clinica/pacientes/nuevo",
                    "/clinica/entrega", "/clinica/historial", "/clinica/recursos?tipo=Insumo"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_enfermera_no_entra_a_admin_ni_citas(self):
        self.assertRedirige("/admin/", "/clinica/pacientes")
        self.assertRedirige("/clinica/citas", "/clinica/pacientes")
        self.assertRedirige("/cita/1/chat", "/clinica/pacientes")

    def test_dia_de_hospitalizacion_se_calcula(self):
        self.assertIn("Día 3 de hospitalización", self.texto(self.c.get("/clinica/paciente/1")))

    def test_novedad_vacia_es_advertencia(self):
        self.assertIn("aviso-advertencia", self.post("/clinica/paciente/1/novedad", texto=""))

    def test_solo_se_ofrecen_camas_libres(self):
        t = self.texto(self.c.get("/clinica/pacientes/nuevo"))
        self.assertIn('value="208"', t)
        self.assertNotIn('value="201"', t)          # ocupada por María Restrepo
        for cama in ("201", "999"):
            t = self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", documento="5", cama=cama, nombre="X", medico=DR, enfermera=ENF)
            self.assertIn("ya no está disponible", t)

    def test_ingreso_exige_documento_y_no_duplica_paciente(self):
        self.assertIn("Faltan datos obligatorios", self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", cama="208", nombre="X", medico=DR, enfermera=ENF))
        self.assertIn("Faltan datos obligatorios", self.post("/clinica/pacientes/nuevo", documento="5", edad="40", diagnostico="", cama="208", nombre="X", medico=DR, enfermera=ENF))
        self.assertIn("Seleccione el médico tratante", self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", documento="5", cama="208", nombre="X"))
        t = self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", documento="21345678", cama="208", nombre="María Restrepo", medico=DR, enfermera=ENF)
        self.assertIn("ya está hospitalizado en la cama 201", t)
        self.assertIn("Revise la edad", self.post("/clinica/pacientes/nuevo", diagnostico="Dx", documento="5", cama="208", nombre="X",
                                                  edad="300", medico=DR, enfermera=ENF))
        # la enfermera debe ser del turno que marca el reloj (Mañana)
        self.assertIn("enfermera del turno", self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", documento="5", cama="208", nombre="X",
                                                       medico=DR, enfermera=ENF_TARDE))

    def test_registrar_dosis(self):
        # 12:00 acetaminofén: más de 30 min tarde -> Atrasado, se puede registrar
        self.assertIn("registrado como administrado", self.post("/clinica/medicamento/3/registrar"))
        # registrarlo de nuevo no sobreescribe quién lo aplicó
        self.assertIn("ya estaba registrado", self.post("/clinica/medicamento/3/registrar"))
        # 14:00 nebulización: todavía no es hora
        self.assertIn("Todavía no es hora", self.post("/clinica/medicamento/4/registrar"))
        # dosis inexistente
        self.assertIn("ya no existe", self.post("/clinica/medicamento/999/registrar"))

    def test_estados_de_dosis(self):
        t = self.texto(self.c.get("/clinica/paciente/2"))   # Jorge: 12:00 atrasado, 13:00 toca ahora
        self.assertIn("Atrasado", t)
        self.assertIn("Toca ahora", t)

    def test_enfermeria_no_formula_ni_da_alta(self):
        self.assertNotIn("Programar", self.texto(self.c.get("/clinica/paciente/1")))
        self.assertEqual(self.c.get("/clinica/paciente/1").status_code, 200)   # sí ve la ficha
        r = self.c.post("/clinica/paciente/1/alta")
        self.assertTrue(r.headers["Location"].endswith("/clinica/pacientes"))
        self.assertEqual(self.sql("SELECT alta FROM pacientes WHERE id=1")[0][0], None)
        self.c.post("/clinica/paciente/1/medicamento", data={"hora": "18:00", "nombre": "X"})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM medicamentos WHERE nombre='X'")[0][0], 0)

    def test_recursos_sin_datos_de_admin(self):
        t = self.texto(self.c.get("/clinica/recursos"))
        self.assertNotIn("Mínimo", t)
        self.assertNotIn("Farmacia piso 2", t)

    def test_registrar_uso_y_faltante(self):
        self.assertIn("Quedan 13", self.post("/clinica/recursos/5/uso", cantidad="1"))
        self.assertIn("Solo hay 13", self.post("/clinica/recursos/5/uso", cantidad="999"))
        self.assertIn("reportado", self.post("/clinica/recursos/7/faltante"))
        self.assertIn("Ya hay un reporte abierto", self.post("/clinica/recursos/7/faltante"))


class TestOrdenesMedicas(BaseVozMedica):
    def setUp(self):
        super().setUp()
        self.entrar("Dr. Camilo Rojas")

    def test_formular(self):
        self.assertIn("formulado: 1 dosis a las 18:00", self.post("/clinica/paciente/1/medicamento", hora="18:00", nombre="Dipirona 1 g IV"))
        self.assertIn("ya pasó", self.post("/clinica/paciente/1/medicamento", hora="08:00", nombre="X"))
        self.assertIn("HH:MM", self.post("/clinica/paciente/1/medicamento", hora="ab:cd", nombre="X"))
        t = self.post("/clinica/paciente/1/medicamento", fecha=MANANA, hora="08:00", nombre="Dosis de mañana")
        self.assertIn("formulado", t)
        self.assertEqual(self.c.get("/clinica/pacientes").status_code, 200)   # el censo sigue funcionando

    def test_alta_conserva_historia_y_libera_cama(self):
        self.assertIn("historia clínica se conserva", self.post("/clinica/paciente/1/alta"))
        self.assertIsNotNone(self.sql("SELECT alta FROM pacientes WHERE id=1")[0][0])
        self.assertGreater(self.sql("SELECT COUNT(*) FROM novedades WHERE paciente_id=1")[0][0], 0)
        self.assertNotIn("María Restrepo", self.texto(self.c.get("/clinica/pacientes")))
        self.assertIn('value="201"', self.texto(self.c.get("/clinica/pacientes/nuevo")))
        # despues del alta ya no se puede escribir en su ficha
        self.assertIn("ya no está hospitalizado", self.post("/clinica/paciente/1/novedad", texto="x"))
        # y el mismo paciente puede volver a ingresar
        t = self.post("/clinica/pacientes/nuevo", edad="40", diagnostico="Dx", documento="21345678", cama="208", nombre="María Restrepo", medico=DR, enfermera=ENF)
        self.assertIn("registrado en la cama 208", t)


class TestMedicoTratante(BaseVozMedica):
    def test_cada_medico_ve_primero_sus_pacientes(self):
        self.entrar(DR)
        t = self.texto(self.c.get("/clinica/pacientes"))
        self.assertIn("María Restrepo", t)                 # suya
        self.assertNotIn("Jorge Cardona", t)               # de la Dra. Vélez
        self.assertIn("Jorge Cardona", self.texto(self.c.get("/clinica/pacientes?ver=todos")))
        # enfermeria ve primero sus camas asignadas y puede ver todo el piso
        self.entrar(ENF)
        t = self.texto(self.c.get("/clinica/pacientes"))
        self.assertIn("María Restrepo", t)
        self.assertNotIn("Hernán Villa", t)                # cama de Enf. Camila Ortiz
        self.assertIn("Hernán Villa", self.texto(self.c.get("/clinica/pacientes?ver=todos")))

    def test_solo_el_tratante_formula_y_da_alta(self):
        self.entrar("Dra. Natalia Vélez")
        self.assertIn("Solo el médico tratante (Dr. Camilo Rojas)",
                      self.post("/clinica/paciente/1/medicamento", hora="18:00", nombre="X"))
        self.assertIn("Solo el médico tratante", self.post("/clinica/paciente/1/alta"))
        self.assertIn("Asumir paciente", self.texto(self.c.get("/clinica/paciente/1")))

    def test_asumir_paciente_queda_registrado(self):
        self.entrar("Dra. Natalia Vélez")
        t = self.post("/clinica/paciente/1/asumir")
        self.assertIn("Ahora usted es el médico tratante de María Restrepo", t)
        self.assertIn("Asume como médico tratante (antes: Dr. Camilo Rojas)", t)
        self.assertIn("formulado", self.post("/clinica/paciente/1/medicamento", hora="18:00", nombre="X"))
        self.assertIn("ya es el médico tratante", self.post("/clinica/paciente/1/asumir"))
        # enfermeria no puede asumir pacientes
        self.entrar("Enf. Laura Gómez")
        self.c.post("/clinica/paciente/2/asumir")
        self.assertEqual(self.sql("SELECT medico FROM pacientes WHERE id=2")[0][0], "Dra. Natalia Vélez")

    def test_medico_que_ingresa_queda_como_tratante_por_defecto(self):
        self.entrar("Dra. Natalia Vélez")
        self.assertIn('<option selected>Dra. Natalia Vélez</option>', self.texto(self.c.get("/clinica/pacientes/nuevo")))


class TestEntregaDeTurno(BaseVozMedica):
    def pantalla(self, quien):
        self.entrar(quien)
        return self.texto(self.c.get("/clinica/entrega"))

    def entregar_todo(self, quien, **cambios):
        """Marca todos sus pacientes como revisados y deja el receptor que propone la pantalla."""
        t = self.pantalla(quien)
        datos = {}
        for pid in sorted(set(re.findall(r'name="rev_(\d+)"', t))):
            datos["rev_" + pid] = "1"
            opciones = re.search(r'name="receptor_%s">(.*?)</select>' % pid, t, re.S).group(1)
            datos["receptor_" + pid] = re.search(r"<option selected>(.*?)</option>", opciones).group(1)
        datos.update(cambios)
        return self.post("/clinica/entrega", **datos)

    def recibir_todo(self, quien):
        t = self.pantalla(quien)
        for eid in re.findall(r"/clinica/entrega/(\d+)/recibir", t):
            t = self.post("/clinica/entrega/%s/recibir" % eid)
        return t

    def a_cargo(self, columna, pid):
        return self.sql("SELECT %s FROM pacientes WHERE id=?" % columna, pid)[0][0]

    def test_cada_enfermera_entrega_solo_sus_camas(self):
        t = self.pantalla(ENF)
        self.assertEqual(sorted(re.findall(r'name="rev_(\d+)"', t)), ["1", "2", "5"])
        self.assertIn("<option selected>%s</option>" % ENF_TARDE, t)   # su pareja de la tarde por defecto

    def test_entrega_incompleta(self):
        self.entrar(ENF)
        t = self.post("/clinica/entrega", rev_1="1", receptor_1=ENF_TARDE)
        self.assertIn("Falta revisar 2 pacientes antes de entregar: cama 202, 203", t)

    def test_solo_se_entrega_al_final_del_turno(self):
        self.entrar(ENF_TARDE)
        self.assertNotIn("Entregar turno", self.texto(self.c.get("/clinica/entrega")))
        self.assertIn("todavía no está por terminar", self.post("/clinica/entrega", rev_1="1"))

    def test_solo_se_entrega_al_turno_siguiente(self):
        t = self.entregar_todo(ENF, receptor_1="Enf. Paula Ríos")   # Paula es de la noche
        self.assertIn("Seleccione quién del turno Tarde recibe la cama 201", t)

    def test_entrega_de_enfermeria_en_dos_pasos(self):
        t = self.entregar_todo(ENF, nota_1="Oxígeno a 3 L")
        self.assertIn("Queda pendiente hasta que lo reciba", t)
        self.assertIn(ENF, t)                                           # sigue en su propia sesión
        self.assertEqual(self.a_cargo("enfermera", 1), ENF)            # hasta que la reciban, sigue a su cargo
        self.assertIn("No tiene pacientes por entregar", self.pantalla(ENF))
        # quien recibe entra con SU usuario: ve el aviso y la nota
        self.entrar(ENF_TARDE)
        self.assertIn("le entregó pacientes", self.texto(self.c.get("/clinica/pacientes")))
        self.assertIn("Oxígeno a 3 L", self.texto(self.c.get("/clinica/entrega")))
        self.assertIn("Esos pacientes ahora están a su cargo", self.recibir_todo(ENF_TARDE))
        for pid in (1, 2, 5):
            self.assertEqual(self.a_cargo("enfermera", pid), ENF_TARDE)
        self.assertEqual(self.a_cargo("enfermera", 3), "Enf. Camila Ortiz")   # las demas camas no cambian

    def test_solo_el_receptor_recibe_y_se_puede_anular(self):
        self.entregar_todo(ENF)
        eid = self.sql("SELECT id FROM entregas WHERE estado='Pendiente'")[0][0]
        self.entrar("Enf. Valentina Mora")
        self.assertIn("No tiene esa entrega", self.post("/clinica/entrega/%d/recibir" % eid))
        self.entrar(ENF)
        self.assertIn("Entrega anulada", self.post("/clinica/entrega/%d/anular" % eid))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM entregas WHERE estado='Pendiente'")[0][0], 0)

    def test_entrega_medica_cubre_sin_cambiar_tratante(self):
        self.assertIn("Turno entregado a %s" % DR_TARDE, self.entregar_todo(DR, nota_1="Vigilar saturación"))
        self.recibir_todo(DR_TARDE)
        self.assertEqual(self.a_cargo("medico", 1), DR)          # el tratante no cambia
        self.assertEqual(self.a_cargo("cubre", 1), DR_TARDE)
        # quien cubre puede formular; otro medico no
        self.assertIn("formulado", self.post("/clinica/paciente/1/medicamento", hora="18:00", nombre="X"))
        self.assertIn("María Restrepo", self.texto(self.c.get("/clinica/pacientes")))   # en "Mis pacientes"
        self.assertIn("Vigilar saturación", self.texto(self.c.get("/clinica/paciente/1")))
        self.entrar("Dra. Isabel Franco")
        self.assertIn("o quien lo cubre (Dr. Julián Mesa)", self.post("/clinica/paciente/1/medicamento", hora="18:00", nombre="X"))

    def test_reloj_de_la_demo(self):
        self.entrar(ENF)
        for esperado in ("13:00", "18:40", "19:00"):
            self.c.post("/clinica/reloj/adelantar")
            self.assertTrue(self.sql("SELECT valor FROM config WHERE clave='reloj'")[0][0].endswith(esperado))

    def test_un_dia_completo_vuelve_a_los_tratantes(self):
        for turno in range(3):
            for quien in EQUIPO[turno]:
                self.entregar_todo(quien)
            for quien in EQUIPO[(turno + 1) % 3]:
                self.recibir_todo(quien)
            self.c.post("/clinica/reloj/adelantar")
            self.c.post("/clinica/reloj/adelantar")
        # de noche a mañana cambio de dia y cada paciente volvio a su tratante y a su enfermera de la mañana
        self.assertTrue(self.sql("SELECT valor FROM config WHERE clave='reloj'")[0][0].startswith(MANANA))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM pacientes WHERE cubre IS NOT NULL")[0][0], 0)
        self.assertEqual(self.a_cargo("enfermera", 1), ENF)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM entregas WHERE estado='Pendiente'")[0][0], 0)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM entregas")[0][0], 6 + 18)   # 6 de la mañana + 18 del dia
        # las dosis de ayer sin aplicar siguen apareciendo como atrasadas
        self.entrar(ENF)
        self.assertIn("Atrasado", self.texto(self.c.get("/clinica/paciente/1")))


class TestReglasClinicas(BaseVozMedica):
    """Reglas de la historia clinica y de los medicamentos como en un hospital."""

    def test_signos_vitales_se_acumulan(self):
        self.entrar(ENF)
        self.post("/clinica/paciente/1/signos", signos="PA 120/80 - SatO2 93%")
        t = self.post("/clinica/paciente/1/signos", signos="PA 118/76 - SatO2 95%")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM signos WHERE paciente_id=1")[0][0], 3)
        self.assertIn("Registros anteriores (2)", t)
        self.assertEqual(self.sql("SELECT autor FROM signos WHERE paciente_id=1 ORDER BY id DESC LIMIT 1")[0][0], ENF)

    def test_novedades_cambio_de_estado_y_pendientes_quedan_firmados(self):
        self.entrar(ENF)
        t = self.post("/clinica/paciente/1/estado", estado="critico")
        self.assertIn("Estado: Vigilancia → Crítico", t)
        self.assertEqual(self.sql("SELECT fecha FROM novedades ORDER BY id DESC LIMIT 1")[0][0], date.today().isoformat())
        self.post("/clinica/pendiente/1/marcar")
        self.assertTrue(self.sql("SELECT hecho_por FROM pendientes WHERE id=1")[0][0].startswith(ENF))

    def test_dosis_no_aplicada_exige_motivo(self):
        self.entrar(ENF)
        self.assertIn("Indique por qué", self.post("/clinica/medicamento/3/no-aplicada", motivo="Otro", detalle=""))
        t = self.post("/clinica/medicamento/3/no-aplicada", motivo="Paciente en ayuno / NPO")
        self.assertIn("NO aplicado", t)
        self.assertEqual(self.sql("SELECT estado, motivo FROM medicamentos WHERE id=3")[0], ("N", "Paciente en ayuno / NPO"))
        self.assertIn("ya estaba registrada", self.post("/clinica/medicamento/3/no-aplicada", motivo="Otro", detalle="x"))

    def test_el_medico_no_registra_dosis_aplicadas(self):
        self.entrar(DR)
        self.c.post("/clinica/medicamento/3/registrar")
        self.assertEqual(self.sql("SELECT estado FROM medicamentos WHERE id=3")[0][0], "P")
        self.assertNotIn(">Aplicada<", self.texto(self.c.get("/clinica/paciente/1")))

    def test_formular_con_frecuencia_y_suspender_la_orden(self):
        self.entrar(DR)
        t = self.post("/clinica/paciente/1/medicamento", nombre="Dipirona 1 g IV", hora="18:00", repetir="8", dias="2")
        self.assertIn("6 dosis desde las 18:00", t)
        ids = [f[0] for f in self.sql("SELECT id FROM medicamentos WHERE nombre='Dipirona 1 g IV' ORDER BY id")]
        self.assertEqual(len(ids), 6)
        self.assertIn("(6 dosis)", self.post("/clinica/medicamento/%d/suspender" % ids[0], motivo="Cambio de analgésico"))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM medicamentos WHERE nombre='Dipirona 1 g IV' AND estado='S'")[0][0], 6)

    def test_alerta_de_alergia(self):
        self.entrar(DR)
        t = self.post("/clinica/paciente/1/medicamento", nombre="Amoxicilina 500 mg VO", hora="18:00")   # María: PENICILINA
        self.assertIn("ALERTA DE ALERGIA", t)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM medicamentos WHERE nombre LIKE 'Amoxicilina%'")[0][0], 0)
        t = self.post("/clinica/paciente/1/medicamento", nombre="Amoxicilina 500 mg VO", hora="18:00", confirmar_alergia="1")
        self.assertIn("formulado", t)
        self.assertIn("pese a la alergia a PENICILINA", t)
        # Hernán es alérgico a AINES: el ibuprofeno también se bloquea
        self.assertIn("ALERTA DE ALERGIA", self.post("/clinica/paciente/3/medicamento", nombre="Ibuprofeno 400 mg VO", hora="18:00"))

    def test_alta_suspende_dosis_pendientes(self):
        self.entrar(DR)
        self.post("/clinica/paciente/1/alta")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM medicamentos WHERE paciente_id=1 AND estado='P'")[0][0], 0)
        self.assertEqual(self.sql("SELECT motivo FROM medicamentos WHERE id=3")[0][0], "Alta médica")

    def test_cambio_de_cama(self):
        self.entrar(ENF)
        t = self.post("/clinica/paciente/1/cama", cama="208")
        self.assertIn("Traslado de cama 201 → 208", t)
        self.assertIn('value="201"', self.texto(self.c.get("/clinica/pacientes/nuevo")))
        self.assertIn("no está disponible", self.post("/clinica/paciente/2/cama", cama="208"))


class TestCitasPorTurno(BaseVozMedica):
    def test_el_medico_solo_atiende_en_su_turno(self):
        self.entrar_paciente("1001")   # su medico es el Dr. Rojas (Mañana)
        t = self.texto(self.c.get("/portal/agendar"))
        self.assertIn('value="07:00"', t)
        self.assertNotIn('value="15:00"', t)
        self.assertIn("turno Mañana (07:00 a 11:30)", self.post("/portal/agendar", fecha=FUTURO, hora="15:00", motivo="x"))
        self.assertIn("Cita agendada", self.post("/portal/agendar", fecha=FUTURO, hora="09:00", motivo="x"))

    def test_medico_de_la_tarde_no_tiene_citas_en_la_manana(self):
        self.entrar("Adm. Carolina Mejía")
        self.c.post("/admin/portal/1002/profesional", data={"profesional": DR_TARDE})
        self.entrar_paciente("1002")
        self.assertIn("turno Tarde", self.post("/portal/agendar", fecha=FUTURO, hora="09:00", motivo="x"))
        self.assertIn("Cita agendada", self.post("/portal/agendar", fecha=FUTURO, hora="14:00", motivo="x"))

    def test_reasignar_cancela_citas_fuera_del_nuevo_turno(self):
        self.entrar("Adm. Carolina Mejía")   # 1001 tiene cita mañana a las 09:00 con el Dr. Rojas
        t = self.post("/admin/portal/1001/profesional", profesional=DR_TARDE)
        self.assertIn("se cancelaron", t)
        self.assertEqual(self.sql("SELECT estado FROM citas WHERE id=1")[0][0], "Cancelada")

    def test_paciente_no_cancela_con_menos_de_2_horas(self):
        from datetime import datetime
        pronto = datetime.now() + timedelta(hours=1)
        db = sqlite3.connect(self.ruta_db)
        db.execute("UPDATE citas SET fecha=?, hora=? WHERE id=1", (pronto.date().isoformat(), pronto.strftime("%H:%M")))
        db.commit()
        db.close()
        self.entrar_paciente("1001")
        self.assertIn("menos de 2 horas", self.post("/portal/cita/1/cancelar"))
        self.assertEqual(self.sql("SELECT estado FROM citas WHERE id=1")[0][0], "Programada")
        # recepcion si puede cancelarla
        self.entrar("Rec. Diana Torres")
        self.post("/clinica/agenda/1/cancelar")
        self.assertEqual(self.sql("SELECT estado FROM citas WHERE id=1")[0][0], "Cancelada")


class TestPersonalYRecursos(BaseVozMedica):
    def test_empleado_desactivado_no_ingresa_y_se_puede_reactivar(self):
        self.entrar("Adm. Carolina Mejía")
        rec = self.ids["Rec. Diana Torres"]
        self.assertIn("desactivado", self.post("/admin/personal/%d/desactivar" % rec))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM personal WHERE id=?", rec)[0][0], 1)   # no se borra
        self.c.get("/salir")
        self.assertNotIn("Rec. Diana Torres", self.texto(self.c.get("/")))
        r = self.c.post("/", data={"tipo": "personal", "personal_id": rec})
        self.assertNotIn("Location", r.headers)        # no entra
        self.entrar("Adm. Carolina Mejía")
        self.assertIn("reactivado", self.post("/admin/personal/%d/reactivar" % rec))
        self.assertTrue(self.entrar("Rec. Diana Torres").headers["Location"].endswith("/clinica/agenda"))

    def test_salida_de_inventario_exige_motivo(self):
        self.entrar("Adm. Carolina Mejía")
        self.assertIn("Indique el motivo de la salida", self.post("/admin/recursos/1/movimiento", cantidad="1", accion="salida"))
        self.assertIn("Quedan 23", self.post("/admin/recursos/1/movimiento", cantidad="1", accion="salida", motivo="Vencimiento"))


class TestRecepcionYMedico(BaseVozMedica):
    def test_recepcion_solo_ve_agenda(self):
        self.entrar("Rec. Diana Torres")
        self.assertEqual(self.c.get("/clinica/agenda?ver=todas").status_code, 200)
        self.assertRedirige("/clinica/pacientes", "/clinica/agenda")
        self.assertRedirige("/clinica/paciente/1", "/clinica/agenda")
        self.assertRedirige("/cita/1/chat", "/clinica/agenda")
        t = self.post("/clinica/agenda/agendar", documento="1002", fecha=FUTURO, hora="09:00", motivo="Control")
        self.assertIn("Cita agendada", t)

    def test_medico_atiende_solo_sus_citas(self):
        self.entrar("Dr. Camilo Rojas")
        for url in ["/clinica/citas", "/cita/1/chat"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertRedirige("/clinica/recursos", "/clinica/pacientes")
        # la cita 1 es mañana: todavía no se puede marcar como atendida
        self.assertIn("Se marca como atendida el día", self.post("/clinica/cita/1/atendida"))
        # el chat de un paciente es confidencial: otra médica no lo ve
        self.entrar("Dra. Natalia Vélez")
        self.assertRedirige("/cita/1/chat", "/clinica/citas")

    def test_citas_vencidas(self):
        self.sql_exec("UPDATE citas SET fecha=? WHERE id=1", (date.today() - timedelta(days=1)).isoformat())
        self.entrar("Dr. Camilo Rojas")
        self.assertIn("Vencida", self.texto(self.c.get("/clinica/citas")))
        self.assertIn("ya no se puede marcar", self.post("/clinica/cita/1/atendida"))
        self.assertIn("solo lectura", self.texto(self.c.get("/cita/1/chat")))

    def sql_exec(self, consulta, *args):
        db = sqlite3.connect(self.ruta_db)
        db.execute(consulta, args)
        db.commit()
        db.close()


class TestAdministracion(BaseVozMedica):
    def setUp(self):
        super().setUp()
        self.entrar("Adm. Carolina Mejía")

    def test_pantallas_cargan(self):
        for url in ["/admin/", "/admin/recursos", "/admin/recursos?bajos=1", "/admin/movimientos",
                    "/admin/solicitudes", "/admin/personal", "/admin/roles"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertRedirige("/clinica/pacientes", "/admin/")

    def test_entrada_cierra_solicitud_solo_si_supera_el_minimo(self):
        # Furosemida: 8 disponibles, minimo 10, con solicitud abierta
        t = self.post("/admin/recursos/3/movimiento", cantidad="1", accion="entrada")
        self.assertNotIn("quedó atendida", t)
        t = self.post("/admin/recursos/3/movimiento", cantidad="20", accion="entrada")
        self.assertIn("quedó atendida", t)

    def test_no_duplica_recursos(self):
        t = self.post("/admin/recursos/nuevo", tipo="Insumo", nombre="jeringa 5 ml", cantidad="1", minimo="1")
        self.assertIn("Ya existe un recurso", t)

    def test_personal(self):
        self.assertIn("registrado", self.post("/admin/personal/nuevo", nombre="Enf. Sofía Cano", documento="1", rol="enfermeria"))
        self.assertIn("ya está registrado a nombre de Enf. Sofía Cano",
                      self.post("/admin/personal/nuevo", nombre="Otra", documento="1", rol="enfermeria"))
        self.assertIn("No se puede desactivar", self.post("/admin/personal/%d/desactivar" % self.ids["Dr. Camilo Rojas"]))
        self.assertIn("propio usuario", self.post("/admin/personal/%d/desactivar" % self.ids["Adm. Carolina Mejía"]))
        self.assertIn("Primero debe entregar el turno", self.post("/admin/personal/%d/desactivar" % self.ids[ENF]))
        self.assertIn("Primero debe entregar el turno", self.post("/admin/personal/%d/turno" % self.ids[ENF], turno="2"))
        self.assertIn("Turno de Enf. Paula Ríos actualizado", self.post("/admin/personal/%d/turno" % self.ids["Enf. Paula Ríos"], turno="1"))
        self.assertIn("No puede quitarse", self.post("/admin/personal/%d/rol" % self.ids["Adm. Carolina Mejía"], rol="enfermeria"))
        # un medico con pacientes no puede pasar a un rol que no atiende citas
        self.assertIn("No se puede cambiar el rol", self.post("/admin/personal/%d/rol" % self.ids["Dr. Camilo Rojas"], rol="enfermeria"))

    def test_reasignar_y_eliminar_medico(self):
        for doc in ("1001", "1003"):
            self.c.post("/admin/portal/%s/profesional" % doc, data={"profesional": "Dra. Natalia Vélez"})
        # todavia es medico tratante de 2 hospitalizados
        self.assertIn("médico tratante de 2", self.post("/admin/personal/%d/desactivar" % self.ids[DR]))
        self.entrar("Dra. Natalia Vélez")
        for pid in (1, 3):
            self.c.post("/clinica/paciente/%d/asumir" % pid)
        self.entrar("Adm. Carolina Mejía")
        self.assertIn("desactivado", self.post("/admin/personal/%d/desactivar" % self.ids[DR]))

    def test_quitar_permiso_aplica_de_inmediato(self):
        self.c.post("/admin/roles", data={"enfermeria:ver_censo": "on", "admin:admin_inventario": "on"})
        self.entrar("Enf. Laura Gómez")
        self.assertEqual(self.c.get("/clinica/pacientes").status_code, 200)
        self.assertRedirige("/clinica/paciente/1", "/clinica/pacientes")
        self.assertNotIn("Ver ficha", self.texto(self.c.get("/clinica/pacientes")))
        # el rol admin conserva siempre el acceso a Personal
        self.entrar("Adm. Carolina Mejía")
        self.assertEqual(self.c.get("/admin/personal").status_code, 200)


class TestPortalPaciente(BaseVozMedica):
    def setUp(self):
        super().setUp()
        self.entrar_paciente("1001")

    def test_pantallas_y_aislamiento(self):
        for url in ["/portal/", "/portal/agendar", "/cita/1/chat"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertRedirige("/clinica/pacientes", "/portal/")
        self.assertRedirige("/admin/", "/portal/")
        self.assertRedirige("/cita/2/chat", "/portal/")   # la cita 2 es de otro paciente

    def test_agendar(self):
        self.assertIn("ya pasaron", self.post("/portal/agendar", fecha="2020-01-01", hora="09:00", motivo="x"))
        self.assertIn("Revise la fecha", self.post("/portal/agendar", fecha="abc", hora="09:00", motivo="x"))
        self.assertIn("Cita agendada", self.post("/portal/agendar", fecha=FUTURO, hora="09:00", motivo="x"))
        self.assertIn("ese día", self.post("/portal/agendar", fecha=FUTURO, hora="10:00", motivo="y"))
        # otro paciente del mismo medico no puede tomar la misma hora
        self.entrar_paciente("1003")
        self.assertIn("ya tiene una cita", self.post("/portal/agendar", fecha=FUTURO, hora="09:00", motivo="z"))

    def test_chat(self):
        self.assertIn("hola doctor", self.post("/cita/1/mensaje", texto="hola doctor"))
        self.post("/portal/cita/1/cancelar")
        t = self.post("/cita/1/mensaje", texto="ya cancelada")
        self.assertNotIn("ya cancelada", t)
        self.assertIn("solo lectura", t)


if __name__ == "__main__":
    unittest.main()
