import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver v3", page_icon="🚕", layout="centered")

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS ---
def carregar_dados(nome_aba):
    try:
        # ttl=0 obriga o app a buscar o dado novo no Google sempre
        df = conn.read(worksheet=nome_aba, ttl=0)
        return df.dropna(how='all')
    except Exception:
        if nome_aba == "Cartoes":
            return pd.DataFrame(columns=["Data", "Nome", "Vencimento", "Limite", "Gasto"])
        elif nome_aba in ["Uber", "99Pop"]:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])
        else:
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽"])

# --- PÁGINA: GASTOS GERAL ⛽ ---
if pagina == "Gastos Geral ⛽":
    st.header("⛽ Lançar Gastos")
    df_g = carregar_dados("Geral")
    
    with st.form("form_gastos", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0)
        dat = st.date_input("Data", datetime.now()) # Aqui ele pega o calendário
        
        btn_salvar = st.form_submit_button("Salvar Gasto")

        if btn_salvar:
            # FORÇANDO O FORMATO BRASILEIRO (DIA/MÊS/ANO)
            data_formatada = dat.strftime("%d/%m/%Y")
            
            nova_linha = pd.DataFrame([{
                "Data": data_formatada, 
                "Categoria": cat, 
                "Valor": vlr, 
                "Tipo": tipo, 
                "Descricao": ""
            }])
            
            df_final = pd.concat([df_g, nova_linha], ignore_index=True)
            
            try:
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear() # Limpa o cache para o extrato atualizar
                st.success(f"✅ Gravado: R$ {vlr:.2f} em {data_formatada}")
                st.rerun()
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {e}")
    
    st.write("---")
    st.subheader("📋 Extrato de Gastos")
    if not df_g.empty:
        # Mostra os lançamentos mais novos primeiro
        st.dataframe(df_g.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("O extrato está vazio. Verifique se o nome da aba na planilha é exatamente 'Geral'.")

# (Aqui viriam as outras páginas Uber e 99 seguindo a mesma lógica...)
