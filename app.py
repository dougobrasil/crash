from flask import Flask, render_template_string, jsonify
import requests
import threading
import time

app = Flask(__name__)

# --- CONFIGURAÇÕES E ESTADO (Lógica V10) ---
config = {"MAX_GALES": 2}
stats = {"vitorias": 0, "derrotas": 0, "win_15": 0, "win_20": 0, "win_alta": 0, "g1": 0, "g2": 0}
state = {"ativo": False, "gale": 0, "alvo": 2.0, "estrategia": "", "desc": "Aguardando mercado...", "historico": []}

URL_API = "https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4"
HEADERS = {"User-Agent": "Mozilla/5.0", "Bypass-Tunnel-Reminder": "true"}

# --- MOTOR DE ANÁLISE ---
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

# --- LOOP DE MONITORAMENTO EM SEGUNDO PLANO ---
def monitor_bot():
    global stats, state
    ultimo_id = None
    while True:
        try:
            res = requests.get(URL_API, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                dados = res.json()
                historico = [float(i['ponto']) for i in dados if 'ponto' in i and i['ponto'] != "0"]
                state["historico"] = historico[:10]

                if historico and historico[0] != ultimo_id:
                    novo_res = historico[0]
                    ultimo_id = novo_res
                    
                    if state["ativo"]:
                        if novo_res >= state["alvo"]:
                            stats["vitorias"] += 1
                            if state["gale"] == 1: stats["g1"] += 1
                            if state["gale"] == 2: stats["g2"] += 1
                            state["ativo"] = False
                            state["gale"] = 0
                        else:
                            if state["gale"] < config["MAX_GALES"]:
                                state["gale"] += 1
                            else:
                                stats["derrotas"] += 1
                                state["ativo"] = False
                                state["gale"] = 0
                    
                    if not state["ativo"]:
                        est, alvo, desc = analisar_v10(historico)
                        if est:
                            state.update({"ativo": True, "estrategia": est, "alvo": alvo, "desc": desc})
                        else:
                            state["desc"] = "Aguardando Padrão..."
        except: pass
        time.sleep(3)

# Inicia o monitor em uma thread separada
threading.Thread(target=monitor_bot, daemon=True).start()

# --- INTERFACE WEB (HTML/JS) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DougoBrasil V10 - Web</title>
    <style>
        body { font-family: sans-serif; background: #0f1923; color: white; text-align: center; }
        .container { max-width: 600px; margin: auto; padding: 20px; }
        .card { background: #1a242d; border-radius: 10px; padding: 15px; margin: 10px 0; border: 1px solid #303c47; }
        .sinal-ativo { background: #28a745; color: black; font-weight: bold; padding: 20px; border-radius: 10px; animation: pulse 1.5s infinite; }
        .gale-ativo { background: #ffc107; color: black; font-weight: bold; padding: 20px; border-radius: 10px; }
        .velas { display: flex; justify-content: center; gap: 5px; margin-top: 10px; }
        .vela { padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>DougoBrasil V10</h1>
        <div id="status_box" class="card">Aguardando dados...</div>
        
        <div class="card">
            <h3>Estatísticas</h3>
            <p id="stats">W: 0 | L: 0 | G1: 0 | G2: 0</p>
        </div>

        <div class="card">
            <h3>Últimos Resultados</h3>
            <div id="velas_list" class="velas"></div>
        </div>
    </div>

    <script>
        async function update() {
            try {
                const response = await fetch('/data');
                const data = await response.json();
                
                // Atualiza Sinal
                const box = document.getElementById('status_box');
                if (data.state.ativo) {
                    box.className = data.state.gale > 0 ? 'gale-ativo' : 'sinal-ativo';
                    box.innerHTML = `SINAL: ${data.state.desc} <br> ALVO: ${data.state.alvo}x ${data.state.gale > 0 ? '(GALE ' + data.state.gale + ')' : ''}`;
                } else {
                    box.className = 'card';
                    box.innerHTML = data.state.desc;
                }

                // Atualiza Stats
                document.getElementById('stats').innerText = `W: ${data.stats.vitorias} | L: ${data.stats.derrotas} | G1: ${data.stats.g1} | G2: ${data.stats.g2}`;

                // Atualiza Velas
                const vList = document.getElementById('velas_list');
                vList.innerHTML = data.state.historico.map(v => {
                    let color = v >= 2 ? '#28a745' : '#dc3545';
                    if (v >= 5) color = '#6f42c1';
                    return `<span class="vela" style="background:${color}">${v.toFixed(2)}x</span>`;
                }).join('');
            } catch (e) {}
        }
        setInterval(update, 3000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/data')
def get_data():
    return jsonify({"stats": stats, "state": state})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
