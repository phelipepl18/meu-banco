import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# Configuração da Página
st.set_page_config(page_title="Bank Pro Driver", layout="wide")

# --- ESTILO CSS ---
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
        if df is not None and not df.empty:
            # Limpeza de dados para evitar erros de soma
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- FUNÇÃO PARA COLORIR O EXTRATO ---
def colorir_valor(row):
    # Vermelho para Saída, Verde para Entrada
    color = 'background-color: rgba(255, 75, 75, 0.2);' if row['Tipo'] == 'Saída' else 'background-color: rgba(0, 255, 0, 0.1);'
    return [color] * len(row)

# --- MENU SUPERIOR ---
st.title("Pro Driver")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: btn_geral = st.button("Geral", use_container_width=True)
with col_m2: btn_uber = st.button("Uber", use_container_width=True)
with col_m3: btn_99 = st.button("99Pop", use_container_width=True)
with col_m4: btn_cartao = st.button("Cartao", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99 Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

hoje_str = datetime.now().strftime("%d/%m/%Y")

# --- PÁGINA: GERAL ---
if st.session_state.pagina == "Geral":
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    df_g = carregar_dados("Geral")
    df_cartoes = carregar_dados("MeusCartoes")
    df_saldos = carregar_dados("Saldos")
    
    # 1. SALDOS ACUMULADOS
    st.subheader("Saldos")
    if not df_saldos.empty:
        cols_s = st.columns(4)
        for i, row in df_saldos.iterrows():
            with cols_s[i % 4]:
                st.metric(row['Local'], f"R$ {float(row['Valor']):.2f}")
    
    with st.expander("Ajustar Saldos"):
        if not df_saldos.empty:
            local_sel = st.selectbox("Local:", df_saldos['Local'].tolist())
            novo_v = st.number_input("Novo Valor:", min_value=0.0, step=1.0)
            if st.button("Salvar Ajuste"):
                df_saldos.loc[df_saldos['Local'] == local_sel, 'Valor'] = novo_v
                conn.update(worksheet="Saldos", data=df_saldos)
                st.cache_data.clear(); st.rerun()

    # 2. RESUMO DO DIA (Cálculo Corrigido)
    st.write("---")
    # Ganhos Uber + 99 hoje
    ganho_uber = df_u[df_u['Data'] == hoje_str]['Valor'].sum() if not df_u.empty else 0
    ganho_99 = df_n[df_n['Data'] == hoje_str]['Valor'].sum() if not df_n.empty else 0
    # Entradas manuais hoje
    entradas_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Entrada")]['Valor'].sum() if not df_g.empty else 0
    
    total_ganhos = ganho_uber + ganho_99 + entradas_g
    
    # Saídas hoje (ignorando cartão de crédito para não abater do lucro imediato)
    total_saidas = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum() if not df_g.empty else 0
    
    lucro = total_ganhos - total_saidas
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Hoje", f"R$ {total_ganhos:.2f}")
    c2.metric("Saídas Hoje", f"R$ {total_saidas:.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro:.2f}")

    # 3. LANÇAMENTO
    st.write("---")
    col_f, col_e = st.columns([1, 2])
    with col_f:
        st.subheader("Lançamento")
        with st.form("form_g", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
            vlr = st.number_input("Valor", min_value=0.0)
            forma = st.selectbox("Pagamento", ["Dinheiro/PIX", "Débito", "Cartão de Crédito"])
            c_sel = "N/A"; p_sel = 1
            if forma == "Cartão de Crédito" and not df_cartoes.empty:
                c_sel = st.selectbox("Qual Cartão?", df_cartoes['Nome'].tolist())
                p_sel = st.number_input("Parcelas", min_value=1, step=1)
            desc = st.text_input("Descrição")
            data_lanc = st.date_input("Data do Lançamento", datetime.now())
            if st.form_submit_button("Lançar"):
                nova = pd.DataFrame([{"Data": data_lanc.strftime("%d/%m/%Y"), "Categoria": "Geral", "Descricao": desc, "Valor": float(vlr), "Tipo": tipo, "Forma_Pagamento": forma, "Cartao_Nome": c_sel, "Parcelas": p_sel, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_e:
        st.subheader("Extrato Geral")
        if not df_g.empty:
            # Ordena pelo mais recente e aplica cores
            df_display = df_g.drop(columns=['ID'], errors='ignore').tail(15)
            st.dataframe(df_display.style.apply(colorir_valor, axis=1), use_container_width=True)

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99 Pop"]:
    aba = "Uber" if "Uber" in st.session_state.pagina else "99Pop"
    st.header(aba)
    df_app = carregar_dados(aba)
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form(f"f_{aba}", clear_on_submit=True):
            v = st.number_input("Valor", min_value=0.0); k = st.number_input("KM", min_value=0)
            d_app = st.date_input("Data", datetime.now())
            if st.form_submit_button("Salvar"):
                n = pd.DataFrame([{"Data": d_app.strftime("%d/%m/%Y"), "Valor": float(v), "Descricao": "", "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, n], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    with c2: 
        if not df_app.empty:
            df_app['Tipo'] = 'Entrada'
            st.dataframe(df_app.drop(columns=['ID', 'Tipo'], errors='ignore').tail(10).style.apply(colorir_valor, axis=1), use_container_width=True)

# --- PÁGINA: CARTÃO ---
elif st.session_state.pagina == "Cartao":
    st.header("Cartão")
    df_cartoes = carregar_dados("MeusCartoes"); df_g = carregar_dados("Geral")
    ca, cb = st.columns([1, 2])
    with ca:
        with st.form("f_c"):
            nc = st.text_input("Nome Cartão"); lc = st.number_input("Limite")
            if st.form_submit_button("Adicionar"):
                nv = pd.DataFrame([{"Nome": nc, "Limite": float(lc), "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, nv], ignore_index=True))
                st.cache_data.clear(); st.rerun()
        for _, r in df_cartoes.iterrows():
            gasto = df_g[df_g['Cartao_Nome'] == r['Nome']]['Valor'].sum() if "Cartao_Nome" in df_g.columns else 0
            st.info(f"**{r['Nome']}**\n\nDisp: R$ {r['Limite']-gasto:.2f} / Lim: R$ {r['Limite']:.2f}")
    with cb:
        st.subheader("Extrato Cartão")
        if not df_g.empty and "Forma_Pagamento" in df_g.columns:
            compras = df_g[df_g['Forma_Pagamento'] == "Cartão de Crédito"][['Data', 'Cartao_Nome', 'Valor', 'Parcelas', 'Tipo']]
            st.dataframe(compras.style.apply(colorir_valor, axis=1), use_container_width=True)
