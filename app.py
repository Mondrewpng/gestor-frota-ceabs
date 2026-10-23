from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"


def conectar():
    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():

    conn = conectar()

    total_alarmes = conn.execute("""
        SELECT COUNT(*)
        FROM tb_safe_alarmes
    """).fetchone()[0]

    total_veiculos = conn.execute("""
        SELECT COUNT(*)
        FROM tb_safe_veiculos
    """).fetchone()[0]

    total_tipos = conn.execute("""
        SELECT COUNT(*)
        FROM tb_safe_tipos_alarme
    """).fetchone()[0]

    ultimos = conn.execute("""
        SELECT
            a.placa,
            t.descricao,
            a.data_hora,
            a.nivel_risco
        FROM tb_safe_alarmes a
        INNER JOIN tb_safe_tipos_alarme t
            ON a.codigo_alarme = t.codigo_alarme
        ORDER BY a.id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_alarmes=total_alarmes,
        total_veiculos=total_veiculos,
        total_tipos=total_tipos,
        ultimos=ultimos
    )


if __name__ == "__main__":
    app.run(debug=True)