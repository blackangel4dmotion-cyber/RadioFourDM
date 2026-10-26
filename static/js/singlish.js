/**
 * Helakuru-Standard Singlish to Sinhala Unicode Converter Engine
 * Real-time phonetic transliteration matching Helakuru Sri Lanka conventions.
 * Supports F12, Ctrl + Space, and UI toggle buttons.
 */

(function () {
    // Default language mode (true = Sinhala Unicode, false = English)
    let isSinhala = true; 

    // Base mapping for Singlish characters to Sinhala letters
    const baseMapping = {
        'a': 'අ', 'A': 'ඇ', 'i': 'ඉ', 'I': 'ඉ', 'u': 'උ', 'U': 'උ', 'e': 'එ', 'E': 'එ', 'o': 'ඔ', 'O': 'ඔ',
        'k': 'ක්', 'K': 'ක්', 'c': 'ක්\u200C', 'C': 'ක්\u200C', 
        'g': 'ග්', 'G': 'ග්', 'j': 'ජ්', 't': 'ට්', 'd': 'ඩ්', 'q': 'ද්', 'n': 'න්',
        'p': 'ප්', 'P': 'ප්', 'b': 'බ්', 'm': 'ම්', 'M': 'ම්', 'y': 'ය්', 'Y': 'ය්', 'r': 'ර්', 'l': 'ල්', 'v': 'ව්',
        'V': 'ව්', 'w': 'ව්', 'W': 'ව්', 's': 'ස්', 'h': 'හ්', 'f': 'ෆ්', 'F': 'ෆ්',
        'N': 'ණ්', 'L': 'ළ්', 'S': 'ෂ්', 'J': 'ඣ්', 'T': 'ඨ්', 'D': 'ඪ්', 'Q': 'ධ්', 'B': 'ඹ්',
        'R': 'ඍ', 'H': 'ඃ', 'x': 'ං', 'X': 'ඞ', 'z': 'z'
    };

    // Special combination rules for standard Helakuru Singlish typing
    const stateRules = [
        { regex: /(.)්\u200Dර්$/, char: 'u', replace: '$1ෘ' },
        { regex: /(.)්\u200Dර්$/, char: 'a', replace: '$1්\u200Dර' },
        { regex: /(.)්\u200Dය්$/, char: 'a', replace: '$1්\u200Dය' },
        { regex: /(.)ැ$/, char: 'a', replace: '$1ෑ' },
        { regex: /(.)ැ$/, char: 'A', replace: '$1ෑ' },
        { regex: /(.)ැ$/, char: 'e', replace: '$1ෑ' },
        { regex: /(.)ි$/, char: 'i', replace: '$1ී' },
        { regex: /(.)ි$/, char: 'e', replace: '$1ී' },
        { regex: /(.)ු$/, char: 'u', replace: '$1ූ' },
        { regex: /(.)ෙ$/, char: 'e', replace: '$1ේ' },
        { regex: /(.)ෙ$/, char: 'i', replace: '$1ෛ' },
        { regex: /(.)ො$/, char: 'o', replace: '$1ෝ' },
        { regex: /(.)ො$/, char: 'u', replace: '$1ෞ' },
        { regex: /(.)ා$/, char: 'u', replace: '$1ෞ' },
        { regex: /(.)ෘ$/, char: 'u', replace: '$1ෲ' },
        { regex: /ච්$/, char: 'h', replace: 'ඡ්' },
        { regex: /ත්$/, char: 'h', replace: 'ථ්' },
        { regex: /ද්$/, char: 'h', replace: 'ධ්' },
        { regex: /ඬ්$/, char: 'h', replace: 'ඳ්' },
        { regex: /ට්$/, char: 'h', replace: 'ත්' },
        { regex: /ඩ්$/, char: 'h', replace: 'ද්' },
        { regex: /ස්$/, char: 'h', replace: 'ශ්' },
        { regex: /ෂ්$/, char: 'h', replace: 'ෂ්' },
        { regex: /ක්\u200C$/, char: 'h', replace: 'ච්' },
        { regex: /ක්$/, char: 'h', replace: 'ඛ්' },
        { regex: /ප්$/, char: 'h', replace: 'ඵ්' },
        { regex: /බ්$/, char: 'h', replace: 'භ්' },
        { regex: /ග්$/, char: 'h', replace: 'ඝ්' },
        { regex: /න්$/, char: 'd', replace: 'ඳ්' },
        { regex: /ම්$/, char: 'b', replace: 'ඹ්' },
        { regex: /න්$/, char: 'g', replace: 'ඟ්' },
        { regex: /(.)්$/, char: 'r', replace: '$1්\u200Dර්' },
        { regex: /(.)්$/, char: 'y', replace: '$1්\u200Dය්' },
        { regex: /ක්\u200C$/, char: 'r', replace: 'ක්\u200Dර්' },
        { regex: /ක්\u200C$/, char: 'y', replace: 'ක්\u200Dය්' },
        { regex: /z$/, char: 'g', replace: 'ඟ්' },
        { regex: /z$/, char: 'j', replace: 'ඦ්' },
        { regex: /z$/, char: 'd', replace: 'ඬ්' },
        { regex: /z$/, char: 'h', replace: 'ඥ්' },
        { regex: /z$/, char: 'k', replace: 'ඤ්' },
        { regex: /z$/, char: 'n', replace: 'ං' },
        { regex: /ළ්$/, char: 'u', replace: 'ඏ' },
        { regex: /අ$/, char: 'a', replace: 'ආ' },
        { regex: /අ$/, char: 'e', replace: 'ඇ' },
        { regex: /අ$/, char: 'i', replace: 'ඓ' },
        { regex: /අ$/, char: 'u', replace: 'ඖ' },
        { regex: /ඇ$/, char: 'a', replace: 'ඈ' },
        { regex: /ඇ$/, char: 'A', replace: 'ඈ' },
        { regex: /ඇ$/, char: 'e', replace: 'ඈ' },
        { regex: /ඉ$/, char: 'i', replace: 'ඊ' },
        { regex: /උ$/, char: 'u', replace: 'ඌ' },
        { regex: /එ$/, char: 'e', replace: 'ඒ' },
        { regex: /එ$/, char: 'i', replace: 'ඓ' },
        { regex: /ඔ$/, char: 'o', replace: 'ඕ' },
        { regex: /ඔ$/, char: 'u', replace: 'ඖ' },
        { regex: /ඍ$/, char: 'u', replace: 'ඎ' },
        { regex: /(.)්$/, char: 'a', replace: '$1' },
        { regex: /ක්\u200C$/, char: 'a', replace: 'ක' },
        { regex: /([\u0D9A-\u0DC6])$/, char: 'a', replace: '$1ා' },
        { regex: /([\u0D9A-\u0DC6])$/, char: 'i', replace: '$1ෛ' },
        { regex: /([\u0D9A-\u0DC6])$/, char: 'u', replace: '$1ෞ' },
        { regex: /(.)්$/, char: 'A', replace: '$1ැ' },
        { regex: /ක්\u200C$/, char: 'A', replace: 'කැ' },
        { regex: /(.)්$/, char: 'i', replace: '$1ි' },
        { regex: /ක්\u200C$/, char: 'i', replace: 'කි' },
        { regex: /(.)්$/, char: 'u', replace: '$1ු' },
        { regex: /ක්\u200C$/, char: 'u', replace: 'කු' },
        { regex: /(.)්$/, char: 'e', replace: '$1ෙ' },
        { regex: /ක්\u200C$/, char: 'e', replace: 'කෙ' },
        { regex: /(.)්$/, char: 'o', replace: '$1ො' },
        { regex: /ක්\u200C$/, char: 'o', replace: 'කො' }
    ];

    function insertSinhalaChar(char, targetElement) {
        const start = targetElement.selectionStart;
        const end = targetElement.selectionEnd;
        let textBefore = targetElement.value.substring(0, start);
        const textAfter = targetElement.value.substring(end);
        let replaced = false;

        for (let rule of stateRules) {
            if (rule.regex.test(textBefore)) {
                if (rule.char === char) {
                    textBefore = textBefore.replace(rule.regex, rule.replace);
                    replaced = true;
                    break;
                }
            }
        }

        if (!replaced) {
            const mappedChar = baseMapping[char] || char;
            textBefore += mappedChar;
        }

        targetElement.value = textBefore + textAfter;
        
        const newPos = textBefore.length;
        targetElement.setSelectionRange(newPos, newPos);
        targetElement.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // Public API to set or toggle Singlish state
    window.setHelakuruMode = function(enabled) {
        isSinhala = !!enabled;
        document.dispatchEvent(new CustomEvent('singlishModeChange', { detail: { isSinhala } }));
    };

    window.toggleHelakuruMode = function() {
        window.setHelakuruMode(!isSinhala);
        return isSinhala;
    };

    window.isHelakuruActive = function() {
        return isSinhala;
    };

    // Global Keydown Listener
    document.addEventListener('keydown', (e) => {
        // Switch Language Mode via F12 or Ctrl + Space
        if (e.key === 'F12' || (e.ctrlKey && e.code === 'Space')) {
            e.preventDefault();
            window.toggleHelakuruMode();
            return;
        }

        if (!isSinhala) return;
        
        const target = e.target;
        const isTextInput = target.tagName === 'TEXTAREA' || 
                            (target.tagName === 'INPUT' && ['text', 'search', 'url', 'email'].includes(target.type));

        if (!isTextInput) return;
        
        // Intercept standard English letters (a-z, A-Z)
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
            if (/[a-zA-Z]/.test(e.key)) {
                e.preventDefault();
                insertSinhalaChar(e.key, target);
            }
        }
    }, true);

})();
