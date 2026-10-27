import time
import random
import threading
import yt_dlp
from typing import List, Dict, Any, Optional

CHART_CATALOGS = {
    "sinhala": [
        {"title": "Manike Mage Hithe (මැණිකේ මගේ හිතේ)", "artist": "Yohani & Satheeshan", "query": "ytsearch1:Manike Mage Hithe Yohani Chamath Sangeeth"},
        {"title": "Haadu (හාදු)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Haadu Kanchana Anuradhi Official"},
        {"title": "Naadagam Geethaya (නාඩගම් ගීතය)", "artist": "Dinesh Gamage & Sanuka", "query": "ytsearch1:Naadagam Geethaya Dinesh Gamage Sanuka"},
        {"title": "Saragaye (සරාගයේ)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Saragaye Sanuka Wickramasinghe Official"},
        {"title": "Rawwath (රව්වත්)", "artist": "Yohani & Chamath Sangeeth", "query": "ytsearch1:Rawwath Yohani Official Music Video"},
        {"title": "Chanchala (චංචල)", "artist": "Dinesh Gamage", "query": "ytsearch1:Chanchala Dinesh Gamage Official"},
        {"title": "Kuweni (කුවේණි)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Kuweni Ridma Weerawardena Charitha Attalage"},
        {"title": "Rata Wata (රට වටා)", "artist": "Hana Shafa", "query": "ytsearch1:Rata Wata Hana Shafa Official"},
        {"title": "Mal Onchilla (මල් ඔන්චිල්ලා)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Mal Onchilla Kanchana Anuradhi"},
        {"title": "Seethala Pinne (සීතල පින්නේ)", "artist": "Kasun Kalhara", "query": "ytsearch1:Seethala Pinne Kasun Kalhara"},
        {"title": "Sandaganawa (සඳගනාව)", "artist": "Kanchana Anuradhi", "query": "ytsearch1:Sandaganawa Kanchana Anuradhi Official"},
        {"title": "Mathaka Manpeth (මතක මංපෙත්)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Mathaka Manpeth Sanuka Official"},
        {"title": "Sandawathura Se (සඳවතුර සේ)", "artist": "Kasun Kalhara", "query": "ytsearch1:Sandawathura Se Kasun Kalhara Official"},
        {"title": "Thahanam (තහනම්)", "artist": "Supun Perera", "query": "ytsearch1:Thahanam Supun Perera Official"},
        {"title": "Ananthayata Yanawamai (අනන්තයට යනවාමයි)", "artist": "Kasun Kalhara", "query": "ytsearch1:Ananthayata Yanawamai Kasun Kalhara"},
        {"title": "Mal Mitak Thiyanna (මල් මිටක් තියන්න)", "artist": "Kasun Kalhara", "query": "ytsearch1:Mal Mitak Thiyanna Kasun Kalhara"},
        {"title": "Adariye (ආදරියේ)", "artist": "Mihiran", "query": "ytsearch1:Adariye Mihiran Official Video"},
        {"title": "Neth Mane (නෙත් මානේ)", "artist": "Dinesh Gamage & Kaizer Kaiz", "query": "ytsearch1:Neth Mane Dinesh Gamage Kaizer Kaiz"},
        {"title": "Duka Daara (දුක දාරා)", "artist": "Mihiran & Dilki Uresha", "query": "ytsearch1:Duka Daara Mihiran Dilki Uresha"},
        {"title": "Rosa Pethi (රෝස පෙති)", "artist": "Sohan Weerasinghe", "query": "ytsearch1:Rosa Pethi Sohan Weerasinghe"},
        {"title": "Oba Magemai (ඔබ මගේමයි)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Oba Magemai Sanuka Official"},
        {"title": "Den Numba Koheda (දැන් නුඹ කොහෙද)", "artist": "Supun Perera", "query": "ytsearch1:Den Numba Koheda Supun Perera"},
        {"title": "Ra Tharakawo (රෑ තාරකාවෝ)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Ra Tharakawo Bathiya Santhush"},
        {"title": "Nethu Saluna (නෙතු සැලුණා)", "artist": "Bathiya and Santhush", "query": "ytsearch1:Nethu Saluna Bathiya Santhush BnS"},
        {"title": "Obe Premaye (ඔබේ ප්‍රේමයේ)", "artist": "Sanuka Wickramasinghe", "query": "ytsearch1:Obe Premaye Sanuka Official Video"},
        {"title": "Me Jeewithe (මේ ජීවිතේ)", "artist": "Sanuka & Dinesh", "query": "ytsearch1:Me Jeewithe Sanuka Dinesh Gamage"},
        {"title": "Hitha Wawannema Na (හිත වාවන්නෙම නෑ)", "artist": "Chamath Sangeeth", "query": "ytsearch1:Hitha Wawannema Na Chamath Sangeeth"},
        {"title": "Radhawani (රාධාවනී)", "artist": "Supun Perera", "query": "ytsearch1:Radhawani Supun Perera Official"},
        {"title": "Malbara Himidiriye (මල්බර හිමිදිරියේ)", "artist": "Bathiya & Santhush", "query": "ytsearch1:Malbara Himidiriye Bathiya Santhush"},
        {"title": "Sulagak Wee (සුළඟක් වී)", "artist": "Mihiran", "query": "ytsearch1:Sulagak Wee Mihiran Official"},
        {"title": "Gindara (ගින්දර)", "artist": "Dinesh Gamage", "query": "ytsearch1:Gindara Dinesh Gamage Official"},
        {"title": "Sanda Midulata Enawa (සඳ මිදුලට එනවා)", "artist": "Kasun Kalhara", "query": "ytsearch1:Sanda Midulata Enawa Kasun Kalhara"},
        {"title": "Nelum Vile (නෙළුම් විලේ)", "artist": "Daddy", "query": "ytsearch1:Nelum Vile Daddy Band Official"},
        {"title": "Chandrayan Pidu (චන්ද්‍රයාන් පිදූ)", "artist": "Kasun Kalhara", "query": "ytsearch1:Chandrayan Pidu Kasun Kalhara"},
        {"title": "Kawiyak Wee (කවියක් වී)", "artist": "Ridma Weerawardena", "query": "ytsearch1:Kawiyak Wee Ridma Weerawardena"}
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

def get_mixed_chart() -> List[Dict[str, str]]:
    """Builds a diverse, randomized mixed chart across Sinhala, English, and Hindi."""
    sinhala_items = [dict(x, category="Sinhala") for x in CHART_CATALOGS["sinhala"]]
    hindi_items = [dict(x, category="Hindi") for x in CHART_CATALOGS["hindi"]]
    english_items = [dict(x, category="English") for x in CHART_CATALOGS["english"]]

    # Randomly shuffle each category list
    random.shuffle(sinhala_items)
    random.shuffle(hindi_items)
    random.shuffle(english_items)

    mixed = []
    max_len = max(len(sinhala_items), len(hindi_items), len(english_items))
    for i in range(max_len):
        if i < len(sinhala_items):
            mixed.append(sinhala_items[i])
        if i < len(english_items):
            mixed.append(english_items[i])
        if i < len(hindi_items):
            mixed.append(hindi_items[i])
            
    # Final random shuffle for maximum unpredictability
    random.shuffle(mixed)
    return mixed

class AutoDJEngine:
    def __init__(self, station_engine):
        self.station_engine = station_engine
        self.enabled = True
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
            print("[AutoDJ] 24/7 Auto-DJ Engine started with Random Shuffle active.")

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
        Picks a purely RANDOM song from the unplayed catalog tracks.
        Guarantees tracks do not repeat in a predictable cycle.
        """
        with self.lock:
            # Refresh mixed catalog if empty
            if not self.mixed_catalog:
                self.mixed_catalog = get_mixed_chart()

            # Find all candidates currently not active, not queued, and not in recent history
            unplayed = [
                item for item in self.mixed_catalog
                if not self.station_engine.is_duplicate(item["title"])
            ]

            if unplayed:
                chosen = random.choice(unplayed)
                print(f"[AutoDJ Random] Picked random hit ({len(unplayed)} candidates remaining): {chosen['title']}")
                return chosen

            # If all catalog songs were recently played, re-shuffle fresh mixed catalog
            print("[AutoDJ Random] All catalog songs recently played. Refreshing random pool...")
            self.mixed_catalog = get_mixed_chart()
            return random.choice(self.mixed_catalog)

    def queue_single_chart_item(self, item: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Resolve YouTube direct stream and add to queue with strict duplicate check."""
        query = item.get("query") or item.get("title")
        
        # Check title before expensive YouTube extraction
        if self.station_engine.is_duplicate(item.get("title", "")):
            print(f"[AutoDJ] Skipping duplicate catalog song: {item.get('title')}")
            return None

        entry = None
        # 1. Fast SoundCloud query first (Zero bot checks, instant 0.5s resolution in Cloud Datacenters)
        try:
            sc_query = f"scsearch5:{item.get('title')}"
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
                        print(f"[AutoDJ] Fast SoundCloud hit: {entry.get('title')} ({dur}s)")
                        break
        except Exception as sc_err:
            print(f"[AutoDJ] SoundCloud attempt: {sc_err}")

        # 2. YouTube extraction fallback if SoundCloud didn't return
        if not entry or not entry.get('url'):
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
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
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        entry = info['entries'][0]
                    elif info and info.get('url'):
                        entry = info
            except Exception as yt_err:
                print(f"[AutoDJ] YouTube fallback failed ({yt_err})")

        if not entry or not entry.get('url'):
            return None

        audio_url = entry.get('url')

        title = f"[{item.get('category', 'Hit')}] {entry.get('title', item['title'])}"
        original_url = entry.get("webpage_url", "")

        # Strict duplicate check on resolved YouTube title and URL
        if self.station_engine.is_duplicate(title, original_url):
            print(f"[AutoDJ] Duplicate detected post-extraction, skipping: {title}")
            return None

        # Filter out 30s snippets (<45s); allow long mixes and DJ remixes
        raw_dur = entry.get("duration", 0)
        if raw_dur and raw_dur < 45:
            print(f"[AutoDJ] Invalid short snippet duration ({raw_dur}s), skipping: {title}")
            return None

        track = {
            "id": f"autodj_{int(time.time() * 1000)}",
            "type": "youtube",
            "title": title,
            "duration": entry.get("duration", 0),
            "duration_str": time.strftime('%M:%S', time.gmtime(entry.get("duration", 0))),
            "thumbnail": entry.get("thumbnail", ""),
            "uploader": entry.get("uploader", item.get("artist", "Auto-DJ")),
            "stream_url": audio_url,
            "original_url": original_url,
            "http_headers": entry.get("http_headers", {}),
            "added_at": time.strftime("%H:%M:%S")
        }

        with self.station_engine.lock:
            self.station_engine.playlist.append(track)
        print(f"[AutoDJ] Queued random song: {track['title']}")
        return track

    def load_preset_chart(self, chart_type: str = "mixed", count: int = 5) -> List[Dict[str, Any]]:
        """Loads a random selection of unplayed songs from the chosen chart."""
        if chart_type == "sinhala":
            catalog = [dict(x, category="Sinhala") for x in CHART_CATALOGS["sinhala"]]
        elif chart_type == "hindi":
            catalog = [dict(x, category="Hindi") for x in CHART_CATALOGS["hindi"]]
        elif chart_type == "english":
            catalog = [dict(x, category="English") for x in CHART_CATALOGS["english"]]
        else:
            catalog = list(self.mixed_catalog)

        # Randomly shuffle candidates so every click yields a fresh, random set
        random.shuffle(catalog)

        added = []
        for item in catalog:
            if len(added) >= count:
                break
            if self.station_engine.is_duplicate(item.get("title", "")):
                continue
            try:
                t = self.queue_single_chart_item(item)
                if t:
                    added.append(t)
            except Exception as e:
                print(f"[AutoDJ] Error loading {item['title']}: {e}")
        return added

    def _autodj_loop(self):
        print("[AutoDJ] Auto-DJ 24/7 Engine Loop active (Fast Standby Preload Mode).")
        time.sleep(2)
        
        while self.is_running:
            try:
                if self.enabled:
                    # Keep 10-song standby chart fully loaded at all times
                    while len(self.station_engine.playlist) < 10 and self.is_running and self.enabled:
                        item = self.get_next_unplayed_catalog_item()
                        if not item:
                            # Reset history to allow fresh continuous rotation
                            with self.station_engine.lock:
                                self.station_engine.played_history.clear()
                            item = self.get_next_unplayed_catalog_item()
                        if item:
                            try:
                                t = self.queue_single_chart_item(item)
                                if not t:
                                    time.sleep(0.3)
                            except Exception as e:
                                print(f"[AutoDJ] Auto-queue error: {e}")
                                time.sleep(0.3)
                        else:
                            break
                        time.sleep(0.8)
            except Exception as e:
                print(f"[AutoDJ] Loop error: {e}")

            time.sleep(5)
