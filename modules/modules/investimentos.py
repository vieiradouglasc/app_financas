import streamlit as st
import pandas as pd
from database import create_connection
from datetime import datetime

def deletar_investimento(id_item):
    """Remove o lançamento e ajusta o saldo na carteira"""
    conn = create_connection()
    # Busca o valor e o tipo antes de deletar para estornar da carteira
    res = conn.execute("SELECT valor, descricao FROM lancamentos WHERE id = ?", (id_item,)).fetchone()
    if res:
        valor, desc = res
        # Tenta extrair o nome do ativo da descrição "Aporte Invest: Nome"
        # Fazemos um split para pegar o nome entre o prefixo e o primeiro pipe
        try:
            nome_ativo = desc.split("Aporte Invest: ")[1].split(" |")[0]
            
            # Deleta o lançamento
            conn.execute("DELETE FROM lancamentos WHERE id = ?", (id_item,))
            
            # Estorna o valor da carteira
            conn.execute("""
                UPDATE carteira_investimentos 
                SET valor_acumulado = valor_acumulado - ? 
                WHERE tipo_id = (SELECT id FROM tipos_investimentos WHERE nome = ?)
            """, (valor, nome_ativo))
        except:
            conn.execute("DELETE FROM lancamentos WHERE id = ?", (id_item,))
        
    conn.commit()
    conn.close()
    st.rerun()

def exibir_investimentos():
    st.markdown("<h2 style='color: white;'>Meus Investimentos</h2>", unsafe_allow_html=True)

    # --- BARRA DE FILTROS ---
    with st.container():
        f1, f2, f3 = st.columns([1, 1, 2.7])
        mes_sel = f1.selectbox("Mês", ["01","02","03","04","05","06","07","08","09","10","11","12"], index=datetime.now().month-1, key="mes_inv")
        ano_sel = f2.selectbox("Ano", [2025, 2026], index=1, key="ano_inv")

    conn = create_connection()
    # Busca apenas lançamentos do tipo Investimento
    df = pd.read_sql_query("SELECT * FROM lancamentos WHERE tipo_custo = 'Investimento'", conn)
    
    # Busca saldo consolidado da carteira
    res_carteira = pd.read_sql_query("SELECT SUM(valor_acumulado) as total FROM carteira_investimentos", conn)
    total_patrimonio = res_carteira['total'].iloc[0] if res_carteira['total'].iloc[0] is not None else 0.0
    conn.close()

    # Padronização e Filtro
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
        df_f = df[(df['data'].dt.month == int(mes_sel)) & (df['data'].dt.year == int(ano_sel))].copy()
        aporte_mes = df_f['valor'].sum()
    else:
        df_f = pd.DataFrame()
        aporte_mes = 0.0

    # --- CARDS DE RESUMO ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True):
            st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Patrimônio Acumulado</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:#58a6ff; margin:0;'>R$ {total_patrimonio:,.2f}</h3>", unsafe_allow_html=True)
    
    with c2:
        with st.container(border=True):
            st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Aportes no Mês</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:#3fb950; margin:0;'>R$ {aporte_mes:,.2f}</h3>", unsafe_allow_html=True)
    
    with c3:
        with st.container(border=True):
            perc_crescimento = (aporte_mes / total_patrimonio * 100) if total_patrimonio > 0 else 0
            st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Representatividade</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:#bc8cff; margin:0;'>{perc_crescimento:.1f}%</h3>", unsafe_allow_html=True)

    st.divider()

    # --- LISTAGEM ESTILO LANÇAMENTOS ---
    if not df_f.empty:
        st.markdown(f"#### 📈 Histórico de Aportes - {mes_sel}/{ano_sel}")
        for _, row in df_f.iterrows():
            with st.container():
                st.markdown(f'<div style="border-left: 4px solid #58a6ff; background: #161b22; padding: 12px; border-radius: 6px; margin-bottom: 8px;">', unsafe_allow_html=True)
                r1, r2, r3, r4, r5 = st.columns([1, 3, 2, 2, 0.5])
                
                r1.write(row['data'].strftime('%d/%m'))
                r2.write(row['descricao'])
                r3.write(f"`{row['categoria']}`")
                r4.write(f"**R$ {row['valor']:,.2f}**")
                
                if r5.button("🗑️", key=f"del_inv_{row['id']}"):
                    deletar_investimento(row['id'])
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(f"Nenhum aporte registrado para {mes_sel}/{ano_sel}.")