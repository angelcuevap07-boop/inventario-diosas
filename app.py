import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Guizado & Moda", layout="wide", page_icon="🛍️")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if u == "tienda" and p == "ventas2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# --- 2. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def cargar_datos():
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        
        # Mapeo de nombres de columnas para evitar errores
        mapeo = {
            'precio unidad': 'precio_unitario',
            'precio_unidad': 'precio_unitario',
            'precio mayor': 'precio_mayorista',
            'precio_mayor': 'precio_mayorista'
        }
        data = data.rename(columns=mapeo)
        
        # Asegurar columnas numéricas
        cols_num = ['stock', 'precio_unitario', 'precio_mayorista']
        for c in cols_num:
            if c not in data.columns:
                data[c] = 0
            data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
            
        return data

    df = cargar_datos()
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Control Maestro")
    modo = st.radio("Selecciona una opción:", 
                    ["📦 Ver/Editar Stock", "🚚 Traslado Inteligente", "🏭 Gestión Taller"])
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK (FILTRADO) ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    
    # Filtramos para no mostrar lo que está en 0
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        st.subheader(f"Inventario en {local_sel}")
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
