import subprocess
import time
import socket
import webview

STREAMLIT = r"C:\Users\paulo.herrera\AppData\Local\Python\pythoncore-3.14-64\Scripts\streamlit.exe"

DASHBOARD = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\dashboard.py"

def servidor_ativo():

    try:

        socket.create_connection(
            ("127.0.0.1", 8501),
            timeout=1
        )

        return True

    except:

        return False

if not servidor_ativo():

    subprocess.Popen(
        [
            STREAMLIT,
            "run",
            DASHBOARD,
            "--server.headless=true"
        ]
    )

for _ in range(30):

    if servidor_ativo():

        break

    time.sleep(1)

webview.create_window(
    "Gestor CEABS",
    "http://127.0.0.1:8501",
    width=1600,
    height=900
)

webview.start()