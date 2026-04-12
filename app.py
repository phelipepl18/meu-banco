import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid # Para gerar IDs únicos

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver v3", layout="centered")

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS ---
def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        # Se a coluna ID não existir no que foi lido, a gente garante que o DF não quebre
        if not df.empty and "ID" not in df.columns:
            df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df
    except Exception:
        if nome_aba == "Geral":
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo", "ID"])
        else:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado", "ID"])

# Menu Lateral
st.sidebar.title("Painel do Motorista")
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber", "99 Pop", "Gastos Geral"])

# --- PÁGINA: GASTOS GERAL ---
if pagina == "Gastos Geral":
    st.header("Lançar Gastos")
    df_g = carregar_dados("Geral")
    
    with st.form("form_gastos", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
        cat = st.selectbox("Categoria", ["Combustível", "Alimentação", "Manutenção", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0, step=0.01)
        dat = st.date_input("Data", datetime.now())
        
        if st.form_submit_button("Salvar Gasto"):
            nova_linha = pd.DataFrame([{
                "Data": dat.strftime("%d/%m/%Y"), 
                "Categoria": cat, 
                "Descricao": "", 
                "Valor": vlr, 
                "Tipo": tipo,
                "ID": str(uuid.uuid4())[:8] # Gera um ID curto
            }])
            df_final = pd.concat([df_g, nova_linha], ignore_index=True)
            conn.update(worksheet="Geral", data=df_final)
            st.cache_data.clear()
            st.rerun()

    st.write("---")
    st.subheader("Extrato de Gastos")
    
    if not df_g.empty:
        # Criamos uma lista para o usuário escolher qual item apagar
        # Mostra a Data e o Valor para o usuário identificar
        df_g['Identificador'] = df_g['Data'] + " - " + df_g['Categoria'] + " (R$ " + df_g['Valor'].astype(str) + ")"
        
        item_para_deletar = st.selectbox("Selecione um item para apagar:", df_g['Identificador'].tolist())
        
        if st.button("🗑️ Apagar Item Selecionado"):
            # Filtra o DataFrame mantendo tudo, exceto o item selecionado
            # Usamos o ID para ter certeza de apagar a linha certa
            id_para_remover = df_g[df_g['Identificador'] == item_para_deletar]['ID'].values[0]
            df_atualizado = df_g[df_g['ID'] != id_para_remover]
            
            # Removemos a coluna temporária de identificação antes de salvar
            df_atualizado = df_atualizado.drop(columns=['Identificador'])
            
            conn.update(worksheet="Geral", data=df_atualizado)
            st.cache_data.clear()
            st.success("Item removido! O saldo foi atualizado.")
            st.rerun()
            
        st.dataframe(df_g.drop(columns=['ID', 'Identificador']).tail(10), use_container_width=True)
    else:
        st.warning("O extrato está vazio.")

# --- AJUSTE NAS PÁGINAS UBER / 99 ---
elif pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    with st.form(f"form_{aba}", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        v = st.number_input("Valor R$", min_value=0.0)
        km = st.number_input("KM Rodados", min_value=0)
        
        if st.form_submit_button(f"Salvar {aba}"):
            nova = pd.DataFrame([{
                "Data": d.strftime("%d/%m/%Y"), 
                "Valor": v, 
                "Descricao": "", 
                "KM_Rodado": km,
                "ID": str(uuid.uuid4())[:8]
            }])
            df_f = pd.concat([df_app, nova], ignore_index=True)
            conn.update(worksheet=aba, data=df_f)
            st.cache_data.clear()
            st.rerun()

    if not df_app.empty:
        st.write("---")
        item_del = st.selectbox("Apagar lançamento:", df_app['Data'] + " (R$ " + df_app['Valor'].astype(str) + ")")
        if st.button(f"Remover de {aba}"):
            # Lógica similar de filtro
            df_novo = df_app[~(df_app['Data'] + " (R$ " + df_app['Valor'].astype(str) + ")" == item_del)]
            conn.update(worksheet=aba, data=df_novo)
            st.cache_data.clear()
            st.rerun()
        st.dataframe(df_app.drop(columns=['ID']).tail(10))
