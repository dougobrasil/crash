import requests
import time
import os
import threading
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from colorama import Fore, Back, Style, init

# Silenciar logs internos para manter o painel limpo
logging.basicConfig(level=logging.CRITICAL)
init(autoreset=True)

# --- CONFIGURAÇÕES DE ACESSO ---
# 1. Cole o seu Token aqui
TELEGRAM_TOKEN = "7512042682:AAEmHzdH0Jen9I8S6sb-OdeDebh5Pb1rkjg"

# 2. Cole o ID do seu Grupo aqui (Ex: -100123456789)
# Use o comando /id no grupo para descobrir o número correto
CHAT_ID_GRUPO = "-1002632966907" 

URL_API = "https://blaze.bet.br/api/singleplayer-originals/originals/crash_games/recent/4"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Bypass-Tunnel-Reminder": "true"
}

# --- ESTADO DO SISTEMA ---
MAX_GALES = 2
stats = {
    "vitorias": 0, "derrotas": 0, 
    "win_15": 0, "win_20": 0, "win_alta": 0,
    "g1_count": 0, "g2_count": 0
}

state = {
    "ativo": False, "gale": 0, "alvo": 2.0, 
    "estrategia": "", "desc": "", 
    "status_conexao": "Iniciando...",
    "status_telegram": "Offline",
    "logs": []
}

loop_telegram = None
application = None

def add_log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    state["logs"].append(f"[{timestamp}] {msg}")
    if len(state["logs"]) > 8:
        state["logs"].pop(0)

# --- FUNÇÕES TELEGRAM ---

async def get_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"📍 ID deste Chat: `{chat_id}`", parse_mode=ParseMode.MARKDOWN)

async def async_broadcast(text):
    if CHAT_ID_GRUPO == "SEU_CHAT_ID_AQUI" or not CHAT_ID_GRUPO:
        add_log("Erro: CHAT_ID_GRUPO não configurado!")
        return
    try:
        await application.bot.send_message(chat_id=CHAT_ID_GRUPO, text=text, parse_mode=ParseMode.MARKDOWN)
        add_log("Mensagem enviada para o grupo.")
    except Exception as e:
        add_log(f"Erro ao enviar: {e}")

def enviar_telegram_sinal(desc, alvo, gale=0):
    if not application: return
    emoji = "🎯" if gale == 0 else "🔄"
    txt = "SINAL IDENTIFICADO" if gale == 0 else f"ENTRAR NO GALE {gale}"
    
    msg = (
        f"{emoji} *{txt}* {emoji}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 *Estratégia:* {desc}\n"
        f"📈 *Alvo:* {alvo:.2f}x\n"
        f"🛡️ *Gales:* {MAX_GALES}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 [ENTRAR NA BLAZE](https://blaze.bet.br/)\n"
    )
    if loop_telegram and loop_telegram.is_running():
        asyncio.run_coroutine_threadsafe(async_broadcast(msg), loop_telegram)
    else:
        add_log("Erro: Loop do Telegram não está pronto.")

def enviar_telegram_resultado(res, alvo, win=True):
    if not application: return
    emoji = "✅" if win else "❌"
    titulo = "GREEN CONFIRMADO!" if win else "LOSS (STOP)"
    modo = "Direta" if state["gale"] == 0 else f"Gale {state['gale']}"
    placar = f"✅ {stats['vitorias']}  |  ❌ {stats['derrotas']}"
    
    msg = (
        f"{emoji} *{titulo}* {emoji}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏁 Vela: *{res:.2f}x*\n"
        f"🎯 Alvo: *{alvo:.2f}x*\n"
        f"🔍 Modo: {modo if win else '---'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 Placar: `{placar}`"
    )
    if loop_telegram and loop_telegram.is_running():
        asyncio.run_coroutine_threadsafe(async_broadcast(msg), loop_telegram)

# --- LÓGICA V10 ORIGINAL ---

def analisar_v10(h):
    if len(h) < 15: return None, 0, ""
    
    densidade_green = (len([x for x in h[:12] if x >= 2.0]) / 12) * 100

    # 🎯 ESTRATÉGIA PARA VELAS ALTAS (5.0x+)
    if all(x < 5.0 for x in h[:10]) and h[0] >= 2.0 and h[1] >= 2.0:
        return "VELA_ROSA", 5.0, "🚀 BUSCA DE VELA ALTA"

    # 🎯 ESTRATÉGIA DE REVERSÃO (2.0x)
    if h[0] < 2.0 and h[1] < 2.0 and h[2] < 2.0:
        return "REVERSÃO", 2.0, "🎯 QUEBRA DE SEQUÊNCIA RED"

    # 🎯 ESTRATÉGIA DE FLUXO (1.5x)
    if h[0] < 2.0 and h[1] >= 2.0 and densidade_green > 40:
        return "FLUXO", 1.5, "🛡️ ENTRADA DE SEGURANÇA"

    # 🎯 PADRÃO ESPELHO DUPLO (2.0x)
    if h[0] < 2.0 and h[1] < 2.0 and h[2] >= 2.0 and h[3] >= 2.0:
        return "ESPELHO", 2.0, "🔄 PADRÃO DE DUPLAS"

    return None, 0, ""

def registrar_resultado(res):
    global stats, state
    win = res >= state["alvo"]
    
    if win:
        stats["vitorias"] += 1
        if state["gale"] == 1: stats["g1_count"] += 1
        elif state["gale"] == 2: stats["g2_count"] += 1
        
        if state["alvo"] >= 5.0: stats["win_alta"] += 1
        elif state["alvo"] >= 2.0: stats["win_20"] += 1
        else: stats["win_15"] += 1
        
        add_log(f"GREEN em {res:.2f}x (Alvo {state['alvo']})")
        enviar_telegram_resultado(res, state["alvo"], True)
        state["ativo"] = False
        state["gale"] = 0
    else:
        if state["gale"] < MAX_GALES:
            state["gale"] += 1
            add_log(f"Entrando Gale {state['gale']}")
            enviar_telegram_sinal(state["desc"], state["alvo"], state["gale"])
        else:
            stats["derrotas"] += 1
            add_log(f"RED em {res:.2f}x")
            enviar_telegram_resultado(res, state["alvo"], False)
            state["ativo"] = False
            state["gale"] = 0

# --- INTERFACE ---

def draw_interface(h):
    os.system('cls' if os.name == 'nt' else 'clear')
    total = stats["vitorias"] + stats["derrotas"]
    wr = (stats["vitorias"] / total * 100) if total > 0 else 0
    
    print(Fore.CYAN + "╔" + "═"*66 + "╗")
    print(Fore.CYAN + "║" + Fore.YELLOW + "      DOUGOBRASIL V10 - PAINEL PROFISSIONAL COM LOGS      " + Fore.CYAN + "║")
    print(Fore.CYAN + "╠" + "═"*32 + "╦" + "═"*33 + "╣")
    print(Fore.CYAN + f"║ PLACAR: {stats['vitorias']}W - {stats['derrotas']}L".ljust(33) + Fore.CYAN + "║" + Fore.WHITE + f" API: {state['status_conexao']}".ljust(33) + Fore.CYAN + "║")
    print(Fore.CYAN + f"║ ASSERT: {wr:.1f}%".ljust(33) + Fore.CYAN + "║" + Fore.WHITE + f" TG: {state['status_telegram']}".ljust(33) + Fore.CYAN + "║")
    print(Fore.CYAN + "╠" + "═"*32 + "╩" + "═"*33 + "╣")
    print(Fore.CYAN + f"║ [1.5x]: {stats['win_15']} | [2.0x]: {stats['win_20']} | [5.0x]: {stats['win_alta']}".center(66) + Fore.CYAN + "║")
    print(Fore.CYAN + "╠" + "═"*66 + "╣")
    
    # Histórico de Velas
    print(Fore.CYAN + "║ ", end="")
    for p in h[:10]:
        cor = Fore.MAGENTA if p >= 10 else (Fore.CYAN if p >= 5 else (Fore.GREEN if p >= 2 else (Fore.YELLOW if p >= 1.5 else Fore.RED)))
        print(f"{cor}{p:.2f}x  ", end="")
    print(Fore.CYAN + "║")
    
    print(Fore.CYAN + "╠" + "═"*66 + "╣")
    if state["ativo"]:
        fundo = Back.YELLOW if state["gale"] > 0 else Back.GREEN
        msg = f" >> {state['desc']} | ALVO: {state['alvo']}x | GALE: {state['gale']} << "
        print(fundo + Fore.BLACK + msg.center(66) + Style.RESET_ALL)
    else:
        print(Fore.WHITE + " AGUARDANDO PADRÃO DE ALTA ASSERTIVIDADE... ".center(66))
    
    print(Fore.CYAN + "╠" + "═"*66 + "╣")
    print(Fore.CYAN + "║" + Fore.YELLOW + " LOGS DO SISTEMA:".ljust(66) + Fore.CYAN + "║")
    for log in state["logs"]:
        print(Fore.CYAN + "║" + Fore.WHITE + f" {log}".ljust(66) + Fore.CYAN + "║")
    for _ in range(8 - len(state["logs"])):
        print(Fore.CYAN + "║".ljust(67) + Fore.CYAN + "║")
    print(Fore.CYAN + "╚" + "═"*66 + "╝")

# --- MONITORAMENTO ---

def obter_dados():
    try:
        response = requests.get(URL_API, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            state["status_conexao"] = "Online"
            return response.json()
        state["status_conexao"] = "Erro HTTP"
        return None
    except:
        state["status_conexao"] = "Erro Conexão"
        return None

def monitor():
    global state
    ultimo_id = None
    add_log("Monitoramento V10 iniciado.")
    
    while True:
        dados = obter_dados()
        if not dados:
            time.sleep(2); continue
            
        try:
            raw = dados.get('records') if isinstance(dados, dict) else dados
            historico = []
            if raw:
                for i in raw:
                    val = i.get('ponto') or i.get('crash_point') or i.get('multiplier')
                    if val and float(val) > 0: historico.append(float(val))
            
            if not historico: continue
            
            if historico[0] != ultimo_id:
                novo_resultado = historico[0]
                if state["ativo"] and ultimo_id is not None:
                    registrar_resultado(novo_resultado)
                
                ultimo_id = novo_resultado
                draw_interface(historico)
                
                if not state["ativo"]:
                    est, alvo, desc = analisar_v10(historico)
                    if est:
                        state.update({"ativo": True, "estrategia": est, "alvo": alvo, "desc": desc, "gale": 0})
                        add_log(f"Sinal Detectado: {desc}")
                        enviar_telegram_sinal(desc, alvo)
                        draw_interface(historico)
        except Exception as e:
            add_log(f"Erro Processamento: {e}")
            
        time.sleep(1)

def run_telegram():
    global application, loop_telegram
    req_config = HTTPXRequest(connect_timeout=60, read_timeout=60)
    
    while True:
        try:
            state["status_telegram"] = "Iniciando..."
            application = Application.builder().token(TELEGRAM_TOKEN).request(req_config).build()
            application.add_handler(CommandHandler("id", get_id_handler))
            
            # Inicializa a aplicação e o loop de forma controlada
            loop_telegram = asyncio.new_event_loop()
            asyncio.set_event_loop(loop_telegram)
            
            # Esta chamada bloqueia o thread, mas o loop_telegram fica ativo para run_coroutine_threadsafe
            state["status_telegram"] = "Online"
            application.run_polling(close_loop=False, drop_pending_updates=True)
        except Exception as e:
            add_log(f"Reiniciando TG: {e}")
            state["status_telegram"] = "Reconectando..."
            time.sleep(10)

if __name__ == "__main__":
    # Inicia o monitor em thread separada
    threading.Thread(target=monitor, daemon=True).start()
    
    # Inicia o Telegram no thread principal
    try:
        run_telegram()
    except KeyboardInterrupt:
        pass
