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
        df = conn.read(worksheet=nome_aba, ttl=0)
        return df.dropna(how='all')
    except Exception:
        if nome_aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        elif nome_aba in ["Uber", "99Pop"]:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])
        else:
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .card { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 10px; }
    .lucro { color: #28a745; font-weight: bold; font-size: 22px; }
    .gasto { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Menu Lateral
st.sidebar.title("🚕 Painel do Motorista")
meta = st.sidebar.number_input("Sua Meta Diária (R$)", min_value=0, value=250)
pagina = st.sidebar.radio("Selecione:", ["Resumo do Dia", "Uber 🚗", "99 Pop 🚙", "Gastos Geral ⛽", "Cartões 💳"])

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

    st.markdown(f"""
    <div class="card">
        <small>Ganhos nos Apps</small><br><span>R$ {total_ganhos:.2f}</span><br><br>
        <small>Gastos (Gasolina/Outros)</small><br><span class="gasto">- R$ {gastos_hoje:.2f}</span><br><hr>
        <small>LUCRO REAL</small><br><span class="lucro">R$ {lucro:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    prog = min(total_ganhos/meta, 1.0) if meta > 0 else 0
    st.progress(prog)
    st.write(f"🎯 Meta: {prog*100:.1f}% concluída")

# --- PÁGINA: GASTOS GERAL ⛽ ---
elif pagina == "Gastos Geral ⛽":
    st.header("⛽ Lançar Gastos")
    df_g = carregar_dados("Geral")
    
    with st.form("form_gastos", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0)
        dat = st.date_input("Data", datetime.now())
        
        if st.form_submit_button("Salvar Gasto"):
            nova_linha = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": cat, "Valor": vlr, "Tipo": tipo, "Descricao": ""}])
            df_final = pd.concat([df_g, nova_linha], ignore_index=True)
            try:
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear()
                st.success("✅ Gravado!")
                st.rerun()
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {e}")
    
    st.subheader("📋 Extrato de Gastos")
    st.dataframe(df_g.sort_index(ascending=False), use_container_width=True)

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
            df_final = pd.concat([df_app, nova], ignore_index=True)
            try:
                conn.update(worksheet=aba, data=df_final)
                st.cache_data.clear()
                st.success("✅ Sucesso!")
                st.rerun()
            except Exception as e:
                if "200" in str(e):
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {e}")

    st.subheader("📋 Últimas Corridas")
    st.dataframe(df_app.sort_index(ascending=False), use_container_width=True)

# --- PÁGINA CARTÕES ---
elif pagina == "Cartões 💳":
    st.header("💳 Cartões")
    df_c = carregar_dados("Cartoes")
    st.dataframe(df_c, use_container_width=True)
