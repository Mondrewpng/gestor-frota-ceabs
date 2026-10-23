import os
import subprocess
import sys
import time
import webbrowser

# Garante que o diretório de trabalho é o correto
pasta_trabalho = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas"
if os.path.exists(pasta_trabalho):
  os.chdir(pasta_trabalho)

print("=" * 60)
print("INICIANDO GESTOR CEABS - CARGA & DASHBOARD")
print("=" * 60)

# 1. Executa o ETL completo antes de abrir o painel
print("\n[1/3] Executando sincronização de dados (ETL)...")
subprocess.run([sys.executable, "executar_tudo.py"])

# 2. Inicia o Streamlit em segundo plano
print("\n[2/3] Subindo o servidor do painel...")
streamlit_process = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "dashboard.py"]
)

# Aguarda alguns segundos para o servidor estabilizar
time.sleep(4)

# 3. Abre o navegador padrão automaticamente
print("\n[3/3] Abrindo navegador...")
webbrowser.open("http://localhost:8501")

print("\nAplicativo rodando com sucesso! Você pode minimizar esta janela.")

# Mantém o processo ativo enquanto o Streamlit estiver aberto
streamlit_process.wait()