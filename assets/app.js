/**
 * Vertex Design Pricing Portal v4.0
 * Refactored: Modular structure, external config loading
 * Packages aligned: A (Concept), B (Full Design), C (Rollout)
 */

'use strict';

// ============================================
// AUTHENTICATION & USER SESSION
// ============================================

const AuthManager = {
    // Check if user is logged in, redirect to login page if not
    checkAuth() {
        const user = this.getUser();
        if (!user) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    },

    // Get current user from session
    getUser() {
        try {
            const userData = sessionStorage.getItem('vertex_user');
            return userData ? JSON.parse(userData) : null;
        } catch (e) {
            return null;
        }
    },

    // Get user's discount rate (0-1)
    getDiscount() {
        const user = this.getUser();
        return user?.discount || 0;
    },

    // Check if user has discount
    hasDiscount() {
        return this.getDiscount() > 0;
    },

    // Get discount percentage for display
    getDiscountPercent() {
        return Math.round(this.getDiscount() * 100);
    },

    // Apply discount to amount
    applyDiscount(amount) {
        const discount = this.getDiscount();
        return Math.round(amount * (1 - discount));
    },

    // Update UI with user info
    updateUserUI() {
        const user = this.getUser();
        if (!user) return;

        const userNameEl = document.getElementById('user-name');
        const discountBadgeEl = document.getElementById('discount-badge');
        const logoutBtn = document.getElementById('logout-btn');
        const adminDiscountControl = document.getElementById('admin-discount-control');
        const adminDiscountInput = document.getElementById('admin-discount-input');

        if (userNameEl) {
            userNameEl.textContent = user.displayName || 'Guest';
        }

        if (discountBadgeEl) {
            if (user.discount > 0) {
                discountBadgeEl.textContent = `${Math.round(user.discount * 100)}% OFF`;
                discountBadgeEl.hidden = false;
            } else {
                discountBadgeEl.hidden = true;
            }
        }

        // Show admin discount control for admin users
        if (adminDiscountControl && this.isAdmin()) {
            adminDiscountControl.hidden = false;

            // Bind admin discount input event
            if (adminDiscountInput) {
                adminDiscountInput.addEventListener('change', () => {
                    const discountPercent = Math.min(50, Math.max(0, parseInt(adminDiscountInput.value) || 0));
                    adminDiscountInput.value = discountPercent;
                    AppState.customDiscount = discountPercent / 100;

                    // Update discount badge to show admin-set discount
                    if (discountBadgeEl) {
                        if (discountPercent > 0) {
                            discountBadgeEl.textContent = `${discountPercent}% OFF`;
                            discountBadgeEl.hidden = false;
                        } else {
                            discountBadgeEl.hidden = true;
                        }
                    }

                    // Recalculate if quote exists
                    updateSummaryPanel();
                    if (typeof calculateQuote === 'function' && AppState.classification) {
                        calculateQuote();
                    }
                });
            }
        }

        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
    },

    // Logout and redirect to login
    logout() {
        sessionStorage.removeItem('vertex_user');
        window.location.href = 'login.html';
    },

    // Check if user is admin
    isAdmin() {
        const user = this.getUser();
        return user?.role === 'admin';
    }
};

// ============================================
// FALLBACK PRICING CONFIGURATION
// ============================================

const DEFAULT_CONFIG = {
    version: "4.0.0",
    currency: "KWD",
    vat_rate: 0,
    offer_validity_days: 14,

    thresholds: {
        size: {
            small: { maxArea: 100, maxSpaces: 4 },
            medium: { maxArea: 350, maxSpaces: 10 },
            large: { maxArea: Infinity, maxSpaces: Infinity }
        },
        complexity: {
            typeMap: {
                retail: "normal",
                office: "normal",
                showroom: "normal",
                fnb: "complex",
                clinic: "complex",
                salon: "normal",
                gym: "normal",
                hospital: "complex",
                datacenter: "complex",
                other: "normal"
            }
        },
        scale: {
            single: { maxSites: 1 },
            multi: { maxSites: 5 },
            rollout: { maxSites: Infinity }
        }
    },

    multipliers: {
        size: { small: 1.0, medium: 1.15, large: 1.3 },
        complexity: { simple: 0.85, normal: 1.0, complex: 1.25 },
        facade: { F0: 1.0, F1: 1.10, F2: 1.20, F3: 1.35 }
    },

    services: {
        S1: { name: "Design Visualization", ratePerSqm: 3.5, minFee: 400, durationWeeks: 1.5 },
        S2: { name: "Architectural Design Package", ratePerSqm: 6.0, minFee: 600, durationWeeks: 2.5 },
        S3: { name: "MEP Design Package", ratePerSqm: 2.5, minFee: 350, durationWeeks: 1.5 },
        S4: { name: "Material & Detail Specs", ratePerSqm: 2.0, minFee: 300, durationWeeks: 1.5 },
        S5: { name: "Tender Documentation", ratePerSqm: 1.5, minFee: 250, durationWeeks: 1 },
        S6: { name: "BOQ & Cost Documentation", ratePerSqm: 2.0, minFee: 300, durationWeeks: 1 },
        SF1: { name: "Façade Design & Detailing", ratePerSqm: 3.0, minFee: 400, durationWeeks: 1.5 },
        SF2: { name: "Signage & Branding Integration", ratePerSqm: 1.5, minFee: 250, durationWeeks: 1 }
    },

    addons: {
        extra_renders: { price: 80, unit: "per view" },
        extra_revisions: { price: 150, unit: "per round" },
        authority_submission: { price: 600, unit: "flat" },
        site_visits: { price: 50, unit: "per visit" },
        fast_track: { percent: 15 }
    },

    // Package definitions - ALIGNED TO CONFIG A/B/C
    packages: {
        A: {
            name: "Package A – Concept",
            description: "Brief, layouts, concept design and budget estimate.",
            services: ["S1", "S2"]
        },
        B: {
            name: "Package B – Full Design",
            description: "Full design development with tender-ready drawings, specs, and coordination.",
            services: ["S1", "S2", "S3", "S4", "S5"]
        },
        C: {
            name: "Package C – Rollout Kit",
            description: "Standardized design kit for multi-location deployments.",
            services: ["S1", "S2", "S3", "S4", "S5", "S6"]
        },
        custom: {
            name: "⭐ Customize Your Package (Recommended)",
            description: "Select individual services below to create a custom scope.",
            services: null
        }
    },

    rollout: {
        adaptationPercent: { new: 100, adapted: 40, replica: 15 },
        minPerSite: 300
    },

    revisions: {
        included: 2,
        note: "Additional revisions available at additional cost."
    },

    paymentTerms: {
        milestones: [
            { label: "Upon signing", percent: 50 },
            { label: "Design approval", percent: 30 },
            { label: "Final delivery", percent: 20 }
        ],
        netDays: 7
    },

    assumptions: [
        "Client provides base drawings or survey measurement",
        "Project information provided at kickoff",
        "Timely feedback (within 5 working days)",
        "Standard construction methods applicable"
    ],

    exclusions: [
        "Site surveys and measurements",
        "Municipality/authority approvals",
        "Structural engineering calculations",
        "Specialty consultant fees",
        "Construction/project management"
    ],

    company: {
        name: "Vertex Design Buildings General Contracting Co.",
        address: "Salmiya Block 4, Salem Al-Mubarak Street, Tala Center, Mezzanine Floor, Office 6, Kuwait",
        tel: "+965 2571 2021",
        mobile: "+965 9721 9663",
        email: "info@VertexDesignkw.com"
    }
};

// ============================================
// GLOBAL STATE
// ============================================

let CONFIG = { ...DEFAULT_CONFIG };

const AppState = {
    currentStep: 1,
    classification: null,
    quote: null,
    quoteHistory: [],
    configLoaded: false,
    elements: {}
};

// ============================================
// CONFIG LOADER
// ============================================

async function loadConfig() {
    try {
        const response = await fetch('assets/config.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const externalConfig = await response.json();

        // Merge external config with defaults (external takes precedence)
        CONFIG = mergeConfig(DEFAULT_CONFIG, externalConfig);
        AppState.configLoaded = true;

        console.log(`Config loaded: v${CONFIG.version}`);
        hideConfigWarning();

    } catch (error) {
        console.warn('External config not loaded, using defaults:', error.message);
        showConfigWarning('Using default configuration. External config.json could not be loaded.');
    }
}

function mergeConfig(defaults, external) {
    const merged = { ...defaults };

    for (const key in external) {
        if (external.hasOwnProperty(key)) {
            if (typeof external[key] === 'object' && !Array.isArray(external[key]) && external[key] !== null) {
                merged[key] = mergeConfig(defaults[key] || {}, external[key]);
            } else {
                merged[key] = external[key];
            }
        }
    }

    return merged;
}

function showConfigWarning(message) {
    const banner = document.getElementById('config-warning');
    if (banner) {
        banner.textContent = message;
        banner.hidden = false;
    }
}

function hideConfigWarning() {
    const banner = document.getElementById('config-warning');
    if (banner) {
        banner.hidden = true;
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener("DOMContentLoaded", async () => {
    // Check authentication first
    if (!AuthManager.checkAuth()) return;

    // Update user UI (name, discount badge, logout)
    AuthManager.updateUserUI();

    cacheElements();
    await loadConfig();
    loadQuoteHistory();
    bindEvents();
    setOfferDate();
    generateQuoteId();
    updateFacadeVisibility();
    updateReuseVisibility();
    updateSpecialSystems();
    applyPackage("B"); // Default to Package B
    updateSummaryPanel();
});

function cacheElements() {
    AppState.elements = {
        form: document.getElementById("pricing-form"),
        feedback: document.getElementById("form-feedback"),
        wizardSteps: document.querySelectorAll(".wizard-step"),
        formSteps: document.querySelectorAll(".form-step"),
        facadeDetails: document.getElementById("facade-details"),
        facadeServices: document.getElementById("facade-services"),
        reuseLabel: document.getElementById("reuse-label"),
        offerOutput: document.getElementById("offer-output"),
        offerText: document.getElementById("offer-text"),
        quoteHistory: document.getElementById("quote-history"),
        tooltipContainer: document.getElementById("tooltip-container"),
        specialSystemsGroup: document.getElementById("special-systems-group"),
        packageType: document.getElementById("package-type"),
        packageDescription: document.getElementById("package-description"),
        floatingAmount: document.getElementById("floating-amount"),
        floatingTotal: document.getElementById("floating-total"),
        // Sticky summary panel
        summaryTotal: document.getElementById("summary-total"),
        summaryTimeline: document.getElementById("summary-timeline"),
        summaryPackage: document.getElementById("summary-package"),
        summarySize: document.getElementById("summary-size"),
        summaryComplexity: document.getElementById("summary-complexity"),
        summaryServices: document.getElementById("summary-services"),
        summaryCta: document.getElementById("summary-cta-btn"),
        summaryCard: document.getElementById("summary-card"),
        // Floating action bar for proposal page
        proposalFloatingBar: document.getElementById("proposal-floating-bar")
    };
}

function bindEvents() {
    const { form } = AppState.elements;
    if (!form) return;

    // Navigation
    document.querySelectorAll("[data-next]").forEach(btn => {
        btn.addEventListener("click", () => {
            const next = parseInt(btn.dataset.next, 10);
            if (validateStep(AppState.currentStep)) {
                if (next === 2) updateClassification();
                if (next === 3) updateServicePrices();
                if (next === 4) calculateQuote();
                if (next === 5) generateProposal();
                goToStep(next);
            }
        });
    });

    document.querySelectorAll("[data-prev]").forEach(btn => {
        btn.addEventListener("click", () => {
            goToStep(parseInt(btn.dataset.prev, 10));
        });
    });

    // Summary CTA button
    AppState.elements.summaryCta?.addEventListener("click", () => {
        const next = AppState.currentStep + 1;
        if (next <= 5 && validateStep(AppState.currentStep)) {
            if (next === 2) updateClassification();
            if (next === 3) updateServicePrices();
            if (next === 4) calculateQuote();
            if (next === 5) generateProposal();
            goToStep(next);
        }
    });

    // Façade type toggle
    form.querySelectorAll("input[name='facadeType']").forEach(radio => {
        radio.addEventListener("change", () => {
            updateFacadeVisibility();
            updateSummaryPanel();
        });
    });

    // Sites count toggle for reuse
    const sitesInput = form.elements["sites"];
    sitesInput?.addEventListener("input", () => {
        updateReuseVisibility();
        updateSummaryPanel();
    });

    // Area input change
    form.elements["area"]?.addEventListener("input", debounce(() => {
        updateSummaryPanel();
    }, 300));

    // Spaces input change
    form.elements["spaces"]?.addEventListener("input", debounce(() => {
        updateSummaryPanel();
    }, 300));

    // Override acknowledge
    const overrideAck = document.getElementById("override-acknowledge");
    overrideAck?.addEventListener("change", (e) => {
        const fields = document.getElementById("override-fields");
        if (fields) fields.hidden = !e.target.checked;
    });

    // Package dropdown
    AppState.elements.packageType?.addEventListener("change", (e) => {
        applyPackage(e.target.value);
    });

    // Project type change - update special systems
    form.elements["projectType"]?.addEventListener("change", () => {
        updateSpecialSystems();
        updateSummaryPanel();
    });

    // Addon quantity toggles
    form.querySelectorAll("input[name='addons']").forEach(checkbox => {
        checkbox.addEventListener("change", () => {
            const qtyInput = checkbox.closest("label")?.querySelector(".addon-qty");
            if (qtyInput) {
                qtyInput.disabled = !checkbox.checked;
                if (checkbox.checked && parseInt(qtyInput.value) === 0) {
                    qtyInput.value = 1;
                }
            }
            updateFloatingTotal();
            updateSummaryPanel();
        });
    });

    // Addon quantity input changes
    form.querySelectorAll(".addon-qty").forEach(input => {
        input.addEventListener("input", debounce(() => {
            updateFloatingTotal();
            updateSummaryPanel();
        }, 200));
    });

    // Service checkboxes update pricing and floating total
    const serviceCheckboxes = form.querySelectorAll("input[name='services']");
    console.log('[DEBUG] Found', serviceCheckboxes.length, 'service checkboxes');
    serviceCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            console.log('[DEBUG] Service checkbox changed:', cb.value, 'checked:', cb.checked);
            updateServicePrices();
            updateFloatingTotal();
            updateSummaryPanel();
        });
    });

    // Action buttons
    document.getElementById("download-pdf")?.addEventListener("click", downloadPdf);
    document.getElementById("print-offer")?.addEventListener("click", () => window.print());
    document.getElementById("copy-offer")?.addEventListener("click", copyOfferText);
    document.getElementById("save-quote")?.addEventListener("click", saveQuote);
    document.getElementById("new-quote")?.addEventListener("click", resetForm);

    // Tooltips
    document.querySelectorAll(".tooltip-trigger").forEach(trigger => {
        trigger.addEventListener("mouseenter", showTooltip);
        trigger.addEventListener("focus", showTooltip);
        trigger.addEventListener("mouseleave", hideTooltip);
        trigger.addEventListener("blur", hideTooltip);
    });
}

// ============================================
// WIZARD NAVIGATION
// ============================================

function goToStep(step) {
    AppState.currentStep = step;

    AppState.elements.wizardSteps?.forEach(ws => {
        const stepNum = parseInt(ws.dataset.step, 10);
        ws.classList.toggle("active", stepNum === step);
        ws.classList.toggle("completed", stepNum < step);
    });

    AppState.elements.formSteps?.forEach(fs => {
        fs.classList.toggle("active", fs.id === `step-${step}`);
    });

    // Show/hide floating total (only on step 3)
    if (AppState.elements.floatingTotal) {
        AppState.elements.floatingTotal.style.display = step === 3 ? "block" : "none";
    }

    // Show/hide summary card (only on step 3 and 4)
    if (AppState.elements.summaryCard) {
        AppState.elements.summaryCard.hidden = step < 3 || step > 4;
    }

    // Show/hide floating action bar (only on step 5)
    if (AppState.elements.proposalFloatingBar) {
        AppState.elements.proposalFloatingBar.classList.toggle("visible", step === 5);
    }

    // Update summary CTA button text
    updateSummaryCta(step);

    // Focus first input
    const activeStep = document.getElementById(`step-${step}`);
    const firstInput = activeStep?.querySelector("input:not([type='hidden']):not([type='checkbox']):not([type='radio']), select");
    if (firstInput) setTimeout(() => firstInput.focus(), 100);

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateSummaryCta(step) {
    const btn = AppState.elements.summaryCta;
    if (!btn) return;

    const labels = {
        1: "Continue to Classification",
        2: "Select Services",
        3: "View Quote",
        4: "Generate Proposal",
        5: "Complete"
    };

    btn.textContent = labels[step] || "Continue";
    btn.disabled = step >= 5;
}

function validateStep(step) {
    showFeedback("", false);
    const form = AppState.elements.form;
    if (!form) return false;

    if (step === 1) {
        const area = sanitize(form.elements["area"]?.value, 10, 50000);
        const spaces = sanitize(form.elements["spaces"]?.value, 1, 100);
        const projectType = form.elements["projectType"]?.value;

        if (area < 10) {
            showFeedback("Please enter a valid area (minimum 10 sqm).", true);
            form.elements["area"]?.focus();
            return false;
        }
        if (spaces < 1) {
            showFeedback("Please enter at least 1 space.", true);
            form.elements["spaces"]?.focus();
            return false;
        }
        if (!projectType) {
            showFeedback("Please select a project type.", true);
            form.elements["projectType"]?.focus();
            return false;
        }
    }

    if (step === 3) {
        const services = getSelectedServices();
        if (services.length === 0) {
            showFeedback("Please select at least one service.", true);
            return false;
        }
    }

    return true;
}

// ============================================
// CLASSIFICATION ENGINE
// ============================================

function updateClassification() {
    const form = AppState.elements.form;
    if (!form) return;

    const data = getFormData();
    const classification = deriveClassification(data);
    AppState.classification = classification;

    updateClassificationUI(classification);
    updateSummaryPanel();
}

function deriveClassification(data) {
    const th = CONFIG.thresholds;

    // SIZE
    let sizeClass = "large";
    let sizeReason = `${data.area} sqm + ${data.spaces} spaces`;
    if (data.area <= th.size.small.maxArea && data.spaces <= th.size.small.maxSpaces) {
        sizeClass = "small";
        sizeReason += " → Small";
    } else if (data.area <= th.size.medium.maxArea && data.spaces <= th.size.medium.maxSpaces) {
        sizeClass = "medium";
        sizeReason += " → Medium";
    } else {
        sizeReason += " → Large";
    }

    // COMPLEXITY
    const baseComplexity = th.complexity.typeMap[data.projectType] || "normal";
    const systemCount = data.specialSystems.length;
    let complexityClass = baseComplexity;
    let complexityReason = `${capitalize(data.projectType)}`;

    if (baseComplexity === "normal" && systemCount >= 2) {
        complexityClass = "complex";
        complexityReason += ` + ${systemCount} special systems → Complex`;
    } else if (baseComplexity === "complex") {
        complexityReason += " (inherently complex)";
    } else if (systemCount > 0) {
        complexityReason += ` + ${systemCount} system(s)`;
    }

    // Allow simple only for basic retail/office with no systems
    if (baseComplexity === "normal" && systemCount === 0 && data.area < 100) {
        complexityClass = "simple";
        complexityReason = `Basic ${data.projectType}, small area → Simple`;
    }

    // SCALE
    let scaleClass = "single";
    let scaleReason = `${data.sites} site(s)`;
    if (data.sites > th.scale.multi.maxSites) {
        scaleClass = "rollout";
        scaleReason += " → Rollout";
    } else if (data.sites > th.scale.single.maxSites) {
        scaleClass = "multi";
        scaleReason += " → Multi-site";
    } else {
        scaleReason += " → Single";
    }

    // FAÇADE
    const facadeMap = { none: "F0", frontage: "F1", enhanced: "F2", full: "F3" };
    const facadeType = data.facadeType || "none";
    const facadeClass = facadeMap[facadeType] || "F0";
    const facadeLabels = { F0: "Interior Only", F1: "Mall Frontage", F2: "Enhanced", F3: "Full Façade" };
    const facadeReason = facadeLabels[facadeClass];

    return {
        size: { value: sizeClass, reason: sizeReason },
        complexity: { value: complexityClass, reason: complexityReason },
        scale: { value: scaleClass, reason: scaleReason },
        facade: { value: facadeClass, reason: facadeReason }
    };
}

function updateClassificationUI(c) {
    document.getElementById("derived-size").textContent = capitalize(c.size.value);
    document.getElementById("reason-size").textContent = c.size.reason;

    document.getElementById("derived-complexity").textContent = capitalize(c.complexity.value);
    document.getElementById("reason-complexity").textContent = c.complexity.reason;

    document.getElementById("derived-scale").textContent = capitalize(c.scale.value);
    document.getElementById("reason-scale").textContent = c.scale.reason;

    document.getElementById("derived-facade").textContent = c.facade.value;
    document.getElementById("reason-facade").textContent = c.facade.reason;
}

// ============================================
// SERVICE PRICING ENGINE
// ============================================

function updateServicePrices() {
    if (!AppState.classification) updateClassification();

    const data = getFormData();
    const c = AppState.classification;
    const mult = CONFIG.multipliers;

    // Complexity multiplier (still based on project type)
    const complexMult = mult.complexity[c.complexity.value] || 1;

    // Façade multiplier applies only to façade services
    const facadeMult = mult.facade[c.facade.value] || 1;

    document.querySelectorAll(".service-price").forEach(el => {
        const serviceId = el.dataset.service;
        const service = CONFIG.services[serviceId];
        if (!service) return;

        // Use the new calculateServiceFee function
        let subtotal = calculateServiceFee(serviceId, data.area, complexMult);

        // Apply façade multiplier for façade services
        if (serviceId.startsWith("SF")) {
            subtotal = Math.round(subtotal * facadeMult);
        }

        el.textContent = formatCurrency(subtotal);
    });

    // Show/hide façade services
    const facadeServices = AppState.elements.facadeServices;
    if (facadeServices) {
        facadeServices.hidden = c.facade.value === "F0";
    }
}

function getTierMultiplier(area) {
    // Tiered rate multipliers - economies of scale
    // Smaller projects pay premium, larger projects get volume discount
    if (area <= 100) return 1.15;      // Small project premium
    if (area <= 300) return 1.0;       // Standard rate
    if (area <= 600) return 0.92;      // Volume discount
    if (area <= 1000) return 0.85;     // Scale efficiency
    return 0.78;                        // Major project discount
}

function calculateServiceFee(serviceId, area, complexityMult) {
    const service = CONFIG.services[serviceId];
    if (!service) return 0;

    const tierMult = getTierMultiplier(area);

    // Calculate area-based fee: area × rate × tier × complexity
    const areaFee = area * service.ratePerSqm * tierMult * complexityMult;

    // Apply minimum fee guarantee
    return Math.round(Math.max(areaFee, service.minFee));
}

// ============================================
// QUOTE CALCULATION
// ============================================

function calculateQuote() {
    const data = getFormData();
    const c = AppState.classification;
    if (!c) updateClassification();

    const mult = CONFIG.multipliers;
    const complexMult = mult.complexity[c.complexity.value] || 1;
    const facadeMult = mult.facade[c.facade.value] || 1;

    // Services - now using area-based calculation
    const selectedServices = getSelectedServices();
    const servicesBreakdown = selectedServices.map(id => {
        const s = CONFIG.services[id];
        let subtotal = calculateServiceFee(id, data.area, complexMult);

        // Apply façade multiplier for façade services
        if (id.startsWith("SF")) {
            subtotal = Math.round(subtotal * facadeMult);
        }

        return {
            id,
            name: s.name,
            ratePerSqm: s.ratePerSqm,
            area: data.area,
            subtotal,
            duration: s.durationWeeks
        };
    });
    const servicesTotal = servicesBreakdown.reduce((sum, s) => sum + s.subtotal, 0);

    // Addons
    const addonsBreakdown = [];
    let addonsTotal = 0;

    const addonChecks = AppState.elements.form.querySelectorAll("input[name='addons']:checked");
    addonChecks.forEach(cb => {
        const key = cb.value;
        const addon = CONFIG.addons[key];
        if (!addon) return;

        if (key === "extra_renders") {
            const qty = sanitize(AppState.elements.form.elements["extraRenderCount"]?.value, 0, 20);
            const subtotal = addon.price * qty;
            addonsBreakdown.push({ name: "Additional renders", qty, price: addon.price, subtotal });
            addonsTotal += subtotal;
        } else if (key === "extra_revisions") {
            const qty = sanitize(AppState.elements.form.elements["extraRevisionCount"]?.value, 0, 10);
            const subtotal = addon.price * qty;
            addonsBreakdown.push({ name: "Extra revision rounds", qty, price: addon.price, subtotal });
            addonsTotal += subtotal;
        } else if (key === "authority_submission") {
            addonsBreakdown.push({ name: "Authority submission set", qty: 1, price: addon.price, subtotal: addon.price });
            addonsTotal += addon.price;
        } else if (key === "site_visits") {
            const qty = sanitize(AppState.elements.form.elements["siteVisitCount"]?.value, 0, 20);
            const subtotal = addon.price * qty;
            addonsBreakdown.push({ name: "Extra site visits", qty, price: addon.price, subtotal });
            addonsTotal += subtotal;
        }
    });

    // Fast-track
    const fastTrack = AppState.elements.form.querySelector("input[name='addons'][value='fast_track']")?.checked;
    let fastTrackAmount = 0;
    if (fastTrack) {
        fastTrackAmount = Math.round((servicesTotal + addonsTotal) * 0.15);
        addonsBreakdown.push({ name: "Fast-track delivery", qty: 1, price: "15%", subtotal: fastTrackAmount });
        addonsTotal += fastTrackAmount;
    }

    // Rollout
    let rolloutTotal = 0;
    let rolloutBreakdown = null;
    if (data.sites > 1) {
        const reuseLevel = data.reuseLevel;
        const adaptPct = CONFIG.rollout.adaptationPercent[reuseLevel] || 40;
        const minPerSite = CONFIG.rollout.minPerSite;
        const additionalSites = data.sites - 1;
        const perSiteFee = Math.max(minPerSite, Math.round(servicesTotal * (adaptPct / 100)));
        rolloutTotal = perSiteFee * additionalSites;
        rolloutBreakdown = {
            additionalSites,
            reuseLevel,
            adaptPct,
            perSiteFee,
            total: rolloutTotal
        };
    }

    // Totals (before discount)
    const subtotal = servicesTotal + addonsTotal + rolloutTotal;
    const vatRate = CONFIG.vat_rate;
    const vatAmount = vatRate > 0 ? Math.round(subtotal * (vatRate / 100)) : 0;
    const beforeDiscount = subtotal + vatAmount;

    // Apply discount (user auto-discount or admin custom discount)
    const discountRate = AppState.customDiscount !== undefined ? AppState.customDiscount : AuthManager.getDiscount();
    const discountPercent = Math.round(discountRate * 100);
    const discountAmount = discountRate > 0 ? Math.round(beforeDiscount * discountRate) : 0;
    const grandTotal = beforeDiscount - discountAmount;

    // Timeline
    const timeline = calculateTimeline(servicesBreakdown, fastTrack);

    AppState.quote = {
        data,
        classification: c,
        services: servicesBreakdown,
        servicesTotal,
        addons: addonsBreakdown,
        addonsTotal,
        rollout: rolloutBreakdown,
        rolloutTotal,
        subtotal,
        vatRate,
        vatAmount,
        beforeDiscount,
        discountRate,
        discountPercent,
        discountAmount,
        grandTotal,
        timeline,
        quoteId: document.getElementById("quote-id")?.textContent || generateQuoteId(),
        date: new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    };

    renderQuoteBreakdown(AppState.quote);
    updateSummaryPanel();
}

// ============================================
// TIMELINE ENGINE
// ============================================

function calculateTimeline(services, fastTrack) {
    const overlapFactor = 0.65;
    let totalWeeks = 0;

    services.forEach((s, i) => {
        if (i === 0) {
            totalWeeks = s.duration;
        } else {
            totalWeeks += s.duration * overlapFactor;
        }
    });

    if (fastTrack) {
        totalWeeks *= 0.75;
    }

    const minWeeks = Math.ceil(totalWeeks);
    const maxWeeks = Math.ceil(totalWeeks * 1.3);

    return {
        minWeeks,
        maxWeeks,
        label: `${minWeeks}-${maxWeeks} weeks`,
        note: "Timeline depends on timely approvals and feedback."
    };
}

// ============================================
// RENDER QUOTE BREAKDOWN
// ============================================

function renderQuoteBreakdown(quote) {
    // Header
    document.getElementById("quote-total").textContent = formatCurrency(quote.grandTotal);
    document.getElementById("quote-timeline").textContent = `Timeline: ${quote.timeline.label}`;

    // Services table
    const tbody = document.querySelector("#services-breakdown tbody");
    if (tbody) {
        tbody.innerHTML = quote.services.map(s => `
            <tr>
                <td>${escapeHtml(s.name)}</td>
                <td>${s.ratePerSqm ? `${s.ratePerSqm} KWD/sqm` : '-'}</td>
                <td>${s.area ? `${s.area} sqm` : '-'}</td>
                <td>${formatCurrency(s.subtotal)}</td>
            </tr>
        `).join("");
    }

    // Addons
    const addonsList = document.getElementById("addons-breakdown");
    const addonsSection = document.getElementById("addons-breakdown-section");
    if (addonsList && addonsSection) {
        if (quote.addons.length > 0) {
            addonsSection.hidden = false;
            addonsList.innerHTML = quote.addons.map(a => `
                <li><span>${escapeHtml(a.name)} ${a.qty > 1 ? `(×${a.qty})` : ''}</span><span>${formatCurrency(a.subtotal)}</span></li>
            `).join("");
        } else {
            addonsSection.hidden = true;
        }
    }

    // Rollout
    const rolloutSection = document.getElementById("rollout-breakdown-section");
    const rolloutP = document.getElementById("rollout-breakdown");
    if (rolloutSection && rolloutP) {
        if (quote.rollout) {
            rolloutSection.hidden = false;
            rolloutP.innerHTML = `${quote.rollout.additionalSites} additional site(s) @ ${formatCurrency(quote.rollout.perSiteFee)}/site (${quote.rollout.adaptPct}% adaptation) = <strong>${formatCurrency(quote.rollout.total)}</strong>`;
        } else {
            rolloutSection.hidden = true;
        }
    }

    // Summary
    document.getElementById("subtotal-services").textContent = formatCurrency(quote.servicesTotal);
    document.getElementById("subtotal-addons").textContent = formatCurrency(quote.addonsTotal);
    document.getElementById("subtotal-rollout").textContent = formatCurrency(quote.rolloutTotal);
    document.getElementById("total-before-vat").textContent = formatCurrency(quote.subtotal);

    const vatRow = document.getElementById("vat-row");
    if (vatRow) {
        if (quote.vatRate > 0) {
            vatRow.hidden = false;
            document.getElementById("vat-rate").textContent = quote.vatRate;
            document.getElementById("vat-amount").textContent = formatCurrency(quote.vatAmount);
        } else {
            vatRow.hidden = true;
        }
    }

    // Discount row
    const discountRow = document.getElementById("discount-row");
    if (discountRow) {
        if (quote.discountAmount > 0) {
            discountRow.hidden = false;
            discountRow.innerHTML = `
                <td colspan="3"><strong>Discount (${quote.discountPercent}%)</strong></td>
                <td class="discount-applied">- ${formatCurrency(quote.discountAmount)}</td>
            `;
        } else {
            discountRow.hidden = true;
        }
    }

    // Grand total - show original if discount applied
    const grandTotalEl = document.getElementById("grand-total");
    if (grandTotalEl) {
        if (quote.discountAmount > 0) {
            grandTotalEl.innerHTML = `
                <span class="discount-original">${formatCurrency(quote.beforeDiscount)}</span>
                <span class="discount-applied">${formatCurrency(quote.grandTotal)}</span>
            `;
        } else {
            grandTotalEl.textContent = formatCurrency(quote.grandTotal);
        }
    }

    // Pricing explanation
    renderPricingExplanation(quote);
}

function renderPricingExplanation(quote) {
    const c = quote.classification;
    const html = `
        <p><strong>Classification Applied:</strong></p>
        <ul>
            <li><strong>Size:</strong> ${capitalize(c.size.value)} — ${c.size.reason}</li>
            <li><strong>Complexity:</strong> ${capitalize(c.complexity.value)} — ${c.complexity.reason}</li>
            <li><strong>Scale:</strong> ${capitalize(c.scale.value)} — ${c.scale.reason}</li>
            <li><strong>Façade:</strong> ${c.facade.value} — ${c.facade.reason}</li>
        </ul>
        <p><strong>Multipliers:</strong> Size ×${CONFIG.multipliers.size[c.size.value]}, Complexity ×${CONFIG.multipliers.complexity[c.complexity.value]}, Façade ×${CONFIG.multipliers.facade[c.facade.value]}</p>
        <p><strong>Timeline:</strong> ${quote.timeline.note}</p>
        <p><strong>Revisions:</strong> ${CONFIG.revisions.included} rounds included. ${CONFIG.revisions.note}</p>
    `;
    document.getElementById("pricing-explanation").innerHTML = html;
}

// ============================================
// GENERATE PROPOSAL
// ============================================

function generateProposal() {
    if (!AppState.quote) calculateQuote();
    const q = AppState.quote;
    const cfg = CONFIG;

    const selectedServiceNames = q.services.map(s => s.name);
    const excludedServices = Object.values(cfg.services)
        .filter(s => !selectedServiceNames.includes(s.name))
        .map(s => s.name);

    const html = `
        <div class="proposal-content">
            <h2>Design Services Proposal</h2>
            <p class="proposal-meta">Quote ID: <strong>${escapeHtml(q.quoteId)}</strong> | Date: ${escapeHtml(q.date)} | Valid for ${cfg.offer_validity_days} days</p>
            
            <div class="proposal-section">
                <h3>Client</h3>
                <p><strong>${escapeHtml(q.data.clientName || 'To be confirmed')}</strong></p>
                <p>Project: ${escapeHtml(q.data.projectName || '-')}</p>
                <p>Location: ${escapeHtml(q.data.location || '-')}</p>
            </div>

            <div class="proposal-section">
                <h3>Project Classification</h3>
                <table class="proposal-table">
                    <tr><td>Area</td><td>${q.data.area} sqm (${q.data.spaces} spaces)</td></tr>
                    <tr><td>Type</td><td>${capitalize(q.data.projectType)}</td></tr>
                    <tr><td>Size</td><td>${capitalize(q.classification.size.value)}</td></tr>
                    <tr><td>Complexity</td><td>${capitalize(q.classification.complexity.value)}</td></tr>
                    <tr><td>Scale</td><td>${capitalize(q.classification.scale.value)} (${q.data.sites} site${q.data.sites > 1 ? 's' : ''})</td></tr>
                    <tr><td>Façade</td><td>${q.classification.facade.value} - ${q.classification.facade.reason}</td></tr>
                </table>
            </div>

            <div class="proposal-section">
                <h3>Selected Services</h3>
                <ul>
                    ${q.services.map(s => `<li>${escapeHtml(s.name)} — ${formatCurrency(s.subtotal)}</li>`).join('')}
                </ul>
            </div>

            ${excludedServices.length > 0 ? `
            <div class="proposal-section">
                <h3>Excluded from Scope</h3>
                <ul>
                    ${excludedServices.map(n => `<li>${escapeHtml(n)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${q.addons.length > 0 ? `
            <div class="proposal-section">
                <h3>Add-ons</h3>
                <ul>
                    ${q.addons.map(a => `<li>${escapeHtml(a.name)} ${a.qty > 1 ? `(×${a.qty})` : ''} — ${formatCurrency(a.subtotal)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${q.rollout ? `
            <div class="proposal-section">
                <h3>Rollout Adaptation</h3>
                <p>${q.rollout.additionalSites} additional site(s) at ${q.rollout.adaptPct}% effort = ${formatCurrency(q.rollout.total)}</p>
            </div>
            ` : ''}

            <div class="proposal-section proposal-total">
                <h3>Total Fee</h3>
                <table class="proposal-table">
                    <tr><td>Services</td><td>${formatCurrency(q.servicesTotal)}</td></tr>
                    <tr><td>Add-ons</td><td>${formatCurrency(q.addonsTotal)}</td></tr>
                    ${q.rollout ? `<tr><td>Rollout</td><td>${formatCurrency(q.rolloutTotal)}</td></tr>` : ''}
                    ${q.vatRate > 0 ? `<tr><td>VAT (${q.vatRate}%)</td><td>${formatCurrency(q.vatAmount)}</td></tr>` : ''}
                    ${q.discountAmount > 0 ? `
                    <tr><td>Subtotal</td><td>${formatCurrency(q.beforeDiscount)}</td></tr>
                    <tr class="discount-row"><td><strong>Discount (${q.discountPercent}%)</strong></td><td class="discount-applied">- ${formatCurrency(q.discountAmount)}</td></tr>
                    ` : ''}
                    <tr class="total-row"><td><strong>Grand Total</strong></td><td><strong>${formatCurrency(q.grandTotal)}</strong></td></tr>
                </table>
            </div>

            <div class="proposal-section">
                <h3>Timeline</h3>
                <p><strong>${q.timeline.label}</strong></p>
                <p>${q.timeline.note}</p>
            </div>

            <div class="proposal-section">
                <h3>Revisions Policy</h3>
                <p>${cfg.revisions.included} revision rounds included. ${cfg.revisions.note}</p>
            </div>

            <div class="proposal-section">
                <h3>Payment Terms</h3>
                <ul>
                    ${cfg.paymentTerms.milestones.map(m => `<li>${m.label}: ${m.percent}%</li>`).join('')}
                </ul>
                <p>Net ${cfg.paymentTerms.netDays} days from invoice.</p>
            </div>

            <div class="proposal-section">
                <h3>Assumptions</h3>
                <ul>
                    ${cfg.assumptions.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                </ul>
            </div>

            <div class="proposal-section">
                <h3>Exclusions</h3>
                <ul>
                    ${cfg.exclusions.map(e => `<li>${escapeHtml(e)}</li>`).join('')}
                </ul>
            </div>

            <div class="proposal-section signature-section">
                <h3>Acceptance</h3>
                <p>Please sign below to accept this proposal.</p>
                <div class="signature-block">
                    <div class="signature-line">
                        <span>Client Signature</span>
                        <span>Date</span>
                    </div>
                    <div class="signature-line">
                        <span>Name & Title</span>
                        <span></span>
                    </div>
                </div>
            </div>

            <div class="proposal-footer">
                <p><strong>${cfg.company.name}</strong></p>
                <p>${cfg.company.address}</p>
                <p>Tel: ${cfg.company.tel} | Mobile: ${cfg.company.mobile}</p>
                <p>Email: ${cfg.company.email}</p>
            </div>
        </div>
    `;

    AppState.elements.offerOutput.innerHTML = html;

    // Also set plain text version
    const plainText = generatePlainTextProposal(q, cfg);
    if (AppState.elements.offerText) {
        AppState.elements.offerText.value = plainText;
    }
}

function generatePlainTextProposal(q, cfg) {
    return `
VERTEX DESIGN - DESIGN SERVICES PROPOSAL
=========================================

Quote ID: ${q.quoteId}
Date: ${q.date}
Valid for: ${cfg.offer_validity_days} days

CLIENT
------
${q.data.clientName || 'To be confirmed'}
Project: ${q.data.projectName || '-'}
Location: ${q.data.location || '-'}

PROJECT SCOPE
-------------
Area: ${q.data.area} sqm (${q.data.spaces} spaces)
Type: ${capitalize(q.data.projectType)}
Classification: ${capitalize(q.classification.size.value)} / ${capitalize(q.classification.complexity.value)} / ${capitalize(q.classification.scale.value)}

SELECTED SERVICES
-----------------
${q.services.map(s => `• ${s.name}: ${formatCurrency(s.subtotal)}`).join('\n')}

TOTAL FEE
---------
Services: ${formatCurrency(q.servicesTotal)}
Add-ons: ${formatCurrency(q.addonsTotal)}
${q.rollout ? `Rollout: ${formatCurrency(q.rolloutTotal)}\n` : ''}Grand Total: ${formatCurrency(q.grandTotal)}

TIMELINE
--------
${q.timeline.label}

PAYMENT TERMS
-------------
${cfg.paymentTerms.milestones.map(m => `• ${m.label}: ${m.percent}%`).join('\n')}

---
${cfg.company.name}
${cfg.company.tel} | ${cfg.company.email}
    `.trim();
}

// ============================================
// FLOATING TOTAL UPDATE
// ============================================

function updateFloatingTotal() {
    // This is an alias - updateSummaryPanel handles the floating total
    updateSummaryPanel();
}

// ============================================
// STICKY SUMMARY PANEL
// ============================================

function updateSummaryPanel() {
    console.log('[DEBUG] updateSummaryPanel called');
    const form = AppState.elements.form;
    if (!form) {
        console.log('[DEBUG] form is null, returning');
        return;
    }

    // Get quick estimate
    const data = getFormData();
    console.log('[DEBUG] Form data:', data);

    // Try to derive classification if not yet set
    if (data.area >= 10 && data.projectType) {
        if (!AppState.classification) {
            updateClassification();
        }
    }

    const c = AppState.classification;
    console.log('[DEBUG] Classification:', c);

    // Get selected services
    const selectedServices = getSelectedServices();
    const serviceCount = selectedServices.length;
    console.log('[DEBUG] Selected services:', selectedServices, 'count:', serviceCount);

    // Quick price calculation (services + addons) - now using area-based rates
    let servicesTotal = 0;
    let addonsTotal = 0;

    // Use default multiplier if classification not yet set
    const complexMult = c ? (CONFIG.multipliers.complexity[c.complexity.value] || 1) : 1;
    const facadeMult = c ? (CONFIG.multipliers.facade[c.facade.value] || 1) : 1;

    // Always calculate services total (even without classification)
    selectedServices.forEach(id => {
        let fee = calculateServiceFee(id, data.area || 100, complexMult);
        console.log('[DEBUG] Service', id, 'fee:', fee);
        // Apply façade multiplier for façade services
        if (id.startsWith("SF")) {
            fee = Math.round(fee * facadeMult);
        }
        servicesTotal += fee;
    });
    console.log('[DEBUG] Services total:', servicesTotal);

    // Calculate add-ons total
    const addonChecks = form.querySelectorAll("input[name='addons']:checked");
    addonChecks.forEach(cb => {
        const key = cb.value;
        const addon = CONFIG.addons[key];
        if (!addon) return;

        if (key === "extra_renders") {
            const qty = sanitize(form.elements["extraRenderCount"]?.value, 0, 20);
            addonsTotal += addon.price * qty;
        } else if (key === "extra_revisions") {
            const qty = sanitize(form.elements["extraRevisionCount"]?.value, 0, 10);
            addonsTotal += addon.price * qty;
        } else if (key === "authority_submission") {
            addonsTotal += addon.price;
        } else if (key === "site_visits") {
            const qty = sanitize(form.elements["siteVisitCount"]?.value, 0, 20);
            addonsTotal += addon.price * qty;
        } else if (key === "fast_track") {
            // Fast-track is 15% of services + other addons
            addonsTotal += Math.round((servicesTotal + addonsTotal) * 0.15);
        }
    });

    const total = servicesTotal + addonsTotal;

    // Apply user discount if applicable
    const hasDiscount = AuthManager.hasDiscount();
    const discountedTotal = hasDiscount ? AuthManager.applyDiscount(total) : total;
    const discountPercent = AuthManager.getDiscountPercent();

    // Update floating total element (only one Estimated Total bar now)
    const floatingAmount = document.getElementById("floating-amount");
    if (floatingAmount) {
        if (hasDiscount && total > 0) {
            // Show both original and discounted price
            floatingAmount.innerHTML = `
                <span class="discount-original">${formatCurrency(total)}</span>
                <span class="discount-applied">${formatCurrency(discountedTotal)}</span>
            `;
        } else {
            floatingAmount.textContent = formatCurrency(total);
        }
    }
}

// ============================================
// QUOTE HISTORY
// ============================================

function saveQuote() {
    if (!AppState.quote) {
        showFeedback("No quote to save. Please complete the form first.", true);
        return;
    }

    const q = AppState.quote;
    const historyItem = {
        id: q.quoteId,
        date: q.date,
        clientName: q.data.clientName || "Unnamed",
        projectName: q.data.projectName || "Untitled",
        total: q.grandTotal,
        data: { ...q.data },
        timestamp: Date.now()
    };

    AppState.quoteHistory.unshift(historyItem);
    if (AppState.quoteHistory.length > 10) {
        AppState.quoteHistory.pop();
    }

    try {
        localStorage.setItem("vertex_quote_history", JSON.stringify(AppState.quoteHistory));
    } catch (e) {
        console.warn("Could not save to localStorage:", e);
    }

    renderQuoteHistory();
    showFeedback("Quote saved to history!", false);
}

function loadQuoteHistory() {
    try {
        const saved = localStorage.getItem("vertex_quote_history");
        if (saved) {
            AppState.quoteHistory = JSON.parse(saved);
            renderQuoteHistory();
        }
    } catch (e) {
        console.warn("Could not load quote history:", e);
    }
}

function renderQuoteHistory() {
    const container = AppState.elements.quoteHistory;
    if (!container) return;

    if (AppState.quoteHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">No saved quotes yet.</p>';
        return;
    }

    container.innerHTML = AppState.quoteHistory.map(item => `
        <div class="history-item" data-id="${escapeHtml(item.id)}">
            <strong>${escapeHtml(item.projectName)}</strong>
            <span>${escapeHtml(item.clientName)} • ${formatCurrency(item.total)}</span>
            <span>${escapeHtml(item.date)}</span>
        </div>
    `).join("");

    // Click to load
    container.querySelectorAll(".history-item").forEach(el => {
        el.addEventListener("click", () => loadSavedQuote(el.dataset.id));
    });
}

function loadSavedQuote(id) {
    const item = AppState.quoteHistory.find(q => q.id === id);
    if (!item) return;

    const form = AppState.elements.form;
    if (!form) return;

    Object.keys(item.data).forEach(key => {
        const field = form.elements[key];
        if (field) {
            if (typeof item.data[key] === "boolean") {
                field.checked = item.data[key];
            } else if (Array.isArray(item.data[key])) {
                // Handle checkboxes
            } else {
                field.value = item.data[key];
            }
        }
    });

    goToStep(1);
    showFeedback(`Loaded quote: ${item.id}`, false);
}

// ============================================
// FORM DATA HELPERS
// ============================================

function getFormData() {
    const form = AppState.elements.form;
    if (!form) return {};

    const data = new FormData(form);

    return {
        clientName: (data.get("clientName") || "").trim(),
        clientEmail: (data.get("clientEmail") || "").trim(),
        projectName: (data.get("projectName") || "").trim(),
        location: (data.get("location") || "").trim(),
        area: sanitize(data.get("area"), 10, 50000),
        spaces: sanitize(data.get("spaces"), 1, 100),
        projectType: data.get("projectType") || "retail",
        specialSystems: data.getAll("specialSystems"),
        sites: sanitize(data.get("sites"), 1, 100),
        reuseLevel: data.get("reuseLevel") || "adapted",
        facadeType: data.get("facadeType") || "none",
        facadeArea: sanitize(data.get("facadeArea"), 0, 5000),
        signageCount: data.get("signageCount") || "0",
        facadeFeatures: data.getAll("facadeFeatures")
    };
}

function getSelectedServices() {
    const form = AppState.elements.form;
    if (!form) return [];
    return Array.from(form.querySelectorAll("input[name='services']:checked")).map(cb => cb.value);
}

// ============================================
// PACKAGE HANDLER - ALIGNED TO A/B/C
// ============================================

function applyPackage(packageType) {
    const form = AppState.elements.form;
    if (!form) return;

    const pkg = CONFIG.packages[packageType];
    if (!pkg) return;

    // Update description
    const descEl = AppState.elements.packageDescription;
    if (descEl) {
        descEl.textContent = pkg.description;
    }

    // Get services grid
    const servicesGrid = form.querySelector(".services-grid");
    const serviceCheckboxes = form.querySelectorAll("input[name='services']");

    if (packageType === "custom" || pkg.services === null) {
        // Enable all checkboxes for manual selection
        serviceCheckboxes.forEach(cb => {
            cb.disabled = false;
        });
        if (servicesGrid) servicesGrid.classList.remove("disabled");
    } else {
        // Apply preset and disable manual changes
        serviceCheckboxes.forEach(cb => {
            cb.checked = pkg.services.includes(cb.value);
            cb.disabled = true; // Lock selection for presets
        });
        if (servicesGrid) servicesGrid.classList.add("disabled");
    }

    updateServicePrices();
    updateFloatingTotal();
    updateSummaryPanel();
}

// ============================================
// UI HELPERS
// ============================================

function updateFacadeVisibility() {
    const form = AppState.elements.form;
    const facadeType = form?.querySelector("input[name='facadeType']:checked")?.value;
    const details = AppState.elements.facadeDetails;
    const services = AppState.elements.facadeServices;

    if (details) {
        details.hidden = (facadeType === "none");
    }
    if (services) {
        services.hidden = (facadeType === "none");
    }
}

function updateReuseVisibility() {
    const form = AppState.elements.form;
    const sites = sanitize(form?.elements["sites"]?.value, 1, 100);
    const reuseSelect = form?.elements["reuseLevel"];

    if (reuseSelect) {
        reuseSelect.disabled = sites <= 1;
    }
}

function setOfferDate() {
    const now = new Date();
    const formatted = now.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

    ["offer-date", "print-date"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = formatted;
    });
}

function generateQuoteId() {
    const now = new Date();
    const yyyymmdd = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0")
    ].join("");

    let random;
    if (typeof crypto !== "undefined" && crypto.getRandomValues) {
        const arr = new Uint16Array(1);
        crypto.getRandomValues(arr);
        random = 1000 + (arr[0] % 9000);
    } else {
        random = Math.floor(1000 + Math.random() * 9000);
    }

    const id = `VD-${yyyymmdd}-${random}`;

    ["quote-id", "print-quote-id"].forEach(elId => {
        const el = document.getElementById(elId);
        if (el) el.textContent = id;
    });

    return id;
}

function showFeedback(message, isError) {
    const el = AppState.elements.feedback;
    if (!el) return;

    el.textContent = message;
    el.classList.remove("visible", "error", "success");

    if (message) {
        el.classList.add("visible", isError ? "error" : "success");
    }
}

function showTooltip(e) {
    const text = e.currentTarget.dataset.tooltip;
    const container = AppState.elements.tooltipContainer;
    if (!container || !text) return;

    container.textContent = text;
    container.classList.add("visible");
    container.setAttribute("aria-hidden", "false");

    const rect = e.currentTarget.getBoundingClientRect();
    container.style.top = `${rect.bottom + 8}px`;
    container.style.left = `${rect.left + rect.width / 2}px`;
    container.style.transform = "translateX(-50%)";
}

function hideTooltip() {
    const container = AppState.elements.tooltipContainer;
    if (container) {
        container.classList.remove("visible");
        container.setAttribute("aria-hidden", "true");
    }
}

// ============================================
// SPECIAL SYSTEMS - CONDITIONAL DISPLAY
// ============================================

function updateSpecialSystems() {
    const form = AppState.elements.form;
    const group = AppState.elements.specialSystemsGroup;
    if (!form || !group) return;

    const projectType = form.elements["projectType"]?.value || "";

    // Hide all systems first
    const allOptions = group.querySelectorAll(".checkbox-option");
    allOptions.forEach(opt => {
        opt.style.display = "none";
        const checkbox = opt.querySelector("input[type='checkbox']");
        if (checkbox) checkbox.checked = false;
    });

    // If no project type selected or retail/showroom (no special systems), hide group
    const typesWithNoSystems = ["", "retail", "showroom"];
    if (typesWithNoSystems.includes(projectType)) {
        group.hidden = true;
        return;
    }

    // Show group and relevant systems
    group.hidden = false;

    allOptions.forEach(opt => {
        const categories = (opt.dataset.category || "").split(" ");
        if (categories.includes(projectType)) {
            opt.style.display = "flex";
        }
    });
}

// Note: updateFloatingTotal is defined earlier as an alias to updateSummaryPanel

// ============================================
// ACTIONS
// ============================================

async function downloadPdf() {
    if (typeof html2pdf === "undefined") {
        showFeedback("PDF library not loaded. Please try printing instead.", true);
        return;
    }

    const content = AppState.elements.offerOutput;
    if (!content || !content.innerHTML.trim()) {
        showFeedback("No proposal to download. Please complete all steps first.", true);
        return;
    }

    const opt = {
        margin: [15, 15, 20, 15],
        filename: `Vertex-Design-${document.getElementById("quote-id")?.textContent || "Quote"}.pdf`,
        image: { type: "jpeg", quality: 0.95 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] }
    };

    try {
        await html2pdf().set(opt).from(content).save();
        showFeedback("PDF downloaded successfully!", false);
    } catch (error) {
        console.error("PDF error:", error);
        showFeedback("PDF generation failed. Please try printing.", true);
    }
}

function copyOfferText() {
    const text = AppState.elements.offerText?.value;
    if (!text) {
        showFeedback("No offer text to copy.", true);
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showFeedback("Offer copied to clipboard!", false);
    }).catch(() => {
        showFeedback("Copy failed. Please select and copy manually.", true);
    });
}

function resetForm() {
    const form = AppState.elements.form;
    if (form) form.reset();

    AppState.currentStep = 1;
    AppState.classification = null;
    AppState.quote = null;

    generateQuoteId();
    setOfferDate();
    updateFacadeVisibility();
    updateReuseVisibility();
    updateSpecialSystems();

    // Reset package dropdown to B
    if (AppState.elements.packageType) {
        AppState.elements.packageType.value = "B";
    }
    applyPackage("B");

    goToStep(1);

    if (AppState.elements.offerOutput) {
        AppState.elements.offerOutput.innerHTML = '<p class="placeholder">Proposal will appear here...</p>';
    }
}

// ============================================
// UTILITIES
// ============================================

function sanitize(value, min = 0, max = Infinity) {
    const num = Number(value);
    if (!Number.isFinite(num)) return min;
    return Math.max(min, Math.min(max, num));
}

function escapeHtml(str) {
    if (typeof str !== "string") return "";
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return str.replace(/[&<>"']/g, c => map[c]);
}

function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatCurrency(value, currency = CONFIG.currency) {
    if (!Number.isFinite(value)) return "-";
    try {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    } catch (e) {
        return `${currency} ${Math.round(value).toLocaleString()}`;
    }
}

function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
