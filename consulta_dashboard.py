import sqlite3

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

cursor.execute("""
SELECT
    a.placa,
    t.descricao,
    t.categoria_nome,
    a.nivel_risco,
    a.data_hora
FROM tb_safe_alarmes a
INNER JOIN tb_safe_tipos_alarme t
    ON a.codigo_alarme = t.codigo_alarme
ORDER BY a.data_hora DESC
LIMIT 20
""")

dados = cursor.fetchall()

for linha in dados:
    print(linha)

conn.close()