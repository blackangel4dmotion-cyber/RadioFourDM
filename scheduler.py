import time
import os
import threading
import datetime
import asyncio
from streamer import station_engine
from tts_engine import generate_speech_file_sync, get_sinhala_time_text, CACHE_DIR
from news_engine import fetch_quick_news, build_news_broadcast_audio

def get_colombo_time() -> datetime.datetime:
    """Returns accurate Sri Lanka Standard Time (Asia/Colombo, UTC+5:30)."""
    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(tz)

class HourlyTimeScheduler:
    def __init__(self):
        self.time_enabled = True
        self.news_enabled = True
        self.last_announced_hour = -1
        self.last_news_id = None
        self.last_polled_news_time = 0
        self.lock = threading.Lock()
        
        # Threads for hourly time and 10-minute quick news poller
        self.worker_thread = threading.Thread(target=self._run_time_loop, daemon=True)
        self.worker_thread.start()
        
        self.news_poller_thread = threading.Thread(target=self._run_news_poller, daemon=True)
        self.news_poller_thread.start()

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
                # Queue to broadcast cleanly between songs (after currently playing song ends, before next song starts)
                station_engine.set_pending_transition_news(audio_file, title=news_data["headline"])
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

    def _run_time_loop(self):
        """Hourly Time Announcement at :00 (Sri Lanka Time)."""
        print("[Scheduler] Hourly Sinhala Time (Asia/Colombo UTC+5:30) & 10-Minute Quick News Poller active.")
        while True:
            try:
                now = get_colombo_time()
                # Hourly Time Announcement at :00
                if self.time_enabled and now.minute == 0 and 0 <= now.second <= 12:
                    if self.last_announced_hour != now.hour:
                        self.last_announced_hour = now.hour
                        print(f"[Scheduler] Auto Time Announcement for {now.hour}:00")
                        try:
                            self.broadcast_time_sync()
                        except Exception as te:
                            print(f"[Scheduler] Error in time announcement: {te}")
            except Exception as e:
                print(f"[Scheduler] Time loop error: {e}")

            time.sleep(6)

time_scheduler = HourlyTimeScheduler()
