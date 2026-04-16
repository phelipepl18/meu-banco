import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px

st.set_page_config(page_title="Pro Driver - Oficial", layout="wide")

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
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- ESTADO DA PÁGINA ---
if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"

# --- NAVEGAÇÃO ---
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
    # 1. CÁLCULO DE SALDOS (BALÕES)
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
    
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total))
    st.write("---")

    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("📝 Novo Lançamento")
        v = st.number_input("VALOR (R$)", min_value=0.0, step=0.01)
        
        c1, c2 = st.columns(2)
        with c1:
            # O LOCAL é de onde sai o dinheiro (Ex: Itaú)
            f = st.selectbox("SAINDO DE (LOCAL)", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Cartão de Crédito"])
            t = st.selectbox("TIPO", ["Saída", "Entrada"])
        
        with c2:
            cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel", "Fatura Cartão", "Outros"])
            
            # Se for gasto no crédito OU pagamento de fatura, precisa selecionar o cartão
            cartao_escolhido = "N/A"
            parc = 1
            if f == "Cartão de Crédito" or cat == "Fatura Cartão":
                cartao_list = df_cartoes['Nome'].tolist() if not df_cartoes.empty else []
                cartao_escolhido = st.selectbox("QUAL CARTÃO?", cartao_list)
                if f == "Cartão de Crédito":
                    parc = st.number_input("Nº DE PARCELAS", min_value=1, max_value=48, value=1)
        
        d = st.text_input("DESCRIÇÃO")
        
        if st.button("🚀 LANÇAR AGORA", use_container_width=True):
            if v > 0:
                # Se for Fatura Cartão, o sistema registra como uma 'Entrada' interna no cartão para abater o gasto
                nova = pd.DataFrame([{
                    "Data": hoje.strftime("%d/%m/%Y"), 
                    "Descricao": d, "Valor": v, "Tipo": t, 
                    "Forma_Pagamento": f, "Categoria": cat, 
                    "Cartao_Vinculado": cartao_escolhido, 
                    "Parcelas": parc, "ID": str(uuid.uuid4())[:8]
                }])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_r:
        st.subheader("💳 Limites de Cartão")
        if not df_cartoes.empty:
            for _, r in df_cartoes.iterrows():
                # LÓGICA DE CÁLCULO DO CARTÃO:
                # Gastos (Saídas no cartão) - Pagamentos (Fatura Cartão vinculada a este cartão)
                gastos_reais = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Forma_Pagamento'] == 'Cartão de Crédito') & (df_g['Tipo'] == 'Saída')]['Valor'].sum() if not df_g.empty else 0
                pagamentos_feitos = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Categoria'] == 'Fatura Cartão')]['Valor'].sum() if not df_g.empty else 0
                
                divida_atual = gastos_reais - pagamentos_feitos
                disp = r['Limite'] - divida_atual
                
                st.metric(r['Nome'], formatar_br(disp), f"Dívida: {formatar_br(divida_atual)}", delta_color="inverse")
        else:
            st.info("Sem cartões.")

    st.write("---")
    st.subheader("📊 Extrato Detalhado")
    if not df_g.empty:
        df_ext = df_g.iloc[::-1].copy()
        for _, row in df_ext.iterrows():
            cor = "🔴" if row['Tipo'] == "Saída" else "🟢"
            # Destaque para Fatura
            info_cat = f" [FATURA]" if row['Categoria'] == "Fatura Cartão" else ""
            with st.expander(f"{cor}{info_cat} {row['Data']} - {row['Descricao']} ({formatar_br(row['Valor'])})"):
                st.write(f"**De onde saiu:** {row['Forma_Pagamento']} | **Cartão Impactado:** {row['Cartao_Vinculado']}")
                if st.button("🗑️ Excluir", key=f"del_{row['ID']}"):
                    df_novo = df_g[df_g['ID'] != row['ID']]
                    conn.update(worksheet="Geral", data=df_novo)
                    st.cache_data.clear(); st.rerun()
