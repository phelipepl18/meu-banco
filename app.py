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
    .btn-excluir { color: #FF4B4B; cursor: pointer; }
    </style>
    """, unsafe_allow_html=True)

# Conecta ao Google Sheets
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
        color = 'background-color: rgba(255, 75, 75, 0.1);' if row['Tipo'] == 'Saída' else 'background-color: rgba(0, 255, 0, 0.05);'
    else:
        color = 'background-color: rgba(0, 255, 0, 0.05);'
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
    
    # 1. SALDOS AUTOMÁTICOS
    st.subheader("💰 Meus Saldos Atualizados")
    if not df_saldos.empty:
        cols_s = st.columns(4)
        for i, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            saldo_inicial = float(row['Valor'])
            # Filtra movimentações no Geral para este Local
            mov_local = df_g[df_g['Forma_Pagamento'] == local]
            entradas = mov_local[mov_local['Tipo'] == "Entrada"]['Valor'].sum()
            saidas = mov_local[mov_local['Tipo'] == "Saída"]['Valor'].sum()
            
            saldo_atual = saldo_inicial + entradas - saidas
            with cols_s[i % 4]:
                st.metric(local, formatar_br(saldo_atual))

    # 2. DEFINIR SALDO INICIAL
    with st.expander("📝 Ajustar Saldo Inicial (Mão)"):
        if not df_saldos.empty:
            with st.form("form_ajuste_saldos"):
                local_sel = st.selectbox("Local:", df_saldos['Local'].tolist())
                valor_novo = st.number_input("Quanto você tem agora neste local?", min_value=0.0, step=0.01, format="%.2f")
                if st.form_submit_button("Atualizar"):
                    df_saldos.loc[df_saldos['Local'] == local_sel, 'Valor'] = valor_novo
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear(); st.rerun()

    # 3. NOVO LANÇAMENTO
    st.write("---")
    with st.form("form_lancamento", clear_on_submit=True):
        st.subheader("📝 Novo Lançamento")
        valor_in = st.number_input("VALOR (R$)", min_value=0.0, step=0.01, format="%.2f")
        c1, c2 = st.columns(2)
        with c1:
            tipo_in = st.selectbox("TIPO", ["Saída", "Entrada"])
            forma_in = st.selectbox("PAGAMENTO/LOCAL", ["Cédula", "Itaú", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
        with c2:
            desc_in = st.text_input("DESCRIÇÃO")
            c_nome = "N/A"
            if forma_in == "Cartão de Crédito":
                c_nome = st.selectbox("QUAL CARTÃO?", df_cartoes['Nome'].tolist()) if not df_cartoes.empty else "N/A"
        
        if st.form_submit_button("LANÇAR AGORA", use_container_width=True):
            if valor_in > 0:
                nova_d = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": desc_in, "Valor": float(valor_in), "Tipo": tipo_in, "Forma_Pagamento": forma_in, "Cartao_Nome": c_nome, "ID": str(uuid.uuid4())[:8]}])
                df_final = pd.concat([df_g, nova_d], ignore_index=True)
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear(); st.rerun()

    # 4. EXTRATO COM OPÇÃO DE EXCLUIR
    st.write("---")
    st.subheader("📊 Extrato")
    if not df_g.empty:
        df_mostrar = df_g.iloc[::-1].copy() # Mais recentes primeiro
        
        for index, row in df_mostrar.iterrows():
            with st.container():
                col_info, col_btn = st.columns([0.85, 0.15])
                with col_info:
                    cor = "🔴" if row['Tipo'] == "Saída" else "🟢"
                    st.write(f"{cor} **{row['Data']}** - {row['Descricao']} | **{formatar_br(row['Valor'])}** ({row['Forma_Pagamento']})")
                with col_btn:
                    if st.button("🗑️", key=f"del_{row['ID']}"):
                        # Remove a linha pelo ID
                        df_novo_geral = df_g[df_g['ID'] != row['ID']]
                        conn.update(worksheet="Geral", data=df_novo_geral)
                        st.cache_data.clear()
                        st.success("Excluído!")
                        st.rerun()
                st.write("---")

# --- PÁGINAS UBER / 99 ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(aba)
    df_app = carregar_dados(aba)
    with st.form(f"f_{aba}", clear_on_submit=True):
        v = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        k = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            n = pd.DataFrame([{"Data": hoje_str, "Valor": float(v), "KM_Rodado": k, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet=aba, data=pd.concat([df_app, n], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    
    # Lista com exclusão para Uber/99 também
    for index, row in df_app.iloc[::-1].iterrows():
        c_i, c_b = st.columns([0.85, 0.15])
        c_i.write(f"📅 {row['Data']} | 💰 {formatar_br(row['Valor'])} | 🛣️ {row['KM_Rodado']} KM")
        if c_b.button("🗑️", key=f"del_app_{row['ID']}"):
            df_n_app = df_app[df_app['ID'] != row['ID']]
            conn.update(worksheet=aba, data=df_n_app)
            st.cache_data.clear(); st.rerun()
