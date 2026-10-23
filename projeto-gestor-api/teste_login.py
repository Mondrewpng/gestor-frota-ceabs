import requests

# LOGIN

response = requests.post(
    "https://api.showtecnologia.com/api/login",
    json={
        "user": "paulo.herrera@viccorp.com.br",
        "password": "38df1d8ce69f9e28fcd45dd7f5f276cb"
    },
    headers={
        "Content-Type": "application/json"
    }
)

dados_login = response.json()

token = dados_login["token"]

print("TOKEN:")
print(token)

# ALARMES

response_alarmes = requests.get(
    "https://api.showtecnologia.com/api/safe/alarmes/monitoramento?tipoConsulta=id&desde=0&limit=10&apenasMidia=false",
    headers={
        "accept": "application/json",
        "x-access-token": token
    }
)

print("\nSTATUS ALARMES:")
print(response_alarmes.status_code)

print("\nRESPOSTA:")
print(response_alarmes.text[:2000])