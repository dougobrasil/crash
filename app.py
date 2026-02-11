from flask import Flask, render_template_string, jsonify
import requests
import threading
import time

app = Flask(__name__)

# --- 100% DA SUA LÓGICA V10 INTEGRADA ---
stats = {
    "vitorias": 0, "derrotas": 0, 
    "win_15": 0, "win_20": 0, "win_alta": 0,
    "g1_count": 0, "g2_count": 0
}

state = {
    "ativo": False, "gale": 0, "alvo": 2.0, 
    "estrategia": "", "desc": "Aguardando mercado...", "historico": []
}

URL_API = "https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Bypass-Tunnel-Reminder": "true"
}

def analisar_v10(h):
    """Motor de IA Multi-Alvo Original DougoBrasil"""
    if len(h) < 10: return None, 0, ""
    
    # Cálculo de tendência
    velas_altas = len([x for x in h[:20] if x >= 5.0])
    densidade_green = (len([x for x in h[:12] if x >= 2.0]) / 12) * 100

    # 🎯 ESTRATÉGIA VELA ROSA (5.0x)
    if all(x < 5.0 for x in h[:10]) and h[0] >= 2.0 and h[1] >= 2.0:
        return "VELA_ROSA", 5.0, "🚀 BUSCA DE VELA ALTA (ALVO 5X)"

    # 🎯 ESTRATÉGIA REVERSÃO (2.0x)
    if h[0] < 2.0 and h[1] < 2.0 and h[2] < 2.0:
        return "REVERSÃO", 2.0, "🎯 QUEBRA DE SEQUÊNCIA RED"

    # 🎯 ESTRATÉGIA FLUXO (1.5x)
    if h[0] < 2.0 and h[1] >= 2.0 and densidade_green > 40:
        return "FLUXO", 1.5, "🛡️ ENTRADA DE SEGURANÇA"

    # 🎯 PADRÃO ESPELHO DUPLO (2.0x)
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
                historico = [float(i['ponto']) for i in dados if 'ponto' in i and i['ponto'] != "0"]
                state["historico"] = historico[:15] # Mostra as últimas 15 na web

                if historico and historico[0] != ultimo_id:
                    novo_res = historico[0]
                    ultimo_id = novo_res
                    
                    # Processamento de Resultado (Win/Loss/Gale)
                    if state["ativo"]:
                        if novo_res >= state["alvo"]:
                            stats["vitorias"] += 1
                            if state["gale"] == 1: stats["g1_count"] += 1
                            if state["gale"] == 2: stats["g2_count"] += 1
                            if state["alvo"] >= 5.0: stats["win_alta"] += 1
                            elif state["alvo"] >= 2.0: stats["win_20"] += 1
                            state["ativo"] = False
                            state["gale"] = 0
                        else:
                            if state["gale"] < 2:
                                state["gale"] += 1
                            else:
                                stats["derrotas"] += 1
                                state["ativo"] = False
                                state["gale"] = 0
                    
                    # Análise de novos sinais
                    if not state["ativo"]:
                        est, alvo, desc = analisar_v10(historico)
                        if est:
                            state.update({"ativo": True, "estrategia": est, "alvo": alvo, "desc": desc})
                        else:
                            state["desc"] = "Aguardando Padrão de Alta Assertividade..."
        except Exception as e:
            print(f"Erro na API: {e}")
        time.sleep(2)

# Iniciar bot em background
threading.Thread(target=monitor_bot, daemon=True).start()

# --- INTERFACE WEB COMPLETA ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>DOUGOBRASIL V10 - ULTRA ELITE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0b1218; color: white; text-align: center; margin: 0; padding: 20px; }
        .header { color: #f1c40f; text-shadow: 0 0 10px rgba(241, 196, 15, 0.5); margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; max-width: 800px; margin: auto; }
        .card { background: #151f28; padding: 15px; border-radius: 8px; border: 1px solid #232f3b; }
        .status-box { padding: 30px; margin: 20px auto; max-width: 800px; border-radius: 12px; font-size: 1.5rem; font-weight: bold; border: 2px solid #232f3b; transition: 0.5s; }
        .win { background: rgba(46, 204, 113, 0.2); border-color: #2ecc71; color: #2ecc71; }
        .gale { background: rgba(241, 196, 15, 0.2); border-color: #f1c40f; color: #f1c40f; }
        .aguardando { background: #151f28; color: #95a5a6; }
        .velas { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 20px; }
        .vela { padding: 8px 12px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; }
    </style>
</head>
<body>
    <h1 class="header">DOUGOBRASIL V10 - ULTRA ELITE</h1>
    
    <div id="box" class="status-box aguardando">Carregando sinal...</div>

    <div class="grid">
        <div class="card"><small>WINRATE</small><br><strong id="wr">0%</strong></div>
        <div class="card"><small>VITÓRIAS</small><br><strong id="wins">0</strong></div>
        <div class="card"><small>DERROTAS</small><br><strong id="loss">0</strong></div>
        <div class="card"><small>GALE 1/2</small><br><strong id="gales">0 / 0</strong></div>
    </div>

    <div class="card" style="margin-top: 20px; max-width: 800px; margin-left: auto; margin-right: auto;">
        <h3>ÚLTIMOS RESULTADOS</h3>
        <div id="velas" class="velas"></div>
    </div>

    <script>
        async function refresh() {
            const r = await fetch('/data');
            const d = await r.json();
            
            const box = document.getElementById('box');
            if(d.state.ativo) {
                box.className = 'status-box ' + (d.state.gale > 0 ? 'gale' : 'win');
                box.innerHTML = (d.state.gale > 0 ? '⚠️ ENTRAR GALE ' + d.state.gale : '✅ SINAL CONFIRMADO') + 
                                '<br><small>' + d.state.desc + '</small><br>ALVO: ' + d.state.alvo + 'x';
            } else {
                box.className = 'status-box aguardando';
                box.innerHTML = d.state.desc;
            }

            document.getElementById('wins').innerText = d.stats.vitorias;
            document.getElementById('loss').innerText = d.stats.derrotas;
            document.getElementById('gales').innerText = d.stats.g1_count + ' / ' + d.stats.g2_count;
            
            const total = d.stats.vitorias + d.stats.derrotas;
            document.getElementById('wr').innerText = total > 0 ? ((d.stats.vitorias / total) * 100).toFixed(1) + '%' : '0%';

            document.getElementById('velas').innerHTML = d.state.historico.map(v => {
                let color = v >= 2 ? '#2ecc71' : '#e74c3c';
                if(v >= 5) color = '#9b59b6';
                if(v >= 10) color = '#f1c40f';
                return `<div class="vela" style="background: ${color}; color: ${v >= 10 ? 'black' : 'white'}">${v.toFixed(2)}x</div>`;
            }).join('');
        }
        setInterval(refresh, 2500);
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
