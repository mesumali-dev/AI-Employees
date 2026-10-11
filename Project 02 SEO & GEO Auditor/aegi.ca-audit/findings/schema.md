# Structured Data & Schema Findings — aegi.ca

**Target Domain:** `https://www.aegi.ca/`  
**Current Types:** `WebSite`, `ProfessionalService`, `BreadcrumbList`, `FAQPage`, `Review`, `AggregateRating`  
**Schema Score:** 75 / 100

---

## 1. Schema Validation & Google Rich Result Issues

### Finding 1.1: Directional Conflict on Nested `Review` Schema (GSC Flagged)
- **Specific Observation (Evidence):**
  - Live Google Search Console URL Inspection on `https://www.aegi.ca/` raised 4 Warnings under Review Snippets:
    > *"A nested '<parent_node>' object can't contain the 'itemReviewed' field. Remove 'itemReviewed' to avoid directional conflict."*
  - The JSON-LD embeds reviews inside `ProfessionalService.review[]`, and each review item includes `"itemReviewed": {"@id": "https://www.aegi.ca/#organization"}`.
  - Because the review is already an explicit property of the parent organization, re-declaring `itemReviewed` causes a circular reference.
- **Concrete Action Step:**
  - Remove `"itemReviewed"` from inside individual reviews when they are nested inside `ProfessionalService`. The parent entity is automatically interpreted by Google as the entity being reviewed.
- **Leading Indicator:**
  - Re-testing the URL in Google's Rich Results Test tool or GSC URL Inspection returns 0 warnings under Review Snippets.
- **Falsifiability Test:**
  - If GSC URL Inspection still outputs `issueMessage: "A nested '<parent_node>' object can't contain the 'itemReviewed' field"`, the fix has failed.

---

### Finding 1.2: Deprecated `FAQPage` Rich Result Markup on Commercial Pages
- **Specific Observation (Evidence):**
  - Service pages (e.g. `/services/civil-engineering`) embed an extensive 4,430-byte `FAQPage` JSON-LD block.
  - Per Google's official Search documentation (August 2023 update onwards), `FAQPage` rich results are strictly limited to authoritative government and health sites. Commercial B2B service sites do not receive FAQ accordion snippets in SERPs.
- **Concrete Action Step:**
  - Keep the FAQ questions and answers in user-visible HTML for user utility and LLM citability, but replace the schema type with structured `Service` and `Offer` schema, or associate FAQs via semantic entity relations rather than relying on `FAQPage` rich result badges.
- **Leading Indicator:**
  - Service pages feature structured `Service` markup with `provider`, `serviceType`, and `areaServed` directly linked to `@id: "https://www.aegi.ca/#organization"`.
- **Falsifiability Test:**
  - If service pages lack a dedicated `Service` entity graph recognized by Google's Rich Results Test, the schema enhancement has failed.

---

### Finding 1.3: Missing Service Catalog Schema Graph
- **Specific Observation (Evidence):**
  - AEGI offers 8 distinct engineering services (Civil, Structural, Mechanical HVAC, Electrical, Project Management, Construction Support, Material Takeoff, Machine Control Model).
  - The organization markup includes credentials (`hasCredential` for APEGA), but lacks an `hasOfferCatalog` or individual `@type: "Service"` nodes linking each service URL to the parent organization.
- **Concrete Action Step:**
  - Implement a clean Schema.org graph connecting all 8 service landing pages:
    ```json
    {
      "@type": "Service",
      "@id": "https://www.aegi.ca/services/civil-engineering#service",
      "name": "Civil Engineering Consulting Services",
      "provider": { "@id": "https://www.aegi.ca/#organization" },
      "areaServed": [
        { "@type": "AdministrativeArea", "name": "Alberta" },
        { "@type": "City", "name": "Edmonton" },
        { "@type": "City", "name": "Calgary" }
      ],
      "hasCredential": {
        "@type": "EducationalOccupationalCredential",
        "name": "APEGA Permit to Practice"
      }
    }
    ```
- **Leading Indicator:**
  - Google Schema Validator detects valid interconnected `@graph` nodes linking Service ➔ Organization ➔ Credentials.
- **Falsifiability Test:**
  - If Schema.org validator reports disconnected or unlinked nodes on service URLs, the graph integration has failed.
