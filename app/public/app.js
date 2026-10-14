/**
 * Main application bootstrap script.
 * Initializes modules and interactive helpers (date pickers, audio captcha).
 */

function bootstrapApp() {
    // Initialize Search Module
    SearchModule.init();

    // Date Picker Sync Helpers
    setupDatePicker("fromDateInput", "fromDateBtn", "nativeFromDate");
    setupDatePicker("toDateInput", "toDateBtn", "nativeToDate");

    // Audio Captcha (Text-to-Speech Accessibility)
    const audioBtn = document.getElementById("captchaAudioBtn");
    if (audioBtn) {
        audioBtn.addEventListener("click", () => {
            if ('speechSynthesis' in window) {
                const textToSay = "Please enter the characters visible in the captcha box.";
                const utterance = new SpeechSynthesisUtterance(textToSay);
                utterance.rate = 0.9;
                window.speechSynthesis.speak(utterance);
            } else {
                alert("Audio synthesizer is not supported by your browser.");
            }
        });
    }

    // Refresh Captcha Button
    const refreshBtn = document.getElementById("captchaRefreshBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            const icon = refreshBtn.querySelector("i");
            if (icon) {
                icon.classList.add("spin-animation");
                setTimeout(() => icon.classList.remove("spin-animation"), 600);
            }
            const captchaInput = document.getElementById("captchaInput");
            if (captchaInput) {
                captchaInput.value = "";
                captchaInput.focus();
            }
        });
    }

    console.log("eCourts Order Date Search Frontend Initialized.");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrapApp);
} else {
    bootstrapApp();
}

/**
 * Connect a text input (DD-MM-YYYY) with a native hidden datepicker (YYYY-MM-DD).
 */
function setupDatePicker(textInputId, buttonId, nativeInputId) {
    const textInput = document.getElementById(textInputId);
    const btn = document.getElementById(buttonId);
    const nativeInput = document.getElementById(nativeInputId);

    if (!textInput || !btn || !nativeInput) return;

    btn.addEventListener("click", () => {
        // If text input already has DD-MM-YYYY, convert to YYYY-MM-DD for native input
        const val = textInput.value.trim();
        if (/^\d{2}-\d{2}-\d{4}$/.test(val)) {
            const [d, m, y] = val.split("-");
            nativeInput.value = `${y}-${m}-${d}`;
        }
        nativeInput.showPicker ? nativeInput.showPicker() : nativeInput.click();
    });

    nativeInput.addEventListener("change", () => {
        const val = nativeInput.value; // YYYY-MM-DD
        if (val) {
            const [y, m, d] = val.split("-");
            textInput.value = `${d}-${m}-${y}`;
            textInput.classList.remove("is-invalid");
        }
    });

    // Auto format typing DD-MM-YYYY
    textInput.addEventListener("input", (e) => {
        let v = e.target.value.replace(/[^0-9]/g, '');
        if (v.length > 2 && v.length <= 4) {
            e.target.value = v.slice(0, 2) + '-' + v.slice(2);
        } else if (v.length > 4) {
            e.target.value = v.slice(0, 2) + '-' + v.slice(2, 4) + '-' + v.slice(4, 8);
        }
    });
}
