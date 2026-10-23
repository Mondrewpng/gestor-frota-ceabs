import sqlite3

banco = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(banco)

cursor = conn.cursor()

cursor.execute("PRAGMA table_info(tb_safe_alarmes)")

for coluna in cursor.fetchall():
    print(coluna)

conn.close()