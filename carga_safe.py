import requests
import sqlite3
from datetime import datetime

# =====================================
# CONFIGURAÇÃO DO BANCO
# =====================================

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

# =====================================
# ÚLTIMO ID
# =====================================

cursor.execute("""
SELECT COALESCE(MAX(id),0)
FROM tb_safe_alarmes
""")

ultimo_id = cursor.fetchone()[0]

print(f"Ultimo ID encontrado: {ultimo_id}")

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

print("Token obtido com sucesso")

# =====================================
# CONSULTA SAFE
# =====================================

url = (
    f"https://api.showtecnologia.com/api/safe/alarmes/monitoramento"
    f"?tipoConsulta=id"
    f"&desde={ultimo_id}"
    f"&limit=250"
    f"&apenasMidia=false"
)

response_safe = requests.get(
    url,
    headers={
        "accept": "application/json",
        "x-access-token": token
    }
)

if response_safe.status_code != 200:
    raise Exception(response_safe.text)

dados = response_safe.json()["dados"]

print(f"Alarmes retornados: {len(dados)}")

# =====================================
# INSERT ALARMES
# =====================================

registros_inseridos = 0

for item in dados:

    cursor.execute("""
        INSERT OR IGNORE INTO tb_safe_alarmes (
            id,
            placa,
            data_hora,
            codigo_alarme,
            velocidade,
            nivel_risco,
            tratado,
            endereco,
            latitude,
            longitude,
            data_carga,
            cpf_motorista
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        item.get("id"),
        item.get("objeto"),
        item.get("momentoOcorrencia", {}).get("inicio"),
        item.get("alarme", {}).get("codigo"),
        item.get("velocidade"),
        item.get("nivelRisco"),
        int(item.get("tratado", False)),
        item.get("localizacao", {}).get("endereco"),
        item.get("localizacao", {}).get("latitude"),
        item.get("localizacao", {}).get("longitude"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        item.get("cpf_motorista")
    ))

    if cursor.rowcount > 0:
        registros_inseridos += 1

conn.commit()

# =====================================
# LOG
# =====================================

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
    "SAFE",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    registros_inseridos,
    "SUCESSO",
    f"Carga SAFE - {registros_inseridos} registros"
))

conn.commit()
conn.close()

print(f"Registros novos inseridos: {registros_inseridos}")
print("Carga concluida com sucesso")