import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# 1. Configuração da Página (Deve ser a primeira linha de comando Streamlit)
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

# 2. Conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão com a planilha: {e}")
    st.stop()

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba.strip(), ttl=0)
        if df is not None and not df.empty:
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
            return df
        return pd.DataFrame(columns=["Data", "Categoria", "Descricao", "Valor", "Tipo", "Forma_Pagamento", "ID"])
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def colorir_valor(row):
    if 'Tipo' in row.index:
        color = 'background-color: rgba(255, 75, 75, 0.2);' if row['Tipo'] == 'Saída' else 'background-color: rgba(0, 255, 0, 0.1);'
    else:
        color = 'background-color: rgba(0, 255, 0, 0.1);'
    return [color] * len(row)

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

# --- LÓGICA DA PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # Carregamento seguro
    df_g = carregar_dados("Geral")
    df_saldos = carregar_dados("Saldos")
    df_u = carregar_dados("Uber")
    df_n = carregar_dados("99Pop")
    
    # Cálculos de Saldo
    lucro_total = 0
    saldos_lista = []
    
    if not df_saldos.empty:
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            saldo_ini = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local] if not df_g.empty else pd.DataFrame()
            
            ent = movs[movs['Tipo'] == "Entrada"]['Valor'].sum() if not movs.empty else 0
            sai = movs[movs['Tipo'] == "Saída"]['Valor'].sum() if not movs.empty else 0
            
            atual = saldo_ini + ent - sai
            saldos_lista.append({"local": local, "valor": atual})
            lucro_total += atual

    # Exibição dos Balões
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total))
    
    if saldos_lista:
        cols = st.columns(len(saldos_lista))
        for idx, s in enumerate(saldos_lista):
            with cols[idx]:
                st.metric(s['local'], formatar_br(s['valor']))

    st.write("---")
    
    # Formulário e Ajustes
    col_l, col_a = st.columns([2, 1])
    
    with col_l:
        with st.form("form_novo_lanc", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v_val = st.number_input("VALOR (R$)", min_value=0.0, step=0.01)
            f_pag = st.selectbox("LOCAL", ["Cédula", "Itaú", "Nubank", "Uber", "99Pop"])
            t_mov = st.selectbox("TIPO", ["Saída", "Entrada"])
            d_mov = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR"):
                if v_val > 0:
                    nova_linha = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": d_mov, "Valor": v_val, "Tipo": t_mov, "Forma_Pagamento": f_pag, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova_linha], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

    with col_a:
        with st.expander("⚙️ SOMAR AO SALDO"):
            if not df_saldos.empty:
                l_sel = st.selectbox("Local", df_saldos['Local'].tolist())
                v_add = st.number_input("Quanto somar?", min_value=0.0, step=0.01)
                if st.button("Confirmar Soma"):
                    idx = df_saldos[df_saldos['Local'] == l_sel].index[0]
                    df_saldos.at[idx, 'Valor'] += v_add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear()
                    st.rerun()

    # Extrato
    st.write("---")
    if not df_g.empty:
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore').style.apply(colorir_valor, axis=1), use_container_width=True)
        
        with st.expander("🗑️ Excluir Registro"):
            df_sel = df_g.iloc[::-1]
            opcoes = df_sel.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1).tolist()
            item_excluir = st.selectbox("Selecione para apagar:", opcoes)
            if st.button("Confirmar Exclusão"):
                # Acha o ID do item selecionado e remove
                idx_to_remove = df_sel.index[df_sel.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1) == item_excluir][0]
                df_final = df_g.drop(idx_to_remove)
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear()
                st.rerun()

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(aba)
    df_app = carregar_dados(aba)
    with st.form(f"f_{aba}"):
        v_app = st.number_input("Valor", min_value=0.0)
        k_app = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            nova_l = pd.DataFrame([{"Data": hoje_str, "Valor": v_app, "KM_Rodado": k_app, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet=aba, data=pd.concat([df_app, nova_l], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
    st.dataframe(df_app.iloc[::-1], use_container_width=True)
