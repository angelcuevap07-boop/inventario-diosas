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
    modo = st.radio("Menú:", ["📦 Ver/Editar Stock", "🚚 Traslados Inteligentes", "🏭 Gestión Taller"])
    st.divider()
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['color'].upper()}** (S/{row['precio_unitario'] if 'precio_unitario' in df.columns else row['precio_unidad']})")
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

# --- 5. MODO: TRASLADOS INTELIGENTES (CON IA DE TEXTO/VOZ) ---
elif modo == "🚚 Traslados Inteligentes":
    st.header("🚚 Traslado con Procesamiento de Voz")
    st.info("💡 Haz clic abajo y usa el MICRÓFONO de tu teclado. Di: 'De taller a moda palazo talla ST negro 5'")
    instruccion = st.text_input("Dicta o escribe aquí la orden:").lower()

    # Variables para autocompletar
    s_orig, s_dest, s_prenda, s_talla, s_color, s_cant = None, None, None, None, None, 1

    if instruccion:
        # Detectar Origen y Destino
        for l in df['local'].unique():
            if f"de {l.lower()}" in instruccion: s_orig = l
            if f"a {l.lower()}" in instruccion: s_dest = l
        # Detectar Prenda
        for p in df['prenda'].unique():
            if p.lower() in instruccion: s_prenda = p
        # Detectar Talla
        for t in df['talla'].unique():
            if f"talla {t.lower()}" in instruccion or f" {t.lower()} " in instruccion: s_talla = t
        # Detectar Color
        for c in df['color'].unique():
            if c.lower() in instruccion: s_color = c
        # Detectar Cantidad
        nums = re.findall(r'\d+', instruccion)
        if nums: s_cant = int(nums[-1])

    st.divider()
    col1, col2 = st.columns(2)
    lista_locales = sorted(df['local'].unique())
    origen = col1.selectbox("Desde:", lista_locales, index=lista_locales.index(s_orig) if s_orig in lista_locales else 0)
    
    dest_posibles = [l for l in lista_locales if l != origen]
    destino = col2.selectbox("Hacia:", dest_posibles, 
                             index=dest_posibles.index(s_dest) if s_dest in dest_posibles else 0)
    
    df_orig = df[(df['local'] == origen) & (df['stock'] > 0)]
    
    if not df_orig.empty:
        prendas_list = sorted(df_orig['prenda'].unique())
        prenda_t = st.selectbox("Prenda:", prendas_list, index=prendas_list.index(s_prenda) if s_prenda in prendas_list else 0)
        
        df_prenda = df_orig[df_orig['prenda'] == prenda_t]
        tallas_list = sorted(df_prenda['talla'].unique())
        talla_t = st.selectbox("Talla:", tallas_list, index=tallas_list.index(s_talla) if s_talla in tallas_list else 0)
        
        colores_list = sorted(df_prenda[df_prenda['talla'] == talla_t]['color'].unique())
        color_t = st.selectbox("Color:", colores_list, index=colores_list.index(s_color) if s_color in colores_list else 0)
        
        fila_orig = df_prenda[(df_prenda['talla'] == talla_t) & (df_prenda['color'] == color_t)].iloc[0]
        st.warning(f"Stock disponible en {origen}: {int(fila_orig['stock'])}")
        
        cant = st.number_input("Cantidad a trasladar:", min_value=1, max_value=int(fila_orig['stock']), value=min(s_cant, int(fila_orig['stock'])))
        
        if st.button("🚀 Confirmar Traslado"):
            df.at[fila_orig.name, 'stock'] -= cant
            # Buscar en destino o crear
            idx_dest = df[(df['local'] == destino) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)].index
            if not idx_dest.empty:
                df.at[idx_dest[0], 'stock'] += cant
            else:
                nueva = {'local': destino, 'tela': fila_orig['tela'], 'prenda': prenda_t, 'talla': talla_t, 'color': color_t, 'stock': cant, 'precio_unidad': fila_orig['precio_unidad'], 'precio_mayor': fila_orig['precio_mayor']}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Traslado exitoso")
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("El local de origen no tiene mercadería disponible.")

# --- 6. MODO: GESTIÓN TALLER ---
else:
    st.header("🏭 Gestión de Producción - Taller")
    opcion_taller = st.tabs(["📥 Agregar a Existente", "➕ Crear Nueva Prenda"])
    
    with opcion_taller[0]:
        df_taller = df[df['local'] == "Taller"]
        if not df_taller.empty:
            p_ex = st.selectbox("Buscar Prenda:", sorted(df_taller['prenda'].unique()))
            df_p_ex = df_taller[df_taller['prenda'] == p_ex]
            t_ex = st.selectbox("Talla:", sorted(df_p_ex['talla'].unique()), key="t_ex")
            c_ex = st.selectbox("Color:", sorted(df_p_ex[df_p_ex['talla'] == t_ex]['color'].unique()), key="c_ex")
            cant_add = st.number_input("Cantidad:", min_value=1, value=12)
            if st.button("📥 Sumar al Taller"):
                idx_ex = df[(df['local'] == "Taller") & (df['prenda'] == p_ex) & (df['talla'] == t_ex) & (df['color'] == c_ex)].index[0]
                df.at[idx_ex, 'stock'] += cant_add
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Actualizado")
                st.cache_data.clear()
                st.rerun()

    with opcion_taller[1]:
        with st.form("crear_nueva"):
            c1, c2 = st.columns(2)
            np = c1.text_input("Modelo:").upper()
            nt = c2.text_input("Tela:", value="General")
            nta = st.selectbox("Talla:", ["ST", "S", "M", "L", "S/M"])
            nc = st.text_input("Color:").upper()
            ns = st.number_input("Cantidad:", min_value=1)
            pu = st.number_input("Precio Unidad:", min_value=0.0)
            if st.form_submit_button("➕ Crear y Registrar"):
                nf = {'local': 'Taller', 'tela': nt, 'prenda': np, 'talla': nta, 'color': nc, 'stock': ns, 'precio_unidad': pu, 'precio_mayor': 0}
                df = pd.concat([df, pd.DataFrame([nf])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Creado")
                st.cache_data.clear()
                st.rerun()
