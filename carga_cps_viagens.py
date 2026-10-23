import sqlite3
import requests
from datetime import datetime, timedelta

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

TOKEN = "43086FE2338A4D43A2B489450BD13091"
URL = "https://apicps.ceabs.com.br/api/Viagens/BuscarViagensPorObjetoRastreavelEDia"
BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

# Lista completa de todas as placas da frota extraídas da base operacional
FROTA_PLACAS = [
    "GCU9940", "GHG7G39", "DTR4505", "TZA0D69", "TJC7H84", "RNL0C63",
    "BIH6457", "GJZ6J14", "ECM0J17", "TJD5B43", "TKV3A35", "FMT0J16",
    "BJJ5F65", "KET2C20", "EPP1823", "TKF2A71", "TBP5F69", "QST9C98",
    "BJT4C91", "TJF1J71", "GFE9407", "TKT7J27", "DRK2951", "UEB6C51",
    "BPZ5C31", "TLQ5A47", "GFT6I01", "UFI9A22", "EPK7A16", "UQZ8C19",
    "BQN4I78", "UFF6H01", "JMY2661", "SWU8J88", "FDS6E15",
    "BQV5I36", "SVU1E70", "JOL8E55", "ARO4A54", "FQM6887",
    "CUE3J04", "DAZ8F21", "PEL9D44", "BZA6808", "FQU0021",
    "CZJ3A94", "GBO0A69", "SWI7H18", "TAQ1J74", "GBW4329",
    "DZZ7138", "BXF2228", "TBD5F35", "TAQ2D70", "TKL0D76",
    "ECCOB00", "BXS8381", "TBE3E46", "TBM6C66", "TJH2C37",
    "EPM2188", "CPG9512", "TBM6C81", "UDH5F27", "UDV1J79",
    "FSS9I21", "CUD3A01", "TBP5F68", "UDQ4F88", "UEB9B68",
    "GDP4J81", "DEL5920", "TKF9C96", "UDU0C89", "UGR8G79"
]

# ==========================================================
# CONEXÃO
# ==========================================================

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

print("=" * 80)
print("CPS - CARGA DE VIAGENS POR PLACA E DIA (FROTA COMPLETA)")
print("=" * 80)

headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

novos = 0
existentes = 0
recebidas = 0
dias_analise = 2  # Altere para 15 ou 30 se precisar de mais histórico retroativo

# ==========================================================
# LOOP POR DIA E POR CADA PLACA DA FROTA
# ==========================================================

for dia in range(dias_analise):
    data_consulta = (datetime.now() - timedelta(days=dia)).strftime("%Y-%m-%dT00:00:00")
    print(f"\n--- Consultando data: {data_consulta} ---")

    for placa in FROTA_PLACAS:
        payload = {
            "Data": data_consulta,
            "Placa": placa
        }

        try:
            response = requests.post(
                URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                continue

            dados = response.json()

            if isinstance(dados, list):
                registros = dados
            elif isinstance(dados, dict):
                registros = dados.get("Registros", [])
            else:
                registros = []

            if not registros:
                continue

            recebidas += len(registros)

            # ======================================================
            # PROCESSAMENTO E GRAVAÇÃO NO SQLITE
            # ======================================================
            for item in registros:
                p_placa = item.get("Placa")
                inicio = item.get("Inicio")
                termino = item.get("Termino")

                cursor.execute("""
                    SELECT 1
                    FROM tb_cps_viagens
                    WHERE placa = ?
                    AND inicio = ?
                    AND termino = ?
                """, (p_placa, inicio, termino))

                if cursor.fetchone():
                    existentes += 1
                    continue

                cursor.execute("""
                    INSERT INTO tb_cps_viagens (
                        placa, chassi, numero_serie, inicio, termino,
                        inicio_local, termino_local, tempo_segundos,
                        odometro_inicio, odometro_termino, distancia_km,
                        velocidade_maxima, velocidade_media,
                        qtd_aceleracao_brusca, qtd_freada_brusca,
                        qtd_curva_agressiva, qtd_banguela, tempo_parado_ignicao,
                        latitude_inicio, longitude_inicio, latitude_fim, longitude_fim,
                        cidade_inicio, cidade_fim, motorista_nome, motorista_cpf, data_carga
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("Placa"),
                    item.get("Chassi"),
                    item.get("NumeroSerie"),
                    item.get("Inicio"),
                    item.get("Termino"),
                    item.get("InicioLocal"),
                    item.get("TerminoLocal"),
                    item.get("Tempo"),
                    item.get("OdometroPainelInicio"),
                    item.get("OdometroPainelTermino"),
                    item.get("Distancia"),
                    item.get("VelocidadeMaxima"),
                    item.get("VelocidadeMedia"),
                    item.get("QtdAceleracaoBrusca"),
                    item.get("QtdFreadaBrusca"),
                    item.get("QtdCurvaAgressiva"),
                    item.get("QtdBanguela"),
                    item.get("TempoParadoIgnicaoLigada"),
                    item.get("LatitudeInicio"),
                    item.get("LongitudeInicio"),
                    item.get("LatitudeTermino"),
                    item.get("LongitudeTermino"),
                    item.get("CidadeInicio"),
                    item.get("CidadeTermino"),
                    item.get("MotoristaNome"),
                    item.get("MotoristaCpf"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                novos += 1

        except Exception as e:
            # Mantém o loop rodando mesmo se algum veículo falhar pontualmente
            continue

    conn.commit()

# ==========================================================
# FINALIZAÇÃO
# ==========================================================

cursor.execute("SELECT COUNT(*) FROM tb_cps_viagens")
total_banco = cursor.fetchone()[0]
conn.close()

print()
print("=" * 80)
print("RESUMO FINAL DA CARGA DE VIAGENS")
print("=" * 80)
print(f"Viagens Recebidas : {recebidas}")
print(f"Novas Inseridas   : {novos}")
print(f"Já Existentes     : {existentes}")
print(f"Total no Banco    : {total_banco}")
print("=" * 80)
print("Carga concluída com sucesso.")