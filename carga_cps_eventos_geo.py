import sqlite3
import requests
from datetime import datetime, timedelta

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

TOKEN = "43086FE2338A4D43A2B489450BD13091"

URL = "https://apicps.ceabs.com.br/api/Evento/List"

BANCO = (
    r"C:\Users\paulo.herrera\OneDrive - VIC"
    r"\Área de Trabalho\BancoAPI\SQL - e-Frotas"
    r"\Gestor - Ceabs.db"
)

TIMEOUT_SEGUNDOS = 300

# ==========================================================
# CONEXÃO COM O BANCO
# ==========================================================

conn = sqlite3.connect(BANCO, timeout=60)
cursor = conn.cursor()

cursor.execute("PRAGMA busy_timeout = 60000")

print("=" * 80)
print("CPS - EVENTOS GEO")
print("=" * 80)

# ==========================================================
# DEFINE O PERÍODO
#
# Se já houver registros:
# começa 6 horas antes do último evento, por segurança.
#
# Se estiver vazio:
# busca os últimos 2 dias.
#
# A janela consultada nunca ultrapassa 2 dias corridos.
# ==========================================================

cursor.execute(
    """
    SELECT MAX(data_hora_evento)
    FROM tb_cps_eventos_geo
    """
)

ultima_data = cursor.fetchone()[0]

agora = datetime.now()

if ultima_data:

    try:
        dt_ultima = datetime.fromisoformat(
            str(ultima_data).replace("T", " ")
        )

        data_inicio_dt = dt_ultima - timedelta(hours=6)

        # Não permite começar depois do horário atual
        if data_inicio_dt > agora:
            data_inicio_dt = agora - timedelta(days=1)

        print(f"Último evento encontrado: {ultima_data}")

    except Exception as erro_data:
        print(f"Falha ao interpretar última data: {erro_data}")

        data_inicio_dt = (
            agora - timedelta(days=1)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

else:
    # Hoje e ontem, totalizando dois dias corridos
    data_inicio_dt = (
        agora - timedelta(days=1)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

# Final da janela: máximo de dois dias corridos
data_fim_dt = (
    data_inicio_dt + timedelta(days=1)
).replace(
    hour=23,
    minute=59,
    second=59,
    microsecond=0
)

# Não consulta além do horário atual
if data_fim_dt > agora:
    data_fim_dt = agora

data_inicio = data_inicio_dt.strftime(
    "%Y-%m-%dT%H:%M:%S-03:00"
)

data_fim = data_fim_dt.strftime(
    "%Y-%m-%dT%H:%M:%S-03:00"
)

print(f"Data Início: {data_inicio}")
print(f"Data Fim   : {data_fim}")

# ==========================================================
# REQUISIÇÃO
# ==========================================================

headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "StartIndex": 1,
    "DataInicio": data_inicio,
    "DataFim": data_fim,
    "Dispositivo": {
        "Placa": ""
    }
}

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=TIMEOUT_SEGUNDOS
    )

    print(f"Status HTTP: {response.status_code}")

    response.raise_for_status()

    dados = response.json()

except requests.RequestException as erro_http:
    conn.close()
    raise RuntimeError(
        f"Erro na comunicação com a API CPS: {erro_http}"
    )

except ValueError as erro_json:
    texto_retorno = response.text[:2000]
    conn.close()

    raise RuntimeError(
        "A API CPS não retornou um JSON válido.\n"
        f"Retorno recebido:\n{texto_retorno}"
    ) from erro_json

# ==========================================================
# VALIDAÇÃO DO RETORNO CPS
# ==========================================================

if isinstance(dados, dict):

    mensagem = dados.get("Message")

    if dados.get("Success") is False and mensagem:
        conn.close()

        raise RuntimeError(
            f"Erro retornado pela CPS: {mensagem}"
        )

    registros = dados.get("Registros")

elif isinstance(dados, list):

    registros = dados

else:

    registros = []

if not isinstance(registros, list):
    registros = []

print(f"Eventos retornados: {len(registros)}")

# ==========================================================
# PROCESSAMENTO
# ==========================================================

novos = 0
existentes = 0
invalidos = 0
erros = 0

data_carga = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

for item in registros:

    try:
        placa = item.get("Placa")
        data_hora_evento = item.get("DataHoraEvento")
        rastreador = item.get("RastreadorNumeroSerie")

        if not placa or not data_hora_evento:
            invalidos += 1
            continue

        # Verificação de duplicidade:
        # placa + horário + rastreador
        cursor.execute(
            """
            SELECT 1
            FROM tb_cps_eventos_geo
            WHERE placa = ?
              AND data_hora_evento = ?
              AND COALESCE(rastreador_numero_serie, '') =
                  COALESCE(?, '')
            LIMIT 1
            """,
            (
                placa,
                data_hora_evento,
                rastreador
            )
        )

        if cursor.fetchone():
            existentes += 1
            continue

        # O campo id não é informado.
        # O SQLite gera o INTEGER PRIMARY KEY automaticamente.
        cursor.execute(
            """
            INSERT INTO tb_cps_eventos_geo (
                placa,
                chassi,
                rastreador_numero_serie,
                data_hora_evento,
                latitude,
                longitude,
                velocidade,
                ignicao,
                gps_fixado,
                odometro,
                horimetro,
                municipio,
                uf,
                motorista_nome,
                motorista_identificador,
                data_carga
            )
            VALUES (
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                placa,
                item.get("Chassi"),
                rastreador,
                data_hora_evento,
                item.get("Latitude"),
                item.get("Longitude"),
                item.get("Velocidade"),
                1 if item.get("Ignicao") else 0,
                1 if item.get("GpsFixado") else 0,
                item.get("Odometro"),
                item.get("Horimetro"),
                item.get("RevGeoMunicipio"),
                item.get("RevGeoUf"),
                item.get("MotoristaNome"),
                item.get("MotoristaIdentificador"),
                data_carga
            )
        )

        novos += 1

    except Exception as erro_item:
        erros += 1

        print(
            "Erro ao processar evento "
            f"{item.get('Placa')} / "
            f"{item.get('DataHoraEvento')}: "
            f"{erro_item}"
        )

# ==========================================================
# FINALIZAÇÃO
# ==========================================================

conn.commit()

cursor.execute(
    """
    SELECT COUNT(*)
    FROM tb_cps_eventos_geo
    """
)

total_banco = cursor.fetchone()[0]

cursor.execute(
    """
    SELECT
        MIN(data_hora_evento),
        MAX(data_hora_evento)
    FROM tb_cps_eventos_geo
    """
)

periodo_banco = cursor.fetchone()

conn.close()

print()
print("=" * 80)
print("RESUMO")
print("=" * 80)
print(f"Recebidos  : {len(registros)}")
print(f"Novos      : {novos}")
print(f"Existentes : {existentes}")
print(f"Inválidos  : {invalidos}")
print(f"Erros      : {erros}")
print(f"Banco      : {total_banco}")

if periodo_banco:
    print(f"Primeiro   : {periodo_banco[0]}")
    print(f"Último     : {periodo_banco[1]}")

print("=" * 80)
print("Carga concluída.")