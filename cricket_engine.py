import os
import sys
import re
import time
import json
import urllib.request
import urllib.parse
import subprocess
from bs4 import BeautifulSoup
import imageio_ffmpeg
from tts_engine import generate_speech_file_sync, CACHE_DIR

CRICKET_INTRO_FILE = os.path.join(CACHE_DIR, "cricket_intro.mp3")
CRICBUZZ_SL_SCHEDULE_URL = "https://www.cricbuzz.com/cricket-team/sri-lanka/5/schedule"
CRICBUZZ_LIVE_URL = "https://www.cricbuzz.com/cricket-match/live-scores"

def ensure_cricket_intro_jingle():
    """Generates an energetic radio sports chime for cricket updates."""
    if not os.path.exists(CRICKET_INTRO_FILE):
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg,
                '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
                '-filter_complex',
                'sine=frequency=392:duration=0.15[s1];'
                'sine=frequency=494:duration=0.15[s2];'
                'sine=frequency=587:duration=0.15[s3];'
                'sine=frequency=784:duration=0.4[s4];'
                '[s2]adelay=150|150[d2];[s3]adelay=300|300[d3];[s4]adelay=450|450[d4];'
                '[s1][d2][d3][d4]amix=inputs=4,volume=2.2[aout]',
                '-map', '[aout]',
                '-t', '1.8',
                '-acodec', 'libmp3lame',
                '-b:a', '128k',
                '-y', CRICKET_INTRO_FILE
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Cricket] Error generating cricket intro jingle: {e}")

ensure_cricket_intro_jingle()

TEAM_NAMES_SINHALA = {
    "ENG": "එංගලන්තය",
    "ENGLAND": "එංගලන්තය",
    "SL": "ශ්‍රී ලංකාව",
    "SRI LANKA": "ශ්‍රී ලංකාව",
    "AUS": "ඕස්ට්‍රේලියාව",
    "AUSTRALIA": "ඕස්ට්‍රේලියාව",
    "IND": "ඉන්දියාව",
    "INDIA": "ඉන්දියාව",
    "PAK": "පාකිස්තානය",
    "PAKISTAN": "පාකිස්තානය",
    "NZ": "නවසීලන්තය",
    "NEW ZEALAND": "නවසීලන්තය",
    "RSA": "දකුණු අප්‍රිකාව",
    "SA": "දකුණු අප්‍රිකාව",
    "SOUTH AFRICA": "දකුණු අප්‍රිකාව",
    "BAN": "බංග්ලාදේශය",
    "BANGLADESH": "බංග්ලාදේශය",
    "WI": "බටහිර ඉන්දීය කොදෙව්",
    "WEST INDIES": "බටහිර ඉන්දීය කොදෙව්",
    "AFG": "ඇෆ්ගනිස්ථානය",
    "AFGHANISTAN": "ඇෆ්ගනිස්ථානය",
    "IRE": "අයර්ලන්තය",
    "IRELAND": "අයර්ලන්තය",
    "ZIM": "සිම්බාබ්වේ",
    "ZIMBABWE": "සිම්බාබ්වේ",
    "UAE": "එක්සත් අරාබි එමීර්",
    "OMAN": "ඕමානය",
    "SCO": "ස්කොට්ලන්තය",
    "SCOTLAND": "ස්කොට්ලන්තය",
    "NAM": "නැමීබියාව",
    "NAMIBIA": "නැමීබියාව",
    "NEP": "නේපාලය",
    "NEPAL": "නේපාලය",
    "NED": "නෙදර්ලන්තය",
    "NETHERLANDS": "නෙදර්ලන්තය",
    "USA": "ඇමරිකාව",
    "CAN": "කැනඩාව"
}

def translate_team_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z\s]', '', name or '').strip()
    return TEAM_NAMES_SINHALA.get(clean.upper(), clean or "ශ්‍රී ලංකාව")

def translate_match_desc_sinhala(desc: str) -> str:
    d = desc or ""
    d = re.sub(r'(\d+)(?:st|nd|rd|th)\s+Match', r'\1 වන තරගය', d, flags=re.I)
    d = re.sub(r'(\d+)(?:st|nd|rd|th)\s+Test', r'\1 වන ටෙස්ට් තරගය', d, flags=re.I)
    d = re.sub(r'(\d+)(?:st|nd|rd|th)\s+ODI', r'\1 වන එක්දින තරගය', d, flags=re.I)
    d = re.sub(r'(\d+)(?:st|nd|rd|th)\s+T20I?', r'\1 වන විස්සයි විස්ස තරගය', d, flags=re.I)
    d = re.sub(r'Final', 'අවසාන මහා තරගය', d, flags=re.I)
    d = re.sub(r'Semi[- ]?Final', 'අවසන් පූර්ව තරගය', d, flags=re.I)
    d = re.sub(r'Group\s+([A-Z])', r'\1 කාණ්ඩයේ තරගය', d, flags=re.I)
    return d

def translate_status_sinhala(status: str) -> str:
    st = status or ""
    for k, v in TEAM_NAMES_SINHALA.items():
        st = re.sub(r'\b' + re.escape(k) + r'\b', v, st, flags=re.I)
    st = re.sub(r'opt to bowl|opt to field', 'කාසියේ වාසිය දිනා පළමුව පන්දු යැවීමට තීරණය කළා', st, flags=re.I)
    st = re.sub(r'opt to bat', 'කාසියේ වාසිය දිනා පළමුව පන්දුවට පහරදීමට තීරණය කළා', st, flags=re.I)
    st = re.sub(r'lead by (\d+) runs?', r'ලකුණු \1කින් පෙරමුණේ පසුවෙනවා', st, flags=re.I)
    st = re.sub(r'trail by (\d+) runs?', r'ලකුණු \1ක් පිටුපසින් සිටිනවා', st, flags=re.I)
    st = re.sub(r'need (\d+) runs?', r'ජයග්‍රහණය සඳහා තවත් ලකුණු \1ක් අවශ්‍යයි', st, flags=re.I)
    st = re.sub(r'Day (\d+):\s*(\d+)(?:st|nd|rd|th)\s*Session', r'\1 වන දිනයේ \2 වන සැසිය', st, flags=re.I)
    st = re.sub(r'Day (\d+):\s*Stumps', r'\1 වන දිනය නිමාවට පත්ව තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Play stopped due to bad light', 'අඩු ආලෝකය හේතුවෙන් තරගය තාවකාලිකව නතර කර තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Match delayed due to rain', 'වර්ෂාව හේතුවෙන් තරගය තාවකාලිකව නතර කර තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Innings Break', 'ඉනිම නිමාවට පත්ව තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Tea Break', 'තේ පානය සඳහා තරගය නතර කර තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Lunch Break', 'දිවා ආහාරය සඳහා තරගය නතර කර තිබෙනවා', st, flags=re.I)
    st = re.sub(r'Stumps', 'දිනය නිමාවට පත්ව තිබෙනවා', st, flags=re.I)
    st = re.sub(r'won by (\d+) wkts?', r'කඩුලු \1කින් ජයග්‍රහණය කළා', st, flags=re.I)
    st = re.sub(r'won by (\d+) runs?', r'ලකුණු \1කින් ජයග්‍රහණය කළා', st, flags=re.I)
    st = re.sub(r'Match starts at', 'තරගය ආරම්භ වීමට නියමිත වේලාව', st, flags=re.I)
    return st

def format_score_speech_from_json(info: dict, score: dict) -> tuple:
    """
    Parses Cricbuzz structured matchScore JSON into:
    (short_summary_string, natural_sinhala_speech_string)
    """
    team1 = info.get('team1', {})
    team2 = info.get('team2', {})
    t1_sname = team1.get('teamSName') or team1.get('teamName') or 'Team 1'
    t2_sname = team2.get('teamSName') or team2.get('teamName') or 'Team 2'
    t1_name_si = translate_team_name(team1.get('teamName', ''))
    t2_name_si = translate_team_name(team2.get('teamName', ''))
    
    speech_parts = []
    short_parts = []

    # Team 1 Innings
    t1_inngs = (score.get('team1Score') or {}).get('inngs1')
    if t1_inngs:
        runs = t1_inngs.get('runs', 0)
        wkts = t1_inngs.get('wickets', 0)
        overs = str(t1_inngs.get('overs', ''))
        short_parts.append(f"{t1_sname}: {runs}/{wkts} ({overs} ov)")
        ov_str = ""
        if overs:
            if '.' in overs:
                ov, b = overs.split('.')
                ov_str = f"පන්දුවාර {ov}යි පන්දු {b}ක් අවසානයේ"
            else:
                ov_str = f"පන්දුවාර {overs}ක් අවසානයේ"
        w_str = "කිසිවෙකු නොදැවී" if wkts == 0 else f"කඩුලු {wkts}කට"
        speech_parts.append(f"{t1_name_si} කණ්ඩායම {ov_str} {w_str} ලකුණු {runs}ක් ලබා සිටිනවා".strip())

    # Team 2 Innings
    t2_inngs = (score.get('team2Score') or {}).get('inngs1')
    if t2_inngs:
        runs = t2_inngs.get('runs', 0)
        wkts = t2_inngs.get('wickets', 0)
        overs = str(t2_inngs.get('overs', ''))
        short_parts.append(f"{t2_sname}: {runs}/{wkts} ({overs} ov)")
        ov_str = ""
        if overs:
            if '.' in overs:
                ov, b = overs.split('.')
                ov_str = f"පන්දුවාර {ov}යි පන්දු {b}ක් අවසානයේ"
            else:
                ov_str = f"පන්දුවාර {overs}ක් අවසානයේ"
        w_str = "කිසිවෙකු නොදැවී" if wkts == 0 else f"කඩුලු {wkts}කට"
        speech_parts.append(f"{t2_name_si} කණ්ඩායම {ov_str} {w_str} ලකුණු {runs}ක් ලබා සිටිනවා".strip())

    short_summary = " | ".join(short_parts)
    speech_summary = ". ".join(speech_parts)
    return short_summary, speech_summary

def fetch_sri_lanka_schedule_matches() -> dict:
    """
    Directly scrapes https://www.cricbuzz.com/cricket-team/sri-lanka/5/schedule.
    Filters and extracts ONLY Sri Lanka matches.
    Identifies any live match currently in progress, or upcoming Sri Lanka matches.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    try:
        req = urllib.request.Request(CRICBUZZ_SL_SCHEDULE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[Cricket Engine] Cricbuzz Sri Lanka schedule fetch error: {e}")
        return {"live": None, "upcoming": None, "all": []}

    pos = html.find('teamMatchesData')
    if pos == -1:
        print("[Cricket Engine] teamMatchesData not found in Sri Lanka schedule page.")
        return {"live": None, "upcoming": None, "all": []}

    bracket_start = html.find('[', pos)
    brackets = 0
    end_idx = -1
    for i in range(bracket_start, len(html)):
        if html[i] == '[':
            brackets += 1
        elif html[i] == ']':
            brackets -= 1
            if brackets == 0:
                end_idx = i + 1
                break

    if end_idx == -1:
        return {"live": None, "upcoming": None, "all": []}

    raw_str = html[bracket_start:end_idx]
    raw_json = raw_str.replace(r'\"', '"').replace(r'\\', '\\')
    try:
        data = json.loads(raw_json)
    except Exception as e:
        print(f"[Cricket Engine] JSON parse error: {e}")
        return {"live": None, "upcoming": None, "all": []}

    live_match = None
    upcoming_match = None
    all_matches = []

    for day in data:
        key = day.get('matchDetailsMap', {}).get('key', '')
        for m in day.get('matchDetailsMap', {}).get('match', []):
            info = m.get('matchInfo', {})
            state = (info.get('state') or '').lower()
            all_matches.append(m)
            # Detect live match
            if not live_match and state in ['in progress', 'live', 'innings break', 'tea break', 'lunch break', 'rain delay', 'stumps']:
                live_match = m
            # Detect next upcoming match
            elif not upcoming_match and state in ['preview', 'upcoming']:
                upcoming_match = m

    return {
        "live": live_match,
        "upcoming": upcoming_match,
        "all": all_matches
    }

def get_cricket_highlights_text(lang: str = "si") -> dict:
    """
    Fetches Sri Lanka matches strictly from:
    https://www.cricbuzz.com/cricket-team/sri-lanka/5/schedule
    Filters and broadcasts ONLY Sri Lanka matches.
    """
    schedule_data = fetch_sri_lanka_schedule_matches()
    live_match = schedule_data.get("live")
    upcoming_match = schedule_data.get("upcoming")
    time_str = time.strftime("%H:%M")

    # 1. LIVE SRI LANKA MATCH IN PROGRESS
    if live_match:
        info = live_match.get("matchInfo", {})
        sc = live_match.get("matchScore", {})
        series = info.get("seriesName", "ජාත්‍යන්තර ක්‍රිකට් තරගාවලිය")
        desc = info.get("matchDesc", "සජීවී තරගය")
        desc_si = translate_match_desc_sinhala(desc)
        status = info.get("status", "")
        status_si = translate_status_sinhala(status)
        
        t1_en = info.get("team1", {}).get("teamName", "Team 1")
        t2_en = info.get("team2", {}).get("teamName", "Team 2")
        t1_si = translate_team_name(t1_en)
        t2_si = translate_team_name(t2_en)
        
        venue_info = info.get("venueInfo", {})
        venue_str = f"{venue_info.get('ground', '')}, {venue_info.get('city', '')}".strip(', ')
        
        short_score, score_speech = format_score_speech_from_json(info, sc)
        score_detail = f"{score_speech}." if score_speech else (f"ලකුණු: {short_score}." if short_score else "")

        if lang == "en":
            script = (
                f"Cricbuzz Live Cricket: {desc} between {t1_en} and {t2_en}. {status}. "
                f"{short_score}. Stay tuned to Radio Four D M!"
            )
            headline = f"🦁 Cricbuzz Live: {t1_en} vs {t2_en} ({desc})"
            summary = f"{status} | {short_score}"
        else:
            script = (
                f"Cricbuzz සජීවී ක්‍රිකට් තොරතුරු: {desc_si} ලෙස {t1_si} සහ {t2_si} අතර තරගය. {status_si}. "
                f"{score_detail} දිගටම රැඳී සිටින්න Radio Four D M සමඟින්!"
            )
            headline = f"🦁 Cricbuzz සජීවී ක්‍රිකට්: {t1_si} සහ {t2_si} ({desc_si})"
            summary = f"{status_si} | {short_score}"

        return {
            "has_live": True,
            "is_sl": True,
            "matches_count": 1,
            "headline": headline,
            "summary": summary,
            "script": script,
            "scores": short_score,
            "venue": venue_str,
            "source": CRICBUZZ_SL_SCHEDULE_URL,
            "time": time_str
        }

    # 2. NO ACTIVE LIVE SRI LANKA MATCH (Upcoming Schedule from Sri Lanka Page)
    if upcoming_match:
        info = upcoming_match.get("matchInfo", {})
        series = info.get("seriesName", "ක්‍රිකට් තරගාවලිය")
        desc = info.get("matchDesc", "තරගය")
        desc_si = translate_match_desc_sinhala(desc)
        status = info.get("status", "")
        status_si = translate_status_sinhala(status)
        
        t1_en = info.get("team1", {}).get("teamName", "Team 1")
        t2_en = info.get("team2", {}).get("teamName", "Team 2")
        t1_si = translate_team_name(t1_en)
        t2_si = translate_team_name(t2_en)
        
        venue_info = info.get("venueInfo", {})
        venue_str = f"{venue_info.get('ground', '')}, {venue_info.get('city', '')}".strip(', ')

        if lang == "en":
            script = (
                f"Cricbuzz Cricket Update: Sri Lanka's next match is {desc} against {t2_en}. {status}. "
                f"Stay tuned to Radio Four D M!"
            )
            headline = f"🦁 Cricbuzz Next Match: {t1_en} vs {t2_en} ({desc})"
            summary = f"No live match right now. Next: {t1_en} vs {t2_en} ({status})"
        else:
            script = (
                f"Cricbuzz ක්‍රිකට් තොරතුරු: ශ්‍රී ලංකාවේ ඊළඟ තරගය {desc_si} ලෙස {t1_si} සහ {t2_si} අතර. {status_si}. "
                f"දිගටම රැඳී සිටින්න Radio Four D M සමඟින්!"
            )
            headline = f"🦁 Cricbuzz ශ්‍රී ලංකා මීළඟ තරගය: {t1_si} සහ {t2_si}"
            summary = f"මේ මොහොතේ සජීවී තරග නොමැත. මීළඟ තරගය: {t1_si} සහ {t2_si} ({status_si})"

        return {
            "has_live": False,
            "is_sl": True,
            "matches_count": 0,
            "headline": headline,
            "summary": summary,
            "script": script,
            "venue": venue_str,
            "source": CRICBUZZ_SL_SCHEDULE_URL,
            "time": time_str
        }

    return {
        "has_live": False,
        "is_sl": True,
        "matches_count": 0,
        "headline": "ක්‍රියාකාරී සජීවී තරග නොමැත (No Active Sri Lanka Matches)",
        "summary": "Cricbuzz ශ්‍රී ලංකා දත්ත අනුව මේ මොහොතේ සජීවී තරග නොමැත. තරගයක් ආරම්භ වූ වහාම විකාශය කෙරේ.",
        "script": None,
        "source": CRICBUZZ_SL_SCHEDULE_URL,
        "time": time_str
    }

def build_cricket_broadcast_audio(lang: str = "si", preloaded_data: dict = None) -> str:
    """
    Synthesizes the Sri Lanka live cricket update audio using Gemini AI and prepends the sports fanfare chime.
    Returns path to the ready-to-air MP3 file.
    """
    data = preloaded_data or get_cricket_highlights_text(lang)
    if not data or not data.get("script"):
        print("[Cricket Engine] No cricket commentary text available to broadcast.")
        return None

    script = data["script"]
    voice_key = "si-female" if lang == "si" else "en-female"
    
    # Generate raw voice file
    raw_voice_file = generate_speech_file_sync(
        text=script,
        voice_key=voice_key,
        lang=lang,
        provider="gemini",
        filename_prefix="cricket_sl_cricbuzz",
        add_chime=False
    )
    if not raw_voice_file or not os.path.exists(raw_voice_file):
        raise RuntimeError("Failed to generate cricket speech audio")
        
    out_file = os.path.join(CACHE_DIR, f"cricbuzz_sl_broadcast_{lang}_{int(time.time())}.mp3")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    # Prepend sports intro jingle
    if os.path.exists(CRICKET_INTRO_FILE):
        try:
            cmd = [
                ffmpeg,
                '-i', CRICKET_INTRO_FILE,
                '-i', raw_voice_file,
                '-filter_complex',
                '[0:a]volume=0.9[jingle];[1:a]adelay=1400|1400,volume=1.55[voice];[jingle][voice]amix=inputs=2:duration=longest:dropout_transition=2[aout]',
                '-map', '[aout]',
                '-acodec', 'libmp3lame',
                '-b:a', '192k',
                '-y', out_file
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(out_file):
                return out_file
        except Exception as e:
            print(f"[Cricket] Jingle mix error: {e}")

    return raw_voice_file
