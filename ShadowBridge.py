import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('shadowbridge.app')

import tkinter as tk
from tkinter import scrolledtext
import pyaudiowpatch as pyaudio
import socket
import threading
import queue
import struct
import json
import os
import re
import sys
import uuid
import logging
import datetime
import time
import traceback
import asyncio

try:
    import websockets
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

try:
    import pystray
    from PIL import Image as PILImage
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    import audioop
    def _scale_volume(data, volume_pct):
        if volume_pct >= 100:
            return data
        return audioop.mul(data, 2, volume_pct / 100.0)
except ImportError:
    def _scale_volume(data, volume_pct):
        if volume_pct >= 100:
            return data
        vol = volume_pct / 100.0
        count = len(data) // 2
        if count == 0:
            return data
        samples = struct.unpack(f"{count}h", data)
        return struct.pack(f"{count}h", *[max(-32768, min(32767, int(s * vol))) for s in samples])

VERSION = "0.3.1"

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

BG     = "#0f0f0f"
BG2    = "#1a1a1a"
BG3    = "#242424"
BORDER = "#2e2e2e"
TEXT   = "#e8e8e8"
MUTED  = "#666666"
GREEN  = "#4ade80"
GREEN2 = "#166534"
RED    = "#f87171"
RED2   = "#7f1d1d"
AMBER  = "#fbbf24"
AMBER2 = "#78350f"
BLUE   = "#60a5fa"
BLUE2  = "#1e3a5f"
DIM    = "#404040"

DARK_PALETTE = {
    'BG': '#0f0f0f', 'BG2': '#1a1a1a', 'BG3': '#242424',
    'BORDER': '#2e2e2e', 'TEXT': '#e8e8e8', 'MUTED': '#666666',
    'GREEN': '#4ade80', 'GREEN2': '#166534',
    'RED': '#f87171', 'RED2': '#7f1d1d',
    'AMBER': '#fbbf24', 'AMBER2': '#78350f',
    'BLUE': '#60a5fa', 'BLUE2': '#1e3a5f',
    'DIM': '#404040',
}

LIGHT_PALETTE = {
    'BG': '#f0f0f0', 'BG2': '#e4e4e4', 'BG3': '#d0d0d0',
    'BORDER': '#b8b8b8', 'TEXT': '#1a1a1a', 'MUTED': '#707070',
    'GREEN': '#16a34a', 'GREEN2': '#dcfce7',
    'RED': '#dc2626', 'RED2': '#fee2e2',
    'AMBER': '#d97706', 'AMBER2': '#fef3c7',
    'BLUE': '#2563eb', 'BLUE2': '#dbeafe',
    'DIM': '#a0a0a0',
}

def _apply_palette(palette):
    global BG, BG2, BG3, BORDER, TEXT, MUTED
    global GREEN, GREEN2, RED, RED2, AMBER, AMBER2, BLUE, BLUE2, DIM
    BG     = palette['BG'];    BG2    = palette['BG2'];  BG3    = palette['BG3']
    BORDER = palette['BORDER']; TEXT  = palette['TEXT']; MUTED  = palette['MUTED']
    GREEN  = palette['GREEN']; GREEN2 = palette['GREEN2']
    RED    = palette['RED'];   RED2   = palette['RED2']
    AMBER  = palette['AMBER']; AMBER2 = palette['AMBER2']
    BLUE   = palette['BLUE'];  BLUE2  = palette['BLUE2']
    DIM    = palette['DIM']
    STATUS_COLORS[STATUS_IDLE]         = MUTED
    STATUS_COLORS[STATUS_ACTIVE]       = GREEN
    STATUS_COLORS[STATUS_ERROR]        = RED
    STATUS_COLORS[STATUS_RECONNECTING] = AMBER

DISCOVERY_PORT = 47777

STATUS_IDLE         = "idle"
STATUS_ACTIVE       = "active"
STATUS_ERROR        = "error"
STATUS_RECONNECTING = "reconnecting"

STATUS_COLORS = {
    STATUS_IDLE:         MUTED,
    STATUS_ACTIVE:       GREEN,
    STATUS_ERROR:        RED,
    STATUS_RECONNECTING: AMBER,
}

APP_DIR  = os.path.join(os.path.expanduser("~"), "Documents", "ShadowBridge")
LOG_DIR  = os.path.join(APP_DIR, "logs")
CFG_FILE = os.path.join(APP_DIR, "config.json")
os.makedirs(LOG_DIR, exist_ok=True)

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)

class ABLogger:
    def __init__(self):
        self.ui_queue = queue.Queue()
        log_file = os.path.join(LOG_DIR, f"shadowbridge_{datetime.date.today()}.log")
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.file_logger = logging.getLogger("shadowbridge")

    def info(self, msg):
        self.file_logger.info(msg)
        self.ui_queue.put(("normal", msg))

    def success(self, msg):
        self.file_logger.info(msg)
        self.ui_queue.put(("green", msg))

    def warning(self, msg):
        self.file_logger.warning(msg)
        self.ui_queue.put(("amber", msg))

    def error(self, msg):
        self.file_logger.error(msg)
        self.ui_queue.put(("red", msg))

logger = ABLogger()

CRASH_LOG = os.path.join(APP_DIR, "crash.log")

def _write_crash_log(text):
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def _excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.error(f"Unhandled exception:\n{msg}")
    _write_crash_log(f"\n[{timestamp}] UNHANDLED EXCEPTION:\n{msg}")
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

DEFAULT_GAMING_CHANNELS = [
    {"id": str(uuid.uuid4()), "name": "Game Audio",   "direction": "out", "device": "Game (Elgato Virtual Audio)",         "port": 5000, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Discord",      "direction": "out", "device": "Discord (Elgato Virtual Audio)",      "port": 5001, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Spotify",      "direction": "out", "device": "Spotify (Elgato Virtual Audio)",      "port": 5002, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Lumia Stream", "direction": "out", "device": "Lumia Stream (Elgato Virtual Audio)", "port": 5003, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "OBS Alerts",   "direction": "in",  "device": "Headset Earphone (CORSAIR VOID ELITE Wireless Gaming Headset)", "port": 5011, "enabled": True},
]

DEFAULT_STREAMING_CHANNELS = [
    {"id": str(uuid.uuid4()), "name": "Game Audio",   "direction": "in",  "device": "Game (Elgato Virtual Audio)",       "port": 5000, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Discord",      "direction": "in",  "device": "VC Audio (Elgato Virtual Audio)",   "port": 5001, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Spotify",      "direction": "in",  "device": "Spotify (Elgato Virtual Audio)",    "port": 5002, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "Lumia Stream", "direction": "in",  "device": "TTS (Elgato Virtual Audio)",        "port": 5003, "enabled": True},
    {"id": str(uuid.uuid4()), "name": "OBS Alerts",   "direction": "out", "device": "OBS Studio (Elgato Virtual Audio)", "port": 5011, "enabled": True},
]

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "unknown"

def load_config():
    try:
        with open(CFG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(cfg):
    try:
        with open(CFG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

def get_next_port(channels):
    used = {c['port'] for c in channels}
    port = 5000
    while port in used:
        port += 1
    return port

def get_loopback_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if '[Loopback]' in info['name']:
            name = info['name'].replace(' [Loopback]', '').strip()
            if name not in seen:
                seen.add(name)
                devices.append(name)   # full name — never truncate here
    return devices

def get_output_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0 and '[Loopback]' not in info['name']:
            name = info['name']        # full name — never truncate here
            if name not in seen:
                seen.add(name)
                devices.append(name)
    return devices

def find_loopback(pa, name):
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and '[Loopback]' in info['name']:
            return i
    return None

def get_input_devices(pa):
    devices = []
    seen = set()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0 and '[Loopback]' not in info['name']:
            name = info['name']
            if name not in seen:
                seen.add(name)
                devices.append(name)
    return devices

def find_input(pa, name):
    best = None
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and info['maxInputChannels'] > 0 and '[Loopback]' not in info['name']:
            if info['defaultSampleRate'] == 48000.0:
                return i
            if best is None:
                best = i
    return best

def find_output(pa, name):
    best = None
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if name in info['name'] and info['maxOutputChannels'] > 0 and '[Loopback]' not in info['name']:
            if info['defaultSampleRate'] == 48000.0:
                return i
            if best is None:
                best = i
    return best

def get_level(data):
    count = len(data) // 2
    if count == 0:
        return 0
    samples = struct.unpack(f"{count}h", data)
    return min(max(abs(s) for s in samples) / 32767.0, 1.0)


class AudioEngine:
    def __init__(self, on_status_change, on_level):
        self.on_status_change = on_status_change
        self.on_level = on_level
        self.running = False
        self.pa = None
        self.streams = {}
        self.pa_streams = {}   # ch_id → live PortAudio stream handle
        self.statuses = {}
        self.stop_events = {}
        self.channel_map = {}
        self.dest_ip = ""
        self.mode = 'gaming'
        self.watchdog_thread = None

    def start(self, channels, dest_ip, mode='gaming'):
        if self.running:
            return
        self.running = True
        self.dest_ip = dest_ip
        self.mode = mode
        self.pa = pyaudio.PyAudio()
        self.channel_map = {ch['id']: ch for ch in channels}
        logger.success(f"Audio engine starting — destination: {dest_ip}, mode: {mode}")
        for ch in channels:
            if ch['enabled']:
                self._start_channel(ch)
        self.watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self.watchdog_thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Step 1 — signal all stream threads to stop.
        for ev in self.stop_events.values():
            ev.set()
        # Step 2 — force-stop every live PA stream from this thread so that any
        # blocking stream.read() or stream.write() call in the worker thread
        # unblocks immediately.  This must happen BEFORE the joins below.
        for ch_id, pa_stream in list(self.pa_streams.items()):
            try:
                pa_stream.stop_stream()
            except Exception:
                logger.error(f"engine.stop(): force stop_stream({ch_id}) error:\n{traceback.format_exc()}")
        # Step 3 — join every stream thread.  Track whether they all exited;
        # pa.terminate() is only safe when no PA calls are still in flight.
        all_stopped = True
        for ch_id, t in list(self.streams.items()):
            t.join(timeout=5)
            if t.is_alive():
                logger.warning(f"engine.stop(): stream thread {ch_id} did not exit — skipping pa.terminate() to avoid segfault.")
                all_stopped = False
        self.streams.clear()
        self.stop_events.clear()
        self.pa_streams.clear()
        # Step 4 — join the watchdog.
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            logger.info("engine.stop(): waiting for watchdog thread to exit...")
            self.watchdog_thread.join(timeout=8)
            if self.watchdog_thread.is_alive():
                logger.warning("engine.stop(): watchdog did not exit within timeout.")
        self.statuses.clear()
        self.channel_map.clear()
        # Step 5 — terminate PortAudio only when every thread exited cleanly.
        if self.pa:
            if all_stopped:
                time.sleep(0.1)  # drain any in-flight C-layer callbacks
                try:
                    self.pa.terminate()
                except Exception:
                    logger.error(f"engine.stop(): pa.terminate() error:\n{traceback.format_exc()}")
            else:
                logger.warning("engine.stop(): pa.terminate() skipped — thread(s) still alive.")
            self.pa = None
        logger.info("Audio engine stopped.")

    def _start_channel(self, ch):
        ev = threading.Event()
        self.stop_events[ch['id']] = ev
        self._set_status(ch['id'], STATUS_IDLE)
        t = threading.Thread(target=self._run_channel, args=(ch, ev), daemon=True)
        t.start()
        self.streams[ch['id']] = t

    def _set_status(self, ch_id, status):
        self.statuses[ch_id] = status
        self.on_status_change(ch_id, status)

    def _run_channel(self, ch, stop_ev):
        try:
            if ch['direction'] == "out":
                self._stream_out(ch['id'], ch['name'], ch['device'], ch['port'], stop_ev)
            elif ch['direction'] == "mic":
                # Streaming PC: capture from input device, send over network.
                # Gaming PC:    receive from network, play to output device.
                if self.mode == 'streaming':
                    self._stream_mic(ch['id'], ch['name'], ch['device'], ch['port'], stop_ev)
                else:
                    self._stream_in(ch['id'], ch['name'], ch['device'], ch['port'], stop_ev)
            else:
                self._stream_in(ch['id'], ch['name'], ch['device'], ch['port'], stop_ev)
        except Exception as e:
            logger.error(f"Channel '{ch['name']}' fatal error: {e}")
            self._set_status(ch['id'], STATUS_ERROR)

    def _stream_out(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            idx = find_loopback(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': loopback not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': sending → {self.dest_ip}:{port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            # frames_per_buffer=256 (~5 ms at 48 kHz) so each read() returns
            # quickly and stop_ev is checked frequently.
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=48000,
                input=True, input_device_index=idx, frames_per_buffer=256
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                data = stream.read(256, exception_on_overflow=False)
                data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                self.on_level(ch_id, get_level(data))
                sock.sendto(data, (self.dest_ip, port))
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def _stream_mic(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            idx = find_input(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': input device not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': mic sending → {self.dest_ip}:{port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=48000,
                input=True, input_device_index=idx, frames_per_buffer=256
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                data = stream.read(256, exception_on_overflow=False)
                data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                self.on_level(ch_id, get_level(data))
                sock.sendto(data, (self.dest_ip, port))
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def _stream_in(self, ch_id, name, device, port, stop_ev):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.bind(("0.0.0.0", port))
            idx = find_output(self.pa, device)
            if idx is None:
                logger.error(f"'{name}': output not found for '{device}'")
                self._set_status(ch_id, STATUS_ERROR)
                return
            logger.success(f"'{name}': receiving ← port {port}")
            self._set_status(ch_id, STATUS_ACTIVE)
            stream = self.pa.open(
                format=pyaudio.paInt16, channels=2, rate=48000,
                output=True, output_device_index=idx, frames_per_buffer=1024
            )
            self.pa_streams[ch_id] = stream
            while not stop_ev.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                    if stop_ev.is_set():
                        break
                    data = _scale_volume(data, self.channel_map[ch_id].get('volume', 100))
                    self.on_level(ch_id, get_level(data))
                    stream.write(data)
                except socket.timeout:
                    continue
            self.pa_streams.pop(ch_id, None)
            stream.stop_stream()
            time.sleep(0.05)
            stream.close()
        except Exception as e:
            self.pa_streams.pop(ch_id, None)
            logger.error(f"'{name}' error: {e}")
            self._set_status(ch_id, STATUS_ERROR)
        finally:
            sock.close()
            self.on_level(ch_id, 0)

    def start_channel(self, ch):
        """Start a single channel while the engine is running (for TOGGLE_CHANNEL)."""
        if not self.running:
            return
        ch_id = ch['id']
        self.channel_map[ch_id] = ch
        if ch_id in self.streams and self.streams[ch_id].is_alive():
            return
        self._start_channel(ch)

    def stop_channel(self, ch_id):
        """Stop a single channel while the engine is running (for TOGGLE_CHANNEL)."""
        if ch_id in self.stop_events:
            self.stop_events[ch_id].set()
        if ch_id in self.pa_streams:
            try:
                self.pa_streams[ch_id].stop_stream()
            except Exception:
                pass
        self._set_status(ch_id, STATUS_IDLE)

    def _watchdog(self):
        logger.info("Watchdog active.")
        while self.running:
            time.sleep(5)
            if not self.running:
                break
            try:
                for ch_id, thread in list(self.streams.items()):
                    if not thread.is_alive() and self.running:
                        status = self.statuses.get(ch_id)
                        if status in (STATUS_ACTIVE, STATUS_RECONNECTING):
                            ch = self.channel_map.get(ch_id)
                            if ch:
                                logger.warning(f"'{ch['name']}' dropped — reconnecting in 3s...")
                                self._set_status(ch_id, STATUS_RECONNECTING)
                                time.sleep(3)
                                if self.running:
                                    self._start_channel(ch)
                                    logger.success(f"'{ch['name']}' reconnected.")
            except Exception:
                # pa may have been terminated mid-reconnect; exit cleanly.
                logger.error(f"Watchdog caught exception (engine stopping):\n{traceback.format_exc()}")
                break
        logger.info("Watchdog exited.")


class PeerDiscovery:
    ANNOUNCE_INTERVAL = 5.0
    PEER_TIMEOUT      = 15.0

    def __init__(self, get_announce_data, on_peer_found, on_peer_lost, on_port_sync, on_command=None):
        self.get_announce_data = get_announce_data
        self.on_peer_found     = on_peer_found
        self.on_peer_lost      = on_peer_lost
        self.on_port_sync      = on_port_sync
        self.on_command        = on_command
        self._running          = False
        self._peer_last_seen   = 0.0
        self._peer_ip          = None
        self._peer_mode        = None
        self._lock             = threading.Lock()

    def start(self):
        if self._running:
            return
        with self._lock:
            self._peer_last_seen = 0.0
            self._peer_ip        = None
            self._peer_mode      = None
        self._running = True
        threading.Thread(target=self._listen_loop,   daemon=True).start()
        threading.Thread(target=self._announce_loop, daemon=True).start()
        threading.Thread(target=self._timeout_loop,  daemon=True).start()

    def stop(self):
        self._running = False

    def is_peer_connected(self):
        with self._lock:
            return self._peer_ip is not None

    def get_peer_info(self):
        with self._lock:
            return self._peer_ip, self._peer_mode

    def send_command(self, dest_ip, cmd):
        try:
            msg = json.dumps({'app': 'ShadowBridge', 'type': 'CMD', 'cmd': cmd})
            encoded = msg.encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(encoded, (dest_ip, DISCOVERY_PORT))
            sock.close()
            logger.info(f"UDP TX CMD:{cmd} → {dest_ip}:{DISCOVERY_PORT} ({len(encoded)}b)")
        except Exception as e:
            logger.error(f"Failed to send {cmd} command: {e}")

    def _announce_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self._running:
            try:
                data = self.get_announce_data()
                data['type'] = 'ANNOUNCE'
                sock.sendto(json.dumps(data).encode(), ('255.255.255.255', DISCOVERY_PORT))
            except Exception as e:
                logger.error(f"Discovery announce: {e}")
            deadline = time.time() + self.ANNOUNCE_INTERVAL
            while self._running and time.time() < deadline:
                time.sleep(0.25)
        try:
            sock.close()
        except:
            pass

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind(('', DISCOVERY_PORT))
        except OSError as e:
            logger.error(f"Discovery: cannot bind port {DISCOVERY_PORT}: {e}")
            return
        local_ip = get_local_ip()
        logger.info(f"Discovery listener bound to 0.0.0.0:{DISCOVERY_PORT}, local_ip={local_ip}")
        while self._running:
            try:
                raw, addr = sock.recvfrom(4096)
                sender_ip = addr[0]
                if sender_ip == local_ip:
                    continue
                try:
                    msg = json.loads(raw.decode())
                except Exception:
                    continue
                if msg.get('app') != 'ShadowBridge':
                    continue  # silently ignore packets from other apps (e.g. old AudioBridge)
                # Log only after confirming this is a ShadowBridge packet.
                logger.info(f"UDP RX {sender_ip}:{addr[1]} → {len(raw)}b: {raw[:120]}")
                msg_type = msg.get('type')
                if msg_type == 'CMD':
                    if self._running and self.on_command and msg.get('cmd'):
                        self.on_command(msg['cmd'], sender_ip)
                    continue
                if msg_type not in ('ANNOUNCE', 'ACK'):
                    continue
                self._handle_message(msg, sender_ip)
            except socket.timeout:
                continue
            except Exception:
                pass
        try:
            sock.close()
        except:
            pass

    def _handle_message(self, msg, sender_ip):
        peer_mode = msg.get('mode')
        channels  = msg.get('channels', [])
        fire_found = False
        with self._lock:
            fire_found           = (self._peer_ip is None)
            self._peer_last_seen = time.time()
            self._peer_ip        = sender_ip
            self._peer_mode      = peer_mode
        if fire_found:
            self.on_peer_found(sender_ip, peer_mode)
        if channels:
            self.on_port_sync(channels)
        if msg.get('type') == 'ANNOUNCE':
            self._send_ack(sender_ip)

    def _send_ack(self, dest_ip):
        try:
            data = self.get_announce_data()
            data['type'] = 'ACK'
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(data).encode(), (dest_ip, DISCOVERY_PORT))
            sock.close()
        except:
            pass

    def _timeout_loop(self):
        while self._running:
            for _ in range(4):          # 4 × 0.5 s = 2 s poll cycle
                time.sleep(0.5)
                if not self._running:
                    return
            if not self._running:
                return
            fire_lost = False
            with self._lock:
                if self._peer_ip is not None:
                    if time.time() - self._peer_last_seen > self.PEER_TIMEOUT:
                        self._peer_ip   = None
                        self._peer_mode = None
                        fire_lost = True
            if fire_lost and self._running:  # don't fire after stop
                self.on_peer_lost()


class WsServer:
    PORT = 8765

    def __init__(self, app):
        self._app            = app
        self._loop           = None
        self._clients        = set()
        self._cached_status  = None   # JSON string, always built on the main thread

    def start(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        try:
            async with websockets.serve(self._handler, "localhost", self.PORT):
                logger.success(f"WS API: ws://localhost:{self.PORT}")
                await asyncio.Future()
        except Exception as e:
            logger.error(f"WsServer: {e}")

    async def _handler(self, ws):
        self._clients.add(ws)
        try:
            if self._cached_status:
                await ws.send("STATUS " + self._cached_status)
            else:
                self._app.root.after(0, self.push_status)
            async for msg in ws:
                self._dispatch(msg.strip())
        except Exception:
            pass
        finally:
            self._clients.discard(ws)

    def _dispatch(self, msg):
        if msg == "START":
            self._app.root.after(0, self._app._start)
        elif msg == "STOP":
            self._app.root.after(0, self._app._stop)
        elif msg.startswith("TOGGLE_CHANNEL "):
            ch_id = msg[len("TOGGLE_CHANNEL "):]
            self._app.root.after(0, lambda cid=ch_id: self._app._toggle_channel(cid))
        elif msg.startswith("SET_VOLUME "):
            parts = msg.split()
            logger.info(f"WS RX: {msg!r}")
            if len(parts) == 3:
                try:
                    vol = max(0, min(100, int(parts[2])))
                    ch_id = parts[1]
                    logger.info(f"SET_VOLUME dispatching: id={ch_id} vol={vol}")
                    self._app.root.after(0, lambda cid=ch_id, v=vol: self._app._set_volume(cid, v))
                except ValueError:
                    logger.warning(f"SET_VOLUME: bad volume value in {msg!r}")
            else:
                logger.warning(f"SET_VOLUME: malformed message {msg!r}")

    def push_status(self):
        """Must be called from the main (tkinter) thread."""
        payload = json.dumps(self._build_status())
        self._cached_status = payload
        if self._loop is None or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast("STATUS " + payload), self._loop
        )

    def _build_status(self):
        channels = []
        for ch in self._app._channels():
            ch_id = ch['id']
            row   = self._app.rows.get(ch_id)
            channels.append({
                "id":      ch_id,
                "name":    ch['name'],
                "enabled": ch.get('enabled', True),
                "volume":  ch.get('volume', 100),
                "level":   round(row.smooth_level, 3) if row else 0.0,
                "status":  self._app.engine.statuses.get(ch_id, STATUS_IDLE),
            })
        return {
            "running":        self._app.engine.running,
            "peer_connected": self._app._discovery.is_peer_connected(),
            "channels":       channels,
        }

    async def _broadcast(self, msg):
        dead = set()
        for ws in list(self._clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead


class ChannelRow(tk.Frame):
    def __init__(self, parent, channel, loopback_devices, output_devices, on_remove, on_change, on_refresh=None, mode='gaming', **kwargs):
        super().__init__(parent, bg=BG2, highlightbackground=BORDER, highlightthickness=1, **kwargs)
        self.channel = channel
        self.on_remove = on_remove
        self.on_change = on_change
        self.on_refresh = on_refresh
        self.mode = mode
        self.level_queue = queue.Queue(maxsize=10)
        self.smooth_level = 0
        self._build(loopback_devices, output_devices)

    def _build(self, loopback_devices, output_devices):
        top = tk.Frame(self, bg=BG2)
        top.pack(fill="x", padx=10, pady=(8, 3))

        self.dot = tk.Label(top, text="●", font=("Segoe UI", 10), bg=BG2, fg=MUTED)
        self.dot.pack(side="left", padx=(0, 6))

        self.status_label = tk.Label(top, text="idle", font=("Segoe UI", 9),
                                      bg=BG2, fg=MUTED, width=13, anchor="w")
        self.status_label.pack(side="left")

        direction = self.channel['direction']
        if direction == "out":
            dir_bg, dir_fg, dir_text = GREEN2, GREEN, "OUT →"
        elif direction == "mic":
            dir_bg, dir_fg, dir_text = AMBER2, AMBER, "MIC ↑"
        else:
            dir_bg, dir_fg, dir_text = BLUE2, BLUE, "← IN"
        self.dir_btn = tk.Button(top, text=dir_text, font=("Segoe UI", 9, "bold"),
                                  bg=dir_bg, fg=dir_fg, padx=6, pady=2,
                                  relief="flat", bd=0, cursor="hand2",
                                  activebackground=dir_bg, activeforeground=dir_fg,
                                  command=self._toggle_direction)
        self.dir_btn.pack(side="left", padx=(4, 8))

        tk.Button(top, text="✕", font=("Segoe UI", 10),
                  bg=BG2, fg=MUTED, relief="flat", bd=0,
                  activebackground=RED2, activeforeground=RED,
                  cursor="hand2",
                  command=lambda: self.on_remove(self.channel['id'])).pack(side="right")
        tk.Button(top, text="ⓘ", font=("Segoe UI", 10),
                  bg=BG2, fg=MUTED, relief="flat", bd=0,
                  activebackground=BG3, activeforeground=TEXT,
                  cursor="hand2",
                  command=self._open_info_popup).pack(side="right", padx=(0, 4))
        _en = self.channel.get('enabled', True)
        self._en_btn = tk.Button(top,
                                  text="ON" if _en else "OFF",
                                  font=("Segoe UI", 8, "bold"),
                                  bg=GREEN2 if _en else BG3,
                                  fg=GREEN if _en else MUTED,
                                  relief="flat", bd=0, cursor="hand2",
                                  activebackground=GREEN2, activeforeground=GREEN,
                                  padx=5, pady=1,
                                  command=self._toggle_enable)
        self._en_btn.pack(side="right", padx=(0, 4))

        self.name_var = tk.StringVar(value=self.channel['name'])
        name_wrap = tk.Frame(top, bg=BG2)
        name_wrap.pack(side="left", fill="x", expand=True, padx=(0, 6))
        name_inner = tk.Frame(name_wrap, bg=BG2)
        name_inner.pack(fill="x")
        tk.Label(name_inner, text="✎", font=("Segoe UI", 9),
                 bg=BG2, fg=MUTED).pack(side="left", padx=(0, 2))
        self._name_entry = tk.Entry(name_inner, textvariable=self.name_var,
                 font=("Segoe UI", 11), bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 highlightthickness=0, width=1)
        self._name_entry.pack(side="left", fill="x", expand=True)
        self.name_var.trace_add("write", lambda *a: self._save_field('name', self.name_var.get()))
        self._name_uline = tk.Canvas(name_wrap, height=2, bg=BG2,
                                      highlightthickness=0, bd=0)
        self._name_uline.pack(fill="x")
        self._name_uline.bind("<Configure>", lambda e: self._draw_name_underline())

        dd_frame = tk.Frame(self, bg=BG2)
        dd_frame.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(dd_frame, text="device:", font=("Segoe UI", 9),
                 bg=BG2, fg=MUTED).pack(side="left", padx=(0, 6))

        current_device = self.channel.get('device', '')
        btn_label = (current_device[:42] + "..." if len(current_device) > 42 else current_device) if current_device else "Select Device"
        self.device_btn = tk.Button(dd_frame, text=btn_label,
                                     font=("Segoe UI", 9), bg=BG3, fg=TEXT,
                                     relief="flat", bd=0, cursor="hand2",
                                     highlightthickness=1, highlightbackground=BORDER,
                                     activebackground=BG2, activeforeground=TEXT,
                                     anchor="w", padx=6,
                                     command=self._open_device_popup)
        self.device_btn.pack(fill="x", expand=True)

        vol_frame = tk.Frame(self, bg=BG2)
        vol_frame.pack(fill="x", padx=10, pady=(0, 2))
        tk.Label(vol_frame, text="vol:", font=("Segoe UI", 8),
                 bg=BG2, fg=MUTED).pack(side="left", padx=(0, 4))
        self.vol_var = tk.IntVar(value=self.channel.get('volume', 100))
        self._vol_pct_lbl = tk.Label(vol_frame,
                                      text=f"{self.channel.get('volume', 100)}%",
                                      font=("Segoe UI", 8), bg=BG2, fg=MUTED,
                                      width=4, anchor="e")
        self._vol_pct_lbl.pack(side="right")
        self._build_vol_canvas(vol_frame)

        adv_toggle_frame = tk.Frame(self, bg=BG2)
        adv_toggle_frame.pack(fill="x", padx=10, pady=(0, 2))
        self._adv_open = False
        self._adv_toggle_lbl = tk.Label(adv_toggle_frame, text="▸ advanced",
                                         font=("Segoe UI", 8), bg=BG2, fg=MUTED,
                                         cursor="hand2")
        self._adv_toggle_lbl.pack(side="left")
        self._adv_toggle_lbl.bind("<Button-1>", lambda e: self._toggle_advanced())

        self._adv_frame = tk.Frame(self, bg=BG2)
        adv_inner = tk.Frame(self._adv_frame, bg=BG2)
        adv_inner.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(adv_inner, text="port:", font=("Segoe UI", 9),
                 bg=BG2, fg=MUTED).pack(side="left")
        self.port_var = tk.StringVar(value=str(self.channel['port']))
        tk.Entry(adv_inner, textvariable=self.port_var,
                 font=("Segoe UI", 10), bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightcolor=MUTED,
                 highlightbackground=BORDER, width=5).pack(side="left", padx=(4, 0))
        self.port_var.trace_add("write", lambda *a: self._save_port())

        self._bar_frame = tk.Frame(self, bg=BG2)
        self._bar_frame.pack(fill="x", padx=0, pady=(4, 0))
        self.canvas = tk.Canvas(self._bar_frame, height=4, bg=BG3, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x")
        self.bar_id = self.canvas.create_rectangle(0, 0, 0, 4, fill=GREEN, outline="")
        self._apply_enable_state()

    def _draw_name_underline(self, color=None):
        if color is None:
            color = MUTED
        w = self._name_uline.winfo_width()
        if w < 2:
            return
        self._name_uline.delete("all")
        x, dash, gap = 0, 4, 3
        while x < w:
            self._name_uline.create_line(x, 1, min(x + dash, w), 1, fill=color, width=1)
            x += dash + gap

    def _build_vol_canvas(self, parent):
        c = tk.Canvas(parent, height=16, bg=BG2, highlightthickness=0, bd=0, cursor="hand2")
        c.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._vol_canvas = c

        def _redraw(w=None):
            if w is None:
                w = c.winfo_width()
            if w < 4:
                return
            v = self.vol_var.get()
            cx = int(v / 100 * (w - 12)) + 6
            cy = 8
            c.delete("all")
            c.create_rectangle(6, cy - 2, w - 6, cy + 2, fill=BG3, outline="")
            c.create_rectangle(6, cy - 2, cx, cy + 2, fill=MUTED, outline="")
            c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=TEXT, outline="")

        self._vol_redraw = _redraw
        c.bind("<Configure>", lambda e: _redraw(e.width))

        def _set_from_x(ex):
            w = c.winfo_width()
            if w < 4:
                return
            v = max(0, min(100, int((ex - 6) / max(w - 12, 1) * 100)))
            self.vol_var.set(v)
            self._on_volume_change(v)

        c.bind("<Button-1>", lambda e: _set_from_x(e.x))
        c.bind("<B1-Motion>", lambda e: _set_from_x(e.x))

    def _save_field(self, key, value):
        self.channel[key] = value
        self.on_change()

    def _save_port(self):
        try:
            self.channel['port'] = int(self.port_var.get())
            self.on_change()
        except:
            pass

    def _toggle_enable(self):
        self.channel['enabled'] = not self.channel.get('enabled', True)
        self._apply_enable_state()
        self.on_change()

    def _apply_enable_state(self):
        enabled = self.channel.get('enabled', True)
        dim = DIM
        if enabled:
            self.configure(highlightbackground=BORDER)
            self._en_btn.config(text="ON", bg=GREEN2, fg=GREEN,
                                 activebackground=GREEN2, activeforeground=GREEN)
            self.dot.config(fg=MUTED)
            self.status_label.config(fg=MUTED)
            self._name_entry.config(fg=TEXT, state="normal")
            self.device_btn.config(fg=TEXT, state="normal")
            self._vol_pct_lbl.config(fg=MUTED)
            self._adv_toggle_lbl.config(fg=MUTED)
            self._draw_name_underline()
        else:
            self.configure(highlightbackground=BG3)
            self._en_btn.config(text="OFF", bg=BG3, fg=MUTED,
                                 activebackground=RED2, activeforeground=RED)
            self.dot.config(fg=dim)
            self.status_label.config(fg=dim)
            self._name_entry.config(fg=dim, state="disabled")
            self.device_btn.config(fg=dim, state="disabled")
            self._vol_pct_lbl.config(fg=dim)
            self._adv_toggle_lbl.config(fg=dim)
            self._draw_name_underline(color=dim)

    def _on_volume_change(self, val):
        v = int(float(val))
        self.channel['volume'] = v
        self._vol_pct_lbl.config(text=f"{v}%")
        self._vol_redraw()
        self.on_change()

    def set_volume(self, vol: int) -> None:
        """Update slider position and label from an external source (e.g. WS command)."""
        self.vol_var.set(vol)
        self._vol_pct_lbl.config(text=f"{vol}%")
        self._vol_redraw()

    def _toggle_advanced(self):
        self._adv_open = not self._adv_open
        if self._adv_open:
            self._adv_frame.pack(fill="x", before=self._bar_frame)
            self._adv_toggle_lbl.config(text="▾ advanced")
        else:
            self._adv_frame.pack_forget()
            self._adv_toggle_lbl.config(text="▸ advanced")

    def _open_info_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Channel Info")
        popup.geometry("340x210")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="CHANNEL INFO", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 12))

        def info_row(label, value, value_fg=TEXT, mono=False):
            f = tk.Frame(popup, bg=BG)
            f.pack(fill="x", padx=16, pady=2)
            tk.Label(f, text=label, font=("Segoe UI", 9),
                     bg=BG, fg=MUTED, width=12, anchor="w").pack(side="left")
            vfont = ("Courier New", 9) if mono else ("Segoe UI", 9)
            tk.Label(f, text=value, font=vfont,
                     bg=BG, fg=value_fg, anchor="w").pack(side="left")

        ch = self.channel
        _dir_fg_map   = {"out": GREEN, "mic": AMBER, "in": BLUE}
        _dir_text_map = {"out": "OUT →", "mic": "MIC ↑", "in": "← IN"}
        dir_fg     = _dir_fg_map.get(ch['direction'], MUTED)
        cur_status = self.status_label.cget("text")
        status_fg  = STATUS_COLORS.get(cur_status, MUTED)

        info_row("name",      ch.get('name', '—'))
        info_row("direction", _dir_text_map.get(ch['direction'], ch['direction']), dir_fg)
        info_row("device",    ch.get('device') or '—')
        info_row("port",      str(ch.get('port', '—')), mono=True)
        info_row("volume",    f"{ch.get('volume', 100)}%")
        info_row("status",    cur_status, status_fg)

        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(12, 0))
        tk.Button(popup, text="CLOSE", font=("Segoe UI", 9, "bold"),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=6).pack(pady=12, padx=16, fill="x")

    def _toggle_direction(self):
        old_dir = self.channel['direction']
        ch_name = self.channel.get('name', '?')
        ch_id   = self.channel.get('id', '?')
        logger.info(f"_toggle_direction START — channel='{ch_name}' id={ch_id} old_dir='{old_dir}'")
        try:
            # Step 1 — compute new direction
            if old_dir == "out":
                new_dir = "in"
            elif old_dir == "in":
                new_dir = "mic"
            else:
                new_dir = "out"
            logger.info(f"_toggle_direction [1/6] new_dir='{new_dir}'")

            # Step 2 — write new direction into channel dict
            self.channel['direction'] = new_dir
            logger.info(f"_toggle_direction [2/6] channel dict updated, direction now='{self.channel['direction']}'")

            # Step 3 — update button appearance
            if new_dir == "out":
                dir_bg, dir_fg, dir_text = GREEN2, GREEN, "OUT →"
            elif new_dir == "mic":
                dir_bg, dir_fg, dir_text = AMBER2, AMBER, "MIC ↑"
            else:
                dir_bg, dir_fg, dir_text = BLUE2, BLUE, "← IN"
            self.dir_btn.config(text=dir_text, bg=dir_bg, fg=dir_fg,
                                 activebackground=dir_bg, activeforeground=dir_fg)
            logger.info(f"_toggle_direction [3/6] dir_btn updated to '{dir_text}'")

            # Step 4 — clear device selection
            self.channel['device'] = ""
            self.device_btn.config(text="Select Device")
            logger.info(f"_toggle_direction [4/6] device cleared")

            # Step 5 — save config via on_change callback
            logger.info(f"_toggle_direction [5/6] calling on_change() to save config")
            self.on_change()
            logger.info(f"_toggle_direction [5/6] on_change() returned — verifying saved direction")
            # Confirm the channel dict still holds the right value after save
            saved_dir = self.channel.get('direction', '<missing>')
            if saved_dir != new_dir:
                logger.error(f"_toggle_direction [5/6] CONFIG MISMATCH after save: expected '{new_dir}', got '{saved_dir}'")
            else:
                logger.info(f"_toggle_direction [5/6] config OK — direction='{saved_dir}'")

            # Step 6 — rebuild channel rows via on_refresh
            if self.on_refresh:
                logger.info(f"_toggle_direction [6/6] calling on_refresh() to rebuild channel rows")
                self.on_refresh()
                logger.info(f"_toggle_direction [6/6] on_refresh() returned")
            else:
                logger.info(f"_toggle_direction [6/6] on_refresh is None — skipping row rebuild")

            logger.info(f"_toggle_direction DONE — '{ch_name}' is now '{new_dir}'")

        except Exception:
            logger.error(f"_toggle_direction EXCEPTION (reverting '{ch_name}' to '{old_dir}'):\n{traceback.format_exc()}")
            self.channel['direction'] = old_dir

    def _open_device_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Select Device")
        popup.geometry("440x320")
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.grab_set()

        tk.Label(popup, text="SELECT DEVICE", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        list_frame = tk.Frame(popup, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        lb = tk.Listbox(list_frame, font=("Segoe UI", 9),
                        bg=BG2, fg=TEXT, selectbackground=BG3, selectforeground=GREEN,
                        relief="flat", bd=0, highlightthickness=1,
                        highlightbackground=BORDER, activestyle="none")
        sb_scroll = tk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        self._popup_devices = []

        def populate():
            try:
                pa = pyaudio.PyAudio()
            except Exception:
                logger.error(f"_open_device_popup: PyAudio init failed:\n{traceback.format_exc()}")
                return
            try:
                direction = self.channel['direction']
                if direction == "out":
                    devs = get_loopback_devices(pa)
                elif direction == "mic":
                    # Streaming PC captures from a real input device (Wave XLR).
                    # Gaming PC plays received mic audio to an output device.
                    devs = get_input_devices(pa) if self.mode == 'streaming' else get_output_devices(pa)
                elif direction == "in":
                    devs = get_output_devices(pa)
                else:
                    logger.error(f"_open_device_popup: unknown direction '{direction}'")
                    devs = []
            except Exception:
                logger.error(f"_open_device_popup: device enumeration failed:\n{traceback.format_exc()}")
                devs = []
            finally:
                pa.terminate()
            self._popup_devices = devs  # full names — used when saving to config
            lb.delete(0, tk.END)
            for d in devs:
                lb.insert(tk.END, d[:60] + '...' if len(d) > 60 else d)  # truncate display only
            current = self.channel.get('device', '')
            if current in devs:
                idx = devs.index(current)
                lb.selection_set(idx)
                lb.see(idx)

        def select():
            sel = lb.curselection()
            if not sel:
                return
            device = self._popup_devices[sel[0]]   # always the full, untruncated name
            self.channel['device'] = device         # store full name in config
            label = device[:42] + "..." if len(device) > 42 else device  # display only
            self.device_btn.config(text=label)
            self.on_change()
            popup.destroy()

        populate()
        lb.bind("<Double-Button-1>", lambda e: select())

        bf = tk.Frame(popup, bg=BG)
        bf.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(bf, text="SELECT", font=("Segoe UI", 9, "bold"),
                  bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                  cursor="hand2", command=select,
                  padx=8, pady=5).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="REFRESH", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=populate,
                  padx=8, pady=5).pack(side="left", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=popup.destroy,
                  padx=8, pady=5).pack(side="left")

    def set_status(self, status):
        color = STATUS_COLORS.get(status, MUTED)
        self.dot.config(fg=color)
        self.status_label.config(text=status, fg=color)

    def set_level(self, level):
        try:
            self.level_queue.put_nowait(level)
        except:
            pass

    def update_level(self):
        target = self.smooth_level
        while not self.level_queue.empty():
            try:
                target = self.level_queue.get_nowait()
            except:
                pass
        self.smooth_level = self.smooth_level * 0.7 + target * 0.3
        w = self.canvas.winfo_width()
        if w < 2:
            w = 400
        filled = int(self.smooth_level * w)
        self.canvas.coords(self.bar_id, 0, 0, filled, 4)
        color = RED if self.smooth_level > 0.85 else (AMBER if self.smooth_level > 0.6 else GREEN)
        self.canvas.itemconfig(self.bar_id, fill=color)


class SettingsPanel(tk.Toplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.title("Settings — ShadowBridge")
        self.geometry("420x360")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.cfg = cfg
        self.on_save = on_save
        self._build()

    def _build(self):
        tk.Label(self, text="SETTINGS", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=(20, 4))
        tk.Frame(self, height=1, bg=BORDER).pack(fill="x", padx=20, pady=(4, 16))

        def field(label, var):
            f = tk.Frame(self, bg=BG)
            f.pack(fill="x", padx=20, pady=5)
            tk.Label(f, text=label, font=("Segoe UI", 10),
                     bg=BG, fg=MUTED, width=20, anchor="w").pack(side="left")
            tk.Entry(f, textvariable=var, font=("Segoe UI", 10),
                     bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat",
                     highlightthickness=1, highlightcolor=MUTED,
                     highlightbackground=BORDER).pack(side="left", fill="x", expand=True)

        self.gaming_ip_var    = tk.StringVar(value=self.cfg.get('gaming_ip',    '192.168.4.225'))
        self.streaming_ip_var = tk.StringVar(value=self.cfg.get('streaming_ip', '192.168.4.224'))

        field("Gaming PC IP:", self.gaming_ip_var)
        field("Streaming PC IP:", self.streaming_ip_var)

        tk.Label(self, text=f"This PC detected as: {get_local_ip()}",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w", padx=20, pady=(10, 0))

        theme_row = tk.Frame(self, bg=BG)
        theme_row.pack(fill="x", padx=20, pady=(12, 0))
        tk.Label(theme_row, text="Appearance:", font=("Segoe UI", 10),
                 bg=BG, fg=MUTED, width=20, anchor="w").pack(side="left")
        self.theme_var = tk.StringVar(value=self.cfg.get('theme', 'dark'))
        btn_frame = tk.Frame(theme_row, bg=BG)
        btn_frame.pack(side="left")

        def _refresh_theme_btns():
            t = self.theme_var.get()
            self._dark_btn.config(bg=BG3 if t == 'dark' else BG2,
                                   fg=TEXT if t == 'dark' else MUTED)
            self._light_btn.config(bg=BG3 if t == 'light' else BG2,
                                    fg=TEXT if t == 'light' else MUTED)

        t0 = self.cfg.get('theme', 'dark')
        self._dark_btn = tk.Button(btn_frame, text="Dark", font=("Segoe UI", 9),
                                    bg=BG3 if t0 == 'dark' else BG2,
                                    fg=TEXT if t0 == 'dark' else MUTED,
                                    relief="flat", bd=0, padx=10, pady=3,
                                    cursor="hand2",
                                    command=lambda: [self.theme_var.set('dark'), _refresh_theme_btns()])
        self._dark_btn.pack(side="left", padx=(0, 2))
        self._light_btn = tk.Button(btn_frame, text="Light", font=("Segoe UI", 9),
                                     bg=BG3 if t0 == 'light' else BG2,
                                     fg=TEXT if t0 == 'light' else MUTED,
                                     relief="flat", bd=0, padx=10, pady=3,
                                     cursor="hand2",
                                     command=lambda: [self.theme_var.set('light'), _refresh_theme_btns()])
        self._light_btn.pack(side="left")

        tk.Frame(self, height=1, bg=BORDER).pack(fill="x", padx=20, pady=16)

        bf = tk.Frame(self, bg=BG)
        bf.pack(fill="x", padx=20)
        tk.Button(bf, text="SAVE", font=("Segoe UI", 10, "bold"),
                  bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                  activebackground="#14532d", cursor="hand2",
                  command=self._save, pady=8).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(bf, text="CANCEL", font=("Segoe UI", 10, "bold"),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=self.destroy, pady=8).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _save(self):
        self.cfg['gaming_ip']    = self.gaming_ip_var.get().strip()
        self.cfg['streaming_ip'] = self.streaming_ip_var.get().strip()
        self.cfg['theme']        = self.theme_var.get()
        self.on_save(self.cfg)
        self.destroy()


class ShadowBridgeApp:
    def __init__(self):
        self.cfg  = load_config()
        self.rows = {}
        self._log_popup_text  = None
        self._streams_active  = False
        self._app_alive       = True
        self._shutting_down   = False
        self._init_config()
        self.engine = AudioEngine(
            on_status_change=self._on_status_change,
            on_level=self._on_level
        )
        self._build_ui()
        self._setup_tray()
        self._discovery = PeerDiscovery(
            get_announce_data=self._get_announce_data,
            on_peer_found=self._on_peer_found,
            on_peer_lost=self._on_peer_lost,
            on_port_sync=self._on_port_sync,
            on_command=self._on_remote_command,
        )
        self._discovery.start()
        self._ws_server = WsServer(self) if WS_AVAILABLE else None
        if not WS_AVAILABLE:
            logger.warning("websockets not installed — Stream Deck WS API disabled.")
        self._refresh_channels()

    def _init_config(self):
        local_ip = get_local_ip()
        if 'gaming_ip' not in self.cfg:
            self.cfg['gaming_ip']    = '192.168.4.225'
        if 'streaming_ip' not in self.cfg:
            self.cfg['streaming_ip'] = '192.168.4.224'
        if 'mode' not in self.cfg:
            if local_ip == self.cfg['gaming_ip']:
                self.cfg['mode'] = 'gaming'
            elif local_ip == self.cfg['streaming_ip']:
                self.cfg['mode'] = 'streaming'
            else:
                self.cfg['mode'] = 'gaming'
        if 'gaming_channels' not in self.cfg:
            self.cfg['gaming_channels'] = DEFAULT_GAMING_CHANNELS
        if 'streaming_channels' not in self.cfg:
            self.cfg['streaming_channels'] = DEFAULT_STREAMING_CHANNELS
        if 'theme' not in self.cfg:
            self.cfg['theme'] = 'dark'
        _apply_palette(LIGHT_PALETTE if self.cfg['theme'] == 'light' else DARK_PALETTE)
        self._migrate_channel_devices()
        save_config(self.cfg)

    def _migrate_channel_devices(self):
        for key in ('gaming_channels', 'streaming_channels'):
            for ch in self.cfg.get(key, []):
                device = ch.get('device', '')
                if device and _UUID_RE.match(device):
                    logger.warning(
                        f"Channel '{ch.get('name', '?')}': device field contained "
                        f"a UUID — cleared (please re-select the device)."
                    )
                    ch['device'] = ''

    def _channels(self):
        return self.cfg.get(f"{self.cfg['mode']}_channels", [])

    def _dest_ip(self):
        if self.cfg['mode'] == 'gaming':
            return self.cfg.get('streaming_ip', '192.168.4.224')
        return self.cfg.get('gaming_ip', '192.168.4.225')

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.report_callback_exception = self._on_tk_exception
        self.root.title("ShadowBridge")
        self.root.geometry("960x720")
        self.root.resizable(True, True)
        self.root.minsize(800, 560)
        self.root.configure(bg=BG)

        try:
            self.root.iconbitmap(resource_path('audiobridge_icon.ico'))
            self.root.wm_iconbitmap(resource_path('audiobridge_icon.ico'))
        except:
            pass
        self.root.after(100, self._set_taskbar_icon)

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(header, text="SHADOWBRIDGE", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text=f"v{VERSION}", font=("Segoe UI", 9),
                 bg=BG, fg=MUTED).pack(side="left", padx=(8, 0), pady=(4, 0))

        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        tk.Button(right, text="⚙ settings", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  activebackground=BG2, activeforeground=TEXT,
                  cursor="hand2", command=self._open_settings,
                  padx=8, pady=4).pack(side="right", padx=(4, 0))
        tk.Button(right, text="log", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  activebackground=BG2, activeforeground=TEXT,
                  cursor="hand2", command=self._open_log_popup,
                  padx=8, pady=4).pack(side="right", padx=(4, 0))
        self.mode_btn = tk.Button(right, text="", font=("Segoe UI", 9, "bold"),
                                   relief="flat", bd=0, cursor="hand2",
                                   command=self._switch_mode, padx=10, pady=4)
        self.mode_btn.pack(side="right")

        tk.Frame(self.root, height=1, bg=BORDER).pack(fill="x", padx=20, pady=(8, 0))

        sb = tk.Frame(self.root, bg=BG2)
        sb.pack(fill="x")
        self.peer_dot = tk.Label(sb, text="●", font=("Segoe UI", 9), bg=BG2, fg=MUTED)
        self.peer_dot.pack(side="left", padx=(20, 5), pady=6)
        self.peer_label = tk.Label(sb, text="searching for peer...",
                                    font=("Segoe UI", 9), bg=BG2, fg=MUTED)
        self.peer_label.pack(side="left", pady=6)
        tk.Label(sb, text="│", font=("Segoe UI", 9), bg=BG2, fg=BORDER).pack(side="left", padx=12, pady=6)
        self.status_ip_label = tk.Label(sb, text="", font=("Segoe UI", 9), bg=BG2, fg=MUTED)
        self.status_ip_label.pack(side="left", pady=6)
        tk.Frame(self.root, height=1, bg=BORDER).pack(fill="x")

        cols = tk.Frame(self.root, bg=BG)
        cols.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # ── Left column – Outgoing (green) ───────────────────────────────────
        left_col = tk.Frame(cols, bg=BG)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        left_hdr = tk.Frame(left_col, bg=BG)
        left_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(left_hdr, text="OUTGOING", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=GREEN).pack(side="left")
        tk.Button(left_hdr, text="+ add", font=("Segoe UI", 9),
                  bg=BG3, fg=GREEN, relief="flat", bd=0,
                  activebackground=GREEN2, activeforeground=GREEN,
                  cursor="hand2", command=lambda: self._add_channel("out"),
                  padx=6, pady=2).pack(side="right")
        tk.Frame(left_col, height=1, bg=GREEN2).pack(fill="x", pady=(0, 4))

        left_outer = tk.Frame(left_col, bg=BG)
        left_outer.pack(fill="both", expand=True)
        self.out_canvas = tk.Canvas(left_outer, bg=BG, highlightthickness=0, bd=0)
        out_sb = tk.Scrollbar(left_outer, orient="vertical", command=self.out_canvas.yview)
        self.out_frame = tk.Frame(self.out_canvas, bg=BG)
        self.out_frame.bind("<Configure>", lambda e: self.out_canvas.configure(
            scrollregion=self.out_canvas.bbox("all")))
        _out_win = self.out_canvas.create_window((0, 0), window=self.out_frame, anchor="nw")
        self.out_canvas.bind("<Configure>", lambda e: self.out_canvas.itemconfig(_out_win, width=e.width))
        self.out_canvas.configure(yscrollcommand=out_sb.set)
        self.out_canvas.pack(side="left", fill="both", expand=True)
        out_sb.pack(side="right", fill="y")

        # ── Right column – Incoming (blue) ───────────────────────────────────
        right_col = tk.Frame(cols, bg=BG)
        right_col.pack(side="left", fill="both", expand=True, padx=(6, 0))

        right_hdr = tk.Frame(right_col, bg=BG)
        right_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(right_hdr, text="INCOMING", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=BLUE).pack(side="left")
        tk.Button(right_hdr, text="+ add", font=("Segoe UI", 9),
                  bg=BG3, fg=BLUE, relief="flat", bd=0,
                  activebackground=BLUE2, activeforeground=BLUE,
                  cursor="hand2", command=lambda: self._add_channel("in"),
                  padx=6, pady=2).pack(side="right")
        tk.Frame(right_col, height=1, bg=BLUE2).pack(fill="x", pady=(0, 4))

        right_outer = tk.Frame(right_col, bg=BG)
        right_outer.pack(fill="both", expand=True)
        self.in_canvas = tk.Canvas(right_outer, bg=BG, highlightthickness=0, bd=0)
        in_sb = tk.Scrollbar(right_outer, orient="vertical", command=self.in_canvas.yview)
        self.in_frame = tk.Frame(self.in_canvas, bg=BG)
        self.in_frame.bind("<Configure>", lambda e: self.in_canvas.configure(
            scrollregion=self.in_canvas.bbox("all")))
        _in_win = self.in_canvas.create_window((0, 0), window=self.in_frame, anchor="nw")
        self.in_canvas.bind("<Configure>", lambda e: self.in_canvas.itemconfig(_in_win, width=e.width))
        self.in_canvas.configure(yscrollcommand=in_sb.set)
        self.in_canvas.pack(side="left", fill="both", expand=True)
        in_sb.pack(side="right", fill="y")

        tk.Frame(self.root, height=1, bg=BORDER).pack(fill="x", padx=20, pady=8)

        bf = tk.Frame(self.root, bg=BG)
        bf.pack(fill="x", padx=20)
        self.btn_start = tk.Button(bf, text="START ALL",
                                    font=("Segoe UI", 11, "bold"),
                                    bg=GREEN2, fg=GREEN, relief="flat", bd=0,
                                    activebackground="#14532d", activeforeground=GREEN,
                                    cursor="hand2", command=self._start, pady=10)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_stop = tk.Button(bf, text="STOP ALL",
                                   font=("Segoe UI", 11, "bold"),
                                   bg=BG3, fg=MUTED, relief="flat", bd=0,
                                   activebackground=RED2, activeforeground=RED,
                                   cursor="hand2", command=self._stop, pady=10,
                                   state=tk.DISABLED)
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.text_log = scrolledtext.ScrolledText(
            self.root, height=0, font=("Segoe UI", 9),
            state=tk.DISABLED, bg=BG2, fg=MUTED,
            relief="flat", bd=0, padx=10, pady=0,
            insertbackground=TEXT
        )
        self.text_log.tag_config("green",  foreground=GREEN)
        self.text_log.tag_config("red",    foreground=RED)
        self.text_log.tag_config("amber",  foreground=AMBER)
        self.text_log.tag_config("normal", foreground=MUTED)

        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._update_mode_ui()

    def _set_taskbar_icon(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            icon_path = resource_path('audiobridge_icon.ico')
            icon_handle = ctypes.windll.user32.LoadImageW(
                0, icon_path, 1, 0, 0, 0x00000010 | 0x00000040)
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon_handle)
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, icon_handle)
        except:
            pass

    def _update_mode_ui(self):
        mode = self.cfg['mode']
        local = get_local_ip()
        if mode == 'gaming':
            self.mode_btn.config(text="GAMING PC", bg=GREEN2, fg=GREEN,
                                  activebackground="#14532d", activeforeground=GREEN)
            dest = self.cfg.get('streaming_ip', '?')
            self.status_ip_label.config(text=f"this pc: {local}   →   streaming pc: {dest}")
            self.root.title("ShadowBridge — Gaming PC")
        else:
            self.mode_btn.config(text="STREAMING PC", bg=BLUE2, fg=BLUE,
                                  activebackground="#1e3a8a", activeforeground=BLUE)
            dest = self.cfg.get('gaming_ip', '?')
            self.status_ip_label.config(text=f"this pc: {local}   →   gaming pc: {dest}")
            self.root.title("ShadowBridge — Streaming PC")

    def _refresh_channels(self):
        channels = self._channels()
        logger.info(f"_refresh_channels START — {len(channels)} channel(s) in config: "
                    + ", ".join(f"'{c.get('name','?')}' dir={c.get('direction','?')}" for c in channels))

        # Enumerate devices BEFORE touching the UI so that a PyAudio failure
        # never leaves the channel list blank.
        try:
            logger.info("_refresh_channels [1] initialising PyAudio for device enumeration")
            pa_temp   = pyaudio.PyAudio()
            loopbacks = get_loopback_devices(pa_temp)
            outputs   = get_output_devices(pa_temp)
            pa_temp.terminate()
            logger.info(f"_refresh_channels [1] OK — {len(loopbacks)} loopback(s), {len(outputs)} output(s)")
        except Exception:
            logger.error(f"_refresh_channels [1] PyAudio enumeration failed — channels unchanged:\n{traceback.format_exc()}")
            return

        logger.info("_refresh_channels [2] destroying existing row widgets")
        for w in self.out_frame.winfo_children():
            w.destroy()
        for w in self.in_frame.winfo_children():
            w.destroy()
        self.rows.clear()
        logger.info("_refresh_channels [2] rows cleared")

        mode = self.cfg.get('mode', 'gaming')

        # OUT → left column always.
        # MIC → left column on streaming PC (it captures and sends),
        #        right column on gaming PC (it receives and plays).
        # IN  → right column always.
        out_channels = [ch for ch in channels if ch.get('direction') == 'out']
        mic_channels = [ch for ch in channels if ch.get('direction') == 'mic']
        in_channels  = [ch for ch in channels if ch.get('direction') == 'in']
        mic_frame    = self.out_frame if mode == 'streaming' else self.in_frame
        logger.info(f"_refresh_channels [3] mode={mode} buckets — out={len(out_channels)} mic={len(mic_channels)} in={len(in_channels)} mic→{'out_frame' if mode == 'streaming' else 'in_frame'}")

        def _build_row(ch, parent):
            ch_name = ch.get('name', '?')
            ch_dir  = ch.get('direction', '?')
            ch_id   = ch.get('id', '?')
            logger.info(f"_refresh_channels [3] building '{ch_name}' dir='{ch_dir}'")
            try:
                row = ChannelRow(
                    parent, ch, loopbacks, outputs,
                    on_remove=self._remove_channel,
                    on_change=self._save_channels,
                    on_refresh=self._refresh_channels,
                    mode=mode,
                )
                row.pack(fill="x", pady=3)
                self.rows[ch_id] = row
                logger.info(f"_refresh_channels [3] '{ch_name}' OK")
            except Exception:
                logger.error(f"_refresh_channels [3] FAILED '{ch_name}' dir='{ch_dir}':\n{traceback.format_exc()}")

        for ch in out_channels:
            _build_row(ch, self.out_frame)

        if mic_channels and mode == 'streaming':
            # Streaming PC: mic channels capture and send — shown in outgoing
            # column beneath OUT rows with an amber "MIC INPUTS" divider.
            sep = tk.Frame(self.out_frame, bg=BG)
            sep.pack(fill="x", pady=(8, 0))
            tk.Frame(sep, height=1, bg=AMBER2).pack(fill="x")
            lbl_row = tk.Frame(sep, bg=BG)
            lbl_row.pack(fill="x", pady=(4, 2))
            tk.Label(lbl_row, text="MIC INPUTS", font=("Segoe UI", 8, "bold"),
                     bg=BG, fg=AMBER).pack(side="left")
            for ch in mic_channels:
                _build_row(ch, self.out_frame)

        for ch in in_channels:
            _build_row(ch, self.in_frame)

        if mic_channels and mode == 'gaming':
            # Gaming PC: mic channels receive and play — shown in incoming
            # column beneath IN rows with an amber "MIC INPUTS" divider.
            sep = tk.Frame(self.in_frame, bg=BG)
            sep.pack(fill="x", pady=(8, 0))
            tk.Frame(sep, height=1, bg=AMBER2).pack(fill="x")
            lbl_row = tk.Frame(sep, bg=BG)
            lbl_row.pack(fill="x", pady=(4, 2))
            tk.Label(lbl_row, text="MIC INPUTS", font=("Segoe UI", 8, "bold"),
                     bg=BG, fg=AMBER).pack(side="left")
            for ch in mic_channels:
                _build_row(ch, self.in_frame)

        logger.info(f"_refresh_channels DONE — {len(self.rows)} row(s) registered in self.rows")

        # Force both canvases to recalculate scroll regions after all widgets
        # have been packed. update_idletasks() flushes geometry propagation so
        # bbox("all") returns the true content size.
        for canvas in (self.out_canvas, self.in_canvas):
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _save_channels(self):
        mode = self.cfg.get('mode', '?')
        channels = self.cfg.get(f'{mode}_channels', [])
        snapshot = [(c.get('name','?'), c.get('direction','?')) for c in channels]
        logger.info(f"_save_channels: writing config — mode={mode}, channels={snapshot}")
        save_config(self.cfg)
        logger.info("_save_channels: config written")

    def _add_channel(self, direction="out"):
        if self.engine.running:
            logger.warning("Stop all streams before adding channels.")
            return
        channels = self._channels()
        new_ch = {
            "id":        str(uuid.uuid4()),
            "name":      f"Channel {len(channels) + 1}",
            "direction": direction,
            "device":    "",
            "port":      get_next_port(channels),
            "volume":    100,
            "enabled":   True
        }
        channels.append(new_ch)
        save_config(self.cfg)
        self._refresh_channels()
        logger.info(f"Added channel: {new_ch['name']}")

    def _remove_channel(self, ch_id):
        if self.engine.running:
            logger.warning("Stop all streams before removing channels.")
            return
        mode = self.cfg['mode']
        self.cfg[f'{mode}_channels'] = [c for c in self._channels() if c['id'] != ch_id]
        save_config(self.cfg)
        self._refresh_channels()
        logger.info("Channel removed.")

    def _switch_mode(self):
        if self.engine.running:
            logger.warning("Stop all streams before switching mode.")
            return
        self.cfg['mode'] = 'streaming' if self.cfg['mode'] == 'gaming' else 'gaming'
        save_config(self.cfg)
        self._update_mode_ui()
        self._refresh_channels()
        logger.info(f"Switched to {self.cfg['mode'].upper()} PC mode.")

    def _open_settings(self):
        old_theme = self.cfg.get('theme', 'dark')
        def on_save(new_cfg):
            self.cfg.update(new_cfg)
            save_config(self.cfg)
            if self.cfg.get('theme', 'dark') != old_theme:
                self._apply_theme(self.cfg['theme'])
            else:
                self._update_mode_ui()
            logger.success("Settings saved.")
        SettingsPanel(self.root, self.cfg, on_save)

    def _apply_theme(self, theme_name):
        old_palette = LIGHT_PALETTE if theme_name == 'dark' else DARK_PALETTE
        new_palette = DARK_PALETTE  if theme_name == 'dark' else LIGHT_PALETTE
        _apply_palette(new_palette)
        color_map = {old_palette[k]: new_palette[k]
                     for k in old_palette if old_palette[k] != new_palette[k]}
        self._retheme_widgets(self.root, color_map)
        self._update_mode_ui()
        self._refresh_channels()

    def _retheme_widgets(self, widget, color_map):
        for attr in ('bg', 'fg', 'highlightbackground', 'highlightcolor',
                     'activebackground', 'activeforeground',
                     'selectbackground', 'selectforeground',
                     'insertbackground', 'disabledforeground'):
            try:
                val = str(widget.cget(attr))
                if val in color_map:
                    widget.configure(**{attr: color_map[val]})
            except tk.TclError:
                pass
        for child in widget.winfo_children():
            self._retheme_widgets(child, color_map)

    def _start(self, send_remote=True):
        self._shutting_down = False   # clear before guard so callbacks re-enable on next start
        if self.engine.running or self._streams_active:
            logger.info(f"_start() called but blocked by guard (engine.running={self.engine.running}, _streams_active={self._streams_active}, send_remote={send_remote})")
            return
        # Guard passed — this log confirms _start() is actually executing.
        logger.info(f"_start(): guards passed, send_remote={send_remote} — proceeding.")
        if not send_remote:
            logger.info("CMD:START: _start() executing — streams not yet active, proceeding")
        if send_remote and not self._discovery.is_peer_connected():
            logger.warning("Peer not connected — remote start command may not be received.")

        logger.info("_start(): step 1 — setting _streams_active = True")
        self._streams_active = True
        self._poll_log()
        self._update_levels()

        logger.info("_start(): step 2 — syncing peer status bar")
        peer_ip, peer_mode = self._discovery.get_peer_info()
        if peer_ip:
            self._update_peer_status(True, peer_ip, peer_mode)

        logger.info("_start(): step 3 — updating buttons")
        self.btn_start.config(state=tk.DISABLED, bg=BG3, fg=MUTED)
        self.btn_stop.config(state=tk.NORMAL, bg=RED2, fg=RED)

        logger.info(f"_start(): step 4 — calling engine.start(), dest={self._dest_ip()}, mode={self.cfg['mode']}, channels={len(self._channels())}")
        self.engine.start(self._channels(), self._dest_ip(), mode=self.cfg['mode'])

        if send_remote:
            logger.info("_start(): step 5 — sending CMD:START to peer.")
            self._discovery.send_command(self._dest_ip(), 'START')
        else:
            logger.info("_start(): step 5 — send_remote=False, NOT sending CMD:START (remote-triggered).")

        if self._ws_server:
            self._ws_server.push_status()
        logger.info("_start(): all steps complete.")

    def _stop(self, send_remote=True):
        logger.info(f"_stop(): called, send_remote={send_remote}")
        # Step 1 — raise shutdown flag; blocks audio-engine callbacks from
        # touching the UI while we tear down. Discovery keeps running so peer
        # callbacks are re-enabled as soon as _shutting_down is cleared below.
        self._shutting_down  = True
        self._streams_active = False
        # Step 2 — send remote command (only when locally triggered).
        try:
            if send_remote:
                logger.info("_stop(): sending CMD:STOP to peer.")
                self._discovery.send_command(self._dest_ip(), 'STOP')
            else:
                logger.info("_stop(): send_remote=False — NOT sending CMD:STOP (remote-triggered).")
        except Exception:
            logger.error(f"_stop() CRASH at send_command:\n{traceback.format_exc()}")
        # Step 3 — update Start/Stop buttons.
        try:
            self.btn_start.config(state=tk.NORMAL, bg=GREEN2, fg=GREEN)
        except Exception:
            logger.error(f"_stop() CRASH at btn_start.config():\n{traceback.format_exc()}")
        try:
            self.btn_stop.config(state=tk.DISABLED, bg=BG3, fg=MUTED)
        except Exception:
            logger.error(f"_stop() CRASH at btn_stop.config():\n{traceback.format_exc()}")
        # Step 4 — reset every channel row.
        try:
            for row in self.rows.values():
                row.set_status(STATUS_IDLE)
                row.set_level(0)
        except Exception:
            logger.error(f"_stop() CRASH at row reset:\n{traceback.format_exc()}")
        # Step 5 — stop audio engine in background (PortAudio terminate is slow).
        try:
            logger.info("_stop(): launching engine.stop() background thread.")
            threading.Thread(target=self.engine.stop, daemon=True).start()
        except Exception:
            logger.error(f"_stop() CRASH at engine.stop() thread launch:\n{traceback.format_exc()}")
        # Step 6 — clear shutdown flag so discovery peer callbacks re-enable.
        # Discovery never stopped, so the peer status bar stays live.
        self._shutting_down = False
        if self._ws_server:
            self._ws_server.push_status()
        logger.info("_stop(): all stop steps completed.")

    def _on_status_change(self, ch_id, status):
        if self._shutting_down or not self._streams_active or not self._app_alive:
            return
        self.root.after(0, lambda: self._apply_status_change(ch_id, status))

    def _apply_status_change(self, ch_id, status):
        if self._shutting_down or not self._streams_active:
            return
        if ch_id in self.rows:
            self.rows[ch_id].set_status(status)
        if self._ws_server:
            self._ws_server.push_status()

    def _on_level(self, ch_id, level):
        if self._shutting_down or not self._streams_active or not self._app_alive:
            return
        if ch_id in self.rows:
            self.rows[ch_id].set_level(level)

    def _on_tk_exception(self, exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"tkinter callback exception:\n{msg}")
        _write_crash_log(f"\n[{timestamp}] TKINTER CALLBACK EXCEPTION:\n{msg}")

    def _poll_log(self):
        if not self._streams_active:
            return  # loop cancelled; _start() will restart it
        while not logger.ui_queue.empty():
            try:
                color, msg = logger.ui_queue.get_nowait()
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                line = f"[{ts}] {msg}\n"
                self.text_log.config(state=tk.NORMAL)
                self.text_log.insert(tk.END, line, color)
                self.text_log.config(state=tk.DISABLED)
                if self._log_popup_text is not None:
                    try:
                        self._log_popup_text.config(state=tk.NORMAL)
                        self._log_popup_text.insert(tk.END, line, color)
                        self._log_popup_text.see(tk.END)
                        self._log_popup_text.config(state=tk.DISABLED)
                    except:
                        self._log_popup_text = None
            except:
                pass
        self.root.after(100, self._poll_log)

    def _update_levels(self):
        if not self._streams_active:
            return  # loop cancelled; _start() will restart it
        for row in self.rows.values():
            row.update_level()
        self.root.after(40, self._update_levels)

    def _copy_log(self):
        content = self.text_log.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        logger.info("Log copied to clipboard.")

    def _open_log_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Log — ShadowBridge")
        popup.geometry("700x420")
        popup.configure(bg=BG)
        popup.resizable(True, True)

        hdr = tk.Frame(popup, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(hdr, text="LOG", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="open log folder", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=lambda: os.startfile(LOG_DIR),
                  padx=6, pady=2).pack(side="right")
        tk.Button(hdr, text="copy log", font=("Segoe UI", 9),
                  bg=BG3, fg=MUTED, relief="flat", bd=0,
                  cursor="hand2", command=self._copy_log,
                  padx=6, pady=2).pack(side="right", padx=(0, 4))
        tk.Frame(popup, height=1, bg=BORDER).pack(fill="x", padx=16, pady=(0, 8))

        log_widget = scrolledtext.ScrolledText(
            popup, font=("Segoe UI", 9),
            state=tk.DISABLED, bg=BG2, fg=MUTED,
            relief="flat", bd=0, padx=10, pady=6,
            insertbackground=TEXT
        )
        log_widget.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        log_widget.tag_config("green",  foreground=GREEN)
        log_widget.tag_config("red",    foreground=RED)
        log_widget.tag_config("amber",  foreground=AMBER)
        log_widget.tag_config("normal", foreground=MUTED)

        existing = self.text_log.get("1.0", tk.END)
        if existing.strip():
            log_widget.config(state=tk.NORMAL)
            log_widget.insert("1.0", existing)
            log_widget.see(tk.END)
            log_widget.config(state=tk.DISABLED)

        self._log_popup_text = log_widget

        def on_close():
            self._log_popup_text = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_close)

    def _hide_to_tray(self):
        self.root.withdraw()
        logger.info("Minimized to tray.")

    def _toggle_window(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self.root.withdraw()

    def _quit_app(self):
        self._app_alive = False
        if self.engine.running:
            self.engine.stop()
        try:
            self._discovery.stop()
        except:
            pass
        try:
            self._tray_icon.stop()
        except:
            pass
        self.root.destroy()

    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        try:
            icon_path = resource_path('audiobridge_icon.ico')
            if os.path.exists(icon_path):
                img = PILImage.open(icon_path).resize((64, 64))
            else:
                img = PILImage.new('RGBA', (64, 64), color=(74, 222, 128, 255))
        except:
            try:
                img = PILImage.new('RGBA', (64, 64), color=(74, 222, 128, 255))
            except:
                return

        def on_show_hide(icon, item):
            self.root.after(0, self._toggle_window)

        def on_quit(icon, item):
            self.root.after(0, self._quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide", on_show_hide, default=True),
            pystray.MenuItem("Quit", on_quit),
        )
        self._tray_icon = pystray.Icon("ShadowBridge", img, "ShadowBridge", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()
        logger.info("System tray initialized.")

    def _get_announce_data(self):
        channels = [{'name': ch['name'], 'port': ch['port']} for ch in self._channels()]
        return {
            'app':      'ShadowBridge',
            'version':  VERSION,
            'mode':     self.cfg['mode'],
            'ip':       get_local_ip(),
            'channels': channels,
        }

    def _on_peer_found(self, peer_ip, peer_mode):
        if self._shutting_down or not self._app_alive:
            return
        self.root.after(0, lambda: self._handle_peer_found(peer_ip, peer_mode))

    def _on_peer_lost(self):
        if self._shutting_down or not self._app_alive:
            return
        self.root.after(0, self._handle_peer_lost)

    def _on_port_sync(self, peer_channels):
        if not self._streams_active or not self._app_alive:
            return
        self.root.after(0, lambda: self._apply_port_sync(peer_channels))

    def _handle_peer_found(self, peer_ip, peer_mode):
        our_mode = self.cfg.get('mode', 'gaming')
        if peer_mode and peer_mode != our_mode:
            ip_key = f"{peer_mode}_ip"
            if self.cfg.get(ip_key) != peer_ip:
                self.cfg[ip_key] = peer_ip
                save_config(self.cfg)
                self._update_mode_ui()
        logger.success(f"Peer discovered: {peer_mode or 'unknown'} PC at {peer_ip}")
        self._update_peer_status(True, peer_ip, peer_mode)
        if self._ws_server:
            self._ws_server.push_status()

    def _handle_peer_lost(self):
        logger.warning("Peer connection lost — searching...")
        self._update_peer_status(False, None, None)
        if self._ws_server:
            self._ws_server.push_status()

    def _apply_port_sync(self, peer_channels):
        if not self._streams_active:
            return
        my_channels = self._channels()
        changed = False
        peer_port_map = {ch['name']: ch['port'] for ch in peer_channels}
        for my_ch in my_channels:
            if my_ch['name'] in peer_port_map:
                new_port = peer_port_map[my_ch['name']]
                if my_ch['port'] != new_port:
                    my_ch['port'] = new_port
                    changed = True
        if changed:
            save_config(self.cfg)
            self._refresh_channels()
            logger.info("Port assignments synced with peer.")

    def _toggle_channel(self, ch_id):
        ch = next((c for c in self._channels() if c['id'] == ch_id), None)
        if ch is None:
            logger.warning(f"TOGGLE_CHANNEL: unknown id {ch_id}")
            return
        ch['enabled'] = not ch.get('enabled', True)
        save_config(self.cfg)
        if ch_id in self.rows:
            self.rows[ch_id]._apply_enable_state()
        if self.engine.running:
            if ch['enabled']:
                self.engine.start_channel(ch)
            else:
                self.engine.stop_channel(ch_id)
        if self._ws_server:
            self._ws_server.push_status()
        logger.info(f"Channel '{ch['name']}' toggled {'ON' if ch['enabled'] else 'OFF'} via WS.")

    def _set_volume(self, ch_id, vol):
        known = [(c['id'], c['name']) for c in self._channels()]
        logger.info(f"_set_volume: looking for id={ch_id!r} among {len(known)} channels: {known}")
        ch = next((c for c in self._channels() if c['id'] == ch_id), None)
        if ch is None:
            logger.warning(f"SET_VOLUME: id {ch_id!r} not found. Known IDs: {[k[0] for k in known]}")
            return
        old_vol = ch.get('volume', 100)
        ch['volume'] = vol
        save_config(self.cfg)
        engine_updated = False
        if self.engine.running and ch_id in self.engine.channel_map:
            self.engine.channel_map[ch_id]['volume'] = vol
            engine_updated = True
        if ch_id in self.rows:
            try:
                self.rows[ch_id].set_volume(vol)
            except Exception:
                pass
        if self._ws_server:
            self._ws_server.push_status()
        logger.success(f"SET_VOLUME applied: '{ch['name']}' {old_vol}% → {vol}% (engine_updated={engine_updated})")

    def _on_remote_command(self, cmd, sender_ip):
        # Called on the discovery listener background thread — delegate immediately.
        self._handle_remote_command(cmd, sender_ip)

    def _handle_remote_command(self, cmd, sender_ip):
        # Called from the discovery background thread.
        # Only schedule UI work via root.after — never call _start/_stop directly here.
        try:
            if not self._app_alive:
                return
            if cmd == 'START':
                logger.info(f"CMD:START received from {sender_ip} — scheduling _start(send_remote=False) on main thread.")
                self.root.after(0, lambda: self._start(send_remote=False))
            elif cmd == 'STOP':
                logger.info(f"CMD:STOP received from {sender_ip} — scheduling _stop(send_remote=False) on main thread.")
                self.root.after(0, lambda: self._stop(send_remote=False))
            else:
                logger.warning(f"Unknown remote command '{cmd}' from {sender_ip} — ignored.")
        except Exception:
            logger.error(f"_handle_remote_command('{cmd}') error:\n{traceback.format_exc()}")

    def _update_peer_status(self, connected, peer_ip, peer_mode):
        if connected:
            self.peer_dot.config(fg=GREEN)
            mode_str = f"{peer_mode} pc" if peer_mode else "peer"
            self.peer_label.config(
                text=f"{mode_str}   {peer_ip}   connected", fg=GREEN)
        else:
            self.peer_dot.config(fg=MUTED)
            self.peer_label.config(text="searching for peer...", fg=MUTED)

    def run(self):
        logger.success(f"ShadowBridge v{VERSION} started.")
        logger.info(f"Mode: {self.cfg['mode'].upper()} PC")
        logger.info(f"This PC: {get_local_ip()}")
        logger.info(f"Config: {CFG_FILE}")
        logger.info(f"Logs:   {LOG_DIR}")
        if self._ws_server:
            self._ws_server.start()
        try:
            self.root.mainloop()
        except Exception:
            logger.error(f"tkinter mainloop crashed:\n{traceback.format_exc()}")
            sys.exit(1)


if __name__ == "__main__":
    app = ShadowBridgeApp()
    app.run()