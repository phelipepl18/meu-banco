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
            return df
        return pd.DataFrame()
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
    df_g = carregar_dados("Geral")
    df_saldos = carregar_dados("Saldos")
    
    # --- CÁLCULO DINÂMICO DOS BALÕES ---
    lucro_total_real = 0
    baloes_para_exibir = []

    if not df_saldos.empty:
        for _, row in df_saldos.iterrows():
            local = str(row['Local']).strip()
            valor_base = float(row['Valor']) # O que foi "Somado ao Saldo"
            
            # Filtra o que aconteceu no Extrato Geral para este banco/local
            if not df_g.empty:
                movimentacoes = df_g[df_g['Forma_Pagamento'] == local]
                entradas = movimentacoes[movimentacoes['Tipo'] == "Entrada"]['Valor'].sum()
                saidas = movimentacoes[movimentacoes['Tipo'] == "Saída"]['Valor'].sum()
                saldo_atualizado = valor_base + entradas - saidas
            else:
                saldo_atualizado = valor_base
            
            baloes_para_exibir.append({"local": local, "valor": saldo_atualizado})
            lucro_total_real += saldo_atualizado

    # Exibe o Lucro Total (Soma de todos os balões atualizados)
    st.metric("💰 LUCRO LÍQUIDO TOTAL", formatar_br(lucro_total_real))
    
    # Exibe os balões individuais
    if baloes_para_exibir:
        cols = st.columns(len(baloes_para_exibir))
        for idx, b in enumerate(baloes_para_exibir):
            with cols[idx]:
                st.metric(b['local'], formatar_br(b['valor']))

    st.write("---")
    
    col_lanc, col_ajuste = st.columns([2, 1])
    
    with col_lanc:
        with st.form("form_novo_lanc", clear_on_submit=True):
            st.subheader("📝 Novo Lançamento")
            v_val = st.number_input("VALOR (R$)", min_value=0.0, step=0.01)
            # DICA: O nome aqui deve ser IGUAL ao nome que está na aba Saldos (Cédula, Itaú, etc)
            f_pag = st.selectbox("LOCAL DO DINHEIRO", ["Cédula", "Itaú", "Nubank", "Uber", "99Pop", "Débito", "Cartão de Crédito"])
            t_mov = st.selectbox("TIPO", ["Saída", "Entrada"])
            d_mov = st.text_input("DESCRIÇÃO")
            if st.form_submit_button("LANÇAR AGORA"):
                if v_val > 0:
                    nova_linha = pd.DataFrame([{"Data": hoje_str, "Categoria": "Geral", "Descricao": d_mov, "Valor": v_val, "Tipo": t_mov, "Forma_Pagamento": f_pag, "ID": str(uuid.uuid4())[:8]}])
                    conn.update(worksheet="Geral", data=pd.concat([df_g, nova_linha], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

    with col_ajuste:
        with st.expander("⚙️ SOMAR DINHEIRO EXTRA"):
            if not df_saldos.empty:
                l_sel = st.selectbox("Escolha o Balão", df_saldos['Local'].tolist())
                v_add = st.number_input("Valor a somar", min_value=0.0, step=0.01)
                if st.button("Confirmar Soma"):
                    idx = df_saldos[df_saldos['Local'] == l_sel].index[0]
                    df_saldos.at[idx, 'Valor'] += v_add
                    conn.update(worksheet="Saldos", data=df_saldos)
                    st.cache_data.clear()
                    st.rerun()

    # --- EXTRATO ---
    st.write("---")
    st.subheader("📊 Extrato")
    if not df_g.empty:
        st.dataframe(df_g.iloc[::-1].drop(columns=['ID'], errors='ignore').style.apply(colorir_valor, axis=1), use_container_width=True)
        
        with st.expander("🗑️ Excluir Lançamento"):
            df_excluir = df_g.iloc[::-1]
            lista_opcoes = df_excluir.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1).tolist()
            item_sel = st.selectbox("Qual deseja apagar?", lista_opcoes)
            if st.button("Apagar Definitivamente"):
                id_idx = df_excluir.index[df_excluir.apply(lambda r: f"{r['Data']} - {r['Descricao']} ({r['Valor']})", axis=1) == item_sel][0]
                df_final = df_g.drop(id_idx)
                conn.update(worksheet="Geral", data=df_final)
                st.cache_data.clear()
                st.rerun()

# (As outras abas Uber/99Pop continuam funcionando normalmente)
