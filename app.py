import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

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
    st.stop()

# --- 2. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def cargar_datos():
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        
        # Mapeo de columnas
        mapeo = {
            'precio unidad': 'precio_unitario',
            'precio_unidad': 'precio_unitario',
            'precio mayor': 'precio_mayorista',
            'precio_mayor': 'precio_mayorista'
        }
        data = data.rename(columns=mapeo)
        
        cols_num = ['stock', 'precio_unitario', 'precio_mayorista']
        for c in cols_num:
            if c not in data.columns:
                data[c] = 0
            data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
            
        return data

    df = cargar_datos()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Panel Control")
    modo = st.radio("Menú:", ["📦 Ver/Editar Stock", "🚚 Traslados", "🏭 Gestión Taller"])
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Local:", sorted(df['local'].unique()))
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['color'].upper()}** (S/{row['precio_unitario']})")
            c2.metric("Stock", int(row['stock']))
            adj = c3.number_input("Venta/Ajuste", value=0, key=f"v_{idx}")
            if st.button("Guardar", key=f"b_{idx}"):
                df.at[idx, 'stock'] += adj
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("¡Hecho!")
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("No hay stock en este local.")

# --- 5. MODO: TRASLADOS (Dictado por Voz del teclado) ---
elif modo == "🚚 Traslados":
    st.header("🚚 Traslado Inteligente")
    st.info("💡 Usa el micrófono de tu teclado en el cuadro de abajo. Ej: 'De taller a moda palazo talla ST negro 5'")
    instruccion = st.text_input("Escribe o dicta aquí:").lower()

    s_orig, s_dest, s_prenda, s_talla, s_color, s_cant = None, None, None, None, None, 1
    if instruccion:
        for l in df['local'].unique():
            if f"de {l.lower()}" in instruccion: s_orig = l
            if f"a {l.lower()}" in instruccion: s_dest = l
        for p in df['prenda'].unique():
            if p.lower() in instruccion: s_prenda = p
        for t in df['talla'].unique():
            if f"talla {t.lower()}" in instruccion or f" {t.lower()} " in instruccion: s_talla = t
        for c in df['color'].unique():
            if c.lower() in instruccion: s_color = c
        n = re.findall(r'\d+', instruccion)
        if n: s_cant = int(n[-1])

    st.divider()
    col1, col2 = st.columns(2)
    lista_locales = sorted(df['local'].unique())
    origen = col1.selectbox("Desde:", lista_locales, 
                            index=lista_locales.index(s_orig) if s_orig in lista_locales else 0)
    
    dest_disp = [l for l in lista_locales if l != origen]
    destino = col2.selectbox("Hacia:", dest_disp,
                             index=dest_disp.index(s_dest) if s_dest in dest_disp else 0)
    
    df_o = df[(df['local'] == origen) & (df['stock'] > 0)]
    if not df_o.empty:
        p_disp = sorted(df_o['prenda'].unique())
        p_t = st.selectbox("Prenda:", p_disp, index=p_disp.index(s_prenda) if s_prenda in p_disp else 0)
        df_p = df_o[df_o['prenda'] == p_t]
        t_disp = sorted(df_p['talla'].unique())
        t_t = st.selectbox("Talla:", t_disp, index=t_disp.index(s_talla) if s_talla in t_disp else 0)
        c_disp = sorted(df_p[df_p['talla'] == t_t]['color'].unique())
        c_t = st.selectbox("Color:", c_disp, index=c_disp.index(s_color) if s_color in c_disp else 0)
        
        f_o = df_p[(df_p['talla'] == t_t) & (df_p['color'] == c_t)].iloc[0]
        cant = st.number_input("Cantidad:", min_value=1, max_value=int(f_o['stock']), value=min(s_cant, int(f_o['stock'])))
        
        if st.button("Confirmar Traslado"):
            df.at[f_o.name, 'stock'] -= cant
            idx_d = df[(df['local'] == destino) & (df['prenda'] == p_t) & (df['talla'] == t_t) & (df['color'] == c_t)].index
            if not idx_d.empty:
                df.at[idx_d[0], 'stock'] += cant
            else:
                nueva = {'local': destino, 'tela': f_o['tela'], 'prenda': p_t, 'talla': t_t, 'color': c_t, 'stock': cant, 'precio_unitario': f_o['precio_unitario'], 'precio_mayorista': f_o['precio_mayorista']}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Traslado exitoso")
            st.cache_data.clear()
            st.rerun()

# --- 6. GESTIÓN TALLER ---
else:
    st.header("🏭 Producción Taller")
    t1, t2 = st.tabs(["📥 Agregar Stock", "➕ Nueva Prenda"])
    with t1:
        df_t = df[df['local'] == "Taller"]
        if not df_t.empty:
            p_taller = st.selectbox("Modelo:", sorted(df_t['prenda'].unique()))
            df_pt = df_t[df_t['prenda'] == p_taller]
            t_taller = st.selectbox("Talla:", sorted(df_pt['talla'].unique()))
            c_taller = st.selectbox("Color:", sorted(df_pt[df_pt['talla'] == t_taller]['color'].unique()))
            n_taller = st.number_input("Cantidad Producida:", min_value=1, value=12)
            if st.button("Sumar Stock"):
                idx_t = df[(df['local'] == "Taller") & (df['prenda'] == p_taller) & (df['talla'] == t_taller) & (df['color'] == c_taller)].index[0]
                df.at[idx_t, 'stock'] += n_taller
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Stock actualizado")
                st.cache_data.clear()
                st.rerun()
    with t2:
        with st.form("crear"):
            c1, c2 = st.columns(2)
            np = c1.text_input("Nombre:").upper()
            nt = c2.text_input("Tela:", value="General")
            c3, c4 = st.columns(2)
            nta = c3.selectbox("Talla:", ["ST", "S", "M", "L", "S/M"])
            nc = c4.text_input("Color:").upper()
            c5, c6 = st.columns(2)
            ns = c5.number_input("Stock:", min_value=1)
            pu = c6.number_input("Precio:", min_value=0.0)
            if st.form_submit_button("Crear"):
                nf = {'local': 'Taller', 'tela': nt, 'prenda': np, 'talla': nta, 'color': nc, 'stock': ns, 'precio_unitario': pu, 'precio_mayorista': 0}
                df = pd.concat([df, pd.DataFrame([nf])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Nueva prenda creada")
                st.cache_data.clear()
                st.rerun()
