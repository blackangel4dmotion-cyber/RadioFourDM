import sys
import time
import random
import threading
import concurrent.futures
import yt_dlp
from typing import List, Dict, Any, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# In-memory stream cache for repeat-less queries (2 hours TTL)
_STREAM_CACHE: Dict[str, Any] = {}

def is_unwanted_unofficial_cover(title: str, uploader: str = "") -> bool:
    """
    Detects and filters out amateur / unofficial cover songs, reactions, karaoke, and old classical tracks.
    Station plays ONLY modern hits (2018-2026), modern EDM remixes, and official studio masters.
    """
    t = (title or "").lower()
    u = (uploader or "").lower()

    # Reject obvious amateur cover, karaoke, and pitch-altered patterns
    bad_patterns = [
        "guitar cover", "piano cover", "drum cover", "acoustic cover",
        "karaoke", "instrumental cover", "reaction", "reacting", "vocal cover",
        "singing cover", "bedroom cover", "fan cover", "amateur cover",
        "female version cover", "male version cover", "unplugged cover",
        "bass cover", "ukulele cover", "dance cover", "tutorial",
        "how to play", "lyrics only", "chords", "shorts", "shorts cover",
        "minus one", "minus track", "instrumental", "backing track",
        "without vocal", "without vocals", "vocals removed", "vocal cut",
        "vocal removed", "acapella", "pitch shifted", "pitch shift",
        "nightcore", "speed up", "sped up", "slowed reverb", "slowed + reverb",
        "slowed down", "chipmunk", "8d audio", "high pitch", "low pitch",
        "key change", "karaoke version", "vocal isolated"
    ]
    for p in bad_patterns:
        if p in t:
            return True

    # Reject old classical songs / retro oldies (Station plays ONLY modern hits & modern remixes)
    old_classic_patterns = [
        "old song", "classic song", "golden oldies", "70s", "80s", "90s hits",
        "70's", "80's", "90's", "purana", "parana sindu", "calypso", "vintage", "retro live",
        "old hits", "nonstop oldies", "sarala gee", "classical", "gramophone",
        "bailaya", "old baila", "clarence wijewardena", "clarence", "h.r. jothipala",
        "hr jothipala", "jothipala", "milton mallawarachchi", "milton", "amaradeva",
        "pandith amaradeva", "victor rathnayake", "sunil santha", "c.t. fernando",
        "ct fernando", "edward jayakody", "t.m. jayaratne", "tm jayaratne",
        "sanath nandashiri", "neela wickramasinghe", "old cassette", "parana geetha",
        "cassette", "retro hits", "alborada", "parana", "old sinhala", "classic hits",
        "parana songs", "purana geetha", "walikada", "calypso nonstop", "baila nonstop",
        "oldies", "nostalgia", "vintage sinhala", "cassette eka", "sarala geetha",
        "parani", "parani gee", "baila party", "calypso band", "acoustic baila",
        "victor", "mohideen baig", "dharmadasa walpola", "latha walpola",
        "sujatha attanayake", "gunadasa kapuge", "kapuge", "malani bulathsinhala", "nanda malini"
    ]
    for p in old_classic_patterns:
        if p in t or p in u:
            return True

    # If the word 'cover' is present:
    if "cover" in t:
        is_official = any(w in t for w in [
            "official cover", "official music video", "official video", "coke red", "coke studio",
            "derana", "rootunes", "torana", "maathra", "live in concert", "coke"
        ])
        is_official_channel = any(w in u for w in [
            "vevo", "official", "records", "music", "studio", "t-series", "sony", "saregama", "zeemusic", "coke studio"
        ])
        if not is_official and not is_official_channel:
            return True

    return False

def check_channel_quality(cand: dict) -> Tuple[bool, str]:
    """
    Enforces Rule B:
    - YouTube Music Topic tracks (- Topic) are authentic studio masters.
    - Verified channels or channels with at least 50,000 subscribers (followers >= 50,000).
    - Rejects low-subscriber amateur channels (< 50,000 subscribers).
    """
    uploader = (cand.get('uploader') or '').lower()
    channel = (cand.get('channel') or '').lower()
    title = (cand.get('title') or '').lower()
    
    # 1. YouTube Music Topic tracks are always authentic master recordings
    if "- topic" in uploader or "- topic" in channel or " - topic" in title:
        return True, "YouTube Music Topic Master"
    
    # 2. Check follower / subscriber count
    followers = cand.get('channel_follower_count')
    if followers is None:
        followers = cand.get('subscriber_count')
        
    if followers is not None:
        if followers >= 50000:
            return True, f"Official Channel ({followers:,} subscribers >= 50k)"
        else:
            return False, f"Low-subscriber channel ({followers:,} < 50,000 subscribers)"
            
    # 3. If follower count not exposed directly in search result:
    is_verified = bool(cand.get('channel_is_verified'))
    views = cand.get('view_count') or 0
    if is_verified:
        return True, f"Verified YouTube Channel ({views:,} views)"
    if views >= 100000:
        return True, f"High-view official video ({views:,} views >= 100k)"
        
    return False, f"Unverified / Low quality ({views} views, no sub count)"

# Curated catalog of modern hits & official master tracks
CHART_CATALOGS = {
    "sinhala_regular": [
        {"title": "Manike Mage Hithe (මැණිකේ මගේ හිතේ)", "artist": "Yohani & Satheeshan", "query": "ytsearch1:Manike Mage Hithe Yohani Chamath Sangeeth Official"},
        {"title": "Haadu (හාදු)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Haadu Kanchana Anuradhi Official"},
        {"title": "Naadagam Geethaya (නාඩගම් ගීතය)", "artist": "Dinesh Gamage & Sanuka", "query": "ytsearch1:Naadagam Geethaya Dinesh Gamage Sanuka Official"},
        {"title": "Saragaye (සරාගයේ)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Saragaye Sanuka Wickramasinghe Official"},
        {"title": "Pandama (පන්දම)", "artist": "Dhanith Sri", "query": "ytsearch1:Pandama Dhanith Sri Official Music Video"},
        {"title": "Rawwath (රව්වත්)", "artist": "Yohani & Chamath Sangeeth", "query": "ytsearch1:Rawwath Yohani Official Music Video"},
        {"title": "Chanchala (චංචල)", "artist": "Dinesh Gamage", "query": "ytsearch1:Chanchala Dinesh Gamage Official"},
        {"title": "Kuweni (කුවේණි)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Kuweni Ridma Weerawardena Charitha Attalage"},
        {"title": "Rata Wata (රට වටා)", "artist": "Hana Shafa", "query": "ytsearch1:Rata Wata Hana Shafa Official"},
        {"title": "Mal Onchilla (මල් ඔන්චිල්ලා)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Mal Onchilla Kanchana Anuradhi Official"},
        {"title": "Jeewithe (ජීවිතේ)", "artist": "Dhanith Sri", "query": "ytsearch1:Jeewithe Dhanith Sri Official"},
        {"title": "Sandaganawa (සඳගනාව)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Sandaganawa Kanchana Anuradhi Official"},
        {"title": "Mathaka Manpeth (මතක මංපෙත්)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Mathaka Manpeth Sanuka Official"},
        {"title": "Dumbarata Peyana (දුම්බරට පායනා)", "artist": "Dinesh Gamage", "query": "ytsearch1:Dumbarata Peyana Dinesh Gamage Official"},
        {"title": "Thahanam (තහනම්)", "artist": "Supun Perera", "query": "ytsearch1:Thahanam Supun Perera Official"},
        {"title": "Moving On (යන්නට ගියා)", "artist": "Yohani", "query": "ytsearch1:Moving On Yohani Official Music Video"},
        {"title": "Adariye (ආදරියේ)", "artist": "Mihiran", "query": "ytsearch1:Adariye Mihiran Official Video"},
        {"title": "Neth Mane (නෙත් මානේ)", "artist": "Dinesh Gamage & Kaizer Kaiz", "query": "ytsearch1:Neth Mane Dinesh Gamage Kaizer Kaiz Official"},
        {"title": "Duka Daara (දුක දාරා)", "artist": "Mihiran & Dilki Uresha", "query": "ytsearch1:Duka Daara Mihiran Dilki Uresha Official"},
        {"title": "Nawathinna Ba (නවතින්න බෑ)", "artist": "Drill Team", "query": "ytsearch1:Nawathinna Ba Drill Team West Coast Official"},
        {"title": "Oba Magemai (ඔබ මගේමයි)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Oba Magemai Sanuka Official"},
        {"title": "Den Numba Koheda (දැන් නුඹ කොහෙද)", "artist": "Supun Perera", "query": "ytsearch1:Den Numba Koheda Supun Perera Official"},
        {"title": "Ayubowewa (ආයුබෝවේවා)", "artist": "Costa ft. Master D", "query": "ytsearch1:Ayubowewa Costa Master D Official"},
        {"title": "Ra Tharakawo (රෑ තාරකාවෝ)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Ra Tharakawo Bathiya Santhush Official"},
        {"title": "Nethu Saluna (නෙතු සැලුණා)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Nethu Saluna Bathiya Santhush BnS Official"},
        {"title": "Obe Premaye (ඔබේ ප්‍රේමයේ)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Obe Premaye Sanuka Official Video"},
        {"title": "Me Jeewithe (මේ ජීවිතේ)", "artist": "Sanuka & Dinesh", "query": "ytsearch1:Me Jeewithe Sanuka Dinesh Gamage Official"},
        {"title": "Hitha Wawannema Na (හිත වාවන්නෙම නෑ)", "artist": "Chamath Sangeeth", "query": "ytsearch1:Hitha Wawannema Na Chamath Sangeeth Official"},
        {"title": "Radhawani (රාධාවනී)", "artist": "Supun Perera", "query": "ytsearch1:Radhawani Supun Perera Official"},
        {"title": "Malbara Himidiriye (මල්බර හිමිදිරියේ)", "artist": "Bathiya & Santhush", "query": "ytsearch1:Malbara Himidiriye Bathiya Santhush Official"},
        {"title": "Sulagak Wee (සුළඟක් වී)", "artist": "Mihiran", "query": "ytsearch1:Sulagak Wee Mihiran Official"},
        {"title": "Gindara (ගින්දර)", "artist": "Dinesh Gamage", "query": "ytsearch1:Gindara Dinesh Gamage Official"},
        {"title": "Kella (කෙල්ල)", "artist": "Yohani & Harsha Withanage", "query": "ytsearch1:Kella Yohani Harsha Withanage Official"},
        {"title": "Nelum Vile (නෙළුම් විලේ)", "artist": "Daddy", "query": "ytsearch1:Nelum Vile Daddy Band Official"},
        {"title": "Giniyam Rae (ගිනියම් රෑ)", "artist": "Supun Perera & Kaizer Kaiz", "query": "ytsearch1:Giniyam Rae Supun Perera Kaizer Kaiz Official"},
        {"title": "Kawiyak Wee (කවියක් වී)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Kawiyak Wee Ridma Weerawardena Official"},
        {"title": "Dilisena Tharuwo (දිලිසෙන තරුවෝ)", "artist": "Costa ft. Master D", "query": "ytsearch1:Dilisena Tharuwo Costa Official"},
        {"title": "Kiri Kodu Hithata (කිරි කෝඩු හිතට)", "artist": "Bathiya Jayakody & Kanchana", "query": "ytsearch1:Kiri Kodu Hithata Bathiya Kanchana Official"},
        {"title": "Athin Mathin (ඇතින් මතින්)", "artist": "Dinesh Gamage", "query": "ytsearch1:Dinesh Gamage Athin Mathin Official"},
        {"title": "Hadakari Naari (හැඩකාරී නාරි)", "artist": "Dinesh Gamage & Kaizer Kaiz", "query": "ytsearch1:Hadakari Naari Dinesh gamage Kaizer kaiz Official"},
        {"title": "Awasan Satana (අවසන් සටන)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Sanuka Awasan Satana Official"},
        {"title": "Thawthisa (තවුතිසා)", "artist": "Smokio X ShanPutha", "query": "ytsearch1:Thawthisa Smokio ShanPutha Official"},
        {"title": "Nela Ganna Baha (නෙලා ගන්න බැහැ)", "artist": "Centigradz", "query": "ytsearch1:Nela Ganna Baha Centigradz Official"},
        {"title": "Rusiri (රුසිරී)", "artist": "Centigradz", "query": "ytsearch1:Rusiri Centigradz Official Video"},
        {"title": "Kurunegala (කුරුණෑගල)", "artist": "Costa", "query": "ytsearch1:Costa Kurunegala Official Music Video"},
        {"title": "Api Sanasille (අපි සැනසිල්ලේ)", "artist": "Kaizer Kaiz", "query": "ytsearch1:Api Sanasille Kaizer Kaiz Official"},
        {"title": "Sanda Tharakawa (සඳ තාරකාව)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Sanda Tharakawa Bathiya and Santhush Official"},
        {"title": "Yanna Rata Wate (යන්න රට වටේ)", "artist": "Daddy", "query": "ytsearch1:Yanna Rata Wate Daddy Band Official"},
        {"title": "Massina (මස්සිනා)", "artist": "Daddy Band", "query": "ytsearch1:Massina Daddy Band Official"},
        {"title": "Rahasak (රහසක්)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Rahasak Kanchana Anuradhi Official"},
        {"title": "Nidi Nena (නිදි නේනා)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Nidi Nena Sanuka Official"},
        {"title": "Soya (සොයා)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Soya Ridma Weerawardena Charitha Attalage Official"},
        {"title": "Hada Wela (හඬ වෙලා)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Hada Wela Bathiya and Santhush Official"},
        {"title": "Kandula (කඳුල)", "artist": "Centigradz", "query": "ytsearch1:Kandula Centigradz Official"},
        {"title": "Galana Ganga (ගලන ගංගා)", "artist": "Charitha Attalage & Ridma", "query": "ytsearch1:Galana Ganga Charitha Attalage Ridma Weerawardena Official"},
        {"title": "Sanda Eliye (සඳ එළියේ)", "artist": "Dhanith Sri", "query": "ytsearch1:Sanda Eliye Dhanith Sri Official Music Video"},
        {"title": "Tharu Atharin (තරු අතරින්)", "artist": "Romesh Sugathapala", "query": "ytsearch1:Tharu Atharin Romesh Sugathapala Official"},
        {"title": "Mage Hitha Thawamath (මගේ හිත තවමත්)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Mage Hitha Thawamath Sanuka Official"},
        {"title": "Bambara Patikki (බඹර පැටිකී)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Bambara Patikki Bathiya Santhush Official"},
        {"title": "Mage Pem Purawatha (මගේ පෙම් පුරාවත)", "artist": "Ravi Jay", "query": "ytsearch1:Mage Pem Purawatha Ravi Jay Official"},
        {"title": "Sithuwili (සිතිවිලි)", "artist": "Centigradz", "query": "ytsearch1:Sithuwili Centigradz Official"},
        {"title": "Piyambanna (පියඹන්න)", "artist": "Daddy Band", "query": "ytsearch1:Piyambanna Daddy Band Official Video"},
        {"title": "Adare Hithenawa (ආදරේ හිතෙනවා)", "artist": "Romesh Sugathapala", "query": "ytsearch1:Adare Hithenawa Romesh Sugathapala Official"},
        {"title": "Kanya (කන්‍යා)", "artist": "Smokio", "query": "ytsearch1:Kanya Smokio Official Music Video"},
        {"title": "Mage Wenawada (මගේ වෙනවද)", "artist": "Dinesh Gamage", "query": "ytsearch1:Mage Wenawada Dinesh Gamage Official"},
        {"title": "Sandarenu (සඳරේණු)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Sandarenu Sanuka Official Music Video"},
        {"title": "Ahasa Usata (අහස උසට)", "artist": "Dhanith Sri", "query": "ytsearch1:Ahasa Usata Dhanith Sri Official"},
        {"title": "Heenayakda Me (හීනයක්ද මේ)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Heenayakda Me Kanchana Anuradhi Official"},
        {"title": "Sanda Mithuri (සඳ මිතුරී)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Sanda Mithuri Ridma Weerawardena Official"},
        {"title": "Dawasak Ewi (දවසක් ඒවි)", "artist": "Piyath Rajapakse", "query": "ytsearch1:Dawasak Ewi Piyath Rajapakse Official Music Video"},
        {"title": "Kawda Bole (කවුද බොලේ)", "artist": "Dinesh Gamage", "query": "ytsearch1:Kawda Bole Dinesh Gamage Official Video"},
        {"title": "Aalawanthi (ආලාවන්තී)", "artist": "Mihiran & Dilki Uresha", "query": "ytsearch1:Aalawanthi Mihiran Dilki Uresha Official"},
        {"title": "As Thewena (ඇස් තෙමෙනා)", "artist": "Supun Perera", "query": "ytsearch1:As Thewena Supun Perera Official"},
        {"title": "Kiyanna Bari Tharam (කියන්න බැරි තරම්)", "artist": "Piyath Rajapakse", "query": "ytsearch1:Kiyanna Bari Tharam Piyath Rajapakse Official"},
        {"title": "Pem Kawak (පෙම් කවක්)", "artist": "Piyath Rajapakse", "query": "ytsearch1:Pem Kawak Piyath Rajapakse Official Music Video"},
        {"title": "Dedunna Sedi (දේදුන්න සෑදී)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Dedunna Sedi Bathiya and Santhush Official"},
        {"title": "Oba Nisa (ඔබ නිසා)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Oba Nisa Bathiya and Santhush BnS Official"},
        {"title": "Sonduru Athithaye (සොඳුරු අතීතයේ)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Sonduru Athithaye Bathiya and Santhush Official"},
        {"title": "Chandramandale (චන්ද්‍රමණ්ඩලේ)", "artist": "Daddy Band", "query": "ytsearch1:Chandramandale Daddy Band Official"},
        {"title": "Baila Gamana (බයිලා ගමන)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Baila Gamana Bathiya and Santhush Official"},
        {"title": "Pethikada (පෙතිකඩ)", "artist": "Charitha Attalage & Ridma", "query": "ytsearch1:Pethikada Charitha Attalage Ridma Weerawardena Official"},
        {"title": "Naada (නාද)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Naada Ridma Weerawardena Official"},
        {"title": "Me Nagaraya (මේ නගරය)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Me Nagaraya Sanuka Wickramasinghe Official"},
        {"title": "Gahani (ගැහැනී)", "artist": "Dhanith Sri", "query": "ytsearch1:Gahani Dhanith Sri Official Music Video"},
        {"title": "Sadakalika Nowu (සදාකාලික නොවූ)", "artist": "Dhanith Sri", "query": "ytsearch1:Sadakalika Nowu Dhanith Sri Official"},
        {"title": "Ra Ahase (රෑ අහසේ)", "artist": "Centigradz", "query": "ytsearch1:Ra Ahase Centigradz Official"},
        {"title": "Mage Pana (මගේ පණ)", "artist": "Romesh Sugathapala", "query": "ytsearch1:Mage Pana Romesh Sugathapala Official"},
        {"title": "Maha Sayura (මහ සයුර)", "artist": "Ravi Jay ft. Charitha Attalage", "query": "ytsearch1:Maha Sayura Ravi Jay Charitha Attalage Official"},
        {"title": "Kandulu Binduwak (කඳුළු බිඳුවක්)", "artist": "Centigradz", "query": "ytsearch1:Kandulu Binduwak Centigradz Official"},
        {"title": "Ninda Noyena Hade (නින්ද නොයෙනා හදේ)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Ninda Noyena Hade Sanuka Official"},
        {"title": "Mal Kakulak (මල් කැකුළක්)", "artist": "Daddy Band", "query": "ytsearch1:Mal Kakulak Daddy Band Official"},
        {"title": "Yali Hamuwemu (යලි හමුවෙමු)", "artist": "Bathiya & Santhush", "query": "ytsearch1:Yali Hamuwemu Bathiya Santhush Official"},
        {"title": "Ashawo (ආශාවෝ)", "artist": "Yohani", "query": "ytsearch1:Ashawo Yohani Chamath Sangeeth Official"},
        {"title": "Kelle (කෙල්ලේ)", "artist": "Costa & Master D", "query": "ytsearch1:Kelle Costa Master D Official Video"},
        {"title": "Sulanga Numba (සුළඟ නුඹ)", "artist": "Dhanith Sri", "query": "ytsearch1:Sulanga Numba Dhanith Sri Official"},
        {"title": "Adare Pawasa (ආදරේ පිපාසා)", "artist": "Piyath Rajapakse", "query": "ytsearch1:Adare Pawasa Piyath Rajapakse Official"},
        {"title": "Numba Ha (නුඹ හා)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Numba Ha Sanuka Wickramasinghe Official"}
    ],
    "sinhala_remix": [
        {"title": "Thawthisa (Trap Remix)", "artist": "Smokio DJ Remix", "query": "ytsearch1:Thawthisa Trap DJ Remix"},
        {"title": "Saragaye (Club Remix)", "artist": "Sanuka Wickramasinghe Remix", "query": "ytsearch1:Saragaye Remix Sanuka"},
        {"title": "Manike Mage Hithe (DJ Party Remix)", "artist": "Yohani DJ Remix", "query": "ytsearch1:Manike Mage Hithe DJ Remix Chamath"},
        {"title": "Naadagam Geethaya (Club Remix)", "artist": "Dinesh Gamage Remix", "query": "ytsearch1:Naadagam Geethaya Remix Dinesh Gamage"},
        {"title": "Kuweni (Club Remix)", "artist": "Ridma Weerawardena Remix", "query": "ytsearch1:Kuweni Remix Charitha Attalage"},
        {"title": "Ra Tharakawo (Nonstop DJ Remix)", "artist": "Bathiya and Santhush Remix", "query": "ytsearch1:Ra Tharakawo DJ Remix Bathiya"},
        {"title": "Chanchala (EDM Remix)", "artist": "Dinesh Gamage Remix", "query": "ytsearch1:Chanchala Remix Dinesh Gamage"},
        {"title": "Hadakari Naari (Club Remix)", "artist": "Dinesh Gamage Remix", "query": "ytsearch1:Hadakari Naari DJ Remix"},
        {"title": "Ayubowewa (EDM Club Mix)", "artist": "Costa Remix", "query": "ytsearch1:Ayubowewa EDM DJ Remix"},
        {"title": "Nelum Vile (Rock Remix)", "artist": "Daddy Remix", "query": "ytsearch1:Nelum Vile Daddy Remix"},
        {"title": "Rawwath (Club Remix)", "artist": "Yohani Remix", "query": "ytsearch1:Rawwath Remix Yohani"},
        {"title": "Dilisena Tharuwo (Trap Remix)", "artist": "Costa Remix", "query": "ytsearch1:Dilisena Tharuwo Remix Costa"},
        {"title": "Pandama (Bass Boosted Remix)", "artist": "Dhanith Sri Remix", "query": "ytsearch1:Pandama Dhanith Sri DJ Remix"},
        {"title": "Massina (DJ Party Remix)", "artist": "Daddy Band Remix", "query": "ytsearch1:Daddy Massina DJ Remix"},
        {"title": "Haadu (Deep House Remix)", "artist": "Kanchana Anuradhi Remix", "query": "ytsearch1:Haadu Deep House Remix Kanchana"},
        {"title": "Dumbarata Peyana (Club Remix)", "artist": "Dinesh Gamage Remix", "query": "ytsearch1:Dumbarata Peyana DJ Remix"},
        {"title": "Nawathinna Ba (Trap Remix)", "artist": "Drill Team Remix", "query": "ytsearch1:Nawathinna Ba Trap Remix"},
        {"title": "Nela Ganna Baha (Remix)", "artist": "Centigradz Remix", "query": "ytsearch1:Nela Ganna Baha Remix Centigradz"},
        {"title": "Galana Ganga (Club Remix)", "artist": "Charitha Attalage Remix", "query": "ytsearch1:Galana Ganga Remix Charitha Attalage"},
        {"title": "Sanda Eliye (EDM Mix)", "artist": "Dhanith Sri Remix", "query": "ytsearch1:Sanda Eliye Remix Dhanith Sri"},
        {"title": "Bambara Patikki (Party Remix)", "artist": "Bathiya Santhush Remix", "query": "ytsearch1:Bambara Patikki DJ Remix Bathiya"},
        {"title": "Awasan Satana (Club Remix)", "artist": "Sanuka Remix", "query": "ytsearch1:Sanuka Awasan Satana Remix"},
        {"title": "Soya (DJ Remix)", "artist": "Ridma Weerawardena Remix", "query": "ytsearch1:Soya Ridma Weerawardena Remix"},
        {"title": "Kurunegala (Trap Remix)", "artist": "Costa Remix", "query": "ytsearch1:Costa Kurunegala Remix Official"},
        {"title": "Aalawanthi (Club Remix)", "artist": "Mihiran Remix", "query": "ytsearch1:Aalawanthi Remix Mihiran Dilki"},
        {"title": "Giniyam Rae (EDM Club Mix)", "artist": "Supun Perera Remix", "query": "ytsearch1:Giniyam Rae EDM Remix Supun"},
        {"title": "Thahanam (Club Mix)", "artist": "Supun Perera Remix", "query": "ytsearch1:Thahanam Club Remix Supun Perera"},
        {"title": "Dawasak Ewi (Bass Boosted Mix)", "artist": "Piyath Rajapakse Remix", "query": "ytsearch1:Dawasak Ewi Remix Piyath"},
        {"title": "Adariye (Party Remix)", "artist": "Mihiran Remix", "query": "ytsearch1:Adariye Remix Mihiran Official"},
        {"title": "Kandula (Club Mix)", "artist": "Centigradz Remix", "query": "ytsearch1:Kandula Centigradz Club Remix"},
        {"title": "Baila Gamana (EDM Mix)", "artist": "BnS Remix", "query": "ytsearch1:Baila Gamana Remix Bathiya Santhush"},
        {"title": "Sandaganawa (EDM Remix)", "artist": "Kanchana Anuradhi Remix", "query": "ytsearch1:Sandaganawa Remix Kanchana"},
        {"title": "Mal Onchilla (Club Mix)", "artist": "Kanchana Anuradhi Remix", "query": "ytsearch1:Mal Onchilla Remix Kanchana"},
        {"title": "Kella (Bass Remix)", "artist": "Yohani Remix", "query": "ytsearch1:Kella Yohani Remix Official"},
        {"title": "Ashawo (Club Remix)", "artist": "Yohani Remix", "query": "ytsearch1:Ashawo Remix Yohani"}
    ],
    "hindi": [
        {"title": "Kesariya (Brahmāstra)", "artist": "Arijit Singh", "query": "ytsearch1:Kesariya Brahmastra Arijit Singh Ranbir Kapoor"},
        {"title": "Raataan Lambiyan (Shershaah)", "artist": "Jubin Nautiyal & Asees Kaur", "query": "ytsearch1:Raataan Lambiyan Shershaah Jubin Nautiyal"},
        {"title": "Tum Hi Ho (Aashiqui 2)", "artist": "Arijit Singh", "query": "ytsearch1:Tum Hi Ho Aashiqui 2 Arijit Singh"},
        {"title": "Chaleya (Jawan)", "artist": "Arijit Singh & Shilpa Rao", "query": "ytsearch1:Chaleya Jawan Arijit Singh Shah Rukh Khan"},
        {"title": "Apna Bana Le (Bhediya)", "artist": "Arijit Singh & Sachin-Jigar", "query": "ytsearch1:Apna Bana Le Bhediya Arijit Singh"},
        {"title": "Heeriye", "artist": "Jasleen Royal & Arijit Singh", "query": "ytsearch1:Heeriye Jasleen Royal Arijit Singh Dulquer"},
        {"title": "Kal Ho Naa Ho", "artist": "Sonu Nigam", "query": "ytsearch1:Kal Ho Naa Ho Title Track Sonu Nigam Shah Rukh Khan"},
        {"title": "Shayad (Love Aaj Kal)", "artist": "Arijit Singh", "query": "ytsearch1:Shayad Love Aaj Kal Arijit Singh Kartik"},
        {"title": "Tere Vaste (Zara Hatke)", "artist": "Varun Jain & Sachin-Jigar", "query": "ytsearch1:Tere Vaste Zara Hatke Zara Bachke"},
        {"title": "Agar Tum Saath Ho (Tamasha)", "artist": "Arijit Singh & Alka Yagnik", "query": "ytsearch1:Agar Tum Saath Ho Tamasha Arijit Alka"},
        {"title": "Pehle Bhi Main (Animal)", "artist": "Vishal Mishra", "query": "ytsearch1:Pehle Bhi Main Animal Vishal Mishra Ranbir"},
        {"title": "Satranga (Animal)", "artist": "Arijit Singh", "query": "ytsearch1:Satranga Animal Arijit Singh Ranbir"},
        {"title": "O Maahi (Dunki)", "artist": "Arijit Singh", "query": "ytsearch1:O Maahi Dunki Arijit Singh Shah Rukh Khan"},
        {"title": "Ghungroo (War)", "artist": "Arijit Singh & Shilpa Rao", "query": "ytsearch1:Ghungroo Song War Hrithik Roshan Arijit"},
        {"title": "Hawayein (Jab Harry Met Sejal)", "artist": "Arijit Singh", "query": "ytsearch1:Hawayein Jab Harry Met Sejal Arijit Singh"},
        {"title": "Gerua (Dilwale)", "artist": "Arijit Singh & Antara Mitra", "query": "ytsearch1:Gerua Dilwale Shah Rukh Khan Kajol Arijit"},
        {"title": "Channa Mereya (ADHM)", "artist": "Arijit Singh", "query": "ytsearch1:Channa Mereya Ae Dil Hai Mushkil Arijit Singh"},
        {"title": "Dil Diyan Gallan (TZH)", "artist": "Atif Aslam", "query": "ytsearch1:Dil Diyan Gallan Tiger Zinda Hai Atif Aslam"},
        {"title": "Roke Na Ruke Naina", "artist": "Arijit Singh", "query": "ytsearch1:Roke Na Ruke Naina Badrinath Ki Dulhania Arijit"},
        {"title": "Teri Mitti (Kesari)", "artist": "B Praak", "query": "ytsearch1:Teri Mitti Kesari Akshay Kumar B Praak"},
        {"title": "Lutt Putt Gaya (Dunki)", "artist": "Arijit Singh", "query": "ytsearch1:Lutt Putt Gaya Dunki Arijit Singh"},
        {"title": "Rasiya (Brahmāstra)", "artist": "Pritam & Shreya Ghoshal", "query": "ytsearch1:Rasiya Brahmastra Pritam Shreya Ghoshal"},
        {"title": "Manike (Thank God)", "artist": "Yohani & Jubin Nautiyal", "query": "ytsearch1:Manike Thank God Yohani Jubin Nautiyal Official"},
        {"title": "Besharam Rang (Pathaan)", "artist": "Vishal-Shekhar & Shilpa Rao", "query": "ytsearch1:Besharam Rang Pathaan Deepika Padukone"},
        {"title": "Jhoome Jo Pathaan", "artist": "Arijit Singh & Sukriti Kakar", "query": "ytsearch1:Jhoome Jo Pathaan Shah Rukh Khan Deepika"}
    ],
    "english": [
        {"title": "Shape of You", "artist": "Ed Sheeran", "query": "ytsearch1:Ed Sheeran Shape of You Official Video"},
        {"title": "Blinding Lights", "artist": "The Weeknd", "query": "ytsearch1:The Weeknd Blinding Lights Official Video"},
        {"title": "Levitating", "artist": "Dua Lipa", "query": "ytsearch1:Dua Lipa Levitating Official Music Video"},
        {"title": "Believer", "artist": "Imagine Dragons", "query": "ytsearch1:Imagine Dragons Believer Official Video"},
        {"title": "As It Was", "artist": "Harry Styles", "query": "ytsearch1:Harry Styles As It Was Official Video"},
        {"title": "Hymn for the Weekend", "artist": "Coldplay", "query": "ytsearch1:Coldplay Hymn for the Weekend Official Video"},
        {"title": "Memories", "artist": "Maroon 5", "query": "ytsearch1:Maroon 5 Memories Official Video"},
        {"title": "Stay", "artist": "The Kid LAROI & Justin Bieber", "query": "ytsearch1:The Kid LAROI Justin Bieber Stay Official Video"},
        {"title": "Flowers", "artist": "Miley Cyrus", "query": "ytsearch1:Miley Cyrus Flowers Official Video"},
        {"title": "Counting Stars", "artist": "OneRepublic", "query": "ytsearch1:OneRepublic Counting Stars Official Music Video"},
        {"title": "Bad Habits", "artist": "Ed Sheeran", "query": "ytsearch1:Ed Sheeran Bad Habits Official Video"},
        {"title": "Perfect", "artist": "Ed Sheeran", "query": "ytsearch1:Ed Sheeran Perfect Official Music Video"},
        {"title": "Save Your Tears", "artist": "The Weeknd", "query": "ytsearch1:The Weeknd Save Your Tears Official Video"},
        {"title": "Someone You Loved", "artist": "Lewis Capaldi", "query": "ytsearch1:Lewis Capaldi Someone You Loved Official Video"},
        {"title": "Starboy", "artist": "The Weeknd ft. Daft Punk", "query": "ytsearch1:The Weeknd Starboy Official Music Video"},
        {"title": "Closer", "artist": "The Chainsmokers ft. Halsey", "query": "ytsearch1:The Chainsmokers Closer Official Video"},
        {"title": "Attention", "artist": "Charlie Puth", "query": "ytsearch1:Charlie Puth Attention Official Video"},
        {"title": "Watermelon Sugar", "artist": "Harry Styles", "query": "ytsearch1:Harry Styles Watermelon Sugar Official Video"},
        {"title": "Viva La Vida", "artist": "Coldplay", "query": "ytsearch1:Coldplay Viva La Vida Official Video"},
        {"title": "Don't Start Now", "artist": "Dua Lipa", "query": "ytsearch1:Dua Lipa Don't Start Now Official Video"},
        {"title": "Senorita", "artist": "Shawn Mendes & Camila Cabello", "query": "ytsearch1:Shawn Mendes Camila Cabello Senorita"},
        {"title": "Roar", "artist": "Katy Perry", "query": "ytsearch1:Katy Perry Roar Official Music Video"},
        {"title": "Heat Waves", "artist": "Glass Animals", "query": "ytsearch1:Glass Animals Heat Waves Official Video"},
        {"title": "Sunflower", "artist": "Post Malone & Swae Lee", "query": "ytsearch1:Post Malone Swae Lee Sunflower Official"},
        {"title": "Dance Monkey", "artist": "Tones and I", "query": "ytsearch1:Tones and I Dance Monkey Official Music Video"},
        {"title": "Cruel Summer", "artist": "Taylor Swift", "query": "ytsearch1:Taylor Swift Cruel Summer Official Audio"},
        {"title": "Anti-Hero", "artist": "Taylor Swift", "query": "ytsearch1:Taylor Swift Anti-Hero Official Music Video"},
        {"title": "Uptown Funk", "artist": "Mark Ronson ft. Bruno Mars", "query": "ytsearch1:Mark Ronson Bruno Mars Uptown Funk Official Video"},
        {"title": "Cheap Thrills", "artist": "Sia", "query": "ytsearch1:Sia Cheap Thrills Official Music Video"},
        {"title": "Wake Me Up", "artist": "Avicii", "query": "ytsearch1:Avicii Wake Me Up Official Video"}
    ]
}

# Dynamic YouTube queries for endless variety when catalog tracks are in 24-hr lockout
DYNAMIC_SEARCH_QUERIES = {
    "sinhala_regular": [
        "ytsearch12:sinhala latest official music video 2024 2025",
        "ytsearch12:sinhala new hit songs official video",
        "ytsearch12:popular sinhala songs official audio",
        "ytsearch12:trending sinhala official music video",
        "ytsearch12:sinhala pop hits official video",
        "ytsearch12:sinhala hit songs official studio video"
    ],
    "sinhala_remix": [
        "ytsearch12:sinhala dj remix official club mix",
        "ytsearch12:sinhala party remix dj official",
        "ytsearch12:sinhala edm bass boosted remix official",
        "ytsearch12:sinhala mashup remix official",
        "ytsearch12:sinhala dance mix dj official"
    ],
    "english": [
        "ytsearch12:top billboard hits official music video",
        "ytsearch12:popular english pop songs official video",
        "ytsearch12:global top hits official music video",
        "ytsearch12:english dance pop hits official video"
    ],
    "hindi": [
        "ytsearch12:bollywood latest romantic hits official video",
        "ytsearch12:hindi hit songs official music video t-series",
        "ytsearch12:bollywood top chartbusters official video",
        "ytsearch12:hindi party dance hits official video"
    ]
}

def get_target_category_for_step(step: int) -> Tuple[str, str]:
    """
    Returns (catalog_key, display_label) for any step in the 22-song rotation cycle:
    - Steps 0..9: 10 Sinhala songs (steps 3, 7 are Remixes; others are Regular)
    - Step 10: 1 English hit
    - Steps 11..20: 10 Sinhala songs (steps 14, 18 are Remixes; others are Regular)
    - Step 21: 1 Hindi hit
    """
    s = step % 22
    if s in (3, 7, 14, 18):
        return "sinhala_remix", "Sinhala Remix"
    elif s == 10:
        return "english", "English"
    elif s == 21:
        return "hindi", "Hindi"
    else:
        return "sinhala_regular", "Sinhala"

class AutoDJEngine:
    def __init__(self, station_engine):
        self.station_engine = station_engine
        self.enabled = True
        self.rotation_step = 0 # 0..21 (22-song rotation cycle)
        self.dynamic_query_idx = {k: 0 for k in DYNAMIC_SEARCH_QUERIES}
        self.is_running = False
        self.lock = threading.Lock()
        self.worker: Optional[threading.Thread] = None

    def start(self):
        """Starts background worker thread once."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.worker = threading.Thread(target=self._autodj_loop, daemon=True)
            self.worker.start()
            print("[AutoDJ] 24/7 Auto-DJ Engine started with strict 22-step Rotation Sequence:")
            print("[AutoDJ] Sequence: 10 Sinhala (incl. 2 remixes) -> 1 English -> 10 Sinhala (incl. 2 remixes) -> 1 Hindi.")

    def stop(self):
        with self.lock:
            self.is_running = False

    def set_enabled(self, state: bool):
        with self.lock:
            self.enabled = state
            print(f"[AutoDJ] Auto-DJ set to: {'ON' if state else 'OFF'}")

    def is_enabled(self) -> bool:
        with self.lock:
            return self.enabled

    def _resolve_candidate_stream(self, cand_query_or_url: str, cat_name: str, fallback_title: str = "", fallback_artist: str = "") -> Optional[Dict[str, Any]]:
        """
        Resolves stream URL with yt-dlp and enforces:
        1. Duplicate check (< 24 hours lockout).
        2. Channel quality (>= 50,000 subscribers or Topic track).
        3. Anti-karaoke & anti-classic check.
        4. Duration limit (45s to 360s cap).
        """
        query = cand_query_or_url
        now = time.time()
        entry = None

        if query in _STREAM_CACHE and (now - _STREAM_CACHE[query][1]) < 7200:
            cached_entry = _STREAM_CACHE[query][0]
            if cached_entry and cached_entry.get('url'):
                entry = cached_entry

        if not entry or not entry.get('url'):
            yt_query = query
            if yt_query.startswith("ytsearch1:"):
                yt_query = "ytsearch2:" + yt_query[len("ytsearch1:"):]
            elif not yt_query.startswith("ytsearch") and not yt_query.startswith("http"):
                yt_query = f"ytsearch2:{yt_query} Official"

            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'format_sort': ['abr', 'quality'],
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
                'source_address': '0.0.0.0',
                'socket_timeout': 6,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios', 'mweb']
                    }
                }
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(yt_query, download=False)
                    raw_cands = info.get('entries') or ([info] if info and info.get('url') else [])
                    topic_candidates = []
                    valid_candidates = []

                    for c in raw_cands:
                        if not c or not c.get('url'):
                            continue
                        c_title = c.get('title', fallback_title)
                        c_uploader = c.get('uploader', fallback_artist)
                        c_channel = c.get('channel', '')
                        c_url = c.get('webpage_url', '')

                        # Check 1: Anti-karaoke / anti-classic
                        if is_unwanted_unofficial_cover(c_title, c_uploader) or is_unwanted_unofficial_cover(c_title, c_channel):
                            continue

                        # Check 2: 24-Hour Deduplication
                        if self.station_engine.is_duplicate(c_title, c_url):
                            continue

                        # Check 3: Minimum 50k subscriber rule
                        passed_quality, reason = check_channel_quality(c)
                        if not passed_quality:
                            continue

                        is_topic = "- topic" in (c_uploader or "").lower() or "- topic" in (c_channel or "").lower()
                        if is_topic:
                            topic_candidates.append(c)
                        else:
                            valid_candidates.append(c)

                    if topic_candidates:
                        entry = topic_candidates[0]
                    elif valid_candidates:
                        entry = valid_candidates[0]
            except Exception as e:
                print(f"[AutoDJ] Extraction error for '{query}': {e}")
                return None

        if not entry or not entry.get('url'):
            return None

        # Post-extraction verification
        final_title = entry.get('title', fallback_title)
        final_uploader = entry.get('uploader', fallback_artist)
        final_url = entry.get('webpage_url', '')

        if is_unwanted_unofficial_cover(final_title, final_uploader):
            return None

        if self.station_engine.is_duplicate(final_title, final_url):
            return None

        raw_dur = entry.get("duration", 0)
        if raw_dur and raw_dur < 45:
            return None

        capped_dur = min(raw_dur, 360) if raw_dur else 360

        _STREAM_CACHE[query] = (entry, now)

        formatted_title = f"[{cat_name}] {final_title}"
        track = {
            "id": f"autodj_{int(time.time() * 1000)}_{random.randint(100, 999)}",
            "type": "youtube",
            "title": formatted_title,
            "duration": capped_dur,
            "duration_str": time.strftime('%M:%S', time.gmtime(capped_dur)),
            "thumbnail": entry.get("thumbnail", ""),
            "uploader": final_uploader,
            "stream_url": entry.get('url'),
            "original_url": final_url,
            "http_headers": entry.get("http_headers", {}),
            "added_at": time.strftime("%H:%M:%S"),
            "resolved_at": time.time(),
            "category": cat_name
        }
        return track

    def _fetch_from_dynamic_youtube_search(self, cat_key: str, cat_name: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically searches YouTube for the required category using rotating queries.
        Guarantees that when catalog items have all been played within 24h, fresh tracks are streamed.
        """
        queries = DYNAMIC_SEARCH_QUERIES.get(cat_key, [])
        if not queries:
            return None

        with self.lock:
            q_idx = self.dynamic_query_idx[cat_key] % len(queries)
            search_query = queries[q_idx]
            self.dynamic_query_idx[cat_key] += 1

        print(f"[AutoDJ Dynamic Search] Querying fresh {cat_name} tracks: '{search_query}'")

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'format_sort': ['abr', 'quality'],
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'socket_timeout': 7,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries') or ([info] if info and info.get('url') else [])

                for cand in entries:
                    if not cand or not cand.get('url'):
                        continue
                    cand_title = cand.get('title', '')
                    cand_uploader = cand.get('uploader', '')
                    cand_channel = cand.get('channel', '')
                    cand_url = cand.get('webpage_url', '')

                    # 1. Anti-karaoke / anti-classic
                    if is_unwanted_unofficial_cover(cand_title, cand_uploader) or is_unwanted_unofficial_cover(cand_title, cand_channel):
                        continue

                    # 2. 24-Hour Deduplication
                    if self.station_engine.is_duplicate(cand_title, cand_url):
                        continue

                    # 3. 50k subscriber rule
                    passed_quality, reason = check_channel_quality(cand)
                    if not passed_quality:
                        continue

                    raw_dur = cand.get("duration", 0)
                    if raw_dur and raw_dur < 45:
                        continue
                    capped_dur = min(raw_dur, 360) if raw_dur else 360

                    formatted_title = f"[{cat_name}] {cand_title}"
                    track = {
                        "id": f"autodj_{int(time.time() * 1000)}_{random.randint(100, 999)}",
                        "type": "youtube",
                        "title": formatted_title,
                        "duration": capped_dur,
                        "duration_str": time.strftime('%M:%S', time.gmtime(capped_dur)),
                        "thumbnail": cand.get("thumbnail", ""),
                        "uploader": cand_uploader,
                        "stream_url": cand.get('url'),
                        "original_url": cand_url,
                        "http_headers": cand.get("http_headers", {}),
                        "added_at": time.strftime("%H:%M:%S"),
                        "resolved_at": time.time(),
                        "category": cat_name
                    }
                    print(f"[AutoDJ Dynamic Search] Discovered valid track: {formatted_title} ({reason})")
                    return track
        except Exception as e:
            print(f"[AutoDJ Dynamic Search] Error for '{search_query}': {e}")

        return None

    def resolve_next_slot_track(self, step: int) -> Optional[Dict[str, Any]]:
        """
        Resolves a guaranteed valid track strictly matching the category required for 'step':
        1. Checks curated catalog for unplayed candidates (< 24h lockout).
        2. Tries candidate resolution (validating follower count >= 50k, anti-karaoke).
        3. If catalog candidates are exhausted or fail, executes dynamic YouTube search for that category.
        """
        cat_key, cat_name = get_target_category_for_step(step)

        catalog = [dict(x, category=cat_name) for x in CHART_CATALOGS.get(cat_key, [])]
        random.shuffle(catalog)

        # 1. Filter out songs played in the last 24 hours
        unplayed = [c for c in catalog if not self.station_engine.is_duplicate(c["title"])]

        # Try unplayed catalog items first
        for item in unplayed[:5]:
            track = self._resolve_candidate_stream(
                cand_query_or_url=item.get("query") or item.get("title"),
                cat_name=cat_name,
                fallback_title=item.get("title"),
                fallback_artist=item.get("artist")
            )
            if track:
                return track

        # 2. Dynamic Search fallback for fresh variety & exhausted catalog
        dyn_track = self._fetch_from_dynamic_youtube_search(cat_key, cat_name)
        if dyn_track:
            return dyn_track

        # 3. Last fallback: try any unplayed catalog items that haven't been resolved yet
        for item in catalog:
            if not self.station_engine.is_duplicate(item.get("title", "")):
                track = self._resolve_candidate_stream(
                    cand_query_or_url=item.get("query") or item.get("title"),
                    cat_name=cat_name,
                    fallback_title=item.get("title"),
                    fallback_artist=item.get("artist")
                )
                if track:
                    return track

        return None

    def get_next_unplayed_catalog_item(self) -> Optional[Dict[str, str]]:
        """Picks the next unplayed catalog item adhering to the rotation sequence."""
        with self.lock:
            step = self.rotation_step
            cat_key, cat_name = get_target_category_for_step(step)
            candidates = [dict(x, category=cat_name) for x in CHART_CATALOGS.get(cat_key, [])]
            random.shuffle(candidates)
            unplayed = [c for c in candidates if not self.station_engine.is_duplicate(c["title"])]
            if unplayed:
                return unplayed[0]
            if candidates:
                return candidates[0]
            return None

    def queue_single_chart_item(self, item: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Resolves and immediately adds a single track item to the playlist queue."""
        cat_name = item.get("category", "Hit")
        track = self._resolve_candidate_stream(
            cand_query_or_url=item.get("query") or item.get("title"),
            cat_name=cat_name,
            fallback_title=item.get("title"),
            fallback_artist=item.get("artist")
        )
        if track:
            with self.station_engine.lock:
                self.station_engine.playlist.append(track)
            print(f"[AutoDJ] Manually queued track: {track['title']}")
        return track

    def load_preset_chart(self, chart_type: str = "mixed", count: int = 5) -> List[Dict[str, Any]]:
        """Loads a selection of unplayed songs concurrently preserving exact rules and sequence."""
        tracks_to_add = []
        if chart_type == "mixed":
            for _ in range(count):
                step = self.rotation_step
                track = self.resolve_next_slot_track(step)
                if track:
                    with self.station_engine.lock:
                        self.station_engine.playlist.append(track)
                    self.rotation_step = (self.rotation_step + 1) % 22
                    tracks_to_add.append(track)
            return tracks_to_add

        cat_map = {
            "sinhala": ("sinhala_regular", "Sinhala"),
            "remix": ("sinhala_remix", "Sinhala Remix"),
            "hindi": ("hindi", "Hindi"),
            "english": ("english", "English")
        }
        cat_info = cat_map.get(chart_type, ("sinhala_regular", "Sinhala"))
        cat_key, cat_name = cat_info

        pool = [dict(x, category=cat_name) for x in CHART_CATALOGS.get(cat_key, [])]
        random.shuffle(pool)
        unplayed = [c for c in pool if not self.station_engine.is_duplicate(c["title"])]

        for item in unplayed[:count]:
            track = self._resolve_candidate_stream(
                cand_query_or_url=item.get("query") or item.get("title"),
                cat_name=cat_name,
                fallback_title=item.get("title"),
                fallback_artist=item.get("artist")
            )
            if track:
                with self.station_engine.lock:
                    self.station_engine.playlist.append(track)
                tracks_to_add.append(track)

        return tracks_to_add

    def _autodj_loop(self):
        """
        Continuous 24/7 Auto-DJ loop.
        Maintains a 10-song standby queue in strict, deterministic rotation sequence:
        - 10 Sinhala songs (guaranteeing at least 2 DJ remixes)
        - 1 English hit
        - 10 Sinhala songs (guaranteeing at least 2 DJ remixes)
        - 1 Hindi hit
        - Repeat!
        Only advances rotation_step once a track for that exact slot is resolved and added.
        """
        print("[AutoDJ] 24/7 Auto-DJ deterministic rotation loop initialized.")
        time.sleep(1.0)

        while self.is_running:
            try:
                if self.enabled:
                    # Maintain full 10-song standby queue in exact deterministic sequence
                    queue_len = len(self.station_engine.playlist)
                    needed = 10 - queue_len

                    if needed > 0 and self.is_running and self.enabled:
                        for _ in range(needed):
                            if not self.is_running or not self.enabled:
                                break
                            
                            current_step = self.rotation_step
                            cat_key, cat_name = get_target_category_for_step(current_step)
                            
                            track = self.resolve_next_slot_track(current_step)
                            if track:
                                with self.station_engine.lock:
                                    self.station_engine.playlist.append(track)
                                
                                # Advance rotation step ONLY after track is safely queued
                                self.rotation_step = (self.rotation_step + 1) % 22
                                print(f"[AutoDJ] Queued Slot [{len(self.station_engine.playlist)}/10] (Step {current_step+1}/22 - {cat_name}): {track['title']} ({track['duration']}s)")
                            else:
                                print(f"[AutoDJ] Warning: Could not resolve track for step {current_step+1}/22 ({cat_name}). Will retry same slot.")
                                time.sleep(1.0)
                                break
            except Exception as e:
                print(f"[AutoDJ] Loop error: {e}")

            time.sleep(2)
