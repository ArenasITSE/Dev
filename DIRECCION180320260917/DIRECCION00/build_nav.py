# Script para reemplazar tabs por st.navigation en directorio.py
import re

VISTA_NAMES = [
    "vista_inicio", "vista_organigrama", "vista_unidades", "vista_edificios",
    "vista_personal", "vista_docentes", "vista_cv", "vista_capacitacion",
    "vista_programas", "vista_produccion", "vista_usuarios", "vista_identidad",
    "vista_configuracion", "vista_bitacora"
]

PAGE_CONFIG = [
    ("Inicio", ":material/home:", True),   # default
    ("Organigrama y Directorio", ":material/account_tree:", False),
    ("Unidades y Puestos", ":material/domain:", False),
    ("Edificios", ":material/location_city:", False),
    ("Personal", ":material/groups:", False),
    ("Docentes", ":material/school:", False),
    ("CV", ":material/contact_page:", False),
    ("Capacitación", ":material/model_training:", False),
    ("Programas Educativos", ":material/menu_book:", False),
    ("Producción Académica", ":material/science:", False),
    ("Usuarios", ":material/manage_accounts:", False),
    ("Identidad", ":material/palette:", False),
    ("Configuración", ":material/settings:", False),
    ("Bitácora", ":material/receipt_long:", False),
]

with open("directorio.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

blocks = []
i = 0
while i < len(lines):
    line = lines[i]
    if re.match(r'if \(".*" in tab_dict\) or \(".*" in tab_dict\):', line):
        i += 1
        if i < len(lines) and 'with tab_dict.get' in lines[i]:
            i += 1
            start = i
            while i < len(lines):
                if re.match(r'^if \(', lines[i]) and 'tab_dict' in lines[i]:
                    break
                if re.match(r'^# =+$', lines[i].strip()) and i > start:
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and lines[j].strip().startswith("if ("):
                        break
                i += 1
            end = i
            body_lines = lines[start:end]
            new_body = []
            for ln in body_lines:
                if len(ln) >= 8 and ln.startswith("        "):
                    new_body.append("    " + ln[8:])  # 4 spaces for function body
                else:
                    new_body.append("    " + ln if ln.strip() else ln)
            blocks.append(new_body)
            continue
    i += 1

# Build new section
out = []
out.append("# --- 5. NAVEGACIÓN (st.navigation + st.Page) ---")
out.append("rol_actual = st.session_state.rol or \"Empleado\"")
out.append("")
for idx, name in enumerate(VISTA_NAMES):
    if idx < len(blocks):
        out.append(f"def {name}():")
        out.extend(blocks[idx])
        out.append("")
    else:
        out.append(f"def {name}():")
        out.append("    st.info(\"Página en construcción.\")")
        out.append("")

out.append("# Páginas en el orden solicitado")
out.append("p_inicio = st.Page(vista_inicio, title=\"Inicio\", icon=\":material/home:\", default=True)")
out.append("p_organigrama = st.Page(vista_organigrama, title=\"Organigrama y Directorio\", icon=\":material/account_tree:\")")
out.append("p_unidades = st.Page(vista_unidades, title=\"Unidades y Puestos\", icon=\":material/domain:\")")
out.append("p_edificios = st.Page(vista_edificios, title=\"Edificios\", icon=\":material/location_city:\")")
out.append("p_personal = st.Page(vista_personal, title=\"Personal\", icon=\":material/groups:\")")
out.append("p_docentes = st.Page(vista_docentes, title=\"Docentes\", icon=\":material/school:\")")
out.append("p_cv = st.Page(vista_cv, title=\"CV\", icon=\":material/contact_page:\")")
out.append("p_capacitacion = st.Page(vista_capacitacion, title=\"Capacitación\", icon=\":material/model_training:\")")
out.append("p_programas = st.Page(vista_programas, title=\"Programas Educativos\", icon=\":material/menu_book:\")")
out.append("p_produccion = st.Page(vista_produccion, title=\"Producción Académica\", icon=\":material/science:\")")
out.append("p_usuarios = st.Page(vista_usuarios, title=\"Usuarios\", icon=\":material/manage_accounts:\")")
out.append("p_identidad = st.Page(vista_identidad, title=\"Identidad\", icon=\":material/palette:\")")
out.append("p_configuracion = st.Page(vista_configuracion, title=\"Configuración\", icon=\":material/settings:\")")
out.append("p_bitacora = st.Page(vista_bitacora, title=\"Bitácora\", icon=\":material/receipt_long:\")")
out.append("")
out.append("# Filtrar páginas por rol (RBAC)")
out.append("TODAS = [p_inicio, p_organigrama, p_unidades, p_edificios, p_personal, p_docentes, p_cv, p_capacitacion, p_programas, p_produccion, p_usuarios, p_identidad, p_configuracion, p_bitacora]")
out.append("PAGINAS_SUPER = TODAS")
out.append("PAGINAS_RRHH = [p_inicio, p_organigrama, p_unidades, p_edificios, p_personal, p_docentes, p_cv, p_capacitacion, p_identidad]")
out.append("PAGINAS_DESARROLLO = [p_inicio, p_organigrama, p_docentes, p_programas, p_produccion, p_cv]")
out.append("PAGINAS_EMPLEADO = [p_organigrama, p_cv]")
out.append("if rol_actual == \"Súper Admin\": paginas_visibles = PAGINAS_SUPER")
out.append("elif rol_actual == \"RRHH\": paginas_visibles = PAGINAS_RRHH")
out.append("elif rol_actual == \"Desarrollo Académico\": paginas_visibles = PAGINAS_DESARROLLO")
out.append("else: paginas_visibles = PAGINAS_EMPLEADO")
out.append("")
out.append("menu_agrupado = {\"Menú\": paginas_visibles}")
out.append("pg = st.navigation(menu_agrupado)")
out.append("pg.run()")
out.append("")

new_section = "\n".join(out)

# Find start: "# --- 5. MENÚ SUPERIOR"
# Find end: last line of Bitácora block (st.info("Aún no hay registros..."))
start_idx = None
end_idx = None
for i, ln in enumerate(lines):
    if "# --- 5. MENÚ SUPERIOR" in ln or "# --- 5. NAVEGACIÓN" in ln:
        if start_idx is None:
            start_idx = i
    if start_idx is not None and i > start_idx:
        if "st.info(\"Aún no hay registros en la bitácora.\")" in ln:
            end_idx = i + 1
            break

if start_idx is None:
    for i, ln in enumerate(lines):
        if "MENÚ SUPERIOR" in ln and "RBAC" in ln:
            start_idx = i
            break
if start_idx is None:
    start_idx = 1351  # 0-based
if end_idx is None:
    end_idx = 3914

print(f"Replacing lines {start_idx+1} to {end_idx}")

new_lines = lines[:start_idx] + [new_section] + lines[end_idx:]
with open("directorio.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Done. directorio.py updated.")
