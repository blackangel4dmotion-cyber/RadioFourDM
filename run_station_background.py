import os
import sys
import time
import re
import json
import socket
import subprocess
import ctypes
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY = os.path.join(BASE_DIR, "app.py")
NGROK_EXE = os.path.join(BASE_DIR, "ngrok.exe")
LINKS_FILE = os.path.join(BASE_DIR, "RADIO_LIVE_LINKS.txt")
STATION_LOG = os.path.join(BASE_DIR, "station.log")
ASSIGNED_NGROK_URL = "https://brilliant-roving-provoke.ngrok-free.dev"

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
    except Exception:
        pass

def show_popup(msg: str, title: str = "Radio 4DM Online"):
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40 | 0x1000)
    except Exception:
        pass

def main():
    lan_ip = get_lan_ip()
    lan_url = f"http://{lan_ip}:8000"
    
    # Clean proxy environment for ngrok agent
    ngrok_env = os.environ.copy()
    for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        ngrok_env.pop(k, None)

    # 1. Start Station Engine (app.py) writing to station.log
    python_exe = sys.executable
    s_log = open(STATION_LOG, "w", encoding="utf-8")
    station_proc = subprocess.Popen(
        [python_exe, APP_PY],
        cwd=BASE_DIR,
        stdout=s_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

    time.sleep(3)

    # 2. Start ngrok tunnel with user's permanent static domain
    tunnel_proc = None
    public_url = ASSIGNED_NGROK_URL

    if os.path.exists(NGROK_EXE):
        try:
            tunnel_proc = subprocess.Popen(
                [NGROK_EXE, "http", "8000", "--url", ASSIGNED_NGROK_URL],
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=ngrok_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception as e:
            print(f"Ngrok start error: {e}")

    # Save to file
    content = f"""============================================================
📻 RADIO 4DM - WORLDWIDE ONLINE & WI-FI BROADCAST LINKS
============================================================

🌐 1. WORLDWIDE ONLINE LINK (Mobile 4G/5G, Tablet, Any PC in the World):
   {public_url}
   *(ලෝකයේ ඕනෑම තැනක සිට මෙම Link එකෙන් Radio එකට සම්බන්ධ විය හැක)*

📱 2. LOCAL WI-FI LINK (Connected to this Home/Office Wi-Fi):
   {lan_url}
   *(ගෙදර Wi-Fi එකේදී කිසිදු ප්‍රමාදයකින් තොරව සෘජුවම සම්බන්ධ වේ)*

💻 3. THIS PC LOCALHOST LINK:
   http://localhost:8000

============================================================
• Ultra-Lightweight: Background එකේ 100% නිහඬව දුවයි.
• Zero Window: Normal PC වැඩ වලට කිසිදු බාධාවක් නැත.
• 24/7 Live: PC එක On කර ඇති තාක් Radio එක නොනවත්වාම විකාශය වේ.
• To Stop Station: "STOP_RADIO.bat" double click කරන්න.
============================================================
"""
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    # Create Desktop shortcut / .url
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop):
            url_file = os.path.join(desktop, "Radio 4DM Studio (Online).url")
            with open(url_file, "w") as f:
                f.write(f"[InternetShortcut]\nURL={public_url}\n")
    except Exception:
        pass

    # Copy link to clipboard
    copy_to_clipboard(public_url)

    # Show pleasant success popup
    msg = f"🎉 Radio 4DM Worldwide Station එක සාර්ථකව Active විය!\n\n🌐 Worldwide Online Link (Mobile 4G & Anywhere):\n{public_url}\n\n📱 Local Wi-Fi Link:\n{lan_url}\n\n(Online Link එක Clipboard එකට Copy කර ඇත. Mobile Phone එකෙන් හෝ ඕනෑම Device එකකින් Open කර බලන්න!)"
    show_popup(msg, "Radio 4DM - Online Worldwide")

    # Keep running forever until terminated
    try:
        while True:
            time.sleep(5)
            if station_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        pass
    finally:
        station_proc.terminate()
        if tunnel_proc:
            tunnel_proc.terminate()
        s_log.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(os.path.join(BASE_DIR, "launcher_error.log"), "w", encoding="utf-8") as f:
            import traceback
            traceback.print_exc(file=f)
