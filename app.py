import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Ultra", page_icon="💰", layout="wide")

# Estilização Customizada (Cores e Layout)
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 10px; background-color: #1e2130; color: white; }
    .stTabs [data-baseweb="tab"]:hover { background-color: #2b3044; }
    .entrada { color: #28a745; font-weight: bold; }
    .saida { color: #dc3545; font-weight: bold; }
    div[data-testid="stExpander"] { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar dados de uma aba específica
def carregar_dados(aba="Transacoes"):
    try:
        df = conn.read(worksheet=aba, ttl="0")
        return df.dropna(how='all')
    except:
        if aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

df = carregar_dados("Transacoes")
df_cartoes = carregar_dados("Cartoes")

# --- MENU LATERAL / PÁGINAS ---
st.sidebar.title("🏦 Bank Pro Ultra")
pagina = st.sidebar.radio("Navegar", ["Geral", "Uber 🚗", "99 Pop 🚙", "Cartões de Crédito 💳"])

# --- FUNÇÃO PARA EXIBIR EXTRATO COLORIDO ---
def exibir_extrato(dataframe_filtrado):
    if not dataframe_filtrado.empty:
        st.write("### 📜 Extrato")
        # Criando versão visual do extrato
        for _, row in dataframe_filtrado.sort_index(ascending=False).iterrows():
            cor = "green" if "Entrada" in row['Tipo'] else "red"
            simbolo = "+" if "Entrada" in row['Tipo'] else "-"
            with st.container():
                st.markdown(f"""
                **{row['Data']}** | {row['Descricao']}  
                <span style='color:{cor}; font-size: 20px;'>{simbolo} R$ {row['Valor']:.2f}</span>
                <hr style='margin: 10px 0;'>
                """, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado nesta categoria.")

# --- PÁGINA GERAL ---
if pagina == "Geral":
    st.header("Resumo Geral")
    aba_add, aba_extrato = st.tabs(["➕ Novo Lançamento", "📑 Extrato Completo"])
    
    with aba_add:
        with st.form("form_geral"):
            col1, col2 = st.columns(2)
            data = col1.date_input("Data", datetime.now())
            tipo = col2.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
            cat = st.selectbox("Categoria", ["Alimentação", "Lazer", "Uber 🚗", "99 Pop 🚙", "Cartão 💳", "Outros"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Salvar Registro"):
                nova_linha = pd.DataFrame([{"Data": data.strftime("%d/%m/%Y"), "Categoria": cat, "Descricao": desc, "Valor": valor, "Tipo": tipo}])
                df = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(worksheet="Transacoes", data=df)
                st.success("Salvo!")
                st.rerun()

    with aba_extrato:
        exibir_extrato(df)

# --- PÁGINAS ESPECÍFICAS (UBER / 99) ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    st.header(f"Gerenciamento - {pagina}")
    categoria_filtro = "Uber 🚗" if "Uber" in pagina else "99 Pop 🚙"
    
    with st.expander("➕ Adicionar Corrida/Gasto"):
        with st.form(f"form_{pagina}"):
            data_p = st.date_input("Data")
            tipo_p = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
            desc_p = st.text_input("Detalhes")
            valor_p = st.number_input("Valor (R$) ", min_value=0.0)
            if st.form_submit_button("Lançar"):
                nova = pd.DataFrame([{"Data": data_p.strftime("%d/%m/%Y"), "Categoria": categoria_filtro, "Descricao": desc_p, "Valor": valor_p, "Tipo": tipo_p}])
                df = pd.concat([df, nova], ignore_index=True)
                conn.update(worksheet="Transacoes", data=df)
                st.rerun()

    df_filtrado = df[df['Categoria'] == categoria_filtro]
    exibir_extrato(df_filtrado)

# --- PÁGINA DE CARTÕES ---
elif pagina == "Cartões de Crédito 💳":
    st.header("Meus Cartões")
    
    with st.expander("➕ Cadastrar Novo Cartão"):
        with st.form("novo_cartao"):
            nome = st.text_input("Nome do Cartão (Ex: Nubank)")
            venc = st.number_input("Dia do Vencimento", 1, 31)
            limite = st.number_input("Limite Total", min_value=0.0)
            gasto = st.number_input("Valor já Gasto", min_value=0.0)
            if st.form_submit_button("Adicionar Cartão"):
                novo_c = pd.DataFrame([{"Nome": nome, "Vencimento": venc, "Limite": limite, "Gasto": gasto}])
                df_cartoes = pd.concat([df_cartoes, novo_c], ignore_index=True)
                conn.update(worksheet="Cartoes", data=df_cartoes)
                st.rerun()

    if not df_cartoes.empty:
        for _, c in df_cartoes.iterrows():
            disponivel = c['Limite'] - c['Gasto']
            st.subheader(f"💳 {c['Nome']}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Gasto Atual", f"R$ {c['Gasto']:.2f}", delta_color="inverse")
            col2.metric("Limite Disponível", f"R$ {disponivel:.2f}")
            col3.write(f"📅 Vencimento: Dia {c['Vencimento']}")
            st.progress(min(c['Gasto']/c['Limite'], 1.0))
            st.write("---")
