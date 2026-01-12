import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- FUNÇÕES DE AÇÃO ---

def deletar_item(id_item):
    conn = create_connection()
    conn.execute("DELETE FROM lancamentos WHERE id = ?", (id_item,))
    conn.commit()
    conn.close()
    st.rerun()

@st.dialog("Editar Lançamento")
def popup_editar_item(row):
    st.markdown(f"### ✏️ Editar Registro")
    
    nova_data = st.date_input("Data", pd.to_datetime(row['data']))
    nova_desc = st.text_input("Descrição", str(row['descricao']))
    novo_valor = st.number_input("Valor R$", min_value=0.0, value=float(row['valor']), format="%.2f")
    
    st.caption("Nota: Alterações aqui afetam apenas esta parcela individual.")

    if st.button("Salvar Alterações", use_container_width=True):
        conn = create_connection()
        conn.execute("UPDATE lancamentos SET data = ?, descricao = ?, valor = ? WHERE id = ?", 
                     (str(nova_data), nova_desc, novo_valor, row['id']))
        conn.commit()
        conn.close()
        st.toast("Alterado com sucesso!", icon="📝")
        st.rerun()

@st.dialog("Confirmar Pagamento")
def popup_pagar_item(id_item, descricao, valor):
    st.markdown(f"### 💸 Confirmar Quitação")
    st.info(f"**{descricao}**\n\nValor: **R$ {valor:,.2f}**")
    data_pagto = st.date_input("Data do Pagamento", date.today())
    
    if st.button("Confirmar e Atualizar", use_container_width=True):
        conn = create_connection()
        nova_desc = descricao.replace("Pendente", "Paga")
        conn.execute("UPDATE lancamentos SET descricao = ?, data = ? WHERE id = ?", (nova_desc, str(data_pagto), id_item))
        
        if "Dívida:" in descricao:
            try:
                nome_divida = descricao.split("|")[0].replace("Dívida:", "").split("(")[0].strip()
                conn.execute("UPDATE dividas SET valor_pago = valor_pago + ? WHERE nome = ?", (valor, nome_divida))
            except: pass
        
        conn.commit()
        conn.close()
        st.toast("Pagamento registrado!", icon="✅")
        st.rerun()

@st.dialog("Novo Lançamento", width="medium")
def popup_novo_lancamento():
    st.markdown("### 📝 Registrar Movimentação")
    # REMOVIDO "Dívida" das opções abaixo
    tipo_mov = st.radio("", ["Despesa", "Receita", "Meta", "Investimento"], horizontal=True)
    
    conn = create_connection()
    df_metas = pd.read_sql_query("SELECT id, nome, icone FROM metas", conn)
    df_invest_tipos = pd.read_sql_query("SELECT id, nome FROM tipos_investimentos", conn)
    df_cartoes = pd.read_sql_query("SELECT nome, fechamento, vencimento FROM cartoes_credito", conn)
    df_resp = pd.read_sql_query("SELECT nome FROM responsaveis ORDER BY nome ASC", conn)
    
    categorias = []
    try:
        tabela_cat = "categorias_receitas" if tipo_mov == "Receita" else "categorias_despesas"
        categorias = pd.read_sql_query(f"SELECT nome FROM {tabela_cat} ORDER BY nome ASC", conn)['nome'].tolist()
    except: categorias = ["Geral"]
    conn.close()

    c1, c2 = st.columns(2)
    with c1:
        data_f = st.date_input("Data da Compra", date.today())
        valor_f = st.number_input("Valor Total R$", min_value=0.0, format="%.2f")
        resps = df_resp['nome'].tolist() if not df_resp.empty else ["Geral"]
        responsavel_sel = st.selectbox("Responsável", resps)
    
    with c2:
        # Lógica simplificada sem a opção Dívida
        if tipo_mov in ["Meta", "Investimento"]:
            opcoes = {}
            if tipo_mov == "Meta": 
                opcoes = {f"{row['icone']} {row['nome']}": row['id'] for _, row in df_metas.iterrows()}
            else: 
                opcoes = {row['nome']: row['id'] for _, row in df_invest_tipos.iterrows()}
            
            if not opcoes:
                st.warning(f"⚠️ Cadastre {tipo_mov} primeiro!")
                return
            sel_nome = st.selectbox(f"Selecione {tipo_mov}", list(opcoes.keys()))
            id_vinc = opcoes[sel_nome]
            descricao = f"{tipo_mov}: {sel_nome}"
            cat_sel = tipo_mov
        else:
            descricao = st.text_input("Descrição")
            cat_sel = st.selectbox("Categoria", categorias)

    metadados = f" | 👤 {responsavel_sel}"
    qtd_parcelas, status, data_referencia = 1, "Paga", data_f

    if tipo_mov == "Despesa":
        st.divider()
        cd1, cd2 = st.columns(2)
        with cd1:
            forma_pagto = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Débito", "Crédito"])
        with cd2:
            if forma_pagto == "Crédito":
                if df_cartoes.empty:
                    st.error("Cadastre um cartão primeiro!")
                    return
                status = "Pendente"
                cartao_sel = st.selectbox("Cartão", df_cartoes['nome'].tolist())
                regra = df_cartoes[df_cartoes['nome'] == cartao_sel].iloc[0]
                
                venc_base = date(data_f.year, data_f.month, int(regra['vencimento']))
                data_referencia = venc_base + relativedelta(months=1) if data_f.day >= int(regra['fechamento']) else venc_base
                metadados += f" | 💳 {cartao_sel}"
                
                if st.checkbox("Parcelado?"):
                    qtd_parcelas = st.number_input("Nº Parcelas", min_value=2, value=2)
            else:
                status = st.selectbox("Status", ["Paga", "Pendente"])
                metadados += f" | 💰 {forma_pagto}"

    if st.button("🚀 Confirmar Lançamento", use_container_width=True):
        if not descricao:
            st.error("Preencha a descrição!")
            return
        
        conn = create_connection()
        tipo_custo = tipo_mov
        if tipo_mov == "Despesa":
            res = conn.execute("SELECT tipo FROM categorias_despesas WHERE nome = ?", (cat_sel,)).fetchone()
            tipo_custo = res[0] if res else "Variável"
        
        valor_parc = valor_f / qtd_parcelas
        for i in range(qtd_parcelas):
            dt_p = data_referencia + relativedelta(months=i)
            suf = f" ({i+1}/{qtd_parcelas})" if qtd_parcelas > 1 else ""
            desc_final = f"{descricao}{suf}{metadados} | {status}"
            
            conn.execute("""
                INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(dt_p), desc_final, cat_sel, valor_parc, "Receita" if tipo_mov == "Receita" else "Despesa", tipo_custo))
        
        if tipo_mov == "Meta": conn.execute("UPDATE metas SET valor_atual = valor_atual + ? WHERE id = ?", (valor_f, id_vinc))
        elif tipo_mov == "Investimento": conn.execute("UPDATE carteira_investimentos SET valor_acumulado = valor_acumulado + ? WHERE tipo_id = ?", (valor_f, id_vinc))
        
        conn.commit()
        conn.close()
        st.toast("✅ Lançamento realizado!")
        st.rerun()

# --- EXIBIÇÃO PRINCIPAL MANTIDA CONFORME SOLICITADO ---
def exibir_lancamentos():
    # ... (Restante do seu código de listagem permanece igual)
    pass