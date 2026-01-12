import streamlit as st
import pandas as pd
from database import create_connection
import plotly.express as px
from datetime import datetime, date

def exibir_dashboard():
    st.markdown("<h2 style='color: white;'>🚀 Cockpit Financeiro</h2>", unsafe_allow_html=True)
    
    conn = create_connection()
    df_lanc = pd.read_sql_query("SELECT * FROM lancamentos", conn)
    df_metas = pd.read_sql_query("SELECT * FROM metas", conn)
    df_carteira = pd.read_sql_query("""
        SELECT t.nome, c.valor_acumulado, t.cor 
        FROM carteira_investimentos c 
        JOIN tipos_investimentos t ON c.tipo_id = t.id
    """, conn)
    df_cartoes = pd.read_sql_query("SELECT * FROM cartoes_credito", conn)
    conn.close()

    if df_lanc.empty:
        st.info("💡 O cockpit aparecerá assim que você realizar o primeiro lançamento.")
        return

    # Processamento de Datas
    df_lanc['data'] = pd.to_datetime(df_lanc['data'])
    hoje = datetime.now()
    df_mes = df_lanc[(df_lanc['data'].dt.month == hoje.month) & (df_lanc['data'].dt.year == hoje.year)]

    # --- KPIs SUPERIORES ---
    total_receita = df_mes[df_mes['tipo_mov'] == 'Receita']['valor'].sum()
    total_gastos = df_mes[(df_mes['tipo_mov'] == 'Despesa') & (~df_mes['tipo_custo'].isin(['Meta', 'Investimento']))]['valor'].sum()
    total_investido = df_mes[df_mes['tipo_custo'] == 'Investimento']['valor'].sum()
    patrimonio = df_carteira['valor_acumulado'].sum() if not df_carteira.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita (Mês)", f"R$ {total_receita:,.2f}")
    c2.metric("Despesas Reais", f"R$ {total_gastos:,.2f}", delta=f"-{total_gastos/total_receita*100:.1f}%" if total_receita > 0 else None, delta_color="inverse")
    c3.metric("Aportes (Mês)", f"R$ {total_investido:,.2f}")
    c4.metric("Patrimônio Total", f"R$ {patrimonio:,.2f}")

    st.divider()

    # --- COLUNA DUPLA: GRÁFICO ANUAL E ALERTAS ---
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.markdown("#### 📈 Evolução Mensal")
        df_anual = df_lanc[df_lanc['data'].dt.year == hoje.year].copy()
        df_anual['Mes'] = df_anual['data'].dt.strftime('%b')
        df_chart = df_anual.groupby(['Mes', 'tipo_mov'])['valor'].sum().reset_index()
        
        fig_evolucao = px.bar(df_chart, x='Mes', y='valor', color='tipo_mov', barmode='group',
                              color_discrete_map={'Receita': '#3fb950', 'Despesa': '#f85149'},
                              category_orders={"Mes": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]})
        fig_evolucao.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_evolucao, use_container_width=True)

    with col_dir:
        st.markdown("#### 🔔 Alertas de Cartão")
        dia_hoje = date.today().day
        if not df_cartoes.empty:
            for _, cartao in df_cartoes.iterrows():
                venc = cartao['vencimento']
                if 0 <= (venc - dia_hoje) <= 5:
                    st.warning(f"**{cartao['nome']}**: Vence em {venc - dia_hoje} dias!")
                elif dia_hoje > venc:
                    st.error(f"**{cartao['nome']}**: Vencido dia {venc}")
        else:
            st.caption("Nenhum cartão cadastrado.")

    st.divider()

    # --- TERCEIRA LINHA: INVESTIMENTOS E METAS ---
    c_inv, c_meta = st.columns(2)

    with c_inv:
        st.markdown("#### 🏦 Alocação de Ativos")
        if not df_carteira.empty:
            fig_pie = px.pie(df_carteira, values='valor_acumulado', names='nome', hole=0.5,
                             color_discrete_sequence=df_carteira['cor'].tolist())
            fig_pie.update_layout(height=280, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Cadastre investimentos para ver o gráfico.")

    with c_meta:
        st.markdown("#### 🎯 Status das Metas")
        if not df_metas.empty:
            for _, m in df_metas.iterrows():
                perc = min(m['valor_atual'] / m['valor_objetivo'], 1.0)
                st.write(f"{m['icone']} {m['nome']} ({perc*100:.0f}%)")
                st.progress(perc)
        else:
            st.info("Nenhuma meta ativa.")