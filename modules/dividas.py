import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def deletar_divida(id_divida, nome_divida):
    conn = create_connection()
    conn.execute("DELETE FROM dividas WHERE id = ?", (id_divida,))
    # Deleta lançamentos que ainda estão pendentes vinculados a essa dívida
    busca_desc = f"Dívida: {nome_divida}%"
    conn.execute("DELETE FROM lancamentos WHERE descricao LIKE ? AND descricao LIKE '%Pendente%'", (busca_desc,))
    conn.commit()
    conn.close()
    st.toast(f"Dívida '{nome_divida}' removida!", icon="🗑️")
    st.rerun()

def planejar_pagamentos(id_divida, nome, valor_total, responsavel):
    """Função para gerar os lançamentos no fluxo de caixa baseado no plano"""
    st.markdown(f"### 🗓️ Planejar Pagamento: {nome}")
    
    with st.form(f"form_plan_{id_divida}"):
        c1, c2, c3 = st.columns(3)
        forma = c1.selectbox("Forma de Pagamento", ["À Vista", "Parcelado", "Cartão de Crédito"])
        data_inicio = c2.date_input("Data de Início/Vencimento", date.today())
        
        if forma == "À Vista":
            qtd_parc = 1
        else:
            qtd_parc = c3.number_input("Quantidade de Parcelas", min_value=2, value=12)

        valor_parc_sugerido = valor_total / qtd_parc
        st.info(f"Valor sugerido por parcela: **R$ {valor_parc_sugerido:,.2f}**")
        
        # Campo para ajuste manual se necessário
        valor_ajustado = st.number_input("Ajustar valor da parcela (opcional)", min_value=0.0, value=float(valor_parc_sugerido))

        if st.form_submit_button("Confirmar e Gerar Parcelas"):
            conn = create_connection()
            for i in range(qtd_parc):
                dt_p = data_inicio + relativedelta(months=i)
                sufixo = f" ({i+1}/{qtd_parc})" if qtd_parc > 1 else ""
                desc_completa = f"Dívida: {nome}{sufixo} | 👤 {responsavel} | Pendente"
                
                conn.execute("""
                    INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(dt_p), desc_completa, "Dívidas", valor_ajustado, "Despesa", "Dívida"))
            
            # Atualiza a dívida com a forma de pagto escolhida
            conn.execute("UPDATE dividas SET forma_pagto = ?, total_parcelas = ? WHERE id = ?", (forma, qtd_parc, id_divida))
            conn.commit()
            conn.close()
            st.success("Plano de pagamento gerado no Fluxo de Caixa!")
            st.rerun()

def exibir_dividas():
    st.markdown("<h2 style='color: white;'>📉 Gestão Estratégica de Dívidas</h2>", unsafe_allow_html=True)
    
    # --- NOVO CADASTRO DE DÍVIDA (APENAS REGISTRO) ---
    with st.expander("➕ Cadastrar Nova Dívida", expanded=False):
        with st.form("form_cadastro_divida"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Credor / Nome da Dívida")
            valor_total = c2.number_input("Valor Total da Dívida", min_value=0.0)
            
            conn = create_connection()
            df_resp = pd.read_sql_query("SELECT nome FROM responsaveis ORDER BY nome ASC", conn)
            conn.close()
            
            resps = df_resp['nome'].tolist() if not df_resp.empty else ["Geral"]
            responsavel = st.selectbox("Responsável pela Dívida", resps)
            
            if st.form_submit_button("Registrar Dívida"):
                if nome and valor_total > 0:
                    conn = create_connection()
                    conn.execute("""
                        INSERT INTO dividas (nome, valor_total, valor_pago, responsavel, status) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (nome, valor_total, 0, responsavel, 'Ativa'))
                    conn.commit()
                    conn.close()
                    st.rerun()

    st.divider()

    # --- LISTAGEM ---
    conn = create_connection()
    df_div = pd.read_sql_query("SELECT * FROM dividas WHERE status = 'Ativa'", conn)
    conn.close()

    if not df_div.empty:
        for _, row in df_div.iterrows():
            valor_restante = row['valor_total'] - row['valor_pago']
            perc = min(row['valor_pago'] / row['valor_total'], 1.0) if row['valor_total'] > 0 else 0
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([2.5, 2, 1.5])
                
                with col1:
                    st.markdown(f"### {row['nome']}")
                    st.markdown(f"👤 **Responsável:** {row['responsavel']}")
                    if row['forma_pagto']:
                        st.caption(f"Plano: {row['forma_pagto']} ({row['total_parcelas']}x)")
                    else:
                        st.warning("⚠️ Aguardando Planejamento")
                
                with col2:
                    st.metric("Saldo Devedor", f"R$ {valor_restante:,.2f}")
                    st.progress(perc, text=f"{perc*100:.1f}% amortizado")
                
                with col3:
                    # Botão para Planejar (Só aparece se ainda não foi planejado ou para reajustar)
                    if st.button("📅 Planejar", key=f"plan_{row['id']}", use_container_width=True):
                        st.session_state[f"show_plan_{row['id']}"] = True
                    
                    if st.button("🗑️ Excluir", key=f"del_{row['id']}", use_container_width=True):
                        deletar_divida(row['id'], row['nome'])

                # Se clicou em planejar, abre o formulário de planejamento abaixo do card
                if st.session_state.get(f"show_plan_{row['id']}", False):
                    st.divider()
                    planejar_pagamentos(row['id'], row['nome'], row['valor_total'], row['responsavel'])
                    if st.button("Cancelar Planejamento", key=f"cancel_{row['id']}"):
                        st.session_state[f"show_plan_{row['id']}"] = False
                        st.rerun()
    else:
        st.info("Nenhuma dívida cadastrada.")