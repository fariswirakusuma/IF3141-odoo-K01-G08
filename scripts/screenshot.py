#!/usr/bin/env python3
"""Ambil tangkapan layar seluruh layar modul pilar_po dengan Playwright."""

import argparse
import os
import xmlrpc.client

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


ACTIONS = {
    "dashboard": "action_pilar_po_dashboard",
    "queue": "action_pilar_po_queue",
    "approval": "action_pilar_po_approval",
    "returned": "action_pilar_po_returned",
    "approved": "action_pilar_po_approved",
    "purchasing": "action_pilar_po_purchasing",
    "finance": "action_pilar_po_finance",
    "driver": "action_pilar_po_driver",
    "cancelled": "action_pilar_po_cancelled",
    "overdue": "action_pilar_po_overdue",
    "history": "action_pilar_po_history",
    "config": "action_pilar_po_config",
}


def resolve_ids(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    action_ids = {}
    for key, xmlid in ACTIONS.items():
        rows = models.execute_kw(
            db, uid, password, "ir.model.data", "search_read",
            [[("module", "=", "pilar_po"), ("name", "=", xmlid)]],
            {"fields": ["res_id"], "limit": 1},
        )
        if not rows:
            raise SystemExit(f"Action tidak ditemukan: {xmlid}")
        action_ids[key] = rows[0]["res_id"]

    record_ids = {}
    for key, state in (
        ("inspection", "dalam_pemeriksaan"),
        ("returned", "dikembalikan"),
        ("decision", "menunggu_keputusan"),
    ):
        rows = models.execute_kw(
            db, uid, password, "pilar.po", "search_read",
            [[("state", "=", state)]], {"fields": ["id"], "limit": 1, "order": "id"},
        )
        if rows:
            record_ids[key] = rows[0]["id"]

    return action_ids, record_ids


def wait_view(page):
    page.wait_for_selector(
        ".o_control_panel, .o_form_view, .o_kanban_view, .o_list_view, "
        ".o_calendar_view, .o_pivot_view",
        timeout=90000,
    )
    page.wait_for_timeout(1800)


def shot(page, base_url, out, name, action_id=None, record_id=None, tab=None,
         wide=False, height=1000, expand_groups=False):
    if action_id is not None:
        suffix = f"/web#action={action_id}"
        if record_id:
            suffix += f"&id={record_id}&view_type=form"
        page.goto(base_url + suffix, wait_until="domcontentloaded")
    wait_view(page)
    if tab:
        try:
            page.locator(f".nav-link:has-text('{tab}')").first.click()
            page.wait_for_timeout(1200)
        except PlaywrightTimeout:
            print(f"  ! tab '{tab}' tidak ditemukan pada {name}")
    if expand_groups:
        headers = page.locator(".o_group_header")
        for index in range(headers.count()):
            headers.nth(index).click()
            page.wait_for_timeout(400)
    page.evaluate(
        "() => { const c = document.querySelector('.o_content'); "
        "if (c) c.scrollTop = 0; window.scrollTo(0, 0); }"
    )
    page.mouse.move(5, 5)
    base_width = page.viewport_size["width"]
    if wide:
        page.set_viewport_size({"width": 2500, "height": height})
    elif height != 1000:
        page.set_viewport_size({"width": base_width, "height": height})
    page.wait_for_timeout(900)
    path = os.path.join(out, name)
    page.screenshot(path=path, full_page=False)
    if wide or height != 1000:
        page.set_viewport_size({"width": base_width, "height": 1000})
    print(f"  {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--db", default="odoo_app")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--out", default="docs/screenshots")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    actions, records = resolve_ids(args.url, args.db, args.user, args.password)

    po_inspection = records.get("inspection")
    po_returned = records.get("returned")
    po_decision = records.get("decision")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=1,
            locale="id-ID",
        )
        page = context.new_page()
        page.set_default_timeout(90000)

        page.goto(f"{args.url}/web/login", wait_until="domcontentloaded")
        page.fill("input[name='login']", args.user)
        page.fill("input[name='password']", args.password)
        page.click("button[type='submit']")
        page.wait_for_url(lambda current: "/web/login" not in current, timeout=90000)
        page.wait_for_timeout(2000)

        shots = [
            {"name": "01-dashboard-po.png", "action": "dashboard",
             "wide": True, "height": 1200},
            {"name": "02-antrean-po-staff-sales.png", "action": "queue"},
            {"name": "03-form-po-split-screen.png", "action": "dashboard",
             "record": po_inspection, "height": 1500},
            {"name": "04-validasi-po-bermasalah.png", "action": "returned",
             "record": po_returned, "tab": "Pemeriksaan & Validasi",
             "height": 1500},
            {"name": "05-persetujuan-po.png", "action": "approval"},
            {"name": "06-form-keputusan-persetujuan.png", "action": "approval",
             "record": po_decision, "height": 1500},
            {"name": "07-po-dikembalikan.png", "action": "returned"},
            {"name": "08-riwayat-audit.png", "action": "history"},
            {"name": "09-ringkasan-po-tertunda.png", "action": "overdue",
             "height": 1200, "expand": True},
            {"name": "10-po-disahkan.png", "action": "approved"},
            {"name": "11-kebutuhan-barang-purchasing.png", "action": "purchasing"},
            {"name": "12-dasar-tagihan-keuangan.png", "action": "finance"},
            {"name": "13-jadwal-pengiriman.png", "action": "driver"},
            {"name": "14-po-dibatalkan.png", "action": "cancelled"},
            {"name": "15-pengaturan-validasi.png", "action": "config"},
        ]

        print(f"Mengambil {len(shots)} tangkapan layar...")
        for item in shots:
            shot(
                page, args.url, args.out, item["name"],
                actions[item["action"]], item.get("record"), item.get("tab"),
                item.get("wide", False), item.get("height", args.height),
                item.get("expand", False),
            )

        browser.close()

    print(f"Selesai. Hasil di {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
