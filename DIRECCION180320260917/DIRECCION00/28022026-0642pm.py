import streamlit as st
import time
import os
from datetime import datetime
from sqlalchemy import Float, Boolean, Date, Column, Integer, String, ForeignKey, create_engine, DateTime, or_
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, backref

# --- INYECCIÓN DE TEMAS PERSONALIZADOS ---
if 'tema_visual' not in st.session_state:
    st.session_state.tema_visual = "Claro (Por defecto)"

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
st.set_page_config(page_title="Directorio ITS Escárcega", layout="wide")

if not os.path.exists("fotos_personal"):
    os.makedirs("fotos_personal")

# Inicializar estados para la edición interactiva
for key in ['edit_u', 'del_u', 'edit_p', 'del_p', 'edit_e', 'del_e']:
    if key not in st.session_state: st.session_state[key] = None

st.markdown("""
    <style>
        div[data-testid="stTabs"] > div:first-child {
            position: sticky; top: 2.875rem; z-index: 999;
            background-color: var(--background-color);
            padding-top: 1rem; padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--secondary-background-color);
        }
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
    
    sub_unidades = relationship('Unidad', backref=backref('parent', remote_side=[id]), cascade="all, delete-orphan")
    puestos = relationship("Puesto", back_populates="unidad", cascade="all, delete-orphan")

class Puesto(Base):
    __tablename__ = 'puestos'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    unidad_id = Column(Integer, ForeignKey('unidades.id'))
    
    unidad = relationship("Unidad", back_populates="puestos")
    personal = relationship("Personal", back_populates="puesto", cascade="all, delete-orphan")

class Personal(Base):
    __tablename__ = 'personal'
    id = Column(Integer, primary_key=True, index=True)
    # Bloque 1: Identidad
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
        # NUEVO CAMPO AÑADIDO:
    programas_educativos = Column(String, nullable=True)
    area_asignada = Column(String, nullable=True) # <-- AÑADIR ESTA LÍNEA 
    
    puesto = relationship("Puesto", back_populates="personal")
    # Relaciones para Bloque 5 y 6
    producciones = relationship("ProduccionAcademica", back_populates="empleado", cascade="all, delete-orphan")
    cursos = relationship("CursoCapacitacion", back_populates="empleado", cascade="all, delete-orphan")
# Tablas auxiliares para soportar múltiples registros
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
    engine = create_engine('sqlite:///directorio_escarcega.db', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

# --- 3. LÓGICA DEL ORGANIGRAMA INTERACTIVO (CON 3 NIVELES) ---
def reset_states():
    for key in ['edit_u', 'del_u', 'edit_p', 'del_p', 'edit_e', 'del_e']:
        st.session_state[key] = None

def renderizar_organigrama(unidades, puestos, personal_lista, parent_id=None, nivel=0):
    hijos = [u for u in unidades if u.parent_id == parent_id]
    sp_u = "&nbsp;" * (nivel * 12)
    sp_p = "&nbsp;" * ((nivel + 1) * 12)
    sp_e = "&nbsp;" * ((nivel + 2) * 12)
    
    for u in hijos:
        # === FILA: UNIDAD ===
        c_txt, c_ed, c_del = st.columns([8, 1, 1])
        with c_txt:
            st.markdown(f"{sp_u} 📁 **{u.nombre}** <span style='color:gray; font-size:0.85em;'>({u.tipo_nivel})</span>", unsafe_allow_html=True)
        with c_ed:
            if st.button("✏️", key=f"eu_{u.id}", help="Editar Unidad"): 
                reset_states(); st.session_state.edit_u = u.id
        with c_del:
            if st.button("🗑️", key=f"du_{u.id}", help="Eliminar Unidad"): 
                reset_states(); st.session_state.del_u = u.id

        if st.session_state.edit_u == u.id:
            with st.container():
                n_nom = st.text_input("Renombrar unidad:", value=u.nombre, key=f"in_u_{u.id}")
                cb1, cb2 = st.columns(2)
                if cb1.button("💾 Guardar", key=f"sv_u_{u.id}"):
                    session.query(Unidad).get(u.id).nombre = n_nom
                    session.commit(); reset_states(); st.rerun()
                if cb2.button("❌ Cancelar", key=f"cc_u_{u.id}"): reset_states(); st.rerun()

        if st.session_state.del_u == u.id:
            st.warning("⚠️ ¿Borrar unidad y todo lo que depende de ella?")
            cb1, cb2 = st.columns(2)
            if cb1.button("✅ Sí, Eliminar", key=f"cd_u_{u.id}"):
                session.delete(session.query(Unidad).get(u.id))
                session.commit(); reset_states(); st.rerun()
            if cb2.button("❌ Cancelar", key=f"cx_u_{u.id}"): reset_states(); st.rerun()

        # === FILA: PUESTOS ===
        puestos_unidad = [p for p in puestos if p.unidad_id == u.id]
        for p in puestos_unidad:
            cp_txt, cp_ed, cp_del = st.columns([8, 1, 1])
            with cp_txt:
                st.markdown(f"{sp_p} 💼 <span style='color:#2980b9; font-weight:bold;'>{p.nombre}</span>", unsafe_allow_html=True)
            with cp_ed:
                if st.button("✏️", key=f"ep_{p.id}", help="Editar Puesto"): 
                    reset_states(); st.session_state.edit_p = p.id
            with cp_del:
                if st.button("🗑️", key=f"dp_{p.id}", help="Eliminar Puesto"): 
                    reset_states(); st.session_state.del_p = p.id

            if st.session_state.edit_p == p.id:
                with st.container():
                    n_puesto = st.text_input("Renombrar puesto:", value=p.nombre, key=f"in_p_{p.id}")
                    cb1, cb2 = st.columns(2)
                    if cb1.button("💾 Guardar", key=f"sv_p_{p.id}"):
                        session.query(Puesto).get(p.id).nombre = n_puesto
                        session.commit(); reset_states(); st.rerun()
                    if cb2.button("❌ Cancelar", key=f"cc_p_{p.id}"): reset_states(); st.rerun()

            if st.session_state.del_p == p.id:
                st.warning("⚠️ ¿Eliminar este puesto? Se borrará al empleado asignado también.")
                cb1, cb2 = st.columns(2)
                if cb1.button("✅ Sí, Eliminar", key=f"cd_p_{p.id}"):
                    session.delete(session.query(Puesto).get(p.id))
                    session.commit(); reset_states(); st.rerun()
                if cb2.button("❌ Cancelar", key=f"cx_p_{p.id}"): reset_states(); st.rerun()

            # === FILA: EMPLEADOS DEL PUESTO ===
            emps = [e for e in personal_lista if e.puesto_id == p.id]
            if not emps:
                st.markdown(f"{sp_e} 👤 <span style='color:gray; font-style:italic;'>*(Vacante)*</span>", unsafe_allow_html=True)
            else:
                for e in emps:
                    ce_txt, ce_ed, ce_del = st.columns([8, 1, 1])
                    with ce_txt:
                        st.markdown(f"{sp_e} <span style='color:#16a085;'>👤 {e.nombre} {e.apellido_paterno}</span>", unsafe_allow_html=True)
                    with ce_ed:
                        if st.button("✏️", key=f"ee_{e.id}", help="Editar Persona"): 
                            reset_states(); st.session_state.edit_e = e.id
                    with ce_del:
                        if st.button("🗑️", key=f"de_{e.id}", help="Despedir Persona"): 
                            reset_states(); st.session_state.del_e = e.id

                    if st.session_state.edit_e == e.id:
                        with st.container():
                            st.info("Para editar todos los datos, ve a la pestaña 'Personal'.")
                            if st.button("❌ Cerrar", key=f"cc_e_{e.id}"): reset_states(); st.rerun()

                    if st.session_state.del_e == e.id:
                        st.warning("⚠️ ¿Quitar a esta persona del puesto? (El puesto quedará vacante)")
                        cb1, cb2 = st.columns(2)
                        if cb1.button("✅ Sí, Despedir", key=f"cd_e_{e.id}"):
                            session.delete(session.query(Personal).get(e.id))
                            session.commit(); reset_states(); st.rerun()
                        if cb2.button("❌ Cancelar", key=f"cx_e_{e.id}"): reset_states(); st.rerun()

        # Llamada recursiva (Sub-unidades)
        renderizar_organigrama(unidades, puestos, personal_lista, u.id, nivel + 1)
# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS (Debe ir arriba) ---
engine = create_engine('sqlite:///directorio_escarcega.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session() # <--- AQUÍ SE DEFINE 'session'

# --- 4. TÍTULO PRINCIPAL ---
st.title("🏛️ Sistema de Gestión - ITS de Escárcega")

# --- 5. MENÚ SUPERIOR ---
# Añadimos "Capacitación" a la lista
tab_inicio, tab_unidades, tab_personal, tab_edificios, tab_produccion, tab_cursos, tab_docentes, tab_usuarios, tab_config = st.tabs([
    "🏠 Inicio", 
    "🏢 Unidades y Puestos", 
    "👥 Personal", 
    "🏫 Edificios", 
    "📚 Producción Académica",
    "🛠️ Capacitación", # <-- NUEVA PESTAÑA
    "👨‍🏫 Docentes", 
    "🔐 Usuarios", 
    "⚙️ Configuración"
])

# ==========================================
# PESTAÑA 1: INICIO (ORGANIGRAMA)
# ==========================================
with tab_inicio:
    session.expire_all()
    st.header("Organigrama Institucional Interactivo")
    st.write("Visualiza Unidades (📁), Puestos (💼) y Personal (👤). Edita o elimina directamente aquí.")
    st.divider()
    
    todas_unidades = session.query(Unidad).all()
    todos_puestos = session.query(Puesto).all()
    todo_personal = session.query(Personal).all()
    
    if todas_unidades:
        renderizar_organigrama(todas_unidades, todos_puestos, todo_personal, parent_id=None)
    else:
        st.info("Aún no hay unidades registradas. Ve a la pestaña 'Unidades y Puestos' para comenzar.")

# ==========================================
# PESTAÑA 2: UNIDADES Y PUESTOS
# ==========================================
with tab_unidades:
    session.expire_all()
    todas_unidades = session.query(Unidad).all()
    
    st.header("1. Crear Nueva Unidad Orgánica")
    with st.form("form_unidad", clear_on_submit=True):
        nombre_u = st.text_input("Nombre de la Unidad")
        tipo_u = st.selectbox("Nivel Jerárquico", ["Dirección General", "Subdirección", "Jefatura de Departamento"])
        
        opciones_padre = {u.nombre: u.id for u in todas_unidades}
        padre_sel = st.selectbox("¿Depende de alguna unidad?", options=["-- Es una Dirección Principal --"] + list(opciones_padre.keys()))
        
        if st.form_submit_button("Guardar Unidad"):
            if nombre_u:
                padre_id = None if padre_sel == "-- Es una Dirección Principal --" else opciones_padre[padre_sel]
                nueva_unidad = Unidad(nombre=nombre_u, tipo_nivel=tipo_u, parent_id=padre_id)
                session.add(nueva_unidad)
                session.commit()
                st.success("Unidad guardada.")
                time.sleep(1)
                st.rerun()
                
    st.divider()
    
    st.header("2. Crear Puesto de Trabajo")
    st.write("Crea vacantes o puestos que pertenecen a una unidad específica.")
    if todas_unidades:
        with st.form("form_puesto", clear_on_submit=True):
            nombre_p = st.text_input("Nombre del Puesto (Ej. Jefe de Cómputo, Docente, Secretaria)")
            unidad_sel_p = st.selectbox("Pertenece a la unidad:", options=todas_unidades, format_func=lambda u: u.nombre)
            
            if st.form_submit_button("Guardar Puesto"):
                if nombre_p:
                    nuevo_puesto = Puesto(nombre=nombre_p, unidad_id=unidad_sel_p.id)
                    session.add(nuevo_puesto)
                    session.commit()
                    st.success("Puesto creado correctamente.")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Primero debes crear una unidad arriba para poder asignarle puestos.")

# ==========================================
# PESTAÑA 3: PERSONAL (CUESTIONARIO COMPLETO)
# ==========================================
with tab_personal:
    st.header("👤 Registro Integral de Personal")
    
    puestos_disponibles = session.query(Puesto).all()
    edificios_disp = session.query(Edificio).all()

    if not puestos_disponibles:
        st.error("⚠️ Error: No hay Puestos de Trabajo. Créalos en 'Unidades y Puestos'.")
    elif not edificios_disp:
        st.warning("⚠️ Error: No hay Edificios registrados.")
        st.info("Es obligatorio tener al menos un edificio para asignar la ubicación del personal.")
    else:
        # EL FORMULARIO DEBE EMPEZAR AQUÍ
        with st.form("form_expediente_personal", clear_on_submit=True):
            
            # --- BLOQUE 1: IDENTIDAD ---
            st.subheader("👤 Bloque 1: Identidad y Datos Personales")
            c_foto, c_nombres = st.columns([1, 2])
            with c_foto:
                foto = st.file_uploader("Fotografía*", type=["jpg", "png"], key="foto_u")
            with c_nombres:
                nombre = st.text_input("Nombre(s)*", key="nom_u")
                ap_pat = st.text_input("Apellido Paterno*", key="app_u")
                ap_mat = st.text_input("Apellido Materno", key="apm_u")
            
            c1, c2, c3 = st.columns(3)
            f_nacimiento = c1.date_input("Fecha de Nacimiento", value=datetime(1990, 1, 1), min_value=datetime(1950, 1, 1), key="fnac_u")
            genero = c2.selectbox("Género", ["Femenino", "Masculino"], key="gen_u")
            est_civil = c3.selectbox("Estado Civil", ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Unión Libre"], key="ec_u")
            
            # --- BLOQUE 2: CONTACTO ---
            st.subheader("📞 Bloque 2: Información de Contacto")
            correo_institucional = st.text_input("Correo Electrónico Institucional*", key="corr_inst_u")

            # --- BLOQUE 3: DATOS LABORALES (Ahora dentro del form) ---
            st.subheader("🏢 Bloque 3: Datos Laborales y Ubicación")
            puesto_sel = st.selectbox("Puesto*", options=puestos_disponibles, format_func=lambda p: f"{p.nombre}", key="p_sel_u")

            c12, c13, c14 = st.columns([2, 1, 2])
            edif_sel = c12.selectbox("Edificio*", options=edificios_disp, format_func=lambda e: f"{e.letra}", key="e_sel_u")
            
            plantas_del_edif = session.query(Planta).filter_by(edificio_id=edif_sel.id).all()
            planta_sel = None
            area_sel = None

            if plantas_del_edif:
                planta_sel = c13.selectbox("Planta*", options=plantas_del_edif, format_func=lambda p: p.nombre_nivel, key="pl_sel_u")
                areas_de_planta = session.query(Espacio).filter_by(planta_id=planta_sel.id).all()
                area_sel = c14.selectbox("Área (Opcional)", options=[None] + areas_de_planta, format_func=lambda a: a.nombre if a else "N/A", key="ar_sel_u")
            
            # --- BLOQUE 4: ACADÉMICO ---
            st.subheader("🎓 Bloque 4: Perfil Académico")
            titulo_abrev = st.selectbox("Título", ["Ing.", "Mtro.", "Dr."], key="tit_u")
            licenciatura = st.text_input("Licenciatura*", key="lic_u")

            # EL BOTÓN Y EL CIERRE DEL FORMULARIO DEBEN IR AL FINAL
            submit = st.form_submit_button("💾 GUARDAR EXPEDIENTE", use_container_width=True)
            
            if submit:
                if nombre and ap_pat and correo_institucional and planta_sel:
                    try:
                        nuevo = Personal(
                            nombre=nombre, apellido_paterno=ap_pat, correo_institucional=correo_institucional,
                            puesto_id=puesto_sel.id, edificio=edif_sel.letra, 
                            planta=planta_sel.nombre_nivel,
                            area_asignada=area_sel.nombre if area_sel else "Sin asignar",
                            titulo_abreviatura=titulo_abrev, licenciatura=licenciatura
                        )
                        session.add(nuevo)
                        session.commit()
                        st.success("Guardado correctamente")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                        session.rollback()
                else:
                    st.error("Faltan campos obligatorios o el edificio no tiene plantas.")
# ==========================================
# PESTAÑA 4: EDIFICIOS E INFRAESTRUCTURA
# ==========================================
with tab_edificios:
    st.header("🏫 Gestión de Infraestructura y Espacios")
    session.expire_all()
    
    sub_mapa, sub_add_edif, sub_add_planta, sub_add_espacio, sub_edit_del = st.tabs([
        "🗺️ Buscador", 
        "🏗️ 1. Edificios", 
        "🏢 2. Plantas/Niveles",
        "🚪 3. Áreas/Espacios", 
        "✏️ Editar / Eliminar"
    ])
    
    edificios_db = session.query(Edificio).all()
    plantas_db = session.query(Planta).all()
    
    # --- 1. BUSCADOR ---
    with sub_mapa:
        st.subheader("Buscador de Infraestructura")
        busqueda_infra = st.text_input("🔍 Buscar área, nivel o edificio...")
        
        query_espacios = session.query(Espacio).join(Planta).join(Edificio)
        
        if busqueda_infra:
            termino = f"%{busqueda_infra}%"
            query_espacios = query_espacios.filter(or_(
                Edificio.letra.ilike(termino),
                Edificio.nombre.ilike(termino),
                Planta.nombre_nivel.ilike(termino),
                Espacio.nombre.ilike(termino),
                Espacio.tipo.ilike(termino)
            ))
            
        resultados_infra = query_espacios.all()
        
        if resultados_infra:
            st.markdown("---")
            c_edif, c_planta, c_tipo, c_area = st.columns([1, 1, 1, 2])
            c_edif.markdown("**Edificio**")
            c_planta.markdown("**Nivel/Planta**")
            c_tipo.markdown("**Tipo**")
            c_area.markdown("**Nombre del Área**")
            st.markdown("---")
            
            for esp in resultados_infra:
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                c1.write(f"🏢 {esp.planta.edificio.letra}")
                c2.write(f"🪜 {esp.planta.nombre_nivel}")
                c3.write(f"🏷️ {esp.tipo}")
                c4.write(f"🚪 {esp.nombre}")
        else:
            st.info("Utiliza el buscador o comienza a registrar infraestructura en las siguientes pestañas.")

    # --- 2. NUEVO EDIFICIO ---
    with sub_add_edif:
        st.subheader("Registrar Nuevo Edificio")
        with st.form("form_add_edificio", clear_on_submit=True):
            col_l, col_n = st.columns([1, 3])
            letra_e = col_l.text_input("Letra (Ej. A, B)*", max_chars=3)
            nombre_e = col_n.text_input("Nombre (Ej. Aulas Generales)*")
            
            if st.form_submit_button("Guardar Edificio"):
                if letra_e and nombre_e:
                    letra_upper = letra_e.strip().upper()
                    if session.query(Edificio).filter(Edificio.letra == letra_upper).first():
                        st.error(f"⚠️ La letra '{letra_upper}' ya está en uso.")
                    else:
                        session.add(Edificio(letra=letra_upper, nombre=nombre_e))
                        session.commit()
                        st.success("Edificio guardado."); time.sleep(1); st.rerun()
                else:
                    st.error("Llena todos los campos obligatorios.")

    # --- 3. NUEVA PLANTA / NIVEL ---
    with sub_add_planta:
        st.subheader("Registrar Planta en un Edificio")
        if not edificios_db:
            st.warning("Primero registra un Edificio.")
        else:
            with st.form("form_add_planta", clear_on_submit=True):
                edif_sel = st.selectbox("Selecciona el Edificio*", options=edificios_db, format_func=lambda e: f"{e.letra} - {e.nombre}")
                
                c_n, c_u = st.columns(2)
                nombre_nivel = c_n.text_input("Nivel (Ej. Planta Baja, Nivel 1)*")
                uso_princ = c_u.selectbox("Uso Principal", ["Aulas", "Administrativo", "Laboratorios", "Mixto", "Servicios"])
                
                st.write("Características de Infraestructura:")
                c_ch1, c_ch2 = st.columns(2)
                tiene_rack = c_ch1.checkbox("📡 Cuenta con Rack/Switch de Red (IDF) en este piso")
                es_accesible = c_ch2.checkbox("♿ Accesible para sillas de ruedas (Rampa/Elevador)", value=True)
                
                croquis = st.file_uploader("Croquis / Plano de Red (Opcional)", type=["png", "jpg", "pdf"])
                
                if st.form_submit_button("Guardar Planta"):
                    if nombre_nivel:
                        # Lógica para guardar archivo omitida por brevedad
                        nueva_planta = Planta(edificio_id=edif_sel.id, nombre_nivel=nombre_nivel, uso_principal=uso_princ, tiene_rack_red=tiene_rack, accesible_silla_ruedas=es_accesible)
                        session.add(nueva_planta)
                        session.commit()
                        st.success("Planta guardada."); time.sleep(1); st.rerun()
                    else:
                        st.error("El nombre del nivel es obligatorio.")

    # --- 4. NUEVO ESPACIO / ÁREA ---
    with sub_add_espacio:
        st.subheader("Registrar Área o Espacio")
        if not plantas_db:
            st.warning("Debes registrar al menos una Planta en un Edificio.")
        else:
            with st.form("form_add_espacio", clear_on_submit=True):
                # Formateamos para que diga "Edificio A - Planta Baja"
                planta_sel = st.selectbox("Ubicación Física*", options=plantas_db, format_func=lambda p: f"Edificio {p.edificio.letra} -> {p.nombre_nivel}")
                
                c_tipo, c_nombre = st.columns([1, 2])
                tipo_espacio = c_tipo.selectbox("Tipo", ["Oficina", "SITE de Redes", "Laboratorio", "Salón/Aula", "Bodega", "Auditorio", "Baños", "Otro"])
                nombre_espacio = c_nombre.text_input("Nombre del Área (Ej. SITE Principal, Salón 4)*")
                
                if st.form_submit_button("Guardar Área"):
                    if nombre_espacio:
                        session.add(Espacio(planta_id=planta_sel.id, nombre=nombre_espacio, tipo=tipo_espacio))
                        session.commit()
                        st.success("Área guardada."); time.sleep(1); st.rerun()

    # --- 5. EDITAR / ELIMINAR ---
    with sub_edit_del:
        st.subheader("Gestión de Modificaciones")
        st.info("Para eliminar un área específica, utilice la base de datos directa o futuras actualizaciones de este panel. La eliminación de edificios o plantas borra todo en cascada.")
        
        if edificios_db:
            edif_del = st.selectbox("Selecciona el Edificio a eliminar:", options=edificios_db, format_func=lambda e: f"{e.letra} - {e.nombre}")
            with st.form("form_del_edificio"):
                st.warning("⚠️ Eliminar un edificio borrará todas sus plantas y áreas.")
                if st.form_submit_button("🗑️ Eliminar Edificio y Contenido"):
                    session.delete(edif_del)
                    session.commit()
                    st.success("Eliminado."); time.sleep(1.5); st.rerun()
 ## estaña 5               
# ==========================================
# PESTAÑA 5: PRODUCCIÓN ACADÉMICA
# ==========================================
with tab_produccion:
    st.header("📚 Gestión de Producción Académica")
    session.expire_all()
    
    personal_db = session.query(Personal).all()
    
    if not personal_db:
        st.warning("⚠️ No hay personal registrado. Ve a la pestaña de 'Personal' para registrar al menos a un docente o investigador primero.")
    else:
        sub_list_prod, sub_add_prod, sub_edit_del_prod = st.tabs([
            "📋 Listar y Buscar", 
            "➕ Registrar Producción", 
            "✏️ Editar / Eliminar"
        ])
        
        # --- 1. LISTAR Y BUSCAR ---
        with sub_list_prod:
            st.subheader("Buscador de Publicaciones")
            busqueda_prod = st.text_input("🔍 Buscar por título de obra, autor o ISBN/ISSN...")
            
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
                st.write("🎓 **Programas Educativos del Docente**")
                prog_act = st.text_area("Carreras en donde da clases", value=empleado_sel.programas_educativos or "")
                if st.form_submit_button("💾 Actualizar Programas"):
                    empleado_sel.programas_educativos = prog_act
                    session.commit()
                    st.success("Programas educativos actualizados."); time.sleep(1); st.rerun()

            st.markdown("---")
            
            # 2.2 Formulario Dinámico de Producción
            st.write("📚 **2. Agregar Nueva Publicación**")
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
                    rev_med = None
                    
                elif tipo_prod == "Artículo":
                    tit_obra = st.text_input("Título del Artículo*")
                    rev_med = st.text_input("Revista o Medio de Publicación*")
                    c_f, c_i = st.columns(2)
                    f_pub = c_f.date_input("Fecha")
                    ident = c_i.text_input("ISSN*")
                    tit_cap = None
                
                if st.form_submit_button("💾 Guardar Publicación"):
                    if tit_obra and ident:
                        nueva_prod = ProduccionAcademica(
                            personal_id=empleado_sel.id, tipo=tipo_prod, titulo=tit_obra,
                            titulo_capitulo=tit_cap, revista_medio=rev_med, fecha=f_pub, identificador=ident
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
                    if c_btn1.form_submit_button("💾 Actualizar Publicación"):
                        prod_mod.titulo = n_tit
                        prod_mod.identificador = n_ident
                        prod_mod.fecha = n_fecha
                        session.commit()
                        st.success("Actualizado."); time.sleep(1); st.rerun()
                        
                    if c_btn2.form_submit_button("🗑️ Eliminar Publicación"):
                        session.delete(prod_mod)
                        session.commit()
                        st.success("Publicación eliminada."); time.sleep(1.5); st.rerun()
            else:
                st.info("No hay publicaciones registradas para editar o eliminar.")
# ==========================================
# PESTAÑA 6: HISTORIAL DE CAPACITACIÓN
# ==========================================
with tab_cursos:
    st.header("🛠️ Gestión de Capacitación y Cursos")
    session.expire_all()
    
    personal_db = session.query(Personal).all()
    
    if not personal_db:
        st.warning("⚠️ Registra personal en la pestaña 'Personal' antes de agregar cursos.")
    else:
        sub_list_cur, sub_add_cur, sub_edit_del_cur = st.tabs([
            "📋 Consultar Historial", 
            "➕ Registrar Curso", 
            "✏️ Editar / Eliminar"
        ])
        
        # --- 1. CONSULTAR HISTORIAL ---
        with sub_list_cur:
            st.subheader("Buscador de Capacitaciones")
            busqueda_cur = st.text_input("🔍 Buscar por nombre de curso, institución o empleado...")
            
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
                    with st.expander(f"🎓 {cur.nombre_curso} — {nombre_emp}"):
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
            
            # Selección de empleado
            emp_cur_sel = st.selectbox("Selecciona al Empleado*", options=personal_db, 
                                      format_func=lambda p: f"{p.nombre} {p.apellido_paterno} - {p.puesto.nombre}",
                                      key="sel_emp_curso")
            
            with st.form("form_add_curso", clear_on_submit=True):
                nom_curso = st.text_input("Nombre del Curso / Taller*")
                inst_curso = st.text_input("Institución que lo imparte*")
                
                col_h, col_f, col_d = st.columns([1, 1, 1])
                hrs_curso = col_h.number_input("Horas Totales", min_value=1, value=20)
                fec_curso = col_f.date_input("Fecha de Finalización")
                doc_curso = col_d.selectbox("Documento Recibido", ["Constancia", "Diploma", "Certificado", "Reconocimiento", "Otro"])
                
                if st.form_submit_button("💾 Guardar en Historial"):
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
                    if c_btn1.form_submit_button("💾 Actualizar"):
                        cur_mod.nombre_curso = edit_nom
                        cur_mod.institucion = edit_inst
                        cur_mod.horas = edit_hrs
                        cur_mod.fecha_termino = edit_fec
                        session.commit()
                        st.success("Registro actualizado."); time.sleep(1); st.rerun()
                        
                    if c_btn2.form_submit_button("🗑️ Eliminar Registro"):
                        session.delete(cur_mod)
                        session.commit()
                        st.success("Registro eliminado."); time.sleep(1.2); st.rerun()
            else:
                st.info("No hay cursos registrados para gestionar.")
# ==========================================
# PESTAÑA 7: CONFIGURACIÓN GENERAL
# ==========================================
with tab_config:
    st.header("⚙️ Configuración del Sistema")
    
    st.subheader("🎨 Apariencia de la Interfaz")
    st.write("Cambia los colores de la aplicación para hacer más cómoda la lectura.")
    
    # Menú para elegir el tema
    tema_elegido = st.radio(
        "Selecciona el tema visual:",
        ["Claro (Por defecto)", "Nocturno (Negro)", "Gris Pizarra"],
        index=["Claro (Por defecto)", "Nocturno (Negro)", "Gris Pizarra"].index(st.session_state.tema_visual),
        horizontal=True
    )
    
    # Botón para aplicar el cambio
    if st.button("Aplicar Tema Visual"):
        st.session_state.tema_visual = tema_elegido
        st.rerun()  # Recarga la página para aplicar el CSS