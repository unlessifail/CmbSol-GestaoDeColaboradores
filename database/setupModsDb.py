import sqlite3
import hashlib

def criar_bd():
    conn = sqlite3.connect("cmob_moderadores.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        )
    ''')
    
    # Lista de moderadores fixos
    moderadores = [
        ("cmob-mod01", "pass01modsgc"),
        ("cmob-mod02", "passIImodSGC"),
        ("cmob-mod03", "passMasterKey03III")
    ]
    
    for usuario, senha in moderadores:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        try:
            cursor.execute("INSERT INTO moderadores (usuario, senha_hash) VALUES (?, ?)", (usuario, senha_hash))
        except sqlite3.IntegrityError:
            pass  # Evita erro caso já existam usuários
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    criar_bd()
    print("Banco de dados e moderadores configurados com sucesso!")