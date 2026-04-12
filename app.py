import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# --- ESTILO CSS PARA CELULAR E DESKTOP ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    
    /* Ajuste das métricas para caberem lado a lado no celular */
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; color: #00FF00; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    
    .stMetric { 
        background-color: #1e1e1e; 
        padding: 10px !important; 
        border-radius: 8px; 
        border: 1px solid #333;
        margin-bottom: 5px;
    }

    /* Botões do menu mais compactos */
    .stButton button {
        width: 100%;
        padding: 0.4rem;
        font-size: 0.8rem;
    }
    
    .block-container { padding-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        if not df.empty:
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df
    except:
        if nome_aba == "MeusCartoes": return pd.DataFrame(columns=["Nome", "Limite", "ID"])
        if nome_aba == "Saldos": return pd.DataFrame(columns=["Local", "Valor", "ID"])
        if nome_aba == "Geral": return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo", "Forma_Pagamento", "Cartao_Nome", "Parcelas", "ID"])
        return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado", "ID"])

# --- MENU SUPERIOR ---
st.title("🚖 Pro Driver")
m1, m2, m3, m4 = st.columns(4)
with m1: btn_geral = st.button("Geral")
with m2: btn_uber = st.button("Uber")
with m3: btn_99 = st.button("99Pop")
with m4: btn_cartao = st.button("Cartão")

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99 Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

# --- PÁGINA: GERAL ---
if st.session_state.pagina == "Geral":
    hoje = datetime.now().strftime("%d/%m/%Y")
    df_u = carregar_dados("Uber"); df_n = carregar_dados("99Pop"); df_g = carregar_dados("Geral")
    df_cartoes = carregar_dados("MeusCartoes"); df_saldos = carregar_dados("Saldos")
    
    if df_saldos.empty:
        df_saldos = pd.DataFrame([
            {"Local": "Cédula", "Valor": 0.0, "ID": "1"},
            {"Local": "Itaú", "Valor": 0.0, "ID": "2"},
            {"Local": "Uber", "Valor": 0.0, "ID": "3"},
            {"Local": "99Pop", "Valor": 0.0, "ID": "4"}
        ])

    # 1. SALDOS
    st.subheader("💰 Saldos")
    s1, s2, s3, s4 = st.columns(4)
    locais = df_saldos.to_dict('records')
    for i, col_obj in enumerate([s1, s2, s3, s4]):
        if i < len(locais):
            col_obj.metric(locais[i]['Local'], f"R$ {float(locais[i]['Valor']):.2f}")
    
    with st.expander("Ajustar Saldos"):
        with st.form("ajuste_s"):
            l_sel = st.selectbox("Local:", df_saldos['Local'].tolist())
            v_nov = st.number_input("Valor Atual:", min_value=0.0, format="%.2f")
            if st.form_submit_button("Atualizar"):
                df_saldos.loc[df_saldos['Local'] == l_sel, 'Valor'] = v_nov
                conn.update(worksheet="Saldos", data=df_saldos)
                st.cache_data.clear(); st.rerun()

    # 2. RESUMO HOJE
    st.write("---")
    ganho_h = df_u[df_u['Data'] == hoje]['Valor'].sum() + df_n[df_n['Data'] == hoje]['Valor'].sum()
    saida_h = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum() if "Forma_Pagamento" in df_g.columns else 0
    
    r1, r2, r3 = st.columns(3)
    r1.metric("Ganhos", f"R$ {ganho_h:.2f}")
    r2.metric("Saídas", f"R$ {saida_h:.2f}")
    r3.metric("Lucro", f"R$ {ganho_h - saida_h:.2f}")

    # 3. LANÇAMENTO
    st.write("---")
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        with st.form("f_geral", clear_on_submit=True):
            t = st.selectbox("Tipo", ["Saída", "Entrada"])
            v = st.number_input("Valor", min_value=0.0)
            f = st.selectbox("Pagamento", ["Dinheiro/PIX", "Débito", "Cartão de Crédito"])
            c_n = "N/A"; p = 1
            if f == "Cartão de Crédito" and not df_cartoes.empty:
                c_n = st.selectbox("Qual Cartão?", df_cartoes['Nome'].tolist())
                p = st.number_input("Parcelas", min_value=1, step=1)
            desc = st.text_input("Descrição")
            if st.form_submit_button("Lançar"):
                nova = pd.DataFrame([{"Data": hoje, "Categoria": "Geral", "Descricao": desc, "Valor": float(v), "Tipo": t, "Forma_Pagamento": f, "Cartao_Nome": c_n, "Parcelas": p, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    with col_b:
        st.dataframe(df_g.drop(columns=['ID'], errors='ignore').tail(8), use_container_width=True)

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(f"Ganhos {aba}")
    df_app = carregar_dados(aba)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        with st.form(f"f_{aba}", clear_on_submit=True):
            v_app = st.number_input("Valor", min_value=0.0)
            km_app = st.number_input("KM", min_value=0)
            if st.form_submit_button("Salvar"):
                n_app = pd.DataFrame([{"Data": hoje, "Valor": float(v_app), "Descricao": "", "KM_Rodado": km_app, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, n_app], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    with c2: st.dataframe(df_app.drop(columns=['ID'], errors='ignore').tail(10), use_container_width=True)

# --- PÁGINA: CARTÃO ---
elif st.session_state.pagina == "Cartao":
    st.header("Meus Cartões")
    df_cartoes = carregar_dados("MeusCartoes"); df_g = carregar_dados("Geral")
    ca, cb = st.columns([1, 1.5])
    with ca:
        with st.form("f_c"):
            nc = st.text_input("Nome Cartão"); lc = st.number_input("Limite")
            if st.form_submit_button("Adicionar"):
                nv = pd.DataFrame([{"Nome": nc, "Limite": float(lc), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, nv], ignore_index=True))
                st.cache_data.clear(); st.rerun()
        for _, r in df_cartoes.iterrows():
            g = df_g[df_g['Cartao_Nome'] == r['Nome']]['Valor'].sum() if "Cartao_Nome" in df_g.columns else 0
            st.info(f"**{r['Nome']}**\n\nDisp: R$ {r['Limite']-g:.2f} / Lim: R$ {r['Limite']:.2f}")
    with cb:
        if "Forma_Pagamento" in df_g.columns:
            st.dataframe(df_g[df_g['Forma_Pagamento'] == "Cartão de Crédito"][['Data', 'Cartao_Nome', 'Valor', 'Parcelas']], use_container_width=True)
