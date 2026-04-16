import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px

st.set_page_config(page_title="Pro Driver - Gestão Financeira", layout="wide")

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
            df.columns = [c.strip() for c in df.columns]
            cols_num = ['Valor', 'Limite', 'Parcelas', 'KM_Rodado']
            for col in cols_num:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- NAVEGAÇÃO ---
if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"

m1, m2, m3, m4, m5 = st.columns(5)
with m1: 
    if st.button("🏠 Geral", use_container_width=True): st.session_state.pagina = "Geral"
with m2: 
    if st.button("🚗 Uber", use_container_width=True): st.session_state.pagina = "Uber"
with m3: 
    if st.button("🚕 99Pop", use_container_width=True): st.session_state.pagina = "99Pop"
with m4: 
    if st.button("💳 Cartão", use_container_width=True): st.session_state.pagina = "Cartao"
with m5: 
    if st.button("📊 Gastos", use_container_width=True): st.session_state.pagina = "Relatorios"

hoje = datetime.now()
df_g = carregar_dados("Geral")
df_saldos = carregar_dados("Saldos")
df_cartoes = carregar_dados("MeusCartoes")

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # BALÕES DE SALDO
    lucro_total = 0
    if not df_saldos.empty:
        cols_s = st.columns(len(df_saldos))
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            v_base = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local] if not df_g.empty else pd.DataFrame()
            ent = movs[movs['Tipo'] == "Entrada"]['Valor'].sum() if not movs.empty else 0
            sai = movs[movs['Tipo'] == "Saída"]['Valor'].sum() if not movs.empty else 0
            saldo = v_base + ent - sai
            lucro_total += saldo
            cols_s[i].metric(local, formatar_br(saldo))
    
    st.write("---")
    col_l, col_a = st.columns([2, 1])
    
    with col_l:
        with st.form("form_novo", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v = st.number_input("VALOR TOTAL (R$)", min_value=0.0)
            c1, c2 = st.columns(2)
            with c1:
                f = st.selectbox("LOCAL", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Cartão de Crédito"])
                t = st.selectbox("TIPO", ["Saída", "Entrada"])
            with c2:
                cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel", "Fatura Cartão", "Outros"])
                cartao_list = df_cartoes['Nome'].tolist() if not df_cartoes.empty else []
                cartao_escolhido = st.selectbox("QUAL CARTÃO?", ["N/A"] + cartao_list) if f == "Cartão de Crédito" else "N/A"
            
            # OPÇÃO DE PARCELAMENTO
            parc = 1
            if f == "Cartão de Crédito":
                parc = st.number_input("PARCELAS", min_value=1, max_value=48, value=1)
            
            d = st.text_input("DESCRIÇÃO (Use nomes fáceis para identificar pagamentos)")
            
            if st.form_submit_button("LANÇAR"):
                if v > 0:
                    novo_id = str(uuid.uuid4())[:8]
                    nova = pd.DataFrame([{
                        "Data": hoje.strftime("%d/%m/%Y"), 
                        "Descricao": d, "Valor": v, "Tipo": t, 
                        "Forma_Pagamento": f, "Categoria": cat, 
                        "Cartao_Vinculado": cartao_escolhido, 
                        "Parcelas": parc, "ID": novo_id
                    }])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    # EXTRATO
    st.subheader("📊 Extrato")
    if not df_g.empty:
        df_ext = df_g.iloc[::-1]
        for idx, r in df_ext.iterrows():
            with st.expander(f"{r['Data']} - {r['Descricao']} | {formatar_br(r['Valor'])}"):
                st.write(f"Local: {r['Forma_Pagamento']} | Parcelas: {r.get('Parcelas', 1)}")
                if st.button("🗑️ Excluir", key=f"del_{r['ID']}"):
                    df_novo = df_g[df_g['ID'] != r['ID']]
                    conn.update(worksheet="Geral", data=df_novo)
                    st.cache_data.clear(); st.rerun()

# --- PÁGINA CARTÃO ---
elif st.session_state.pagina == "Cartao":
    st.header("💳 Controle de Cartões e Parcelas")
    
    if not df_cartoes.empty:
        for i, r in df_cartoes.iterrows():
            # 1. Total de compras feitas no cartão (Saídas)
            compras = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Tipo'] == 'Saída')]
            total_gasto = compras['Valor'].sum()
            
            # 2. Total de pagamentos feitos para esse cartão (Identificados pela Descrição ou Categoria Fatura)
            # Regra: Se a descrição da Entrada for igual à descrição da Saída, ele abate.
            pagamentos = df_g[(df_g['Forma_Pagamento'] != 'Cartão de Crédito') & 
                              (df_g['Tipo'] == 'Saída') & 
                              (df_g['Categoria'] == 'Fatura Cartão') &
                              (df_g['Descricao'].str.contains(r['Nome'], case=False, na=False))]
            
            # Simplificação para o limite: Limite Total - Gastos Atuais que ainda não foram pagos
            limite_atual = r['Limite'] - total_gasto
            
            col1, col2, col3 = st.columns(3)
            col1.metric(f"Cartão {r['Nome']}", formatar_br(limite_atual), "Limite Disp.")
            col2.metric("Total Gasto", formatar_br(total_gasto))
            col3.metric("Limite Total", formatar_br(r['Limite']))
            
            if st.button(f"🗑️ Remover {r['Nome']}", key=f"del_c_{r['ID']}"):
                df_c_novo = df_cartoes[df_cartoes['ID'] != r['ID']]
                conn.update(worksheet="MeusCartoes", data=df_c_novo)
                st.cache_data.clear(); st.rerun()
            st.write("---")
    
    with st.expander("➕ Adicionar Novo Cartão"):
        with st.form("new_card"):
            n = st.text_input("Nome"); lim = st.number_input("Limite")
            if st.form_submit_button("Cadastrar"):
                nc = pd.DataFrame([{"Nome": n, "Limite": lim, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, nc], ignore_index=True))
                st.cache_data.clear(); st.rerun()
