import os
import time
import threading
os.environ["NO_PROXY"] = "localhost,127.0.0.1," + os.environ.get("NO_PROXY", "")
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from streamer import station_engine
from tts_engine import generate_speech_file, generate_speech_file_sync, get_tagline_info, STATION_TAGLINES, VOICES, load_config, save_config
from scheduler import time_scheduler
from autodj import AutoDJEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Initialize AutoDJ
auto_dj = AutoDJEngine(station_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background workers exactly once
    station_engine.start()
    auto_dj.start()
    yield
    # Shutdown
    auto_dj.stop()
    station_engine.stop()

app = FastAPI(title="AI Online Radio Station - Pro DJ Console", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class YouTubeRequest(BaseModel):
    url: str

class AdSpeakRequest(BaseModel):
    text: str
    voice: str = "si-female"
    lang: str = "si" # "si", "en", "auto"
    provider: Optional[str] = None
    immediate: bool = True
    rate: str = "-4%"
    pitch: str = "+2Hz"

class TimeToggleRequest(BaseModel):
    enabled: bool

class AutoDJToggleRequest(BaseModel):
    enabled: bool

class ChartLoadRequest(BaseModel):
    chart: str = "mixed"
    count: int = 5

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class GeminiVerifyRequest(BaseModel):
    api_key: str

class ConfigUpdateRequest(BaseModel):
    tts_provider: Optional[str] = "gemini"
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM"
    crossfade_seconds: Optional[int] = 6
    ducking_volume: Optional[float] = 0.18

class SfxRequest(BaseModel):
    sfx: str

class CrossfadePosRequest(BaseModel):
    pos: Optional[float] = None

class DeckGainRequest(BaseModel):
    deck: str
    gain: float

class DeckMuteRequest(BaseModel):
    deck: str

class TrackActionRequest(BaseModel):
    track_id: str

class TrackMoveRequest(BaseModel):
    track_id: str
    direction: str # 'up' or 'down'

class TaglineRequest(BaseModel):
    tagline_id: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.get("/stream")
def audio_stream():
    """Continuous live MP3 radio stream with DJ crossfade and audio ducking."""
    client_queue = station_engine.subscribe_client()

    def stream_generator():
        try:
            while True:
                try:
                    chunk = client_queue.get(timeout=2.0)
                    yield chunk
                except Exception:
                    yield station_engine.get_silence_chunk()
        except GeneratorExit:
            pass
        finally:
            station_engine.unsubscribe_client(client_queue)

    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Accept-Ranges": "none",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.get("/api/ping")
@app.head("/api/ping")
async def ping_healthcheck():
    """Ultra-fast 0ms ping endpoint for UptimeRobot keep-alive and cloud health probes."""
    return {"status": "ok", "time": time.time(), "station": "Radio Four D M"}

@app.get("/api/status")
async def get_station_status():
    status = station_engine.get_status()
    status["scheduler_enabled"] = time_scheduler.is_enabled()
    status["news_scheduler_enabled"] = time_scheduler.is_news_enabled()
    status["cricket_scheduler_enabled"] = time_scheduler.is_cricket_enabled()
    status["cricket_lang"] = time_scheduler.get_cricket_lang()
    status["autodj_enabled"] = auto_dj.is_enabled()
    status["config"] = load_config()
    return status

@app.get("/api/config")
async def get_system_config():
    return load_config()

@app.post("/api/config")
async def update_system_config(req: ConfigUpdateRequest):
    cfg = load_config()
    if req.tts_provider is not None:
        cfg["tts_provider"] = req.tts_provider
    if req.gemini_api_key is not None:
        cfg["gemini_api_key"] = req.gemini_api_key.strip()
    if req.elevenlabs_api_key is not None:
        cfg["elevenlabs_api_key"] = req.elevenlabs_api_key.strip()
    if req.elevenlabs_voice_id is not None:
        cfg["elevenlabs_voice_id"] = req.elevenlabs_voice_id.strip()
    if req.crossfade_seconds is not None:
        cfg["crossfade_seconds"] = int(req.crossfade_seconds)
    if req.ducking_volume is not None:
        cfg["ducking_volume"] = float(req.ducking_volume)
    
    save_config(cfg)
    return {"status": "success", "config": cfg}

@app.get("/api/config/gemini-status")
async def get_gemini_status_endpoint():
    cfg = load_config()
    key = cfg.get("gemini_api_key", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return {
            "configured": False,
            "valid": False,
            "masked_key": "",
            "message": "No Gemini API key configured"
        }
    
    # Fast test with Google GenAI
    try:
        from google import genai
        client = genai.Client(api_key=key)
        # Attempt to list one model
        for _ in client.models.list():
            break
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
        return {
            "configured": True,
            "valid": True,
            "masked_key": masked,
            "message": "Gemini AI API Key verified and active"
        }
    except Exception as e:
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
        return {
            "configured": True,
            "valid": False,
            "masked_key": masked,
            "message": f"Auth error: {str(e)[:120]}"
        }

@app.post("/api/config/verify-gemini")
async def verify_and_save_gemini_key(req: GeminiVerifyRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API Key cannot be empty.")
    
    try:
        from google import genai
        client = genai.Client(api_key=key)
        # Verify by querying models
        for _ in client.models.list():
            break
        
        # Save valid key
        cfg = load_config()
        cfg["gemini_api_key"] = key
        cfg["tts_provider"] = "gemini"
        save_config(cfg)
        os.environ["GEMINI_API_KEY"] = key
        
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
        return {
            "status": "success",
            "valid": True,
            "masked_key": masked,
            "message": "Google Gemini API Key successfully verified and linked!"
        }
    except Exception as e:
        err_msg = str(e)
        return {
            "status": "error",
            "valid": False,
            "detail": err_msg
        }

# DJ Mixer Controls
@app.post("/api/dj/sfx")
async def play_dj_sfx(req: SfxRequest):
    """Trigger a DJ Sound Effect over the live broadcast."""
    success = station_engine.trigger_sfx(req.sfx)
    if not success:
        raise HTTPException(status_code=404, detail="SFX not found")
    return {"status": "success", "sfx": req.sfx}

@app.post("/api/dj/crossfade")
async def set_crossfade(req: CrossfadePosRequest):
    station_engine.set_manual_crossfade(req.pos)
    return {"status": "success", "pos": req.pos}

@app.post("/api/dj/deck/gain")
async def set_deck_gain(req: DeckGainRequest):
    station_engine.set_deck_gain(req.deck, req.gain)
    return {"status": "success", "deck": req.deck, "gain": req.gain}

@app.post("/api/dj/deck/mute")
async def toggle_deck_mute(req: DeckMuteRequest):
    is_muted = station_engine.toggle_deck_mute(req.deck)
    return {"status": "success", "deck": req.deck, "is_muted": is_muted}

@app.post("/api/queue/youtube")
async def add_youtube_song(req: YouTubeRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL or search query required")
    try:
        track = await asyncio.to_thread(station_engine.add_youtube_track, req.url)
        return {"status": "success", "track": track}
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load YouTube audio: {str(e)}")

@app.post("/api/search/tracks")
async def search_tracks_endpoint(req: SearchRequest):
    """Search for songs and DJ remixes online returning top 4-5 candidates with metadata."""
    if not req.query:
        return {"status": "success", "results": []}
    results = await asyncio.to_thread(station_engine.search_tracks, req.query, req.limit or 5)
    return {"status": "success", "results": results}

@app.post("/api/queue/add-direct")
async def add_direct_track(track: dict):
    """Directly queues a pre-resolved track into the standby playlist."""
    try:
        t = station_engine.queue_track_direct(track)
        return {"status": "success", "track": t}
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/queue/{track_id}")
async def delete_queue_song(track_id: str):
    removed = station_engine.remove_playlist_track(track_id)
    return {"status": "success", "removed": removed}

@app.post("/api/queue/play-next")
async def queue_make_next(req: TrackActionRequest):
    """Make this song the very next track in the standby playlist."""
    success = station_engine.move_track_to_next(req.track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found in queue")
    return {"status": "success", "message": "Song moved to NEXT position"}

@app.post("/api/queue/play-now")
async def queue_play_now(req: TrackActionRequest):
    """Instantly crossfade to this specific standby track right now."""
    success = station_engine.play_track_now(req.track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found in queue")
    return {"status": "success", "message": "Now playing chosen track"}

@app.post("/api/queue/move")
async def queue_move(req: TrackMoveRequest):
    """Move track up or down to reorder playlist pattern."""
    success = station_engine.move_track(req.track_id, req.direction)
    return {"status": "success", "moved": success}

@app.delete("/api/queue")
async def clear_queue():
    station_engine.clear_playlist()
    return {"status": "success", "message": "Queue cleared"}

@app.post("/api/charts/load")
async def load_chart_songs(req: ChartLoadRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(auto_dj.load_preset_chart, req.chart, req.count)
        return {
            "status": "success",
            "message": f"Queuing {req.count} random unique tracks from {req.chart.title()} Chart..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart loading error: {str(e)}")

@app.post("/api/queue/random")
async def add_random_song(background_tasks: BackgroundTasks):
    try:
        item = auto_dj.get_next_unplayed_catalog_item()
        if item:
            background_tasks.add_task(auto_dj.queue_single_chart_item, item)
            return {"status": "success", "message": f"Queuing random track: {item['title']} ({item.get('category')})"}
        return {"status": "error", "message": "No unplayed songs available."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Random queue error: {str(e)}")

@app.post("/api/autodj/toggle")
async def toggle_autodj(req: AutoDJToggleRequest):
    auto_dj.set_enabled(req.enabled)
    return {"status": "success", "autodj_enabled": req.enabled}

@app.post("/api/ad/speak")
async def trigger_ad_speak(req: AdSpeakRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        def _worker_generate_and_inject():
            audio_file = generate_speech_file_sync(
                text=req.text,
                voice_key=req.voice,
                lang=req.lang,
                provider=req.provider,
                rate=req.rate,
                pitch=req.pitch,
                filename_prefix="ad",
                add_chime=True
            )
            station_engine.inject_priority_audio(
                audio_file_path=audio_file,
                title=f"දැන්වීම (Ad): {req.text[:30]}...",
                audio_type="ad",
                play_immediately=req.immediate
            )

        # Offload TTS generation and FFmpeg conversion completely off the event loop
        await asyncio.to_thread(_worker_generate_and_inject)
        return {"status": "success", "message": "Advertisement playing over dimmed music (Audio Ducking active)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

@app.post("/api/time/trigger")
async def trigger_time():
    try:
        res = await time_scheduler.broadcast_time_async()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Time broadcast error: {str(e)}")

@app.post("/api/time/toggle")
async def toggle_time_scheduler(req: TimeToggleRequest):
    time_scheduler.set_enabled(req.enabled)
    return {"status": "success", "scheduler_enabled": req.enabled}

class NewsToggleRequest(BaseModel):
    enabled: bool

@app.get("/api/news/latest")
async def get_latest_news():
    from news_engine import fetch_quick_news
    news = await asyncio.to_thread(fetch_quick_news)
    if news:
        return {"status": "success", "news": news}
    return {"status": "error", "message": "Unable to fetch news"}

@app.post("/api/news/trigger")
async def trigger_news_broadcast():
    try:
        res = await time_scheduler.broadcast_news_async()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News broadcast error: {str(e)}")

@app.post("/api/news/toggle")
async def toggle_news_scheduler(req: NewsToggleRequest):
    time_scheduler.set_news_enabled(req.enabled)
    return {"status": "success", "news_scheduler_enabled": req.enabled}

class CricketBroadcastRequest(BaseModel):
    lang: str = "si" # "si" (Sinhala) or "en" (English)

class CricketSchedulerRequest(BaseModel):
    enabled: bool

class CricketLangRequest(BaseModel):
    lang: str

@app.get("/api/cricket/latest")
async def get_latest_cricket(lang: str = "si"):
    """Fetch latest Cricbuzz live cricket match data in Sinhala or English."""
    from cricket_engine import get_cricket_highlights_text
    cricket = await asyncio.to_thread(get_cricket_highlights_text, lang)
    return {"status": "success", "cricket": cricket}

@app.post("/api/cricket/toggle")
async def toggle_cricket_scheduler(req: CricketSchedulerRequest):
    """Enable or disable the 20-minute Cricbuzz live match broadcast scheduler."""
    time_scheduler.set_cricket_enabled(req.enabled)
    return {"status": "success", "cricket_scheduler_enabled": req.enabled}

@app.post("/api/cricket/language")
async def set_cricket_scheduler_language(req: CricketLangRequest):
    """Set the commentary language (si / en) for 20-minute Cricbuzz broadcasts."""
    time_scheduler.set_cricket_lang(req.lang)
    return {"status": "success", "cricket_lang": req.lang}

@app.post("/api/cricket/broadcast")
async def broadcast_cricket_highlights(req: CricketBroadcastRequest):
    """
    Broadcasts Live Cricket Highlights with 20% ducking over music in chosen language (si / en).
    Condition: Broadcasts ONLY if an active live match is currently running on Cricbuzz.
    """
    from cricket_engine import build_cricket_broadcast_audio, get_cricket_highlights_text
    meta = await asyncio.to_thread(get_cricket_highlights_text, req.lang)
    if not meta.get("has_live"):
        return {
            "status": "skipped",
            "message": "Cricbuzz හි මේ මොහොතේ සජීවී තරග නොමැත (No active live matches currently in progress). සජීවී තරගයක් ආරම්භ වූ වහාම විකාශය කෙරේ.",
            "has_live": False
        }

    def _worker():
        try:
            audio_path = build_cricket_broadcast_audio(req.lang, preloaded_data=meta)
            if audio_path:
                title = f"{meta.get('headline', '🏏 Cricbuzz Cricket Highlights')}"
                station_engine.inject_priority_audio(audio_path, title=title, audio_type="ad", play_immediately=True)
        except Exception as e:
            print(f"[Cricket Broadcast Error] {e}")

    threading.Thread(target=_worker, daemon=True).start()
    return {
        "status": "success", 
        "has_live": True,
        "message": f"Broadcasting Cricbuzz live cricket highlights ({req.lang.upper()}) on radio with 20% ducking"
    }

@app.post("/api/control/skip")
async def skip_track():
    station_engine.skip()
    return {"status": "success", "message": "Crossfading into next track..."}

class VoiceGainRequest(BaseModel):
    gain: float

@app.post("/api/control/voice-gain")
async def set_station_voice_gain(req: VoiceGainRequest):
    """Sets master gain multiplier for all AI speech/voiceovers (e.g. 1.35 = 135%)."""
    station_engine.set_voice_gain(req.gain)
    return {
        "status": "success",
        "voice_gain": float(round(station_engine.master_voice_gain, 2)),
        "voice_gain_pct": int(round(station_engine.master_voice_gain * 100))
    }

class OnAirRequest(BaseModel):
    on_air: Optional[bool] = None

@app.post("/api/control/on-air")
async def toggle_master_on_air(req: OnAirRequest):
    """Toggle or set Master Broadcast ON AIR / OFF AIR."""
    if req.on_air is None:
        state = station_engine.toggle_on_air()
    else:
        state = station_engine.set_on_air(req.on_air)
    return {"status": "success", "on_air": state}

class PreRenderedVoiceRequest(BaseModel):
    clip: str

PROMO_SCRIPTS = {
    "promo_discounts": {
        "text": "මෙම හෝරාව Radio 4DM වෙතින් ඔබ වෙත ගෙන එන්නේ විශේෂ වෙළඳ දැන්වීමක් සමඟින්. සුවිශේෂී වට්ටම් සහ අනගි දීමනා රැසක් ලබාගන්න අදම සම්බන්ධ වන්න!",
        "title": "RJ Drop: විශේෂ වට්ටම් වෙළඳ දැන්වීම"
    },
    "promo_wishes": {
        "text": "Radio 4DM සමඟින් එකතුවී සිටින අපගේ ආදරණීය සියලුම ශ්‍රාවක යහළු යෙහෙළියන්ට සුබම සුබ දවසක් වේවා කියා අපි ආදරයෙන් ප්‍රාර්ථනා කරනවා!",
        "title": "RJ Drop: ශ්‍රාවක සුබ පැතුම්"
    },
    "promo_station_id": {
        "text": "ඔබ මේ ශ්‍රවණය කරන්නේ අන්තර්ජාලය ඔස්සේ ලොව පුරා විකාශනය වන ඔබේ ආදරණීය Radio 4DM සජීවී විකාශයයි! දිගටම රැඳී සිටින්න!",
        "title": "RJ Drop: Radio Station ID Drop"
    },
    "promo_morning": {
        "text": "සුබ උදෑසනක් වේවා යාලුවනේ! අද දවසත් Radio 4DM ලස්සනම සිංදු එක්ක සතුටින් ගත කරන්න අපිත් එක්ක එකතු වෙන්න!",
        "title": "RJ Drop: සුබ උදෑසනක් සුබපැතුම"
    },
    "promo_night": {
        "text": "සුබ රාත්‍රියක් යාලුවනේ! හිතට සනීපයක් ගෙනෙන ලස්සනම සිංදු අහන්න රැඳී ඉන්න ඔබේ Radio 4DM එක්ක!",
        "title": "RJ Drop: සුබ රාත්‍රියක් සුබපැතුම"
    },
    "promo_next_song": {
        "text": "ඔන්න එහෙනම් ඊළඟට Radio 4DM අපි සූදානම් වන්නේ ඔබ වඩාත්ම ආදරය කරන තවත් ලස්සනම ගීතයක් ඔබට තිළිණ කරන්න. රසවිඳින්න!",
        "title": "RJ Drop: මීළඟ ගීතය හඳුන්වාදීම"
    },
    "promo_birthday": {
        "text": "අද දින උපන්දිනය සමරන අපගේ ආදරණීය ශ්‍රාවක යහළු යෙහෙළියන්ට Radio 4DM පවුලේ සැමගෙන් සුබම සුබ උපන්දිනයක් වේවා කියා ආදරයෙන් ප්‍රාර්ථනා කරනවා!",
        "title": "RJ Drop: උපන්දින සුබ පැතුම්"
    },
    "promo_comedy": {
        "text": "ආයුබෝවන් යාලුවනේ! වැඩ රාජකාරි කරලා ඔළුවත් රිදෙනවා නේද? කිසි දේකට හිත කරදර කරගන්න එපා, Radio 4DM එක දාලා සින්දුවක් අහලා full chill එකක් දාන්න!",
        "title": "RJ Drop: විනෝදජනක කතාබහ"
    },
    "promo_dedication": {
        "text": "අප සමඟින් රැඳී සිටින ආදරණීය ශ්‍රාවක ඔබ වෙනුවෙන්ම Radio 4DM වෙතින් පිරිනමන විශේෂ ගීත තිළිණයයි මේ. දිගටම රැඳී සිටින්න අප සමඟින්!",
        "title": "RJ Drop: විශේෂ ගීත තිළිණය"
    },
    "promo_radio_future": {
        "text": "Listen to the best hits, nonstop music on Radio Four D M - The Future of Digital Sound!",
        "title": "RJ Drop: Future Sound Radio ID"
    },
    "promo_traffic": {
        "text": "ට්‍රැෆික් එකේ හිරවෙලාද ඉන්නේ? එහෙනම් හෝන් ගහලා වැඩක් නෑ, Radio 4DM volume එක වැඩි කරලා බීට් එකට නටන්න!",
        "title": "RJ Drop: ට්‍රැෆික් විනෝදය"
    }
}

@app.post("/api/voice/prerendered/play")
async def play_prerendered_voice(req: PreRenderedVoiceRequest):
    """Broadcasts 1-Click Studio RJ Drop with Gemini AI Real Girl voice, 100% pure Sinhala."""
    clip_id = req.clip
    clip_info = PROMO_SCRIPTS.get(clip_id)
    title = clip_info["title"] if clip_info else f"RJ Studio Drop: {clip_id}"
    text = clip_info["text"] if clip_info else None

    # Offload voice generation / playback to worker thread
    def _worker():
        audio_file = None
        # Try dynamic Gemini AI synthesis in pure Sinhala
        if text:
            try:
                audio_file = generate_speech_file_sync(
                    text=text,
                    voice_key="si-female",
                    lang="si",
                    provider="gemini",
                    filename_prefix=clip_id,
                    add_chime=True
                )
            except Exception as ge:
                print(f"[RJ Drop] Dynamic Gemini generation fallback: {ge}")

        # Fallback to pre-rendered file if available
        if not audio_file or not os.path.exists(audio_file):
            prerender_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache", "prerendered")
            file_path = os.path.join(prerender_dir, f"{clip_id}.mp3")
            if os.path.exists(file_path):
                audio_file = file_path

        if not audio_file or not os.path.exists(audio_file):
            raise RuntimeError(f"Unable to play clip '{clip_id}'")

        station_engine.inject_priority_audio(
            audio_file_path=audio_file,
            title=title,
            audio_type="ad",
            play_immediately=True
        )

    try:
        await asyncio.to_thread(_worker)
        return {"status": "success", "clip": clip_id, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error playing drop: {str(e)}")

@app.post("/api/tagline/play")
async def trigger_station_tagline(req: TaglineRequest):
    """Trigger Radio 4DM official Station Tagline in random or chosen accent/voice persona."""
    info = get_tagline_info(req.tagline_id)

    def _tagline_worker():
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
            title=f"Radio 4DM Tagline • {info['title']}",
            audio_type="ad",
            play_immediately=True
        )

    try:
        await asyncio.to_thread(_tagline_worker)
        return {
            "status": "success",
            "tagline_id": info["id"],
            "title": info["title"],
            "text": info["text"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tagline error: {str(e)}")

@app.post("/api/weather/broadcast")
async def trigger_colombo_weather():
    """Trigger Colombo live weather announcement over music (Ducking)."""
    try:
        res = await time_scheduler.broadcast_weather_async()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather broadcast error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Render defaults to 10000, Hugging Face to 7860, Local to 8000
    raw_port = os.getenv("PORT")
    if raw_port:
        port = int(raw_port)
    elif os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"):
        port = 10000
    else:
        port = 8000
    print(f"[Radio Four D M] Starting server on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
