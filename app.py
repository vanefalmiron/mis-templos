import streamlit as st
from datetime import date
import json, os, base64, io
from PIL import Image, ImageOps

def corregir_orientacion(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes))
    img = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()

st.set_page_config(page_title="Mis Templos", page_icon="⛪", layout="centered")
st.markdown("""
<style>
  h1 { color: #c9993a; text-align: center; letter-spacing: .1em; }
  p, .stMarkdown p { white-space: normal !important; word-wrap: break-word; }
</style>
""", unsafe_allow_html=True)

ARCHIVO = "iglesias.json"

def cargar():
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar(datos):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

if "iglesias"     not in st.session_state: st.session_state.iglesias     = cargar()
if "lightbox_src" not in st.session_state: st.session_state.lightbox_src = None

# ── Lightbox ──────────────────────────────────────────────────────
if st.session_state.lightbox_src:
    st.markdown("### 🔍 Foto ampliada")
    st.image(st.session_state.lightbox_src, use_container_width=True)
    if st.button("✕  Cerrar y volver"):
        st.session_state.lightbox_src = None
        st.rerun()
    st.stop()

st.title("✦ Mis Templos ✦")
st.caption("Registro personal de lugares sagrados visitados")

iglesias = st.session_state.iglesias
c1, c2, c3 = st.columns(3)
c1.metric("⛪ Visitados",  len(iglesias))
c2.metric("🌍 Países",    len(set(i.get("pais","") for i in iglesias if i.get("pais"))))
c3.metric("⭐ Favoritos", sum(1 for i in iglesias if i.get("favorita")))
st.divider()

# ── Fotos en miniatura lado a lado ────────────────────────────────
def mostrar_fotos(fotos_b64, clave):
    if not fotos_b64:
        return
    n = len(fotos_b64)
    cols = st.columns(min(n, 4))
    for i, fb in enumerate(fotos_b64):
        foto_bytes = corregir_orientacion(base64.b64decode(fb))
        with cols[i % 4]:
            st.image(foto_bytes, width=160)
            if st.button("Ver", key=f"lb_{clave}_{i}"):
                st.session_state.lightbox_src = foto_bytes
                st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────
tab_lista, tab_nueva, tab_editar = st.tabs(["📋 Mi lista", "➕ Añadir nueva", "✏️ Editar"])

# ════════════════════════════════════════════════════
# TAB LISTA — más reciente primero
# ════════════════════════════════════════════════════
with tab_lista:
    if not iglesias:
        st.info("Aún no tienes ningún templo registrado. ¡Añade el primero!")
    else:
        busqueda   = st.text_input("🔍 Buscar", placeholder="Nombre, ciudad o país...")
        cats       = ["Todas"] + sorted(set(i.get("categoria","") for i in iglesias))
        filtro_cat = st.selectbox("Filtrar por categoría", cats)

        filtradas = [
            i for i in iglesias
            if busqueda.lower() in (i.get("nombre","") + i.get("ciudad","") + i.get("pais","")).lower()
            and (filtro_cat == "Todas" or i.get("categoria") == filtro_cat)
        ]

        # Más reciente primero
        filtradas = sorted(filtradas, key=lambda x: x.get("fecha", ""), reverse=True)

        for ig in filtradas:
            real_idx = iglesias.index(ig)
            fotos    = ig.get("fotos_bytes") or ([ig["foto_bytes"]] if ig.get("foto_bytes") else [])
            with st.container():
                mostrar_fotos(fotos, f"lista_{real_idx}")
                cols = st.columns([6, 1])
                with cols[0]:
                    fav = "⭐" if ig.get("favorita") else "☆"
                    st.subheader(f"{fav} {ig.get('nombre','')}")
                    st.caption(
                        f"📍 {ig.get('ciudad','')}, {ig.get('pais','')}  |  "
                        f"🏷️ {ig.get('categoria','')}  |  📅 {ig.get('fecha','')}"
                    )
                    if ig.get("notas"):
                        st.markdown(ig.get("notas"))
                with cols[1]:
                    if st.button("🗑️", key=f"del_{real_idx}", help="Eliminar"):
                        st.session_state.iglesias.pop(real_idx)
                        guardar(st.session_state.iglesias)
                        st.rerun()
                    fav_label = "★" if ig.get("favorita") else "⭐"
                    if st.button(fav_label, key=f"fav_{real_idx}"):
                        st.session_state.iglesias[real_idx]["favorita"] = not ig.get("favorita", False)
                        guardar(st.session_state.iglesias)
                        st.rerun()
            st.markdown("---")

# ════════════════════════════════════════════════════
# TAB AÑADIR
# ════════════════════════════════════════════════════
with tab_nueva:
    st.subheader("Nueva visita")
    fotos_upload = st.file_uploader(
        "📷 Fotos del lugar — puedes subir varias a la vez",
        type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True,
        key="upload_nueva"
    )
    fotos_b64_nueva = []
    if fotos_upload:
        st.caption(f"{len(fotos_upload)} foto(s) seleccionada(s):")
        prev_cols = st.columns(min(len(fotos_upload), 4))
        for i, f in enumerate(fotos_upload):
            corr = corregir_orientacion(f.read())
            fotos_b64_nueva.append(base64.b64encode(corr).decode())
            with prev_cols[i % 4]:
                st.image(corr, use_container_width=True)

    nombre    = st.text_input("Nombre del templo *", placeholder="Ej: Catedral de Burgos", key="n_nombre")
    ciudad    = st.text_input("Ciudad",  placeholder="Ej: Burgos",  key="n_ciudad")
    pais      = st.text_input("País",    placeholder="Ej: España",  key="n_pais")
    categoria = st.selectbox("Categoría", ["Iglesia","Basílica","Catedral","Capilla","Monasterio"], key="n_cat")
    fecha     = st.date_input("Fecha de visita", value=date.today(), key="n_fecha")
    notas     = st.text_area("Notas personales", placeholder="Escribe tus impresiones...", key="n_notas", height=200)
    favorita  = st.checkbox("⭐ Marcar como favorita", key="n_fav")

    if st.button("💾 Guardar", type="primary", use_container_width=True, key="btn_nueva"):
        if not nombre.strip():
            st.error("El nombre del templo es obligatorio.")
        else:
            st.session_state.iglesias.append({
                "nombre": nombre, "ciudad": ciudad, "pais": pais,
                "categoria": categoria, "fecha": str(fecha),
                "notas": notas, "favorita": favorita,
                "fotos_bytes": fotos_b64_nueva, "foto_bytes": None,
            })
            guardar(st.session_state.iglesias)
            st.success(f"✅ '{nombre}' guardado correctamente.")
            st.balloons()

# ════════════════════════════════════════════════════
# TAB EDITAR
# ════════════════════════════════════════════════════
with tab_editar:
    if not iglesias:
        st.info("Aún no hay iglesias para editar.")
    else:
        nombres   = [f"{i+1}. {ig['nombre']} ({ig.get('ciudad','')})" for i, ig in enumerate(iglesias)]
        seleccion = st.selectbox("Selecciona cuál editar", nombres)
        idx_edit  = nombres.index(seleccion)
        ig_edit   = iglesias[idx_edit]
        st.divider()

        fotos_actuales = ig_edit.get("fotos_bytes") or ([ig_edit["foto_bytes"]] if ig_edit.get("foto_bytes") else [])

        if fotos_actuales:
            st.caption(f"📷 Fotos actuales ({len(fotos_actuales)}) — pulsa 🗑️ para eliminar una:")
            for i, fb in enumerate(fotos_actuales):
                col_img, col_btn = st.columns([5, 1])
                with col_img:
                    st.image(corregir_orientacion(base64.b64decode(fb)), use_container_width=True)
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"delfoto_{idx_edit}_{i}", help=f"Eliminar foto {i+1}"):
                        nueva_lista = [f for j, f in enumerate(fotos_actuales) if j != i]
                        st.session_state.iglesias[idx_edit]["fotos_bytes"] = nueva_lista
                        st.session_state.iglesias[idx_edit]["foto_bytes"]  = None
                        guardar(st.session_state.iglesias)
                        st.success(f"Foto {i+1} eliminada.")
                        st.rerun()

        st.markdown("**➕ Añadir más fotos:**")
        fotos_nuevas_up = st.file_uploader(
            "Selecciona fotos para añadir",
            type=["jpg","jpeg","png","webp"],
            accept_multiple_files=True,
            key="upload_editar"
        )
        fotos_b64_añadir = []
        if fotos_nuevas_up:
            cols_new = st.columns(min(len(fotos_nuevas_up), 4))
            for i, f in enumerate(fotos_nuevas_up):
                corr = corregir_orientacion(f.read())
                fotos_b64_añadir.append(base64.b64encode(corr).decode())
                with cols_new[i % 4]:
                    st.image(corr, caption="Nueva", use_container_width=True)

        st.divider()
        nombre_e    = st.text_input("Nombre *",  value=ig_edit.get("nombre",""),  key="e_nombre")
        ciudad_e    = st.text_input("Ciudad",     value=ig_edit.get("ciudad",""),  key="e_ciudad")
        pais_e      = st.text_input("País",       value=ig_edit.get("pais",""),    key="e_pais")
        cats_list   = ["Iglesia","Basílica","Catedral","Capilla","Monasterio"]
        cat_idx     = cats_list.index(ig_edit["categoria"]) if ig_edit.get("categoria") in cats_list else 0
        categoria_e = st.selectbox("Categoría", cats_list, index=cat_idx, key="e_cat")
        try:    fecha_val = date.fromisoformat(ig_edit.get("fecha", str(date.today())))
        except: fecha_val = date.today()
        fecha_e    = st.date_input("Fecha", value=fecha_val, key="e_fecha")
        notas_e    = st.text_area("Notas", value=ig_edit.get("notas",""), key="e_notas", height=200)
        favorita_e = st.checkbox("⭐ Favorita", value=ig_edit.get("favorita", False), key="e_fav")

        if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key="btn_editar"):
            if not nombre_e.strip():
                st.error("El nombre es obligatorio.")
            else:
                fotos_vigentes = st.session_state.iglesias[idx_edit].get("fotos_bytes") or fotos_actuales
                fotos_final    = fotos_vigentes + fotos_b64_añadir
                st.session_state.iglesias[idx_edit] = {
                    "nombre": nombre_e, "ciudad": ciudad_e, "pais": pais_e,
                    "categoria": categoria_e, "fecha": str(fecha_e),
                    "notas": notas_e, "favorita": favorita_e,
                    "fotos_bytes": fotos_final, "foto_bytes": None,
                }
                guardar(st.session_state.iglesias)
                st.success(f"✅ '{nombre_e}' actualizado correctamente.")
                st.rerun()
