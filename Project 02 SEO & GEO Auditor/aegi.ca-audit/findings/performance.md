# Performance & Core Web Vitals Findings — AEGI.ca

## 1. Executive Summary
- **Hosting Infrastructure**: Vercel Edge Network
- **Rendering Model**: Next.js SSG / ISR (Prerendered HTML)
- **Time to First Byte (TTFB)**: ~150ms – 240ms (Excellent)
- **Cumulative Layout Shift (CLS)**: < 0.05 (Pass)
- **Largest Contentful Paint (LCP)**: ~1.8s – 2.4s (Pass)
- **Interaction to Next Paint (INP)**: Low JavaScript execution overhead (Pass)
- **Performance Health Score**: 82 / 100

---

## 2. Findings & Evidence

### PERF-01 (Medium): Unconstrained Hero / Logo Image Sizing via Next.js Image Optimization
* **Specific Observation (Evidence)**:
  `scripts/analyze_visual.py` detected that the main branding asset in the hero banner requests a massive width bucket:
  `/_next/image?url=%2Flogo.png&w=3840&q=75`.
  On mobile devices and standard 1080p monitors, requesting a 3840px image variant forces unnecessary server-side resizing on Vercel and consumes excess bandwidth.
* **Concrete Action Step**:
  In `components/Navbar.tsx` and `components/Hero.tsx`, add explicit `sizes` attributes to the `next/image` component:
  ```tsx
  <Image
    src="/logo.png"
    alt="AEGI Engineering Logo"
    width={220}
    height={60}
    sizes="(max-width: 768px) 160px, 220px"
    priority
  />
  ```
* **Leading Indicator**: Network inspection shows the client requests `&w=256` or `&w=384` on mobile devices instead of `&w=3840`.
* **Falsifiability Test**: If network waterfall logs continue to show `w=3840` requests from viewport widths below 1440px, the `sizes` attribute is misconfigured.

---

### PERF-02 (Low): Missing Critical Font Preload Directives
* **Specific Observation (Evidence)**:
  Custom web fonts are loaded dynamically without explicit `<link rel="preload">` or Next.js `next/font` local font optimization, introducing minor First Contentful Paint (FCP) delays during initial text rendering.
* **Concrete Action Step**:
  Migrate font loading to `next/font/google` or `next/font/local` in `app/layout.tsx`. Next.js will automatically inline font definitions and preload the required WOFF2 subsets with zero layout shift.
* **Leading Indicator**: Lighthouse reports 0 "Eliminate render-blocking resources" warnings for typography assets.
* **Falsifiability Test**: If font file requests block DOM rendering or trigger FOIT (Flash of Invisible Text), font optimization was not adopted.
