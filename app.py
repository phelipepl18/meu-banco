import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import plotly.express as px
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Pro Driver - Oficial", layout="wide")

# --- ESTILO GERAL ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    .main { background-color: #121212; }
    [data-testid="stMetric"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba.strip(), ttl=0)
        if df is not None and not df.empty:
            df.columns = [c.strip() for c in df.columns]
            cols_num = ['Valor', 'Limite', 'KM_Rodado', 'Parcelas', 'Dia_Pagamento']
            for col in cols_num:
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

def card_estilizado(titulo, valor, info_extra="", cor_borda="#00FF00"):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2b2b2b 0%, #1e1e1e 100%); padding: 20px; border-radius: 15px; border-left: 5px solid {cor_borda}; margin-bottom: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.3);">
        <h4 style="margin:0; color: #888; font-size: 13px; text-transform: uppercase;">{titulo}</h4>
        <h2 style="margin:5px 0; color: #ffffff; font-weight: bold; font-size: 24px;">{formatar_br(valor)}</h2>
        <div style="margin:0; font-size: 12px; color: #ccc; line-height: 1.4;">{info_extra}</div>
    </div>
    """, unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
if 'pagina' not in st.session_state: st.session_state.pagina = "Geral"

m1, m2, m3, m4, m5 = st.columns(5)
with m1: 
    if st.button("Geral", use_container_width=True): st.session_state.pagina = "Geral"
with m2: 
    if st.button("Uber", use_container_width=True): st.session_state.pagina = "Uber"
with m3: 
    if st.button("99Pop", use_container_width=True): st.session_state.pagina = "99Pop"
with m4: 
    if st.button("Cartão", use_container_width=True): st.session_state.pagina = "Cartao"
with m5: 
    if st.button("Relatórios", use_container_width=True): st.session_state.pagina = "Relatorios"

hoje = datetime.now()
df_g = carregar_dados("Geral")
df_saldos = carregar_dados("Saldos")
df_cartoes = carregar_dados("MeusCartoes")

# --- PÁGINA GERAL ---
if st.session_state.pagina == "Geral":
    st.subheader("Meus Saldos")
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
            with cols_s[i]:
                card_estilizado(local, saldo, "Saldo em conta")
    
    card_estilizado("Lucro Líquido Total", lucro_total, "Soma de todas as contas", cor_borda="#00E5FF")
    
    st.write("---")
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Novo Lançamento")
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
        if st.button("LANÇAR AGORA", use_container_width=True):
            if v > 0:
                nova = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Descricao": d, "Valor": v, "Tipo": t, "Forma_Pagamento": f, "Categoria": cat, "Cartao_Vinculado": cartao_escolhido, "Parcelas": parc, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="Geral", data=pd.concat([df_g, nova], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    with col_r:
        st.subheader("Resumo de Cartões")
        if not df_cartoes.empty:
            for _, r in df_cartoes.iterrows():
                if not df_g.empty:
                    df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
                    gastos_totais = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Forma_Pagamento'] == 'Cartão de Crédito') & (df_g['Tipo'] == 'Saída')]['Valor'].sum()
                    pagos_totais = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Categoria'] == 'Fatura Cartão')]['Valor'].sum()
                    divida_total = gastos_totais - pagos_totais

                    fatura_mes = 0
                    compras_cartao = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Forma_Pagamento'] == 'Cartão de Crédito') & (df_g['Tipo'] == 'Saída')]
                    for _, compra in compras_cartao.iterrows():
                        v_parc = compra['Valor'] / compra['Parcelas']
                        data_inicio = compra['Data_DT']
                        for p in range(int(compra['Parcelas'])):
                            mes_parcela = data_inicio + relativedelta(months=p)
                            if mes_parcela.month == hoje.month and mes_parcela.year == hoje.year:
                                fatura_mes += v_parc
                    
                    pagos_mes = df_g[(df_g['Cartao_Vinculado'] == r['Nome']) & (df_g['Categoria'] == 'Fatura Cartão') & (df_g['Data_DT'].dt.month == hoje.month)]['Valor'].sum()
                    fatura_mes_ajustada = max(0, fatura_mes - pagos_mes)
                else:
                    divida_total = 0
                    fatura_mes_ajustada = 0

                info = f"""
                <b>Limite Disponível:</b> {formatar_br(r['Limite'] - divida_total)}<br>
                <span style='color:#FF4B4B;'><b>Pagar este mês:</b> {formatar_br(fatura_mes_ajustada)}</span><br>
                <b>Total Gasto (Dívida):</b> {formatar_br(divida_total)}
                """
                card_estilizado(r['Nome'], divida_total, info, cor_borda="#FF8C00")

    st.subheader("Extrato")
    if not df_g.empty:
        df_ext = df_g.iloc[::-1].copy()
        for _, row in df_ext.iterrows():
            # Define a cor de fundo baseada no tipo
            cor_fundo = "rgba(255, 75, 75, 0.2)" if row['Tipo'] == "Saída" else "rgba(0, 255, 127, 0.2)"
            cor_texto = "#FF4B4B" if row['Tipo'] == "Saída" else "#00FF7F"
            info_p = f" | {int(row['Parcelas'])}x" if row['Parcelas'] > 1 else ""
            
            # Balão colorido para o extrato
            st.markdown(f"""
                <div style="background-color: {cor_fundo}; padding: 15px; border-radius: 10px; border-left: 5px solid {cor_texto}; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: white;">{row['Data']} - {row['Descricao']}</span>
                        <span style="font-weight: bold; color: {cor_texto}; font-size: 18px;">{formatar_br(row['Valor'])}{info_p}</span>
                    </div>
                    <div style="font-size: 12px; color: #bbb; margin-top: 5px;">
                        Local: {row['Forma_Pagamento']} | Categoria: {row['Categoria']} | Cartão: {row['Cartao_Vinculado']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Botão de excluir logo abaixo do balão (Streamlit não permite botões dentro de HTML puro)
            if st.button("Excluir", key=f"del_{row['ID']}", use_container_width=False):
                conn.update(worksheet="Geral", data=df_g[df_g['ID'] != row['ID']])
                st.cache_data.clear(); st.rerun()

# --- PÁGINA CARTÃO ---
elif st.session_state.pagina == "Cartao":
    st.header("Gestão de Cartões")
    with st.expander("Adicionar Novo Cartão"):
        with st.form("new_card_form"):
            n_c = st.text_input("Nome do Cartão")
            l_c = st.number_input("Limite Total", min_value=0.0)
            v_c = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10)
            if st.form_submit_button("Cadastrar"):
                novo_cartao = pd.DataFrame([{"Nome": n_c, "Limite": l_c, "Dia_Pagamento": v_c, "ID": str(uuid.uuid4())[:8]}])
                conn.update(worksheet="MeusCartoes", data=pd.concat([df_cartoes, novo_cartao], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    if not df_cartoes.empty:
        cols = st.columns(3)
        for idx, r in df_cartoes.iterrows():
            with cols[idx % 3]:
                card_estilizado(r['Nome'], r['Limite'], f"Vencimento todo dia {int(r['Dia_Pagamento'])}", cor_borda="#FF8C00")
                if st.button(f"Remover {r['Nome']}", key=f"del_c_{r['ID']}", use_container_width=True):
                    conn.update(worksheet="MeusCartoes", data=df_cartoes[df_cartoes['ID'] != r['ID']])
                    st.cache_data.clear(); st.rerun()

# --- PÁGINAS UBER / 99POP / RELATÓRIOS ---
elif st.session_state.pagina in ["Uber", "99Pop"]:
    aba = st.session_state.pagina
    st.header(f"Ganhos {aba}")
    df_app = carregar_dados(aba)
    with st.form(f"f_{aba}"):
        v_dia = st.number_input("Ganhos", min_value=0.0); km_dia = st.number_input("KM", min_value=0)
        if st.form_submit_button("Salvar"):
            nova_l = pd.DataFrame([{"Data": hoje.strftime("%d/%m/%Y"), "Valor": v_dia, "KM_Rodado": km_dia, "ID": str(uuid.uuid4())[:8]}])
            conn.update(worksheet=aba, data=pd.concat([df_app, nova_l], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    if not df_app.empty:
        card_estilizado(f"Total {aba}", df_app['Valor'].sum(), f"KM Total: {df_app['KM_Rodado'].sum()}")
        st.dataframe(df_app.iloc[::-1], use_container_width=True)

elif st.session_state.pagina == "Relatorios":
    st.header("Relatórios")
    if not df_g.empty:
        df_g['Data_DT'] = pd.to_datetime(df_g['Data'], dayfirst=True, errors='coerce')
        df_saidas = df_g[(df_g['Tipo'] == 'Saída') & (df_g['Data_DT'].dt.month == hoje.month)].copy()
        df_grafico = df_saidas[~df_saidas['Forma_Pagamento'].isin(["Uber", "99Pop"])].copy()
        if not df_grafico.empty:
            df_grafico['Label'] = df_grafico.apply(lambda x: x['Descricao'] if x['Categoria'] == 'Outros' else x['Categoria'], axis=1)
            st.plotly_chart(px.pie(df_grafico, values='Valor', names='Label', hole=.4, template="plotly_dark"), use_container_width=True)
            card_estilizado("Gasto Total do Mês", df_grafico['Valor'].sum(), "Despesas fora dos apps", "#FF4B4B")
