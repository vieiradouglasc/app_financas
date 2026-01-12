import streamlit as st
from database import create_tables

# Configuração da página (DEVE ser o primeiro comando)
st.set_page_config(page_title="Controle Financeiro", page_icon="💰", layout="wide")

# Inicializa o banco (Garante que a tabela de dívidas seja criada)
create_tables()

# Importações dos módulos
from modules.dashboard import exibir_dashboard
from modules.lancamentos import exibir_lancamentos
from modules.metas import exibir_metas
from modules.investimentos import exibir_investimentos
from modules.dividas import exibir_dividas  # Nova importação
from modules.cadastros import exibir_cadastros

# --- MENU LATERAL ---
with st.sidebar:
    st.title("Controle Financeiro")
    st.markdown("---")
    menu = st.radio(
        "Menu Principal",
        [
            "📊 Dashboard", 
            "💸 Lançamentos", 
            "🎯 Metas", 
            "📈 Investimentos", 
            "📉 Dívidas", # Nova opção no menu
            "⚙️ Configurações"
        ],
        index=0
    )
    st.markdown("---")
    st.caption("Sistema v2.6 | 2026")

# --- ROTEAMENTO ---
if menu == "📊 Dashboard":
    exibir_dashboard()

elif menu == "💸 Lançamentos":
    exibir_lancamentos()

elif menu == "🎯 Metas":
    exibir_metas()

elif menu == "📈 Investimentos":
    exibir_investimentos()

elif menu == "📉 Dívidas":
    exibir_dividas()  # Chamada do novo módulo

elif menu == "⚙️ Configurações":
    exibir_cadastros()