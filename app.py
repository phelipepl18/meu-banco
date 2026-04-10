import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver v3", page_icon="🚕", layout="centered")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS ---
def carregar_dados(nome_aba):
    try:
        # Tenta ler a aba específica
        df = conn.read(worksheet=nome_aba, ttl="0")
        return df.dropna(how='all')
    except Exception:
        # Se a aba não existir, cria o formato correto
        if nome_aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        elif nome_aba in ["Uber", "99Pop"]:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "KM_Rodado"])
        else:
            return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo"])

# --- ESTILO ---
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

# --- PÁGINA: RESUMO ---
if pagina == "Resumo do Dia":
    st.header("📊 Lucro de Hoje")
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    df_g = carregar_dados("Geral")
    
    ganho_u = df_u[df_u['Data'] == hoje]['Valor'].sum() if not df_u.empty and 'Valor' in df_u.columns else 0
    ganho_n = df_n[df_n['Data'] == hoje]['Valor'].sum() if not df_n.empty and 'Valor' in df_n.columns else 0
    total_ganhos = ganho_u + ganho_n
    
    gastos_hoje = 0
    if not df_g.empty and 'Tipo' in df_g.columns:
        # Filtra por data e por tipo Saída
        gastos_hoje = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'].str.contains("Saída", na=False))]['Valor'].sum()
    
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
    st.write(f"🎯 Faltam R$ {max(meta-total_ganhos, 0.0):.2f} para a meta.")

# --- PÁGINAS UBER E 99 ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    with st.form(f"form_{aba}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        d = col1.date_input("Data", datetime.now())
        v = col2.number_input("Valor Ganho R$", min_value=0.0)
        km = st.number_input("KM Rodados no dia", min_value=0)
        txt = st.text_input("Nota/Descrição")
        
        if st.form_submit_button("Salvar no Banco"):
            nova = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": v, "Descricao": txt, "KM_Rodado": km}])
            df_atualizado = pd.concat([df_app, nova], ignore_index=True)
            try:
                conn.update(worksheet=aba, data=df_atualizado)
                st.success("✅ Salvo com sucesso!")
                st.rerun()
            except Exception as e:
                st.error("❌ Erro de Permissão: Verifique se a planilha está como 'EDITOR' no botão Compartilhar do Google.")

# --- PÁGINA GERAL ---
elif pagina == "Gastos Geral ⛽":
    st.header("⛽ Lançar Gastos/Extras")
    df_geral = carregar_dados("Geral")
    
    with st.form("form_g", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
        cat = st.selectbox("Categoria", ["Combustível ⛽", "Alimentação 🍕", "Manutenção 🔧", "Outros"])
        vlr = st.number_input("Valor R$", min_value=0.0)
        dat = st.date_input("Data", datetime.now())
        if st.form_submit_button("Confirmar"):
            nova_g = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": cat, "Valor": vlr, "Tipo": tipo, "Descricao": ""}])
            df_final = pd.concat([df_geral, nova_g], ignore_index=True)
            try:
                conn.update(worksheet="Geral", data=df_final)
                st.success("✅ Registrado!")
                st.rerun()
            except:
                st.error("❌ Erro ao salvar. Mude o acesso da planilha para EDITOR.")

# --- PÁGINA CARTÕES ---
elif pagina == "Cartões 💳":
    st.header("💳 Controle de Cartões")
    df_c = carregar_dados("Cartoes")
    
    with st.expander("Adicionar Novo Cartão"):
        with st.form("f_c"):
            n = st.text_input("Nome do Cartão")
            l = st.number_input("Limite Total", min_value=0.0)
            g = st.number_input("Gasto Atual", min_value=0.0)
            if st.form_submit_button("Cadastrar"):
                nova_c = pd.DataFrame([{"Nome": n, "Limite": l, "Gasto": g, "Vencimento": 0}])
                df_c_novo = pd.concat([df_c, nova_c], ignore_index=True)
                conn.update(worksheet="Cartoes", data=df_c_novo)
                st.rerun()

    for _, r in df_c.iterrows():
        disp = r['Limite'] - r['Gasto']
        st.markdown(f"""
        <div class="card">
            <b>{r['Nome']}</b><br>
            <span class="gasto">Gasto: R$ {r['Gasto']:.2f}</span> | 
            <span style="color:#28a745">Livre: R$ {disp:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
