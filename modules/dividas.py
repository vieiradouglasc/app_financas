import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def deletar_divida(id_divida, nome_divida):
    conn = create_connection()
    conn.execute("DELETE FROM dividas WHERE id = ?", (id_divida,))
    busca_desc = f"Dívida: {nome_divida}%"
    conn.execute("DELETE FROM lancamentos WHERE descricao LIKE ? AND descricao LIKE '%Pendente%'", (busca_desc,))
    conn.commit()
    conn.close()
    st.toast(f"Dívida '{nome_divida}' removida!", icon="🗑️")
    st.rerun()

def planejar_pagamentos(id_divida, nome, valor_original, valor_pago, responsavel):
    """Função para gerar lançamentos com atualização instantânea de parcelas"""
    
    valor_atualizado = valor_original - valor_pago
    st.markdown(f"#### 🗓️ Planejar Pagamento: {nome}")
    st.info(f"Saldo Devedor Atual: **R$ {valor_atualizado:,.2f}**")
    
    # --- CONTROLES DINÂMICOS (FORA DO FORM PARA ATUALIZAÇÃO INSTANTÂNEA) ---
    c1, c2 = st.columns(2)
    forma = c1.selectbox("Forma de Pagamento", ["À Vista", "Parcelado"], key=f"f_sel_{id_divida}")
    data_inicio = c2.date_input("Data do 1º Vencimento", date.today(), key=f"d_sel_{id_divida}")
    
    qtd_parc = 1
    if forma == "Parcelado":
        qtd_parc = st.number_input("Quantidade de Parcelas", min_value=2, value=12, step=1, key=f"n_sel_{id_divida}")

    # Cálculo instantâneo
    valor_parcela = valor_atualizado / qtd_parc if qtd_parc > 0 else 0
    
    # Exibição do valor bloqueado
    st.number_input("Valor por Parcela (Calculado)", value=float(valor_parcela), disabled=True, format="%.2f", key=f"v_sel_{id_divida}")

    # Botão de ação
    if st.button("🚀 Confirmar e Gerar Parcelas", use_container_width=True, key=f"btn_sel_{id_divida}"):
        if valor_atualizado <= 0:
            st.error("Dívida já quitada!")
            return

        conn = create_connection()
        for i in range(int(qtd_parc)):
            dt_p = data_inicio + relativedelta(months=i)
            sufixo = f" ({i+1}/{int(qtd_parc)})" if qtd_parc > 1 else ""
            desc_completa = f"Dívida: {nome}{sufixo} | 👤 {responsavel} | Pendente"
            
            conn.execute("""
                INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(dt_p), desc_completa, "Dívidas", valor_parcela, "Despesa", "Dívida"))
        
        conn.execute("""
            UPDATE dividas 
            SET forma_pagto = ?, total_parcelas = ?, vencimento = ? 
            WHERE id = ?
        """, (forma, int(qtd_parc), str(data_inicio), id_divida))
        
        conn.commit()
        conn.close()
        st.toast(f"Plano de {int(qtd_parc)}x gerado com sucesso!", icon="✅")
        st.rerun()

def exibir_dividas():
    st.markdown("<h2 style='color: white;'>📉 Gestão Estratégica de Dívidas</h2>", unsafe_allow_html=True)
    
    # --- CADASTRO ---
    with st.expander("➕ Cadastrar Nova Dívida", expanded=False):
        with st.form("form_cadastro_divida"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Credor / Nome da Dívida")
            valor_total = c2.number_input("Valor Original da Dívida", min_value=0.0)
            
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
                        st.success(f"✅ {row['forma_pagto']} ({row['total_parcelas']}x)")
                    else:
                        st.warning("⚠️ Aguardando Planejamento")
                
                with col2:
                    st.metric("Saldo Devedor Atual", f"R$ {valor_restante:,.2f}")
                    st.progress(perc, text=f"{perc*100:.1f}% pago")
                
                with col3:
                    if st.button("📅 Planejar", key=f"plan_{row['id']}", use_container_width=True):
                        st.session_state[f"show_plan_{row['id']}"] = True
                    
                    if st.button("🗑️ Excluir", key=f"del_{row['id']}", use_container_width=True):
                        deletar_divida(row['id'], row['nome'])

                if st.session_state.get(f"show_plan_{row['id']}", False):
                    st.markdown("---")
                    planejar_pagamentos(row['id'], row['nome'], row['valor_total'], row['valor_pago'], row['responsavel'])
                    if st.button("Fechar Planejador", key=f"close_{row['id']}", use_container_width=True):
                        st.session_state[f"show_plan_{row['id']}"] = False
                        st.rerun()
    else:
        st.info("Nenhuma dívida ativa encontrada.")