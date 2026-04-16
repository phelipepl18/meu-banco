import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px

st.set_page_config(page_title="Pro Driver - Gestão Completa", layout="wide")

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
            for col in ['Valor', 'Limite', 'KM_Rodado', 'Parcelas']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if "ID" not in df.columns:
                df["ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def formatar_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- NAVEGAÇÃO ---
if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"

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

# --- PÁGINA GERAL (MANTIDA CONFORME SOLICITADO) ---
if st.session_state.pagina == "Geral":
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
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("📝 Novo Lançamento")
        v = st.number_input("VALOR (R$)", min_value=0.0, step=0.01)
        c1, c2 = st.columns(2)
        with c1:
            f = st.selectbox("SAINDO DE (LOCAL)", ["Cédula", "Banco Itaú", "Nubank", "Uber", "99Pop", "Cartão de Crédito"])
            t = st.selectbox("TIPO", ["Saída", "Entrada"])
        with c2:
            cat = st.selectbox("CATEGORIA", ["Combustível", "Manutenção", "Alimentação", "Aluguel", "Fatura Cartão", "Outros"])
            cartao_escolhido = "N/A"
            parc = 1
            if f == "Cartão de Crédito" or cat == "Fatura Cartão":
                cartao_list = df_cartoes['Nome'].tolist() if not df_cartoes.empty else []
                cartao_escolhido = st.selectbox("QUAL CARTÃO?", cartao_list)
                if f == "Cartão de Crédito":
                    parc = st.number_input("Nº DE PARCELAS", min_value=1, max_value=48, value=1)
        d = st.text_input("DESCRIÇÃO")
        if st.button("🚀 LANÇAR AGORA", use_container_width=True):
            if v > 0:
                nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "Parcelas": parc, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_r:
        st.subheader("💳 Limites")
        if not df_cartoes.empty:
            for _, r in df_cartoes.iterrows():
                gastos = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Forma_Pagamento'] == 'Cartão de Crédito') & (df_g['Tipo'] == 'Saída')]['Valor'].sum() if not df_g.empty else 0
                pagos = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Categoria'] == 'Fatura Cartão')]['Valor'].sum() if not df_g.empty else 0
                disp = r['Limite'] - (gastos - pagos)
                st.metric(r['Nome'], formatar_br(disp), f"Dívida: {formatar_br(gastos - pagos)}", delta_color="inverse")

    st.subheader("📊 Extrato")
    if not df_g.empty:
        df_ext = df_g.iloc[::-1].copy()
        for _, row in df_ext.iterrows():
            cor = "🔴" if row['Tipo'] == "Saída" else "🟢"
            with st.expander(f"{cor} {row['Data']} - {row['Descricao']} ({formatar_br(row['Valor'])})"):
                st.write(f"Local: {row['Forma_Pagamento']} | Categoria: {row['Categoria']}")
                if st.button("🗑️ Excluir", key=f"del_{row['ID']}"):
                    conn.update(worksheet="Geral", data=df_g[df_g['ID'] != row['ID']])
                    st.cache_data.clear(); st.rerun()

# --- PÁGINAS DOS APPS (UBER E 99POP) ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(f"💰 Histórico de Ganhos {aba}")
    df_app = carregar_dados(aba)
    
    col_f, col_v = st.columns([1, 2])
    with col_f:
        with st.form(f"f_{aba}"):
            v_dia = st.number_input("Ganhos do Dia (Bruto)", min_value=0.0)
            km_dia = st.number_input("KM Rodado", min_value=0)
            if st.form_submit_button("Salvar Dia"):
                nova_l = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Valor": v_dia, "KM_Rodado": km_dia, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet=aba, data=pd.concat([df_app, nova_l], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    
    with col_v:
        if not df_app.empty:
            total_v = df_app['Valor'].sum()
            total_km = df_app['KM_Rodado'].sum()
            st.metric("Total Ganho no App", formatar_br(total_v))
            st.metric("KM Total Percorrido", f"{total_km} km")
            if total_km > 0:
                st.metric("Média R$/KM", formatar_br(total_v/total_km))

    st.write("### Registros Diários")
    if not df_app.empty:
        df_app_inv = df_app.iloc[::-1].copy()
        for _, r in df_app_inv.iterrows():
            with st.expander(f"📅 {r['Data']} - {formatar_br(r['Valor'])}"):
                st.write(f"KM: {r['KM_Rodado']}")
                if st.button("Excluir Dia", key=f"del_{aba}_{r['ID']}"):
                    conn.update(worksheet=aba, data=df_app[df_app['ID'] != r['ID']])
                    st.cache_data.clear(); st.rerun()

# --- PÁGINA CARTÃO (GESTÃO DE LIMITES) ---
elif st.session_state.pagina == "Cartao":
    st.header("💳 Gerenciar Meus Cartões")
    with st.form("new_card"):
        n_c = st.text_input("Nome do Cartão"); l_c = st.number_input("Limite do Cartão", min_value=0.0)
        if st.form_submit_button("Cadastrar Cartão"):
            novo_df = pd.concat([df_cartoes, pd.DataFrame([{"Nome": n_c, "Limite": l_c, "ID": str(uuid.uuid4())[:8]}])], ignore_index=True)
            conn.update(worksheet="MeusCartoes", data=novo_df)
            st.cache_data.clear(); st.rerun()
    
    if not df_cartoes.empty:
        for _, r in df_cartoes.iterrows():
            col1, col2 = st.columns([4,1])
            col1.write(f"💳 **{r['Nome']}** | Limite Total: {formatar_br(r['Limite'])}")
            if col2.button("🗑️", key=f"del_c_{r['ID']}"):
                conn.update(worksheet="MeusCartoes", data=df_cartoes[df_cartoes['ID'] != r['ID']])
                st.cache_data.clear(); st.rerun()

# --- PÁGINA RELATÓRIOS (GRÁFICOS) ---
elif st.session_state.pagina == "Relatorios":
    st.header("📊 Resumo Financeiro")
    if not df_g.empty:
        df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        df_saidas = df_g[(df_g['Tipo'] == 'Saída') & (df_g['Data_DT'].dt.month == hoje.month)].copy()
        df_grafico = df_saidas[~df_saidas['Forma_Pagamento'].isin(["Uber", "99Pop"])].copy()
        
        if not df_grafico.empty:
            df_grafico['Label'] = df_grafico.apply(lambda x: x['Descricao'] if x['Categoria'] == 'Outros' else x['Categoria'], axis=1)
            fig = px.pie(df_grafico, values='Valor', names='Label', hole=.4, template="plotly_dark", title="Gastos por Categoria (Mês Atual)")
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Gasto Total Real", formatar_br(df_grafico['Valor'].sum()))
        else:
            st.warning("Nenhum gasto registrado fora dos apps neste mês.")
