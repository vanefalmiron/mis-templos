import streamlit as st
from datetime import date
import os, io, uuid
from PIL import Image, ImageOps
from supabase import create_client

# ── Conexión a Supabase ───────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

db = get_client()

# ── Utilidades de imagen ──────────────────────────────────────────
def corregir_orientacion(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes))
    img = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()

def subir_foto(imagen_bytes):
    """Sube bytes a Supabase Storage y devuelve la URL pública."""
    nombre = f"{uuid.uuid4()}.jpg"
    path = f"fotos/{nombre}"
    db.storage.from_("templos").upload(
        path=path,
        file=imagen_bytes,
        file_options={"content-type": "image/jpeg"},
    )
    return db.storage.from_("templos").get_public_url(path)

def urls_validas(lista):
    return [u for u in (lista or []) if isinstance(u, str) and u.startswith("http")]

# ── CRUD Supabase ─────────────────────────────────────────────────
def cargar():
    res = db.table("templos").select("*").order("fecha", desc=True).execute()
    return res.data or []

def guardar_nuevo(ig, fotos_urls):
    db.table("templos").insert({
        "nombre":     ig["nombre"],
        "ciudad":     ig["ciudad"],
        "pais":       ig["pais"],
        "categoria":  ig["categoria"],
        "fecha":      ig["fecha"],
        "notas":      ig["notas"],
        "favorita":   ig["favorita"],
        "fotos_urls": fotos_urls,
    }).execute()

def actualizar(ig, fotos_urls):
    db.table("templos").update({
        "nombre":     ig["nombre"],
        "ciudad":     ig["ciudad"],
        "pais":       ig["pais"],
        "categoria":  ig["categoria"],
        "fecha":      ig["fecha"],
        "notas":      ig["notas"],
        "favorita":   ig["favorita"],
        "fotos_urls": fotos_urls,
    }).eq("id", ig["id"]).execute()

def eliminar(ig_id):
    db.table("templos").delete().eq("id", ig_id).execute()

def toggle_fav(ig):
    db.table("templos").update({"favorita": not ig["favorita"]}).eq("id", ig["id"]).execute()

# ── Estilos ───────────────────────────────────────────────────────
st.set_page_config(page_title="Mis Templos", page_icon="⛪", layout="centered")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600&family=Lato:wght@300;400&display=swap');

html, body, [class*="css"] {
    font-family: 'Lato', sans-serif;
}
h1 {
    font-family: 'Cinzel', serif !important;
    color: #b8883a !important;
    text-align: center;
    letter-spacing: .15em;
    font-size: 2rem !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Cinzel', serif;
    font-size: 0.8rem;
    letter-spacing: .05em;
}
.metric-card {
    background: linear-gradient(135deg, #1a1209 0%, #2e1f0a 100%);
    border: 1px solid #b8883a44;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    color: #e8d5a3;
}
.metric-card .num {
    font-family: 'Cinzel', serif;
    font-size: 2rem;
    color: #b8883a;
    display: block;
}
.metric-card .label {
    font-size: 0.75rem;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #a08060;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
if "lightbox" not in st.session_state:
    st.session_state.lightbox = None

# ── Lightbox ──────────────────────────────────────────────────────
if st.session_state.lightbox:
    st.markdown("### 🔍 Foto ampliada")
    st.image(st.session_state.lightbox, use_container_width=True)
    if st.button("✕ Cerrar"):
        st.session_state.lightbox = None
        st.rerun()
    st.stop()

# ── Cargar datos ──────────────────────────────────────────────────
templos = cargar()

# ── Cabecera ──────────────────────────────────────────────────────
st.title("✦ Mis Templos ✦")
st.caption("Registro personal de lugares sagrados visitados")
st.markdown("")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""<div class="metric-card">
        <span class="num">{len(templos)}</span>
        <span class="label">⛪ Visitados</span>
    </div>""", unsafe_allow_html=True)
with col2:
    paises = len(set(t.get("pais", "") for t in templos if t.get("pais")))
    st.markdown(f"""<div class="metric-card">
        <span class="num">{paises}</span>
        <span class="label">🌍 Países</span>
    </div>""", unsafe_allow_html=True)
with col3:
    favs = sum(1 for t in templos if t.get("favorita"))
    st.markdown(f"""<div class="metric-card">
        <span class="num">{favs}</span>
        <span class="label">⭐ Favoritos</span>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Categorías ────────────────────────────────────────────────────
CATEGORIAS = [
    "Iglesia", "Catedral", "Basílica", "Capilla",
    "Monasterio", "Templo Budista", "Templo Hindú",
    "Templo Sintoísta", "Mezquita", "Sinagoga",
    "Santuario", "Otro",
]

# ── Helper fotos ──────────────────────────────────────────────────
def mostrar_miniaturas(fotos, clave):
    fotos = urls_validas(fotos)
    if not fotos:
        return
    cols = st.columns(min(len(fotos), 4))
    for i, url in enumerate(fotos):
        with cols[i % 4]:
            st.image(url, width=150)
            if st.button("🔍", key=f"lb_{clave}_{i}"):
                st.session_state.lightbox = url
                st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────
tab_lista, tab_nueva, tab_editar = st.tabs(["📋 Mi lista", "➕ Añadir", "✏️ Editar"])

# ════════════════════════════════════════════════════
# TAB LISTA
# ════════════════════════════════════════════════════
with tab_lista:
    if not templos:
        st.info("Aún no tienes ningún templo registrado. ¡Añade el primero!")
    else:
        busqueda = st.text_input("🔍 Buscar", placeholder="Nombre, ciudad o país...")
        cats_filtro = ["Todas"] + sorted(set(t.get("categoria", "") for t in templos if t.get("categoria")))
        filtro_cat = st.selectbox("Categoría", cats_filtro)
        solo_favs = st.checkbox("⭐ Solo favoritos")

        filtrados = [
            t for t in templos
            if busqueda.lower() in (t.get("nombre","") + t.get("ciudad","") + t.get("pais","")).lower()
            and (filtro_cat == "Todas" or t.get("categoria") == filtro_cat)
            and (not solo_favs or t.get("favorita"))
        ]

        if not filtrados:
            st.warning("No hay resultados para esa búsqueda.")

        for t in filtrados:
            fotos = urls_validas(t.get("fotos_urls"))
            with st.container():
                mostrar_miniaturas(fotos, t["id"])
                col_info, col_btns = st.columns([6, 1])
                with col_info:
                    fav = "⭐" if t.get("favorita") else "☆"
                    st.subheader(f"{fav} {t.get('nombre','')}")
                    st.caption(
                        f"📍 {t.get('ciudad','')}, {t.get('pais','')}  |  "
                        f"🏷️ {t.get('categoria','')}  |  📅 {t.get('fecha','')}"
                    )
                    if t.get("notas"):
                        st.markdown(t["notas"])
                with col_btns:
                    if st.button("🗑️", key=f"del_{t['id']}", help="Eliminar"):
                        eliminar(t["id"])
                        st.rerun()
                    if st.button("★" if t.get("favorita") else "☆", key=f"fav_{t['id']}"):
                        toggle_fav(t)
                        st.rerun()
            st.markdown("---")

# ════════════════════════════════════════════════════
# TAB AÑADIR
# ════════════════════════════════════════════════════
with tab_nueva:
    st.subheader("Nueva visita")

    fotos_up = st.file_uploader(
        "📷 Fotos (puedes subir varias)",
        type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True,
        key="up_nueva",
    )

    # Leer todos los bytes ANTES de mostrar el preview
    fotos_bytes_nueva = []
    if fotos_up:
        for f in fotos_up:
            fotos_bytes_nueva.append(f.read())
        prev = st.columns(min(len(fotos_bytes_nueva), 4))
        for i, datos in enumerate(fotos_bytes_nueva):
            with prev[i % 4]:
                st.image(corregir_orientacion(datos), use_container_width=True)

    nombre = st.text_input("Nombre del templo *", placeholder="Ej: Catedral de Burgos", key="n_nombre")
    ciudad = st.text_input("Ciudad", placeholder="Ej: Burgos", key="n_ciudad")
    pais   = st.text_input("País", placeholder="Ej: España", key="n_pais")
    cat    = st.selectbox("Categoría", CATEGORIAS, key="n_cat")
    fecha  = st.date_input("Fecha de visita", value=date.today(), key="n_fecha")
    notas  = st.text_area("Notas personales", placeholder="Tus impresiones...", height=180, key="n_notas")
    fav    = st.checkbox("⭐ Marcar como favorita", key="n_fav")

    if st.button("💾 Guardar", type="primary", use_container_width=True, key="btn_nueva"):
        if not nombre.strip():
            st.error("El nombre es obligatorio.")
        else:
            with st.spinner("Subiendo fotos..."):
                urls = []
                for datos in fotos_bytes_nueva:
                    try:
                        url = subir_foto(corregir_orientacion(datos))
                        urls.append(url)
                    except Exception as e:
                        st.warning(f"No se pudo subir una foto: {e}")
            guardar_nuevo({
                "nombre": nombre, "ciudad": ciudad, "pais": pais,
                "categoria": cat, "fecha": str(fecha),
                "notas": notas, "favorita": fav,
            }, urls)
            st.success(f"✅ '{nombre}' guardado correctamente.")
            st.balloons()
            st.rerun()

# ════════════════════════════════════════════════════
# TAB EDITAR
# ════════════════════════════════════════════════════
with tab_editar:
    if not templos:
        st.info("Aún no hay templos para editar.")
    else:
        nombres = [f"{t['nombre']} ({t.get('ciudad','')})" for t in templos]
        sel = st.selectbox("Selecciona cuál editar", nombres, key="sel_editar")
        t_edit = templos[nombres.index(sel)]
        st.divider()

        # Fotos actuales
        fotos_act = urls_validas(t_edit.get("fotos_urls"))
        if fotos_act:
            st.caption(f"📷 Fotos actuales ({len(fotos_act)}) — pulsa 🗑️ para eliminar:")
            for i, url in enumerate(fotos_act):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.image(url, use_container_width=True)
                with c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_foto_{t_edit['id']}_{i}"):
                        nueva = [u for j, u in enumerate(fotos_act) if j != i]
                        db.table("templos").update({"fotos_urls": nueva}).eq("id", t_edit["id"]).execute()
                        st.success("Foto eliminada.")
                        st.rerun()

        st.markdown("**➕ Añadir más fotos:**")
        fotos_new_up = st.file_uploader(
            "Selecciona fotos",
            type=["jpg","jpeg","png","webp"],
            accept_multiple_files=True,
            key="up_editar",
        )

        # Leer todos los bytes ANTES de mostrar el preview
        fotos_bytes_editar = []
        if fotos_new_up:
            for f in fotos_new_up:
                fotos_bytes_editar.append(f.read())
            cols_new = st.columns(min(len(fotos_bytes_editar), 4))
            for i, datos in enumerate(fotos_bytes_editar):
                with cols_new[i % 4]:
                    st.image(corregir_orientacion(datos), caption="Nueva", use_container_width=True)

        st.divider()
        nombre_e = st.text_input("Nombre *", value=t_edit.get("nombre",""), key="e_nombre")
        ciudad_e = st.text_input("Ciudad", value=t_edit.get("ciudad",""), key="e_ciudad")
        pais_e   = st.text_input("País", value=t_edit.get("pais",""), key="e_pais")
        cat_idx  = CATEGORIAS.index(t_edit["categoria"]) if t_edit.get("categoria") in CATEGORIAS else 0
        cat_e    = st.selectbox("Categoría", CATEGORIAS, index=cat_idx, key="e_cat")
        try:
            fecha_val = date.fromisoformat(t_edit.get("fecha", str(date.today())))
        except:
            fecha_val = date.today()
        fecha_e  = st.date_input("Fecha", value=fecha_val, key="e_fecha")
        notas_e  = st.text_area("Notas", value=t_edit.get("notas",""), height=180, key="e_notas")
        fav_e    = st.checkbox("⭐ Favorita", value=t_edit.get("favorita", False), key="e_fav")

        if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key="btn_editar"):
            if not nombre_e.strip():
                st.error("El nombre es obligatorio.")
            else:
                with st.spinner("Subiendo fotos nuevas..."):
                    urls_nuevas = []
                    for datos in fotos_bytes_editar:
                        try:
                            url = subir_foto(corregir_orientacion(datos))
                            urls_nuevas.append(url)
                        except Exception as e:
                            st.warning(f"No se pudo subir una foto: {e}")
                fotos_final = fotos_act + urls_nuevas
                actualizar({
                    "id": t_edit["id"],
                    "nombre": nombre_e, "ciudad": ciudad_e, "pais": pais_e,
                    "categoria": cat_e, "fecha": str(fecha_e),
                    "notas": notas_e, "favorita": fav_e,
                }, fotos_final)
                st.success(f"✅ '{nombre_e}' actualizado correctamente.")
                st.rerun()
