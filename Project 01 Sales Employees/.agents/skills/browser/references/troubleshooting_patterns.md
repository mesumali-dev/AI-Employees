# Troubleshooting Patterns

Common blockers when automating a real site with `scripts/browser.py`,
and how to work through them without giving up too early or looping
forever. To re-inspect a page, use a compact reader — `info` (url/title),
`text`, `buttons`, or `inputs` — rather than dumping `html`.

## Cookie / consent banners
Almost always the first thing blocking interaction on a fresh page load
in the EU/UK or on sites with strict consent tooling. Look for
buttons/links labeled "Accept," "Accept all," "I agree," "Got it," or an
X/close icon on a banner overlay. Dismiss before doing anything else on
the page — a banner can intercept clicks meant for elements underneath it.

## Popups / modals
Newsletter signup modals, app-download interstitials, and "sign in to
continue" overlays commonly appear a second or two after page load —
re-inspect the page after a short wait even if the initial read
looked clean. Close via the visible X/close control; avoid clicking
through a modal's own CTA unless that CTA is actually the task.

## Element not found after a click
- The click may have triggered navigation or an async content swap —
  re-run `info`/`text`/`buttons` before concluding the element is missing.
- Label text may differ from what was assumed (e.g. "Sign in" vs.
  "Log in" vs. "Login") — `buttons`/`inputs` show what's actually
  rendered plus a usable `selector`.
- The element might be inside an iframe — the readers/`eval` only see
  the top-level document by default; if a clearly-visible-looking
  control doesn't respond, check for iframes.
- Site may have lazy-loaded content below the fold — `scroll down` and
  re-check before assuming something isn't there.

## Forms that reject submission
- Re-read validation messages that appeared after a failed submit rather
  than resubmitting blindly — field-level errors usually explain exactly
  what's wrong (format, required field, mismatch).
- Some forms need a field blurred (click elsewhere) before validation
  clears, not just filled.

## Slow-loading pages / SPAs
Client-rendered pages often finish the network request before the DOM
actually updates. Prefer `wait-for-selector`/`wait-for-text` for the
specific expected element over a fixed delay; use `wait-idle` before
treating a mostly-blank page as final.

## Session / login walls appearing mid-task
If a task that started logged-in suddenly hits a login screen, the
session likely expired or a step navigated somewhere requiring re-auth.
Don't attempt to log back in with guessed or stored credentials unless
the user explicitly provided them for this task — stop and ask.

## When to actually stop and report failure
After trying the relevant alternatives above (re-inspect, alternate
selector, dismiss overlays, wait longer) a handful of times without
progress, stop. Report exactly what was attempted and what's currently
blocking, so the user can decide whether to intervene manually (e.g. by
solving a CAPTCHA themselves) rather than continuing to retry
indefinitely.