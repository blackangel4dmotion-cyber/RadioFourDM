import os
import sys
import re
import time
import urllib.request
import urllib.parse
import subprocess
from bs4 import BeautifulSoup
import imageio_ffmpeg
from tts_engine import generate_speech_file_sync, CACHE_DIR

NEWS_INTRO_FILE = os.path.join(CACHE_DIR, "news_intro.mp3")

# Ensure news intro chime jingle exists; create if not
def ensure_news_intro_jingle():
    if not os.path.exists(NEWS_INTRO_FILE):
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg,
                '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
                '-filter_complex', 'sine=frequency=880:duration=0.1[b1];sine=frequency=880:duration=0.1[b2];sine=frequency=1174:duration=0.3[b3];sine=frequency=587:duration=1.8[pad];[b2]adelay=180|180[d2];[b3]adelay=360|360[d3];[pad]adelay=360|360[dpad];[b1][d2][d3][dpad]amix=inputs=4,volume=2.0[aout]',
                '-map', '[aout]',
                '-t', '2.5',
                '-acodec', 'libmp3lame',
                '-b:a', '128k',
                '-y', NEWS_INTRO_FILE
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[News] Error generating news intro jingle: {e}")

ensure_news_intro_jingle()

def fetch_quick_news() -> dict:
    """
    Scrapes the real-time 'එසැණ පුවත්' (Quick / Latest Flash News) directly.
    STRICT REQUIREMENT: Absolutely no website names (e.g. Lankadeepa, Ada Derana) are preserved or spoken.
    Returns dictionary with unique id, headline, concise body, url, and timestamp.
    """
    url = 'https://www.lankadeepa.lk'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')

        items = []
        for elem in soup.find_all(string=lambda t: t and 'එසැණ' in t):
            container = elem.find_parent(['div', 'section', 'aside'])
            if container:
                for a in container.find_all('a', href=True):
                    href = a['href']
                    if '/latest_news/' in href:
                        txt = a.get_text(strip=True)
                        if txt and len(txt) > 5 and txt != 'එසැණ පුවත්':
                            items.append((href, txt))

        if not items:
            return None

        first_href, first_title = items[0]
        m = re.search(r'(\d+-\d+|\d+)$', first_href)
        news_id = m.group(1) if m else first_href

        # Fetch article body
        parsed = urllib.parse.urlsplit(first_href)
        encoded_path = urllib.parse.quote(parsed.path)
        full_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))

        req2 = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            html2 = resp2.read().decode('utf-8', errors='ignore')
        soup2 = BeautifulSoup(html2, 'html.parser')

        body = ''
        for p in soup2.find_all('p'):
            txt = p.get_text(strip=True)
            txt = re.sub(r'^\s*\([^\)]*\)\s*', '', txt) # Strip author byline in parenthesis
            if len(txt) > 20:
                body = txt
                break

        # STRICT: Strip out any website name or brand
        clean_headline = re.sub(r'ලංකාදීප|Lankadeepa|lankadeepa\.lk|අද දෙරණ|Ada Derana', '', first_title, flags=re.I).strip(' -:|')
        clean_body = re.sub(r'ලංකාදීප|Lankadeepa|lankadeepa\.lk|අද දෙරණ|Ada Derana', '', body, flags=re.I).strip(' -:|')

        # Take first 1-2 concise sentences for quick news
        sentences = [s.strip() for s in re.split(r'[.।]', clean_body) if len(s.strip()) > 10]
        short_body = (sentences[0] + ".") if sentences else clean_body

        return {
            'id': news_id,
            'headline': clean_headline,
            'body': short_body,
            'full_body': clean_body,
            'url': first_href,
            'fetched_at': time.strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"[News] Error fetching quick news: {e}")
        return None

# Backwards compatibility alias
fetch_adaderana_main_news = fetch_quick_news

def build_news_broadcast_audio(news_data: dict) -> str:
    """
    Synthesizes quick flash news in 100% pure Sinhala with Gemini Live Voice.
    Strictly identifies the station as 'Radio Four D M' and never mentions any website name.
    Prepends the official Radio Four D M breaking news chime jingle.
    """
    headline = news_data.get('headline', '')
    body = news_data.get('body', '')

    script = (
        f"Radio Four D M විශේෂ පුවත් නිවේදනයක්. "
        f"{headline}. "
        f"{body} "
        f"වැඩිදුර තොරතුරු සඳහා දිගටම රැඳී සිටින්න Radio Four D M අපගේ සජීවී විකාශය සමඟින්."
    )

    # Synthesize news speech using Gemini Live Native AI Voice
    speech_path = generate_speech_file_sync(
        text=script,
        voice_key="si-female",
        lang="si",
        provider="gemini",
        filename_prefix="quick_news",
        add_chime=False
    )

    out_file = os.path.join(CACHE_DIR, f"news_final_{int(time.time()*1000)}.mp3")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Prepend news jingle if exists
    if os.path.exists(NEWS_INTRO_FILE) and os.path.exists(speech_path):
        try:
            cmd = [
                ffmpeg_exe,
                "-i", NEWS_INTRO_FILE,
                "-i", speech_path,
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                "-map", "[out]",
                "-acodec", "libmp3lame",
                "-b:a", "128k",
                "-y", out_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.remove(speech_path)
            except Exception:
                pass
            return out_file
        except Exception as e:
            print(f"[News] Error combining jingle: {e}")
            return speech_path

    return speech_path
