import streamlit as st
from datetime import date
import os, base64, io, json
from PIL import Image, ImageOps
from supabase import create_client

# ── Conexión a Supabase ───────────────────────────────────────────
# En local: edita directamente aquí
# En Streamlit Cloud: deja estas líneas así y configura los Secrets
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://deemrewpebmxvocfvesh.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY", "sb_publishable_HDy1NgJqXFXLxdTUJ5yM4A_pIva_zjP"
)


@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


db = get_client()


# ── Utilidades ────────────────────────────────────────────────────
def corregir_orientacion(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes))
    img = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def cargar():
    res = db.table("iglesias").select("*").order("fecha", desc=True).execute()
    iglesias = []
    for row in res.data:
        fotos = row.get("fotos_bytes") or []
        if isinstance(fotos, str):
            fotos = json.loads(fotos)
        row["fotos_bytes"] = fotos
        row["foto_bytes"] = None
        iglesias.append(row)
    return iglesias


def guardar_nueva(ig):
    db.table("iglesias").insert(
        {
            "nombre": ig["nombre"],
            "ciudad": ig["ciudad"],
            "pais": ig["pais"],
            "categoria": ig["categoria"],
            "fecha": ig["fecha"],
            "notas": ig["notas"],
            "favorita": ig["favorita"],
            "fotos_bytes": ig.get("fotos_bytes", []),
        }
    ).execute()


def actualizar(ig):
    db.table("iglesias").update(
        {
            "nombre": ig["nombre"],
            "ciudad": ig["ciudad"],
            "pais": ig["pais"],
            "categoria": ig["categoria"],
            "fecha": ig["fecha"],
            "notas": ig["notas"],
            "favorita": ig["favorita"],
            "fotos_bytes": ig.get("fotos_bytes", []),
        }
    ).eq("id", ig["id"]).execute()


def eliminar(ig_id):
    db.table("iglesias").delete().eq("id", ig_id).execute()


def toggle_fav(ig):
    db.table("iglesias").update({"favorita": not ig["favorita"]}).eq(
        "id", ig["id"]
    ).execute()


# ── Config ────────────────────────────────────────────────────────
st.set_page_config(page_title="Mis Templos", page_icon="⛪", layout="centered")
st.markdown(
    """
<style>
  h1 { color: #c9993a; text-align: center; letter-spacing: .1em; }
  p, .stMarkdown p { white-space: normal !important; word-wrap: break-word; }
</style>
""",
    unsafe_allow_html=True,
)

if "lightbox_src" not in st.session_state:
    st.session_state.lightbox_src = None
if "reload" not in st.session_state:
    st.session_state.reload = 0

# ── Cargar datos ──────────────────────────────────────────────────
iglesias = cargar()

# ── Lightbox ──────────────────────────────────────────────────────
if st.session_state.lightbox_src:
    st.markdown("### 🔍 Foto ampliada")
    st.image(st.session_state.lightbox_src, use_container_width=True)
    if st.button("✕  Cerrar y volver"):
        st.session_state.lightbox_src = None
        st.rerun()
    st.stop()

# ── Cabecera ──────────────────────────────────────────────────────
st.title("✦ Mis Templos ✦")
st.caption("Registro personal de lugares sagrados visitados")

c1, c2, c3 = st.columns(3)
c1.metric("⛪ Visitados", len(iglesias))
c2.metric("🌍 Países", len(set(i.get("pais", "") for i in iglesias if i.get("pais"))))
c3.metric("⭐ Favoritos", sum(1 for i in iglesias if i.get("favorita")))
st.divider()


# ── Fotos en miniatura ────────────────────────────────────────────
def mostrar_fotos(fotos_b64, clave):
    if not fotos_b64:
        return
    cols = st.columns(min(len(fotos_b64), 4))
    for i, fb in enumerate(fotos_b64):
        foto_bytes = corregir_orientacion(base64.b64decode(fb))
        with cols[i % 4]:
            st.image(foto_bytes, width=160)
            if st.button("Ver", key=f"lb_{clave}_{i}"):
                st.session_state.lightbox_src = foto_bytes
                st.rerun()


# ── Tabs ──────────────────────────────────────────────────────────
tab_lista, tab_nueva, tab_editar = st.tabs(
    ["📋 Mi lista", "➕ Añadir nueva", "✏️ Editar"]
)

# ════════════════════════════════════════════════════
# TAB LISTA
# ════════════════════════════════════════════════════
with tab_lista:
    if not iglesias:
        st.info("Aún no tienes ningún templo registrado. ¡Añade el primero!")
    else:
        busqueda = st.text_input("🔍 Buscar", placeholder="Nombre, ciudad o país...")
        cats = ["Todas"] + sorted(set(i.get("categoria", "") for i in iglesias))
        filtro_cat = st.selectbox("Filtrar por categoría", cats)

        filtradas = [
            i
            for i in iglesias
            if busqueda.lower()
            in (i.get("nombre", "") + i.get("ciudad", "") + i.get("pais", "")).lower()
            and (filtro_cat == "Todas" or i.get("categoria") == filtro_cat)
        ]

        for ig in filtradas:
            fotos = ig.get("fotos_bytes") or []
            with st.container():
                mostrar_fotos(fotos, ig["id"])
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
                    if st.button("🗑️", key=f"del_{ig['id']}", help="Eliminar"):
                        eliminar(ig["id"])
                        st.rerun()
                    fav_label = "★" if ig.get("favorita") else "⭐"
                    if st.button(fav_label, key=f"fav_{ig['id']}"):
                        toggle_fav(ig)
                        st.rerun()
            st.markdown("---")

# ════════════════════════════════════════════════════
# TAB AÑADIR
# ════════════════════════════════════════════════════
with tab_nueva:
    st.subheader("Nueva visita")
    fotos_upload = st.file_uploader(
        "📷 Fotos del lugar — puedes subir varias a la vez",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="upload_nueva",
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

    nombre = st.text_input(
        "Nombre del templo *", placeholder="Ej: Catedral de Burgos", key="n_nombre"
    )
    ciudad = st.text_input("Ciudad", placeholder="Ej: Burgos", key="n_ciudad")
    pais = st.text_input("País", placeholder="Ej: España", key="n_pais")
    categoria = st.selectbox(
        "Categoría",
        ["Iglesia", "Basílica", "Catedral", "Capilla", "Monasterio"],
        key="n_cat",
    )
    fecha = st.date_input("Fecha de visita", value=date.today(), key="n_fecha")
    notas = st.text_area(
        "Notas personales",
        placeholder="Escribe tus impresiones...",
        key="n_notas",
        height=200,
    )
    favorita = st.checkbox("⭐ Marcar como favorita", key="n_fav")

    if st.button(
        "💾 Guardar", type="primary", use_container_width=True, key="btn_nueva"
    ):
        if not nombre.strip():
            st.error("El nombre del templo es obligatorio.")
        else:
            guardar_nueva(
                {
                    "nombre": nombre,
                    "ciudad": ciudad,
                    "pais": pais,
                    "categoria": categoria,
                    "fecha": str(fecha),
                    "notas": notas,
                    "favorita": favorita,
                    "fotos_bytes": fotos_b64_nueva,
                }
            )
            st.success(f"✅ '{nombre}' guardado correctamente.")
            st.balloons()
            st.rerun()

# ════════════════════════════════════════════════════
# TAB EDITAR
# ════════════════════════════════════════════════════
with tab_editar:
    if not iglesias:
        st.info("Aún no hay iglesias para editar.")
    else:
        nombres = [f"{ig['nombre']} ({ig.get('ciudad','')})" for ig in iglesias]
        seleccion = st.selectbox("Selecciona cuál editar", nombres)
        ig_edit = iglesias[nombres.index(seleccion)]
        st.divider()

        fotos_actuales = ig_edit.get("fotos_bytes") or []

        if fotos_actuales:
            st.caption(
                f"📷 Fotos actuales ({len(fotos_actuales)}) — pulsa 🗑️ para eliminar una:"
            )
            for i, fb in enumerate(fotos_actuales):
                col_img, col_btn = st.columns([5, 1])
                with col_img:
                    st.image(
                        corregir_orientacion(base64.b64decode(fb)),
                        use_container_width=True,
                    )
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"delfoto_{ig_edit['id']}_{i}"):
                        nueva_lista = [
                            f for j, f in enumerate(fotos_actuales) if j != i
                        ]
                        ig_edit["fotos_bytes"] = nueva_lista
                        actualizar(ig_edit)
                        st.success(f"Foto {i+1} eliminada.")
                        st.rerun()

        st.markdown("**➕ Añadir más fotos:**")
        fotos_nuevas_up = st.file_uploader(
            "Selecciona fotos para añadir",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="upload_editar",
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
        nombre_e = st.text_input(
            "Nombre *", value=ig_edit.get("nombre", ""), key="e_nombre"
        )
        ciudad_e = st.text_input(
            "Ciudad", value=ig_edit.get("ciudad", ""), key="e_ciudad"
        )
        pais_e = st.text_input("País", value=ig_edit.get("pais", ""), key="e_pais")
        cats_list = ["Iglesia", "Basílica", "Catedral", "Capilla", "Monasterio"]
        cat_idx = (
            cats_list.index(ig_edit["categoria"])
            if ig_edit.get("categoria") in cats_list
            else 0
        )
        categoria_e = st.selectbox("Categoría", cats_list, index=cat_idx, key="e_cat")
        try:
            fecha_val = date.fromisoformat(ig_edit.get("fecha", str(date.today())))
        except:
            fecha_val = date.today()
        fecha_e = st.date_input("Fecha", value=fecha_val, key="e_fecha")
        notas_e = st.text_area(
            "Notas", value=ig_edit.get("notas", ""), key="e_notas", height=200
        )
        favorita_e = st.checkbox(
            "⭐ Favorita", value=ig_edit.get("favorita", False), key="e_fav"
        )

        if st.button(
            "💾 Guardar cambios",
            type="primary",
            use_container_width=True,
            key="btn_editar",
        ):
            if not nombre_e.strip():
                st.error("El nombre es obligatorio.")
            else:
                fotos_final = (ig_edit.get("fotos_bytes") or []) + fotos_b64_añadir
                actualizar(
                    {
                        "id": ig_edit["id"],
                        "nombre": nombre_e,
                        "ciudad": ciudad_e,
                        "pais": pais_e,
                        "categoria": categoria_e,
                        "fecha": str(fecha_e),
                        "notas": notas_e,
                        "favorita": favorita_e,
                        "fotos_bytes": fotos_final,
                    }
                )
                st.success(f"✅ '{nombre_e}' actualizado correctamente.")
                st.rerun()
