import sys
import os
import time
import threading
from javascript import require, On
from flask import Flask
from colorama import init, Fore, Style

# Flask setup (Render ko active rakhne ke liye)
app = Flask(__name__)
@app.route('/')
def home(): return "MandalBot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

init(autoreset=True)

# Node.js library load karo (Ye sabse stable hai)
try:
    bedrock = require('bedrock-protocol')
except Exception:
    print("Error: Node.js environment missing or bedrock-protocol not found.")

# --- SETTINGS ---
HOST = os.getenv('HOST', 'mynewsearver.aternos.me')
PORT = int(os.getenv('PORT', 25851))
VERSION = os.getenv('VERSION', '1.26.13.1')
USERNAME = os.getenv('USERNAME', 'mandalbot')
OFFLINE = True

class MandalBot:
    def __init__(self):
        self.client = None
        self.is_running = False

    def start(self):
        print(f"{Fore.CYAN}[mandalbot]{Fore.WHITE} Connecting to {HOST}...")
        
        try:
            self.client = bedrock.createClient({
                'host': HOST,
                'port': PORT,
                'username': USERNAME,
                'offline': OFFLINE,
                'version': VERSION
            })

            @On(self.client, 'spawn')
            def on_spawn(pkt):
                print(f"{Fore.GREEN}[mandalbot]{Fore.WHITE} Bot spawned! Starting Jumps...")
                self.is_running = True
                self.jump_loop()

            @On(self.client, 'error')
            def on_error(err):
                print(f"{Fore.RED}[mandalbot] Error: {err}")

            @On(self.client, 'disconnect')
            def on_dist(pkt):
                print(f"{Fore.YELLOW}[mandalbot] Disconnected. Reconnecting...")
                time.sleep(5)
                self.start()

        except Exception as e:
            print(f"Connection Failed: {e}")
            time.sleep(10)
            self.start()

    def jump_loop(self):
        while self.is_running:
            try:
                # Jump Packet
                self.client.queue('player_auth_input', {
                    'pitch': 0, 'yaw': 0,
                    'position': {'x': 0, 'y': 65, 'z': 0},
                    'move_vector': {'x': 0, 'z': 0},
                    'input_data': int(64), # 64 is Jump bit
                    'tick': int(time.time() * 20)
                })
                time.sleep(0.6)
            except:
                self.is_running = False
                break

if __name__ == "__main__":
    # Start Flask for Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Bot
    bot = MandalBot()
    bot.start()
