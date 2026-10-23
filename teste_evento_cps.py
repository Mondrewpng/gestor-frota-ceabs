import requests
import json

TOKEN = "43086FE2338A4D43A2B489450BD13091"

URL = "https://apicps.ceabs.com.br/api/Evento/List"

headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

payload = {
    "StartIndex": 1,
    "DataInicio": "2026-10-01T00:00:00",
    "DataFim": "2026-10-09T23:59:59-03:00",
    "Dispositivo": {
        "Placa": ""
    }
}

response = requests.post(
    URL,
    headers=headers,
    json=payload,
    timeout=300
)

print("=" * 80)
print("STATUS")
print("=" * 80)
print(response.status_code)

print()
print("=" * 80)
print("RESPOTA BRUTA")
print("=" * 80)

print(response.text[:10000])

try:

    dados = response.json()

    print()
    print("=" * 80)
    print("TIPO")
    print("=" * 80)

    print(type(dados))

    if isinstance(dados, dict):

        print()
        print("CHAVES:")
        print(dados.keys())

except Exception as erro:

    print(erro)