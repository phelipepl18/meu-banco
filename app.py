import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        if df is not None and not df.empty:
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- FUNÇÃO PARA FORMATAR MOEDA BRASIL (R$ 2.550,00) ---
def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- FUNÇÃO PARA COLORIR O EXTRATO ---
def colorir_valor(row):
    if 'Tipo' in row.index:
        color = 'background-color: rgba(255, 75, 75, 0.2);' if row['Tipo'] == 'Saída' else 'background-color: rgba(0, 255, 0, 0.1);'
    else:
        color = 'background-color: rgba(0, 255, 0, 0.1);'
    return [color] * len(row)

# --- MENU SUPERIOR ---
st.title("Pro Driver")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: btn_geral = st.button("Geral", use_container_width=True)
with col_m2: btn_uber = st.button("Uber", use_container_width=True)
with col_m3: btn_99 = st.button("99Pop", use_container_width=True)
with col_m4: btn_cartao = st.button("Cartao", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99 Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

hoje_str = datetime.now().strftime("%d/%m/%Y")

# --- PÁGINA: GERAL ---
if st.session_state.pagina == "Geral":
    df_u = carregar_dados("Uber"); df_n = carregar_dados("99Pop"); df_g = carregar_dados("Geral")
    df_cartoes = carregar_dados("MeusCartoes"); df_saldos = carregar_dados("Saldos")
    
    st.subheader("Saldos")
    if not df_saldos.empty:
        cols_s = st.columns(4)
        for i, row in df_saldos.iterrows():
            with cols_s[i % 4]:
                st.metric(row['Local'], formatar_br(float(row['Valor'])))
    
    with st.expander("Ajustar Saldos"):
        if not df_saldos.empty:
            l_sel = st.selectbox("Local:", df_saldos['Local'].tolist())
            n_v = st.number_input("Novo Valor:", min_value=0.0, step=0.01, format="%.2f")
            if st.button("Salvar Ajuste"):
                df_saldos.loc[df_saldos['Local'] == l_sel, 'Valor'] = n_v
                conn.update(worksheet="Saldos", data=df_saldos)
                st.cache_data.clear(); st.rerun()

    st.write("---")
    g_u = df_u[df_u['Data'] == hoje_str]['Valor'].sum() if not df_u.empty else 0
    g_n = df_n[df_n['Data'] == hoje_str]['Valor'].sum() if not df_n.empty else 0
    e_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Entrada")]['Valor'].sum() if not df_g.empty else 0
    s_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum() if not df_g.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Hoje", formatar_br(g_u + g_n + e_g))
    c2.metric("Saídas Hoje", formatar_br(s_g))
    c3.metric("Lucro Líquido", formatar_br((g_u + g_n + e_g) - s_g))

    st.write("---")
    col_f, col_e = st.columns([1, 2])
    with col_f:
        st.subheader("Lançamento")
        with st.form("form_g", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            vlr = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
            forma = st.selectbox("Pagamento", ["Dinheiro/PIX", "Débito", "Cartão de Crédito"])
            desc = st.text_input("Descrição")
            if st.form_submit_button("Lançar"):
                nova = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": desc, "Valor": float(vlr), "Tipo": tipo, "Forma_Pagamento": forma, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_e:
        if not df_g.empty:
            st.dataframe(df_g.drop(columns=['ID'], errors='ignore').tail(15).style.apply(colorir_valor, axis=1), use_container_width=True)

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(aba)
    df_app = carregar_dados(aba)
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form(f"f_{aba}", clear_on_submit=True):
            v = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
            k = st.number_input("KM", min_value=0)
            if st.form_submit_button("Salvar"):
                n = pd.DataFrame([{"Data": hoje_str, "Valor": float(v), "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, n], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    with c2: 
        if not df_app.empty:
            st.dataframe(df_app.drop(columns=['ID'], errors='ignore').tail(15).style.apply(colorir_valor, axis=1), use_container_width=True)

# --- PÁGINA: CARTÃO (Ajustada para valores altos) ---
elif st.session_state.pagina == "Cartao":
    st.header("Cartão")
    df_cartoes = carregar_dados("MeusCartoes"); df_g = carregar_dados("Geral")
    ca, cb = st.columns([1, 2])
    with ca:
        with st.form("f_c"):
            nc = st.text_input("Nome Cartão")
            # Ajustado para permitir 2.550,00 e formatos grandes
            lc = st.number_input("Limite", min_value=0.0, step=50.0, format="%.2f")
            if st.form_submit_button("Adicionar"):
                nv = pd.DataFrame([{"Nome": nc, "Limite": float(lc), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, nv], ignore_index=True))
                st.cache_data.clear(); st.rerun()
        
        for _, r in df_cartoes.iterrows():
            gasto = df_g[df_g['Cartao_Nome'] == r['Nome']]['Valor'].sum() if not df_g.empty and "Cartao_Nome" in df_g.columns else 0
            disp = r['Limite'] - gasto
            st.info(f"**{r['Nome']}**\n\nDisponível: {formatar_br(disp)}")
    with cb:
        if not df_g.empty and "Forma_Pagamento" in df_g.columns:
            compras = df_g[df_g['Forma_Pagamento'] == "Cartão de Crédito"]
            st.dataframe(compras.style.apply(colorir_valor, axis=1), use_container_width=True)
