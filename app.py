import streamlit as st
from datetime import date
import os, io, uuid, html as html_lib
from urllib.parse import quote
from PIL import Image, ImageOps
from supabase import create_client

# ── Conexión a Supabase ───────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

db = get_client()

# ── Categorías ────────────────────────────────────────────────────
CATEGORIAS = [
    "Iglesia", "Catedral", "Basílica", "Capilla",
    "Monasterio", "Templo Budista", "Templo Hindú",
    "Templo Sintoísta", "Mezquita", "Sinagoga",
    "Santuario", "Otro",
]

# ── Utilidades de imagen ──────────────────────────────────────────
def corregir_orientacion(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes))
    img = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()

def subir_foto(imagen_bytes):
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

def maps_url(direccion):
    return f"https://www.google.com/maps/search/?api=1&query={quote(direccion)}"

# ── CRUD Supabase ─────────────────────────────────────────────────
def cargar():
    res = db.table("templos").select("*").order("fecha", desc=True).execute()
    return res.data or []

def guardar_nuevo(ig, fotos_urls):
    db.table("templos").insert({
        "nombre":     ig["nombre"],
        "ciudad":     ig["ciudad"],
        "pais":       ig["pais"],
        "direccion":  ig["direccion"],
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
        "direccion":  ig["direccion"],
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

html, body, [class*="css"] { font-family: 'Lato', sans-serif; }
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
.notas-texto {
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow: visible !important;
    max-height: none !important;
    font-size: 0.95rem;
    line-height: 1.6;
    padding: 0.5rem 0;
}
.maps-link a {
    color: #b8883a !important;
    text-decoration: none;
    font-size: 0.85rem;
}
.maps-link a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
if "lightbox" not in st.session_state:
    st.session_state.lightbox = None

# ── Lightbox ──────────────────────────────────────────────────────
if st.session_state.lightbox:
    fotos_lb = st.session_state.get("lightbox_fotos", [st.session_state.lightbox])
    idx = st.session_state.get("lightbox_idx", 0)
    st.markdown(f"### 🖼️ Foto {idx + 1} de {len(fotos_lb)}")
    st.image(fotos_lb[idx], use_container_width=True)
    col_prev, col_cerrar, col_next = st.columns([1, 2, 1])
    with col_prev:
        if idx > 0:
            if st.button("◀ Anterior"):
                st.session_state.lightbox_idx = idx - 1
                st.session_state.lightbox = fotos_lb[idx - 1]
                st.rerun()
    with col_cerrar:
        if st.button("✕ Cerrar", use_container_width=True):
            st.session_state.lightbox = None
            st.session_state.lightbox_fotos = []
            st.session_state.lightbox_idx = 0
            st.rerun()
    with col_next:
        if idx < len(fotos_lb) - 1:
            if st.button("Siguiente ▶"):
                st.session_state.lightbox_idx = idx + 1
                st.session_state.lightbox = fotos_lb[idx + 1]
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

# ── Helper fotos ──────────────────────────────────────────────────
def mostrar_miniaturas(fotos, clave):
    fotos = urls_validas(fotos)
    if not fotos:
        return
    st.image(fotos[0], width=150)
    if st.button(f"🖼️ Ver fotos ({len(fotos)})", key=f"lb_{clave}"):
        st.session_state.lightbox = fotos[0]
        st.session_state.lightbox_fotos = fotos
        st.session_state.lightbox_idx = 0
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
        cats_filtro = ["Todas"] + CATEGORIAS
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
                    if t.get("direccion"):
                        dir_escaped = html_lib.escape(t["direccion"])
                        url = maps_url(t["direccion"])
                        st.markdown(
                            f'<div class="maps-link">🗺️ <a href="{url}" target="_blank">{dir_escaped}</a></div>',
                            unsafe_allow_html=True
                        )
                with col_btns:
                    if st.button("🗑️", key=f"del_{t['id']}", help="Eliminar"):
                        eliminar(t["id"])
                        st.rerun()
                    if st.button("★" if t.get("favorita") else "☆", key=f"fav_{t['id']}"):
                        toggle_fav(t)
                        st.rerun()
                if t.get("notas"):
                    notas_escaped = html_lib.escape(t["notas"])
                    st.markdown(
                        f'<p class="notas-texto">{notas_escaped}</p>',
                        unsafe_allow_html=True
                    )
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

    fotos_bytes_nueva = []
    if fotos_up:
        for f in fotos_up:
            fotos_bytes_nueva.append(f.read())
        prev = st.columns(min(len(fotos_bytes_nueva), 4))
        for i, datos in enumerate(fotos_bytes_nueva):
            with prev[i % 4]:
                st.image(corregir_orientacion(datos), use_container_width=True)

    nombre    = st.text_input("Nombre del templo *", placeholder="Ej: Catedral de Burgos", key="n_nombre")
    ciudad    = st.text_input("Ciudad", placeholder="Ej: Burgos", key="n_ciudad")
    pais      = st.text_input("País", placeholder="Ej: España", key="n_pais")
    direccion = st.text_input("Dirección", placeholder="Ej: Pl. de la Catedral, s/n, Burgos", key="n_direccion")
    cat       = st.selectbox("Categoría", CATEGORIAS, key="n_cat")
    fecha     = st.date_input("Fecha de visita", value=date.today(), key="n_fecha")
    notas     = st.text_area("Notas personales", placeholder="Tus impresiones...", height=180, key="n_notas")
    fav       = st.checkbox("⭐ Marcar como favorita", key="n_fav")

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
                "direccion": direccion, "categoria": cat, "fecha": str(fecha),
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

        # Fotos actuales en miniaturas lado a lado
        fotos_act = urls_validas(t_edit.get("fotos_urls"))
        if fotos_act:
            st.caption(f"📷 Fotos actuales ({len(fotos_act)}) — pulsa 🗑️ para eliminar:")
            cols_fotos = st.columns(min(len(fotos_act), 4))
            for i, url in enumerate(fotos_act):
                with cols_fotos[i % 4]:
                    st.image(url, width=140)
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

        fotos_bytes_editar = []
        if fotos_new_up:
            for f in fotos_new_up:
                fotos_bytes_editar.append(f.read())
            cols_new = st.columns(min(len(fotos_bytes_editar), 4))
            for i, datos in enumerate(fotos_bytes_editar):
                with cols_new[i % 4]:
                    st.image(corregir_orientacion(datos), width=140, caption="Nueva")

        st.divider()

        # Campos del formulario — usan el id del templo en la key para forzar reset al cambiar
        tid = t_edit["id"]
        cat_idx = CATEGORIAS.index(t_edit["categoria"]) if t_edit.get("categoria") in CATEGORIAS else 0
        try:
            fecha_val = date.fromisoformat(t_edit.get("fecha", str(date.today())))
        except:
            fecha_val = date.today()

        nombre_e    = st.text_input("Nombre *",    value=t_edit.get("nombre",""),         key=f"e_nombre_{tid}")
        ciudad_e    = st.text_input("Ciudad",      value=t_edit.get("ciudad",""),          key=f"e_ciudad_{tid}")
        pais_e      = st.text_input("País",        value=t_edit.get("pais",""),            key=f"e_pais_{tid}")
        direccion_e = st.text_input("Dirección",   value=t_edit.get("direccion","") or "", key=f"e_direccion_{tid}")
        cat_e       = st.selectbox("Categoría", CATEGORIAS, index=cat_idx,                 key=f"e_cat_{tid}")
        fecha_e     = st.date_input("Fecha",       value=fecha_val,                        key=f"e_fecha_{tid}")
        notas_e     = st.text_area("Notas", height=180,
                                   value=t_edit.get("notas","") or "",                     key=f"e_notas_{tid}")
        fav_e       = st.checkbox("⭐ Favorita",   value=t_edit.get("favorita", False),    key=f"e_fav_{tid}")

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
                    "direccion": direccion_e, "categoria": cat_e, "fecha": str(fecha_e),
                    "notas": notas_e, "favorita": fav_e,
                }, fotos_final)
                st.success(f"✅ '{nombre_e}' actualizado correctamente.")
                st.rerun()
