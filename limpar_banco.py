import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect("notas.db")
cursor = conn.cursor()

# Apagar todos os usuários e notas
cursor.execute("DELETE FROM usuarios;")
cursor.execute("DELETE FROM notas;")

# Resetar os IDs para começar do 1 novamente
cursor.execute("DELETE FROM sqlite_sequence WHERE name='usuarios';")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='notas';")

# Confirmar mudanças
conn.commit()
conn.close()

print("Usuários e notas foram apagados com sucesso!")
