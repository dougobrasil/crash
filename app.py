from flask import Flask, render_template_string, jsonify
import requests
import threading
import time

app = Flask(__name__)

# --- ESTADO GLOBAL (100% DAS SUAS LÓGICAS) ---
stats = {
    "vitorias": 0, "derrotas": 0, 
    "win_15": 0, "win_20": 0, "win_alta": 0,
    "g1_count": 0, "g2_count": 0
}

state = {
    "ativo": False, 
    "gale": 0, 
    "alvo": 2.0, 
    "estrategia": "", 
    "desc": "🔍 Analisando tendências...", 
    "historico": []
}

# URL da API e Headers atualizados para evitar bloqueios
URL_API = "https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Bypass-Tunnel-Reminder": "true"
}

def analisar_v10(h):
    """Motor de IA DougoBrasil V10 - Sem cortes"""
    if len(h) < 10: return None, 0, ""
    
    densidade_green = (len([x for x in h[:12] if x >= 2.0]) / 12) * 100

    # 🚀 ESTRATÉGIA VELA ROSA
    if all(x < 5.0 for x in h[:10]) and h[0] >= 2.0 and h[1] >= 2.0:
        return "VELA_ROSA", 5.0, "🚀 BUSCA DE VELA ALTA (5X)"

    # 🎯 ESTRATÉGIA REVERSÃO
    if h[0] < 2.0 and h[1] < 2.0 and h[2] < 2.0:
        return "REVERSÃO", 2.0, "🎯 QUEBRA DE SEQUÊNCIA RED"

    # 🛡️ ESTRATÉGIA FLUXO
    if h[0] < 2.0 and h[1] >= 2.0 and densidade_green > 40:
        return "FLUXO", 1.5, "🛡️ ENTRADA DE SEGURANÇA"

    # 🔄 PADRÃO ESPELHO
    if h[0] < 2.0 and h[1] < 2.0 and h[2] >= 2.0 and h[3] >= 2.0:
        return "ESPELHO", 2.0, "🔄 PADRÃO DE DUPLAS"

    return None, 0, ""

def monitor_bot():
    global stats, state
    ultimo_id = None
    
    while True:
        try:
            res = requests.get(URL_API, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                dados = res.json()
                # Tratamento rigoroso para evitar KeyError
                historico = [float(i['ponto']) for i in dados if isinstance(i, dict) and 'ponto' in i and i['ponto'] != "0"]
                state["historico"] = historico[:15]

                if historico and historico[0] != ultimo_id:
                    novo_res = historico[0]
                    ultimo_id = novo_res
                    
                    if state["ativo"]:
                        if novo_res >= state["alvo"]:
                            stats["vitorias"] += 1
                            if state["gale"] == 1: stats["g1_count"] += 1
                            if state["gale"] == 2: stats["g2_count"] += 1
                            state["ativo"] = False
                            state["gale"] = 0
                            state["desc"] = "✅ GREEN CONFIRMADO!"
                        else:
                            if state["gale"] < 2:
                                state["gale"] += 1
                                state["desc"] = f"⚠️ ATENÇÃO: ENTRAR GALE {state['gale']}"
                            else:
                                stats["derrotas"] += 1
                                state["ativo"] = False
                                state["gale"] = 0
                                state["desc"] = "❌ LOSS - AGUARDANDO PRÓXIMO"
                    
                    if not state["ativo"]:
                        est, alvo, desc = analisar_v10(historico)
                        if est:
                            state.update({"ativo": True, "estrategia": est, "alvo": alvo, "desc": desc})
                        elif "GREEN" not in state["desc"] and "LOSS" not in state["desc"]:
                            state["desc"] = "🔍 Analisando padrões..."
            else:
                state["desc"] = f"⚠️ Erro de Conexão ({res.status_code})"
        except Exception as e:
            state["desc"] = "⚠️ API Offline ou Instável"
        
        time.sleep(2.5)

# Inicia thread de monitoramento
threading.Thread(target=monitor_bot, daemon=True).start()

# --- INTERFACE WEB (REATIVIDADE MELHORADA) ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>DOUGOBRASIL V10 WEB</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Arial', sans-serif; background: #0b1218; color: white; text-align: center; margin: 0; padding: 15px; }
        .status-card { background: #151f28; padding: 25px; border-radius: 15px; border: 2px solid #232f3b; margin-bottom: 20px; transition: 0.3s; }
        .sinal-ativo { border-color: #2ecc71; background: rgba(46, 204, 113, 0.1); box-shadow: 0 0 20px rgba(46, 204, 113, 0.2); }
        .gale-ativo { border-color: #f1c40f; background: rgba(241, 196, 15, 0.1); }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
        .stat-item { background: #151f28; padding: 10px; border-radius: 8px; border: 1px solid #232f3b; }
        .vela { padding: 6px 12px; border-radius: 4px; font-weight: bold; display: inline-block; margin: 3px; font-size: 0.85rem; }
    </style>
</head>
<body>
    <h2 style="color: #f1c40f;">DOUGOBRASIL V10 - WEB</h2>
    
    <div id="status_box" class="status-card">Carregando sinal...</div>

    <div class="stats-grid">
        <div class="stat-item"><small>WINRATE</small><br><b id="wr">0%</b></div>
        <div class="stat-item"><small>W / L</small><br><b id="wl">0 / 0</b></div>
    </div>

    <div class="status-card">
        <small>HISTÓRICO RECENTE</small>
        <div id="velas" style="margin-top: 10px;"></div>
    </div>

    <script>
        async function update() {
            try {
                const r = await fetch('/data');
                const d = await r.json();
                
                const box = document.getElementById('status_box');
                if(d.state.ativo) {
                    box.className = 'status-card ' + (d.state.gale > 0 ? 'gale-ativo' : 'sinal-ativo');
                    box.innerHTML = `<h3 style="margin:0">${d.state.desc}</h3><p style="margin:5px 0">ALVO: ${d.state.alvo}x</p>`;
                } else {
                    box.className = 'status-card';
                    box.innerHTML = d.state.desc;
                }

                const total = d.stats.vitorias + d.stats.derrotas;
                document.getElementById('wr').innerText = total > 0 ? ((d.stats.vitorias / total) * 100).toFixed(1) + '%' : '0%';
                document.getElementById('wl').innerText = `${d.stats.vitorias} / ${d.stats.derrotas}`;
                
                document.getElementById('velas').innerHTML = d.state.historico.map(v => {
                    let color = v >= 2 ? '#2ecc71' : '#e74c3c';
                    if(v >= 5) color = '#9b59b6';
                    return `<span class="vela" style="background:${color}">${v.toFixed(2)}x</span>`;
                }).join('');
            } catch(e) {}
        }
        setInterval(update, 2000); // Atualiza a cada 2 segundos
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_PAGE)

@app.route('/data')
def get_data(): return jsonify({"stats": stats, "state": state})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
