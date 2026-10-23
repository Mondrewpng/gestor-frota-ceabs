import sqlite3

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

cursor.execute("""
INSERT OR IGNORE INTO tb_safe_veiculos (
    placa
)
SELECT DISTINCT placa
FROM tb_safe_alarmes
WHERE placa IS NOT NULL
""")

conn.commit()

print(f"Veículos inseridos: {cursor.rowcount}")

conn.close()