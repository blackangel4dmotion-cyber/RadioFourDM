import os
import json
import asyncio
import edge_tts
import time
import requests
import subprocess
import imageio_ffmpeg
from typing import Optional, Dict, Any, List
from gtts import gTTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CHIME_FILE = os.path.join(CACHE_DIR, "chime.mp3")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Default Config
DEFAULT_CONFIG = {
    "tts_provider": "gemini", # 'gemini', 'elevenlabs', 'google', 'edge'
    "gemini_api_key": "",
    "elevenlabs_api_key": "",
    "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",
    "crossfade_seconds": 6,
    "ducking_volume": 0.18,
    "style": "friendly_rj",
    "station_name": "Radio 4DM"
}

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    env_gemini = os.getenv("GEMINI_API_KEY")
    if env_gemini:
        cfg["gemini_api_key"] = env_gemini
    return cfg

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Error saving config: {e}")

VOICES = {
    "si-female": "si-LK-ThiliniNeural",
    "si-male": "si-LK-SameeraNeural",
    "en-female": "en-US-JennyNeural",
    "en-male": "en-US-GuyNeural"
}

def get_sinhala_time_text(hour: int, minute: int, style: str = "friendly_rj") -> str:
    """Convert 24-hour time to natural spoken Sinhala text for radio RJ."""
    hour_words = {
        1: "එකයි", 2: "දෙකයි", 3: "තුනයි", 4: "හතරයි",
        5: "පහයි", 6: "හයයි", 7: "හතයි", 8: "අටයි",
        9: "නමයයි", 10: "දහයයි", 11: "එකොළහයි", 12: "දොළහයි"
    }

    minute_words = {
        0: "", 5: "පහයි", 10: "දහයයි", 15: "පහළොවයි", 20: "විස්සයි",
        25: "විසිපහයි", 30: "තිහයි", 35: "තිස්පහයි", 40: "හතළිහයි",
        45: "හතළිස්පහයි", 50: "පනහයි", 55: "පනස්පහයි"
    }

    h12 = hour % 12
    if h12 == 0:
        h12 = 12

    if 0 <= hour < 4:
        period = "මැදියම් රැයේ"
    elif 4 <= hour < 6:
        period = "පාන්දර"
    elif 6 <= hour < 12:
        period = "උදෑසන"
    elif hour == 12:
        period = "දහවල්"
    elif 13 <= hour < 18:
        period = "හවස"
    else:
        period = "රෑ"

    h_word = hour_words.get(h12, f"{h12} යි")

    if minute == 0:
        time_phrase = f"{period} {h_word}"
    else:
        m_closest = round(minute / 5) * 5
        h_prefix = h_word.rstrip("යි")
        if m_closest in minute_words and minute_words[m_closest]:
            time_phrase = f"{period} {h_prefix} {minute_words[m_closest]}"
        else:
            time_phrase = f"{period} {h_prefix} විනාඩි {minute} යි"

    if style == "friendly_rj":
        import random
        templates = [
            f"හායි යාලුවනේ... ඔන්න Radio Four D M වෙතින් දැන් වෙලාව {time_phrase}. දිගටම ලස්සන සිංදු අහන්න රැඳී ඉන්න Radio Four D M එක්ක!",
            f"සුබ මොහොතක් යාලුවනේ! ඔන්න Radio Four D M හෝරා නිවේදනය, දැන් වෙලාව {time_phrase} වුණා. ආසම සිංදු එක්ක අපි දිගටම ඉන්නවා, Stay tuned to Radio Four D M!",
            f"ඔන්න එහෙනම් Radio Four D M වෙලාව බැලුවොත් දැන් {time_phrase}. දිගටම ලස්සනම සිංදු අහන්න එකතු වෙන්න Radio Four D M එක්ක!",
            f"Radio Four D M අහන යාලුවෝ හැමෝටම ආදරයෙන් මතක් කරන්නේ, දැන් වෙලාව {time_phrase}යි. ඔබේ දවස ලස්සන කරන සුපිරිම ගීත පෙළක් එක්ක දිගටම රැඳී ඉන්න!",
            f"සුබ දවසක් වේවා! ඔන්න Radio Four D M වෙතින් දැන් වෙලාව {time_phrase}. වැඩකටයුතු කරන ගමන්, ගෙදර ඉන්න ගමන් ලස්සනම සිංදු අහන්න Radio Four D M එක්ක ඉන්න!",
            f"ඔබ මේ එක්වන්නේ Radio Four D M හෝරා නිවේදනය සමඟයි. දැන් වේලාව {time_phrase}. හොඳම සිංදු අහන්න දිගටම රැඳී සිටින්න අප සමඟ!",
            f"හායි... Radio Four D M අහන ඔබ සැමට සුබ පැතුම්! දැන් වෙලාව {time_phrase}යි. ඔබේ හදවතට දැනෙන ලස්සනම ගීත සමඟින් අපේ සජීවී විකාශය දිගටම!",
            f"දැන් වේලාව {time_phrase}යි. Radio Four D M ඔබේ ආදරණීය සංගීත නවාතැනෙන් ඔබ කැමතිම ගීත රැසක් තවමත් ඔබ වෙනුවෙන් විකාශනය වෙනවා!",
            f"ඔන්න යාලුවනේ, Radio Four D M වෙලාව දැන් {time_phrase}. දවසේ වෙහෙස නිවාගන්න හොඳම සිංදු අහන්න දිගටම ඉන්න Radio Four D M සමඟින්!",
            f"Radio Four D M ශ්‍රාවක ඔබ සැමට සුබ මොහොතක්! දැන් වෙලාව {time_phrase}යි. ඔබේ දවස ප්‍රබෝධමත් කරන ගීත පෙළක් සමඟින් රැඳී ඉන්න Radio Four D M එක්ක!"
        ]
        return random.choice(templates)
    else:
        return f"Radio Four D M ශ්‍රාවක ඔබගේ විශේෂ අවධානයට, දැන් වේලාව {time_phrase}යි. රැඳී සිටින්න අප සමඟ."

def _generate_gemini_live_sync(gemini_key: str, text: str, voice_name: str, is_sinhala: bool, out_mp3: str) -> bool:
    """Generate high-fidelity human speech via Gemini Multimodal Live Native Audio API."""
    async def _runner():
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1alpha'})
        model = 'gemini-2.5-flash-native-audio-latest'
        if is_sinhala:
            instruction = (
                "You are a lively, native Sri Lankan female radio RJ on station Radio Four D M. "
                "The radio station name is strictly 'Radio Four D M' (pronounced in Sinhala as 'රේඩියෝ ෆෝ ඩී එම්'). "
                "Never say any other station name, and never mention any website name. "
                "Speak with genuine Sri Lankan radio RJ enthusiasm, warmth, natural rhythm, and clear Sinhala broadcast accent. "
                "Speak 100% ONLY in pure natural Sinhala. Never speak in English, do not translate, and do not use English greetings."
            )
            prompt = f"Read this radio announcement verbatim in pure natural Sinhala with radio DJ energy:\n{text}"
        else:
            instruction = (
                "You are a cheerful, young female radio RJ on station Radio 4DM. "
                "Speak with natural broadcast energy and warmth in fluent English."
            )
            prompt = f"Read this radio announcement aloud in English with radio DJ energy:\n{text}"

        config = types.LiveConnectConfig(
            response_modalities=['AUDIO'],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=instruction)]
            )
        )
        async with client.aio.live.connect(model=model, config=config) as session:
            await session.send(input=prompt, end_of_turn=True)
            audio_bytes = bytearray()
            async for response in session.receive():
                server_content = response.server_content
                if server_content is not None:
                    model_turn = server_content.model_turn
                    if model_turn is not None:
                        for part in model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                audio_bytes.extend(part.inline_data.data)
                    if server_content.turn_complete:
                        break

            if len(audio_bytes) > 1000:
                raw_bin = out_mp3 + f".{int(time.time()*1000)}.bin"
                with open(raw_bin, "wb") as f:
                    f.write(audio_bytes)
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                subprocess.run([
                    ffmpeg_exe, "-f", "s16le", "-ar", "24000", "-ac", "1",
                    "-i", raw_bin,
                    "-acodec", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                    "-y", out_mp3
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    os.remove(raw_bin)
                except Exception:
                    pass
                return os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1000
        return False

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(_runner())).result()
        else:
            return asyncio.run(_runner())
    except Exception as e:
        print(f"[Gemini Live Audio] Error: {e}")
        return False

def generate_speech_file_sync(
    text: str,
    voice_key: str = "si-female",
    lang: str = "si",
    provider: str = None,
    rate: str = "-4%",
    pitch: str = "+2Hz",
    filename_prefix: str = "tts",
    add_chime: bool = False
) -> str:
    """
    Synchronous speech generation executed in a background worker thread.
    Prevents blocking the FastAPI asyncio event loop and preserves smooth live radio streaming.
    Supports dedicated Sinhala-only ('si'), English-only ('en'), or auto-detected language mode.
    """
    cfg = load_config()
    chosen_provider = provider or cfg.get("tts_provider", "gemini")
    out_path = os.path.join(CACHE_DIR, f"{filename_prefix}_{int(time.time()*1000)}.mp3")
    temp_raw = os.path.join(CACHE_DIR, f"raw_{int(time.time()*1000)}.mp3")

    # Determine language mode strictly
    if lang == "si":
        is_sinhala = True
    elif lang == "en":
        is_sinhala = False
    else: # auto
        is_sinhala = any('\u0D80' <= c <= '\u0DFF' for c in text)

    generated = False

    # 1. Try Google Gemini Modern Audio AI if selected or API key configured
    gemini_key = cfg.get("gemini_api_key", "").strip()
    if (chosen_provider == "gemini" or not generated) and gemini_key:
        voice_name = "Aoede" if "female" in str(voice_key).lower() else "Puck"

        # 1a. Try Gemini Multimodal Live Native Audio (Real Human Expressive Voice, No 10-req daily cap)
        try:
            ok_live = _generate_gemini_live_sync(gemini_key, text, voice_name, is_sinhala, temp_raw)
            if ok_live and os.path.exists(temp_raw) and os.path.getsize(temp_raw) > 500:
                generated = True
                print(f"[TTS] Generated with Modern Google Gemini Live Native Voice ({voice_name}, lang={'si' if is_sinhala else 'en'})!")
        except Exception as live_err:
            print(f"[TTS] Gemini Live Native attempt: {live_err}")

        # 1b. Fallback to Gemini GenerateContent TTS models
        if not generated:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                raw_audio_temp = os.path.join(CACHE_DIR, f"gemini_{int(time.time()*1000)}.bin")
                
                # Select strict prompt based on language
                if is_sinhala:
                    gemini_contents = (
                        "You are a lively, native Sri Lankan female radio RJ on station 'Radio 4DM'.\n"
                        "Task: Read the following Sinhala script aloud with an enthusiastic, friendly, real radio broadcast voice and natural Sinhala accent.\n"
                        "Strict Language Rule: Speak 100% ONLY in pure natural Sinhala. Do NOT speak in English, do NOT include English words or greetings, and do NOT translate.\n"
                        f"Script to speak:\n{text}"
                    )
                else:
                    gemini_contents = (
                        "You are a cheerful young female radio RJ on station 'Radio 4DM'.\n"
                        "Task: Read the following English radio announcement aloud with a natural human broadcast voice.\n"
                        "Strict Language Rule: Speak ONLY in clear, fluent English. Do NOT speak in Sinhala.\n"
                        f"Script to speak:\n{text}"
                    )

                # Modern Gemini TTS models
                gemini_models = [
                    'gemini-3.1-flash-tts-preview',
                    'gemini-2.5-flash-preview-tts',
                    'gemini-3.8-flash-tts',
                    'gemini-3.8-flash-lite-tts'
                ]
                for model_id in gemini_models:
                    try:
                        resp = client.models.generate_content(
                            model=model_id,
                            contents=gemini_contents,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice_name
                                        )
                                    )
                                )
                            )
                        )
                        if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
                            for part in resp.candidates[0].content.parts:
                                if part.inline_data and part.inline_data.data:
                                    with open(raw_audio_temp, "wb") as f:
                                        f.write(part.inline_data.data)
                                    
                                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                                    mime = (part.inline_data.mime_type or "").lower()
                                    if "pcm" in mime or "l16" in mime or "raw" in mime:
                                        conv = [
                                            ffmpeg_exe, "-f", "s16le", "-ar", "24000", "-ac", "1",
                                            "-i", raw_audio_temp,
                                            "-acodec", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                                            "-y", temp_raw
                                        ]
                                    else:
                                        conv = [
                                            ffmpeg_exe, "-i", raw_audio_temp,
                                            "-acodec", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                                            "-y", temp_raw
                                        ]
                                    subprocess.run(conv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    if os.path.exists(temp_raw) and os.path.getsize(temp_raw) > 500:
                                        generated = True
                                        print(f"[TTS] Generated with Modern Google Gemini AI Speech ({model_id}, {voice_name}, lang={'si' if is_sinhala else 'en'})!")
                                    try:
                                        os.remove(raw_audio_temp)
                                    except Exception:
                                        pass
                                    if generated:
                                        break
                        if generated:
                            break
                    except Exception as mod_err:
                        print(f"[TTS] Gemini model {model_id} error: {mod_err}")
            except Exception as e:
                print(f"[TTS] Gemini AI error: {e}")

    # 2. Try ElevenLabs if selected and API key available
    if not generated and chosen_provider == "elevenlabs" and cfg.get("elevenlabs_api_key"):
        try:
            api_key = cfg["elevenlabs_api_key"]
            voice_id = cfg.get("elevenlabs_voice_id") or "21m00Tcm4TlvDq8ikWAM"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.45,
                    "similarity_boost": 0.85,
                    "style": 0.35,
                    "use_speaker_boost": True
                }
            }
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                with open(temp_raw, "wb") as f:
                    f.write(res.content)
                generated = True
                print("[TTS] Generated with ElevenLabs AI Multilingual v2!")
            else:
                print(f"[TTS] ElevenLabs error: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"[TTS] ElevenLabs failed: {e}")

    # 3. Fallback to Microsoft Edge-TTS Studio Neural Voice (Natural Sri Lankan RJ)
    if not generated:
        try:
            if is_sinhala:
                voice = "si-LK-ThiliniNeural" if "female" in str(voice_key).lower() else "si-LK-SameeraNeural"
            else:
                voice = "en-US-JennyNeural" if "female" in str(voice_key).lower() else "en-US-GuyNeural"
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            asyncio.run(communicate.save(temp_raw))
            generated = True
            print(f"[TTS] Backup: Generated with Neural Studio Voice ({voice})!")
        except Exception as e:
            print(f"[TTS] Edge-TTS error: {e}")

    # 4. Fallback to Google Basic TTS if absolutely needed
    if not generated:
        try:
            lang_code = 'si' if is_sinhala else 'en'
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(temp_raw)
            generated = True
            print(f"[TTS] Fallback: Generated with Basic Google Speech (lang={lang_code})!")
        except Exception as e:
            print(f"[TTS] Google TTS error: {e}")

    if not generated or not os.path.exists(temp_raw):
        raise RuntimeError("Failed to synthesize speech using all available TTS engines.")

    # Prepend radio chime/jingle
    if add_chime and os.path.exists(CHIME_FILE):
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            filter_cmd = [
                ffmpeg_exe,
                "-i", CHIME_FILE,
                "-i", temp_raw,
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                "-map", "[out]",
                "-acodec", "libmp3lame",
                "-b:a", "128k",
                "-y", out_path
            ]
            subprocess.run(filter_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.remove(temp_raw)
            except Exception:
                pass
            return out_path
        except Exception:
            return temp_raw

    return temp_raw

async def generate_speech_file(
    text: str,
    voice_key: str = "si-female",
    lang: str = "si",
    provider: str = None,
    rate: str = "-4%",
    pitch: str = "+2Hz",
    filename_prefix: str = "tts",
    add_chime: bool = False
) -> str:
    """Non-blocking asynchronous wrapper running TTS synthesis in worker thread."""
    return await asyncio.to_thread(
        generate_speech_file_sync,
        text, voice_key, lang, provider, rate, pitch, filename_prefix, add_chime
    )

async def generate_hourly_time_speech(hour: int, minute: int = 0, style: str = "friendly_rj") -> str:
    """Generate friendly female RJ radio time announcement with radio jingle."""
    text = get_sinhala_time_text(hour, minute, style=style)
    return await generate_speech_file(
        text=text,
        filename_prefix="time_rj",
        add_chime=True
    )

STATION_TAGLINES = [
    {
        "id": "tagline_si_cheerful",
        "title": "🌸 Sinhala Cheerful RJ (Radio 4DM)",
        "lang": "si",
        "voice": "si-female",
        "text": "ඔබ ශ්‍රවණය කරන්නේ Radio 4DM! ඔබේ ආදරණීය සංගීත නවාතැන."
    },
    {
        "id": "tagline_si_sweet",
        "title": "🌺 Sinhala Sweet RJ (Radio 4DM)",
        "lang": "si",
        "voice": "si-female",
        "text": "හිතට දැනෙන ලස්සනම සිංදු අහන්න, දිගටම රැඳී ඉන්න Radio 4DM එක්ක!"
    },
    {
        "id": "tagline_en_dj",
        "title": "🎧 English Cool DJ (Radio 4DM)",
        "lang": "en",
        "voice": "en-male",
        "text": "This is Radio 4DM! Non-stop beats, live 24/7 worldwide!"
    },
    {
        "id": "tagline_en_smooth",
        "title": "🎙️ English Smooth Host (Radio 4DM)",
        "lang": "en",
        "voice": "en-male",
        "text": "You are locked into Radio 4DM, streaming live in crystal-clear digital sound."
    },
    {
        "id": "tagline_en_bold",
        "title": "⚡ English Bold Voice (Radio 4DM)",
        "lang": "en",
        "voice": "en-male",
        "text": "Radio 4DM! The rhythm of the nation, live on air."
    },
    {
        "id": "tagline_si_classic",
        "title": "📻 Sinhala Classic Jingle (Radio 4DM)",
        "lang": "si",
        "voice": "si-female",
        "text": "ඔබේ දවස ලස්සන කරන සොඳුරු ගීත පෙළක් සමඟින්, මේ ඔබේම Radio 4DM!"
    }
]

def get_tagline_info(tagline_id: Optional[str] = None) -> Dict[str, Any]:
    import random
    if tagline_id:
        for t in STATION_TAGLINES:
            if t["id"] == tagline_id:
                return t
    return random.choice(STATION_TAGLINES)
