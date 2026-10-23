from datetime import datetime, timedelta
import sqlite3
import requests

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

TOKEN = "43086FE2338A4D43A2B489450BD13091"

URL = "https://apicps.ceabs.com.br/api/Infracao/BuscarInfracoesPorObjetoEDia"

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

TIPOS_INFRACAO = [
    45,   # Aceleração Brusca
    46,   # Freada Brusca
    47,   # Curva Brusca
    48,   # Velocidade Excessiva (>120 km/h)
    79,   # Banguela
    81,   # RPM Elevado
    84,   # Extrema Velocidade (>140 km/h)
    95,   # Pernoite Fora da Base
    996,  # Entrada Drino
    997   # Saída Drino
]

# ==========================================================
# CONEXÃO
# ==========================================================

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

# Índice para evitar duplicidade
cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_cps_infracao
ON tb_cps_infracoes(infracao_id)
""")

print("=" * 80)
print("CARGA CPS - INFRAÇÕES")
print("=" * 80)

# ==========================================================
# BUSCAR PLACAS
# ==========================================================

cursor.execute("""
SELECT DISTINCT placa
FROM tb_cps_ultima_posicao
WHERE placa IS NOT NULL
AND placa <> ''
ORDER BY placa
""")

placas = [row[0] for row in cursor.fetchall()]

if not placas:
    print("Nenhuma placa encontrada.")
    conn.close()
    raise SystemExit()

print(f"Total de veículos encontrados: {len(placas)}")

# ==========================================================
# VARIÁVEIS
# ==========================================================

headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

novos_total = 0
existentes_total = 0
erros_total = 0

tipos_encontrados = {}

# ==========================================================
# LOOP DE CONSULTA
# ==========================================================

for dia in range(31):

    data_consulta = (
        datetime.now() - timedelta(days=dia)
    ).strftime("%Y-%m-%dT00:00:00")

    print()
    print("=" * 80)
    print(f"DATA: {data_consulta}")
    print("=" * 80)

    novos_dia = 0

    for placa in placas:

        payload = {
            "Data": data_consulta,
            "Placa": placa,
            "InfracaoTipo": TIPOS_INFRACAO
        }

        try:

            resposta = requests.post(
                URL,
                headers=headers,
                json=payload,
                timeout=60
            )

            resposta.raise_for_status()

            dados = resposta.json()

            if isinstance(dados, list):
                registros = dados

            elif isinstance(dados, dict):
                registros = dados.get("Registros", [])

            else:
                registros = []

            if registros:
                print(
                    f"[{placa}] -> "
                    f"{len(registros)} infrações"
                )

            for item in registros:

                try:

                    infracao_id = item.get("InfracaoId")

                    if not infracao_id:
                        continue

                    tipo = item.get("InfracaoTipoid")

                    # Segurança extra
                    if tipo == 998:
                        continue

                    if tipo not in tipos_encontrados:
                        tipos_encontrados[tipo] = 1

                    cursor.execute("""
                    INSERT OR IGNORE INTO tb_cps_infracoes (
                        infracao_id,
                        placa,
                        chassi,
                        infracao_tipo_id,
                        inicio,
                        termino,
                        tempo_segundos,
                        distancia,
                        velocidade,
                        velocidade_maxima,
                        velocidade_via,
                        latitude_inicio,
                        longitude_inicio,
                        cidade,
                        estado,
                        data_carga,
                        inicio_local,
                        termino_local,
                        logradouro_inicio,
                        faixa_numeracao_inicio,
                        cep_inicio,
                        motorista
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        item.get("InfracaoId"),
                        item.get("Placa"),
                        item.get("Chassi"),
                        item.get("InfracaoTipoid"),
                        item.get("Inicio"),
                        item.get("Termino"),
                        item.get("Tempo"),
                        item.get("Distancia"),
                        item.get("Velocidade"),
                        item.get("VelocidadeMaxima"),
                        item.get("VelocidadeVia"),
                        item.get("LatitudeInicio"),
                        item.get("LongitudeInicio"),
                        item.get("Cidade"),
                        item.get("Estado"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        item.get("InicioLocal"),
                        item.get("TerminoLocal"),
                        item.get("LogradouroInicio"),
                        item.get("FaixaNumeracaoInicio"),
                        item.get("CepInicio"),
                        item.get("Motorista")
                    ))

                    if cursor.rowcount > 0:
                        novos_total += 1
                        novos_dia += 1
                    else:
                        existentes_total += 1

                except Exception as erro:

                    erros_total += 1

                    print(
                        f"Erro ao inserir infração "
                        f"{item.get('InfracaoId')}: {erro}"
                    )

            conn.commit()

        except Exception as erro:

            erros_total += 1

            print(
                f"Erro na placa {placa}: {erro}"
            )

    print(f"Total inserido no dia: {novos_dia}")

# ==========================================================
# RESUMO DE TIPOS
# ==========================================================

print()
print("=" * 80)
print("TIPOS ENCONTRADOS")
print("=" * 80)

for tipo in sorted(tipos_encontrados):
    print(f"Tipo {tipo}")

# ==========================================================
# FINALIZAÇÃO
# ==========================================================

cursor.execute("""
SELECT COUNT(*)
FROM tb_cps_infracoes
""")

total_banco = cursor.fetchone()[0]

conn.close()

print()
print("=" * 80)
print("RESUMO FINAL")
print("=" * 80)
print(f"Novos registros : {novos_total}")
print(f"Já existentes   : {existentes_total}")
print(f"Erros           : {erros_total}")
print(f"Total no banco  : {total_banco}")
print("=" * 80)
print("Carga concluída com sucesso.")
print("=" * 80)