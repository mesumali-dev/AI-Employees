# Developer Remediation Plan: `aegi.ca`

**Status:** Handoff Ready. Strictly Informational / Advisory.  
**Auditor Role:** Analysis and documentation only. No website source files, server configurations, or GSC properties have been modified.

---

## 1. Executive Remediation Summary

This remediation plan organizes developer tasks by priority, estimated effort, and expected business/search impact. It distinguishes **actionable technical fixes** from **healthy, expected GSC exclusions** that must not be altered.

---

## 2. Prioritized Task Matrix

| ID | Issue Title | Severity | Priority | Effort | Confidence | Target Location | Acceptance Criteria |
|:---:|---|:---:|:---:|:---:|:---:|---|---|
| **P1.1** | **Review Schema Directional Conflict** | High | **P1** | ~30 min | 100% (GSC Verified) | `app/page.tsx` or `components/Schema.tsx` | Google Rich Results Test passes with 0 warnings on Review snippets. |
| **P2.1** | **Root Canonical Trailing-Slash Discrepancy** | Medium | **P2** | ~15 min | 100% (DOM & GSC Verified) | `app/page.tsx` (`metadata.alternates.canonical`) | HTML source outputs `<link rel="canonical" href="https://www.aegi.ca/">`. |
| **P2.2** | **Mobile Horizontal Overflow at 375px** | Medium | **P2** | 1–2 hrs | 100% (Playwright Verified) | `app/layout.tsx` / card slider CSS | `document.documentElement.scrollWidth === window.innerWidth` at 375px width. |
| **P2.3** | **Blog-to-Service Internal Linking Funnels** | Medium | **P2** | 2 hrs | 100% (Content Audit) | `app/blog/[slug]/page.tsx` or blog content | Every blog article includes 2+ contextual links pointing to commercial service pages. |
| **P3.1** | **Heading Hierarchy Normalization** | Low | **P3** | 1 hr | 100% (DOM Verified) | `app/page.tsx` & `components/Footer.tsx` | Outline validator outputs sequential headings (H1 ➔ H2 ➔ H3); footer headings converted to `<p>`. |
| **P3.2** | **Direct Single-Hop Legacy WordPress Redirects** | Low | **P3** | ~30 min | 100% (HTTP Trace Verified) | `next.config.js` (`redirects` array) | `curl -IL https://aegi.ca/electrical-engineering/` reaches final destination without intermediate hops. |

---

## 3. Detailed Developer Implementation Guidance

### Task P1.1: Remove Circular `itemReviewed` in Nested Review Schema
- **Evidence:** GSC URL Inspection on `https://www.aegi.ca/` raised 4 warnings: *"A nested '<parent_node>' object can't contain the 'itemReviewed' field. Remove 'itemReviewed' to avoid directional conflict."*
- **Source File:** `app/page.tsx` or your root JSON-LD structured data generator.
- **Implementation Guidance (Illustrative):**
  ```diff
  // In your ProfessionalService review array:
  "review": [
    {
      "@type": "Review",
      "author": { "@type": "Person", "name": "Salim Rana" },
      "reviewRating": { "@type": "Rating", "ratingValue": "5", "bestRating": "5" },
      "reviewBody": "Advanced Engineering Group Inc did a great job...",
  -   "itemReviewed": { "@id": "https://www.aegi.ca/#organization" }
    }
  ]
  ```
- **Post-Fix Verification:** Run `https://www.aegi.ca/` in [Google Rich Results Test](https://search.google.com/test/rich-results) and verify 0 warnings under Review Snippets.

---

### Task P2.1: Align Canonical Tag Trailing Slash
- **Evidence:** HTML declares `https://www.aegi.ca` (no slash), but server response and Google-selected canonical is `https://www.aegi.ca/`.
- **Source File:** `app/page.tsx` or `app/layout.tsx`.
- **Implementation Guidance (Illustrative):**
  ```diff
  export const metadata = {
    alternates: {
  -   canonical: 'https://www.aegi.ca',
  +   canonical: 'https://www.aegi.ca/',
    },
  };
  ```
- **Post-Fix Verification:** `curl -s https://www.aegi.ca/ | grep 'rel="canonical"'` confirms `href="https://www.aegi.ca/"`.

---

### Task P2.2: Resolve Mobile Horizontal Overflow at 375px
- **Evidence:** Playwright emulation at 375×812 detected `scrollWidth > innerWidth` (`horizontal_scroll: true`).
- **Source File:** `app/layout.tsx` and container components in "Consultancy Insights" and "Our Work Values".
- **Implementation Guidance (Illustrative):**
  - Add `overflow-x-hidden` on parent layout wrapper:
    ```tsx
    <main className="min-h-screen overflow-x-hidden max-w-full">
    ```
  - Ensure card sliders or logo rows utilize `max-w-full` rather than fixed pixel minimums.
- **Post-Fix Verification:** In browser dev tools set to iPhone SE/12 (375px width), confirm horizontal scrolling is completely eliminated.

---

### Task P2.3: Build Editorial Internal Links from 13 Blog Articles
- **Evidence:** 13 technical articles receive organic impressions in GSC but contain 0 in-body links or inquiry banners pointing to `/services/*`.
- **Source File:** Blog markdown content / CMS.
- **Implementation Guidance:**
  - Add 2 contextual editorial links per post pointing to the relevant engineering service page.
  - Add an inline callout block at the bottom of each article:
    `"Need P.Eng stamped drawings for your project? Contact our licensed engineers for a consultation."` ➔ linking to `/get-quote` or the relevant `/services/:slug`.
- **Post-Fix Verification:** Verify with an internal link crawler that all 13 articles pass link equity to core service URLs.

---

### Task P3.1: Sequential Heading Structure Normalization
- **Evidence:** Homepage outline skips from H1 to H3, and H2 to H4. Footer navigation uses H4 headings.
- **Source File:** `app/page.tsx` and `components/Footer.tsx`.
- **Implementation Guidance:**
  - Change "Quick Consultation Request" from `H3` to `H2` or a stylized `<p>`.
  - Change affiliation and testimonial headers from `H4` to `H3`.
  - In `components/Footer.tsx`, change `H4` tags ("Quick Links", "Services", "Contact") to `<p className="font-semibold text-sm">` inside `<nav aria-label="Footer">`.
- **Post-Fix Verification:** Run an accessibility/heading outline validator and verify zero skipped heading ranks.

---

### Task P3.2: Direct Legacy URL Redirect Mapping
- **Evidence:** Requests to legacy WordPress URLs (e.g. `https://aegi.ca/electrical-engineering/`) experience 3 hops before reaching the destination.
- **Source File:** `next.config.js`.
- **Implementation Guidance (Illustrative):**
  ```javascript
  // next.config.js
  module.exports = {
    async redirects() {
      return [
        {
          source: '/electrical-engineering',
          destination: 'https://www.aegi.ca/services/electrical-engineering',
          permanent: true,
        },
        {
          source: '/mechanical-hvac',
          destination: 'https://www.aegi.ca/services/mechanical-hvac',
          permanent: true,
        },
      ];
    },
  };
  ```
- **Post-Fix Verification:** `curl -IL https://aegi.ca/electrical-engineering/` reaches the final destination with no unnecessary intermediate hops.

---

## 4. What Developers Should NOT Change (Safe GSC Exclusions)

1. **Do NOT add `X-Robots-Tag: noindex` to AVIF images:**
   - Appears in GSC Page Indexing because images are binary assets, not web documents.
   - Adding `noindex` removes them from **Google Image Search**. Leave them as-is.
2. **Do NOT add generic trailing-slash regexes in `next.config.js`:**
   - Next.js natively manages `trailingSlash: false`. Custom regexes risk routing conflicts and infinite loops.
3. **Do NOT create a standalone `/services` page without client approval:**
   - AEGI deliberately routes `/services` ➔ `/#services` to present their service cards on the homepage, while maintaining 8 separate service sub-pages.
4. **Do NOT click "Validate Fix" in Google Search Console:**
   - Validating expected redirects or media assets triggers automated validation failure because these URLs are intended to remain excluded.
