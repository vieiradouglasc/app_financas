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
    df_mes = df_lanc[(df_lanc['data'].dt.month == mes_sel) & (df_lanc['data'].dt.year == ano_sel)]

    # --- CÁLCULOS 50/30/20 ---
    receita_total = df_mes[df_mes['tipo_mov'] == 'Receita']['valor'].sum()
    
    # 50% Essencial: Fixos + Dívidas
    essencial = df_mes[(df_mes['tipo_mov'] == 'Despesa') & 
                       (df_mes['tipo_custo'].isin(['Fixo', 'Dívida']))]['valor'].sum()
    
    # 30% Lazer: Variável (Despesas que não são investimentos nem fixas)
    lazer = df_mes[(df_mes['tipo_mov'] == 'Despesa') & 
                   (df_mes['tipo_custo'] == 'Variável')]['valor'].sum()
    
    # 20% Investimentos
    investido_mes = df_mes[df_mes['tipo_custo'] == 'Investimento']['valor'].sum()
    
    # Totalizadores
    despesa_total = essencial + lazer + investido_mes
    saldo_livre = receita_total - despesa_total

    # --- INDICADORES DE SAÚDE FINANCEIRA (50/30/20) ---
    with st.container(border=True):
        st.markdown(f"### 📊 Saúde Financeira ({meses_pt[mes_sel]}/{ano_sel})")
        
        if receita_total > 0:
            p_ess = (essencial / receita_total)
            p_laz = (lazer / receita_total)
            p_inv = (investido_mes / receita_total)

            k1, k2, k3 = st.columns(3)
            k1.metric("Essencial (Meta 50%)", f"{p_ess*100:.1f}%", delta=f"{50 - p_ess*100:.1f}%", delta_color="normal" if p_ess <= 0.5 else "inverse")
            k2.metric("Lazer (Meta 30%)", f"{p_laz*100:.1f}%", delta=f"{30 - p_laz*100:.1f}%", delta_color="normal" if p_laz <= 0.3 else "inverse")
            k3.metric("Investir (Meta 20%)", f"{p_inv*100:.1f}%", delta=f"{p_inv*100 - 20:.1f}%", delta_color="normal" if p_inv >= 0.2 else "inverse")
            
            st.markdown(f"**Saldo Final do Mês:** R$ {saldo_livre:,.2f}")
            st.progress(min(p_ess + p_laz + p_inv, 1.0), text="Percentual da Renda Utilizada")
        else:
            st.warning("Sem receitas registradas para este período.")

    st.divider()

    # --- KPIs SUPERIORES (Patrimônio Geral) ---
    patrimonio = df_carteira['valor_acumulado'].sum() if not df_carteira.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Período", f"R$ {receita_total:,.2f}")
    c2.metric("Despesas Reais", f"R$ {(essencial + lazer):,.2f}")
    c3.metric("Aportes Período", f"R$ {investido_mes:,.2f}")
    c4.metric("Patrimônio Total", f"R$ {patrimonio:,.2f}")

    st.divider()

    # --- GRÁFICO ANUAL E ALERTAS ---
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.markdown("#### 📈 Evolução Anual")
        df_anual = df_lanc[df_lanc['data'].dt.year == ano_sel].copy()
        if not df_anual.empty:
            df_anual['Mes'] = df_anual['data'].dt.strftime('%b')
            df_chart = df_anual.groupby(['Mes', 'tipo_mov'])['valor'].sum().reset_index()
            fig_evolucao = px.bar(df_chart, x='Mes', y='valor', color='tipo_mov', barmode='group',
                                  color_discrete_map={'Receita': '#3fb950', 'Despesa': '#f85149'},
                                  category_orders={"Mes": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]})
            fig_evolucao.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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
            st.error("⚠️ Orçamento Negativo para este mês!")

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