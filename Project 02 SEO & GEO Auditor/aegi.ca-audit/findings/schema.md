# Schema & Structured Data Audit Findings — AEGI.ca

## 1. Executive Summary
- **Total Validated Pages**: 34 URLs
- **Current Schemas Detected**: `WebSite`, `ProfessionalService`, `Service`, `BreadcrumbList`, `FAQPage`
- **Missing Core Schemas**: `BlogPosting` / `Article` on all 13 blog publications
- **Broken Endpoints in Schema**: Sitelinks `SearchAction` targets a 404 URL
- **Schema Health Score**: 64 / 100

---

## 2. Findings & Evidence

### SCHEMA-01 (Critical): Dead Internal Search Target in Sitelinks Searchbox (`SearchAction`)
* **Specific Observation (Evidence)**:
  On the homepage and multiple subpages, the `WebSite` JSON-LD contains:
  ```json
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "AEGI - Advanced Engineering Group Inc.",
    "url": "https://www.aegi.ca",
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://www.aegi.ca/search?q={search_term_string}",
      "query-input": "required name=search_term_string"
    }
  }
  ```
  Sending an HTTP GET request to `https://www.aegi.ca/search?q=test` returns **HTTP 404 Not Found**. Google explicitly requires that the URL template declared in `SearchAction` must return valid search results. Having a non-existent search route violates Google's Structured Data guidelines.
* **Concrete Action Step**:
  Remove `potentialAction: SearchAction` from `WebSite` schema unless a functional internal site search route is implemented and deployed.
* **Leading Indicator**: Schema.org Rich Results Test reports 0 invalid actions or dead target parameters on `WebSite` markup.
* **Falsifiability Test**: If a GET request to the `potentialAction.target` template continues to return HTTP 404, the fix was not deployed.

---

### SCHEMA-02 (High): Missing `BlogPosting` / `Article` Schema Across All 13 Technical Blog Posts
* **Specific Observation (Evidence)**:
  Inspection of all 13 blog post URLs (e.g. `/blog/structural-engineering-report-alberta`, `/blog/stormwater-management-design`) reveals only 3 schemas: `WebSite`, `ProfessionalService`, and `BreadcrumbList`. There is **zero article-level structured data**. As a result, Google Search and AI engines cannot identify the article headline, author entity, publication date, modification date, or featured image.
* **Concrete Action Step**:
  Implement a dynamic `BlogPosting` schema in the Next.js blog template (`app/blog/[slug]/page.tsx`):
  ```json
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "What Is a Structural Engineering Report and When Do You Need One?",
    "description": "Comprehensive guide on structural engineering reports in Alberta...",
    "image": "https://www.aegi.ca/images/blog/structural-report.jpg",
    "datePublished": "2026-08-15T08:00:00+00:00",
    "dateModified": "2026-10-01T19:55:42+00:00",
    "author": {
      "@type": "Person",
      "name": "Senior Structural Engineer, P.Eng",
      "jobTitle": "Principal Structural Engineer",
      "affiliation": {
        "@type": "Organization",
        "name": "Advanced Engineering Group Inc."
      }
    },
    "publisher": {
      "@id": "https://www.aegi.ca/#organization"
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": "https://www.aegi.ca/blog/structural-engineering-report-alberta"
    }
  }
  ```
* **Leading Indicator**: Google Search Console URL Inspection confirms "Articles" structured data detected on all 13 blog URLs within 14 days of re-crawl.
* **Falsifiability Test**: If Rich Results Test reports "No Article structured data found" on any `/blog/*` URL, template integration failed.

---

### SCHEMA-03 (Medium): Multiple Redundant Global Schema Blocks Injected Per Page
* **Specific Observation (Evidence)**:
  On service pages (e.g. `/services/civil-engineering`), 5 separate unlinked `<script type="application/ld+json">` tags are injected: `WebSite`, `ProfessionalService`, `Service`, `BreadcrumbList`, and `FAQPage`. This creates fragmented entity definitions where `Service.provider` is disconnected from `ProfessionalService`.
* **Concrete Action Step**:
  Consolidate into a single `@graph` JSON-LD object using `@id` references:
  - `"@id": "https://www.aegi.ca/#organization"`
  - `"@id": "https://www.aegi.ca/#website"`
  - Connect `Service.provider` directly to `{"@id": "https://www.aegi.ca/#organization"}`.
* **Leading Indicator**: The Schema Markup Validator shows a single interconnected knowledge graph for each page without orphaned entities.
* **Falsifiability Test**: If Google's Rich Results Test continues to parse multiple disconnected root entities for the same organization, graph linking was omitted.

---

### SCHEMA-04 (Info): Deprecated `FAQPage` Rich Result Status
* **Specific Observation (Evidence)**:
  `FAQPage` schema is embedded on `/about` and all service landing pages.
* **Analysis**:
  Google officially retired `FAQPage` rich results globally for commercial sites on May 7, 2026. While the markup does not trigger a Google manual penalty, it will no longer produce expandable accordion snippets in SERPs.
* **Action Step**:
  Retain existing FAQ schema if used for internal data feeding or voice bots, but do not prioritize new `FAQPage` generation for SERP visibility. Ensure answer content remains directly accessible in the visible HTML for user consumption and LLM extraction.
* **Leading Indicator**: Editorial team stops allocating resources to FAQ SERP schema and focuses on visible structured headings.
* **Falsifiability Test**: N/A (informational guidance).
