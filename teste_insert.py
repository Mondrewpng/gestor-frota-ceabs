import sqlite3
from datetime import datetime

banco = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(banco)

cursor = conn.cursor()

cursor.execute("""
INSERT INTO tb_carga_log (
    origem,
    data_execucao,
    registros_importados,
    status,
    mensagem
)
VALUES (?, ?, ?, ?, ?)
""", (
    "SAFE",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    1,
    "SUCESSO",
    "Teste Python"
))

conn.commit()

conn.close()

print("Registro gravado com sucesso!")