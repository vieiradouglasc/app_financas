import sqlite3

def create_connection():
    """Estabelece a conexão com o banco de dados SQLite."""
    return sqlite3.connect('financeiro.db', check_same_thread=False)

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()
    
    # 1. TABELA DE LANÇAMENTOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            descricao TEXT,
            categoria TEXT,
            valor REAL,
            tipo_mov TEXT,
            tipo_custo TEXT
        )
    """)
    
    # 2. TABELA DE METAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor_objetivo REAL NOT NULL,
            valor_atual REAL DEFAULT 0,
            icone TEXT DEFAULT '🎯'
        )
    """)
    
    # 3. TABELA DE CARTÕES DE CRÉDITO
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cartoes_credito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            limite REAL,
            fechamento INTEGER,
            vencimento INTEGER
        )
    """)

    # 4. NOVO: TABELA DE CARTÕES DE BENEFÍCIOS (Vale Alimentação / Presente)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cartoes_beneficios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            saldo REAL DEFAULT 0
        )
    """)

    # 5. TABELAS DE INVESTIMENTOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipos_investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT NOT NULL, 
            cor TEXT DEFAULT '#58a6ff'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carteira_investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_id INTEGER,
            valor_acumulado REAL DEFAULT 0,
            FOREIGN KEY (tipo_id) REFERENCES tipos_investimentos(id)
        )
    """)

    # 6. TABELA DE DÍVIDAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dividas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor_total REAL NOT NULL,
            valor_pago REAL DEFAULT 0,
            vencimento TEXT,
            responsavel TEXT,
            forma_pagto TEXT,
            total_parcelas INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Ativa'
        )
    """)
    
    # 7. TABELAS AUXILIARES
    cursor.execute("CREATE TABLE IF NOT EXISTS categorias_receitas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS categorias_despesas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, tipo TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS contas_bancarias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS responsaveis (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")

    # --- BLOCO DE MIGRAÇÃO ---
    # Garante que colunas novas existam em bancos de dados antigos
    try: cursor.execute("ALTER TABLE metas ADD COLUMN icone TEXT DEFAULT '🎯'")
    except: pass
    
    try: cursor.execute("ALTER TABLE lancamentos ADD COLUMN tipo_custo TEXT DEFAULT 'Variável'")
    except: pass

    try: cursor.execute("ALTER TABLE dividas ADD COLUMN status TEXT DEFAULT 'Ativa'")
    except: pass

    try: cursor.execute("ALTER TABLE dividas ADD COLUMN forma_pagto TEXT")
    except: pass

    try: cursor.execute("ALTER TABLE dividas ADD COLUMN total_parcelas INTEGER DEFAULT 1")
    except: pass

    try: cursor.execute("ALTER TABLE dividas ADD COLUMN responsavel TEXT")
    except: pass

    conn.commit()
    conn.close()

# Executa ao carregar para garantir que o esquema esteja pronto
create_tables()