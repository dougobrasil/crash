import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# Configuração da Página Web
st.set_page_config(page_title="DougoBrasil V10", page_icon="🚀", layout="wide")

# --- LÓGICA DO BOT (MANTIDA) ---
if 'stats' not in st.session_state:
    st.session_state.stats = {"vitorias": 0, "derrotas": 0, "win_15": 0, "win_20": 0, "win_alta": 0, "g1_count": 0, "g2_count": 0}
if 'state' not in st.session_state:
    st.session_state.state = {"ativo": False, "gale": 0, "alvo": 2.0, "estrategia": "", "desc": "", "ultimo_id": None}

URL_API = "https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4"
HEADERS = {"User-Agent": "Mozilla/5.0", "Bypass-Tunnel-Reminder": "true"}

def obter_dados():
    try:
        res = requests.get(URL_API, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            dados = res.json()
            if isinstance(dados, list) and len(dados) > 0 and 'ponto' in dados[0]:
                return dados
        return None
    except: return None

def analisar_v10(h):
    if len(h) < 10: return None, 0, ""
    densidade_green = (len([x for x in h[:12] if x >= 2.0]) / 12) * 100
    
    if all(x < 5.0 for x in h[:10]) and h[0] >= 2.0 and h[1] >= 2.0:
        return "VELA_ROSA", 5.0, "🚀 BUSCA DE VELA ALTA (ALVO 5X)"
    if h[0] < 2.0 and h[1] < 2.0 and h[2] < 2.0:
        return "REVERSÃO", 2.0, "🎯 QUEBRA DE SEQUÊNCIA RED"
    if h[0] < 2.0 and h[1] >= 2.0 and densidade_green > 40:
        return "FLUXO", 1.5, "🛡️ ENTRADA DE SEGURANÇA"
    if h[0] < 2.0 and h[1] < 2.0 and h[2] >= 2.0 and h[3] >= 2.0:
        return "ESPELHO", 2.0, "🔄 PADRÃO DE DUPLAS"
    return None, 0, ""

# --- INTERFACE STREAMLIT ---
st.title("🥇 DougoBrasil V10 - Dashboard Web")
st.markdown("---")

# Colunas de Métricas
m1, m2, m3, m4, m5 = st.columns(5)
total = st.session_state.stats["vitorias"] + st.session_state.stats["derrotas"]
wr = (st.session_state.stats["vitorias"] / total * 100) if total > 0 else 0

m1.metric("Winrate", f"{wr:.1f}%")
m2.metric("Vitórias", st.session_state.stats["vitorias"])
m3.metric("Derrotas", st.session_state.stats["derrotas"])
m4.metric("Gale 1", st.session_state.stats["g1_count"])
m5.metric("Gale 2", st.session_state.stats["g2_count"])

# Área do Sinal
container_sinal = st.empty()
container_grafico = st.empty()
container_hist = st.empty()

# Loop de Monitoramento
while True:
    dados = obter_dados()
    if dados:
        historico = [float(i['ponto']) for i in dados if 'ponto' in i and i['ponto'] != "0"]
        
        if historico and historico[0] != st.session_state.state["ultimo_id"]:
            novo_res = historico[0]
            st.session_state.state["ultimo_id"] = novo_res
            
            # Processa resultado
            if st.session_state.state["ativo"]:
                if novo_res >= st.session_state.state["alvo"]:
                    st.session_state.stats["vitorias"] += 1
                    if st.session_state.state["gale"] == 1: st.session_state.stats["g1_count"] += 1
                    if st.session_state.state["gale"] == 2: st.session_state.stats["g2_count"] += 1
                    st.session_state.state["ativo"] = False
                    st.session_state.state["gale"] = 0
                    st.balloons()
                else:
                    if st.session_state.state["gale"] < 2:
                        st.session_state.state["gale"] += 1
                    else:
                        st.session_state.stats["derrotas"] += 1
                        st.session_state.state["ativo"] = False
                        st.session_state.state["gale"] = 0

            # Busca novo sinal
            if not st.session_state.state["ativo"]:
                est, alvo, desc = analisar_v10(historico)
                if est:
                    st.session_state.state.update({"ativo": True, "alvo": alvo, "desc": desc, "estrategia": est})

        # Atualiza a Interface Web
        with container_sinal:
            if st.session_state.state["ativo"]:
                tipo = "warning" if st.session_state.state["gale"] > 0 else "success"
                txt = f"🔥 SINAL ATIVO: {st.session_state.state['desc']} | ALVO: {st.session_state.state['alvo']}x"
                if st.session_state.state["gale"] > 0: txt = f"⚠️ ENTRAR GALE {st.session_state.state['gale']}: {st.session_state.state['desc']}"
                st.info(txt) if tipo == "success" else st.warning(txt)
            else:
                st.write("🔎 Analisando tendências do mercado...")

        with container_grafico:
            st.line_chart(historico[:30])

        with container_hist:
            cols = st.columns(10)
            for idx, val in enumerate(historico[:10]):
                cor = "green" if val >= 2.0 else "red"
                cols[idx].markdown(f"<p style='color:{cor}; font-weight:bold;'>{val:.2f}x</p>", unsafe_allow_html=True)

    time.sleep(3)
    st.rerun() # Atualiza a página para mostrar os novos dados
