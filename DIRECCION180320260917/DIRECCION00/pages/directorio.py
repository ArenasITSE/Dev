import streamlit as st
import time
import os
import sys
import io
import json
import base64
import hashlib
import secrets
import qrcode
import re
import pandas as pd

import os
import streamlit as st
from appdb import SessionLocal, DB_PATH
from models import Unidad, Puesto, Personal

from datetime import datetime, timedelta
from urllib.parse import quote
from sqlalchemy import Float, Boolean, Date, Column, Integer, String, ForeignKey, Text, create_engine, DateTime, or_
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, backref
from PIL import Image as PILImage, ImageOps

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from appdb import Base, engine, SessionLocal

# --- INYECCIÓN DE TEMAS PERSONALIZADOS Y ESTILO DE EMOJIS ---
if 'tema_visual' not in st.session_state:
    st.session_state.tema_visual = "Claro (Por defecto)"

if 'estilo_emojis' not in st.session_state:
    # Dos estilos: "Emojis de colores" (actual) y "Minimalista" (sin emoji)
    st.session_state.estilo_emojis = "Emojis de colores"

# Color del encabezado del CV (gradiente principal) - HEX
if 'cv_color_header' not in st.session_state:
    # Azul marino claro por defecto
    st.session_state.cv_color_header = "#0b3c5d"

if st.session_state.tema_visual == "Nocturno (Negro)":
    st.markdown("""
        <style>
            .stApp { background-color: #121212 !important; }
            p, h1, h2, h3, h4, h5, h6, span, label, li { color: #E0E0E0 !important; }
            div[data-testid="stForm"] { background-color: #1E1E1E !important; border: 1px solid #333 !important; }
            header[data-testid="stHeader"] { background: transparent !important; }
        </style>
    """, unsafe_allow_html=True)
elif st.session_state.tema_visual == "Gris Pizarra":
    st.markdown("""
        <style>
            .stApp { background-color: #374151 !important; }
            p, h1, h2, h3, h4, h5, h6, span, label, li { color: #F3F4F6 !important; }
            div[data-testid="stForm"] { background-color: #1F2937 !important; border: 1px solid #4B5563 !important; }
            header[data-testid="stHeader"] { background: transparent !important; }
        </style>
    """, unsafe_allow_html=True)

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTADOS ---
st.set_page_config(page_title="Directorios ITSE", page_icon=":material/network_node:", layout="wide")

if not os.path.exists("fotos_personal"):
    os.makedirs("fotos_personal")
if not os.path.exists("logos_carreras"):
    os.makedirs("logos_carreras")

# Inicializar estados para autenticación (RBAC)
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'usuario_nombre' not in st.session_state:
    st.session_state.usuario_nombre = None
if 'personal_id' not in st.session_state:
    st.session_state.personal_id = None
if 'usuario_id' not in st.session_state:
    st.session_state.usuario_id = None

# Inicializar estados para la edición interactiva
for key in ['edit_u', 'del_u', 'edit_p', 'del_p', 'edit_e', 'del_e']:
    if key not in st.session_state: st.session_state[key] = None

st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
    <style>
        div[data-testid="stTabs"] > div:first-child {
            position: sticky; top: 2.875rem; z-index: 999;
            background-color: var(--background-color);
            padding-top: 1rem; padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--secondary-background-color);
        }
        button[title="View fullscreen"] { display: none !important; }
        .fa-icon { margin-right: 0.35em; }
    </style>
""", unsafe_allow_html=True)


# --- 2. BASE DE DATOS MEJORADA ---
Base = declarative_base()

class Unidad(Base):
    __tablename__ = 'unidades'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    tipo_nivel = Column(String)
    parent_id = Column(Integer, ForeignKey('unidades.id'), nullable=True)
    
    # Jerarquía: sub_unidades (hijos), parent (padre) con remote_side en el backref
    sub_unidades = relationship(
        'Unidad',
        foreign_keys=[parent_id],
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )
    puestos = relationship("Puesto", back_populates="unidad", cascade="all, delete-orphan")

class Puesto(Base):
    __tablename__ = 'puestos'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    unidad_id = Column(Integer, ForeignKey('unidades.id'))
    # Si es True, el puesto funciona como "plantilla": puede tener múltiples personas asignadas
    multipuesto = Column(Boolean, default=False)
    
    unidad = relationship("Unidad", back_populates="puestos")
    personal = relationship("Personal", back_populates="puesto", cascade="all, delete-orphan")

class Personal(Base):
    __tablename__ = 'personal'
    id = Column(Integer, primary_key=True, index=True)
    # Bloque 1: Identidad
    numero_empleado = Column(String, nullable=True)
    fotografia = Column(String, nullable=True)
    nombre = Column(String)
    apellido_paterno = Column(String)
    apellido_materno = Column(String)
    fecha_nacimiento = Column(Date)
    genero = Column(String)
    estado_civil = Column(String)
    domicilio = Column(String)
    curp = Column(String)
    rfc = Column(String)
    nss = Column(String)
    ine_pasaporte = Column(String)
    # Bloque 2: Contacto
    celular_personal = Column(String)
    correo_personal = Column(String)
    telefono_oficina = Column(String)
    extension = Column(String)
    correo_institucional = Column(String)
    # Bloque 3: Laborales
    puesto_id = Column(Integer, ForeignKey('puestos.id'))
    grado_academico = Column(String, nullable=True)
    cvu = Column(String, nullable=True)
    edificio = Column(String)
    planta = Column(String)
    fecha_ingreso = Column(Date)
    tipo_contrato = Column(String)
    jornada_laboral = Column(String)
    salario_base = Column(Float)
    salario_bruto_neto = Column(String)
    periodicidad_pago = Column(String)
    # Bloque 4: Académico
    titulo_abreviatura = Column(String) 
    licenciatura = Column(String)
    maestria = Column(String, nullable=True)
    doctorado = Column(String, nullable=True)
    licenciatura_mencion_honorifica = Column(Boolean, default=False, nullable=True)
    maestria_mencion_honorifica = Column(Boolean, default=False, nullable=True)
    doctorado_mencion_honorifica = Column(Boolean, default=False, nullable=True)
    # Ubicación de residencia y teléfonos adicionales
    estado_residencia = Column(String, nullable=True)
    municipio_residencia = Column(String, nullable=True)
    localidad_residencia = Column(String, nullable=True)
    codigo_postal = Column(String, nullable=True)
    telefono_casa = Column(String, nullable=True)
    telefono_otro = Column(String, nullable=True)
    # Datos familiares
    nombre_padre = Column(String, nullable=True)
    nombre_madre = Column(String, nullable=True)
    numero_hijos = Column(Integer, nullable=True)
    # Perfil personal y salud
    talla_camisa = Column(String, nullable=True)
    deporte = Column(String, nullable=True)
    actividad_cultural = Column(String, nullable=True)
    pasatiempo = Column(String, nullable=True)
    alergias = Column(String, nullable=True)
    # Otros campos existentes
    programas_educativos = Column(String, nullable=True)
    area_asignada = Column(String, nullable=True)
    
    puesto = relationship("Puesto", back_populates="personal")
    usuario_sistema = relationship("UsuarioSistema", back_populates="personal", uselist=False)
    # Relaciones para Bloque 5 y 6
    producciones = relationship("ProduccionAcademica", back_populates="empleado", cascade="all, delete-orphan")
    cursos = relationship("CursoCapacitacion", back_populates="empleado", cascade="all, delete-orphan")
# Tablas auxiliares para soportar múltiples registros
class UsuarioSistema(Base):
    """Usuarios del sistema para login y control de acceso por roles."""
    __tablename__ = 'usuarios_sistema'
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    rol = Column(String, nullable=False)  # Súper Admin, RRHH, Desarrollo Académico, Empleado
    personal_id = Column(Integer, ForeignKey('personal.id'), nullable=True)
    
    personal = relationship("Personal", back_populates="usuario_sistema")
    preferencias = relationship("PreferenciasUsuario", back_populates="usuario", uselist=False)


class DominioCorreo(Base):
    """Dominios institucionales para correo (ej. itscarcega.edu.mx)."""
    __tablename__ = 'dominios_correo'
    id = Column(Integer, primary_key=True, index=True)
    dominio = Column(String, unique=True, nullable=False)  # Sin @, ej: itscarcega.edu.mx


class PreferenciasUsuario(Base):
    """Preferencias visuales por usuario (tema, emojis, etc.)."""
    __tablename__ = 'preferencias_usuario'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), unique=True, nullable=False)
    tema_visual = Column(String, default="Claro (Por defecto)")
    estilo_emojis = Column(String, default="Emojis de colores")
    
    usuario = relationship("UsuarioSistema", back_populates="preferencias")


class ConfiguracionSMTP(Base):
    """Configuración SMTP para envío de correos (restablecimiento de contraseña)."""
    __tablename__ = 'configuracion_smtp'
    id = Column(Integer, primary_key=True, index=True)
    smtp_host = Column(String, default="smtp.gmail.com")
    smtp_puerto = Column(Integer, default=587)
    smtp_usuario = Column(String, nullable=True)  # Correo Gmail
    smtp_clave = Column(String, nullable=True)   # Contraseña de aplicación
    usar_tls = Column(Boolean, default=True)
    activo = Column(Boolean, default=False)


class TokenRestablecimiento(Base):
    """Token temporal para restablecer contraseña olvidada (expira en 15 min)."""
    __tablename__ = 'tokens_restablecimiento'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=False)
    token = Column(String(32), nullable=False, index=True)
    expira_en = Column(DateTime, nullable=False)


class BitacoraActividad(Base):
    """Bitácora de auditoría para rastrear acciones de usuarios autenticados."""
    __tablename__ = 'bitacora_actividad'
    id = Column(Integer, primary_key=True, index=True)
    fecha_hora = Column(DateTime, default=datetime.now)
    usuario_nombre = Column(String, nullable=False)
    accion = Column(String, nullable=False)
    modulo = Column(String, nullable=False)
    detalles = Column(String, nullable=True)


class ProduccionAcademica(Base):
    __tablename__ = 'producciones'
    id = Column(Integer, primary_key=True)
    personal_id = Column(Integer, ForeignKey('personal.id'))
    tipo = Column(String) # Libro, Capítulo de Libro, Artículo
    titulo = Column(String) # Título del Libro o del Artículo
    titulo_capitulo = Column(String, nullable=True) # Solo para capítulos
    revista_medio = Column(String, nullable=True) # Solo para artículos
    fecha = Column(Date)
    identificador = Column(String) # ISBN, ISSN, etc.

    empleado = relationship("Personal", back_populates="producciones")

class CursoCapacitacion(Base):
    __tablename__ = 'cursos_cap'
    id = Column(Integer, primary_key=True)
    personal_id = Column(Integer, ForeignKey('personal.id'))
    nombre_curso = Column(String)
    institucion = Column(String)
    horas = Column(Integer)
    fecha_termino = Column(Date)
    tipo_documento = Column(String) # Ej. Constancia, Diploma, Certificado
    
    # El "apretón de manos" que ya corregimos
    empleado = relationship("Personal", back_populates="cursos")


class SolicitudCaptura(Base):
    """
    Solicitudes de captura/modificación del empleado, pendientes de aprobación por RH.
    Soporta: modificar, agregar, eliminar. payload_json guarda los datos; al aprobar se aplican.
    """
    __tablename__ = 'solicitudes_captura'
    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey('personal.id'), nullable=False, index=True)
    seccion = Column(String(80), nullable=False, index=True)  # datos_personales, estudios, experiencia_laboral, reconocimientos, publicaciones
    accion = Column(String(20), nullable=False)  # modificar | agregar | eliminar
    tabla_destino = Column(String(80), nullable=False)
    registro_ref_id = Column(Integer, nullable=True)
    payload_json = Column(Text, nullable=True)
    estado = Column(String(20), default='pendiente', index=True)  # pendiente | aprobado | rechazado
    motivo_rechazo = Column(String(500), nullable=True)
    fecha_solicitud = Column(DateTime, default=datetime.now)
    solicitante_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)
    fecha_revision = Column(DateTime, nullable=True)
    revisor_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)


class Carrera(Base):
    """Catálogo de carreras con características, link de material y logo."""
    __tablename__ = 'carreras'
    id = Column(Integer, primary_key=True, index=True)
    tipo_nivel = Column(String)  # Licenciatura, Ingeniería
    nombre = Column(String)
    modalidad = Column(String)  # Escolarizado, En línea
    link_material = Column(String, nullable=True)  # URL de la página con material
    logo = Column(String, nullable=True)  # Ruta del archivo del logo


class IdentidadInstitucional(Base):
    """Parámetros globales / identidad institucional (una sola fila, id=1)."""
    __tablename__ = 'identidad_institucional'
    id = Column(Integer, primary_key=True)
    # Bloque 1: Identificación oficial y legal
    nombre_oficial = Column(String, nullable=True)
    acronimo = Column(String, nullable=True)
    cct = Column(String, nullable=True)  # Clave de Centro de Trabajo
    rfc = Column(String, nullable=True)
    # Bloque 2: Elementos gráficos (rutas de archivos)
    logo_principal = Column(String, nullable=True)
    logo_secundario = Column(String, nullable=True)
    sello_marca_agua = Column(String, nullable=True)
    color_institucional = Column(String, nullable=True)  # HEX ej. #1b5e20
    # Bloque 3: Filosofía y contacto
    lema = Column(String, nullable=True)
    direccion_oficial = Column(String, nullable=True)
    telefono_oficial = Column(String, nullable=True)
    correo_contacto = Column(String, nullable=True)
    pagina_web = Column(String, nullable=True)


# edificios tabalas
class Edificio(Base):
    __tablename__ = 'edificios'
    id = Column(Integer, primary_key=True, index=True)
    letra = Column(String, unique=True, index=True) 
    nombre = Column(String) 
    
    # Relación: Un edificio tiene muchas plantas
    plantas = relationship("Planta", back_populates="edificio", cascade="all, delete-orphan")

class Planta(Base):
    __tablename__ = 'plantas'
    id = Column(Integer, primary_key=True, index=True)
    edificio_id = Column(Integer, ForeignKey('edificios.id'))
    nombre_nivel = Column(String) # Ej. Planta Baja, Nivel 1
    uso_principal = Column(String) # Ej. Aulas, Laboratorios, Administrativo
    tiene_rack_red = Column(Boolean, default=False)
    accesible_silla_ruedas = Column(Boolean, default=True)
    croquis = Column(String, nullable=True) # Ruta de imagen
    
    # Relaciones
    edificio = relationship("Edificio", back_populates="plantas")
    espacios = relationship("Espacio", back_populates="planta", cascade="all, delete-orphan")

class Espacio(Base):
    __tablename__ = 'espacios'
    id = Column(Integer, primary_key=True, index=True)
    planta_id = Column(Integer, ForeignKey('plantas.id')) # Ahora el espacio pertenece a la planta
    nombre = Column(String) 
    tipo = Column(String) 
    
    planta = relationship("Planta", back_populates="espacios")

    # 2. SEGUNDO LA CONEXIÓN (Corta y pega esto debajo de las clases)
  
    Base.metadata.create_all(engine)
    session = SessionLocal()

# --- 3. LÓGICA DEL ORGANIGRAMA INTERACTIVO (RECURSIVO, NIVELES INFINITOS) ---
def reset_states():
    for key in ['edit_u', 'del_u', 'edit_p', 'del_p', 'edit_e', 'del_e']:
        st.session_state[key] = None


def _parse_si_no(val):
    """Convierte valor a booleano: Sí/Yes/1/True -> True, resto -> False."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    return s in ("sí", "si", "yes", "1", "true", "verdadero")


def _cargar_catalogo_estados_municipios():
    """
    Catálogo fijo por estado -> lista de municipios.
    Preferimos un archivo local en `catalogos/estados-municipios.json` o `catalogos/estados_municipios.json`.
    Si no existe (o falla), se descarga una copia pública y se cachea.
    """
    cache_key = "_cat_est_mun"
    if cache_key in st.session_state and isinstance(st.session_state.get(cache_key), dict):
        cached = st.session_state.get(cache_key)
        # Si quedó cacheado incompleto (o vacío), lo recalculamos.
        if isinstance(cached, dict) and len(cached) >= 32:
            return cached
    import json
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent
    candidatos = [
        base_dir / "catalogos" / "estados-municipios.json",
        base_dir / "catalogos" / "estados_municipios.json",
    ]

    data = None
    for p in candidatos:
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                break
        except Exception:
            data = None

    # Si el archivo existe pero está incompleto, preferimos descargar catálogo completo.
    if isinstance(data, dict) and len(data) < 32:
        data = None

    if not isinstance(data, dict):
        # Descarga pública (INEGI derivado): estados->municipios
        try:
            import urllib.request
            url = "https://raw.githubusercontent.com/cisnerosnow/json-estados-municipios-mexico/master/estados-municipios.json"
            with urllib.request.urlopen(url, timeout=10) as resp:
                txt = resp.read().decode("utf-8", errors="replace")
            data = json.loads(txt)
            # Cachear a archivo si se puede
            try:
                out = base_dir / "catalogos" / "estados-municipios.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(txt, encoding="utf-8")
            except Exception:
                pass
        except Exception:
            data = {}

    st.session_state[cache_key] = data
    return data


def _validar_curp(curp_raw):
    """
    Valida CURP (estructura + fecha + entidad + dígito verificador) y extrae datos.
    Retorna dict: {ok: bool, errores: [..], datos: {fecha_nacimiento, sexo, entidad}}
    """
    curp = (curp_raw or "").strip().upper()
    res = {"ok": False, "errores": [], "datos": {}}
    if not curp:
        res["ok"] = True
        return res
    if len(curp) != 18:
        res["errores"].append("La CURP debe tener 18 caracteres.")
        return res

    # Códigos de entidad federativa (RENAPO) + NE (nacido en el extranjero)
    entidades = {
        "AS","BC","BS","CC","CL","CM","CS","CH","DF","DG","GT","GR","HG","JC","MC","MN","MS","NT",
        "NL","OC","PL","QT","QR","SP","SL","SR","TC","TS","TL","VZ","YN","ZS","NE"
    }

    # Regex general (no valida dígito verificador)
    patron = re.compile(r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$")
    if not patron.match(curp):
        res["errores"].append("Estructura inválida (formato CURP no coincide).")
        return res

    # Extraer bloques
    yy = int(curp[4:6])
    mm = int(curp[6:8])
    dd = int(curp[8:10])
    sexo = curp[10]  # H/M
    ent = curp[11:13]
    pos17 = curp[16]  # distingue siglo (0-9: 1900s, A-Z: 2000s)
    digito = curp[17]

    if ent not in entidades:
        res["errores"].append(f"Entidad inválida en CURP: '{ent}'.")
        return res

    anio = (1900 + yy) if pos17.isdigit() else (2000 + yy)
    try:
        fecha_nac = datetime(anio, mm, dd).date()
    except ValueError:
        res["errores"].append("Fecha de nacimiento inválida en CURP.")
        return res

    # Dígito verificador (posición 18) calculado con los 17 primeros
    # Tabla oficial: 0-9, A-Z y Ñ (incluida)
    tabla = {str(i): i for i in range(10)}
    for idx, ch in enumerate("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ", start=10):
        tabla[ch] = idx
    suma = 0
    for i, ch in enumerate(curp[:17]):
        if ch not in tabla:
            res["errores"].append("Caracter inválido para cálculo de dígito verificador.")
            return res
        valor = tabla[ch]
        # Pesos oficiales para posiciones 1..17: 18..2
        peso = 18 - i
        suma += valor * peso
    dv_calc = (10 - (suma % 10)) % 10
    if not digito.isdigit() or int(digito) != dv_calc:
        res["errores"].append("Dígito verificador inválido (la CURP parece mal capturada).")
        return res

    res["ok"] = True
    res["datos"] = {"fecha_nacimiento": fecha_nac, "sexo": sexo, "entidad": ent}
    return res


def _validar_rfc(rfc_raw):
    """
    Valida RFC (estructura + fecha) y extrae tipo/persona y fecha.
    Retorna dict: {ok: bool, errores: [..], datos: {tipo, fecha}}
    """
    rfc = (rfc_raw or "").strip().upper()
    res = {"ok": False, "errores": [], "datos": {}}
    if not rfc:
        res["ok"] = True
        return res
    if len(rfc) not in (12, 13):
        res["errores"].append("El RFC debe tener 12 (moral) o 13 (física) caracteres.")
        return res

    # Permitir letras A-Z, Ñ y & en la parte de letras; homoclave alfanumérica
    pat_fis = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
    pat_mor = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
    if len(rfc) == 13:
        if not pat_fis.match(rfc):
            res["errores"].append("Estructura inválida de RFC (persona física).")
            return res
        tipo = "Física"
        fecha_txt = rfc[4:10]
    else:
        if not pat_mor.match(rfc):
            res["errores"].append("Estructura inválida de RFC (persona moral).")
            return res
        tipo = "Moral"
        fecha_txt = rfc[3:9]

    yy = int(fecha_txt[0:2])
    mm = int(fecha_txt[2:4])
    dd = int(fecha_txt[4:6])

    # RFC usa año de 2 dígitos; inferimos siglo de forma práctica:
    # si el año es mayor al año actual (2 dígitos), asumimos 1900; si no, 2000.
    hoy = datetime.now().date()
    yy_hoy = hoy.year % 100
    anio = (1900 + yy) if yy > yy_hoy else (2000 + yy)
    try:
        fecha = datetime(anio, mm, dd).date()
    except ValueError:
        res["errores"].append("Fecha inválida en RFC.")
        return res

    res["ok"] = True
    res["datos"] = {"tipo": tipo, "fecha": fecha}
    return res


def _validar_nss(nss_raw, fecha_nacimiento=None):
    """
    Valida NSS (IMSS) de 11 dígitos con dígito verificador (módulo 10) y coherencias básicas.
    Normaliza quitando espacios/guiones. Retorna dict: {ok, errores, datos:{nss_norm, verificador_calc}}.
    """
    nss_norm = (nss_raw or "").strip().replace("-", "").replace(" ", "")
    res = {"ok": False, "errores": [], "datos": {"nss_norm": nss_norm}}
    if not nss_norm:
        res["ok"] = True
        return res
    if not nss_norm.isdigit():
        res["errores"].append("El NSS debe contener solo dígitos (puedes omitir guiones/espacios).")
        return res
    if len(nss_norm) != 11:
        res["errores"].append("El NSS debe tener 11 dígitos.")
        return res

    base10 = nss_norm[:10]
    dv = int(nss_norm[10])
    pesos = [1, 2] * 5  # 10 pesos: 1-2-1-2...
    suma = 0
    for d_ch, w in zip(base10, pesos):
        prod = int(d_ch) * w
        # sumar dígitos del producto (ej. 12 => 1+2 = 3)
        suma += prod if prod < 10 else (prod // 10 + prod % 10)
    dv_calc = (10 - (suma % 10)) % 10
    res["datos"]["verificador_calc"] = dv_calc
    if dv != dv_calc:
        res["errores"].append("Dígito verificador inválido (NSS parece mal capturado).")
        return res

    # Coherencia opcional: año de nacimiento del NSS (pos 5-6) vs fecha_nacimiento
    try:
        if fecha_nacimiento:
            fn = fecha_nacimiento.date() if isinstance(fecha_nacimiento, datetime) else fecha_nacimiento
            yy_nss = int(nss_norm[4:6])
            if (fn.year % 100) != yy_nss:
                res["errores"].append("El año de nacimiento no coincide con el NSS (revisa captura).")
                return res
    except Exception:
        pass

    res["ok"] = True
    return res


def _validar_celular_mx(cel_raw):
    """
    Valida celular mexicano. Acepta 10 dígitos o formatos con +52/52, espacios o guiones.
    Retorna dict: {ok, errores, datos:{cel_norm_10}}
    """
    s = (cel_raw or "").strip()
    res = {"ok": False, "errores": [], "datos": {}}
    if not s:
        res["ok"] = True
        return res
    # dejar solo dígitos
    digits = re.sub(r"\D+", "", s)
    # remover prefijo país si viene
    if digits.startswith("52") and len(digits) > 10:
        digits = digits[2:]
    if len(digits) != 10:
        res["errores"].append("El celular debe tener 10 dígitos (puedes capturarlo con +52, espacios o guiones).")
        return res
    if digits[0] == "0":
        res["errores"].append("El celular no debe iniciar con 0.")
        return res
    res["ok"] = True
    res["datos"] = {"cel_norm_10": digits}
    return res


def _validar_email(email_raw):
    """
    Email opcional: normaliza y valida reglas prácticas.
    Retorna dict: {ok, errores, datos:{email_norm}}
    """
    email = (email_raw or "").strip()
    res = {"ok": False, "errores": [], "datos": {}}
    if not email:
        res["ok"] = True
        return res
    if any(ch.isspace() for ch in email):
        res["errores"].append("No se permiten espacios en el correo.")
        return res
    email_norm = email.lower()
    if len(email_norm) > 254:
        res["errores"].append("El correo es demasiado largo.")
        return res
    if email_norm.count("@") != 1:
        res["errores"].append("Debe contener un solo @.")
        return res
    local, domain = email_norm.split("@", 1)
    if not local:
        res["errores"].append("Falta la parte antes del @.")
        return res
    if not domain or "." not in domain:
        res["errores"].append("El dominio debe contener un punto (ej. gmail.com).")
        return res
    if domain.startswith(".") or domain.endswith("."):
        res["errores"].append("Dominio inválido.")
        return res
    # Regex simple y práctica
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email_norm):
        res["errores"].append("Formato de correo inválido.")
        return res
    res["ok"] = True
    res["datos"] = {"email_norm": email_norm}
    return res


def _validar_telefono_mx(tel_raw):
    """
    Teléfono MX (oficina): opcional. Acepta 10 dígitos o formatos con +52/52, espacios o guiones.
    Retorna dict: {ok, errores, datos:{tel_norm_10}}
    """
    s = (tel_raw or "").strip()
    res = {"ok": False, "errores": [], "datos": {}}
    if not s:
        res["ok"] = True
        return res
    digits = re.sub(r"\D+", "", s)
    if digits.startswith("52") and len(digits) > 10:
        digits = digits[2:]
    if len(digits) != 10:
        res["errores"].append("El teléfono debe tener 10 dígitos (puedes capturarlo con +52, espacios o guiones).")
        return res
    if digits[0] == "0":
        res["errores"].append("El teléfono no debe iniciar con 0.")
        return res
    res["ok"] = True
    res["datos"] = {"tel_norm_10": digits}
    return res


def _validar_extension(ext_raw, max_len=6):
    """Extensión opcional: solo dígitos (1..max_len)."""
    s = (ext_raw or "").strip()
    res = {"ok": False, "errores": [], "datos": {}}
    if not s:
        res["ok"] = True
        return res
    digits = re.sub(r"\D+", "", s)
    if digits != s:
        res["errores"].append("La extensión debe contener solo dígitos.")
        return res
    if not (1 <= len(digits) <= max_len):
        res["errores"].append(f"La extensión debe tener de 1 a {max_len} dígitos.")
        return res
    res["ok"] = True
    res["datos"] = {"ext_norm": digits}
    return res


def _generar_plantilla_excel_infraestructura():
    """Genera un archivo .xlsx de plantilla con 3 hojas: Edificios, Plantas, Áreas. Retorna bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_edif = pd.DataFrame({
            "Letra": ["A", "B", "S"],
            "Nombre": ["Aulas Generales", "Laboratorios", "SITE"]
        })
        df_edif.to_excel(writer, sheet_name="Edificios", index=False)
        df_plantas = pd.DataFrame({
            "Edificio_Letra": ["A", "A", "B"],
            "Nivel": [1, 2, 1],
            "Uso": ["Aulas", "Administrativo", "Laboratorios"],
            "Rack_Red": ["No", "Sí", "Sí"],
            "Accesible": ["Sí", "Sí", "Sí"]
        })
        df_plantas.to_excel(writer, sheet_name="Plantas", index=False)
        df_areas = pd.DataFrame({
            "Edificio_Letra": ["A", "A", "B"],
            "Nivel": [1, 2, 1],
            "Nombre_Area": ["SITE Principal", "Oficina RRHH", "Lab Química"],
            "Tipo_Area": ["SITE de Redes", "Oficina", "Laboratorio"]
        })
        df_areas.to_excel(writer, sheet_name="Áreas", index=False)
    buf.seek(0)
    return buf.getvalue()


def _generar_plantilla_excel_unidades():
    """Genera un archivo .xlsx de plantilla para Unidades Orgánicas. Retorna bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_u = pd.DataFrame({
            "Nombre": [
                "Dirección General",
                "Subdirección Académica",
                "Subdirección Administrativa",
                "Jefatura de Departamento de Sistemas",
            ],
            "Tipo_Nivel": [
                "Dirección General",
                "Subdirección",
                "Subdirección",
                "Jefatura de Departamento",
            ],
            "Depende_De": [
                "",
                "Dirección General",
                "Dirección General",
                "Subdirección Académica",
            ],
        })
        df_u.to_excel(writer, sheet_name="Unidades", index=False)
    buf.seek(0)
    return buf.getvalue()


def _procesar_foto_infantil(uploaded_file, max_bytes=1024 * 1024):
    """
    Procesa la foto subida con Pillow:
    - Recorta con ImageOps.fit al centro (proporción tamaño infantil México: 2.5 x 3.0 cm = 5:6)
    - Redimensiona a 300x360 px (súper ligero)
    - Convierte a JPEG con compresión ~85%, garantizando < max_bytes (default 1MB)
    Retorna bytes JPEG.
    """
    img = PILImage.open(io.BytesIO(uploaded_file.getvalue()))
    if img.mode in ("RGBA", "P", "LA"):
        fondo = PILImage.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P" and "transparency" in img.info:
            img = img.convert("RGBA")
        fondo.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = fondo
    elif img.mode != "RGB":
        img = img.convert("RGB")
    # Proporción 2.5:3.0 cm = 5:6; en px: 300x360 (~30–50 KB con quality 85)
    tamano = (300, 360)
    img_fit = ImageOps.fit(img, tamano, method=PILImage.Resampling.LANCZOS)
    quality = 85
    while quality > 20:
        buf = io.BytesIO()
        img_fit.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            break
        quality -= 10
    buf.seek(0)
    return buf.read()


def _generar_vcard_docente(doc):
    """Genera el texto vCard 3.0 para un docente (nombre, título, puesto, correo)."""
    titulo = (doc.titulo_abreviatura or "").strip()
    nombre = (doc.nombre or "").strip()
    ap_pat = (doc.apellido_paterno or "").strip()
    ap_mat = (doc.apellido_materno or "").strip()
    puesto = doc.puesto.nombre if doc.puesto else ""
    correo = (doc.correo_institucional or "").strip()
    # N: Apellido;Nombre;;Prefijo; - vCard 3.0
    apellidos = " ".join(x for x in [ap_pat, ap_mat] if x)
    nombre_completo = " ".join(x for x in [titulo, nombre, ap_pat, ap_mat] if x)
    lineas = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{apellidos};{nombre};;{titulo};",
        f"FN:{nombre_completo}",
        f"TITLE:{puesto}",
        f"EMAIL:{correo}",
        "END:VCARD"
    ]
    return "\n".join(lineas)


def _generar_qr_vcard(vcard_texto):
    """Genera imagen QR en memoria (BytesIO) a partir del texto vCard."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(vcard_texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _generar_cv_pdf(persona):
    """Genera el CV en PDF y retorna los bytes del archivo."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors

    def _v(x): return x if x else "—"
    def _f(d): return d.strftime('%d/%m/%Y') if d else "—"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(name="TituloCV", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#1b5e20"), spaceAfter=6)
    seccion_style = ParagraphStyle(name="SeccionCV", parent=styles["Heading2"], fontSize=10, textColor=colors.HexColor("#1b5e20"), spaceBefore=12, spaceAfter=4)
    normal_style = styles["Normal"]

    nombre_full = f"{persona.titulo_abreviatura or ''} {persona.nombre or ''} {persona.apellido_paterno or ''} {persona.apellido_materno or ''}".strip()
    puesto_nom = persona.puesto.nombre if persona.puesto else "N/A"

    # Foto y QR
    foto_img = None
    if persona.fotografia and os.path.exists(persona.fotografia):
        try:
            foto_img = Image(persona.fotografia, width=2.5*cm, height=2.5*cm)
        except Exception:
            foto_img = None
    qr_img = None
    if persona.correo_institucional:
        vcard = _generar_vcard_docente(persona)
        qr_buf = _generar_qr_vcard(vcard)
        try:
            qr_img = Image(qr_buf, width=2.2*cm, height=2.2*cm)
        except Exception:
            qr_img = None

    header_style = ParagraphStyle(name="HeaderCV", parent=normal_style, textColor=colors.white, fontSize=11)
    c1 = foto_img if foto_img else Paragraph("<i>Foto</i>", header_style)
    c2 = Paragraph(f"<b>{nombre_full}</b><br/>{puesto_nom}<br/>📧 {_v(persona.correo_institucional)} | 📱 {_v(persona.celular_personal)} | Ext. {_v(persona.extension)}", header_style)
    c3 = qr_img if qr_img else Paragraph("", normal_style)
    fila = [c1, c2, c3]
    t_header = Table([fila], colWidths=[3*cm, 12*cm, 3*cm])
    t_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1b5e20")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    elementos = [t_header, Spacer(1, 0.5*cm)]

    def _bloque(titulo, lineas):
        elementos.append(Paragraph(titulo, seccion_style))
        for l in lineas:
            elementos.append(Paragraph(l, normal_style))
        elementos.append(Spacer(1, 0.2*cm))

    _bloque("📞 Contacto", [
        f"Correo institucional: {_v(persona.correo_institucional)}",
        f"Correo personal: {_v(persona.correo_personal)}",
        f"Celular: {_v(persona.celular_personal)}",
        f"Tel. oficina: {_v(persona.telefono_oficina)} Ext. {_v(persona.extension)}",
    ])
    _bloque("🎓 Formación Académica", [
        f"Título: {_v(persona.titulo_abreviatura)}",
        f"Licenciatura: {_v(persona.licenciatura)}",
        f"Maestría: {_v(persona.maestria)}",
        f"Doctorado: {_v(persona.doctorado)}",
    ])
    prog_text = " • ".join(x.strip() for x in (persona.programas_educativos or "").split(",") if x.strip()) if persona.programas_educativos else "—"
    _bloque("🎓 Programas Educativos", [prog_text])
    prod_text = "<br/>".join(f"• {p.tipo}: {p.titulo or ''}" + (f" — {p.titulo_capitulo}" if p.titulo_capitulo else "") + f" ({_f(p.fecha)})" for p in (persona.producciones or [])) if persona.producciones else "—"
    _bloque("📚 Producción Académica", [prod_text])
    cur_text = "<br/>".join(f"• {c.nombre_curso or ''} — {c.institucion or ''} ({c.horas or 0} hrs, {_f(c.fecha_termino)})" for c in (persona.cursos or [])) if persona.cursos else "—"
    _bloque("🛠️ Capacitación", [cur_text])
    _bloque("🏢 Datos Laborales", [
        f"Ubicación: Edif. {_v(persona.edificio)}, Planta {_v(persona.planta)}",
        f"Área: {_v(persona.area_asignada)}",
        f"Ingreso: {_f(persona.fecha_ingreso)}",
        f"Contrato: {_v(persona.tipo_contrato)} · {_v(persona.jornada_laboral)}",
    ])
    _bloque("🆔 Identidad Oficial", [
        f"CURP: {_v(persona.curp)}",
        f"RFC: {_v(persona.rfc)}",
        f"NSS: {_v(persona.nss)}",
    ])
    _bloque("📍 Datos Personales", [
        f"Domicilio: {_v(persona.domicilio)}",
        f"Nacimiento: {_f(persona.fecha_nacimiento)} · {_v(persona.genero)} · {_v(persona.estado_civil)}",
    ])

    doc.build(elementos)
    buf.seek(0)
    return buf.getvalue()


def renderizar_organigrama(unidades, puestos, personal_lista, parent_id=None, nivel=0):
    """
    Renderiza el organigrama recursivamente: Dirección -> Subdirección -> Jefatura -> ...
    Soporta niveles infinitos usando parent_id para la jerarquía.
    """
    hijos = [u for u in unidades if u.parent_id == parent_id]
    indent = nivel * 12
    sp_u = "&nbsp;" * indent
    sp_p = "&nbsp;" * (indent + 12)
    sp_e = "&nbsp;" * (indent + 24)
    _linea_h = '<div style="border-top:1px solid rgba(0,0,0,0.2);margin:2px 0 4px 0;"></div>'

    for u in hijos:
        # === UNIDAD (nivel recursivo) ===
        c_txt, c_ed, c_del = st.columns([8, 1, 1])
        with c_txt:
            st.markdown(f"{sp_u} <i class='fa-solid fa-folder fa-icon' style='color:#1b5e20;'></i> **{u.nombre}** <span style='color:gray; font-size:0.85em;'>({u.tipo_nivel})</span>", unsafe_allow_html=True)
        with c_ed:
            if st.button(":material/edit:", key=f"eu_{u.id}", help="Editar Unidad"):
                reset_states()
                st.session_state.edit_u = u.id
        with c_del:
            if st.button(":material/delete:", key=f"du_{u.id}", help="Eliminar Unidad"):
                reset_states()
                st.session_state.del_u = u.id
        st.markdown(_linea_h, unsafe_allow_html=True)

        if st.session_state.edit_u == u.id:
            with st.container():
                n_nom = st.text_input("Renombrar unidad:", value=u.nombre, key=f"in_u_{u.id}")
                cb1, cb2 = st.columns(2)
                if cb1.button(":material/save: Guardar", key=f"sv_u_{u.id}"):
                    session.query(Unidad).get(u.id).nombre = n_nom
                    session.commit()
                    reset_states()
                    st.rerun()
                if cb2.button(":material/close: Cancelar", key=f"cc_u_{u.id}"):
                    reset_states()
                    st.rerun()

        if st.session_state.del_u == u.id:
            st.warning("¿Borrar unidad y todo lo que depende de ella?")
            cb1, cb2 = st.columns(2)
            if cb1.button(":material/check: Sí, Eliminar", key=f"cd_u_{u.id}"):
                session.delete(session.query(Unidad).get(u.id))
                session.commit()
                reset_states()
                st.rerun()
            if cb2.button(":material/close: Cancelar", key=f"cx_u_{u.id}"):
                reset_states()
                st.rerun()

        # === PUESTOS de esta unidad ===
        puestos_unidad = [p for p in puestos if p.unidad_id == u.id]
        for p in puestos_unidad:
            cp_txt, cp_ed, cp_del = st.columns([8, 1, 1])
            with cp_txt:
                st.markdown(f"{sp_p} <i class='fa-solid fa-briefcase fa-icon' style='color:#2980b9;'></i> <span style='color:#2980b9; font-weight:bold;'>{p.nombre}</span>", unsafe_allow_html=True)
            with cp_ed:
                if st.button(":material/edit:", key=f"ep_{p.id}", help="Editar Puesto"):
                    reset_states()
                    st.session_state.edit_p = p.id
            with cp_del:
                if st.button(":material/delete:", key=f"dp_{p.id}", help="Eliminar Puesto"):
                    reset_states()
                    st.session_state.del_p = p.id
            st.markdown(_linea_h, unsafe_allow_html=True)

            if st.session_state.edit_p == p.id:
                with st.container():
                    n_puesto = st.text_input("Renombrar puesto:", value=p.nombre, key=f"in_p_{p.id}")
                    cb1, cb2 = st.columns(2)
                    if cb1.button(":material/save: Guardar", key=f"sv_p_{p.id}"):
                        session.query(Puesto).get(p.id).nombre = n_puesto
                        session.commit()
                        reset_states()
                        st.rerun()
                    if cb2.button(":material/close: Cancelar", key=f"cc_p_{p.id}"):
                        reset_states()
                        st.rerun()

            if st.session_state.del_p == p.id:
                st.warning("¿Eliminar este puesto? Se borrará al empleado asignado también.")
                cb1, cb2 = st.columns(2)
                if cb1.button(":material/check: Sí, Eliminar", key=f"cd_p_{p.id}"):
                    session.delete(session.query(Puesto).get(p.id))
                    session.commit()
                    reset_states()
                    st.rerun()
                if cb2.button(":material/close: Cancelar", key=f"cx_p_{p.id}"):
                    reset_states()
                    st.rerun()

            # === EMPLEADOS del puesto ===
            emps = [e for e in personal_lista if e.puesto_id == p.id]
            if not emps:
                st.markdown(f"{sp_e} <i class='fa-solid fa-user fa-icon' style='color:#9ca3af;'></i> <span style='color:gray; font-style:italic;'>*(Vacante)*</span>", unsafe_allow_html=True)
            else:
                for e in emps:
                    ce_txt, ce_ed, ce_del = st.columns([8, 1, 1])
                    with ce_txt:
                        st.markdown(f"{sp_e} <i class='fa-solid fa-user fa-icon' style='color:#16a085;'></i> <span style='color:#16a085;'>{e.nombre} {e.apellido_paterno}</span>", unsafe_allow_html=True)
                    with ce_ed:
                        if st.button(":material/edit:", key=f"ee_{e.id}", help="Editar expediente de esta persona"):
                            reset_states()
                            st.session_state["persona_editar_id"] = e.id
                            st.rerun()
                    with ce_del:
                        if st.button(":material/delete:", key=f"de_{e.id}", help="Despedir Persona"):
                            reset_states()
                            st.session_state.del_e = e.id
                    st.markdown(_linea_h, unsafe_allow_html=True)

                    if st.session_state.del_e == e.id:
                        st.warning("¿Quitar a esta persona del puesto? (El puesto quedará vacante)")
                        cb1, cb2 = st.columns(2)
                        if cb1.button(":material/check: Sí, Despedir", key=f"cd_e_{e.id}"):
                            session.delete(session.query(Personal).get(e.id))
                            session.commit()
                            reset_states()
                            st.rerun()
                        if cb2.button(":material/close: Cancelar", key=f"cx_e_{e.id}"):
                            reset_states()
                            st.rerun()

        # Recursión: sub-unidades (Subdirecciones bajo Dirección, Jefaturas bajo Subdirección, etc.)
        renderizar_organigrama(unidades, puestos, personal_lista, u.id, nivel + 1)


def _nombre_completo_personal(p):
    """Retorna nombre completo de una persona."""
    n = (p.nombre or "").strip()
    ap = (p.apellido_paterno or "").strip()
    am = (p.apellido_materno or "").strip()
    return " ".join(x for x in [n, ap, am] if x) or "N/A"


def _clasificar_unidad(nombre_unidad):
    """Clasifica un nombre de unidad en: direccion, planeacion, academica, administrativos."""
    if not nombre_unidad:
        return "otro"
    n = nombre_unidad.upper()
    if "DIRECCIÓN GENERAL" in n or "DIRECCION GENERAL" in n:
        return "direccion"
    if "PLANEACIÓN" in n or "PLANEACION" in n or "VINCULACIÓN" in n or "VINCULACION" in n:
        return "planeacion"
    if "ACADÉMICA" in n or "ACADEMICA" in n or "JEFATURA DE DIVISIÓN" in n or "DIVISIÓN" in n or "DIVISION" in n or "INGENIERÍA" in n or "INGENIERIA" in n or "LICENCIATURA" in n:
        return "academica"
    if "ADMINISTRATIVOS" in n or "ADMINISTRATIVO" in n or "SERVICIOS" in n or "CÓMPUTO" in n or "COMPUTO" in n or "RECURSOS MATERIALES" in n:
        return "administrativos"
    return "otro"


def _es_staff_direccion(puesto_nombre):
    """True si el puesto es de staff directo de Dirección (Secretaria, Chofer, etc.)."""
    if not puesto_nombre:
        return False
    p = puesto_nombre.upper()
    return "SECRETARIA" in p or "SECRETARIO" in p or "CHOFER" in p or "ASISTENTE" in p


def _es_director_general(puesto_nombre):
    """True si el puesto es Director General."""
    if not puesto_nombre:
        return False
    return "DIRECTOR GENERAL" in (puesto_nombre or "").upper()


def _es_docente(puesto_nombre):
    """True si el puesto es de docente/investigador."""
    if not puesto_nombre:
        return False
    p = puesto_nombre.upper()
    return "DOCENTE" in p or "INVESTIGADOR" in p or "PROFESOR" in p


# Ancho estándar de fotos en Directorio Institucional (encabezado y áreas debajo)
_ANCHO_FOTO_DIRECTORIO = 120

def _render_docente_expediente(doc, session_db, puesto_id_to_puesto):
    """Renderiza el expediente integral del docente (mismo contenido que pestaña Docentes)."""
    try:
        session_db.refresh(doc)
    except Exception:
        pass
    puesto_nom = puesto_id_to_puesto.get(doc.puesto_id).nombre if doc.puesto_id and puesto_id_to_puesto.get(doc.puesto_id) else "N/A"
    titulo_full = f"{doc.titulo_abreviatura or ''} {doc.nombre or ''} {doc.apellido_paterno or ''} {doc.apellido_materno or ''}".strip()
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 2, 3])
        with col1:
            if doc.fotografia and os.path.exists(doc.fotografia):
                st.image(doc.fotografia, width=_ANCHO_FOTO_DIRECTORIO)
            else:
                st.info("📷 Sin foto")
        with col2:
            st.markdown(f"**{titulo_full}** — {puesto_nom}")
            st.write(f"**Correo:** {doc.correo_institucional or 'N/A'}")
            st.write(f"**Ubicación:** Edificio {doc.edificio or 'N/A'}, Planta {doc.planta or 'N/A'}")
            st.write(f"**Área:** {doc.area_asignada or 'No especificada'}")
        with col3:
            st.write(f"**Licenciatura:** {doc.licenciatura or 'N/A'}")
            st.write(f"**Maestría:** {doc.maestria or 'N/A'}")
            st.write(f"**Doctorado:** {doc.doctorado or 'N/A'}")

        # Mostrar el bloque de Producción/Capacitación solo si hay información relevante
        producciones = list(doc.producciones or [])
        libros = [x for x in producciones if x.tipo == "Libro"]
        caps = [x for x in producciones if x.tipo == "Capítulo de Libro"]
        arts = [x for x in producciones if x.tipo == "Artículo"]
        cursos = list(doc.cursos or [])
        tiene_prog = bool(doc.programas_educativos and doc.programas_educativos.strip())

        if libros or caps or arts or cursos or tiene_prog:
            with st.expander(":material/menu_book: Producción y Capacitación", expanded=False):
                t_libros, t_capitulos, t_articulos, t_cursos, t_prog = st.tabs([
                    ":material/menu_book: Libros", ":material/book: Capítulos", ":material/article: Artículos", ":material/construction: Cursos/Capacitación", ":material/school: Prog. Educativos"
                ])
                with t_libros:
                    if libros:
                        datos_tabla = []
                        for l in libros:
                            ident_raw = l.identificador or ""
                            if " | " in ident_raw:
                                isbn, ident_libro = ident_raw.split(" | ", 1)
                                ident_libro = ident_libro.strip() if ident_libro.strip() else "N/A"
                            else:
                                isbn = ident_raw if ident_raw else "N/A"
                                ident_libro = "N/A"
                            datos_tabla.append({
                                ":material/calendar_today: Fecha": l.fecha.strftime('%d/%m/%Y') if l.fecha else "S/F",
                                ":material/numbers: ISBN": isbn,
                                ":material/tag: Identificador del Libro": ident_libro,
                                ":material/book: Título": l.titulo or ""
                            })
                        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
                    else:
                        st.info("Este docente no tiene libros registrados.")
                with t_capitulos:
                    if caps:
                        datos_cap = []
                        for c in caps:
                            ident_raw = c.identificador or ""
                            isbn = ident_raw.split(" | ", 1)[0].strip() if ident_raw else "N/A"
                            datos_cap.append({
                                ":material/calendar_today: Fecha": c.fecha.strftime('%d/%m/%Y') if c.fecha else "S/F",
                                ":material/book: Título del Capítulo": c.titulo_capitulo or "",
                                ":material/numbers: ISBN": isbn,
                                ":material/menu_book: Título del Libro": c.titulo or ""
                            })
                        st.dataframe(pd.DataFrame(datos_cap), use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay capítulos registrados.")
                with t_articulos:
                    if arts:
                        datos_art = []
                        for a in arts:
                            ident_raw = a.identificador or ""
                            issn = ident_raw.split(" | ", 1)[0].strip() if ident_raw else "N/A"
                            datos_art.append({
                                ":material/calendar_today: Fecha": a.fecha.strftime('%d/%m/%Y') if a.fecha else "S/F",
                                ":material/article: Artículo": a.revista_medio or "",
                                ":material/numbers: ISSN": issn,
                                ":material/description: Título de Artículo": a.titulo or ""
                            })
                        st.dataframe(pd.DataFrame(datos_art), use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay artículos registrados.")
                with t_cursos:
                    if cursos:
                        datos_cursos = []
                        for c in cursos:
                            datos_cursos.append({
                                ":material/calendar_today: Fecha de Finalización": c.fecha_termino.strftime('%d/%m/%Y') if c.fecha_termino else "S/F",
                                ":material/construction: Curso Taller": c.nombre_curso or "",
                                ":material/business: Institución que lo imparte": c.institucion or "",
                                ":material/schedule: Horas Totales": c.horas if c.horas is not None else "N/A",
                                ":material/description: Documento Recibido": c.tipo_documento or "N/A"
                            })
                        st.dataframe(pd.DataFrame(datos_cursos), use_container_width=True, hide_index=True)
                    else:
                        st.info("No cuenta con cursos registrados.")
                with t_prog:
                    if tiene_prog:
                        carreras = [c.strip() for c in doc.programas_educativos.split(",") if c.strip()]
                        if carreras:
                            carreras_cat = session_db.query(Carrera).all()
                            link_por_carrera = {f"{c.tipo_nivel} en {c.nombre} ({c.modalidad})": (c.link_material or "").strip() for c in carreras_cat}
                            filas_lista = []
                            for cr in carreras:
                                clave = cr.split(" | ", 1)[0].strip()
                                link = link_por_carrera.get(clave, "")
                                if link:
                                    filas_lista.append(f'<tr><td><i class="fa-solid fa-graduation-cap fa-icon" style="color:#1b5e20;"></i> <a href="{link}" target="_blank">{cr}</a></td></tr>')
                                else:
                                    filas_lista.append(f'<tr><td><i class="fa-solid fa-graduation-cap fa-icon" style="color:#1b5e20;"></i> {cr}</td></tr>')
                            tabla_html = f'<table style="width:100%"><tbody>{"".join(filas_lista)}</tbody></table>'
                            st.markdown(tabla_html, unsafe_allow_html=True)
                        else:
                            st.info("No hay programas educativos asignados.")
                    else:
                        st.info("No hay programas educativos asignados.")


def _render_persona_tarjeta(p, puesto_id_to_puesto, show_foto=True, session_db=None):
    """Tarjeta compacta de personal no docente: foto a la izquierda y datos en pocas líneas.
    Si tiene cursos o producción académica, se muestra el expander Producción y Capacitación."""
    try:
        if session_db:
            session_db.refresh(p)
    except Exception:
        pass
    puesto_nom = puesto_id_to_puesto.get(p.puesto_id).nombre if p.puesto_id and puesto_id_to_puesto.get(p.puesto_id) else "N/A"
    nombre_con_titulo = f"{p.titulo_abreviatura or ''} {p.nombre or ''} {p.apellido_paterno or ''} {p.apellido_materno or ''}".strip() or _nombre_completo_personal(p)
    # Ubicación: Edificio, Planta, Área Específica
    ubi_partes = [
        f"Edificio {p.edificio or 'N/A'}",
        f"Planta {p.planta or 'N/A'}",
        (p.area_asignada or 'N/A').strip() or 'N/A'
    ]
    linea_ubicacion = " · ".join(ubi_partes)
    # Teléfono y extensión (línea aparte)
    tel_partes = []
    if p.telefono_oficina and str(p.telefono_oficina).strip():
        tel_partes.append(p.telefono_oficina.strip())
    if p.extension and str(p.extension).strip():
        tel_partes.append(f"Extensión: {p.extension.strip()}")
    linea_telefono = " · ".join(tel_partes) if tel_partes else ""
    _suf = " — :material/workspace_premium: Mención Honorífica"
    lineas_formacion = [x for x in [
        f"Licenciatura: {p.licenciatura}{_suf}" if (p.licenciatura and getattr(p, "licenciatura_mencion_honorifica", False)) else (f"Licenciatura: {p.licenciatura}" if p.licenciatura else None),
        f"Maestría: {p.maestria}{_suf}" if (p.maestria and getattr(p, "maestria_mencion_honorifica", False)) else (f"Maestría: {p.maestria}" if p.maestria else None),
        f"Doctorado: {p.doctorado}{_suf}" if (p.doctorado and getattr(p, "doctorado_mencion_honorifica", False)) else (f"Doctorado: {p.doctorado}" if p.doctorado else None),
    ] if x]
    with st.container(border=True):
        col_f, col_i = st.columns([1, 5])
        with col_f:
            ruta_foto = p.fotografia
            if show_foto and ruta_foto and os.path.exists(ruta_foto):
                try:
                    st.image(ruta_foto, width=_ANCHO_FOTO_DIRECTORIO)
                except Exception:
                    st.caption("📷")
            elif show_foto:
                st.caption(":material/person:")
        with col_i:
            st.markdown(f"**{nombre_con_titulo}**")
            st.caption(linea_ubicacion)
            if linea_telefono:
                st.caption(linea_telefono)
            if p.correo_institucional:
                st.caption(p.correo_institucional)
            if lineas_formacion:
                for linea in lineas_formacion:
                    st.caption(linea)
            st.caption(f"<span style='color:gray;'>{puesto_nom}</span>", unsafe_allow_html=True)

        # Producción y Capacitación para el resto del personal (si tiene cursos o producción)
        producciones = list(p.producciones or [])
        libros = [x for x in producciones if x.tipo == "Libro"]
        caps = [x for x in producciones if x.tipo == "Capítulo de Libro"]
        arts = [x for x in producciones if x.tipo == "Artículo"]
        cursos = list(p.cursos or [])
        tiene_prog = bool(p.programas_educativos and (p.programas_educativos or "").strip())
        if libros or caps or arts or cursos or tiene_prog:
            with st.expander(":material/menu_book: Producción y Capacitación", expanded=False):
                t_libros, t_capitulos, t_articulos, t_cursos, t_prog = st.tabs([
                    ":material/menu_book: Libros", ":material/book: Capítulos", ":material/article: Artículos", ":material/construction: Cursos/Capacitación", ":material/school: Prog. Educativos"
                ])
                with t_libros:
                    if libros:
                        datos_tabla = [{"Fecha": l.fecha.strftime('%d/%m/%Y') if l.fecha else "S/F", "Título": l.titulo or ""} for l in libros]
                        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin libros registrados.")
                with t_capitulos:
                    if caps:
                        datos_cap = [{"Fecha": c.fecha.strftime('%d/%m/%Y') if c.fecha else "S/F", "Capítulo": c.titulo_capitulo or "", "Libro": c.titulo or ""} for c in caps]
                        st.dataframe(pd.DataFrame(datos_cap), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin capítulos registrados.")
                with t_articulos:
                    if arts:
                        datos_art = [{"Fecha": a.fecha.strftime('%d/%m/%Y') if a.fecha else "S/F", "Artículo": a.titulo or "", "Revista/Medio": a.revista_medio or ""} for a in arts]
                        st.dataframe(pd.DataFrame(datos_art), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin artículos registrados.")
                with t_cursos:
                    if cursos:
                        datos_cursos = [{"Fecha": c.fecha_termino.strftime('%d/%m/%Y') if c.fecha_termino else "S/F", "Curso": c.nombre_curso or "", "Institución": c.institucion or "", "Horas": c.horas or 0} for c in cursos]
                        st.dataframe(pd.DataFrame(datos_cursos), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin cursos registrados.")
                with t_prog:
                    if tiene_prog:
                        carreras = [c.strip() for c in (p.programas_educativos or "").split(",") if c.strip()]
                        if carreras:
                            if session_db:
                                carreras_cat = session_db.query(Carrera).all()
                                link_por_carrera = {f"{c.tipo_nivel} en {c.nombre} ({c.modalidad})": (c.link_material or "").strip() for c in carreras_cat}
                                filas_lista = []
                                for cr in carreras:
                                    clave = cr.split(" | ", 1)[0].strip()
                                    link = link_por_carrera.get(clave, "")
                                    if link:
                                        filas_lista.append(f'<tr><td><i class="fa-solid fa-graduation-cap fa-icon" style="color:#1b5e20;"></i> <a href="{link}" target="_blank">{cr}</a></td></tr>')
                                    else:
                                        filas_lista.append(f'<tr><td><i class="fa-solid fa-graduation-cap fa-icon" style="color:#1b5e20;"></i> {cr}</td></tr>')
                                st.markdown(f'<table style="width:100%"><tbody>{"".join(filas_lista)}</tbody></table>', unsafe_allow_html=True)
                            else:
                                for c in carreras:
                                    st.write(c)
                        else:
                            st.info("No hay programas educativos asignados.")
                    else:
                        st.info("No hay programas educativos asignados.")


def renderizar_organigrama_visual(session_db, unidades, puestos, personal_lista):
    """
    Renderiza el organigrama dinámico visual: Dirección General (cúspide),
    tres columnas de subdirecciones, y expanders por departamento/jefatura.
    Respeta la jerarquía: Subdirección -> Jefaturas de División -> Docentes.
    Los docentes muestran el mismo expediente integral que en la pestaña Docentes.
    """
    unidad_id_to_unidad = {u.id: u for u in unidades}
    puesto_id_to_puesto = {p.id: p for p in puestos}
    puesto_id_to_unidad = {p.id: unidad_id_to_unidad.get(p.unidad_id) for p in puestos if p.unidad_id in unidad_id_to_unidad}

    # Personal por unidad
    personal_por_unidad = {}
    for p in personal_lista:
        if p.puesto_id:
            u = puesto_id_to_unidad.get(p.puesto_id)
            if u:
                uid = u.id
                if uid not in personal_por_unidad:
                    personal_por_unidad[uid] = []
                personal_por_unidad[uid].append(p)

    # Hijos por unidad (jerarquía)
    hijos_por_unidad = {}
    for u in unidades:
        pid = u.parent_id
        if pid not in hijos_por_unidad:
            hijos_por_unidad[pid] = []
        hijos_por_unidad[pid].append(u)

    # Dirección General: unidades con parent_id=None o tipo Dirección General
    dir_general = None
    for u in unidades:
        if u.tipo_nivel == "Dirección General" or (u.parent_id is None and "DIRECCIÓN" in (u.nombre or "").upper()):
            dir_general = u
            break
    if not dir_general:
        dir_general = next((u for u in unidades if u.parent_id is None), None)

    def _render_persona_o_docente(p, show_foto=False):
        """Renderiza tarjeta simple o expediente integral según sea docente."""
        puesto_nom = puesto_id_to_puesto.get(p.puesto_id).nombre if p.puesto_id and puesto_id_to_puesto.get(p.puesto_id) else ""
        if _es_docente(puesto_nom):
            _render_docente_expediente(p, session_db, puesto_id_to_puesto)
        else:
            # Para personal no docente: tarjeta compacta y, si tiene cursos o producción, expander Producción y Capacitación
            _render_persona_tarjeta(p, puesto_id_to_puesto, show_foto=True, session_db=session_db)


    st.write("BD admin:", DB_PATH)
    st.write("Existe archivo admin:", os.path.exists(DB_PATH))
    st.write("Total unidades admin:", session.query(Unidad).count())
    st.write("Total puestos admin:", session.query(Puesto).count())
    st.write("Total personal admin:", session.query(Personal).count())

    # Nivel 1: Directorio Institucional (cúspide)
    st.markdown("---")
    st.markdown("<h2 style='text-align: center; color: 	#431616; font-size: 2rem;'><i class='fa-solid fa-sitemap fa-icon'></i> Directorio Institucional</h2>", unsafe_allow_html=True)
    col_izq, col_centro, col_der = st.columns([1, 6, 1])
    with col_centro:
        with st.container(border=True):
            personal_dir = personal_por_unidad.get(dir_general.id, []) if dir_general else []
            def _puesto_nom(pid):
                po = puesto_id_to_puesto.get(pid) if pid else None
                return (po.nombre or "") if po else ""
            dg = [p for p in personal_dir if _es_director_general(_puesto_nom(p.puesto_id))]
            staff = [p for p in personal_dir if _es_staff_direccion(_puesto_nom(p.puesto_id))]
            otros = [p for p in personal_dir if p not in dg and p not in staff]

            # Mostrar solo al Director General en la tarjeta principal
            mostrar_en_tarjeta = dg or (staff[:1] if staff else (personal_dir[:1] if personal_dir else []))
            for p in mostrar_en_tarjeta:
                _render_persona_o_docente(p, show_foto=True)

    # Expander para el resto del personal de la Dirección (mismo formato que subdirecciones)
    if dir_general:
        resto_dir = staff + otros
        if resto_dir:
            total_resto = len(resto_dir)
            with st.expander(
                f":material/folder: {dir_general.nombre or 'Dirección General'} ({total_resto} persona{'s' if total_resto != 1 else ''})",
                expanded=False
            ):
                st.caption("_Personal de la unidad de Dirección:_")
                for p in resto_dir:
                    _render_persona_o_docente(p, show_foto=True)

    st.markdown("---")

    # Subdirecciones / Unidades de segundo nivel: hijos de Dirección General, o todas las demás si no hay jerarquía
    subdirecciones = hijos_por_unidad.get(dir_general.id, []) if dir_general else []
    if not subdirecciones and dir_general:
        # Fallback: estructura plana, usar todas las unidades excepto Dirección General
        subdirecciones = [u for u in unidades if u.id != dir_general.id]
    u_plan = [u for u in subdirecciones if _clasificar_unidad(u.nombre) == "planeacion"]
    u_acad = [u for u in subdirecciones if _clasificar_unidad(u.nombre) == "academica"]
    u_admin = [u for u in subdirecciones if _clasificar_unidad(u.nombre) == "administrativos"]
    u_otros = [u for u in subdirecciones if _clasificar_unidad(u.nombre) == "otro"]

    def _render_columna_unidades(lista_u):
        for u in lista_u:
            pers = personal_por_unidad.get(u.id, [])
            hijos = hijos_por_unidad.get(u.id, [])
            total = len(pers) + sum(len(personal_por_unidad.get(h.id, [])) for h in hijos)
            with st.expander(f":material/folder: {u.nombre or 'N/A'} ({total} persona{'s' if total != 1 else ''})", expanded=False):
                # Staff directo de la subdirección
                if pers:
                    st.caption("_Personal de la subdirección:_")
                    for p in pers:
                        _render_persona_o_docente(p, show_foto=False)
                # Jefaturas/Departamentos dentro (Cuerpo Docente en sus respectivas divisiones)
                for hijo in hijos:
                    pers_h = personal_por_unidad.get(hijo.id, [])
                    if pers_h:
                        with st.expander(f":material/folder_open: {hijo.nombre or 'N/A'} ({len(pers_h)})", expanded=False):
                            for p in pers_h:
                                _render_persona_o_docente(p, show_foto=False)

    # Nivel 2: Subdirecciones apiladas verticalmente (una debajo de otra), sin separadores extra
    if u_plan:
        _render_columna_unidades(u_plan)
    if u_acad:
        _render_columna_unidades(u_acad)
    if u_admin:
        _render_columna_unidades(u_admin)

    # Unidades no clasificadas (si las hay) se muestran igual que las demás, sin encabezado extra
    if u_otros:
        for u in u_otros:
            pers = personal_por_unidad.get(u.id, [])
            hijos = hijos_por_unidad.get(u.id, [])
            total = len(pers) + sum(len(personal_por_unidad.get(h.id, [])) for h in hijos)
            with st.expander(f":material/folder: {u.nombre or 'N/A'} ({total} persona{'s' if total != 1 else ''})", expanded=False):
                if pers:
                    st.caption("_Personal de la unidad:_")
                    for p in pers:
                        _render_persona_o_docente(p, show_foto=False)
                for hijo in hijos:
                    pers_h = personal_por_unidad.get(hijo.id, [])
                    if pers_h:
                        with st.expander(f":material/folder_open: {hijo.nombre or 'N/A'} ({len(pers_h)})", expanded=False):
                            for p in pers_h:
                                _render_persona_o_docente(p, show_foto=False)


# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS (Debe ir arriba) ---
engine = create_engine('sqlite:///directorio_escarcega.db', echo=False)
Base.metadata.create_all(engine)

# Migración: añadir columnas faltantes en `personal` si no existen
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(personal)"))
        cols = [row[1] for row in r]
        mig = [
            # menciones honoríficas (compat)
            ("licenciatura_mencion_honorifica", "BOOLEAN DEFAULT 0"),
            ("maestria_mencion_honorifica", "BOOLEAN DEFAULT 0"),
            ("doctorado_mencion_honorifica", "BOOLEAN DEFAULT 0"),
            # nuevos campos solicitados
            ("numero_empleado", "TEXT"),
            ("grado_academico", "TEXT"),
            ("cvu", "TEXT"),
            ("estado_residencia", "TEXT"),
            ("municipio_residencia", "TEXT"),
            ("localidad_residencia", "TEXT"),
            ("codigo_postal", "TEXT"),
            ("telefono_casa", "TEXT"),
            ("telefono_otro", "TEXT"),
            ("nombre_padre", "TEXT"),
            ("nombre_madre", "TEXT"),
            ("numero_hijos", "INTEGER"),
            ("talla_camisa", "TEXT"),
            ("deporte", "TEXT"),
            ("actividad_cultural", "TEXT"),
            ("pasatiempo", "TEXT"),
            ("alergias", "TEXT"),
        ]
        for c, ddl in mig:
            if c not in cols:
                conn.execute(text(f"ALTER TABLE personal ADD COLUMN {c} {ddl}"))
        conn.commit()
except Exception:
    pass
Session = sessionmaker(bind=engine)
session = Session() # <--- AQUÍ SE DEFINE 'session'

def _hash_password(pw):
    """Genera hash seguro de la contraseña con werkzeug (bcrypt-like)."""
    try:
        from werkzeug.security import generate_password_hash
        return generate_password_hash(pw or "", method="pbkdf2:sha256")
    except ImportError:
        return hashlib.sha256((pw or "").encode()).hexdigest()

def _check_password(plain_pw, stored_hash):
    """Verifica si la contraseña coincide. Soporta werkzeug y SHA256 legacy."""
    if not stored_hash:
        return False
    try:
        from werkzeug.security import check_password_hash
        if stored_hash.startswith("pbkdf2:"):
            return check_password_hash(stored_hash, plain_pw or "")
        sha = hashlib.sha256((plain_pw or "").encode()).hexdigest()
        return stored_hash == sha
    except Exception:
        sha = hashlib.sha256((plain_pw or "").encode()).hexdigest()
        return stored_hash == sha

def _get_config_smtp():
    """Obtiene la configuración SMTP activa (singleton id=1)."""
    return session.query(ConfiguracionSMTP).filter_by(id=1).first()

def _enviar_email_restablecimiento(destinatario, codigo):
    """Envía el código de restablecimiento por correo. Retorna (True, None) o (False, mensaje_error)."""
    cfg = _get_config_smtp()
    if not cfg or not cfg.activo or not cfg.smtp_usuario or not cfg.smtp_clave:
        return False, "SMTP no configurado"
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        msg["From"] = cfg.smtp_usuario
        msg["To"] = destinatario
        msg["Subject"] = "Código para restablecer tu contraseña - Directorio ITS"
        cuerpo = f"""Has solicitado restablecer tu contraseña.

Tu código de restablecimiento es: {codigo}

Este código expira en 15 minutos.

Si no solicitaste este cambio, ignora este correo."""
        msg.attach(MIMEText(cuerpo, "plain"))
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_puerto) as server:
            if cfg.usar_tls:
                server.starttls()
            server.login(cfg.smtp_usuario, cfg.smtp_clave)
            server.sendmail(cfg.smtp_usuario, destinatario, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)

def _generar_token_restablecimiento():
    """Genera un token alfanumérico de 8 caracteres."""
    return secrets.token_hex(4)  # 8 caracteres hex

def _limpiar_tokens_expirados():
    """Elimina tokens de restablecimiento ya expirados."""
    from sqlalchemy import delete
    session.execute(delete(TokenRestablecimiento).where(TokenRestablecimiento.expira_en < datetime.now()))
    session.commit()

def _crear_usuario_admin_si_no_existe():
    """Si no hay usuarios en BD, crea admin/admin como Súper Admin."""
    if session.query(UsuarioSistema).count() == 0:
        u = UsuarioSistema(usuario="admin", password=_hash_password("admin"), rol="Súper Admin", personal_id=None)
        session.add(u)
        session.commit()


def registrar_bitacora(session_db, accion, modulo, detalles=""):
    """Registra una entrada en la bitácora de auditoría con el usuario actual."""
    usuario_actual = st.session_state.get("usuario_nombre", "Sistema")
    entrada = BitacoraActividad(
        usuario_nombre=usuario_actual,
        accion=accion,
        modulo=modulo,
        detalles=detalles or None
    )
    session_db.add(entrada)
    session_db.commit()


def _aplicar_payload_solicitud(session_db, solicitud):
    """
    Aplica el payload_json de una SolicitudCaptura aprobada a la tabla destino.
    Retorna True si se aplicó correctamente, False en caso contrario.
    """
    if not solicitud.payload_json or solicitud.estado != 'pendiente':
        return False
    try:
        payload = json.loads(solicitud.payload_json)
    except (json.JSONDecodeError, TypeError):
        return False
    tabla = (solicitud.tabla_destino or "").strip().lower()
    personal_id = solicitud.personal_id
    accion = (solicitud.accion or "modificar").lower()
    if tabla == "personal":
        persona = session_db.get(Personal, personal_id)
        if not persona:
            return False
        campos_personal = {"nombre", "apellido_paterno", "apellido_materno", "celular_personal", "correo_personal",
                          "telefono_oficina", "extension", "correo_institucional", "domicilio", "genero", "estado_civil",
                          "curp", "rfc", "nss", "licenciatura", "maestria", "doctorado", "titulo_abreviatura",
                          "programas_educativos", "fecha_nacimiento", "ine_pasaporte",
                          "licenciatura_mencion_honorifica", "maestria_mencion_honorifica", "doctorado_mencion_honorifica"}
        for k, v in payload.items():
            if k in campos_personal:
                if k == "fecha_nacimiento" and isinstance(v, str):
                    try:
                        from datetime import datetime
                        v = datetime.strptime(v[:10], "%Y-%m-%d").date()
                    except Exception:
                        pass
                if k in ("licenciatura_mencion_honorifica", "maestria_mencion_honorifica", "doctorado_mencion_honorifica"):
                    v = bool(v)
                setattr(persona, k, v)
    elif tabla == "producciones":
        if accion == "agregar":
            fec = payload.get("fecha")
            if isinstance(fec, str):
                try:
                    fec = datetime.strptime(fec[:10], "%Y-%m-%d").date()
                except Exception:
                    fec = datetime.now().date()
            reg = ProduccionAcademica(
                personal_id=personal_id,
                tipo=payload.get("tipo"),
                titulo=payload.get("titulo"),
                titulo_capitulo=payload.get("titulo_capitulo"),
                revista_medio=payload.get("revista_medio"),
                fecha=fec,
                identificador=payload.get("identificador", "") or "—"
            )
            session_db.add(reg)
        elif accion == "modificar" and solicitud.registro_ref_id:
            reg = session_db.get(ProduccionAcademica, solicitud.registro_ref_id)
            if reg:
                for k in ["tipo", "titulo", "titulo_capitulo", "revista_medio", "identificador"]:
                    if k in payload:
                        setattr(reg, k, payload[k])
                if "fecha" in payload:
                    fv = payload["fecha"]
                    if isinstance(fv, str):
                        try:
                            fv = datetime.strptime(fv[:10], "%Y-%m-%d").date()
                        except Exception:
                            pass
                    reg.fecha = fv
        elif accion == "eliminar" and solicitud.registro_ref_id:
            reg = session_db.get(ProduccionAcademica, solicitud.registro_ref_id)
            if reg:
                session_db.delete(reg)
    elif tabla == "cursos_cap":
        if accion == "agregar":
            fec = payload.get("fecha_termino")
            if isinstance(fec, str):
                try:
                    fec = datetime.strptime(fec[:10], "%Y-%m-%d").date()
                except Exception:
                    fec = datetime.now().date()
            reg = CursoCapacitacion(
                personal_id=personal_id,
                nombre_curso=payload.get("nombre_curso") or "",
                institucion=payload.get("institucion") or "",
                horas=int(payload.get("horas", 0) or 0),
                fecha_termino=fec,
                tipo_documento=payload.get("tipo_documento", "Constancia")
            )
            session_db.add(reg)
        elif accion == "modificar" and solicitud.registro_ref_id:
            reg = session_db.get(CursoCapacitacion, solicitud.registro_ref_id)
            if reg:
                for k in ["nombre_curso", "institucion", "tipo_documento"]:
                    if k in payload:
                        setattr(reg, k, payload[k])
                if "horas" in payload:
                    reg.horas = int(payload.get("horas") or 0)
                if "fecha_termino" in payload:
                    fv = payload["fecha_termino"]
                    if isinstance(fv, str):
                        try:
                            fv = datetime.strptime(fv[:10], "%Y-%m-%d").date()
                        except Exception:
                            fv = None
                    if fv is not None and hasattr(fv, "year"):
                        reg.fecha_termino = fv
        elif accion == "eliminar" and solicitud.registro_ref_id:
            reg = session_db.get(CursoCapacitacion, solicitud.registro_ref_id)
            if reg:
                session_db.delete(reg)
    else:
        return False
    return True


# --- 2. GATE DE LOGIN ---
if not st.session_state.autenticado:
    _crear_usuario_admin_si_no_existe()
    _limpiar_tokens_expirados()
    if "reset_codigo" not in st.session_state:
        st.session_state.reset_codigo = None
    if "reset_usuario" not in st.session_state:
        st.session_state.reset_usuario = None
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    col_empty, col_form, _ = st.columns([1, 2, 1])
    with col_form:
        with st.form("login_form"):
            st.markdown("### :material/lock: Inicio de Sesión")
            usuario_input = st.text_input("Usuario", placeholder="Nombre de usuario", autocomplete="username")
            pass_input = st.text_input("Contraseña", type="password", placeholder="Contraseña", autocomplete="current-password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                if usuario_input and pass_input:
                    usr = session.query(UsuarioSistema).filter(UsuarioSistema.usuario == usuario_input.strip()).first()
                    if usr and _check_password(pass_input, usr.password):
                        st.session_state.autenticado = True
                        st.session_state.rol = usr.rol
                        st.session_state.usuario_nombre = usr.usuario
                        st.session_state.personal_id = usr.personal_id
                        st.session_state.usuario_id = usr.id
                        # Cargar preferencias visuales del usuario
                        prefs = session.query(PreferenciasUsuario).filter_by(usuario_id=usr.id).first()
                        if prefs:
                            st.session_state.tema_visual = prefs.tema_visual or "Claro (Por defecto)"
                            raw_estilo = prefs.estilo_emojis or "Emojis de colores"
                            # Permitir que en estilo_emojis venga también el color de CV separado por |
                            partes = (raw_estilo or "").split("|", 1)
                            st.session_state.estilo_emojis = partes[0] or "Emojis de colores"
                            if len(partes) > 1 and partes[1].strip().startswith("#"):
                                st.session_state.cv_color_header = partes[1].strip()
                        else:
                            st.session_state.tema_visual = "Claro (Por defecto)"
                            st.session_state.estilo_emojis = "Emojis de colores"
                        registrar_bitacora(session, "LOGIN", "Autenticación", f"Usuario: {usr.usuario}")
                        st.success("Sesión iniciada correctamente.")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")
                else:
                    st.error("Indica usuario y contraseña.")

        st.markdown("<br/>", unsafe_allow_html=True)
        with st.expander(":material/key: ¿Olvidaste tu contraseña?"):
            if st.session_state.reset_codigo:
                st.info("Introduce el código que se generó y tu nueva contraseña. El código expira en 15 minutos.")
                if st.button(":material/undo: Cancelar y solicitar otro código", key="cancel_reset"):
                    st.session_state.reset_codigo = None
                    st.session_state.reset_usuario = None
                    st.rerun()
                with st.form("form_restablecer"):
                    st.caption(f"Usuario: **{st.session_state.reset_usuario}**")
                    codigo_rest = st.text_input("Código de restablecimiento", placeholder="Ej. a1b2c3d4")
                    nueva_pass = st.text_input("Nueva contraseña", type="password", placeholder="••••••••")
                    conf_pass = st.text_input("Confirmar contraseña", type="password", placeholder="••••••••")
                    if st.form_submit_button("Restablecer contraseña"):
                        usuario_r = st.session_state.reset_usuario or ""
                        usr = session.query(UsuarioSistema).filter(UsuarioSistema.usuario == usuario_r).first()
                        tok = session.query(TokenRestablecimiento).filter(
                            TokenRestablecimiento.usuario_id == usr.id,
                            TokenRestablecimiento.token == (codigo_rest or "").strip().lower(),
                            TokenRestablecimiento.expira_en > datetime.now()
                        ).first() if usr else None
                        if not usr:
                            st.error("Usuario no encontrado.")
                        elif not tok:
                            st.error("Código inválido o expirado.")
                        elif not nueva_pass or len(nueva_pass) < 4:
                            st.error("La contraseña debe tener al menos 4 caracteres.")
                        elif nueva_pass != conf_pass:
                            st.error("Las contraseñas no coinciden.")
                        else:
                            usr.password = _hash_password(nueva_pass)
                            session.delete(tok)
                            session.commit()
                            st.session_state.reset_codigo = None
                            st.session_state.reset_usuario = None
                            st.success("Contraseña actualizada. Inicia sesión con tu nueva contraseña.")
                            time.sleep(1.5)
                            st.rerun()
            else:
                with st.form("form_solicitar_codigo"):
                    usuario_sol = st.text_input("Usuario", placeholder="Nombre de usuario para restablecer")
                    if st.form_submit_button("Generar código"):
                        usr = session.query(UsuarioSistema).filter(UsuarioSistema.usuario == (usuario_sol or "").strip()).first() if usuario_sol else None
                        if not usr:
                            st.error("Usuario no encontrado.")
                        else:
                            for t in session.query(TokenRestablecimiento).filter(TokenRestablecimiento.usuario_id == usr.id).all():
                                session.delete(t)
                            codigo = _generar_token_restablecimiento()
                            session.add(TokenRestablecimiento(usuario_id=usr.id, token=codigo, expira_en=datetime.now() + timedelta(minutes=15)))
                            session.commit()
                            st.session_state.reset_codigo = codigo
                            st.session_state.reset_usuario = usr.usuario
                            # Intentar enviar por correo si SMTP está configurado y el usuario tiene email
                            correo_dest = None
                            if usr.personal_id:
                                pers = session.get(Personal, usr.personal_id)
                                if pers:
                                    correo_dest = (pers.correo_institucional or pers.correo_personal or "").strip()
                            if correo_dest:
                                ok, err = _enviar_email_restablecimiento(correo_dest, codigo)
                                if ok:
                                    st.success("Se envió el código a tu correo institucional. Revisa tu bandeja (y spam). Expira en 15 minutos.")
                                else:
                                    st.warning(f"No se pudo enviar por correo ({err}). Tu código: **{codigo}**")
                            else:
                                st.success(f"Código generado: **{codigo}**. Expira en 15 minutos.")
                            st.rerun()
    st.stop()

# --- 3. SIDEBAR: Usuario y Cerrar Sesión ---
with st.sidebar:
    st.markdown(f"**:material/person: {st.session_state.usuario_nombre}**")
    st.caption(f"Rol: {st.session_state.rol}")
    if st.button(":material/logout: Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.rol = None
        st.session_state.usuario_nombre = None
        st.session_state.personal_id = None
        st.session_state.usuario_id = None
        st.rerun()

# --- 4. usa_emojis_color (usado en tabs y otros) ---
usa_emojis_color = st.session_state.estilo_emojis == "Emojis de colores"

# --- Formulario de edición de expediente (desde Organigrama) ---
persona_editar_id = st.session_state.get("persona_editar_id")
if persona_editar_id:
    persona = session.query(Personal).get(persona_editar_id)
    if persona:
        nombre_completo = f"{persona.nombre or ''} {persona.apellido_paterno or ''}".strip() or "N/A"
        with st.expander(f":material/edit: Editar expediente: **{nombre_completo}**", expanded=True):
            todos_puestos_edit = session.query(Puesto).order_by(Puesto.id).all()
            edificios_edit = session.query(Edificio).order_by(Edificio.id).all()
            dominios_edit = session.query(DominioCorreo).order_by(DominioCorreo.dominio).all()
            puesto_id_to_obj_edit = {p.id: p for p in todos_puestos_edit}
            edificio_id_to_obj_edit = {e.id: e for e in edificios_edit}
            # Resolver edificio y planta actuales para prellenar
            edif_actual = None
            planta_actual = None
            area_id_actual = -1
            if persona.edificio and edificios_edit:
                edif_actual = next((e for e in edificios_edit if (e.letra or "").strip().upper() == (persona.edificio or "").strip().upper()), edificios_edit[0] if edificios_edit else None)
            if edif_actual and persona.planta:
                plantas_edif = session.query(Planta).filter_by(edificio_id=edif_actual.id).order_by(Planta.id).all()
                planta_actual = next((p for p in plantas_edif if (p.nombre_nivel or "").strip() == (persona.planta or "").strip()), plantas_edif[0] if plantas_edif else None)
                if planta_actual and persona.area_asignada and persona.area_asignada.strip() and persona.area_asignada.strip() != "Sin asignar":
                    areas_planta = session.query(Espacio).filter_by(planta_id=planta_actual.id).order_by(Espacio.id).all()
                    area_match = next((a for a in areas_planta if (a.nombre or "").strip() == persona.area_asignada.strip()), None)
                    if area_match:
                        area_id_actual = area_match.id
            if not edif_actual and edificios_edit:
                edif_actual = edificios_edit[0]
            if edif_actual and not planta_actual:
                plantas_edif = session.query(Planta).filter_by(edificio_id=edif_actual.id).order_by(Planta.id).all()
                planta_actual = plantas_edif[0] if plantas_edif else None

            # Puesto y Ubicación FUERA del form para que la cascada Edificio→Planta→Área funcione
            st.caption("Puedes cambiar el puesto (ej. de docente a administrativo) usando el selector de Puesto.")
            st.subheader(":material/business: Puesto y Ubicación")
            idx_puesto = 0
            if persona.puesto_id:
                ids_p = [p.id for p in todos_puestos_edit]
                if persona.puesto_id in ids_p:
                    idx_puesto = ids_p.index(persona.puesto_id)
            puesto_id_sel = st.selectbox("Puesto*", options=[p.id for p in todos_puestos_edit],
                format_func=lambda pid: f"{puesto_id_to_obj_edit[pid].nombre} ({puesto_id_to_obj_edit[pid].unidad.nombre})", index=idx_puesto, key="edit_p_reg")
            puesto_sel = puesto_id_to_obj_edit[puesto_id_sel]
            idx_edif = 0
            if edif_actual:
                ids_e = [e.id for e in edificios_edit]
                if edif_actual.id in ids_e:
                    idx_edif = ids_e.index(edif_actual.id)
            edif_id_sel = st.selectbox("Edificio*", options=[e.id for e in edificios_edit],
                format_func=lambda eid: f"Edificio {edificio_id_to_obj_edit[eid].letra} - {edificio_id_to_obj_edit[eid].nombre}", index=idx_edif, key="edit_reg_edif_p")
            edif_sel = edificio_id_to_obj_edit[edif_id_sel]
            plantas_del_edif = session.query(Planta).filter_by(edificio_id=edif_sel.id).order_by(Planta.id).all()
            planta_sel = None
            area_sel = None
            if plantas_del_edif:
                planta_id_to_obj = {p.id: p for p in plantas_del_edif}
                ids_planta = [p.id for p in plantas_del_edif]
                idx_planta = 0
                if planta_actual and planta_actual.id in ids_planta:
                    idx_planta = ids_planta.index(planta_actual.id)
                planta_id_sel = st.selectbox("Planta*", options=ids_planta,
                    format_func=lambda pid: planta_id_to_obj[pid].nombre_nivel, index=idx_planta, key="edit_reg_planta_p")
                planta_sel = planta_id_to_obj[planta_id_sel]
                areas_de_planta = session.query(Espacio).filter_by(planta_id=planta_sel.id).order_by(Espacio.id).all()
                area_opciones_ids = [-1] + [a.id for a in areas_de_planta]
                area_id_to_obj = {a.id: a for a in areas_de_planta}
                idx_area = 0
                if area_id_actual != -1 and area_id_actual in area_id_to_obj:
                    idx_area = area_opciones_ids.index(area_id_actual)
                area_id_sel = st.selectbox("Área Específica (Opcional)", options=area_opciones_ids,
                    format_func=lambda aid: "Sin asignar" if aid == -1 else area_id_to_obj[aid].nombre, index=idx_area, key="edit_reg_area_p")
                area_sel = None if area_id_sel == -1 else area_id_to_obj[area_id_sel]
            else:
                st.warning("Sin plantas en este edificio. Registra plantas en la pestaña Edificios.")
            st.markdown("---")

            with st.form("form_editar_expediente", clear_on_submit=False):
                st.caption("Puedes cambiar el puesto (ej. de docente a administrativo) usando el selector de Puesto.")
                c_foto, c_nombres = st.columns([1, 2])
                with c_foto:
                    foto_u = st.file_uploader("Fotografía (sube nueva para cambiar)", type=["jpg", "png"], key="edit_foto_p")
                    if persona.fotografia and os.path.exists(persona.fotografia):
                        st.image(persona.fotografia, caption="Actual", width=100)
                    elif foto_u:
                        st.image(foto_u, caption="Nueva", width=100)
                with c_nombres:
                    nombre = st.text_input("Nombre(s)*", value=persona.nombre or "", key="edit_nom_p")
                    ap_pat = st.text_input("Apellido Paterno*", value=persona.apellido_paterno or "", key="edit_app_p")
                    ap_mat = st.text_input("Apellido Materno", value=persona.apellido_materno or "", key="edit_apm_p")
                c1, c2, c3 = st.columns(3)
                fnac = persona.fecha_nacimiento or datetime(1990, 1, 1)
                f_nacimiento = c1.date_input("Fecha de Nacimiento", value=fnac, min_value=datetime(1950, 1, 1), format="DD/MM/YYYY", key="edit_fnac_p")
                genero = c2.selectbox("Género", ["Femenino", "Masculino"], index=1 if (persona.genero or "").lower() == "masculino" else 0, key="edit_gen_p")
                est_civil = c3.selectbox("Estado Civil", ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"], 
                    index=["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"].index(persona.estado_civil) if persona.estado_civil in ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"] else 0, key="edit_ec_p")
                c4, c5 = st.columns([2, 1])
                domicilio = c4.text_input("Domicilio Real", value=persona.domicilio or "", key="edit_dom_p")
                curp = st.text_input("CURP", value=persona.curp or "", key="edit_curp_p")
                curp_norm = (curp or "").strip().upper()
                val_curp = _validar_curp(curp_norm)
                if curp_norm:
                    if not val_curp["ok"]:
                        st.error("CURP inválida: " + " · ".join(val_curp["errores"]))
                    else:
                        datos = val_curp.get("datos", {})
                        fn_curp = datos.get("fecha_nacimiento")
                        sexo_curp = datos.get("sexo")
                        ent_curp = datos.get("entidad")
                        st.caption(f"CURP OK · Nac: {fn_curp.strftime('%d/%m/%Y')} · Sexo: {sexo_curp} · Entidad: {ent_curp}")
                        # Comparaciones opcionales
                        if isinstance(f_nacimiento, datetime):
                            fn_form = f_nacimiento.date()
                        else:
                            fn_form = f_nacimiento
                        if fn_form and fn_curp and fn_form != fn_curp:
                            st.warning(f"La fecha de nacimiento no coincide con CURP ({fn_curp.strftime('%d/%m/%Y')}).")
                        sexo_form = "M" if (genero or "").lower().startswith("fem") else "H"
                        if sexo_curp and sexo_form and sexo_curp != sexo_form:
                            st.warning(f"El género no coincide con CURP (CURP={sexo_curp}).")
                rfc = st.text_input("RFC", value=persona.rfc or "", key="edit_rfc_p")
                rfc_norm = (rfc or "").strip().upper()
                val_rfc = _validar_rfc(rfc_norm)
                if rfc_norm:
                    if not val_rfc["ok"]:
                        st.error("RFC inválido: " + " · ".join(val_rfc["errores"]))
                    else:
                        datos_r = val_rfc.get("datos", {})
                        f_rfc = datos_r.get("fecha")
                        t_rfc = datos_r.get("tipo")
                        st.caption(f"RFC OK · Tipo: {t_rfc} · Fecha: {f_rfc.strftime('%d/%m/%Y') if f_rfc else '—'}")
                        # Comparación opcional (solo física): fecha del RFC vs fecha de nacimiento
                        if t_rfc == "Física":
                            fn_form = f_nacimiento.date() if isinstance(f_nacimiento, datetime) else f_nacimiento
                            if fn_form and f_rfc and fn_form != f_rfc:
                                st.warning(f"La fecha de nacimiento no coincide con RFC ({f_rfc.strftime('%d/%m/%Y')}).")
                nss = st.text_input("NSS", value=persona.nss or "", key="edit_nss_p")
                nss_norm = (nss or "").strip().replace("-", "").replace(" ", "")
                val_nss = _validar_nss(nss_norm, fecha_nacimiento=f_nacimiento)
                if nss_norm:
                    if not val_nss["ok"]:
                        st.error("NSS inválido: " + " · ".join(val_nss["errores"]))
                    else:
                        st.caption("NSS OK")
                st.markdown("---")
                st.subheader(":material/phone: Contacto")
                c_con1, c_con2 = st.columns(2)
                cel_personal = c_con1.text_input("Celular Personal", value=persona.celular_personal or "", key="edit_cel_p")
                cel_norm = None
                val_cel = _validar_celular_mx(cel_personal)
                with c_con2:
                    correo_personal = st.text_input("Correo Electrónico Personal", value=persona.correo_personal or "", key="edit_corr_p")
                    correo_personal_norm = None
                    val_email = _validar_email(correo_personal)
                # Mensajes de validación en una segunda fila, alineados
                v_cel, v_mail = st.columns(2)
                with v_cel:
                    if (cel_personal or "").strip():
                        if not val_cel["ok"]:
                            st.error("Celular inválido: " + " · ".join(val_cel["errores"]))
                        else:
                            cel_norm = val_cel["datos"].get("cel_norm_10")
                            st.caption(f"Celular OK · {cel_norm}")
                with v_mail:
                    if (correo_personal or "").strip():
                        if not val_email["ok"]:
                            st.error("Correo personal inválido: " + " · ".join(val_email["errores"]))
                        else:
                            correo_personal_norm = val_email["datos"].get("email_norm")
                            st.caption(f"Correo personal OK · {correo_personal_norm}")
                c_con3, c_con4 = st.columns(2)
                tel_oficina = c_con3.text_input("Teléfono de Oficina", value=persona.telefono_oficina or "", key="edit_tel_o")
                ext_oficina = c_con4.text_input("Extensión", value=persona.extension or "", key="edit_ext_p")
                tel_of_norm = None
                ext_norm = None
                val_tel_of = _validar_telefono_mx(tel_oficina)
                val_ext = _validar_extension(ext_oficina)
                v_tel, v_ext = st.columns(2)
                with v_tel:
                    if (tel_oficina or "").strip():
                        if not val_tel_of["ok"]:
                            st.error("Teléfono de oficina inválido: " + " · ".join(val_tel_of["errores"]))
                        else:
                            tel_of_norm = val_tel_of["datos"].get("tel_norm_10")
                            st.caption(f"Teléfono OK · {tel_of_norm}")
                with v_ext:
                    if (ext_oficina or "").strip():
                        if not val_ext["ok"]:
                            st.error("Extensión inválida: " + " · ".join(val_ext["errores"]))
                        else:
                            ext_norm = val_ext["datos"].get("ext_norm")
                            st.caption(f"Extensión OK · {ext_norm}")
                if dominios_edit:
                    parte_local = ""
                    dominio_id_sel_default = dominios_edit[0].id
                    if persona.correo_institucional and "@" in persona.correo_institucional:
                        parte_local = persona.correo_institucional.split("@", 1)[0].strip()
                        dominio_str = persona.correo_institucional.split("@", 1)[-1].strip()
                        dom_match = next((d for d in dominios_edit if (d.dominio or "").strip() == dominio_str), None)
                        if dom_match:
                            dominio_id_sel_default = dom_match.id
                    c_corr1, c_corr2 = st.columns([1, 1])
                    parte_local_in = c_corr1.text_input("Correo Institucional* (parte antes de @)", value=parte_local, key="edit_corri_parte")
                    dominio_id_sel = c_corr2.selectbox("Dominio", options=[d.id for d in dominios_edit], 
                        format_func=lambda did: next((f"@{d.dominio}" for d in dominios_edit if d.id == did), ""), index=[d.id for d in dominios_edit].index(dominio_id_sel_default) if dominio_id_sel_default in [d.id for d in dominios_edit] else 0, key="edit_corri_dom")
                    dominio_sel = next((d for d in dominios_edit if d.id == dominio_id_sel), None)
                    correo_institucional = (f"{parte_local_in.strip()}@{dominio_sel.dominio}" if parte_local_in and dominio_sel else "") or ""
                else:
                    correo_institucional = st.text_input("Correo Institucional*", value=persona.correo_institucional or "", key="edit_corri_p")
                st.markdown("---")
                st.subheader(":material/school: Bloque 4: Perfil Académico")
                lista_titulos = ["Ing.", "Mtro.", "Mtra.", "Lic.", "Lcda.", "Dr.", "Dra.", "Arq.", "C.P."]
                idx_titulo = 0
                if persona.titulo_abreviatura and persona.titulo_abreviatura in lista_titulos:
                    idx_titulo = lista_titulos.index(persona.titulo_abreviatura)
                st.markdown("**Título profesional**")
                titulo_abrev = st.selectbox("Abreviatura con la que se firma (ej. Ing., Dr., Mtro.)", lista_titulos, index=idx_titulo, key="edit_reg_tabr_p", label_visibility="collapsed")
                st.markdown("---")
                st.markdown("**Licenciatura o Ingeniería** *(opcional)*")
                licenciatura = st.text_input("Nombre completo del programa", value=persona.licenciatura or "", placeholder="Ej. Ingeniería en Industrias Alimentarias", key="edit_reg_lic_p", label_visibility="collapsed")
                mencio_lic = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Licenciatura", value=bool(getattr(persona, "licenciatura_mencion_honorifica", False)), key="edit_mencio_lic")
                st.markdown("**Maestría** *(opcional)*")
                maestria = st.text_input("Nombre del programa de Maestría", value=persona.maestria or "", placeholder="Ej. Ciencias en Producción Pecuaria Tropical", key="edit_reg_maest_p", label_visibility="collapsed")
                mencio_maes = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Maestría", value=bool(getattr(persona, "maestria_mencion_honorifica", False)), key="edit_mencio_maes")
                st.markdown("**Doctorado** *(opcional)*")
                doctorado = st.text_input("Nombre del programa de Doctorado", value=persona.doctorado or "", placeholder="Ej. Ciencias en Agricultura Tropical Sustentable", key="edit_reg_doct_p", label_visibility="collapsed")
                mencio_doct = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Doctorado", value=bool(getattr(persona, "doctorado_mencion_honorifica", False)), key="edit_mencio_doct")
                submit_edit = st.form_submit_button(":material/save: ACTUALIZAR EXPEDIENTE", use_container_width=True)
                if submit_edit:
                    faltantes = []
                    if not nombre: faltantes.append("Nombre")
                    if not ap_pat: faltantes.append("Apellido Paterno")
                    if not correo_institucional: faltantes.append("Correo Institucional")
                    if not planta_sel: faltantes.append("Ubicación (Planta)")
                    if curp_norm and not val_curp["ok"]:
                        faltantes.append("CURP válida")
                    if rfc_norm and not val_rfc["ok"]:
                        faltantes.append("RFC válido")
                    if nss_norm and not val_nss["ok"]:
                        faltantes.append("NSS válido")
                    if (cel_personal or "").strip() and not val_cel["ok"]:
                        faltantes.append("Celular Personal válido")
                    if (correo_personal or "").strip() and not val_email["ok"]:
                        faltantes.append("Correo Personal válido")
                    if (tel_oficina or "").strip() and not val_tel_of["ok"]:
                        faltantes.append("Teléfono de Oficina válido")
                    if (ext_oficina or "").strip() and not val_ext["ok"]:
                        faltantes.append("Extensión válida")
                    if faltantes:
                        st.error(f"Faltan: {', '.join(faltantes)}")
                    else:
                        try:
                            ruta_foto = persona.fotografia
                            if foto_u:
                                ruta_foto = os.path.join("fotos_personal", f"p_{int(time.time()*1000)}.jpg")
                                foto_bytes = _procesar_foto_infantil(foto_u, max_bytes=2 * 1024 * 1024)
                                with open(ruta_foto, "wb") as f:
                                    f.write(foto_bytes)
                            persona.fotografia = ruta_foto
                            persona.nombre = nombre
                            persona.apellido_paterno = ap_pat
                            persona.apellido_materno = ap_mat
                            persona.fecha_nacimiento = f_nacimiento
                            persona.genero = genero
                            persona.estado_civil = est_civil
                            persona.domicilio = domicilio
                            persona.curp = curp_norm or None
                            persona.rfc = rfc_norm or None
                            persona.nss = nss_norm or None
                            persona.celular_personal = (cel_norm or "").strip() or None
                            persona.correo_personal = (correo_personal_norm or "").strip() or None
                            persona.telefono_oficina = (tel_of_norm or "").strip() or None
                            persona.extension = (ext_norm or "").strip() or None
                            persona.correo_institucional = correo_institucional
                            persona.puesto_id = puesto_sel.id
                            persona.edificio = edif_sel.letra
                            persona.planta = planta_sel.nombre_nivel
                            persona.area_asignada = area_sel.nombre if area_sel else "Sin asignar"
                            persona.titulo_abreviatura = titulo_abrev
                            persona.licenciatura = licenciatura
                            persona.maestria = maestria
                            persona.doctorado = doctorado
                            persona.licenciatura_mencion_honorifica = mencio_lic
                            persona.maestria_mencion_honorifica = mencio_maes
                            persona.doctorado_mencion_honorifica = mencio_doct
                            session.commit()
                            del st.session_state["persona_editar_id"]
                            st.success(f"Expediente de {nombre} {ap_pat} actualizado correctamente.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al actualizar: {ex}")
                            session.rollback()
            if st.button(":material/close: Cancelar edición (cerrar sin guardar)", key="edit_cancel_btn"):
                del st.session_state["persona_editar_id"]
                st.rerun()
    else:
        del st.session_state["persona_editar_id"]

# --- 5. MENÚ SUPERIOR (RBAC: pestañas según rol) ---
if usa_emojis_color:
    TABS_SUPER_ADMIN = [
        ":material/home: Inicio",
        ":material/analytics: Estadísticas",
        ":material/account_tree: Organigrama y Directorio",
        ":material/group: Personal",
        ":material/description: CV",
        ":material/auto_stories: Producción Académica",
        ":material/construction: Capacitación",
        ":material/badge: Identidad",
        ":material/inbox: Buzón Aprobaciones",
        ":material/settings: Configuración",
        ":material/history_edu: Bitácora",
    ]
    TABS_RRHH = [
        ":material/home: Inicio",
        ":material/analytics: Estadísticas",
        ":material/account_tree: Organigrama y Directorio",
        ":material/group: Personal",
        ":material/description: CV",
        ":material/construction: Capacitación",
        ":material/badge: Identidad",
        ":material/inbox: Buzón Aprobaciones",
    ]
    TABS_DESARROLLO_ACADEMICO = [
        ":material/home: Inicio",
        ":material/analytics: Estadísticas",
        ":material/account_tree: Organigrama y Directorio",
        ":material/description: CV",
        ":material/badge: Identidad",
        ":material/auto_stories: Producción Académica",
    ]
    TABS_EMPLEADO = [
        ":material/person: Mi Perfil",
        ":material/description: CV",
    ]
else:
    TABS_SUPER_ADMIN = [
        "Inicio",
        "Estadísticas",
        "Organigrama y Directorio",
        "Personal",
        "CV",
        "Producción Académica",
        "Capacitación",
        "Identidad",
        "Buzón Aprobaciones",
        "Configuración",
        "Bitácora",
    ]
    TABS_RRHH = [
        "Inicio",
        "Estadísticas",
        "Organigrama y Directorio",
        "Personal",
        "CV",
        "Capacitación",
        "Identidad",
        "Buzón Aprobaciones",
    ]
    TABS_DESARROLLO_ACADEMICO = [
        "Inicio",
        "Estadísticas",
        "Organigrama y Directorio",
        "CV",
        "Identidad",
        "Producción Académica",
    ]
    TABS_EMPLEADO = [
        "Mi Perfil",
        "CV",
    ]

rol_actual = st.session_state.rol or "Empleado"
if rol_actual == "Súper Admin":
    tabs_lista = TABS_SUPER_ADMIN
elif rol_actual == "RRHH":
    tabs_lista = TABS_RRHH
elif rol_actual == "Desarrollo Académico":
    tabs_lista = TABS_DESARROLLO_ACADEMICO
else:
    tabs_lista = TABS_EMPLEADO

# Navegación principal en menú lateral (radio) en lugar de pestañas superiores
with st.sidebar:
    st.markdown("### Navegación")
    selected_tab = st.radio("Ir a sección:", tabs_lista, index=0, key="nav_principal")

# Solo creamos contenedor para la pestaña seleccionada
tab_dict = {selected_tab: st.container()}

# ==========================================
# PESTAÑA 1: INICIO (ORGANIGRAMA)
# ==========================================
if (":material/home: Inicio" in tab_dict) or ("Inicio" in tab_dict):
    with tab_dict.get(":material/home: Inicio", tab_dict.get("Inicio")):
        session.expire_all()
        st.header("Organigrama Institucional Interactivo")
        st.write("Visualiza Unidades (:material/folder:), Puestos (:material/work:) y Personal (:material/person:). Edita o elimina directamente aquí.")
        st.divider()
        
        todas_unidades = session.query(Unidad).all()
        todos_puestos = session.query(Puesto).all()
        todo_personal = session.query(Personal).all()
        
        if todas_unidades:
            renderizar_organigrama(todas_unidades, todos_puestos, todo_personal, parent_id=None)
        else:
            st.info("Aún no hay unidades registradas. Ve a la pestaña 'Unidades y Puestos' para comenzar.")

# ==========================================
# PESTAÑA: ESTADÍSTICAS DEL PERSONAL
# ==========================================
if (":material/analytics: Estadísticas" in tab_dict) or ("Estadísticas" in tab_dict):
    with tab_dict.get(":material/analytics: Estadísticas", tab_dict.get("Estadísticas")):
        session.expire_all()
        st.header(":material/analytics: Estadísticas del Personal")
        st.caption("Métricas y gráficos basados en los datos registrados en el sistema.")

        # --- Cargar datos ---
        todo_personal = session.query(Personal).all()
        todos_puestos = session.query(Puesto).all()
        todas_unidades = session.query(Unidad).all()
        todos_cursos = session.query(CursoCapacitacion).all()
        todas_producciones = session.query(ProduccionAcademica).all()
        puesto_id_to_puesto = {p.id: p for p in todos_puestos}
        unidad_id_to_unidad = {u.id: u for u in todas_unidades}

        # --- DataFrames para gráficos ---
        rows_pers = []
        for p in todo_personal:
            puesto_obj = puesto_id_to_puesto.get(p.puesto_id) if p.puesto_id else None
            unidad_obj = unidad_id_to_unidad.get(puesto_obj.unidad_id) if puesto_obj and puesto_obj.unidad_id else None
            rows_pers.append({
                "id": p.id, "nombre": p.nombre, "apellido_paterno": p.apellido_paterno,
                "genero": p.genero or "Sin especificar", "edificio": p.edificio or "Sin asignar",
                "fecha_ingreso": p.fecha_ingreso, "tipo_contrato": p.tipo_contrato or "Sin especificar",
                "jornada_laboral": p.jornada_laboral or "Sin especificar",
                "puesto_nombre": puesto_obj.nombre if puesto_obj else "Sin puesto",
                "unidad_nombre": unidad_obj.nombre if unidad_obj else "Sin unidad",
            })
        df_personal = pd.DataFrame(rows_pers)

        rows_cur = [{"id": c.id, "personal_id": c.personal_id, "nombre_curso": c.nombre_curso, "institucion": c.institucion or "N/A", "horas": c.horas, "fecha_termino": c.fecha_termino} for c in todos_cursos]
        df_cursos = pd.DataFrame(rows_cur)

        rows_prod = [{"id": pr.id, "personal_id": pr.personal_id, "tipo": pr.tipo or "N/A", "fecha": pr.fecha} for pr in todas_producciones]
        df_producciones = pd.DataFrame(rows_prod)

        # --- st.metric: Números destacados ---
        total_personal = len(todo_personal)
        total_unidades = len(todas_unidades)
        total_puestos = len(todos_puestos)
        personal_con_cursos = len(set(df_cursos["personal_id"].tolist())) if not df_cursos.empty else 0
        personal_con_produccion = len(set(df_producciones["personal_id"].tolist())) if not df_producciones.empty else 0
        total_cursos = len(todos_cursos)
        total_publicaciones = len(todas_producciones)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Personal", total_personal, help="Personas registradas en el sistema")
        m2.metric("Total de Cursos", total_cursos, help="Cursos de capacitación registrados")
        m3.metric("Con Capacitación", personal_con_cursos, help="Personal con al menos un curso")
        m4.metric("Con Producción Académica", personal_con_produccion, help="Personal con al menos una publicación")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Unidades", total_unidades, help="Unidades orgánicas")
        m6.metric("Puestos", total_puestos, help="Puestos de trabajo")
        m7.metric("Total Publicaciones", total_publicaciones, help="Libros, artículos, capítulos")
        m8.metric("Edificios", len(set(df_personal["edificio"].dropna().replace("", "Sin asignar"))), help="Personal distribuido por edificio")

        st.divider()

        # --- Cumpleaños en la semana ---
        st.subheader(":material/cake: Cumpleaños de la semana")
        hoy = datetime.now().date()
        dias_semana = [((hoy + timedelta(days=d)).month, (hoy + timedelta(days=d)).day) for d in range(7)]
        cumple_semana = []
        for p in todo_personal:
            if p.fecha_nacimiento is None:
                continue
            if (p.fecha_nacimiento.month, p.fecha_nacimiento.day) in dias_semana:
                nombre_full = f"{p.nombre or ''} {p.apellido_paterno or ''}".strip() or "Sin nombre"
                puesto_nom = puesto_id_to_puesto.get(p.puesto_id).nombre if p.puesto_id and puesto_id_to_puesto.get(p.puesto_id) else ""
                fnac = p.fecha_nacimiento

                # Próximo cumpleaños (para calcular la edad que cumple)
                try:
                    cumple_este_anio = fnac.replace(year=hoy.year)
                except ValueError:
                    # Caso 29-Feb: en años no bisiestos, usamos 28-Feb
                    cumple_este_anio = fnac.replace(year=hoy.year, day=28)
                prox_cumple = cumple_este_anio if cumple_este_anio >= hoy else cumple_este_anio.replace(year=hoy.year + 1)
                edad_cumple = prox_cumple.year - fnac.year

                cumple_semana.append((p, nombre_full, puesto_nom, fnac, prox_cumple, edad_cumple))
        _meses_es = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
        cumple_semana.sort(key=lambda x: (x[4].month, x[4].day))
        if cumple_semana:
            cols_cumple = st.columns(min(len(cumple_semana), 4))
            for i, (p, nombre_full, puesto_nom, fnac, prox_cumple, edad_cumple) in enumerate(cumple_semana):
                with cols_cumple[i % len(cols_cumple)]:
                    with st.container(border=True):
                        st.markdown(f"**:material/cake: {nombre_full}**")
                        st.caption(f"{puesto_nom or 'Sin puesto'}")
                        mes_nom = _meses_es[prox_cumple.month - 1] if 1 <= prox_cumple.month <= 12 else ""
                        st.caption(f"Cumple: {prox_cumple.day} de {mes_nom} · **{edad_cumple} años**")
        else:
            st.info("Nadie cumple años en los próximos 7 días.")

        st.divider()

        # --- Top 3 docentes destacados y Top 3 empleados destacados ---
        st.subheader(":material/emoji_events: Destacados")
        prod_por_persona = df_producciones.groupby("personal_id").size() if not df_producciones.empty else pd.Series(dtype=int)
        cur_por_persona = df_cursos.groupby("personal_id").size() if not df_cursos.empty else pd.Series(dtype=int)
        docentes_con_puntaje = []
        empleados_con_puntaje = []

        def _fmt_antiguedad(fecha_ingreso, ref_date):
            if not fecha_ingreso:
                return "Antigüedad: N/D"
            fi = fecha_ingreso
            if isinstance(fi, datetime):
                fi = fi.date()
            # Meses completos transcurridos
            meses = (ref_date.year - fi.year) * 12 + (ref_date.month - fi.month)
            if ref_date.day < fi.day:
                meses -= 1
            if meses < 0:
                meses = 0
            if meses == 0:
                return "Antigüedad: < 1 mes"
            anios = meses // 12
            rem = meses % 12
            partes = []
            if anios:
                partes.append(f"{anios} año" + ("s" if anios != 1 else ""))
            if rem:
                partes.append(f"{rem} mes" + ("es" if rem != 1 else ""))
            return "Antigüedad: " + " ".join(partes)

        hoy_stats = datetime.now().date()
        for p in todo_personal:
            puesto_nom = puesto_id_to_puesto.get(p.puesto_id).nombre if p.puesto_id and puesto_id_to_puesto.get(p.puesto_id) else ""
            num_prod = int(prod_por_persona.get(p.id, 0))
            num_cur = int(cur_por_persona.get(p.id, 0))
            nombre_full = f"{p.nombre or ''} {p.apellido_paterno or ''}".strip() or "Sin nombre"
            antig = _fmt_antiguedad(getattr(p, "fecha_ingreso", None), hoy_stats)
            if _es_docente(puesto_nom):
                docentes_con_puntaje.append((p, nombre_full, puesto_nom, num_prod, num_cur, num_prod * 2 + num_cur, antig))
            else:
                empleados_con_puntaje.append((p, nombre_full, puesto_nom, num_cur, antig))
        docentes_con_puntaje.sort(key=lambda x: x[5], reverse=True)
        empleados_con_puntaje.sort(key=lambda x: x[3], reverse=True)
        top10_doc = docentes_con_puntaje[:10]
        top10_emp = empleados_con_puntaje[:10]

        col_doc, col_emp = st.columns(2)
        with col_doc:
            st.markdown("**Top 10 docentes destacados** _(por producción académica y capacitación)_")
            if top10_doc:
                for i, (p, nombre_full, puesto_nom, num_prod, num_cur, _, antig) in enumerate(top10_doc, 1):
                    with st.container(border=True):
                        st.markdown(f"**{i}. {nombre_full}**")
                        st.caption(f"{puesto_nom or 'Sin puesto'}")
                        st.caption(f":material/menu_book: {num_prod} publicación(es) · :material/construction: {num_cur} curso(s)")
                        st.caption(f":material/timer: {antig}")
            else:
                st.info("No hay docentes con producción o cursos registrados.")
        with col_emp:
            st.markdown("**Top 10 empleados destacados** _(por capacitación)_")
            if top10_emp:
                for i, (p, nombre_full, puesto_nom, num_cur, antig) in enumerate(top10_emp, 1):
                    with st.container(border=True):
                        st.markdown(f"**{i}. {nombre_full}**")
                        st.caption(f"{puesto_nom or 'Sin puesto'}")
                        st.caption(f":material/construction: {num_cur} curso(s) de capacitación")
                        st.caption(f":material/timer: {antig}")
            else:
                st.info("No hay empleados no docentes con cursos registrados.")

        st.divider()

        # --- st.bar_chart ---
        if not df_personal.empty:
            st.subheader(":material/bar_chart: Personal por categoría")
            bc1, bc2 = st.columns(2)
            with bc1:
                por_puesto = df_personal["puesto_nombre"].value_counts().head(15)
                if not por_puesto.empty:
                    df_bar = pd.DataFrame({"Cantidad": por_puesto})
                    st.bar_chart(df_bar, use_container_width=True)
                st.caption("Personal por Puesto (Top 15)")
            with bc2:
                por_unidad = df_personal["unidad_nombre"].value_counts().head(15)
                if not por_unidad.empty:
                    df_bar_u = pd.DataFrame({"Cantidad": por_unidad})
                    st.bar_chart(df_bar_u, use_container_width=True)
                st.caption("Personal por Unidad (Top 15)")

            bc3, bc4 = st.columns(2)
            with bc3:
                por_genero = df_personal["genero"].value_counts()
                if not por_genero.empty:
                    try:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(5, 4))
                        ax.pie(por_genero.values, labels=por_genero.index, autopct="%1.1f%%", startangle=90)
                        ax.axis("equal")
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                    except Exception:
                        df_bar_g = pd.DataFrame({"Cantidad": por_genero})
                        st.bar_chart(df_bar_g, use_container_width=True)
                st.caption("Personal por Género")
            with bc4:
                por_edificio = df_personal["edificio"].value_counts()
                if not por_edificio.empty:
                    df_bar_e = pd.DataFrame({"Cantidad": por_edificio})
                    st.bar_chart(df_bar_e, use_container_width=True)
                st.caption("Personal por Edificio")

        # Producción por tipo y Cursos por institución
        if not df_producciones.empty:
            st.subheader(":material/auto_stories: Producción Académica")
            por_tipo = df_producciones["tipo"].value_counts()
            df_bar_prod = pd.DataFrame({"Cantidad": por_tipo})
            st.bar_chart(df_bar_prod, use_container_width=True)
            st.caption("Publicaciones por tipo (Libro, Capítulo, Artículo)")

        if not df_cursos.empty:
            st.subheader(":material/construction: Cursos de Capacitación")
            por_inst = df_cursos["institucion"].value_counts().head(10)
            df_bar_cur = pd.DataFrame({"Cantidad": por_inst})
            st.bar_chart(df_bar_cur, use_container_width=True)
            st.caption("Cursos por institución (Top 10)")

        # --- st.line_chart: Series temporales ---
        st.subheader(":material/show_chart: Evolución temporal")

        lc1, lc2 = st.columns(2)
        with lc1:
            if not df_personal.empty and df_personal["fecha_ingreso"].notna().any():
                df_ing = df_personal.dropna(subset=["fecha_ingreso"]).copy()
                df_ing["periodo"] = pd.to_datetime(df_ing["fecha_ingreso"]).dt.to_period("M").astype(str)
                ing_por_mes = df_ing["periodo"].value_counts().sort_index()
                df_line_ing = pd.DataFrame({"Ingresos": ing_por_mes})
                st.line_chart(df_line_ing, use_container_width=True)
                st.caption("Ingresos de personal por mes")
            else:
                st.info("No hay fechas de ingreso para mostrar.")

        with lc2:
            if not df_cursos.empty and df_cursos["fecha_termino"].notna().any():
                df_cur = df_cursos.dropna(subset=["fecha_termino"]).copy()
                df_cur["periodo"] = pd.to_datetime(df_cur["fecha_termino"]).dt.to_period("M").astype(str)
                cur_por_mes = df_cur["periodo"].value_counts().sort_index()
                df_line_cur = pd.DataFrame({"Cursos finalizados": cur_por_mes})
                st.line_chart(df_line_cur, use_container_width=True)
                st.caption("Cursos finalizados por mes")
            else:
                st.info("No hay fechas de finalización de cursos.")

        if not df_producciones.empty and df_producciones["fecha"].notna().any():
            df_pr = df_producciones.dropna(subset=["fecha"]).copy()
            df_pr["anio"] = pd.to_datetime(df_pr["fecha"]).dt.year.astype(str)
            prod_por_anio = df_pr["anio"].value_counts().sort_index()
            df_line_prod = pd.DataFrame({"Publicaciones": prod_por_anio})
            st.line_chart(df_line_prod, use_container_width=True)
            st.caption("Producción académica por año")

# ==========================================
# PESTAÑA: ORGANIGRAMA Y DIRECTORIO (Visual e interactivo)
# ==========================================
if (":material/account_tree: Organigrama y Directorio" in tab_dict) or ("Organigrama y Directorio" in tab_dict):
    with tab_dict.get(":material/account_tree: Organigrama y Directorio", tab_dict.get("Organigrama y Directorio")):
        session.expire_all()
        todas_unidades = session.query(Unidad).all()
        todos_puestos = session.query(Puesto).all()
        todo_personal = session.query(Personal).all()
        puesto_id_to_puesto = {p.id: p for p in todos_puestos}
        unidad_id_to_unidad = {u.id: u for u in todas_unidades}

        # 1. Buscador y Filtro Rápido
        busqueda = st.text_input(
            ":material/search: Buscar",
            placeholder="Buscar por nombre, puesto o departamento...",
            key="org_busqueda"
        )

        if busqueda and busqueda.strip():
            # Búsqueda activa: ocultar organigrama, mostrar tarjetas con coincidencias
            q = busqueda.strip().upper()
            coincidencias = []
            for p in todo_personal:
                nombre_full = _nombre_completo_personal(p).upper()
                puesto_obj = puesto_id_to_puesto.get(p.puesto_id) if p.puesto_id else None
                puesto_nom = (puesto_obj.nombre or "") if puesto_obj else ""
                unidad = unidad_id_to_unidad.get(puesto_obj.unidad_id) if puesto_obj and puesto_obj.unidad_id else None
                depto = (unidad.nombre or "").upper() if unidad else ""
                if q in nombre_full or q in puesto_nom.upper() or q in depto:
                    coincidencias.append((p, puesto_nom, unidad))

            if coincidencias:
                st.markdown(f"**{len(coincidencias)} coincidencia(s) encontrada(s)**")
                for p, puesto_nom, unidad in coincidencias:
                    if _es_docente(puesto_nom):
                        _render_docente_expediente(p, session, puesto_id_to_puesto)
                    else:
                        _render_persona_tarjeta(p, puesto_id_to_puesto, show_foto=True, session_db=session)
            else:
                st.info("No se encontraron coincidencias. Intenta con otros términos.")
        else:
            # Sin búsqueda: mostrar organigrama dinámico
            if todas_unidades:
                renderizar_organigrama_visual(session, todas_unidades, todos_puestos, todo_personal)
            else:
                st.info("Aún no hay unidades registradas. Ve a la pestaña 'Unidades y Puestos' para comenzar.")

# ==========================================
# PESTAÑA 2: UNIDADES Y PUESTOS
# ==========================================
# ==========================================
# SECCIÓN: UNIDADES Y PUESTOS (usada dentro de Identidad)
# ==========================================
def render_unidades_y_puestos():
    session.expire_all()
    todas_unidades = session.query(Unidad).all()
    
    # Subpestañas internas similares a la sección de Edificios
    sub_unidades, sub_puestos = st.tabs([
        ":material/business: 1. Unidades Orgánicas",
        ":material/work: 2. Puestos de Trabajo"
    ])
    
    # --- SUBPestaña 1: Unidades Orgánicas ---
    with sub_unidades:
        st.header("Crear Nueva Unidad Orgánica")
    
        with st.expander(":material/upload_file: Cargar Unidades desde Excel", expanded=False):
            st.caption("Descarga la plantilla, llénala y súbela en formato .xlsx (hoja **Unidades**).")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.download_button(
                    ":material/download: Descargar plantilla",
                    data=_generar_plantilla_excel_unidades(),
                    file_name="plantilla_unidades_organicas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_plantilla_unidades"
                )
            with c2:
                unidades_xlsx = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx"], key="upload_unidades_xlsx")
            procesar_unidades = st.button("Procesar y cargar Unidades", type="primary", key="btn_procesar_unidades_xlsx") if unidades_xlsx else False
    
            if unidades_xlsx and procesar_unidades:
                try:
                    xl_u = pd.ExcelFile(unidades_xlsx, engine="openpyxl")
                    hojas_u = [s.strip() for s in xl_u.sheet_names]
                    hoja_u = next((h for h in hojas_u if h.lower() in ("unidades", "unidad")), hojas_u[0] if hojas_u else None)
                    if not hoja_u:
                        st.error("No se encontró la hoja 'Unidades'.")
                        st.stop()
    
                    df_u = xl_u.parse(hoja_u).dropna(how="all")
                    col_map = {str(c).strip().lower(): c for c in df_u.columns if isinstance(c, str)}
                    c_nombre = col_map.get("nombre")
                    c_tipo = col_map.get("tipo_nivel") or col_map.get("tipo") or col_map.get("nivel")
                    c_padre = col_map.get("depende_de") or col_map.get("depende de") or col_map.get("padre") or col_map.get("unidad_padre")
    
                    if not c_nombre or not c_tipo:
                        st.error("Faltan columnas obligatorias. Se requieren: **Nombre** y **Tipo_Nivel**.")
                        st.stop()
    
                    def _norm_txt(x):
                        if x is None or (isinstance(x, float) and pd.isna(x)):
                            return ""
                        return str(x).strip()
    
                    def _norm_lower(x):
                        return _norm_txt(x).lower()
    
                    def _tipo_canon(tipo_raw):
                        t = _norm_lower(tipo_raw)
                        if "dirección general" in t or "direccion general" in t:
                            return "Dirección General"
                        if "subdirección" in t or "subdireccion" in t:
                            return "Subdirección"
                        if "jefatura" in t:
                            return "Jefatura de Departamento"
                        return ""
    
                    # Cache de unidades existentes (por tipo y nombre) para resolver padres rápidamente
                    session.expire_all()
                    existentes = session.query(Unidad).all()
                    by_tipo_nombre = {}
                    for u in existentes:
                        key = (_tipo_canon(u.tipo_nivel), (u.nombre or "").strip().lower())
                        if key not in by_tipo_nombre:
                            by_tipo_nombre[key] = []
                        by_tipo_nombre[key].append(u)
    
                    def _unidad_existe(nombre, tipo, parent_id):
                        q = session.query(Unidad).filter(
                            Unidad.nombre == nombre,
                            Unidad.tipo_nivel == tipo
                        )
                        if parent_id is None:
                            q = q.filter(Unidad.parent_id.is_(None))
                        else:
                            q = q.filter(Unidad.parent_id == parent_id)
                        return session.query(q.exists()).scalar()
    
                    # Orden por jerarquía para poder crear en cascada
                    orden = {"Dirección General": 0, "Subdirección": 1, "Jefatura de Departamento": 2}
                    filas = []
                    for _, r in df_u.iterrows():
                        nombre = _norm_txt(r.get(c_nombre))
                        tipo = _tipo_canon(r.get(c_tipo))
                        padre = _norm_txt(r.get(c_padre)) if c_padre else ""
                        if not nombre or not tipo:
                            continue
                        filas.append({"nombre": nombre, "tipo": tipo, "padre": padre})
                    filas.sort(key=lambda x: (orden.get(x["tipo"], 99), x["nombre"].lower()))
    
                    creadas = 0
                    omitidas = 0
                    errores = 0
    
                    for f in filas:
                        nombre = f["nombre"]
                        tipo = f["tipo"]
                        padre_txt = f["padre"]
    
                        parent_id = None
                        if tipo == "Dirección General":
                            parent_id = None
                        elif tipo == "Subdirección":
                            if not padre_txt:
                                st.warning(f"Subdirección '{nombre}': falta Depende_De (Dirección General). Se omitió.")
                                omitidas += 1
                                continue
                            parent_candidates = by_tipo_nombre.get(("Dirección General", padre_txt.strip().lower()), [])
                            if not parent_candidates:
                                st.warning(f"Subdirección '{nombre}': no se encontró Dirección General '{padre_txt}'. Se omitió.")
                                omitidas += 1
                                continue
                            parent_id = parent_candidates[0].id
                        else:  # Jefatura
                            if not padre_txt:
                                st.warning(f"Jefatura '{nombre}': falta Depende_De (Subdirección). Se omitió.")
                                omitidas += 1
                                continue
                            parent_candidates = by_tipo_nombre.get(("Subdirección", padre_txt.strip().lower()), [])
                            if not parent_candidates:
                                st.warning(f"Jefatura '{nombre}': no se encontró Subdirección '{padre_txt}'. Se omitió.")
                                omitidas += 1
                                continue
                            parent_id = parent_candidates[0].id
    
                        if _unidad_existe(nombre, tipo, parent_id):
                            omitidas += 1
                            continue
    
                        try:
                            u_new = Unidad(nombre=nombre, tipo_nivel=tipo, parent_id=parent_id)
                            session.add(u_new)
                            session.flush()
                            key = (tipo, nombre.strip().lower())
                            if key not in by_tipo_nombre:
                                by_tipo_nombre[key] = []
                            by_tipo_nombre[key].append(u_new)
                            creadas += 1
                        except Exception:
                            session.rollback()
                            errores += 1
    
                    session.commit()
                    st.success(f"Carga completada: **{creadas}** creadas, **{omitidas}** omitidas (duplicadas o inválidas), **{errores}** con error.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error al procesar el archivo: {ex}")
    
        # Widgets normales (sin formulario) para que el cambio de nivel actualice al instante el combo de dependencia
        # Usamos un contador en session_state para forzar el reseteo de los campos tras guardar
        if '_unidad_form_reset_cnt' not in st.session_state:
            st.session_state['_unidad_form_reset_cnt'] = 0
        _cnt_unidad = st.session_state['_unidad_form_reset_cnt']
        _k_unidad = lambda base: f"{base}_{_cnt_unidad}"
    
        nombre_u = st.text_input("Nombre de la Unidad", key=_k_unidad("nombre_unidad"))
        tipo_u = st.selectbox("Nivel Jerárquico", ["Dirección General", "Subdirección", "Jefatura de Departamento"], key=_k_unidad("nivel_jerarquico"))
    
        # Filtrar las unidades disponibles como padre según el nivel jerárquico elegido
        # Normalizamos posibles variaciones en texto (espacios, mayúsculas, etc.)
        direcciones = []
        subdirecciones = []
        for u in todas_unidades:
            nivel_u = (u.tipo_nivel or "").strip().lower()
            if nivel_u == "dirección general" or nivel_u == "direccion general":
                direcciones.append(u)
            elif nivel_u == "subdirección" or nivel_u == "subdireccion":
                subdirecciones.append(u)
    
        padre_id_sel = None
        if tipo_u == "Dirección General":
            # Siempre es principal, no necesita seleccionar padre
            st.selectbox(
                "Depende de...",
                options=["-- Es una Dirección Principal --"],
                key="sb_padre_unidad_dg"
            )
        elif tipo_u == "Subdirección":
            # Solo puede depender de Direcciones Generales
            if not direcciones:
                st.info("Primero registra una Dirección General.")
            else:
                padre_id_sel = st.selectbox(
                    "Depende de (Dirección General)*",
                    options=[u.id for u in direcciones],
                    format_func=lambda uid: next((f"{u.nombre} ({u.tipo_nivel})" for u in direcciones if u.id == uid), ""),
                    key="sb_padre_unidad_subdir"
                )
        else:  # Jefatura de Departamento
            # Solo puede depender de Subdirecciones
            if not subdirecciones:
                st.info("Primero registra una Subdirección.")
            else:
                padre_id_sel = st.selectbox(
                    "Depende de (Subdirección)*",
                    options=[u.id for u in subdirecciones],
                    format_func=lambda uid: next((f"{u.nombre} ({u.tipo_nivel})" for u in subdirecciones if u.id == uid), ""),
                    key="sb_padre_unidad_jef"
                )
    
        if st.button("Guardar Unidad", key=_k_unidad("guardar_unidad")):
            if not nombre_u:
                st.error("El nombre de la unidad es obligatorio.")
            else:
                # Validar que los niveles dependan correctamente
                if tipo_u == "Dirección General":
                    padre_id = None  # Siempre principal
                else:
                    if padre_id_sel is None:
                        if tipo_u == "Subdirección":
                            st.error("Selecciona una Dirección General de la que dependa la Subdirección.")
                        else:
                            st.error("Selecciona una Subdirección de la que dependa la Jefatura de Departamento.")
                        st.stop()
                    padre_id = padre_id_sel
    
                nueva_unidad = Unidad(nombre=nombre_u, tipo_nivel=tipo_u, parent_id=padre_id)
                session.add(nueva_unidad)
                session.commit()
                st.success(f"Unidad '{nombre_u}' creada exitosamente.")
                # Incrementamos el contador para forzar nuevos widgets vacíos en el próximo rerun
                st.session_state['_unidad_form_reset_cnt'] = _cnt_unidad + 1
                time.sleep(1)
                st.rerun()
    
        st.markdown("---")
        st.subheader("Unidades registradas")
        unidades_all = session.query(Unidad).all()
    
        # Ordenar por nivel jerárquico real: Dirección General -> Subdirección -> Jefatura de Departamento
        def _orden_nivel(tipo):
            t = (tipo or "").strip().lower()
            if "dirección general" in t or "direccion general" in t:
                return 0
            if "subdirección" in t or "subdireccion" in t:
                return 1
            if "jefatura" in t:
                return 2
            return 99
    
        unidades_all = sorted(
            unidades_all,
            key=lambda u: (
                _orden_nivel(u.tipo_nivel),
                (u.parent.nombre if getattr(u, "parent", None) else ""),
                u.nombre or ""
            )
        )
        if not unidades_all:
            st.info("Aún no hay unidades registradas.")
        else:
            for u in unidades_all:
                nivel = u.tipo_nivel or ""
                depende = u.parent.nombre if getattr(u, "parent", None) else "-- Principal --"
                c_nivel, c_nombre, c_dep, c_edit, c_del = st.columns([1.2, 3, 3, 0.8, 0.8])
                c_nivel.write(nivel)
                c_nombre.write(u.nombre)
                c_dep.write(depende)
                if c_edit.button(":material/edit: Editar", key=f"edit_unidad_{u.id}"):
                    st.session_state["unidad_edit_id"] = u.id
                if c_del.button(":material/delete: Eliminar", key=f"del_unidad_{u.id}"):
                    st.warning("Al eliminar la unidad se borrarán también sus subunidades y puestos asociados.")
                    session.delete(u)
                    session.commit()
                    st.success("Unidad eliminada."); time.sleep(1); st.rerun()

                    # Formulario de edición en línea para la unidad seleccionada (solo nombre)
                    if st.session_state.get("unidad_edit_id") == u.id:
                        with st.form(f"form_edit_unidad_{u.id}"):
                            nuevo_nombre_u = st.text_input("Nombre de la Unidad", value=u.nombre)
                            if st.form_submit_button("Guardar cambios"):
                                if nuevo_nombre_u:
                                    u.nombre = nuevo_nombre_u
                                    session.commit()
                                    st.session_state.pop("unidad_edit_id", None)
                                    st.success("Unidad actualizada."); time.sleep(1); st.rerun()
                                else:
                                    st.error("El nombre de la unidad es obligatorio.")

        # --- SUBPestaña 2: Puestos de Trabajo ---
        with sub_puestos:
            st.header("Crear Puesto de Trabajo")
            if todas_unidades:
                with st.form("form_puesto", clear_on_submit=True):
                    nombre_p = st.text_input("Nombre del Puesto (Ej. DOCENTE, SECRETARIA)")
                    es_multipuesto = st.checkbox("Este puesto puede tener múltiples personas (plantilla)", value=False)
                    unidad_id_sel = st.selectbox(
                        "¿A qué unidad pertenece este puesto?*",
                        options=[u.id for u in todas_unidades],
                        format_func=lambda uid: next((f"[{u.tipo_nivel}] - {u.nombre}" for u in todas_unidades if u.id == uid), ""),
                        key="sb_unidad_puesto"
                    )
                    submitted = st.form_submit_button(":material/save: Guardar Puesto")
                    if submitted:
                        unidad_sel_p = next((u for u in todas_unidades if u.id == unidad_id_sel), None)
                        if nombre_p and unidad_sel_p:
                            try:
                                nuevo_puesto = Puesto(
                                    nombre=nombre_p.upper(),
                                    unidad_id=unidad_sel_p.id,
                                    multipuesto=es_multipuesto
                                )
                                session.add(nuevo_puesto)
                                session.commit()
                                st.success(f"Puesto '{nombre_p}' asignado correctamente a: {unidad_sel_p.nombre}")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")
                                session.rollback()
                        else:
                            st.error("Por favor escribe el nombre del puesto.")
            else:
                st.info("Primero debes crear una unidad orgánica arriba.")

            st.markdown("---")
            st.subheader("Puestos registrados")
            puestos_all = session.query(Puesto).join(Unidad).order_by(Unidad.tipo_nivel, Unidad.nombre, Puesto.nombre).all()
            if not puestos_all:
                st.info("Aún no hay puestos registrados.")
            else:
                for p in puestos_all:
                    unidad = p.unidad
                    etiqueta_unidad = f"[{unidad.tipo_nivel}] - {unidad.nombre}" if unidad else "Sin unidad"
                    c_unid, c_nom, c_multi, c_edit, c_del = st.columns([3, 3, 1.5, 0.8, 0.8])
                    c_unid.write(etiqueta_unidad)
                    c_nom.write(p.nombre)
                    c_multi.write(":material/check: Multipuesto" if getattr(p, "multipuesto", False) else "—")
                    if c_edit.button(":material/edit: Editar", key=f"edit_puesto_{p.id}"):
                        st.session_state["puesto_edit_id"] = p.id
                    if c_del.button(":material/delete: Eliminar", key=f"del_puesto_{p.id}"):
                        session.delete(p)
                        session.commit()
                        st.success("Puesto eliminado."); time.sleep(1); st.rerun()

                    # Formulario de edición en línea para el puesto seleccionado (nombre y multipuesto)
                    if st.session_state.get("puesto_edit_id") == p.id:
                        with st.form(f"form_edit_puesto_{p.id}"):
                            nuevo_nombre_p = st.text_input("Nombre del Puesto", value=p.nombre)
                            nuevo_multipuesto = st.checkbox(
                                "Este puesto puede tener múltiples personas (plantilla)",
                                value=getattr(p, "multipuesto", False)
                            )
                            c_btn1, c_btn2 = st.columns(2)
                            if c_btn1.form_submit_button("Guardar cambios"):
                                if nuevo_nombre_p:
                                    p.nombre = nuevo_nombre_p.upper()
                                    p.multipuesto = nuevo_multipuesto
                                    session.commit()
                                    st.session_state.pop("puesto_edit_id", None)
                                    st.success("Puesto actualizado."); time.sleep(1); st.rerun()
                                else:
                                    st.error("El nombre del puesto es obligatorio.")
                            if c_btn2.form_submit_button("Cerrar"):
                                st.session_state.pop("puesto_edit_id", None)
                                st.rerun()

# ==========================================
# PESTAÑA 3: PERSONAL (CUESTIONARIO COMPLETO)
# ==========================================
if (":material/group: Personal" in tab_dict) or ("Personal" in tab_dict):
    with tab_dict.get(":material/group: Personal", tab_dict.get("Personal")):
        st.tabs([":material/person: Registro Integral de Personal"])
        
        # Solo listar puestos vacantes (sin personal asignado) para nuevas altas.
        # Los puestos marcados como "multipuesto" (plantilla) siempre aparecen como disponibles.
        todos_puestos = session.query(Puesto).order_by(Puesto.id).all()
        personal_actual = session.query(Personal).all()
        puestos_ocupados_ids = {p.puesto_id for p in personal_actual if p.puesto_id is not None}
        puestos_disponibles = [
            p for p in todos_puestos
            if (p.id not in puestos_ocupados_ids) or getattr(p, "multipuesto", False)
        ]

        edificios_disp = session.query(Edificio).order_by(Edificio.id).all()
        dominios_correo = session.query(DominioCorreo).order_by(DominioCorreo.dominio).all()
        puesto_id_to_obj = {p.id: p for p in puestos_disponibles}
        edificio_id_to_obj = {e.id: e for e in edificios_disp}

        if not puestos_disponibles:
            st.error("Error: No hay Puestos de Trabajo registrados.")
        elif not edificios_disp:
            st.warning("Error: No hay Edificios registrados. Es obligatorio crear infraestructura primero.")
        else:
            # Contador para forzar reset del formulario: al cambiar las keys, Streamlit crea widgets "nuevos" sin estado previo
            if '_personal_form_reset_cnt' not in st.session_state:
                st.session_state['_personal_form_reset_cnt'] = 0
            _cnt = st.session_state['_personal_form_reset_cnt']
            _k = lambda base: f"{base}_{_cnt}"  # Sufijo único para cada ciclo del formulario

            # --- BLOQUE 3: UBICACIÓN (fuera del form para que la cascada Edificio→Planta→Área funcione) ---
            st.subheader(":material/business: Bloque 1: Datos Laborales y Ubicación")
            puesto_id_sel = st.selectbox(
                "Puesto*",
                options=[p.id for p in puestos_disponibles],
                format_func=lambda pid: f"{puesto_id_to_obj[pid].nombre} ({puesto_id_to_obj[pid].unidad.nombre})",
                key=_k("p_reg")
            )
            puesto_sel = puesto_id_to_obj[puesto_id_sel]
            c12, c13, c14 = st.columns([2, 1, 2])
            edif_id_sel = c12.selectbox(
                "Edificio*",
                options=[e.id for e in edificios_disp],
                format_func=lambda eid: f"Edificio {edificio_id_to_obj[eid].letra} - {edificio_id_to_obj[eid].nombre}",
                key=_k("reg_edif_p")
            )
            edif_sel = edificio_id_to_obj[edif_id_sel]
            plantas_del_edif = session.query(Planta).filter_by(edificio_id=edif_sel.id).order_by(Planta.id).all()
            planta_sel = None
            area_sel = None
            if plantas_del_edif:
                planta_id_to_obj = {p.id: p for p in plantas_del_edif}
                planta_id_sel = c13.selectbox(
                    "Planta*",
                    options=[p.id for p in plantas_del_edif],
                    format_func=lambda pid: planta_id_to_obj[pid].nombre_nivel,
                    key=_k("reg_planta_p")
                )
                planta_sel = planta_id_to_obj[planta_id_sel]
                areas_de_planta = session.query(Espacio).filter_by(planta_id=planta_sel.id).order_by(Espacio.id).all()
                area_opciones_ids = [-1] + [a.id for a in areas_de_planta]
                area_id_to_obj = {a.id: a for a in areas_de_planta}
                area_id_sel = c14.selectbox(
                    "Área Específica (Opcional)",
                    options=area_opciones_ids,
                    format_func=lambda aid: "Sin asignar" if aid == -1 else area_id_to_obj[aid].nombre,
                    key=_k("reg_area_p")
                )
                area_sel = None if area_id_sel == -1 else area_id_to_obj[area_id_sel]
            else:
                c13.warning("Sin plantas en este edificio. Registra plantas en la pestaña Edificios.")
            st.markdown("---")

            # --- UBICACIÓN Y CONTACTO (RESIDENCIA) FUERA DEL FORM (para cascada Estado→Municipio→Localidad) ---
            st.subheader(":material/location_on: Ubicación y Contacto (Residencia)")
            c_ubi1, c_ubi2, c_ubi3 = st.columns(3)
            cat_est_mun = _cargar_catalogo_estados_municipios()
            estados_opts = sorted(list(cat_est_mun.keys()))
            # OJO: estas keys deben ser ESTABLES para que la cascada funcione en cada rerun.
            # No usar _k() aquí, porque _k cambia con el contador de reset del formulario.
            _key_estado = "reg_estado_res"
            _key_mun = "reg_municipio_res"
            _key_loc = "reg_localidad_res"
            # Si antes eran multiselect, podrían existir como lista en session_state.
            if isinstance(st.session_state.get(_key_estado), list):
                st.session_state[_key_estado] = st.session_state[_key_estado][0] if st.session_state[_key_estado] else None
            if isinstance(st.session_state.get(_key_mun), list):
                st.session_state[_key_mun] = st.session_state[_key_mun][0] if st.session_state[_key_mun] else None
            if isinstance(st.session_state.get(_key_loc), list):
                st.session_state[_key_loc] = st.session_state[_key_loc][0] if st.session_state[_key_loc] else None

            # Reset dependencias cuando cambia el padre
            _prev_estado_key = f"{_key_estado}__prev"
            _prev_mun_key = f"{_key_mun}__prev"

            estado_res = c_ubi1.selectbox("Estado", options=estados_opts, key=_key_estado)
            if st.session_state.get(_prev_estado_key) != estado_res:
                st.session_state[_key_mun] = None
                st.session_state[_key_loc] = None
                st.session_state[_prev_estado_key] = estado_res

            municipios_opts = []
            if estado_res:
                municipios_opts.extend(cat_est_mun.get(estado_res, []) or [])
            municipios_opts = sorted(list(dict.fromkeys(municipios_opts)))
            if not municipios_opts:
                municipio_res = c_ubi2.selectbox("Municipio", options=["—"], index=0, key=_key_mun, disabled=True)
                municipio_res = None
            else:
                # Si el valor previo ya no está en opciones, lo reseteamos
                if st.session_state.get(_key_mun) not in municipios_opts:
                    st.session_state[_key_mun] = municipios_opts[0]
                municipio_res = c_ubi2.selectbox("Municipio", options=municipios_opts, key=_key_mun)
            if st.session_state.get(_prev_mun_key) != municipio_res:
                st.session_state[_key_loc] = None
                st.session_state[_prev_mun_key] = municipio_res

            localidades_opts = []
            if municipio_res:
                localidades_opts.extend([municipio_res, "Otro"])
            localidades_opts = sorted(list(dict.fromkeys(localidades_opts)))
            if not localidades_opts:
                localidad_res = c_ubi3.selectbox("Localidad", options=["—"], index=0, key=_key_loc, disabled=True)
                localidad_res = None
            else:
                if st.session_state.get(_key_loc) not in localidades_opts:
                    st.session_state[_key_loc] = localidades_opts[0]
                localidad_res = c_ubi3.selectbox("Localidad", options=localidades_opts, key=_key_loc)

            c_ubi4, c_ubi5, c_ubi6 = st.columns(3)
            codigo_postal = c_ubi4.text_input("Código Postal", key="reg_cp")
            tel_casa = c_ubi5.text_input("Tel. Casa", key="reg_tel_casa")
            tel_otro = c_ubi6.text_input("Tel. Otros", key="reg_tel_otro")

            st.markdown("---")

            # IMPORTANTE: clear_on_submit=False para no perder datos si hay error de validación
            with st.form("form_expediente_personal", clear_on_submit=False):
                # --- BLOQUE 0: DATOS LABORALES Y DE IDENTIDAD (extra) ---
                st.subheader(":material/badge: Datos Laborales y de Identidad")
                c_lab1, c_lab2, c_lab3 = st.columns(3)
                numero_empleado = c_lab1.text_input("Número Empleado", key=_k("reg_num_empleado"))
                grado_academico = c_lab2.selectbox(
                    "Grado Académico*",
                    ["Licenciatura", "Maestría", "Doctorado", "Postdoctorado", "Otro"],
                    key=_k("reg_grado_academico"),
                )
                cvu = c_lab3.text_input(
                    "No. de CVU*",
                    help="Para modificar este campo, pasar al Departamento de Capital Humano.",
                    key=_k("reg_cvu"),
                )
                st.caption("Nota del sistema: Para modificar el CVU, pasar al Departamento de Capital Humano.")
                st.markdown("---")

                # --- BLOQUE 1: IDENTIDAD ---
                st.subheader(":material/person: Bloque 2: Identidad y Datos Personales")
                c_foto, c_nombres = st.columns([1, 2])
                with c_foto:
                    foto_u = st.file_uploader("Fotografía* (Obligatoria)", type=["jpg", "png"], key=_k("reg_foto_p"), 
                                             help="Formato JPG o PNG. Campo obligatorio para el expediente.")
                    if foto_u is not None:
                        st.image(foto_u, caption="Vista previa", width=150)
                with c_nombres:
                    nombre = st.text_input("Nombre(s)*", key=_k("reg_nom_p"))
                    ap_pat = st.text_input("Apellido Paterno*", key=_k("reg_app_p"))
                    ap_mat = st.text_input("Apellido Materno", key=_k("reg_apm_p"))
                
                c1, c2, c3 = st.columns(3)
                f_nacimiento = c1.date_input("Fecha de Nacimiento", value=datetime(1990, 1, 1), min_value=datetime(1950, 1, 1), format="DD/MM/YYYY", key=_k("reg_fnac_p"))
                genero = c2.selectbox("Género", ["Femenino", "Masculino"], key=_k("reg_gen_p"))
                est_civil = c3.selectbox("Estado Civil", ["Soltero", "Unión Libre", "Casado", "Divorciado", "Viudo"], key=_k("reg_ec_p"))
                
                c4, c5 = st.columns([2, 1])
                domicilio = c4.text_input("Domicilio Real", key=_k("reg_dom_p"))
                curp = st.text_input("CURP", key=_k("reg_curp_p"))
                curp_norm = (curp or "").strip().upper()
                val_curp = _validar_curp(curp_norm)
                if curp_norm:
                    if not val_curp["ok"]:
                        st.error("CURP inválida: " + " · ".join(val_curp["errores"]))
                    else:
                        datos = val_curp.get("datos", {})
                        fn_curp = datos.get("fecha_nacimiento")
                        sexo_curp = datos.get("sexo")
                        ent_curp = datos.get("entidad")
                        st.caption(f"CURP OK · Nac: {fn_curp.strftime('%d/%m/%Y')} · Sexo: {sexo_curp} · Entidad: {ent_curp}")
                        # Comparaciones opcionales
                        fn_form = f_nacimiento.date() if isinstance(f_nacimiento, datetime) else f_nacimiento
                        if fn_form and fn_curp and fn_form != fn_curp:
                            st.warning(f"La fecha de nacimiento no coincide con CURP ({fn_curp.strftime('%d/%m/%Y')}).")
                        sexo_form = "M" if (genero or "").lower().startswith("fem") else "H"
                        if sexo_curp and sexo_form and sexo_curp != sexo_form:
                            st.warning(f"El género no coincide con CURP (CURP={sexo_curp}).")
                rfc = st.text_input("RFC", key=_k("reg_rfc_p"))
                rfc_norm = (rfc or "").strip().upper()
                val_rfc = _validar_rfc(rfc_norm)
                if rfc_norm:
                    if not val_rfc["ok"]:
                        st.error("RFC inválido: " + " · ".join(val_rfc["errores"]))
                    else:
                        datos_r = val_rfc.get("datos", {})
                        f_rfc = datos_r.get("fecha")
                        t_rfc = datos_r.get("tipo")
                        st.caption(f"RFC OK · Tipo: {t_rfc} · Fecha: {f_rfc.strftime('%d/%m/%Y') if f_rfc else '—'}")
                        if t_rfc == "Física":
                            fn_form = f_nacimiento.date() if isinstance(f_nacimiento, datetime) else f_nacimiento
                            if fn_form and f_rfc and fn_form != f_rfc:
                                st.warning(f"La fecha de nacimiento no coincide con RFC ({f_rfc.strftime('%d/%m/%Y')}).")
                nss = st.text_input("NSS", key=_k("reg_nss_p"))
                nss_norm = (nss or "").strip().replace("-", "").replace(" ", "")
                val_nss = _validar_nss(nss_norm, fecha_nacimiento=f_nacimiento)
                if nss_norm:
                    if not val_nss["ok"]:
                        st.error("NSS inválido: " + " · ".join(val_nss["errores"]))
                    else:
                        st.caption("NSS OK")

                st.markdown("---")
                
                # --- BLOQUE 3: CONTACTO (existente) ---
                st.subheader(":material/phone: Información de Contacto")
                c_con1, c_con2 = st.columns(2)
                cel_personal = c_con1.text_input("Celular Personal", key=_k("reg_cel_p"))
                cel_norm = None
                val_cel = _validar_celular_mx(cel_personal)
                with c_con2:
                    correo_personal = st.text_input("Correo Electrónico Personal", key=_k("reg_corr_p"))
                    correo_personal_norm = None
                    val_email = _validar_email(correo_personal)
                # Mensajes de validación en una segunda fila, alineados
                v_cel, v_mail = st.columns(2)
                with v_cel:
                    if (cel_personal or "").strip():
                        if not val_cel["ok"]:
                            st.error("Celular inválido: " + " · ".join(val_cel["errores"]))
                        else:
                            cel_norm = val_cel["datos"].get("cel_norm_10")
                            st.caption(f"Celular OK · {cel_norm}")
                with v_mail:
                    if (correo_personal or "").strip():
                        if not val_email["ok"]:
                            st.error("Correo personal inválido: " + " · ".join(val_email["errores"]))
                        else:
                            correo_personal_norm = val_email["datos"].get("email_norm")
                            st.caption(f"Correo personal OK · {correo_personal_norm}")
                
                c_con3, c_con4 = st.columns(2)
                tel_oficina = c_con3.text_input("Teléfono de Oficina", key=_k("reg_tel_o"))
                ext_oficina = c_con4.text_input("Extensión", key=_k("reg_ext_p"))
                tel_of_norm = None
                ext_norm = None
                val_tel_of = _validar_telefono_mx(tel_oficina)
                val_ext = _validar_extension(ext_oficina)
                v_tel, v_ext = st.columns(2)
                with v_tel:
                    if (tel_oficina or "").strip():
                        if not val_tel_of["ok"]:
                            st.error("Teléfono de oficina inválido: " + " · ".join(val_tel_of["errores"]))
                        else:
                            tel_of_norm = val_tel_of["datos"].get("tel_norm_10")
                            st.caption(f"Teléfono OK · {tel_of_norm}")
                with v_ext:
                    if (ext_oficina or "").strip():
                        if not val_ext["ok"]:
                            st.error("Extensión inválida: " + " · ".join(val_ext["errores"]))
                        else:
                            ext_norm = val_ext["datos"].get("ext_norm")
                            st.caption(f"Extensión OK · {ext_norm}")
                # Correo Institucional: si hay dominios configurados, usuario escribe solo la parte local
                if dominios_correo:
                    c_corr1, c_corr2 = st.columns([1, 1])
                    parte_local = c_corr1.text_input("Correo Institucional* (parte antes de @)", placeholder="juan.perez", key=_k("reg_corri_parte"))
                    dominio_id_sel = c_corr2.selectbox("Dominio", options=[d.id for d in dominios_correo], format_func=lambda did: next((f"@{d.dominio}" for d in dominios_correo if d.id == did), ""), key=_k("reg_corri_dom"))
                    dominio_sel = next((d for d in dominios_correo if d.id == dominio_id_sel), None)
                    correo_institucional = (f"{parte_local.strip()}@{dominio_sel.dominio}" if parte_local and dominio_sel else "") or ""
                else:
                    correo_institucional = st.text_input("Correo Institucional*", key=_k("reg_corri_p"))

                st.markdown("---")

                # --- BLOQUE 3.1: DATOS FAMILIARES ---
                st.subheader(":material/family_restroom: Datos Familiares")
                c_fam1, c_fam2 = st.columns(2)
                nombre_padre = c_fam1.text_input("Nombre del Padre", key=_k("reg_nombre_padre"))
                nombre_madre = c_fam2.text_input("Nombre de la Madre", key=_k("reg_nombre_madre"))
                c_fam3, c_fam4 = st.columns(2)
                numero_hijos = c_fam3.number_input("Número de Hijos", min_value=0, step=1, key=_k("reg_num_hijos"))
                # estado civil ya se captura arriba (se mantiene una sola fuente)

                st.markdown("---")

                # --- BLOQUE 3.2: PERFIL PERSONAL Y SALUD ---
                st.subheader(":material/monitor_heart: Perfil Personal y Salud")
                c_sal1, c_sal2, c_sal3 = st.columns(3)
                talla_camisa = c_sal1.text_input("Talla de Camisa", key=_k("reg_talla_camisa"))
                deporte = c_sal2.text_input("Deporte que Practica", key=_k("reg_deporte"))
                actividad_cultural = c_sal3.text_input("Actividad Cultural", key=_k("reg_actividad_cultural"))
                c_sal4, c_sal5 = st.columns(2)
                pasatiempo = c_sal4.text_input("Pasatiempo", key=_k("reg_pasatiempo"))
                alergias = c_sal5.text_input("Alérgico a", key=_k("reg_alergias"))

                st.markdown("---")

                # --- BLOQUE 4: ACADÉMICO ---
                st.subheader(":material/school: Bloque 4: Perfil Académico")
                lista_titulos = ["Ing.", "Mtro.", "Mtra.", "Lic.", "Lcda.", "Dr.", "Dra.", "Arq.", "C.P."]
                st.markdown("**Título profesional**")
                titulo_abrev = st.selectbox("Abreviatura con la que se firma (ej. Ing., Dr., Mtro.)", lista_titulos, key=_k("reg_tabr_p"), label_visibility="collapsed")
                st.markdown("---")
                st.markdown("**Licenciatura o Ingeniería** *(opcional)*")
                licenciatura = st.text_input("Nombre completo del programa", placeholder="Ej. Ingeniería en Industrias Alimentarias", key=_k("reg_lic_p"), label_visibility="collapsed")
                mencio_lic = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Licenciatura", key=_k("reg_mencio_lic"))
                st.markdown("**Maestría** *(opcional)*")
                maestria = st.text_input("Nombre del programa de Maestría", placeholder="Ej. Ciencias en Producción Pecuaria Tropical", key=_k("reg_maest_p"), label_visibility="collapsed")
                mencio_maes = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Maestría", key=_k("reg_mencio_maes"))
                st.markdown("**Doctorado** *(opcional)*")
                doctorado = st.text_input("Nombre del programa de Doctorado", placeholder="Ej. Ciencias en Agricultura Tropical Sustentable", key=_k("reg_doct_p"), label_visibility="collapsed")
                mencio_doct = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica en Doctorado", key=_k("reg_mencio_doct"))

                st.markdown("---")

                # --- LÓGICA DEL BOTÓN DE GUARDADO ---
                submit = st.form_submit_button(":material/save: GUARDAR EXPEDIENTE COMPLETO", use_container_width=True)
                
                if submit:
                    # 1. Validación minuciosa de obligatorios (incluye Fotografía obligatoria)
                    faltantes = []
                    if not foto_u: faltantes.append("Fotografía")
                    if not nombre: faltantes.append("Nombre")
                    if not ap_pat: faltantes.append("Apellido Paterno")
                    if not correo_institucional: faltantes.append("Correo Institucional")
                    if not planta_sel: faltantes.append("Ubicación (Planta)")
                    if not grado_academico: faltantes.append("Grado Académico")
                    if not (cvu or "").strip(): faltantes.append("No. de CVU")
                    if curp_norm and not val_curp["ok"]:
                        faltantes.append("CURP válida")
                    if rfc_norm and not val_rfc["ok"]:
                        faltantes.append("RFC válido")
                    if nss_norm and not val_nss["ok"]:
                        faltantes.append("NSS válido")
                    if (cel_personal or "").strip() and not val_cel["ok"]:
                        faltantes.append("Celular Personal válido")
                    if (correo_personal or "").strip() and not val_email["ok"]:
                        faltantes.append("Correo Personal válido")
                    if (tel_oficina or "").strip() and not val_tel_of["ok"]:
                        faltantes.append("Teléfono de Oficina válido")
                    if (ext_oficina or "").strip() and not val_ext["ok"]:
                        faltantes.append("Extensión válida")

                    if faltantes:
                        st.error(f"No se puede guardar. Faltan los campos obligatorios: {', '.join(faltantes)}")
                    else:
                        try:
                            ruta_foto = os.path.join("fotos_personal", f"p_{int(time.time()*1000)}.jpg")
                            foto_bytes = _procesar_foto_infantil(foto_u, max_bytes=2 * 1024 * 1024)
                            with open(ruta_foto, "wb") as f:
                                f.write(foto_bytes)

                            nuevo_personal = Personal(
                                numero_empleado=(numero_empleado or "").strip() or None,
                                fotografia=ruta_foto,
                                nombre=nombre,
                                apellido_paterno=ap_pat,
                                apellido_materno=ap_mat,
                                fecha_nacimiento=f_nacimiento,
                                genero=genero,
                                estado_civil=est_civil,
                                domicilio=domicilio,
                                curp=curp_norm or None,
                                rfc=rfc_norm or None,
                                nss=nss_norm or None,
                                celular_personal=(cel_norm or "").strip() or None,
                                correo_personal=(correo_personal_norm or "").strip() or None,
                                telefono_oficina=(tel_of_norm or "").strip() or None,
                                extension=(ext_norm or "").strip() or None,
                                correo_institucional=correo_institucional,
                                puesto_id=puesto_sel.id,
                                grado_academico=(grado_academico or "").strip() or None,
                                cvu=(cvu or "").strip() or None,
                                edificio=edif_sel.letra,
                                planta=planta_sel.nombre_nivel,
                                area_asignada=area_sel.nombre if area_sel else "Sin asignar",
                                titulo_abreviatura=titulo_abrev,
                                licenciatura=licenciatura,
                                maestria=maestria,
                                doctorado=doctorado,
                                licenciatura_mencion_honorifica=mencio_lic,
                                maestria_mencion_honorifica=mencio_maes,
                                doctorado_mencion_honorifica=mencio_doct,
                                estado_residencia=(estado_res or "").strip() or None,
                                municipio_residencia=(municipio_res or "").strip() or None,
                                localidad_residencia=(localidad_res or "").strip() or None,
                                codigo_postal=(codigo_postal or "").strip() or None,
                                telefono_casa=(tel_casa or "").strip() or None,
                                telefono_otro=(tel_otro or "").strip() or None,
                                nombre_padre=(nombre_padre or "").strip() or None,
                                nombre_madre=(nombre_madre or "").strip() or None,
                                numero_hijos=int(numero_hijos) if numero_hijos is not None else None,
                                talla_camisa=(talla_camisa or "").strip() or None,
                                deporte=(deporte or "").strip() or None,
                                actividad_cultural=(actividad_cultural or "").strip() or None,
                                pasatiempo=(pasatiempo or "").strip() or None,
                                alergias=(alergias or "").strip() or None,
                            )
                            session.add(nuevo_personal)
                            session.commit()
                            session.close()
                            st.success("Personal guardado correctamente")
                            st.rerun()
                            
                            st.success(f"¡Expediente de {nombre} {ap_pat} guardado con éxito!")
                            
                            st.session_state['_personal_form_reset_cnt'] = st.session_state.get('_personal_form_reset_cnt', 0) + 1
                            time.sleep(2)
                            st.rerun() 
                            
                        except Exception as e:
                            st.error(f"Error crítico al guardar en base de datos: {e}")
# ==========================================
# FUNCIÓN: RENDER EDIFICIOS (usada desde Identidad > Edificios)
# ==========================================
def render_infraestructura_y_espacios():
    st.header(":material/apartment: Gestión de Infraestructura y Espacios")
    session.expire_all()

    # --- CARGAR DESDE EXCEL ---
    with st.expander(":material/upload_file: Cargar desde Excel", expanded=False):
        st.caption("Sube un archivo .xlsx con 3 hojas: **Edificios**, **Plantas**, **Áreas**. Las columnas deben coincidir con la plantilla.")
        col_plantilla, col_upload = st.columns([1, 2])
        with col_plantilla:
            plantilla_bytes = _generar_plantilla_excel_infraestructura()
            st.download_button(
                ":material/download: Descargar plantilla",
                data=plantilla_bytes,
                file_name="plantilla_infraestructura.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_plantilla_infra"
            )
        with col_upload:
            excel_file = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx"], key="excel_infra_upload")
        procesar_btn = st.button("Procesar y cargar datos", type="primary", key="btn_procesar_excel") if excel_file else False
        if excel_file and procesar_btn:
            try:
                xl = pd.ExcelFile(excel_file, engine="openpyxl")
                hojas = [s.strip() for s in xl.sheet_names]
                # Buscar hojas por nombre (flexible)
                hoja_edif = next((h for h in hojas if h.lower() in ("edificios", "edificio")), hojas[0] if hojas else None)
                hoja_plantas = next((h for h in hojas if h.lower() in ("plantas", "planta", "niveles", "nivel")), hojas[1] if len(hojas) > 1 else None)
                hoja_areas = next((h for h in hojas if h.lower() in ("áreas", "areas", "area", "espacios", "espacio")), hojas[2] if len(hojas) > 2 else None)

                def _norm_cols(df):
                    return {str(c).strip().lower(): c for c in df.columns if isinstance(c, str)}

                def _get(col_map, *aliases):
                    for a in aliases:
                        k = str(a).lower().strip()
                        if k in col_map:
                            return col_map[k]
                    return None

                errores = []
                n_edif, n_pl, n_esp = 0, 0, 0
                letra_to_id = {}
                planta_key_to_id = {}

                # 1. EDIFICIOS
                if hoja_edif:
                    df_e = xl.parse(hoja_edif)
                    df_e = df_e.dropna(how="all")
                    cols_e = _norm_cols(df_e)
                    c_letra = _get(cols_e, "Letra", "letra")
                    c_nombre = _get(cols_e, "Nombre", "nombre")
                    if c_letra and c_nombre:
                        for _, row in df_e.iterrows():
                            letra = row.get(c_letra)
                            nombre = row.get(c_nombre)
                            if pd.isna(letra) or pd.isna(nombre) or str(letra).strip() == "" or str(nombre).strip() == "":
                                continue
                            letra_u = str(letra).strip().upper()[:3]
                            nombre_s = str(nombre).strip()
                            exist = session.query(Edificio).filter(Edificio.letra == letra_u).first()
                            if not exist:
                                e_new = Edificio(letra=letra_u, nombre=nombre_s)
                                session.add(e_new)
                                session.flush()
                                letra_to_id[letra_u] = e_new.id
                                n_edif += 1
                        session.commit()
                    else:
                        errores.append(f"Hoja '{hoja_edif}': faltan columnas Letra y/o Nombre.")
                else:
                    errores.append("No se encontró hoja 'Edificios'.")

                # 2. PLANTAS (necesitan edificios cargados)
                if hoja_plantas and not errores:
                    session.expire_all()
                    letra_to_id = {e.letra: e.id for e in session.query(Edificio).all()}
                    df_p = xl.parse(hoja_plantas)
                    df_p = df_p.dropna(how="all")
                    cols_p = _norm_cols(df_p)
                    c_edif = _get(cols_p, "Edificio_Letra", "edificio_letra", "Edificio", "edificio")
                    c_nivel = _get(cols_p, "Nivel", "nivel")
                    c_uso = _get(cols_p, "Uso", "uso")
                    c_rack = _get(cols_p, "Rack_Red", "rack_red")
                    c_acc = _get(cols_p, "Accesible", "accesible")
                    if c_edif and c_nivel:
                        opciones_uso = ["Aulas", "Administrativo", "Laboratorios", "Mixto", "Servicios"]
                        for _, row in df_p.iterrows():
                            letra = row.get(c_edif)
                            nivel = row.get(c_nivel)
                            if pd.isna(letra) or pd.isna(nivel):
                                continue
                            letra_u = str(letra).strip().upper()[:3]
                            nivel_s = str(int(nivel)) if isinstance(nivel, (int, float)) and not pd.isna(nivel) else str(nivel).strip()
                            if nivel_s not in ("1", "2", "3", "4", "5"):
                                nivel_s = nivel_s.replace("Nivel ", "").strip()
                            if nivel_s not in ("1", "2", "3", "4", "5"):
                                continue
                            edif_id = letra_to_id.get(letra_u)
                            if not edif_id:
                                errores.append(f"Planta: edificio '{letra_u}' no existe. Carga primero Edificios.")
                                continue
                            exist = session.query(Planta).filter_by(edificio_id=edif_id, nombre_nivel=nivel_s).first()
                            if not exist:
                                uso = str(row.get(c_uso, "Mixto")).strip() if c_uso else "Mixto"
                                uso = uso if uso in opciones_uso else "Mixto"
                                rack = _parse_si_no(row.get(c_rack)) if c_rack else False
                                acc = _parse_si_no(row.get(c_acc)) if c_acc else True
                                p_new = Planta(edificio_id=edif_id, nombre_nivel=nivel_s, uso_principal=uso, tiene_rack_red=rack, accesible_silla_ruedas=acc)
                                session.add(p_new)
                                session.flush()
                                planta_key_to_id[(letra_u, nivel_s)] = p_new.id
                                n_pl += 1
                        session.commit()
                    else:
                        errores.append(f"Hoja '{hoja_plantas}': faltan columnas Edificio_Letra y/o Nivel.")
                elif hoja_plantas and errores:
                    pass
                elif not hoja_plantas:
                    errores.append("No se encontró hoja 'Plantas'.")

                # 3. ÁREAS/ESPACIOS
                if hoja_areas and not errores:
                    session.expire_all()
                    plantas_all = session.query(Planta).join(Edificio).all()
                    planta_key_to_id = {(p.edificio.letra, p.nombre_nivel): p.id for p in plantas_all if p.edificio}
                    tipos_validos = ["Oficina", "SITE de Redes", "Laboratorio", "Salón/Aula", "Bodega", "Auditorio", "Baños", "Otro"]
                    df_a = xl.parse(hoja_areas)
                    df_a = df_a.dropna(how="all")
                    cols_a = _norm_cols(df_a)
                    c_edif = _get(cols_a, "Edificio_Letra", "edificio_letra", "Edificio", "edificio")
                    c_nivel = _get(cols_a, "Nivel", "nivel")
                    c_nom = _get(cols_a, "Nombre_Area", "nombre_area", "Nombre", "nombre")
                    c_tipo = _get(cols_a, "Tipo_Area", "tipo_area", "Tipo", "tipo")
                    if c_edif and c_nivel and c_nom:
                        for _, row in df_a.iterrows():
                            letra = row.get(c_edif)
                            nivel = row.get(c_nivel)
                            nombre = row.get(c_nom)
                            if pd.isna(letra) or pd.isna(nivel) or pd.isna(nombre) or str(nombre).strip() == "":
                                continue
                            letra_u = str(letra).strip().upper()[:3]
                            nivel_s = str(int(nivel)) if isinstance(nivel, (int, float)) and not pd.isna(nivel) else str(nivel).strip()
                            nivel_s = nivel_s.replace("Nivel ", "").strip()
                            planta_id = planta_key_to_id.get((letra_u, nivel_s))
                            if not planta_id:
                                continue
                            nom_s = str(nombre).strip()
                            tipo_s = str(row.get(c_tipo, "Otro")).strip() if c_tipo else "Otro"
                            tipo_s = tipo_s if tipo_s in tipos_validos else "Otro"
                            session.add(Espacio(planta_id=planta_id, nombre=nom_s, tipo=tipo_s))
                            n_esp += 1
                        session.commit()
                    else:
                        errores.append(f"Hoja '{hoja_areas}': faltan columnas Edificio_Letra, Nivel y/o Nombre_Area.")
                elif hoja_areas and errores:
                    pass
                elif not hoja_areas:
                    errores.append("No se encontró hoja 'Áreas'.")

                if errores:
                    for e in errores:
                        st.error(e)
                else:
                    st.success(f"Carga completada: **{n_edif}** edificios, **{n_pl}** niveles, **{n_esp}** áreas/espacios.")
                    st.rerun()
            except Exception as ex:
                st.error(f"Error al procesar el archivo: {ex}")
    
    sub_add_edif, sub_add_planta, sub_add_espacio = st.tabs([
        ":material/foundation: 1. Edificios", 
        ":material/layers: 2. Plantas/Niveles",
        "🚪 3. Áreas/Espacios"
    ])
    
    edificios_db = session.query(Edificio).all()
    # Plantas ordenadas alfabéticamente por letra de edificio y nombre de nivel
    plantas_db = (
        session.query(Planta)
        .join(Edificio)
        .order_by(Edificio.letra, Planta.nombre_nivel)
        .all()
    )
    
    # --- 1. NUEVO EDIFICIO ---
    with sub_add_edif:
        st.subheader("Registrar Nuevo Edificio")
        st.caption("Paso 1: Registra primero los Edificios. Luego continúa con “2. Plantas/Niveles”.")

        # Mensaje flash específico de Edificios
        flash = st.session_state.pop("_flash_edificio", None)
        if flash and isinstance(flash, (list, tuple)) and len(flash) >= 2:
            tipo, msg = flash[0], flash[1]
            if tipo == "success":
                st.success(msg)
            elif tipo == "warning":
                st.warning(msg)
            elif tipo == "error":
                st.error(msg)

        total_edif = session.query(Edificio).count()
        total_pl = session.query(Planta).count()
        total_esp = session.query(Espacio).count()
        edif_con_pl = set(x[0] for x in session.query(Planta.edificio_id).distinct().all())
        sin_planta = max(total_edif - len(edif_con_pl), 0)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Edificios", total_edif)
        m2.metric("Niveles", total_pl)
        m3.metric("Áreas/Espacios", total_esp)
        m4.metric("Edif. sin niveles", sin_planta)

        with st.form("form_add_edificio", clear_on_submit=True):
            col_l, col_n = st.columns([1, 3])
            letra_e = col_l.text_input("Letra (Ej. A, B)*", max_chars=3)
            nombre_e = col_n.text_input("Nombre (Ej. Aulas Generales)*")
        
            if st.form_submit_button("Guardar Edificio"):
                if letra_e and nombre_e:
                    letra_upper = letra_e.strip().upper()
                    if session.query(Edificio).filter(Edificio.letra == letra_upper).first():
                        st.error(f"La letra '{letra_upper}' ya está en uso.")
                    else:
                        session.add(Edificio(letra=letra_upper, nombre=nombre_e))
                        session.commit()
                        etiqueta_new = f"{letra_upper} – {nombre_e}"
                        st.session_state["_flash_edificio"] = ("success", f"Edificio {etiqueta_new} guardado correctamente.")
                        st.rerun()
                else:
                    st.error("Llena todos los campos obligatorios.")

        # Listado de todos los edificios (tabla) + acciones por selección
        edificios_all = session.query(Edificio).order_by(Edificio.letra).all()
        st.markdown("---")
        st.subheader("Edificios registrados")
        if not edificios_all:
            st.info("No hay edificios registrados.")
        else:
            df_edif = pd.DataFrame([{
                "ID": e.id,
                "Edificio": e.letra,
                "Nombre": e.nombre
            } for e in edificios_all])
            filtro_ed = st.text_input("Filtrar edificios (letra o nombre)", key="filtro_edif_tbl")
            if filtro_ed and filtro_ed.strip():
                f = filtro_ed.strip().lower()
                df_edif = df_edif[
                    df_edif["Edificio"].astype(str).str.lower().str.contains(f, na=False)
                    | df_edif["Nombre"].astype(str).str.lower().str.contains(f, na=False)
                ]
            st.dataframe(df_edif, use_container_width=True, hide_index=True)

            st.markdown("**Acciones**")
            edif_id_acc = st.selectbox(
                "Selecciona un edificio",
                options=[e.id for e in edificios_all],
                format_func=lambda eid: next((f"{e.letra} - {e.nombre}" for e in edificios_all if e.id == eid), str(eid)),
                key="acc_edif_id"
            )
            # Si cambia la selección, cancelamos cualquier confirmación previa
            cd = st.session_state.get("confirm_delete_infra")
            if cd and cd.get("tipo") == "edificio" and cd.get("id") != int(edif_id_acc):
                st.session_state.pop("confirm_delete_infra", None)

            b1, b2 = st.columns(2)
            if b1.button(":material/edit: Editar edificio", use_container_width=True, key="btn_acc_edit_edif"):
                st.session_state["edificio_edit_id"] = edif_id_acc
            if b2.button(":material/delete: Eliminar edificio", use_container_width=True, key="btn_acc_del_edif"):
                st.session_state["confirm_delete_infra"] = {"tipo": "edificio", "id": int(edif_id_acc)}

            cd = st.session_state.get("confirm_delete_infra")
            if cd and cd.get("tipo") == "edificio" and cd.get("id") == int(edif_id_acc):
                n_plantas = session.query(Planta).filter_by(edificio_id=edif_id_acc).count()
                n_areas = (
                    session.query(Espacio)
                    .join(Planta)
                    .filter(Planta.edificio_id == edif_id_acc)
                    .count()
                )
                with st.expander(":material/warning: Confirmar eliminación de edificio", expanded=True):
                    edificio_sel = next((e for e in edificios_all if e.id == edif_id_acc), None)
                    etiqueta = f"{edificio_sel.letra} – {edificio_sel.nombre}" if edificio_sel else str(edif_id_acc)
                    st.warning(f"Vas a eliminar el **Edificio {etiqueta}**. Esta acción no se puede deshacer.")
                    st.caption(f"Impacto: **{n_plantas}** nivel(es) y **{n_areas}** área(s)/espacio(s) se eliminarán junto con el edificio.")
                    cdel1, cdel2 = st.columns(2)
                    if cdel1.button(":material/delete: Confirmar eliminación", use_container_width=True, key="confirm_del_edif"):
                        e_del = session.get(Edificio, edif_id_acc) if hasattr(session, "get") else session.query(Edificio).get(edif_id_acc)
                        if e_del:
                            etiqueta_del = f"{e_del.letra} – {e_del.nombre}" if e_del.nombre else e_del.letra
                            session.delete(e_del)
                            session.commit()
                            st.session_state.pop("confirm_delete_infra", None)
                            st.session_state["_flash_edificio"] = ("success", f"Edificio {etiqueta_del} eliminado correctamente.")
                            st.rerun()
                    if cdel2.button("Cancelar", use_container_width=True, key="cancel_del_edif"):
                        st.session_state.pop("confirm_delete_infra", None)
                        st.rerun()

            edif_edit_id = st.session_state.get("edificio_edit_id")
            if edif_edit_id:
                e_edit = next((e for e in edificios_all if e.id == edif_edit_id), None)
                if e_edit:
                    with st.form("form_edit_edif_acc"):
                        nueva_letra = st.text_input("Letra (Ej. A, B)*", value=e_edit.letra)
                        nuevo_nombre = st.text_input("Nombre (Ej. Aulas Generales)*", value=e_edit.nombre)
                        c_btn_g, c_btn_c = st.columns([1, 1])
                        if c_btn_g.form_submit_button("Guardar cambios"):
                            if nueva_letra and nuevo_nombre:
                                letra_upper = nueva_letra.strip().upper()
                                existente = session.query(Edificio).filter(
                                    Edificio.letra == letra_upper,
                                    Edificio.id != e_edit.id
                                ).first()
                                if existente:
                                    st.error(f"La letra '{letra_upper}' ya está en uso por otro edificio.")
                                else:
                                    e_edit.letra = letra_upper
                                    e_edit.nombre = nuevo_nombre
                                    session.commit()
                                    st.session_state.pop("edificio_edit_id", None)
                                    etiqueta_upd = f"{e_edit.letra} – {e_edit.nombre}"
                                    st.session_state["_flash_edificio"] = ("success", f"Edificio {etiqueta_upd} actualizado correctamente.")
                                    st.rerun()
                            else:
                                st.error("Llena todos los campos obligatorios.")
                        if c_btn_c.form_submit_button("Cerrar edición"):
                            st.session_state.pop("edificio_edit_id", None)
                            st.rerun()

    # --- 3. NUEVA PLANTA / NIVEL ---
    with sub_add_planta:
        st.subheader("Registrar Planta en un Edificio")
        st.caption("Paso 2: Registra los Niveles (1–5) dentro de un Edificio. Luego crea “3. Áreas/Espacios”.")

        total_edif = session.query(Edificio).count()
        total_pl = session.query(Planta).count()
        total_esp = session.query(Espacio).count()
        pl_con_esp = set(x[0] for x in session.query(Espacio.planta_id).distinct().all())
        sin_area = max(total_pl - len(pl_con_esp), 0)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Edificios", total_edif)
        m2.metric("Niveles", total_pl)
        m3.metric("Áreas/Espacios", total_esp)
        m4.metric("⚠ Niveles sin áreas", sin_area)

        if not edificios_db:
            st.warning("Primero registra un Edificio.")
        else:
            with st.form("form_add_planta", clear_on_submit=True):
                # Usar id del edificio como valor para que la selección se guarde correctamente al cambiar de edificio
                edif_id_sel = st.selectbox(
                    "Selecciona el Edificio*",
                    options=[e.id for e in edificios_db],
                    format_func=lambda eid: next((f"{e.letra} - {e.nombre}" for e in edificios_db if e.id == eid), str(eid)),
                    key="select_edificio_planta"
                )
            
                c_n, c_u = st.columns(2)
                # Selección de nivel predefinido (1-5) para evitar duplicados y estandarizar valores
                opciones_nivel = ["1", "2", "3", "4", "5"]
                nombre_nivel = c_n.selectbox("Nivel* (1–5)", options=opciones_nivel, format_func=lambda n: f"Nivel {n}")
                uso_princ = c_u.selectbox("Uso Principal", ["Aulas", "Administrativo", "Laboratorios", "Mixto", "Servicios"])
            
                st.write("Características de Infraestructura:")
                c_ch1, c_ch2 = st.columns(2)
                tiene_rack = c_ch1.checkbox("📡 Cuenta con Rack/Switch de Red (IDF) en este piso")
                es_accesible = c_ch2.checkbox("♿ Accesible para sillas de ruedas (Rampa/Elevador)", value=True)
            
                croquis = st.file_uploader("Croquis / Plano de Red (Opcional)", type=["png", "jpg", "pdf"])
            
                if st.form_submit_button("Guardar Planta"):
                    if nombre_nivel:
                        # Verificar que no exista ya una planta con el mismo nivel en este edificio
                        planta_existente = session.query(Planta).filter_by(
                            edificio_id=edif_id_sel,
                            nombre_nivel=nombre_nivel
                        ).first()
                        if planta_existente:
                            st.error("Ya existe una planta con este nivel en este edificio.")
                        else:
                            ruta_croquis = None
                            if croquis is not None:
                                try:
                                    os.makedirs("croquis_plantas", exist_ok=True)
                                    ext = os.path.splitext(croquis.name)[1].lower() if getattr(croquis, "name", None) else ""
                                    if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
                                        ext = ".pdf"
                                    ruta_croquis = os.path.join(
                                        "croquis_plantas",
                                        f"pl_{int(edif_id_sel)}_{str(nombre_nivel)}_{int(time.time()*1000)}{ext}"
                                    )
                                    with open(ruta_croquis, "wb") as f:
                                        f.write(croquis.getvalue())
                                except Exception:
                                    ruta_croquis = None
                            nueva_planta = Planta(
                                edificio_id=edif_id_sel,
                                nombre_nivel=nombre_nivel,
                                uso_principal=uso_princ,
                                tiene_rack_red=tiene_rack,
                                accesible_silla_ruedas=es_accesible,
                                croquis=ruta_croquis
                            )
                            session.add(nueva_planta)
                            session.commit()
                            edif_sel_obj = next((e for e in edificios_db if e.id == edif_id_sel), None)
                            etiqueta_edif = f"{edif_sel_obj.letra} – {edif_sel_obj.nombre}" if edif_sel_obj and edif_sel_obj.nombre else (edif_sel_obj.letra if edif_sel_obj else str(edif_id_sel))
                            st.session_state["_flash_planta"] = ("success", f"Nivel {nombre_nivel} en Edificio {etiqueta_edif} guardado correctamente.")
                            st.rerun()
                    else:
                        st.error("El nombre del nivel es obligatorio.")

            # Listado de todas las plantas con acciones de edición y eliminación,
            # agrupadas y ordenadas alfabéticamente por letra de edificio
            plantas_all = (
                session.query(Planta)
                .join(Edificio)
                .order_by(Edificio.letra, Planta.nombre_nivel)
                .all()
            )
            st.markdown("---")
            st.subheader("Plantas registradas (todos los edificios)")
            if not plantas_all:
                st.info("No hay plantas registradas.")
            else:
                df_plantas = pd.DataFrame([{
                    "ID": p.id,
                    "Edificio": f"{p.edificio.letra} - {p.edificio.nombre}" if p.edificio and p.edificio.nombre else (p.edificio.letra if p.edificio else "?"),
                    "Nivel": f"Nivel {p.nombre_nivel}",
                    "Uso": p.uso_principal or "",
                    "Rack": "Sí" if p.tiene_rack_red else "No",
                    "Accesible": "Sí" if p.accesible_silla_ruedas else "No",
                } for p in plantas_all])
                filtro_pl = st.text_input("Filtrar niveles (edificio, nivel o uso)", key="filtro_pl_tbl")
                if filtro_pl and filtro_pl.strip():
                    f = filtro_pl.strip().lower()
                    df_plantas = df_plantas[
                        df_plantas["Edificio"].astype(str).str.lower().str.contains(f, na=False)
                        | df_plantas["Nivel"].astype(str).str.lower().str.contains(f, na=False)
                        | df_plantas["Uso"].astype(str).str.lower().str.contains(f, na=False)
                    ]
                st.dataframe(df_plantas, use_container_width=True, hide_index=True)

                st.markdown("**Acciones**")
                planta_id_acc = st.selectbox(
                    "Selecciona una planta/nivel",
                    options=[p.id for p in plantas_all],
                    format_func=lambda pid: next(
                        (f"Edificio {p.edificio.letra} - {p.edificio.nombre} · Nivel {p.nombre_nivel}" for p in plantas_all if p.id == pid and p.edificio),
                        str(pid)
                    ),
                    key="acc_planta_id"
                )
                # Si cambia la selección, cancelamos cualquier confirmación previa de nivel
                cd = st.session_state.get("confirm_delete_infra")
                if cd and cd.get("tipo") == "planta" and cd.get("id") != int(planta_id_acc):
                    st.session_state.pop("confirm_delete_infra", None)

                pb1, pb2 = st.columns(2)
                if pb1.button(":material/edit: Editar nivel", use_container_width=True, key="btn_acc_edit_planta"):
                    st.session_state["planta_edit_id"] = planta_id_acc
                if pb2.button(":material/delete: Eliminar nivel", use_container_width=True, key="btn_acc_del_planta"):
                    st.session_state["confirm_delete_infra"] = {"tipo": "planta", "id": int(planta_id_acc)}

                cd = st.session_state.get("confirm_delete_infra")
                if cd and cd.get("tipo") == "planta" and cd.get("id") == int(planta_id_acc):
                    n_areas = session.query(Espacio).filter_by(planta_id=planta_id_acc).count()
                    p_sel = next((p for p in plantas_all if p.id == planta_id_acc), None)
                    etiqueta_pl = f"Nivel {p_sel.nombre_nivel}" if p_sel else f"Nivel {planta_id_acc}"
                    with st.expander(":material/warning: Confirmar eliminación de nivel", expanded=True):
                        st.warning(f"Vas a eliminar el **{etiqueta_pl}**. Esta acción no se puede deshacer.")
                        st.caption(f"Impacto: **{n_areas}** área(s)/espacio(s) se eliminarán junto con este nivel.")
                        cdel1, cdel2 = st.columns(2)
                        if cdel1.button(":material/delete: Confirmar eliminación", use_container_width=True, key="confirm_del_planta"):
                            p_del = session.get(Planta, planta_id_acc) if hasattr(session, "get") else session.query(Planta).get(planta_id_acc)
                            if p_del:
                                etiqueta_pl_del = f"Nivel {p_del.nombre_nivel}"
                                session.delete(p_del)
                                session.commit()
                                st.session_state.pop("confirm_delete_infra", None)
                                st.session_state["_flash_planta"] = ("success", f"{etiqueta_pl_del} eliminado correctamente.")
                                st.rerun()
                        if cdel2.button("Cancelar", use_container_width=True, key="cancel_del_planta"):
                            st.session_state.pop("confirm_delete_infra", None)
                            st.rerun()

                planta_edit_id = st.session_state.get("planta_edit_id")
                if planta_edit_id:
                    p_edit = next((p for p in plantas_all if p.id == planta_edit_id), None)
                    if p_edit:
                        with st.form("form_edit_planta_acc"):
                            opciones_nivel_edit = ["1", "2", "3", "4", "5"]
                            if p_edit.nombre_nivel and p_edit.nombre_nivel not in opciones_nivel_edit:
                                opciones_nivel_edit = [p_edit.nombre_nivel] + opciones_nivel_edit
                            idx_niv = opciones_nivel_edit.index(p_edit.nombre_nivel) if p_edit.nombre_nivel in opciones_nivel_edit else 0
                            nuevo_nombre = st.selectbox(
                                "Nivel* (1–5)",
                                options=opciones_nivel_edit,
                                index=idx_niv,
                                format_func=lambda n: f"Nivel {n}" if str(n).isdigit() else str(n)
                            )
                            opciones_uso = ["Aulas", "Administrativo", "Laboratorios", "Mixto", "Servicios"]
                            idx_uso = opciones_uso.index(p_edit.uso_principal) if p_edit.uso_principal in opciones_uso else 0
                            nuevo_uso = st.selectbox("Uso Principal", opciones_uso, index=idx_uso)
                            c_ch1, c_ch2 = st.columns(2)
                            nuevo_tiene_rack = c_ch1.checkbox(
                                "📡 Cuenta con Rack/Switch de Red (IDF) en este piso",
                                value=p_edit.tiene_rack_red
                            )
                            nuevo_es_accesible = c_ch2.checkbox(
                                "♿ Accesible para sillas de ruedas (Rampa/Elevador)",
                                value=p_edit.accesible_silla_ruedas
                            )
                            c_btn_g, c_btn_c = st.columns([1, 1])
                            if c_btn_g.form_submit_button("Guardar cambios"):
                                p_edit.nombre_nivel = nuevo_nombre
                                p_edit.uso_principal = nuevo_uso
                                p_edit.tiene_rack_red = nuevo_tiene_rack
                                p_edit.accesible_silla_ruedas = nuevo_es_accesible
                                session.commit()
                                st.session_state.pop("planta_edit_id", None)
                                etiqueta_pl_upd = f"Nivel {p_edit.nombre_nivel}"
                                st.session_state["_flash_planta"] = ("success", f"{etiqueta_pl_upd} actualizado correctamente.")
                                st.rerun()
                            if c_btn_c.form_submit_button("Cerrar edición"):
                                st.session_state.pop("planta_edit_id", None)
                                st.rerun()

    # --- 4. NUEVO ESPACIO / ÁREA ---
    with sub_add_espacio:
        st.subheader("Registrar Área o Espacio")
        st.caption("Paso 3: Registra las Áreas/Espacios dentro de un Edificio y Nivel.")

        # Mensaje flash específico de Áreas/Espacios
        flash_esp = st.session_state.pop("_flash_espacio", None)
        if flash_esp and isinstance(flash_esp, (list, tuple)) and len(flash_esp) >= 2:
            tipo, msg = flash_esp[0], flash_esp[1]
            if tipo == "success":
                st.success(msg)
            elif tipo == "warning":
                st.warning(msg)
            elif tipo == "error":
                st.error(msg)

        total_edif = session.query(Edificio).count()
        total_pl = session.query(Planta).count()
        total_esp = session.query(Espacio).count()
        m1, m2, m3 = st.columns(3)
        m1.metric("Edificios", total_edif)
        m2.metric("Niveles", total_pl)
        m3.metric("Áreas/Espacios", total_esp)

        if not plantas_db:
            st.warning("Debes registrar al menos una Planta en un Edificio.")
        else:
            with st.form("form_add_espacio", clear_on_submit=True):
                # Usar id de la planta como valor para que la selección sea estable y se asocie correctamente
                planta_id_sel = st.selectbox(
                    "Ubicación (Edificio y Nivel)*",
                    options=[p.id for p in plantas_db],
                    format_func=lambda pid: next(
                        (f"Edificio {p.edificio.letra} - {p.edificio.nombre} · Nivel {p.nombre_nivel}" for p in plantas_db if p.id == pid and p.edificio),
                        str(pid)
                    ),
                    key="select_planta_espacio"
                )
            
                c_tipo, c_nombre = st.columns([1, 2])
                tipo_espacio = c_tipo.selectbox("Tipo de Área/Espacio", ["Oficina", "SITE de Redes", "Laboratorio", "Salón/Aula", "Bodega", "Auditorio", "Baños", "Otro"])
                nombre_espacio = c_nombre.text_input("Nombre del Área/Espacio (Ej. SITE Principal, Salón 4)*")
            
                if st.form_submit_button("Guardar Área"):
                    if nombre_espacio:
                        session.add(Espacio(planta_id=planta_id_sel, nombre=nombre_espacio, tipo=tipo_espacio))
                        session.commit()
                        st.session_state["_flash_espacio"] = ("success", f"Área/Espacio “{nombre_espacio}” guardado correctamente.")
                        st.rerun()

        # Listado de todas las áreas/espacios con acciones de edición y eliminación,
        # agrupadas y ordenadas por edificio y nivel
        espacios_all = (
            session.query(Espacio)
            .join(Planta)
            .join(Edificio)
            .order_by(Edificio.letra, Planta.nombre_nivel, Espacio.nombre)
            .all()
        )
        st.markdown("---")
        st.subheader("Áreas / Espacios registrados (todos los edificios)")
        if not espacios_all:
            st.info("No hay áreas registradas.")
        else:
            df_esp = pd.DataFrame([{
                "ID": esp.id,
                "Edificio": f"{esp.planta.edificio.letra} - {esp.planta.edificio.nombre}" if esp.planta and esp.planta.edificio and esp.planta.edificio.nombre else (esp.planta.edificio.letra if esp.planta and esp.planta.edificio else "?"),
                "Nivel": f"Nivel {esp.planta.nombre_nivel}" if esp.planta else "Nivel ?",
                "Tipo": esp.tipo or "",
                "Área/Espacio": esp.nombre or "",
            } for esp in espacios_all])
            filtro_esp = st.text_input("Filtrar áreas (edificio, nivel, tipo o nombre)", key="filtro_esp_tbl")
            if filtro_esp and filtro_esp.strip():
                f = filtro_esp.strip().lower()
                df_esp = df_esp[
                    df_esp["Edificio"].astype(str).str.lower().str.contains(f, na=False)
                    | df_esp["Nivel"].astype(str).str.lower().str.contains(f, na=False)
                    | df_esp["Tipo"].astype(str).str.lower().str.contains(f, na=False)
                    | df_esp["Área/Espacio"].astype(str).str.lower().str.contains(f, na=False)
                ]
            st.dataframe(df_esp, use_container_width=True, hide_index=True)

            st.markdown("**Acciones**")
            esp_id_acc = st.selectbox(
                "Selecciona un área/espacio",
                options=[e.id for e in espacios_all],
                format_func=lambda eid: next((
                    f"Edificio {esp.planta.edificio.letra} - {esp.planta.edificio.nombre} · Nivel {esp.planta.nombre_nivel} · {esp.nombre}"
                    for esp in espacios_all
                    if esp.id == eid and esp.planta and esp.planta.edificio
                ), str(eid)),
                key="acc_espacio_id"
            )
            # Si cambia la selección, cancelamos cualquier confirmación previa de área/espacio
            cd = st.session_state.get("confirm_delete_infra")
            if cd and cd.get("tipo") == "espacio" and cd.get("id") != int(esp_id_acc):
                st.session_state.pop("confirm_delete_infra", None)

            eb1, eb2 = st.columns(2)
            if eb1.button(":material/edit: Editar área/espacio", use_container_width=True, key="btn_acc_edit_espacio"):
                st.session_state["espacio_edit_id"] = esp_id_acc
            if eb2.button(":material/delete: Eliminar área/espacio", use_container_width=True, key="btn_acc_del_espacio"):
                st.session_state["confirm_delete_infra"] = {"tipo": "espacio", "id": int(esp_id_acc)}

            cd = st.session_state.get("confirm_delete_infra")
            if cd and cd.get("tipo") == "espacio" and cd.get("id") == int(esp_id_acc):
                esp_sel = next((e for e in espacios_all if e.id == esp_id_acc), None)
                etiqueta_esp = esp_sel.nombre if esp_sel and esp_sel.nombre else str(esp_id_acc)
                with st.expander(":material/warning: Confirmar eliminación de área/espacio", expanded=True):
                    st.warning(f"Vas a eliminar el área/espacio **“{etiqueta_esp}”**. Esta acción no se puede deshacer.")
                    cdel1, cdel2 = st.columns(2)
                    if cdel1.button(":material/delete: Confirmar eliminación", use_container_width=True, key="confirm_del_espacio"):
                        esp_del = session.get(Espacio, esp_id_acc) if hasattr(session, "get") else session.query(Espacio).get(esp_id_acc)
                        if esp_del:
                            etiqueta_esp_del = esp_del.nombre or str(esp_id_acc)
                            session.delete(esp_del)
                            session.commit()
                            st.session_state.pop("confirm_delete_infra", None)
                            st.session_state["_flash_espacio"] = ("success", f"Área/Espacio “{etiqueta_esp_del}” eliminado correctamente.")
                            st.rerun()
                    if cdel2.button("Cancelar", use_container_width=True, key="cancel_del_espacio"):
                        st.session_state.pop("confirm_delete_infra", None)
                        st.rerun()

            espacio_edit_id = st.session_state.get("espacio_edit_id")
            if espacio_edit_id:
                esp_edit = next((e for e in espacios_all if e.id == espacio_edit_id), None)
                if esp_edit:
                    with st.form("form_edit_espacio_acc"):
                        nuevo_nombre_esp = st.text_input("Nombre del Área/Espacio*", value=esp_edit.nombre or "")
                        opciones_tipo = ["Oficina", "SITE de Redes", "Laboratorio", "Salón/Aula", "Bodega", "Auditorio", "Baños", "Otro"]
                        idx_tipo = opciones_tipo.index(esp_edit.tipo) if esp_edit.tipo in opciones_tipo else 0
                        nuevo_tipo_esp = st.selectbox("Tipo", opciones_tipo, index=idx_tipo)
                        c_btn_g, c_btn_c = st.columns([1, 1])
                        if c_btn_g.form_submit_button("Guardar cambios"):
                            if nuevo_nombre_esp:
                                esp_edit.nombre = nuevo_nombre_esp.strip()
                                esp_edit.tipo = nuevo_tipo_esp
                                session.commit()
                                st.session_state.pop("espacio_edit_id", None)
                                etiqueta_esp_upd = esp_edit.nombre or str(espacio_edit_id)
                                st.session_state["_flash_espacio"] = ("success", f"Área/Espacio “{etiqueta_esp_upd}” actualizado correctamente.")
                                st.rerun()
                            else:
                                st.error("El nombre del área es obligatorio.")
                        if c_btn_c.form_submit_button("Cerrar edición"):
                            st.session_state.pop("espacio_edit_id", None)

 # ==========================================
# PESTAÑA 5: PRODUCCIÓN ACADÉMICA
# ==========================================
if (":material/auto_stories: Producción Académica" in tab_dict) or ("Producción Académica" in tab_dict):
    with tab_dict.get(":material/auto_stories: Producción Académica", tab_dict.get("Producción Académica")):
        st.header(":material/auto_stories: Gestión de Producción Académica")
        session.expire_all()
        
        personal_db = session.query(Personal).all()
        
        if not personal_db:
            st.warning("No hay personal registrado. Ve a la pestaña de 'Personal' para registrar al menos a un docente o investigador primero.")
        else:
            sub_list_prod, sub_add_prod, sub_edit_del_prod = st.tabs([
                "📋 Listar y Buscar", 
                ":material/add: Registrar Producción", 
                ":material/edit: Editar / Eliminar"
            ])
            
            # --- 1. LISTAR Y BUSCAR ---
            with sub_list_prod:
                st.subheader("Buscador de Publicaciones")
                busqueda_prod = st.text_input(":material/search: Buscar por título de obra, autor o ISBN/ISSN...")
                
                query_prod = session.query(ProduccionAcademica).join(Personal)
                
                if busqueda_prod:
                    termino = f"%{busqueda_prod}%"
                    query_prod = query_prod.filter(or_(
                        ProduccionAcademica.titulo.ilike(termino),
                        ProduccionAcademica.identificador.ilike(termino),
                        Personal.nombre.ilike(termino),
                        Personal.apellido_paterno.ilike(termino)
                    ))
                    
                resultados_prod = query_prod.all()
                
                if resultados_prod:
                    st.markdown("---")
                    for prod in resultados_prod:
                        autor = f"{prod.empleado.titulo_abreviatura or ''} {prod.empleado.nombre} {prod.empleado.apellido_paterno}"
                        with st.expander(f"{prod.tipo}: {prod.titulo} — (Autor: {autor})"):
                            c1, c2 = st.columns(2)
                            c1.write(f"**Fecha de publicación:** {prod.fecha.strftime('%d/%m/%Y')}")
                            c1.write(f"**Identificador (ISBN/ISSN):** {prod.identificador}")
                            if prod.tipo == "Capítulo de Libro":
                                c2.write(f"**Título del Capítulo:** {prod.titulo_capitulo}")
                            if prod.tipo == "Artículo":
                                c2.write(f"**Revista / Medio:** {prod.revista_medio}")
                            c2.write(f"**Programas en los que imparte clases:** {prod.empleado.programas_educativos or 'No especificado'}")
                else:
                    st.info("No se encontraron publicaciones con ese criterio.")
    
            # --- 2. REGISTRAR PRODUCCIÓN ---
            with sub_add_prod:
                st.subheader("Registrar Nueva Publicación")
                
                # 2.1 Seleccionar Autor y Programas Educativos
                empleado_sel = st.selectbox("1. Selecciona al Docente/Investigador (Autor)*", options=personal_db, format_func=lambda p: f"{p.nombre} {p.apellido_paterno} - {p.puesto.nombre}")
                
                with st.form("form_prog_edu"):
                    st.write(":material/school: **Programas Educativos del Docente**")
                    prog_act = st.text_area("Carreras en donde da clases", value=empleado_sel.programas_educativos or "")
                    if st.form_submit_button(":material/save: Actualizar Programas"):
                        empleado_sel.programas_educativos = prog_act
                        session.commit()
                        st.success("Programas educativos actualizados."); time.sleep(1); st.rerun()
    
                st.markdown("---")
                
                # 2.2 Formulario Dinámico de Producción
                st.write(":material/auto_stories: **2. Agregar Nueva Publicación**")
                tipo_prod = st.selectbox("Tipo de Producción a Registrar", ["Libro", "Capítulo de Libro", "Artículo"])
                
                with st.form("form_add_prod", clear_on_submit=True):
                    if tipo_prod == "Libro":
                        c_t, c_f = st.columns([3, 1])
                        tit_obra = c_t.text_input("Título del Libro*")
                        f_pub = c_f.date_input("Fecha")
                        c_i, c_id = st.columns(2)
                        ident = c_i.text_input("ISBN*")
                        extra_id = c_id.text_input("Identificador del Libro (Opcional)")
                        tit_cap = None
                        rev_med = None
                        
                    elif tipo_prod == "Capítulo de Libro":
                        tit_obra = st.text_input("Título del Libro (Que contiene el capítulo)*")
                        tit_cap = st.text_input("Título del Capítulo*")
                        c_f, c_i = st.columns(2)
                        f_pub = c_f.date_input("Fecha")
                        ident = c_i.text_input("ISBN*")
                        extra_id = None
                        rev_med = None
                        
                    elif tipo_prod == "Artículo":
                        tit_obra = st.text_input("Título del Artículo*")
                        rev_med = st.text_input("Revista o Medio de Publicación*")
                        c_f, c_i = st.columns(2)
                        f_pub = c_f.date_input("Fecha")
                        ident = c_i.text_input("ISSN*")
                        extra_id = None
                        tit_cap = None
                    
                    if st.form_submit_button(":material/save: Guardar Publicación"):
                        if tit_obra and ident:
                            # Combinar ISBN/ISSN con identificador opcional (ej. "PUBLICADO") si existe
                            ident_final = f"{ident} | {extra_id}" if extra_id and extra_id.strip() else ident
                            nueva_prod = ProduccionAcademica(
                                personal_id=empleado_sel.id, tipo=tipo_prod, titulo=tit_obra,
                                titulo_capitulo=tit_cap, revista_medio=rev_med, fecha=f_pub, identificador=ident_final
                            )
                            session.add(nueva_prod)
                            session.commit()
                            st.success(f"Publicación registrada a nombre de {empleado_sel.nombre}.")
                            time.sleep(1.5); st.rerun()
                        else:
                            st.error("Por favor, llena los campos obligatorios (*).")
    
            # --- 3. EDITAR / ELIMINAR ---
            with sub_edit_del_prod:
                st.subheader("Gestión de Modificaciones")
                producciones_db = session.query(ProduccionAcademica).all()
                
                if producciones_db:
                    prod_mod = st.selectbox("Selecciona la publicación a modificar:", options=producciones_db, format_func=lambda pr: f"[{pr.tipo}] {pr.titulo} - Autor: {pr.empleado.nombre}")
                    
                    with st.form("form_mod_prod"):
                        n_tit = st.text_input("Título", value=prod_mod.titulo)
                        n_ident = st.text_input("ISBN/ISSN", value=prod_mod.identificador)
                        n_fecha = st.date_input("Fecha", value=prod_mod.fecha)
                        
                        c_btn1, c_btn2 = st.columns(2)
                        if c_btn1.form_submit_button(":material/save: Actualizar Publicación"):
                            prod_mod.titulo = n_tit
                            prod_mod.identificador = n_ident
                            prod_mod.fecha = n_fecha
                            session.commit()
                            st.success("Actualizado."); time.sleep(1); st.rerun()
                            
                        if c_btn2.form_submit_button(":material/delete: Eliminar Publicación"):
                            session.delete(prod_mod)
                            session.commit()
                            st.success("Publicación eliminada."); time.sleep(1.5); st.rerun()
                else:
                    st.info("No hay publicaciones registradas para editar o eliminar.")
# ==========================================
# PESTAÑA 6: HISTORIAL DE CAPACITACIÓN
# ==========================================
if (":material/construction: Capacitación" in tab_dict) or ("Capacitación" in tab_dict):
    with tab_dict.get(":material/construction: Capacitación", tab_dict.get("Capacitación")):
        st.header(":material/construction: Gestión de Capacitación y Cursos")
        session.expire_all()
        
        personal_db = session.query(Personal).all()
        
        if not personal_db:
            st.warning("Registra personal en la pestaña 'Personal' antes de agregar cursos.")
        else:
            sub_list_cur, sub_add_cur, sub_edit_del_cur = st.tabs([
                "📋 Consultar Historial", 
                ":material/add: Registrar Curso", 
                ":material/edit: Editar / Eliminar"
            ])
            
            # --- 1. CONSULTAR HISTORIAL ---
            with sub_list_cur:
                st.subheader("Buscador de Capacitaciones")
                busqueda_cur = st.text_input(":material/search: Buscar por nombre de curso, institución o empleado...")
                
                query_cur = session.query(CursoCapacitacion).join(Personal)
                
                if busqueda_cur:
                    termino = f"%{busqueda_cur}%"
                    query_cur = query_cur.filter(or_(
                        CursoCapacitacion.nombre_curso.ilike(termino),
                        CursoCapacitacion.institucion.ilike(termino),
                        Personal.nombre.ilike(termino),
                        Personal.apellido_paterno.ilike(termino)
                    ))
                
                resultados_cur = query_cur.all()
                
                if resultados_cur:
                    for cur in resultados_cur:
                        nombre_emp = f"{cur.empleado.nombre} {cur.empleado.apellido_paterno}"
                        with st.expander(f":material/school: {cur.nombre_curso} — {nombre_emp}"):
                            c1, c2 = st.columns(2)
                            c1.write(f"**Institución:** {cur.institucion}")
                            c1.write(f"**Duración:** {cur.horas} horas")
                            c2.write(f"**Fecha de Término:** {cur.fecha_termino.strftime('%d/%m/%Y')}")
                            c2.write(f"**Documento:** {cur.tipo_documento}")
                else:
                    st.info("No se encontraron registros.")
    
            # --- 2. REGISTRAR CURSO ---
            with sub_add_cur:
                st.subheader("Asignar Curso a Empleado")
                
                # Usar IDs para que la selección persista correctamente entre reruns
                personal_id_to_obj = {p.id: p for p in personal_db}
                emp_id_sel = st.selectbox(
                    "Selecciona al Empleado*",
                    options=list(personal_id_to_obj.keys()),
                    format_func=lambda pid: f"{personal_id_to_obj[pid].nombre} {personal_id_to_obj[pid].apellido_paterno} - {personal_id_to_obj[pid].puesto.nombre if personal_id_to_obj[pid].puesto else 'Sin puesto'}",
                    key="sel_emp_curso"
                )
                emp_cur_sel = personal_id_to_obj.get(emp_id_sel)
                
                with st.form("form_add_curso", clear_on_submit=True):
                    nom_curso = st.text_input("Nombre del Curso / Taller*")
                    inst_curso = st.text_input("Institución que lo imparte*")
                    
                    col_h, col_f, col_d = st.columns([1, 1, 1])
                    hrs_curso = col_h.number_input("Horas Totales", min_value=1, value=20)
                    fec_curso = col_f.date_input("Fecha de Finalización")
                    doc_curso = col_d.selectbox("Documento Recibido", ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"])
                    
                    if st.form_submit_button(":material/save: Guardar en Historial"):
                        if nom_curso and inst_curso:
                            nuevo_curso = CursoCapacitacion(
                                personal_id=emp_cur_sel.id,
                                nombre_curso=nom_curso,
                                institucion=inst_curso,
                                horas=hrs_curso,
                                fecha_termino=fec_curso,
                                tipo_documento=doc_curso
                            )
                            session.add(nuevo_curso)
                            session.commit()
                            st.success(f"Curso registrado para {emp_cur_sel.nombre}.")
                            time.sleep(1.2); st.rerun()
                        else:
                            st.error("Nombre e Institución son obligatorios.")
    
            # --- 3. EDITAR / ELIMINAR ---
            with sub_edit_del_cur:
                st.subheader("Modificar Registros")
                cursos_db = session.query(CursoCapacitacion).all()
                
                if cursos_db:
                    cur_mod = st.selectbox("Selecciona el registro a modificar:", 
                                           options=cursos_db, 
                                           format_func=lambda c: f"{c.nombre_curso} ({c.empleado.nombre})")
                    
                    with st.form("form_mod_curso"):
                        edit_nom = st.text_input("Nombre del Curso", value=cur_mod.nombre_curso)
                        edit_inst = st.text_input("Institución", value=cur_mod.institucion)
                        
                        c_h, c_f = st.columns(2)
                        edit_hrs = c_h.number_input("Horas", value=cur_mod.horas)
                        edit_fec = c_f.date_input("Fecha", value=cur_mod.fecha_termino)
                        
                        c_btn1, c_btn2 = st.columns(2)
                        if c_btn1.form_submit_button(":material/save: Actualizar"):
                            cur_mod.nombre_curso = edit_nom
                            cur_mod.institucion = edit_inst
                            cur_mod.horas = edit_hrs
                            cur_mod.fecha_termino = edit_fec
                            session.commit()
                            st.success("Registro actualizado."); time.sleep(1); st.rerun()
                            
                        if c_btn2.form_submit_button(":material/delete: Eliminar Registro"):
                            session.delete(cur_mod)
                            session.commit()
                            st.success("Registro eliminado."); time.sleep(1.2); st.rerun()
                else:
                    st.info("No hay cursos registrados para gestionar.")

# ==========================================
# SECCIÓN: PROGRAMAS EDUCATIVOS (usada dentro de Identidad)
# ==========================================
def render_programas_educativos():
    session.expire_all()
    
    personal_db = session.query(Personal).all()
    
    sub_catalog_carreras, sub_add_prog, sub_list_prog = st.tabs([
        ":material/auto_stories: Catálogo de Carreras",
        ":material/add: Asignar Programa",
        "📋 Consultar Programas",
    ])
        
    # --- 1. CONSULTAR PROGRAMAS ---
    with sub_list_prog:
        st.subheader("📋 Consultar Programas Educativos")
        st.write("Consulta qué programas tiene cada docente o qué docentes imparten en cada programa. Usa el buscador para filtrar por nombre, carrera, modalidad o institución.")
        st.markdown("---")
        sub_por_docente, sub_por_programa = st.tabs([":material/person: Por Docente", ":material/school: Por Programa"])
        
        with sub_por_docente:
            st.markdown("#### :material/person: Listado por docente")
            st.caption("Expande cada nombre para ver los programas adscritos. Usa **Eliminar** junto a una carrera para quitarla del expediente.")
            busqueda_prog = st.text_input(":material/search: Buscar por docente, carrera, modalidad o institución...", key="busq_docente")
            if busqueda_prog:
                term_lower = busqueda_prog.lower().strip()
                docentes_con_prog = [p for p in personal_db if p.programas_educativos and term_lower in (p.programas_educativos or "").lower()]
                docentes_por_nombre = [p for p in personal_db if (
                    term_lower in (p.nombre or "").lower() or
                    term_lower in (p.apellido_paterno or "").lower() or
                    term_lower in (p.apellido_materno or "").lower() or
                    term_lower in (p.correo_institucional or "").lower()
                )]
                resultados_prog = list(dict.fromkeys(docentes_con_prog + docentes_por_nombre))
            else:
                resultados_prog = [p for p in personal_db if p.programas_educativos and p.programas_educativos.strip()]
            
            if resultados_prog:
                st.markdown("---")
                for doc in resultados_prog:
                    nombre_full = f"{doc.titulo_abreviatura or ''} {doc.nombre} {doc.apellido_paterno} {doc.apellido_materno}".strip()
                    with st.expander(f":material/school: {nombre_full} — {doc.puesto.nombre}"):
                        programas_lista = [p.strip() for p in (doc.programas_educativos or "").split(",") if p.strip()]
                        if not programas_lista:
                            st.write("_Sin programas asignados._")
                        else:
                            st.write("**Programas adscritos:**")
                            for i, prog in enumerate(programas_lista):
                                col_prog, col_btn = st.columns([4, 1])
                                with col_prog:
                                    st.write(f":material/school: {prog}")
                                with col_btn:
                                    if st.button(":material/delete: Eliminar", key=f"consultar_del_{doc.id}_{i}", type="secondary"):
                                        restantes = [p for j, p in enumerate(programas_lista) if j != i]
                                        doc.programas_educativos = ", ".join(restantes) if restantes else None
                                        session.commit()
                                        st.success("Carrera quitada del expediente.")
                                        time.sleep(0.8)
                                        st.rerun()
            else:
                st.info("No se encontraron docentes con programas educativos. Usa la pestaña 'Asignar Programa' para registrar.")
        
        with sub_por_programa:
            st.markdown("#### :material/school: Listado por programa")
            st.caption("Expande cada carrera para ver los docentes que la tienen asignada.")
            busqueda_prog2 = st.text_input(":material/search: Buscar por programa o docente...", key="busq_programa")
            # Extraer programas y agrupar por programa -> [docentes]
            prog_a_docentes = {}
            for p in personal_db:
                if p.programas_educativos and p.programas_educativos.strip():
                    programas_str = [x.strip() for x in p.programas_educativos.split(",") if x.strip()]
                    for prog in programas_str:
                        if prog not in prog_a_docentes:
                            prog_a_docentes[prog] = []
                        prog_a_docentes[prog].append(p)
            # Filtrar por búsqueda si hay término
            if busqueda_prog2:
                term = busqueda_prog2.lower().strip()
                prog_a_docentes = {
                    prog: docentes for prog, docentes in prog_a_docentes.items()
                    if term in prog.lower() or any(
                        term in (d.nombre or "").lower() or term in (d.apellido_paterno or "").lower() or
                        term in (d.apellido_materno or "").lower() or term in (d.correo_institucional or "").lower()
                        for d in docentes
                    )
                }
            if prog_a_docentes:
                st.markdown("---")
                for prog in sorted(prog_a_docentes.keys()):
                    docentes = prog_a_docentes[prog]
                    with st.expander(f":material/school: {prog} — {len(docentes)} docente(s)"):
                        for doc in docentes:
                            nombre_full = f"{doc.titulo_abreviatura or ''} {doc.nombre} {doc.apellido_paterno} {doc.apellido_materno}".strip()
                            st.write(f"• **{nombre_full}** — {doc.puesto.nombre if doc.puesto else 'N/A'}")
                            st.caption(f"   {doc.correo_institucional or 'Sin correo'}")
            else:
                st.info("No se encontraron programas educativos. Usa la pestaña 'Asignar Programa' para registrar.")
    
    # --- 2. ASIGNAR PROGRAMA (desde catálogo) ---
    with sub_add_prog:
        st.subheader(":material/add: Asignar y desasignar programas")
        st.write("Asigna carreras del catálogo a los docentes o quita del expediente las que ya no correspondan.")
        st.markdown("---")
        carreras_db = session.query(Carrera).all()
        
        sub_asignar, sub_desasignar = st.tabs([":material/add: Asignar Carreras al Docente", ":material/delete: Desasignar Carrera"])
        
        with sub_asignar:
            st.markdown("#### :material/school: Asignar carreras al docente")
            if not personal_db:
                st.warning("No hay personal registrado. Ve a la pestaña 'Personal' para registrar al menos a un docente primero.")
            elif not carreras_db:
                st.warning("No hay carreras en el catálogo. Ve a la sub-pestaña 'Catálogo de Carreras' para registrar carreras primero.")
            else:
                st.caption("Selecciona un docente y una o varias carreras del catálogo para asignarlas a su expediente.")
                docentes_opts = {
                    p.id: f"{p.nombre} {p.apellido_paterno} {p.apellido_materno} - {p.correo_institucional}"
                    for p in personal_db
                }
                carreras_opts = {
                    c.id: f"{c.tipo_nivel} en {c.nombre} ({c.modalidad})"
                    for c in carreras_db
                }
                
                with st.form("form_asignar_programa", clear_on_submit=False):
                    docente_id = st.selectbox(
                        ":material/person: Selecciona el Docente*",
                        options=list(docentes_opts.keys()),
                        format_func=lambda pid: docentes_opts.get(pid, str(pid)),
                        key="prog_docente_id"
                    )
                    
                    carreras_ids = st.multiselect(
                        ":material/school: Selecciona una o varias carreras*",
                        options=list(carreras_opts.keys()),
                        format_func=lambda cid: carreras_opts.get(cid, str(cid)),
                        key="prog_carreras_ids"
                    )
                    
                    submit_prog = st.form_submit_button(":material/save: Asignar Carreras al Docente", use_container_width=True)
                    
                    if submit_prog:
                        if docente_id is not None and len(carreras_ids) > 0:
                            try:
                                try:
                                    docente_sel = session.get(Personal, docente_id)
                                except Exception:
                                    docente_sel = session.query(Personal).get(docente_id)
                                
                                carreras_por_id = {c.id: c for c in carreras_db}
                                carreras_sel = [carreras_por_id[cid] for cid in carreras_ids if cid in carreras_por_id]
                                if not docente_sel or not carreras_sel:
                                    st.error("Selección inválida. Vuelve a seleccionar el docente y las carreras.")
                                    st.stop()
                                
                                institucion = "TECNM - CAMPUS ESCÁRCEGA"
                                programas_str_nuevos = [f"{c.tipo_nivel} en {c.nombre} ({c.modalidad}) | {institucion}" for c in carreras_sel]
                                programas_actuales_str = docente_sel.programas_educativos or ""
                                ya_asignados = {p.strip() for p in programas_actuales_str.split(",") if p.strip()}
                                programas_a_agregar = [p for p in programas_str_nuevos if p not in ya_asignados]
                                omitidos = len(programas_str_nuevos) - len(programas_a_agregar)
                                
                                if not programas_a_agregar:
                                    st.warning("Todas las carreras seleccionadas ya estaban asignadas a este docente. No se duplican programas.")
                                    st.stop()
                                
                                if programas_actuales_str.strip() != "":
                                    docente_sel.programas_educativos = f"{programas_actuales_str}, " + ", ".join(programas_a_agregar)
                                else:
                                    docente_sel.programas_educativos = ", ".join(programas_a_agregar)
                                
                                session.commit()
                                msg = f"Se asignaron {len(programas_a_agregar)} carrera(s) a {docente_sel.nombre}."
                                if omitidos > 0:
                                    msg += f" ({omitidos} ya estaban asignadas y fueron omitidas)"
                                st.success(msg)
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")
                                session.rollback()
                        else:
                            st.error("Debes seleccionar un docente y al menos una carrera.")
        
        with sub_desasignar:
            st.markdown("#### :material/delete: Quitar carreras del expediente")
            docentes_con_prog = [p for p in personal_db if p.programas_educativos and (p.programas_educativos or "").strip()]
            if not docentes_con_prog:
                st.info("No hay docentes con programas asignados. Usa la pestaña 'Asignar Carreras al Docente' para asignar.")
            else:
                st.caption("Elige un docente y usa el botón **Eliminar** junto a cada carrera para quitarla del expediente.")
                docentes_des_opts = {
                    p.id: f"{p.nombre} {p.apellido_paterno} {p.apellido_materno} - {p.correo_institucional}"
                    for p in docentes_con_prog
                }
                docente_des_id = st.selectbox(
                    ":material/person: Selecciona el docente",
                    options=list(docentes_des_opts.keys()),
                    format_func=lambda pid: docentes_des_opts.get(pid, str(pid)),
                    key="desasignar_docente_id"
                )
                try:
                    docente_des = session.get(Personal, docente_des_id)
                except Exception:
                    docente_des = session.query(Personal).get(docente_des_id)
                
                if docente_des and docente_des.programas_educativos:
                    carreras_actuales = [c.strip() for c in docente_des.programas_educativos.split(",") if c.strip()]
                    if not carreras_actuales:
                        st.info("Este docente no tiene carreras asignadas.")
                    else:
                        nombre_doc = f"{docente_des.nombre} {docente_des.apellido_paterno} {docente_des.apellido_materno}".strip()
                        st.markdown("---")
                        st.markdown("**📋 Carreras asignadas:** haz clic en **Eliminar** para quitar una del expediente.")
                        for i, car in enumerate(carreras_actuales):
                            col_texto, col_btn = st.columns([4, 1])
                            with col_texto:
                                st.write(f":material/school: {car}")
                            with col_btn:
                                if st.button(":material/delete: Eliminar", key=f"del_prog_{docente_des_id}_{i}", type="secondary"):
                                    restantes = [c for j, c in enumerate(carreras_actuales) if j != i]
                                    docente_des.programas_educativos = ", ".join(restantes) if restantes else None
                                    session.commit()
                                    st.success(f"Carrera quitada del expediente de {nombre_doc}.")
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.info("Este docente no tiene programas asignados.")
    
    # --- 3. CATÁLOGO DE CARRERAS ---
    with sub_catalog_carreras:
        st.subheader(":material/auto_stories: Registro de Carreras y Características")
        st.write("Captura las carreras ofertadas con sus características, enlace a material y logo. Registra nuevas carreras o edita las existentes.")
        st.markdown("---")
        sub_registro_carrera, sub_editar_carrera = st.tabs([":material/add: Registro de Carrera", ":material/edit: Editar Carrera"])
        
        with sub_registro_carrera:
            st.markdown("#### :material/school: Datos de la Carrera")
            with st.form("form_catalogo_carrera", clear_on_submit=True):
                
                c_tipo, c_nombre = st.columns([1, 2])
                with c_tipo:
                    tipo_nivel = st.selectbox("Tipo de Grado*", ["Licenciatura", "Ingeniería"])
                with c_nombre:
                    nombre_carrera = st.text_input("Nombre de la Carrera*", placeholder="Ej. Sistemas Computacionales, Turismo, Administración")
                
                modalidad_carrera = st.selectbox("Modalidad*", ["Escolarizado", "En línea"])
                
                link_material = st.text_input("🔗 Link de la página con material de la carrera", placeholder="https://...")
                
                st.markdown("#### :material/image: Logo de la Carrera")
                logo_carrera = st.file_uploader("Sube el logo (PNG, JPG)", type=["png", "jpg", "jpeg"])
                if logo_carrera:
                    st.image(logo_carrera, caption="Vista previa del logo", width=120)
                
                st.markdown("---")
                submit_carrera = st.form_submit_button(":material/save: Guardar Carrera en Catálogo", use_container_width=True)
                
                if submit_carrera:
                    if nombre_carrera:
                        try:
                            ruta_logo = None
                            if logo_carrera:
                                ext = os.path.splitext(logo_carrera.name)[1] if logo_carrera.name else ".png"
                                if ext.lower() not in (".jpg", ".jpeg", ".png"):
                                    ext = ".png"
                                ruta_logo = os.path.join("logos_carreras", f"carrera_{int(time.time()*1000)}{ext}")
                                with open(ruta_logo, "wb") as f:
                                    f.write(logo_carrera.getvalue())
                            
                            nueva_carrera = Carrera(
                                tipo_nivel=tipo_nivel,
                                nombre=nombre_carrera.strip(),
                                modalidad=modalidad_carrera,
                                link_material=link_material.strip() if link_material and link_material.strip() else None,
                                logo=ruta_logo
                            )
                            session.add(nueva_carrera)
                            session.commit()
                            st.success(f"Carrera '{nombre_carrera}' registrada en el catálogo.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                            session.rollback()
                    else:
                        st.error("El nombre de la carrera es obligatorio.")
        
        with sub_editar_carrera:
            st.markdown("#### :material/edit: Editar carrera existente")
            st.caption("Selecciona una carrera del catálogo y actualiza sus datos o logo.")
            carreras_db_edit = session.query(Carrera).all()
            if not carreras_db_edit:
                st.info("No hay carreras en el catálogo. Registra una en la pestaña 'Registro de Carrera'.")
            else:
                opts_carreras = {c.id: f"{c.tipo_nivel} en {c.nombre} ({c.modalidad})" for c in carreras_db_edit}
                carrera_id = st.selectbox(
                    "Selecciona la carrera a editar:",
                    options=list(opts_carreras.keys()),
                    format_func=lambda cid: opts_carreras.get(cid, str(cid)),
                    key="select_carrera_editar"
                )
                try:
                    carrera_sel = session.get(Carrera, carrera_id)
                except Exception:
                    carrera_sel = session.query(Carrera).get(carrera_id)
                if carrera_sel:
                    with st.form("form_editar_carrera", clear_on_submit=False):
                        st.markdown("#### :material/school: Datos de la Carrera")
                        opciones_tipo = ["Licenciatura", "Ingeniería"]
                        opciones_modalidad = ["Escolarizado", "En línea"]
                        idx_tipo = opciones_tipo.index(carrera_sel.tipo_nivel) if carrera_sel.tipo_nivel in opciones_tipo else 0
                        idx_modalidad = opciones_modalidad.index(carrera_sel.modalidad) if carrera_sel.modalidad in opciones_modalidad else 0
                        
                        c_tipo_e, c_nombre_e = st.columns([1, 2])
                        with c_tipo_e:
                            tipo_edit = st.selectbox("Tipo de Grado*", opciones_tipo, index=idx_tipo)
                        with c_nombre_e:
                            nombre_edit = st.text_input("Nombre de la Carrera*", value=carrera_sel.nombre or "", placeholder="Ej. Sistemas Computacionales")
                        
                        modalidad_edit = st.selectbox("Modalidad*", opciones_modalidad, index=idx_modalidad)
                        link_edit = st.text_input("🔗 Link de la página con material", value=carrera_sel.link_material or "", placeholder="https://...")
                        
                        st.markdown("#### :material/image: Logo de la Carrera")
                        if carrera_sel.logo and os.path.exists(carrera_sel.logo):
                            st.image(carrera_sel.logo, caption="Logo actual", width=120)
                        logo_edit = st.file_uploader("Sube un nuevo logo (opcional; si no subes, se mantiene el actual)", type=["png", "jpg", "jpeg"], key="logo_editar_carrera")
                        if logo_edit:
                            st.image(logo_edit, caption="Nuevo logo", width=120)
                        
                        st.markdown("---")
                        if st.form_submit_button(":material/save: Guardar Cambios"):
                            if nombre_edit and nombre_edit.strip():
                                try:
                                    carrera_sel.tipo_nivel = tipo_edit
                                    carrera_sel.nombre = nombre_edit.strip()
                                    carrera_sel.modalidad = modalidad_edit
                                    carrera_sel.link_material = link_edit.strip() if link_edit and link_edit.strip() else None
                                    if logo_edit:
                                        ext = os.path.splitext(logo_edit.name)[1] if logo_edit.name else ".png"
                                        if ext.lower() not in (".jpg", ".jpeg", ".png"):
                                            ext = ".png"
                                        ruta_nueva = os.path.join("logos_carreras", f"carrera_edit_{carrera_sel.id}_{int(time.time()*1000)}{ext}")
                                        with open(ruta_nueva, "wb") as f:
                                            f.write(logo_edit.getvalue())
                                        carrera_sel.logo = ruta_nueva
                                    session.commit()
                                    st.success("Carrera actualizada correctamente.")
                                    time.sleep(1.2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al guardar: {e}")
                                    session.rollback()
                            else:
                                st.error("El nombre de la carrera es obligatorio.")
        
        # Listado de carreras registradas
        st.markdown("---")
        st.markdown("#### 📋 Carreras en el Catálogo")
        carreras_db = session.query(Carrera).all()
        if carreras_db:
            for car in carreras_db:
                col_logo, col_info = st.columns([1, 4])
                with col_logo:
                    if car.logo and os.path.exists(car.logo):
                        st.image(car.logo, width=80)
                    else:
                        st.caption("Sin logo")
                with col_info:
                    st.write(f"**{car.tipo_nivel} en {car.nombre}** — {car.modalidad}")
                    if car.link_material:
                        st.markdown(f"🔗 [Ver material]({car.link_material})")
        else:
            st.info("Aún no hay carreras registradas en el catálogo.")
    
# ==========================================
# SECCIÓN: USUARIOS (usada dentro de Configuración)
# ==========================================
def render_usuarios():
    st.header(":material/lock: Gestión de Usuarios del Sistema")
    session.expire_all()
    usuarios_lista = session.query(UsuarioSistema).all()
    personal_lista = session.query(Personal).all()
    st.write("Administra usuarios de acceso al sistema. Solo usuarios con rol **Súper Admin** pueden gestionar esta sección.")
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        st.subheader("Registrar nuevo usuario")
        nuevo_usuario = st.text_input("Usuario (login)")
        nueva_pass = st.text_input("Contraseña", type="password")
        nuevo_rol = st.selectbox("Rol", ["Súper Admin", "RRHH", "Desarrollo Académico", "Empleado"])
        personal_sel = st.selectbox("Vincular con Personal (opcional)", options=[None] + [p.id for p in personal_lista],
            format_func=lambda x: "-- Sin vincular --" if x is None else next((f"{p.nombre} {p.apellido_paterno}" for p in personal_lista if p.id == x), str(x)),
            key="sel_personal_usuario")
        if st.form_submit_button("Crear usuario"):
            if nuevo_usuario and nueva_pass:
                if session.query(UsuarioSistema).filter(UsuarioSistema.usuario == nuevo_usuario.strip()).first():
                    st.error("El usuario ya existe.")
                else:
                    u_nuevo = UsuarioSistema(usuario=nuevo_usuario.strip(), password=_hash_password(nueva_pass), rol=nuevo_rol, personal_id=personal_sel)
                    session.add(u_nuevo)
                    session.commit()
                    st.success("Usuario creado.")
                    st.rerun()
            else:
                st.error("Usuario y contraseña son obligatorios.")
    
    st.markdown("---")
    st.subheader(":material/group: Usuarios registrados")
    busqueda_usr = st.text_input(":material/search: Buscar usuario", placeholder="Buscar por nombre de usuario, rol o persona vinculada...", key="usuarios_busqueda")
    term_usr = (busqueda_usr or "").strip().lower()
    if term_usr:
        usuarios_filtrados = []
        for u in usuarios_lista:
            p = session.get(Personal, u.personal_id) if u.personal_id else None
            nom_pers = f"{p.nombre or ''} {p.apellido_paterno or ''}".strip() if p else ""
            if term_usr in (u.usuario or "").lower() or term_usr in (u.rol or "").lower() or term_usr in nom_pers.lower():
                usuarios_filtrados.append(u)
    else:
        usuarios_filtrados = usuarios_lista
    if usuarios_filtrados:
        for u in usuarios_filtrados:
            nom_pers = ""
            if u.personal_id:
                p = session.get(Personal, u.personal_id)
                nom_pers = f" — {p.nombre} {p.apellido_paterno}" if p else ""

            col_info, col_edit, col_reset, col_del = st.columns([6, 2, 2, 2])
            with col_info:
                st.markdown(f"**{u.usuario}** · {u.rol}{nom_pers}")
            with col_edit:
                if st.button(":material/edit: Editar", key=f"edit_rol_{u.id}", use_container_width=True):
                    st.session_state["usuario_edit_rol_id"] = u.id
            with col_reset:
                if st.button(":material/key: Código", key=f"gen_reset_{u.id}", use_container_width=True):
                    for t in session.query(TokenRestablecimiento).filter(TokenRestablecimiento.usuario_id == u.id).all():
                        session.delete(t)
                    cod = _generar_token_restablecimiento()
                    session.add(TokenRestablecimiento(usuario_id=u.id, token=cod, expira_en=datetime.now() + timedelta(minutes=15)))
                    session.commit()
                    st.session_state[f"codigo_mostrado_{u.id}"] = cod
                    st.rerun()
            with col_del:
                if st.button(":material/delete: Eliminar", key=f"del_usuario_{u.id}", use_container_width=True):
                    session.delete(u)
                    session.commit()
                    st.success(f"Usuario '{u.usuario}' eliminado. El perfil de empleado vinculado no fue modificado.")
                    time.sleep(0.5)
                    st.rerun()
            if st.session_state.get(f"codigo_mostrado_{u.id}"):
                st.info(f"Código para **{u.usuario}** (15 min): **{st.session_state[f'codigo_mostrado_{u.id}']}**. Comunícale al usuario para que lo use en '¿Olvidaste tu contraseña?'")
                if st.button(":material/close: Cerrar", key=f"cerrar_cod_{u.id}"):
                    del st.session_state[f"codigo_mostrado_{u.id}"]
                    st.rerun()
            if st.session_state.get("usuario_edit_rol_id") == u.id:
                with st.container(border=True):
                    st.caption("Editar usuario")
                    nuevo_usuario_edit = st.text_input("Nombre de usuario (login)", value=u.usuario or "", key=f"edit_usuario_{u.id}")
                    nueva_pass_edit = st.text_input("Nueva contraseña (dejar vacío para no cambiar)", type="password", placeholder="••••••••", key=f"edit_pass_{u.id}")
                    roles_opc = ["Súper Admin", "RRHH", "Desarrollo Académico", "Empleado"]
                    idx_actual = roles_opc.index(u.rol) if u.rol in roles_opc else 0
                    nuevo_rol = st.selectbox("Rol", roles_opc, index=idx_actual, key=f"sel_rol_{u.id}")
                    opts_vinculo = [None] + [p.id for p in personal_lista]
                    try:
                        idx_vin = opts_vinculo.index(u.personal_id)
                    except (ValueError, TypeError):
                        idx_vin = 0
                    vincular_pers = st.selectbox("Vincular con Personal", options=opts_vinculo,
                        format_func=lambda x: "-- Sin vincular --" if x is None else next((f"{p.nombre} {p.apellido_paterno}" for p in personal_lista if p.id == x), str(x)),
                        index=idx_vin,
                        key=f"sel_vinculacion_{u.id}")
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.button(":material/save: Guardar cambios", key=f"guardar_rol_{u.id}"):
                        usr_trim = (nuevo_usuario_edit or "").strip()
                        if not usr_trim:
                            st.error("El nombre de usuario es obligatorio.")
                        else:
                            otro = session.query(UsuarioSistema).filter(UsuarioSistema.usuario == usr_trim, UsuarioSistema.id != u.id).first()
                            if otro:
                                st.error(f"El usuario '{usr_trim}' ya existe en otro registro.")
                            else:
                                u.usuario = usr_trim
                                u.rol = nuevo_rol
                                u.personal_id = vincular_pers
                                if nueva_pass_edit and nueva_pass_edit.strip():
                                    u.password = _hash_password(nueva_pass_edit.strip())
                                session.commit()
                                st.session_state.pop("usuario_edit_rol_id", None)
                                st.success("Usuario actualizado correctamente.")
                                time.sleep(0.8)
                                st.rerun()
                    if c_b2.button(":material/close: Cancelar", key=f"cancelar_rol_{u.id}"):
                        st.session_state.pop("usuario_edit_rol_id", None)
                        st.rerun()
    else:
        st.info("No hay usuarios registrados o no hay coincidencias con la búsqueda.")
    
# ==========================================
# PESTAÑA: IDENTIDAD (PARÁMETROS GLOBALES)
# ==========================================
ID_IDENTIDAD = 1
CARPETA_IDENTIDAD = "identidad_assets"

if (":material/badge: Identidad" in tab_dict) or ("Identidad" in tab_dict):
    with tab_dict.get(":material/badge: Identidad", tab_dict.get("Identidad")):
        tab_ident_institucional, tab_edificios, tab_unidades_puestos, tab_programas = st.tabs([
            ":material/badge: Identidad Institucional",
            ":material/apartment: Edificios",
            ":material/business: Unidades y Puestos",
            ":material/menu_book: Programas Educativos",
        ])

        with tab_ident_institucional:
            st.write("Centraliza el nombre, logos, colores y datos de contacto. Un solo lugar para actualizar reportes, PDFs y pantallas.")
            session.expire_all()

            # Carpeta para guardar logos/sellos
            if not os.path.exists(CARPETA_IDENTIDAD):
                os.makedirs(CARPETA_IDENTIDAD)
        
            # Cargar registro existente (singleton id=1)
            identidad = session.query(IdentidadInstitucional).get(ID_IDENTIDAD)
        
            with st.form("form_identidad", clear_on_submit=False):
                st.markdown("#### :material/badge: Bloque 1: Identificación Oficial y Legal")
                nombre_oficial = st.text_input("Nombre Oficial Completo", value=(identidad.nombre_oficial or "") if identidad else "", placeholder="Ej. Instituto Tecnológico Superior de Escárcega")
                acronimo = st.text_input("Acrónimo / Siglas", value=(identidad.acronimo or "") if identidad else "", placeholder="Ej. ITSE o TECNM Campus Escárcega")
                cct = st.text_input("Clave de Centro de Trabajo (CCT)", value=(identidad.cct or "") if identidad else "", placeholder="Fundamental para trámites oficiales")
                rfc = st.text_input("RFC de la Institución", value=(identidad.rfc or "") if identidad else "", placeholder="Útil para viáticos o presupuestos")
                submit_bloque1 = st.form_submit_button(":material/save: Guardar Bloque 1")
        
            st.markdown("---")
            with st.form("form_bloque2", clear_on_submit=False):
                st.markdown("#### :material/palette: Bloque 2: Elementos Gráficos y Visuales")
                col_hex, _ = st.columns([1, 2])
                with col_hex:
                    color_hex = st.text_input("Colores Institucionales (HEX)", value=(identidad.color_institucional or "#1b5e20") if identidad else "#1b5e20", placeholder="#1b5e20")
            
                logo_principal_file = st.file_uploader("Logo Principal (interfaz)", type=["png", "jpg", "jpeg"], key="logo_principal")
                if identidad and identidad.logo_principal and os.path.exists(identidad.logo_principal):
                    st.image(identidad.logo_principal, caption="Logo actual", width=120)
                if logo_principal_file:
                    st.image(logo_principal_file, caption="Nueva imagen", width=120)
            
                logo_secundario_file = st.file_uploader("Logo Secundario / Dependencia (TECNM, SEP, etc.)", type=["png", "jpg", "jpeg"], key="logo_secundario")
                if identidad and identidad.logo_secundario and os.path.exists(identidad.logo_secundario):
                    st.image(identidad.logo_secundario, caption="Logo secundario actual", width=120)
                if logo_secundario_file:
                    st.image(logo_secundario_file, caption="Nueva imagen", width=120)
            
                sello_file = st.file_uploader("Sello o Marca de Agua (fondo de constancias)", type=["png", "jpg", "jpeg"], key="sello_agua")
                if identidad and identidad.sello_marca_agua and os.path.exists(identidad.sello_marca_agua):
                    st.image(identidad.sello_marca_agua, caption="Sello actual", width=120)
                if sello_file:
                    st.image(sello_file, caption="Nueva imagen", width=120)
            
                submit_bloque2 = st.form_submit_button(":material/save: Guardar Bloque 2")
        
            st.markdown("---")
            with st.form("form_bloque3", clear_on_submit=False):
                st.markdown("#### :material/menu_book: Bloque 3: Filosofía y Contacto Institucional")
                lema = st.text_input("Lema Institucional", value=(identidad.lema or "") if identidad else "", placeholder='Ej. "Excelencia en Educación Tecnológica"')
                direccion_oficial = st.text_area("Dirección Oficial Completa", value=(identidad.direccion_oficial or "") if identidad else "", placeholder="Calle, número, colonia, CP, municipio")
                telefono_oficial = st.text_input("Teléfono Oficial (Conmutador)", value=(identidad.telefono_oficial or "") if identidad else "")
                correo_contacto = st.text_input("Correo Electrónico de Contacto", value=(identidad.correo_contacto or "") if identidad else "", placeholder="Ej. contacto@itescam.edu.mx")
                pagina_web = st.text_input("Página Web Oficial", value=(identidad.pagina_web or "") if identidad else "", placeholder="https://...")
            
                submit_bloque3 = st.form_submit_button(":material/save: Guardar Bloque 3")
            if submit_bloque1:
                try:
                    if identidad:
                        identidad.nombre_oficial = nombre_oficial.strip() or None
                        identidad.acronimo = acronimo.strip() or None
                        identidad.cct = cct.strip() or None
                        identidad.rfc = rfc.strip() or None
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 1 actualizado")
                        st.success("Bloque 1 actualizado correctamente.")
                    else:
                        nueva = IdentidadInstitucional(
                            id=ID_IDENTIDAD,
                            nombre_oficial=nombre_oficial.strip() or None,
                            acronimo=acronimo.strip() or None,
                            cct=cct.strip() or None,
                            rfc=rfc.strip() or None,
                            logo_principal=None, logo_secundario=None, sello_marca_agua=None,
                            color_institucional=None, lema=None, direccion_oficial=None,
                            telefono_oficial=None, correo_contacto=None, pagina_web=None
                        )
                        session.add(nueva)
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 1 guardado (nuevo)")
                        st.success("Bloque 1 guardado correctamente.")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar Bloque 1: {e}")
                    session.rollback()
        
            if submit_bloque2:
                try:
                    def _guardar_archivo(uploader, prefijo):
                        if not uploader:
                            return None
                        ext = os.path.splitext(uploader.name)[1] if uploader.name else ".png"
                        if ext.lower() not in (".jpg", ".jpeg", ".png"):
                            ext = ".png"
                        ruta = os.path.join(CARPETA_IDENTIDAD, f"{prefijo}_{int(time.time()*1000)}{ext}")
                        with open(ruta, "wb") as f:
                            f.write(uploader.getvalue())
                        return ruta
                    logo_principal_ruta = _guardar_archivo(logo_principal_file, "logo_principal") if logo_principal_file else (identidad.logo_principal if identidad else None)
                    logo_secundario_ruta = _guardar_archivo(logo_secundario_file, "logo_secundario") if logo_secundario_file else (identidad.logo_secundario if identidad else None)
                    sello_ruta = _guardar_archivo(sello_file, "sello") if sello_file else (identidad.sello_marca_agua if identidad else None)
                    if identidad:
                        identidad.color_institucional = color_hex.strip() or None
                        identidad.logo_principal = logo_principal_ruta
                        identidad.logo_secundario = logo_secundario_ruta
                        identidad.sello_marca_agua = sello_ruta
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 2 actualizado")
                        st.success("Bloque 2 actualizado correctamente.")
                    else:
                        nueva = IdentidadInstitucional(
                            id=ID_IDENTIDAD,
                            nombre_oficial=None, acronimo=None, cct=None, rfc=None,
                            logo_principal=logo_principal_ruta, logo_secundario=logo_secundario_ruta, sello_marca_agua=sello_ruta,
                            color_institucional=color_hex.strip() or None,
                            lema=None, direccion_oficial=None, telefono_oficial=None, correo_contacto=None, pagina_web=None
                        )
                        session.add(nueva)
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 2 guardado (nuevo)")
                        st.success("Bloque 2 guardado correctamente.")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar Bloque 2: {e}")
                    session.rollback()

            if submit_bloque3:
                try:
                    if identidad:
                        identidad.lema = lema.strip() or None
                        identidad.direccion_oficial = direccion_oficial.strip() or None
                        identidad.telefono_oficial = telefono_oficial.strip() or None
                        identidad.correo_contacto = correo_contacto.strip() or None
                        identidad.pagina_web = pagina_web.strip() or None
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 3 actualizado")
                        st.success("Bloque 3 actualizado correctamente.")
                    else:
                        nueva = IdentidadInstitucional(
                            id=ID_IDENTIDAD,
                            nombre_oficial=None, acronimo=None, cct=None, rfc=None,
                            logo_principal=None, logo_secundario=None, sello_marca_agua=None,
                            color_institucional=None,
                            lema=lema.strip() or None,
                            direccion_oficial=direccion_oficial.strip() or None,
                            telefono_oficial=telefono_oficial.strip() or None,
                            correo_contacto=correo_contacto.strip() or None,
                            pagina_web=pagina_web.strip() or None
                        )
                        session.add(nueva)
                        session.commit()
                        registrar_bitacora(session, "EDITAR", "Identidad", "Bloque 3 guardado (nuevo)")
                        st.success("Bloque 3 guardado correctamente.")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar Bloque 3: {e}")
                    session.rollback()

            # Dominios de correo institucional (debajo de Bloques 1, 2 y 3)
            st.markdown("---")
            st.markdown("#### :material/mail: Dominios de correo institucional")
            st.caption("Configura los dominios que aparecerán en Correo Institucional. El usuario solo escribe la parte antes de @.")
            dominios_idt = session.query(DominioCorreo).order_by(DominioCorreo.dominio).all()
            if dominios_idt:
                st.caption("Dominios registrados:")
                editing_id = st.session_state.get("editing_dom_idt")
                for d in dominios_idt:
                    if editing_id == d.id:
                        with st.form(f"form_edit_dom_idt_{d.id}"):
                            nuevo_valor = st.text_input("Corregir dominio", value=d.dominio, key=f"edit_dom_val_{d.id}")
                            ce1, ce2 = st.columns(2)
                            with ce1:
                                if st.form_submit_button(":material/check: Guardar"):
                                    dom = (nuevo_valor or "").strip().lower().replace("@", "")
                                    if dom:
                                        otro = session.query(DominioCorreo).filter(DominioCorreo.dominio == dom, DominioCorreo.id != d.id).first()
                                        if otro:
                                            st.error("Ese dominio ya está registrado.")
                                        else:
                                            d.dominio = dom
                                            session.commit()
                                            del st.session_state["editing_dom_idt"]
                                            st.success("Dominio actualizado.")
                                            time.sleep(0.5)
                                            st.rerun()
                                    else:
                                        st.error("Escribe un dominio válido.")
                            with ce2:
                                if st.form_submit_button(":material/close: Cancelar"):
                                    del st.session_state["editing_dom_idt"]
                                    st.rerun()
                    else:
                        c1, c2, c3 = st.columns([2, 1, 1])
                        c1.write(f"@{d.dominio}")
                        if c2.button(":material/edit: Editar", key=f"edit_dom_idt_{d.id}"):
                            st.session_state["editing_dom_idt"] = d.id
                            st.rerun()
                        if c3.button(":material/delete: Eliminar", key=f"del_dom_idt_{d.id}"):
                            session.delete(d)
                            session.commit()
                            st.success("Dominio eliminado.")
                            time.sleep(0.8)
                            st.rerun()
            with st.form("form_dominio_identidad"):
                nuevo_dom = st.text_input("Nuevo dominio (ej. itscarcega.edu.mx)", placeholder="itscarcega.edu.mx", key="nuevo_dom_idt")
                if st.form_submit_button(":material/add: Añadir dominio"):
                    dom = (nuevo_dom or "").strip().lower().replace("@", "")
                    if dom:
                        if session.query(DominioCorreo).filter_by(dominio=dom).first():
                            st.error("Ese dominio ya está registrado.")
                        else:
                            session.add(DominioCorreo(dominio=dom))
                            session.commit()
                            st.success("Dominio añadido.")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("Escribe un dominio.")

        with tab_unidades_puestos:
            render_unidades_y_puestos()

        with tab_edificios:
            render_infraestructura_y_espacios()

        with tab_programas:
            render_programas_educativos()

# ==========================================
# PESTAÑA: CV Y EXPEDIENTE INTEGRAL
# ==========================================
if (":material/description: CV" in tab_dict) or ("CV" in tab_dict):
    with tab_dict.get(":material/description: CV", tab_dict.get("CV")):
        st.tabs([":material/description: CV y Expediente Integral"])
        session.expire_all()
        personal_cv = session.query(Personal).all()
        dominios_cv = session.query(DominioCorreo).order_by(DominioCorreo.dominio).all()
        if not personal_cv:
            st.info("No hay personal registrado. Ve a la pestaña 'Personal' para dar de alta.")
        else:
            rol_cv = st.session_state.rol or ""
            personal_id_cv = st.session_state.personal_id
            
            # Si es Empleado, cargar automáticamente su expediente (sin búsqueda ni selectbox)
            if rol_cv == "Empleado":
                if personal_id_cv:
                    persona = session.get(Personal, personal_id_cv)
                    persona_id = personal_id_cv
                else:
                    persona = None
                    persona_id = None
                    st.info("Tu expediente no está vinculado a tu usuario. Contacta al administrador.")
            else:
                opts_personal = {p.id: f"{p.nombre} {p.apellido_paterno} {p.apellido_materno} - {p.correo_institucional or 'Sin correo'}" for p in personal_cv}
                busqueda_cv = st.text_input(":material/search: Buscar persona", placeholder="Escribe nombre, apellido o correo para filtrar...", key="cv_busqueda")
                term_cv = (busqueda_cv or "").strip().lower()
                if term_cv:
                    filtrados = sorted([
                        p for p in personal_cv
                        if term_cv in (p.nombre or "").lower() or term_cv in (p.apellido_paterno or "").lower()
                        or term_cv in (p.apellido_materno or "").lower() or term_cv in (p.correo_institucional or "").lower()
                        or term_cv in (p.correo_personal or "").lower()
                    ], key=lambda x: f"{(x.apellido_paterno or '')} {(x.apellido_materno or '')} {(x.nombre or '')}".strip())
                else:
                    filtrados = sorted(personal_cv, key=lambda x: f"{(x.apellido_paterno or '')} {(x.apellido_materno or '')} {(x.nombre or '')}".strip())
                opts_filtrados = {p.id: opts_personal[p.id] for p in filtrados[:150]}
                if not opts_filtrados:
                    st.warning("No se encontraron coincidencias. Intenta con otro término o borra la búsqueda.")
                    persona_id = None
                else:
                    persona_id = st.selectbox("Selecciona a la persona", options=list(opts_filtrados.keys()),
                        format_func=lambda pid: opts_filtrados.get(pid, str(pid)), key="cv_select_persona")
                persona = None
                if persona_id:
                    try:
                        persona = session.get(Personal, persona_id)
                    except Exception:
                        persona = session.query(Personal).get(persona_id)
            if persona:
                nombre_full = f"{persona.titulo_abreviatura or ''} {persona.nombre or ''} {persona.apellido_paterno or ''} {persona.apellido_materno or ''}".strip()
                puesto_nom = persona.puesto.nombre if persona.puesto else "N/A"
                def _v(x): return x if x else "—"
                def _f(d): return d.strftime('%d/%m/%Y') if d else "—"
                # Generar QR para incrustar en HTML si hay correo
                qr_b64 = ""
                if persona.correo_institucional:
                    vcard = _generar_vcard_docente(persona)
                    qr_img = _generar_qr_vcard(vcard)
                    qr_b64 = base64.b64encode(qr_img.getvalue()).decode()
                foto_src = ""
                if persona.fotografia and os.path.exists(persona.fotografia):
                    with open(persona.fotografia, "rb") as f:
                        foto_b64 = base64.b64encode(f.read()).decode()
                        ext = os.path.splitext(persona.fotografia)[1].lower()
                        mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                        foto_src = f"data:{mime};base64,{foto_b64}"
                # Todos ven el CV completo; Empleado solo puede editar datos personales y contacto
                seccion_formacion = f"""
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-graduation-cap fa-icon"></i> Formación Académica</div>
                                <div class="cv-item"><strong>Título:</strong> {_v(persona.titulo_abreviatura)}</div>
                                <div class="cv-item"><strong>Licenciatura:</strong> {_v(persona.licenciatura)}</div>
                                <div class="cv-item"><strong>Maestría:</strong> {_v(persona.maestria)}</div>
                                <div class="cv-item"><strong>Doctorado:</strong> {_v(persona.doctorado)}</div>
                            </div>
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-graduation-cap fa-icon"></i> Programas Educativos</div>
                                <div class="cv-prog">{"• " + "<br/>• ".join(x.strip() for x in (persona.programas_educativos or "").split(",") if x.strip()) if persona.programas_educativos and persona.programas_educativos.strip() else "—"}</div>
                            </div>
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-book fa-icon"></i> Producción Académica</div>
                                <div class="cv-prog">{"<br/>".join(f"• <strong>{p.tipo}:</strong> {p.titulo or ''}" + (f" — {p.titulo_capitulo}" if p.titulo_capitulo else "") + f" ({_f(p.fecha)})" + (f" | {p.identificador or ''}" if p.identificador else "") for p in (persona.producciones or [])) if persona.producciones else "—"}</div>
                            </div>
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-screwdriver-wrench fa-icon"></i> Capacitación</div>
                                <div class="cv-prog">{"<br/>".join(f"• {c.nombre_curso or ''} — {c.institucion or ''} ({c.horas or 0} hrs, {_f(c.fecha_termino)})" for c in (persona.cursos or [])) if persona.cursos else "—"}</div>
                            </div>"""
                seccion_datos_laborales = f"""
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-briefcase fa-icon"></i> Datos Laborales</div>
                                <div class="cv-item"><strong>Ubicación:</strong> Edif. {_v(persona.edificio)}, Planta {_v(persona.planta)}</div>
                                <div class="cv-item"><strong>Área:</strong> {_v(persona.area_asignada)}</div>
                                <div class="cv-item"><strong>Ingreso:</strong> {_f(persona.fecha_ingreso)}</div>
                                <div class="cv-item"><strong>Contrato:</strong> {_v(persona.tipo_contrato)} · {_v(persona.jornada_laboral)}</div>
                            </div>"""
                # Color de encabezado del CV según preferencia (hex en cv_color_header)
                base_color = st.session_state.get("cv_color_header", "#0b3c5d")
                grad_ini = base_color
                grad_fin = base_color
                titulo_color = base_color

                cv_html = f"""
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
                <style>
                    .cv-wrapper {{ max-width: 900px; margin: 0 auto; font-family: 'Segoe UI', system-ui, sans-serif; box-shadow: 0 4px 20px rgba(0,0,0,0.12); border-radius: 12px; overflow: hidden; background: #fff; }}
                    .cv-header {{ background: linear-gradient(135deg, {grad_ini} 0%, {grad_fin} 100%); color: white; padding: 2rem 2.5rem; display: flex; align-items: center; gap: 2rem; }}
                    .cv-foto-wrap {{ width: 120px; height: 120px; border-radius: 50%; overflow: hidden; border: 4px solid rgba(255,255,255,0.5); flex-shrink: 0; display: flex; align-items: center; justify-content: center; }}
                    .cv-foto {{ width: 100%; height: 100%; object-fit: cover; object-position: center; display: block; }}
                    .cv-foto-placeholder {{ width: 120px; height: 120px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 3rem; flex-shrink: 0; }}
                    .cv-header-text {{ flex: 1; }}
                    .cv-name {{ font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; margin: 0 0 0.3rem 0; }}
                    .cv-puesto {{ font-size: 1.1rem; opacity: 0.95; font-weight: 500; margin: 0; }}
                    .cv-contact-line {{ font-size: 0.9rem; margin-top: 0.6rem; opacity: 0.9; }}
                    .cv-qr {{ width: 130px; height: 130px; border-radius: 8px; background: white; padding: 4px; flex-shrink: 0; object-fit: contain; }}
                    .cv-body {{ padding: 2rem 2.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
                    .cv-section {{ margin-bottom: 1.5rem; }}
                    .cv-section-title {{ font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: {titulo_color}; margin-bottom: 0.6rem; padding-bottom: 0.3rem; border-bottom: 2px solid {titulo_color}; }}
                    .cv-item {{ font-size: 0.9rem; margin-bottom: 0.35rem; line-height: 1.5; color: #333; }}
                    .cv-item strong {{ color: #1a1a1a; font-weight: 600; }}
                    .cv-prog {{ font-size: 0.85rem; color: #444; line-height: 1.6; }}
                </style>
                <div class="cv-wrapper">
                    <div class="cv-header">
                        {"<div class='cv-foto-wrap'><img class='cv-foto' src='" + foto_src + "' alt='Foto'/></div>" if foto_src else "<div class='cv-foto-placeholder'><i class='fa-solid fa-user fa-2x'></i></div>"}
                        <div class="cv-header-text">
                            <h1 class="cv-name">{nombre_full}</h1>
                            <p class="cv-puesto">{puesto_nom}</p>
                            <p class="cv-contact-line"><i class='fa-solid fa-envelope fa-icon'></i> {_v(persona.correo_institucional)} &nbsp;|&nbsp; <i class='fa-solid fa-mobile-screen fa-icon'></i> {_v(persona.celular_personal)} &nbsp;|&nbsp; <i class='fa-solid fa-building fa-icon'></i> Ext. {_v(persona.extension)}</p>
                        </div>
                        {"<img class='cv-qr' src='data:image/png;base64," + qr_b64 + "' alt='QR' title='Escanear para guardar contacto'/>" if qr_b64 else ""}
                    </div>
                    <div class="cv-body">
                        <div>
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-phone fa-icon"></i> Contacto</div>
                                <div class="cv-item"><strong>Correo institucional:</strong> {_v(persona.correo_institucional)}</div>
                                <div class="cv-item"><strong>Correo personal:</strong> {_v(persona.correo_personal)}</div>
                                <div class="cv-item"><strong>Celular:</strong> {_v(persona.celular_personal)}</div>
                                <div class="cv-item"><strong>Tel. oficina:</strong> {_v(persona.telefono_oficina)} Ext. {_v(persona.extension)}</div>
                            </div>
                            {seccion_formacion}
                        </div>
                        <div>
                            {seccion_datos_laborales}
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-id-card fa-icon"></i> Identidad Oficial</div>
                                <div class="cv-item"><strong>CURP:</strong> {_v(persona.curp)}</div>
                                <div class="cv-item"><strong>RFC:</strong> {_v(persona.rfc)}</div>
                                <div class="cv-item"><strong>NSS:</strong> {_v(persona.nss)}</div>
                            </div>
                            <div class="cv-section">
                                <div class="cv-section-title"><i class="fa-solid fa-location-dot fa-icon"></i> Datos Personales</div>
                                <div class="cv-item"><strong>Domicilio:</strong> {_v(persona.domicilio)}</div>
                                <div class="cv-item"><strong>Nacimiento:</strong> {_f(persona.fecha_nacimiento)} · {_v(persona.genero)} · {_v(persona.estado_civil)}</div>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.html(cv_html)
                st.markdown("<br/>", unsafe_allow_html=True)
                # --- Botón descarga PDF ---
                try:
                    pdf_bytes = _generar_cv_pdf(persona)
                    nombre_archivo = f"CV_{(persona.apellido_paterno or '')}_{(persona.nombre or '')}".replace(" ", "_").strip("_") or "CV"
                    st.download_button(":material/download: Descargar CV en PDF", data=pdf_bytes, file_name=f"{nombre_archivo}.pdf", mime="application/pdf", key="cv_descarga_pdf")
                except Exception as ex:
                    st.caption(f"No se pudo generar el PDF: {ex}")
                st.markdown("<br/>", unsafe_allow_html=True)
                # --- MODO EDICIÓN (Expander) ---
                es_empleado = (rol_cv == "Empleado")
                with st.expander(":material/edit: Editar información de este expediente", expanded=False):
                    with st.form("form_cv_editar"):
                        st.markdown("#### Identidad")
                        c1, c2 = st.columns(2)
                        with c1:
                            nom = st.text_input("Nombre", value=persona.nombre or "")
                            ap_pat = st.text_input("Apellido paterno", value=persona.apellido_paterno or "")
                            ap_mat = st.text_input("Apellido materno", value=persona.apellido_materno or "")
                            fecha_nac = st.date_input("Fecha nacimiento", value=persona.fecha_nacimiento or datetime(1990, 1, 1).date(), format="DD/MM/YYYY")
                            gen = st.text_input("Género", value=persona.genero or "")
                            opts_ec = ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"]
                            idx_ec = opts_ec.index(persona.estado_civil) if persona.estado_civil and persona.estado_civil in opts_ec else 0
                            ec = st.selectbox("Estado civil", opts_ec, index=idx_ec)
                        with c2:
                            dom = st.text_input("Domicilio", value=persona.domicilio or "")
                            curp = st.text_input("CURP", value=persona.curp or "")
                            curp_norm = (curp or "").strip().upper()
                            val_curp = _validar_curp(curp_norm)
                            if curp_norm:
                                if not val_curp["ok"]:
                                    st.error("CURP inválida: " + " · ".join(val_curp["errores"]))
                                else:
                                    datos = val_curp.get("datos", {})
                                    fn_curp = datos.get("fecha_nacimiento")
                                    sexo_curp = datos.get("sexo")
                                    ent_curp = datos.get("entidad")
                                    st.caption(f"CURP OK · Nac: {fn_curp.strftime('%d/%m/%Y')} · Sexo: {sexo_curp} · Entidad: {ent_curp}")
                                    fn_form = fecha_nac
                                    if fn_form and fn_curp and fn_form != fn_curp:
                                        st.warning(f"La fecha de nacimiento no coincide con CURP ({fn_curp.strftime('%d/%m/%Y')}).")
                                    sexo_form = "M" if (gen or "").strip().lower().startswith("fem") else ("H" if (gen or "").strip() else "")
                                    if sexo_curp and sexo_form and sexo_curp != sexo_form:
                                        st.warning(f"El género no coincide con CURP (CURP={sexo_curp}).")
                            rfc = st.text_input("RFC", value=persona.rfc or "")
                            rfc_norm = (rfc or "").strip().upper()
                            val_rfc = _validar_rfc(rfc_norm)
                            if rfc_norm:
                                if not val_rfc["ok"]:
                                    st.error("RFC inválido: " + " · ".join(val_rfc["errores"]))
                                else:
                                    datos_r = val_rfc.get("datos", {})
                                    f_rfc = datos_r.get("fecha")
                                    t_rfc = datos_r.get("tipo")
                                    st.caption(f"RFC OK · Tipo: {t_rfc} · Fecha: {f_rfc.strftime('%d/%m/%Y') if f_rfc else '—'}")
                                    if t_rfc == "Física":
                                        if fecha_nac and f_rfc and fecha_nac != f_rfc:
                                            st.warning(f"La fecha de nacimiento no coincide con RFC ({f_rfc.strftime('%d/%m/%Y')}).")
                            nss = st.text_input("NSS", value=persona.nss or "")
                            nss_norm = (nss or "").strip().replace("-", "").replace(" ", "")
                            val_nss = _validar_nss(nss_norm, fecha_nacimiento=fecha_nac)
                            if nss_norm:
                                if not val_nss["ok"]:
                                    st.error("NSS inválido: " + " · ".join(val_nss["errores"]))
                                else:
                                    st.caption("NSS OK")
                            ine = st.text_input("INE/Pasaporte", value=persona.ine_pasaporte or "")
                        st.markdown("#### Contacto")
                        c3, c4 = st.columns(2)
                        with c3:
                            cel = st.text_input("Celular", value=persona.celular_personal or "")
                            cel_norm = None
                            val_cel = _validar_celular_mx(cel)
                            if (cel or "").strip():
                                if not val_cel["ok"]:
                                    st.error("Celular inválido: " + " · ".join(val_cel["errores"]))
                                else:
                                    cel_norm = val_cel["datos"].get("cel_norm_10")
                                    st.caption(f"Celular OK · {cel_norm}")
                            corr_per = st.text_input("Correo personal", value=persona.correo_personal or "")
                            corr_per_norm = None
                            val_email = _validar_email(corr_per)
                            if (corr_per or "").strip():
                                if not val_email["ok"]:
                                    st.error("Correo personal inválido: " + " · ".join(val_email["errores"]))
                                else:
                                    corr_per_norm = val_email["datos"].get("email_norm")
                                    st.caption(f"Correo personal OK · {corr_per_norm}")
                            if dominios_cv:
                                ci_raw = (persona.correo_institucional or "")
                                parte_inst, dom_inst = (ci_raw.split("@", 1) if "@" in ci_raw else (ci_raw, ""))
                                dom_id_def = next((d.id for d in dominios_cv if d.dominio == dom_inst), dominios_cv[0].id if dominios_cv else None)
                                parte_local_cv = st.text_input("Correo institucional (parte antes de @)", value=parte_inst or "", key="cv_corr_parte")
                                dom_sel_cv = st.selectbox("Dominio", options=[d.id for d in dominios_cv], format_func=lambda did: next((f"@{d.dominio}" for d in dominios_cv if d.id == did), ""), index=[d.id for d in dominios_cv].index(dom_id_def) if dom_id_def in [d.id for d in dominios_cv] else 0, key="cv_corr_dom")
                                d_sel = next((d for d in dominios_cv if d.id == dom_sel_cv), None)
                                corr_inst = (f"{parte_local_cv.strip()}@{d_sel.dominio}" if parte_local_cv and d_sel else "") or ""
                            else:
                                corr_inst = st.text_input("Correo institucional", value=persona.correo_institucional or "")
                        with c4:
                            tel_of = st.text_input("Tel. oficina", value=persona.telefono_oficina or "")
                            ext = st.text_input("Extensión", value=persona.extension or "")
                            tel_of_norm = None
                            ext_norm = None
                            val_tel_of = _validar_telefono_mx(tel_of)
                            val_ext = _validar_extension(ext)
                            v_tel, v_ext = st.columns(2)
                            with v_tel:
                                if (tel_of or "").strip():
                                    if not val_tel_of["ok"]:
                                        st.error("Teléfono de oficina inválido: " + " · ".join(val_tel_of["errores"]))
                                    else:
                                        tel_of_norm = val_tel_of["datos"].get("tel_norm_10")
                                        st.caption(f"Teléfono OK · {tel_of_norm}")
                            with v_ext:
                                if (ext or "").strip():
                                    if not val_ext["ok"]:
                                        st.error("Extensión inválida: " + " · ".join(val_ext["errores"]))
                                    else:
                                        ext_norm = val_ext["datos"].get("ext_norm")
                                        st.caption(f"Extensión OK · {ext_norm}")
                        if not es_empleado:
                            st.markdown("#### Laborales / Ubicación")
                            c5, c6 = st.columns(2)
                            with c5:
                                edif = st.text_input("Edificio", value=persona.edificio or "")
                                plan = st.text_input("Planta", value=persona.planta or "")
                                area = st.text_input("Área asignada", value=persona.area_asignada or "")
                                fing = st.date_input("Fecha ingreso", value=persona.fecha_ingreso or datetime.today().date(), format="DD/MM/YYYY")
                            with c6:
                                tcont = st.text_input("Tipo contrato", value=persona.tipo_contrato or "")
                                jorn = st.text_input("Jornada laboral", value=persona.jornada_laboral or "")
                                sal = st.number_input("Salario base", value=float(persona.salario_base) if persona.salario_base is not None else 0.0, step=100.0)
                                sal_bruto = st.text_input("Salario bruto/neto", value=persona.salario_bruto_neto or "")
                                perpag = st.text_input("Periodicidad pago", value=persona.periodicidad_pago or "")
                            st.markdown("#### Académico")
                            tit = st.text_input("Título abreviatura", value=persona.titulo_abreviatura or "")
                            lic = st.text_input("Licenciatura", value=persona.licenciatura or "")
                            maes = st.text_input("Maestría", value=persona.maestria or "")
                            doc = st.text_input("Doctorado", value=persona.doctorado or "")
                            prog = st.text_area("Programas educativos", value=persona.programas_educativos or "", height=80)
                        if st.form_submit_button(":material/save: Guardar cambios"):
                            if curp_norm and not val_curp["ok"]:
                                st.error("No se puede guardar: la CURP es inválida.")
                                st.stop()
                            if rfc_norm and not val_rfc["ok"]:
                                st.error("No se puede guardar: el RFC es inválido.")
                                st.stop()
                            if nss_norm and not val_nss["ok"]:
                                st.error("No se puede guardar: el NSS es inválido.")
                                st.stop()
                            if (cel or "").strip() and not val_cel["ok"]:
                                st.error("No se puede guardar: el celular es inválido.")
                                st.stop()
                            if (corr_per or "").strip() and not val_email["ok"]:
                                st.error("No se puede guardar: el correo personal es inválido.")
                                st.stop()
                            if (tel_of or "").strip() and not val_tel_of["ok"]:
                                st.error("No se puede guardar: el teléfono de oficina es inválido.")
                                st.stop()
                            if (ext or "").strip() and not val_ext["ok"]:
                                st.error("No se puede guardar: la extensión es inválida.")
                                st.stop()
                            persona.nombre = nom.strip() or None
                            persona.apellido_paterno = ap_pat.strip() or None
                            persona.apellido_materno = ap_mat.strip() or None
                            persona.fecha_nacimiento = fecha_nac
                            persona.genero = gen.strip() or None
                            persona.estado_civil = ec.strip() or None
                            persona.domicilio = dom.strip() or None
                            persona.curp = curp_norm or None
                            persona.rfc = rfc_norm or None
                            persona.nss = nss_norm or None
                            persona.ine_pasaporte = ine.strip() or None
                            persona.celular_personal = (cel_norm or "").strip() or None
                            persona.correo_personal = (corr_per_norm or "").strip() or None
                            persona.correo_institucional = corr_inst.strip() or None
                            persona.telefono_oficina = (tel_of_norm or "").strip() or None
                            persona.extension = (ext_norm or "").strip() or None
                            if not es_empleado:
                                persona.edificio = edif.strip() or None
                                persona.planta = plan.strip() or None
                                persona.area_asignada = area.strip() or None
                                persona.fecha_ingreso = fing
                                persona.tipo_contrato = tcont.strip() or None
                                persona.jornada_laboral = jorn.strip() or None
                                persona.salario_base = sal if sal else None
                                persona.salario_bruto_neto = sal_bruto.strip() or None
                                persona.periodicidad_pago = perpag.strip() or None
                                persona.titulo_abreviatura = tit.strip() or None
                                persona.licenciatura = lic.strip() or None
                                persona.maestria = maes.strip() or None
                                persona.doctorado = doc.strip() or None
                                persona.programas_educativos = prog.strip() or None
                            session.commit()
                            nombre_persona_cv = f"{persona.nombre or ''} {persona.apellido_paterno or ''} {persona.apellido_materno or ''}".strip() or "Sin nombre"
                            registrar_bitacora(session, "EDITAR", "CV", f"Expediente editado: {nombre_persona_cv}")
                            st.success("Expediente actualizado correctamente.")
                            time.sleep(1)
                            st.rerun()
    
                    if not es_empleado:
                        st.markdown("---")
                        st.markdown("#### :material/auto_stories: Producción Académica")
                        prod_persona = list(persona.producciones or [])
                        if prod_persona:
                            for p in prod_persona:
                                col_p, col_b = st.columns([5, 1])
                                with col_p:
                                    st.caption(f"{p.tipo}: {p.titulo or ''}" + (f" — {p.titulo_capitulo}" if p.titulo_capitulo else "") + f" ({p.fecha.strftime('%d/%m/%Y') if p.fecha else ''})")
                                with col_b:
                                    if st.button(":material/delete:", key=f"cv_del_prod_{persona.id}_{p.id}", type="secondary"):
                                        session.delete(p)
                                        session.commit()
                                        st.success("Producción eliminada.")
                                        time.sleep(0.8)
                                        st.rerun()
                        if prod_persona:
                            prod_edit = st.selectbox("Editar publicación", options=[p.id for p in prod_persona],
                                format_func=lambda pid: next((f"{p.tipo}: {p.titulo}" for p in prod_persona if p.id == pid), str(pid)),
                                key="cv_sel_edit_prod")
                            if prod_edit:
                                pe = next((p for p in prod_persona if p.id == prod_edit), None)
                                if pe:
                                    with st.form("form_cv_edit_prod"):
                                        e_tipo = st.selectbox("Tipo", ["Libro", "Capítulo de Libro", "Artículo"], index=["Libro", "Capítulo de Libro", "Artículo"].index(pe.tipo) if pe.tipo in ["Libro", "Capítulo de Libro", "Artículo"] else 0, key="cv_edit_tipo")
                                        e_tit = st.text_input("Título*", value=pe.titulo or "", key="cv_edit_tit")
                                        e_titcap = st.text_input("Título capítulo (opcional)", value=pe.titulo_capitulo or "", key="cv_edit_titcap")
                                        e_rev = st.text_input("Revista/Medio (opcional)", value=pe.revista_medio or "", key="cv_edit_rev")
                                        e_fec = st.date_input("Fecha", value=pe.fecha or datetime.today().date(), key="cv_edit_fec")
                                        e_ident = st.text_input("ISBN/ISSN*", value=pe.identificador or "", key="cv_edit_ident")
                                        if st.form_submit_button(":material/save: Actualizar Producción"):
                                            if e_tit and e_ident:
                                                pe.tipo = e_tipo
                                                pe.titulo = e_tit.strip()
                                                pe.titulo_capitulo = e_titcap.strip() or None
                                                pe.revista_medio = e_rev.strip() or None
                                                pe.fecha = e_fec
                                                pe.identificador = e_ident.strip()
                                                session.commit()
                                                st.success("Producción actualizada.")
                                                time.sleep(0.8)
                                                st.rerun()
                                            else:
                                                st.error("Título e ISBN/ISSN son obligatorios.")
                        with st.form("form_cv_add_prod", clear_on_submit=True):
                            st.caption("Añadir nueva publicación")
                            tp = st.selectbox("Tipo", ["Libro", "Capítulo de Libro", "Artículo"], key="cv_prod_tipo")
                            tit = st.text_input("Título*")
                            tit_cap = st.text_input("Título del capítulo (opcional)", key="cv_prod_titcap")
                            rev = st.text_input("Revista/Medio (opcional)", key="cv_prod_rev")
                            fec = st.date_input("Fecha", value=datetime.today().date(), key="cv_prod_fec")
                            ident = st.text_input("ISBN/ISSN*", key="cv_prod_ident")
                            if st.form_submit_button(":material/add: Añadir Producción"):
                                if tit and ident:
                                    np = ProduccionAcademica(personal_id=persona.id, tipo=tp, titulo=tit.strip(),
                                        titulo_capitulo=tit_cap.strip() or None, revista_medio=rev.strip() or None,
                                        fecha=fec, identificador=ident.strip())
                                    session.add(np)
                                    session.commit()
                                    st.success("Producción añadida.")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("Título e ISBN/ISSN son obligatorios.")
    
                        st.markdown("---")
                        st.markdown("#### :material/construction: Capacitación")
                        cur_persona = list(persona.cursos or [])
                        if cur_persona:
                            for c in cur_persona:
                                col_c, col_b = st.columns([5, 1])
                                with col_c:
                                    st.caption(f"{c.nombre_curso or ''} — {c.institucion or ''} ({c.horas or 0} hrs, {c.fecha_termino.strftime('%d/%m/%Y') if c.fecha_termino else ''})")
                                with col_b:
                                    if st.button(":material/delete:", key=f"cv_del_cur_{persona.id}_{c.id}", type="secondary"):
                                        session.delete(c)
                                        session.commit()
                                        st.success("Curso eliminado.")
                                        time.sleep(0.8)
                                        st.rerun()
                        if cur_persona:
                            cur_edit = st.selectbox("Editar capacitación", options=[c.id for c in cur_persona],
                                format_func=lambda cid: next((f"{c.nombre_curso} — {c.institucion}" for c in cur_persona if c.id == cid), str(cid)),
                                key="cv_sel_edit_cur")
                            if cur_edit:
                                ce = next((c for c in cur_persona if c.id == cur_edit), None)
                                if ce:
                                    with st.form("form_cv_edit_cur"):
                                        e_nom = st.text_input("Nombre del curso*", value=ce.nombre_curso or "", key="cv_edit_cur_nom")
                                        e_inst = st.text_input("Institución*", value=ce.institucion or "", key="cv_edit_cur_inst")
                                        e_hrs = st.number_input("Horas", min_value=1, value=ce.horas or 20, key="cv_edit_cur_hrs")
                                        e_fec = st.date_input("Fecha de término", value=ce.fecha_termino or datetime.today().date(), key="cv_edit_cur_fec")
                                        opts_doc = ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"]
                                        e_doc = st.selectbox("Documento", opts_doc, index=opts_doc.index(ce.tipo_documento) if ce.tipo_documento in opts_doc else 0, key="cv_edit_cur_doc")
                                        if st.form_submit_button(":material/save: Actualizar Capacitación"):
                                            if e_nom and e_inst:
                                                ce.nombre_curso = e_nom.strip()
                                                ce.institucion = e_inst.strip()
                                                ce.horas = int(e_hrs)
                                                ce.fecha_termino = e_fec
                                                ce.tipo_documento = e_doc
                                                session.commit()
                                                st.success("Capacitación actualizada.")
                                                time.sleep(0.8)
                                                st.rerun()
                                            else:
                                                st.error("Nombre e Institución son obligatorios.")
                        with st.form("form_cv_add_cur", clear_on_submit=True):
                            st.caption("Añadir nuevo curso")
                            nom_c = st.text_input("Nombre del curso*", key="cv_cur_nom")
                            inst_c = st.text_input("Institución*", key="cv_cur_inst")
                            hrs_c = st.number_input("Horas", min_value=1, value=20, key="cv_cur_hrs")
                            fec_c = st.date_input("Fecha de término", key="cv_cur_fec")
                            doc_c = st.selectbox("Documento", ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"], key="cv_cur_doc")
                            if st.form_submit_button(":material/add: Añadir Capacitación"):
                                if nom_c and inst_c:
                                    nc = CursoCapacitacion(personal_id=persona.id, nombre_curso=nom_c.strip(),
                                        institucion=inst_c.strip(), horas=int(hrs_c), fecha_termino=fec_c, tipo_documento=doc_c)
                                    session.add(nc)
                                    session.commit()
                                    st.success("Capacitación añadida.")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("Nombre e Institución son obligatorios.")

# ==========================================
# PESTAÑA: MI PERFIL (Empleado - Solicitudes de Captura)
# ==========================================
if (":material/person: Mi Perfil" in tab_dict) or ("Mi Perfil" in tab_dict):
    with tab_dict.get(":material/person: Mi Perfil", tab_dict.get("Mi Perfil")):
        session.expire_all()
        st.header(":material/person: Mi Perfil")
        st.caption("Tu información pública y solicitudes pendientes de aprobación por RH.")
        personal_id_mp = st.session_state.get("personal_id")
        if not personal_id_mp:
            st.warning("Tu usuario no está vinculado a un expediente. Contacta al administrador.")
        else:
            persona_mp = session.get(Personal, personal_id_mp)
            if not persona_mp:
                st.warning("No se encontró tu expediente.")
            else:
                pendientes_mp = session.query(SolicitudCaptura).filter(
                    SolicitudCaptura.personal_id == personal_id_mp,
                    SolicitudCaptura.estado == "pendiente"
                ).order_by(SolicitudCaptura.fecha_solicitud.desc()).all()
                def _pendiente_por(seccion, campo=None, registro_ref=None):
                    for s in pendientes_mp:
                        if s.seccion != seccion:
                            continue
                        pl = json.loads(s.payload_json) if s.payload_json else {}
                        if s.accion == "agregar":
                            if campo is None:
                                return pl
                            return pl.get(campo)
                        if s.registro_ref_id == registro_ref or (campo and campo in pl):
                            return pl.get(campo) if campo else pl
                    return None
                def _payload_estudios_con_campo(campo_est):
                    """Devuelve el payload de la primera solicitud estudios que incluye este campo (ej. licenciatura)."""
                    for s in pendientes_mp:
                        if s.seccion != "estudios":
                            continue
                        pl = json.loads(s.payload_json) if s.payload_json else {}
                        if campo_est in pl:
                            return pl
                    return None
                tab_dp, tab_est, tab_pub, tab_cap = st.tabs([
                    "Datos Personales", "Estudios", "Publicaciones", "Capacitación"
                ])
                with tab_dp:
                    st.subheader("Datos Personales y Contacto")
                    # Mismos campos editables que en "Editar información de este expediente" del CV
                    campos_dp = [
                        ("nombre", "Nombre", "text"),
                        ("apellido_paterno", "Apellido paterno", "text"),
                        ("apellido_materno", "Apellido materno", "text"),
                        ("fecha_nacimiento", "Fecha nacimiento", "date"),
                        ("genero", "Género", "select_genero"),
                        ("estado_civil", "Estado civil", "select_ec"),
                        ("domicilio", "Domicilio", "text"),
                        ("curp", "CURP", "text"),
                        ("rfc", "RFC", "text"),
                        ("nss", "NSS", "text"),
                        ("ine_pasaporte", "INE/Pasaporte", "text"),
                        ("celular_personal", "Celular", "text"),
                        ("correo_personal", "Correo personal", "text"),
                        ("correo_institucional", "Correo institucional", "text"),
                        ("telefono_oficina", "Tel. oficina", "text"),
                        ("extension", "Extensión", "text"),
                    ]
                    opts_ec = ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"]
                    opts_gen = ["Femenino", "Masculino"]
                    def _fmt_val(p, ckey):
                        v = getattr(p, ckey, None)
                        if ckey == "fecha_nacimiento" and v:
                            return v.strftime('%d/%m/%Y') if hasattr(v, 'strftime') else str(v)
                        return v or "—"
                    def _pendiente_igual_actual(ckey, cval, pend_val):
                        """True si el valor pendiente es igual al actual (no hubo cambio real en este campo)."""
                        if pend_val is None:
                            return True
                        if ckey == "fecha_nacimiento":
                            act = getattr(persona_mp, ckey, None)
                            act_iso = act.isoformat() if act and hasattr(act, "isoformat") else (str(act)[:10] if act else "")
                            pend_iso = str(pend_val)[:10] if pend_val else ""
                            return act_iso == pend_iso
                        return (str(cval).strip() or "—") == (str(pend_val).strip() if pend_val else "—")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Identidad**")
                        for ckey, clabel, _ in campos_dp[:11]:
                            cval = _fmt_val(persona_mp, ckey)
                            pend_val = _pendiente_por("datos_personales", ckey)
                            st.markdown(f"**{clabel}:** {cval}")
                            if pend_val is not None:
                                if _pendiente_igual_actual(ckey, cval, pend_val):
                                    st.caption("Sin cambio")
                                else:
                                    st.warning(f"⏳ Cambio pendiente en **{clabel}**: *{str(pend_val)[:60]}*")
                    with col_b:
                        st.markdown("**Contacto**")
                        for ckey, clabel, _ in campos_dp[11:]:
                            cval = _fmt_val(persona_mp, ckey)
                            pend_val = _pendiente_por("datos_personales", ckey)
                            st.markdown(f"**{clabel}:** {cval}")
                            if pend_val is not None:
                                if _pendiente_igual_actual(ckey, cval, pend_val):
                                    st.caption("Sin cambio")
                                else:
                                    st.warning(f"⏳ Cambio pendiente en **{clabel}**: *{str(pend_val)[:60]}*")
                    expander_abierto = not st.session_state.pop("_contraer_expander_sol_datos", True)
                    with st.expander("Solicitar modificación del bloque Identidad y Contacto", expanded=expander_abierto):
                        st.caption("Completa o modifica los datos y envía una sola solicitud con todo el bloque.")
                        with st.form("form_sol_dato_personal"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown("**Identidad**")
                                nom = st.text_input("Nombre", value=persona_mp.nombre or "", key="sol_nom")
                                ap_pat = st.text_input("Apellido paterno", value=persona_mp.apellido_paterno or "", key="sol_app")
                                ap_mat = st.text_input("Apellido materno", value=persona_mp.apellido_materno or "", key="sol_apm")
                                try:
                                    fn_def = persona_mp.fecha_nacimiento if hasattr(persona_mp.fecha_nacimiento, 'year') else (datetime.strptime(str(persona_mp.fecha_nacimiento or "")[:10], "%Y-%m-%d").date() if persona_mp.fecha_nacimiento else datetime(1990, 1, 1).date())
                                except Exception:
                                    fn_def = datetime(1990, 1, 1).date()
                                fecha_nac = st.date_input("Fecha nacimiento", value=fn_def, format="DD/MM/YYYY", key="sol_fnac")
                                idx_gen = next((i for i, g in enumerate(opts_gen) if str(persona_mp.genero or "")[:3].lower() == g[:3].lower()), 0)
                                gen = st.selectbox("Género", opts_gen, index=idx_gen, key="sol_gen")
                                idx_ec = opts_ec.index(persona_mp.estado_civil) if persona_mp.estado_civil in opts_ec else 0
                                ec = st.selectbox("Estado civil", opts_ec, index=idx_ec, key="sol_ec")
                                dom = st.text_input("Domicilio", value=persona_mp.domicilio or "", key="sol_dom")
                                curp = st.text_input("CURP", value=persona_mp.curp or "", key="sol_curp")
                                rfc = st.text_input("RFC", value=persona_mp.rfc or "", key="sol_rfc")
                                nss = st.text_input("NSS", value=persona_mp.nss or "", key="sol_nss")
                                ine = st.text_input("INE/Pasaporte", value=persona_mp.ine_pasaporte or "", key="sol_ine")
                            with c2:
                                st.markdown("**Contacto**")
                                cel = st.text_input("Celular", value=persona_mp.celular_personal or "", key="sol_cel")
                                corr_per = st.text_input("Correo personal", value=persona_mp.correo_personal or "", key="sol_corrp")
                                corr_inst = st.text_input("Correo institucional", value=persona_mp.correo_institucional or "", key="sol_corri")
                                tel_of = st.text_input("Tel. oficina", value=persona_mp.telefono_oficina or "", key="sol_telof")
                                ext = st.text_input("Extensión", value=persona_mp.extension or "", key="sol_ext")
                            if st.form_submit_button("Enviar solicitud (bloque completo)"):
                                # Validaciones antes de enviar
                                curp_norm = (curp or "").strip().upper() or None
                                rfc_norm = (rfc or "").strip().upper() or None
                                nss_norm = (nss or "").strip().replace("-", "").replace(" ", "") or None
                                val_curp = _validar_curp(curp_norm)
                                val_rfc = _validar_rfc(rfc_norm)
                                val_nss = _validar_nss(nss_norm, fecha_nacimiento=fecha_nac)
                                val_tel_of = _validar_telefono_mx(tel_of)
                                val_ext = _validar_extension(ext)
                                val_cel = _validar_telefono_mx(cel)
                                val_corr_per = _validar_email(corr_per)
                                val_corr_inst = _validar_email(corr_inst)
                                errores_sol = []
                                if curp_norm and not val_curp["ok"]:
                                    errores_sol.append("CURP: " + " · ".join(val_curp["errores"]))
                                if rfc_norm and not val_rfc["ok"]:
                                    errores_sol.append("RFC: " + " · ".join(val_rfc["errores"]))
                                if nss_norm and not val_nss["ok"]:
                                    errores_sol.append("NSS: " + " · ".join(val_nss["errores"]))
                                if (tel_of or "").strip() and not val_tel_of["ok"]:
                                    errores_sol.append("Tel. oficina: " + " · ".join(val_tel_of["errores"]))
                                if (ext or "").strip() and not val_ext["ok"]:
                                    errores_sol.append("Extensión: " + " · ".join(val_ext["errores"]))
                                if (cel or "").strip() and not val_cel["ok"]:
                                    errores_sol.append("Celular: " + " · ".join(val_cel["errores"]))
                                if (corr_per or "").strip() and not val_corr_per["ok"]:
                                    errores_sol.append("Correo personal: " + " · ".join(val_corr_per["errores"]))
                                if (corr_inst or "").strip() and not val_corr_inst["ok"]:
                                    errores_sol.append("Correo institucional: " + " · ".join(val_corr_inst["errores"]))
                                if errores_sol:
                                    st.error("Corrige los siguientes datos antes de enviar: " + " | ".join(errores_sol))
                                    st.stop()
                                payload = {
                                    "nombre": (nom or "").strip() or None,
                                    "apellido_paterno": (ap_pat or "").strip() or None,
                                    "apellido_materno": (ap_mat or "").strip() or None,
                                    "fecha_nacimiento": fecha_nac.isoformat() if fecha_nac else None,
                                    "genero": (gen or "").strip() or None,
                                    "estado_civil": (ec or "").strip() or None,
                                    "domicilio": (dom or "").strip() or None,
                                    "curp": curp_norm,
                                    "rfc": rfc_norm,
                                    "nss": nss_norm,
                                    "ine_pasaporte": (ine or "").strip() or None,
                                    "celular_personal": (val_cel["datos"].get("tel_norm_10") if val_cel.get("ok") else (cel or "").strip()) if (cel or "").strip() else None,
                                    "correo_personal": (corr_per or "").strip() or None,
                                    "correo_institucional": (corr_inst or "").strip() or None,
                                    "telefono_oficina": (val_tel_of["datos"].get("tel_norm_10") if val_tel_of.get("ok") else (tel_of or "").strip()) if (tel_of or "").strip() else None,
                                    "extension": (val_ext["datos"].get("ext_norm") if val_ext.get("ok") else (ext or "").strip()) if (ext or "").strip() else None,
                                }
                                sol = SolicitudCaptura(
                                    personal_id=persona_mp.id,
                                    seccion="datos_personales",
                                    accion="modificar",
                                    tabla_destino="personal",
                                    registro_ref_id=persona_mp.id,
                                    payload_json=json.dumps(payload),
                                    estado="pendiente",
                                    solicitante_usuario_id=st.session_state.get("usuario_id")
                                )
                                session.add(sol)
                                session.commit()
                                registrar_bitacora(session, "SOLICITUD_CAPTURA", "Mi Perfil", "Modificar bloque Identidad y Contacto")
                                st.session_state["_contraer_expander_sol_datos"] = True
                                st.success("Solicitud registrada. RH la revisará pronto.")
                                st.rerun()
                with tab_est:
                    try:
                        session.refresh(persona_mp)
                    except Exception:
                        pass
                    st.subheader("Estudios Realizados")
                    st.markdown(f"**Licenciatura:** {persona_mp.licenciatura or '—'}")
                    pl_lic = _payload_estudios_con_campo("licenciatura")
                    if pl_lic is not None:
                        texto_igual = (persona_mp.licenciatura or "").strip() == (pl_lic.get("licenciatura") or "").strip()
                        mencio_igual = bool(getattr(persona_mp, "licenciatura_mencion_honorifica", False)) == bool(pl_lic.get("licenciatura_mencion_honorifica"))
                        if texto_igual and mencio_igual:
                            st.caption("Sin cambio")
                        else:
                            det = (pl_lic.get("licenciatura") or "").strip() if not texto_igual else ""
                            if not mencio_igual:
                                det = (det + " — Mención honorífica") if det else "Mención honorífica" if pl_lic.get("licenciatura_mencion_honorifica") else (det + " — Sin mención honorífica") if det else "Sin mención honorífica"
                            st.warning(f"⏳ Cambio pendiente en **Licenciatura**: *{det}*")
                    st.markdown(f"**Maestría:** {persona_mp.maestria or '—'}")
                    pl_maes = _payload_estudios_con_campo("maestria")
                    if pl_maes is not None:
                        texto_igual = (persona_mp.maestria or "").strip() == (pl_maes.get("maestria") or "").strip()
                        mencio_igual = bool(getattr(persona_mp, "maestria_mencion_honorifica", False)) == bool(pl_maes.get("maestria_mencion_honorifica"))
                        if texto_igual and mencio_igual:
                            st.caption("Sin cambio")
                        else:
                            det = (pl_maes.get("maestria") or "").strip() if not texto_igual else ""
                            if not mencio_igual:
                                det = (det + " — Mención honorífica") if det else "Mención honorífica" if pl_maes.get("maestria_mencion_honorifica") else (det + " — Sin mención honorífica") if det else "Sin mención honorífica"
                            st.warning(f"⏳ Cambio pendiente en **Maestría**: *{det}*")
                    st.markdown(f"**Doctorado:** {persona_mp.doctorado or '—'}")
                    pl_doct = _payload_estudios_con_campo("doctorado")
                    if pl_doct is not None:
                        texto_igual = (persona_mp.doctorado or "").strip() == (pl_doct.get("doctorado") or "").strip()
                        mencio_igual = bool(getattr(persona_mp, "doctorado_mencion_honorifica", False)) == bool(pl_doct.get("doctorado_mencion_honorifica"))
                        if texto_igual and mencio_igual:
                            st.caption("Sin cambio")
                        else:
                            det = (pl_doct.get("doctorado") or "").strip() if not texto_igual else ""
                            if not mencio_igual:
                                det = (det + " — Mención honorífica") if det else "Mención honorífica" if pl_doct.get("doctorado_mencion_honorifica") else (det + " — Sin mención honorífica") if det else "Sin mención honorífica"
                            st.warning(f"⏳ Cambio pendiente en **Doctorado**: *{det}*")
                    with st.expander("Solicitar modificación de estudio", expanded=False):
                        # Selector fuera del form para que al cambiar provoque rerun y se actualicen valor y casilla
                        est_campo = st.selectbox("Campo", ["licenciatura", "maestria", "doctorado"], format_func=lambda x: x.capitalize(), key="sol_est_campo_sel")
                        val_act = (getattr(persona_mp, est_campo, None) or "") if persona_mp else ""
                        if isinstance(val_act, str):
                            val_act = val_act.strip()
                        else:
                            val_act = str(val_act or "")
                        mencion_key = f"{est_campo}_mencion_honorifica"
                        mencion_actual = bool(getattr(persona_mp, mencion_key, False))
                        with st.form("form_sol_estudio"):
                            nuevo_est = st.text_input("Nuevo valor", value=val_act, key=f"sol_est_val_{est_campo}", placeholder="Ej. Ingeniería en Industrias Alimentarias")
                            mencio_honorifica = st.checkbox(":material/workspace_premium: Obtuvo mención honorífica", value=mencion_actual, key=f"sol_est_mencio_{est_campo}")
                            if st.form_submit_button("Enviar solicitud"):
                                valor_cambio = (nuevo_est or "").strip() != (val_act or "").strip()
                                mencion_cambio = mencio_honorifica != mencion_actual
                                if valor_cambio or mencion_cambio:
                                    payload = {est_campo: (nuevo_est or "").strip() or None, mencion_key: mencio_honorifica}
                                    sol = SolicitudCaptura(
                                        personal_id=persona_mp.id, seccion="estudios", accion="modificar",
                                        tabla_destino="personal", registro_ref_id=persona_mp.id,
                                        payload_json=json.dumps(payload), estado="pendiente",
                                        solicitante_usuario_id=st.session_state.get("usuario_id")
                                    )
                                    session.add(sol)
                                    session.commit()
                                    registrar_bitacora(session, "SOLICITUD_CAPTURA", "Mi Perfil", f"Modificar {est_campo}")
                                    st.success("Solicitud registrada.")
                                    st.rerun()
                                else:
                                    st.error("Modifica el valor del estudio o la casilla de mención honorífica.")
                with tab_pub:
                    st.subheader("Publicaciones")
                    for p in (persona_mp.producciones or []):
                        pend_p = _pendiente_por("publicaciones", registro_ref=p.id)
                        st.caption(f"• {p.tipo}: {p.titulo or ''} ({p.fecha.strftime('%d/%m/%Y') if p.fecha else ''})")
                        if pend_p:
                            tit_pend = pend_p.get("titulo", pend_p) if isinstance(pend_p, dict) else pend_p
                            st.warning(f"⏳ Cambio pendiente en **Publicación**: *{str(tit_pend)[:60]}*")
                    with st.expander("Solicitar agregar publicación"):
                        with st.form("form_sol_add_pub"):
                            tp = st.selectbox("Tipo", ["Libro", "Capítulo de Libro", "Artículo"])
                            tit = st.text_input("Título*")
                            tit_cap = st.text_input("Título capítulo (opcional)", key="sol_pub_titcap")
                            rev = st.text_input("Revista/Medio (opcional)", key="sol_pub_rev")
                            fec = st.date_input("Fecha", value=datetime.now().date(), key="sol_pub_fec")
                            ident = st.text_input("ISBN/ISSN*")
                            if st.form_submit_button("Enviar solicitud"):
                                if tit and ident:
                                    payload = {"tipo": tp, "titulo": tit.strip(), "titulo_capitulo": tit_cap.strip() or None,
                                               "revista_medio": rev.strip() or None, "fecha": fec.isoformat(), "identificador": ident.strip()}
                                    sol = SolicitudCaptura(
                                        personal_id=persona_mp.id, seccion="publicaciones", accion="agregar",
                                        tabla_destino="producciones", registro_ref_id=None,
                                        payload_json=json.dumps(payload), estado="pendiente",
                                        solicitante_usuario_id=st.session_state.get("usuario_id")
                                    )
                                    session.add(sol)
                                    session.commit()
                                    registrar_bitacora(session, "SOLICITUD_CAPTURA", "Mi Perfil", "Agregar publicación")
                                    st.success("Solicitud registrada.")
                                    st.rerun()
                                else:
                                    st.error("Título e ISBN/ISSN son obligatorios.")
                with tab_cap:
                    st.subheader("Capacitación")
                    cursos_mp = list(persona_mp.cursos or [])
                    for c in cursos_mp:
                        st.caption(f"• {c.nombre_curso or ''} — {c.institucion or ''} ({c.horas or 0} hrs)")
                    if cursos_mp:
                        with st.expander("Solicitar modificación de capacitación", expanded=False):
                            curso_opciones = [(c.id, f"{c.nombre_curso or 'Sin nombre'} — {c.institucion or ''} ({c.horas or 0} hrs)") for c in cursos_mp]
                            curso_id_sel = st.selectbox("Selecciona el curso a modificar", options=[c[0] for c in curso_opciones], format_func=lambda cid: next((t for i, t in curso_opciones if i == cid), str(cid)), key="sol_cap_edit_sel")
                            curso_sel = next((c for c in cursos_mp if c.id == curso_id_sel), None)
                            if curso_sel:
                                with st.form("form_sol_edit_cap"):
                                    nom_c_edit = st.text_input("Nombre del curso*", value=curso_sel.nombre_curso or "", key=f"sol_cap_edit_nom_{curso_sel.id}")
                                    inst_c_edit = st.text_input("Institución*", value=curso_sel.institucion or "", key=f"sol_cap_edit_inst_{curso_sel.id}")
                                    hrs_c_edit = st.number_input("Horas", min_value=1, value=int(curso_sel.horas or 0), key=f"sol_cap_edit_hrs_{curso_sel.id}")
                                    fec_c_edit = st.date_input("Fecha término", value=curso_sel.fecha_termino or datetime.now().date(), format="DD/MM/YYYY", key=f"sol_cap_edit_fec_{curso_sel.id}")
                                    doc_opts = ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"]
                                    idx_doc = doc_opts.index(curso_sel.tipo_documento) if (curso_sel.tipo_documento or "") in doc_opts else 0
                                    doc_c_edit = st.selectbox("Documento", doc_opts, index=idx_doc, key=f"sol_cap_edit_doc_{curso_sel.id}")
                                    if st.form_submit_button("Enviar solicitud de modificación"):
                                        if nom_c_edit and inst_c_edit:
                                            payload = {"nombre_curso": nom_c_edit.strip(), "institucion": inst_c_edit.strip(), "horas": int(hrs_c_edit), "fecha_termino": fec_c_edit.isoformat(), "tipo_documento": doc_c_edit}
                                            sol = SolicitudCaptura(
                                                personal_id=persona_mp.id, seccion="reconocimientos", accion="modificar",
                                                tabla_destino="cursos_cap", registro_ref_id=curso_sel.id,
                                                payload_json=json.dumps(payload), estado="pendiente",
                                                solicitante_usuario_id=st.session_state.get("usuario_id")
                                            )
                                            session.add(sol)
                                            session.commit()
                                            registrar_bitacora(session, "SOLICITUD_CAPTURA", "Mi Perfil", "Modificar capacitación")
                                            st.success("Solicitud de modificación registrada. RH la revisará pronto.")
                                            st.rerun()
                                        else:
                                            st.error("Nombre e Institución son obligatorios.")
                    with st.expander("Solicitar agregar capacitación"):
                        with st.form("form_sol_add_cap"):
                            nom_c = st.text_input("Nombre del curso*", key="sol_cap_nom")
                            inst_c = st.text_input("Institución*", key="sol_cap_inst")
                            hrs_c = st.number_input("Horas", min_value=1, value=20, key="sol_cap_hrs")
                            fec_c = st.date_input("Fecha término", key="sol_cap_fec")
                            doc_c = st.selectbox("Documento", ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"], key="sol_cap_doc")
                            if st.form_submit_button("Enviar solicitud"):
                                if nom_c and inst_c:
                                    payload = {"nombre_curso": nom_c.strip(), "institucion": inst_c.strip(), "horas": int(hrs_c),
                                               "fecha_termino": fec_c.isoformat(), "tipo_documento": doc_c}
                                    sol = SolicitudCaptura(
                                        personal_id=persona_mp.id, seccion="reconocimientos", accion="agregar",
                                        tabla_destino="cursos_cap", registro_ref_id=None,
                                        payload_json=json.dumps(payload), estado="pendiente",
                                        solicitante_usuario_id=st.session_state.get("usuario_id")
                                    )
                                    session.add(sol)
                                    session.commit()
                                    registrar_bitacora(session, "SOLICITUD_CAPTURA", "Mi Perfil", "Agregar capacitación")
                                    st.success("Solicitud registrada.")
                                    st.rerun()
                                else:
                                    st.error("Nombre e Institución son obligatorios.")
                with st.expander("📥 Mis solicitudes pendientes", expanded=bool(pendientes_mp)):
                    if pendientes_mp:
                        labels_dp_mp = {
                            "nombre": "Nombre", "apellido_paterno": "Ap. paterno", "apellido_materno": "Ap. materno",
                            "fecha_nacimiento": "Fecha nac.", "genero": "Género", "estado_civil": "Estado civil",
                            "domicilio": "Domicilio", "curp": "CURP", "rfc": "RFC", "nss": "NSS",
                            "ine_pasaporte": "INE/Pasaporte", "celular_personal": "Celular", "correo_personal": "Correo personal",
                            "correo_institucional": "Correo institucional", "telefono_oficina": "Tel. oficina", "extension": "Extensión",
                        }
                        for s in pendientes_mp:
                            pl = json.loads(s.payload_json) if s.payload_json else {}
                            if s.seccion == "datos_personales" and pl:
                                # Solo listar campos que realmente cambian respecto al valor actual
                                campos_cambio = []
                                for k in pl:
                                    if k not in labels_dp_mp:
                                        continue
                                    actual = getattr(persona_mp, k, None)
                                    solicitado = pl.get(k)
                                    if actual is None and (solicitado is None or (isinstance(solicitado, str) and not solicitado.strip())):
                                        continue
                                    if k == "fecha_nacimiento":
                                        act_str = actual.isoformat() if actual and hasattr(actual, "isoformat") else str(actual or "")[:10]
                                        sol_str = (solicitado or "")[:10] if isinstance(solicitado, str) else str(solicitado or "")[:10]
                                        if act_str != sol_str:
                                            campos_cambio.append(labels_dp_mp[k])
                                    elif (str(actual or "").strip() != str(solicitado or "").strip()):
                                        campos_cambio.append(labels_dp_mp[k])
                                txt = "Cambios en: " + ", ".join(campos_cambio) if campos_cambio else "Campos: " + ", ".join(labels_dp_mp.get(k, k) for k in pl if k in labels_dp_mp)
                            elif s.seccion == "estudios" and pl:
                                # Indicar grado, valor y si incluye mención honorífica
                                grado_label = ""
                                valor = ""
                                mencion = False
                                if "licenciatura" in pl:
                                    grado_label = "Licenciatura"
                                    valor = (pl.get("licenciatura") or "").strip()
                                    mencion = bool(pl.get("licenciatura_mencion_honorifica"))
                                elif "maestria" in pl:
                                    grado_label = "Maestría"
                                    valor = (pl.get("maestria") or "").strip()
                                    mencion = bool(pl.get("maestria_mencion_honorifica"))
                                elif "doctorado" in pl:
                                    grado_label = "Doctorado"
                                    valor = (pl.get("doctorado") or "").strip()
                                    mencion = bool(pl.get("doctorado_mencion_honorifica"))
                                if grado_label:
                                    txt = f"{grado_label}: {valor or '(vacío)'}" + (" (mención honorífica)" if mencion else "")
                                else:
                                    txt = str(list(pl.values())[0]) if pl else s.seccion
                            else:
                                txt = pl.get("titulo") or pl.get("nombre_curso") or (str(list(pl.values())[0]) if pl else s.seccion)
                            st.caption(f"• {s.seccion} — {s.accion}: {txt} — {s.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if s.fecha_solicitud else ''}")
                    else:
                        st.info("No tienes solicitudes pendientes.")

# ==========================================
# PESTAÑA: BUZÓN DE APROBACIONES (RH / Súper Admin)
# ==========================================
if (":material/inbox: Buzón Aprobaciones" in tab_dict) or ("Buzón Aprobaciones" in tab_dict):
    with tab_dict.get(":material/inbox: Buzón Aprobaciones", tab_dict.get("Buzón Aprobaciones")):
        session.expire_all()
        st.header(":material/inbox: Buzón de Aprobaciones")
        pendientes_rh = session.query(SolicitudCaptura).filter(SolicitudCaptura.estado == "pendiente").order_by(
            SolicitudCaptura.fecha_solicitud.desc()
        ).all()
        st.metric("Solicitudes pendientes", len(pendientes_rh))
        if not pendientes_rh:
            st.info("No hay solicitudes pendientes.")
        else:
            # Etiquetas legibles para campos de datos_personales (para listar en el Buzón)
            LABELS_DATOS_PERSONALES = {
                "nombre": "Nombre", "apellido_paterno": "Ap. paterno", "apellido_materno": "Ap. materno",
                "fecha_nacimiento": "Fecha nacimiento", "genero": "Género", "estado_civil": "Estado civil",
                "domicilio": "Domicilio", "curp": "CURP", "rfc": "RFC", "nss": "NSS",
                "ine_pasaporte": "INE/Pasaporte", "celular_personal": "Celular", "correo_personal": "Correo personal",
                "correo_institucional": "Correo institucional", "telefono_oficina": "Tel. oficina", "extension": "Extensión",
            }
            for sol in pendientes_rh:
                pers = session.get(Personal, sol.personal_id)
                nom_emp = f"{pers.nombre or ''} {pers.apellido_paterno or ''} {pers.apellido_materno or ''}".strip() if pers else "—"
                pl = json.loads(sol.payload_json) if sol.payload_json else {}
                fecha_str = sol.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if sol.fecha_solicitud else ''
                if sol.seccion == "datos_personales" and sol.accion == "modificar" and pl:
                    campos_mod = [LABELS_DATOS_PERSONALES.get(k, k) for k in pl.keys()]
                    titulo_exp = f"📋 {nom_emp} — {sol.seccion}: {', '.join(campos_mod)} — {fecha_str}"
                else:
                    titulo_exp = f"📋 {nom_emp} — {sol.seccion} ({sol.accion}) — {fecha_str}"
                with st.expander(titulo_exp, expanded=False):
                    col_act, col_sol = st.columns(2)
                    with col_act:
                        st.markdown("**📌 Dato actual**")
                        if sol.tabla_destino == "personal" and pers:
                            if sol.accion == "modificar":
                                for k in pl:
                                    val_act = getattr(pers, k, "—") or "—"
                                    st.write(f"**{k}:** {val_act}")
                            else:
                                st.info("N/A (agregar)")
                        elif sol.tabla_destino == "producciones":
                            if sol.registro_ref_id:
                                reg = session.get(ProduccionAcademica, sol.registro_ref_id)
                                st.write(reg.titulo if reg else "—")
                            else:
                                st.info("Nueva publicación")
                        elif sol.tabla_destino == "cursos_cap":
                            if sol.registro_ref_id:
                                reg = session.get(CursoCapacitacion, sol.registro_ref_id)
                                st.write(f"{reg.nombre_curso} — {reg.institucion}" if reg else "—")
                            else:
                                st.info("Nuevo curso/capacitación")
                        else:
                            st.info("—")
                    with col_sol:
                        st.markdown("**📝 Dato solicitado**")
                        for k, v in pl.items():
                            if k == "fecha" or k == "fecha_termino":
                                st.write(f"**{k}:** {v[:10] if isinstance(v, str) else v}")
                            else:
                                st.write(f"**{k}:** {v}")
                    st.divider()
                    motivo_rech = st.text_input("Motivo de rechazo (si aplica)", key=f"motivo_rech_{sol.id}", placeholder="Opcional")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Aprobar", key=f"ap_{sol.id}", type="primary"):
                            ok = _aplicar_payload_solicitud(session, sol)
                            if ok:
                                sol.estado = "aprobado"
                                sol.fecha_revision = datetime.now()
                                sol.revisor_usuario_id = st.session_state.get("usuario_id")
                                session.commit()
                                registrar_bitacora(session, "APROBAR_SOLICITUD", "Buzón", f"Solicitud {sol.id} aprobada")
                                st.success("Solicitud aprobada.")
                                st.rerun()
                            else:
                                st.error("No se pudo aplicar el cambio.")
                    with c2:
                        if st.button("❌ Rechazar", key=f"rej_{sol.id}"):
                            if motivo_rech.strip():
                                sol.estado = "rechazado"
                                sol.motivo_rechazo = motivo_rech.strip()
                                sol.fecha_revision = datetime.now()
                                sol.revisor_usuario_id = st.session_state.get("usuario_id")
                                session.commit()
                                registrar_bitacora(session, "RECHAZAR_SOLICITUD", "Buzón", f"Solicitud {sol.id} rechazada")
                                st.warning("Solicitud rechazada.")
                                st.rerun()
                            else:
                                st.error("Indica el motivo de rechazo para informar al empleado.")

# ==========================================
# PESTAÑA: CONFIGURACIÓN GENERAL
# ==========================================
if (":material/settings: Configuración" in tab_dict) or ("Configuración" in tab_dict):
    with tab_dict.get(":material/settings: Configuración", tab_dict.get("Configuración")):
        tab_config_sistema, tab_usuarios = st.tabs([
            ":material/settings: Configuración del Sistema",
            ":material/lock: Usuarios",
        ])
        with tab_config_sistema:
            st.markdown("---")
            st.subheader(":material/description: Apariencia del encabezado del CV")
            st.write("Configura el color del encabezado del CV generado.")
            color_cv_sel = st.color_picker(
                "Color del encabezado del CV",
                value=st.session_state.get("cv_color_header", "#0b3c5d")
            )
            if st.button("Aplicar color de CV"):
                st.session_state.cv_color_header = color_cv_sel
                usuario_nombre = st.session_state.get("usuario_nombre")
                if usuario_nombre:
                    usr = session.query(UsuarioSistema).filter_by(usuario=usuario_nombre).first()
                    if usr:
                        prefs = session.query(PreferenciasUsuario).filter_by(usuario_id=usr.id).first()
                        if not prefs:
                            prefs = PreferenciasUsuario(usuario_id=usr.id)
                            session.add(prefs)
                        # Guardamos tema y estilo + color CV combinado en estilo_emojis para persistir preferencias
                        prefs.tema_visual = st.session_state.tema_visual
                        estilo_base = st.session_state.estilo_emojis or "Emojis de colores"
                        prefs.estilo_emojis = f"{estilo_base}|{st.session_state.cv_color_header}"
                        session.commit()
                st.success("Color del encabezado del CV actualizado. Los siguientes CV usarán este color.")
            st.markdown("---")
            st.subheader(":material/mail: SMTP para restablecimiento de contraseña por correo")
            st.write("Configura Gmail para enviar códigos de restablecimiento por correo. Usa una [Contraseña de aplicación](https://support.google.com/accounts/answer/185833) de Google.")
            cfg_smtp = _get_config_smtp()
            if not cfg_smtp:
                cfg_smtp = ConfiguracionSMTP(id=1, smtp_host="smtp.gmail.com", smtp_puerto=587, usar_tls=True, activo=False)
                session.add(cfg_smtp)
                session.commit()
            with st.form("form_smtp"):
                smtp_host = st.text_input("Servidor SMTP", value=cfg_smtp.smtp_host or "smtp.gmail.com", placeholder="smtp.gmail.com")
                smtp_puerto = st.number_input("Puerto", min_value=1, max_value=65535, value=int(cfg_smtp.smtp_puerto or 587))
                smtp_usuario = st.text_input("Correo (usuario Gmail)", value=cfg_smtp.smtp_usuario or "", placeholder="tucorreo@gmail.com")
                smtp_clave = st.text_input("Contraseña de aplicación", type="password", placeholder="Dejar vacío para no cambiar", key="smtp_clave_input")
                usar_tls = st.checkbox("Usar TLS (recomendado para Gmail)", value=bool(cfg_smtp.usar_tls if cfg_smtp.usar_tls is not None else True))
                activo = st.checkbox("Activar envío de correos para restablecimiento", value=bool(cfg_smtp.activo))
                col_smtp1, col_smtp2 = st.columns(2)
                with col_smtp1:
                    if st.form_submit_button("Guardar configuración SMTP"):
                        cfg_smtp.smtp_host = smtp_host.strip() or "smtp.gmail.com"
                        cfg_smtp.smtp_puerto = smtp_puerto
                        cfg_smtp.smtp_usuario = smtp_usuario.strip() or None
                        if smtp_clave:
                            cfg_smtp.smtp_clave = smtp_clave
                        cfg_smtp.usar_tls = usar_tls
                        cfg_smtp.activo = activo and bool(smtp_usuario.strip())
                        session.commit()
                        st.success("Configuración SMTP guardada.")
                        st.rerun()
                with col_smtp2:
                    if st.form_submit_button(":material/mail: Enviar correo de prueba"):
                        session.expire_all()
                        cfg = _get_config_smtp()
                        if not cfg or not cfg.smtp_usuario or not cfg.smtp_clave:
                            st.error("Guarda la configuración con correo y contraseña antes de probar.")
                        else:
                            ok, err = _enviar_email_restablecimiento(cfg.smtp_usuario, "PRUEBA123")
                            if ok:
                                st.success("Correo de prueba enviado. Revisa tu bandeja (y spam).")
                            else:
                                st.error(f"Error: {err}")

            st.markdown("---")
            st.subheader(":material/save: Gestión de Datos y Mantenimiento")

            # --- Copias de Seguridad (Backups) ---
            with st.expander(":material/backup: Copias de Seguridad (Backups)", expanded=False):
                st.write("Descarga una copia de seguridad de la base de datos para respaldarla.")
                db_path = "directorio_escarcega.db"
                if os.path.exists(db_path):
                    with open(db_path, "rb") as f:
                        db_bytes = f.read()
                    nombre_backup = f"directorio_escarcega_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    st.download_button(":material/download: Descargar copia de seguridad", data=db_bytes, file_name=nombre_backup, mime="application/x-sqlite3", key="download_backup")
                else:
                    st.warning("No se encontró el archivo de base de datos.")

            # --- Limpieza de Datos ---
            with st.expander(":material/cleaning_services: Limpieza de Datos", expanded=False):
                st.write("Elimina registros antiguos que ya no son necesarios.")
                total_bitacora = session.query(BitacoraActividad).count()
                st.caption(f"Registros en bitácora: {total_bitacora}")
                dias_bitacora = st.number_input("Eliminar registros de bitácora anteriores a (días)", min_value=30, value=365, step=30, key="limpieza_dias")
            if st.button(":material/delete: Limpiar bitácora antigua", key="btn_limpiar_bitacora"):
                fecha_limite = datetime.now() - timedelta(days=int(dias_bitacora))
                borrados = session.query(BitacoraActividad).filter(BitacoraActividad.fecha_hora < fecha_limite).delete()
                session.commit()
                st.success(f"Se eliminaron {borrados} registros de la bitácora.")
                time.sleep(1)
                st.rerun()

        with tab_usuarios:
            render_usuarios()

# ==========================================
# PESTAÑA: BITÁCORA DE ACTIVIDAD (solo Súper Admin)
# ==========================================
if (":material/history_edu: Bitácora" in tab_dict) or ("Bitácora" in tab_dict):
    with tab_dict.get(":material/history_edu: Bitácora", tab_dict.get("Bitácora")):
        st.header(":material/history_edu: Bitácora de Actividad del Sistema")
        st.write("Registro de acciones realizadas por los usuarios autenticados.")
        st.divider()
        registros = session.query(BitacoraActividad).order_by(BitacoraActividad.fecha_hora.desc()).limit(500).all()
        if registros:
            df_bitacora = pd.DataFrame([{
                "Fecha/Hora": r.fecha_hora.strftime("%d/%m/%Y %H:%M:%S") if r.fecha_hora else "",
                "Usuario": r.usuario_nombre,
                "Acción": r.accion,
                "Módulo": r.modulo,
                "Detalles": r.detalles or ""
            } for r in registros])
            st.table(df_bitacora)
        else:
            st.info("Aún no hay registros en la bitácora.")