/**
 * Search workflow, API communication, and State Machine module.
 */

const SearchModule = (() => {
    // Form and input elements
    const searchForm = document.getElementById("orderDateSearchForm");
    const stateInput = document.getElementById("stateInput");
    const districtInput = document.getElementById("districtInput");
    const courtComplexInput = document.getElementById("courtComplexInput");
    const fromDateInput = document.getElementById("fromDateInput");
    const toDateInput = document.getElementById("toDateInput");
    
    // Captcha elements
    const captchaSection = document.getElementById("captchaSection");
    const captchaImage = document.getElementById("captchaImage");
    const captchaPlaceholderText = document.getElementById("captchaPlaceholderText");
    const captchaInput = document.getElementById("captchaInput");
    const captchaRefreshBtn = document.getElementById("captchaRefreshBtn");
    const captchaAudioBtn = document.getElementById("captchaAudioBtn");

    // Action buttons
    const goButton = document.getElementById("goButton");
    const goButtonText = document.getElementById("goButtonText");
    const goSpinner = document.getElementById("goSpinner");
    const resetButton = document.getElementById("resetButton");

    // Status display elements
    const statusContainer = document.getElementById("statusContainer");
    const statusAlert = document.getElementById("statusAlert");
    const statusIcon = document.getElementById("statusIcon");
    const statusTitle = document.getElementById("statusTitle");
    const statusMessage = document.getElementById("statusMessage");
    const statusProgressBar = document.getElementById("statusProgressBar");

    // State tracking
    let activeSearchId = null;
    let pollInterval = null;
    let currentState = "READY"; // READY, SEARCHING, CAPTCHA_REQUIRED, RESULTS_FOUND, etc.

    /**
     * Set and render distinct UI state.
     */
    function setUIState(state, details = {}) {
        currentState = state;
        statusContainer.style.display = "block";
        statusProgressBar.classList.add("d-none");
        statusAlert.className = "alert alert-dismissible fade show d-flex align-items-start gap-3 p-3 rounded-3 shadow-xs";

        switch (state) {
            case "READY":
                statusContainer.style.display = "none";
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                captchaInput.disabled = true;
                captchaInput.value = "";
                captchaImage.classList.add("d-none");
                captchaPlaceholderText.classList.remove("d-none");
                break;

            case "SEARCHING":
                setFormDisabled(true);
                goSpinner.classList.remove("d-none");
                goButtonText.textContent = "Searching...";
                statusAlert.classList.add("alert-primary");
                statusIcon.innerHTML = `<i class="bi bi-hourglass-split text-primary"></i>`;
                statusTitle.textContent = "Searching eCourts Portal";
                statusMessage.textContent = details.message || "Connecting to court server and verifying location...";
                statusProgressBar.classList.remove("d-none");
                break;

            case "CAPTCHA_REQUIRED":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Submit Captcha";
                statusAlert.classList.add("alert-warning");
                statusIcon.innerHTML = `<i class="bi bi-shield-lock text-warning"></i>`;
                statusTitle.textContent = "CAPTCHA Verification Required";
                statusMessage.textContent = details.message || "Please enter the characters from the image challenge into the *Enter Captcha field.";
                
                // Display captcha image
                if (details.captcha_image) {
                    captchaImage.src = details.captcha_image;
                    captchaImage.classList.remove("d-none");
                    captchaPlaceholderText.classList.add("d-none");
                }
                captchaInput.disabled = false;
                captchaInput.focus();
                break;

            case "RESULTS_FOUND":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-success");
                statusIcon.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i>`;
                statusTitle.textContent = "Court Orders Retrieved";
                statusMessage.textContent = details.message || `Successfully retrieved ${details.count || ''} court orders.`;
                break;

            case "NO_RESULTS":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-info");
                statusIcon.innerHTML = `<i class="bi bi-search text-info"></i>`;
                statusTitle.textContent = "No Records Found";
                statusMessage.textContent = details.message || "No court orders found matching the specified date criteria for this court complex.";
                break;

            case "UNMATCHED_LOCATION":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-danger");
                statusIcon.innerHTML = `<i class="bi bi-geo-alt-fill text-danger"></i>`;
                statusTitle.textContent = "Location Matching Error";
                statusMessage.textContent = details.message || "Could not match the typed location with official options.";
                break;

            case "AMBIGUOUS_LOCATION":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-warning");
                statusIcon.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-warning"></i>`;
                statusTitle.textContent = "Ambiguous Location Match";
                statusMessage.textContent = details.message || "Multiple locations match your input. Please enter a more specific name.";
                break;

            case "INVALID_DATE_INPUT":
            case "INVALID_LOCATION_INPUT":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-danger");
                statusIcon.innerHTML = `<i class="bi bi-exclamation-circle-fill text-danger"></i>`;
                statusTitle.textContent = "Input Validation Error";
                statusMessage.textContent = details.message || "Please correct the highlighted fields and retry.";
                break;

            case "WEBSITE_UNAVAILABLE":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-danger");
                statusIcon.innerHTML = `<i class="bi bi-cloud-slash text-danger"></i>`;
                statusTitle.textContent = "Official Portal Unavailable";
                statusMessage.textContent = details.message || "The official eCourts portal is currently unreachable or geo-restricted.";
                break;

            case "SEARCH_FAILED":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-danger");
                statusIcon.innerHTML = `<i class="bi bi-x-octagon-fill text-danger"></i>`;
                statusTitle.textContent = "Search Failed";
                statusMessage.textContent = details.message || "The search operation encountered an error. Please try again.";
                break;

            case "SEARCH_CANCELLED":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-secondary");
                statusIcon.innerHTML = `<i class="bi bi-slash-circle text-secondary"></i>`;
                statusTitle.textContent = "Search Cancelled";
                statusMessage.textContent = "The active search was cancelled and temporary resources were cleared.";
                break;

            case "SESSION_EXPIRED":
                setFormDisabled(false);
                goSpinner.classList.add("d-none");
                goButtonText.textContent = "Go";
                statusAlert.classList.add("alert-warning");
                statusIcon.innerHTML = `<i class="bi bi-clock-history text-warning"></i>`;
                statusTitle.textContent = "Session Expired";
                statusMessage.textContent = "Search session timed out due to inactivity. Please submit a new search.";
                break;
        }
    }

    function setFormDisabled(disabled) {
        stateInput.disabled = disabled;
        districtInput.disabled = disabled;
        courtComplexInput.disabled = disabled;
        fromDateInput.disabled = disabled;
        toDateInput.disabled = disabled;
        document.querySelectorAll("input[name='order_type']").forEach(r => r.disabled = disabled);
        goButton.disabled = disabled;
    }

    /**
     * Validate client-side inputs.
     */
    function validateInputs() {
        let valid = true;

        // Clean & trim location inputs
        const stateVal = stateInput.value.trim();
        const districtVal = districtInput.value.trim();
        const courtComplexVal = courtComplexInput.value.trim();

        if (!stateVal) {
            stateInput.classList.add("is-invalid");
            valid = false;
        } else {
            stateInput.classList.remove("is-invalid");
        }

        if (!districtVal) {
            districtInput.classList.add("is-invalid");
            valid = false;
        } else {
            districtInput.classList.remove("is-invalid");
        }

        if (!courtComplexVal) {
            courtComplexInput.classList.add("is-invalid");
            valid = false;
        } else {
            courtComplexInput.classList.remove("is-invalid");
        }

        // Validate Date format DD-MM-YYYY
        const dateRegex = /^\d{2}-\d{2}-\d{4}$/;
        const fromDateVal = fromDateInput.value.trim();
        const toDateVal = toDateInput.value.trim();

        let dateFromObj = null;
        let dateToObj = null;

        if (!fromDateVal || !dateRegex.test(fromDateVal)) {
            fromDateInput.classList.add("is-invalid");
            valid = false;
        } else {
            const [d, m, y] = fromDateVal.split("-").map(Number);
            dateFromObj = new Date(y, m - 1, d);
            if (dateFromObj.getFullYear() !== y || dateFromObj.getMonth() !== (m - 1) || dateFromObj.getDate() !== d) {
                fromDateInput.classList.add("is-invalid");
                valid = false;
            } else {
                fromDateInput.classList.remove("is-invalid");
            }
        }

        if (!toDateVal || !dateRegex.test(toDateVal)) {
            toDateInput.classList.add("is-invalid");
            valid = false;
        } else {
            const [d, m, y] = toDateVal.split("-").map(Number);
            dateToObj = new Date(y, m - 1, d);
            if (dateToObj.getFullYear() !== y || dateToObj.getMonth() !== (m - 1) || dateToObj.getDate() !== d) {
                toDateInput.classList.add("is-invalid");
                valid = false;
            } else {
                toDateInput.classList.remove("is-invalid");
            }
        }

        // Date range logical check
        if (dateFromObj && dateToObj && dateFromObj > dateToObj) {
            toDateInput.classList.add("is-invalid");
            document.getElementById("toDateFeedback").textContent = "To Date cannot be earlier than From Date.";
            valid = false;
        }

        return valid;
    }

    /**
     * Submit search to backend API.
     */
    async function handleSearchSubmit(e) {
        if (e) e.preventDefault();

        // If currently awaiting CAPTCHA, submit the CAPTCHA response
        if (currentState === "CAPTCHA_REQUIRED") {
            await handleCaptchaSubmit();
            return;
        }

        if (!validateInputs()) {
            setUIState("INVALID_LOCATION_INPUT", { message: "Please fill in all required location fields and valid DD-MM-YYYY dates." });
            return;
        }

        // Clear existing results
        ResultsModule.clearResults();

        // Read values (trimmed)
        const payload = {
            state: stateInput.value.trim(),
            district: districtInput.value.trim(),
            court_complex: courtComplexInput.value.trim(),
            order_date_criteria: {
                from_date: fromDateInput.value.trim(),
                to_date: toDateInput.value.trim(),
                order_type: document.querySelector("input[name='order_type']:checked").value
            }
        };

        setUIState("SEARCHING", { message: "Initiating authorized search session..." });

        try {
            const response = await fetch("/api/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Server error (${response.status})`);
            }

            const data = await response.json();
            activeSearchId = data.search_id;

            // Start polling status
            startPolling(activeSearchId);

        } catch (err) {
            console.error("Search submission error:", err);
            setUIState("SEARCH_FAILED", { message: err.message || "Failed to start search. Please verify server connection." });
        }
    }

    /**
     * Poll status endpoint for search progress.
     */
    function startPolling(searchId) {
        stopPolling();

        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/search/${searchId}`);
                if (!response.ok) {
                    if (response.status === 404) {
                        stopPolling();
                        setUIState("SESSION_EXPIRED");
                        return;
                    }
                    throw new Error(`Status check error (${response.status})`);
                }

                const data = await response.json();
                processStatusUpdate(data);

            } catch (err) {
                console.warn("Polling error:", err);
            }
        }, 1200);
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    /**
     * Process received status payload.
     */
    function processStatusUpdate(data) {
        const status = data.status;

        switch (status) {
            case "running":
                setUIState("SEARCHING", { message: data.message });
                break;

            case "captcha_required":
                stopPolling();
                setUIState("CAPTCHA_REQUIRED", {
                    message: data.message,
                    captcha_image: data.captcha_image
                });
                break;

            case "completed":
                stopPolling();
                setUIState("RESULTS_FOUND", { message: data.message, count: data.total_count });
                ResultsModule.renderResults(data.results);
                break;

            case "no_results":
                stopPolling();
                setUIState("NO_RESULTS", { message: data.message });
                ResultsModule.clearResults();
                break;

            case "failed":
                stopPolling();
                if (data.error_code === "UNMATCHED_STATE" || data.error_code === "UNMATCHED_DISTRICT" || data.error_code === "UNMATCHED_COURT_COMPLEX") {
                    setUIState("UNMATCHED_LOCATION", { message: data.message });
                } else if (data.error_code === "AMBIGUOUS_STATE" || data.error_code === "AMBIGUOUS_LOCATION") {
                    setUIState("AMBIGUOUS_LOCATION", { message: data.message });
                } else if (data.error_code === "UPSTREAM_UNAVAILABLE") {
                    setUIState("WEBSITE_UNAVAILABLE", { message: data.message });
                } else {
                    setUIState("SEARCH_FAILED", { message: data.message });
                }
                break;

            case "cancelled":
                stopPolling();
                setUIState("SEARCH_CANCELLED");
                break;

            case "expired":
                stopPolling();
                setUIState("SESSION_EXPIRED");
                break;
        }
    }

    /**
     * Submit manually entered CAPTCHA response.
     */
    async function handleCaptchaSubmit() {
        const captchaVal = captchaInput.value.trim();
        if (!captchaVal) {
            captchaInput.classList.add("is-invalid");
            captchaInput.focus();
            return;
        }
        captchaInput.classList.remove("is-invalid");

        if (!activeSearchId) return;

        setUIState("SEARCHING", { message: "Verifying CAPTCHA and submitting search..." });

        try {
            const response = await fetch(`/api/search/${activeSearchId}/captcha`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ captcha: captchaVal })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "CAPTCHA submission failed");
            }

            // Resume polling
            startPolling(activeSearchId);

        } catch (err) {
            console.error("CAPTCHA submit error:", err);
            setUIState("SEARCH_FAILED", { message: err.message || "Failed to submit CAPTCHA." });
        }
    }

    /**
     * Reset form, clear results, and cancel active search session.
     */
    async function handleReset() {
        stopPolling();

        if (activeSearchId) {
            try {
                await fetch(`/api/search/${activeSearchId}/cancel`, { method: "POST" });
            } catch (e) {
                // Ignore failure on reset
            }
            activeSearchId = null;
        }

        // Reset inputs
        searchForm.reset();
        document.getElementById("orderTypeInterim").checked = true;

        // Remove invalid classes
        document.querySelectorAll(".is-invalid").forEach(el => el.classList.remove("is-invalid"));

        // Clear results
        ResultsModule.clearResults();

        // Reset state
        setUIState("READY");
    }

    return {
        init: () => {
            searchForm.addEventListener("submit", handleSearchSubmit);
            resetButton.addEventListener("click", handleReset);
            
            // Allow pressing Enter in captcha input
            captchaInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    handleCaptchaSubmit();
                }
            });
        },
        getState: () => currentState
    };
})();
