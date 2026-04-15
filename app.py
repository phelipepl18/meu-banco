import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px # Biblioteca para gráficos

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

# --- MENU ---
st.title("Pro Driver")
m1, m2, m3, m4, m5 = st.columns(5)
with m1: btn_geral = st.button("Geral", use_container_width=True)
with m2: btn_uber = st.button("Uber", use_container_width=True)
with m3: btn_99 = st.button("99Pop", use_container_width=True)
with m4: btn_cartao = st.button("Cartão", use_container_width=True)
with m5: btn_relat = st.button("📊 Gastos", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99Pop"
if btn_cartao: st.session_state.pagina = "Cartao"
if btn_relat: st.session_state.pagina = "Relatorios"

hoje = datetime.now()
df_g = carregar_dados("Geral")

# --- PÁGINA DE RELATÓRIOS (GASTOS MENSAIS) ---
if st.session_state.pagina == "Relatorios":
    st.header("📊 Análise de Gastos Mensais")

    if not df_g.empty:
        # Converter coluna de Data para o formato real do Python
        df_g['Data_Obj'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        
        # Filtros de Mês e Ano
        col1, col2 = st.columns(2)
        with col1:
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            mes_sel = st.selectbox("Selecione o Mês", meses, index=hoje.month - 1)
        with col2:
            ano_sel = st.number_input("Ano", min_value=2024, max_value=2030, value=hoje.year)

        # Filtrar dados pelo mês e ano escolhidos
        idx_mes = meses.index(mes_sel) + 1
        df_mes = df_g[(df_g['Data_Obj'].dt.month == idx_mes) & (df_g['Data_Obj'].dt.year == ano_sel)]
        
        # Só pega o que é Saída (Gasto)
        df_gastos = df_mes[df_mes['Tipo'] == 'Saída']

        if not df_gastos.empty:
            total_mes = df_gastos['Valor'].sum()
            st.metric(f"Total de Gastos em {mes_sel}", formatar_br(total_mes))

            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.subheader("Gastos por Local")
                gastos_por_local = df_gastos.groupby('Forma_Pagamento')['Valor'].sum().reset_index()
                fig_local = px.pie(gastos_por_local, values='Valor', names='Forma_Pagamento', hole=.4, template="plotly_dark")
                st.plotly_chart(fig_local, use_container_width=True)

            with c2:
                st.subheader("Maiores Despesas do Mês")
                df_top = df_gastos.sort_values(by='Valor', ascending=False)[['Data', 'Descricao', 'Valor']].head(10)
                st.table(df_top.style.format({"Valor": lambda x: formatar_br(x)}))
        else:
            st.warning(f"Nenhum gasto registrado em {mes_sel} de {ano_sel}.")
    else:
        st.info("Lance dados na página Geral para ver o relatório.")

# --- MANTÉM AS OUTRAS PÁGINAS (Geral, Cartão, etc) ---
elif st.session_state.pagina == "Geral":
    # (Seu código da página geral que já temos)
    st.write("Você está na página Geral. Use o botão 📊 Gastos para ver o relatório mensal.")
