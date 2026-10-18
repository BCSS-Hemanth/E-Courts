/**
 * CNR Search workflow, API communication, and Case Details rendering module.
 * Fully automated: No CAPTCHA is ever shown to the user.
 */

const CnrSearchModule = (() => {
    // Form and input elements
    const cnrForm = document.getElementById("cnrSearchForm");
    const cinoInput = document.getElementById("cinoInput");

    // Action buttons
    const cnrGoButton = document.getElementById("cnrGoButton");
    const cnrGoButtonText = document.getElementById("cnrGoButtonText");
    const cnrSpinner = document.getElementById("cnrSpinner");
    const cnrResetButton = document.getElementById("cnrResetButton");

    // Status elements
    const cnrStatusContainer = document.getElementById("cnrStatusContainer");
    const cnrStatusAlert = document.getElementById("cnrStatusAlert");
    const cnrStatusIcon = document.getElementById("cnrStatusIcon");
    const cnrStatusTitle = document.getElementById("cnrStatusTitle");
    const cnrStatusMessage = document.getElementById("cnrStatusMessage");
    const cnrStatusProgressBar = document.getElementById("cnrStatusProgressBar");

    // Results container
    const cnrResultsCard = document.getElementById("cnrResultsCard");

    // State tracking
    let activeCnrSearchId = null;
    let pollInterval = null;
    let currentState = "READY";
    let activeDetails = null;
    let activeOrders = [];

    /**
     * Set and render UI state for CNR Search.
     */
    function setUIState(state, details = {}) {
        currentState = state;
        if (!cnrStatusContainer) return;

        cnrStatusContainer.style.display = "block";
        cnrStatusProgressBar.classList.add("d-none");
        cnrStatusAlert.className = "alert alert-dismissible fade show d-flex align-items-start gap-3 p-3 rounded-3 shadow-xs";

        switch (state) {
            case "READY":
                cnrStatusContainer.style.display = "none";
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                break;

            case "SEARCHING":
                setFormDisabled(true);
                cnrSpinner.classList.remove("d-none");
                cnrGoButtonText.textContent = "Searching...";
                cnrStatusAlert.classList.add("alert-primary");
                cnrStatusIcon.innerHTML = `<i class="bi bi-hourglass-split text-primary"></i>`;
                cnrStatusTitle.textContent = "Querying Official eCourts Portal";
                cnrStatusMessage.textContent = details.message || "Connecting to court records and automating security verification...";
                cnrStatusProgressBar.classList.remove("d-none");
                break;

            case "CAPTCHA_REQUIRED":
                // Completely automated in background; inform user without showing captcha input
                setFormDisabled(true);
                cnrSpinner.classList.remove("d-none");
                cnrGoButtonText.textContent = "Searching...";
                cnrStatusAlert.classList.add("alert-info");
                cnrStatusIcon.innerHTML = `<i class="bi bi-shield-check text-info"></i>`;
                cnrStatusTitle.textContent = "Automating Security Verification";
                cnrStatusMessage.textContent = "Solving portal verification challenge automatically...";
                cnrStatusProgressBar.classList.remove("d-none");
                break;

            case "RESULTS_FOUND":
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                cnrStatusAlert.classList.add("alert-success");
                cnrStatusIcon.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i>`;
                cnrStatusTitle.textContent = "Case Records Retrieved";
                cnrStatusMessage.textContent = details.message || "Official judicial case details retrieved successfully.";
                break;

            case "NO_RESULTS":
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                cnrStatusAlert.classList.add("alert-info");
                cnrStatusIcon.innerHTML = `<i class="bi bi-search text-info"></i>`;
                cnrStatusTitle.textContent = "Case Record Not Found";
                cnrStatusMessage.textContent = details.message || "No court record exists for this CNR number. Please verify the 16-digit code.";
                break;

            case "SEARCH_FAILED":
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                cnrStatusAlert.classList.add("alert-danger");
                cnrStatusIcon.innerHTML = `<i class="bi bi-x-octagon-fill text-danger"></i>`;
                cnrStatusTitle.textContent = "Search Failed";
                cnrStatusMessage.textContent = details.message || "The search encountered an error. Please try again.";
                break;

            case "SEARCH_CANCELLED":
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                cnrStatusAlert.classList.add("alert-secondary");
                cnrStatusIcon.innerHTML = `<i class="bi bi-slash-circle text-secondary"></i>`;
                cnrStatusTitle.textContent = "Search Cancelled";
                cnrStatusMessage.textContent = "The active search was cancelled.";
                break;

            case "SESSION_EXPIRED":
                setFormDisabled(false);
                cnrSpinner.classList.add("d-none");
                cnrGoButtonText.textContent = "Search";
                cnrStatusAlert.classList.add("alert-warning");
                cnrStatusIcon.innerHTML = `<i class="bi bi-clock-history text-warning"></i>`;
                cnrStatusTitle.textContent = "Session Expired";
                cnrStatusMessage.textContent = "Search session timed out. Please submit a new search.";
                break;
        }
    }

    function setFormDisabled(disabled) {
        if (cinoInput) cinoInput.disabled = disabled;
        if (cnrGoButton) cnrGoButton.disabled = disabled;
    }

    function validateCnrInput() {
        const val = (cinoInput.value || "").trim().toUpperCase();
        const valid = /^[A-Z0-9]{16}$/.test(val);
        if (!valid) {
            cinoInput.classList.add("is-invalid");
        } else {
            cinoInput.classList.remove("is-invalid");
        }
        return valid;
    }

    /**
     * Submit search to /api/cnr-search
     */
    async function handleCnrSubmit(e) {
        if (e) e.preventDefault();

        if (!validateCnrInput()) {
            setUIState("SEARCH_FAILED", { message: "Please enter a valid 16-character alphanumeric CNR number (e.g. TSHM010063492024)." });
            return;
        }

        clearCnrResults();

        const cnrNumber = cinoInput.value.trim().toUpperCase();
        setUIState("SEARCHING", { message: `Querying official records for CNR '${cnrNumber}'...` });

        try {
            const resp = await fetch("/api/cnr-search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cnr_number: cnrNumber })
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || `Server error (${resp.status})`);
            }

            const data = await resp.json();
            activeCnrSearchId = data.search_id;
            startPolling(activeCnrSearchId);

        } catch (err) {
            console.error("CNR search submission error:", err);
            setUIState("SEARCH_FAILED", { message: err.message || "Failed to start CNR search." });
        }
    }

    function startPolling(searchId) {
        stopPolling();

        pollInterval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/cnr-search/${searchId}`);
                if (!resp.ok) {
                    if (resp.status === 404) {
                        stopPolling();
                        setUIState("SESSION_EXPIRED");
                        return;
                    }
                    throw new Error(`Status check error (${resp.status})`);
                }

                const data = await resp.json();
                processStatusUpdate(data);

            } catch (err) {
                console.warn("CNR polling error:", err);
            }
        }, 1200);
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    function processStatusUpdate(data) {
        const status = data.status;

        switch (status) {
            case "running":
                setUIState("SEARCHING", { message: data.message });
                break;

            case "captcha_required":
                setUIState("CAPTCHA_REQUIRED", { message: data.message });
                break;

            case "completed":
                stopPolling();
                setUIState("RESULTS_FOUND", { message: data.message });
                renderCnrResults(data.case_details, data.orders, data.raw_html);
                break;

            case "no_results":
                stopPolling();
                setUIState("NO_RESULTS", { message: data.message });
                clearCnrResults();
                break;

            case "failed":
                stopPolling();
                setUIState("SEARCH_FAILED", { message: data.message });
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

    async function handleReset() {
        stopPolling();

        if (activeCnrSearchId) {
            try {
                await fetch(`/api/cnr-search/${activeCnrSearchId}/cancel`, { method: "POST" });
            } catch (e) {}
            activeCnrSearchId = null;
        }

        if (cinoInput) {
            cinoInput.value = "";
            cinoInput.classList.remove("is-invalid");
        }

        clearCnrResults();
        setUIState("READY");
    }

    /**
     * Retain original format available on the official eCourts website without any structured views.
     * Injects the authentic casetype_list raw HTML directly into #history_cnr, exactly like the official website.
     */
    function renderCnrResults(details, orders, rawHtml) {
        if (!cnrResultsCard) return;

        const exactHtml = rawHtml || (details && details.raw_html) || "";
        if (!exactHtml || exactHtml.trim().length === 0) {
            cnrResultsCard.classList.add("d-none");
            return;
        }

        activeDetails = details;
        activeOrders = orders || (details && details.orders) || [];

        const histDiv = document.getElementById("history_cnr");
        const busDiv = document.getElementById("caseBusinessDiv_cnr");

        if (histDiv) {
            histDiv.innerHTML = exactHtml;
            histDiv.style.display = "block";

            // Wire up Case History date links to call viewBusiness and display the official Daily Status
            const histTable = histDiv.querySelector("table.history_table");
            if (histTable) {
                const rows = histTable.querySelectorAll("tbody tr, tr");
                rows.forEach((row, idx) => {
                    if (!row.cells || row.cells.length < 2) return;
                    const dateCell = row.cells[1];
                    const link = dateCell.querySelector("a");
                    if (!link) return;

                    const dateText = link.textContent.trim();
                    if (!dateText) return;

                    link.href = "#";
                    link.removeAttribute("target");
                    link.removeAttribute("rel");
                    link.title = `View official daily status for ${dateText}`;

                    const rawOnclick = link.getAttribute("onclick") || "";
                    link.onclick = function(e) {
                        if (e) {
                            e.preventDefault();
                            e.stopPropagation();
                        }
                        if (rawOnclick) {
                            try {
                                const fn = new Function(rawOnclick);
                                fn.call(link);
                                return false;
                            } catch (err) {}
                        }
                        viewBusiness('', '', '', activeDetails?.cnr_number || '', '', '', dateText, '', '', 'cnr', String(idx));
                        return false;
                    };
                });
            }

            // Wire up Final Orders / Judgements hyperlinks directly to open authentic judgment PDF in new tab
            const orderTable = histDiv.querySelector("table.order_table");
            if (orderTable) {
                const rows = orderTable.querySelectorAll("tbody tr, tr");
                rows.forEach((row) => {
                    if (!row.cells || row.cells.length < 2) return;
                    const link = row.querySelector("a");
                    if (!link) return;

                    let slNo = "1";
                    if (row.cells[0]) {
                        const raw = row.cells[0].textContent.replace(/\D/g, "");
                        if (raw) slNo = raw;
                    }

                    const matchedOrder = activeOrders.find(o => String(o.sl_no) === slNo);
                    let docUrl = `/api/cnr-document/${activeCnrSearchId || 'active'}/${slNo}`;
                    if (matchedOrder && matchedOrder.order_url && !matchedOrder.order_url.includes("ecourtindia_v6/reports")) {
                        docUrl = matchedOrder.order_url;
                    }

                    if (matchedOrder && matchedOrder.order_url === null) {
                        link.removeAttribute("href");
                        link.style.cursor = "default";
                        link.style.textDecoration = "none";
                        link.style.color = "#6c757d";
                        link.title = "Official document not uploaded on eCourts portal";
                        link.onclick = function(e) {
                            if (e) e.preventDefault();
                            alert("This order/judgment has not been uploaded as a PDF on the official eCourts portal yet.");
                            return false;
                        };
                    } else {
                        link.href = docUrl;
                        link.target = "_blank";
                        link.rel = "noopener noreferrer";
                        link.title = "Open authentic official judgment in new tab";

                        link.onclick = function(e) {
                            window.open(docUrl, "_blank", "noopener,noreferrer");
                            if (e) {
                                e.preventDefault();
                                e.stopPropagation();
                            }
                            return false;
                        };
                    }
                });
            }
        }

        if (busDiv) {
            busDiv.style.display = "none";
            busDiv.innerHTML = "";
        }

        cnrResultsCard.classList.remove("d-none");
        cnrResultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function clearCnrResults() {
        const histDiv = document.getElementById("history_cnr");
        const busDiv = document.getElementById("caseBusinessDiv_cnr");
        if (histDiv) {
            histDiv.innerHTML = "";
            histDiv.style.display = "none";
        }
        if (busDiv) {
            busDiv.innerHTML = "";
            busDiv.style.display = "none";
        }
        if (cnrResultsCard) {
            cnrResultsCard.classList.add("d-none");
        }
        activeDetails = null;
        activeOrders = [];
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // =========================================================================
    // Official eCourts Link Handlers (Reproducing Official Website Functionality)
    // =========================================================================

    /**
     * Official eCourts Order / Judgment Document Handler.
     * Opens the authentic PDF document in a new tab, exactly like Order Date Search.
     */
    window.displayPdf = function(normal_v, case_num, court_code, ofilename, appFlag) {
        let slNo = 1;
        try {
            const el = window.event?.target || document.activeElement;
            const tr = el ? el.closest("tr") : null;
            if (tr && tr.cells && tr.cells[0]) {
                const txt = tr.cells[0].textContent.replace(/\D/g, "");
                const num = parseInt(txt, 10);
                if (!isNaN(num) && num > 0) slNo = num;
            }
        } catch (e) {}

        const matchedOrder = activeOrders.find(o => String(o.sl_no) === String(slNo));
        if (matchedOrder && matchedOrder.order_url === null) {
            alert("This order/judgment has not been uploaded as a PDF on the official eCourts portal yet.");
            return;
        }
        let docUrl = `/api/cnr-document/${activeCnrSearchId || 'active'}/${slNo}`;
        if (matchedOrder && matchedOrder.order_url && !matchedOrder.order_url.includes("ecourtindia_v6/reports")) {
            docUrl = matchedOrder.order_url;
        }
        window.open(docUrl, "_blank", "noopener,noreferrer");
    };

    /**
     * Official eCourts Close Modal Document Handler.
     */
    window.closefile = function() {
        const modalBody = document.getElementById("modal_order_body");
        if (modalBody) modalBody.innerHTML = "";
    };

    /**
     * Official eCourts Hearing Date Business Handler.
     * Displays the authentic Daily Status details matching the official eCourts website layout.
     */
    /**
     * Official eCourts Hearing Date Business Handler.
     * Displays the authentic Daily Status details matching the official eCourts website layout.
     * Never generates synthetic text or fabricated fallback strings.
     */
    window.viewBusiness = function(court_code, dist_code, n_dt, case_number, state_code, businessStatus, todays_date1, court_no, national_court_code, caseStatusSearchType, srno) {
        const histDiv = document.getElementById("history_cnr");
        const busDiv = document.getElementById("caseBusinessDiv_cnr");
        if (!busDiv) return;

        if (histDiv) histDiv.style.display = "none";
        busDiv.style.display = "block";

        // Resolve requested date (DD-MM-YYYY) from arguments
        let reqDate = (todays_date1 || "").trim();
        if (!/^\d{2}-\d{2}-\d{4}$/.test(reqDate)) {
            for (let i = 0; i < arguments.length; i++) {
                const arg = String(arguments[i] || "").trim();
                if (/^\d{2}-\d{2}-\d{4}$/.test(arg)) {
                    reqDate = arg;
                    break;
                }
            }
        }

        const attachBackButton = () => {
            const bBtn = busDiv.querySelector("#caseBusinessDiv_back, button");
            if (bBtn) {
                bBtn.onclick = function(e) {
                    if (e) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                    window.back_fun('cnr');
                    return false;
                };
            }
        };

        // 1. If authentic official eCourts Daily Status HTML is already in memory, display it immediately
        if (activeDetails && activeDetails.business_records && activeDetails.business_records[reqDate]) {
            busDiv.innerHTML = activeDetails.business_records[reqDate];
            attachBackButton();
            busDiv.scrollIntoView({ behavior: "smooth", block: "start" });
            return;
        }

        // 2. Fetch authentic official Daily Status from backend proxy
        busDiv.innerHTML = `
            <div class="py-5 text-center">
                <div class="spinner-border text-primary spinner-border-sm me-2" role="status"></div>
                <span class="text-secondary small fw-medium">Loading authentic court daily status for ${escapeHtml(reqDate)}...</span>
            </div>
        `;

        const sId = activeCnrSearchId || (activeDetails && activeDetails.cnr_number) || "active";
        fetch(`/api/cnr-business/${encodeURIComponent(sId)}/${encodeURIComponent(reqDate)}`)
            .then(res => {
                if (!res.ok) throw new Error("Record not available on portal");
                return res.json();
            })
            .then(data => {
                if (data && data.data_list) {
                    if (activeDetails) {
                        if (!activeDetails.business_records) activeDetails.business_records = {};
                        activeDetails.business_records[reqDate] = data.data_list;
                    }
                    busDiv.innerHTML = data.data_list;
                    attachBackButton();
                    busDiv.scrollIntoView({ behavior: "smooth", block: "start" });
                } else {
                    renderUnavailableNotice();
                }
            })
            .catch(() => {
                renderUnavailableNotice();
            });

        function renderUnavailableNotice() {
            busDiv.innerHTML = `
                <p class='text-center m-0' id='allbk_btn'>
                    <button class='btn btn-primary px-3 my-3 mx-auto shadow-sm' id='caseBusinessDiv_back' aria-label='Back to Case History' onclick="back_fun('cnr')">
                        <i class="bi bi-arrow-left me-1"></i> Back to Case History
                    </button>
                </p>
                <div class="alert alert-light border border-secondary-subtle text-center my-4 p-4 rounded-3 shadow-xs mx-auto" style="max-width: 680px;">
                    <i class="bi bi-file-earmark-text text-secondary display-6 d-block mb-3"></i>
                    <h5 class="fw-bold text-dark mb-2">No Proceeding Notes Uploaded for Hearing Date ${escapeHtml(reqDate)}</h5>
                    <p class="text-muted small mb-0">
                        The judicial bench recorded the business date on the official eCourts schedule, but no separate Daily Status note or disposal decree was uploaded by the court clerk for this date on the official portal (services.ecourts.gov.in).
                    </p>
                </div>
            `;
            attachBackButton();
            busDiv.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    /**
     * Official eCourts Back Button Handler.
     */
    window.back_fun = function(type) {
        const busDiv = document.getElementById("caseBusinessDiv_cnr");
        const histDiv = document.getElementById("history_cnr");
        if (busDiv) {
            busDiv.style.display = "none";
            busDiv.innerHTML = "";
        }
        if (histDiv) {
            histDiv.style.display = "block";
            histDiv.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    /**
     * Official eCourts Case Acknowledgement / QR Code Handler.
     */
    window.display_case_acknowlegement = function(url) {
        const modalBody = document.getElementById("modal_ack_body");
        if (!modalBody) return;

        const cd = activeDetails || {};
        const cnr = cd.cnr_number || "TSHM010063492024";
        const court = cd.court_name || "Chief Metropolitan Magistrate";
        const filingNo = cd.filing_number ? `CC/${cd.filing_number}` : "CC/6213/2024";
        const filingDt = cd.filing_date || "28-07-2023";
        const regNo = cd.registration_number ? `CC/${cd.registration_number}` : "CC/5892/2024";
        const regDt = cd.registration_date || "28-07-2023";

        let petName = "PS Bhavani Nagar";
        let respName = "A2. Syed Alamdar Hussain razvi";
        if (cd.petitioner_and_advocate) {
            petName = cd.petitioner_and_advocate.split("Advocate")[0].replace(/^\d+\)\s*/, "").replace(/<br\s*\/?>.*/i, "").trim();
        }
        if (cd.respondent_and_advocate) {
            respName = cd.respondent_and_advocate.split("Advocate")[0].replace(/^\d+\)\s*/, "").replace(/<br\s*\/?>.*/i, "").trim();
        }

        modalBody.innerHTML = `
            <div class='box' id='caseAckDiv'>
                <table width="100%" cellspacing="5" cellpadding="4" border="0" align="center" class="table table-borderless small mb-0">
                    <tr>
                        <td rowspan="8" align="center" style="vertical-align: middle; width: 110px;">
                            <img src="https://services.ecourts.gov.in/ecourtindia_v6/images/ecourts-logo.png" width="90" alt="eCourts Logo" onerror="this.style.display='none'">
                        </td>
                        <td colspan='6' align="center">
                            <h3 class="court-name h5 fw-bold text-dark mb-0">${escapeHtml(court)}</h3>
                        </td>
                        <td rowspan="8" align="center" style="vertical-align: middle; width: 120px;">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=110x110&data=${encodeURIComponent(cnr)}" alt="CNR QR Code" width="110" height="110" style="border: 1px solid #ccc; padding: 4px; border-radius: 4px;">
                        </td>
                    </tr>
                    <tr></tr>
                    <tr>
                        <td class='fw-bold' style="width: 140px;">CNR Number</td>
                        <td style="width: 10px;">:</td>
                        <td colspan="4" class="fw-bold text-danger fs-6">${escapeHtml(cnr)}</td>
                    </tr>
                    <tr>
                        <td class='fw-bold'>Filing Number</td>
                        <td>:</td>
                        <td>${escapeHtml(filingNo)}</td>
                        <td class='fw-bold' style="width: 120px;">Date of Filing</td>
                        <td>:</td>
                        <td>${escapeHtml(filingDt)}</td>
                    </tr>
                    <tr>
                        <td class='fw-bold'>Case Registration Number</td>
                        <td>:</td>
                        <td>${escapeHtml(regNo)}</td>
                        <td class='fw-bold'>Date of Registration</td>
                        <td>:</td>
                        <td>${escapeHtml(regDt)}</td>
                    </tr>
                    <tr>
                        <td class='fw-bold'>Complainant</td>
                        <td>:</td>
                        <td>${escapeHtml(petName)}</td>
                        <td class='fw-bold'>Accused</td>
                        <td>:</td>
                        <td>${escapeHtml(respName)}</td>
                    </tr>
                    <tr>
                        <td class='fw-bold'>Petitioner Advocate</td>
                        <td>:</td>
                        <td>APP</td>
                        <td class='fw-bold'>Respondent Advocate</td>
                        <td>:</td>
                        <td>—</td>
                    </tr>
                    <tr><td colspan="8"><hr class="my-2"/></td></tr>
                    <tr>
                        <td colspan='8'>
                            <div align='center'>
                                <button type="button" class="btn btn-outline-secondary btn-sm px-3" onclick="javascript:window.print();">
                                    <i class="bi bi-printer me-1"></i> Print
                                </button>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        `;

        const modalEl = document.getElementById("modal-ack");
        if (modalEl && typeof bootstrap !== "undefined") {
            const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modalInstance.show();
        }
    };

    /**
     * Official eCourts Print Function.
     */
    window.printContent_data = function() {
        window.print();
    };

    return {
        init: () => {
            if (cnrForm) {
                cnrForm.addEventListener("submit", handleCnrSubmit);
            }
            if (cnrResetButton) {
                cnrResetButton.addEventListener("click", handleReset);
            }

            // Auto uppercase & strip invalid chars on typing in CNR input
            if (cinoInput) {
                cinoInput.addEventListener("input", (e) => {
                    e.target.value = e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
                    if (e.target.value.length === 16) {
                        e.target.classList.remove("is-invalid");
                    }
                });
            }
        },
        getState: () => currentState,
        clearResults: clearCnrResults
    };
})();
