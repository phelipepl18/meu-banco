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
        # Forçamos o TTL para 0 para não usar memória antiga
        df = conn.read(worksheet=nome_aba, ttl=0)
        return df
    except Exception:
        # Se a aba não existir ou estiver vazia, cria o esqueleto
        if nome_aba == "Geral":
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])
        else:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽"])

# --- PÁGINA: GASTOS GERAL ⛽ ---
elif pagina == "Gastos Geral ⛽":
    st.header("⛽ Lançar Gastos")
    df_g = carregar_dados("Geral")
    
    with st.form("form_gastos", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0, step=0.01)
        dat = st.date_input("Data", datetime.now())
        
        btn_salvar = st.form_submit_button("Salvar Gasto")

        if btn_salvar:
            data_br = dat.strftime("%d/%m/%Y")
            nova_linha = pd.DataFrame([{
                "Data": data_br, 
                "Categoria": cat, 
                "Descricao": "", 
                "Valor": vlr, 
                "Tipo": tipo
            }])
            
            df_final = pd.concat([df_g, nova_linha], ignore_index=True)
            
            try:
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear()
                st.success("✅ Gravado com sucesso!")
                st.rerun()
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {e}")
    
    st.write("---")
    st.subheader("📋 Extrato de Gastos")
    df_exibir = carregar_dados("Geral")
    if not df_exibir.empty:
        st.dataframe(df_exibir.tail(10), use_container_width=True)
    else:
        st.warning("O extrato ainda está vazio no Google Sheets.")
    
    # Carregamos os dados atuais
    df_g = carregar_dados("Geral")
    
    with st.form("form_gastos", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0, step=0.01)
        dat = st.date_input("Data", datetime.now())
        
        btn_salvar = st.form_submit_button("Salvar Gasto")

        if btn_salvar:
            data_br = dat.strftime("%d/%m/%Y")
            nova_linha = pd.DataFrame([{
                "Data": data_br, 
                "Categoria": cat, 
                "Descricao": "", # Certifique-se que na planilha está 'Descricao'
                "Valor": vlr, 
                "Tipo": tipo
            }])
            
            # Garante que as colunas fiquem na ordem certa da Imagem 3
            df_final = pd.concat([df_g, nova_linha], ignore_index=True)
            
            try:
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear() # Limpa o cache para obrigar a nova leitura
                st.success(f"✅ Gravado com sucesso!")
                st.rerun() 
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {e}")
    
    st.write("---")
    st.subheader("📋 Extrato de Gastos")
    
    # FORÇAMOS UMA NOVA LEITURA AQUI PARA EXIBIR
    df_exibir = carregar_dados("Geral")
    
    if not df_exibir.empty:
        # Reordenar as colunas para bater com a Imagem 3
        df_exibir = df_exibir[["Data", "Categoria", "Descricao", "Valor", "Tipo"]]
        st.dataframe(df_exibir.tail(10), use_container_width=True)
    else:
        st.warning("O extrato ainda está vazio. Verifique se clicou em 'Salvar'.")

            try:
                # Envia para a planilha
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear() # Limpa o cache
                st.success(f"✅ Gravado: R$ {vlr:.2f}")
                st.rerun() # Recarrega a página para atualizar o extrato
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {e}")
    
    st.write("---")
    st.subheader("📋 Extrato de Gastos")
    
    # FORÇAMOS A EXIBIÇÃO: Se o DF existir, ele mostra
    if df_g is not None and not df_g.empty:
        st.dataframe(df_g.tail(10), use_container_width=True)
    else:
        st.warning("O extrato ainda está vazio no Google Sheets.")

# --- PÁGINAS UBER E 99 (Simplificadas para funcionar) ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    with st.form(f"form_{aba}", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        v = st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": v}])
            df_f = pd.concat([df_app, nova], ignore_index=True)
            conn.update(worksheet=aba, data=df_f)
            st.cache_data.clear()
            st.rerun()
    st.dataframe(df_app)
