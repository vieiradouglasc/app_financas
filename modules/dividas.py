import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime
from dateutil.relativedelta import relativedelta

def deletar_divida(id_divida, nome_divida):
    conn = create_connection()
    # 1. Deleta o registro da dívida
    conn.execute("DELETE FROM dividas WHERE id = ?", (id_divida,))
    
    # 2. Deleta os lançamentos automáticos vinculados a esta dívida no fluxo de caixa
    busca_desc = f"Dívida: {nome_divida}%"
    conn.execute("DELETE FROM lancamentos WHERE descricao LIKE ?", (busca_desc,))
    
    conn.commit()
    conn.close()
    st.toast(f"Dívida '{nome_divida}' e seus lançamentos removidos!", icon="🗑️")
    st.rerun()

def salvar_divida_completa(nome, valor_total, forma, parcelas, data_venc, status_avista):
    conn = create_connection()
    
    # 1. Salva o cabeçalho da dívida
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dividas (nome, valor_total, valor_pago, vencimento, forma_pagto, total_parcelas, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nome, valor_total, 0, str(data_venc), forma, parcelas, 'Ativa'))
    
    # 2. Gera os Lançamentos automáticos no Fluxo de Caixa
    valor_parcela = valor_total / parcelas
    for i in range(parcelas):
        data_parc = data_venc + relativedelta(months=i)
        status_lanc = "Paga" if (forma == "À Vista" and status_avista == "Pago") else "Pendente"
        sufixo = f" ({i+1}/{parcelas})" if parcelas > 1 else ""
        
        desc_completa = f"Dívida: {nome}{sufixo} | {forma} | {status_lanc}"
        
        conn.execute("""
            INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(data_parc), desc_completa, "Dívidas", valor_parcela, "Despesa", "Dívida"))
        
        # Se já foi pago à vista, atualizamos o valor_pago na tabela dividas
        if forma == "À Vista" and status_avista == "Pago":
            conn.execute("UPDATE dividas SET valor_pago = valor_total WHERE nome = ? AND vencimento = ?", (nome, str(data_venc)))

    conn.commit()
    conn.close()
    st.toast("Dívida e lançamentos registrados!", icon="✅")
    st.rerun()

def exibir_dividas():
    st.markdown("<h2 style='color: white;'>📉 Gestão Estratégica de Dívidas</h2>", unsafe_allow_html=True)
    
    # --- FORMULÁRIO DE CADASTRO EXPANDIDO ---
    with st.expander("➕ Registrar Nova Dívida Estruturada", expanded=False):
        with st.form("form_divida_nova", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Credor/Descrição (ex: Empréstimo Banco)")
            valor_total = c2.number_input("Valor Total", min_value=0.0, step=100.0)
            
            f1, f2, f3 = st.columns(3)
            forma = f1.selectbox("Forma de Pagamento", ["À Vista", "Parcelado"])
            
            if forma == "À Vista":
                status_avista = f2.selectbox("Status Atual", ["Pendente", "Pago"])
                data_venc = f3.date_input("Vencimento")
                parcelas = 1
            else:
                parcelas = f2.number_input("Nº de Parcelas", min_value=2, value=12)
                data_venc = f3.date_input("Vencimento da 1ª")
                status_avista = "Pendente"
                st.info(f"💡 Isso gerará {parcelas} lançamentos de R$ {valor_total/parcelas:,.2f} mensais.")

            if st.form_submit_button("Salvar e Gerar Lançamentos", use_container_width=True):
                if nome and valor_total > 0:
                    salvar_divida_completa(nome, valor_total, forma, parcelas, data_venc, status_avista)

    st.divider()

    # --- LISTAGEM E CONTROLE ---
    conn = create_connection()
    df_div = pd.read_sql_query("SELECT * FROM dividas WHERE status = 'Ativa'", conn)
    conn.close()

    if not df_div.empty:
        for _, row in df_div.iterrows():
            valor_restante = row['valor_total'] - row['valor_pago']
            perc = min(row['valor_pago'] / row['valor_total'], 1.0)
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"### {row['nome']}")
                    st.caption(f"Tipo: {row['forma_pagto']} | {row['total_parcelas']}x")
                    st.write(f"📅 Vencimento Ref: {row['vencimento']}")
                
                with col2:
                    st.metric("Saldo Devedor", f"R$ {valor_restante:,.2f}")
                    st.progress(perc, text=f"{perc*100:.1f}% amortizado")
                
                with col3:
                    # Botão de exclusão para cada dívida
                    if st.button("🗑️ Excluir", key=f"del_{row['id']}", use_container_width=True):
                        deletar_divida(row['id'], row['nome'])
                    
                    if valor_restante > 0:
                        st.write("---")
                        st.caption("Controle os pagamentos em 'Lançamentos'")
                    else:
                        st.success("Quitada! 🎉")
    else:
        st.info("Nenhuma dívida ativa no momento.")