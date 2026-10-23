import requests
import sqlite3
from datetime import datetime

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

# =====================================
# LOGIN
# =====================================

response_login = requests.post(
    "https://api.showtecnologia.com/api/login",
    headers={
        "Content-Type": "application/json"
    },
    json={
        "user": "paulo.herrera@viccorp.com.br",
        "password": "38df1d8ce69f9e28fcd45dd7f5f276cb"
    }
)

if response_login.status_code != 200:
    raise Exception(response_login.text)

dados_login = response_login.json()

token = dados_login["token"]

print("Token obtido")

# =====================================
# TIPOS
# =====================================

response_tipos = requests.get(
    "https://api.showtecnologia.com/api/safe/alarmes/tipos",
    headers={
        "accept": "application/json",
        "x-access-token": token
    }
)

if response_tipos.status_code != 200:
    raise Exception(response_tipos.text)

tipos = response_tipos.json()["dados"]

print(f"Tipos encontrados: {len(tipos)}")

registros_inseridos = 0

for item in tipos:

    categoria = item.get("categoria", {})

    cursor.execute("""
        INSERT OR IGNORE INTO tb_safe_tipos_alarme (
            codigo_alarme,
            descricao,
            alerta,
            severidade,
            categoria_nome,
            categoria_codigo
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        item.get("id"),
        item.get("descricao"),
        item.get("alerta"),
        item.get("severidade"),
        categoria.get("nome"),
        categoria.get("codigo")
    ))

    if cursor.rowcount > 0:
        registros_inseridos += 1

conn.commit()

cursor.execute("""
INSERT INTO tb_carga_log (
    origem,
    data_execucao,
    registros_importados,
    status,
    mensagem
)
VALUES (?, ?, ?, ?, ?)
""",
(
    "SAFE_TIPOS",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    registros_inseridos,
    "SUCESSO",
    f"Tipos SAFE - {registros_inseridos} registros"
))

conn.commit()
conn.close()

print(f"Tipos inseridos: {registros_inseridos}")
print("Carga concluida com sucesso")