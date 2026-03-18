import os
import sys
import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from appdb import SessionLocal
from directorio import (
    Unidad,
    Puesto,
    Personal,
    _nombre_completo_personal,
    _render_persona_tarjeta,
    _render_docente_expediente,
    _es_docente,
    renderizar_organigrama_visual
)

st.set_page_config(page_title="Directorio Institucional", layout="wide")

st.markdown("""
<style>
    section[data-testid="stSidebar"] {display: none;}
    header {display: none;}
    footer {display: none;}
</style>
""", unsafe_allow_html=True)



session = SessionLocal()

try:
    session.expire_all()

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
        coincidencias = []

        for p in todo_personal:
            nombre_full = _nombre_completo_personal(p).upper()
            puesto_obj = puesto_id_to_puesto.get(p.puesto_id) if p.puesto_id else None
            puesto_nom = (puesto_obj.nombre or "") if puesto_obj else ""
            unidad = (
                unidad_id_to_unidad.get(puesto_obj.unidad_id)
                if puesto_obj and puesto_obj.unidad_id
                else None
            )
            depto = (unidad.nombre or "").upper() if unidad else ""

            if q in nombre_full or q in puesto_nom.upper() or q in depto:
                coincidencias.append((p, puesto_nom, unidad))

        if coincidencias:
            st.markdown(f"**{len(coincidencias)} coincidencia(s) encontrada(s)**")
            for p, puesto_nom, unidad in coincidencias:
                if _es_docente(puesto_nom):
                    _render_docente_expediente(p, session, puesto_id_to_puesto)
                else:
                    _render_persona_tarjeta(
                        p,
                        puesto_id_to_puesto,
                        show_foto=True,
                        session_db=session
                    )
        else:
            st.info("No se encontraron coincidencias. Intenta con otros términos.")
    else:
        if todas_unidades:
            renderizar_organigrama_visual(
                session,
                todas_unidades,
                todos_puestos,
                todo_personal
            )
        else:
            st.info("Aún no hay unidades registradas.")

finally:
    session.close()