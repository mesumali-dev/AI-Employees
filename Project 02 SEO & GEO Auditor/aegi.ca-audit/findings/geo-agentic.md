# Generative Engine Optimization (GEO) & Agent Readiness — aegi.ca

**Target Domain:** `https://www.aegi.ca/`  
**GEO / Agent Readiness Score:** 88 / 100

---

## 1. AI Engine Discovery & Citability Signals

### What Is Working Exceptionally Well
- **Deliberate AI Crawler Allowances in `robots.txt`**:
  - AEGI has already implemented dedicated user-agent allowances for major AI foundation crawlers:
    `GPTBot`, `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Google-Extended`, and `Applebot-Extended`.
  - All bot directives explicitly permit access to site pages and AI resources.
- **`llms.txt` and `llms-full.txt` Implemented**:
  - Both files exist at root (`/llms.txt` at 5.0 KB, `/llms-full.txt` at 7.7 KB).
  - Both return `HTTP 200 OK` and follow the Lighthouse / llmstxt.org structure.
- **Server-Side Rendered HTML**:
  - Primary text and content are 100% visible in raw HTML without requiring JavaScript execution, ensuring low-resource crawlers (Perplexity, ChatGPT Search, Gemini) extract complete text without timeout.

---

## 2. Areas for GEO Enhancement

### Finding 1.1: Missing Markdown Negotiation for AI Agents
- **Specific Observation (Evidence):**
  - Agent-readiness inspection confirmed that while `/llms.txt` exists, individual landing pages do not support content negotiation (`Accept: text/markdown`) or link to markdown equivalents via `<link rel="alternate" type="text/markdown" href="...">`.
- **Concrete Action Step:**
  - Add a route handler or edge function in Next.js that inspects incoming `Accept: text/markdown` headers and returns clean Markdown representations of service and project pages, or expose static `.md` mirrors.
- **Leading Indicator:**
  - `curl -H "Accept: text/markdown" https://www.aegi.ca/services/civil-engineering` returns raw markdown content.
- **Falsifiability Test:**
  - If a curl request with `Accept: text/markdown` returns standard HTML or 406 Not Acceptable, markdown delivery has failed.

---

### Finding 1.2: Entity Disambiguation for Perplexity & ChatGPT Citation
- **Specific Observation (Evidence):**
  - In `robots.txt` and homepage text, AEGI is cited under both "Advanced Engineering Group Inc." and "AEGI".
  - Schema defines both names, but Wikidata / Wikipedia entity connections and Canadian federal business registry numbers (e.g. Alberta Corporate Registry / NEB) are not linked under `sameAs` or `identifier`.
- **Concrete Action Step:**
  - Add official regulatory and corporate registry links to `sameAs` in Organization JSON-LD:
    - Official APEGA Permit directory verification URL.
    - Better Business Bureau (BBB) profile.
    - Dun & Bradstreet / OpenCorporates / Canadian business directory profiles.
- **Leading Indicator:**
  - Organization JSON-LD contains 3+ verifiable third-party authority links under `sameAs`.
- **Falsifiability Test:**
  - If an AI search query in Perplexity ("Who is AEGI in Alberta?") hallucinates or fails to identify AEGI as Advanced Engineering Group Inc., entity disambiguation has failed.
