# Technical SEO Audit Findings — aegi.ca

**Target Domain:** `https://www.aegi.ca/`  
**Host Environment:** Next.js on Vercel Edge Network  
**Technical Score:** 78 / 100

---

## 1. Crawlability & Canonicalization

### Finding 1.1: Multi-Hop Canonical Redirect Chain on HTTP & Non-WWW
- **Specific Observation (Evidence):**
  - Request to `http://aegi.ca` issues `308 Permanent Redirect` to `https://aegi.ca/`, which then issues a second `308 Permanent Redirect` to `https://www.aegi.ca/`.
  - Request to `https://aegi.ca/electrical-engineering/` issues `308` to `/electrical-engineering`, which issues a second `308` to `https://www.aegi.ca/services/electrical-engineering`.
  - In Google Search Console, `http://aegi.ca/` and legacy WordPress URLs (`/electrical-engineering/`, `/mechanical-hvac/`) still appear with residual impressions.
- **Concrete Action Step:**
  - In `next.config.js` or Vercel routing configuration, collapse all HTTP, non-WWW, and legacy trailing-slash rules into single-hop 301/308 redirects directly to the canonical destination:
    `http://aegi.ca/*` ➔ `https://www.aegi.ca/*`
    `/:legacy-service/` ➔ `https://www.aegi.ca/services/:legacy-service`
- **Leading Indicator:**
  - Running `curl -IL http://aegi.ca` yields exactly 1 redirect hop (`HTTP/2 308` followed immediately by `HTTP/2 200` from `https://www.aegi.ca/`).
- **Falsifiability Test:**
  - If a curl trace still records more than 1 redirect hop or if GSC reports `Page with redirect` count climbing for legacy URLs after 28 days, this fix has failed.

---

### Finding 1.2: Root Canonical Tag Trailing Slash Discrepancy
- **Specific Observation (Evidence):**
  - The rendered homepage HTML declares: `<link rel="canonical" href="https://www.aegi.ca">` (without a trailing slash).
  - The server default and Google-selected canonical URL is `https://www.aegi.ca/` (with a trailing slash).
  - Google URL Inspection confirms: `google_canonical: https://www.aegi.ca/`.
- **Concrete Action Step:**
  - Update Next.js `metadata.alternates.canonical` in `app/page.tsx` or `app/layout.tsx` to include the canonical trailing slash: `https://www.aegi.ca/`.
- **Leading Indicator:**
  - HTML `<link rel="canonical">` matches the exact URL returned in HTTP headers (`https://www.aegi.ca/`).
- **Falsifiability Test:**
  - If URL Inspection in GSC flags "User-declared canonical" different from "Google-selected canonical", the fix has failed.

---

## 2. Mobile Layout & Usability

### Finding 2.1: Mobile Horizontal Overflow at 375px Viewport
- **Specific Observation (Evidence):**
  - Playwright mobile emulation at 375px width (iPhone standard viewport) detected `scrollWidth > innerWidth` (`horizontal_scroll: true`).
  - Container width in navigation or service cards causes horizontal scrolling, damaging mobile user experience and Core Web Vitals stability.
- **Concrete Action Step:**
  - Inspect grid containers in the header and "Consultancy Insights" / "Our Work Values" sections. Add `overflow-x-hidden` on parent wrappers or clamp min-widths to `max-w-full`.
- **Leading Indicator:**
  - `document.documentElement.scrollWidth === window.innerWidth` across all viewports from 320px to 414px.
- **Falsifiability Test:**
  - If a headless Chromium test at 375x812 reports `document.documentElement.scrollWidth > 375`, the layout fix has failed.

---

## 3. Semantic Heading Hierarchy

### Finding 3.1: Heading Level Skips and Footer Non-Semantic Headings
- **Specific Observation (Evidence):**
  - The homepage hierarchy skips heading ranks: `H1` ("P.Eng Stamped Drawings...") is immediately followed by `H3` ("Quick Consultation Request"), skipping `H2`.
  - Under `H2` ("Our Affiliations") and `H2` ("Consultancy Insights"), child items skip `H3` and jump directly to `H4`.
  - Footer navigational columns use `H4` ("Quick Links", "Services", "Contact"), injecting non-content navigation text into document outline.
- **Concrete Action Step:**
  - Restructure heading hierarchy:
    - Change consultation title to an `H2` or stylized `p` tag.
    - Change affiliation cards and testimonial author names to semantic `H3` elements.
    - Replace footer `H4` tags with `<p className="font-semibold text-sm">` inside semantic `<nav aria-label="Footer">` containers.
- **Leading Indicator:**
  - Running HTML outline validator outputs zero skipped heading levels (H1 ➔ H2 ➔ H3).
- **Falsifiability Test:**
  - If automated heading audit detects any jump from H1 directly to H3 or H2 directly to H4, the semantic fix has failed.
