# Technical SEO Audit Findings — AEGI.ca

## 1. Executive Summary
- **Target URL**: https://www.aegi.ca/
- **Hosting / Platform**: Next.js App Router (SSG/ISR) on Vercel CDN
- **Total Indexed Pages in Sitemap**: 34 URLs
- **Broken Internal Links**: 0 (100% crawl success rate)
- **Technical Health Score**: 72 / 100

---

## 2. Findings & Evidence

### TECH-01 (High): Legacy WordPress Directives in `robots.txt` on a Next.js Site
* **Specific Observation (Evidence)**:
  `https://www.aegi.ca/robots.txt` contains:
  ```text
  User-Agent: *
  Allow: /
  Disallow: /private/
  Disallow: /admin/
  Disallow: /api/
  Disallow: /shop/
  Disallow: /shop
  Disallow: /wp-content/
  Disallow: /wp-admin/
  Disallow: /wp-includes/
  Disallow: /wp-json/
  ```
  The site is fully built on Next.js/Vercel, yet contains legacy WordPress paths (`/wp-content/`, `/wp-includes/`). Furthermore, it lacks explicit crawl guidance for AI search and training bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended).
* **Concrete Action Step**:
  Replace `robots.txt` with a clean Next.js configuration. Add dedicated AI search crawler rules:
  ```text
  User-Agent: *
  Allow: /
  Disallow: /api/
  Disallow: /admin/

  # AI Search & Retrieval Crawlers (Allow)
  User-agent: OAI-SearchBot
  Allow: /

  User-agent: Claude-SearchBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /

  Sitemap: https://www.aegi.ca/sitemap.xml
  ```
* **Leading Indicator**: Search console robots.txt fetcher validates 0 syntax warnings and 0 legacy crawl queries within 48 hours.
* **Falsifiability Test**: If access logs show 404 crawler attempts on non-existent `/wp-admin/` or if AI search engines fail to cite site content within 30 days, the robots configuration failed to clarify site architecture.

---

### TECH-02 (Medium): Multi-Hop Redirect Chain on Non-Secure / Non-WWW Variants
* **Specific Observation (Evidence)**:
  Requesting `http://aegi.ca` produces a two-hop redirect chain:
  `http://aegi.ca` $\rightarrow$ `308 https://aegi.ca/` $\rightarrow$ `301 https://www.aegi.ca/`.
* **Concrete Action Step**:
  Configure edge redirect rules in `vercel.json` or DNS-level domain forwarding to redirect `http://aegi.ca`, `http://www.aegi.ca`, and `https://aegi.ca` directly to `https://www.aegi.ca/` in a single 301 hop.
* **Leading Indicator**: `curl -ILs http://aegi.ca` outputs exactly one 301 response code before reaching `https://www.aegi.ca/` (200 OK).
* **Falsifiability Test**: If testing any protocol/host combination results in `chain length > 1`, redirect edge configuration is incomplete.

---

### TECH-03 (Medium): Missing Standard Security Headers
* **Specific Observation (Evidence)**:
  HTTP response inspection reveals `Strict-Transport-Security: max-age=63072000` is present, but the following headers are completely missing:
  - `X-Frame-Options` (Clickjacking vulnerability)
  - `X-Content-Type-Options: nosniff` (MIME sniffing prevention)
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy`
  - `Permissions-Policy`
* **Concrete Action Step**:
  Add standard security headers in `next.config.js` via the `headers()` configuration:
  ```javascript
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' }
        ],
      },
    ];
  }
  ```
* **Leading Indicator**: Security header scanners (e.g. securityheaders.com) award grade A/A+ within 24 hours of deployment.
* **Falsifiability Test**: If any page response header lacks `X-Content-Type-Options: nosniff` or `X-Frame-Options: DENY`, the deployment failed.

---

### TECH-04 (Low): Trailing Slash Normalization & Sitemaps Consistency
* **Specific Observation (Evidence)**:
  `sitemap.xml` lists all paths without trailing slashes (e.g. `https://www.aegi.ca/about`), which return 200 OK. Requests with trailing slashes (`https://www.aegi.ca/about/`) trigger 308 redirects to non-trailing slash versions. All canonical tags correctly declare the non-trailing slash variant.
* **Concrete Action Step**:
  Maintain strict enforcement of trailing slash canonicalization across all internal links, preventing unnecessary 308 redirect overhead for internal crawlers.
* **Leading Indicator**: Internal link crawler reports 0 redirect hops on internal anchor paths.
* **Falsifiability Test**: If internal links contain trailing slashes that trigger 308 redirects, internal linking QA failed.
