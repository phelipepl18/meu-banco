import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px

st.set_page_config(page_title="Pro Driver - Gestão", layout="wide")

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
            for col in ['Valor', 'Limite', 'KM_Rodado']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df if df is not None else pd.DataFrame()
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

# Garantir colunas essenciais
for col in ["Cartao_Vinculado", "Categoria", "Forma_Pagamento"]:
    if not df_g.empty and col not in df_g.columns:
        df_g[col] = "N/A"

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    lucro_total = 0
    if not df_saldos.empty:
        cols_s = st.columns(len(df_saldos))
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            v_base = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local] if not df_g.empty else pd.DataFrame()
            saldo = v_base + movs[movs['Tipo'] == "Entrada"]['Valor'].sum() - movs[movs['Tipo'] == "Saída"]['Valor'].sum()
            lucro_total += saldo
            cols_s[i].metric(local, formatar_br(saldo))
    
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total))
    st.write("---")

    col_l, col_a = st.columns([2, 1])
    with col_l:
        with st.form("form_novo", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v = st.number_input("VALOR (R$)", min_value=0.0)
            c1, c2 = st.columns(2)
            with c1:
                f = st.selectbox("LOCAL", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
                t = st.selectbox("TIPO", ["Saída", "Entrada"])
            with c2:
                cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel Carro", "Seguro", "Limpeza", "Outros"])
                cartao_escolhido = "N/A"
                if f == "Cartão de Crédito" and not df_cartoes.empty:
                    cartao_escolhido = st.selectbox("QUAL CARTÃO?", df_cartoes['Nome'].tolist())
            d = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR AGORA"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    st.write("---")
    st.subheader("📊 Extrato Geral")
    if not df_g.empty:
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore'), use_container_width=True)

# --- PÁGINA RELATÓRIOS (CORRIGIDA) ---
elif st.session_state.pagina == "Relatorios":
    st.header("📊 Resumo de Gastos Reais")
    if not df_g.empty:
        df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        
        # FILTRO CRÍTICO: 
        # 1. Apenas Saídas
        # 2. Apenas do mês atual
        # 3. IGNORA Uber e 99Pop no gráfico de gastos
        locais_ignorar = ["Uber", "99Pop"]
        df_saidas = df_g[
            (df_g['Tipo'] == 'Saída') & 
            (df_g['Data_DT'].dt.month == hoje.month) & 
            (~df_g['Forma_Pagamento'].isin(locais_ignorar))
        ].copy()
        
        if not df_saidas.empty:
            # Lógica para "Outros" usar a descrição no gráfico
            df_saidas['Exibir_No_Grafico'] = df_saidas.apply(
                lambda x: x['Descricao'] if x['Categoria'] == 'Outros' else x['Categoria'], axis=1
            )
            
            fig = px.pie(df_saidas, values='Valor', names='Exibir_No_Grafico', hole=.4, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            st.metric("Total de Gastos Reais (Excluindo Apps)", formatar_br(df_saidas['Valor'].sum()))
            st.write("### Detalhes dos Gastos")
            st.dataframe(df_saidas[['Data', 'Descricao', 'Forma_Pagamento', 'Valor']], use_container_width=True)
        else:
            st.warning("Nenhum gasto (saída) registrado fora dos apps de corrida este mês.")
    else:
        st.info("Sem dados para exibir.")

# --- OUTRAS PÁGINAS (UBER, 99, CARTÃO) ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(f"Registros {aba}")
    df_app = carregar_dados(aba)
    with st.form(f"f_{aba}"):
        v_app = st.number_input("Valor Ganho", min_value=0.0)
        k_app = st.number_input("KM Total do Dia", min_value=0)
        if st.form_submit_button("Salvar Dia"):
            nova_l = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Valor": v_app, "KM_Rodado": k_app, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet=aba, data=pd.concat([df_app, nova_l], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    st.dataframe(df_app.iloc[::-1], use_container_width=True)

elif st.session_state.pagina == "Cartao":
    st.header("💳 Cartões de Crédito")
    with st.expander("➕ Adicionar Cartão"):
        with st.form("add_c"):
            n_c = st.text_input("Nome")
            l_c = st.number_input("Limite", min_value=0.0)
            if st.form_submit_button("Salvar"):
                n_df = pd.DataFrame([{"Nome": n_c, "Limite": l_c, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, n_df], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    if not df_cartoes.empty:
        for i, r in df_cartoes.iterrows():
            # Gastos vinculados ao cartão no Geral
            g = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Tipo'] == 'Saída')]['Valor'].sum()
            st.metric(r['Nome'], formatar_br(r['Limite'] - g), delta=f"Gasto: {formatar_br(g)}")
