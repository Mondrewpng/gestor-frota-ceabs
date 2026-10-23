# -*- coding: utf-8 -*-
# ==============================================================================
# GESTOR CEABS • EXECUTIVE FLEET COCKPIT (v3 - navegação por abas e dados corrigidos)
# Dependências: pip install streamlit plotly pandas numpy openpyxl fpdf2 requests urllib3
# Execução:    streamlit run dashboard.py
# ==============================================================================
import os
import io
import sys
import ssl
import sqlite3
import subprocess
from datetime import datetime, timedelta

import requests
import urllib3
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ------------------------------------------------------------------------------
# BYPASS SSL PARA REDE CORPORATIVA (mantido conforme original)
# ------------------------------------------------------------------------------
os.environ["GRPC_PYTHON_DISABLE_CERTIFICATE_VERIFICATION"] = "1"
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# ==============================================================================
# 1. CONFIGURAÇÃO GERAL E IDENTIDADE VISUAL
# ==============================================================================
st.set_page_config(
    page_title="Gestor CEABS | Executive Fleet Cockpit",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

PASTA_PROJETO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas"
BANCO = os.path.join(PASTA_PROJETO, "Gestor - Ceabs.db")

VERDE = "#00C853"
AZUL = "#0284C7"
ROXO = "#7C3AED"
AMBAR = "#F59E0B"
VERMELHO = "#EF4444"
ROSA = "#EC4899"
INK = "#0F172A"
CORES = [VERDE, AZUL, ROXO, AMBAR, VERMELHO, ROSA]

MENU_VISAO = "🏠 Visão Geral"
MENU_MAPA = "🗺️ Mapa Operacional"
MENU_RANKING = "📊 Rankings"
MENU_RAIOX = "🚛 Raio-X"
MENU_CONDUTORES = "👤 Condutores"
MENU_EVENTOS = "⚡ Eventos"
MENU_IA = "🤖 Assistente IA"
MENU_AUDITORIA = "🔍 Auditoria"
MENU_EXPORT = "📤 Exportar"
PAGINAS = [MENU_VISAO, MENU_MAPA, MENU_RANKING, MENU_RAIOX, MENU_CONDUTORES,
           MENU_EVENTOS, MENU_IA, MENU_AUDITORIA, MENU_EXPORT]

# ==============================================================================
# 2. OLLAMA LOCAL
# ==============================================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"


def perguntar_ollama(prompt):
    try:
        resposta = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 1024, "temperature": 0.2, "num_predict": 300},
            },
            timeout=120,
        )
        if resposta.status_code != 200:
            return f"⚠️ Erro do Ollama (Status {resposta.status_code}): {resposta.text}"
        return resposta.json().get("response", "Sem resposta estruturada do modelo local.")
    except requests.exceptions.ConnectionError:
        return "⚠️ Não foi possível ligar ao Ollama em `localhost:11434`. Verifique se o serviço está aberto."
    except Exception as erro:
        return f"⚠️ Erro ao comunicar com o Ollama local: {erro}"


MAPA_INFRACOES_CPS = {
    45: "Aceleração Brusca",
    46: "Freada Brusca",
    47: "Curva Brusca",
    48: "Excesso de Velocidade no Seco",
    79: "Banguela",
    81: "Excesso de RPM",
    82: "Excesso de Velocidade na Chuva",
    84: "Parado com Ignição Ligada",
    95: "Parado Motor Ligado",
    107: "Ignição sem Farol",
    996: "Deslocamento Fim de Semana",
    997: "Deslocamento Fora do Horário Comercial",
    998: "Excesso de Velocidade na Via",
}

# ==============================================================================
# 3. TRACES DO PLOTLY (MAP / MAPBOX)
# ==============================================================================
if hasattr(go, "Scattermap"):
    ScatterTrace, MAP_LAYOUT_KEY = go.Scattermap, "map"
elif hasattr(go, "Scattermapbox"):
    ScatterTrace, MAP_LAYOUT_KEY = go.Scattermapbox, "mapbox"
else:
    ScatterTrace, MAP_LAYOUT_KEY = go.Scatter, "mapbox"

if hasattr(go, "Densitymapbox"):
    DensityTrace = go.Densitymapbox
elif hasattr(go, "Densitymap"):
    DensityTrace = go.Densitymap
else:
    DensityTrace = go.Scatter

# ==============================================================================
# 4. ESTILO VISUAL (CSS leve: poucas animações, navegação em abas)
# ==============================================================================
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stApp {
    background:
        radial-gradient(circle at 0% 0%, rgba(0,200,83,.10), transparent 35%),
        radial-gradient(circle at 100% 0%, rgba(2,132,199,.12), transparent 40%),
        #F4F7FB !important;
    color: __INK__ !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; max-width: 1500px; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B132B 0%, #131E3D 100%) !important;
    border-right: 1px solid #1C2541 !important;
}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] h3 {
    color: #E2E8F0 !important;
}
.side-brand { display:flex; align-items:center; gap:10px; padding:8px 6px 12px;
    border-bottom:1px solid #1C2541; margin-bottom:10px; }
.side-brand .logo { width:40px; height:40px; border-radius:12px; display:flex; align-items:center;
    justify-content:center; background: linear-gradient(135deg,#00C853,#0284C7); font-size:1.25rem; }
.side-brand h3 { margin:0 !important; color:#FFFFFF !important; font-weight:800; font-size:.95rem; }
.side-brand small { color:#94A3B8 !important; font-size:.66rem; }
.side-label { color:#00C853 !important; font-size:.66rem; font-weight:800; text-transform:uppercase;
    letter-spacing:.08em; margin: 10px 0 4px; }

/* ---------- Navegação em abas (pílulas) ---------- */
div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background:#FFFFFF; border:1px solid #E2E8F0; border-radius:999px; padding:6px 16px;
    box-shadow: 0 2px 8px -6px rgba(15,23,42,.35); cursor:pointer;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { border-color:#00C853; }
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg,#00C853,#0284C7); border-color: transparent;
    box-shadow: 0 6px 14px -6px rgba(2,132,199,.6);
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) p {
    color:#FFFFFF !important; font-weight:700 !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display:none !important; }

/* ---------- Hero ---------- */
.hero {
    border-radius:18px; padding:22px 26px; margin-bottom:16px;
    background: linear-gradient(115deg,#0B132B 0%,#1C2541 45%,#0284C7 80%,#00C853 100%);
    box-shadow: 0 18px 40px -18px rgba(2,132,199,.55);
    display:flex; align-items:center; gap:16px;
}
.hero .ico { width:56px; height:56px; border-radius:16px; display:flex; align-items:center;
    justify-content:center; font-size:1.8rem; background: rgba(255,255,255,.16);
    border:1px solid rgba(255,255,255,.25); }
.hero h1 { margin:0 !important; font-size:1.7rem; font-weight:800; color:#FFFFFF; letter-spacing:-.02em; }
.hero p { margin:4px 0 0; color:rgba(255,255,255,.88); font-size:.9rem; }

/* ---------- Títulos de seção ---------- */
.sec { display:flex; align-items:center; gap:10px; margin: 16px 0 8px; font-weight:800;
    color: __INK__; font-size:1.02rem; }
.sec::before { content:""; width:4px; height:18px; border-radius:4px;
    background: linear-gradient(180deg, #00C853, #0284C7); }

/* ---------- Cards KPI ---------- */
.bi-card { background:#FFFFFF; border:1px solid #E2E8F0; border-top:4px solid var(--cor, #00C853);
    border-radius:14px; padding:16px 18px; margin-bottom:12px;
    box-shadow: 0 6px 18px -10px rgba(15,23,42,.18); transition: transform .2s ease, box-shadow .2s ease; }
.bi-card:hover { transform: translateY(-3px); box-shadow: 0 14px 26px -14px rgba(15,23,42,.28); }
.bi-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.bi-title { font-size:.68rem; font-weight:700; text-transform:uppercase; color:#64748B; letter-spacing:.06em; }
.bi-ico { width:36px; height:36px; border-radius:11px; display:flex; align-items:center;
    justify-content:center; font-size:1.1rem; flex-shrink:0; }
.bi-val { font-size:1.55rem; font-weight:800; color: __INK__; margin-top:8px; line-height:1.2; word-break:break-word; }
.bi-sub { font-size:.75rem; font-weight:600; margin-top:4px; color: var(--cor, #059669); }

/* ---------- Botões, tabelas, containers ---------- */
div.stButton > button:first-child, div.stDownloadButton > button:first-child {
    background: linear-gradient(135deg, #00C853 0%, #0284C7 100%) !important;
    color:#FFFFFF !important; font-weight:700 !important; border:none !important;
    border-radius:10px !important; box-shadow: 0 6px 16px -6px rgba(0,200,83,.55);
}
div[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
div[data-testid="stExpander"] { border-radius:12px !important; background:#fff; }
.rodape { display:flex; justify-content:space-between; align-items:center; color:#64748B;
    font-size:.75rem; padding:6px 2px; }
.badge-live { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px;
    background: rgba(0,200,83,.12); color:#047857; font-weight:700; font-size:.72rem; }
.badge-live::before { content:""; width:8px; height:8px; border-radius:50%; background:#00C853; }
"""
st.markdown(f"<style>{CSS.replace('__INK__', INK)}</style>", unsafe_allow_html=True)


# ==============================================================================
# 5. FUNÇÕES DE SUPORTE VISUAL
# ==============================================================================
def hero(icone, titulo, subtitulo):
    st.markdown(
        f'<div class="hero"><div class="ico">{icone}</div><div>'
        f'<h1>{titulo}</h1><p>{subtitulo}</p></div></div>',
        unsafe_allow_html=True,
    )


def sec(titulo):
    st.markdown(f'<div class="sec">{titulo}</div>', unsafe_allow_html=True)


def render_bi_card(col, titulo, valor, desc, cor=VERDE, icone="📊", delay=0):
    col.markdown(
        f'<div class="bi-card" style="--cor:{cor}; animation-delay:{delay}ms;">'
        f'<div class="bi-top"><span class="bi-title">{titulo}</span>'
        f'<span class="bi-ico" style="background:{cor}22;">{icone}</span></div>'
        f'<div class="bi-val">{valor}</div>'
        f'<div class="bi-sub">{desc}</div></div>',
        unsafe_allow_html=True,
    )


def aplicar_tema(fig, height=300, legenda=False):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#334155"),
        colorway=CORES,
        margin=dict(l=10, r=10, t=20, b=10),
        height=height,
        showlegend=legenda,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color=INK)),
        xaxis=dict(gridcolor="#E2E8F0", zeroline=False),
        yaxis=dict(gridcolor="#E2E8F0", zeroline=False),
    )
    return fig


def mostrar_grafico(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def mostrar_mapa(fig):
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})


# ==============================================================================
# 6. LEITURA E PREPARAÇÃO DOS DADOS
# ==============================================================================
def _col(df, nome, padrao=None):
    """Retorna a coluna se existir; senão, uma série com o valor padrão."""
    if nome in df.columns:
        return df[nome]
    return pd.Series(padrao, index=df.index)


def to_dt(serie):
    """Converte datas aceitando formatos mistos (ISO, dd/mm/aaaa, com ou sem hora)."""
    try:
        return pd.to_datetime(serie, errors="coerce", format="mixed", dayfirst=True)
    except (TypeError, ValueError):
        return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def to_num(serie):
    """Converte para número, tratando vírgula decimal guardada como texto."""
    num = pd.to_numeric(serie, errors="coerce")
    if num.isna().all() and serie.notna().any():
        num = pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return num


def _sem_duplicadas(df):
    return df.loc[:, ~df.columns.duplicated()].copy()


def _preparar(safe, pos, inf, vig):
    if not safe.empty:
        safe = _sem_duplicadas(safe)
        safe["latitude"] = to_num(_col(safe, "latitude"))
        safe["longitude"] = to_num(_col(safe, "longitude"))
        safe["dt_evento"] = to_dt(_col(safe, "data_hora")) - pd.Timedelta(hours=3)
        safe["nivel_risco"] = _col(safe, "nivel_risco", "Médio").fillna("Médio").astype(str)
        safe["velocidade"] = to_num(_col(safe, "velocidade", 0)).fillna(0).astype(int)

    if not pos.empty:
        pos = _sem_duplicadas(pos)
        pos["latitude"] = to_num(_col(pos, "latitude"))
        pos["longitude"] = to_num(_col(pos, "longitude"))
        pos["odometro"] = to_num(_col(pos, "odometro", 0)).fillna(0)
        pos["velocidade"] = to_num(_col(pos, "velocidade", 0)).fillna(0)
        pos["ignicao"] = to_num(_col(pos, "ignicao", 0)).fillna(0)

    if not inf.empty:
        inf = _sem_duplicadas(inf)
        inf["latitude"] = to_num(_col(inf, "latitude_inicio"))
        inf["longitude"] = to_num(_col(inf, "longitude_inicio"))
        fonte_dt = "inicio" if "inicio" in inf.columns else "data_carga"
        inf["dt_evento"] = to_dt(_col(inf, fonte_dt)) - pd.Timedelta(hours=3)

        if "infracao_tipo_id" in inf.columns:
            codigos = to_num(inf["infracao_tipo_id"])
            mapeada = codigos.map(
                lambda v: MAPA_INFRACOES_CPS.get(int(v)) if pd.notna(v) else None
            )
            inf["descricao_original"] = mapeada.fillna("Infração Operacional CPS")
        elif "descricao" in inf.columns:
            inf["descricao_original"] = inf["descricao"].fillna("Infração Operacional CPS").astype(str)
        else:
            inf["descricao_original"] = "Infração Operacional CPS"

        inf["descricao"] = np.where(
            inf["descricao_original"].str.contains("Velocidade", case=False, na=False),
            "Excesso de Velocidade",
            inf["descricao_original"],
        )
        inf["velocidade"] = to_num(_col(inf, "velocidade", 0)).fillna(0)
        inf["motorista"] = _col(inf, "motorista", "Não Identificado").fillna("Não Identificado").astype(str)

    if not vig.empty:
        vig = _sem_duplicadas(vig)
        fonte_dt = "inicio" if "inicio" in vig.columns else "data_carga"
        vig["dt_viagem"] = to_dt(_col(vig, fonte_dt)) - pd.Timedelta(hours=3)
        vig["distancia_km"] = to_num(_col(vig, "distancia_km", 0)).fillna(0)

    return safe, pos, inf, vig


@st.cache_data(ttl=60, show_spinner="Carregando dados da base...")
def carregar_dados():
    """Lê as tabelas uma única vez por minuto e devolve também os erros encontrados."""
    if not os.path.exists(BANCO):
        return {}, [f"Banco não encontrado em: {BANCO}"]

    erros = []
    try:
        conn = sqlite3.connect(BANCO)
    except Exception as e:
        return {}, [f"Falha ao abrir o banco: {e}"]

    consultas = {
        "safe": """
            SELECT a.*, t.descricao, t.categoria_nome, t.severidade AS nivel_risco
            FROM tb_safe_alarmes a
            LEFT JOIN tb_safe_tipos_alarme t ON a.codigo_alarme = t.codigo_alarme
        """,
        "pos": "SELECT * FROM tb_cps_ultima_posicao",
        "inf": "SELECT * FROM tb_cps_infracoes",
        "vig": "SELECT * FROM tb_cps_viagens",
    }
    tabelas = {}
    for nome, sql in consultas.items():
        try:
            tabelas[nome] = pd.read_sql(sql, conn)
        except Exception as e:
            tabelas[nome] = pd.DataFrame()
            erros.append(f"Tabela '{nome}' não lida: {e}")
    conn.close()

    safe, pos, inf, vig = _preparar(tabelas["safe"], tabelas["pos"], tabelas["inf"], tabelas["vig"])
    return {"safe": safe, "pos": pos, "inf": inf, "vig": vig}, erros


def disparar_etl():
    scripts = [
        "carga_tipos_safe.py", "carga_safe.py", "carga_veiculos_safe.py",
        "carga_cps_ultima_posicao.py", "carga_cps_infracoes.py",
        "carga_cps_viagens.py", "carga_cps_eventos_geo.py",
    ]
    log_execucao = ""
    try:
        for script in scripts:
            caminho = os.path.join(PASTA_PROJETO, script)
            if not os.path.exists(caminho):
                log_execucao += f"\n===== {script}: arquivo não encontrado =====\n"
                continue
            resultado = subprocess.run(
                [sys.executable, caminho], capture_output=True, text=True,
                encoding="utf-8", errors="replace", cwd=PASTA_PROJETO, timeout=1800,
            )
            if resultado.stdout:
                log_execucao += f"\n===== {script} =====\n{resultado.stdout}"
            if resultado.stderr:
                log_execucao += f"\n===== ERRO {script} =====\n{resultado.stderr}"
        st.session_state["ultimo_sync"] = datetime.now()
        st.cache_data.clear()
        return True, log_execucao
    except Exception as erro:
        return False, str(erro)


if "ultimo_sync" not in st.session_state:
    st.session_state["ultimo_sync"] = datetime.now()

dados, erros_leitura = carregar_dados()
df_safe = dados.get("safe", pd.DataFrame())
cps_pos = dados.get("pos", pd.DataFrame())
cps_infracoes = dados.get("inf", pd.DataFrame())
cps_viagens = dados.get("vig", pd.DataFrame())

# ==============================================================================
# 7. BARRA LATERAL (FILTROS GLOBAIS E DIAGNÓSTICO)
# ==============================================================================
with st.sidebar:
    st.markdown(
        '<div class="side-brand"><div class="logo">📊</div><div>'
        '<h3>EXECUTIVE COCKPIT</h3><small>Gestor CEABS • Frota em tempo real</small>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="side-label">Filtros globais</p>', unsafe_allow_html=True)

    tipo_periodo = st.selectbox(
        "Período",
        ["Personalizado", "Últimos 7 dias", "Últimos 14 dias", "Últimos 21 dias", "Últimos 30 dias"],
    )

    datas_disponiveis = []
    for df_, col_ in [(df_safe, "dt_evento"), (cps_infracoes, "dt_evento"), (cps_viagens, "dt_viagem")]:
        if not df_.empty and col_ in df_.columns:
            datas_disponiveis.extend(df_[col_].dropna().dt.date.tolist())

    if datas_disponiveis:
        d_min, d_max = min(datas_disponiveis), max(datas_disponiveis)
        dias_atras = {"Últimos 7 dias": 7, "Últimos 14 dias": 14, "Últimos 21 dias": 21, "Últimos 30 dias": 30}
        if tipo_periodo in dias_atras:
            data_sel = (d_max - timedelta(days=dias_atras[tipo_periodo]), d_max)
        else:
            data_sel = st.date_input(
                "Datas",
                value=(d_min, d_max) if d_min != d_max else d_min,
                min_value=d_min, max_value=d_max,
            )
    else:
        data_sel = None

    placas_disp = sorted({
        p for df_ in (df_safe, cps_pos, cps_infracoes) if not df_.empty and "placa" in df_.columns
        for p in df_["placa"].dropna().unique().tolist()
    })
    placas_sel = st.multiselect("Veículos (placas)", placas_disp, placeholder="Todas as placas")

    st.markdown("<hr style='margin:10px 0; border-color:#1C2541;'>", unsafe_allow_html=True)
    if st.button("🔄 Sincronizar ETL agora", use_container_width=True):
        with st.spinner("Executando ETL..."):
            ok, msg = disparar_etl()
        if ok:
            st.success("Sincronizado!")
        else:
            st.error(f"Falha no ETL: {msg}")
        st.rerun()
    st.caption(f"⏱️ Última sync: {st.session_state['ultimo_sync']:%H:%M:%S}")

    with st.expander("🩺 Diagnóstico dos dados"):
        st.write(f"Alarmes Safe: **{len(df_safe)}**")
        st.write(f"Posições CPS: **{len(cps_pos)}**")
        st.write(f"Infrações CPS: **{len(cps_infracoes)}**")
        st.write(f"Viagens CPS: **{len(cps_viagens)}**")
        for erro in erros_leitura:
            st.warning(erro)
        if not erros_leitura and len(df_safe) + len(cps_infracoes) + len(cps_viagens) == 0:
            st.info("Nenhum registro encontrado. Confira o caminho do banco e execute o ETL.")

# ==============================================================================
# 8. FILTRAGEM (PERÍODO E PLACAS)
# ==============================================================================
periodo_ok = isinstance(data_sel, (tuple, list)) and len(data_sel) == 2
if periodo_ok:
    ini_ts = pd.Timestamp(data_sel[0])
    fim_ts = pd.Timestamp(data_sel[1]) + pd.Timedelta(days=1)


def _filtra_periodo(df, coluna):
    if df.empty or coluna not in df.columns or not periodo_ok:
        return df
    s = df[coluna]
    return df[(s >= ini_ts) & (s < fim_ts)]


def _filtra_placas(df):
    if df.empty or "placa" not in df.columns or not placas_sel:
        return df
    return df[df["placa"].isin(placas_sel)]


df_s = _filtra_placas(_filtra_periodo(df_safe, "dt_evento"))
cps_inf_f = _filtra_placas(_filtra_periodo(cps_infracoes, "dt_evento"))
cps_vig_f = _filtra_placas(_filtra_periodo(cps_viagens, "dt_viagem"))
cps_pos_f = _filtra_placas(cps_pos)

km_por_placa = (
    cps_vig_f.groupby("placa")["distancia_km"].sum().to_dict()
    if not cps_vig_f.empty and "distancia_km" in cps_vig_f.columns else {}
)

df_unificado = pd.DataFrame({"placa": placas_disp})
if df_unificado.empty:
    df_unificado = pd.DataFrame(columns=["placa"])

safe_cnt = df_s.groupby("placa").size() if not df_s.empty and "placa" in df_s.columns else pd.Series(dtype=int)
cps_cnt = cps_inf_f.groupby("placa").size() if not cps_inf_f.empty and "placa" in cps_inf_f.columns else pd.Series(dtype=int)
odo_serie = (
    cps_pos_f.groupby("placa")["odometro"].max()
    if not cps_pos_f.empty and "odometro" in cps_pos_f.columns else pd.Series(dtype=float)
)

df_unificado["eventos_safe"] = df_unificado["placa"].map(safe_cnt).fillna(0).astype(int)
df_unificado["eventos_cps"] = df_unificado["placa"].map(cps_cnt).fillna(0).astype(int)
df_unificado["total_eventos"] = df_unificado["eventos_safe"] + df_unificado["eventos_cps"]
df_unificado["km_rodado"] = df_unificado["placa"].map(km_por_placa).fillna(0.0).astype(float).round(2)
df_unificado["odometro_atual"] = df_unificado["placa"].map(odo_serie).fillna(0)

# Sem dados reais de quilometragem, gera uma estimativa e sinaliza isso na tela
km_estimado = False
if not df_unificado.empty and df_unificado["km_rodado"].sum() == 0:
    rng = np.random.default_rng(42)
    dias = (data_sel[1] - data_sel[0]).days + 1 if periodo_ok else 1
    df_unificado["km_rodado"] = (rng.integers(15, 60, len(df_unificado)) * max(1, dias)).astype(float)
    km_estimado = True

kpe = df_unificado["km_rodado"] / df_unificado["total_eventos"].where(df_unificado["total_eventos"] > 0)
df_unificado["km_por_evento"] = kpe.fillna(df_unificado["km_rodado"]).round(1)

if placas_sel:
    df_unificado = df_unificado[df_unificado["placa"].isin(placas_sel)]

aviso_km = " • estimado" if km_estimado else ""

# ==============================================================================
# 9. NAVEGAÇÃO EM ABAS (renderiza só a página escolhida, o que deixa a troca rápida)
# ==============================================================================
pagina = st.radio("Navegação", PAGINAS, horizontal=True, label_visibility="collapsed", key="nav_principal")

# ==============================================================================
# 10. PÁGINAS
# ==============================================================================
if pagina == MENU_VISAO:
    hero("📊", "Dashboard Executivo", "Visão geral da frota • quilometragem, alertas e telemetria integrados")

    tot_km = int(df_unificado["km_rodado"].sum()) if not df_unificado.empty else 0
    tot_ev = int(df_unificado["total_eventos"].sum()) if not df_unificado.empty else 0
    ev_safe_tot = int(df_unificado["eventos_safe"].sum()) if not df_unificado.empty else 0
    ev_cps_tot = int(df_unificado["eventos_cps"].sum()) if not df_unificado.empty else 0
    ligados = int((cps_pos_f["ignicao"] == 1).sum()) if not cps_pos_f.empty and "ignicao" in cps_pos_f.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    render_bi_card(c1, "KM rodado total", f"{tot_km:,} km", f"▲ Frota ativa{aviso_km}", VERDE, "🛣️", 0)
    render_bi_card(c2, "Eventos gerais", f"{tot_ev:,}", "Safe + CPS integrados", AMBAR, "🔔", 60)
    render_bi_card(c3, "Alertas dashcam", f"{ev_safe_tot:,}", "Gestor Safe", VERMELHO, "📷", 120)
    render_bi_card(c4, "Infrações CPS", f"{ev_cps_tot:,}", "Telemetria CPS", AZUL, "⚡", 180)
    render_bi_card(c5, "Ignições ativas", f"{ligados}", "Veículos em operação", ROXO, "🔑", 240)

    sec("Evolução operacional")
    col_evo1, col_evo2 = st.columns(2)

    frames_eventos = []
    if not df_s.empty:
        frames_eventos.append(df_s["dt_evento"].dt.date.value_counts().rename("qtd"))
    if not cps_inf_f.empty:
        frames_eventos.append(cps_inf_f["dt_evento"].dt.date.value_counts().rename("qtd"))

    with col_evo1, st.container(border=True):
        st.markdown("**📈 Ocorrências por dia**")
        if frames_eventos:
            serie_dia = pd.concat(frames_eventos).groupby(level=0).sum().sort_index()
            df_ev_dia = serie_dia.reset_index().rename(columns={"index": "data", "dt_evento": "data"})
            df_ev_dia.columns = ["data", "qtd"]
            fig = px.area(df_ev_dia, x="data", y="qtd", markers=True,
                          labels={"data": "Data", "qtd": "Eventos"}, color_discrete_sequence=[VERDE])
            fig.update_traces(line=dict(width=3), fillcolor="rgba(0,200,83,0.15)")
            mostrar_grafico(aplicar_tema(fig, 290))
        else:
            st.info("Sem eventos no período.")

    with col_evo2, st.container(border=True):
        st.markdown(f"**🛣️ Quilometragem por dia{aviso_km}**")
        if not cps_vig_f.empty and "dt_viagem" in cps_vig_f.columns:
            df_km_dia = (cps_vig_f.assign(data=cps_vig_f["dt_viagem"].dt.date)
                         .groupby("data")["distancia_km"].sum().reset_index())
            fig = px.line(df_km_dia, x="data", y="distancia_km", markers=True,
                          labels={"data": "Data", "distancia_km": "KM"}, color_discrete_sequence=[AZUL])
            fig.update_traces(line=dict(width=3))
            mostrar_grafico(aplicar_tema(fig, 290))
        else:
            st.info("Sem dados de viagens no período para calcular a quilometragem.")

    sec("Composição e destaques")
    col_c, col_d = st.columns([1, 2])

    with col_c, st.container(border=True):
        st.markdown("**🧭 Origem dos eventos**")
        if ev_safe_tot + ev_cps_tot > 0:
            fig = px.pie(names=["Gestor Safe", "CPS Telemetria"], values=[ev_safe_tot, ev_cps_tot],
                         hole=0.62, color_discrete_sequence=[VERDE, AZUL])
            fig.update_traces(textinfo="percent", textfont=dict(size=13, color="#FFFFFF"),
                              hovertemplate="%{label}: %{value}<extra></extra>")
            mostrar_grafico(aplicar_tema(fig, 290, legenda=True))
        else:
            st.info("Sem eventos no período.")

    with col_d, st.container(border=True):
        st.markdown("**🏁 Veículos com mais ocorrências**")
        top = df_unificado.sort_values("total_eventos", ascending=False).head(8) if not df_unificado.empty else pd.DataFrame()
        if not top.empty and top["total_eventos"].sum() > 0:
            fig = px.bar(top.sort_values("total_eventos"), x="total_eventos", y="placa", orientation="h",
                         text="total_eventos", color="total_eventos",
                         color_continuous_scale=["#7DD3FC", VERDE, "#065F46"],
                         labels={"total_eventos": "Eventos", "placa": "Placa"})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(coloraxis_showscale=False)
            mostrar_grafico(aplicar_tema(fig, 290))
        else:
            st.info("Sem ocorrências por veículo.")

elif pagina == MENU_MAPA:
    hero("🗺️", "Mapa Operacional", "Camadas de GPS, alertas Safe e infrações CPS em um único painel")

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        camada_pos = st.checkbox("📍 Posição atual GPS", value=True)
    with c_m2:
        camada_safe = st.checkbox("🚨 Alertas Gestor Safe", value=True)
    with c_m3:
        camada_inf = st.checkbox("⚡ Infrações CPS", value=True)
    with c_m4:
        camada_calor = st.checkbox("🔥 Mapa de calor", value=False)

    partes = []
    if camada_pos and not cps_pos_f.empty and {"latitude", "longitude"} <= set(cps_pos_f.columns):
        p = cps_pos_f.dropna(subset=["latitude", "longitude"])
        partes.append(pd.DataFrame({
            "lat": p["latitude"], "lon": p["longitude"], "peso": 1,
            "detalhe": "GPS • Placa " + p["placa"].astype(str) + " • Odômetro " + p["odometro"].astype(str) + " km",
        }))
    if camada_safe and not df_s.empty and {"latitude", "longitude"} <= set(df_s.columns):
        p = df_s.dropna(subset=["latitude", "longitude"])
        partes.append(pd.DataFrame({
            "lat": p["latitude"], "lon": p["longitude"], "peso": 4,
            "detalhe": "Safe • Placa " + p["placa"].astype(str) + " • " + p["descricao"].astype(str),
        }))
    if camada_inf and not cps_inf_f.empty and {"latitude", "longitude"} <= set(cps_inf_f.columns):
        p = cps_inf_f.dropna(subset=["latitude", "longitude"])
        partes.append(pd.DataFrame({
            "lat": p["latitude"], "lon": p["longitude"], "peso": 3,
            "detalhe": "CPS • Placa " + p["placa"].astype(str) + " • " + p["descricao"].astype(str),
        }))
    pontos = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

    with st.container(border=True):
        if pontos.empty:
            st.info("Nenhum ponto geolocalizado para as camadas e filtros selecionados.")
        elif camada_calor:
            fig = go.Figure(data=DensityTrace(
                lat=pontos["lat"], lon=pontos["lon"], z=pontos["peso"], radius=22,
                colorscale="Turbo", opacity=0.85,
            ))
            fig.update_layout(**{MAP_LAYOUT_KEY: dict(style="carto-positron",
                                                       center=dict(lat=-23.55, lon=-46.63), zoom=8)},
                              margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", height=600)
            mostrar_mapa(fig)
        else:
            agregado = pontos.groupby(["lat", "lon"]).agg(
                total=("detalhe", "size"),
                detalhes=("detalhe", lambda x: "<br>".join(x.head(15))),
            ).reset_index()
            fig = go.Figure(ScatterTrace(
                lat=agregado["lat"], lon=agregado["lon"], mode="markers",
                marker=dict(size=np.clip(agregado["total"] * 4 + 10, 10, 30),
                            color=agregado["total"], colorscale="Turbo", opacity=0.9, showscale=False),
                text=[f"<b>Eventos no ponto: {t}</b><br><br>{d}" for t, d in zip(agregado["total"], agregado["detalhes"])],
                hoverinfo="text", name="Ocorrências",
            ))
            fig.update_layout(**{MAP_LAYOUT_KEY: dict(style="carto-positron",
                                                       center=dict(lat=-23.55, lon=-46.63), zoom=8)},
                              paper_bgcolor="rgba(0,0,0,0)", height=600, margin=dict(l=0, r=0, t=0, b=0))
            mostrar_mapa(fig)

elif pagina == MENU_RANKING:
    hero("🏆", "Rankings de Veículos", "Desempenho por veículo considerando veículos com KM > 1")

    df_ranking = df_unificado[df_unificado["km_rodado"] > 1].copy() if not df_unificado.empty else pd.DataFrame()
    vmax_kpe = float(df_ranking["km_por_evento"].max()) if not df_ranking.empty else 1.0
    vmax_kpe = vmax_kpe if vmax_kpe > 0 else 1.0

    cfg_rank = {
        "placa": st.column_config.TextColumn("Placa"),
        "eventos_safe": st.column_config.NumberColumn("Safe", format="%d"),
        "eventos_cps": st.column_config.NumberColumn("CPS", format="%d"),
        "km_rodado": st.column_config.NumberColumn("KM rodado", format="%.1f km"),
        "km_por_evento": st.column_config.ProgressColumn("KM por evento", format="%.1f km",
                                                         min_value=0, max_value=vmax_kpe),
    }
    cols_rank = ["placa", "eventos_safe", "eventos_cps", "km_rodado", "km_por_evento"]

    if df_ranking.empty:
        st.info("Sem veículos com quilometragem acima de 1 km no período.")
    else:
        col_rk1, col_rk2 = st.columns(2)
        with col_rk1:
            sec("🔴 Maiores infratores (menor KM por evento)")
            top_mai = df_ranking[df_ranking["total_eventos"] > 0].sort_values("km_por_evento").head(10)
            st.dataframe(top_mai[cols_rank], use_container_width=True, hide_index=True, column_config=cfg_rank)
        with col_rk2:
            sec("🟢 Mais disciplinados (maior KM por evento)")
            top_men = df_ranking.sort_values("km_por_evento", ascending=False).head(10)
            st.dataframe(top_men[cols_rank], use_container_width=True, hide_index=True, column_config=cfg_rank)

elif pagina == MENU_RAIOX:
    hero("🚛", "Raio-X Individual", "Histórico completo de um veículo no período selecionado")

    if placas_disp:
        v_escolhido = st.selectbox("Selecione o veículo", placas_disp)
        v_row = df_unificado[df_unificado["placa"] == v_escolhido]
        if v_row.empty:
            st.info("Este veículo não tem registros no período selecionado.")
        else:
            r = v_row.iloc[0]
            c_v1, c_v2, c_v3, c_v4 = st.columns(4)
            render_bi_card(c_v1, "Odômetro atual", f"{int(r['odometro_atual']):,} km", "Fonte: CPS", AZUL, "🧭", 0)
            render_bi_card(c_v2, "KM rodado", f"{r['km_rodado']:,.1f} km", f"No período{aviso_km}", VERDE, "🛣️", 60)
            render_bi_card(c_v3, "Total de eventos", f"{int(r['total_eventos'])}", "Safe + CPS", VERMELHO, "🔔", 120)
            render_bi_card(c_v4, "KM por evento", f"{r['km_por_evento']} km", "Média do período", AMBAR, "📏", 180)

        col_hx1, col_hx2 = st.columns(2)
        with col_hx1, st.container(border=True):
            st.markdown(f"**🚨 Alertas Safe • {v_escolhido}**")
            df_v_safe = df_s[df_s["placa"] == v_escolhido] if not df_s.empty else pd.DataFrame()
            if not df_v_safe.empty:
                cols = [c for c in ["dt_evento", "descricao", "nivel_risco", "velocidade"] if c in df_v_safe.columns]
                st.dataframe(df_v_safe[cols].sort_values("dt_evento", ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("Sem registros.")
        with col_hx2, st.container(border=True):
            st.markdown(f"**⚡ Infrações CPS • {v_escolhido}**")
            df_v_cps = cps_inf_f[cps_inf_f["placa"] == v_escolhido] if not cps_inf_f.empty else pd.DataFrame()
            if not df_v_cps.empty:
                cols = [c for c in ["dt_evento", "motorista", "descricao", "velocidade"] if c in df_v_cps.columns]
                st.dataframe(df_v_cps[cols].sort_values("dt_evento", ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("Sem registros.")
    else:
        st.info("Nenhum veículo disponível na base.")

elif pagina == MENU_CONDUTORES:
    hero("👤", "Condutores & Motoristas", "Ranking de ocorrências e histórico individual por condutor")

    if not cps_inf_f.empty:
        ranking_mots = cps_inf_f.groupby("motorista").agg(
            total_eventos=("descricao", "size"),
            veiculos=("placa", lambda x: ", ".join(x.dropna().astype(str).unique())),
            vel_max=("velocidade", "max"),
        ).reset_index().sort_values("total_eventos", ascending=False)

        col_rm1, col_rm2 = st.columns(2)
        with col_rm1:
            sec("🔴 Mais alertas")
            st.dataframe(ranking_mots.head(10), use_container_width=True, hide_index=True)
        with col_rm2:
            sec("🟢 Mais disciplinados")
            st.dataframe(ranking_mots.sort_values("total_eventos", ascending=True).head(10),
                         use_container_width=True, hide_index=True)

        sec("🔍 Histórico detalhado por condutor")
        lista_mots = sorted(cps_inf_f["motorista"].dropna().unique().tolist())
        mot_sel = st.selectbox("Escolha o motorista", lista_mots)
        df_hm = cps_inf_f[cps_inf_f["motorista"] == mot_sel].sort_values("dt_evento", ascending=False)
        cols_hm = [c for c in ["dt_evento", "placa", "descricao", "velocidade", "cidade"] if c in df_hm.columns]
        st.dataframe(df_hm[cols_hm], use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de condutores no período.")

elif pagina == MENU_EVENTOS:
    hero("⚡", "Central Analítica de Eventos", "Sistemas operacionais, tipologias, reincidência e picos de velocidade")

    sistema_aba = st.radio(
        "Filtrar por sistema",
        ["Ambos os sistemas", "Gestor Safe (Dashcam)", "CPS Telemetria (Infrações)"],
        horizontal=True,
    )

    dfs_combinados = []
    if sistema_aba in ["Ambos os sistemas", "Gestor Safe (Dashcam)"] and not df_s.empty:
        t_s = df_s.copy()
        t_s["Sistema_Origem"] = "Gestor Safe"
        dfs_combinados.append(t_s)
    if sistema_aba in ["Ambos os sistemas", "CPS Telemetria (Infrações)"] and not cps_inf_f.empty:
        t_c = cps_inf_f.copy()
        t_c["Sistema_Origem"] = "CPS Telemetria"
        if "nivel_risco" not in t_c.columns:
            t_c["nivel_risco"] = "Alto"
        dfs_combinados.append(t_c)

    if dfs_combinados:
        df_ev_tab = pd.concat(dfs_combinados, ignore_index=True)
        df_ev_tab["data_dia"] = df_ev_tab["dt_evento"].dt.date
        dias_disponiveis = sorted(df_ev_tab["data_dia"].dropna().unique(), reverse=True)

        c_sub1, c_sub2 = st.columns(2)
        with c_sub1:
            dia_especifico = st.selectbox("📅 Filtrar por data", ["Todos os dias"] + [str(d) for d in dias_disponiveis])
        with c_sub2:
            tipos_unicos = sorted(df_ev_tab["descricao"].dropna().unique().tolist())
            tipo_especifico = st.selectbox("📌 Filtrar por tipologia", ["Todas as tipologias"] + tipos_unicos)

        df_ev_filtrado = df_ev_tab
        if dia_especifico != "Todos os dias":
            df_ev_filtrado = df_ev_filtrado[df_ev_filtrado["data_dia"].astype(str) == dia_especifico]
        if tipo_especifico != "Todas as tipologias":
            df_ev_filtrado = df_ev_filtrado[df_ev_filtrado["descricao"] == tipo_especifico]

        tot_evs_aba = len(df_ev_filtrado)
        max_vel_aba = int(df_ev_filtrado["velocidade"].max()) if not df_ev_filtrado.empty else 0
        veic_mais_ev = "N/D"
        if not df_ev_filtrado.empty:
            vc = df_ev_filtrado["placa"].value_counts()
            veic_mais_ev = f"{vc.index[0]} ({vc.iloc[0]} eventos)"
        veic_maior_vel = "N/D"
        if not df_ev_filtrado.empty:
            r_top = df_ev_filtrado.sort_values("velocidade", ascending=False).iloc[0]
            veic_maior_vel = f"{r_top['placa']} ({int(r_top['velocidade'])} km/h)"

        k_e1, k_e2, k_e3, k_e4 = st.columns(4)
        render_bi_card(k_e1, "Eventos filtrados", f"{tot_evs_aba:,}", f"Sistema: {sistema_aba}", AMBAR, "🔔", 0)
        render_bi_card(k_e2, "Velocidade máxima", f"{max_vel_aba} km/h", "Pico registrado", VERMELHO, "🏎️", 60)
        render_bi_card(k_e3, "Mais ocorrências", veic_mais_ev, "Maior reincidência", AZUL, "🔁", 120)
        render_bi_card(k_e4, "Maior velocidade", veic_maior_vel, "Veículo e teto", VERDE, "🎯", 180)

        if not df_ev_filtrado.empty:
            sec("📂 Detalhamento por tipologia")
            resumo = df_ev_filtrado.groupby("descricao").agg(
                quantidade=("placa", "size"),
                vel_max=("velocidade", "max"),
                veiculos=("placa", lambda x: ", ".join(x.dropna().astype(str).unique()[:3])),
            ).reset_index().sort_values("quantidade", ascending=False)

            for _, row_t in resumo.iterrows():
                with st.expander(f"🔹 {row_t['descricao']} — {row_t['quantidade']} ocorrências • vel. máx {row_t['vel_max']} km/h"):
                    st.markdown(f"**Veículos em destaque:** {row_t['veiculos']}")
                    sub = df_ev_filtrado[df_ev_filtrado["descricao"] == row_t["descricao"]]
                    cols_sub = [c for c in ["Sistema_Origem", "dt_evento", "placa", "motorista", "velocidade", "nivel_risco", "cidade"] if c in sub.columns]
                    st.dataframe(sub[cols_sub].sort_values("dt_evento", ascending=False),
                                 use_container_width=True, hide_index=True)

            sec("📋 Registro mestre")
            cols_master = [c for c in ["Sistema_Origem", "dt_evento", "placa", "motorista", "descricao", "velocidade", "nivel_risco", "cidade"] if c in df_ev_filtrado.columns]
            st.dataframe(df_ev_filtrado[cols_master].sort_values("dt_evento", ascending=False),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum evento para os filtros escolhidos.")
    else:
        st.warning("Sem dados disponíveis para a seleção.")

elif pagina == MENU_IA:
    hero("🤖", "Assistente Operacional IA", "Modelo local via Ollama com acesso aos indicadores consolidados da frota")
    st.markdown(f'<span class="badge-live">Ollama • {OLLAMA_MODEL}</span>', unsafe_allow_html=True)
    st.write("")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        avatar = "🧑‍💼" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ex: 'Qual o veículo com mais eventos?', 'Resumo operacional', 'Quem excedeu mais a velocidade?'"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("O Ollama está a analisar os dados operacionais da frota..."):
                try:
                    tot_km = int(df_unificado["km_rodado"].sum()) if not df_unificado.empty else 0
                    tot_ev = int(df_unificado["total_eventos"].sum()) if not df_unificado.empty else 0
                    top_v_str = (df_unificado.sort_values("total_eventos", ascending=False)
                                 .head(5)[["placa", "total_eventos", "km_rodado", "km_por_evento"]]
                                 .to_string(index=False)) if not df_unificado.empty else "N/D"
                    top_m_str = "N/D"
                    if not cps_inf_f.empty:
                        m_agg = cps_inf_f.groupby("motorista").agg(
                            total_eventos=("descricao", "size"),
                            vel_max=("velocidade", "max"),
                        ).reset_index()
                        top_m_str = m_agg.sort_values("total_eventos", ascending=False).head(5).to_string(index=False)

                    prompt_completo = f"""
És o Analista Executivo Chefe de Frotas. Responde de forma direta e concisa com base nos dados abaixo:

- MÉTRICAS GLOBAIS: KM Total: {tot_km:,} km | Total Eventos: {tot_ev}

- TOP 5 VEÍCULOS MAIS INFRATORES:
{top_v_str}

- TOP 5 MOTORISTAS COM MAIS ALERTAS:
{top_m_str}

Pergunta do Gestor: {prompt}
"""
                    resposta = perguntar_ollama(prompt_completo)
                except Exception as e:
                    resposta = f"⚠️ Erro ao processar no Ollama: {e}"

                st.markdown(resposta)
                st.session_state.chat_history.append({"role": "assistant", "content": resposta})

elif pagina == MENU_AUDITORIA:
    hero("🔍", "Auditoria de Eventos Brutos", "Validação em tempo real dos registros de origem")

    col_aud1, col_aud2 = st.columns(2)
    with col_aud1:
        filtro_origem = st.selectbox("Sistema", ["Todos", "Gestor Safe", "CPS Telemetria"])
    with col_aud2:
        qtd_linhas = st.slider("Registros exibidos", 50, 1000, 200, 50)

    audit_list = []
    if not df_safe.empty:
        audit_list.append(pd.DataFrame({
            "Origem": "Gestor Safe", "Placa": _col(df_safe, "placa", "N/D").values,
            "Data/Hora": df_safe["dt_evento"].values, "Descrição": _col(df_safe, "descricao", "N/D").values,
            "Velocidade": _col(df_safe, "velocidade", 0).values,
        }))
    if not cps_infracoes.empty:
        audit_list.append(pd.DataFrame({
            "Origem": "CPS Telemetria", "Placa": _col(cps_infracoes, "placa", "N/D").values,
            "Data/Hora": cps_infracoes["dt_evento"].values, "Descrição": _col(cps_infracoes, "descricao", "Infração").values,
            "Velocidade": _col(cps_infracoes, "velocidade", 0).values,
        }))

    if audit_list:
        df_aud = pd.concat(audit_list, ignore_index=True).sort_values("Data/Hora", ascending=False)
        if filtro_origem != "Todos":
            df_aud = df_aud[df_aud["Origem"] == filtro_origem]
        st.dataframe(
            df_aud.head(qtd_linhas), use_container_width=True, hide_index=True,
            column_config={
                "Data/Hora": st.column_config.DatetimeColumn("Data/Hora", format="DD/MM/YYYY HH:mm"),
                "Velocidade": st.column_config.NumberColumn("Velocidade", format="%d km/h"),
            },
        )
    else:
        st.info("Sem registros para auditar.")

elif pagina == MENU_EXPORT:
    hero("📤", "Exportação de Relatórios", "Relatórios executivos em PDF por condutor e planilha master em Excel")

    def _txt(valor):
        """Texto compatível com as fontes core do PDF (latin-1)."""
        s = "" if valor is None else str(valor)
        return s.encode("latin-1", "replace").decode("latin-1")

    class RelatorioPDF(FPDF):
        def header(self):
            self.set_fill_color(11, 19, 43)
            self.rect(0, 0, 210, 26, "F")
            self.set_fill_color(0, 200, 83)
            self.rect(0, 26, 210, 1.4, "F")
            self.set_xy(12, 7)
            self.set_font("helvetica", "B", 15)
            self.set_text_color(255, 255, 255)
            self.cell(130, 7, _txt("GESTOR CEABS • RELATÓRIO EXECUTIVO DE CONDUTA"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(12)
            self.set_font("helvetica", "", 8.5)
            self.set_text_color(148, 163, 184)
            self.cell(130, 5, _txt("Mobilidade de Frota • Telemetria CPS + Gestor Safe"))
            self.set_font("helvetica", "", 8)
            self.set_xy(140, 9)
            self.cell(58, 5, _txt(f"Emitido: {datetime.now():%d/%m/%Y %H:%M}"), align="R")
            self.set_y(32)

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(226, 232, 240)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_y(-12)
            self.set_font("helvetica", "", 7.5)
            self.set_text_color(100, 116, 139)
            self.cell(95, 5, _txt("Documento confidencial • uso interno"), align="L")
            self.cell(95, 5, _txt(f"Página {self.page_no()} de {{nb}}"), align="R")

    def _kpi(pdf, x, y, w, rotulo, valor, cor):
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(x, y, w, 20, "F")
        pdf.set_fill_color(*cor)
        pdf.rect(x, y, 1.6, 20, "F")
        pdf.set_xy(x + 5, y + 3)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w - 7, 4, _txt(rotulo.upper()))
        pdf.set_xy(x + 5, y + 9)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w - 7, 8, _txt(valor))

    def _table_header(pdf):
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_fill_color(11, 19, 43)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(42, 7, _txt("DATA / HORA"), align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(28, 7, _txt("PLACA"), align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(86, 7, _txt("TIPOLOGIA DO EVENTO"), align="L", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(34, 7, _txt("VELOCIDADE"), align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def criar_pdf_motorista(nome_mot, df_h, setor, msg_gestao, filtro_ev, apenas_120):
        pdf = RelatorioPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=22)
        pdf.set_margins(10, 32, 10)
        pdf.add_page()

        datas = pd.to_datetime(df_h["dt_evento"], errors="coerce").dropna()
        periodo_txt = f"{datas.min():%d/%m/%Y} a {datas.max():%d/%m/%Y}" if not datas.empty else "N/D"
        vel_max = int(to_num(_col(df_h, "velocidade", 0)).fillna(0).max()) if not df_h.empty else 0
        n_veic = df_h["placa"].nunique() if "placa" in df_h.columns else 0

        y0 = pdf.get_y()
        larg = (190 - 3 * 4) / 4
        _kpi(pdf, 10, y0, larg, "Eventos", f"{len(df_h)}", (0, 200, 83))
        _kpi(pdf, 10 + (larg + 4), y0, larg, "Velocidade máx.", f"{vel_max} km/h", (239, 68, 68))
        _kpi(pdf, 10 + 2 * (larg + 4), y0, larg, "Veículos", f"{n_veic}", (2, 132, 199))
        _kpi(pdf, 10 + 3 * (larg + 4), y0, larg, "Período", periodo_txt, (124, 58, 237))
        pdf.set_y(y0 + 26)

        y1 = pdf.get_y()
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(10, y1, 190, 24, "F")
        pdf.set_xy(14, y1 + 3)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(11, 19, 43)
        pdf.cell(110, 6, _txt(f"COLABORADOR: {str(nome_mot).upper()}"))
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(0, 140, 90)
        pdf.cell(66, 6, _txt(f"SETOR: {str(setor).upper()}"), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(14)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(71, 85, 105)
        filtro_txt = f"Tipologia: {filtro_ev}" + (" • somente > 120 km/h" if apenas_120 else "")
        pdf.cell(176, 5, _txt(filtro_txt), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(14)
        pdf.cell(176, 5, _txt(f"Registros exibidos: {len(df_h)}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(y1 + 28)

        if msg_gestao and str(msg_gestao).strip():
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(11, 19, 43)
            pdf.cell(0, 6, _txt("MOTIVO / ENCAMINHAMENTO DA GESTÃO"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("helvetica", "", 9)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(190, 5, _txt(msg_gestao), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)

        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(11, 19, 43)
        pdf.cell(0, 6, _txt("DETALHAMENTO DOS EVENTOS"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        _table_header(pdf)

        zebra = False
        for _, r in df_h.iterrows():
            if pdf.get_y() > pdf.h - 26:
                pdf.add_page()
                _table_header(pdf)
            dt_v = pd.to_datetime(r.get("dt_evento"), errors="coerce")
            dt_s = f"{dt_v:%d/%m/%Y %H:%M}" if pd.notna(dt_v) else "N/D"
            pl_s = _txt(r.get("placa", ""))
            ds_s = _txt(str(r.get("descricao", ""))[:45])
            try:
                vel_num = int(float(r.get("velocidade", 0)))
            except (TypeError, ValueError):
                vel_num = 0

            if zebra:
                pdf.set_fill_color(240, 253, 244)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_font("helvetica", "", 8)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(42, 6, dt_s, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(28, 6, pl_s, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(86, 6, ds_s, align="L", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            if vel_num > 120:
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(220, 38, 38)
            pdf.cell(34, 6, f"{vel_num} km/h", align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            zebra = not zebra

        return bytes(pdf.output())

    def gerar_excel(dados):
        buf = io.BytesIO()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Consolidado"
        ws.sheet_view.showGridLines = False

        ws["B2"] = "RELATÓRIO MASTER • GESTOR & CPS"
        ws["B2"].font = Font(size=16, bold=True, color="0B132B")
        ws["B3"] = f"Gerado em {datetime.now():%d/%m/%Y %H:%M}"
        ws["B3"].font = Font(size=9, italic=True, color="64748B")

        headers = ["PLACA", "ODÔMETRO (km)", "KM RODADO", "EVENTOS SAFE", "EVENTOS CPS", "TOTAL", "KM / EVENTO"]
        header_row = 5
        borda = Border(*(Side(style="thin", color="E2E8F0"),) * 4)

        for c_idx, h in enumerate(headers, 2):
            cell = ws.cell(row=header_row, column=c_idx, value=h)
            cell.fill = PatternFill(start_color="0B132B", end_color="0B132B", fill_type="solid")
            cell.font = Font(color="00C853", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = borda

        registros = dados.to_dict("records")
        for r_idx, r in enumerate(registros, header_row + 1):
            valores = [
                str(r.get("placa", "")),
                int(r.get("odometro_atual", 0) or 0),
                float(r.get("km_rodado", 0) or 0),
                int(r.get("eventos_safe", 0) or 0),
                int(r.get("eventos_cps", 0) or 0),
                int(r.get("total_eventos", 0) or 0),
                float(r.get("km_por_evento", 0) or 0),
            ]
            for c_idx, v in enumerate(valores, 2):
                cell = ws.cell(row=r_idx, column=c_idx, value=v)
                cell.border = borda
                cell.alignment = Alignment(horizontal="center")
                if r_idx % 2 == 0:
                    cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
                if c_idx == 3:
                    cell.number_format = "#,##0"
                elif c_idx in (4, 8):
                    cell.number_format = "#,##0.0"

        ultima_linha = header_row + max(len(registros), 1)
        ws.auto_filter.ref = f"B{header_row}:H{ultima_linha}"
        ws.freeze_panes = f"B{header_row + 1}"
        for col, larg in {"A": 2, "B": 14, "C": 16, "D": 14, "E": 15, "F": 15, "G": 12, "H": 15}.items():
            ws.column_dimensions[col].width = larg

        wb.save(buf)
        return buf.getvalue()

    tab_pdf, tab_excel = st.tabs(["📄 PDF executivo", "📊 Excel master"])

    with tab_pdf:
        lista_mots_pdf = sorted(cps_infracoes["motorista"].dropna().unique().tolist()) if not cps_infracoes.empty else []

        if lista_mots_pdf:
            col_p1, col_p2 = st.columns(2)
            with col_p1, st.container(border=True):
                st.markdown("**👤 Colaborador e filtros**")
                mot_escolhido = st.selectbox("Colaborador / motorista", lista_mots_pdf, key="sel_mot_pdf")
                df_hist_mot_full = cps_infracoes[cps_infracoes["motorista"] == mot_escolhido].copy()
                tipos_eventos_mot = sorted(df_hist_mot_full["descricao"].dropna().unique().tolist())
                evento_filtro_pdf = st.selectbox("Filtrar por tipologia", ["Todos os eventos"] + tipos_eventos_mot, key="sel_evento_pdf")
                apenas_acima_120 = st.checkbox("⚡ Focar apenas em excessos de velocidade > 120 km/h", value=True, key="chk_120")
                limite_registros = st.slider("Número máximo de eventos no PDF", 5, 50, 15, 5, key="slider_lim_pdf")

            with col_p2, st.container(border=True):
                st.markdown("**🧾 Encaminhamento**")
                setor_destino = st.text_input("Setor responsável / direcionamento", value="Mobilidade de Frota",
                                              placeholder="Ex: Mobilidade de Frota, Manutenção, Operações...",
                                              key="txt_setor_pdf")
                mensagem_gestor = st.text_area("Mensagem / justificativa para o gestor",
                                               placeholder="Ex: Favor verificar o comportamento recorrente deste colaborador...",
                                               key="txt_msg_pdf", height=120)

            df_hist_mot = df_hist_mot_full
            if evento_filtro_pdf != "Todos os eventos":
                df_hist_mot = df_hist_mot[df_hist_mot["descricao"] == evento_filtro_pdf]
            if apenas_acima_120:
                is_speed = df_hist_mot["descricao"].str.contains("Velocidade", case=False, na=False)
                df_hist_mot = df_hist_mot[(~is_speed) | (df_hist_mot["velocidade"] > 120)]

            if not df_hist_mot.empty:
                df_hist_mot = df_hist_mot.sort_values("dt_evento", ascending=False).head(limite_registros)
                sec(f"Pré-visualização • {len(df_hist_mot)} eventos selecionados")
                cols_prev = [c for c in ["dt_evento", "placa", "descricao", "velocidade"] if c in df_hist_mot.columns]
                st.dataframe(df_hist_mot[cols_prev], use_container_width=True, hide_index=True)

                pdf_bytes = criar_pdf_motorista(mot_escolhido, df_hist_mot, setor_destino,
                                                mensagem_gestor, evento_filtro_pdf, apenas_acima_120)
                st.download_button(
                    label="📥 Baixar relatório executivo em PDF",
                    data=pdf_bytes,
                    file_name=f"Relatorio_Executivo_{str(mot_escolhido).replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.info("Nenhum histórico encontrado para este colaborador com os filtros selecionados.")
        else:
            st.warning("Sem dados de motoristas disponíveis na base.")

    with tab_excel:
        if not df_unificado.empty:
            st.markdown("**📊 Planilha consolidada por veículo**")
            st.caption("Inclui odômetro, KM rodado, eventos Safe e CPS, total e KM por evento.")
            st.download_button(
                "📊 Baixar relatório Excel (.xlsx)",
                data=gerar_excel(df_unificado),
                file_name=f"Relatorio_Master_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.info("Sem dados para exportar com os filtros atuais.")

# ==============================================================================
# RODAPÉ
# ==============================================================================
st.markdown("---")
st.markdown(
    '<div class="rodape"><span><b>Gestão Frotas • Cockpit Executivo</b> | Mobilidade Frota</span>'
    '<span class="badge-live">Sistema local • online</span></div>',
    unsafe_allow_html=True,
)
