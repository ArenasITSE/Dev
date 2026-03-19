import os
import sys
import streamlit as st
from models import Unidad, Puesto, Personal
from sqlalchemy import or_

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from appdb import SessionLocal, DB_PATH
from modelos_aprobacion import Unidad, Puesto, Personal

st.set_page_config(page_title="Directorio Institucional", layout="wide")

st.markdown("""
<style>
    section[data-testid="stSidebar"] {display: none;}
    header {display: none;}
    footer {display: none;}
</style>
""", unsafe_allow_html=True)

st.title("📘 Directorio Institucional")
st.caption(f"BD en uso: {DB_PATH}")

if st.button("🔄 Recargar"):
    st.rerun()

def nombre_completo(p):
    partes = [
        (p.nombre or "").strip(),
        (p.apellido_paterno or "").strip(),
        (p.apellido_materno or "").strip(),
    ]
    return " ".join([x for x in partes if x]).strip()

session = SessionLocal()

try:
    todas_unidades = session.query(Unidad).all()
    todos_puestos = session.query(Puesto).all()
    todo_personal = session.query(Personal).all()

    st.caption(
        f"Unidades: {len(todas_unidades)} | "
        f"Puestos: {len(todos_puestos)} | "
        f"Personal: {len(todo_personal)}"
    )

    puesto_id_to_puesto = {p.id: p for p in todos_puestos}
    unidad_id_to_unidad = {u.id: u for u in todas_unidades}

    busqueda = st.text_input(
        "🔍 Buscar",
        placeholder="Buscar por nombre, puesto o departamento..."
    )

    if busqueda and busqueda.strip():
        q = busqueda.strip().upper()
        resultados = []

        for persona in todo_personal:
            nombre = nombre_completo(persona).upper()
            puesto = puesto_id_to_puesto.get(persona.puesto_id)
            puesto_nombre = (puesto.nombre or "").upper() if puesto else ""
            unidad = unidad_id_to_unidad.get(puesto.unidad_id) if puesto and puesto.unidad_id else None
            unidad_nombre = (unidad.nombre or "").upper() if unidad else ""

            if q in nombre or q in puesto_nombre or q in unidad_nombre:
                resultados.append((persona, puesto, unidad))

        if resultados:
            st.markdown(f"**{len(resultados)} coincidencia(s) encontrada(s)**")
            for persona, puesto, unidad in resultados:
                with st.container(border=True):
                    st.subheader(nombre_completo(persona))
                    st.write(f"**Puesto:** {(puesto.nombre if puesto else 'Sin puesto')}")
                    st.write(f"**Unidad:** {(unidad.nombre if unidad else 'Sin unidad')}")
                    if getattr(persona, "correo_institucional", None):
                        st.write(f"**Correo:** {persona.correo_institucional}")
                    if getattr(persona, "extension", None):
                        st.write(f"**Extensión:** {persona.extension}")
                    if getattr(persona, "celular_personal", None):
                        st.write(f"**Celular:** {persona.celular_personal}")
        else:
            st.info("No se encontraron coincidencias. Intenta con otros términos.")

    else:
        if not todas_unidades:
            st.info("Aún no hay unidades registradas.")
        else:
            st.markdown("## 🏢 Estructura del Directorio")

            for unidad in todas_unidades:
                personas_unidad = []

                for persona in todo_personal:
                    puesto = puesto_id_to_puesto.get(persona.puesto_id)
                    if puesto and puesto.unidad_id == unidad.id:
                        personas_unidad.append((persona, puesto))

                if personas_unidad:
                    with st.expander(f"📁 {unidad.nombre} ({len(personas_unidad)} persona(s))", expanded=False):
                        for persona, puesto in personas_unidad:
                            with st.container(border=True):
                                st.write(f"**Nombre:** {nombre_completo(persona)}")
                                st.write(f"**Puesto:** {puesto.nombre if puesto else 'Sin puesto'}")
                                if getattr(persona, "correo_institucional", None):
                                    st.write(f"**Correo:** {persona.correo_institucional}")
                                if getattr(persona, "extension", None):
                                    st.write(f"**Extensión:** {persona.extension}")

finally:
    session.close()