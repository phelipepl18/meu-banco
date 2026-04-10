import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver v2", page_icon="🚕", layout="centered")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS COM PROTEÇÃO ---
def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl="0")
        return df.dropna(how='all')
    except Exception:
        # Se a aba não existir ou der erro, cria um visual vazio com colunas
        if nome_aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        elif nome_aba in ["Uber", "99Pop"]:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])
        else:
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .card { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 10px; }
    .lucro { color: #28a745; font-weight: bold; font-size: 20px; }
    .gasto { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
meta = st.sidebar.number_input("Sua Meta Diária (R$)", min_value=0, value=250)
pagina = st.sidebar.radio("Ir para:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽", "Cartões 💳"])

# --- PÁGINA: RESUMO DO DIA ---
if pagina == "Resumo do Dia":
    st.header("📊 Lucro de Hoje")
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    df_g = carregar_dados("Geral")
    
    # Soma Ganhos
    ganho_u = df_u[df_u['Data'] == hoje]['Valor'].sum() if 'Valor' in df_u.columns else 0
    ganho_n = df_n[df_n['Data'] == hoje]['Valor'].sum() if 'Valor' in df_n.columns else 0
    total_ganhos = ganho_u + ganho_n
    
    # Soma Gastos
    total_gastos = 0
    if not df_g.empty and 'Tipo' in df_g.columns:
        total_gastos = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'].str.contains("Saída"))]['Valor'].sum()
    
    lucro = total_ganhos - total_gastos

    st.markdown(f"""
    <div class="card">
        <small>Ganhos nos Apps</small><br><span>R$ {total_ganhos:.2f}</span><br><br>
        <small>Gastos/Combustível</small><br><span class="gasto">- R$ {total_gastos:.2f}</span><br><hr>
        <small>LUCRO LÍQUIDO</small><br><span class="lucro">R$ {lucro:.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    prog = min(total_ganhos/meta, 1.0) if meta > 0 else 0
    st.write(f"🎯 Meta: {prog*100:.1f}% concluída")
    st.progress(prog)

# --- PÁGINAS UBER E 99 ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Lançar {aba}")
    df_app = carregar_dados(aba)
    
    with st.form(f"form_{aba}"):
        col1, col2 = st.columns(2)
        d = col1.date_input("Data")
        v = col2.number_input("Valor Ganho R$", min_value=0.0)
        km = st.number_input("KM Rodados")
        txt = st.text_input("Nota")
        if st.form_submit_button("Salvar Corrida"):
            nova_linha = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": v, "Descricao": txt, "KM_Rodado": km}])
            df_app = pd.concat([df_app, nova_linha], ignore_index=True)
            conn.update(worksheet=aba, data=df_app)
            st.success("Salvo na Planilha!")
            st.rerun()
    
    st.write("### Últimos Lançamentos")
    st.dataframe(df_app.sort_index(ascending=False), use_container_width=True)

# --- PÁGINA GERAL (COMBUSTÍVEL) ---
elif pagina == "Gastos Geral ⛽":
    st.header("⛽ Gastos Gerais")
    df_geral = carregar_dados("Geral")
    
    with st.form("form_geral"):
        t = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        c = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0)
        dat = st.date_input("Data")
        if st.form_submit_button("Lançar Agora"):
            nova_g = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": c, "Valor": vlr, "Tipo": t, "Descricao": ""}])
            df_geral = pd.concat([df_geral, nova_g], ignore_index=True)
            conn.update(worksheet="Geral", data=df_geral)
            st.success("Gasto registrado!")
            st.rerun()
    
    st.dataframe(df_geral.sort_index(ascending=False), use_container_width=True)

# --- PÁGINA CARTÕES ---
elif pagina == "Cartões 💳":
    st.header("💳 Meus Cartões")
    df_c = carregar_dados("Cartoes")
    
    with st.expander("Novo Cartão"):
        with st.form("f_cartao"):
            n = st.text_input("Nome")
            vnc = st.number_input("Vencimento (Dia)", 1, 31)
            lmt = st.number_input("Limite")
            gst = st.number_input("Gasto Atual")
            if st.form_submit_button("Cadastrar"):
                nova_c = pd.DataFrame([{"Nome": n, "Vencimento": vnc, "Limite": lmt, "Gasto": gst}])
                df_c = pd.concat([df_c, nova_c], ignore_index=True)
                conn.update(worksheet="Cartoes", data=df_c)
                st.rerun()

    for _, r in df_c.iterrows():
        st.markdown(f"""
        <div class="card">
            <b>{r['Nome']}</b> (Vence dia {r['Vencimento']})<br>
            <span class="gasto">Gasto: R$ {r['Gasto']:.2f}</span> | 
            <span>Livre: R$ {r['Limite']-r['Gasto']:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
