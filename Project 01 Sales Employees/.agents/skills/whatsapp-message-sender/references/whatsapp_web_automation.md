# WhatsApp Web Automation Reference & Selector Guide

This document specifies the Playwright selectors, UI state machines, popups, and timing rules for automating WhatsApp Web (`https://web.whatsapp.com/`).

---

## 1. Core DOM Selectors

| UI Element | Selector | Purpose / Notes |
| :--- | :--- | :--- |
| **New Chat Button** | `page.getByRole('button', { name: 'New chat' })` | Opens chat drawer if dialer is closed. |
| **Phone Number Button** | `page.getByRole('button', { name: 'Phone number' })` | Selects direct phone number input. |
| **Dialer Input** | `page.getByTestId('dialer-pad-drawer').getByRole('textbox')` | Direct dialer pad text field for phone numbers. |
| **Contact Cell Result** | `page.getByTestId('cell-frame-container')` | Shows the resolved contact if number exists on WhatsApp. |
| **Compose Box** | `page.getByTestId('conversation-compose-box-input')` | Active chat message input box. |
| **VoIP Popup Close** | `page.getByTestId('voip-calling-nux-close')` | Dismisses the "Voice calling is here" onboarding banner. |
| **Invalid Number Popup "OK"** | `page.getByRole('button', { name: 'OK' })` | Dismisses the "Phone number shared via url is invalid" modal. |
| **Drawer Back Button** | `page.getByRole('button', { name: 'Back' })` | Returns from dialer drawer to default chat list. |

---

## 2. Pacing, Anti-Ban & Human-like Delays

To maintain high WhatsApp account health and avoid temporary rate limits:
- **Phone Lookup Wait:** 2000–2500 ms after entering the phone number in dialer.
- **Message Input Delay:** 500 ms between filling the compose box and pressing Enter.
- **Delivery Confirmation Wait:** 3500–4500 ms after pressing Enter to verify the message is sent.
- **Inter-Send Pacing:** Minimum **3000–6000 ms** delay before proceeding to the next lead in the batch.

---

## 3. UI State Transitions & Recovery

```
[Start Lead]
      │
      ▼
Check VoIP Popup ──(Visible)──> Dismiss
      │
      ▼
Check Dialer Input ──(Not Visible)──> Click 'New chat' / 'Phone number'
      │
      ▼
Fill Dialer with clean E.164 phone
      │
      ▼
Wait 2500ms for Contact Cell
      │
  ┌───┴───────────────────────────┐
  ▼                               ▼
[Contact Found]             [Contact Not Found]
  │                               │
  ├─> Click Cell                  ├─> Click 'OK' on invalid modal
  ├─> Wait for Compose Box        ├─> Click 'Back' button
  ├─> Fill Personalized Message   └─> Record Status: 'Not Found'
  ├─> Press 'Enter'
  ├─> Wait 4000ms (delivery)
  ├─> Record Status: 'Sent'
  └─> Wait 5000ms (pacing)
```

---

## 4. Error Recovery Pattern

If an unhandled exception or selector timeout occurs during processing of any lead:
1. Catch the exception and record `{ status: "failed", error: String(err) }`.
2. Attempt to reset UI state by clicking `page.getByRole('button', { name: 'Back' })`.
3. Clear dialer if still open before continuing to the next lead in the batch.
