import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Bank Pro Premium", page_icon="🏦", layout="centered")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar dados de abas específicas
def carregar(aba):
    try:
        return conn.read(worksheet=aba, ttl="0").dropna(how='all')
    except:
        if aba == "Cartoes":
            return pd.DataFrame(columns=["Nome", "Vencimento", "Limite", "Gasto"])
        return pd.DataFrame(columns=["Data", "Valor", "Descricao"])

# CSS para Cores e Estilo iPhone
st.markdown("""
    <style>
    .entrada { color: #28a745; font-weight: bold; font-size: 18px; }
    .saida { color: #dc3545; font-weight: bold; font-size: 18px; }
    .card { background-color: #1e2130; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# Menu Lateral
st.sidebar.title("🏦 Menu Principal")
pagina = st.sidebar.radio("Selecione a Área", ["Página Geral", "Uber 🚗", "99 Pop 🚙", "Cartões 💳"])

# --- LÓGICA DE EXTRATO COLORIDO ---
def mostrar_extrato(df_extrato, col_desc="Descricao", mostrar_tipo=True):
    if not df_extrato.empty:
        for _, row in df_extrato.sort_index(ascending=False).iterrows():
            # Na Uber/99 tudo é gasto (vermelho), na Geral depende do Tipo
            is_saida = True
            if mostrar_tipo and "Entrada" in str(row.get('Tipo', '')):
                is_saida = False
            
            classe = "saida" if is_saida else "entrada"
            simbolo = "-" if is_saida else "+"
            
            st.markdown(f"""
            <div class="card">
                <small>{row['Data']}</small><br>
                <b>{row[col_desc]}</b><br>
                <span class="{classe}">{simbolo} R$ {row['Valor']:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Ainda não há registros aqui.")

# --- PÁGINA GERAL ---
if pagina == "Página Geral":
    st.header("🏠 Resumo Geral")
    df_geral = carregar("Geral")
    
    with st.expander("➕ Novo Lançamento Geral"):
        with st.form("form_geral"):
            data_g = st.date_input("Data", datetime.now())
            tipo_g = st.selectbox("Tipo", ["Saída 📉", "Entrada 📈"])
            cat_g = st.selectbox("Categoria", ["Alimentação", "Lazer", "Uber (Geral)", "99 (Geral)", "Outros"])
            desc_g = st.text_input("Descrição")
            valor_g = st.number_input("Valor R$", min_value=0.0)
            if st.form_submit_button("Salvar na Geral"):
                nova = pd.DataFrame([{"Data": data_g.strftime("%d/%m/%Y"), "Categoria": cat_g, "Descricao": desc_g, "Valor": valor_g, "Tipo": tipo_g}])
                df_geral = pd.concat([df_geral, nova], ignore_index=True)
                conn.update(worksheet="Geral", data=df_geral)
                st.rerun()
    
    mostrar_extrato(df_geral)

# --- PÁGINAS INDEPENDENTES (UBER E 99) ---
elif pagina in ["Uber 🚗", "99 Pop 🚙"]:
    nome_aba = "Uber" if "Uber" in pagina else "99Pop"
    st.header(f"💰 Controle {pagina}")
    df_esp = carregar(nome_aba)
    
    with st.form(f"form_{nome_aba}"):
        st.write("Adicionar Data e Valor")
        col_d, col_v = st.columns(2)
        data_e = col_d.date_input("Data", datetime.now(), key=f"dt_{nome_aba}")
        valor_e = col_v.number_input("Valor R$", min_value=0.0, key=f"vl_{nome_aba}")
        desc_e = st.text_input("Descrição Opcional", "Corrida", key=f"ds_{nome_aba}")
        
        if st.form_submit_button(f"Salvar em {nome_aba}"):
            nova_e = pd.DataFrame([{"Data": data_e.strftime("%d/%m/%Y"), "Valor": valor_e, "Descricao": desc_e}])
            df_esp = pd.concat([df_esp, nova_e], ignore_index=True)
            conn.update(worksheet=nome_aba, data=df_esp)
            st.success(f"Adicionado à lista da {nome_aba}!")
            st.rerun()
    
    st.markdown("---")
    st.subheader(f"Extrato {nome_aba}")
    mostrar_extrato(df_esp, mostrar_tipo=False) # Tudo aqui é saída

# --- PÁGINA DE CARTÕES ---
elif pagina == "Cartões 💳":
    st.header("💳 Gerenciar Cartões")
    df_c = carregar("Cartoes")
    
    with st.expander("➕ Adicionar Novo Cartão"):
        with st.form("add_cartao"):
            n = st.text_input("Nome do Cartão")
            v = st.number_input("Dia do Vencimento", 1, 31)
            lim = st.number_input("Limite Total R$", min_value=0.0)
            gast = st.number_input("Gasto Atual R$", min_value=0.0)
            if st.form_submit_button("Cadastrar"):
                nc = pd.DataFrame([{"Nome": n, "Vencimento": v, "Limite": lim, "Gasto": gast}])
                df_c = pd.concat([df_c, nc], ignore_index=True)
                conn.update(worksheet="Cartoes", data=df_c)
                st.rerun()

    for _, c in df_c.iterrows():
        disp = c['Limite'] - c['Gasto']
        st.markdown(f"""
        <div class="card">
            <h3>{c['Nome']}</h3>
            <p>Vencimento: Dia {c['Vencimento']}</p>
            <p>Gasto: <span class="saida">R$ {c['Gasto']:.2f}</span></p>
            <p>Disponível: <span class="entrada">R$ {disp:.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(c['Gasto']/c['Limite'], 1.0) if c['Limite'] > 0 else 0)
