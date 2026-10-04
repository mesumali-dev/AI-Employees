#!/usr/bin/env python3
"""
whatsapp_batch_sender.py — Prepares optimized sequential batch queues for
Playwright MCP WhatsApp Web dispatching, handles pacing, and triggers single-pass bulk CSV updates.

Usage:
  # Generate browser runner script for the pending drafts:
  python whatsapp_batch_sender.py --queue whatsapp_queue.json --csv outputs/leads/2026/leads-sep.csv

  # Apply execution results in a single atomic CSV update:
  python whatsapp_batch_sender.py --apply-results results.json --csv outputs/leads/2026/leads-sep.csv

  # Dry-run inspection:
  python whatsapp_batch_sender.py --queue whatsapp_queue.json --dry-run
"""

import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BULK_UPDATER = os.path.join(SCRIPT_DIR, "bulk_csv_updater.py")


def load_queue(queue_path):
    if not os.path.exists(queue_path):
        print(f"ERROR: Queue file not found: {queue_path}")
        sys.exit(1)
    with open(queue_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_batch_js(items, output_js_path, delay_sec=5):
    """Generates the Playwright JavaScript code for sequential batch execution."""
    json_payload = json.dumps(items, indent=2)
    pacing_ms = int(delay_sec * 1000)

    js_code = f"""// Auto-generated WhatsApp Web Batch Dispatcher
async (page) => {{
  const wait = (ms) => page.waitForTimeout(ms);
  const batch = {json_payload};
  const results = [];

  for (const item of batch) {{
    const startTime = new Date().toISOString();
    try {{
      // 0. Dismiss any VoIP calling popup if present
      try {{
        const dialogClose = page.getByRole('dialog').getByRole('button', {{ name: 'Close' }});
        if (await dialogClose.isVisible({{ timeout: 500 }})) {{
          await dialogClose.click({{ timeout: 500 }});
          await wait(300);
        }}
      }} catch (e) {{}}

      // 1. Ensure phone number input dialer is active
      const dialerDrawer = page.getByTestId('dialer-pad-drawer');
      const newChatDrawer = page.getByTestId('new-chat-drawer');
      let dialer = dialerDrawer.getByRole('textbox');
      let dialerVisible = await dialer.isVisible({{ timeout: 600 }}).catch(() => false);

      if (!dialerVisible) {{
        const phoneBtn = page.getByRole('button', {{ name: 'Phone number' }});
        let phoneBtnVisible = await phoneBtn.isVisible({{ timeout: 600 }}).catch(() => false);

        if (!phoneBtnVisible) {{
          const newChatBtn = page.getByRole('button', {{ name: 'New chat' }});
          await newChatBtn.click({{ timeout: 1500 }}).catch(() => {{}});
          await wait(600);
        }}

        await page.getByRole('button', {{ name: 'Phone number' }}).click({{ timeout: 1500 }}).catch(() => {{}});
        await wait(600);
      }}

      // 2. Clear and type international phone number
      dialer = dialerDrawer.getByRole('textbox');
      await dialer.click();
      await page.keyboard.press('Control+A');
      await page.keyboard.press('Backspace');
      await wait(300);

      const targetPhone = (item.clean_phone && item.clean_phone.startsWith('+')) 
        ? item.clean_phone 
        : ('+' + (item.clean_phone || item.phone));

      await page.keyboard.type(targetPhone, {{ delay: 30 }});
      // Wait for WhatsApp lookup query
      await wait(2000);

      // 3. Check if contact exists on WhatsApp
      const cells = dialerDrawer.getByTestId('cell-frame-container');
      const cellCount = await cells.count();

      if (cellCount > 0) {{
        // Open conversation
        await cells.first().click({{ timeout: 1500 }});
        await wait(1000);

        // Fill and send message via insertText to preserve multiline structure
        const composeBox = page.getByTestId('conversation-compose-box-input');
        await composeBox.waitFor({{ state: 'visible', timeout: 8000 }});
        await composeBox.click();
        await wait(250);

        await page.keyboard.insertText(item.message);
        await wait(600);
        await page.keyboard.press('Enter');
        await wait(2500); // Delivery checkmark wait

        results.push({{
          row: item.row,
          company: item.company,
          phone: item.phone,
          status: 'sent',
          timestamp: startTime
        }});

        // Anti-ban pacing delay (3-6s)
        await wait({pacing_ms});
      }} else {{
        // Contact not found on WhatsApp
        try {{
          const okBtn = page.getByRole('button', {{ name: 'OK' }});
          if (await okBtn.isVisible({{ timeout: 400 }}).catch(() => false)) {{
            await okBtn.click();
            await wait(200);
          }}
        }} catch (e) {{}}

        const dialerBack = dialerDrawer.getByRole('button', {{ name: 'Back' }});
        if (await dialerBack.isVisible({{ timeout: 800 }}).catch(() => false)) {{
          await dialerBack.click();
          await wait(300);
        }}
        const newChatBack = newChatDrawer.getByRole('button', {{ name: 'Back' }});
        if (await newChatBack.isVisible({{ timeout: 800 }}).catch(() => false)) {{
          await newChatBack.click();
          await wait(300);
        }}
        results.push({{
          row: item.row,
          company: item.company,
          phone: item.phone,
          status: 'not_on_whatsapp',
          timestamp: startTime
        }});
        await wait(500);
      }}
    }} catch (err) {{
      results.push({{
        row: item.row,
        company: item.company,
        phone: item.phone,
        status: 'failed',
        error: String(err),
        timestamp: startTime
      }});
      // UI recovery: try to back out to clean state
      try {{
        const okBtn = page.getByRole('button', {{ name: 'OK' }});
        if (await okBtn.isVisible({{ timeout: 400 }}).catch(() => false)) await okBtn.click();
      }} catch (e) {{}}
      try {{
        const dialerBack = page.getByTestId('dialer-pad-drawer').getByRole('button', {{ name: 'Back' }});
        if (await dialerBack.isVisible({{ timeout: 600 }}).catch(() => false)) await dialerBack.click();
      }} catch (e) {{}}
      try {{
        const newChatBack = page.getByTestId('new-chat-drawer').getByRole('button', {{ name: 'Back' }});
        if (await newChatBack.isVisible({{ timeout: 600 }}).catch(() => false)) await newChatBack.click();
      }} catch (e) {{}}
      await wait(1000);
    }}
  }}

  return results;
}}
"""
    with open(output_js_path, "w", encoding="utf-8") as f:
        f.write(js_code)
    return js_code


def find_latest_csv(base_dir="outputs/leads"):
    import glob
    pattern = os.path.join(base_dir, "**", "leads-*.csv")
    files = glob.glob(pattern, recursive=True)
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    return "outputs/leads/2026/leads-oct.csv"


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Batch Dispatcher & Bulk Results Processor")
    parser.add_argument("--queue", default="whatsapp_queue.json", help="Path to queue file")
    parser.add_argument("--csv", default=find_latest_csv(), help="Path to leads CSV database (default: latest active CSV)")
    parser.add_argument("--delay", type=float, default=3.5, help="Pacing delay in seconds between sends (default: 3.5)")
    parser.add_argument("--batch-size", type=int, default=25, help="Maximum number of items in generated batch")
    parser.add_argument("--output-js", default="whatsapp_batch_runner.js", help="Path to output Playwright JS script")
    parser.add_argument("--apply-results", help="JSON file containing execution results to apply in bulk")
    parser.add_argument("--dry-run", action="store_true", help="Preview items without generating batch runner")

    args = parser.parse_args()

    if args.apply_results:
        print(f"Applying execution results to {args.csv} via single-pass bulk updater...")
        subprocess.run([
            sys.executable, BULK_UPDATER,
            "--results", args.apply_results,
            "--csv", args.csv
        ], check=True)
        return

    queue = load_queue(args.queue)

    # Filter items that are in Draft status
    draft_items = [
        item for item in queue
        if item.get("status", "").lower() in ("draft", "")
    ]

    if not draft_items:
        # Fallback to entire queue if status not tagged
        draft_items = queue

    print(f"Loaded {len(queue)} total queue items ({len(draft_items)} pending drafts).")

    if args.dry_run:
        print("\n=== DRY RUN PREVIEW ===")
        for idx, item in enumerate(draft_items[:args.batch_size], 1):
            print(f"[{idx}] Row {item.get('row')}: {item.get('company')} ({item.get('clean_phone') or item.get('phone')})")
        print(f"\nDry run complete. Found {len(draft_items)} drafts eligible for sending.")
        return

    batch_to_run = draft_items[:args.batch_size]
    output_path = os.path.abspath(args.output_js)
    build_batch_js(batch_to_run, output_path, delay_sec=args.delay)

    print(f"\n[OK] Generated batch runner ({len(batch_to_run)} items) at: {output_path}")
    print("\nNext Execution Steps:")
    print("  1. In Playwright MCP, execute the runner code in WhatsApp Web using `browser_run_code_unsafe`.")
    print(f"  2. Save returned results array to a JSON file (e.g. `batch_results.json`).")
    print(f"  3. Run single atomic bulk CSV update:")
    print(f"     python whatsapp_batch_sender.py --apply-results batch_results.json --csv \"{args.csv}\"")


if __name__ == "__main__":
    main()
