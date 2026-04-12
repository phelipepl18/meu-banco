import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# Estilo CSS Personalizado
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        if not df.empty:
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df
    except:
        if nome_aba == "MeusCartoes": return pd.DataFrame(columns=["Nome", "Limite", "ID"])
        if nome_aba == "Saldos": return pd.DataFrame(columns=["Local", "Valor", "ID"])
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
    df_saldos = carregar_dados("Saldos")
    
    # Garantir que Saldos existam
    if df_saldos.empty:
        df_saldos = pd.DataFrame([
            {"Local": "Cédula", "Valor": 0.0, "ID": "1"},
            {"Local": "Banco Itaú", "Valor": 0.0, "ID": "2"},
            {"Local": "App Uber", "Valor": 0.0, "ID": "3"},
            {"Local": "App 99Pop", "Valor": 0.0, "ID": "4"}
        ])

    # 1. RESUMO FINANCEIRO DO DIA
    st.subheader(f"Resumo de Hoje: {hoje}")
    ganho_total = (df_u[df_u['Data'] == hoje]['Valor'].sum() + 
                   df_n[df_n['Data'] == hoje]['Valor'].sum() + 
                   (df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Entrada")]['Valor'].sum() if "Tipo" in df_g.columns else 0))
    
    despesas_caixa = 0
    if "Forma_Pagamento" in df_g.columns and "Tipo" in df_g.columns:
        despesas_caixa = df_g[(df_g['Data'] == hoje) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum()
    
    lucro_liquido = ganho_total - despesas_caixa
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Brutos (Hoje)", f"R$ {ganho_total:.2f}")
    c2.metric("Despesas em Caixa", f"R$ {despesas_caixa:.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro_liquido:.2f}")

    # 2. SEÇÃO DE SALDOS (ONDE ESTÁ O DINHEIRO AGORA)
    st.write("---")
    st.subheader("💰 Conferência de Saldos (Total Acumulado)")
    cols_s = st.columns(4)
    for i, row in df_saldos.iterrows():
        with cols_s[i]:
            st.metric(row['Local'], f"R$ {row['Valor']:.2f}")
    
    with st.expander("Ajustar Saldos (Cédula, Bancos e Apps)"):
        col_adj1, col_adj2 = st.columns(2)
        with col_adj1:
            local_sel = st.selectbox("Qual local deseja ajustar?", df_saldos['Local'].tolist())
        with col_adj2:
            novo_v = st.number_input("Novo Valor Total", min_value=0.0, step=10.0, format="%.2f")
        if st.button("Salvar Ajuste de Saldo"):
            df_saldos.loc[df_saldos['Local'] == local_sel, 'Valor'] = novo_v
            conn.update(worksheet="Saldos", data=df_saldos)
            st.cache_data.clear(); st.success("Saldo Atualizado!"); st.rerun()

    # 3. LANÇAMENTO DE MOVIMENTAÇÕES
    st.write("---")
    col_f, col_e = st.columns([1, 2])
    with col_f:
        st.subheader("Novo Lançamento")
        with st.form("form_g", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            cat = st.selectbox("Categoria", ["Combustível", "Alimentação", "Manutenção", "Lazer", "Outros"])
            desc = st.text_input("Descrição")
            vlr = st.number_input("Valor", min_value=0.0, step=0.01)
            forma = st.selectbox("Forma de Pagamento", ["Dinheiro/PIX", "Débito", "Cartão de Crédito"])
            
            c_sel = "N/A"; p_sel = 1
            if forma == "Cartão de Crédito" and not df_cartoes.empty:
                c_sel = st.selectbox("Selecione o Cartão", df_cartoes['Nome'].tolist())
                p_sel = st.number_input("Parcelas", min_value=1, step=1)
            
            dat = st.date_input("Data", datetime.now())
            if st.form_submit_button("Registrar"):
                nova = pd.DataFrame([{"Data": dat.strftime("%d/%m/%Y"), "Categoria": cat, "Descricao": desc, "Valor": float(vlr), "Tipo": tipo, "Forma_Pagamento": forma, "Cartao_Nome": c_sel, "Parcelas": p_sel, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_e:
        st.subheader("Extrato Geral")
        if not df_g.empty:
            st.dataframe(df_g.drop(columns=['ID'], errors='ignore').tail(10), use_container_width=True)
            with st.expander("Limpar Extrato Geral"):
                it = df_g['Data'] + " - " + df_g['Descricao'] + " (R$ " + df_g['Valor'].astype(str) + ")"
                sel_del = st.selectbox("Item para apagar:", it.tolist())
                if st.button("Apagar Item"):
                    id_d = df_g[it == sel_del]['ID'].values[0]
                    conn.update(worksheet="Geral", data=df_g[df_g['ID'] != id_d])
                    st.cache_data.clear(); st.rerun()

# --- PÁGINA: CARTÃO DE CRÉDITO ---
elif st.session_state.pagina == "Cartao":
    st.header("Gerenciamento de Cartoes")
    df_cartoes = carregar_dados("MeusCartoes"); df_g = carregar_dados("Geral")
    
    col_cad, col_ext = st.columns([1, 2])
    with col_cad:
        with st.form("n_c", clear_on_submit=True):
            n = st.text_input("Nome do Cartao"); l = st.number_input("Limite", min_value=0.0)
            if st.form_submit_button("Cadastrar"):
                nv = pd.DataFrame([{"Nome": n, "Limite": float(l), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, nv], ignore_index=True))
                st.cache_data.clear(); st.rerun()
        
        for _, row in df_cartoes.iterrows():
            gasto = df_g[df_g['Cartao_Nome'] == row['Nome']]['Valor'].sum() if "Cartao_Nome" in df_g.columns else 0
            st.info(f"**{row['Nome']}**\n\nDisponível: R$ {row['Limite'] - gasto:.2f} / Limite: R$ {row['Limite']:.2f}")

    with col_ext:
        st.subheader("Extrato do Cartão")
        if "Forma_Pagamento" in df_g.columns:
            st.dataframe(df_g[df_g['Forma_Pagamento'] == "Cartão de Crédito"][['Data', 'Cartao_Nome', 'Descricao', 'Valor', 'Parcelas']], use_container_width=True)

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(f"Ganhos {aba}"); df_app = carregar_dados(aba)
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form(f"f_{aba}", clear_on_submit=True):
            d = st.date_input("Data", datetime.now()); v = st.number_input("Valor", min_value=0.0); k = st.number_input("KM", min_value=0)
            if st.form_submit_button("Salvar"):
                n = pd.DataFrame([{"Data": d.strftime("%d/%m/%Y"), "Valor": float(v), "Descricao": "", "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, n], ignore_index=True)); st.cache_data.clear(); st.rerun()
    with c2: 
        st.dataframe(df_app.drop(columns=['ID'], errors='ignore').tail(10), use_container_width=True)
        with st.expander(f"Limpar Extrato {aba}"):
            it = df_app['Data'] + " - R$ " + df_app['Valor'].astype(str)
            if st.button(f"Apagar Selecionado {aba}"):
                sel = st.selectbox("Item:", it.tolist(), key=f"del_{aba}")
                id_d = df_app[it == sel]['ID'].values[0]
                conn.update(worksheet=aba, data=df_app[df_app['ID'] != id_d])
                st.cache_data.clear(); st.rerun()
