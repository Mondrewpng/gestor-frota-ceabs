import subprocess
import sys
import os
import time
from datetime import datetime

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SCRIPTS = [

    # SAFE
    "carga_tipos_safe.py",
    "carga_safe.py",
    "carga_veiculos_safe.py",

    # CPS
    "carga_cps_ultima_posicao.py",
    "carga_cps_infracoes.py",
    "carga_cps_viagens.py",
    "carga_cps_eventos_geo.py"

]

print("=" * 100)
print("GESTOR CEABS - PROCESSAMENTO MASTER")
print(datetime.now())
print("=" * 100)

sucessos = []
falhas = []

for script in SCRIPTS:

    caminho = os.path.join(
        BASE_DIR,
        script
    )

    print()
    print("-" * 100)
    print(f"EXECUTANDO: {script}")
    print("-" * 100)

    if not os.path.exists(caminho):

        print(
            f"ARQUIVO NÃO ENCONTRADO: {caminho}"
        )

        falhas.append(script)

        continue

    inicio = time.time()

    try:

        resultado = subprocess.run(

            [sys.executable, caminho],

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            cwd=BASE_DIR

        )

        tempo = round(
            time.time() - inicio,
            1
        )

        print(
            f"RETORNO : {resultado.returncode}"
        )

        print(
            f"TEMPO   : {tempo}s"
        )

        if resultado.stdout:

            print()
            print("SAÍDA")
            print(resultado.stdout)

        if resultado.stderr:

            print()
            print("ERROS")
            print(resultado.stderr)

        if resultado.returncode == 0:

            sucessos.append(script)

        else:

            falhas.append(script)

    except Exception as erro:

        print(
            f"ERRO FATAL: {erro}"
        )

        falhas.append(script)

print()
print("=" * 100)
print("RESUMO")
print("=" * 100)

print()
print("SUCESSOS")

for item in sucessos:

    print(f"✅ {item}")

print()

print("FALHAS")

for item in falhas:

    print(f"❌ {item}")

print()

print(
    f"TOTAL SUCESSOS: {len(sucessos)}"
)

print(
    f"TOTAL FALHAS  : {len(falhas)}"
)

print()

print(datetime.now())

print("=" * 100)

if falhas:

    sys.exit(1)

sys.exit(0)