import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("Teste de Gravação")

# Conecta e limpa o cache para forçar a nova permissão
conn = st.connection("gsheets", type=GSheetsConnection)
st.cache_data.clear()

# Tenta carregar a aba Geral
try:
    df = conn.read(worksheet="Geral", ttl="0")
except:
    df = pd.DataFrame(columns=["Data", "Valor"])

st.write("Dados atuais:", df)

if st.button("Testar Gravação Agora"):
    nova_linha = pd.DataFrame([{"Data": "10/04/2026", "Valor": 100.0}])
    df_novo = pd.concat([df, nova_linha], ignore_index=True)
    
    try:
        conn.update(worksheet="Geral", data=df_novo)
        st.success("CONSEGUI GRAVAR! O acesso está liberado.")
        st.rerun()
    except Exception as e:
        st.error(f"Ainda sem acesso de Editor. Erro: {e}")
