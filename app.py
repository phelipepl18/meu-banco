import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", page_icon="🚕", layout="centered")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# CSS Customizado para Estilo Moderno
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .card { background-color: #1e2130; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 15px; }
    .lucro-positivo { color: #28a745; font-weight: bold; font-size: 24px; }
    .gasto-negativo { color: #dc3545; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #007AFF; }
    </style>
    """, unsafe_allow_html=True)

# Função para carregar dados
def carregar(aba):
    try:
        return conn.read(worksheet=aba, ttl="0").dropna(how='all')
    except:
        if aba == "Cartoes": return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
meta_diaria = st.sidebar.number_input("Sua Meta Diária (R$)", min_value=0, value=250)
pagina = st.sidebar.radio("Navegar", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Cartões 💳", "Gastos Geral"])

# --- PÁGINA: RESUMO DO DIA ---
if pagina == "Resumo do Dia":
    st.header("📊 Lucro Real de Hoje")
    
    df_u = carregar("Uber")
    df_n = carregar("99Pop")
    df_g = carregar("Geral")
    
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    # Cálculos com proteção contra erro de coluna ausente
    ganho_u = df_u[df_u['Data'] == hoje]['Valor'].sum() if 'Valor' in df_u.columns else 0
    ganho_n = df_n[df_n['Data'] == hoje]['Valor'].sum() if 'Valor' in df_n.columns else 0
    total_ganho = ganho_u + ganho_n
    
    # Verifica se as colunas existem na aba Geral antes de calcular
    if 'Data' in df_g.columns and 'Tipo' in df_g.columns and 'Valor' in df_g.columns:
        gastos_hoje = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Saída 📉")]['Valor'].sum()
    else:
        gastos_hoje = 0
        
    lucro_liquido = total_ganho - gastos_hoje
    
    # Cards de Resumo
    st.markdown(f"""
    <div class="card">
        <small>Total Ganhos (App)</small><br>
        <span style="font-size: 20px;">R$ {total_ganho:.2f}</span><br><br>
        <small>Gastos/Combustível Hoje</small><br>
        <span class="gasto-negativo">- R$ {gastos_hoje:.2f}</span><br><hr>
        <small>LUCRO LÍQUIDO NO BOLSO</small><br>
        <span class="lucro-positivo">R$ {lucro_liquido:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Barra de Meta
    progresso = min(total_ganho / meta_diaria, 1.0) if meta_diaria > 0 else 0
    st.write(f"🎯 Meta: R$ {total_ganho:.2f} de R$ {meta_diaria:.2f}")
    st.progress(progresso)

# --- PÁGINAS UBER E 99 (PADRONIZADAS) ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    nome_aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Ganhos {nome_aba}")
    df_esp = carregar(nome_aba)
    
    with st.form(f"add_{nome_aba}"):
        col1, col2 = st.columns(2)
        dt = col1.date_input("Data", datetime.now())
        vl = col2.number_input("Valor da Corrida/Dia R$", min_value=0.0)
        km = st.number_input("KM Rodado (Opcional)", min_value=0)
        ds = st.text_input("Nota (ex: Dinheiro ou App)")
        
        if st.form_submit_button(f"Salvar na {nome_aba}"):
            nova = pd.DataFrame([{"Data": dt.strftime("%d/%m/%Y"), "Valor": vl, "Descricao": ds, "KM_Rodado": km}])
            df_esp = pd.concat([df_esp, nova], ignore_index=True)
            conn.update(worksheet=nome_aba, data=df_esp)
            st.success("Salvo com sucesso!")
            st.rerun()

    st.subheader("Extrato Recente")
    if not df_esp.empty:
        st.dataframe(df_esp.sort_index(ascending=False), use_container_width=True, hide_index=True)

# --- PÁGINA GERAL (COMBUSTÍVEL E OUTROS) ---
elif pagina == "Gastos Geral":
    st.header("⛽ Gastos e Outras Entradas")
    df_geral = carregar("Geral")
    
    with st.form("form_g"):
        tipo = st.radio("Tipo", ["Saída 📉", "Entrada 📈"], horizontal=True)
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Manutenção 🔧", "Alimentação 🍕", "Extra 💰"])
        vlr = st.number_input("Valor R$", min_value=0.0)
        dt_g = st.date_input("Data", datetime.now())
        if st.form_submit_button("Lançar"):
            nova_g = pd.DataFrame([{"Data": dt_g.strftime("%d/%m/%Y"), "Tipo": tipo, "Categoria": cat, "Valor": vlr}])
            df_geral = pd.concat([df_geral, nova_g], ignore_index=True)
            conn.update(worksheet="Geral", data=df_geral)
            st.rerun()

    st.dataframe(df_geral.sort_index(ascending=False), use_container_width=True)

# --- PÁGINA CARTÕES ---
elif pagina == "Cartões 💳":
    st.header("💳 Limite de Cartões")
    df_c = carregar("Cartoes")
    
    with st.expander("Cadastrar Novo"):
        with st.form("c_form"):
            n = st.text_input("Nome")
            v = st.number_input("Vencimento (Dia)", 1, 31)
            l = st.number_input("Limite R$")
            g = st.number_input("Gasto R$")
            if st.form_submit_button("Salvar"):
                nc = pd.DataFrame([{"Nome": n, "Vencimento": v, "Limite": l, "Gasto": g}])
                df_c = pd.concat([df_c, nc], ignore_index=True)
                conn.update(worksheet="Cartoes", data=df_c)
                st.rerun()

    for _, row in df_c.iterrows():
        disp = row['Limite'] - row['Gasto']
        st.markdown(f"""
        <div class="card">
            <b>{row['Nome']}</b> (Vence dia {row['Vencimento']})<br>
            <span style="color: #dc3545;">Gasto: R$ {row['Gasto']:.2f}</span> | 
            <span style="color: #28a745;">Livre: R$ {disp:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
