document.addEventListener("DOMContentLoaded", () => {
    // --- Utility Functions for UI management ---
    function showLoader(button, isLoading) {
        button.disabled = isLoading;
        const loader = button.querySelector('.loader');
        const icon = button.querySelector('.fa-solid');
        const text = button.querySelector('span');

        if (isLoading) {
            button.classList.add('loading');
            if (loader) loader.style.display = 'inline-block';
            if (icon) icon.style.display = 'none';
            if (text) text.style.display = 'none';
        } else {
            button.classList.remove('loading');
            if (loader) loader.style.display = 'none';
            if (icon) icon.style.display = 'inline-flex';
            if (text) text.style.display = 'inline';
        }
    }

    function updateStatus(statusEl, message, type = 'info') {
        statusEl.textContent = message;
        statusEl.className = `status show ${type}`;
    }

    function clearStatus(statusEl) {
        if (statusEl) {
            statusEl.textContent = '';
            statusEl.className = 'status';
        }
    }

    // --- General UI Setup ---
    const openReportsBtn = document.getElementById("openReportsBtn");
    const reportsGrid = document.getElementById("reportsGrid");

    openReportsBtn.addEventListener("click", () => {
        reportsGrid.classList.toggle("show");
        const isOpening = reportsGrid.classList.contains("show");
        openReportsBtn.querySelector('span').textContent = isOpening ? 'Hide Reports' : 'View Available Reports';
    });

    document.addEventListener("click", (e) => {
        const card = document.querySelector(".card");
        if (card && !card.contains(e.target) && !openReportsBtn.contains(e.target)) {
            reportsGrid.classList.remove("show");
            openReportsBtn.querySelector('span').textContent = 'View Available Reports';
            document.querySelectorAll(".panel.show").forEach(p => {
                p.classList.remove("show");
                p.previousElementSibling?.querySelector?.(".expandBtn")?.setAttribute("aria-expanded", "false");
            });
        }
    });

    document.querySelectorAll(".report-tile").forEach(tile => {
        const expandBtn = tile.querySelector(".expandBtn");
        const panel = tile.querySelector(".panel");
        if (expandBtn && panel) {
            expandBtn.addEventListener("click", () => {
                const isExpanded = panel.classList.contains("show");
                document.querySelectorAll(".report-tile .panel.show").forEach(otherPanel => {
                    if (otherPanel !== panel) {
                        otherPanel.classList.remove("show");
                        otherPanel.previousElementSibling?.querySelector(".expandBtn")?.setAttribute("aria-expanded", "false");
                        clearStatus(otherPanel.querySelector('.status'));
                    }
                });
                panel.classList.toggle("show");
                expandBtn.setAttribute("aria-expanded", String(!isExpanded));
                if (!panel.classList.contains("show")) {
                    clearStatus(panel.querySelector('.status'));
                }
            });
        }
    });

    // --- BACKEND INTEGRATION LOGIC ---
    // *** THIS IS THE UPDATED LINE ***
    const API_BASE_URL = 'http://localhost:5001'; // The address of your Flask server

    /**
     * Handles fetching the report from the backend and triggering the download.
     * @param {string} endpoint - The API endpoint (e.g., '/report/daily_summary').
     * @param {object|null} params - Query parameters for the request (e.g., { date: '2025-08-10' }).
     * @param {HTMLElement} button - The button element that was clicked.
     * @param {HTMLElement} statusEl - The status message element for this tile.
     */
    async function fetchAndDownloadReport(endpoint, params, button, statusEl) {
        const url = new URL(`${API_BASE_URL}${endpoint}`);
        if (params) {
            Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        }

        showLoader(button, true);
        updateStatus(statusEl, "Connecting to server and generating report...", "info");

        try {
            const response = await fetch(url);

            // Handle API errors (e.g., no data for the selected date)
            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = errorData.error || `Request failed (Status: ${response.status}).`;
                updateStatus(statusEl, errorMessage, "error");
                return; // Stop execution
            }

            // Handle successful file download
            const blob = await response.blob();
            // Extract filename from the 'Content-Disposition' header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'report.xlsx'; // A default filename
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
                if (filenameMatch && filenameMatch.length > 1) {
                    filename = filenameMatch[1];
                }
            }

            // Create a temporary link and trigger the browser download
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();

            // Clean up the temporary link and URL
            document.body.removeChild(link);
            window.URL.revokeObjectURL(link.href);
            updateStatus(statusEl, `Success! Your report "${filename}" has started downloading.`, "success");

        } catch (error) {
            console.error("Fetch error:", error);
            updateStatus(statusEl, "Connection Error: Could not connect to the backend server. Please ensure it is running.", "error");
        } finally {
            showLoader(button, false);
        }
    }

    // 1. Number of Students Tile
    // 1. Custom Date Report Tile
const studentsTile = document.getElementById("studentsTile");
if (studentsTile) {
    const submitBtn = studentsTile.querySelector(".submitBtn");
    const startDateInput = studentsTile.querySelector("#startDate");
    const endDateInput = studentsTile.querySelector("#endDate");
    const status = studentsTile.querySelector(".status");
    submitBtn.addEventListener("click", () => {
        if (!startDateInput.value || !endDateInput.value) {
            updateStatus(status, "Please select both starting and end dates.", "error");
            return;
        }
        if (new Date(startDateInput.value) > new Date(endDateInput.value)) {
            updateStatus(status, "Starting date cannot be later than end date.", "error");
            return;
        }
        fetchAndDownloadReport('/report/custom_date_range', { start_date: startDateInput.value, end_date: endDateInput.value }, submitBtn, status);
    });
}
    // 2. Daily Summarized Report Tile
    const dailyReportTile = document.getElementById("dailyReportTile");
    if (dailyReportTile) {
        const submitBtn = dailyReportTile.querySelector(".submitBtn");
        const dateInput = dailyReportTile.querySelector(".dateInput");
        const status = dailyReportTile.querySelector(".status");
        submitBtn.addEventListener("click", () => {
            if (!dateInput.value) {
                updateStatus(status, "Please select a date first.", "error");
                return;
            }
            fetchAndDownloadReport('/report/daily_summary', { date: dateInput.value }, submitBtn, status);
        });
    }

    // 3. Weekly Report Tile
    const weeklyReportTile = document.getElementById("weeklyReportTile");
    if (weeklyReportTile) {
        const submitBtn = weeklyReportTile.querySelector(".submitBtn");
        const dateInput = weeklyReportTile.querySelector(".dateInput");
        const status = weeklyReportTile.querySelector(".status");
        submitBtn.addEventListener("click", () => {
            if (!dateInput.value) {
                updateStatus(status, "Please select a date first.", "error");
                return;
            }
            fetchAndDownloadReport('/report/weekly_summary', { date: dateInput.value }, submitBtn, status);
        });
    }

    // 4. Download Full Log Tile
    const excelTile = document.getElementById("excelTile");
    if (excelTile) {
        const downloadBtn = excelTile.querySelector(".downloadBtn");
        const status = excelTile.querySelector(".status");
        downloadBtn.addEventListener("click", () => {
            fetchAndDownloadReport('/report/full_log_dump', null, downloadBtn, status);
        });
    }
});
