document.addEventListener("DOMContentLoaded", () => {
    // --- DATE & CLOCK LOGIC ---
    const clockElement = document.getElementById("digital-clock");
    const dateElement = document.getElementById("digital-date");

    function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateString = now.toLocaleDateString('en-US', dateOptions);

        if (clockElement) { clockElement.textContent = `${hours}:${minutes}:${seconds}`; }
        if (dateElement) { dateElement.textContent = dateString; }
    }
    setInterval(updateClock, 1000);
    updateClock();
    // --- END OF DATE & CLOCK LOGIC ---

    // ===== LOGIN OVERLAY SYSTEM =====
    const loginOverlay = document.getElementById("login-overlay");
    const loginId = document.getElementById("login-id");
    const loginPass = document.getElementById("login-pass");
    const loginBtn = document.getElementById("login-submit");
    const loginError = document.getElementById("login-error");

    let failedAttempts = 0;
    let lockoutUntil = null;

    const sessionData = JSON.parse(localStorage.getItem("studentSession"));
    if (sessionData && new Date(sessionData.expiry) > new Date()) {
        loginOverlay.style.display = "none"; // Already logged in today
        initMainUI();
    } else {
        loginOverlay.style.display = "flex"; // Show login
    }

    loginBtn.addEventListener("click", () => {
        if (lockoutUntil && Date.now() < lockoutUntil) {
            const remaining = Math.ceil((lockoutUntil - Date.now()) / 1000);
            loginError.textContent = `Locked out. Try again in ${remaining} seconds.`;
            return;
        }

        const id = loginId.value.trim();
        const pass = loginPass.value.trim();

        if (!id || !pass) {
            loginError.textContent = "Enter ID and password.";
            return;
        }

        fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, pass })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    failedAttempts = 0;
                    const expiry = new Date();
                    expiry.setHours(23, 59, 59, 999);
                    localStorage.setItem("studentSession", JSON.stringify({ id, expiry }));
                    loginOverlay.style.display = "none";
                    initMainUI();
                } else {
                    failedAttempts++;
                    loginError.textContent = "Invalid credentials.";
                    if (failedAttempts >= 5) {
                        lockoutUntil = Date.now() + 15 * 60 * 1000;
                        startCountdown();
                    }
                }
            })
            .catch(err => {
                loginError.textContent = "Login failed.";
                console.error(err);
            });
    });

    function startCountdown() {
        const timer = setInterval(() => {
            const remaining = Math.ceil((lockoutUntil - Date.now()) / 1000);
            if (remaining <= 0) {
                clearInterval(timer);
                loginError.textContent = "";
                failedAttempts = 0;
            } else {
                loginError.textContent = `Locked out. Try again in ${remaining} seconds.`;
            }
        }, 1000);
    }

    // --- LIVE STATS (NEW) ---
    function updateLiveStats() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('entries-today').textContent = data.total_entries_today;
                document.getElementById('currently-inside').textContent = data.currently_inside;
                document.getElementById('peak-hour').textContent = data.peak_hour_today;
            })
            .catch(error => console.error('Error fetching live stats:', error));
    }

    updateLiveStats();
    setInterval(updateLiveStats, 15000);
    // ===== MAIN UI INITIALIZATION =====
    function initMainUI() {
        const logo = document.getElementById("logo");
        const loginPanel = document.getElementById("loginPanel");
        const roleSelection = document.getElementById("roleSelection");
        const roleOptions = document.querySelectorAll(".role-option");
        // const reasonSelection = document.getElementById("reasonSelection");
        const reasonOptions = document.querySelectorAll(".reason-option");
        const enrollment = document.getElementById("enrollment");
        const enrollInput = document.getElementById("enrollInput");
        const submitBtn = document.getElementById("submitBtn");
        const enrollError = document.getElementById("enrollError");
        const enrollForm = document.getElementById("enrollForm");
        const hiddenRole = document.getElementById("hiddenRole");
        const hiddenReason = document.getElementById("hiddenReason");
        const hiddenEnroll = document.getElementById("hiddenEnroll");

        let step = 0; // 0: idle, 1: role, 2: enrollment, 3: reason
        let selectedRoleIndex = 0;
        let selectedReasonIndex = 0;

        function updateHighlight(options, selectedIndex) {
            options.forEach((opt, idx) => {
                opt.classList.toggle("selected", idx === selectedIndex);
            });
        }

        function addHoverListeners(options, getSelectedIndex, updateFunction) {
            options.forEach(option => {
                option.addEventListener("mouseenter", () => {
                    options.forEach(opt => opt.classList.remove("selected"));
                    option.classList.add("hovered");
                });
                option.addEventListener("mouseleave", () => {
                    option.classList.remove("hovered");
                    updateFunction(options, getSelectedIndex());
                });
            });
        }
        addHoverListeners(roleOptions, () => selectedRoleIndex, updateHighlight);
        addHoverListeners(reasonOptions, () => selectedReasonIndex, updateHighlight);

        function showPanel(panelToShow) {
            [roleSelection, enrollment].forEach(panel => {
                panel.classList.toggle("hidden", panel !== panelToShow);
            });
        }

        function showLoginPanel() {
            if (step !== 0) return;
            logo.style.transform = "scale(1.2)";
            setTimeout(() => {
                loginPanel.classList.add("visible");
                showPanel(roleSelection);
                step = 1;
            }, 400);
        }

        function hideLoginPanel() {
            loginPanel.classList.remove("visible");
            setTimeout(() => {
                logo.style.transform = "scale(1)";
                enrollInput.value = "";
                enrollError.textContent = "";
                step = 0;
                selectedRoleIndex = 0;
                selectedReasonIndex = 0;
                updateHighlight(roleOptions, selectedRoleIndex);
                updateHighlight(reasonOptions, selectedReasonIndex);
                showPanel(null);
            }, 500);
        }

        enrollInput.addEventListener("input", () => {
            const selectedRole = roleOptions[selectedRoleIndex].dataset.role;
            const maxLength = selectedRole === 'Student' ? 5 : 4;
            enrollInput.value = enrollInput.value.replace(/\D/g, "").slice(0, maxLength);
            enrollError.textContent = "";
        });

        submitBtn.addEventListener("click", () => {
            const selectedRole = roleOptions[selectedRoleIndex].dataset.role;
            const expectedLength = selectedRole === 'Student' ? 5 : 4;
            const value = enrollInput.value;

            if (value.length !== expectedLength) {
                enrollError.textContent = `Please enter exactly ${expectedLength} digits.`;
                return;
            }

            enrollError.textContent = "";

            // Prepare form data to check user status
           const formData = new FormData();
            formData.append('registry_last_digits', value);
            formData.append('role', selectedRole);

            fetch('/check-status', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // No matter if user is inside or outside, the action is the same: submit the main form.
                        // The backend /check route will handle both entry and exit.
                        hiddenEnroll.value = value;
                        hiddenRole.value = selectedRole;
                        enrollForm.submit();
                    } else {
                        enrollError.textContent = data.error || "Invalid user or role.";
                    }
                })
                .catch(error => {
                    enrollError.textContent = "System error. Please try again.";
                    console.error(error);
                });
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") { hideLoginPanel(); return; }
            if (step === 0 && e.key === "Enter") { showLoginPanel(); return; }
            if (!loginPanel.classList.contains('visible')) return;

            if (e.key === "Enter") {
                e.preventDefault();
                if (step === 1) {
                    showPanel(enrollment);
                    enrollInput.focus();
                    step = 2;
                } else if (step === 2) {
                    submitBtn.click();
                } else if (step === 3) {
                    reasonOptions[selectedReasonIndex].click();
                }
            }

            if (step === 1) {
                if (e.key === "ArrowDown") selectedRoleIndex = (selectedRoleIndex + 1) % roleOptions.length;
                if (e.key === "ArrowUp") selectedRoleIndex = (selectedRoleIndex - 1 + roleOptions.length) % roleOptions.length;
                updateHighlight(roleOptions, selectedRoleIndex);
            } else if (step === 3) {
                if (e.key === "ArrowDown") selectedReasonIndex = (selectedReasonIndex + 1) % reasonOptions.length;
                if (e.key === "ArrowUp") selectedReasonIndex = (selectedReasonIndex - 1 + reasonOptions.length) % reasonOptions.length;
                updateHighlight(reasonOptions, selectedReasonIndex);
            }
        });

        logo.addEventListener("click", showLoginPanel);

        roleOptions.forEach((option, idx) => {
            option.addEventListener("click", () => {
                selectedRoleIndex = idx;
                updateHighlight(roleOptions, selectedRoleIndex);
                setTimeout(() => {
                    showPanel(enrollment);
                    enrollInput.focus();
                    step = 2;
                }, 200);
            });
        });

        reasonOptions.forEach((option, idx) => {
            option.addEventListener("click", () => {
                selectedReasonIndex = idx;
                updateHighlight(reasonOptions, selectedReasonIndex);
                hiddenRole.value = roleOptions[selectedRoleIndex].dataset.role;
                hiddenReason.value = reasonOptions[selectedReasonIndex].dataset.reason;
                hiddenEnroll.value = enrollInput.value;
                enrollForm.submit();
            });
        });

        const toast = document.getElementById("toast");
        if (toast) {
            const message = toast.getAttribute("data-message");
            const isError = toast.getAttribute("data-type") === "error";
            if (message) {
                toast.textContent = message;
                toast.style.backgroundColor = isError ? "#d9534f" : "#4169e1";
                toast.classList.add("show");
                setTimeout(() => toast.classList.remove("show"), 4000);
            }
        }
    }
});
