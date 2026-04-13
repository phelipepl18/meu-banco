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
    /* Estilo para o balão de Lucro Total */
    .total-box { background-color: #004d00; border: 2px solid #00FF00; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
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

if st.session_state.pagina == "Geral":
    df_u = carregar_dados("Uber"); df_n = carregar_dados("99Pop"); df_g = carregar_dados("Geral")
    df_saldos = carregar_dados("Saldos"); df_cartoes = carregar_dados("MeusCartoes")
    
    # --- CÁLCULO DOS SALDOS E LUCRO TOTAL ---
    lucro_total_acumulado = 0
    saldos_calculados = []

    if not df_saldos.empty:
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            saldo_ini = float(row['Valor'])
            movs = df_g[df_g['Forma_Pagamento'] == local]
            saldo_atual = saldo_ini + movs[movs['Tipo'] == "Entrada"]['Valor'].sum() - movs[movs['Tipo'] == "Saída"]['Valor'].sum()
            saldos_calculados.append({"local": local, "valor": saldo_atual})
            lucro_total_acumulado += saldo_atual

    # --- EXIBIÇÃO DO LUCRO TOTAL ---
    st.markdown("---")
    st.metric("💰 LUCRO LÍQUIDO TOTAL (Soma de tudo)", formatar_br(lucro_total_acumulado))
    st.write("---")

    # --- BALÕES INDIVIDUAIS ---
    st.subheader("Saldos Individuais")
    cols_s = st.columns(len(saldos_calculados) if saldos_calculados else 4)
    for idx, s in enumerate(saldos_calculados):
        with cols_s[idx]:
            st.metric(s['local'], formatar_br(s['valor']))

    # --- RESUMO DO DIA ---
    st.write("---")
    g_u = df_u[df_u['Data'] == hoje_str]['Valor'].sum() if not df_u.empty else 0
    g_n = df_n[df_n['Data'] == hoje_str]['Valor'].sum() if not df_n.empty else 0
    e_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Entrada")]['Valor'].sum() if not df_g.empty else 0
    s_g = df_g[(df_g['Data'] == hoje_str) & (df_g['Tipo'] == "Saída") & (df_g['Forma_Pagamento'] != "Cartão de Crédito")]['Valor'].sum() if not df_g.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ganhos Hoje", formatar_br(g_u + g_n + e_g))
    c2.metric("Saídas Hoje", formatar_br(s_g))
    c3.metric("Lucro Hoje", formatar_br((g_u + g_n + e_g) - s_g))

    # --- NOVO LANÇAMENTO ---
    st.write("---")
    col_l, col_a = st.columns([2, 1])
    with col_l:
        with st.form("form_geral", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v_in = st.number_input("VALOR (R$)", min_value=0.0, step=0.01, format="%.2f")
            f_in = st.selectbox("PAGAMENTO/LOCAL", ["Cédula", "Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
            t_in = st.selectbox("TIPO", ["Saída", "Entrada"])
            d_in = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR AGORA", use_container_width=True):
                if v_in > 0:
                    nova_d = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": d_in, "Valor": float(v_in), "Tipo": t_in, "Forma_Pagamento": f_in, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova_d], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    with col_a:
        with st.expander("⚙️ Definir Saldo Inicial"):
            if not df_saldos.empty:
                local_sel = st.selectbox("Local", df_saldos['Local'].tolist())
                v_novo = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f", key="ajuste_s")
                if st.button("Atualizar Saldo"):
                    df_saldos.loc[df_saldos['Local'] == local_sel, 'Valor'] = v_novo
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.rerun()

    # --- EXTRATO E EXCLUSÃO ---
    st.write("---")
    st.subheader("📊 Extrato")
    if not df_g.empty:
        df_inv = df_g.iloc[::-1]
        st.dataframe(df_inv.drop(columns=['ID'], errors='ignore').style.apply(colorir_valor, axis=1), use_container_width=True)
        
        with st.expander("🗑️ Excluir Registro"):
            id_excluir = st.selectbox("Selecione para apagar:", df_inv.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({formatar_br(r['Valor'])})", axis=1))
            idx_real = df_inv.index[df_inv.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({formatar_br(r['Valor'])})", axis=1) == id_excluir][0]
            if st.button("Confirmar Exclusão", type="primary"):
                df_final = df_g.drop(idx_real)
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear(); st.rerun()
