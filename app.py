import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# --- ESTILO ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba.strip(), ttl=0)
        if df is not None and not df.empty:
            for col in ['Valor', 'Limite']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- MENU ---
st.title("Pro Driver")
m1, m2, m3, m4 = st.columns(4)
with m1: btn_geral = st.button("Geral", use_container_width=True)
with m2: btn_uber = st.button("Uber", use_container_width=True)
with m3: btn_99 = st.button("99Pop", use_container_width=True)
with m4: btn_cartao = st.button("Cartao", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

hoje_str = datetime.now().strftime("%d/%m/%Y")

# --- LÓGICA DE CARREGAMENTO SEGURO ---
df_g = carregar_dados("Geral")
df_saldos = carregar_dados("Saldos")
df_cartoes = carregar_dados("MeusCartoes")

# Garante que a coluna de vínculo existe para não dar KeyError
if not df_g.empty and "Cartao_Vinculado" not in df_g.columns:
    df_g["Cartao_Vinculado"] = "N/A"

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # BALÕES DE SALDO
    lucro_total = 0
    if not df_saldos.empty:
        cols = st.columns(len(df_saldos))
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            v_base = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local] if not df_g.empty else pd.DataFrame()
            saldo = v_base + movs[movs['Tipo'] == "Entrada"]['Valor'].sum() - movs[movs['Tipo'] == "Saída"]['Valor'].sum()
            lucro_total += saldo
            cols[i].metric(local, formatar_br(saldo))
    
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total))
    st.write("---")

    col_l, col_a = st.columns([2, 1])
    with col_l:
        with st.form("form_novo", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v = st.number_input("VALOR (R$)", min_value=0.0)
            f = st.selectbox("LOCAL", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
            
            cartao_escolhido = "N/A"
            if f == "Cartão de Crédito" and not df_cartoes.empty:
                cartao_escolhido = st.selectbox("QUAL CARTÃO?", df_cartoes['Nome'].tolist())
            
            t = st.selectbox("TIPO", ["Saída", "Entrada"])
            d = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje_str, "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Cartao_Vinculado": cartao_escolhido, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    with col_a:
        with st.expander("⚙️ SOMAR AO SALDO"):
            if not df_saldos.empty:
                sel = st.selectbox("Balão", df_saldos['Local'].tolist())
                add = st.number_input("Valor", min_value=0.0)
                if st.button("Somar"):
                    idx = df_saldos[df_saldos['Local'] == sel].index[0]
                    df_saldos.at[idx, 'Valor'] += add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.rerun()

    if not df_g.empty:
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore'), use_container_width=True)

# --- PÁGINA CARTÃO ---
elif st.session_state.pagina == "Cartao":
    st.header("💳 Gestão de Cartões de Crédito")

    with st.expander("➕ Cadastrar Novo Cartão"):
        with st.form("add_cartao"):
            nome_c = st.text_input("Nome do Cartão")
            limite_c = st.number_input("Limite Total (R$)", min_value=0.0)
            if st.form_submit_button("Salvar Cartão"):
                novo_c = pd.DataFrame([{"Nome": nome_c, "Limite": limite_c, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, novo_c], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    if not df_cartoes.empty:
        st.subheader("Meus Limites Disponíveis")
        cols_c = st.columns(len(df_cartoes))
        for i, row in df_cartoes.iterrows():
            # Cálculo seguro: verifica se a coluna existe antes de somar
            if not df_g.empty and "Cartao_Vinculado" in df_g.columns:
                gastos = df_g[(df_g['Cartao_Vinculado'] == row['Nome']) & (df_g['Tipo'] == 'Saída')]['Valor'].sum()
            else:
                gastos = 0
                
            limite_disponivel = row['Limite'] - gastos
            with cols_c[i]:
                st.metric(row['Nome'], formatar_br(limite_disponivel), help=f"Limite Total: {formatar_br(row['Limite'])}")
        
        st.write("---")
        st.dataframe(df_cartoes.drop(columns=['ID'], errors='ignore'), use_container_width=True)
