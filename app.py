import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página para ficar bonita no iPhone
st.set_page_config(page_title="Bank Pro", page_icon="💰", layout="centered")

st.title("💰 Bank Pro Online")

# Conectar ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Ler dados existentes
try:
    df = conn.read(ttl="0")
except:
    # Se a planilha estiver vazia, cria o formato básico
    df = pd.DataFrame(columns=["Data", "Descricao", "Valor", "Tipo"])

# --- Interface do Usuário ---
aba1, aba2 = st.tabs(["Resumo", "Novo Gasto"])

with aba2:
    st.subheader("📝 Adicionar Registro")
    with st.form("novo_gasto"):
        desc = st.text_input("O que você comprou?")
        valor = st.number_input("Quanto custou? (R$)", min_value=0.0, step=0.01)
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        submit = st.form_submit_button("Salvar no Banco")

        if submit:
            nova_linha = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Descricao": desc,
                "Valor": valor,
                "Tipo": tipo
            }])
            
            # Adiciona os novos dados ao que já existe
            df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
            
            # Salva de volta no Google Sheets
            conn.update(data=df_atualizado)
            st.success("Salvo com sucesso na nuvem! ☁️")
            st.balloons()

with aba1:
    st.subheader("📊 Saldo e Histórico")
    if not df.empty:
        # Cálculo simples de saldo
        entradas = df[df['Tipo'] == "Entrada 📈"]['Valor'].sum()
        saidas = df[df['Tipo'] == "Saída 📉"]['Valor'].sum()
        saldo = entradas - saidas
        
        st.metric("Saldo Atual", f"R$ {saldo:.2f}")
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Nenhum dado encontrado. Comece adicionando um gasto!")
