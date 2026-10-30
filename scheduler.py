import sys
import time
import os
import threading
import datetime
import asyncio
import urllib.request
import json
import ssl

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from streamer import station_engine
from tts_engine import generate_speech_file_sync, get_sinhala_time_text, get_tagline_info, STATION_TAGLINES, CACHE_DIR
from news_engine import fetch_quick_news, build_news_broadcast_audio
from cricket_engine import get_cricket_highlights_text, build_cricket_broadcast_audio

WEATHER_CODE_SINHALA = {
    0: "හිරු රැසින් පිරි පැහැදිලි අහසක්",
    1: "ප්‍රධාන වශයෙන් පැහැදිලි කාලගුණයක්",
    2: "මඳ වශයෙන් වළාකුළු සහිත කාලගුණයක්",
    3: "වළාකුළු සහිත අහසක්",
    45: "මීදුම් සහිත තත්ත්වයක්",
    48: "මීදුම් සහිත තත්ත්වයක්",
    51: "සිහින් පොද වැසි සහිත තත්ත්වයක්",
    53: "මධ්‍යස්ථ පොද වැසි සහිත තත්ත්වයක්",
    55: "තද පොද වැසි සහිත තත්ත්වයක්",
    61: "මඳ වැසි සහිත කාලගුණයක්",
    63: "මධ්‍යස්ථ වැසි සහිත තත්ත්වයක්",
    65: "තද වැසි සහිත තත්ත්වයක්",
    80: "වැසි වාර කිහිපයක්",
    81: "වැසි හෝ ගිගුරුම් සහිත වැසි",
    82: "තද වැසි සහිත කාලගුණයක්",
    95: "ගිගුරුම් සහිත වැසි තත්ත්වයක්",
    96: "ගිගුරුම් සහිත වැසි තත්ත්වයක්",
    99: "තද ගිගුරුම් සහිත වැසි තත්ත්වයක්"
}

def fetch_colombo_weather() -> dict:
    """Fetches real-time weather metrics for Colombo, Sri Lanka (100% Free Open-Meteo, No API key)."""
    try:
        ctx = ssl._create_unverified_context()
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            "latitude=6.9271&longitude=79.8612&"
            "current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&"
            "timezone=Asia%2FColombo"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RadioFourDM/2.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            data = json.loads(r.read().decode())
            return data.get("current", {})
    except Exception as e:
        print(f"[Weather] Error fetching weather: {e}")
        return {}

def get_colombo_weather_text() -> str:
    """Generates natural Sinhala radio RJ speech for Colombo live weather."""
    try:
        w = fetch_colombo_weather()
        temp = round(w.get("temperature_2m", 30))
        humidity = round(w.get("relative_humidity_2m", 75))
        code = w.get("weather_code", 1)
        condition = WEATHER_CODE_SINHALA.get(code, "සාමාන්‍ය කාලගුණික තත්ත්වයක්")
        
        text = (
            f"Radio Four D M වෙතින් කොළඹ නගරයේ සජීවී කාලගුණ තොරතුරු. "
            f"මේ වන විට කොළඹ ප්‍රදේශයේ උෂ්ණත්වය සෙල්සියස් අංශක {temp}ක් පමණ වන අතර, {condition} පවතී. "
            f"සාපේක්ෂ ආර්ද්‍රතාවය සියයට {humidity}ක්. "
            f"හොඳම ගීත සමඟින් දිගටම Radio Four D M සමඟ රැඳී සිටින්න!"
        )
        return text
    except Exception as e:
        print(f"[Weather] Error formatting weather text: {e}")
        return "Radio Four D M වෙතින් කොළඹ නගරයේ සජීවී කාලගුණ තොරතුරු. මේ වන විට කොළඹ ප්‍රදේශයේ උෂ්ණත්වය සෙල්සියස් අංශක තිහක් පමණ වන අතර සාමාන්‍ය කාලගුණික තත්ත්වයක් පවතී."

def get_colombo_time() -> datetime.datetime:
    """Returns accurate Sri Lanka Standard Time (Asia/Colombo, UTC+5:30)."""
    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(tz)

class HourlyTimeScheduler:
    def __init__(self):
        self.time_enabled = True
        self.news_enabled = True
        self.last_announced_hour = -1
        self.last_weather_hour = -1
        self.last_cricket_hour = -1
        self.last_news_id = None
        self.last_polled_news_time = 0
        self.last_tagline_time = time.time()
        self.cricket_enabled = True
        self.cricket_lang = "si"
        self.last_cricket_broadcast_time = time.time()
        self.lock = threading.Lock()
        
        # Threads for hourly time/weather/cricket loop, 10-minute quick news poller, and automatic Radio ID drops
        self.worker_thread = threading.Thread(target=self._run_time_loop, daemon=True)
        self.worker_thread.start()
        
        self.news_poller_thread = threading.Thread(target=self._run_news_poller, daemon=True)
        self.news_poller_thread.start()

        self.tagline_thread = threading.Thread(target=self._run_tagline_loop, daemon=True)
        self.tagline_thread.start()

    def set_enabled(self, state: bool):
        with self.lock:
            self.time_enabled = state
            print(f"[Scheduler] Auto Hourly Time Announcement set to: {'ON' if state else 'OFF'}")

    def is_enabled(self) -> bool:
        with self.lock:
            return self.time_enabled

    def set_news_enabled(self, state: bool):
        with self.lock:
            self.news_enabled = state
            print(f"[Scheduler] Auto 10-Minute Quick News Poller set to: {'ON' if state else 'OFF'}")

    def is_news_enabled(self) -> bool:
        with self.lock:
            return self.news_enabled

    def set_cricket_enabled(self, state: bool):
        with self.lock:
            self.cricket_enabled = state
            print(f"[Scheduler] Auto 20-Min Cricbuzz Cricket Broadcast set to: {'ON' if state else 'OFF'}")

    def is_cricket_enabled(self) -> bool:
        with self.lock:
            return self.cricket_enabled

    def set_cricket_lang(self, lang: str):
        with self.lock:
            if lang in ("si", "en"):
                self.cricket_lang = lang
                print(f"[Scheduler] Cricket commentary language set to: {lang.upper()}")

    def get_cricket_lang(self) -> str:
        with self.lock:
            return self.cricket_lang

    def broadcast_time_sync(self) -> dict:
        """Broadcasts current time in lively Sinhala female RJ voice (Radio Four D M)."""
        now = get_colombo_time()
        text = get_sinhala_time_text(now.hour, now.minute, style="friendly_rj")

        audio_file = generate_speech_file_sync(
            text=text,
            voice_key="si-female",
            lang="si",
            provider="gemini",
            filename_prefix="time_rj",
            add_chime=True
        )

        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=f"Radio Four D M හෝරා නිවේදනය: {text[:35]}...",
            audio_type="time",
            play_immediately=True
        )
        return {
            "status": "success",
            "message": f"Broadcasted: {text}",
            "text": text,
            "hour": now.hour,
            "minute": now.minute
        }

    async def broadcast_time_async(self) -> dict:
        return await asyncio.to_thread(self.broadcast_time_sync)

    def broadcast_news_sync(self) -> dict:
        """Manual 1-Click trigger: Fetches latest quick flash news and broadcasts with jingle bed."""
        news_data = fetch_quick_news()
        if not news_data:
            raise RuntimeError("Unable to fetch quick flash news.")

        audio_file = build_news_broadcast_audio(news_data)
        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=f"Radio Four D M එසැණ පුවත්: {news_data['headline'][:35]}...",
            audio_type="ad",
            play_immediately=True
        )
        return {
            "status": "success",
            "headline": news_data["headline"],
            "body": news_data["body"],
            "url": news_data["url"],
            "fetched_at": news_data.get("fetched_at")
        }

    async def broadcast_news_async(self) -> dict:
        return await asyncio.to_thread(self.broadcast_news_sync)

    def check_and_queue_new_news(self):
        """Checks for new quick news and queues it to play cleanly between songs before the next song begins."""
        try:
            news_data = fetch_quick_news()
            if not news_data:
                return

            news_id = news_data.get("id")
            if not news_id:
                return

            if self.last_news_id is None:
                # Initial run: store ID so station doesn't spam on initial boot, but queues if fresh
                self.last_news_id = news_id
                print(f"[News Poller] Initialized tracking. Latest Quick News ID: {news_id} ('{news_data['headline'][:40]}')")
                return

            if news_id != self.last_news_id:
                self.last_news_id = news_id
                print(f"[News Poller] New Quick News detected ({news_id}): '{news_data['headline']}'. Generating Gemini speech...")
                audio_file = build_news_broadcast_audio(news_data)
                # Broadcast immediately OVER the currently playing song with Audio Ducking (music volume lowered, song NOT muted)
                station_engine.inject_priority_audio(
                    audio_file_path=audio_file,
                    title=f"Radio Four D M එසැණ පුවත්: {news_data['headline'][:35]}...",
                    audio_type="news",
                    play_immediately=True
                )
        except Exception as e:
            print(f"[News Poller] Error checking quick news: {e}")

    def _run_news_poller(self):
        """Polls for new quick news updates every 10 minutes (600 seconds)."""
        time.sleep(10) # Initial grace period
        while True:
            try:
                if self.is_news_enabled():
                    self.check_and_queue_new_news()
            except Exception as e:
                print(f"[News Poller] Loop error: {e}")
            
            # Wait 10 minutes (600 seconds)
            for _ in range(60):
                time.sleep(10)

    def broadcast_weather_sync(self) -> dict:
        """Broadcasts Colombo live weather announcement in friendly RJ voice (exactly 10 mins past the hour)."""
        text = get_colombo_weather_text()
        audio_file = generate_speech_file_sync(
            text=text,
            voice_key="si-female",
            lang="si",
            provider="gemini",
            filename_prefix="weather_colombo",
            add_chime=True
        )
        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=f"Radio Four D M කොළඹ කාලගුණය: {text[:35]}...",
            audio_type="ad",
            play_immediately=True
        )
        print(f"[Scheduler] Broadcasted Colombo Weather: {text[:60]}...")
        return {"status": "success", "text": text}

    async def broadcast_weather_async(self) -> dict:
        return await asyncio.to_thread(self.broadcast_weather_sync)

    def _run_time_loop(self):
        """
        Hourly Time Announcement at :00 (Sri Lanka Time).
        Colombo Live Weather Announcement at :10 (Default, 10 minutes past the hour).
        Cricbuzz Sri Lanka Live Cricket Announcement at :55 (ONLY if a Sri Lanka live match is active).
        """
        print("[Scheduler] Automation Matrix Online: Time (:00), Weather (:10), & Live Cricket (:55) active.")
        while True:
            try:
                now = get_colombo_time()
                # 1. Hourly Time Announcement at :00
                if self.time_enabled and now.minute == 0 and 0 <= now.second <= 12:
                    if self.last_announced_hour != now.hour:
                        self.last_announced_hour = now.hour
                        print(f"[Scheduler] Auto Time Announcement for {now.hour}:00")
                        try:
                            self.broadcast_time_sync()
                        except Exception as te:
                            print(f"[Scheduler] Error in time announcement: {te}")

                # 2. Colombo Weather Announcement at :10 (Default, 10 minutes past the hour)
                if self.time_enabled and now.minute == 10 and 0 <= now.second <= 12:
                    if self.last_weather_hour != now.hour:
                        self.last_weather_hour = now.hour
                        print(f"[Scheduler] Auto Colombo Weather Announcement at {now.hour}:10")
                        try:
                            self.broadcast_weather_sync()
                        except Exception as we:
                            print(f"[Scheduler] Error in weather announcement: {we}")

                # 3. Cricbuzz Sri Lanka Live Cricket Announcement at :55
                # Strictly only plays if an active live Sri Lanka match is in progress
                if self.cricket_enabled and now.minute == 55 and 0 <= now.second <= 12:
                    if self.last_cricket_hour != now.hour:
                        self.last_cricket_hour = now.hour
                        print(f"[Scheduler] Checking Cricbuzz Live Sri Lanka matches at :55 ({now.hour}:55)...")
                        try:
                            data = get_cricket_highlights_text(self.cricket_lang)
                            if data.get("has_live"):
                                print(f"[Cricket Engine] Sri Lanka Live match found! Broadcasting at :55...")
                                self.broadcast_cricket_sync(self.cricket_lang)
                            else:
                                print(f"[Cricket Engine] No live match for Sri Lanka at :55. Skipping broadcast (Silent).")
                        except Exception as ce:
                            print(f"[Scheduler] Error in cricket announcement: {ce}")
            except Exception as e:
                print(f"[Scheduler] Time/Weather/Cricket loop error: {e}")

            time.sleep(6)

    def broadcast_tagline_sync(self, tagline_id: str = None) -> dict:
        """Broadcasts Radio 4DM official Station ID / Tagline fittingly over music (Ducking to 20%)."""
        info = get_tagline_info(tagline_id)
        audio_file = generate_speech_file_sync(
            text=info["text"],
            voice_key=info["voice"],
            lang=info["lang"],
            provider="gemini",
            filename_prefix="tagline",
            add_chime=True
        )
        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=f"Radio 4DM Station ID • {info['title']}",
            audio_type="tagline",
            play_immediately=True
        )
        self.last_tagline_time = time.time()
        print(f"[Radio ID Engine] Broadcasted Station ID Tagline: {info['title']}")
        return {"status": "success", "title": info["title"], "text": info["text"]}

    def _run_tagline_loop(self):
        """
        Periodically announces Station Radio ID ("Radio Four D M") every 15 minutes (900 seconds)
        fittingly over active tracks, remixes, and sets with music ducking (down to 20%).
        """
        time.sleep(60) # Initial warmup delay
        while True:
            try:
                # Check if at least 15 minutes (900s) passed since last voice broadcast
                elapsed_since_last = time.time() - self.last_tagline_time
                if elapsed_since_last >= 900:
                    # Only drop Radio ID if music is actively playing and no other voice is queued
                    has_active_music = (station_engine.deck_a.is_active or station_engine.deck_b.is_active)
                    has_pending_voice = bool(station_engine.current_voice_pcm) or bool(station_engine.voice_queue)
                    if has_active_music and not has_pending_voice and station_engine.is_on_air:
                        self.broadcast_tagline_sync()
            except Exception as e:
                print(f"[Radio ID Engine] Loop error: {e}")

            time.sleep(15)

    def broadcast_cricket_sync(self, lang: str = None) -> dict:
        """
        Broadcasts live cricket updates from Cricbuzz with 20% music ducking.
        Condition: Broadcasts ONLY if an active live match is currently in progress.
        """
        chosen_lang = lang or self.cricket_lang
        data = get_cricket_highlights_text(chosen_lang)
        if not data.get("has_live"):
            print("[Cricket Engine] Cricbuzz reports no active live matches right now. Skipping broadcast.")
            return {"status": "skipped", "reason": "No live match in progress", "has_live": False}

        audio_file = build_cricket_broadcast_audio(chosen_lang, preloaded_data=data)
        if not audio_file:
            return {"status": "skipped", "reason": "Could not synthesize audio", "has_live": False}

        title = data.get("headline", "Cricbuzz සජීවී ක්‍රිකට් විකාශය")
        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=title,
            audio_type="ad",
            play_immediately=True
        )
        self.last_cricket_broadcast_time = time.time()
        print(f"[Cricket Engine] Broadcasted Cricbuzz live update ({chosen_lang.upper()}): {data.get('top_match', {}).get('title')}")
        return {
            "status": "success",
            "has_live": True,
            "headline": data.get("headline"),
            "summary": data.get("summary"),
            "time": data.get("time")
        }

    async def broadcast_cricket_async(self, lang: str = None) -> dict:
        return await asyncio.to_thread(self.broadcast_cricket_sync, lang)

time_scheduler = HourlyTimeScheduler()
