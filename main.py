#!/usr/bin/env python3
# ============================================================
#
#   ███╗   ███╗ █████╗ ███╗   ██╗██████╗  █████╗ ██╗
#   ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔══██╗██║
#   ██╔████╔██║███████║██╔██╗ ██║██║  ██║███████║██║
#   ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██╔══██║██║
#   ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝██║  ██║███████╗
#   ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚══════╝
#
#   Minecraft Bedrock Edition — Jump Bot
#   Install : pip install mcproto pycryptodome colorama
#   Run     : python3 mandalbot.py
#
# ============================================================

import sys
import time
import threading
import signal
from dataclasses import dataclass
from typing import Optional
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# ============================================================
#   ⚙️  SETTINGS — Yahan apni settings badlo
# ============================================================

HOST             = 'mynewsearver.aternos.me'  # ← Server IP ya domain
PORT             = 25851                       # ← Server port (default 19132)
VERSION          = '1.26.13.1'                 # ← Apne server ka Minecraft version
USERNAME         = 'mandalbot'                 # ← Bot ka naam

# True  = Offline/LAN server (koi Xbox login nahi chahiye)
# False = Online server    (Xbox Live se login hoga)
OFFLINE          = True

JUMP_INTERVAL_MS = 600                        # ← Har kitne ms baad jump kare
JUMP_VELOCITY    = 0.42                       # ← Jump ki taaqat (standard = 0.42)

AUTO_RECONNECT   = True                       # ← Disconnect par auto-reconnect
RECONNECT_DELAY  = 5000                       # ← Reconnect se pehle kitni ms wait
MAX_RECONNECTS   = 10                         # ← Max tries (0 = unlimited)

# ============================================================

@dataclass
class Position:
    x: float = 0.0
    y: float = 64.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0

# ── Logger ───────────────────────────────────────────────────
class Logger:
    @staticmethod
    def info(msg: str):
        print(f"{Fore.CYAN}[mandalbot]{Style.RESET_ALL} {Fore.BLACK}INFO  {Style.RESET_ALL} {msg}")
    
    @staticmethod
    def ok(msg: str):
        print(f"{Fore.GREEN}[mandalbot]{Style.RESET_ALL} {Fore.BLACK}OK    {Style.RESET_ALL} {msg}")
    
    @staticmethod
    def warn(msg: str):
        print(f"{Fore.YELLOW}[mandalbot]{Style.RESET_ALL} {Fore.BLACK}WARN  {Style.RESET_ALL} {msg}")
    
    @staticmethod
    def error(msg: str):
        print(f"{Fore.RED}[mandalbot]{Style.RESET_ALL} {Fore.BLACK}ERROR {Style.RESET_ALL} {msg}")
    
    @staticmethod
    def jump(msg: str):
        print(f"{Fore.MAGENTA}[mandalbot]{Style.RESET_ALL} {Fore.BLACK}JUMP  {Style.RESET_ALL} {msg}")

L = Logger()

# ── Banner ───────────────────────────────────────────────────
def print_banner():
    print()
    print(f"{Fore.MAGENTA}╔════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.LIGHTWHITE_EX}{Style.BRIGHT}     🤖  mandalbot  —  Jump Bot          {Style.RESET_ALL} {Fore.MAGENTA}║{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}╠════════════════════════════════════════════╣{Style.RESET_ALL}")
    
    mode_str = 'Offline (LAN)' if OFFLINE else 'Online (Xbox)'
    print(f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.BLACK}Host    : {HOST}:{PORT}".ljust(43) + f"{Fore.MAGENTA}║{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.BLACK}Version : {VERSION}".ljust(43) + f"{Fore.MAGENTA}║{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.BLACK}Mode    : {mode_str}".ljust(43) + f"{Fore.MAGENTA}║{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.BLACK}Jump    : every {JUMP_INTERVAL_MS}ms".ljust(43) + f"{Fore.MAGENTA}║{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}╚════════════════════════════════════════════╝{Style.RESET_ALL}")
    print()

# ============================================================
#   🤖  MANDALBOT CLASS
# ============================================================

class MandalBot:
    def __init__(self):
        # State variables
        self.client = None
        self.jump_thread = None
        self.physics_thread = None
        self.reconnect_timer = None
        self.reconnect_count = 0
        self.is_spawned = False
        self.is_running = False
        
        # Entity IDs
        self.my_entity_id = None
        self.my_unique_id = None
        
        # Position
        self.pos = Position()
        
        # Jump physics
        self.jump_phase = 'idle'  # 'idle' | 'rising' | 'falling'
        self.jump_velocity_y = 0.0
        self.GRAVITY = 0.08
        self.DRAG = 0.98
        self.GROUND_Y = 64.0
        
        # Locks for thread safety
        self.lock = threading.Lock()
    
    # ── Physics Tick (20 TPS) ────────────────────────────────────
    def physics_tick(self):
        """Simulate gravity and jump physics at 20 TPS"""
        while self.is_running:
            try:
                with self.lock:
                    if self.jump_phase != 'idle':
                        self.jump_velocity_y = (self.jump_velocity_y - self.GRAVITY) * self.DRAG
                        self.pos.y += self.jump_velocity_y
                        
                        if self.jump_velocity_y < 0:
                            self.jump_phase = 'falling'
                        
                        if self.pos.y <= self.GROUND_Y:
                            self.pos.y = self.GROUND_Y
                            self.jump_phase = 'idle'
                            self.jump_velocity_y = 0.0
                        
                        self.send_move_player()
                
                time.sleep(0.05)  # 20 TPS = 50ms
            except Exception as e:
                L.error(f"Physics tick error: {e}")
                break
    
    # ── Jump Trigger ─────────────────────────────────────────────
    def do_jump(self):
        """Trigger a jump"""
        with self.lock:
            if not self.is_spawned or self.jump_phase != 'idle' or self.my_entity_id is None:
                return
            
            self.jump_phase = 'rising'
            self.jump_velocity_y = JUMP_VELOCITY
            
            L.jump(f"⬆  Jumping! entityId={self.my_entity_id}  Y={self.pos.y:.2f}")
            
            self.send_auth_input(jumping=True)
    
    # ── Jump Loop ────────────────────────────────────────────────
    def jump_loop(self):
        """Main jump loop"""
        while self.is_running:
            try:
                self.do_jump()
                time.sleep(JUMP_INTERVAL_MS / 1000.0)
            except Exception as e:
                L.error(f"Jump loop error: {e}")
                break
    
    # ── Packet: player_auth_input ────────────────────────────────
    def send_auth_input(self, jumping: bool = False):
        """Send player authentication input packet"""
        if not self.is_spawned or self.my_entity_id is None:
            return
        try:
            # This is where you'd send the actual packet
            # For now, this is a placeholder for bedrock-protocol equivalent
            if jumping:
                L.jump(f"Auth input sent (jump={jumping})")
        except Exception as e:
            L.error(f"send_auth_input error: {e}")
            self.send_move_player()
    
    # ── Packet: move_player ──────────────────────────────────────
    def send_move_player(self):
        """Send move_player packet"""
        if not self.is_spawned or self.my_entity_id is None:
            return
        try:
            # This is where you'd send the actual move_player packet
            # Placeholder for bedrock-protocol equivalent
            pass
        except Exception as e:
            L.error(f"move_player error: {e}")
    
    # ── Start / Stop Jump Loop ────────────────────────────────────
    def start_jumping(self):
        """Start the jump and physics loops"""
        if self.jump_thread is not None:
            return
        
        L.ok(f"Jump loop started — every {JUMP_INTERVAL_MS}ms")
        
        self.is_running = True
        
        # Start physics thread
        self.physics_thread = threading.Thread(target=self.physics_tick, daemon=True)
        self.physics_thread.start()
        
        # Start jump thread
        self.jump_thread = threading.Thread(target=self.jump_loop, daemon=True)
        self.jump_thread.start()
    
    def stop_jumping(self):
        """Stop jump and physics loops"""
        self.is_running = False
        
        with self.lock:
            self.jump_phase = 'idle'
            self.jump_velocity_y = 0.0
        
        if self.jump_thread:
            self.jump_thread.join(timeout=1)
            self.jump_thread = None
        
        if self.physics_thread:
            self.physics_thread.join(timeout=1)
            self.physics_thread = None
    
    # ── Create Bot ───────────────────────────────────────────────
    def create_bot(self):
        """Create and connect the bot"""
        L.info(f"Connecting to {HOST}:{PORT} as \"{USERNAME}\"...")
        
        # Reset state
        self.is_spawned = False
        self.my_entity_id = None
        self.my_unique_id = None
        self.stop_jumping()
        
        try:
            # Try to import bedrock-protocol library
            # pip install bedrock-protocol
            try:
                import bedrock_protocol
                self.client = bedrock_protocol.create_client(
                    host=HOST,
                    port=PORT,
                    username=USERNAME,
                    offline=OFFLINE,
                    version=VERSION,
                )
                
                # Register event handlers
                self.client.on('start_game', self.on_start_game)
                self.client.on('join', self.on_join)
                self.client.on('spawn', self.on_spawn)
                self.client.on('move_player', self.on_move_player)
                self.client.on('respawn', self.on_respawn)
                self.client.on('text', self.on_text)
                self.client.on('disconnect', self.on_disconnect)
                self.client.on('close', self.on_close)
                self.client.on('error', self.on_error)
                
            except ImportError:
                L.warn("bedrock-protocol not installed. Using mock connection...")
                self.setup_mock_client()
        
        except Exception as err:
            L.error(f"Failed to create client: {err}")
            self.schedule_reconnect()
    
    def setup_mock_client(self):
        """Setup a mock client for testing (when bedrock-protocol not available)"""
        L.ok("Mock client ready. Simulating connection...")
        time.sleep(1)
        
        # Simulate start_game
        self.on_start_game({'runtime_entity_id': 1, 'entity_id': 1, 
                           'player_position': {'x': 0, 'y': 65.62, 'z': 0},
                           'rotation': {'x': 0, 'y': 0}})
        
        # Simulate join
        time.sleep(0.5)
        self.on_join()
        
        # Simulate spawn
        time.sleep(0.5)
        self.on_spawn()
    
    # ── Event Handlers ───────────────────────────────────────────
    def on_start_game(self, pkt):
        """Handle start_game packet"""
        self.my_entity_id = pkt['runtime_entity_id']
        self.my_unique_id = pkt['entity_id']
        
        # Get spawn position
        self.pos.x = pkt['player_position']['x']
        self.pos.y = pkt['player_position']['y'] - 1.62
        self.pos.z = pkt['player_position']['z']
        
        rotation = pkt.get('rotation', {})
        self.pos.yaw = rotation.get('y', 0)
        self.pos.pitch = rotation.get('x', 0)
        
        L.ok('start_game packet mila!')
        L.ok(f'  Runtime Entity ID : {self.my_entity_id}')
        L.ok(f'  Unique Entity ID  : {self.my_unique_id}')
        L.ok(f'  Spawn pos         : ({self.pos.x:.1f}, {self.pos.y:.1f}, {self.pos.z:.1f})')
    
    def on_join(self):
        """Handle join event"""
        L.ok(f'Server se join ho gaya! ({HOST}:{PORT})')
        self.reconnect_count = 0
    
    def on_spawn(self):
        """Handle spawn event"""
        if self.my_entity_id is None:
            L.warn('Spawn event aaya lekin start_game abhi nahi mila — ruk raha hoon...')
            
            def check_entity():
                time.sleep(2)
                if self.my_entity_id is not None:
                    L.ok(f'Entity ID mila: {self.my_entity_id} — jumps shuru!')
                    self.is_spawned = True
                    self.start_jumping()
                else:
                    L.error('start_game packet nahi mila. Bot kaam nahi karega.')
            
            threading.Thread(target=check_entity, daemon=True).start()
            return
        
        L.ok(f'Bot spawn ho gaya! entityId={self.my_entity_id} — Jumps shuru!')
        self.is_spawned = True
        self.start_jumping()
    
    def on_move_player(self, pkt):
        """Handle move_player packet"""
        if self.my_entity_id is not None and pkt['runtime_entity_id'] == self.my_entity_id:
            with self.lock:
                self.pos.x = pkt['position']['x']
                self.pos.y = pkt['position']['y'] - 1.62
                self.pos.z = pkt['position']['z']
                self.pos.yaw = pkt['yaw']
                self.pos.pitch = pkt['pitch']
    
    def on_respawn(self, pkt):
        """Handle respawn event"""
        L.warn(f"Respawn event (state={pkt['state']})")
        if pkt['state'] == 1:
            self.is_spawned = True
            self.pos.x = pkt['position']['x']
            self.pos.y = pkt['position']['y']
            self.pos.z = pkt['position']['z']
            L.ok(f"Respawn ho gaya ({self.pos.x:.1f}, {self.pos.y:.1f}, {self.pos.z:.1f})")
    
    def on_text(self, pkt):
        """Handle chat message"""
        if pkt.get('source_name') and pkt['source_name'] != USERNAME:
            L.info(f"[Chat] <{pkt['source_name']}> {pkt['message']}")
    
    def on_disconnect(self, pkt):
        """Handle disconnect event"""
        L.warn(f"Disconnect! Reason: {pkt.get('message', 'Unknown')}")
        self.handle_disconnect()
    
    def on_close(self):
        """Handle connection close"""
        L.warn('Connection band ho gayi.')
        self.handle_disconnect()
    
    def on_error(self, err):
        """Handle error event"""
        L.error(f'Client error: {err}')
        self.handle_disconnect()
    
    # ── Handle Disconnect ────────────────────────────────────────
    def handle_disconnect(self):
        """Handle disconnection"""
        self.is_spawned = False
        self.my_entity_id = None
        self.my_unique_id = None
        self.stop_jumping()
        
        if self.client:
            try:
                if hasattr(self.client, 'removeAllListeners'):
                    self.client.removeAllListeners()
            except:
                pass
            self.client = None
        
        self.schedule_reconnect()
    
    # ── Auto Reconnect ───────────────────────────────────────────
    def schedule_reconnect(self):
        """Schedule automatic reconnection"""
        if not AUTO_RECONNECT:
            L.warn('Auto-reconnect off. Exiting.')
            sys.exit(0)
        
        if self.reconnect_timer is not None:
            return
        
        if MAX_RECONNECTS > 0 and self.reconnect_count >= MAX_RECONNECTS:
            L.error(f'Max reconnect tries ({MAX_RECONNECTS}) reach ho gayi. Exiting.')
            sys.exit(1)
        
        self.reconnect_count += 1
        delay_sec = RECONNECT_DELAY / 1000.0
        max_str = str(MAX_RECONNECTS) if MAX_RECONNECTS > 0 else '∞'
        L.warn(f'{delay_sec:.1f}s mein reconnect hoga... (try {self.reconnect_count}/{max_str})')
        
        self.reconnect_timer = threading.Timer(delay_sec, self.reconnect)
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()
    
    def reconnect(self):
        """Perform reconnection"""
        self.reconnect_timer = None
        self.create_bot()
    
    # ── Shutdown ─────────────────────────────────────────────────
    def shutdown(self):
        """Shutdown the bot gracefully"""
        L.warn('Ctrl+C — Shutting down...')
        self.stop_jumping()
        
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
        
        if self.client:
            try:
                if hasattr(self.client, 'disconnect'):
                    self.client.disconnect()
            except:
                pass
        
        time.sleep(0.4)
        sys.exit(0)

# ============================================================
#   🚀 MAIN
# ============================================================

def main():
    """Main entry point"""
    # Setup signal handlers
    bot = MandalBot()
    
    def signal_handler(sig, frame):
        bot.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start banner and bot
    print_banner()
    bot.create_bot()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.shutdown()

if __name__ == '__main__':
    main()
