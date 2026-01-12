import streamlit as st
import pandas as pd
from database import create_connection

def deletar_cadastro(tabela, id_item):
    """Função genérica para deletar itens das tabelas de configuração"""
    conn = create_connection()
    try:
        conn.execute(f"DELETE FROM {tabela} WHERE id = ?", (id_item,))
        conn.commit()
        st.toast(f"Item removido com sucesso!", icon="🗑️")
    except Exception as e:
        st.error(f"Erro ao deletar: {e}")
    finally:
        conn.close()
    st.rerun()

def exibir_cadastros():
    st.markdown("<h2 style='color: white;'>Configurações e Cadastros</h2>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏷️ Categorias", 
        "💳 Cartões", 
        "🏦 Contas", 
        "👥 Responsáveis",
        "📈 Investimentos"
    ])
    
    conn = create_connection()

    # --- ABA 1: CATEGORIAS ---
    with tab1:
        st.subheader("Gerenciar Categorias")
        exp_rec = st.expander("➕ Adicionar Nova Categoria")
        with exp_rec:
            tipo_cat = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
            nome_cat = st.text_input("Nome da Categoria", key="input_nome_cat")
            tipo_custo = st.selectbox("Se Despesa, qual o custo?", ["Fixo", "Variável"]) if tipo_cat == "Despesa" else "Receita"
            
            if st.button("Salvar Categoria"):
                if nome_cat:
                    if tipo_cat == "Receita":
                        conn.execute("INSERT INTO categorias_receitas (nome) VALUES (?)", (nome_cat,))
                    else:
                        conn.execute("INSERT INTO categorias_despesas (nome, tipo) VALUES (?,?)", (nome_cat, tipo_custo))
                    conn.commit()
                    st.toast("Categoria salva!", icon="✅")
                    st.rerun()

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Categorias de Receitas**")
            df_rec = pd.read_sql_query("SELECT * FROM categorias_receitas ORDER BY nome", conn)
            for _, row in df_rec.iterrows():
                c_v1, c_v2 = st.columns([0.8, 0.2])
                c_v1.text(f"● {row['nome']}")
                if c_v2.button("🗑️", key=f"del_catrec_{row['id']}"):
                    deletar_cadastro("categorias_receitas", row['id'])
        with col2:
            st.markdown("**Categorias de Despesas**")
            df_desp = pd.read_sql_query("SELECT * FROM categorias_despesas ORDER BY nome", conn)
            for _, row in df_desp.iterrows():
                c_v1, c_v2 = st.columns([0.8, 0.2])
                c_v1.text(f"● {row['nome']} ({row['tipo']})")
                if c_v2.button("🗑️", key=f"del_catdesp_{row['id']}"):
                    deletar_cadastro("categorias_despesas", row['id'])

    # --- ABA 2: CARTÕES (Crédito e Benefícios) ---
    with tab2:
        # Seção de Cartões de Crédito
        st.subheader("💳 Cartões de Crédito")
        with st.form("form_cartao", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nome = c1.text_input("Nome do Cartão")
            limite = c2.number_input("Limite Total", min_value=0.0)
            f1, f2 = st.columns(2)
            fechamento = f1.number_input("Dia de Fechamento", 1, 31, 1)
            vencimento = f2.number_input("Dia de Vencimento", 1, 31, 10)
            
            if st.form_submit_button("Salvar Cartão"):
                if nome:
                    conn.execute("INSERT INTO cartoes_credito (nome, limite, fechamento, vencimento) VALUES (?,?,?,?)", (nome, limite, fechamento, vencimento))
                    conn.commit()
                    st.toast("Cartão cadastrado!", icon="💳")
                    st.rerun()

        df_c = pd.read_sql_query("SELECT * FROM cartoes_credito", conn)
        for _, row in df_c.iterrows():
            col_b1, col_b2 = st.columns([0.9, 0.1])
            col_b1.write(f"💳 **{row['nome']}** - Limite: R$ {row['limite']:.2f} (Venc: {row['vencimento']})")
            if col_b2.button("🗑️", key=f"del_card_{row['id']}"):
                deletar_cadastro("cartoes_credito", row['id'])

        st.markdown("---")
        
        # Nova Seção: Vale Alimentação / Presente
        st.subheader("🍏 Vale Alimentação / Presente")
        with st.form("form_vale", clear_on_submit=True):
            cv1, cv2 = st.columns([2, 1])
            nome_vale = cv1.text_input("Nome do Benefício (ex: VR, Ticket, Gift Card)")
            saldo_vale = cv2.number_input("Saldo Inicial", min_value=0.0)
            
            if st.form_submit_button("Salvar Benefício"):
                if nome_vale:
                    # Assumindo que você tenha ou criará a tabela cartoes_beneficios
                    conn.execute("INSERT INTO cartoes_beneficios (nome, saldo) VALUES (?,?)", (nome_vale, saldo_vale))
                    conn.commit()
                    st.toast("Benefício cadastrado!", icon="🍏")
                    st.rerun()

        # Listagem de Benefícios (Tente ler da tabela, se não existir, ignore para não quebrar)
        try:
            df_v = pd.read_sql_query("SELECT * FROM cartoes_beneficios", conn)
            for _, row in df_v.iterrows():
                col_v1, col_v2 = st.columns([0.9, 0.1])
                col_v1.write(f"🍏 **{row['nome']}** - Saldo: R$ {row['saldo']:.2f}")
                if col_v2.button("🗑️", key=f"del_vale_{row['id']}"):
                    deletar_cadastro("cartoes_beneficios", row['id'])
        except:
            st.info("Cadastre seu primeiro vale alimentação acima.")

    # --- ABA 3: CONTAS ---
    with tab3:
        with st.form("form_conta", clear_on_submit=True):
            n = st.text_input("Novo Banco/Conta")
            if st.form_submit_button("Cadastrar"):
                if n:
                    conn.execute("INSERT INTO contas_bancarias (nome) VALUES (?)", (n,))
                    conn.commit()
                    st.toast("Conta salva!", icon="🏦")
                    st.rerun()
        df_contas = pd.read_sql_query("SELECT * FROM contas_bancarias", conn)
        for _, row in df_contas.iterrows():
            col_b1, col_b2 = st.columns([0.9, 0.1])
            col_b1.write(f"🏦 {row['nome']}")
            if col_b2.button("🗑️", key=f"del_conta_{row['id']}"):
                deletar_cadastro("contas_bancarias", row['id'])

    # --- ABA 4: RESPONSÁVEIS ---
    with tab4:
        with st.form("form_resp", clear_on_submit=True):
            n = st.text_input("Nome")
            if st.form_submit_button("Cadastrar"):
                if n:
                    conn.execute("INSERT INTO responsaveis (nome) VALUES (?)", (n,))
                    conn.commit()
                    st.toast("Responsável salva!", icon="👤")
                    st.rerun()
        df_resp = pd.read_sql_query("SELECT * FROM responsaveis", conn)
        for _, row in df_resp.iterrows():
            col_b1, col_b2 = st.columns([0.9, 0.1])
            col_b1.write(f"👤 {row['nome']}")
            if col_b2.button("🗑️", key=f"del_resp_{row['id']}"):
                deletar_cadastro("responsaveis", row['id'])

    # --- ABA 5: INVESTIMENTOS ---
    with tab5:
        st.subheader("🏦 Tipos de Investimento")
        with st.form("form_invest", clear_on_submit=True):
            nome_inv = st.text_input("Nome do Investimento (ex: CDB Itaú, PETR4)")
            cor_inv = st.color_picker("Escolha uma cor para os gráficos", "#58a6ff")
            if st.form_submit_button("Salvar Ativo"):
                if nome_inv:
                    conn.execute("INSERT INTO tipos_investimentos (nome, cor) VALUES (?,?)", (nome_inv, cor_inv))
                    conn.commit()
                    st.toast("Ativo cadastrado!", icon="📈")
                    st.rerun()
        
        df_inv = pd.read_sql_query("SELECT * FROM tipos_investimentos ORDER BY nome", conn)
        for _, row in df_inv.iterrows():
            col_b1, col_b2 = st.columns([0.9, 0.1])
            col_b1.markdown(f"<span style='color:{row['cor']}'>●</span> {row['nome']}", unsafe_allow_html=True)
            if col_b2.button("🗑️", key=f"del_tipo_inv_{row['id']}"):
                deletar_cadastro("tipos_investimentos", row['id'])

    conn.close()