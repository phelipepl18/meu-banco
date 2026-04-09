import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# --- CONFIGURAÇÃO DA PÁGINA PARA MOBILE ---
st.set_page_config(page_title="Bank Pro", page_icon="📊", layout="centered")

# Estilo CSS para deixar com cara de App de iPhone
st.markdown("""
    <style>
    .main { background-color: #f2f2f7; }
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #ffffff;
        border: 1px solid #e5e5ea;
        color: #000000;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #e5e5ea;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE DADOS ---
ARQUIVO = "dados_financeiros.json"

def carregar_dados():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    return {
        "saldo": 0.0,
        "historico": [],
        "cartoes": [],
        "viagens_uber": [],
        "viagens_99": [],
        "contas_mensais": []
    }

def salvar_dados(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f)

if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

def atualizar_saldo(valor, tipo, operacao="adicionar"):
    if operacao == "adicionar":
        st.session_state.dados["saldo"] += valor if tipo == "Entrada" else -valor
    else: # excluir
        st.session_state.dados["saldo"] -= valor if tipo == "Entrada" else -valor
    salvar_dados(st.session_state.dados)

# --- INTERFACE ---
st.title(" Bank Pro")

# Menu de Navegação estilo Abas (melhor para celular)
aba1, aba2, aba3, aba4, aba5 = st.tabs(["📊 Fluxo", "🚗 Uber", "🚕 99", "💳 Cartão", "📝 Contas"])

# --- ABA 1: FLUXO (PÁGINA PRINCIPAL) ---
with aba1:
    # Cards de Saldo
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Saldo Atual", f"R$ {st.session_state.dados['saldo']:,.2f}")
    with c2:
        receita_total = sum(i['valor'] for i in st.session_state.dados['historico'] if i['tipo'] == "Entrada")
        st.metric("Entradas", f"R$ {receita_total:,.2f}")

    # Botões de Ação Rápida
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ Receita"):
            st.session_state.abrir_form = "Entrada"
    with col_btn2:
        if st.button("➖ Despesa"):
            st.session_state.abrir_form = "Saída"

    # Formulário de Lançamento
    if 'abrir_form' in st.session_state:
        with st.expander(f"Novo Lançamento: {st.session_state.abrir_form}", expanded=True):
            with st.form("form_transacao"):
                desc = st.text_input("Descrição (Ex: Uber, Aluguel)")
                valor = st.number_input("Valor R$", min_value=0.0, step=0.01)
                data_lanche = st.date_input("Data", datetime.now())
                
                if st.form_submit_button("Confirmar"):
                    novo_item = {
                        "tipo": st.session_state.abrir_form,
                        "valor": valor,
                        "desc": desc,
                        "data": data_lanche.strftime("%d %b")
                    }
                    st.session_state.dados["historico"].append(novo_item)
                    if "uber" in desc.lower(): st.session_state.dados["viagens_uber"].append(novo_item)
                    if "99" in desc.lower(): st.session_state.dados["viagens_99"].append(novo_item)
                    
                    atualizar_saldo(valor, st.session_state.abrir_form)
                    del st.session_state.abrir_form
                    st.rerun()

    # Extrato com Rolagem (Tabela)
    st.subheader("Atividade Recente")
    if st.session_state.dados["historico"]:
        df = pd.DataFrame(st.session_state.dados["historico"]).iloc[::-1] # Inverter para ver mais recentes
        st.dataframe(df, use_container_width=True, height=250)
        
        if st.button("🗑️ Limpar último registro"):
            item = st.session_state.dados["historico"].pop()
            atualizar_saldo(item['valor'], item['tipo'], "excluir")
            st.rerun()
    
    # Ajuste manual de saldo
    with st.expander("⚙️ Ajustar Saldo Manual"):
        novo_s = st.number_input("Novo Valor", value=st.session_state.dados["saldo"])
        if st.button("Resetar Saldo"):
            st.session_state.dados["saldo"] = novo_s
            salvar_dados(st.session_state.dados)
            st.rerun()

# --- ABA 2 & 3: UBER E 99 (GRÁFICOS) ---
def mostrar_pagina_app(nome, lista_key, cor):
    st.subheader(f"Ganhos {nome}")
    lista = st.session_state.dados[lista_key]
    if lista:
        df_app = pd.DataFrame(lista)
        # Agrupar por data para o gráfico
        graf_data = df_app.groupby("data")["valor"].sum().reset_index()
        st.bar_chart(graf_data.set_index("data"), color=cor)
        st.write(df_app.iloc[::-1])
    else:
        st.info("Nenhuma corrida registrada.")

with aba2:
    mostrar_pagina_app("Uber", "viagens_uber", "#05a3ad")

with aba3:
    mostrar_pagina_app("99 App", "viagens_99", "#E67E22")

# --- ABA 4: CARTÕES ---
with aba4:
    st.subheader("Meus Cartões")
    if st.button("+ Adicionar Cartão"):
        st.session_state.add_card = True
    
    if st.session_state.get('add_card'):
        n_c = st.text_input("Nome do Cartão")
        l_c = st.number_input("Limite R$", min_value=0.0)
        if st.button("Salvar Cartão"):
            st.session_state.dados["cartoes"].append({"nome": n_c, "limite": l_c})
            salvar_dados(st.session_state.dados)
            del st.session_state.add_card
            st.rerun()

    for c in st.session_state.dados["cartoes"]:
        gasto = sum(i['valor'] for i in st.session_state.dados['historico'] if i['desc'].lower() == c['nome'].lower())
        st.write(f"**{c['nome'].upper()}**")
        st.progress(min(gasto/c['limite'], 1.0) if c['limite'] > 0 else 0)
        st.caption(f"Gasto: R$ {gasto} / Limite: R$ {c['limite']}")

# --- ABA 5: CONTAS ---
with aba5:
    st.subheader("Contas Fixas")
    # Lógica similar aos cartões para adicionar e listar...
    st.info("Adicione suas contas fixas para controlar o que falta pagar.")