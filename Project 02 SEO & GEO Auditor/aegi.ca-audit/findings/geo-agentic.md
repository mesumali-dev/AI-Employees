# Generative Engine Optimization (GEO) & Agentic Readiness — AEGI.ca

## 1. Executive Summary
- **Auditing Tool**: `scripts/agentic_check.py`
- **AI Agent Access Status**: Open by default (no explicit blocks)
- **`llms.txt` / `llms-full.txt`**: 404 Not Found
- **`.well-known/ai-catalog.json`**: 404 Not Found
- **Markdown Delivery Negotiation**: Not supported (HTML fallback)
- **Passage-Level Citability**: Moderate (strong technical data, but lacks direct answer summaries)
- **GEO & Agentic Health Score**: 58 / 100

---

## 2. Findings & Evidence

### GEO-01 (High): Missing `llms.txt` and LLM Context Architecture
* **Specific Observation (Evidence)**:
  `scripts/agentic_check.py` confirmed `https://www.aegi.ca/llms.txt` and `https://www.aegi.ca/llms-full.txt` return **HTTP 404**. When LLM-powered answer engines (ChatGPT Search, Perplexity, Claude, Gemini) explore a technical domain, `llms.txt` provides a structured, token-efficient index of core services, capabilities, regional regulatory accreditations, and engineering leadership.
* **Concrete Action Step**:
  Deploy a clean `public/llms.txt` file in the Next.js repository:
  ```markdown
  # AEGI — Advanced Engineering Group Inc.
  > Multidisciplinary engineering consultancy founded in 2007 in Edmonton, Alberta. APEGA Permit Holder providing P.Eng stamped drawings.

  ## Core Engineering Services
  - [Civil Engineering](https://www.aegi.ca/services/civil-engineering): Grading design, stormwater management, drainage plans.
  - [Structural Engineering](https://www.aegi.ca/services/structural-engineering): Commercial, industrial, and residential structural analysis, API 650 tank foundations.
  - [Mechanical HVAC](https://www.aegi.ca/services/mechanical-hvac): Commercial HVAC, plumbing, ventilation compliance.
  - [Electrical Engineering](https://www.aegi.ca/services/electrical-engineering): Industrial power distribution, CSA C22.1 compliance.
  - [Construction Support](https://www.aegi.ca/services/construction-support): Field reviews, inspections, as-built documentation.

  ## Regulatory Accreditations
  - APEGA Permit to Practice (Alberta)
  - Engineers and Geoscientists BC (EGBC)
  ```
* **Leading Indicator**: `curl -I https://www.aegi.ca/llms.txt` returns HTTP 200 with `content-type: text/plain; charset=utf-8`.
* **Falsifiability Test**: If LLMs crawling the domain receive a 404 status code for `/llms.txt`, the deployment was not synced to the production CDN.

---

### GEO-02 (High): Absence of Direct Definition Snippets for AI Overview Ingestion
* **Specific Observation (Evidence)**:
  Analysis of technical blog articles shows long narrative introductions without structured, extractable answer summaries. For example, in `/blog/structural-engineering-report-alberta`, the explanation of when a structural report is legally mandatory in Alberta is distributed across several paragraphs rather than isolated in an executive answer block.
* **Concrete Action Step**:
  Add an "Executive Answer" callout block (45–60 words) immediately below the main H1 or first H2 on each technical guide:
  *Example Structure*:
  > **Quick Summary (P.Eng Guide)**: A structural engineering report in Alberta is legally required when modifying load-bearing elements, validating foundation cracks under the Alberta Building Code, permitting commercial changes of use, or completing insurance damage assessments. Reports must be signed and stamped by an APEGA-licensed Professional Engineer (P.Eng).
* **Leading Indicator**: Content passage appears as a cited source in Google AI Overviews and Perplexity search answers for "when is a structural engineering report required in Alberta".
* **Falsifiability Test**: If AI search engines continue to cite competitor engineering firms with zero citations for AEGI after 45 days, passage structure requires further atomic optimization.

---

### GEO-03 (Medium): Unspecified AI Agent Governance Directives
* **Specific Observation (Evidence)**:
  `scripts/agentic_check.py` detected that `robots.txt` has no explicit rules for AI user agents (`GPTBot`, `Claude-SearchBot`, `PerplexityBot`, `Google-Extended`). While they default to `User-Agent: *`, lack of explicit directives leaves crawl frequency unmanaged and fails to distinguish between search citation vs model training scraping.
* **Concrete Action Step**:
  Add clear crawler directives in `robots.txt` allowing search/citation bots (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) while asserting copyright and data usage intentions.
* **Leading Indicator**: `agentic_check.py` reports green status on all P0/P1 agent-readiness audit checks.
* **Falsifiability Test**: If AI bot access logs indicate crawling ambiguity or blockages, governance definitions were incomplete.
