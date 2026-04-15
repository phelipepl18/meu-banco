import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px

st.set_page_config(page_title="Pro Driver - Oficial", layout="wide")

# --- ESTILO ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba.strip(), ttl=0)
        if df is not None and not df.empty:
            df.columns = [c.strip() for c in df.columns]
            for col in ['Valor', 'Limite', 'KM_Rodado']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            # Garante que todos tenham ID para exclusão
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- ESTADO DA PÁGINA ---
if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"

# --- NAVEGAÇÃO ---
m1, m2, m3, m4, m5 = st.columns(5)
with m1: 
    if st.button("🏠 Geral", use_container_width=True): st.session_state.pagina = "Geral"
with m2: 
    if st.button("🚗 Uber", use_container_width=True): st.session_state.pagina = "Uber"
with m3: 
    if st.button("🚕 99Pop", use_container_width=True): st.session_state.pagina = "99Pop"
with m4: 
    if st.button("💳 Cartão", use_container_width=True): st.session_state.pagina = "Cartao"
with m5: 
    if st.button("📊 Gastos", use_container_width=True): st.session_state.pagina = "Relatorios"

hoje = datetime.now()
df_g = carregar_dados("Geral")
df_saldos = carregar_dados("Saldos")
df_cartoes = carregar_dados("MeusCartoes")

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # 1. CÁLCULO DOS BALÕES (Sempre atualiza após exclusão)
    lucro_total = 0
    if not df_saldos.empty:
        cols_s = st.columns(len(df_saldos))
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            v_base = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local] if not df_g.empty else pd.DataFrame()
            ent = movs[movs['Tipo'] == "Entrada"]['Valor'].sum() if not movs.empty else 0
            sai = movs[movs['Tipo'] == "Saída"]['Valor'].sum() if not movs.empty else 0
            saldo = v_base + ent - sai
            lucro_total += saldo
            cols_s[i].metric(local, formatar_br(saldo))
    
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total))
    st.write("---")

    col_l, col_a = st.columns([2, 1])
    with col_l:
        with st.form("form_novo", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v = st.number_input("VALOR (R$)", min_value=0.0)
            c1, c2 = st.columns(2)
            with c1:
                f = st.selectbox("LOCAL", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
                t = st.selectbox("TIPO", ["Saída", "Entrada"])
            with c2:
                cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel Carro", "Seguro", "Limpeza", "Outros"])
                cartao_list = df_cartoes['Nome'].tolist() if not df_cartoes.empty else []
                cartao_escolhido = st.selectbox("QUAL CARTÃO?", ["N/A"] + cartao_list) if f == "Cartão de Crédito" else "N/A"
            d = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    with col_a:
        with st.expander("⚙️ AJUSTE INICIAL"):
            if not df_saldos.empty:
                sel = st.selectbox("Balão", df_saldos['Local'].tolist())
                add = st.number_input("Valor", min_value=0.0, key="adj")
                if st.button("Confirmar Ajuste"):
                    df_saldos.loc[df_saldos['Local'] == sel, 'Valor'] += add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.rerun()

    # 2. EXTRATO COM OPÇÃO DE EXCLUIR
    st.subheader("📊 Extrato e Gerenciamento")
    if not df_g.empty:
        # Criamos uma lista para exibir de forma amigável
        df_display = df_g.iloc[::-1].copy()
        
        for index, row in df_display.iterrows():
            with st.expander(f"{row['Data']} - {row['Descricao']} ({formatar_br(row['Valor'])})"):
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.write(f"**Tipo:** {row['Tipo']} | **Local:** {row['Forma_Pagamento']} | **Categoria:** {row['Categoria']}")
                with col_btn:
                    # Botão único para cada ID
                    if st.button("🗑️ Excluir", key=f"del_{row['ID']}"):
                        df_novo = df_g[df_g['ID'] != row['ID']]
                        conn.update(worksheet="Geral", data=df_novo)
                        st.success("Removido com sucesso!")
                        st.cache_data.clear(); st.rerun()
    else:
        st.info("Nenhum lançamento encontrado.")

# --- MANTÉM AS OUTRAS PÁGINAS (Uber, 99, Cartão, Relatórios) ---
# ... (restante do código das outras abas)
