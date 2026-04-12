import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# Estilo para esconder o menu lateral original e ajustar o topo
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        if not df.empty and "ID" not in df.columns:
            df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df
    except:
        if nome_aba == "Geral":
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo", "ID"])
        elif nome_aba == "Cartao":
            return pd.DataFrame(columns=["Data", "Cartao", "Valor", "ID"])
        else:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado", "ID"])

# --- MENU SUPERIOR ---
# Usando colunas para simular um menu no topo
st.title("Sistema de Gestao Pro Driver")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    btn_geral = st.button("Geral", use_container_width=True)
with col_m2:
    btn_uber = st.button("Uber", use_container_width=True)
with col_m3:
    btn_99 = st.button("99 Pop", use_container_width=True)
with col_m4:
    btn_cartao = st.button("Cartao de Credito", use_container_width=True)

# Lógica simples para mudar de página sem a barra lateral
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Geral"

if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99 Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

# --- PÁGINA: GERAL (COM RESUMO NO TOPO) ---
if st.session_state.pagina == "Geral":
    # 1. Parte de Cima: Resumo (Antigo Resumo do Dia)
    hoje = datetime.now().strftime("%d/%m/%Y")
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    df_g = carregar_dados("Geral")
    
    ganho_u = pd.to_numeric(df_u[df_u['Data'] == hoje]['Valor'], errors='coerce').sum() if not df_u.empty else 0
    ganho_n = pd.to_numeric(df_n[df_n['Data'] == hoje]['Valor'], errors='coerce').sum() if not df_n.empty else 0
    total_entradas = ganho_u + ganho_n
    total_saidas = pd.to_numeric(df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Saída")]['Valor'], errors='coerce').sum() if not df_g.empty else 0
    lucro_liquido = total_entradas - total_saidas

    st.subheader(f"Resumo de Hoje: {hoje}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Brutos", f"R$ {total_entradas:.2f}")
    c2.metric("Despesas", f"R$ {total_saidas:.2f}")
    c3.metric("Lucro Liquido", f"R$ {lucro_liquido:.2f}")
    
    st.write("---")
    
    # 2. Parte de Baixo: Lancamento de Gastos
    st.subheader("Lancamento de Despesas")
    col_f, col_e = st.columns([1, 2])
    
    with col_f:
        with st.form("form_g", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            cat = st.selectbox("Categoria", ["Combustível", "Alimentação", "Manutenção", "Outros"])
            vlr = st.number_input("Valor", min_value=0.0)
            dat = st.date_input("Data", datetime.now())
            if st.form_submit_button("Registrar"):
                nova = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": cat, "Valor": vlr, "Tipo": tipo, "Descricao": "", "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

    with col_e:
        if not df_g.empty:
            st.dataframe(df_g.drop(columns=['ID']).tail(10), use_container_width=True)
            with st.expander("Apagar Lancamento"):
                opc = df_g['Data'] + " - " + df_g['Categoria'] + " (R$ " + df_g['Valor'].astype(str) + ")"
                item_apagar = st.selectbox("Selecione para remover:", opc.tolist())
                if st.button("Remover"):
                    id_r = df_g[opc == item_apagar]['ID'].values[0]
                    df_u = df_g[df_g['ID'] != id_r]
                    conn.update(worksheet="Geral", data=df_u)
                    st.cache_data.clear()
                    st.rerun()

# --- PÁGINAS UBER E 99 POP ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(f"Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form(f"form_{aba}", clear_on_submit=True):
            d = st.date_input("Data", datetime.now())
            v = st.number_input("Valor Recebido", min_value=0.0)
            km = st.number_input("KM Rodado", min_value=0)
            if st.form_submit_button("Salvar"):
                nova = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": v, "Descricao": "", "KM_Rodado": km, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, nova], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    with c2:
        st.dataframe(df_app.drop(columns=['ID']).tail(10), use_container_width=True)

# --- PÁGINA: CARTAO DE CREDITO ---
elif st.session_state.pagina == "Cartao":
    st.header("Gestao de Cartao de Credito")
    df_c = carregar_dados("Cartao")
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        with st.form("form_cartao", clear_on_submit=True):
            nome_c = st.text_input("Nome do Cartao (ex: Nubank)")
            valor_c = st.number_input("Valor da Compra", min_value=0.0)
            data_c = st.date_input("Data da Compra", datetime.now())
            if st.form_submit_button("Lancar Compra"):
                nova = pd.DataFrame([{"Data": data_c.strftime("%d/%m/%Y"), "Cartao": nome_c, "Valor": valor_c, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Cartao", data=pd.concat([df_c, nova], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    with col_c2:
        if not df_c.empty:
            total_fatura = df_c['Valor'].sum()
            st.metric("Total em Compras no Cartao", f"R$ {total_fatura:.2f}")
            st.dataframe(df_c.drop(columns=['ID']).tail(10), use_container_width=True)
