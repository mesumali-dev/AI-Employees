# Upstream Change Manifest (v2.4.2-3-g4b99de2)

**Upstream Commit**: `4b99de2`  
**Source**: `https://github.com/AgriciDaniel/claude-seo.git`

> [!IMPORTANT]
> **Agent Directive**: Do NOT blindly copy Claude Code files over Antigravity files.
> Apply each change using Antigravity CLI conventions (Windows UTF-8, UV execution, Playwright timeout fallbacks, and preserved author footer).

## Summary of Changes
- **Scripts Modified / New**: 4
- **References & Assets**: 0
- **Skill Prompts**: 24
- **Agents**: 19
- **Dependencies**: 0

## 1. Scripts
### `analyze_visual.py` (MODIFIED) - ⚠️ **[PROTECTED - WINDOWS/SSR PATCH]**
- **Reason**: Contains Windows UTF-8 reconfigure and resilient page.goto(wait_until='load') fallback for Next.js SSR.
- **Antigravity Rule**: Do NOT replace wait_until='load' with wait_until='networkidle'. Keep sys.stdout.reconfigure.
```diff
--- local/analyze_visual.py
+++ upstream/analyze_visual.py
@@ -11,13 +11,6 @@
 import os
 import sys
 from urllib.parse import ParseResult, urlparse
-
-if sys.platform == "win32":
-    try:
-        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
-        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
-    except Exception:
-        pass
 
 try:
     from playwright.sync_api import TimeoutError as PlaywrightTimeout
@@ -109,17 +102,7 @@
             desktop = browser.new_context(viewport={"width": 1920, "height": 1080})
             page = desktop.new_page()
             page.route("**/*", route_handler)
-            try:
-                page.goto(url, wait_until="load", timeout=timeout)
-            except PlaywrightTimeout:
-                try:
-                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
-                except Exception:
-                    pass
-            try:
-                page.wait_for_timeout(500)
-            except Exception:
-                pass
+            page.goto(url, wait_until="networkidle", timeout=timeout)
 
             # Check H1 visibility above fold
             h1 = page.query_selector("h1")
@@ -174,17 +157,7 @@
             mobile = browser.new_context(viewport={"width": 375, "height": 812})
             page = mobile.new_page()
             page.route("**/*", route_handler)
-            try:
-                page.goto(url, wait_until="load", timeout=timeout)
-            except PlaywrightTimeout:
-                try:
-                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
-                except Exception:
-                    pass
-            try:
-                page.wait_for_timeout(500)
-            except Exception:
-                pass
+            page.goto(url, wait_until="networkidle", timeout=timeout)
 
             # Check viewport meta
             viewport_meta = page.query_selector('meta[name="viewport"]')

```

### `capture_screenshot.py` (MODIFIED) - ⚠️ **[PROTECTED - WINDOWS/SSR PATCH]**
- **Reason**: Contains Windows UTF-8 reconfigure, resilient load timeout, and Unicode fallback print.
- **Antigravity Rule**: Do NOT replace wait_until='load' with wait_until='networkidle'. Keep UnicodeEncodeError handler.
```diff
--- local/capture_screenshot.py
+++ upstream/capture_screenshot.py
@@ -19,13 +19,6 @@
 import os
 import sys
 from urllib.parse import ParseResult, urlparse
-
-if sys.platform == "win32":
-    try:
-        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
-        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
-    except Exception:
-        pass
 
 try:
     from playwright.sync_api import (
@@ -142,20 +135,11 @@
             # private IP even after Chromium re-resolves DNS.
             page.route("**/*", route_handler)
 
-            # Navigate with resilient fallback for SSR / dynamic pages
-            try:
-                page.goto(url, wait_until="load", timeout=timeout)
-            except PlaywrightTimeout:
-                try:
-                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
-                except Exception:
-                    pass
+            # Navigate and wait for network idle
+            page.goto(url, wait_until="networkidle", timeout=timeout)
 
             # Wait a bit more for any lazy-loaded content
-            try:
-                page.wait_for_timeout(1000)
-            except Exception:
-                pass
+            page.wait_for_timeout(1000)
 
             # Capture screenshot
             page.screenshot(path=output_path, full_page=full_page)
@@ -217,16 +201,10 @@
             timeout=args.timeout,
         )
 
-        try:
-            if result["success"]:
-                print(f"  ✓ Saved to {output_path}")
-            else:
-                print(f"  ✗ Failed: {result['error']}")
-        except UnicodeEncodeError:
-            if result["success"]:
-                print(f"  [OK] Saved to {output_path}")
-            else:
-                print(f"  [FAIL] Failed: {result['error']}")
+        if result["success"]:
+            print(f"  ✓ Saved to {output_path}")
+        else:
+            print(f"  ✗ Failed: {result['error']}")
 
 
 if __name__ == "__main__":

```

### `google_auth.py` (MODIFIED) - ✅ **[SAFE TO PORT]**
- **Instruction**: Port upstream bug fixes/features into `scripts/google_auth.py` using Antigravity standards.
```diff
--- local/google_auth.py
+++ upstream/google_auth.py
@@ -202,19 +202,25 @@
 
 
 def _prefers_gcloud() -> bool:
-    """CLAUDE_SEO_GOOGLE_AUTH=adc or ANTIGRAVITY_SEO_GOOGLE_AUTH=adc picks the gcloud sign-in."""
-    val = os.environ.get("ANTIGRAVITY_SEO_GOOGLE_AUTH", "") or os.environ.get("CLAUDE_SEO_GOOGLE_AUTH", "")
-    return val.strip().lower() in ("adc", "gcloud")
+    """CLAUDE_SEO_GOOGLE_AUTH=adc picks the gcloud sign-in even when a service
+    account is configured (which may not have access to every property)."""
+    return os.environ.get("CLAUDE_SEO_GOOGLE_AUTH", "").strip().lower() in ("adc", "gcloud")
 
 
 def get_gcloud_credentials(scopes: list):
     """Credentials from the person's own gcloud sign-in
     (`gcloud auth application-default login`), or None.
+
+    Read from the gcloud file directly, never through google.auth.default(),
+    which would load GOOGLE_APPLICATION_CREDENTIALS (a service account) first.
     """
     if _load_gcloud_adc() is None:
         return None
     try:
         from google.oauth2.credentials import Credentials
+        # Refresh with the scopes granted at `gcloud auth application-default login`:
+        # asking for others (say, full webmasters over webmasters.readonly) fails
+        # with invalid_scope. `scopes` is accepted for symmetry and not sent.
         return Credentials.from_authorized_user_file(_gcloud_adc_path())
     except Exception as e:
         print(f"gcloud sign-in could not be used: {type(e).__name__}", file=sys.stderr)
@@ -368,7 +374,7 @@
     """
     config = load_config()
 
-    # An explicit choice of gcloud sign-in wins.
+    # An explicit choice of the person's own gcloud sign-in wins.
     if _prefers_gcloud():
         creds = get_gcloud_credentials(scopes)
         if creds is not None:
@@ -408,7 +414,7 @@
             except ImportError:
                 print("Error: google-auth required. Install with: pip install google-auth", file=sys.stderr)
 
-    # Fall back to service account, then to gcloud sign-in.
+    # Fall back to service account, then to the person's gcloud sign-in.
     return get_service_account_credentials(scopes) or get_gcloud_credentials(scopes)
 
 
@@ -643,6 +649,7 @@
         # Check OAuth token first
         token_data = _load_oauth_token()
         if _prefers_gcloud() and _load_gcloud_adc() is not None:
+            # Chosen with CLAUDE_SEO_GOOGLE_AUTH=adc: used first, so reported first.
             result["available"] = True
             result[
... (diff truncated, see JSON for full diff) ...
```

### `schema_generate.py` (MODIFIED) - ⚠️ **[PROTECTED - WINDOWS/SSR PATCH]**
- **Reason**: Contains custom author profile metadata in docstrings.
- **Antigravity Rule**: Preserve author profile 'Syed Mesum Ali Shah' in examples.
```diff
--- local/schema_generate.py
+++ upstream/schema_generate.py
@@ -34,9 +34,10 @@
         --date 2026-05-12T14:00:00Z
 
     python scripts/schema_generate.py profile \\
-        --name "Syed Mesum Ali Shah" \\
-        --url https://www.mesumali.xyz \\
-        --same-as https://www.linkedin.com/in/mesumali-dev \\
+        --name "Daniel Agrici" \\
+        --url https://agricidaniel.com/about \\
+        --same-as https://github.com/AgriciDaniel \\
+                  https://twitter.com/agricidaniel \\
         --knows-about "SEO" "Schema markup" "Core Web Vitals"
 
 All generators emit JSON-LD with ``@context: https://schema.org`` and

```

## 3. Skill Prompts (`SKILL.md`)
- **`.agents/skills/seo-agentic/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-audit/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-backlinks/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-cluster/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-competitor-pages/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-content/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-dataforseo/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-drift/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-ecommerce/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-flow/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-geo/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-google/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-hreflang/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-image-gen/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-images/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-local/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-maps/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-page/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-plan/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-programmatic/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-schema/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-sitemap/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-sxo/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.
- **`.agents/skills/seo-technical/SKILL.md`**: Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer.

## 4. Agents (`.agents/agents/`)
- **`seo-agentic.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-backlinks.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-cluster.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-content.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-dataforseo.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-drift.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-ecommerce.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-flow.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-geo.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-google.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-image-gen.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-local.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-maps.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-performance.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-schema.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-sitemap.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-sxo.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-technical.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
- **`seo-visual.md`** (MODIFIED): Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools.
