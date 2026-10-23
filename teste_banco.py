import sqlite3

banco = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(banco)

cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""")

for tabela in cursor.fetchall():
    print(tabela[0])

conn.close()