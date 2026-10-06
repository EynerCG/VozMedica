-- Esquema de la base de datos de VozMedica (SQLite).
-- Se ejecuta completo al crear o reiniciar la base: borra todo y lo vuelve a crear.
-- Si cambia, subir VERSION_ESQUEMA en db.py.

DROP TABLE IF EXISTS personal;      DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS permisos;      DROP TABLE IF EXISTS pacientes;
DROP TABLE IF EXISTS medicamentos;  DROP TABLE IF EXISTS novedades;
DROP TABLE IF EXISTS pendientes;    DROP TABLE IF EXISTS entregas;
DROP TABLE IF EXISTS entrega_pacientes;
DROP TABLE IF EXISTS recursos;      DROP TABLE IF EXISTS movimientos;
DROP TABLE IF EXISTS solicitudes;   DROP TABLE IF EXISTS portal;
DROP TABLE IF EXISTS citas;         DROP TABLE IF EXISTS mensajes;
DROP TABLE IF EXISTS config;        DROP TABLE IF EXISTS camas;
DROP TABLE IF EXISTS signos;

-- Personal, roles y permisos
CREATE TABLE roles (clave TEXT PRIMARY KEY, nombre TEXT);
CREATE TABLE permisos (rol TEXT, permiso TEXT, PRIMARY KEY (rol, permiso));
-- turno: 0 Mañana, 1 Tarde, 2 Noche, NULL horario administrativo
-- activo: quien firmo registros clinicos nunca se borra; se desactiva (no puede ingresar)
CREATE TABLE personal (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, documento TEXT, rol TEXT, turno INTEGER,
    activo INTEGER DEFAULT 1);

-- Modulo 1: pacientes hospitalizados y entrega de turno
CREATE TABLE camas (numero TEXT PRIMARY KEY, ubicacion TEXT);  -- ocupada = hay un paciente sin alta en ella
-- La historia clinica no se borra nunca: al dar de alta se llena `alta` y la cama queda libre.
--   medico:    medico tratante (formula y da de alta)
--   cubre:     medico de turno que lo cubre mientras el tratante no esta (NULL = lo atiende su tratante)
--   enfermera: enfermera que tiene la cama asignada en el turno actual
CREATE TABLE pacientes (id INTEGER PRIMARY KEY, documento TEXT, cama TEXT, nombre TEXT, edad INTEGER,
    diagnostico TEXT, ingreso TEXT, alta TEXT, alergias TEXT, estado TEXT,
    medico TEXT, cubre TEXT, enfermera TEXT);
-- Cada dosis de una orden medica.
--   estado: P pendiente, A administrada, N no administrada (con motivo), S suspendida por el medico (con motivo)
--   registro: quien y a que hora la registro / suspendio
CREATE TABLE medicamentos (id INTEGER PRIMARY KEY, paciente_id INTEGER, fecha TEXT, hora TEXT,
    nombre TEXT, estado TEXT, registro TEXT, motivo TEXT);
-- Registros de la historia clinica: nunca se sobrescriben, se agregan con fecha, hora y autor
CREATE TABLE signos (id INTEGER PRIMARY KEY, paciente_id INTEGER, fecha TEXT, hora TEXT, texto TEXT, autor TEXT);
CREATE TABLE novedades (id INTEGER PRIMARY KEY, paciente_id INTEGER, fecha TEXT, hora TEXT, texto TEXT, autor TEXT);
CREATE TABLE pendientes (id INTEGER PRIMARY KEY, paciente_id INTEGER, texto TEXT, hecho INTEGER, hecho_por TEXT);
-- Una entrega pasa un grupo de pacientes de una persona a otra del turno siguiente.
--   tipo: enfermeria / medica      estado: Pendiente (falta la firma de quien recibe) / Recibida
CREATE TABLE entregas (id INTEGER PRIMARY KEY, tipo TEXT, fecha TEXT, hora TEXT, turno TEXT,
    entrega TEXT, recibe TEXT, observaciones TEXT, estado TEXT, recibida TEXT);
CREATE TABLE entrega_pacientes (entrega_id INTEGER, paciente_id INTEGER, nota TEXT);

-- Modulo 2: recursos hospitalarios
CREATE TABLE recursos (id INTEGER PRIMARY KEY, tipo TEXT, nombre TEXT, cantidad INTEGER,
    minimo INTEGER, ubicacion TEXT);
CREATE TABLE movimientos (id INTEGER PRIMARY KEY, recurso_id INTEGER, fecha TEXT, cambio INTEGER,
    motivo TEXT, usuario TEXT);
CREATE TABLE solicitudes (id INTEGER PRIMARY KEY, recurso_id INTEGER, fecha TEXT, usuario TEXT,
    nota TEXT, estado TEXT);                           -- estado: Abierta / Atendida

-- Modulo 3: atencion virtual
CREATE TABLE portal (documento TEXT PRIMARY KEY, nombre TEXT, profesional TEXT);
CREATE TABLE citas (id INTEGER PRIMARY KEY, documento TEXT, profesional TEXT, fecha TEXT, hora TEXT,
    motivo TEXT, estado TEXT, sala TEXT);              -- estado: Programada / Atendida / Cancelada / Vencida
CREATE TABLE mensajes (id INTEGER PRIMARY KEY, cita_id INTEGER, autor TEXT, hora TEXT, texto TEXT);

-- version del esquema y reloj de la demo
CREATE TABLE config (clave TEXT PRIMARY KEY, valor TEXT);
