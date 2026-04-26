import sys
import os
import time
import threading
from javascript import require, On
from flask import Flask
from colorama import init, Fore

app = Flask(__name__)
@app.route('/')
def home(): return "MandalBot is Online!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

init(autoreset=True)

# --- SETTINGS ---
HOST = os.getenv('HOST', 'mynewsearver.aternos.me')
PORT = int(os.getenv('PORT', 25851))
VERSION = os.getenv('VERSION', '1.26.13.1')
USERNAME = os.getenv('USERNAME', 'mandalbot')

def start_bot():
    try:
        # Library load karne ki koshish
        print(f"{Fore.CYAN}[mandalbot]{Fore.WHITE} Loading Node.js components...")
        bedrock = require('bedrock-protocol')
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Node.js ya bedrock-protocol nahi mila! Render settings check karein.")
        return # Agar library nahi hai toh aage mat badho

    print(f"{Fore.CYAN}[mandalbot]{Fore.WHITE} Connecting to {HOST}...")
    
    try:
        client = bedrock.createClient({
            'host': HOST,
            'port': PORT,
            'username': USERNAME,
            'offline': True,
            'version': VERSION
        })

        @On(client, 'spawn')
        def on_spawn(pkt):
            print(f"{Fore.GREEN}[mandalbot]{Fore.WHITE} Bot spawned! Jump active.")
            while True:
                try:
                    client.queue('player_auth_input', {
                        'pitch': 0, 'yaw': 0,
                        'position': {'x': 0, 'y': 65, 'z': 0},
                        'move_vector': {'x': 0, 'z': 0},
                        'input_data': int(64),
                        'tick': int(time.time() * 20)
                    })
                    time.sleep(0.6)
                except: break

        @On(client, 'error')
        def on_error(err):
            print(f"{Fore.RED}[mandalbot] Error: {err}")

        @On(client, 'disconnect')
        def on_dist(pkt):
            print(f"{Fore.YELLOW}[mandalbot] Disconnected. Retrying in 10s...")
            time.sleep(10)
            start_bot()

    except Exception as e:
        print(f"Connection Failed: {e}")
        time.sleep(10)
        start_bot()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
