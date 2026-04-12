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
        # ttl=0 garante que ele busque o dado mais recente no Google
        df = conn.read(worksheet=nome_aba, ttl=0)
        return df
    except Exception:
        # Se a aba estiver vazia, cria as colunas padrão
        if nome_aba == "Geral":
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])
        else:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
meta = st.sidebar.number_input("Sua Meta Diária (R$)", min_value=0, value=250)
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽"])

# --- PÁGINA: RESUMO DO DIA ---
if pagina == "Resumo do Dia":
    st.header("📊 Lucro de Hoje")
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    df_g = carregar_dados("Geral")
    
    ganho_u = pd.to_numeric(df_u[df_u['Data'] == hoje]['Valor'], errors='coerce').sum() if not df_u.empty else 0
    ganho_n = pd.to_numeric(df_n[df_n['Data'] == hoje]['Valor'], errors='coerce').sum() if not df_n.empty else 0
    total_ganhos = ganho_u + ganho_n
    
    gastos_hoje = 0
    if not df_g.empty and 'Tipo' in df_g.columns:
        gastos_hoje = pd.to_numeric(df_g[(df_g['Data'] == hoje) & (df_g['Tipo'].str.contains("Saída", na=False))]['Valor'], errors='coerce').sum()
    
    lucro = total_ganhos - gastos_hoje
    st.metric("Lucro Real Hoje", f"R$ {lucro:.2f}", f"Ganhos: R$ {total_ganhos:.2f}")

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
                    st.error(f"Erro ao salvar: {e}")
    
    st.write("---")
    st.subheader("📋 Extrato de Gastos")
    df_exibir = carregar_dados("Geral") # Recarrega para mostrar o novo
    if not df_exibir.empty:
        st.dataframe(df_exibir.tail(10), use_container_width=True)
    else:
        st.warning("O extrato ainda está vazio no Google Sheets.")

# --- PÁGINAS UBER E 99 ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    with st.form(f"form_{aba}", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        v = st.number_input("Valor R$", min_value=0.0)
        km = st.number_input("KM Rodados", min_value=0)
        
        if st.form_submit_button(f"Salvar {aba}"):
            nova = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": v, "Descricao": "", "KM_Rodado": km}])
            df_f = pd.concat([df_app, nova], ignore_index=True)
            try:
                conn.update(worksheet=aba, data=df_f)
                st.cache_data.clear()
                st.rerun()
            except:
                st.cache_data.clear()
                st.rerun()

    st.subheader("📋 Últimas Corridas")
    st.dataframe(df_app.tail(10), use_container_width=True)
