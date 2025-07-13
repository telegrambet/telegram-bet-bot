import sqlite3

# Cria (ou abre) o banco de dados
conn = sqlite3.connect("apostas.db")
cursor = conn.cursor()

# Cria a tabela de usuários
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_telegram INTEGER UNIQUE,
    nome TEXT,
    saldo REAL
)
""")

conn.commit()
conn.close()

print("Tabela 'usuarios' criada com sucesso.")
