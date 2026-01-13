import streamlit as st
import pandas as pd
from database import create_connection
import plotly.express as px
from datetime import datetime, date

def exibir_dashboard():
    st.markdown("<h2 style='color: white;'>🚀 Cockpit Financeiro</h2>", unsafe_allow_html=True)
    
    # --- BARRA DE FILTRO (MÊS/ANO) ---
    c_f1, c_f2 = st.columns([1, 3])
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    
    mes_sel = c_f1.selectbox("Mês", options=range(1, 13), format_func=lambda x: meses_pt[x], index=datetime.now().month - 1)
    ano_sel = c_f2.number_input("Ano", min_value=2024, max_value=2030, value=datetime.now().year)

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

    # Processamento de Datas e Filtro do Mês Selecionado
    df_lanc['data'] = pd.to_datetime(df_lanc['data'])
    df_mes = df_lanc[(df_lanc['data'].dt.month == mes_sel) & (df_lanc['data'].dt.year == ano_sel)].copy()

    # --- CÁLCULOS 50/30/20 ---
    receita_total = df_mes[df_mes['tipo_mov'] == 'Receita']['valor'].sum()
    essencial = df_mes[(df_mes['tipo_mov'] == 'Despesa') & (df_mes['tipo_custo'].isin(['Fixo', 'Dívida']))]['valor'].sum()
    lazer = df_mes[(df_mes['tipo_mov'] == 'Despesa') & (df_mes['tipo_custo'] == 'Variável')]['valor'].sum()
    investido_mes = df_mes[df_mes['tipo_custo'] == 'Investimento']['valor'].sum()
    
    despesa_total = essencial + lazer + investido_mes
    saldo_livre = receita_total - despesa_total

    # --- INDICADORES DE SAÚDE FINANCEIRA ---
    with st.container(border=True):
        st.markdown(f"### 📊 Saúde Financeira ({meses_pt[mes_sel]}/{ano_sel})")
        if receita_total > 0:
            p_ess, p_laz, p_inv = (essencial / receita_total), (lazer / receita_total), (investido_mes / receita_total)
            k1, k2, k3 = st.columns(3)
            k1.metric("Essencial (Meta 50%)", f"{p_ess*100:.1f}%", delta=f"{50 - p_ess*100:.1f}%", delta_color="normal" if p_ess <= 0.5 else "inverse")
            k2.metric("Lazer (Meta 30%)", f"{p_laz*100:.1f}%", delta=f"{30 - p_laz*100:.1f}%", delta_color="normal" if p_laz <= 0.3 else "inverse")
            k3.metric("Investir (Meta 20%)", f"{p_inv*100:.1f}%", delta=f"{p_inv*100 - 20:.1f}%", delta_color="normal" if p_inv >= 0.2 else "inverse")
            st.progress(min(p_ess + p_laz + p_inv, 1.0), text=f"Saldo Final: R$ {saldo_livre:,.2f}")
        else:
            st.warning("Sem receitas registradas para este período.")

    st.divider()

    # --- NOVOS GRÁFICOS: CARTÕES E CONTAS ---
    st.markdown("#### 💳 Meios de Pagamento e Cartões")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        # Extração do nome do Cartão da descrição: "Crédito (Nome Cartão)"
        df_cartao_chart = df_mes[df_mes['descricao'].str.contains("💳 Crédito", na=False)].copy()
        if not df_cartao_chart.empty:
            df_cartao_chart['Cartao'] = df_cartao_chart['descricao'].str.extract(r'💳 Crédito \((.*?)\)')
            gastos_cartao = df_cartao_chart.groupby('Cartao')['valor'].sum().reset_index()
            fig_cartao = px.bar(gastos_cartao, x='Cartao', y='valor', title="Gastos por Cartão",
                                 text_auto='.2s', color_discrete_sequence=['#f85149'])
            fig_cartao.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_cartao, use_container_width=True)
        else:
            st.info("Sem gastos no crédito este mês.")

    with col_c2:
        # Extração do nome da Conta da descrição: "💰 Tipo (Nome Conta)"
        df_conta_chart = df_mes[df_mes['descricao'].str.contains("💰", na=False)].copy()
        if not df_conta_chart.empty:
            df_conta_chart['Conta'] = df_conta_chart['descricao'].str.extract(r'💰 .*?\((.*?)\)')
            gastos_conta = df_conta_chart.groupby('Conta')['valor'].sum().reset_index()
            fig_conta = px.pie(gastos_conta, values='valor', names='Conta', title="Pagos por Conta",
                               hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_conta.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_conta, use_container_width=True)
        else:
            st.info("Sem pagamentos via conta este mês.")

    st.divider()

    # --- GRÁFICO ANUAL E ALERTAS ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.markdown("#### 📈 Evolução Anual")
        df_anual = df_lanc[df_lanc['data'].dt.year == ano_sel].copy()
        if not df_anual.empty:
            df_anual['Mes'] = df_anual['data'].dt.month # Sort by month number
            df_chart = df_anual.groupby(['Mes', 'tipo_mov'])['valor'].sum().reset_index()
            df_chart['Mes_Nome'] = df_chart['Mes'].apply(lambda x: meses_pt[x])
            fig_evolucao = px.bar(df_chart, x='Mes_Nome', y='valor', color='tipo_mov', barmode='group',
                                  color_discrete_map={'Receita': '#3fb950', 'Despesa': '#f85149'})
            fig_evolucao.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_evolucao, use_container_width=True)

    with col_dir:
        st.markdown("#### 🔔 Alertas")
        dia_hoje = date.today().day
        if not df_cartoes.empty:
            for _, cartao in df_cartoes.iterrows():
                venc = cartao['vencimento']
                if 0 <= (venc - dia_hoje) <= 5:
                    st.warning(f"**{cartao['nome']}**: Vence em {venc - dia_hoje} dias!")
                elif dia_hoje > venc:
                    st.error(f"**{cartao['nome']}**: Venceu dia {venc}")
        if saldo_livre < 0:
            st.error("⚠️ Orçamento Negativo!")

    st.divider()

    # --- INVESTIMENTOS E METAS ---
    c_inv, c_meta = st.columns(2)
    with c_inv:
        st.markdown("#### 🏦 Alocação de Ativos")
        if not df_carteira.empty:
            fig_pie = px.pie(df_carteira, values='valor_acumulado', names='nome', hole=0.5,
                             color_discrete_sequence=df_carteira['cor'].tolist())
            fig_pie.update_layout(height=280, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

    with c_meta:
        st.markdown("#### 🎯 Status das Metas")
        if not df_metas.empty:
            for _, m in df_metas.iterrows():
                perc = min(m['valor_atual'] / m['valor_objetivo'], 1.0) if m['valor_objetivo'] > 0 else 0
                st.write(f"{m['icone']} {m['nome']} ({perc*100:.0f}%)")
                st.progress(perc)