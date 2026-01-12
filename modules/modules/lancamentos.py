import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def deletar_item(id_item):
    conn = create_connection()
    conn.execute("DELETE FROM lancamentos WHERE id = ?", (id_item,))
    conn.commit()
    conn.close()
    st.rerun()

@st.dialog("Editar Lançamento")
def popup_editar_item(row):
    st.markdown(f"### ✏️ Editar Registro")
    
    data_atual = pd.to_datetime(row['data'])
    desc_atual = str(row['descricao'])
    valor_atual = float(row['valor'])
    
    nova_data = st.date_input("Data", data_atual)
    nova_desc = st.text_input("Descrição", desc_atual)
    novo_valor = st.number_input("Valor R$", min_value=0.0, value=valor_atual, format="%.2f")
    
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
    data_pagto = st.date_input("Data do Pagamento", datetime.now())
    
    if st.button("Confirmar e Atualizar", use_container_width=True):
        conn = create_connection()
        nova_desc = descricao.replace("Pendente", "Paga")
        conn.execute("UPDATE lancamentos SET descricao = ?, data = ? WHERE id = ?", (nova_desc, str(data_pagto), id_item))
        
        if "Dívida:" in descricao:
            nome_divida = descricao.split("|")[0].replace("Dívida:", "").split("(")[0].strip()
            conn.execute("UPDATE dividas SET valor_pago = valor_pago + ? WHERE nome = ?", (valor, nome_divida))
        
        conn.commit()
        conn.close()
        st.toast("Pagamento registrado!", icon="✅")
        st.rerun()

@st.dialog("Novo Lançamento", width="large")
def popup_novo_lancamento():
    st.markdown("### 📝 Registrar Movimentação")
    tipo_mov = st.radio("", ["Despesa", "Receita", "Meta", "Investimento", "Dívida"], horizontal=True)
    
    conn = create_connection()
    df_metas = pd.read_sql_query("SELECT id, nome, icone FROM metas", conn)
    df_invest_tipos = pd.read_sql_query("SELECT id, nome FROM tipos_investimentos", conn)
    df_dividas = pd.read_sql_query("SELECT id, nome FROM dividas WHERE status = 'Ativa'", conn)
    df_cartoes = pd.read_sql_query("SELECT nome, fechamento, vencimento FROM cartoes_credito", conn)
    df_resp = pd.read_sql_query("SELECT nome FROM responsaveis ORDER BY nome ASC", conn)
    
    categorias = []
    try:
        query_cat = "SELECT nome FROM categorias_receitas ORDER BY nome ASC" if tipo_mov == "Receita" else "SELECT nome FROM categorias_despesas ORDER BY nome ASC"
        categorias = pd.read_sql_query(query_cat, conn)['nome'].tolist()
    except: pass
    conn.close()

    c1, c2 = st.columns(2)
    with c1:
        data_f = st.date_input("Data da Compra", datetime.now())
        valor_f = st.number_input("Valor Total R$", min_value=0.0, format="%.2f")
        # Campo de Responsável adicionado para todos os tipos, essencial para Dívida
        lista_resp = df_resp['nome'].tolist() if not df_resp.empty else ["Geral"]
        responsavel_sel = st.selectbox("Responsável", lista_resp)
    
    with c2:
        if tipo_mov in ["Dívida", "Meta", "Investimento"]:
            opcoes = {}
            if tipo_mov == "Dívida": opcoes = {row['nome']: row['id'] for _, row in df_dividas.iterrows()}
            elif tipo_mov == "Meta": opcoes = {f"{row['icone']} {row['nome']}": row['id'] for _, row in df_metas.iterrows()}
            else: opcoes = {row['nome']: row['id'] for _, row in df_invest_tipos.iterrows()}
            
            if not opcoes:
                st.warning(f"⚠️ Cadastre {tipo_mov} primeiro!")
                return
            sel_nome = st.selectbox(f"Selecione {tipo_mov}", list(opcoes.keys()))
            id_vinc = opcoes[sel_nome]
            descricao = f"{tipo_mov}: {sel_nome}"
            cat_sel = tipo_mov
        else:
            descricao = st.text_input("Descrição")
            cat_sel = st.selectbox("Categoria", categorias if categorias else ["Geral"])

    # Lógica de Pagamento
    metadados_fixos, qtd_parcelas, status, data_referencia = f" | 👤 {responsavel_sel}", 1, "Paga", data_f

    if tipo_mov == "Despesa":
        st.divider()
        cd1, cd2 = st.columns(2)
        with cd1:
            forma_pagto = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Débito", "Crédito"])
        with cd2:
            if forma_pagto == "Crédito":
                if df_cartoes.empty:
                    st.error("Nenhum cartão cadastrado!")
                    return
                status = "Pendente"
                cartao_sel = st.selectbox("Cartão", df_cartoes['nome'].tolist())
                regra = df_cartoes[df_cartoes['nome'] == cartao_sel].iloc[0]
                
                venc_base = date(data_f.year, data_f.month, int(regra['vencimento']))
                data_referencia = venc_base + relativedelta(months=1) if data_f.day >= int(regra['fechamento']) else venc_base
                metadados_fixos += f" | 💳 {cartao_sel}"
                
                if st.checkbox("Pagamento Parcelado?"):
                    qtd_parcelas = st.number_input("Parcelas", min_value=2, value=2, step=1)
                    valor_cada = valor_f / qtd_parcelas
                    st.info(f"**Resumo:** {qtd_parcelas}x de R$ {valor_cada:,.2f}")
            else:
                status = st.selectbox("Status", ["Paga", "Pendente"])
                metadados_fixos += f" | 💰 {forma_pagto}"

    if st.button("🚀 Confirmar Lançamento", use_container_width=True):
        if not descricao:
            st.error("Preencha a descrição!")
            return
        conn = create_connection()
        res = conn.execute("SELECT tipo FROM categorias_despesas WHERE nome = ?", (cat_sel,)).fetchone()
        tipo_custo = tipo_mov if tipo_mov in ["Receita", "Meta", "Investimento", "Dívida"] else (res[0] if res else "Variável")
        
        valor_parc = valor_f / int(qtd_parcelas)
        for i in range(int(qtd_parcelas)):
            dt_p = data_referencia + relativedelta(months=i)
            suf = f" ({i+1}/{qtd_parcelas})" if qtd_parcelas > 1 else ""
            desc_f = f"{descricao}{suf}{metadados_fixos} | {status}"
            conn.execute("INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) VALUES (?, ?, ?, ?, ?, ?)",
                         (dt_p.strftime('%Y-%m-%d'), desc_f, cat_sel, valor_parc, "Despesa" if tipo_mov != "Receita" else "Receita", tipo_custo))
        
        if tipo_mov == "Meta": conn.execute("UPDATE metas SET valor_atual = valor_atual + ? WHERE id = ?", (valor_f, id_vinc))
        elif tipo_mov == "Investimento": conn.execute("UPDATE carteira_investimentos SET valor_acumulado = valor_acumulado + ? WHERE tipo_id = ?", (valor_f, id_vinc))
        elif tipo_mov == "Dívida": conn.execute("UPDATE dividas SET valor_pago = valor_pago + ? WHERE id = ?", (valor_f, id_vinc))
        
        conn.commit()
        conn.close()
        st.toast(f"✅ Lançamento realizado!")
        st.rerun()

def exibir_lancamentos():
    st.markdown("<h2 style='color: white;'>Fluxo de Caixa</h2>", unsafe_allow_html=True)
    with st.container():
        f1, f2, f3, f4 = st.columns([1, 1, 1.5, 1.2])
        mes_sel = f1.selectbox("Mês", [f"{i:02d}" for i in range(1, 13)], index=datetime.now().month-1)
        ano_sel = f2.selectbox("Ano", [2025, 2026], index=1)
        visualizacao = f3.selectbox("Ver", ["Todos", "Receitas", "Despesas", "Metas", "Investimentos", "Dívidas"])
        if f4.button("➕ NOVO ITEM", use_container_width=True): popup_novo_lancamento()

    conn = create_connection()
    df = pd.read_sql_query("SELECT * FROM lancamentos", conn)
    conn.close()

    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df_f = df[(df['data'].dt.month == int(mes_sel)) & (df['data'].dt.year == int(ano_sel))].copy()
        
        # KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Receitas", f"R$ {df_f[df_f['tipo_mov'] == 'Receita']['valor'].sum():,.2f}")
        c2.metric("Despesas", f"R$ {df_f[(df_f['tipo_mov'] == 'Despesa') & (~df_f['tipo_custo'].isin(['Meta', 'Investimento', 'Dívida']))]['valor'].sum():,.2f}")
        c3.metric("Metas", f"R$ {df_f[df_f['tipo_custo'] == 'Meta']['valor'].sum():,.2f}")
        c4.metric("Investido", f"R$ {df_f[df_f['tipo_custo'] == 'Investimento']['valor'].sum():,.2f}")
        c5.metric("Dívidas", f"R$ {df_f[df_f['tipo_custo'] == 'Dívida']['valor'].sum():,.2f}")

        st.divider()

        def render_secao(dados, titulo, cor_borda):
            if not dados.empty:
                st.markdown(f"#### {titulo}")
                for _, row in dados.iterrows():
                    is_pendente = "Pendente" in str(row['descricao'])
                    bg = "#161b22"
                    
                    with st.container():
                        st.markdown(f'''<div style="border-left: 4px solid {cor_borda}; background: {bg}; padding: 12px; border-radius: 6px; margin-bottom: 8px;">''', unsafe_allow_html=True)
                        cols = st.columns([1, 3, 1.8, 1.8, 1.6]) 
                        cols[0].write(row['data'].strftime('%d/%m'))
                        cols[1].write(row['descricao'])
                        cols[2].write(f"`{row['categoria']}`")
                        cols[3].write(f"**R$ {row['valor']:,.2f}**")
                        
                        b_p, b_e, b_d = cols[4].columns(3)
                        if is_pendente and b_p.button("✅", key=f"p_{row['id']}"): popup_pagar_item(row['id'], row['descricao'], row['valor'])
                        if b_e.button("📝", key=f"e_{row['id']}"): popup_editar_item(row)
                        if b_d.button("🗑️", key=f"d_{row['id']}"): deletar_item(row['id'])
                        st.markdown('</div>', unsafe_allow_html=True)

        filtro_map = {
            "Receitas": (df_f[df_f['tipo_mov'] == 'Receita'], "💰 Receitas", "#3fb950"),
            "Investimentos": (df_f[df_f['tipo_custo'] == 'Investimento'], "📈 Investimentos", "#58a6ff"),
            "Metas": (df_f[df_f['tipo_custo'] == 'Meta'], "🎯 Metas", "#bc8cff"),
            "Dívidas": (df_f[df_f['tipo_custo'] == 'Dívida'], "📉 Dívidas", "#f85149"),
            "Despesas": (df_f[(df_f['tipo_mov'] == 'Despesa') & (~df_f['tipo_custo'].isin(['Meta', 'Investimento', 'Dívida']))], "🛒 Despesas Gerais", "#db6d28")
        }

        if visualizacao == "Todos":
            for k in filtro_map: render_secao(*filtro_map[k])
        else:
            render_secao(*filtro_map[visualizacao])