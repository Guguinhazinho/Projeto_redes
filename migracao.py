import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect("notas.db")
cursor = conn.cursor()

# Verificar se a coluna usuario_id já existe
cursor.execute("PRAGMA table_info(notas);")
colunas = [coluna[1] for coluna in cursor.fetchall()]

if "usuario_id" not in colunas:
    print("Adicionando a coluna 'usuario_id' à tabela 'notas'...")
    cursor.execute("ALTER TABLE notas ADD COLUMN usuario_id INTEGER DEFAULT 1;")
    conn.commit()
    print("Coluna adicionada com sucesso!")
else:
    print("A coluna 'usuario_id' já existe no banco de dados.")

# Fechar conexão
conn.close()
