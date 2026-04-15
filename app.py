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

# --- NAVEGAÇÃO ---
m1, m2, m3, m4, m5 = st.columns(5)
with m1: btn_geral = st.button("🏠 Geral", use_container_width=True)
with m2: btn_uber = st.button("🚗 Uber", use_container_width=True)
with m3: btn_99 = st.button("🚕 99Pop", use_container_width=True)
with m4: btn_cartao = st.button("💳 Cartão", use_container_width=True)
with m5: btn_relat = st.button("📊 Gastos", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99Pop"
if btn_cartao: st.session_state.pagina = "Cartao"
if btn_relat: st.session_state.pagina = "Relatorios"

hoje = datetime.now()
df_g = carregar_dados("Geral")
df_saldos = carregar_dados("Saldos")
df_cartoes = carregar_dados("MeusCartoes")

# Garantir que as colunas novas existam no Geral
for col in ["Cartao_Vinculado", "Categoria"]:
    if not df_g.empty and col not in df_g.columns:
        df_g[col] = "N/A"

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # (Cálculo de balões igual ao anterior...)
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
            c1, c2 = st.columns(2)
            with c1:
                f = st.selectbox("LOCAL", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
                t = st.selectbox("TIPO", ["Saída", "Entrada"])
            with c2:
                # NOVA COLUNA DE CATEGORIA
                cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel Carro", "Seguro", "Limpeza", "Internet", "Outros"])
                cartao_escolhido = "N/A"
                if f == "Cartão de Crédito" and not df_cartoes.empty:
                    cartao_escolhido = st.selectbox("QUAL CARTÃO?", df_cartoes['Nome'].tolist())
            
            d = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "ID": str(uuid.uuid4())[:8]}])
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

# --- PÁGINA RELATÓRIOS ---
elif st.session_state.pagina == "Relatorios":
    st.header("📊 Resumo Mensal de Gastos")
    if not df_g.empty:
        df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Filtro de Saídas do Mês
        df_mes = df_g[(df_g['Data_DT'].dt.month == mes_atual) & (df_g['Data_DT'].dt.year == ano_atual) & (df_g['Tipo'] == 'Saída')]
        
        if not df_mes.empty:
            st.metric(f"Total Gastos em {hoje.strftime('%B')}", formatar_br(df_mes['Valor'].sum()))
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Gastos por Categoria")
                fig = px.pie(df_mes, values='Valor', names='Categoria', hole=.4, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.subheader("Lista de Gastos")
                st.dataframe(df_mes[['Data', 'Descricao', 'Categoria', 'Valor']].sort_values(by='Valor', ascending=False), use_container_width=True)
        else:
            st.warning("Nenhuma saída registrada este mês.")
    else:
        st.info("Sem dados para exibir.")
