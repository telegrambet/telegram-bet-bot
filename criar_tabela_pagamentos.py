import sqlite3

conn = sqlite3.connect("apostas.db")
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_telegram INTEGER,
        payment_id TEXT,
        valor REAL,
        status TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print("Tabela 'pagamentos' criada com sucesso!")
