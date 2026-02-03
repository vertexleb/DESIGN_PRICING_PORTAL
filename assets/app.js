
const DEFAULT_CONFIG = {
    fx_reference_date: "2026-01",
    public_mode: false,
    currency: "KWD",
    budgetary_range_percent: 15,
    anchor_area_sqm: 120,
    anchor_package: "B",
    anchor_complexity: "Standard",
    anchor_rate_kwd_per_sqm_min: 16,
    anchor_rate_kwd_per_sqm_default: 17,
    anchor_rate_kwd_per_sqm_max: 18,
    fast_track_multiplier: 1.15,
    small_area_threshold_sqm: 80,
    small_area_uplift_percent: 10,
    small_area_uplift_cap_kwd: 150,
    medium_project_range_sqm: [80, 300],
    large_area_threshold_sqm: 300,
    large_area_discount_kwd_per_sqm: 1.5,
    very_large_area_threshold_sqm: 1000,
    very_large_area_discount_kwd_per_sqm: 3.0,
    package_effort_factor: {
        A: 0.65,
        B: 1.0,
        C: 1.0
    },
    min_fee_by_package: {
        A: 500,
        B: 1000,
        C: 400
    },
    complexity_levels: ["low", "typical", "high"],
    complexity_additions_kwd: {
        Standard: { low: 0, typical: 0, high: 0 },
        Enhanced: { low: 400, typical: 400, high: 400 },
        Specialized: { low: 1200, typical: 1200, high: 1200 }
    },
    rollout_adaptation_mode: "percent_of_site1_with_min",
    rollout_adaptation_percent_of_site1: 25,
    rollout_adaptation_min_kwd_per_site: 400,
    add_ons: {
        authority_approval_documentation: 600,
        additional_renderings_per_view: 80,
        full_mep_engineering_coordination: 1500
    },
    offer_validity_days: 14,
    payment_terms: {
        net_days: 30,
        milestones: [
            { label: "Start / Mobilization", percent: 30 },
            { label: "Concept Approval", percent: 30 },
            { label: "Tender Package Delivery", percent: 40 }
        ]
    },
    assumptions: [
        "Single floor unless stated otherwise",
        "Client provides as-built drawings or landlord layout drawings",
        "Client provides brand guidelines and operational requirements",
        "Timely approvals and decision-making",
        "Site access and surveys arranged by client"
    ],
    exclusions: [
        "MEP engineering calculations and design",
        "Structural engineering calculations",
        "Permit fees and authority submission stamping",
        "Full construction supervision unless added",
        "Procurement and ordering unless added"
    ],
    revisions_out_of_scope_note:
        "Additional options, scope changes, or changes after approval are treated as out-of-scope and may require a separate fee.",
    next_steps: [
        "Confirm scope and package selection",
        "Provide site documents and brand guidelines",
        "Schedule kickoff meeting"
    ],
    company_info: {
        name: "Vertex Design Buildings General Contracting Co.",
        address_lines: [
            "Salmiya  Block 4",
            "Salem Al-Mubarak Street",
            "Tala Center (Tala Complex)",
            "Mezzanine Floor, Office No. 6",
            "Kuwait"
        ],
        contacts: {
            tel: "+965 2571 2021",
            mobile: "+965 9721 9663",
            email: "info@VertexDesignkw.com"
        }
    },
    timeline_by_package: {
        A: {
            typical_weeks_min: 1,
            typical_weeks_max: 2,
            label: "1-2 weeks (working)"
        },
        B: {
            typical_weeks_min: 3,
            typical_weeks_max: 5,
            label: "3-5 weeks (working)"
        },
        C: {
            typical_weeks_min: 4,
            typical_weeks_max: 6,
            label: "Prototype 4-6 weeks + adaptations 3-5 working days/site",
            adaptation_days_min: 3,
            adaptation_days_max: 5
        }
    },
    package_details: {
        A: {
            title: "Package A - Concept Package",
            purpose: "Brief summary, mood boards, preliminary layouts, initial palette, high-level budget.",
            deliverables: [
                "Design brief summary and scope alignment",
                "Concept mood boards and direction",
                "Preliminary layouts and zoning",
                "Initial material palette",
                "High-level budget guidance"
            ],
            revisions_included: 2,
            typical_timeline_weeks: "1-2 weeks (working)",
            stage_breakdown: [
                "Stage 1: Discovery + Brief",
                "Stage 2: Concept Direction",
                "Stage 3: Preliminary Layouts",
                "Stage 4: Palette + Key Decisions",
                "Stage 5: Budget Alignment",
                "Stage 6: Review + Revisions"
            ]
        },
        B: {
            title: "Package B - Full Design Development + Tender Set",
            purpose:
                "Detailed layouts, 3D views, specs, joinery, ceiling/lighting plans, tender-ready drawings, BOQ support notes.",
            deliverables: [
                "Detailed layouts and final GA",
                "3D views (agreed quantity)",
                "Material and finishes specifications",
                "Joinery and millwork details",
                "Ceiling and lighting plans",
                "Tender-ready drawing package",
                "BOQ support notes"
            ],
            revisions_included: 3,
            typical_timeline_weeks: "3-5 weeks (working)",
            stage_breakdown: [
                "Stage 1: Discovery + Brief",
                "Stage 2: Concept Direction",
                "Stage 3: Space Planning",
                "Stage 4: Design Development",
                "Stage 5: Tender Package",
                "Stage 6: Review + Close-out"
            ]
        },
        C: {
            title: "Package C - Rollout Kit",
            purpose: "Master standards, adaptation templates, modular system, supplier specifications.",
            deliverables: [
                "Master standards and guidelines",
                "Adaptation templates for new sites",
                "Modular detailing system",
                "Supplier specifications pack",
                "Prototype site documentation"
            ],
            revisions_included: 2,
            typical_timeline_weeks: "Prototype 4-6 weeks + adaptations 3-5 working days/site",
            stage_breakdown: [
                "Stage 1: Discovery + Brief",
                "Stage 2: Concept Direction",
                "Stage 3: Space Planning",
                "Stage 4: Design Development",
                "Stage 5: Rollout Standards",
                "Stage 6: Adaptation Prep"
            ]
        }
    }
};

const addOnLabels = {
    authority_approval_documentation: "Authority approval documentation",
    additional_renderings_per_view: "Additional renderings",
    full_mep_engineering_coordination: "Full MEP engineering coordination"
};

let pricingConfig = DEFAULT_CONFIG;
let currentOfferMode = "formal";
let cachedElements = {};
let lastCalculation = null;

document.addEventListener("DOMContentLoaded", () => {
    cacheElements();
    loadConfigAndInit();
});

function cacheElements() {
    cachedElements = {
        form: document.getElementById("pricing-form"),
        feedback: document.getElementById("form-feedback"),
        offerOutput: document.getElementById("offer-output"),
        offerText: document.getElementById("offer-text"),
        copyOfferBtn: document.getElementById("copy-offer"),
        printOfferBtn: document.getElementById("print-offer"),
        offerDate: document.getElementById("offer-date"),
        quoteId: document.getElementById("quote-id"),
        configWarning: document.getElementById("config-warning"),
        offerModeRadios: document.querySelectorAll("input[name='offerMode']"),
        packageTitle: document.getElementById("package-title"),
        packagePurpose: document.getElementById("package-purpose"),
        packageDeliverables: document.getElementById("package-deliverables"),
        packageRevisions: document.getElementById("package-revisions"),
        packageTimeline: document.getElementById("package-timeline"),
        packageStages: document.getElementById("package-stages"),
        // Print header elements
        printQuoteId: document.getElementById("print-quote-id"),
        printDate: document.getElementById("print-date")
    };
}

async function loadConfigAndInit() {
    const result = await loadConfig();
    pricingConfig = mergeConfig(DEFAULT_CONFIG, result.config);
    setConfigWarning(result.warning);
    initializeApp();
}

async function loadConfig() {
    const primary = await fetchConfig("./assets/config.json");
    if (primary.ok) {
        return { config: primary.config, warning: null };
    }

    const fallback = await fetchConfig("./assets/config.example.json");
    if (fallback.ok) {
        const warning = buildWarning(primary.error, true);
        return { config: fallback.config, warning };
    }

    const warning = buildWarning(`${primary.error}; ${fallback.error}`, false);
    return { config: DEFAULT_CONFIG, warning };
}

async function fetchConfig(path) {
    try {
        const response = await fetch(path, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return { ok: true, config: await response.json() };
    } catch (error) {
        return { ok: false, error: error?.message || "Unknown error" };
    }
}

function buildWarning(reason, usedExample) {
    const modeNote = window.location.protocol === "file:"
        ? " Local file mode can block config loading. Use a local server or host on your domain."
        : "";
    if (usedExample) {
        return `Config load failed: ${reason}. Using config.example.json as a read-only fallback.${modeNote}`;
    }
    return `Config load failed: ${reason}. Using embedded defaults.${modeNote}`;
}

function mergeConfig(defaults, overrides) {
    if (Array.isArray(defaults)) {
        return Array.isArray(overrides) ? overrides : defaults;
    }
    if (typeof defaults !== "object" || defaults === null) {
        return overrides !== undefined ? overrides : defaults;
    }
    const result = { ...defaults };
    Object.keys(overrides || {}).forEach((key) => {
        result[key] = mergeConfig(defaults[key], overrides[key]);
    });
    return result;
}

function setConfigWarning(message) {
    if (!cachedElements.configWarning) return;
    if (message) {
        cachedElements.configWarning.textContent = message;
        cachedElements.configWarning.hidden = false;
        return;
    }
    cachedElements.configWarning.hidden = true;
}

function initializeApp() {
    setOfferDate();
    setOfferMode(pricingConfig.public_mode ? "budgetary" : "formal");
    bindEvents();
    generateQuoteId();
    updateComplexityLevelState();
    updateRenderingsCountState();
    updatePackageDetails(getPackageCode());
    calculateAndRender();
}
function bindEvents() {
    if (!cachedElements.form) return;
    cachedElements.form.querySelectorAll("input, select").forEach((field) => {
        field.addEventListener("input", () => {
            if (field.name === "package") {
                updatePackageDetails(field.value);
            }
            if (field.name === "complexity") {
                updateComplexityLevelState();
            }
            if (field.name === "addOns" || field.name === "additionalRenderingsCount") {
                updateRenderingsCountState();
            }
            calculateAndRender();
        });
        field.addEventListener("change", () => {
            if (field.name === "package") {
                updatePackageDetails(field.value);
            }
            if (field.name === "complexity") {
                updateComplexityLevelState();
            }
            if (field.name === "addOns" || field.name === "additionalRenderingsCount") {
                updateRenderingsCountState();
            }
            calculateAndRender();
        });
    });

    cachedElements.offerModeRadios.forEach((radio) => {
        radio.addEventListener("change", () => {
            setOfferMode(radio.value);
            renderOffer(lastCalculation);
        });
    });

    cachedElements.copyOfferBtn?.addEventListener("click", copyOfferText);
    cachedElements.printOfferBtn?.addEventListener("click", () => window.print());
}

function setOfferDate() {
    const now = new Date();
    const formattedDate = now.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
    if (cachedElements.offerDate) {
        cachedElements.offerDate.textContent = formattedDate;
    }
    // Sync to print header
    if (cachedElements.printDate) {
        cachedElements.printDate.textContent = formattedDate;
    }
}

function setOfferMode(mode) {
    if (pricingConfig.public_mode) {
        currentOfferMode = "budgetary";
    } else {
        currentOfferMode = mode === "budgetary" ? "budgetary" : "formal";
    }
    cachedElements.offerModeRadios.forEach((radio) => {
        radio.checked = radio.value === currentOfferMode;
        if (pricingConfig.public_mode) {
            radio.disabled = radio.value !== "budgetary";
        }
    });
}

function updateComplexityLevelState() {
    const complexityField = cachedElements.form?.elements["complexity"];
    const levelField = cachedElements.form?.elements["complexityLevel"];
    if (!complexityField || !levelField) return;
    if (complexityField.value === "Standard") {
        levelField.value = "typical";
        levelField.disabled = true;
    } else {
        levelField.disabled = false;
    }
}

function updateRenderingsCountState() {
    const renderingsCheckbox = cachedElements.form?.querySelector(
        "input[name='addOns'][value='additional_renderings_per_view']"
    );
    const renderingsCount = cachedElements.form?.elements["additionalRenderingsCount"];
    if (!renderingsCheckbox || !renderingsCount) return;
    if (renderingsCheckbox.checked) {
        renderingsCount.disabled = false;
        if (Number(renderingsCount.value) <= 0) {
            renderingsCount.value = 1;
        }
    } else {
        renderingsCount.value = 0;
        renderingsCount.disabled = true;
    }
}

function getPackageCode() {
    return cachedElements.form?.elements["package"]?.value || "B";
}

function getFormData() {
    const form = cachedElements.form;
    if (!form) return null;
    const data = new FormData(form);
    return {
        clientName: (data.get("clientName") || "").trim(),
        projectName: (data.get("projectName") || "").trim(),
        location: (data.get("location") || "").trim(),
        projectType: data.get("projectType") || "Retail",
        area: Number(data.get("area")),
        package: data.get("package") || "B",
        complexity: data.get("complexity") || "Standard",
        complexityLevel: data.get("complexityLevel") || "typical",
        siteCount: Number(data.get("siteCount")) || 1,
        urgency: data.get("urgency") || "Normal",
        addOns: data.getAll("addOns"),
        additionalRenderingsCount: Number(data.get("additionalRenderingsCount")) || 0
    };
}

function validateData(data) {
    const errors = [];
    if (!Number.isFinite(data.area) || data.area <= 0) {
        errors.push("Area must be greater than zero.");
    }
    if (!Number.isFinite(data.siteCount) || data.siteCount < 1) {
        errors.push("Number of sites must be at least 1.");
    }
    if (
        data.addOns.includes("additional_renderings_per_view") &&
        (!Number.isFinite(data.additionalRenderingsCount) || data.additionalRenderingsCount < 1)
    ) {
        errors.push("Additional renderings count must be at least 1.");
    }
    return errors;
}

function calculateAndRender() {
    const data = getFormData();
    if (!data) return;
    const errors = validateData(data);
    if (errors.length) {
        showFeedback(errors.join(" "), true);
        cachedElements.offerOutput.innerHTML =
            '<p class="placeholder">Enter valid project details to generate the offer.</p>';
        cachedElements.offerText.value = "";
        return;
    }
    showFeedback("", false);
    lastCalculation = calculateOffer(data);
    renderOffer(lastCalculation);
}

function calculateOffer(data, options = {}) {
    const cfg = pricingConfig;
    const anchorRate = resolveAnchorRate(options.anchorRate);
    const baseFee = data.area * anchorRate;

    const smallThreshold = toNumber(cfg.small_area_threshold_sqm || cfg.small_project_threshold_sqm);
    const smallPremiumPercent = toNumber(cfg.small_area_uplift_percent || cfg.small_project_premium_percent);
    const smallUpliftCap = toNumber(cfg.small_area_uplift_cap_kwd);
    const largeThreshold = toNumber(cfg.large_area_threshold_sqm || cfg.large_project_threshold_sqm);
    const largeDiscount = toNumber(cfg.large_area_discount_kwd_per_sqm || cfg.large_discount_per_sqm);
    const veryLargeThreshold = toNumber(cfg.very_large_area_threshold_sqm || cfg.very_large_project_threshold_sqm);
    const veryLargeDiscount = toNumber(
        cfg.very_large_area_discount_kwd_per_sqm || cfg.very_large_discount_per_sqm
    );

    let sizeAdjustment = 0;
    if (data.area < smallThreshold) {
        sizeAdjustment = baseFee * (smallPremiumPercent / 100);
        if (smallUpliftCap > 0) {
            sizeAdjustment = Math.min(sizeAdjustment, smallUpliftCap);
        }
    } else if (data.area >= largeThreshold) {
        const discountBaseArea = Math.min(data.area, veryLargeThreshold) - largeThreshold;
        if (discountBaseArea > 0) {
            sizeAdjustment -= discountBaseArea * largeDiscount;
        }
        if (data.area > veryLargeThreshold) {
            sizeAdjustment -= (data.area - veryLargeThreshold) * veryLargeDiscount;
        }
    }

    const sizeAdjustedFee = baseFee + sizeAdjustment;
    const packageFactor = toNumber(cfg.package_effort_factor?.[data.package]) || 1;
    const packageAdjustment = sizeAdjustedFee * (packageFactor - 1);
    let subtotal = sizeAdjustedFee + packageAdjustment;

    const complexityAddition = getComplexityAddition(data.complexity, data.complexityLevel);
    subtotal += complexityAddition;

    let fastTrackAdjustment = 0;
    if (data.urgency === "Fast-track") {
        const multiplier = toNumber(cfg.fast_track_multiplier) || 1;
        fastTrackAdjustment = subtotal * (multiplier - 1);
        subtotal += fastTrackAdjustment;
    }

    const minFee = toNumber(cfg.min_fee_by_package?.[data.package]) || 0;
    let minFeeAdjustment = 0;
    if (subtotal < minFee) {
        minFeeAdjustment = minFee - subtotal;
        subtotal = minFee;
    }

    const site1Fee = subtotal;
    const rollout = calculateRollout(site1Fee, data.siteCount, data.area);
    const addOns = calculateAddOns(data);

    const totalFee = site1Fee + rollout.total + addOns.total;

    return {
        data,
        baseFee,
        sizeAdjustment,
        packageAdjustment,
        complexityAddition,
        fastTrackAdjustment,
        minFeeAdjustment,
        site1Fee,
        rollout,
        addOns,
        totalFee
    };
}
function calculateRollout(site1Fee, siteCount, area) {
    if (siteCount <= 1) {
        return { sites: siteCount, perSiteFee: 0, total: 0 };
    }
    const mode = pricingConfig.rollout_adaptation_mode || pricingConfig.rollout_adaptation?.basis;
    const percent = toNumber(
        pricingConfig.rollout_adaptation_percent_of_site1 || pricingConfig.rollout_adaptation?.percent
    );
    const minFee = toNumber(
        pricingConfig.rollout_adaptation_min_kwd_per_site || pricingConfig.rollout_adaptation?.min_kwd_per_site
    );
    let perSiteFee = 0;

    if (mode === "flat_per_site") {
        perSiteFee = toNumber(
            pricingConfig.rollout_adaptation_flat_kwd_per_site || pricingConfig.rollout_adaptation?.flat_kwd_per_site
        );
    } else if (mode === "per_sqm_with_min") {
        const perSqm = toNumber(
            pricingConfig.rollout_adaptation_per_sqm_kwd || pricingConfig.rollout_adaptation?.per_sqm_kwd
        );
        perSiteFee = perSqm * area;
    } else {
        perSiteFee = site1Fee * (percent / 100);
    }

    perSiteFee = Math.max(perSiteFee, minFee);
    const total = perSiteFee * (siteCount - 1);
    return { sites: siteCount, perSiteFee, total };
}

function calculateAddOns(data) {
    const addOns = [];
    let total = 0;
    data.addOns.forEach((key) => {
        if (key === "additional_renderings_per_view") {
            const unit = toNumber(pricingConfig.add_ons?.[key]);
            const count = Math.max(0, data.additionalRenderingsCount);
            const amount = unit * count;
            if (amount > 0) {
                addOns.push({ key, label: addOnLabels[key], amount, quantity: count, unit });
                total += amount;
            }
            return;
        }
        const amount = toNumber(pricingConfig.add_ons?.[key]);
        if (amount > 0) {
            addOns.push({ key, label: addOnLabels[key], amount, quantity: 1 });
            total += amount;
        }
    });
    return { items: addOns, total };
}

function getComplexityAddition(complexity, level) {
    const tiers = pricingConfig.complexity_additions_kwd || {};
    const values = tiers[complexity] || {};
    const selection = values[level] ?? values.typical ?? 0;
    return toNumber(selection);
}

function renderOffer(calc) {
    if (!calc) return;
    const formatter = (value) => formatCurrency(value, pricingConfig.currency);
    const packageDetails = pricingConfig.package_details?.[calc.data.package] || {};
    const timelineLines = buildTimelineLines(calc.data, packageDetails);
    const summaryHtml = buildSummaryHtml(calc.data, packageDetails);
    const breakdownHtml = buildBreakdownHtml(calc, formatter);
    const budgetaryRange = getBudgetaryRange(calc);
    const fastTrackNote = calc.data.urgency === "Fast-track"
        ? "Fast-track selected: additional resources and revision constraints apply."
        : "";

    if (currentOfferMode === "budgetary") {
        cachedElements.offerOutput.innerHTML = `
            <div class="total-card">
                <div class="section-title">Budgetary Range</div>
                <strong>${formatter(budgetaryRange.lower)} - ${formatter(budgetaryRange.upper)}</strong>
            </div>
            <div>
                <div class="section-title">Key Inputs</div>
                <ul class="summary-list">${summaryHtml}</ul>
            </div>
            <div>
                <div class="section-title">Estimated Fee Breakdown</div>
                <ul class="breakdown-list">${breakdownHtml}</ul>
            </div>
            ${fastTrackNote ? `<p class="meta-line">${fastTrackNote}</p>` : ""}
        `;
    } else {
        cachedElements.offerOutput.innerHTML = `
            <div class="total-card">
                <div class="section-title">Fixed Fee</div>
                <strong>${formatter(calc.totalFee)}</strong>
            </div>
            <div>
                <div class="section-title">Key Inputs</div>
                <ul class="summary-list">${summaryHtml}</ul>
            </div>
            <div>
                <div class="section-title">Fee Breakdown</div>
                <ul class="breakdown-list">${breakdownHtml}</ul>
            </div>
            <div>
                <div class="section-title">Deliverables</div>
                <ul class="bullet-list">${buildBulletList(packageDetails.deliverables)}</ul>
            </div>
            <div>
                <div class="section-title">Timeline</div>
                <ul class="bullet-list">${buildBulletList(timelineLines)}</ul>
                <ul class="bullet-list">${buildBulletList(packageDetails.stage_breakdown)}</ul>
            </div>
            <div>
                <div class="section-title">Revisions Included</div>
                <p class="meta-line">${formatRevisions(packageDetails.revisions_included)}</p>
                <p class="meta-line">${pricingConfig.revisions_out_of_scope_note}</p>
            </div>
            <div>
                <div class="section-title">Payment Terms</div>
                <ul class="bullet-list">${buildPaymentTerms()}</ul>
                <p class="meta-line">Net ${pricingConfig.payment_terms?.net_days || 30} days.</p>
            </div>
            <div>
                <div class="section-title">Assumptions</div>
                <ul class="bullet-list">${buildBulletList(pricingConfig.assumptions)}</ul>
            </div>
            <div>
                <div class="section-title">Exclusions</div>
                <ul class="bullet-list">${buildBulletList(pricingConfig.exclusions)}</ul>
            </div>
            <div>
                <div class="section-title">Validity</div>
                <p class="meta-line">${pricingConfig.offer_validity_days} days from date of issue.</p>
            </div>
            <div>
                <div class="section-title">Next Steps</div>
                <ul class="bullet-list">${buildBulletList(pricingConfig.next_steps)}</ul>
            </div>
            ${fastTrackNote ? `<p class="meta-line">${fastTrackNote}</p>` : ""}
        `;
    }

    cachedElements.offerText.value = buildOfferText(calc, packageDetails, budgetaryRange);
}

function buildSummaryHtml(data, packageDetails) {
    const packageLabel = packageDetails.title || data.package;
    const complexityLabel = data.complexity === "Standard"
        ? "Standard"
        : `${data.complexity} (${capitalize(data.complexityLevel)})`;
    const items = [
        { label: "Client", value: data.clientName || "-" },
        { label: "Project", value: data.projectName || "-" },
        { label: "Location", value: data.location || "-" },
        { label: "Type", value: data.projectType || "-" },
        { label: "Area", value: `${data.area} sqm` },
        { label: "Package", value: packageLabel },
        { label: "Complexity", value: complexityLabel },
        { label: "Urgency", value: data.urgency },
        { label: "Sites", value: data.siteCount > 1 ? `${data.siteCount} sites` : "Single site" }
    ];
    return items
        .map((item) => `<li><span>${item.label}</span><span>${item.value}</span></li>`)
        .join("");
}

function buildBreakdownHtml(calc, formatter) {
    const items = [
        { label: "Base Fee (Area x Rate)", value: calc.baseFee },
        { label: "Size Adjustment", value: calc.sizeAdjustment },
        { label: "Package Adjustment", value: calc.packageAdjustment },
        { label: "Complexity Addition", value: calc.complexityAddition }
    ];
    if (calc.fastTrackAdjustment > 0) {
        items.push({ label: "Fast-track Adjustment", value: calc.fastTrackAdjustment });
    }
    if (calc.minFeeAdjustment > 0) {
        items.push({ label: "Minimum Fee Floor", value: calc.minFeeAdjustment });
    }
    items.push({ label: "Site 1 Design Fee", value: calc.site1Fee });

    if (calc.rollout.sites > 1) {
        items.push({
            label: `Rollout Adaptation (${calc.rollout.sites - 1} sites @ ${formatter(calc.rollout.perSiteFee)})`,
            value: calc.rollout.total
        });
    }

    if (calc.addOns.items.length) {
        calc.addOns.items.forEach((addOn) => {
            const label = addOn.quantity && addOn.quantity > 1
                ? `${addOn.label} (${addOn.quantity}x)`
                : addOn.label;
            items.push({ label, value: addOn.amount });
        });
    }

    items.push({ label: "Total Design Fee", value: calc.totalFee, strong: true });

    return items
        .map((item) => {
            const value = formatter(item.value);
            if (item.strong) {
                return `<li><strong>${item.label}</strong><strong>${value}</strong></li>`;
            }
            return `<li><span>${item.label}</span><span>${value}</span></li>`;
        })
        .join("");
}
function buildOfferText(calc, packageDetails, budgetaryRange) {
    const formatter = (value) => formatCurrency(value, pricingConfig.currency);
    const company = pricingConfig.company_info || {};
    const contacts = company.contacts || {};
    const timelineLines = buildTimelineLines(calc.data, packageDetails);
    const lines = [
        `${company.name || "Vertex Design Buildings General Contracting Co."} (design-only offer)`,
        `Date: ${cachedElements.offerDate?.textContent || "-"}`,
        `Client: ${calc.data.clientName || "-"}`,
        `Project: ${calc.data.projectName || "-"}`,
        `Location: ${calc.data.location || "-"}`,
        `Scope: ${packageDetails.title || calc.data.package}`,
        "Deliverables:",
        ...listLines(packageDetails.deliverables),
        "Timeline:",
        ...listLines(timelineLines),
        "Stage Breakdown:",
        ...listLines(packageDetails.stage_breakdown),
        `Revisions Included: ${formatRevisions(packageDetails.revisions_included)}`,
        `Out-of-Scope: ${pricingConfig.revisions_out_of_scope_note}`,
        "Fee Summary (KWD):",
        `Base Fee (Area x Rate): ${formatter(calc.baseFee)}`,
        `Size Adjustment: ${formatter(calc.sizeAdjustment)}`,
        `Package Adjustment: ${formatter(calc.packageAdjustment)}`,
        `Complexity Addition: ${formatter(calc.complexityAddition)}`,
        calc.fastTrackAdjustment > 0
            ? `Fast-track Adjustment: ${formatter(calc.fastTrackAdjustment)}`
            : null,
        calc.minFeeAdjustment > 0
            ? `Minimum Fee Floor: ${formatter(calc.minFeeAdjustment)}`
            : null,
        `Site 1 Design Fee: ${formatter(calc.site1Fee)}`,
        calc.rollout.sites > 1
            ? `Rollout Adaptation (${calc.rollout.sites - 1} sites @ ${formatter(calc.rollout.perSiteFee)}): ${formatter(calc.rollout.total)}`
            : null,
        calc.addOns.items.length
            ? "Add-ons:"
            : null,
        ...addOnLines(calc.addOns.items, formatter),
        currentOfferMode === "budgetary"
            ? `Budgetary Range: ${formatter(budgetaryRange.lower)} - ${formatter(budgetaryRange.upper)}`
            : `Total Design Fee: ${formatter(calc.totalFee)}`,
        calc.data.urgency === "Fast-track"
            ? "Fast-track selected: additional resources and revision constraints apply."
            : null,
        "Assumptions:",
        ...listLines(pricingConfig.assumptions),
        "Exclusions:",
        ...listLines(pricingConfig.exclusions),
        `Validity: ${pricingConfig.offer_validity_days} days`,
        "Payment Terms:",
        ...paymentLines(),
        `Net ${pricingConfig.payment_terms?.net_days || 30} days`,
        "Next Steps:",
        ...listLines(pricingConfig.next_steps),
        "",
        company.name || "Vertex Design Buildings General Contracting Co.",
        ...(company.address_lines || []),
        "Contacts",
        `Tel: ${contacts.tel || "-"}`,
        `Mobile: ${contacts.mobile || "-"}`,
        `Email: ${contacts.email || "-"}`
    ].filter(Boolean);

    return lines.join("\n");
}

function addOnLines(items, formatter) {
    if (!items.length) return [];
    return items.map((item) => {
        if (item.quantity && item.quantity > 1) {
            return `- ${item.label} (${item.quantity}x): ${formatter(item.amount)}`;
        }
        return `- ${item.label}: ${formatter(item.amount)}`;
    });
}

function listLines(items) {
    if (!Array.isArray(items) || items.length === 0) {
        return ["- "];
    }
    return items.map((item) => `- ${item}`);
}

function buildPaymentTerms() {
    const milestones = pricingConfig.payment_terms?.milestones || [];
    if (!milestones.length) return "";
    return milestones
        .map((item) => `<li>${item.label}: ${item.percent}%</li>`)
        .join("");
}

function paymentLines() {
    const milestones = pricingConfig.payment_terms?.milestones || [];
    return milestones.map((item) => `- ${item.label}: ${item.percent}%`);
}

function buildBulletList(items) {
    if (!Array.isArray(items) || items.length === 0) {
        return "<li>-</li>";
    }
    return items.map((item) => `<li>${item}</li>`).join("");
}

function getTimelineLabel(packageCode, packageDetails) {
    const timeline = pricingConfig.timeline_by_package?.[packageCode] || {};
    if (timeline.label) {
        return timeline.label;
    }
    const range = formatWeeksRange(timeline.typical_weeks_min, timeline.typical_weeks_max);
    return range !== "-" ? range : packageDetails.typical_timeline_weeks || "-";
}

function buildTimelineLines(data, packageDetails) {
    const timeline = pricingConfig.timeline_by_package?.[data.package] || {};
    const minWeeks = toNumber(timeline.typical_weeks_min);
    const maxWeeks = toNumber(timeline.typical_weeks_max);
    const label = timeline.label || packageDetails.typical_timeline_weeks || "-";

    if (data.package === "C" && data.siteCount > 1) {
        const site1Label = formatWeeksRange(minWeeks, maxWeeks);
        const lines = [`Site 1: ${site1Label !== "-" ? site1Label : label}`];
        const minDays = toNumber(timeline.adaptation_days_min);
        const maxDays = toNumber(timeline.adaptation_days_max);
        if (minDays > 0 || maxDays > 0) {
            const totalMinDays = minDays * (data.siteCount - 1);
            const totalMaxDays = maxDays * (data.siteCount - 1);
            const daysText = formatRange(totalMinDays, totalMaxDays, "working days");
            const weekText = formatRange(
                roundToOneDecimal(totalMinDays / 5),
                roundToOneDecimal(totalMaxDays / 5),
                "weeks"
            );
            lines.push(`Sites 2+: ${daysText} total${weekText !== "-" ? ` (~${weekText})` : ""}`);
        }
        return lines;
    }

    return [label !== "-" ? label : formatWeeksRange(minWeeks, maxWeeks)];
}

function formatWeeksRange(min, max) {
    return formatRange(min, max, "weeks (working)");
}

function formatRange(min, max, suffix) {
    const minValue = toNumber(min);
    const maxValue = toNumber(max);
    if (!minValue && !maxValue) {
        return "-";
    }
    if (minValue && maxValue && minValue !== maxValue) {
        return `${minValue}-${maxValue} ${suffix}`;
    }
    const value = minValue || maxValue;
    return `${value} ${suffix}`;
}

function roundToOneDecimal(value) {
    if (!Number.isFinite(value)) return 0;
    return Math.round(value * 10) / 10;
}

function updatePackageDetails(packageCode) {
    const details = pricingConfig.package_details?.[packageCode] || {};
    if (cachedElements.packageTitle) {
        cachedElements.packageTitle.textContent = details.title || "-";
    }
    if (cachedElements.packagePurpose) {
        cachedElements.packagePurpose.textContent = details.purpose || "-";
    }
    populateList(cachedElements.packageDeliverables, details.deliverables);
    if (cachedElements.packageRevisions) {
        cachedElements.packageRevisions.textContent = formatRevisions(details.revisions_included);
    }
    if (cachedElements.packageTimeline) {
        cachedElements.packageTimeline.textContent = getTimelineLabel(packageCode, details);
    }
    populateList(cachedElements.packageStages, details.stage_breakdown);
}

function populateList(target, items) {
    if (!target) return;
    target.innerHTML = "";
    if (!Array.isArray(items) || items.length === 0) {
        const item = document.createElement("li");
        item.textContent = "-";
        target.appendChild(item);
        return;
    }
    items.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = entry;
        target.appendChild(item);
    });
}

function formatRevisions(value) {
    if (typeof value === "number") {
        return `${value} rounds`;
    }
    if (typeof value === "string" && value.trim()) {
        return value;
    }
    return "-";
}

function getBudgetaryRange(calc) {
    const minRate = toNumber(pricingConfig.anchor_rate_kwd_per_sqm_min);
    const maxRate = toNumber(pricingConfig.anchor_rate_kwd_per_sqm_max);
    if (calc && minRate > 0 && maxRate > 0 && maxRate >= minRate) {
        const lowerCalc = calculateOffer(calc.data, { anchorRate: minRate });
        const upperCalc = calculateOffer(calc.data, { anchorRate: maxRate });
        return {
            lower: Math.min(lowerCalc.totalFee, upperCalc.totalFee),
            upper: Math.max(lowerCalc.totalFee, upperCalc.totalFee)
        };
    }
    const total = calc?.totalFee || 0;
    const percent = toNumber(pricingConfig.budgetary_range_percent);
    const ratio = percent > 1 ? percent / 100 : percent;
    return {
        lower: total * (1 - ratio),
        upper: total * (1 + ratio)
    };
}

function copyOfferText() {
    const text = cachedElements.offerText.value;
    if (!text) {
        showFeedback("Generate the offer before copying.", true);
        return;
    }
    navigator.clipboard
        .writeText(text)
        .then(() => showFeedback("Offer copied to clipboard.", false))
        .catch(() => {
            cachedElements.offerText.select();
            document.execCommand("copy");
            showFeedback("Offer copied to clipboard.", false);
        });
}

function generateQuoteId() {
    const now = new Date();
    const yyyymmdd = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0")
    ].join("");
    const random = Math.floor(1000 + Math.random() * 9000);
    const id = `${yyyymmdd}-${random}`;
    if (cachedElements.quoteId) {
        cachedElements.quoteId.textContent = id;
    }
    // Sync to print header
    if (cachedElements.printQuoteId) {
        cachedElements.printQuoteId.textContent = id;
    }
    return id;
}

function formatCurrency(value, currency) {
    if (!Number.isFinite(value)) return "-";
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: currency || "KWD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

function resolveAnchorRate(override) {
    if (Number.isFinite(override)) {
        return override;
    }
    return toNumber(
        pricingConfig.anchor_rate_kwd_per_sqm_default || pricingConfig.anchor_rate_kwd_per_sqm
    );
}

function toNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

function capitalize(value) {
    if (!value) return "";
    return value.charAt(0).toUpperCase() + value.slice(1);
}

function showFeedback(message, isError) {
    if (!cachedElements.feedback) return;
    cachedElements.feedback.textContent = message;
    cachedElements.feedback.style.color = isError ? "#b45309" : "#0b5b4b";
}
