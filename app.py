from flask import Flask, Response
import requests
import threading
import time
import os

app = Flask(__name__)

# --- CONFIGURAÇÕES E LOGS ---
log_terminal = ["Iniciando DougoBrasil V10 - Ultra Elite..."]
stats = {"v": 0, "d": 0, "g1": 0, "g2": 0}
state = {"ativo": False, "alvo": 2.0, "gale": 0}

def adicionar_log(texto):
    global log_terminal
    timestamp = time.strftime("%H:%M:%S")
    log_terminal.append(f"[{timestamp}] {texto}")
    if len(log_terminal) > 40: # Mantém apenas as últimas 40 linhas
        log_terminal.pop(0)

def monitor_bot():
    global stats, state
    ultimo_id = None
    sessao = requests.Session() # Sessão para manter cookies e evitar bloqueios
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://blaze.bet.br/pt/games/crash"
    }

    while True:
        try:
            res = sessao.get("https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4", headers=headers, timeout=10)
            if res.status_code == 200:
                dados = res.json()
                historico = [float(i['ponto']) for i in dados if 'ponto' in i and i['ponto'] != "0"]
                
                if historico and historico[0] != ultimo_id:
                    novo_res = historico[0]
                    ultimo_id = novo_res
                    adicionar_log(f"Nova Vela: {novo_res:.2f}x | Histórico: {historico[:5]}")

                    # --- Lógica de Resultado ---
                    if state["ativo"]:
                        if novo_res >= state["alvo"]:
                            stats["v"] += 1
                            if state["gale"] > 0: stats[f"g{state['gale']}"] += 1
                            adicionar_log(f"✅ WIN NO ALVO {state['alvo']}x!")
                            state["ativo"] = False
                            state["gale"] = 0
                        else:
                            if state["gale"] < 2:
                                state["gale"] += 1
                                adicionar_log(f"⚠️ LOSS: ENTRANDO GALE {state['gale']}")
                            else:
                                stats["d"] += 1
                                adicionar_log("❌ LOSS TOTAL (GALE 2)")
                                state["ativo"] = False
                                state["gale"] = 0
                    
                    # --- Lógica V10 (Original DougoBrasil) ---
                    if not state["ativo"]:
                        # Exemplo: Estratégia de Reversão (3 reds)
                        if len(historico) >= 3 and all(x < 2.0 for x in historico[:3]):
                            state.update({"ativo": True, "alvo": 2.0, "gale": 0})
                            adicionar_log("🚀 SINAL DETECTADO: QUEBRA DE RED! ALVO 2.0x")
            else:
                adicionar_log(f"⚠️ Erro de API: Status {res.status_code}")
        except Exception as e:
            adicionar_log(f"⚠️ Erro de Conexão: {str(e)}")
        
        time.sleep(3)

# Inicia o bot em segundo plano
threading.Thread(target=monitor_bot, daemon=True).start()

@app.route('/')
def home():
    # Retorna o log como texto puro (Estilo Terminal)
    total = stats["v"] + stats["d"]
    wr = (stats["v"] / total * 100) if total > 0 else 0
    header = f"DOUGOBRASIL V10 - CMD WEB\n"
    header += f"WINS: {stats['v']} | LOSS: {stats['d']} | WR: {wr:.1f}%\n"
    header += f"G1: {stats['g1']} | G2: {stats['g2']}\n"
    header += "="*40 + "\n"
    
    content = "\n".join(reversed(log_terminal)) # Mostra o mais recente no topo
    return Response(header + content, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
