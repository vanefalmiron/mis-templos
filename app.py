import streamlit as st
from datetime import date
import os, io, uuid, html as html_lib
from urllib.parse import quote
from PIL import Image, ImageOps
from supabase import create_client
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Photon
from geopy.exc import GeocoderTimedOut, GeocoderRateLimited
import time

# ── Conexión a Supabase ───────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

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

ESTILOS = [
    "Antigua Roma", "Medieval",
    "Románico", "Gótico", "Gótico radiante", "Barroco", "Renacentista",
    "Mudéjar", "Neoclásico", "Bizantino", "Hispanorromanos",
    "Islámico", "Moderno / Contemporáneo",
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

def geocodificar(direccion, ciudad, pais):
    """Devuelve (lat, lon) o (None, None) si falla."""
    if not any([direccion, ciudad, pais]):
        return None, None
    # Intenta primero con dirección completa, luego solo ciudad+país
    queries = []
    if direccion and ciudad and pais:
        queries.append(", ".join(filter(None, [direccion, ciudad, pais])))
    if ciudad and pais:
        queries.append(f"{ciudad}, {pais}")
    elif pais:
        queries.append(pais)

    geolocator = Photon(user_agent="mis_templos_app")
    for query in queries:
        try:
            time.sleep(0.5)
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderRateLimited):
            time.sleep(2)
        except Exception:
            pass
    return None, None

# ── CRUD Supabase ─────────────────────────────────────────────────
def cargar():
    res = db.table("templos").select("*").order("fecha", desc=True).execute()
    return res.data or []

def guardar_nuevo(ig, fotos_urls):
    lat, lon = geocodificar(ig.get("direccion"), ig.get("ciudad"), ig.get("pais"))
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
        "lat":        lat,
        "lon":        lon,
        "estilos":    ig.get("estilos", []),
    }).execute()

def actualizar(ig, fotos_urls):
    lat, lon = geocodificar(ig.get("direccion"), ig.get("ciudad"), ig.get("pais"))
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
        "lat":        lat,
        "lon":        lon,
        "estilos":    ig.get("estilos", []),
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
.temple-header { text-align: center; padding: 0.5rem 0 0.5rem; }
.temple-pediment {
    width: 0; height: 0;
    border-left: 90px solid transparent;
    border-right: 90px solid transparent;
    border-bottom: 24px solid #b8883a33;
    margin: 0 auto;
    position: relative;
}
.temple-pediment::after {
    content: '';
    position: absolute;
    left: -90px; top: 0;
    width: 180px; height: 0;
    border-bottom: 2px solid #b8883a66;
}
.temple-frieze {
    display: flex; justify-content: center; align-items: stretch;
    width: 180px; margin: 0 auto;
    background: linear-gradient(180deg, #b8883a22, #b8883a08);
    border-left: 1px solid #b8883a55; border-right: 1px solid #b8883a55;
    padding: 4px 8px; gap: 6px;
}
.temple-dentil {
    width: 7px; height: 10px;
    background: #b8883a55; border-radius: 1px 1px 0 0; flex-shrink: 0;
}
.temple-colonnade {
    display: flex; justify-content: center; align-items: stretch;
    margin: 0 auto; gap: 0;
}
.temple-col-shaft {
    width: 10px; flex-shrink: 0;
    background: linear-gradient(90deg, #b8883a0a, #b8883a22, #b8883a0a);
    border-left: 1px solid #b8883a44; border-right: 1px solid #b8883a44;
}
.temple-inner {
    padding: 0.6rem 1.8rem 0.4rem; min-width: 160px;
}
.temple-title {
    font-family: 'Cinzel', serif;
    font-size: 2.2rem; font-weight: 600;
    color: #b8883a;
    letter-spacing: 0.35em; text-transform: uppercase;
    margin: 0; line-height: 1.1;
    text-shadow: 0 2px 24px rgba(184,136,58,0.25);
}
.temple-ornament { color: #b8883a66; font-size: 0.65rem; letter-spacing: 0.55em; margin: 0.25rem 0; }
.temple-subtitle {
    font-size: 0.7rem; color: #a08060;
    letter-spacing: 0.2em; text-transform: uppercase; margin-top: 0.3rem;
}
.temple-step { margin: 0 auto; height: 5px; border-bottom: 1px solid #b8883a44; }
.temple-step-1 { width: 180px; }
.temple-step-2 { width: 160px; border-bottom-color: #b8883a33; }
.temple-step-3 { width: 140px; border-bottom-color: #b8883a1a; }
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

/* ── RESPONSIVE ─────────────────────────────────────── */

/* Tablet (≤768px) */
@media (max-width: 768px) {
    .temple-title       { font-size: 1.7rem; letter-spacing: 0.2em; }
    .temple-inner       { padding: 0.5rem 1.2rem 0.3rem; min-width: 120px; }
    .metric-card .num   { font-size: 1.5rem; }
    .metric-card .label { font-size: 0.68rem; }
    .metric-card        { padding: 0.7rem 0.4rem; }
    .temple-step-1      { width: 150px; }
    .temple-step-2      { width: 130px; }
    .temple-step-3      { width: 110px; }
}

/* Móvil (≤480px) */
@media (max-width: 480px) {
    .temple-title    { font-size: clamp(0.9rem, 6vw, 1.2rem); letter-spacing: 0.06em; white-space: nowrap; }
    .temple-subtitle { font-size: 0.55rem; letter-spacing: 0.06em; white-space: nowrap; }
    .temple-ornament { letter-spacing: 0.2em; }
    .temple-inner    { padding: 0.4rem 0.6rem 0.25rem; min-width: 0; }
    .temple-frieze   { width: 120px; padding: 3px 4px; gap: 3px; }
    .temple-dentil   { width: 5px; height: 8px; }
    .temple-pediment { border-left-width: 60px; border-right-width: 60px; border-bottom-width: 18px; }
    .temple-step-1   { width: 120px; }
    .temple-step-2   { width: 100px; }
    .temple-step-3   { width: 80px;  }
    .metric-card        { padding: 0.5rem 0.2rem; border-radius: 7px; }
    .metric-card .num   { font-size: 1.2rem; }
    .metric-card .label { font-size: 0.6rem; letter-spacing: 0.05em; }
    [data-testid="stImage"] img { max-width: 100% !important; height: auto !important; }
    .notas-texto { font-size: 0.85rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.7rem; padding: 6px 8px !important; letter-spacing: 0; }
}
</style>
<!-- Viewport meta: esencial para que los media queries funcionen en móvil -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
if "lightbox" not in st.session_state:
    st.session_state.lightbox = None
if "admin" not in st.session_state:
    st.session_state.admin = False

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
st.markdown("""
<div class="temple-header">
    <div class="temple-pediment"></div>
    <div class="temple-frieze">
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
        <div class="temple-dentil"></div><div class="temple-dentil"></div>
    </div>
    <div class="temple-colonnade">
        <div class="temple-col-shaft"></div>
        <div class="temple-inner">
            <div class="temple-ornament">✦ &nbsp;&nbsp;&nbsp; ✦ &nbsp;&nbsp;&nbsp; ✦</div>
            <div class="temple-title">Mis&nbsp;Templos</div>
            <div class="temple-ornament">✦ &nbsp;&nbsp;&nbsp; ✦ &nbsp;&nbsp;&nbsp; ✦</div>
            <div class="temple-subtitle">Registro personal de lugares sagrados visitados</div>
        </div>
        <div class="temple-col-shaft"></div>
    </div>
    <div class="temple-step temple-step-1"></div>
    <div class="temple-step temple-step-2"></div>
    <div class="temple-step temple-step-3"></div>
</div>
""", unsafe_allow_html=True)
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
    n_cols = min(len(fotos), 4)
    cols = st.columns(n_cols)
    for i, url in enumerate(fotos):
        with cols[i % n_cols]:
            st.image(url, use_container_width=True)
    if st.button(f"🖼️ Ver fotos ({len(fotos)})", key=f"lb_{clave}"):
        st.session_state.lightbox = fotos[0]
        st.session_state.lightbox_fotos = fotos
        st.session_state.lightbox_idx = 0
        st.rerun()

# ── Tabs — solo admin ve Añadir y Editar ──────────────────────────
if st.session_state.admin:
    tab_lista, tab_mapa, tab_nueva, tab_editar = st.tabs(["📋 Mi lista", "🗺️ Mapa", "➕ Añadir", "✏️ Editar"])
else:
    tab_lista, tab_mapa = st.tabs(["📋 Mi lista", "🗺️ Mapa"])

# ════════════════════════════════════════════════════
# TAB LISTA
# ════════════════════════════════════════════════════
with tab_lista:
    if not templos:
        st.info("Aún no tienes ningún templo registrado.")
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
                col_info, col_btns = st.columns([6, 1])
                with col_info:
                    fav = "⭐" if t.get("favorita") else "☆"
                    st.subheader(f"{fav} {t.get('nombre','')}")
                    estilos_str = ("  |  🏛️ " + " · ".join(t["estilos"])) if t.get("estilos") else ""
                    anio = str(t.get("fecha","")) if t.get("fecha") else ""
                    st.caption(
                        f"📍 {t.get('ciudad','')}, {t.get('pais','')}  |  "
                        f"🏷️ {t.get('categoria','')}"
                        f"{estilos_str}"
                        f"{'  |  🏗️ ' + anio if anio else ''}"
                    )
                    if t.get("direccion"):
                        dir_escaped = html_lib.escape(t["direccion"])
                        url = maps_url(t["direccion"])
                        st.markdown(
                            f'<div class="maps-link">🗺️ <a href="{url}" target="_blank">{dir_escaped}</a></div>',
                            unsafe_allow_html=True
                        )
                # Botones eliminar/favorito solo para admin
                with col_btns:
                    if st.session_state.admin:
                        if st.button("🗑️", key=f"del_{t['id']}", help="Eliminar"):
                            eliminar(t["id"])
                            st.rerun()
                    if st.button("★" if t.get("favorita") else "☆", key=f"fav_{t['id']}"):
                        if st.session_state.admin:
                            toggle_fav(t)
                            st.rerun()
                # Fotos debajo de la dirección
                st.markdown("<br>", unsafe_allow_html=True)
                mostrar_miniaturas(fotos, t["id"])
                if t.get("notas"):
                    notas_escaped = html_lib.escape(t["notas"])
                    st.markdown(
                        f'<p class="notas-texto">{notas_escaped}</p>',
                        unsafe_allow_html=True
                    )
            st.markdown("---")

    # ── Login / Logout ────────────────────────────────────────────
    st.divider()
    if not st.session_state.admin:
        with st.expander("🔐 Acceso administrador"):
            pwd = st.text_input("Contraseña", type="password", key="pwd_input")
            if st.button("Entrar", key="btn_login"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
    else:
        if st.button("🔓 Cerrar sesión"):
            st.session_state.admin = False
            st.rerun()

# ════════════════════════════════════════════════════
# TAB MAPA
# ════════════════════════════════════════════════════
with tab_mapa:
    templos_mapa = cargar()  # recarga fresca para el mapa
    con_coords = [t for t in templos_mapa if t.get("lat") and t.get("lon")]
    sin_coords  = [t for t in templos_mapa if not t.get("lat") or not t.get("lon")]

    # Botón admin para geocodificar todos los que faltan
    if st.session_state.admin and sin_coords:
        st.warning(f"{len(sin_coords)} templo(s) sin coordenadas en el mapa.")
        if st.button("📍 Geocodificar todos", type="primary"):
            resultados = []
            progreso = st.progress(0, text="Geocodificando...")
            ok, fallo = 0, 0
            for i, t in enumerate(sin_coords):
                query = ", ".join(filter(None, [t.get("direccion"), t.get("ciudad"), t.get("pais")]))
                lat, lon = geocodificar(t.get("direccion"), t.get("ciudad"), t.get("pais"))
                if lat and lon:
                    db.table("templos").update({"lat": lat, "lon": lon}).eq("id", t["id"]).execute()
                    resultados.append(f"✅ {t.get('nombre','')} → {lat:.4f}, {lon:.4f}")
                    ok += 1
                else:
                    resultados.append(f"❌ {t.get('nombre','')} — no encontrado (query: {query})")
                    fallo += 1
                progreso.progress((i + 1) / len(sin_coords), text=f"Procesando {t.get('nombre','')}")
            progreso.empty()
            for r in resultados:
                st.write(r)
            st.success(f"✅ {ok} geocodificados.{f' ⚠️ {fallo} fallaron.' if fallo else ''}")
            if ok > 0:
                st.rerun()

    if not con_coords:
        st.info("Aún no hay templos con ubicación. Pulsa el botón de arriba para geocodificar los existentes.")
    else:
        m = folium.Map(
            location=[con_coords[0]["lat"], con_coords[0]["lon"]],
            zoom_start=5,
            tiles="CartoDB dark_matter",
        )
        for t in con_coords:
            fotos = urls_validas(t.get("fotos_urls"))
            img_html = f'<img src="{fotos[0]}" width="160" style="border-radius:6px;margin-bottom:6px;"><br>' if fotos else ""
            fav = "⭐ " if t.get("favorita") else ""
            popup_html = (
                f'<div style="font-family:serif;min-width:180px">' +
                img_html +
                f'<b style="font-size:1rem">{fav}{html_lib.escape(t.get("nombre",""))}</b><br>' +
                f'<span style="color:#888;font-size:0.8rem">{html_lib.escape(t.get("ciudad",""))}, {html_lib.escape(t.get("pais",""))}</span><br>' +
                f'<span style="font-size:0.75rem">{html_lib.escape(t.get("categoria",""))}</span>' +
                '</div>'
            )
            folium.Marker(
                location=[t["lat"], t["lon"]],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=t.get("nombre", ""),
                icon=folium.Icon(color="orange", icon="place-of-worship", prefix="fa"),
            ).add_to(m)

        st_folium(m, use_container_width=True, height=500)

        if sin_coords:
            st.caption(f"⚠️ {len(sin_coords)} templo(s) sin coordenadas — éditalos para que aparezcan en el mapa.")

if st.session_state.admin:
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
        fecha     = st.text_input("📅 Año de construcción", placeholder="Ej: 1456, Siglo XII, 220 d.C", key="n_fecha")
        notas     = st.text_area("Notas personales", placeholder="Tus impresiones...", height=180, key="n_notas")
        estilos   = st.multiselect("🏛️ Estilo arquitectónico", ESTILOS, key="n_estilos")
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
                    "direccion": direccion, "categoria": cat, "fecha": fecha,
                    "notas": notas, "favorita": fav, "estilos": estilos,
                }, urls)
                st.success(f"✅ '{nombre}' guardado correctamente.")
                st.balloons()
                st.rerun()

    # ════════════════════════════════════════════════════
    # TAB EDITAR (solo admin)
    # ════════════════════════════════════════════════════
    with tab_editar:
        if not templos:
            st.info("Aún no hay templos para editar.")
        else:
            nombres = [f"{t['nombre']} ({t.get('ciudad','')})" for t in templos]
            sel = st.selectbox("Selecciona cuál editar", nombres, key="sel_editar")
            t_edit = templos[nombres.index(sel)]

            st.divider()

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

            tid = t_edit["id"]
            cat_idx = CATEGORIAS.index(t_edit["categoria"]) if t_edit.get("categoria") in CATEGORIAS else 0
            fecha_val = str(t_edit.get("fecha", "") or "")

            nombre_e    = st.text_input("Nombre *",    value=t_edit.get("nombre",""),         key=f"e_nombre_{tid}")
            ciudad_e    = st.text_input("Ciudad",      value=t_edit.get("ciudad",""),          key=f"e_ciudad_{tid}")
            pais_e      = st.text_input("País",        value=t_edit.get("pais",""),            key=f"e_pais_{tid}")
            direccion_e = st.text_input("Dirección",   value=t_edit.get("direccion","") or "", key=f"e_direccion_{tid}")
            cat_e       = st.selectbox("Categoría", CATEGORIAS, index=cat_idx,                 key=f"e_cat_{tid}")
            fecha_e     = st.text_input("📅 Año de construcción", value=fecha_val, placeholder="Ej: 1456, Siglo XII, 220 d.C", key=f"e_fecha_{tid}")
            notas_e     = st.text_area("Notas", height=180,
                                       value=t_edit.get("notas","") or "",                     key=f"e_notas_{tid}")
            estilos_e   = st.multiselect("🏛️ Estilo arquitectónico", ESTILOS,
                                        default=[s for s in (t_edit.get("estilos") or []) if s in ESTILOS],
                                        key=f"e_estilos_{tid}")
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
                        "direccion": direccion_e, "categoria": cat_e, "fecha": fecha_e,
                        "notas": notas_e, "favorita": fav_e, "estilos": estilos_e,
                    }, fotos_final)
                    st.success(f"✅ '{nombre_e}' actualizado correctamente.")
                    st.rerun()
