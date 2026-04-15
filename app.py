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

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    # BALÕES DE SALDO
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
            if st.form_submit_button("LANÇAR AGORA"):
                if v > 0:
                    nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    with col_a:
        with st.expander("⚙️ AJUSTE DE SALDO"):
            if not df_saldos.empty:
                sel = st.selectbox("Escolha o Balão", df_saldos['Local'].tolist())
                add = st.number_input("Valor", min_value=0.0, key="adj")
                if st.button("Somar ao Saldo"):
                    df_saldos.loc[df_saldos['Local'] == sel, 'Valor'] += add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.rerun()

    st.write("---")
    st.subheader("📊 Extrato Detalhado")
    
    if not df_g.empty:
        # Inverte para mostrar os mais novos primeiro
        df_extrato = df_g.iloc[::-1].copy()
        
        for index, row in df_extrato.iterrows():
            # Define a cor do ícone baseado no tipo
            icon = "🔴" if row['Tipo'] == "Saída" else "🟢"
            
            with st.expander(f"{icon} {row['Data']} - {row['Descricao']} | {formatar_br(row['Valor'])}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Tipo:** {row['Tipo']}")
                    st.write(f"**Local:** {row['Forma_Pagamento']}")
                with c2:
                    st.write(f"**Categoria:** {row['Categoria']}")
                    st.write(f"**Cartão:** {row['Cartao_Vinculado']}")
                with c3:
                    if st.button("🗑️ Excluir Registro", key=f"del_{row['ID']}"):
                        df_novo = df_g[df_g['ID'] != row['ID']]
                        conn.update(worksheet="Geral", data=df_novo)
                        st.cache_data.clear(); st.rerun()
    else:
        st.info("Nenhum lançamento no extrato.")

# --- PÁGINA RELATÓRIOS ---
elif st.session_state.pagina == "Relatorios":
    st.header("📊 Análise de Gastos Mensais")
    if not df_g.empty:
        df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        df_saidas = df_g[(df_g['Tipo'] == 'Saída') & (df_g['Data_DT'].dt.month == hoje.month)].copy()
        df_grafico = df_saidas[~df_saidas['Forma_Pagamento'].isin(["Uber", "99Pop"])].copy()
        
        if not df_grafico.empty:
            df_grafico['Label'] = df_grafico.apply(lambda x: x['Descricao'] if x['Categoria'] == 'Outros' else x['Categoria'], axis=1)
            fig = px.pie(df_grafico, values='Valor', names='Label', hole=.4, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Total de Gastos (Saídas)", formatar_br(df_grafico['Valor'].sum()))
        else:
            st.info("Sem saídas registradas este mês (fora dos apps).")

# --- PÁGINAS UBER / 99 / CARTÃO ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(f"💰 Histórico {aba}")
    df_app = carregar_dados(aba)
    with st.form(f"f_{aba}"):
        v_app = st.number_input("Valor", min_value=0.0); k_app = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            n_l = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Valor": v_app, "KM_Rodado": k_app, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet=aba, data=pd.concat([df_app, n_l], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    if not df_app.empty: st.dataframe(df_app.iloc[::-1], use_container_width=True)

elif st.session_state.pagina == "Cartao":
    st.header("💳 Limites de Cartão")
    if not df_cartoes.empty:
        for i, r in df_cartoes.iterrows():
            g = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Tipo'] == 'Saída')]['Valor'].sum() if not df_g.empty else 0
            st.metric(r['Nome'], formatar_br(r['Limite'] - g), delta=f"Gasto: {formatar_br(g)}")
