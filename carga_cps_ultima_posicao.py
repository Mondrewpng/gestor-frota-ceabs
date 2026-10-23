from datetime import datetime, timedelta
import sqlite3
import requests

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

TOKEN = "43086FE2338A4D43A2B489450BD13091"

URL = "https://apicps.ceabs.com.br/api/UltimaPosicao/List"

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"

# ==========================================================
# CONEXÃO
# ==========================================================

conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

# ==========================================================
# REQUISIÇÃO
# ==========================================================

headers = {"Authorization": TOKEN, "Content-Type": "application/json"}

print("=" * 70)
print("CARGA CPS - ÚLTIMA POSIÇÃO")
print("=" * 70)

response = requests.post(URL, headers=headers, json={}, timeout=120)

response.raise_for_status()

dados = response.json()

registros = dados.get("Registros", [])

print(f"Veículos encontrados: {len(registros)}")

# ==========================================================
# PROCESSAMENTO
# ==========================================================

for item in registros:

  ultima = item.get("UltimaPosicao", {})

  placa = item.get("Placa")
  chassi = item.get("Chassi")
  rastreador_numero_serie = item.get("RastreadorNumeroSerie")

  data_posicao = ultima.get("DataHoraEvento")

  data_posicao_local = None
  dt_local = None

  if data_posicao:
    try:
      dt_api = datetime.fromisoformat(data_posicao)
      dt_local = dt_api - timedelta(hours=3)

      data_posicao_local = dt_local.strftime("%Y-%m-%d %H:%M:%S")

    except Exception:
      pass

  latitude = ultima.get("Latitude")
  longitude = ultima.get("Longitude")

  velocidade = ultima.get("Velocidade")

  gps_fixado = 1 if ultima.get("GpsFixado") else 0

  proa = ultima.get("Proa")

  altitude = ultima.get("Altitude")

  # --- TRATAMENTO INTELIGENTE DE IGNIÇÃO (EVITA FANTASMAS) ---
  ignicao_api = 1 if ultima.get("Ignicao") else 0
  ignicao = 0

  if dt_local:
    # Calcula há quantas horas o veículo enviou o último sinal
    horas_inativo = (datetime.now() - dt_local).total_seconds() / 3600

    # TRAVA: Se o veículo enviou sinal nas últimas 3 horas, confiamos no status da API.
    # Se está há mais de 3 horas sem comunicar, forçamos a ignição como 0 (desligado/offline).
    if horas_inativo <= 3:
      ignicao = ignicao_api
    else:
      ignicao = 0
  else:
    ignicao = 0
  # -----------------------------------------------------------

  municipio = ultima.get("RevGeoMunicipio")
  uf = ultima.get("RevGeoUf")

  odometro = ultima.get("Odometro")
  horimetro = ultima.get("Horimetro")

  motorista_identificador = ultima.get("MotoristaIdentificador")

  data_carga = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  cursor.execute(
      """
        INSERT OR REPLACE INTO tb_cps_ultima_posicao (
            placa,
            chassi,
            rastreador_numero_serie,
            data_posicao,
            data_posicao_local,
            latitude,
            longitude,
            velocidade,
            gps_fixado,
            proa,
            altitude,
            ignicao,
            municipio,
            uf,
            odometro,
            horimetro,
            motorista_identificador,
            data_carga
        )
        VALUES (
            ?, ?, ?,
            ?, ?,
            ?, ?,
            ?,
            ?,
            ?, ?,
            ?,
            ?, ?,
            ?, ?,
            ?,
            ?
        )
        """,
      (
          placa,
          chassi,
          rastreador_numero_serie,
          data_posicao,
          data_posicao_local,
          latitude,
          longitude,
          velocidade,
          gps_fixado,
          proa,
          altitude,
          ignicao,
          municipio,
          uf,
          odometro,
          horimetro,
          motorista_identificador,
          data_carga,
      ),
  )

# ==========================================================
# FINALIZAÇÃO
# ==========================================================

conn.commit()

print(f"{len(registros)} posições atualizadas.")

conn.close()

print("Carga CPS concluída com sucesso.")
print("=" * 70)