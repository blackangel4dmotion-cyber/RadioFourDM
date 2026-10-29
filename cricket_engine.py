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

CRICKET_INTRO_FILE = os.path.join(CACHE_DIR, "cricket_intro.mp3")
CRICBUZZ_LIVE_URL = "https://www.cricbuzz.com/cricket-match/live-scores"

def ensure_cricket_intro_jingle():
    """Generates an energetic radio sports chime for cricket updates."""
    if not os.path.exists(CRICKET_INTRO_FILE):
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            # Upbeat stadium sports fanfare (G4 -> B4 -> D5 -> G5)
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

def is_sri_lanka_match(title: str, text: str, raw_strings: list) -> bool:
    """Robustly checks whether a match features Sri Lanka (national men, women, A-team, under-19)."""
    t_low = title.lower()
    full_low = text.lower()
    sl_keywords = [
        "sri lanka", "srilanka", "sl-w", "sl w", "sl a", "sl-u19", "lanka", "ceylon", "lionesses"
    ]
    if any(k in t_low for k in sl_keywords) or any(k in full_low for k in sl_keywords):
        return True
    if re.search(r'\b(sl|slc|slw|sla)\b', t_low) or re.search(r'\b(sl|slc|slw|sla)\b', full_low):
        return True
    for s in raw_strings:
        s_clean = s.strip().upper()
        if s_clean in ["SL", "SL-W", "SLW", "SLC", "SL-A", "SRI LANKA"]:
            return True
    return False

def fetch_cricbuzz_live_matches() -> list:
    """
    Directly scrapes https://www.cricbuzz.com/cricket-match/live-scores.
    Extracts ONLY active, ongoing LIVE matches (filters out completed and preview/upcoming matches).
    Prioritizes matches featuring Sri Lanka first.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    try:
        req = urllib.request.Request(CRICBUZZ_LIVE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[Cricket Engine] Cricbuzz fetch error: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    seen_titles = set()

    for a in soup.find_all('a', href=lambda h: h and '/live-cricket-scores/' in h):
        title = a.get('title', '').strip()
        if not title or title.lower() in ['live score', 'scorecard', 'full commentary', 'news']:
            continue
        if ' - preview' in title.lower() or 'preview' in title.lower():
            continue

        p = a
        card_el = None
        for _ in range(6):
            if p.parent:
                p = p.parent
                text = ' | '.join(p.stripped_strings)
                if 'Scorecard' in text and ('Live Score' in text or 'Full Commentary' in text):
                    card_el = p
                    break

        if not card_el or title in seen_titles:
            continue
        seen_titles.add(title)

        card_strings = list(card_el.stripped_strings)
        filtered = [s for s in card_strings if s not in ['Live Score', 'Scorecard', 'Full Commentary', 'News', '|']]
        full_text = ' '.join(filtered)
        fl_lower = full_text.lower()

        # Strict exclusion of completed or upcoming matches
        is_completed = any(w in fl_lower for w in [
            'won by', 'match drawn', 'no result', 'match tied', 'abandoned', 'concluded'
        ])
        is_upcoming = any(w in fl_lower for w in [
            'match yet to begin', 'starts at', 'starts in', 'tomorrow', 'preview'
        ])

        if is_completed or is_upcoming:
            continue

        # Check for active live indicators
        is_live = False
        live_keywords = [
            'opt to bowl', 'opt to bat', 'lead by', 'trail by', 'need ', 
            'day ', 'session', 'stumps', 'tea break', 'lunch break', 
            'badlight', 'rain', 'innings break', 'delayed', 'live'
        ]
        if any(w in fl_lower for w in live_keywords) or re.search(r'\(\d+\.?\d*\)', full_text):
            is_live = True

        if is_live:
            venue = filtered[0] if filtered else ""
            status = filtered[-1] if len(filtered) > 1 else ""
            scores_parts = filtered[1:-1] if len(filtered) > 2 else []
            scores_str = " | ".join(scores_parts)
            is_sl = is_sri_lanka_match(title, full_text, filtered)

            matches.append({
                "title": title,
                "venue": venue,
                "status": status,
                "scores": scores_str,
                "raw_strings": filtered,
                "is_sl": is_sl
            })

    # Prioritize Sri Lanka national and league matches at top
    matches.sort(key=lambda m: (not m['is_sl'], m['title']))
    return matches

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
    clean = re.sub(r'[^a-zA-Z\s]', '', name).strip()
    return TEAM_NAMES_SINHALA.get(clean.upper(), clean)

def translate_match_title_sinhala(title: str) -> str:
    t = title
    for k, v in TEAM_NAMES_SINHALA.items():
        t = re.sub(r'\b' + re.escape(k) + r'\b', v, t, flags=re.I)
    t = re.sub(r'\s+vs\s+', ' සහ ', t, flags=re.I)
    t = re.sub(r'(\d+)(?:st|nd|rd|th)\s+Match', r'\1 වන තරගය', t, flags=re.I)
    t = re.sub(r'(\d+)(?:st|nd|rd|th)\s+Test', r'\1 වන ටෙස්ට් තරගය', t, flags=re.I)
    t = re.sub(r'(\d+)(?:st|nd|rd|th)\s+T20I?', r'\1 වන විස්සයි විස්ස තරගය', t, flags=re.I)
    t = re.sub(r'(\d+)(?:st|nd|rd|th)\s+ODI', r'\1 වන එක්දින තරගය', t, flags=re.I)
    return t

def translate_status_sinhala(status: str) -> str:
    st = status
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
    return st

def format_score_speech_sinhala(raw_strings: list) -> str:
    """Converts scorecard elements like ['England', 'ENG', '159-0 (23.1)', 'Sri Lanka', 'SL'] into natural Sinhala speech."""
    speech_parts = []
    i = 0
    while i < len(raw_strings):
        s = raw_strings[i].strip()
        m = re.match(r'^(\d+)-(\d+)(?:\s*\(([\d\.]+)\))?$', s)
        if m:
            runs, wkts, overs = m.groups()
            team_label = ''
            if i > 0:
                team_label = translate_team_name(raw_strings[i-1])
            if overs:
                if '.' in overs:
                    ov, b = overs.split('.')
                    ov_str = f"පන්දුවාර {ov}යි පන්දු {b}ක් අවසානයේ"
                else:
                    ov_str = f"පන්දුවාර {overs}ක් අවසානයේ"
            else:
                ov_str = ""
            
            w_str = "කිසිවෙකු නොදැවී" if wkts == "0" else f"කඩුලු {wkts}කට"
            part = f"{team_label} කණ්ඩායම {ov_str} {w_str} ලකුණු {runs}ක් ලබා සිටිනවා".strip()
            speech_parts.append(part)
        elif re.match(r'^\d+$', s) and i > 0 and len(s) >= 2:
            team_label = translate_team_name(raw_strings[i-1])
            speech_parts.append(f"{team_label} කණ්ඩායම සියලු දෙනා දැවී ලකුණු {s}ක් ලබා ගත්තා")
        i += 1
    return ". ".join(speech_parts)

def clean_score_for_speech(scores: str, status: str) -> str:
    """Formats scores and overs into smooth speech friendly phrasing."""
    clean = scores.replace("&", "සහ").replace("|", " ").strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean

def get_cricket_highlights_text(lang: str = "si") -> dict:
    """
    Fetches live matches from Cricbuzz.
    If no match is currently live, returns has_live=False.
    If live match is in progress, formats bilingual RJ commentary for Radio Four D M.
    """
    matches = fetch_cricbuzz_live_matches()
    time_str = time.strftime("%H:%M")

    if not matches:
        return {
            "has_live": False,
            "matches_count": 0,
            "matches": [],
            "headline": "ක්‍රියාකාරී සජීවී තරග නොමැත (No Active Live Matches)",
            "summary": "Cricbuzz සජීවී දත්ත අනුව මේ මොහොතේ ක්‍රියාත්මක සජීවී ක්‍රිකට් තරග නොමැත. සජීවී තරගයක් ආරම්භ වූ වහාම විකාශය කෙරේ.",
            "script": None,
            "time": time_str
        }

    # Pick top live match (prioritizing Sri Lanka if active)
    top = matches[0]
    title = top["title"]
    status = top["status"]
    scores = top["scores"]
    clean_scores = clean_score_for_speech(scores, status)

    if lang == "en":
        script = (
            f"Hello sports fans! Here is your latest live cricket scorecard from Cricbuzz on Radio Four D M. "
            f"Currently live in {title}: {status}. Current score: {scores}. "
            f"Keep listening to Radio Four D M for continuous live match action and the greatest hits!"
        )
        headline = f"🏏 Live on Cricbuzz: {title}"
        summary = f"{status}. Score: {scores}"
    else:
        # Full Natural Sinhala RJ presentation (All team names ENG -> එංගලන්තය, scores & states fully in Sinhala)
        title_si = translate_match_title_sinhala(title)
        status_si = translate_status_sinhala(status)
        score_speech_si = format_score_speech_sinhala(top.get("raw_strings", []))
        score_detail = f"{score_speech_si}." if score_speech_si else f"ලකුණු පුවරුව: {clean_scores}."

        match_phrase = f"{title_si} හි" if "තරගය" in title_si else f"{title_si} තරගයේ"
        if top.get("is_sl"):
            script = (
                f"ආයුබෝවන් සියලුම ක්‍රිකට් ලෝලී යාලුවනේ! මේ Cricbuzz වෙතින් Radio Four D M විශේෂ සජීවී ක්‍රිකට් තොරතුරු විකාශයයි. "
                f"අද දින අපේ ශ්‍රී ලංකා කණ්ඩායම සහභාගී වන {match_phrase} සජීවී තත්ත්වය මෙසේයි. "
                f"{status_si}. "
                f"{score_detail} "
                f"ශ්‍රී ලංකා සිංහයන්ට ජය පතමින් හොඳම ගීත සමඟින් දිගටම රැඳී සිටින්න ඔබේ Radio Four D M සමඟින්!"
            )
            headline = f"🦁 Cricbuzz සජීවී ක්‍රිකට්: {title_si} (ශ්‍රී ලංකාව)"
        else:
            script = (
                f"ආයුබෝවන් සියලුම ක්‍රිකට් ලෝලී යාලුවනේ! මේ Cricbuzz වෙතින් Radio Four D M සජීවී ක්‍රිකට් තොරතුරු විකාශයයි. "
                f"මේ වන විට සජීවීව පැවැත්වෙන {match_phrase} තත්ත්වය: {status_si}. "
                f"{score_detail} "
                f"හොඳම ගීත සමඟින් ක්‍රිකට් පිටියේ උණුසුම් තොරතුරු දැනගන්න, දිගටම රැඳී සිටින්න ඔබේ Radio Four D M සමඟින්!"
            )
            headline = f"🏏 Cricbuzz සජීවී ක්‍රිකට්: {title_si}"
        summary = f"{status_si} | {scores}"

    return {
        "has_live": True,
        "matches_count": len(matches),
        "matches": matches,
        "top_match": top,
        "lang": lang,
        "headline": headline,
        "summary": summary,
        "script": script,
        "source": "Cricbuzz Live Scores (https://www.cricbuzz.com/cricket-match/live-scores)",
        "time": time_str
    }

def build_cricket_broadcast_audio(lang: str = "si", preloaded_data: dict = None) -> str:
    """
    Synthesizes the live cricket update audio using Gemini AI and prepends the sports fanfare chime.
    Returns path to the finished ready-to-air MP3 file, or None if no live matches.
    """
    data = preloaded_data or get_cricket_highlights_text(lang)
    if not data.get("has_live") or not data.get("script"):
        print("[Cricket Engine] No live matches currently on Cricbuzz to broadcast.")
        return None

    script = data["script"]
    voice_key = "si-female" if lang == "si" else "en-female"
    
    # Generate raw voice file
    raw_voice_file = generate_speech_file_sync(
        text=script,
        voice_key=voice_key,
        lang=lang,
        provider="gemini",
        filename_prefix="cricket_cricbuzz",
        add_chime=False
    )
    if not raw_voice_file or not os.path.exists(raw_voice_file):
        raise RuntimeError("Failed to generate cricket speech audio")
        
    out_file = os.path.join(CACHE_DIR, f"cricbuzz_broadcast_{lang}_{int(time.time())}.mp3")
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

