import os
import sys
import time
import math
import re
import subprocess
import threading
import queue
import collections
import numpy as np
from typing import Optional, Dict, Any, List
import yt_dlp
import imageio_ffmpeg
from tts_engine import load_config

# Get FFmpeg executable path
import shutil
if shutil.which("ffmpeg"):
    FFMPEG_EXE = shutil.which("ffmpeg")
else:
    try:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_EXE = "ffmpeg"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache")
SILENCE_FILE = os.path.join(CACHE_DIR, "silence.mp3")
try:
    with open(SILENCE_FILE, "rb") as f:
        SILENCE_DATA = f.read()
except Exception:
    SILENCE_DATA = b""

CHUNK_SIZE = 17640 # 100ms of 44100Hz 16-bit Stereo PCM (4410 * 4 bytes)

def resolve_fresh_stream_url(track: Dict[str, Any]) -> str:
    """
    Ensures the stream URL passed to FFmpeg is valid without blocking the live broadcast loop.
    YouTube and SoundCloud direct CDN URLs remain valid for 6+ hours (21600s).
    If existing_url is already present, it is returned instantly with 0ms delay to prevent audio dropouts.
    """
    existing_url = track.get("stream_url", "")
    if existing_url:
        return existing_url

    query = track.get("original_url") or track.get("query") or track.get("title")
    if not query:
        return existing_url

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'source_address': '0.0.0.0',
            'socket_timeout': 4,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entry = info['entries'][0] if ('entries' in info and len(info['entries']) > 0) else info
            if entry and entry.get('url'):
                fresh_url = entry['url']
                track['stream_url'] = fresh_url
                track['http_headers'] = entry.get('http_headers', {})
                track['resolved_at'] = time.time()
                return fresh_url
    except Exception as e:
        print(f"[Deck] Stream URL resolve error: {e}")

    return existing_url

class Deck:
    """Represents a virtual DJ Deck (Deck A or Deck B) with non-blocking pre-buffering."""
    def __init__(self, name: str):
        self.name = name
        self.process: Optional[subprocess.Popen] = None
        self.track: Optional[Dict[str, Any]] = None
        self.volume: float = 0.0 # 0.0 to 1.0
        self.target_volume: float = 0.0
        self.user_gain: float = 1.0 # Manual gain fader
        self.fade_step: float = 0.02 # Change per 100ms
        self.elapsed_sec: float = 0.0
        self.duration_sec: float = 0.0
        self.is_active: bool = False
        self.is_muted: bool = False
        self.current_rms_db: float = -60.0 # Real-time acoustic energy in dBFS
        self.eof_reached: bool = False
        self.audio_queue = queue.Queue(maxsize=50) # ~5 seconds pre-buffer
        self.reader_thread: Optional[threading.Thread] = None
        self.stop_signal = threading.Event()
        self.has_audio_flowing: bool = False
        self.empty_count: int = 0
        self.silence_count: int = 0 # Counts consecutive silent 100ms frames (< -46dB)

    def _reader_worker(self, proc):
        while not self.stop_signal.is_set():
            try:
                data = proc.stdout.read(CHUNK_SIZE)
                if not data or len(data) == 0:
                    rc = proc.poll()
                    print(f"[DJ Deck {self.name}] FFmpeg finished/EOF. Code: {rc}")
                    self.eof_reached = True
                    break
                if len(data) < CHUNK_SIZE:
                    data = data.ljust(CHUNK_SIZE, b"\x00")
                    self.eof_reached = True
                    try:
                        self.audio_queue.put(data, timeout=0.5)
                    except Exception:
                        pass
                    break
                self.has_audio_flowing = True
                try:
                    self.audio_queue.put(data, timeout=0.5)
                except Exception:
                    pass
            except Exception as e:
                print(f"[DJ Deck {self.name}] Reader error: {e}")
                self.eof_reached = True
                break

    def load_and_play(self, track: Dict[str, Any], initial_volume: float = 0.0, target_volume: float = 1.0, fade_duration_sec: float = 5.0):
        self.stop()
        self.track = track
        MAX_TRACK_CAP_SEC = 360.0 # 6 minutes maximum cap (strictly enforced)
        raw_dur = float(track.get("duration", 0) or 0)
        if raw_dur > MAX_TRACK_CAP_SEC or raw_dur <= 0:
            self.duration_sec = MAX_TRACK_CAP_SEC
        else:
            self.duration_sec = raw_dur
        self.elapsed_sec = 0.0
        self.empty_count = 0
        self.silence_count = 0
        self.volume = initial_volume
        self.target_volume = target_volume
        
        steps = max(1, int(fade_duration_sec / 0.100))
        self.fade_step = abs(target_volume - initial_volume) / steps
        self.eof_reached = False
        self.has_audio_flowing = False
        self.stop_signal.clear()
        self.is_active = True

        # Dynamically refresh stream_url so signed tokens never 403
        fresh_url = resolve_fresh_stream_url(track)
        if not fresh_url:
            fresh_url = track.get("stream_url", "")

        headers = dict(track.get("http_headers") or {})
        # Only inject soundcloud referer if it is actually a soundcloud URL
        if "soundcloud.cloud" in fresh_url or "sndcdn.com" in fresh_url:
            if "referer" not in [k.lower() for k in headers.keys()]:
                headers["Referer"] = "https://soundcloud.com/"
        elif "googlevideo.com" in fresh_url or "youtube.com" in fresh_url:
            headers.pop("Referer", None)
            headers.pop("referer", None)
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        header_str = "".join([f"{k}: {v}\r\n" for k, v in headers.items()])

        cmd = [
            FFMPEG_EXE,
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5"
        ]
        if header_str:
            cmd.extend(["-headers", header_str])
        cmd.extend([
            "-i", fresh_url,
            "-vn",
            "-f", "s16le",
            "-ac", "2",
            "-ar", "44100",
            "pipe:1"
        ])
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**6
            )
            self.reader_thread = threading.Thread(target=self._reader_worker, args=(self.process,), daemon=True)
            self.reader_thread.start()
            print(f"[DJ Deck {self.name}] Playing: {track.get('title')} (Duration: {self.duration_sec}s, Target Vol: {target_volume})")
        except Exception as e:
            print(f"[DJ Deck {self.name}] Failed to start: {e}")
            self.is_active = False

    def fade_out(self, duration_sec: float = 5.0):
        self.target_volume = 0.0
        steps = max(1, int(duration_sec / 0.100))
        self.fade_step = (self.volume) / steps if steps > 0 else 0.1
        print(f"[DJ Deck {self.name}] Crossfading OUT over {duration_sec}s...")

    def read_chunk(self) -> bytes:
        if not self.is_active:
            return b"\x00" * CHUNK_SIZE

        # Smooth volume update towards target
        if self.volume < self.target_volume:
            self.volume = min(self.target_volume, self.volume + self.fade_step)
        elif self.volume > self.target_volume:
            self.volume = max(self.target_volume, self.volume - self.fade_step)

        # Check if faded out completely
        if self.target_volume == 0.0 and self.volume <= 0.001:
            self.stop()
            return b"\x00" * CHUNK_SIZE

        try:
            data = self.audio_queue.get_nowait()
            self.elapsed_sec += 0.100
            self.empty_count = 0

            # Strict 6-minute track cap: fade out immediately if track reaches 6 minutes (360 seconds)
            if self.elapsed_sec >= 360.0:
                if self.target_volume > 0.0:
                    print(f"[DJ Deck {self.name}] Reached 6-minute track limit ({self.elapsed_sec:.1f}s). Auto-fading out.")
                    self.fade_out(duration_sec=3.5)

            if data and len(data) >= 100:
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                rms = np.sqrt(np.mean(samples ** 2))
                self.current_rms_db = 20.0 * np.log10(rms / 32768.0 + 1e-6)

                # 1. Soundtrack presence verification (Audible music signal)
                if self.current_rms_db > -46.0 and rms > 120.0:
                    self.has_audio_flowing = True
                    self.silence_count = 0
                else:
                    self.silence_count += 1

                # 2. End-of-song trailing silence check:
                # If track has been playing for at least 6s and 3.0s of continuous silence/dead-air occurs:
                if self.elapsed_sec >= 6.0 and self.silence_count >= 30:
                    if self.target_volume > 0.0 and not self.eof_reached:
                        print(f"[DJ Deck {self.name}] 3.0s trailing silence / dead-air detected (RMS: {self.current_rms_db:.1f} dB). Auto-switching to next track immediately!")
                        self.eof_reached = True
                        self.fade_out(duration_sec=1.2)

            # 3. Soundtrack check at start: If 3.0s elapsed with no valid audio sound, auto-skip immediately
            if self.elapsed_sec >= 3.0 and not self.has_audio_flowing:
                print(f"[DJ Deck {self.name}] No sound track detected within 3.0s! Auto-skipping to next track.")
                self.eof_reached = True
                self.stop()

            return data
        except queue.Empty:
            self.current_rms_db = -60.0
            self.empty_count += 1
            self.silence_count += 1
            # If EOF reached, or if stream stalls/delivers no audio for 3.0s (30 cycles of 100ms):
            if self.eof_reached or self.empty_count >= 30 or (self.silence_count >= 30 and self.elapsed_sec >= 3.0):
                print(f"[DJ Deck {self.name}] Stream silent or stalled for 3.0s (flowed={self.has_audio_flowing}, eof={self.eof_reached}, elapsed={self.elapsed_sec:.1f}s). Auto-advancing to next track!")
                self.eof_reached = True
                self.stop()
            return b"\x00" * CHUNK_SIZE

    def stop(self):
        self.is_active = False
        self.volume = 0.0
        self.target_volume = 0.0
        self.stop_signal.set()
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                break

class AudioStationEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients: List[queue.Queue] = []
        self.playlist: List[Dict[str, Any]] = []
        self.voice_queue: List[Dict[str, Any]] = []
        
        # Deduplication tracking: Store normalized titles and timestamps (1-hour / 3600s repeat lockout)
        self.played_history: Dict[str, float] = {}
        
        # Active SFX overlays playing concurrently
        self.active_sfx_list: List[Dict[str, Any]] = []
        
        # Smooth, drop-free burst buffer (16 chunks x 1024 bytes = 16KB = ~1.0s) prevents network drops
        self.burst_buffer = collections.deque(maxlen=16)
        
        self.is_running = False
        self.is_on_air = True # Master Station ON AIR / OFF AIR state
        
        # Dual DJ Decks for seamless crossfading
        self.deck_a = Deck("A")
        self.deck_b = Deck("B")
        self.current_deck_name = "A"
        self.manual_crossfade_pos: Optional[float] = None # None = automatic, 0.0 = 100% Deck A, 1.0 = 100% Deck B
        
        # Voiceover & Ducking state
        self.master_duck_vol = 1.0
        self.current_voice_pcm: Optional[bytes] = None
        self.voice_pos: int = 0
        self.current_voice_info: Optional[Dict[str, Any]] = None
        self.master_voice_gain: float = 1.35  # User adjustable AI Voice gain (default 135%)

        # Inter-Song Quick News Transition (plays between songs before next track begins)
        self.pending_transition_news: Optional[Dict[str, Any]] = None
        self.is_playing_transition_news: bool = False
        
        self.encoder_process: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.mixer_thread: Optional[threading.Thread] = None

    def start(self):
        """Starts background master encoder and DJ mixer threads once."""
        if self.is_running:
            return
        self.is_running = True
        self._start_master_encoder()
        self.mixer_thread = threading.Thread(target=self._dj_mixer_loop, daemon=True)
        self.mixer_thread.start()
        print("[Engine] Master AudioStationEngine started.")

    def stop(self):
        self.is_running = False
        self.deck_a.stop()
        self.deck_b.stop()
        if self.encoder_process:
            try:
                self.encoder_process.terminate()
            except Exception:
                pass

    def _normalize_title(self, title: str) -> str:
        """Strip brackets, artists formatting, and non-alphanumeric chars for accurate duplicate matching."""
        if not title:
            return ""
        is_remix = "remix" in title.lower() or "mix" in title.lower()
        t = re.sub(r'\[.*?\]|\(.*?\)', '', title) # Remove [Sinhala], (Official Video), etc.
        t = re.sub(r'[^a-zA-Z0-9\u0D80-\u0DFF]', '', t).lower()
        if is_remix:
            t += "_remix"
        return t[:35] # Match primary 35 chars

    def is_duplicate(self, title: str, url: str = "") -> bool:
        """Strict check to prevent playing the same song twice on the same day (86400 seconds lockout)."""
        norm = self._normalize_title(title)
        now = time.time()
        with self.lock:
            # Clean up history entries older than 24 hours (86400 seconds)
            self.played_history = {k: v for k, v in self.played_history.items() if (now - v) < 86400}

            # 1. Check active playing decks
            for deck in [self.deck_a, self.deck_b]:
                if deck.is_active and deck.track:
                    if norm and norm == self._normalize_title(deck.track.get("title", "")):
                        return True
                    if url and deck.track.get("original_url") == url:
                        return True

            # 2. Check upcoming playlist
            for t in self.playlist:
                if norm and norm == self._normalize_title(t.get("title", "")):
                    return True
                if url and t.get("original_url") == url:
                    return True

            # 3. Check 24-hour (same day) played history (86400s repeat lockout)
            if norm and norm in self.played_history:
                last_time = self.played_history[norm]
                if now - last_time < 86400:
                    return True

        return False

    def remove_playlist_track(self, track_id: str) -> bool:
        """Remove a song from the playlist queue."""
        with self.lock:
            initial_len = len(self.playlist)
            self.playlist = [t for t in self.playlist if t.get("id") != track_id]
            return len(self.playlist) < initial_len

    def move_track_to_next(self, track_id: str) -> bool:
        """Move selected track to index 0 so it is guaranteed to play next."""
        with self.lock:
            for i, t in enumerate(self.playlist):
                if t.get("id") == track_id:
                    track = self.playlist.pop(i)
                    self.playlist.insert(0, track)
                    print(f"[Playlist] Moved to NEXT track (#1): {track.get('title')}")
                    return True
        return False

    def move_track(self, track_id: str, direction: str) -> bool:
        """Move track up or down in the upcoming playlist order."""
        with self.lock:
            for i, t in enumerate(self.playlist):
                if t.get("id") == track_id:
                    if direction == "up" and i > 0:
                        self.playlist[i], self.playlist[i - 1] = self.playlist[i - 1], self.playlist[i]
                        return True
                    elif direction == "down" and i < len(self.playlist) - 1:
                        self.playlist[i], self.playlist[i + 1] = self.playlist[i + 1], self.playlist[i]
                        return True
                    return False
        return False

    def play_track_now(self, track_id: str) -> bool:
        """
        Immediately inserts/cues selected track into the 2nd (standby) deck,
        and triggers a smooth DJ crossfade with fade effect.
        """
        with self.lock:
            target_track = None
            for i, t in enumerate(self.playlist):
                if t.get("id") == track_id:
                    target_track = self.playlist.pop(i)
                    break
            
            if not target_track:
                return False

            active_deck = self.deck_a if self.current_deck_name == "A" else self.deck_b
            next_deck = self.deck_b if self.current_deck_name == "A" else self.deck_a
            
            norm_title = self._normalize_title(target_track.get("title", ""))
            if norm_title:
                self.played_history[norm_title] = time.time()
            crossfade_sec = 4.0

            # 1. Immediately insert/load track into 2nd Deck so UI reflects it instantly
            next_deck.track = target_track
            raw_dur = float(target_track.get("duration", 0) or 0)
            next_deck.duration_sec = 360.0 if (raw_dur > 360.0 or raw_dur <= 0) else raw_dur
            next_deck.elapsed_sec = 0.0

        # 2. Worker initiates smooth fade transition without blocking HTTP response
        def _crossfade_transition():
            time.sleep(0.4) # Brief cue beat
            next_deck.load_and_play(target_track, initial_volume=0.0, target_volume=1.0, fade_duration_sec=crossfade_sec)
            active_deck.fade_out(duration_sec=crossfade_sec)
            with self.lock:
                self.current_deck_name = next_deck.name
            print(f"[DJ Mixer] Inserted to Deck {next_deck.name} -> Smooth DJ Crossfade ({crossfade_sec}s): {target_track.get('title')}")

        threading.Thread(target=_crossfade_transition, daemon=True).start()
        return True

    def clear_playlist(self):
        """Clear the entire upcoming playlist."""
        with self.lock:
            self.playlist.clear()

    def set_manual_crossfade(self, pos: Optional[float]):
        """Set manual crossfade position: 0.0 (Deck A) to 1.0 (Deck B), or None for auto."""
        with self.lock:
            self.manual_crossfade_pos = pos
            if pos is not None:
                # Calculate equal-power volumes
                pos = max(0.0, min(1.0, float(pos)))
                self.deck_a.volume = np.cos(pos * np.pi / 2)
                self.deck_a.target_volume = self.deck_a.volume
                self.deck_b.volume = np.sin(pos * np.pi / 2)
                self.deck_b.target_volume = self.deck_b.volume

    def set_deck_gain(self, deck_name: str, gain: float):
        """Set manual gain for Deck A or B (0.0 to 1.5)."""
        with self.lock:
            deck = self.deck_a if deck_name.upper() == "A" else self.deck_b
            deck.user_gain = max(0.0, min(1.5, float(gain)))

    def toggle_deck_mute(self, deck_name: str) -> bool:
        with self.lock:
            deck = self.deck_a if deck_name.upper() == "A" else self.deck_b
            deck.is_muted = not deck.is_muted
            return deck.is_muted

    def trigger_sfx(self, sfx_name: str):
        """Play a DJ sound effect overlayed on the live broadcast."""
        sfx_path = os.path.join(CACHE_DIR, f"sfx_{sfx_name}.mp3")
        if not os.path.exists(sfx_path):
            print(f"[DJ Mixer] SFX not found: {sfx_path}")
            return False

        try:
            conv_cmd = [
                FFMPEG_EXE,
                "-i", sfx_path,
                "-vn",
                "-f", "s16le",
                "-ac", "2",
                "-ar", "44100",
                "pipe:1"
            ]
            proc = subprocess.Popen(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pcm, _ = proc.communicate()
            if pcm:
                with self.lock:
                    self.active_sfx_list.append({"name": sfx_name, "pcm": pcm, "pos": 0})
                print(f"[DJ Mixer] Triggered SFX overlay: {sfx_name}")
                return True
        except Exception as e:
            print(f"[DJ Mixer] SFX trigger error: {e}")
        return False

    def set_on_air(self, state: bool) -> bool:
        """Switch Master Station ON AIR / OFF AIR."""
        with self.lock:
            self.is_on_air = bool(state)
            print(f"[Master Station] ON AIR set to: {'ON AIR' if self.is_on_air else 'OFF AIR'}")
            return self.is_on_air

    def toggle_on_air(self) -> bool:
        """Toggle Master Station ON AIR / OFF AIR state."""
        with self.lock:
            self.is_on_air = not self.is_on_air
            print(f"[Master Station] ON AIR toggled to: {'ON AIR' if self.is_on_air else 'OFF AIR'}")
            return self.is_on_air

    def _start_master_encoder(self):
        """Starts a single persistent ultra-low latency MP3 encoder process outputting live broadcast."""
        if self.encoder_process:
            try:
                self.encoder_process.terminate()
            except Exception:
                pass
            self.encoder_process = None

        encoder_cmd = [
            FFMPEG_EXE,
            "-f", "s16le",
            "-ar", "44100",
            "-ac", "2",
            "-i", "pipe:0",
            "-acodec", "libmp3lame",
            "-b:a", "256k",
            "-q:a", "0",
            "-ar", "44100",
            "-ac", "2",
            "-flush_packets", "1",
            "-fflags", "+nobuffer+flush_packets",
            "-flags", "low_delay",
            "-f", "mp3",
            "pipe:1"
        ]
        self.encoder_process = subprocess.Popen(
            encoder_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )
        self.reader_thread = threading.Thread(target=self._pump_encoder_to_listeners, daemon=True)
        self.reader_thread.start()

    def _pump_encoder_to_listeners(self):
        while self.is_running:
            try:
                # 1024 bytes at 128kbps = ~64ms for minimal buffering latency
                chunk = self.encoder_process.stdout.read(1024)
                if not chunk:
                    time.sleep(0.003)
                    continue
                self.broadcast_chunk(chunk)
            except Exception:
                time.sleep(0.01)

    def get_listener_count(self) -> int:
        with self.lock:
            return len(self.clients)

    def get_silence_chunk(self) -> bytes:
        if SILENCE_DATA:
            return SILENCE_DATA[:2048]
        return b"\xff\xfb\x90d" * 128

    def subscribe_client(self) -> queue.Queue:
        # 120 chunks x 1024 bytes = ~7.5 seconds capacity (low-latency online streaming without backlog lag)
        q = queue.Queue(maxsize=120)
        with self.lock:
            if self.burst_buffer:
                for chunk in list(self.burst_buffer):
                    try:
                        q.put_nowait(chunk)
                    except queue.Full:
                        break
            elif SILENCE_DATA:
                for i in range(0, min(len(SILENCE_DATA), 65536), 1024):
                    try:
                        q.put_nowait(SILENCE_DATA[i:i+1024])
                    except queue.Full:
                        break
            self.clients.append(q)
        return q

    def unsubscribe_client(self, q: queue.Queue):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def broadcast_chunk(self, chunk: bytes):
        with self.lock:
            self.burst_buffer.append(chunk)
            dead_clients = []
            for client_q in list(self.clients):
                try:
                    client_q.put_nowait(chunk)
                except queue.Full:
                    # Client buffer is backed up. Fast-forward older frames (drain 30 chunks) to snap back to real-time
                    try:
                        for _ in range(30):
                            client_q.get_nowait()
                        client_q.put_nowait(chunk)
                    except Exception:
                        dead_clients.append(client_q)
                except Exception:
                    dead_clients.append(client_q)
            for dc in dead_clients:
                if dc in self.clients:
                    self.clients.remove(dc)

    def _resolve_youtube_title(self, url: str) -> Optional[Dict[str, str]]:
        """Ultra-fast, unblocked resolution of YouTube URL to clean song title and artist via oEmbed (0.2s)."""
        import urllib.request
        import urllib.parse
        import json
        try:
            safe_url = urllib.parse.quote(url.strip(), safe=':/?=&')
            oembed_url = f"https://www.youtube.com/oembed?url={safe_url}&format=json"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_title = data.get("title", "")
                author = data.get("author_name", "YouTube Artist")
                if raw_title:
                    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', raw_title) # Remove (Official Video), [4K], etc.
                    clean = re.sub(r'[^\w\s\u0D80-\u0DFF]', ' ', clean)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    return {"raw_title": raw_title, "clean_title": clean or raw_title, "author": author}
        except Exception as e:
            print(f"[oEmbed] YouTube resolution skipped: {e}")
        return None

    def add_youtube_track(self, youtube_url_or_query: str) -> Dict[str, Any]:
        entry = None
        is_yt_url = bool(re.search(r'(?:youtube\.com|youtu\.be)', youtube_url_or_query.strip(), re.I))
        is_sc_url = bool(re.search(r'soundcloud\.com', youtube_url_or_query.strip(), re.I))
        yt_meta = None

        # 1. If YouTube URL, resolve title instantly via public oEmbed (never blocked by BotGuard, 0.2s)
        if is_yt_url:
            yt_meta = self._resolve_youtube_title(youtube_url_or_query)
            if yt_meta:
                search_query = yt_meta["clean_title"]
                print(f"[Queue] Resolved YouTube link via oEmbed: '{yt_meta['raw_title']}' -> Searching: '{search_query}'")
                try:
                    sc_query = f"scsearch5:{search_query}"
                    ydl_opts_sc = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'no_warnings': True,
                        'socket_timeout': 6
                    }
                    with yt_dlp.YoutubeDL(ydl_opts_sc) as ydl:
                        info = ydl.extract_info(sc_query, download=False)
                        entries = info.get('entries') or ([info] if info and info.get('url') else [])
                        for cand in entries:
                            dur = cand.get('duration', 0)
                            if dur >= 45 and cand.get('url'):
                                entry = cand
                                entry['title'] = yt_meta['raw_title']
                                entry['uploader'] = yt_meta['author']
                                print(f"[Queue] Matched full SoundCloud stream for YouTube link: {entry['title']} ({dur}s)")
                                break
                except Exception as sc_err:
                    print(f"[Queue] SoundCloud lookup for YouTube link error: {sc_err}")

        # 2. If regular text query, search SoundCloud directly with multi-result duration filtering
        if not entry and not is_yt_url and not is_sc_url:
            try:
                sc_query = f"scsearch5:{youtube_url_or_query.strip()}"
                ydl_opts_sc = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 6
                }
                with yt_dlp.YoutubeDL(ydl_opts_sc) as ydl:
                    info = ydl.extract_info(sc_query, download=False)
                    entries = info.get('entries') or ([info] if info and info.get('url') else [])
                    for cand in entries:
                        dur = cand.get('duration', 0)
                        if dur >= 45 and cand.get('url'):
                            entry = cand
                            print(f"[Queue] Fast SoundCloud query hit: {entry.get('title')} ({dur}s)")
                            break
                    if not entry and entries:
                        entry = entries[0]
            except Exception as sc_err:
                print(f"[Queue] Fast SoundCloud search failed: {sc_err}")

        # 3. Direct extraction fallback for SoundCloud URL or if previous steps didn't resolve
        if not entry or not entry.get('url'):
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'default_search': 'ytsearch',
                    'source_address': '0.0.0.0',
                    'socket_timeout': 5,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios', 'mweb']
                        }
                    }
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url_or_query, download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        entry = info['entries'][0]
                    elif info and info.get('url'):
                        entry = info
            except Exception as yt_err:
                print(f"[Queue] Extraction failed ({yt_err})")

        if not entry or not entry.get('url'):
            raise ValueError("Could not extract playable audio stream. Please check link or search term.")

        audio_url = entry.get('url')
        title = entry.get("title", "Unknown Title")
        original_url = entry.get("webpage_url", youtube_url_or_query)

        # Deduplication check: check if currently active or already waiting in playlist
        norm = self._normalize_title(title)
        is_active_now = False
        with self.lock:
            for deck in [self.deck_a, self.deck_b]:
                if deck.is_active and deck.track:
                    if norm and norm == self._normalize_title(deck.track.get("title", "")):
                        is_active_now = True
            for t in self.playlist:
                if norm and norm == self._normalize_title(t.get("title", "")):
                    is_active_now = True

        if is_active_now:
            print(f"[Queue] Duplicate track ignored: {title}")
            raise ValueError(f"'{title}' is already in queue or currently playing!")

        track = {
            "id": str(int(time.time() * 1000)),
            "type": "youtube",
            "title": title,
            "duration": entry.get("duration", 0),
            "duration_str": time.strftime('%M:%S', time.gmtime(entry.get("duration", 0))),
            "thumbnail": entry.get("thumbnail", ""),
            "uploader": entry.get("uploader", "YouTube"),
            "stream_url": audio_url,
            "original_url": original_url,
            "http_headers": entry.get("http_headers", {}),
            "added_at": time.strftime("%H:%M:%S"),
            "resolved_at": time.time()
        }

        with self.lock:
            self.playlist.append(track)
        return track

    def search_tracks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches for songs, remixes, and artist tracks, returning top matching candidates."""
        query = query.strip()
        if not query:
            return []

        results = []
        is_yt_url = bool(re.search(r'(?:youtube\.com|youtu\.be)', query, re.I))
        search_term = query
        if is_yt_url:
            yt_meta = self._resolve_youtube_title(query)
            if yt_meta:
                search_term = yt_meta["clean_title"]

        try:
            ydl_opts_sc = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 6
            }
            with yt_dlp.YoutubeDL(ydl_opts_sc) as ydl:
                info = ydl.extract_info(f"scsearch{limit}:{search_term}", download=False)
                entries = info.get('entries') or ([info] if info and info.get('url') else [])
                for e in entries:
                    dur = e.get('duration', 0)
                    if dur >= 45 and e.get('url'):
                        results.append({
                            "id": str(int(time.time() * 1000) + len(results)),
                            "type": "youtube",
                            "title": e.get("title", query),
                            "duration": dur,
                            "duration_str": time.strftime('%M:%S', time.gmtime(dur)),
                            "thumbnail": e.get("thumbnail", ""),
                            "uploader": e.get("uploader", "Online Stream"),
                            "stream_url": e.get("url"),
                            "original_url": e.get("webpage_url", query),
                            "http_headers": e.get("http_headers", {}),
                            "added_at": time.strftime("%H:%M:%S")
                        })
        except Exception as err:
            print(f"[Search Engine] Error searching '{query}': {err}")

        return results

    def queue_track_direct(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Directly queues a pre-resolved track into the standby playlist with deduplication."""
        title = track_data.get("title", "Unknown Track")
        norm = self._normalize_title(title)
        is_active_now = False
        with self.lock:
            for deck in [self.deck_a, self.deck_b]:
                if deck.is_active and deck.track:
                    if norm and norm == self._normalize_title(deck.track.get("title", "")):
                        is_active_now = True
            for t in self.playlist:
                if norm and norm == self._normalize_title(t.get("title", "")):
                    is_active_now = True

        if is_active_now:
            raise ValueError(f"'{title}' is already in queue or currently playing!")

        track = dict(track_data)
        track["id"] = str(int(time.time() * 1000))
        track["added_at"] = time.strftime("%H:%M:%S")
        track["resolved_at"] = time.time()

        with self.lock:
            self.playlist.append(track)
        print(f"[Queue Direct] Queued track: {track['title']} ({track.get('duration_str')})")
        return track

    def inject_priority_audio(self, audio_file_path: str, title: str, audio_type: str = "ad", play_immediately: bool = True):
        """Inject voiceover for real-time audio ducking (music lowers to 20%, never stops). Voice volume boosted."""
        try:
            conv_cmd = [
                FFMPEG_EXE,
                "-i", audio_file_path,
                "-vn",
                "-af", "volume=1.35",
                "-f", "s16le",
                "-ac", "2",
                "-ar", "44100",
                "pipe:1"
            ]
            proc = subprocess.Popen(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pcm_bytes, _ = proc.communicate()
            
            try:
                os.remove(audio_file_path)
            except Exception:
                pass

            if not pcm_bytes:
                return

            item = {
                "id": f"voice_{int(time.time()*1000)}",
                "type": audio_type,
                "title": title,
                "pcm": pcm_bytes,
                "added_at": time.strftime("%H:%M:%S")
            }

            with self.lock:
                if play_immediately:
                    self.voice_queue.insert(0, item)
                else:
                    self.voice_queue.append(item)
            print(f"[DJ Mixer] Queued voiceover for ducking: {title} ({len(pcm_bytes)/(44100*4):.1f}s)")
        except Exception as e:
            print(f"[DJ Mixer] Error preparing voiceover: {e}")

    def play_voice_overlay(self, audio_file_path: str, title: str = "Voice Broadcast", duck_vol: float = 0.20, play_immediately: bool = True):
        """Overlay priority voiceover over active stream with audio ducking."""
        self.inject_priority_audio(audio_file_path, title=title, audio_type="ad", play_immediately=play_immediately)

    def set_voice_gain(self, gain: float):
        """Set real-time master gain multiplier for all AI speech/voiceovers (range: 0.3 to 3.0)."""
        with self.lock:
            self.master_voice_gain = max(0.3, min(3.0, float(gain)))
            print(f"[DJ Mixer] Master Voice Gain set to: {self.master_voice_gain:.2f} ({int(round(self.master_voice_gain*100))}%)")

    def set_pending_transition_news(self, audio_file_path: str, title: str):
        """
        Queues quick flash news to be read cleanly AFTER the currently playing song finishes,
        and BEFORE the next song starts playing.
        """
        try:
            conv_cmd = [
                FFMPEG_EXE,
                "-i", audio_file_path,
                "-vn",
                "-f", "s16le",
                "-ac", "2",
                "-ar", "44100",
                "pipe:1"
            ]
            proc = subprocess.Popen(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pcm_bytes, _ = proc.communicate()
            
            try:
                os.remove(audio_file_path)
            except Exception:
                pass

            if not pcm_bytes:
                return

            item = {
                "id": f"news_trans_{int(time.time()*1000)}",
                "type": "ad",
                "title": f"Radio Four D M එසැණ පුවත්: {title[:40]}",
                "pcm": pcm_bytes,
                "added_at": time.strftime("%H:%M:%S")
            }

            with self.lock:
                self.pending_transition_news = item
            print(f"[DJ Mixer] Quick News queued for song-to-song transition (Length: {len(pcm_bytes)/(44100*4):.1f}s): {title}")
        except Exception as e:
            print(f"[DJ Mixer] Error queuing transition news: {e}")

    def skip(self):
        """DJ Skip: Instantly and smoothly crossfades into the next track over 3.5 seconds."""
        with self.lock:
            active_deck = self.deck_a if self.current_deck_name == "A" else self.deck_b
            next_deck = self.deck_b if self.current_deck_name == "A" else self.deck_a
            
            if self.playlist:
                incoming_track = self.playlist.pop(0)
                norm_inc = self._normalize_title(incoming_track.get("title", ""))
                if norm_inc:
                    self.played_history[norm_inc] = time.time()
                crossfade_sec = 3.5
                next_deck.load_and_play(incoming_track, initial_volume=0.0, target_volume=1.0, fade_duration_sec=crossfade_sec)
                active_deck.fade_out(duration_sec=crossfade_sec)
                self.current_deck_name = next_deck.name
                print(f"[DJ Skip] Smooth Equal-Power crossfading Deck {active_deck.name} -> Deck {next_deck.name} ({crossfade_sec}s)")
            elif active_deck.is_active:
                print(f"[DJ Mixer] Skip requested. Crossfading out Deck {active_deck.name}...")
                active_deck.fade_out(duration_sec=2.0)

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            active_deck = self.deck_a if self.deck_a.volume >= self.deck_b.volume else self.deck_b
            current_track = active_deck.track
            
            if not self.is_on_air:
                clean_display = {
                    "title": "Station OFF AIR (Master Broadcast Muted)",
                    "type": "offair",
                    "uploader": "Radio 4DM Master Switch"
                }
            elif self.current_voice_info:
                display_track = {
                    "title": self.current_voice_info.get("title"),
                    "type": self.current_voice_info.get("type"),
                    "uploader": f"Radio RJ (Voiceover Ducking active) • Music: {current_track.get('title') if current_track else 'Station'}",
                    "is_ducking": True
                }
                clean_display = display_track
            else:
                clean_display = {k: v for k, v in current_track.items() if k != "http_headers"} if current_track else None

            return {
                "is_on_air": self.is_on_air,
                "listeners": len(self.clients),
                "current_track": clean_display,
                "bg_volume_pct": int(self.master_duck_vol * 100),
                "playlist_count": len(self.playlist),
                "playlist": [{k: v for k, v in t.items() if k not in ("stream_url", "http_headers")} for t in self.playlist[:15]],
                "voice_active": bool(self.current_voice_info),
                "voice_gain": float(round(self.master_voice_gain, 2)),
                "voice_gain_pct": int(round(self.master_voice_gain * 100)),
                "deck_a": {
                    "active": self.deck_a.is_active,
                    "volume": float(round(self.deck_a.volume, 2)),
                    "gain": float(self.deck_a.user_gain),
                    "muted": bool(self.deck_a.is_muted),
                    "track": self.deck_a.track.get("title") if self.deck_a.track else None,
                    "duration": float(self.deck_a.duration_sec),
                    "elapsed": float(round(self.deck_a.elapsed_sec, 1)),
                    "rms_db": float(round(self.deck_a.current_rms_db, 1))
                },
                "deck_b": {
                    "active": self.deck_b.is_active,
                    "volume": float(round(self.deck_b.volume, 2)),
                    "gain": float(self.deck_b.user_gain),
                    "muted": bool(self.deck_b.is_muted),
                    "track": self.deck_b.track.get("title") if self.deck_b.track else None,
                    "duration": float(self.deck_b.duration_sec),
                    "elapsed": float(round(self.deck_b.elapsed_sec, 1)),
                    "rms_db": float(round(self.deck_b.current_rms_db, 1))
                },
                "crossfade_pos": self.manual_crossfade_pos
            }

    def _dj_mixer_loop(self):
        """
        Master DJ Mixer Loop:
        - Gapless Dual-Deck Crossfade (No silence, no duplicate songs)
        - SFX Multi-Layer Overlays
        - Audio Ducking during voiceover
        - Real-time Pacing at exactly 44100Hz Stereo
        """
        print("[DJ Mixer] Pro Dual-Deck Crossfade Engine Online.")
        target_cycle_time = time.time()
        
        while self.is_running:
            target_cycle_time += 0.100
            cfg = load_config()
            crossfade_sec = float(cfg.get("crossfade_seconds", 6.0))

            active_deck = self.deck_a if self.current_deck_name == "A" else self.deck_b
            next_deck   = self.deck_b if self.current_deck_name == "A" else self.deck_a

            # 1. Check if Inter-Song News finished
            if self.is_playing_transition_news and self.current_voice_pcm is None and not self.voice_queue:
                self.is_playing_transition_news = False
                print("[DJ Mixer] Inter-song news broadcast finished.")

            # 2. Start Initial Song or Post-News Song if both decks are idle
            if not self.deck_a.is_active and not self.deck_b.is_active and not self.is_playing_transition_news:
                with self.lock:
                    if self.playlist:
                        next_track = self.playlist.pop(0)
                        norm_t = self._normalize_title(next_track.get("title", ""))
                        if norm_t:
                            self.played_history[norm_t] = time.time()
                        active_deck.load_and_play(next_track, initial_volume=0.0, target_volume=1.0, fade_duration_sec=2.0)

            # 3. Seamless Decibel-Matched Crossfade Check
            time_left = active_deck.duration_sec - active_deck.elapsed_sec if active_deck.duration_sec > 0 else 999
            
            should_crossfade = False
            if active_deck.is_active and not next_deck.is_active and not self.is_playing_transition_news:
                if active_deck.eof_reached or active_deck.target_volume == 0.0 or active_deck.silence_count >= 30 or active_deck.empty_count >= 30:
                    should_crossfade = True
                elif active_deck.elapsed_sec >= (360.0 - crossfade_sec):
                    # Hard 6-minute maximum track cap (seamless equal-power crossfade)
                    should_crossfade = True
                elif active_deck.duration_sec > 10 and time_left <= crossfade_sec:
                    # Seamless Equal-Power crossfade: starts BEFORE outgoing track decibels drop,
                    # matching incoming song to that exact decibel level for continuous gapless sound
                    should_crossfade = True

            if should_crossfade:
                with self.lock:
                    # Check if there is pending Quick News to read BEFORE the next song begins
                    if self.pending_transition_news:
                        news_item = self.pending_transition_news
                        self.pending_transition_news = None
                        active_deck.fade_out(duration_sec=1.5)
                        self.voice_queue.insert(0, news_item)
                        self.is_playing_transition_news = True
                        print(f"[DJ Mixer] Song ended. Broadcasting Quick News between songs before next track starts: {news_item['title']}")
                    elif self.playlist:
                        incoming_track = self.playlist.pop(0)
                        norm_inc = self._normalize_title(incoming_track.get("title", ""))
                        if norm_inc:
                            self.played_history[norm_inc] = time.time()
                        
                        active_deck.fade_out(duration_sec=crossfade_sec)
                        next_deck.load_and_play(incoming_track, initial_volume=0.0, target_volume=1.0, fade_duration_sec=crossfade_sec)
                        
                        self.current_deck_name = next_deck.name
                        print(f"[DJ Mixer] Seamless Decibel-Matched Crossfade: Deck {active_deck.name} -> Deck {next_deck.name} ({crossfade_sec}s)")

            # 3. Read chunks from both decks
            chunk_a = self.deck_a.read_chunk()
            chunk_b = self.deck_b.read_chunk()

            # 4. Voiceover & Ducking
            if self.current_voice_pcm is None:
                with self.lock:
                    if self.voice_queue:
                        item = self.voice_queue.pop(0)
                        self.current_voice_pcm = item["pcm"]
                        self.voice_pos = 0
                        self.current_voice_info = item
                        print(f"[DJ Mixer] Ducking music: {item['title']}")

            target_duck = 1.0
            voice_chunk = None

            if self.current_voice_pcm is not None:
                vtype = (self.current_voice_info.get("type") if self.current_voice_info else "") or ""
                if vtype == "news":
                    target_duck = 0.10  # Duck music volume to 10% for crisp, audible news
                else:
                    target_duck = 0.20  # Duck music volume to 20% for voice commands, ads, and taglines
                end_pos = self.voice_pos + CHUNK_SIZE
                voice_chunk = self.current_voice_pcm[self.voice_pos:end_pos]
                self.voice_pos = end_pos
                if self.voice_pos >= len(self.current_voice_pcm):
                    self.current_voice_pcm = None
                    self.current_voice_info = None

            self.master_duck_vol += (target_duck - self.master_duck_vol) * 0.30

            # 5. Process Active SFX Overlays
            sfx_combined = np.zeros(CHUNK_SIZE // 2, dtype=np.float32)
            with self.lock:
                finished_sfx = []
                for sfx in self.active_sfx_list:
                    end_pos = sfx["pos"] + CHUNK_SIZE
                    chunk_data = sfx["pcm"][sfx["pos"]:end_pos]
                    sfx["pos"] = end_pos
                    if len(chunk_data) < CHUNK_SIZE:
                        chunk_data = chunk_data.ljust(CHUNK_SIZE, b"\x00")
                        finished_sfx.append(sfx)
                    arr = np.frombuffer(chunk_data, dtype=np.int16).astype(np.float32) * 1.3
                    sfx_combined += arr
                for fin in finished_sfx:
                    self.active_sfx_list.remove(fin)

            # 6. Audio Mixing: Deck A + Deck B + Voiceover + SFX Overlays
            try:
                # Audio mixing with Equal-Power Crossfading (constant total acoustic power)
                vol_a = 0.0 if self.deck_a.is_muted else (self.deck_a.volume * self.deck_a.user_gain)
                vol_b = 0.0 if self.deck_b.is_muted else (self.deck_b.volume * self.deck_b.user_gain)

                if self.manual_crossfade_pos is not None:
                    pos = max(0.0, min(1.0, float(self.manual_crossfade_pos)))
                    gain_a = math.cos(pos * math.pi / 2.0)
                    gain_b = math.sin(pos * math.pi / 2.0)
                    arr_a = np.frombuffer(chunk_a, dtype=np.int16).astype(np.float32) * (vol_a * gain_a)
                    arr_b = np.frombuffer(chunk_b, dtype=np.int16).astype(np.float32) * (vol_b * gain_b)
                elif self.deck_a.is_active and self.deck_b.is_active:
                    tot = vol_a + vol_b
                    if tot > 0.001:
                        ratio_b = max(0.0, min(1.0, vol_b / tot))
                        gain_a = math.cos(ratio_b * math.pi / 2.0)
                        gain_b = math.sin(ratio_b * math.pi / 2.0)
                        arr_a = np.frombuffer(chunk_a, dtype=np.int16).astype(np.float32) * (vol_a * gain_a)
                        arr_b = np.frombuffer(chunk_b, dtype=np.int16).astype(np.float32) * (vol_b * gain_b)
                    else:
                        arr_a = np.frombuffer(chunk_a, dtype=np.int16).astype(np.float32) * vol_a
                        arr_b = np.frombuffer(chunk_b, dtype=np.int16).astype(np.float32) * vol_b
                else:
                    arr_a = np.frombuffer(chunk_a, dtype=np.int16).astype(np.float32) * vol_a
                    arr_b = np.frombuffer(chunk_b, dtype=np.int16).astype(np.float32) * vol_b
                
                music_mixed = (arr_a + arr_b) * self.master_duck_vol
                
                # Add voiceover if active (scaled by user-controlled AI Voice Volume bar)
                if voice_chunk:
                    if len(voice_chunk) < CHUNK_SIZE:
                        voice_chunk = voice_chunk.ljust(CHUNK_SIZE, b"\x00")
                    v_arr = np.frombuffer(voice_chunk, dtype=np.int16).astype(np.float32) * self.master_voice_gain
                    output_pcm = music_mixed + v_arr + sfx_combined
                else:
                    output_pcm = music_mixed + sfx_combined

                if self.is_on_air:
                    final_mixed = np.clip(output_pcm, -32768, 32767).astype(np.int16)
                else:
                    # OFF-AIR: Feed silence to encoder so listeners hear nothing and master output is muted
                    final_mixed = np.zeros(CHUNK_SIZE // 2, dtype=np.int16)

                if self.encoder_process and self.encoder_process.stdin:
                    self.encoder_process.stdin.write(final_mixed.tobytes())
                    self.encoder_process.stdin.flush()
            except Exception as e:
                print(f"[DJ Mixer] Error mixing: {e}")
                try:
                    self._start_master_encoder()
                except Exception:
                    pass

            # 7. Pacing clock
            sleep_duration = target_cycle_time - time.time()
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            else:
                target_cycle_time = time.time()

station_engine = AudioStationEngine()
