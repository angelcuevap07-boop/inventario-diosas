import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Inventario Guizado", layout="wide")

# Verificación de Secrets rápida
if "connections" not in st.secrets:
    st.error("❌ Faltan los Secrets. Ve a Settings > Secrets y pega la configuración del Excel.")
    st.stop()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0)
    st.success("✅ ¡Conexión exitosa! Ya puedes entrar.")
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.info("Revisa que el enlace en Secrets sea correcto y que el Excel sea público (Cualquier persona con el enlace puede leer).")
    st.stop()

# (Aquí seguiría el resto del código de Login...)
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Guizado & Moda", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso</h2>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if u == "tienda" and p == "ventas2026":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# --- 2. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    def cargar_datos():
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        for col in ['stock', 'precio_unidad', 'precio_mayor']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    df = cargar_datos()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 3. MENÚ ---
with st.sidebar:
    st.title("🛍️ Gestión")
    modo = st.radio("Menú:", ["📦 Ver/Editar Stock", "🚚 Traslados por Voz", "🏭 Gestión Taller"])
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: TRASLADOS POR VOZ (NUEVA LÓGICA) ---
if modo == "🚚 Traslados por Voz":
    st.header("🚚 Traslado Inteligente (Voz / Texto)")
    st.info("🎙️ Usa el micrófono de tu teclado. Ejemplo: 'De taller a moda palazo talla ST negro 5'")
    
    voz = st.text_input("Dicta o escribe la instrucción:").lower()
    
    # Valores por defecto para los selectores
    sel_origen, sel_destino, sel_prenda, sel_talla, sel_color, sel_cant = None, None, None, None, None, 1

    if voz:
        # Lógica de detección simple
        locales = [l.lower() for l in df['local'].unique()]
        prendas = [p.lower() for p in df['prenda'].unique()]
        tallas = [t.lower() for t in df['talla'].unique()]
        colores = [c.lower() for c in df['color'].unique()]

        # Buscar origen y destino (De X a Y)
        match_locales = re.findall(r'(\w+)\s+a\s+(\w+)', voz)
        if match_locales:
            cand_orig, cand_dest = match_locales[0]
            if cand_orig in locales: sel_origen = cand_orig.capitalize()
            if cand_dest in locales: sel_destino = cand_dest.capitalize()

        # Buscar prenda
        for p in prendas:
            if p in voz: sel_prenda = p.upper(); break
        
        # Buscar talla
        for t in tallas:
            if f"talla {t}" in voz or f" {t} " in voz: sel_talla = t.upper(); break
            
        # Buscar color
        for c in colores:
            if c in voz: sel_color = c.upper(); break

        # Buscar cantidad (números aislados)
        match_cant = re.findall(r'\d+', voz)
        if match_cant: sel_cant = int(match_cant[-1])

    st.divider()

    # Formulario de confirmación (Se rellena solo con la voz)
    col1, col2 = st.columns(2)
    origen = col1.selectbox("Desde:", sorted(df['local'].unique()), 
                            index=sorted(df['local'].unique()).index(sel_origen) if sel_origen in df['local'].unique() else 0)
    destino = col2.selectbox("Hacia:", [l for l in sorted(df['local'].unique()) if l != origen],
                             index=0 if not sel_destino else ([l for l in sorted(df['local'].unique()) if l != origen].index(sel_destino) if sel_destino in [l for l in sorted(df['local'].unique()) if l != origen] else 0))
    
    df_orig = df[(df['local'] == origen) & (df['stock'] > 0)]
    prenda_t = st.selectbox("Prenda:", sorted(df_orig['prenda'].unique()),
                            index=sorted(df_orig['prenda'].unique()).index(sel_prenda) if sel_prenda in df_orig['prenda'].unique() else 0)
    
    df_p = df_orig[df_orig['prenda'] == prenda_t]
    talla_t = st.selectbox("Talla:", sorted(df_p['talla'].unique()),
                           index=sorted(df_p['talla'].unique()).index(sel_talla) if sel_talla in df_p['talla'].unique() else 0)
    
    color_t = st.selectbox("Color:", sorted(df_p[df_p['talla'] == talla_t]['color'].unique()),
                            index=sorted(df_p[df_p['talla'] == talla_t]['color'].unique()).index(sel_color) if sel_color in df_p[df_p['talla'] == talla_t]['color'].unique() else 0)
    
    fila_orig = df_orig[(df_orig['prenda'] == prenda_t) & (df_orig['talla'] == talla_t) & (df_orig['color'] == color_t)].iloc[0]
    st.warning(f"Stock disponible: {int(fila_orig['stock'])}")
    
    cant = st.number_input("Cantidad:", min_value=1, max_value=int(fila_orig['stock']), value=min(sel_cant, int(fila_orig['stock'])))
    
    if st.button("🚀 Confirmar Traslado"):
        idx_orig = fila_orig.name
        df.at[idx_orig, 'stock'] -= cant
        idx_dest = df[(df['local'] == destino) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)].index
        if not idx_dest.empty:
            df.at[idx_dest[0], 'stock'] += cant
        else:
            nueva = {'local': destino, 'tela': fila_orig['tela'], 'prenda': prenda_t, 'talla': talla_t, 'color': color_t, 'stock': cant, 'precio_unidad': fila_orig['precio_unidad'], 'precio_mayor': fila_orig['precio_mayor']}
            df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
        st.success("Traslado completado")
        st.cache_data.clear()
        st.rerun()

# --- (RESTO DEL CÓDIGO: VER STOCK Y GESTIÓN TALLER IGUAL QUE ANTES) ---
else:
    # ... (Pega aquí el código de Ver Stock y Taller que ya teníamos)
    st.write("Selecciona una opción en el menú lateral.")
