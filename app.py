import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração visual
st.set_page_config(page_title="Bank Pro", page_icon="💰", layout="centered")

# Estilo para parecer um App de iPhone
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 15px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007AFF; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 Bank Pro Online")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Carregar dados
try:
    df = conn.read(ttl="0")
    # Limpar linhas vazias se houver
    df = df.dropna(how='all')
except:
    df = pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# --- LÓGICA DE ABAS ---
aba1, aba2, aba3 = st.tabs(["📊 Resumo", "💸 Novo Gasto", "📜 Extrato"])

with aba2:
    st.subheader("Registrar Movimentação")
    with st.form("form_gasto", clear_on_submit=True):
        tipo = st.radio("Tipo de Transação", ["Saída 📉", "Entrada 📈"], horizontal=True)
        
        # Categorias que você pediu
        cat_opcoes = ["Uber 🚗", "99 Pop 🚙", "Cartão de Crédito 💳", "Alimentação 🍕", "Lazer 🍻", "Salário/Extra 💰", "Outros ⚙️"]
        categoria = st.selectbox("Selecione a Categoria", cat_opcoes)
        
        desc = st.text_input("Descrição (Ex: Viagem pro centro)")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        btn_salvar = st.form_submit_button("Confirmar Lançamento")

        if btn_salvar:
            if valor > 0:
                nova_linha = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Categoria": categoria,
                    "Descricao": desc,
                    "Valor": valor,
                    "Tipo": tipo
                }])
                
                df_novo = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(data=df_novo)
                st.success("Lançamento salvo na nuvem!")
                st.balloons()
                st.rerun()
            else:
                st.error("Digite um valor maior que zero!")

with aba1:
    if not df.empty:
        entradas = df[df['Tipo'] == "Entrada 📈"]['Valor'].sum()
        saidas = df[df['Tipo'] == "Saída 📉"]['Valor'].sum()
        saldo_total = entradas - saidas
        
        col1, col2 = st.columns(2)
        col1.metric("Saldo Atual", f"R$ {saldo_total:.2f}")
        col2.metric("Total Gastos", f"R$ {saidas:.2f}", delta=f"-{saidas:.2f}", delta_color="inverse")
        
        st.write("---")
        st.subheader("Gastos por Categoria")
        # Gráfico simples de onde está indo o dinheiro
        gastos_cat = df[df['Tipo'] == "Saída 📉"].groupby("Categoria")["Valor"].sum()
        st.bar_chart(gastos_cat)
    else:
        st.info("O banco está vazio. Adicione sua primeira movimentação!")

with aba3:
    st.subheader("Extrato Detalhado")
    if not df.empty:
        # Mostra do mais novo para o mais antigo
        st.dataframe(df.sort_index(ascending=False), use_container_width=True, hide_index=True)
        
        if st.button("Limpar Tudo (Cuidado!)"):
            df_limpo = pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])
            conn.update(data=df_limpo)
            st.rerun()
