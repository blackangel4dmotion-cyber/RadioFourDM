import sys
import time
import random
import threading
import concurrent.futures
import yt_dlp
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# In-memory stream cache for instant repeat-less re-queries (2 hours TTL)
_STREAM_CACHE: Dict[str, Any] = {}

def is_unwanted_unofficial_cover(title: str, uploader: str = "") -> bool:
    """
    Detects and filters out amateur / unofficial cover songs, reactions, and karaoke.
    Prioritizes official master recordings, official music videos, Coke studio sessions, and official remixes.
    """
    t = (title or "").lower()
    u = (uploader or "").lower()

    # Reject obvious amateur cover patterns
    bad_patterns = [
        "guitar cover", "piano cover", "drum cover", "acoustic cover",
        "karaoke", "instrumental cover", "reaction", "reacting", "vocal cover",
        "singing cover", "bedroom cover", "fan cover", "amateur cover",
        "female version cover", "male version cover", "unplugged cover",
        "bass cover", "ukulele cover", "dance cover", "tutorial",
        "how to play", "lyrics only", "chords", "shorts", "shorts cover"
    ]
    for p in bad_patterns:
        if p in t:
            return True

    # Reject old classical songs / retro oldies (Station plays ONLY modern hits & remixes)
    old_classic_patterns = [
        "old song", "classic song", "golden oldies", "70s", "80s", "90s hits",
        "purana", "parana sindu", "calypso", "vintage", "retro live",
        "old hits", "nonstop oldies", "sarala gee", "classical", "gramophone",
        "bailaya", "old baila"
    ]
    for p in old_classic_patterns:
        if p in t:
            return True

    # If the word 'cover' is present:
    if "cover" in t:
        # Check if it is an authentic recognized official production
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
        {"title": "Kandula (කඳුල)", "artist": "Centigradz", "query": "ytsearch1:Kandula Centigradz Official"}
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
        {"title": "Nela Ganna Baha (Remix)", "artist": "Centigradz Remix", "query": "ytsearch1:Nela Ganna Baha Remix Centigradz"}
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
        {"title": "Teri Mitti (Kesari)", "artist": "B Praak", "query": "ytsearch1:Teri Mitti Kesari Akshay Kumar B Praak"}
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
        {"title": "Dance Monkey", "artist": "Tones and I", "query": "ytsearch1:Tones and I Dance Monkey Official Music Video"}
    ]
}

# Convenience combined Sinhala catalog
CHART_CATALOGS["sinhala"] = CHART_CATALOGS["sinhala_regular"] + CHART_CATALOGS["sinhala_remix"]

def get_mixed_chart() -> List[Dict[str, str]]:
    """
    Builds a mixed chart strictly adhering to the Radio Four D M 24/7 sequence:
    10 Sinhala (with at least 2 remixes guaranteed) -> 1 English -> 10 Sinhala (with at least 2 remixes guaranteed) -> 1 Hindi -> repeat.
    """
    reg_pool = [dict(x, category="Sinhala") for x in CHART_CATALOGS["sinhala_regular"]]
    remix_pool = [dict(x, category="Sinhala Remix") for x in CHART_CATALOGS["sinhala_remix"]]
    eng_pool = [dict(x, category="English") for x in CHART_CATALOGS["english"]]
    hin_pool = [dict(x, category="Hindi") for x in CHART_CATALOGS["hindi"]]

    random.shuffle(reg_pool)
    random.shuffle(remix_pool)
    random.shuffle(eng_pool)
    random.shuffle(hin_pool)

    mixed = []
    r_idx, rx_idx, e_idx, h_idx = 0, 0, 0, 0

    # Generate 2 full cycles (44 songs)
    for _ in range(2):
        # 1. First 10 Sinhala songs (8 regular + 2 remixes)
        for i in range(10):
            if i in (3, 7):
                mixed.append(dict(remix_pool[rx_idx % len(remix_pool)]))
                rx_idx += 1
            else:
                mixed.append(dict(reg_pool[r_idx % len(reg_pool)]))
                r_idx += 1
        # 2. 1 English song
        mixed.append(dict(eng_pool[e_idx % len(eng_pool)]))
        e_idx += 1

        # 3. Next 10 Sinhala songs (8 regular + 2 remixes)
        for i in range(10):
            if i in (3, 7):
                mixed.append(dict(remix_pool[rx_idx % len(remix_pool)]))
                rx_idx += 1
            else:
                mixed.append(dict(reg_pool[r_idx % len(reg_pool)]))
                r_idx += 1
        # 4. 1 Hindi song
        mixed.append(dict(hin_pool[h_idx % len(hin_pool)]))
        h_idx += 1

    return mixed

class AutoDJEngine:
    def __init__(self, station_engine):
        self.station_engine = station_engine
        self.enabled = True
        self.rotation_step = 0 # 0..21 (22-song rotation cycle)
        self.mixed_catalog = get_mixed_chart()
        self.is_fetching = False
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
            print("[AutoDJ] 24/7 Auto-DJ Engine started with 22-step Rotation Sequence (10 Sinhala [incl. 2 remixes] -> 1 English -> 10 Sinhala [incl. 2 remixes] -> 1 Hindi).")

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

    def get_next_unplayed_catalog_item(self) -> Optional[Dict[str, str]]:
        """
        Picks the next song strictly adhering to the 24/7 rotation pattern:
        - 10 Sinhala songs (guaranteeing at least 2 DJ remixes)
        - 1 English song
        - 10 Sinhala songs (guaranteeing at least 2 DJ remixes)
        - 1 Hindi song
        Strictly enforces 1-hour duplicate lockout so no song repeats within 60 minutes.
        """
        with self.lock:
            step = self.rotation_step
            # Determine target catalog based on step in 22-song cycle
            # Steps 3, 7, 14, 18 = Guaranteed Sinhala Remixes
            # Step 10 = English
            # Step 21 = Hindi
            # Remaining 16 steps = Sinhala Regular
            if step in (3, 7, 14, 18):
                cat_key = "sinhala_remix"
                cat_name = "Sinhala Remix"
            elif step == 10:
                cat_key = "english"
                cat_name = "English"
            elif step == 21:
                cat_key = "hindi"
                cat_name = "Hindi"
            else:
                cat_key = "sinhala_regular"
                cat_name = "Sinhala"

            candidates = [dict(x, category=cat_name) for x in CHART_CATALOGS.get(cat_key, [])]
            random.shuffle(candidates)

            # Filter candidates not played in the last 60 minutes
            unplayed = [c for c in candidates if not self.station_engine.is_duplicate(c["title"])]

            if unplayed:
                chosen = unplayed[0]
                self.rotation_step = (self.rotation_step + 1) % 22
                print(f"[AutoDJ] Sequence [{step + 1}/22] -> Picked {cat_name} ({len(unplayed)} unplayed left): {chosen['title']}")
                return chosen

            # If all tracks in this category were played within 60m, pick fresh from pool
            print(f"[AutoDJ] Sequence [{step + 1}/22]: All {cat_name} songs played recently. Selecting fresh track.")
            if candidates:
                chosen = candidates[0]
                self.rotation_step = (self.rotation_step + 1) % 22
                return chosen

            self.rotation_step = (self.rotation_step + 1) % 22
            return random.choice([dict(x, category="Sinhala") for x in CHART_CATALOGS["sinhala_regular"]])

    def resolve_single_chart_item(self, item: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Resolves YouTube direct stream for a catalog item without modifying playlist.
        Enforces:
        - 1-hour duplicate check
        - Filter out amateur / unofficial cover songs
        - Hard 6-minute cap (360 seconds)
        """
        query = item.get("query") or item.get("title")
        
        # Check title before expensive YouTube extraction
        if self.station_engine.is_duplicate(item.get("title", "")):
            print(f"[AutoDJ] Skipping duplicate catalog song: {item.get('title')}")
            return None

        entry = None
        now = time.time()
        if query in _STREAM_CACHE and (now - _STREAM_CACHE[query][1]) < 7200:
            entry = _STREAM_CACHE[query][0]

        # 1. Primary: Direct YouTube extraction with Android/iOS/Web client headers
        if not entry or not entry.get('url'):
            yt_query = query
            if yt_query.startswith("ytsearch1:"):
                yt_query = "ytsearch2:" + yt_query[len("ytsearch1:"):]
            elif not yt_query.startswith("ytsearch") and not yt_query.startswith("http"):
                yt_query = f"ytsearch2:{yt_query} Official"

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
                    info = ydl.extract_info(yt_query, download=False)
                    candidates = info.get('entries') or ([info] if info and info.get('url') else [])
                    for cand in candidates:
                        if not cand or not cand.get('url'):
                            continue
                        cand_title = cand.get('title', '')
                        cand_uploader = cand.get('uploader', '')
                        # Filter out unofficial / amateur cover songs
                        if is_unwanted_unofficial_cover(cand_title, cand_uploader):
                            print(f"[AutoDJ] Filtered out unofficial cover: '{cand_title}' ({cand_uploader})")
                            continue
                        entry = cand
                        break
                    if not entry and candidates:
                        entry = candidates[0]
            except Exception as yt_err:
                print(f"[AutoDJ] YouTube attempt: {yt_err}")

        # 2. SoundCloud fallback if YouTube didn't return
        if not entry or not entry.get('url'):
            try:
                sc_query = f"scsearch3:{item.get('title')} official"
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
                            if not is_unwanted_unofficial_cover(cand.get('title', ''), cand.get('uploader', '')):
                                entry = cand
                                break
            except Exception as sc_err:
                print(f"[AutoDJ] SoundCloud fallback failed: {sc_err}")

        if not entry or not entry.get('url'):
            return None

        # Verify resolved entry title is not an unwanted unofficial cover
        if is_unwanted_unofficial_cover(entry.get('title', ''), entry.get('uploader', '')):
            print(f"[AutoDJ] Skipped unofficial cover post-check: {entry.get('title')}")
            return None

        # Cache valid entry
        _STREAM_CACHE[query] = (entry, now)

        audio_url = entry.get('url')
        title = f"[{item.get('category', 'Hit')}] {entry.get('title', item['title'])}"
        original_url = entry.get("webpage_url", "")

        # Strict duplicate check on resolved YouTube title and URL
        if self.station_engine.is_duplicate(title, original_url):
            print(f"[AutoDJ] Duplicate detected post-extraction, skipping: {title}")
            return None

        # Filter out short snippets (<45s)
        raw_dur = entry.get("duration", 0)
        if raw_dur and raw_dur < 45:
            print(f"[AutoDJ] Invalid short snippet duration ({raw_dur}s), skipping: {title}")
            return None

        # Hard 6-minute cap (360 seconds) strictly enforced
        capped_dur = min(raw_dur, 360) if raw_dur else 360

        track = {
            "id": f"autodj_{int(time.time() * 1000)}_{random.randint(100, 999)}",
            "type": "youtube",
            "title": title,
            "duration": capped_dur,
            "duration_str": time.strftime('%M:%S', time.gmtime(capped_dur)),
            "thumbnail": entry.get("thumbnail", ""),
            "uploader": entry.get("uploader", item.get("artist", "Auto-DJ")),
            "stream_url": audio_url,
            "original_url": original_url,
            "http_headers": entry.get("http_headers", {}),
            "added_at": time.strftime("%H:%M:%S"),
            "resolved_at": time.time(),
            "category": item.get("category", "Hit")
        }
        return track

    def queue_single_chart_item(self, item: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Resolve and immediately append single track to playlist."""
        track = self.resolve_single_chart_item(item)
        if track:
            with self.station_engine.lock:
                self.station_engine.playlist.append(track)
            print(f"[AutoDJ] Queued rotation song: {track['title']} (Capped at {track['duration']}s)")
        return track

    def load_preset_chart(self, chart_type: str = "mixed", count: int = 5) -> List[Dict[str, Any]]:
        """Loads a selection of unplayed songs concurrently preserving exact sequence."""
        if chart_type == "mixed":
            candidates = []
            for _ in range(count):
                item = self.get_next_unplayed_catalog_item()
                if not item:
                    with self.station_engine.lock:
                        self.station_engine.played_history.clear()
                    item = self.get_next_unplayed_catalog_item()
                if item:
                    candidates.append(item)
        elif chart_type == "sinhala":
            catalog = [dict(x, category="Sinhala") for x in CHART_CATALOGS["sinhala_regular"]]
            random.shuffle(catalog)
            candidates = [c for c in catalog if not self.station_engine.is_duplicate(c["title"])][:count]
        elif chart_type == "remix":
            catalog = [dict(x, category="Sinhala Remix") for x in CHART_CATALOGS["sinhala_remix"]]
            random.shuffle(catalog)
            candidates = [c for c in catalog if not self.station_engine.is_duplicate(c["title"])][:count]
        elif chart_type == "hindi":
            catalog = [dict(x, category="Hindi") for x in CHART_CATALOGS["hindi"]]
            random.shuffle(catalog)
            candidates = [c for c in catalog if not self.station_engine.is_duplicate(c["title"])][:count]
        elif chart_type == "english":
            catalog = [dict(x, category="English") for x in CHART_CATALOGS["english"]]
            random.shuffle(catalog)
            candidates = [c for c in catalog if not self.station_engine.is_duplicate(c["title"])][:count]
        else:
            candidates = []

        if not candidates:
            return []

        resolved_tracks = [None] * len(candidates)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(self.resolve_single_chart_item, it): i for i, it in enumerate(candidates)}
            try:
                for f in concurrent.futures.as_completed(futs, timeout=18):
                    idx = futs[f]
                    try:
                        resolved_tracks[idx] = f.result()
                    except Exception as e:
                        print(f"[AutoDJ] Preset chart extract err {idx}: {e}")
            except TimeoutError:
                pass

        added = []
        with self.station_engine.lock:
            for track in resolved_tracks:
                if track:
                    self.station_engine.playlist.append(track)
                    added.append(track)
        return added

    def _autodj_loop(self):
        print("[AutoDJ] Auto-DJ 24/7 Engine Loop active (Strict Ordered Rotation Mode).")
        # Allow server to bind port
        time.sleep(1.5)

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="AutoDJWorker")

        while self.is_running:
            try:
                if self.enabled:
                    # 1. Instant bootstrap if station is completely silent and queue is empty
                    if len(self.station_engine.playlist) == 0 and not self.station_engine.deck_a.is_active and not self.station_engine.deck_b.is_active:
                        first_item = self.get_next_unplayed_catalog_item()
                        if first_item:
                            first_track = self.resolve_single_chart_item(first_item)
                            if first_track:
                                with self.station_engine.lock:
                                    self.station_engine.playlist.append(first_track)
                                print(f"[AutoDJ] Fast bootstrap track: {first_track['title']} ({first_track['duration']}s)")

                    needed = 10 - len(self.station_engine.playlist)
                    if needed > 0 and self.is_running and self.enabled:
                        batch_size = min(needed, 5)
                        items_to_queue = []
                        for _ in range(batch_size):
                            item = self.get_next_unplayed_catalog_item()
                            if not item:
                                # Reset history to allow fresh continuous rotation
                                with self.station_engine.lock:
                                    self.station_engine.played_history.clear()
                                item = self.get_next_unplayed_catalog_item()
                            if item:
                                items_to_queue.append(item)

                        if items_to_queue:
                            # Map each future to its original sequence index so order is strictly maintained
                            future_to_idx = {executor.submit(self.resolve_single_chart_item, it): idx for idx, it in enumerate(items_to_queue)}
                            resolved_tracks = [None] * len(items_to_queue)
                            try:
                                for f in concurrent.futures.as_completed(future_to_idx, timeout=35):
                                    idx = future_to_idx[f]
                                    try:
                                        resolved_tracks[idx] = f.result()
                                    except Exception as e:
                                        print(f"[AutoDJ] Parallel extract error for item {idx}: {e}")
                            except TimeoutError:
                                print(f"[AutoDJ] Parallel preload timeout reached; proceeding with resolved tracks.")

                            # Append into playlist IN STRICT ORDER of the rotation sequence
                            with self.station_engine.lock:
                                for idx, track in enumerate(resolved_tracks):
                                    if track:
                                        self.station_engine.playlist.append(track)
                                        print(f"[AutoDJ] Added in rotation order [{len(self.station_engine.playlist)}/10]: {track['title']} ({track['duration']}s)")
            except Exception as e:
                print(f"[AutoDJ] Loop error: {e}")

            time.sleep(2)
