/**
 * Results management and table rendering module.
 */

const ResultsModule = (() => {
    const resultsCard = document.getElementById("resultsCard");
    const resultsTableBody = document.getElementById("resultsTableBody");
    const resultsCountBadge = document.getElementById("resultsCountBadge");
    const exportCsvBtn = document.getElementById("exportCsvBtn");

    let currentResults = [];

    /**
     * Render court order records in a responsive Bootstrap table.
     * @param {Array} results - List of CourtOrderResult objects
     */
    function renderResults(results) {
        currentResults = results || [];
        resultsTableBody.innerHTML = "";

        if (!currentResults || currentResults.length === 0) {
            resultsCard.classList.add("d-none");
            return;
        }

        resultsCountBadge.textContent = `${currentResults.length} Order${currentResults.length > 1 ? "s" : ""}`;

        currentResults.forEach((order) => {
            const tr = document.createElement("tr");

            // Format order type badge
            let typeBadge = `<span class="order-badge badge-interim">Order</span>`;
            if (order.order_type) {
                const lowerType = order.order_type.toLowerCase();
                if (lowerType.includes("interim")) {
                    typeBadge = `<span class="order-badge badge-interim">Interim</span>`;
                } else if (lowerType.includes("final")) {
                    typeBadge = `<span class="order-badge badge-final">Final</span>`;
                } else {
                    typeBadge = `<span class="order-badge bg-light text-dark">${escapeHtml(order.order_type)}</span>`;
                }
            }

            // Document link button
            let actionCell = `<span class="text-muted small fst-italic">Unavailable</span>`;
            if (order.order_url) {
                const isDecree = order.order_type && order.order_type.toLowerCase().includes("decree");
                const btnLabel = isDecree ? "Open Decree" : "Open Official Order";
                actionCell = `
                    <a href="${escapeHtml(order.order_url)}" 
                       target="_blank" 
                       rel="noopener noreferrer" 
                       class="btn-official-order"
                       title="Open authentic official document in new tab">
                        <i class="bi bi-file-earmark-pdf"></i>
                        <span>${escapeHtml(btnLabel)}</span>
                        <i class="bi bi-box-arrow-up-right ms-1" style="font-size: 0.7rem;"></i>
                    </a>
                `;
            }

            tr.innerHTML = `
                <td class="text-muted fw-semibold">${order.sl_no}</td>
                <td>
                    <div class="fw-bold text-dark">${escapeHtml(order.case_number || "—")}</div>
                    <div class="text-muted small">${escapeHtml(order.case_type || "General")}</div>
                </td>
                <td>
                    <div class="fw-medium text-dark">${escapeHtml(order.party_name || "—")}</div>
                </td>
                <td>
                    <span class="badge bg-light text-secondary border fw-medium px-2 py-1">
                        <i class="bi bi-calendar-event me-1"></i>${escapeHtml(order.order_date || "—")}
                    </span>
                </td>
                <td>
                    <div>${typeBadge}</div>
                    <div class="text-muted small mt-1">#${escapeHtml(order.order_number || "—")}</div>
                </td>
                <td>
                    <div class="small text-secondary">${escapeHtml(order.court_name || "—")}</div>
                </td>
                <td class="text-center">
                    ${actionCell}
                </td>
            `;

            resultsTableBody.appendChild(tr);
        });

        resultsCard.classList.remove("d-none");
        resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    /**
     * Clear all results and hide table.
     */
    function clearResults() {
        currentResults = [];
        resultsTableBody.innerHTML = "";
        resultsCard.classList.add("d-none");
    }

    /**
     * Export current records as CSV.
     */
    function exportToCsv() {
        if (!currentResults || currentResults.length === 0) {
            alert("No results available to export.");
            return;
        }

        const headers = ["Sl No", "Case Number", "Case Type", "Party Name", "Order Date", "Order Type", "Court Name", "Document URL"];
        const rows = currentResults.map(r => [
            r.sl_no,
            `"${(r.case_number || '').replace(/"/g, '""')}"`,
            `"${(r.case_type || '').replace(/"/g, '""')}"`,
            `"${(r.party_name || '').replace(/"/g, '""')}"`,
            `"${(r.order_date || '').replace(/"/g, '""')}"`,
            `"${(r.order_type || '').replace(/"/g, '""')}"`,
            `"${(r.court_name || '').replace(/"/g, '""')}"`,
            `"${(r.order_url || '').replace(/"/g, '""')}"`
        ]);

        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `ecourts_orders_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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

    // Bind CSV Export
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", exportToCsv);
    }

    return {
        renderResults,
        clearResults
    };
})();
