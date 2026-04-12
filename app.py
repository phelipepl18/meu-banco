import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# Estilo CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        if not df.empty:
            if 'Limite' in df.columns:
                df['Limite'] = pd.to_numeric(df['Limite'], errors='coerce').fillna(0)
            if 'Valor' in df.columns:
                df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df
    except:
        if nome_aba == "MeusCartoes": return pd.DataFrame(columns=["Nome", "Limite", "ID"])
        if nome_aba == "Geral": return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo", "Forma_Pagamento", "Cartao_Nome", "Parcelas", "ID"])
        return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado", "ID"])

# --- MENU SUPERIOR ---
st.title("Sistema de Gestao Pro Driver")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: btn_geral = st.button("Geral", use_container_width=True)
with col_m2: btn_uber = st.button("Uber", use_container_width=True)
with col_m3: btn_99 = st.button("99 Pop", use_container_width=True)
with col_m4: btn_cartao = st.button("Cartao de Credito", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99 Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

# --- PÁGINA: GERAL ---
if st.session_state.pagina == "Geral":
    hoje = datetime.now().strftime("%d/%m/%Y")
    df_u = carregar_dados("Uber"); df_n = carregar_dados("99Pop"); df_g = carregar_dados("Geral")
    df_cartoes = carregar_dados("MeusCartoes")
    
    # Cálculos: Só subtrai do lucro se NÃO for Cartão de Crédito
    ganho_total = (df_u[df_u['Data'] == hoje]['Valor'].sum() + 
                   df_n[df_n['Data'] == hoje]['Valor'].sum() + 
                   df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Entrada")]['Valor'].sum())
    
    # Despesas que saem do bolso hoje (Dinheiro/PIX/Débito)
    despesas_caixa = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum()
    lucro_liquido = ganho_total - despesas_caixa

    st.subheader(f"Resumo de Hoje: {hoje}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Brutos", f"R$ {ganho_total:.2f}")
    c2.metric("Despesas (Caixa)", f"R$ {despesas_caixa:.2f}")
    c3.metric("Lucro Liquido", f"R$ {lucro_liquido:.2f}")
    
    st.write("---")
    col_f, col_e = st.columns([1, 2])
    with col_f:
        st.subheader("Lancamento")
        with st.form("form_g", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            cat = st.selectbox("Categoria", ["Combustível", "Alimentação", "Manutenção", "Outros"])
            desc = st.text_input("Descricao")
            vlr = st.number_input("Valor", min_value=0.0, step=0.01)
            forma = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Débito", "Cartão de Crédito"])
            
            cartao_sel = "N/A"; parc_sel = 1
            if forma == "Cartão de Crédito" and not df_cartoes.empty:
                cartao_sel = st.selectbox("Selecione o Cartão", df_cartoes['Nome'].tolist())
                parc_sel = st.number_input("Parcelas", min_value=1, step=1)
            
            dat = st.date_input("Data", datetime.now())
            if st.form_submit_button("Registrar"):
                nova = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": cat, "Descricao": desc, "Valor": float(vlr), "Tipo": tipo, "Forma_Pagamento": forma, "Cartao_Nome": cartao_sel, "Parcelas": parc_sel, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_e:
        st.subheader("Extrato Geral")
        if not df_g.empty:
            st.dataframe(df_g.drop(columns=['ID']).tail(10), use_container_width=True)

# --- PÁGINA: CARTAO DE CREDITO ---
elif st.session_state.pagina == "Cartao":
    st.header("Gerenciamento de Cartoes")
    df_cartoes = carregar_dados("MeusCartoes")
    df_g = carregar_dados("Geral") # Pega as compras feitas na página Geral
    
    col_cad, col_ext = st.columns([1, 2])
    with col_cad:
        st.subheader("Meus Cartoes")
        with st.form("novo_cartao", clear_on_submit=True):
            nome_c = st.text_input("Nome do Cartao"); limite_c = st.number_input("Limite (R$)", min_value=0.0)
            if st.form_submit_button("Salvar Cartao"):
                novo = pd.DataFrame([{"Nome": nome_c, "Limite": float(limite_c), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, novo], ignore_index=True))
                st.cache_data.clear(); st.rerun()
        
        if not df_cartoes.empty:
            for _, row in df_cartoes.iterrows():
                # Calcula quanto ja usou desse cartao especifico na aba Geral
                gasto_cartao = df_g[(df_g['Cartao_Nome'] == row['Nome'])]['Valor'].sum()
                disponivel = row['Limite'] - gasto_cartao
                st.info(f"**{row['Nome']}**\n\nLimite: R$ {row['Limite']:.2f}\n\nDisponível: R$ {disponivel:.2f}")

            with st.expander("Excluir Cartao"):
                c_del = st.selectbox("Remover:", df_cartoes['Nome'].tolist())
                if st.button("Confirmar Exclusão"):
                    conn.update(worksheet="MeusCartoes", data=df_cartoes[df_cartoes['Nome'] != c_del])
                    st.cache_data.clear(); st.rerun()

    with col_ext:
        st.subheader("Extrato de Compras no Cartao")
        compras_cartao = df_g[df_g['Forma_Pagamento'] == "Cartão de Crédito"]
        if not compras_cartao.empty:
            st.dataframe(compras_cartao[['Data', 'Cartao_Nome', 'Descricao', 'Valor', 'Parcelas']], use_container_width=True)
        else:
            st.write("Nenhuma compra realizada no cartão ainda.")

# --- PÁGINAS UBER / 99 (MANTIDAS) ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(f"Ganhos {aba}"); df_app = carregar_dados(aba)
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form(f"f_{aba}", clear_on_submit=True):
            d = st.date_input("Data", datetime.now()); v = st.number_input("Valor", min_value=0.0)
            if st.form_submit_button("Salvar"):
                n = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": float(v), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, n], ignore_index=True)); st.cache_data.clear(); st.rerun()
    with c2: st.dataframe(df_app.drop(columns=['ID']).tail(10), use_container_width=True)
