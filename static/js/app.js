// AI Radio Master Console - Pro DJ Studio Engine

// DOM Elements
const radioAudio = document.getElementById('radioAudio');
const playBtn = document.getElementById('playBtn');
const skipBtn = document.getElementById('skipBtn');
const volumeSlider = document.getElementById('volumeSlider');
const volumeIcon = document.getElementById('volumeIcon');
const playerStatusTip = document.getElementById('playerStatusTip');

const nowPlayingTitle = document.getElementById('nowPlayingTitle');
const nowPlayingUploader = document.getElementById('nowPlayingUploader');
const trackTypeBadge = document.getElementById('trackTypeBadge');
const listenerCount = document.getElementById('listenerCount');
const queueCount = document.getElementById('queueCount');
const playlistContainer = document.getElementById('playlistContainer');
const liveClock = document.getElementById('liveClock');
const masterDeckCard = document.querySelector('.master-deck-card');

const deckABadge = document.getElementById('deckABadge');
const deckBBadge = document.getElementById('deckBBadge');
const deckATitle = document.getElementById('deckATitle');
const deckBTitle = document.getElementById('deckBTitle');
const deckATime = document.getElementById('deckATime');
const deckBTime = document.getElementById('deckBTime');
const deckAGain = document.getElementById('deckAGain');
const deckBGain = document.getElementById('deckBGain');
const deckAMuteBtn = document.getElementById('deckAMuteBtn');
const deckBMuteBtn = document.getElementById('deckBMuteBtn');
const manualCrossfader = document.getElementById('manualCrossfader');
const crossfadeStatusLabel = document.getElementById('crossfadeStatusLabel');

const youtubeForm = document.getElementById('youtubeForm');
const ytUrlInput = document.getElementById('ytUrlInput');
const addYtBtn = document.getElementById('addYtBtn');
const ytFeedback = document.getElementById('ytFeedback');

const adForm = document.getElementById('adForm');
const adTextInput = document.getElementById('adTextInput');
const adLangSelect = document.getElementById('adLangSelect');
const adProviderSelect = document.getElementById('adProviderSelect');
const adVoiceSelect = document.getElementById('adVoiceSelect');
const broadcastAdBtn = document.getElementById('broadcastAdBtn');
const adFeedback = document.getElementById('adFeedback');

const schedulerToggle = document.getElementById('schedulerToggle');
const newsSchedulerToggle = document.getElementById('newsSchedulerToggle');
const newsHeadlineText = document.getElementById('newsHeadlineText');
const broadcastNewsBtn = document.getElementById('broadcastNewsBtn');
const newsStatusMsg = document.getElementById('newsStatusMsg');
const autoDjToggle = document.getElementById('autoDjToggle');
const testTimeBtn = document.getElementById('testTimeBtn');
const timeStatusMsg = document.getElementById('timeStatusMsg');
const chartFeedback = document.getElementById('chartFeedback');

const singlishToggleBtn = document.getElementById('singlishToggleBtn');
const singlishToggleLabel = document.getElementById('singlishToggleLabel');
const keyboardModeIndicator = document.getElementById('keyboardModeIndicator');

const settingsModal = document.getElementById('settingsModal');
const modalGeminiKey = document.getElementById('modalGeminiKey');
const modalCrossfadeSec = document.getElementById('modalCrossfadeSec');
const modalDuckingVol = document.getElementById('modalDuckingVol');

const geminiLiveStatusBadge = document.getElementById('geminiLiveStatusBadge');
const geminiQuickKeyInput = document.getElementById('geminiQuickKeyInput');
const geminiLinkBtn = document.getElementById('geminiLinkBtn');
const geminiQuickStatus = document.getElementById('geminiQuickStatus');
const geminiEyeIcon = document.getElementById('geminiEyeIcon');

let isPlaying = false;
let isConnecting = false;
let isSinglishActive = true;
let isUserDraggingCrossfader = false;

// Format Stream URL with current host
const streamUrl = `${window.location.protocol}//${window.location.host}/stream`;
document.getElementById('streamUrlDisplay').textContent = streamUrl;

function copyStreamUrl() {
    navigator.clipboard.writeText(streamUrl).then(() => {
        alert("Stream URL copied: " + streamUrl);
    });
}

// Live Clock
function updateClock() {
    const now = new Date();
    liveClock.textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ==========================================
// 1. HELAKURU PHONETIC UNICODE ENGINE INTEGRATION
// ==========================================
function updateSinglishUI(isSinhala) {
    if (isSinhala) {
        singlishToggleBtn.classList.add('active');
        singlishToggleLabel.textContent = "හෙළකුරු ➡️ සිංහල: ON (F12)";
        keyboardModeIndicator.className = "mode-indicator active";
        keyboardModeIndicator.textContent = "හෙළකුරු Unicode ක්‍රියාත්මකයි";
        adTextInput.placeholder = "Helakuru Singlish වලින් type කරන්න (උදා: suba qawasak yaluwane)...";
        if (adLangSelect && adLangSelect.value !== 'en') adLangSelect.value = 'si';
    } else {
        singlishToggleBtn.classList.remove('active');
        singlishToggleLabel.textContent = "English Keyboard: ON (F12)";
        keyboardModeIndicator.className = "mode-indicator";
        keyboardModeIndicator.textContent = "English Keyboard Mode";
        adTextInput.placeholder = "Type advertisement in English...";
        if (adLangSelect && adLangSelect.value !== 'si') adLangSelect.value = 'en';
    }
}

if (adLangSelect) {
    adLangSelect.addEventListener('change', () => {
        if (adLangSelect.value === 'si' && window.setHelakuruMode) {
            window.setHelakuruMode(true);
        } else if (adLangSelect.value === 'en' && window.setHelakuruMode) {
            window.setHelakuruMode(false);
        }
    });
}

document.addEventListener('singlishModeChange', (e) => {
    updateSinglishUI(e.detail.isSinhala);
});

singlishToggleBtn.addEventListener('click', () => {
    if (window.toggleHelakuruMode) {
        const active = window.toggleHelakuruMode();
        updateSinglishUI(active);
    }
});

// Sync initial state
setTimeout(() => {
    if (window.isHelakuruActive) {
        updateSinglishUI(window.isHelakuruActive());
    }
}, 100);

const AI_SCRIPT_TEMPLATES = {
    // 1. Song Dedications
    "dedication_next": (name) => `අපේ ආදරණීය ශ්‍රාවක ${name} ආදරයෙන් එකතු කරගනිමින්, Radio Four D M වෙතින් ඔබ සැමට තිළිණ කෙරෙන මීළඟ මියුරු ගීතය රසවිඳින්න!`,
    "dedication_request": (name) => `මෙන්න අපේ හිතවත් ශ්‍රාවක ${name} ගේ විශේෂ ඉල්ලීම පරිදි, Radio Four D M ඔබ වෙනුවෙන්ම තෝරාගත් අපූරු ගීතයක්!`,
    "dedication_special": (name) => `${name} වෙනුවෙන් Radio Four D M වෙතින් පිරිනමන ආදරණීය ගීත තිළිණයයි මේ. දිගටම රැඳී සිටින්න අප සමඟින්!`,
    
    // 2. Birthday Wishes
    "bday_classic": (name) => `අද දින උපන්දිනය සමරන අපගේ ආදරණීය ${name} ට, Radio Four D M පවුලේ සැමගෙන් සුබම සුබ උපන්දිනයක් ප්‍රාර්ථනා කරනවා! ප්‍රීතිමත් සුන්දර දවසක් වේවා!`,
    "bday_milestone": (name) => `සුභ උපන්දිනයක් වේවා ${name}! ඔබගේ සියලු බලාපොරොත්තු සාර්ථක වන, නිරෝගීමත් වාසනාවන්ත වසරක් වේවායි Radio Four D M අපි එක සිතින් පතනවා!`,
    "bday_party": (name) => `Happy Birthday ${name}! Radio Four D M රිද්මයෙන් ඔයාලගේ උපන්දින සාදය තවත් වර්ණවත් කරගන්න. Have a wonderful blast!`,
    
    // 3. Comedy & Fun Banter
    "comedy_work": (name) => `ආයුබෝවන් යාලුවනේ! දවස පුරාම වැඩ කරලා ඔළුවත් රිදෙනවා නේද? කිසි දේකට හිත කරදර කරගන්න එපා, Radio Four D M එක දාලා සිංදුවක් අහලා full chill එකක් දාන්න!`,
    "comedy_traffic": (name) => `ට්‍රැෆික් එකේ හිරවෙලාද ඉන්නේ? එහෙනම් හෝන් ගහලා වැඩක් නෑ, Radio Four D M volume එක වැඩි කරලා බීට් එකට නටන්න!`,
    "comedy_tea": (name) => `අප්පටසිරි... තේ බොන්න වෙලාවත් හරි නේද? වැඩ ටික පැත්තකින් තියලා තේ එකක් එක්ක Radio Four D M අහන්න සෙට් වෙන්න යාලුවනේ!`,
    "comedy_love": (name) => `කවුරු හරි තරහ වෙලාද ඉන්නේ? ඕවා ගණන් ගන්න එපා, Radio Four D M එකෙන් ලස්සන සිංදුවක් අහලා shape වෙන්න!`,
    
    // 4. Radio 4DM ID Mentions
    "id_fresh": (name) => `ඔබ මේ සවන් දෙන්නේ ශ්‍රී ලාංකේය සංගීතයේ නැවුම් අත්දැකීම, Radio Four D M සජීවී විකාශයටයි!`,
    "id_future": (name) => `Listen to the best hits, nonstop music on Radio Four D M - The Future of Digital Sound!`,
    "id_heart": (name) => `රසික හදවත් දිනූ මියුරු ගීත පෙළහර, මේ Radio Four D M - ඔබේම රේඩියෝව!`,
    "id_nonstop": (name) => `රැය පහන් වන තුරු හොඳම ගීත සමඟින්, Radio Four D M අඛණ්ඩ පැය 24 පුරාම ඔබේ ළඟින්ම!`
};

function applyTemplate(tplKey) {
    const nameInput = document.getElementById('listenerNameInput');
    const name = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : "යහළුවා";
    
    const generator = AI_SCRIPT_TEMPLATES[tplKey];
    if (generator) {
        const text = generator(name);
        if (adTextInput) {
            adTextInput.value = text;
            adTextInput.focus();
        }
        if (adLangSelect) {
            adLangSelect.value = tplKey === 'id_future' ? 'en' : 'si';
        }
        showToast("Template එක සාර්ථකව Script කොටුවට එක්විය!");
    }
}

function onListenerNameChange() {
    // Interactive handler if needed
}

// ==========================================
// XTREAM AUTO-LINK & GEMINI KEY AUTOMATION (2-MIN WATCHDOG)
// ==========================================
let xtreamTimerSeconds = 120; // 2 minutes auto-countdown
let xtreamIntervalId = null;

function updateXtreamTimerDisplay() {
    const el = document.getElementById('xtreamCountdown');
    if (!el) return;
    const mins = Math.floor(xtreamTimerSeconds / 60);
    const secs = xtreamTimerSeconds % 60;
    el.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

async function triggerXtreamLink(silent = false) {
    xtreamTimerSeconds = 120; // Reset countdown to 2 minutes
    updateXtreamTimerDisplay();
    
    if (!silent) showToast("⚡ Xtream Valid Key සක්‍රීය කරමින් පවතී...");
    try {
        const res = await fetch('/api/vault/activate-xtream', { method: 'POST' });
        const data = await res.json();
        if (data.valid) {
            showToast(`🎉 Xtream Gemini AI සාර්ථකව සම්බන්ධ විය! (${data.masked_key})`);
            const codeEl = document.getElementById('predefinedKeyText');
            if (codeEl) codeEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10b981;"></i> Active: ${data.masked_key}`;
            await checkGeminiStatus();
        } else {
            showToast(`⚠️ Xtream: ${data.message || 'Key check failed'}`);
        }
    } catch(e) {
        console.warn("Xtream link error:", e);
    }
}

function startXtreamCountdown() {
    if (xtreamIntervalId) clearInterval(xtreamIntervalId);
    updateXtreamTimerDisplay();
    
    xtreamIntervalId = setInterval(() => {
        xtreamTimerSeconds--;
        if (xtreamTimerSeconds <= 0) {
            xtreamTimerSeconds = 120; // Reset countdown
            console.log("[Xtream Auto-Timer] 2 minutes elapsed. Auto-linking Xtream Key...");
            triggerXtreamLink(true);
        } else {
            updateXtreamTimerDisplay();
        }
    }, 1000);
}

// User-custom paste and link: Supports pasting a custom new key, or activates vault
async function pasteAndLinkPredefinedKey() {
    const customKey = (geminiQuickKeyInput && geminiQuickKeyInput.value.trim()) ? geminiQuickKeyInput.value.trim() : "";
    if (customKey) {
        showToast("Google Key එක ඇතුළත් විය! සම්බන්ධ කර පරීක්ෂා කරමින් පවතී...");
        await verifyAndSaveGeminiKey(false);
    } else {
        // If empty, activate the encrypted Xtream vault directly
        await triggerXtreamLink(false);
    }
}

function copyPredefinedKey() {
    showToast("Xtream Key එක Server-Side Encrypted Vault මඟින් 100% සුරක්ෂිතයි.");
}

function showToast(msg) {
    let t = document.getElementById('studioToast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'studioToast';
        t.className = 'studio-toast';
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('visible');
    setTimeout(() => {
        t.classList.remove('visible');
    }, 3000);
}

function insertSample(type) {
    if (type === 'promo') {
        adTextInput.value = "මෙම හෝරාව ඔබ වෙත ගෙන එන්නේ සිලෝන් ට්‍රේඩර්ස් ආයතනයයි. විශේෂ වට්ටම් සඳහා අදම පිවිසෙන්න!";
        if (adLangSelect) adLangSelect.value = 'si';
    } else if (type === 'wishes') {
        adTextInput.value = "අපගේ සියලුම ශ්‍රාවක යහළු යෙහෙළියන්ට සුබම සුබ දවසක් වේවා!";
        if (adLangSelect) adLangSelect.value = 'si';
    } else if (type === 'radio') {
        adTextInput.value = "ඔබ ශ්‍රවණය කරන්නේ අන්තර්ජාලය ඔස්සේ ලොව පුරා විකාශනය වන ඔබේ ආදරණීය රේඩියෝවයි. දිගටම රැඳී සිටින්න!";
        if (adLangSelect) adLangSelect.value = 'si';
    }
}

async function playPreRenderedDrop(clipId) {
    adFeedback.className = "fixed-feedback loading";
    adFeedback.textContent = "Broadcasting studio real-girl RJ voice drop (Ducking active)...";
    try {
        const res = await fetch('/api/voice/prerendered/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clip: clipId })
        });
        const data = await res.json();
        if (res.ok) {
            adFeedback.className = "fixed-feedback success";
            adFeedback.textContent = `Live On Air: ${data.title}`;
        } else {
            adFeedback.className = "fixed-feedback error";
            adFeedback.textContent = data.detail || "Error broadcasting clip";
        }
    } catch (e) {
        adFeedback.className = "fixed-feedback error";
        adFeedback.textContent = "Network error triggering voice drop";
    }
}

// ==========================================
// 2. DJ MIXER CONTROLS & SFX SOUNDBOARD
// ==========================================
function triggerSfx(sfxName) {
    // 1. Play local acoustic preview for the DJ with Web Audio
    try {
        const audio = new Audio(`/static/../api/dj/sfx?name=${sfxName}`);
    } catch(e) {}

    // Visual button flash animation
    const pad = document.querySelector(`.pad-${sfxName}`);
    if (pad) {
        pad.classList.add('flash');
        setTimeout(() => pad.classList.remove('flash'), 250);
    }

    // 2. Transmit to master broadcast stream
    fetch('/api/dj/sfx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sfx: sfxName })
    }).catch(err => console.error("SFX trigger error:", err));
}

function onManualCrossfade(val) {
    isUserDraggingCrossfader = true;
    const pos = parseFloat(val) / 100.0;
    fetch('/api/dj/crossfade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pos: pos })
    }).catch(e => console.error("Crossfade error:", e));
    
    setTimeout(() => { isUserDraggingCrossfader = false; }, 1000);
}

function snapCrossfade(val) {
    manualCrossfader.value = val;
    onManualCrossfade(val);
}

function autoCrossfade() {
    // Reset to auto equal-power crossfading
    fetch('/api/dj/crossfade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pos: null })
    }).then(() => {
        crossfadeStatusLabel.textContent = "Auto Crossfading...";
        fetch('/api/control/skip', { method: 'POST' });
        setTimeout(fetchStatus, 500);
    });
}

function setGain(deck, val) {
    fetch('/api/dj/deck/gain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck: deck, gain: parseFloat(val) })
    }).catch(e => console.error("Gain error:", e));
}

function toggleMute(deck) {
    fetch('/api/dj/deck/mute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck: deck })
    }).then(res => res.json()).then(data => {
        const btn = deck.toUpperCase() === 'A' ? deckAMuteBtn : deckBMuteBtn;
        if (data.is_muted) btn.classList.add('active');
        else btn.classList.remove('active');
    });
}

// ==========================================
// AI VOICE VOLUME CONTROL
// ==========================================
let _voiceGainDebounce = null;

function onVoiceGainChange(val) {
    window._voiceSliderTouched = true;
    const display = document.getElementById('voiceGainDisplay');
    if (display) display.textContent = `${val}%`;
    localStorage.setItem('radio4dm_voice_gain', val);

    clearTimeout(_voiceGainDebounce);
    _voiceGainDebounce = setTimeout(async () => {
        try {
            await fetch('/api/control/voice-gain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gain: parseFloat(val) / 100.0 })
            });
        } catch (e) {
            console.warn("Error updating voice gain:", e);
        }
    }, 150);
}

function resetVoiceGain() {
    const slider = document.getElementById('voiceGainSlider');
    if (slider) {
        slider.value = 100;
        onVoiceGainChange(100);
    }
}

function updateOnAirUI(isOnAir) {
    const btn = document.getElementById('masterOnAirBtn');
    const btnText = document.getElementById('masterOnAirBtnText');
    const headerBadge = document.getElementById('headerLiveBadge');
    const dot = document.getElementById('onAirDot');
    const label = document.getElementById('onAirStatusLabel');

    if (isOnAir) {
        if (btn) {
            btn.className = 'btn-on-air-master';
            btn.title = 'Master is ON AIR. Click to Switch OFF AIR';
        }
        if (btnText) btnText.textContent = 'ON AIR';
        if (headerBadge) {
            headerBadge.className = 'badge-live';
            headerBadge.textContent = 'ON AIR';
        }
        if (dot) dot.className = 'pulsing-dot';
        if (label) {
            label.textContent = 'MASTER ON AIR';
            label.style.color = 'var(--accent-red)';
        }
    } else {
        if (btn) {
            btn.className = 'btn-on-air-master offair';
            btn.title = 'Master is OFF AIR. Click to GO LIVE (ON AIR)';
        }
        if (btnText) btnText.textContent = 'OFF AIR';
        if (headerBadge) {
            headerBadge.className = 'badge-live offair';
            headerBadge.textContent = 'OFF AIR';
        }
        if (dot) dot.className = 'pulsing-dot offair';
        if (label) {
            label.textContent = 'MASTER OFF AIR';
            label.style.color = '#9ca3af';
        }
    }
}

async function toggleMasterOnAir() {
    try {
        const res = await fetch('/api/control/on-air', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        updateOnAirUI(data.on_air);
        fetchStatus();
    } catch (e) {
        console.error("Toggle on-air error:", e);
    }
}

// Queue item delete & clear
async function deleteQueueItem(trackId) {
    try {
        await fetch(`/api/queue/${trackId}`, { method: 'DELETE' });
        fetchStatus();
    } catch (e) {
        console.error("Delete track error:", e);
    }
}

async function makeNextQueueItem(trackId) {
    try {
        await fetch('/api/queue/play-next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ track_id: trackId })
        });
        fetchStatus();
    } catch (e) {
        console.error("Make next track error:", e);
    }
}

async function playNowQueueItem(trackId) {
    showToast("2nd Deck එකට Cue කරමින් පවතී... Fade In වෙමින් ඇත 🎧");
    try {
        await fetch('/api/queue/play-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ track_id: trackId })
        });
        setTimeout(fetchStatus, 300);
    } catch (e) {
        console.error("Play now track error:", e);
    }
}

async function moveQueueItem(trackId, direction) {
    try {
        await fetch('/api/queue/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ track_id: trackId, direction: direction })
        });
        fetchStatus();
    } catch (e) {
        console.error("Move track error:", e);
    }
}

async function triggerStationTagline() {
    const select = document.getElementById('taglineAccentSelect');
    const taglineId = select ? select.value : 'random';
    const feedback = document.getElementById('taglineFeedback');
    const btn = document.getElementById('playTaglineBtn');

    if (btn) btn.disabled = true;
    if (feedback) {
        feedback.className = "fixed-feedback loading";
        feedback.textContent = "Broadcasting Radio 4DM Station Tagline with DJ ducking...";
    }

    try {
        const res = await fetch('/api/tagline/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tagline_id: taglineId === 'random' ? null : taglineId })
        });
        const data = await res.json();
        if (res.ok) {
            if (feedback) {
                feedback.className = "fixed-feedback success";
                feedback.textContent = `On Air: ${data.title || "Radio 4DM Tagline"}`;
            }
            fetchStatus();
        } else {
            if (feedback) {
                feedback.className = "fixed-feedback error";
                feedback.textContent = data.detail || "Tagline broadcast failed";
            }
        }
    } catch (e) {
        if (feedback) {
            feedback.className = "fixed-feedback error";
            feedback.textContent = "Network error broadcasting tagline.";
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function clearQueue() {
    if (!confirm("Clear all upcoming songs from queue?")) return;
    try {
        await fetch('/api/queue', { method: 'DELETE' });
        fetchStatus();
    } catch (e) {
        console.error("Clear queue error:", e);
    }
}

// ==========================================
// 3. LIVE RADIO STREAM PLAYER
// ==========================================
let streamConnectTimeout = null;

let isStreamManuallyPaused = false;
let autoReconnectTimer = null;

function resetPlayerUI(statusMsg) {
    if (streamConnectTimeout) {
        clearTimeout(streamConnectTimeout);
        streamConnectTimeout = null;
    }
    isPlaying = false;
    isConnecting = false;
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i> Listen Live';
    playBtn.className = 'btn btn-primary btn-play';
    masterDeckCard.classList.remove('playing');
    playerStatusTip.className = "fixed-status-line";
    playerStatusTip.textContent = statusMsg || "Audio paused. Click Listen Live to connect.";
}

function setPlayerPlayingUI() {
    if (streamConnectTimeout) {
        clearTimeout(streamConnectTimeout);
        streamConnectTimeout = null;
    }
    isConnecting = false;
    isPlaying = true;
    isStreamManuallyPaused = false;
    playBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause Audio';
    playBtn.className = 'btn btn-secondary btn-play';
    masterDeckCard.classList.add('playing');
    playerStatusTip.className = "fixed-status-line active";
    playerStatusTip.textContent = "Live Broadcast connected (Pro DJ Dual-Deck Stream).";
}

function handleStreamHiccup(eventReason) {
    if (isStreamManuallyPaused || (!isPlaying && !isConnecting)) return;
    if (autoReconnectTimer) return;
    console.warn(`[Audio Watchdog] Stream interrupted (${eventReason}). Auto-reconnecting...`);
    playerStatusTip.className = "fixed-status-line loading";
    playerStatusTip.textContent = "Reconnecting master broadcast...";
    autoReconnectTimer = setTimeout(() => {
        autoReconnectTimer = null;
        if (isStreamManuallyPaused) return;
        radioAudio.src = `/stream?_t=${Date.now()}`;
        radioAudio.play().then(setPlayerPlayingUI).catch(e => {
            console.warn("[Audio Watchdog] Reconnect retry error:", e);
        });
    }, 1200);
}

playBtn.addEventListener('click', () => {
    // If playing or connecting, allow clicking to pause/cancel
    if (isPlaying || isConnecting) {
        isStreamManuallyPaused = true;
        radioAudio.pause();
        radioAudio.removeAttribute('src');
        radioAudio.load();
        resetPlayerUI("Audio paused. Click Listen Live to resume.");
        return;
    }

    isStreamManuallyPaused = false;
    isConnecting = true;
    playBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Connecting...';
    playBtn.className = 'btn btn-secondary btn-play';
    playerStatusTip.className = "fixed-status-line loading";
    playerStatusTip.textContent = "Connecting to master live stream (Ultra-low latency)...";

    // Set src with cache-busting timestamp
    radioAudio.src = `/stream?_t=${Date.now()}`;

    // Safety timeout: if browser is still connecting after 6s, auto-retry or reset
    streamConnectTimeout = setTimeout(() => {
        if (isConnecting && !isPlaying) {
            console.warn("Live stream connection took too long, retrying...");
            radioAudio.load();
            radioAudio.play().then(setPlayerPlayingUI).catch(() => {
                resetPlayerUI("Connection slow. Click Listen Live to retry.");
            });
        }
    }, 6000);

    const playPromise = radioAudio.play();
    if (playPromise !== undefined) {
        playPromise.then(() => {
            setPlayerPlayingUI();
        }).catch((err) => {
            console.warn("Audio autoplay policy or stream buffering:", err);
            setTimeout(() => {
                if (isConnecting && !isPlaying && !isStreamManuallyPaused) {
                    radioAudio.play().then(setPlayerPlayingUI).catch(() => {
                        resetPlayerUI("Click Listen Live to connect audio.");
                    });
                }
            }, 300);
        });
    }
});

radioAudio.addEventListener('playing', () => {
    isStreamManuallyPaused = false;
    setPlayerPlayingUI();
});
radioAudio.addEventListener('canplay', () => {
    if (isConnecting && !isPlaying && !isStreamManuallyPaused) {
        radioAudio.play().then(setPlayerPlayingUI).catch(() => {});
    }
});
radioAudio.addEventListener('error', (e) => {
    console.warn("Audio element error event:", e);
    handleStreamHiccup('error');
});
radioAudio.addEventListener('ended', () => handleStreamHiccup('ended'));
radioAudio.addEventListener('stalled', () => {
    // Only reconnect if stream is genuinely paused and stalled (never interrupt while playing!)
    if (radioAudio.paused && isPlaying) {
        handleStreamHiccup('stalled_paused');
    }
});

// 5-second resilient watchdog: keeps playing continuously even on mobile sleep or network switch
setInterval(() => {
    if (isPlaying && !isConnecting && !isStreamManuallyPaused && radioAudio.paused) {
        handleStreamHiccup('watchdog_paused');
    }
}, 5000);

// Volume Control
volumeSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    radioAudio.volume = val;
    if (val === 0) {
        volumeIcon.className = "fa-solid fa-volume-xmark";
    } else if (val < 0.5) {
        volumeIcon.className = "fa-solid fa-volume-low";
    } else {
        volumeIcon.className = "fa-solid fa-volume-high";
    }
});

// DJ Smooth Crossfade Skip Track
skipBtn.addEventListener('click', async () => {
    try {
        crossfadeStatusLabel.textContent = "DJ Crossfading...";
        await fetch('/api/control/skip', { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Skip error:", e);
    }
});

// Load Hit Charts (Strict Deduplication in backend)
async function loadChart(chartType) {
    chartFeedback.className = "fixed-feedback loading";
    chartFeedback.textContent = `Queueing unique ${chartType.toUpperCase()} hits into DJ deck...`;

    try {
        const res = await fetch('/api/charts/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chart: chartType, count: 5 })
        });
        const data = await res.json();
        if (res.ok) {
            chartFeedback.className = "fixed-feedback success";
            chartFeedback.textContent = data.message;
            setTimeout(fetchStatus, 1500);
        } else {
            chartFeedback.className = "fixed-feedback error";
            chartFeedback.textContent = data.detail || "Failed to load chart.";
        }
    } catch (err) {
        chartFeedback.className = "fixed-feedback error";
        chartFeedback.textContent = "Failed to load chart.";
    }
}

async function loadRandomSingleTrack() {
    chartFeedback.className = "fixed-feedback loading";
    chartFeedback.textContent = "Selecting a surprise random hit from 90+ song library...";

    try {
        const res = await fetch('/api/queue/random', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            chartFeedback.className = "fixed-feedback success";
            chartFeedback.textContent = data.message;
            setTimeout(fetchStatus, 1500);
        } else {
            chartFeedback.className = "fixed-feedback error";
            chartFeedback.textContent = data.message || "Failed to queue random track.";
        }
    } catch (err) {
        chartFeedback.className = "fixed-feedback error";
        chartFeedback.textContent = "Failed to queue random track.";
    }
}

let currentSearchResults = [];

function closeSearchResults() {
    const box = document.getElementById('searchResultsBox');
    if (box) box.style.display = 'none';
}

async function addDirectSearchResult(index) {
    const track = currentSearchResults[index];
    if (!track) return;
    
    ytFeedback.className = "fixed-feedback loading";
    ytFeedback.textContent = `Adding "${track.title}" to standby queue...`;
    
    try {
        const res = await fetch('/api/queue/add-direct', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(track)
        });
        const data = await res.json();
        if (res.ok) {
            ytFeedback.className = "fixed-feedback success";
            ytFeedback.textContent = `Queued: ${data.track.title} (${data.track.duration_str})`;
            fetchStatus();
        } else {
            ytFeedback.className = "fixed-feedback error";
            ytFeedback.textContent = data.detail || "Track already in queue";
        }
    } catch (err) {
        ytFeedback.className = "fixed-feedback error";
        ytFeedback.textContent = "Error adding track.";
    }
}

// Queue YouTube / Online Track or Search Candidate
youtubeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = ytUrlInput.value.trim();
    if (!query) return;

    const isUrl = /^https?:\/\//i.test(query);

    addYtBtn.disabled = true;
    ytFeedback.className = "fixed-feedback loading";

    if (isUrl) {
        ytFeedback.textContent = "Linking direct YouTube / SoundCloud stream...";
        try {
            const res = await fetch('/api/queue/youtube', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: query })
            });
            const data = await res.json();
            if (res.ok) {
                ytFeedback.className = "fixed-feedback success";
                ytFeedback.textContent = `Queued: ${data.track.title} (${data.track.duration_str || 'Full Track'})`;
                ytUrlInput.value = "";
                closeSearchResults();
                fetchStatus();
            } else {
                ytFeedback.className = "fixed-feedback error";
                ytFeedback.textContent = `${data.detail || "Failed to add song"}`;
            }
        } catch (err) {
            ytFeedback.className = "fixed-feedback error";
            ytFeedback.textContent = "Network error. Please try again.";
        } finally {
            addYtBtn.disabled = false;
        }
    } else {
        // Universal Search query: search online catalog and return top matching candidate tracks
        ytFeedback.textContent = `Searching online catalog for "${query}"...`;
        try {
            const res = await fetch('/api/search/tracks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, limit: 4 })
            });
            const data = await res.json();
            if (res.ok && data.results && data.results.length > 0) {
                currentSearchResults = data.results;
                const box = document.getElementById('searchResultsBox');
                const list = document.getElementById('searchResultsList');

                // Render matching tracks with individual +Queue buttons
                list.innerHTML = data.results.map((t, idx) => `
                    <div class="search-item">
                        <div class="search-item-info">
                            <div class="search-item-title" title="${t.title}">${t.title}</div>
                            <div class="search-item-meta">${t.uploader} • ⏱️ ${t.duration_str}</div>
                        </div>
                        <div class="search-item-actions">
                            <button type="button" class="btn-search-add" onclick="addDirectSearchResult(${idx})" title="Add to Standby Queue">
                                <i class="fa-solid fa-plus"></i> Queue
                            </button>
                        </div>
                    </div>
                `).join('');
                box.style.display = 'block';

                // Automatically queue the #1 top hit immediately
                await addDirectSearchResult(0);
                ytUrlInput.value = "";
            } else {
                ytFeedback.className = "fixed-feedback error";
                ytFeedback.textContent = `No tracks found matching "${query}". Try another title.`;
                closeSearchResults();
            }
        } catch (err) {
            ytFeedback.className = "fixed-feedback error";
            ytFeedback.textContent = "Search error. Please try again.";
        } finally {
            addYtBtn.disabled = false;
        }
    }
});

// Broadcast AI Ad
adForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = adTextInput.value.trim();
    if (!text) return;

    broadcastAdBtn.disabled = true;
    adFeedback.className = "fixed-feedback loading";
    adFeedback.textContent = "Synthesizing AI Human Voice & Ducking Music...";

    try {
        const res = await fetch('/api/ad/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                lang: adLangSelect ? adLangSelect.value : "si",
                provider: adProviderSelect.value,
                voice: adVoiceSelect.value,
                immediate: true
            })
        });
        const data = await res.json();

        if (res.ok) {
            adFeedback.className = "fixed-feedback success";
            adFeedback.textContent = "AI Advertisement broadcasting over dimmed music!";
            fetchStatus();
        } else {
            adFeedback.className = "fixed-feedback error";
            adFeedback.textContent = `Error: ${data.detail || "TTS failed"}`;
        }
    } catch (err) {
        adFeedback.className = "fixed-feedback error";
        adFeedback.textContent = "Network error while sending ad.";
    } finally {
        broadcastAdBtn.disabled = false;
    }
});

// Test Hourly Time Broadcast
testTimeBtn.addEventListener('click', async () => {
    testTimeBtn.disabled = true;
    timeStatusMsg.textContent = "Broadcasting AI Human Time Cast...";

    try {
        const res = await fetch('/api/time/trigger', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            timeStatusMsg.textContent = `Broadcasted: "${data.text}"`;
            fetchStatus();
        }
    } catch (err) {
        timeStatusMsg.textContent = "Error broadcasting time.";
    } finally {
        setTimeout(() => {
            testTimeBtn.disabled = false;
            timeStatusMsg.textContent = "";
        }, 5000);
    }
});

async function triggerColomboWeatherNow() {
    const btn = document.getElementById('testWeatherBtn');
    if (btn) btn.disabled = true;
    if (timeStatusMsg) timeStatusMsg.textContent = "Fetching Colombo live weather & broadcasting RJ speech...";

    try {
        const res = await fetch('/api/weather/broadcast', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            if (timeStatusMsg) timeStatusMsg.textContent = `Colombo Weather Broadcasted!`;
            fetchStatus();
        }
    } catch (err) {
        if (timeStatusMsg) timeStatusMsg.textContent = "Error broadcasting weather.";
    } finally {
        setTimeout(() => {
            if (btn) btn.disabled = false;
            if (timeStatusMsg) timeStatusMsg.textContent = "";
        }, 5000);
    }
}

// Toggles
if (schedulerToggle) {
    schedulerToggle.addEventListener('change', async (e) => {
        fetch('/api/time/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: e.target.checked })
        }).catch(e => console.error(e));
    });
}

if (newsSchedulerToggle) {
    newsSchedulerToggle.addEventListener('change', async (e) => {
        fetch('/api/news/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: e.target.checked })
        }).catch(e => console.error(e));
    });
}

if (autoDjToggle) {
    autoDjToggle.addEventListener('change', async (e) => {
        fetch('/api/autodj/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: e.target.checked })
        }).catch(e => console.error(e));
    });
}

// Ada Derana Live Breaking News Actions
async function refreshAdaDeranaNews() {
    if (!newsHeadlineText) return;
    try {
        const res = await fetch('/api/news/latest');
        if (res.ok) {
            const data = await res.json();
            const newsObj = data.news || data;
            if (newsObj && newsObj.headline) {
                newsHeadlineText.textContent = newsObj.headline;
                newsHeadlineText.title = newsObj.body || newsObj.headline;
            }
        }
    } catch (err) {
        console.warn("Could not fetch latest Quick news:", err);
    }
}

async function triggerNewsBroadcastNow() {
    if (broadcastNewsBtn) broadcastNewsBtn.disabled = true;
    if (newsStatusMsg) {
        newsStatusMsg.className = "status-tip loading";
        newsStatusMsg.textContent = "Fetching news & generating Gemini RJ voice...";
    }
    try {
        const res = await fetch('/api/news/trigger', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            if (newsStatusMsg) {
                newsStatusMsg.className = "status-tip active";
                newsStatusMsg.textContent = `On Air: "${data.headline || 'Radio Four D M Quick News'}"`;
            }
            if (data.headline && newsHeadlineText) {
                newsHeadlineText.textContent = data.headline;
            }
            fetchStatus();
        } else {
            if (newsStatusMsg) {
                newsStatusMsg.className = "status-tip";
                newsStatusMsg.textContent = data.detail || "Failed to broadcast news";
            }
        }
    } catch (err) {
        if (newsStatusMsg) {
            newsStatusMsg.className = "status-tip";
            newsStatusMsg.textContent = "Network error broadcasting news.";
        }
    } finally {
        setTimeout(() => {
            if (broadcastNewsBtn) broadcastNewsBtn.disabled = false;
        }, 5000);
    }
}

// Settings Modal
function openSettingsModal() {
    if (!settingsModal) return;
    settingsModal.style.display = 'flex';
    settingsModal.classList.add('show');
    fetch('/api/config')
        .then(res => res.json())
        .then(cfg => {
            if (modalGeminiKey) modalGeminiKey.value = cfg.gemini_api_key || "";
            if (modalCrossfadeSec) modalCrossfadeSec.value = cfg.crossfade_seconds || 6;
            if (modalDuckingVol) modalDuckingVol.value = cfg.ducking_volume || 0.18;
        }).catch(err => {
            console.warn("Could not fetch config:", err);
        });
}

function closeSettingsModal() {
    if (!settingsModal) return;
    settingsModal.style.display = 'none';
    settingsModal.classList.remove('show');
}

// Close when clicking on backdrop
window.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        closeSettingsModal();
    }
});

// Close with Escape key
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && settingsModal && settingsModal.classList.contains('show')) {
        closeSettingsModal();
    }
});

function toggleGeminiKeyVisibility() {
    if (!geminiQuickKeyInput) return;
    if (geminiQuickKeyInput.type === "password") {
        geminiQuickKeyInput.type = "text";
        if (geminiEyeIcon) {
            geminiEyeIcon.classList.remove('fa-eye');
            geminiEyeIcon.classList.add('fa-eye-slash');
        }
    } else {
        geminiQuickKeyInput.type = "password";
        if (geminiEyeIcon) {
            geminiEyeIcon.classList.remove('fa-eye-slash');
            geminiEyeIcon.classList.add('fa-eye');
        }
    }
}

async function checkGeminiStatus() {
    try {
        const res = await fetch('/api/config/gemini-status');
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.valid) {
            if (geminiLiveStatusBadge) {
                geminiLiveStatusBadge.className = "badge-gemini-status online";
                geminiLiveStatusBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Gemini AI Active`;
                geminiLiveStatusBadge.title = `Gemini AI is verified and linked (${data.masked_key})`;
            }
            if (geminiQuickStatus) {
                geminiQuickStatus.className = "gemini-status-text ok";
                geminiQuickStatus.innerHTML = `✅ Gemini Active & Verified (${data.masked_key})`;
            }
            const codeEl = document.getElementById('predefinedKeyText');
            if (codeEl) {
                codeEl.innerHTML = `<i class="fa-solid fa-shield-halved" style="color: #10b981;"></i> Active: ${data.masked_key}`;
            }
            if (geminiQuickKeyInput && !geminiQuickKeyInput.value) {
                geminiQuickKeyInput.placeholder = `Active Key: ${data.masked_key} (Paste new key to change)`;
            }
            if (modalGeminiKey && !modalGeminiKey.value) {
                modalGeminiKey.placeholder = `Active Key: ${data.masked_key}`;
            }
        } else {
            if (geminiLiveStatusBadge) {
                geminiLiveStatusBadge.className = "badge-gemini-status offline";
                geminiLiveStatusBadge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Not Linked (Fallback)`;
                geminiLiveStatusBadge.title = data.message || "Gemini key not valid";
            }
            if (geminiQuickStatus) {
                geminiQuickStatus.className = "gemini-status-text warn";
                geminiQuickStatus.innerHTML = `⚠️ Gemini Key සම්බන්ධ වී නැත (Edge-TTS Backup ක්‍රියාත්මකයි). කරුණාකර aistudio.google.com යතුරක් ඇතුළත් කරන්න.`;
            }
        }
    } catch (err) {
        console.warn("Could not check Gemini status:", err);
    }
}

async function verifyAndSaveGeminiKey(silent = false) {
    const rawKey = geminiQuickKeyInput ? geminiQuickKeyInput.value.trim() : "";
    if (!rawKey) {
        if (!silent) alert("කරුණාකර ඔබගේ Google Gemini API Key එක ඇතුළත් කරන්න.\n(Google AI Studio වෙතින් නොමිලේ ලබාගත හැක - AIzaSy... වලින් ආරම්භ වේ)");
        return;
    }

    if (geminiLinkBtn) {
        geminiLinkBtn.disabled = true;
        geminiLinkBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying...`;
    }
    if (geminiQuickStatus) {
        geminiQuickStatus.className = "gemini-status-text";
        geminiQuickStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Google AI සමඟ සම්බන්ධතාවය පරීක්ෂා කෙරේ...`;
    }

    try {
        const res = await fetch('/api/config/verify-gemini', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: rawKey })
        });
        const data = await res.json();
        
        if (data.valid) {
            showToast(`🎉 Google Gemini AI සාර්ථකව සම්බන්ධ විය! (${data.masked_key})`);
            if (geminiQuickKeyInput) geminiQuickKeyInput.value = "";
            await checkGeminiStatus();
        } else {
            const errReason = data.detail || "Authentication Failed";
            if (!silent) {
                showToast(`❌ Key Error: ${errReason.substring(0, 80)}`);
            }
            if (geminiQuickStatus) {
                geminiQuickStatus.className = "gemini-status-text warn";
                geminiQuickStatus.innerHTML = `❌ Key Error: ${errReason.substring(0, 80)}`;
            }
            if (geminiLiveStatusBadge) {
                geminiLiveStatusBadge.className = "badge-gemini-status offline";
                geminiLiveStatusBadge.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> Invalid Key`;
            }
        }
    } catch (e) {
        if (!silent) showToast("Server error: " + e.message);
    } finally {
        if (geminiLinkBtn) {
            geminiLinkBtn.disabled = false;
            geminiLinkBtn.innerHTML = `<i class="fa-solid fa-plug-circle-bolt"></i> Link & Test`;
        }
    }
}
            geminiLinkBtn.innerHTML = `<i class="fa-solid fa-plug-circle-bolt"></i> Link & Test`;
        }
    }
}

async function saveStudioSettings() {
    const rawGemini = modalGeminiKey ? modalGeminiKey.value.trim() : "";
    if (rawGemini) {
        try {
            const vRes = await fetch('/api/config/verify-gemini', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: rawGemini })
            });
            const vData = await vRes.json();
            if (!vData.valid) {
                alert(`❌ Gemini API Key දෝෂයකි:\n${vData.detail || 'Invalid Key'}\nකරුණාකර aistudio.google.com යතුරක් යොදන්න.`);
                return;
            }
        } catch (e) {
            console.warn("Verify error:", e);
        }
    }

    const payload = {
        tts_provider: "gemini",
        crossfade_seconds: parseInt(modalCrossfadeSec ? modalCrossfadeSec.value : 6) || 6,
        ducking_volume: parseFloat(modalDuckingVol ? modalDuckingVol.value : 0.18) || 0.18
    };
    if (rawGemini) payload.gemini_api_key = rawGemini;

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeSettingsModal();
            alert("Settings saved successfully!");
            checkGeminiStatus();
        }
    } catch (err) {
        alert("Error saving settings.");
    }
}

// Helpers
function formatSeconds(sec) {
    if (!sec || isNaN(sec)) return "00:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ==========================================
// 4. POLL STATUS & PRO DJ MIXER VISUALIZER
// ==========================================
async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();

        listenerCount.textContent = data.listeners || 0;

        // Master ON AIR state sync
        if (data.is_on_air !== undefined) {
            updateOnAirUI(data.is_on_air);
        }

        // Update Track Info
        if (data.current_track) {
            nowPlayingTitle.textContent = data.current_track.title || "Unknown Title";
            nowPlayingTitle.title = data.current_track.title || "";
            nowPlayingUploader.textContent = data.current_track.uploader || "Radio Stream";
            
            if (data.voice_active) {
                trackTypeBadge.textContent = "VOICEOVER (DUCKING)";
                trackTypeBadge.className = "track-badge ad";
            } else {
                const tType = data.current_track.type || "music";
                trackTypeBadge.textContent = tType.toUpperCase();
                trackTypeBadge.className = `track-badge ${tType}`;
            }
        } else {
            nowPlayingTitle.textContent = "Radio 4DM Live Broadcast Ready...";
            nowPlayingUploader.textContent = "Radio 4DM Broadcast Server";
            trackTypeBadge.textContent = "IDLE";
            trackTypeBadge.className = "track-badge music";
        }

        // Helper to update VU meter LEDs dynamically
        function updateVuMeterLeds(vuContainer, isActive, volume, rmsDb) {
            if (!vuContainer) return;
            const leds = vuContainer.querySelectorAll('.vu-led');
            if (!isActive || volume <= 0.01) {
                leds.forEach(led => led.classList.remove('lit'));
                return;
            }
            let litCount = 0;
            if (rmsDb !== undefined && rmsDb > -60) {
                const norm = Math.max(0, Math.min(1, (rmsDb + 42) / 38));
                litCount = Math.round(norm * volume * 7);
            } else {
                litCount = Math.round(volume * 5);
            }
            if (Math.random() > 0.4 && litCount < 7) litCount += 1;
            litCount = Math.max(1, Math.min(7, litCount));

            // Indices: 0 is top (red), 6 is bottom (green)
            leds.forEach((led, idx) => {
                const rankFromBottom = 7 - idx;
                if (rankFromBottom <= litCount) {
                    led.classList.add('lit');
                } else {
                    led.classList.remove('lit');
                }
            });
        }

        // Update Deck A Live Turntable & VU Meter
        const vinylA = document.getElementById('vinylPlatterA');
        const tonearmA = document.getElementById('tonearmA');
        const pillA = document.getElementById('deckAOnAirPill');
        const vuMeterA = document.getElementById('deckAVuMeter');
        const progressBarA = document.getElementById('deckAProgressBar');
        const channelA = document.getElementById('deckChannelA');

        if (data.deck_a) {
            deckATitle.textContent = data.deck_a.track || "Deck A Idle";
            deckATitle.title = data.deck_a.track || "";
            const cappedDurA = Math.min(data.deck_a.duration || 360, 360);
            deckATime.textContent = `${formatSeconds(data.deck_a.elapsed)} / ${formatSeconds(cappedDurA)} (Max 06:00)`;

            const isAActive = data.deck_a.active && data.deck_a.volume > 0.05 && !data.deck_a.muted;
            if (isAActive) {
                deckABadge.classList.add('active');
                if (channelA) channelA.classList.add('on-air');
                if (vinylA) vinylA.classList.add('spinning');
                if (tonearmA) tonearmA.classList.add('active');
                if (pillA) pillA.classList.add('active');
            } else {
                deckABadge.classList.remove('active');
                if (channelA) channelA.classList.remove('on-air');
                if (vinylA) vinylA.classList.remove('spinning');
                if (tonearmA) tonearmA.classList.remove('active');
                if (pillA) pillA.classList.remove('active');
            }

            // Progress bar
            if (progressBarA && cappedDurA > 0) {
                const pctA = Math.min(100, Math.max(0, (data.deck_a.elapsed / cappedDurA) * 100));
                progressBarA.style.width = `${pctA}%`;
            }

            // VU Meter
            updateVuMeterLeds(vuMeterA, isAActive, data.deck_a.volume, data.deck_a.rms_db);

            if (data.deck_a.muted) deckAMuteBtn.classList.add('active');
            else deckAMuteBtn.classList.remove('active');
        }

        // Update Deck B Live Turntable & VU Meter
        const vinylB = document.getElementById('vinylPlatterB');
        const tonearmB = document.getElementById('tonearmB');
        const pillB = document.getElementById('deckBOnAirPill');
        const vuMeterB = document.getElementById('deckBVuMeter');
        const progressBarB = document.getElementById('deckBProgressBar');
        const channelB = document.getElementById('deckChannelB');

        if (data.deck_b) {
            deckBTitle.textContent = data.deck_b.track || "Deck B Idle";
            deckBTitle.title = data.deck_b.track || "";
            const cappedDurB = Math.min(data.deck_b.duration || 360, 360);
            deckBTime.textContent = `${formatSeconds(data.deck_b.elapsed)} / ${formatSeconds(cappedDurB)} (Max 06:00)`;

            const isBActive = data.deck_b.active && data.deck_b.volume > 0.05 && !data.deck_b.muted;
            if (isBActive) {
                deckBBadge.classList.add('active');
                if (channelB) channelB.classList.add('on-air');
                if (vinylB) vinylB.classList.add('spinning');
                if (tonearmB) tonearmB.classList.add('active');
                if (pillB) pillB.classList.add('active');
            } else {
                deckBBadge.classList.remove('active');
                if (channelB) channelB.classList.remove('on-air');
                if (vinylB) vinylB.classList.remove('spinning');
                if (tonearmB) tonearmB.classList.remove('active');
                if (pillB) pillB.classList.remove('active');
            }

            // Progress bar
            if (progressBarB && cappedDurB > 0) {
                const pctB = Math.min(100, Math.max(0, (data.deck_b.elapsed / cappedDurB) * 100));
                progressBarB.style.width = `${pctB}%`;
            }

            // VU Meter
            updateVuMeterLeds(vuMeterB, isBActive, data.deck_b.volume, data.deck_b.rms_db);

            if (data.deck_b.muted) deckBMuteBtn.classList.add('active');
            else deckBMuteBtn.classList.remove('active');
        }

        // Update Crossfader Slider position (only if user isn't actively dragging it)
        if (!isUserDraggingCrossfader && data.deck_a && data.deck_b) {
            const volA = data.deck_a.volume;
            const volB = data.deck_b.volume;
            const total = volA + volB;
            let percentB = 0;
            if (total > 0) {
                percentB = Math.round((volB / total) * 100);
            } else if (data.deck_b.active) {
                percentB = 100;
            }
            manualCrossfader.value = percentB;

            if (volA > 0.1 && volB > 0.1) {
                crossfadeStatusLabel.textContent = `DJ Crossfade (${Math.round(volA*100)}% / ${Math.round(volB*100)}%)`;
            } else {
                crossfadeStatusLabel.textContent = "Gapless Equal-Power";
            }
        }

        // Update Toggles
        // Master Stereo VU Meters Update
        const masterLeft = document.getElementById('masterVuLeft');
        const masterRight = document.getElementById('masterVuRight');
        if (masterLeft && masterRight) {
            const isAnyActive = (data.deck_a && data.deck_a.active && data.deck_a.volume > 0.05) ||
                                (data.deck_b && data.deck_b.active && data.deck_b.volume > 0.05);
            const maxVol = Math.max(data.deck_a ? data.deck_a.volume : 0, data.deck_b ? data.deck_b.volume : 0);
            const maxRms = Math.max(data.deck_a ? data.deck_a.rms_db : -60, data.deck_b ? data.deck_b.rms_db : -60);
            updateVuMeterLeds(masterLeft, isAnyActive, maxVol, maxRms);
            updateVuMeterLeds(masterRight, isAnyActive, maxVol, maxRms);
        }

        if (schedulerToggle && data.scheduler_enabled !== undefined) {
            schedulerToggle.checked = !!data.scheduler_enabled;
        }
        if (newsSchedulerToggle && data.news_scheduler_enabled !== undefined) {
            newsSchedulerToggle.checked = !!data.news_scheduler_enabled;
        }
        const cricketToggle = document.getElementById('cricketSchedulerToggle');
        if (cricketToggle && data.cricket_scheduler_enabled !== undefined) {
            cricketToggle.checked = !!data.cricket_scheduler_enabled;
        }
        if (autoDjToggle && data.autodj_enabled !== undefined) {
            autoDjToggle.checked = !!data.autodj_enabled;
        }

        const voiceSlider = document.getElementById('voiceGainSlider');
        const voiceDisplay = document.getElementById('voiceGainDisplay');
        if (voiceSlider && data.voice_gain_pct !== undefined && !window._voiceSliderTouched) {
            voiceSlider.value = data.voice_gain_pct;
            if (voiceDisplay) voiceDisplay.textContent = `${data.voice_gain_pct}%`;
        }

        // Update 10-Song Standby Playlist (Only re-render DOM when changed to eliminate UI lag!)
        queueCount.textContent = data.playlist ? data.playlist.length : 0;

        // Auto-bootstrap 10 random mixed chart hits (Sinhala, English, Hindi) on initial app open if queue is empty
        if ((!data.playlist || data.playlist.length === 0) && !window._bootstrappedInitialChart) {
            window._bootstrappedInitialChart = true;
            console.log("[AutoDJ] App open: bootstrapping 10 random mixed chart songs across all languages...");
            fetch('/api/charts/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chart: 'mixed', count: 10 })
            }).then(() => setTimeout(fetchStatus, 1500));
        }

        const currentHash = data.playlist ? data.playlist.map(t => `${t.id}_${t.title}`).join('|') : "";
        if (currentHash !== window._lastPlaylistHash) {
            window._lastPlaylistHash = currentHash;
            if (data.playlist && data.playlist.length > 0) {
                playlistContainer.innerHTML = data.playlist.map((track, i) => `
                    <div class="playlist-item ${i === 0 ? 'is-next-track' : ''}">
                        <span style="color:var(--text-muted); font-size:10.5px; font-weight:700; min-width:20px;">#${i+1}</span>
                        <img src="${track.thumbnail || 'https://via.placeholder.com/60'}" class="playlist-thumb" alt="Thumb">
                        <div class="playlist-item-info">
                            <div class="playlist-title" title="${track.title}">
                                ${i === 0 ? '<span class="badge-next">NEXT UP</span>' : ''}${track.title}
                            </div>
                            <div class="playlist-meta">${track.uploader} • ${track.duration_str || '--:--'}</div>
                        </div>
                        <div class="track-action-group">
                            <button class="btn-track-action play-now" onclick="playNowQueueItem('${track.id}')" title="Play Now (Cues into 2nd Deck with Fade In)">
                                <i class="fa-solid fa-play"></i>
                            </button>
                            ${i > 0 ? `
                            <button class="btn-track-action make-next" onclick="makeNextQueueItem('${track.id}')" title="Set as NEXT Song">
                                <i class="fa-solid fa-bolt"></i> Next
                            </button>
                            ` : ''}
                            <button class="btn-track-action move-btn" onclick="moveQueueItem('${track.id}', 'up')" ${i === 0 ? 'disabled' : ''} title="Move Up">
                                <i class="fa-solid fa-arrow-up"></i>
                            </button>
                            <button class="btn-track-action move-btn" onclick="moveQueueItem('${track.id}', 'down')" ${i === data.playlist.length - 1 ? 'disabled' : ''} title="Move Down">
                                <i class="fa-solid fa-arrow-down"></i>
                            </button>
                            <button class="btn-remove-track" onclick="deleteQueueItem('${track.id}')" title="Remove song">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                playlistContainer.innerHTML = `<div class="empty-state">No standby songs queued. Auto-DJ is loading 10 hits...</div>`;
            }
        }

    } catch (err) {
        console.warn("Status poll error:", err);
    }
}

// ==========================================
// 5. CRICBUZZ LIVE CRICKET BILINGUAL ENGINE
// ==========================================
let currentCricketLang = "si";

async function setCricketLanguage(lang) {
    currentCricketLang = lang;
    const btnSi = document.getElementById('cricketLangSi');
    const btnEn = document.getElementById('cricketLangEn');
    if (btnSi && btnEn) {
        if (lang === 'si') {
            btnSi.classList.add('active');
            btnEn.classList.remove('active');
        } else {
            btnEn.classList.add('active');
            btnSi.classList.remove('active');
        }
    }
    try {
        await fetch('/api/cricket/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lang })
        });
    } catch (e) {
        console.warn("Error saving cricket language:", e);
    }
    refreshCricketHighlights();
}

async function toggleCricketScheduler(enabled) {
    try {
        const res = await fetch('/api/cricket/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !!enabled })
        });
        const data = await res.json();
        showToast(`🏏 20-Min Cricbuzz Updates: ${enabled ? 'ON (Only when matches are live)' : 'OFF'}`);
    } catch (e) {
        console.error("Cricket toggle error:", e);
    }
}

async function refreshCricketHighlights() {
    const headline = document.getElementById('cricketHeadline');
    const summary = document.getElementById('cricketSummary');
    const updateTime = document.getElementById('cricketUpdateTime');
    const badge = document.getElementById('cricketLiveBadge');
    const tag = document.getElementById('cricketLiveStatusTag');
    try {
        const res = await fetch(`/api/cricket/latest?lang=${currentCricketLang}`);
        const data = await res.json();
        if (data.status === 'success' && data.cricket) {
            const c = data.cricket;
            if (headline) headline.textContent = c.headline || "Cricbuzz Live Cricket Highlights";
            if (summary) summary.textContent = c.summary || c.script || "Cricbuzz සජීවී දත්ත ලබා ගනිමින් පවතී...";
            if (updateTime) updateTime.textContent = `Updated: ${c.time || 'Just now'}`;

            if (badge) {
                if (c.has_live) {
                    badge.className = "badge-live-cricket";
                    badge.innerHTML = `<i class="fa-solid fa-circle fa-beat" style="color: #10b981; font-size: 0.65rem;"></i> LIVE (${c.matches_count || 1})`;
                } else {
                    badge.className = "badge-live-cricket standby";
                    badge.innerHTML = `<i class="fa-solid fa-pause"></i> STANDBY`;
                }
            }
            if (tag) {
                if (c.has_live) {
                    tag.innerHTML = `<i class="fa-solid fa-bolt"></i> CRICBUZZ LIVE SCORE`;
                    tag.style.background = "rgba(16, 185, 129, 0.2)";
                    tag.style.color = "#34d399";
                } else {
                    tag.innerHTML = `<i class="fa-solid fa-clock"></i> NO LIVE MATCH`;
                    tag.style.background = "rgba(148, 163, 184, 0.2)";
                    tag.style.color = "#94a3b8";
                }
            }
        }
    } catch (e) {
        console.warn("Cricket refresh error:", e);
    }
}

async function broadcastCricketNow() {
    const btn = document.getElementById('broadcastCricketBtn');
    const feedback = document.getElementById('cricketFeedback');
    if (btn) btn.disabled = true;
    if (feedback) {
        feedback.className = "fixed-feedback loading";
        feedback.textContent = `Cricbuzz සජීවී දත්ත ලබාගනිමින් (${currentCricketLang.toUpperCase()}) 20% Ducking සමඟ විකාශය කෙරේ...`;
    }
    try {
        const res = await fetch('/api/cricket/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lang: currentCricketLang })
        });
        if (!res.ok) {
            const errBody = await res.text();
            throw new Error(`Server status ${res.status}: ${errBody}`);
        }
        const data = await res.json();
        if (data.status === 'skipped') {
            if (feedback) {
                feedback.className = "fixed-feedback warning";
                feedback.textContent = data.message || "Cricbuzz හි සජීවී තරග නොමැති බැවින් විකාශය මඟහරින ලදී.";
            }
            showToast("🏏 Cricbuzz: සජීවී තරග ක්‍රියාත්මක නොවන බැවින් විකාශය මඟහරින ලදී.");
        } else if (data.status === 'success') {
            if (feedback) {
                feedback.className = "fixed-feedback success";
                feedback.textContent = `Cricbuzz Live Cricket විකාශය 20% ducking සමඟ සාර්ථකව ආරම්භ විය!`;
            }
            showToast(`🏏 Cricbuzz Live Cricket (${currentCricketLang === 'si' ? 'සිංහල' : 'English'}) Broadcast On-Air!`);
        }
    } catch (e) {
        if (feedback) {
            feedback.className = "fixed-feedback error";
            feedback.textContent = `Broadcast error: ${e.message}`;
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Initial fetch
fetchStatus();
setInterval(fetchStatus, 1500); // 1.5s interval: perfectly smooth, zero UI lag

// Check Gemini AI API status
checkGeminiStatus();
setInterval(checkGeminiStatus, 15000);

// Start Xtream 2-minute auto-countdown & auto-trigger
startXtreamCountdown();

// Ada Derana Live Headline Polling (Every 5 minutes)
refreshAdaDeranaNews();
setInterval(refreshAdaDeranaNews, 300000);

// Initial Cricket Fetch
refreshCricketHighlights();
setInterval(refreshCricketHighlights, 300000);

// Restore saved Voice Gain preference if present
const savedVoiceGain = localStorage.getItem('radio4dm_voice_gain');
if (savedVoiceGain) {
    window._voiceSliderTouched = true;
    const vSlider = document.getElementById('voiceGainSlider');
    const vDisplay = document.getElementById('voiceGainDisplay');
    if (vSlider) vSlider.value = savedVoiceGain;
    if (vDisplay) vDisplay.textContent = `${savedVoiceGain}%`;
    fetch('/api/control/voice-gain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gain: parseFloat(savedVoiceGain) / 100.0 })
    }).catch(() => {});
}
