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
    try {
        await fetch('/api/queue/play-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ track_id: trackId })
        });
        fetchStatus();
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
    playBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause Audio';
    playBtn.className = 'btn btn-secondary btn-play';
    masterDeckCard.classList.add('playing');
    playerStatusTip.className = "fixed-status-line active";
    playerStatusTip.textContent = "Live Broadcast connected (Pro DJ Dual-Deck Stream).";
}

playBtn.addEventListener('click', () => {
    // If playing or connecting, allow clicking to pause/cancel
    if (isPlaying || isConnecting) {
        radioAudio.pause();
        radioAudio.removeAttribute('src');
        radioAudio.load();
        resetPlayerUI("Audio paused. Click Listen Live to resume.");
        return;
    }

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
                if (isConnecting && !isPlaying) {
                    radioAudio.play().then(setPlayerPlayingUI).catch(() => {
                        resetPlayerUI("Click Listen Live to connect audio.");
                    });
                }
            }, 300);
        });
    }
});

radioAudio.addEventListener('playing', setPlayerPlayingUI);
radioAudio.addEventListener('canplay', () => {
    if (isConnecting && !isPlaying) {
        radioAudio.play().then(setPlayerPlayingUI).catch(() => {});
    }
});
radioAudio.addEventListener('error', (e) => {
    console.error("Audio stream error:", e);
    resetPlayerUI("Stream interrupted. Click Listen Live to reconnect.");
});

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

// Queue YouTube Track with Duplicate Alert
youtubeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = ytUrlInput.value.trim();
    if (!url) return;

    addYtBtn.disabled = true;
    ytFeedback.className = "fixed-feedback loading";
    ytFeedback.textContent = "Verifying & Linking YouTube stream...";

    try {
        const res = await fetch('/api/queue/youtube', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();

        if (res.ok) {
            ytFeedback.className = "fixed-feedback success";
            ytFeedback.textContent = `Queued: ${data.track.title}`;
            ytUrlInput.value = "";
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

async function saveStudioSettings() {
    const payload = {
        tts_provider: "gemini",
        gemini_api_key: modalGeminiKey ? modalGeminiKey.value.trim() : "",
        crossfade_seconds: parseInt(modalCrossfadeSec ? modalCrossfadeSec.value : 6) || 6,
        ducking_volume: parseFloat(modalDuckingVol ? modalDuckingVol.value : 0.18) || 0.18
    };

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeSettingsModal();
            alert("Settings saved successfully!");
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

        // Update Deck A Details
        if (data.deck_a) {
            deckATitle.textContent = data.deck_a.track || "Deck A Idle";
            deckATitle.title = data.deck_a.track || "";
            deckATime.textContent = `${formatSeconds(data.deck_a.elapsed)} / ${formatSeconds(data.deck_a.duration)}`;
            if (data.deck_a.active && data.deck_a.volume > 0.05) {
                deckABadge.classList.add('active');
            } else {
                deckABadge.classList.remove('active');
            }
            if (data.deck_a.muted) deckAMuteBtn.classList.add('active');
            else deckAMuteBtn.classList.remove('active');
        }

        // Update Deck B Details
        if (data.deck_b) {
            deckBTitle.textContent = data.deck_b.track || "Deck B Idle";
            deckBTitle.title = data.deck_b.track || "";
            deckBTime.textContent = `${formatSeconds(data.deck_b.elapsed)} / ${formatSeconds(data.deck_b.duration)}`;
            if (data.deck_b.active && data.deck_b.volume > 0.05) {
                deckBBadge.classList.add('active');
            } else {
                deckBBadge.classList.remove('active');
            }
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
        if (schedulerToggle && data.scheduler_enabled !== undefined) {
            schedulerToggle.checked = !!data.scheduler_enabled;
        }
        if (newsSchedulerToggle && data.news_scheduler_enabled !== undefined) {
            newsSchedulerToggle.checked = !!data.news_scheduler_enabled;
        }
        if (autoDjToggle && data.autodj_enabled !== undefined) {
            autoDjToggle.checked = !!data.autodj_enabled;
        }

        // Update 10-Song Standby Playlist (With Pattern Reordering & Next Song Selection)
        queueCount.textContent = data.playlist ? data.playlist.length : 0;
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
                        <button class="btn-track-action play-now" onclick="playNowQueueItem('${track.id}')" title="Play Now (Instant DJ Crossfade)">
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

    } catch (err) {
        console.warn("Status poll error:", err);
    }
}

// Initial fetch
fetchStatus();
setInterval(fetchStatus, 2000);

// Ada Derana Live Headline Polling (Every 5 minutes)
refreshAdaDeranaNews();
setInterval(refreshAdaDeranaNews, 300000);
