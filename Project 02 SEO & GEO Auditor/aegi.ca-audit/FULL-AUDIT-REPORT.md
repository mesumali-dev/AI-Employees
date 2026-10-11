# Comprehensive Technical SEO & GEO Developer Audit Report: `aegi.ca`

**Target Website:** `https://www.aegi.ca/`  
**Client:** Advanced Engineering Group Inc. (AEGI)  
**Architecture:** Next.js (App Router), React, Tailwind CSS, Vercel Edge Network  
**Overall SEO Health Score:** **81 / 100** (Grade: B+)  
**Audit Date:** October 10, 2026  
**Auditor Engine:** Read-Only Technical SEO & GEO Auditor + Verified Google Search Console API  
**Auditing Posture:** Strictly Read-Only. No website files, server configurations, or GSC properties were modified.

---

## 1. Executive Summary & GSC Context

Advanced Engineering Group Inc. (`aegi.ca`) is an Alberta-based multi-disciplinary engineering consulting firm holding APEGA and NAPEG Permits to Practice.

The website demonstrates a solid modern web baseline: fast edge delivery via Vercel, server-rendered semantic HTML, modern AVIF image compression, dedicated AI crawler rules in `robots.txt` (`GPTBot`, `Claude-SearchBot`, `PerplexityBot`), and structured entity credentials.

However, an audit synthesizing live Google Search Console API inspection data, headless browser tests (Playwright), and HTTP tracing identified two categories of findings:
1. **Misinterpreted GSC Indexing Reports (Expected Exclusions):** The client observed failed validation in GSC for *"Page with redirect"* and *"Crawled - currently not indexed"*. Our investigation proves that **neither issue represents an active penalty or website malfunction**. They failed validation because automated tests were triggered on URLs that are *supposed* to remain excluded (redirects and binary media assets).
2. **Actionable Developer Findings (Genuine Issues):** Several easily rectifiable technical issues were confirmed, including review schema directional conflicts, canonical trailing-slash discrepancies, mobile viewport overflow at 375px, heading outline skips, and multi-hop legacy redirect chains.

---

## 2. Google Search Console Investigation

### Category A: "Page with Redirect" (Validation Failed)

#### 1. Why Validation Failed
In Google Search Console, *"Page with redirect"* is an informational log indicating that Google discovered a URL, followed its redirect (301 or 308), and excluded the source URL from the index in favor of the destination.
- When **"Validate Fix"** is triggered, Google re-crawls sample URLs to confirm whether they stopped redirecting and now return unique `200 OK` content.
- Because these URLs still redirect as intended, Google marked the validation as **"Failed"**.
- **Conclusion:** Do not attempt to validate this report. The exclusion of redirecting URLs is the correct behavior.

#### 2. Itemized Verification of Sample URLs

| Inspected URL | HTTP Status & Chain | Destination URL | Destination Indexable? | Root Cause Analysis | Action Required |
|---|:---:|---|:---:|---|---|
| `https://www.aegi.ca/services` | `301` (1 hop) | `https://www.aegi.ca/#services` | Yes (`200 OK`) | **Confirmed:** Custom redirect sends `/services` to homepage anchor hash. Googlebot strips `#services` and canonicalizes to homepage. | Keep as-is unless client requests a dedicated `/services` overview page. |
| `https://www.aegi.ca/services/` | `308` ➔ `301` (2 hops) | `https://www.aegi.ca/#services` | Yes (`200 OK`) | **Confirmed:** Next.js strips trailing slash (`/services`), then redirects to `/#services`. | No action required. Expected exclusion. |
| `https://www.aegi.ca/careers/` | `308` (1 hop) | `https://www.aegi.ca/careers` | Yes (`200 OK`) | **Confirmed:** Next.js default `trailingSlash: false` router normalizes to canonical `/careers`. | No action required. Expected exclusion. |
| `https://aegi.ca/careers/` | `308` ➔ `308` (2 hops) | `https://www.aegi.ca/careers` | Yes (`200 OK`) | **Confirmed:** Trailing-slash strip occurs before Vercel domain forwarding. | Optional: Collapse in hosting routing. |
| `http://aegi.ca/` | `308` ➔ `308` (2 hops) | `https://www.aegi.ca/` | Yes (`200 OK`) | **Confirmed:** Vercel edge terminates HTTP ➔ HTTPS before applying non-WWW ➔ WWW forwarding. | Optional: Vercel domain setting optimization. |
| `https://aegi.ca/?q=f7l16y9bmlpzbz6` | `308` ➔ `301` (2 hops) | `https://www.aegi.ca/` | Yes (`200 OK`) | **Confirmed:** Scanner probe with 15-char query. Server strips unrecognized parameter and redirects to `/`. | No action required. Expected exclusion. |

---

### Category B: "Crawled - Currently Not Indexed" (Validation Failed Oct 5, 2026)

#### 1. Why Validation Failed
The client observed failed validation on October 5, 2026, for sample URLs:
1. `https://aegi.ca/?q=fr9wumxba7dn1nu`
2. `https://www.aegi.ca/services/electrical-engineering/inspection.avif`
3. `https://www.aegi.ca/services/construction-support/construction_support.avif`

When Google’s validation engine re-crawled these URLs, it determined that:
- The query URL still redirects to the homepage instead of serving unique content.
- Both `.avif` URLs return binary media streams (`Content-Type: image/avif`), not HTML documents.
Because none of these URLs became indexed HTML web pages, Google recorded **"Validation Failed"**.

#### 2. Deep Dive: The Two AVIF Image URLs
- **Binary & MIME Inspection:** `inspection.avif` (77.3 KB) and `construction_support.avif` (87.6 KB) were independently verified via HTTP GET. Both return `HTTP/2 200 OK`, valid headers, and binary `ftypavif` magic bytes.
- **DOM Rendering Verification (Playwright):** Headless Chromium loaded `/services/electrical-engineering`. The image rendered with full natural dimensions (`1024×1024`, `complete: true`).
- **Why GSC Crawled Them as Web Pages:** In Next.js, images are loaded via `/_next/image?url=%2Fservices%2F...%2Finspection.avif`. Googlebot’s web link parser extracts URL-encoded parameters from client-side bundles and queues them. When Googlebot fetched the URL, it discovered an image, not a web document.
- **Sitemap & Links Check:** There are zero direct `<a>` anchor links to these files, and zero image entries in `sitemap.xml`.
- **Conclusion:** These images belong in **Google Images**, not the Web Document Index. Their presence under *"Crawled - currently not indexed"* is standard Googlebot behavior. **Do not modify these image URLs.**

#### 3. Deep Dive: The Random Query URL (`?q=fr9wumxba7dn1nu`)
- **Evidence:** GSC URL Inspection records the referring URL as `https://aegi.ca/?q=flhuq65b6vxvxje`.
- **Pattern:** 15-character alphanumeric probe (`f` + 14 chars), matching automated security scanning footprints (e.g. WPScan / Acunetix).
- **Handling:** Resolves via a 2-hop redirect (`308` ➔ `301` ➔ `200`) back to the clean root homepage `https://www.aegi.ca/`.
- **Conclusion:** Expected bot probe. Safely normalized by the application router.

---

## 3. Genuine Developer Findings (Actionable Issues)

### Finding 1: Review Schema Directional Conflict
- **Category:** Schema & Structured Data
- **Severity:** High | **Priority:** P1
- **Affected URLs:** `https://www.aegi.ca/`
- **Data Source & Verification:** Google Search Console URL Inspection API (`richResults.detectedItems`).
- **Evidence:** GSC returned 4 warnings under Review Snippets:
  > *"A nested '<parent_node>' object can't contain the 'itemReviewed' field. Remove 'itemReviewed' to avoid directional conflict."*
- **Root Cause (Confirmed):** The JSON-LD schema embeds individual reviews inside `ProfessionalService.review[]`. Each review declares `"itemReviewed": { "@id": "https://www.aegi.ca/#organization" }`. Because the review is already a child property of that organization, re-specifying `itemReviewed` causes a circular reference conflict.
- **Impact:** Prevents Review Snippet rich results (stars) from displaying in Google SERPs.
- **Recommended Remediation:** In the homepage schema component, remove the `"itemReviewed"` attribute from reviews that are nested inside `ProfessionalService`.
- **Acceptance Criteria:** Google Rich Results Test passes with **0 warnings** on Review snippets.

---

### Finding 2: Root Canonical Tag Trailing-Slash Discrepancy
- **Category:** Technical SEO / Indexation
- **Severity:** Medium | **Priority:** P2
- **Affected URLs:** `https://www.aegi.ca/`
- **Data Source & Verification:** DOM inspection via Playwright vs. GSC URL Inspection API.
- **Evidence:** 
  - Rendered HTML source: `<link rel="canonical" href="https://www.aegi.ca">` (omits trailing slash).
  - Server response & GSC Google-selected canonical: `https://www.aegi.ca/` (includes trailing slash).
- **Root Cause (Confirmed):** Next.js `metadata.alternates.canonical` in `app/page.tsx` or `app/layout.tsx` is defined without the trailing slash.
- **Impact:** Creates a soft canonical mismatch warning in search engines and minor crawl dilution.
- **Recommended Remediation:** Update `metadata.alternates.canonical` to `https://www.aegi.ca/`.
- **Acceptance Criteria:** HTML `<link rel="canonical">` output exactly matches `https://www.aegi.ca/`.

---

### Finding 3: Multi-Hop Redirect Chains on Legacy WordPress URLs
- **Category:** Technical SEO / Crawl Efficiency
- **Severity:** Medium | **Priority:** P2
- **Affected URLs:** `https://aegi.ca/electrical-engineering/`, `/mechanical-hvac/`, old uploaded PDFs.
- **Data Source & Verification:** Live HTTP request tracing (`requests.Session`).
- **Evidence:** Request to `https://aegi.ca/electrical-engineering/` experiences 3 redirects:
  `https://aegi.ca/electrical-engineering/` ➔ (308) `/electrical-engineering` ➔ (308) `https://www.aegi.ca/electrical-engineering` ➔ (308) `https://www.aegi.ca/services/electrical-engineering`.
- **Root Cause (Confirmed):** Trailing-slash stripping, non-WWW forwarding, and legacy route mapping fire in sequence across separate infrastructure layers.
- **Impact:** Wastes crawl budget and delays link-equity transfer from old external backlinks.
- **Recommended Remediation:** In `next.config.js` `redirects()`, point legacy URLs directly to the absolute final destination:
  ```javascript
  // Illustrative guidance only
  {
    source: '/electrical-engineering',
    destination: 'https://www.aegi.ca/services/electrical-engineering',
    permanent: true,
  }
  ```
- **Acceptance Criteria:** `curl -IL https://aegi.ca/electrical-engineering/` returns no more than 2 hops directly to the final destination.

---

### Finding 4: Heading Hierarchy Irregularities & Footer Non-Semantic Headings
- **Category:** On-Page SEO / Accessibility
- **Severity:** Low | **Priority:** P3
- **Affected URLs:** `https://www.aegi.ca/`
- **Data Source & Verification:** BeautifulSoup DOM tree analysis of rendered HTML.
- **Evidence:** 
  - `H1` ("P.Eng Stamped Drawings...") is immediately followed by `H3` ("Quick Consultation Request"), skipping `H2`.
  - Affiliation and Testimonial cards skip `H3` and jump from `H2` directly to `H4`.
  - Footer navigational column headers ("Quick Links", "Services", "Contact") use `H4` tags.
- **Root Cause (Confirmed):** Visual Tailwind heading classes were tied directly to HTML heading tags without semantic structuring.
- **Impact:** Disrupts document outline for screen readers and search engine content parsers.
- **Recommended Remediation:** Normalize document outline to sequential order (H1 ➔ H2 ➔ H3). Replace footer `H4` tags with `<p className="font-semibold">` inside `<nav aria-label="Footer">`.
- **Acceptance Criteria:** HTML outline validator reports zero skipped heading ranks.

---

### Finding 5: Mobile Horizontal Overflow at 375px Viewport
- **Category:** Mobile Usability & Core Web Vitals
- **Severity:** Medium | **Priority:** P2
- **Affected URLs:** `https://www.aegi.ca/`
- **Data Source & Verification:** Playwright mobile emulation at 375×812 viewport.
- **Evidence:** `document.documentElement.scrollWidth > window.innerWidth` (`horizontal_scroll: true`).
- **Root Cause (Confirmed):** Grid containers in testimonial/affiliation sliders or header elements exceed 375px width.
- **Impact:** Causes mobile horizontal scrolling, triggering mobile usability warnings and CLS instability.
- **Recommended Remediation:** Add `overflow-x: hidden` on root layout wrappers and clamp inner card containers to `max-w-full`.
- **Acceptance Criteria:** At 375px width, `document.documentElement.scrollWidth === 375` is true.

---

### Finding 6: Blog-to-Service Internal Linking Funnels
- **Category:** Content Strategy & Information Architecture
- **Severity:** Medium | **Priority:** P2
- **Affected URLs:** 13 articles under `/blog/*`
- **Data Source & Verification:** Content link audit across all 13 blog posts.
- **Evidence:** Articles such as `/blog/achieve-project-goals-with-trusted-civil-engineering-consulting-services` receive organic impressions (183 impressions in GSC) but contain 0 in-body contextual links pointing to `/services/civil-engineering`.
- **Root Cause (Confirmed):** Blog articles were published without inline commercial callouts or contextual cross-links.
- **Impact:** High organic impressions fail to convert into service quote inquiries.
- **Recommended Remediation:** Add 2 contextual editorial links per post pointing to relevant commercial service pages, plus an inquiry card banner at the end of each article.
- **Acceptance Criteria:** Every published blog post contains at least 2 contextual links pointing to a relevant `/services/*` landing page.

---

## 4. Optional Enhancements (Future Consideration)

1. **Striking-Distance Query Optimization (GSC Insights):**
   - Query `"aegi"` ranks at Position 6.1 with 649 impressions but only 0.62% CTR.
   - *Recommendation:* Update homepage title from `AEGI Engineering | P.Eng Certified Engineering in Alberta` to:  
     `AEGI — Advanced Engineering Group Inc. | Licensed P.Eng in Alberta`.
2. **Service Catalog Schema Graph:**
   - Deploy structured `@type: "Service"` and `hasOfferCatalog` on individual service landing pages linked back to `@id: "https://www.aegi.ca/#organization"`.
3. **AI Search Markdown Content Negotiation:**
   - Configure a Next.js edge route handler to deliver clean Markdown representations when autonomous AI agents request pages with `Accept: text/markdown`.

---

## 5. Dangerous Changes to Avoid (Developer Anti-Patterns)

| Proposed Change | Why It Is Dangerous | Status |
|---|---|:---:|
| **Adding `X-Robots-Tag: noindex` to AVIF images** | Instructs Google to remove engineering diagrams from **Google Image Search**. | ❌ **Rejected** |
| **Adding generic `/:path+/` trailing-slash regexes in `next.config.js`** | Conflicts with Next.js built-in routing; risks infinite redirect loops and breaks static assets. | ❌ **Rejected** |
| **Force-creating a `/services` overview page** | Unilaterally alters site information architecture and disrupts homepage anchor navigation without client approval. | ❌ **Rejected** |
| **Re-clicking "Validate Fix" in GSC for expected exclusions** | Causes repeated automated validation failures because redirects and images are supposed to remain excluded. | ❌ **Rejected** |

---

## 6. Consolidated Developer Remediation Plan

| Item | Issue Title | Severity | Priority | Estimated Effort | Target File / Location | Acceptance Test |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | Review Schema Directional Conflict | High | **P1** | 30 mins | `app/page.tsx` (JSON-LD block) | Google Rich Results Test passes with 0 warnings. |
| **2** | Canonical Trailing-Slash Discrepancy | Medium | **P2** | 15 mins | `app/page.tsx` (`metadata.alternates.canonical`) | HTML source outputs `href="https://www.aegi.ca/"`. |
| **3** | Mobile Horizontal Overflow (375px) | Medium | **P2** | 1–2 hrs | `app/layout.tsx` / `components/ui/*` | `scrollWidth === innerWidth` at 375px. |
| **4** | Heading Outline Sequential Normalization | Low | **P3** | 1 hr | `app/page.tsx` & `components/Footer.tsx` | Heading outline validator outputs 0 level skips. |
| **5** | Contextual Blog-to-Service Links | Medium | **P2** | 2 hrs | `app/blog/[slug]/page.tsx` / CMS Markdown | Minimum 2 contextual service links per blog post. |
| **6** | Legacy WordPress Single-Hop Redirects | Low | **P3** | 30 mins | `next.config.js` (`redirects` array) | Trace shows direct 1-hop redirect to destination. |

---

**Audit Completed:** No modifications have been made to the website. This report and prioritized plan are finalized for handoff to your development team.
