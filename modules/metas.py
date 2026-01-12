import streamlit as st
import pandas as pd
from database import create_connection

def exibir_metas():
    st.markdown("<h2 style='color: white;'>🎯 Metas e Objetivos</h2>", unsafe_allow_html=True)
    
    conn = create_connection()
    
    # --- FILTROS E NOVO ITEM (ESTILO LANÇAMENTOS) ---
    with st.container():
        f1, f2 = st.columns([3, 1])
        if f2.button("➕ NOVA META", use_container_width=True):
            popup_nova_meta()

    # --- PROCESSAMENTO DE DADOS ---
    df_metas = pd.read_sql_query("SELECT * FROM metas", conn)
    
    if not df_metas.empty:
        # --- CARDS DE SOMATÓRIA ---
        total_objetivo = df_metas['valor_objetivo'].sum()
        total_acumulado = df_metas['valor_atual'].sum()
        total_falta = total_objetivo - total_acumulado
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Total Objetivos</p>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='color:#ffffff; margin:0;'>R$ {total_objetivo:,.2f}</h3>", unsafe_allow_html=True)
        with c2:
            with st.container(border=True):
                st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Total Acumulado</p>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='color:#3fb950; margin:0;'>R$ {total_acumulado:,.2f}</h3>", unsafe_allow_html=True)
        with c3:
            with st.container(border=True):
                st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Falta Total</p>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='color:#f85149; margin:0;'>R$ {max(total_falta, 0):,.2f}</h3>", unsafe_allow_html=True)
        with c4:
            with st.container(border=True):
                st.markdown("<p style='color:#8b949e; margin:0; font-size:14px;'>Progresso Geral</p>", unsafe_allow_html=True)
                prog_geral = (total_acumulado/total_objetivo*100) if total_objetivo > 0 else 0
                st.markdown(f"<h3 style='color:#58a6ff; margin:0;'>{prog_geral:.1f}%</h3>", unsafe_allow_html=True)

        st.divider()

        # --- LISTAGEM VERTICAL (ESTILO LANÇAMENTOS) ---
        st.markdown("#### Suas Metas Ativas")
        for _, row in df_metas.iterrows():
            valor_falta = row['valor_objetivo'] - row['valor_atual']
            percent = min(row['valor_atual'] / row['valor_objetivo'], 1.0) if row['valor_objetivo'] > 0 else 0
            
            with st.container():
                # Borda azul lateral para metas
                st.markdown(f'<div style="border-left: 4px solid #58a6ff; background: #161b22; padding: 12px; border-radius: 6px; margin-bottom: 8px;">', unsafe_allow_html=True)
                r1, r2, r3, r4, r5 = st.columns([0.5, 2.5, 2, 2, 0.5])
                
                r1.markdown(f"### {row['icone']}")
                r2.markdown(f"**{row['nome']}**<br><small style='color:#8b949e;'>Alvo: R$ {row['valor_objetivo']:,.2f}</small>", unsafe_allow_html=True)
                
                with r3:
                    st.write(f"Falta: R$ {max(valor_falta, 0):,.2f}")
                    st.progress(percent)
                
                r4.markdown(f"<div style='text-align:right;'><b>R$ {row['valor_atual']:,.2f}</b><br><small>{percent*100:.1f}%</small></div>", unsafe_allow_html=True)
                
                if r5.button("🗑️", key=f"del_meta_{row['id']}"):
                    conn.execute("DELETE FROM metas WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhuma meta cadastrada.")
    
    conn.close()

@st.dialog("Nova Meta")
def popup_nova_meta():
    with st.form("f_nova_meta", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        nome = col1.text_input("Nome da Meta")
        icone = col2.selectbox("Ícone", ["💰", "✈️", "🚗", "🏠", "💍", "🎓", "🏖️", "📱"])
        valor_obj = st.number_input("Valor Objetivo (R$)", min_value=0.0)
        
        if st.form_submit_button("Salvar Meta", use_container_width=True):
            if nome and valor_obj > 0:
                conn = create_connection()
                conn.execute("INSERT INTO metas (nome, valor_objetivo, valor_atual, icone) VALUES (?,?,?,?)", 
                             (nome, valor_obj, 0.0, icone))
                conn.commit()
                conn.close()
                st.rerun()