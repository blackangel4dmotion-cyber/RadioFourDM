import os
import sys
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg
from tts_engine import load_config, _generate_gemini_live_sync

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "audio_cache")
PRERENDER_DIR = os.path.join(CACHE_DIR, "prerendered")
os.makedirs(PRERENDER_DIR, exist_ok=True)

CHIME_FILE = os.path.join(CACHE_DIR, "chime.mp3")
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

HOURLY_TEXTS = {
    0: "හායි යාලුවනේ... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව මැදියම් රැය දොළහයි. දිගටම ලස්සන සිංදු අහන්න රැඳී ඉන්න Radio 4DM එක්ක!",
    1: "සුබ රාත්‍රියක්... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව මැදියම් රැයේ එකයි. සනීපෙට නිදාගන්න ලස්සනම සිංදු අහන්න රැඳී ඉන්න!",
    2: "දැන් වෙලාව මැදියම් රැයේ දෙකයි. Radio 4DM අඛණ්ඩ මියුරු ගීත ප්‍රවාහය සමඟයි ඔබ මේ රැඳී සිටින්නේ.",
    3: "දැන් වෙලාව පාන්දර තුනයි. Radio 4DM ලස්සනම සිංදු එක්ක අපි දිගටම ඉන්නවා.",
    4: "සුබ පාන්දරක් යාලුවනේ... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව පාන්දර හතරයි. අලුත් දවසකට සූදානම් වෙන්න අපිත් එක්ක එකතු වෙන්න!",
    5: "සුබ පාන්දරක් වේවා! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව පාන්දර පහයි. ප්‍රබෝධමත් උදෑසනක් සඳහා ලස්සනම ගීත සමඟින් Radio 4DM ඔබ ළඟින්ම ඉන්නවා.",
    6: "සුබ උදෑසනක් වේවා යාලුවනේ! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව උදෑසන හයයි. අද දවසත් සාර්ථක දවසක් කරගන්න Radio 4DM එක්ක රැඳී ඉන්න!",
    7: "හායි යාලුවනේ... සුබ උදෑසනක්! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව උදෑසන හතයි. ප්‍රබෝධමත් ගීත සමඟින් අපේ විකාශය දිගටම!",
    8: "සුබ උදෑසනක්! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව උදෑසන අටයි. වැඩට යන ගමන්, ගෙදර ඉන්න ගමන් ආසම සිංදු අහන්න Radio 4DM එක්ක එකතු වෙන්න!",
    9: "ඔන්න එහෙනම් Radio 4DM වෙලාව උදෑසන නමයයි. ඔබ ආදරය කරන ජනප්‍රියම ගීත පෙළක් සමඟින් අපි දිගටම රැඳී ඉන්නවා.",
    10: "හායි යාලුවනේ... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව උදෑසන දහයයි. හිතට සතුට ගෙනෙන ලස්සනම ගීත අහන්න දිගටම රැඳී ඉන්න!",
    11: "දැන් වෙලාව උදෑසන එකොළහයි. දවසේ වැඩකටයුතු අතරතුර රසවත් ගීත සමඟින් Radio 4DM ඔබේ තනිකම මකනවා.",
    12: "සුබ මධ්‍යහ්නයක් යාලුවනේ! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව දහවල් දොළහයි. දිවා විවේකය සතුටින් ගතකරන්න Radio 4DM එක්ක එකතු වෙන්න!",
    13: "දැන් වෙලාව දහවල් එකයි. Radio 4DM අඛණ්ඩව ගලායන ජනප්‍රිය ගීත ප්‍රවාහය සමඟින් දිගටම රැඳී සිටින්න.",
    14: "හායි යාලුවනේ... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව දහවල් දෙකයි. හිතට නිදහස දෙන ලස්සනම සිංදු එක්ක අපි ඉන්නවා.",
    15: "දැන් වෙලාව හවස තුනයි. තේ වෙලාවට ලස්සනම සිංදුවක් අහන්න රැඳී ඉන්න Radio 4DM සමඟ.",
    16: "සුබ සන්ධ්‍යාවක් යාලුවනේ! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව හවස හතරයි. හවස් වරුව ලස්සන කරගන්න ආදරණීය ගීත සමඟින් Radio 4DM ඉන්නවා.",
    17: "ඔන්න Radio 4DM වෙතින් දැන් වෙලාව හවස පහයි. දවසේ වෙහෙස නිවාගන්න හොඳම සිංදු අහන්න එකතු වෙන්න!",
    18: "සුබ සන්ධ්‍යාවක් වේවා! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව සවස හයයි. සවස් යාමය ආලෝකමත් කරන ගීත පෙළක් සමඟින් දිගටම රැඳී ඉන්න.",
    19: "හායි යාලුවනේ... ඔන්න Radio 4DM වෙතින් දැන් වෙලාව රාත්‍රී හතයි. රාත්‍රී විවේකය සතුටින් ගතකරන්න Radio 4DM එක්ක ඉන්න.",
    20: "සුබ රාත්‍රියක්! ඔන්න Radio 4DM වෙතින් දැන් වෙලාව රාත්‍රී අටයි. ලස්සනම ලස්සන ආදරණීය ගීත සමඟින් Radio 4DM දිගටම ඔබ ළඟින්ම ඉන්නවා.",
    21: "දැන් වෙලාව රාත්‍රී නමයයි. හිතට සනීපයක් ගෙනෙන මියුරු ගීත සමඟින් Radio 4DM සමඟින් දිගටම රැඳී සිටින්න.",
    22: "ඔන්න Radio 4DM වෙතින් දැන් වෙලාව රාත්‍රී දහයයි. නිදහස් රාත්‍රියකට සුවදායක ගීත රැසක් සමඟින් ඔබ මේ එක්වන්නේ අපගේ සජීවී විකාශය සමඟයි.",
    23: "දැන් වෙලාව රාත්‍රී එකොළහයි. සුන්දර හීන දකින රාත්‍රියකට ආදරණීය ගීත එක්ක Radio 4DM අපි ඔබට සුබ රාත්‍රියක් ප්‍රාර්ථනා කරනවා."
}

PROMO_DROPS = {
    "promo_discounts": "මෙම හෝරාව Radio 4DM වෙතින් ඔබ වෙත ගෙන එන්නේ විශේෂ වෙළඳ දැන්වීමක් සමඟින්. සුවිශේෂී වට්ටම් සහ අනගි දීමනා රැසක් ලබාගන්න අදම සම්බන්ධ වන්න!",
    "promo_wishes": "Radio 4DM සමඟින් එකතුවී සිටින අපගේ ආදරණීය සියලුම ශ්‍රාවක යහළු යෙහෙළියන්ට සුබම සුබ දවසක් වේවා කියා අපි ආදරයෙන් ප්‍රාර්ථනා කරනවා!",
    "promo_station_id": "ඔබ මේ ශ්‍රවණය කරන්නේ අන්තර්ජාලය ඔස්සේ ලොව පුරා විකාශනය වන ඔබේ ආදරණීය Radio 4DM සජීවී විකාශයයි! දිගටම රැඳී සිටින්න!",
    "promo_morning": "සුබ උදෑසනක් වේවා යාලුවනේ! අද දවසත් Radio 4DM ලස්සනම සිංදු එක්ක සතුටින් ගත කරන්න අපිත් එක්ක එකතු වෙන්න!",
    "promo_night": "සුබ රාත්‍රියක් යාලුවනේ! හිතට සනීපයක් ගෙනෙන ලස්සනම සිංදු අහන්න රැඳී ඉන්න ඔබේ Radio 4DM එක්ක!",
    "promo_next_song": "ඔන්න එහෙනම් ඊළඟට Radio 4DM අපි සූදානම් වන්නේ ඔබ වඩාත්ම ආදරය කරන තවත් ලස්සනම ගීතයක් ඔබට තිළිණ කරන්න. රසවිඳින්න!",
    "promo_birthday": "අද දින උපන්දිනය සමරන අපගේ ආදරණීය ශ්‍රාවක යහළු යෙහෙළියන්ට Radio 4DM පවුලේ සැමගෙන් සුබම සුබ උපන්දිනයක් වේවා කියා ආදරයෙන් ප්‍රාර්ථනා කරනවා!",
    "promo_comedy": "ආයුබෝවන් යාලුවනේ! වැඩ රාජකාරි කරලා ඔළුවත් රිදෙනවා නේද? කිසි දේකට හිත කරදර කරගන්න එපා, Radio 4DM එක දාලා සින්දුවක් අහලා full chill එකක් දාන්න!",
    "promo_dedication": "අප සමඟින් රැඳී සිටින ආදරණීය ශ්‍රාවක ඔබ වෙනුවෙන්ම Radio 4DM වෙතින් පිරිනමන විශේෂ ගීත තිළිණයයි මේ. දිගටම රැඳී සිටින්න අප සමඟින්!",
    "promo_radio_future": "Listen to the best hits, nonstop music on Radio Four D M - The Future of Digital Sound!",
    "promo_traffic": "ට්‍රැෆික් එකේ හිරවෙලාද ඉන්නේ? එහෙනම් හෝන් ගහලා වැඩක් නෑ, Radio 4DM volume එක වැඩි කරලා බීට් එකට නටන්න!"
}

async def render_clip(name: str, text: str, add_chime: bool = True):
    raw_path = os.path.join(PRERENDER_DIR, f"raw_{name}.mp3")
    final_path = os.path.join(PRERENDER_DIR, f"{name}.mp3")
    
    cfg = load_config()
    gemini_key = cfg.get("gemini_api_key", "").strip()
    
    generated = False
    
    # 1. Try Gemini Live Native Voice
    if gemini_key:
        try:
            ok_live = _generate_gemini_live_sync(gemini_key, text, "Aoede", True, raw_path)
            if ok_live and os.path.exists(raw_path) and os.path.getsize(raw_path) > 500:
                generated = True
                print(f"[Gemini Live AI] Generated: {name}")
        except Exception as e:
            print(f"[Gemini Live] Error: {e}")

    # 1b. Try Gemini GenerateContent models if Live failed
    if not generated and gemini_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            raw_audio_temp = os.path.join(PRERENDER_DIR, f"temp_{name}.bin")
            gemini_prompt = (
                "You are a lively, native Sri Lankan female radio RJ on station 'Radio 4DM'.\n"
                "Task: Read the following Sinhala announcement aloud in an energetic, cheerful, friendly broadcast voice with a natural Sri Lankan radio accent.\n"
                "STRICT RULE: Speak 100% ONLY in pure natural Sinhala. Do NOT speak any English words, and do NOT translate.\n"
                f"Script:\n{text}"
            )
            for model_id in ['gemini-3.1-flash-tts-preview', 'gemini-2.5-flash-preview-tts', 'gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts']:
                try:
                    resp = client.models.generate_content(
                        model=model_id,
                        contents=gemini_prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Aoede"
                                    )
                                )
                            )
                        )
                    )
                    for cand in (resp.candidates or []):
                        if not cand.content or not cand.content.parts:
                            continue
                        for part in cand.content.parts:
                            if part.inline_data and part.inline_data.data:
                                with open(raw_audio_temp, "wb") as f:
                                    f.write(part.inline_data.data)
                                ffmpeg_exe = FFMPEG_EXE
                                mime = (part.inline_data.mime_type or "").lower()
                                if "pcm" in mime or "l16" in mime or "raw" in mime:
                                    conv = [
                                        ffmpeg_exe, "-f", "s16le", "-ar", "24000", "-ac", "1",
                                        "-i", raw_audio_temp,
                                        "-acodec", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                                        "-y", raw_path
                                    ]
                                else:
                                    conv = [
                                        ffmpeg_exe, "-i", raw_audio_temp,
                                        "-acodec", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                                        "-y", raw_path
                                    ]
                                subprocess.run(conv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                if os.path.exists(raw_path) and os.path.getsize(raw_path) > 500:
                                    generated = True
                                    print(f"[Gemini AI] Generated ({model_id}): {name}")
                                try:
                                    os.remove(raw_audio_temp)
                                except Exception:
                                    pass
                                if generated:
                                    break
                        if generated:
                            break
                    if generated:
                        break
                except Exception as m_err:
                    pass
        except Exception as e:
            print(f"[Gemini TTS] Error: {e}, falling back to Studio RJ voice")

    # 2. High-Fidelity Female Studio Voice (Edge-TTS Tuned Thilini)
    if not generated:
        comm = edge_tts.Communicate(text, "si-LK-ThiliniNeural", rate="-2%", pitch="+1Hz")
        await comm.save(raw_path)
    
    if add_chime and os.path.exists(CHIME_FILE):
        cmd = [
            FFMPEG_EXE,
            "-i", CHIME_FILE,
            "-i", raw_path,
            "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
            "-map", "[out]",
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            "-y", final_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(raw_path):
            os.remove(raw_path)
    else:
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(raw_path, final_path)
        
    print(f"[Radio 4DM PreRender] Rendered {name}.mp3 ({os.path.getsize(final_path)} bytes)")
    return final_path

async def main():
    print("=== Generating Official Radio 4DM Studio Female RJ Voices ===")
    
    for h in range(24):
        await render_clip(f"time_hour_{h:02d}", HOURLY_TEXTS[h], add_chime=True)
        await asyncio.sleep(0.2)
        
    for key, text in PROMO_DROPS.items():
        await render_clip(key, text, add_chime=True)
        await asyncio.sleep(0.2)
        
    print("=== All Radio 4DM Studio Voices Successfully Pre-rendered! ===")

if __name__ == "__main__":
    asyncio.run(main())
