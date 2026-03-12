import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Guizado & Moda", layout="wide")

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

# --- 3. MENÚ PRINCIPAL ---
with st.sidebar:
    st.title("🛍️ Control Maestro")
    modo = st.radio("Menú:", ["📦 Ver/Editar Stock", "🚚 Traslados", "🏭 Gestión Taller"])
    st.divider()
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK (FILTRADO) ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    # Filtramos solo lo que tiene stock > 0
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        # Mostramos solo colores con stock > 0
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['color'].upper()}** (S/{row['precio_unidad']})")
            c2.metric("Stock", int(row['stock']))
            ajuste = c3.number_input("Ajuste", value=0, key=f"v_{idx}")
            if st.button("Actualizar", key=f"b_{idx}"):
                df.at[idx, 'stock'] += ajuste
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Guardado")
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("No hay stock disponible en este local.")

# --- 5. MODO: TRASLADOS (FILTRADO) ---
elif modo == "🚚 Traslados":
    st.header("🚚 Mover Mercadería")
    col1, col2 = st.columns(2)
    origen = col1.selectbox("Desde:", sorted(df['local'].unique()))
    destino = col2.selectbox("Hacia:", [l for l in sorted(df['local'].unique()) if l != origen])
    
    # Solo mostrar prendas que tengan stock real en origen
    df_orig = df[(df['local'] == origen) & (df['stock'] > 0)]
    prendas_t = sorted(df_orig['prenda'].unique())
    
    if prendas_t:
        prenda_t = st.selectbox("Prenda:", prendas_t)
        df_prenda_t = df_orig[df_orig['prenda'] == prenda_t]
        talla_t = st.selectbox("Talla:", sorted(df_prenda_t['talla'].unique()))
        color_t = st.selectbox("Color:", sorted(df_prenda_t[df_prenda_t['talla'] == talla_t]['color'].unique()))
        
        fila_orig = df_orig[(df_orig['prenda'] == prenda_t) & (df_orig['talla'] == talla_t) & (df_orig['color'] == color_t)].iloc[0]
        stock_max = int(fila_orig['stock'])
        
        cant = st.number_input("Cantidad:", min_value=1, max_value=stock_max, value=1)
        if st.button("Confirmar Traslado"):
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
    else:
        st.error("Este local no tiene mercadería para trasladar.")

# --- 6. MODO: GESTIÓN TALLER (AGREGAR VS CREAR) ---
else:
    st.header("🏭 Gestión de Producción - Taller")
    opcion_taller = st.tabs(["📥 Agregar a Existente", "➕ Crear Nueva Prenda"])
    
    with opcion_taller[0]:
        st.subheader("Reponer stock de prendas actuales")
        df_taller = df[df['local'] == "Taller"]
        if not df_taller.empty:
            p_existente = st.selectbox("Buscar Prenda en Taller:", sorted(df_taller['prenda'].unique()))
            df_p_ex = df_taller[df_taller['prenda'] == p_existente]
            t_existente = st.selectbox("Talla:", sorted(df_p_ex['talla'].unique()), key="t_ex")
            c_existente = st.selectbox("Color:", sorted(df_p_ex[df_p_ex['talla'] == t_existente]['color'].unique()), key="c_ex")
            
            cant_add = st.number_input("Cantidad a agregar:", min_value=1, value=10)
            if st.button("📥 Sumar al Taller"):
                idx_ex = df[(df['local'] == "Taller") & (df['prenda'] == p_existente) & (df['talla'] == t_existente) & (df['color'] == c_existente)].index[0]
                df.at[idx_ex, 'stock'] += cant_add
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Stock actualizado correctamente")
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("No hay prendas en el taller para reponer.")

    with opcion_taller[1]:
        st.subheader("Registrar nuevo modelo o color")
        with st.form("crear_nueva"):
            c1, c2 = st.columns(2)
            n_prenda = c1.text_input("Modelo:").upper()
            n_tela = c2.text_input("Tela:", value="General")
            c3, c4 = st.columns(2)
            n_talla = c3.selectbox("Talla:", ["ST", "S", "M", "L", "S/M"])
            n_color = c4.text_input("Color:").upper()
            c5, c6, c7 = st.columns(3)
            n_stock = c5.number_input("Cantidad:", min_value=1)
            n_uni = c6.number_input("Precio Unidad:", min_value=0.0)
            n_may = c7.number_input("Precio Mayor:", min_value=0.0)
            
            if st.form_submit_button("➕ Crear y Registrar"):
                nueva_f = {'local': 'Taller', 'tela': n_tela, 'prenda': n_prenda, 'talla': n_talla, 'color': n_color, 'stock': n_stock, 'precio_unidad': n_uni, 'precio_mayor': n_may}
                df = pd.concat([df, pd.DataFrame([nueva_f])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Nueva prenda registrada")
                st.cache_data.clear()
                st.rerun()
