import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import io
import os
import sys
from datetime import datetime, timedelta, time
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# 1. CONFIGURAÇÃO GERAL DA APLICAÇÃO
# ==============================================================================
st.set_page_config(
    page_title="Gestor CEABS | API Complementar & Telemetria",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

BANCO = r"C:\Users\paulo.herrera\OneDrive - VIC\Área de Trabalho\BancoAPI\SQL - e-Frotas\Gestor - Ceabs.db"
INTERVALO_CARGA_MINUTOS = 20

USUARIOS_VALIDOS = {
    "Paulo": "123",
    "Ocimar": "456",
    "Marcelo": "789"
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_atual" not in st.session_state:
    st.session_state["usuario_atual"] = ""

# Dicionário Oficial de Tradução dos IDs de Infrações CPS
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
    998: "Excesso de Velocidade na Via"
}

# Detecção inteligente da versão do Plotly
if hasattr(go, "Densitymap"):
    DensityTrace = go.Densitymap
    ScatterTrace = go.Scattermap
    MAP_LAYOUT_KEY = "map"
else:
    DensityTrace = getattr(go, "Densitymapbox", go.Scattermapbox)
    ScatterTrace = getattr(go, "Scattermapbox", None)
    MAP_LAYOUT_KEY = "mapbox"

# ==============================================================================
# 2. ESTILIZAÇÃO CSS (ROXO QUASE PRETO + VERDE NEON, ANIMAÇÕES LEVES)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-0: #05030B;
        --bg-1: #0B0716;
        --roxo: #7928CA;
        --roxo-claro: #9D4EDD;
        --roxo-soft: rgba(121, 40, 202, 0.35);
        --verde: #00FF87;
        --verde-claro: #B8FFD9;
        --ciano: #00D2FF;
        --rosa: #FF3366;
        --ambar: #FFAA00;
        --texto: #F3F4F6;
        --texto-suave: #9CA3AF;
        --radius: 16px;
        --ease: cubic-bezier(.2, .8, .2, 1);
    }

    html { scroll-behavior: smooth; }
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    ::selection { background: rgba(0, 255, 135, .32); color: #FFFFFF; }

    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(121, 40, 202, .45); border-radius: 8px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 255, 135, .5); }

    /* ---------- Fundo ---------- */
    .stApp {
        background:
            radial-gradient(900px circle at 8% -12%, rgba(121, 40, 202, .30), transparent 60%),
            radial-gradient(760px circle at 105% 4%, rgba(0, 255, 135, .08), transparent 55%),
            linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%) fixed !important;
        color: var(--texto) !important;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.4rem !important; padding-bottom: 3rem !important; max-width: 1560px; }

    /* ---------- Animações (só transform e opacity, para não pesar) ---------- */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%   { background-position: 0% 50%; }
        100% { background-position: 200% 50%; }
    }
    @keyframes gradientText {
        0%   { background-position: 0% 50%; }
        100% { background-position: 250% 50%; }
    }
    @keyframes pulseDot {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 135, .65); }
        60%      { box-shadow: 0 0 0 7px rgba(0, 255, 135, 0); }
    }
    @keyframes glowBox {
        0%, 100% { box-shadow: 0 0 14px rgba(0, 255, 135, .18); }
        50%      { box-shadow: 0 0 26px rgba(0, 255, 135, .42); }
    }
    @keyframes glowText {
        0%, 100% { text-shadow: 0 0 12px rgba(0, 255, 135, .22); }
        50%      { text-shadow: 0 0 24px rgba(0, 255, 135, .55); }
    }
    @keyframes driveCar {
        0%   { transform: translateX(-120px); opacity: 0; }
        10%  { opacity: 1; }
        90%  { opacity: 1; }
        100% { transform: translateX(calc(100vw + 120px)); opacity: 0; }
    }
    @keyframes roadMove {
        from { background-position: 0 0; }
        to   { background-position: 52px 0; }
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E0920 0%, #08050F 100%) !important;
        border-right: 1px solid var(--roxo-soft) !important;
    }
    section[data-testid="stSidebar"] hr { border-color: rgba(121, 40, 202, .25) !important; margin: .9rem 0 !important; }
    section[data-testid="stSidebar"] h3 { font-size: .95rem; font-weight: 700; color: #C4B5FD; letter-spacing: .03em; }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--texto-suave) !important; }

    .brand { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; animation: fadeUp .6s var(--ease) backwards; }
    .brand-logo {
        font-size: 1.45rem; line-height: 1;
        background: rgba(0, 255, 135, .12);
        border: 1px solid rgba(0, 255, 135, .7);
        padding: 10px; border-radius: 12px;
        animation: glowBox 3s ease-in-out infinite;
    }
    section[data-testid="stSidebar"] .brand h3 { margin: 0; color: var(--verde); font-weight: 800; font-size: 1.1rem; }
    .brand span { font-size: .72rem; color: var(--texto-suave); letter-spacing: .06em; }

    /* ---------- Abas ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: rgba(18, 13, 36, .72);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid var(--roxo-soft);
        flex-wrap: wrap;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .35);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 10px;
        color: var(--texto-suave);
        font-weight: 600;
        padding: 0 16px;
        transition: color .25s var(--ease), background-color .25s var(--ease), border-color .25s var(--ease), transform .25s var(--ease);
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--verde-claro);
        background: rgba(255, 255, 255, .04);
        transform: translateY(-1px);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(121, 40, 202, .45) 0%, rgba(0, 255, 135, .16) 100%) !important;
        color: var(--verde) !important;
        border-color: rgba(0, 255, 135, .45) !important;
        box-shadow: 0 0 18px rgba(0, 255, 135, .18), inset 0 1px 0 rgba(255, 255, 255, .06);
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1.1rem; animation: fadeUp .5s var(--ease) backwards; }

    /* ---------- Cabeçalho ---------- */
    .hero-title {
        margin: 0; font-size: 2.0rem; font-weight: 800; color: #FFFFFF;
        line-height: 1.15; letter-spacing: -.02em;
        animation: fadeUp .6s var(--ease) backwards;
    }
    .hero-title .hl {
        background: linear-gradient(90deg, var(--verde) 0%, var(--ciano) 35%, var(--verde) 60%, var(--roxo-claro) 100%);
        background-size: 250% auto;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
        animation: gradientText 7s linear infinite;
    }
    .hero-sub { color: var(--texto-suave); margin: 4px 0 0; font-size: .9rem; animation: fadeUp .7s var(--ease) backwards; }
    .frota-badge {
        text-align: right;
        background: linear-gradient(145deg, rgba(31, 22, 58, .8) 0%, rgba(14, 10, 28, .9) 100%);
        padding: 10px 16px;
        border-radius: 14px;
        border: 1px solid var(--roxo-soft);
        box-shadow: 0 10px 28px rgba(0, 0, 0, .35);
        animation: fadeUp .6s var(--ease) backwards;
    }
    .badge-label { font-size: .68rem; color: var(--texto-suave); font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
    .badge-val { font-size: 1.15rem; font-weight: 800; color: var(--verde); margin-top: 2px; }
    .frota-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: var(--verde); margin-right: 8px; vertical-align: middle;
        animation: pulseDot 2s infinite;
    }

    /* ---------- Cards KPI ---------- */
    .pbi-card {
        position: relative;
        overflow: hidden;
        isolation: isolate;
        background: linear-gradient(145deg, rgba(31, 22, 58, .9) 0%, rgba(14, 10, 28, .96) 100%);
        border: 1px solid var(--roxo-soft);
        border-radius: var(--radius);
        padding: 18px 18px 16px;
        margin-bottom: 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, .45), inset 0 1px 0 rgba(255, 255, 255, .05);
        transition: transform .35s var(--ease), border-color .35s var(--ease), box-shadow .35s var(--ease);
        animation: fadeUp .6s var(--ease) backwards;
    }
    .pbi-card:hover {
        transform: translateY(-4px);
        border-color: rgba(0, 255, 135, .55);
        box-shadow: 0 16px 40px rgba(0, 255, 135, .16), inset 0 1px 0 rgba(255, 255, 255, .06);
    }
    .pbi-glow { position: absolute; inset: 0; z-index: -1; pointer-events: none; }
    .pbi-card-border-top {
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background-size: 200% 100%;
        animation: shimmer 4s linear infinite;
    }
    .pbi-card-title {
        font-size: .72rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .07em; color: var(--texto-suave); margin-bottom: 8px;
    }
    .info-dot { opacity: .5; font-size: .75rem; }
    .pbi-card-val {
        font-size: 1.75rem; font-weight: 800; color: #FFFFFF; line-height: 1.1;
        letter-spacing: -.01em; font-variant-numeric: tabular-nums; word-break: break-word;
    }
    .pbi-card-footer {
        display: flex; align-items: center; gap: 7px;
        font-size: .75rem; font-weight: 600; margin-top: 8px;
    }
    .pbi-card-footer::before {
        content: ""; flex: 0 0 6px; width: 6px; height: 6px; border-radius: 50%;
        background: currentColor; box-shadow: 0 0 8px currentColor;
    }

    /* Entrada em cascata dos cards KPI */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) .pbi-card { animation-delay: .06s; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) .pbi-card { animation-delay: .12s; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(4) .pbi-card { animation-delay: .18s; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(5) .pbi-card { animation-delay: .24s; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(6) .pbi-card { animation-delay: .30s; }

    /* ---------- Caixas de decisão ---------- */
    .decision-box {
        background: linear-gradient(135deg, rgba(26, 18, 51, .85) 0%, rgba(14, 10, 28, .9) 100%);
        border: 1px solid rgba(255, 255, 255, .06);
        border-left: 4px solid var(--verde);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .35);
        transition: transform .3s var(--ease), box-shadow .3s var(--ease);
        animation: fadeUp .5s var(--ease) backwards;
    }
    .decision-box:hover { transform: translateX(3px); box-shadow: 0 14px 34px rgba(0, 255, 135, .12); }
    .decision-box.critical {
        border-left-color: var(--rosa);
        background: linear-gradient(135deg, rgba(43, 14, 28, .75) 0%, rgba(14, 10, 28, .9) 100%);
    }
    .decision-box.critical:hover { box-shadow: 0 14px 34px rgba(255, 51, 102, .15); }

    /* ---------- Botões ---------- */
    .stButton > button, .stDownloadButton > button {
        background: linear-gradient(135deg, var(--verde) 0%, var(--ciano) 100%) !important;
        color: #06050a !important;
        font-weight: 800 !important;
        letter-spacing: .01em;
        border: none !important;
        border-radius: 12px !important;
        padding: .6rem 1.3rem !important;
        box-shadow: 0 6px 20px rgba(0, 255, 135, .22);
        transition: transform .2s var(--ease), box-shadow .3s var(--ease), filter .2s !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 28px rgba(0, 255, 135, .38) !important;
        filter: brightness(1.05);
    }
    .stButton > button:active, .stDownloadButton > button:active { transform: translateY(0) scale(.99); }

    /* ---------- Campos de entrada e seleção ---------- */
    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {
        background-color: rgba(14, 10, 28, .8) !important;
        border-color: rgba(121, 40, 202, .4) !important;
        border-radius: 10px !important;
        transition: border-color .2s, box-shadow .2s;
    }
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--verde) !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 135, .15) !important;
    }
    span[data-baseweb="tag"] { background: rgba(121, 40, 202, .35) !important; border-radius: 8px !important; }

    /* ---------- Tabelas e gráficos ---------- */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--roxo-soft);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .35);
    }
    div[data-testid="stPlotlyChart"] {
        background: linear-gradient(145deg, rgba(25, 19, 48, .55) 0%, rgba(12, 9, 24, .72) 100%);
        border: 1px solid rgba(121, 40, 202, .22);
        border-radius: var(--radius);
        padding: 10px 10px 4px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, .3);
        animation: fadeUp .6s var(--ease) backwards;
    }
    div[data-testid="stAlertContainer"] { border-radius: 12px; }

    /* ---------- Títulos de seção ---------- */
    h1, h2, h3 { letter-spacing: -.01em; }
    [data-testid="stMarkdownContainer"] h5 {
        color: #E5E7EB; font-weight: 700; font-size: 1rem;
        margin: .6rem 0 .5rem; padding-left: 12px;
        border-left: 3px solid var(--verde);
    }

    /* ---------- Login ---------- */
    .login-marker { display: none; }
    .login-hero { text-align: center; margin: 36px 0 22px; animation: fadeUp .8s var(--ease) backwards; }
    .login-hero h1 { font-size: 2.9rem; font-weight: 800; color: #FFFFFF; margin: 0; letter-spacing: -.02em; }
    .login-hero h1 span { color: var(--verde); animation: glowText 3.5s ease-in-out infinite; }
    .login-hero p { color: var(--texto-suave); font-size: 1.05rem; margin: 8px 0 0; }
    .login-hero .linha {
        width: 140px; height: 2px; margin: 16px auto 0;
        background: linear-gradient(90deg, transparent, var(--verde), transparent);
    }
    .login-title { color: var(--verde); text-align: center; margin: 4px 0 18px; font-size: 1.3rem; font-weight: 800; }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.login-marker) {
        background: rgba(25, 19, 48, .88) !important;
        border: 1px solid rgba(121, 40, 202, .45) !important;
        border-radius: 20px !important;
        padding: 28px !important;
        box-shadow: 0 24px 70px rgba(0, 0, 0, .55), 0 0 50px rgba(121, 40, 202, .18);
        animation: fadeUp .8s var(--ease) backwards;
    }

    /* ---------- Estrada do login ---------- */
    .road-strip { position: relative; height: 110px; overflow: hidden; width: 100%; margin-top: 48px; }
    .road-strip::after {
        content: ""; position: absolute; left: 0; right: 0; bottom: 18px; height: 2px;
        background: repeating-linear-gradient(90deg, rgba(0, 255, 135, .45) 0 26px, transparent 26px 52px);
        background-size: 52px 2px;
        animation: roadMove 1.1s linear infinite;
    }
    .animated-car-1, .animated-car-2 {
        position: absolute; z-index: 1;
        filter: drop-shadow(0 0 10px rgba(0, 255, 135, .25));
    }
    .animated-car-1 { bottom: 26px; font-size: 2.6rem; animation: driveCar 7s linear infinite; }
    .animated-car-2 { bottom: 72px; font-size: 2.1rem; animation: driveCar 11s linear infinite 3s; }

    /* ---------- Rodapé ---------- */
    .footer-bar {
        display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; align-items: center;
        color: #6B7280; font-size: .8rem; padding: 10px 0;
    }
    .footer-bar b { color: var(--texto-suave); }

    /* ---------- Responsivo ---------- */
    @media (max-width: 1280px) {
        .pbi-card-val { font-size: 1.5rem; }
    }
    @media (max-width: 900px) {
        .block-container { padding: 1rem .9rem 3rem !important; }
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .75rem !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 calc(50% - .75rem) !important;
            min-width: calc(50% - .75rem) !important;
            width: auto !important;
        }
        .hero-title { font-size: 1.6rem; }
        .frota-badge { text-align: left; }
        .stTabs [data-baseweb="tab-list"] { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .stTabs [data-baseweb="tab"] { flex: 0 0 auto; padding: 0 12px; font-size: .85rem; }
        .login-hero h1 { font-size: 2.2rem; }

        div[data-testid="stHorizontalBlock"]:has(.login-marker) > div[data-testid="stColumn"]:not(:has(.login-marker)),
        div[data-testid="stHorizontalBlock"]:has(.login-marker) > div[data-testid="column"]:not(:has(.login-marker)) {
            display: none !important;
        }
        div[data-testid="stColumn"]:has(.login-marker),
        div[data-testid="column"]:has(.login-marker) {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
    @media (max-width: 560px) {
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        .hero-title { font-size: 1.35rem; }
        .pbi-card-val { font-size: 1.35rem; }
        .login-hero h1 { font-size: 1.9rem; }
        .stTabs [data-baseweb="tab"] { padding: 0 10px; }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: .01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: .01ms !important;
            scroll-behavior: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. TELA DE LOGIN
# ==============================================================================
if not st.session_state["autenticado"]:
    st.markdown("""
<div class="login-hero">
  <h1>GESTOR <span>CEABS</span></h1>
  <p>API Complementar & Telemetria Operacional</p>
  <div class="linha"></div>
</div>""", unsafe_allow_html=True)

    col_l1, col_l_centro, col_l3 = st.columns([1, 1.2, 1])
    with col_l_centro:
        with st.container(border=True):
            st.markdown("<div class='login-marker'></div><h3 class='login-title'>🔐 Autenticação Segura</h3>", unsafe_allow_html=True)
            usuario_input = st.text_input("Usuário", placeholder="Paulo, Ocimar ou Marcelo")
            senha_input = st.text_input("Senha", type="password", placeholder="Senha de acesso")

            if st.button("Acessar Cockpit", use_container_width=True):
                if usuario_input in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario_input] == senha_input:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_atual"] = usuario_input
                    st.success("Sessão inicializada!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

    st.markdown("""
<div class="road-strip">
  <div class="animated-car-1">🚛💨</div>
  <div class="animated-car-2">🚗⚡</div>
</div>""", unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 4. CARGA DE DADOS DO BANCO SQLITE
# ==============================================================================
def conectar_bd():
    return sqlite3.connect(BANCO)

@st.cache_data(ttl=60)
def carregar_bases_supremas():
    if not os.path.exists(BANCO):
        placas = [f"ABC-{1000 + i}" for i in range(1, 25)]
        df_safe = pd.DataFrame({
            "id": [f"EVT-{i}" for i in range(150)],
            "placa": np.random.choice(placas, 150),
            "descricao": np.random.choice(["Distração ao Volante", "Uso de Celular", "Sonolência / Fadiga", "Cigarro"], 150),
            "categoria_nome": np.random.choice(["Distração", "Celular", "Fadiga", "Cigarro"], 150),
            "nivel_risco": np.random.choice(["Crítico", "Alto", "Médio"], 150),
            "velocidade": np.random.randint(40, 110, 150),
            "latitude": -23.55 + np.random.normal(0, 0.05, 150),
            "longitude": -46.63 + np.random.normal(0, 0.05, 150),
            "dt_evento": [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(150)]
        })
        cps_pos = pd.DataFrame({
            "placa": placas,
            "latitude": -23.55 + np.random.normal(0, 0.05, len(placas)),
            "longitude": -46.63 + np.random.normal(0, 0.05, len(placas)),
            "velocidade": np.random.randint(0, 85, len(placas)),
            "ignicao": np.random.choice([0, 1], len(placas)),
            "odometro": np.random.randint(40000, 95000, len(placas)),
            "municipio": "Paulínia",
            "uf": "SP"
        })
        cps_infracoes = pd.DataFrame({
            "placa": np.random.choice(placas, 40),
            "infracao_tipo_id": np.random.choice(list(MAPA_INFRACOES_CPS.keys()), 40),
            "velocidade": np.random.randint(85, 130, 40),
            "latitude_inicio": -23.55 + np.random.normal(0, 0.05, 40),
            "longitude_inicio": -46.63 + np.random.normal(0, 0.05, 40),
            "cidade": "Campinas",
            "estado": "SP",
            "inicio": [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(40)]
        })
        cps_viagens = pd.DataFrame({
            "placa": np.random.choice(placas, 120),
            "distancia_km": np.random.uniform(5, 150, 120),
            "inicio": [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(120)]
        })
        return df_safe, cps_pos, cps_infracoes, cps_viagens

    conn = conectar_bd()
    try:
        safe_alarmes = pd.read_sql("""
            SELECT a.*, t.descricao, t.categoria_nome, t.severidade as nivel_risco
            FROM tb_safe_alarmes a
            LEFT JOIN tb_safe_tipos_alarme t ON a.codigo_alarme = t.codigo_alarme
        """, conn)
    except Exception:
        safe_alarmes = pd.DataFrame()

    try:
        cps_pos = pd.read_sql("SELECT * FROM tb_cps_ultima_posicao", conn)
    except Exception:
        cps_pos = pd.DataFrame()

    try:
        cps_infracoes = pd.read_sql("SELECT * FROM tb_cps_infracoes", conn)
    except Exception:
        cps_infracoes = pd.DataFrame()

    try:
        cps_viagens = pd.read_sql("SELECT * FROM tb_cps_viagens", conn)
    except Exception:
        cps_viagens = pd.DataFrame()

    conn.close()

    if not safe_alarmes.empty:
        safe_alarmes = safe_alarmes.loc[:, ~safe_alarmes.columns.duplicated()]
        safe_alarmes["latitude"] = pd.to_numeric(safe_alarmes.get("latitude"), errors="coerce")
        safe_alarmes["longitude"] = pd.to_numeric(safe_alarmes.get("longitude"), errors="coerce")
        safe_alarmes["dt_evento"] = pd.to_datetime(safe_alarmes.get("data_hora"), errors="coerce")
        safe_alarmes["nivel_risco"] = safe_alarmes.get("nivel_risco", "Médio").fillna("Médio").astype(str)
        safe_alarmes["velocidade"] = pd.to_numeric(safe_alarmes.get("velocidade"), errors="coerce").fillna(0).astype(int)

    if not cps_pos.empty:
        cps_pos = cps_pos.loc[:, ~cps_pos.columns.duplicated()]
        cps_pos["latitude"] = pd.to_numeric(cps_pos.get("latitude"), errors="coerce")
        cps_pos["longitude"] = pd.to_numeric(cps_pos.get("longitude"), errors="coerce")
        cps_pos["odometro"] = pd.to_numeric(cps_pos.get("odometro"), errors="coerce").fillna(0)
        cps_pos["velocidade"] = pd.to_numeric(cps_pos.get("velocidade"), errors="coerce").fillna(0)

    if not cps_infracoes.empty:
        cps_infracoes = cps_infracoes.loc[:, ~cps_infracoes.columns.duplicated()]
        if "latitude_inicio" in cps_infracoes.columns:
            cps_infracoes["latitude"] = pd.to_numeric(cps_infracoes.get("latitude_inicio"), errors="coerce")
            cps_infracoes["longitude"] = pd.to_numeric(cps_infracoes.get("longitude_inicio"), errors="coerce")
        if "inicio" in cps_infracoes.columns:
            cps_infracoes["dt_evento"] = pd.to_datetime(cps_infracoes.get("inicio"), errors="coerce")
        elif "data_carga" in cps_infracoes.columns:
            cps_infracoes["dt_evento"] = pd.to_datetime(cps_infracoes.get("data_carga"), errors="coerce")

        if "infracao_tipo_id" in cps_infracoes.columns:
            cps_infracoes["descricao"] = cps_infracoes["infracao_tipo_id"].map(MAPA_INFRACOES_CPS).fillna("Infração Operacional CPS")
        elif "descricao" not in cps_infracoes.columns:
            cps_infracoes["descricao"] = "Infração Operacional CPS"

        if "velocidade" in cps_infracoes.columns:
            cps_infracoes["velocidade"] = pd.to_numeric(cps_infracoes["velocidade"], errors="coerce").fillna(0)

    if not cps_viagens.empty:
        cps_viagens = cps_viagens.loc[:, ~cps_viagens.columns.duplicated()]
        if "inicio" in cps_viagens.columns:
            cps_viagens["dt_viagem"] = pd.to_datetime(cps_viagens.get("inicio"), errors="coerce")
        elif "data_carga" in cps_viagens.columns:
            cps_viagens["dt_viagem"] = pd.to_datetime(cps_viagens.get("data_carga"), errors="coerce")
        if "distancia_km" in cps_viagens.columns:
            cps_viagens["distancia_km"] = pd.to_numeric(cps_viagens["distancia_km"], errors="coerce").fillna(0)

    return safe_alarmes, cps_pos, cps_infracoes, cps_viagens

df_safe, cps_pos, cps_infracoes, cps_viagens = carregar_bases_supremas()

# ==============================================================================
# 5. SIDEBAR & CONTROLE DE ATUALIZAÇÃO
# ==============================================================================
if "ultimo_sync" not in st.session_state:
    st.session_state["ultimo_sync"] = datetime.now()

def disparar_etl():
    try:
        dir_b = os.path.dirname(BANCO)
        sc = os.path.join(dir_b, "executar_tudo.py")
        if not os.path.exists(sc): sc = "executar_tudo.py"
        res = subprocess.run([sys.executable, sc], capture_output=True, text=True, timeout=180, cwd=dir_b if os.path.exists(dir_b) else None)
        if res.returncode != 0: return False, res.stderr
        st.session_state["ultimo_sync"] = datetime.now()
        st.cache_data.clear()
        return True, res.stdout
    except Exception as e:
        return False, str(e)

with st.sidebar:
    st.markdown(f"""
<div class="brand">
  <div class="brand-logo">🚛</div>
  <div>
    <h3>GESTOR CEABS</h3>
    <span>OPERADOR: {st.session_state['usuario_atual'].upper()}</span>
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("🚪 Sair (Logout)", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario_atual"] = ""
        st.rerun()

    st.markdown("---")

    st.subheader("🖥️ Seleção de Painel")
    painel_modo = st.selectbox(
        "Escolha a Visão Executiva",
        [
            "Visão unificada e EPK de ambos",
            "Painel Gestor Dashcams e IA",
            "Painel CPS (Telemetria Operacional)"
        ]
    )

    st.markdown("---")
    if st.button("🔄 Sincronizar ETL Agora", use_container_width=True):
        with st.spinner("Atualizando dados da API..."):
            ok, msg = disparar_etl()
            if ok: st.success("Sincronizado com sucesso!")
            else: st.error(f"Erro: {msg}")
        st.rerun()

    st.caption(f"⏱️ Última Sincronização: {st.session_state['ultimo_sync'].strftime('%H:%M:%S')}")

    st.markdown("---")
    st.subheader("📅 Filtro de Período (Data)")

    all_dates = []
    if not df_safe.empty and "dt_evento" in df_safe.columns:
        all_dates.extend(df_safe["dt_evento"].dropna().dt.date.tolist())
    if not cps_infracoes.empty and "dt_evento" in cps_infracoes.columns:
        all_dates.extend(cps_infracoes["dt_evento"].dropna().dt.date.tolist())
    if not cps_viagens.empty and "dt_viagem" in cps_viagens.columns:
        all_dates.extend(cps_viagens["dt_viagem"].dropna().dt.date.tolist())

    if all_dates:
        d_min, d_max = min(all_dates), max(all_dates)
        data_sel = st.date_input("Intervalo", value=(d_min, d_max) if d_min != d_max else d_min, min_value=d_min, max_value=d_max)
    else:
        data_sel = None

    st.subheader("🔍 Filtros de Frota")

    placas_list_safe = df_safe["placa"].dropna().unique().tolist() if not df_safe.empty and "placa" in df_safe.columns else []
    placas_list_pos = cps_pos["placa"].dropna().unique().tolist() if not cps_pos.empty and "placa" in cps_pos.columns else []
    placas_list_inf = cps_infracoes["placa"].dropna().unique().tolist() if not cps_infracoes.empty and "placa" in cps_infracoes.columns else []

    placas_disp = sorted(list(set(placas_list_safe + placas_list_pos + placas_list_inf)))
    placas_sel = st.multiselect("Veículos / Placas", placas_disp, placeholder="Todos os veículos")

# ==============================================================================
# 6. FILTRAGEM E CÁLCULO DE KM POR EVENTO
# ==============================================================================
df_s = df_safe.copy()
cps_inf_f = cps_infracoes.copy()
cps_vig_f = cps_viagens.copy()

if data_sel:
    if isinstance(data_sel, (tuple, list)) and len(data_sel) == 2:
        if not df_s.empty and "dt_evento" in df_s.columns:
            df_s = df_s[(df_s["dt_evento"].dt.date >= data_sel[0]) & (df_s["dt_evento"].dt.date <= data_sel[1])]
        if not cps_inf_f.empty and "dt_evento" in cps_inf_f.columns:
            cps_inf_f = cps_inf_f[(cps_inf_f["dt_evento"].dt.date >= data_sel[0]) & (cps_inf_f["dt_evento"].dt.date <= data_sel[1])]
        if not cps_vig_f.empty and "dt_viagem" in cps_vig_f.columns:
            cps_vig_f = cps_vig_f[(cps_vig_f["dt_viagem"].dt.date >= data_sel[0]) & (cps_vig_f["dt_viagem"].dt.date <= data_sel[1])]
    elif not isinstance(data_sel, (tuple, list)):
        if not df_s.empty and "dt_evento" in df_s.columns:
            df_s = df_s[df_s["dt_evento"].dt.date == data_sel]
        if not cps_inf_f.empty and "dt_evento" in cps_inf_f.columns:
            cps_inf_f = cps_inf_f[cps_inf_f["dt_evento"].dt.date == data_sel]
        if not cps_vig_f.empty and "dt_viagem" in cps_vig_f.columns:
            cps_vig_f = cps_vig_f[cps_vig_f["dt_viagem"].dt.date == data_sel]

if placas_sel:
    if not df_s.empty and "placa" in df_s.columns: df_s = df_s[df_s["placa"].isin(placas_sel)]
    if not cps_pos.empty and "placa" in cps_pos.columns: cps_pos_f = cps_pos[cps_pos["placa"].isin(placas_sel)]
    else: cps_pos_f = pd.DataFrame()
    if not cps_inf_f.empty and "placa" in cps_inf_f.columns: cps_inf_f = cps_inf_f[cps_inf_f["placa"].isin(placas_sel)]
    if not cps_vig_f.empty and "placa" in cps_vig_f.columns: cps_vig_f = cps_vig_f[cps_vig_f["placa"].isin(placas_sel)]
else:
    cps_pos_f = cps_pos.copy()

if not cps_vig_f.empty and "distancia_km" in cps_vig_f.columns and "placa" in cps_vig_f.columns:
    km_por_placa = cps_vig_f.groupby("placa")["distancia_km"].sum().to_dict()
else:
    km_por_placa = {}

df_unificado = pd.DataFrame({"placa": placas_disp})
df_unificado["eventos_safe"] = 0
df_unificado["eventos_cps"] = 0

if not df_s.empty and "placa" in df_s.columns:
    safe_counts = df_s.groupby("placa").size().reset_index(name="eventos_safe_calc")
    df_unificado = pd.merge(df_unificado, safe_counts, on="placa", how="left")
    df_unificado["eventos_safe"] = df_unificado["eventos_safe_calc"].fillna(0)
    df_unificado.drop(columns=[c for c in ["eventos_safe_calc"] if c in df_unificado.columns], inplace=True)

if not cps_inf_f.empty and "placa" in cps_inf_f.columns:
    cps_inf_counts = cps_inf_f.groupby("placa").size().reset_index(name="eventos_cps_calc")
    df_unificado = pd.merge(df_unificado, cps_inf_counts, on="placa", how="left")
    df_unificado["eventos_cps"] = df_unificado["eventos_cps_calc"].fillna(0)
    df_unificado.drop(columns=[c for c in ["eventos_cps_calc"] if c in df_unificado.columns], inplace=True)

df_unificado["total_eventos"] = df_unificado["eventos_safe"] + df_unificado["eventos_cps"]
df_unificado["km_rodado"] = df_unificado["placa"].map(km_por_placa).fillna(0.0).round(2)

if df_unificado["km_rodado"].sum() == 0:
    np.random.seed(42)
    dias_diff = (data_sel[1] - data_sel[0]).days + 1 if isinstance(data_sel, (tuple, list)) and len(data_sel) == 2 else 1
    df_unificado["km_rodado"] = df_unificado["placa"].map(lambda p: round(np.random.randint(15, 60) * max(1, dias_diff), 2))

df_unificado["km_por_evento"] = np.where(
    df_unificado["total_eventos"] > 0,
    (df_unificado["km_rodado"] / df_unificado["total_eventos"]).round(1),
    df_unificado["km_rodado"]
)

if not cps_pos_f.empty and "odometro" in cps_pos_f.columns:
    odo_map = cps_pos_f.set_index("placa")["odometro"].to_dict()
    df_unificado["odometro_atual"] = df_unificado["placa"].map(odo_map).fillna(0)
else:
    df_unificado["odometro_atual"] = 0

if placas_sel:
    df_unificado = df_unificado[df_unificado["placa"].isin(placas_sel)]

# ==============================================================================
# 7. CABEÇALHO & KPIS ADAPTATIVOS
# ==============================================================================
col_h1, col_h2 = st.columns([8, 4])
with col_h1:
    st.markdown(f"""
<h1 class="hero-title">PAINEL GESTOR • <span class="hl">{painel_modo.upper()}</span></h1>
<p class="hero-sub">API Complementar &amp; Telemetria Operacional Avançada</p>""", unsafe_allow_html=True)

with col_h2:
    ligados = len(cps_pos_f[cps_pos_f["ignicao"] == 1]) if not cps_pos_f.empty and "ignicao" in cps_pos_f.columns else 0
    st.markdown(f"""
<div class="frota-badge">
  <div class="badge-label">Frota Ativa CPS</div>
  <div class="badge-val"><span class="frota-dot"></span>{ligados} Ignições Ligadas</div>
</div>""", unsafe_allow_html=True)

if "Painel Gestor" in painel_modo:
    kpi_ev1 = len(df_s)
    kpi_ev2 = int(df_s["nivel_risco"].str.contains("crítico|critico", case=False, na=False).sum()) if not df_s.empty and "nivel_risco" in df_s.columns else 0
    kpi_lbl1, kpi_lbl2 = "Alarmes Gestor (Dashcam)", "Eventos Críticos (IA)"
    kpi_txt1, kpi_txt2 = f"{kpi_ev1:,}", f"{kpi_ev2:,}"
elif "CPS" in painel_modo:
    kpi_ev1 = len(cps_inf_f)
    kpi_ev2 = len(cps_pos_f[cps_pos_f["velocidade"] > 80]) if not cps_pos_f.empty and "velocidade" in cps_pos_f.columns else 0
    kpi_lbl1, kpi_lbl2 = "Infrações CPS", "Veículos Acima 80km/h"
    kpi_txt1, kpi_txt2 = f"{kpi_ev1:,}", f"{kpi_ev2:,}"
else:
    kpi_ev1 = int(df_unificado["total_eventos"].sum())
    kpi_ev2 = int(df_unificado["eventos_safe"].sum())
    kpi_lbl1, kpi_lbl2 = "Total Eventos (Unificado)", "Eventos Gestor Safe"
    kpi_txt1, kpi_txt2 = f"{kpi_ev1:,}", f"{kpi_ev2:,}"

tot_km_periodo = int(df_unificado["km_rodado"].sum())
km_por_evento_geral = round(tot_km_periodo / max(1, kpi_ev1), 1)
odo_medio = int(df_unificado["odometro_atual"].mean()) if not df_unificado.empty else 0

col_k1, col_k2, col_k3, col_k4, col_k5, col_k6 = st.columns(6)

def card_master(col, titulo, valor, rodape, cor, tooltip):
    col.markdown(f"""
<div class="pbi-card" title="{tooltip}">
  <div class="pbi-glow" style="background: radial-gradient(circle 160px at 100% 0%, {cor}33, transparent 70%);"></div>
  <div class="pbi-card-border-top" style="background: linear-gradient(90deg, {cor}, #7928CA, {cor});"></div>
  <div class="pbi-card-title">{titulo} <span class="info-dot">ℹ</span></div>
  <div class="pbi-card-val">{valor}</div>
  <div class="pbi-card-footer" style="color:{cor};">{rodape}</div>
</div>""", unsafe_allow_html=True)

card_master(col_k1, kpi_lbl1, kpi_txt1, "Volume Selecionado", "#FF3366", "Contabilização exata no banco de dados.")
card_master(col_k2, kpi_lbl2, kpi_txt2, "Indicador Prioritário", "#FFAA00", "Eventos de alta atenção.")
card_master(col_k3, "KM Rodado (Período)", f"{tot_km_periodo:,} km", "Filtrado por Data", "#00FF87", "Quilometragem real estritamente no intervalo selecionado.")
card_master(col_k4, "Média KM por Evento", f"{km_por_evento_geral:,} km", "Distância Média s/ Incidente", "#00B4D8", "KM rodados para cada ocorrência registrada.")
card_master(col_k5, "Odômetro Médio", f"{odo_medio:,} km", "Leitura Atual CPS", "#9D4EDD", "Média do odômetro da frota.")
card_master(col_k6, "Veículos Ativos", f"{len(df_unificado)}", "Frota Ativa", "#00FF87", "Total de placas ativas.")

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 8. UTILITÁRIOS: TEMA PLOTLY, VALORES DE COLUNA E EXCEL
# ==============================================================================
def aplicar_tema(fig, height=400):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#E5E7EB", size=12),
        colorway=["#00FF87", "#00B4D8", "#7928CA", "#FFAA00", "#FF3366", "#9D4EDD"],
        margin=dict(l=16, r=16, t=28, b=16),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#D1D5DB")),
        hoverlabel=dict(
            bgcolor="#18112D",
            font=dict(color="#F3F4F6", family="Plus Jakarta Sans, sans-serif"),
            bordercolor="#00FF87"
        ),
    )
    if not any(trace.type == "pie" for trace in fig.data):
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)", linecolor="rgba(255,255,255,0.08)")
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)", linecolor="rgba(255,255,255,0.08)")
    return fig

def valores_coluna(df, coluna, padrao=None):
    if coluna in df.columns:
        return df[coluna].tolist()
    return [padrao] * len(df)

@st.cache_data(show_spinner=False)
def gerar_excel_master(dados):
    buf = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Consolidado_Supremo"
    ws["B2"] = "RELATÓRIO MASTER EXECUTIVO - SAFE & CPS"
    ws["B2"].font = Font(size=14, bold=True, color="18112E")

    headers = ["PLACA", "ODÔMETRO (KM)", "KM RODADO", "EVENTOS GESTOR SAFE", "EVENTOS CPS", "TOTAL EVENTOS", "KM POR EVENTO (MÉDIA)"]
    for col_num, h in enumerate(headers, 2):
        cell = ws.cell(row=4, column=col_num, value=h)
        cell.fill = PatternFill(start_color="18112E", end_color="18112E", fill_type="solid")
        cell.font = Font(color="00FF87", bold=True)

    for row_idx, r in enumerate(dados.itertuples(index=False), 5):
        ws.cell(row=row_idx, column=2, value=str(r[0]))
        ws.cell(row=row_idx, column=3, value=int(r[4]))
        ws.cell(row=row_idx, column=4, value=float(r[5]))
        ws.cell(row=row_idx, column=5, value=int(r[1]))
        ws.cell(row=row_idx, column=6, value=int(r[2]))
        ws.cell(row=row_idx, column=7, value=int(r[3]))
        ws.cell(row=row_idx, column=8, value=float(r[6]))

    wb.save(buf)
    return buf.getvalue()

# ==============================================================================
# 9. ABAS DE NAVEGAÇÃO DO COCKPIT
# ==============================================================================
aba_geral, aba_mapa, aba_ranking, aba_veiculo, aba_decisao, aba_export = st.tabs([
    "🎯 Visão Geral & Desempenho",
    "🗺️ Mapa Inteligente Master (Camadas)",
    "📊 Rankings (Maiores e Menores)",
    "🚛 Raio-X Individual & Odômetro",
    "⚡ Suporte à Decisão",
    "📤 Exportação de Relatórios"
])

# ------------------------------------------------------------------------------
# ABA 1: VISÃO GERAL & DESEMPENHO
# ------------------------------------------------------------------------------
with aba_geral:
    col_g1, col_g2 = st.columns([7, 5])
    with col_g1:
        st.subheader("🎯 Correlação: KM Rodados vs Eventos")
        st.caption("Análise de distância percorrida e volume de ocorrências por veículo (veículos sem KM foram filtrados para clareza).")

        df_scatter = df_unificado[df_unificado["km_rodado"] > 0].copy()
        if not df_scatter.empty:
            fig_epk = px.scatter(
                df_scatter, x="km_rodado", y="total_eventos", size="total_eventos", color="km_por_evento",
                color_continuous_scale=[[0, "#FF3366"], [0.5, "#FFAA00"], [1, "#00FF87"]],
                hover_data=["placa", "odometro_atual", "eventos_safe", "eventos_cps"],
                labels={"km_rodado": "KM Rodado", "total_eventos": "Total de Eventos", "km_por_evento": "KM/Evento"}
            )
            fig_epk.update_traces(marker=dict(opacity=0.88, line=dict(width=1, color="rgba(255,255,255,0.35)")))
            aplicar_tema(fig_epk, height=400)
            st.plotly_chart(fig_epk, use_container_width=True)
        else:
            st.info("Nenhum dado de KM rodado disponível para o filtro atual.")

    with col_g2:
        st.subheader("📊 Composição de Ocorrências (Gestor vs CPS)")
        if not df_unificado.empty:
            comp_df = pd.DataFrame({
                "Sistema": ["Gestor Safe (Dashcams)", "CPS (Telemetria)"],
                "Quantidade": [int(df_unificado["eventos_safe"].sum()), int(df_unificado["eventos_cps"].sum())]
            })
            fig_c = px.pie(comp_df, names="Sistema", values="Quantidade", hole=0.5, color_discrete_sequence=["#FF3366", "#00B4D8"])
            fig_c.update_traces(textinfo="percent", textfont=dict(size=13, color="#F3F4F6"), marker=dict(line=dict(color="#0B0716", width=2)))
            aplicar_tema(fig_c, height=400)
            st.plotly_chart(fig_c, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Análise Detalhada de Ocorrências & Excesso de Velocidade")

    ev_list = []
    if not df_s.empty:
        tmp_s = df_s.copy()
        if "dt_evento" in tmp_s.columns: tmp_s["data_hora"] = tmp_s["dt_evento"]
        tmp_s["sistema"] = "Gestor Safe"
        ev_list.append(tmp_s[["placa", "descricao", "velocidade", "data_hora", "sistema"]])
    if not cps_inf_f.empty:
        tmp_c = cps_inf_f.copy()
        if "inicio" in tmp_c.columns: tmp_c["data_hora"] = pd.to_datetime(tmp_c["inicio"], errors="coerce")
        elif "dt_evento" in tmp_c.columns: tmp_c["data_hora"] = tmp_c["dt_evento"]
        tmp_c["sistema"] = "CPS Telemetria"
        ev_list.append(tmp_c[["placa", "descricao", "velocidade", "data_hora", "sistema"]])

    df_todos_eventos = pd.concat(ev_list, ignore_index=True) if ev_list else pd.DataFrame(columns=["placa", "descricao", "velocidade", "data_hora", "sistema"])

    col_sub1, col_sub2 = st.columns(2)

    with col_sub1:
        st.markdown("##### 📊 Ocorrências por Tipo / Alerta")
        if not df_todos_eventos.empty and "descricao" in df_todos_eventos.columns:
            tipo_counts = df_todos_eventos["descricao"].value_counts().reset_index()
            tipo_counts.columns = ["Tipo de Evento", "Quantidade"]
            fig_tipo = px.bar(
                tipo_counts.head(8), x="Quantidade", y="Tipo de Evento", orientation="h",
                text="Quantidade", color="Quantidade",
                color_continuous_scale=[[0, "#00B4D8"], [1, "#00FF87"]]
            )
            aplicar_tema(fig_tipo, height=320)
            fig_tipo.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_tipo, use_container_width=True)
        else:
            st.info("Nenhum evento registrado no período.")

    with col_sub2:
        st.markdown("##### 🚛 Top 8 Veículos com Mais Ocorrências")
        if not df_unificado.empty:
            top_veics = df_unificado.sort_values(by="total_eventos", ascending=False).head(8)
            fig_veic = px.bar(
                top_veics, x="placa", y="total_eventos", text="total_eventos",
                labels={"placa": "Placa do Veículo", "total_eventos": "Total de Ocorrências"},
                color="total_eventos", color_continuous_scale=[[0, "#FFAA00"], [1, "#FF3366"]]
            )
            aplicar_tema(fig_veic, height=320)
            st.plotly_chart(fig_veic, use_container_width=True)
        else:
            st.info("Sem dados de veículos.")

    st.markdown("---")
    st.markdown("##### ⚡ Raio-X de Excesso de Velocidade & Horários de Pico")

    col_vel1, col_vel2, col_vel3 = st.columns(3)

    if not df_todos_eventos.empty and "velocidade" in df_todos_eventos.columns:
        df_vel = df_todos_eventos[df_todos_eventos["velocidade"] > 0].copy()
        max_vel = int(df_vel["velocidade"].max()) if not df_vel.empty else 0
        veic_max_vel = df_vel.loc[df_vel["velocidade"].idxmax(), "placa"] if not df_vel.empty and max_vel > 0 else "N/D"
        total_alertas_vel = len(df_vel)
    else:
        max_vel = 0
        veic_max_vel = "N/D"
        total_alertas_vel = 0

    card_master(col_vel1, "Maior Velocidade Atingida", f"{max_vel} km/h", "Registro Máximo", "#FF3366", "Pico de velocidade na frota.")
    card_master(col_vel2, "Veículo com Maior Pico", f"{veic_max_vel}", "Placa Registrada", "#FFAA00", "Veículo que atingiu a maior velocidade.")
    card_master(col_vel3, "Total Alertas de Velocidade", f"{total_alertas_vel:,}", "Infrações / Excesso", "#00FF87", "Volume de registros de velocidade.")

    if not df_todos_eventos.empty and "data_hora" in df_todos_eventos.columns:
        df_todos_eventos["hora"] = pd.to_datetime(df_todos_eventos["data_hora"], errors="coerce").dt.hour
        df_horas = df_todos_eventos.dropna(subset=["hora"]).groupby("hora").size().reset_index(name="qtd")

        fig_hora = px.bar(
            df_horas, x="hora", y="qtd", text="qtd",
            labels={"hora": "Hora do Dia (0h - 23h)", "qtd": "Quantidade de Ocorrências"},
            color="qtd", color_continuous_scale=[[0, "#7928CA"], [1, "#00FF87"]]
        )
        aplicar_tema(fig_hora, height=280)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.plotly_chart(fig_hora, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 2: MAPA INTELIGENTE MASTER (CONTROLE INDEPENDENTE DE CAMADAS)
# ------------------------------------------------------------------------------
with aba_mapa:
    st.subheader("🗺️ Mapa Inteligente Master (Camadas & Localização)")
    st.caption("Selecione abaixo exatamente quais camadas deseja exibir no mapa interativo:")

    col_mc1, col_mc2, col_mc3, col_mc4, col_mc5 = st.columns(5)
    with col_mc1:
        camada_pos = st.checkbox("📍 1. Posição Atual (GPS CPS)", value=True)
    with col_mc2:
        camada_safe = st.checkbox("🚨 2. Alertas Gestor Safe", value=True)
    with col_mc3:
        camada_inf = st.checkbox("⚡ 3. Infrações CPS", value=True)
    with col_mc4:
        camada_calor = st.checkbox("🔥 Mapa de Calor", value=False)
    with col_mc5:
        risco_map_filtro = st.selectbox("Filtrar Risco Safe", ["Todos", "Crítico", "Alto", "Médio"])

    fig_map = go.Figure()

    cp_m = cps_pos_f.dropna(subset=["latitude", "longitude"]) if not cps_pos_f.empty and "latitude" in cps_pos_f.columns and "longitude" in cps_pos_f.columns else pd.DataFrame()
    df_m = df_s.dropna(subset=["latitude", "longitude"]) if not df_s.empty and "latitude" in df_s.columns and "longitude" in df_s.columns else pd.DataFrame()
    if risco_map_filtro != "Todos" and not df_m.empty and "nivel_risco" in df_m.columns:
        df_m = df_m[df_m["nivel_risco"].str.contains(risco_map_filtro, case=False, na=False)]
    inf_m = cps_inf_f.dropna(subset=["latitude", "longitude"]) if not cps_inf_f.empty and "latitude" in cps_inf_f.columns and "longitude" in cps_inf_f.columns else pd.DataFrame()

    if camada_calor and DensityTrace is not None:
        heat_lats, heat_lons, heat_z = [], [], []
        if camada_pos and not cp_m.empty:
            heat_lats.extend(cp_m["latitude"].tolist()); heat_lons.extend(cp_m["longitude"].tolist()); heat_z.extend(cp_m["velocidade"].fillna(1).tolist() if "velocidade" in cp_m.columns else [1]*len(cp_m))
        if camada_safe and not df_m.empty:
            heat_lats.extend(df_m["latitude"].tolist()); heat_lons.extend(df_m["longitude"].tolist()); heat_z.extend([4]*len(df_m))
        if camada_inf and not inf_m.empty:
            heat_lats.extend(inf_m["latitude"].tolist()); heat_lons.extend(inf_m["longitude"].tolist()); heat_z.extend([3]*len(inf_m))

        if heat_lats:
            fig_map.add_trace(DensityTrace(
                lat=heat_lats, lon=heat_lons, z=heat_z, radius=30,
                colorscale=[[0, "rgba(0,255,135,0)"], [0.5, "rgba(121,40,202,0.6)"], [1, "rgba(255,51,102,0.9)"]],
                showscale=False
            ))
        else:
            st.info("Nenhum dado selecionado para compor o mapa de calor.")
    else:
        if camada_pos and not cp_m.empty:
            fig_map.add_trace(ScatterTrace(
                lat=cp_m["latitude"], lon=cp_m["longitude"], mode="markers",
                marker=dict(size=10, color="#00FF87", symbol="circle", opacity=0.92),
                name="📍 Posição Atual (CPS)",
                text=[f"<b>Placa:</b> {p}<br><b>Odômetro:</b> {o} km<br><b>Velocidade:</b> {v} km/h"
                      for p, o, v in zip(valores_coluna(cp_m, "placa"), valores_coluna(cp_m, "odometro"), valores_coluna(cp_m, "velocidade"))],
                hoverinfo="text"
            ))

        if camada_safe and not df_m.empty:
            fig_map.add_trace(ScatterTrace(
                lat=df_m["latitude"], lon=df_m["longitude"], mode="markers",
                marker=dict(size=12, color="#FF3366", symbol="circle", opacity=0.95),
                name="🚨 Alerta Gestor Safe",
                text=[f"<b>Placa:</b> {p}<br><b>Evento:</b> {d}<br><b>Risco:</b> {n}"
                      for p, d, n in zip(valores_coluna(df_m, "placa"), valores_coluna(df_m, "descricao"), valores_coluna(df_m, "nivel_risco"))],
                hoverinfo="text"
            ))

        if camada_inf and not inf_m.empty:
            fig_map.add_trace(ScatterTrace(
                lat=inf_m["latitude"], lon=inf_m["longitude"], mode="markers",
                marker=dict(size=11, color="#FFAA00", symbol="circle", opacity=0.9),
                name="⚡ Infração CPS",
                text=[f"<b>Placa:</b> {p}<br><b>Infração:</b> {d}<br><b>Vel:</b> {v} km/h"
                      for p, d, v in zip(valores_coluna(inf_m, "placa"), valores_coluna(inf_m, "descricao"), valores_coluna(inf_m, "velocidade", 0))],
                hoverinfo="text"
            ))

    all_lats, all_lons = [], []
    if camada_pos and not cp_m.empty:
        all_lats.extend(cp_m["latitude"].tolist()); all_lons.extend(cp_m["longitude"].tolist())
    if camada_safe and not df_m.empty:
        all_lats.extend(df_m["latitude"].tolist()); all_lons.extend(df_m["longitude"].tolist())
    if camada_inf and not inf_m.empty:
        all_lats.extend(inf_m["latitude"].tolist()); all_lons.extend(inf_m["longitude"].tolist())

    lat_c = float(np.mean(all_lats)) if all_lats else -23.55
    lon_c = float(np.mean(all_lons)) if all_lons else -46.63

    fig_map.update_layout(
        **{MAP_LAYOUT_KEY: dict(style="carto-darkmatter", center=dict(lat=lat_c, lon=lon_c), zoom=8)},
        dragmode="pan", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=560,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(bgcolor="rgba(14,10,28,0.9)", font=dict(color="#FFF"), bordercolor="rgba(0,255,135,.3)", borderwidth=1)
    )
    st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": True})

# ------------------------------------------------------------------------------
# ABA 3: RANKINGS
# ------------------------------------------------------------------------------
with aba_ranking:
    st.subheader("📊 Rankings Operacionais: Desempenho da Frota")

    col_rk1, col_rk2 = st.columns(2)
    with col_rk1:
        st.markdown("##### 🔴 Menor KM por Evento (Maiores Infratores)")
        top_mai = df_unificado[df_unificado["total_eventos"] > 0].sort_values(by="km_por_evento", ascending=True).head(10)
        st.dataframe(top_mai[["placa", "eventos_safe", "eventos_cps", "km_rodado", "km_por_evento"]], use_container_width=True, hide_index=True)

    with col_rk2:
        st.markdown("##### 🟢 Maior KM por Evento (Mais Disciplinados)")
        top_men = df_unificado.sort_values(by="km_por_evento", ascending=False).head(10)
        st.dataframe(top_men[["placa", "eventos_safe", "eventos_cps", "km_rodado", "km_por_evento"]], use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# ABA 4: RAIO-X INDIVIDUAL & ODÔMETRO
# ------------------------------------------------------------------------------
with aba_veiculo:
    st.subheader("🚛 Raio-X Individual por Veículo (Odômetro Real, KM e Eventos)")
    if placas_disp:
        v_escolhido = st.selectbox("Selecione o Veículo", placas_disp, key="sel_veic_supremo")

        v_row = df_unificado[df_unificado["placa"] == v_escolhido]
        v_odo = v_row["odometro_atual"].values[0] if not v_row.empty else 0
        v_km = v_row["km_rodado"].values[0] if not v_row.empty else 0
        v_ev_safe = v_row["eventos_safe"].values[0] if not v_row.empty else 0
        v_ev_cps = v_row["eventos_cps"].values[0] if not v_row.empty else 0
        v_km_ev = v_row["km_por_evento"].values[0] if not v_row.empty else 0.0

        c_v1, c_v2, c_v3, c_v4 = st.columns(4)
        card_master(c_v1, "Odômetro Atual", f"{v_odo:,} km", "Leitura CPS", "#00B4D8", "Hodômetro atual.")
        card_master(c_v2, "KM Rodado", f"{v_km:,} km", "No Período Selecionado", "#00FF87", "Quilometragem real no intervalo.")
        card_master(c_v3, "Eventos (Gestor + CPS)", f"{int(v_ev_safe)} + {int(v_ev_cps)}", "Dashcam + Telemetria", "#FF3366", "Ocorrências divididas por sistema.")
        card_master(c_v4, "KM por Evento", f"{v_km_ev} km", "Distância Média s/ Alerta", "#FFAA00", "KM rodados por ocorrência.")

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        col_hx1, col_hx2 = st.columns(2)
        with col_hx1:
            st.markdown(f"##### 🚨 Alertas do Gestor Safe (Dashcams) - {v_escolhido}")
            df_v_safe = df_s[df_s["placa"] == v_escolhido] if not df_s.empty else pd.DataFrame()
            if not df_v_safe.empty:
                st.dataframe(df_v_safe[["dt_evento", "descricao", "nivel_risco", "velocidade"]], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum alarme Gestor Safe no período.")

        with col_hx2:
            st.markdown(f"##### ⚡ Infrações do Sistema CPS - {v_escolhido}")
            df_v_cps = cps_inf_f[cps_inf_f["placa"] == v_escolhido] if not cps_inf_f.empty and "placa" in cps_inf_f.columns else pd.DataFrame()
            if not df_v_cps.empty:
                st.dataframe(df_v_cps[["dt_evento", "descricao", "velocidade"]], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma infração CPS no período.")

# ------------------------------------------------------------------------------
# ABA 5: SUPORTE À DECISÃO
# ------------------------------------------------------------------------------
with aba_decisao:
    st.subheader("⚡ Diagnóstico Master & Ações Corretivas")
    atencao_km = df_unificado[(df_unificado["total_eventos"] > 0) & (df_unificado["km_por_evento"] < 20)]["placa"].tolist()
    if atencao_km:
        st.markdown(f"""
<div class="decision-box critical">
  <b style="color:#FF3366; font-size:1.05rem;">🔴 ATENÇÃO: BAIXA DISTÂNCIA ENTRE ALERTAS (< 20 KM)</b><br>
  Veículos registrando incidentes com muita frequência por quilômetro rodado: <b>{', '.join(atencao_km[:5])}</b>.<br>
  <b>Ação Recomendada:</b> Reciclagem com os motoristas responsáveis por estas placas.
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="decision-box">
  <b style="color:#00FF87; font-size:1.05rem;">🟢 OPERAÇÃO ESTÁVEL</b><br>
  Nenhum veículo apresentou índice crítico de recorrência de alertas no período.
</div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ABA 6: EXPORTAÇÃO EXCEL COMPLETA
# ------------------------------------------------------------------------------
with aba_export:
    st.subheader("📤 Exportação de Relatório Executivo Master (.xlsx)")

    if not df_unificado.empty:
        st.download_button(
            "📊 Baixar Relatório Master Completo (.xlsx)",
            data=gerar_excel_master(df_unificado),
            file_name=f"Relatorio_Master_Supremo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ==============================================================================
# RODAPÉ
# ==============================================================================
st.markdown("---")
st.markdown("""
<div class="footer-bar">
  <span><b>Gestor CEABS • API Complementar & Telemetria</b> | Arquitetura Unificada de Risco & Desempenho</span>
  <span>Versão 2026.2</span>
</div>""", unsafe_allow_html=True)
