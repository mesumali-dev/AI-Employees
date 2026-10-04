# Content Quality & E-E-A-T Audit Findings — AEGI.ca

## 1. Executive Summary
- **Total Content Pages Evaluated**: 13 Blog Articles + 8 Core Service Pages
- **Average Word Count (Blog)**: 1,280 words (High technical depth)
- **Primary Strengths**: Citations of Canadian and provincial codes (APEGA, CSA Z662, API 650, Alberta Building Code)
- **Primary Vulnerabilities**: Systemic title tag double-branding bloat, meta description truncation, and anonymous author bylines (weak E-E-A-T)
- **Content Quality Health Score**: 74 / 100

---

## 2. Findings & Evidence

### CONT-01 (High): Systemic Title Tag Double-Branding Causing SERP Truncation
* **Specific Observation (Evidence)**:
  All 13 blog articles and several service pages suffer from a Next.js metadata template misconfiguration that appends the brand name twice.
  Examples:
  - `Haul Road Design: 7 Key Engineering Considerations | AEGI Alberta | AEGI - Advanced Engineering Group Inc.` (106 characters)
  - `Why a Site Grading Plan Is Essential in Construction | AEGI Alberta | AEGI - Advanced Engineering Group Inc.` (108 characters)
  - `Multi-Disciplinary Engineering in Construction | AEGI Edmonton | AEGI - Advanced Engineering Group Inc.` (103 characters)
  Google truncates title tags at approximately 580–600 pixels (~55–60 characters). The double brand suffix (`| AEGI Alberta | AEGI - Advanced Engineering Group Inc.`) completely displaces the primary intent keywords from search snippets.
* **Concrete Action Step**:
  In `app/layout.tsx` (or `app/blog/[slug]/page.tsx`), update the Next.js `title.template` string:
  ```typescript
  // Before:
  title: {
    template: '%s | AEGI | AEGI - Advanced Engineering Group Inc.',
    default: 'AEGI - Advanced Engineering Group Inc.',
  }

  // After:
  title: {
    template: '%s | AEGI Engineering',
    default: 'AEGI Engineering | P.Eng Certified Engineering in Alberta',
  }
  ```
  Ensure all page titles are capped at 50–58 characters total.
* **Leading Indicator**: SERP preview tools and Google Search Console URL inspection confirm title lengths stay below 60 characters with 0 pixel overflow.
* **Falsifiability Test**: If Google SERP snippets show `...` truncation before the primary keyword or brand name on desktop or mobile, title formatting remains unoptimized.

---

### CONT-02 (Medium): Meta Description Character Length Exceeds Optimal Pixel Budget
* **Specific Observation (Evidence)**:
  Meta descriptions across multiple technical articles exceed 180–205 characters:
  - `/blog/power-of-precision-top-electrical-engineering-services`: 207 characters
  - `/blog/achieve-project-goals-with-trusted-civil-engineering-consulting-services`: 204 characters
  - `/blog/role-of-multi-disciplinary-engineering-in-modern-construction`: 200 characters
  Google mobile snippets truncate at ~130–150 characters, and desktop at ~160 characters. Key CTAs and value propositions are cut off mid-sentence.
* **Concrete Action Step**:
  Rewrite all meta descriptions to fit within 135–155 characters. Place the primary keyword, geographic scope (e.g. Edmonton/Alberta), and P.Eng stamping capability in the first 120 characters:
  *Example Fix*: "AEGI provides CSA Z662-compliant oil & gas pipeline engineering in Alberta. Fast P.Eng stamped drawings, AER submissions, and corrosion design." (144 chars).
* **Leading Indicator**: Average meta description length across the site drops to 145 characters with zero snippet truncation in SERP simulators.
* **Falsifiability Test**: If SERP display snippets show ellipsis (`...`) chopping off contact or service information, length reduction targets were not met.

---

### CONT-03 (High): Anonymous By-lines on Engineering Analysis (E-E-A-T Deficiency)
* **Specific Observation (Evidence)**:
  Blog posts provide deep technical analyses of safety-critical subjects (structural inspection reports, oil tank foundations, underground utilities, stormwater hydrology). However, articles are published without an individual author byline, biographical credentials, or professional licensing registration (e.g., "Written by [Engineer Name], P.Eng, Senior Civil Engineer, APEGA License #[X]").
* **Analysis**:
  Under Google's Search Quality Rater Guidelines (E-E-A-T), technical and engineering topics that influence structural safety, financial investment, and regulatory compliance demand verifiable individual expertise.
* **Concrete Action Step**:
  1. Add an author card at the top and bottom of each article displaying the engineer's name, photo, P.Eng designation, and professional summary.
  2. Create dedicated `/team/[author-slug]` bio pages linking to their LinkedIn profile, professional licensing body (APEGA/EGBC), and published project work.
  3. Map this data directly to the `author` field in the `BlogPosting` schema.
* **Leading Indicator**: Google Search Console impressions increase for author entity queries, and the site ranks higher for high-intent technical long-tail keywords.
* **Falsifiability Test**: If content pages continue to show generic company attribution without a named author profile after 60 days, E-E-A-T implementation failed.

---

### CONT-04 (Medium): Heading Formatting & Semantic Tag Integrity
* **Specific Observation (Evidence)**:
  In multiple blog posts, internal numbering conventions are injected directly into the H1:
  - `PROTOCOL #010 Oil and Gas Pipeline Engineering: Designing Safe...`
  - `PROTOCOL #009 The Role of Multi-Disciplinary Engineering...`
  While internal classification codes are useful for documentation, placing "PROTOCOL #00X" inside the `<h1>` dilutes search engine keyword weighting.
* **Concrete Action Step**:
  Separate internal protocol badges from the primary `<h1>` text. Render the protocol badge as an independent `<span class="badge">Protocol #010</span>` above the `<h1>`, keeping the `<h1>` strictly focused on the primary keyword topic: `<h1>Oil and Gas Pipeline Engineering in Alberta</h1>`.
* **Leading Indicator**: Top-level heading element text perfectly matches target search intent in page audits.
* **Falsifiability Test**: If `<h1>` elements still contain non-search prefixes in the rendered DOM, component separation was incomplete.
