import sqlite3
from datetime import datetime

# Caminho do banco
BANCO = r"C:\Users\paulo.herrera\VIC\VIC - HOLDING OPERACIONAL\Mobilidade Frota - VicCorp\Paulo - Pessoal\SQL - e-Frotas\Frota.db"

# Conectar
conn = sqlite3.connect(BANCO)
cursor = conn.cursor()

# Dados de teste
placa = "ABC1D23"
data_autuacao = "2026-09-30"
numero_ait = "AIT0002"
valor = 250.75
status = "Nova"
pdf_path = r"PDFs\ABC1D23_AIT0002.pdf"

# Inserir
cursor.execute("""
INSERT INTO Multas
(
    Placa,
    Dataautuacao,
    NumeroAIT,
    Valor,
    Status,
    PdfPath
)
VALUES (?, ?, ?, ?, ?, ?)
""", (
    placa,
    data_autuacao,
    numero_ait,
    valor,
    status,
    pdf_path
))

conn.commit()
conn.close()

print("Multa gravada com sucesso!")