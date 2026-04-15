import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

st.set_page_config(page_title="Bank Pro Driver", layout="wide")

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
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- MENU ---
st.title("Pro Driver")
m1, m2, m3, m4 = st.columns(4)
with m1: btn_geral = st.button("Geral", use_container_width=True)
with m2: btn_uber = st.button("Uber", use_container_width=True)
with m3: btn_99 = st.button("99Pop", use_container_width=True)
with m4: btn_cartao = st.button("Cartao", use_container_width=True)

if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"
if btn_geral: st.session_state.pagina = "Geral"
if btn_uber: st.session_state.pagina = "Uber"
if btn_99: st.session_state.pagina = "99Pop"
if btn_cartao: st.session_state.pagina = "Cartao"

hoje_str = datetime.now().strftime("%d/%m/%Y")

if st.session_state.pagina == "Geral":
    df_g = carregar_dados("Geral")
    df_saldos = carregar_dados("Saldos")
    
    # --- CÁLCULO DOS BALÕES ---
    lucro_total_real = 0
    baloes_display = []

    if not df_saldos.empty:
        for _, row in df_saldos.iterrows():
            local_planilha = str(row['Local']).strip()
            valor_base = float(row['Valor'])
            
            if not df_g.empty:
                movs = df_g[df_g['Forma_Pagamento'].str.strip() == local_planilha]
                entradas = pd.to_numeric(movs[movs['Tipo'] == "Entrada"]['Valor'], errors='coerce').sum()
                saidas = pd.to_numeric(movs[movs['Tipo'] == "Saída"]['Valor'], errors='coerce').sum()
                saldo_atual = valor_base + entradas - saidas
            else:
                saldo_atual = valor_base
            
            baloes_display.append({"local": local_planilha, "valor": saldo_atual})
            lucro_total_real += saldo_atual

    # Exibe Balão de Lucro Total
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total_real))
    
    # Exibe Balões Individuais
    if baloes_display:
        cols = st.columns(len(baloes_display))
        for idx, b in enumerate(baloes_display):
            with cols[idx]:
                st.metric(b['local'], formatar_br(b['valor']))

    st.write("---")
    
    col_l, col_a = st.columns([2, 1])
    
    with col_l:
        with st.form("form_novo", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v = st.number_input("VALOR (R$)", min_value=0.0, step=0.01)
            
            # --- LISTA ATUALIZADA COM DÉBITO E CRÉDITO ---
            lista_locais = ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"]
            f = st.selectbox("LOCAL DO DINHEIRO", lista_locais)
            
            t = st.selectbox("TIPO", ["Saída", "Entrada"])
            d = st.text_input("DESCRIÇÃO")
            
            if st.form_submit_button("LANÇAR AGORA"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje_str, "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

    with col_a:
        with st.expander("⚙️ SOMAR AO SALDO"):
            if not df_saldos.empty:
                sel = st.selectbox("Escolha o Balão", df_saldos['Local'].tolist())
                add = st.number_input("Quanto quer somar?", min_value=0.0, step=0.01)
                if st.button("Confirmar Soma"):
                    idx = df_saldos[df_saldos['Local'] == sel].index[0]
                    df_saldos.at[idx, 'Valor'] += add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear()
                    st.rerun()

    # --- EXTRATO ---
    if not df_g.empty:
        st.write("---")
        st.subheader("📊 Extrato")
        
        def colorir(row):
            return ['background-color: rgba(255, 75, 75, 0.2)' if row['Tipo'] == 'Saída' else 'background-color: rgba(0, 255, 0, 0.1)'] * len(row)
        
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore').style.apply(colorir, axis=1), use_container_width=True)
        
        with st.expander("🗑️ Excluir Registro"):
            df_del = df_g.iloc[::-1]
            opcs = df_del.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1).tolist()
            item = st.selectbox("Selecionar para apagar:", opcs)
            if st.button("Confirmar Exclusão"):
                id_rem = df_del.index[df_del.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1) == item][0]
                df_f = df_g.drop(id_rem)
                conn.update(worksheet="Geral", data=df_f)
                st.cache_data.clear(); st.rerun()
