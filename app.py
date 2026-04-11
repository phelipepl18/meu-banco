import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver v3", page_icon="🚕", layout="centered")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS ---
def carregar_dados(nome_aba):
    try:
        # ttl=0 força o app a buscar o dado fresquinho no Google
        df = conn.read(worksheet=nome_aba, ttl=0)
        return df.dropna(how='all')
    except Exception:
        if nome_aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        elif nome_aba in ["Uber", "99Pop"]:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])
        else:
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .card { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 10px; }
    .lucro { color: #28a745; font-weight: bold; font-size: 22px; }
    .gasto { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
meta = st.sidebar.number_input("Sua Meta Diária (R$)", min_value=0, value=250)
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽", "Cartões 💳"])

# --- PÁGINA: RESUMO DO DIA ---
if pagina == "Resumo do Dia":
    st.header("📊 Lucro de Hoje
