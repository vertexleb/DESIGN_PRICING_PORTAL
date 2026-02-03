# Vertex Design - Design Services Calculator

**Version**: 3.0.0  
**Last Updated**: 2026-02-03

Professional, client-facing design services pricing calculator with automatic project classification and instant proposal generation. Static web app—runs entirely in the browser, GitHub Pages compatible.

---

## Features

- **Fact-Based Classification**: Project size, complexity, scale, and façade scope derived from objective inputs—no manual "small/simple" selection
- **Modular Service Selection**: Choose from 8 service blocks (S1-S6 + SF1-SF2) or use quick presets
- **Anti-Gaming Boundaries**: Classification locked with reasoning displayed; override requires acknowledgment
- **Timeline Engine**: Automatic duration calculation with parallel work overlap
- **Quote History**: Save and load previous quotes via localStorage
- **PDF Export**: Direct PDF download without print dialog
- **Mobile Responsive**: Works on all devices

---

## Quick Start

1. Open `index.html` in your browser (Chrome, Edge, Firefox, Safari)
2. Follow the 5-step wizard:
   - **Step 1**: Enter project facts (area, spaces, type, systems, scale, façade)
   - **Step 2**: Review derived classification
   - **Step 3**: Select services (or use presets: Starter / Standard / Complete)
   - **Step 4**: Review quote breakdown with "Why this price?" explanation
   - **Step 5**: Download PDF or save quote

### Local Development

```bash
# Python 3
python -m http.server 8000

# Node.js
npx serve
```

Then open `http://localhost:8000`

---

## Classification Axes

| Axis | Derived From | Levels |
|------|--------------|--------|
| **Size** | Area + Spaces | Small / Medium / Large |
| **Complexity** | Project Type + Special Systems | Simple / Normal / Complex |
| **Scale** | Number of Sites | Single / Multi / Rollout |
| **Façade** | Façade Type Selection | F0-F3 |

### Thresholds (Defaults)

- **Small**: ≤100 sqm AND ≤4 spaces
- **Medium**: ≤350 sqm AND ≤12 spaces
- **Large**: Above medium
- **Complex Types**: F&B, Clinic, Hospital, Data Center
- **Multi-site**: 2-5 sites; **Rollout**: 6+ sites

---

## Service Blocks

| ID | Service | Base Fee |
|----|---------|----------|
| S1 | Design Visualization | KWD 800 |
| S2 | Architectural Design Package | KWD 1,200 |
| S3 | MEP Design Package | KWD 600 |
| S4 | Material & Detail Specs | KWD 500 |
| S5 | Tender Documentation | KWD 400 |
| S6 | BOQ & Cost Documentation | KWD 350 |
| SF1 | Façade Design & Detailing | KWD 600 |
| SF2 | Signage & Branding Integration | KWD 400 |

Prices are multiplied by classification factors.

---

## Configuration

All pricing logic is in `assets/app.js` under `PRICING_CONFIG`. Key adjustable values:

- `thresholds`: Size, complexity, scale boundaries
- `multipliers`: Pricing multipliers per classification
- `services`: Base fees and durations
- `addons`: Add-on prices
- `rollout`: Adaptation percentages

---

## File Structure

```
/
├── index.html          # Main application (5-step wizard)
├── robots.txt          # Search engine blocking
├── README.md           # This file
└── assets/
    ├── app.js          # Application logic + PRICING_CONFIG
    ├── styles.css      # Styling
    └── logo.png        # Company logo
```

---

## Deployment

### GitHub Pages
1. Push to a GitHub repository
2. Enable Pages in Settings → Pages
3. Select main branch as source

### Static Hosting
Works with any static file host (Netlify, Vercel, S3). No build step.

---

## Security

- **XSS Protection**: All user inputs escaped before rendering
- **No External APIs**: All calculations client-side
- **No Data Transmission**: Form data stays in browser
- **Classification Lock**: Anti-gaming boundaries prevent manipulation

---

## Changelog

### v3.0.0 (2026-02-03)
- Complete redesign: service-based pricing replaces package-based
- Added 4-axis classification engine (Size, Complexity, Scale, Façade)
- Added modular service blocks (S1-S6 + SF1-SF2)
- Added timeline engine with overlap calculation
- Added quote history with localStorage
- Added preset packages (Starter / Standard / Complete)
- Added anti-gaming classification boundaries
- Added "Why this price?" explanation
- Improved proposal with selected/excluded services

### v2.0.0
- Wizard-style form, PDF download, accessibility improvements

### v1.0.0
- Initial release
