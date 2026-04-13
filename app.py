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
    input { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        # Remove espaços do nome da aba para evitar erro de leitura
        df = conn.read(worksheet=nome_aba.strip(), ttl=0)
        if df is not None and not df.empty:
            for col in ['Valor', 'Limite', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        return df if df is not None else pd.DataFrame()
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

# --- PÁGINA: GERAL ---
if st.session_state.pagina == "Geral":
    df_u = carregar_dados("Uber"); df_n = carregar_dados("99Pop"); df_g = carregar_dados("Geral")
    df_saldos = carregar_dados("Saldos"); df_cartoes = carregar_dados("MeusCartoes")
    
    # --- LÓGICA DE SALDO AUTOMÁTICO ---
    st.subheader("💰 Meus Saldos Atualizados")
    if not df_saldos.empty:
        cols_s = st.columns(4)
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip() # Limpa espaços do nome
            saldo_inicial = float(row['Valor'])
            
            # Soma entradas e saídas no Geral filtrando por esse Local
            entradas = df_g[(df_g['Forma_Pagamento'] == local) & (df_g['Tipo'] == "Entrada")]['Valor'].sum()
            saidas = df_g[(df_g['Forma_Pagamento'] == local) & (df_g['Tipo'] == "Saída")]['Valor'].sum()
            
            saldo_atual = saldo_inicial + entradas - saidas
            
            with cols_s[i % 4]:
                st.metric(local, formatar_br(saldo_atual))
    
    # --- DEFINIR SALDO INICIAL ---
    with st.expander("📝 Definir Saldo Inicial"):
        if not df_saldos.empty:
            with st.form("form_ajuste_saldos"):
                local_sel = st.selectbox("Selecione o Local:", df_saldos['Local'].tolist())
                valor_novo = st.number_input("Valor que você tem agora (R$):", min_value=0.0, step=0.01, format="%.2f")
                if st.form_submit_button("Salvar Saldo Inicial"):
                    # Atualiza o valor na tabela de Saldos
                    df_saldos.loc[df_saldos['Local'] == local_sel, 'Valor'] = valor_novo
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.success("Saldo atualizado!"); st.rerun()

    # RESUMO DO DIA
    st.write("---")
    g_u = df_u[df_u['Data'] == hoje_str]['Valor'].sum() if not df_u.empty else 0
    g_n = df_n[df_n['Data'] == hoje_str]['Valor'].sum() if not df_n.empty else 0
    e_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Entrada")]['Valor'].sum() if not df_g.empty else 0
    s_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum() if not df_g.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Hoje", formatar_br(g_u + g_n + e_g))
    c2.metric("Saídas Hoje", formatar_br(s_g))
    c3.metric("Lucro Líquido", formatar_br((g_u + g_n + e_g) - s_g))

    # NOVO LANÇAMENTO
    st.write("---")
    st.subheader("📝 Novo Lançamento")
    with st.form("form_geral", clear_on_submit=True):
        v_in = st.number_input("VALOR (R$)", min_value=0.0, step=0.01, format="%.2f")
        col1, col2 = st.columns(2)
        with col1:
            t_in = st.selectbox("TIPO", ["Saída", "Entrada"])
            f_in = st.selectbox("PAGAMENTO", ["Cédula", "Itaú", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
        with col2:
            d_in = st.text_input("DESCRIÇÃO")
            c_nome = "N/A"
            if f_in == "Cartão de Crédito" and not df_cartoes.empty:
                c_nome = st.selectbox("QUAL CARTÃO?", df_cartoes['Nome'].tolist())
        
        if st.form_submit_button("LANÇAR AGORA", use_container_width=True):
            if v_in > 0:
                nova_d = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": d_in, "Valor": float(v_in), "Tipo": t_in, "Forma_Pagamento": f_in, "Cartao_Nome": c_nome, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova_d], ignore_index=True))
                st.cache_data.clear(); st.success("Lançado!"); st.rerun()

    # EXTRATO
    if not df_g.empty:
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore').style.apply(colorir_valor, axis=1), use_container_width=True)

# --- PÁGINAS UBER / 99POP ---
elif st.session_state.pagina == "Uber":
    st.header("Uber")
    df_app = carregar_dados("Uber")
    with st.form("f_uber", clear_on_submit=True):
        v = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        k = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            n = pd.DataFrame([{"Data": hoje_str, "Valor": float(v), "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet="Uber", data=pd.concat([df_app, n], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    st.dataframe(df_app.iloc[::-1], use_container_width=True)

elif st.session_state.pagina == "99Pop":
    st.header("99Pop")
    df_app = carregar_dados("99Pop")
    with st.form("f_99", clear_on_submit=True):
        v = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        k = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            n = pd.DataFrame([{"Data": hoje_str, "Valor": float(v), "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet="99Pop", data=pd.concat([df_app, n], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    st.dataframe(df_app.iloc[::-1], use_container_width=True)
