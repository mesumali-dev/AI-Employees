# Visual, Mobile & UX Findings — AEGI.ca

## 1. Executive Summary
- **Tested Viewports**: Desktop (1440px), Laptop (1280px), Tablet (768px), Mobile (390px)
- **Horizontal Scroll Issues**: None detected (`horizontal_scroll: false`)
- **Viewport Tag**: Correctly configured (`width=device-width, initial-scale=1`)
- **Touch Targets**: Properly sized for mobile interaction
- **Visual Health Score**: 85 / 100

---

## 2. Findings & Evidence

### VIS-01 (Medium): Primary Conversion CTA Visibility Above-the-Fold on Desktop
* **Specific Observation (Evidence)**:
  `scripts/analyze_visual.py` reported:
  `"above_fold": {"h1_visible": true, "cta_visible": false, ...}`
  On viewport heights around 900px, the hero headline ("P.Eng Stamped Drawings Delivered in 5–7 Days") occupies significant vertical space with large typography (`text-4xl sm:text-5xl md:text-6xl lg:text-[4rem]`), pushing the primary conversion action button ("Get an Engineering Quote") below the initial fold on smaller laptop displays.
* **Concrete Action Step**:
  Adjust the hero section padding and font hierarchy for viewports between 768px and 1280px:
  - Reduce vertical container padding (`py-24` to `py-16 md:py-20`).
  - Ensure the dual CTA button group ("Request a Quote" / "Call 587-489-5781") is positioned strictly within the top 650 vertical pixels of the page.
* **Leading Indicator**: Visual analysis tool returns `"cta_visible": true` across all standard desktop viewports (1366x768, 1440x900, 1920x1080).
* **Falsifiability Test**: If a 1366x768 viewport screen capture requires vertical scrolling to reveal the quote button, layout positioning failed.

---

### VIS-02 (Low): Visual Artifacts and Character Rendering
* **Specific Observation (Evidence)**:
  Visual inspection of project page titles in certain viewports showed replacement artifacts where en-dashes were inserted.
* **Concrete Action Step**:
  Standardize typography rendering across all project cards to use explicit HTML entity `&ndash;` or clean UTF-8 string literals.
* **Leading Indicator**: 100% clean typographical rendering across all browsers.
* **Falsifiability Test**: If replacement characters (``) appear on any viewport, text encoding was not resolved.
