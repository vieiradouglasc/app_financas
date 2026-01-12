import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- FUNÇÕES DE AÇÃO ---

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
    """Lógica corrigida: Entrada define o início e oculta campos desnecessários"""
    
    valor_restante_atual = valor_original - valor_pago
    st.markdown(f"#### 🗓️ Planejar Pagamento: {nome}")
    st.info(f"Saldo Devedor Atual: **R$ {valor_restante_atual:,.2f}**")
    
    # --- CONTROLES DINÂMICOS ---
    c1, c2 = st.columns(2)
    forma = c1.selectbox("Forma de Pagamento", ["À Vista", "Parcelado"], key=f"f_sel_{id_divida}")
    
    tem_entrada = False
    valor_entrada = 0.0
    data_entrada = date.today()
    data_primeira_parcela = None

    if forma == "Parcelado":
        st.markdown("---")
        # Checkbox de entrada
        tem_entrada = st.checkbox("Necessário Entrada?", key=f"ent_chk_{id_divida}")
        
        if tem_entrada:
            ce1, ce2 = st.columns(2)
            valor_entrada = ce1.number_input("Valor da Entrada R$", min_value=0.0, max_value=float(valor_restante_atual), value=0.0, format="%.2f", key=f"ent_val_{id_divida}")
            data_entrada = ce2.date_input("Vencimento da Entrada", date.today(), key=f"ent_dt_{id_divida}")
            # A primeira parcela é forçada para o mês seguinte à entrada
            data_primeira_parcela = data_entrada + relativedelta(months=1)
            st.info(f"📅 A 1ª parcela será lançada para: **{data_primeira_parcela.strftime('%d/%m/%Y')}**")
        else:
            # Se não tem entrada, mostra o campo de data do 1º vencimento
            data_primeira_parcela = c2.date_input("Data do 1º Vencimento", date.today(), key=f"d_sel_{id_divida}")
    else:
        # À Vista
        data_primeira_parcela = c2.date_input("Data do Pagamento", date.today(), key=f"d_vista_{id_divida}")

    # Quantidade e Valor das Parcelas
    qtd_parc = 1
    if forma == "Parcelado":
        label_parc = "Qtd. de Parcelas (após entrada)" if tem_entrada else "Quantidade de Parcelas"
        qtd_parc = st.number_input(label_parc, min_value=1, value=12, step=1, key=f"n_sel_{id_divida}")

    # Cálculo e Campo Editável
    saldo_para_parcelar = valor_restante_atual - valor_entrada
    sugestao_parcela = saldo_para_parcelar / qtd_parc if qtd_parc > 0 else 0
    valor_parcela_final = st.number_input("Valor de cada Parcela (Editável)", min_value=0.0, value=float(sugestao_parcela), format="%.2f", key=f"v_edit_{id_divida}")
    
    # Recálculo do Total Final para atualização do banco
    novo_total_db = valor_pago + valor_entrada + (qtd_parc * valor_parcela_final)

    if st.button("🚀 Confirmar e Gerar Lançamentos", use_container_width=True, key=f"btn_sel_{id_divida}"):
        conn = create_connection()
        
        # 1. Lançar Entrada (se existir)
        if tem_entrada and valor_entrada > 0:
            status_ent = "Paga" if data_entrada <= date.today() else "Pendente"
            desc_ent = f"Dívida: {nome} (Entrada) | 👤 {responsavel} | {status_ent}"
            conn.execute("""
                INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(data_entrada), desc_ent, "Dívidas", valor_entrada, "Despesa", "Dívida"))
            
            if status_ent == "Paga":
                conn.execute("UPDATE dividas SET valor_pago = valor_pago + ? WHERE id = ?", (valor_entrada, id_divida))

        # 2. Lançar Parcelas (Mês sequente à entrada ou data manual)
        for i in range(int(qtd_parc)):
            dt_p = data_primeira_parcela + relativedelta(months=i)
            sufixo = f" ({i+1}/{int(qtd_parc)})"
            desc_parc = f"Dívida: {nome}{sufixo} | 👤 {responsavel} | Pendente"
            
            conn.execute("""
                INSERT INTO lancamentos (data, descricao, categoria, valor, tipo_mov, tipo_custo) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(dt_p), desc_parc, "Dívidas", valor_parcela_final, "Despesa", "Dívida"))
        
        # 3. Atualizar o Valor Total da Dívida e o Plano
        total_fatias = qtd_parc + (1 if tem_entrada else 0)
        conn.execute("""
            UPDATE dividas 
            SET valor_total = ?, forma_pagto = ?, total_parcelas = ?, vencimento = ? 
            WHERE id = ?
        """, (novo_total_db, forma, int(total_fatias), str(data_entrada if tem_entrada else data_primeira_parcela), id_divida))
        
        conn.commit()
        conn.close()
        st.toast(f"Plano de {total_fatias}x confirmado!", icon="✅")
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
                        st.success(f"✅ {row['forma_pagto']} ({row['total_parcelas']} fatias)")
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