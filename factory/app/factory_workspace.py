"""Tabbed, live-data workspace for the Warder Factory desktop application."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


_JSON_ERROR = "__factory_load_error__"


def _json(path):
    """Read a JSON object and retain failures so GUI panels never invent zeroes."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {_JSON_ERROR: "JSON root is not an object"}
        return value
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError) as exc:
        return {_JSON_ERROR: f"{type(exc).__name__}: {exc}"}


def _load_error(data):
    return data.get(_JSON_ERROR) if isinstance(data, dict) else None


def latest_json(folder: Path, prefix: str):
    files = sorted(Path(folder).glob(prefix + "*.json"), key=lambda p: (p.stat().st_mtime_ns, p.name))
    return files[-1] if files else None


def source_rows(ingest: Path, inbox: Path, source_manifest: Path, chocho_positions: Path | None = None,
                master_snapshot: Path | None = None, state_dir: Path | None = None,
                legacy_state_dir: Path | None = None):
    """Describe source state from persisted checkpoints and actual local files."""
    rows = []
    for key, filename in (("Vhannibal", "vhannibal-state.json"),
                          ("OpenATV 8", "openatv8-state.json"),
                          ("Chocholousek", "chocholousek-state.json")):
        path = Path(state_dir or ingest) / filename
        legacy = Path(legacy_state_dir) / filename if legacy_state_dir is not None else None
        if not path.exists() and legacy is not None and legacy.is_file():
            path = legacy
        state = _json(path)
        if not path.exists():
            status, details = "Ešte nesynchronizované", "Checkpoint zatiaľ neexistuje"
        elif _load_error(state):
            status, details = "CHYBA načítania", _load_error(state)
        else:
            status = str(state.get("status", "Checkpoint uložený"))
            details = ", ".join(f"{k}: {state[k]}" for k in ("version", "imported", "imported_png", "index_sha1") if k in state) or "Checkpoint je dostupný"
        rows.append((key, status, details, str(path)))
    manifest = _json(source_manifest)
    if _load_error(manifest):
        rows.append(("Overené voliteľné zdroje", "CHYBA načítania", _load_error(manifest), str(source_manifest)))
    else:
        rows.append(("Overené voliteľné zdroje", "Nakonfigurované" if manifest.get("sources") else "Nekonfigurované",
                     f"{len(manifest.get('sources', []))} zdrojov v overenom manifeste" if manifest.get("sources") else "Bez manifestu sa žiadne URL nehádajú", str(source_manifest)))
    positions_file = Path(chocho_positions) if chocho_positions else Path(ingest) / "chocholousek-positions.json"
    position_state = _json(positions_file)
    positions = position_state.get("positions", [])
    if _load_error(position_state):
        rows.append(("Chocholousek · vybrané pozície", "CHYBA načítania", _load_error(position_state), str(positions_file)))
    else:
        rows.append(("Chocholousek · vybrané pozície", "Vybrané" if positions else "Čaká na výber",
                     ", ".join(str(value) for value in positions) if positions else "Vyber iba satelitné pozície, ktoré používaš", str(positions_file)))
    snapshot_file = Path(master_snapshot) if master_snapshot else Path(state_dir or ingest) / "master-current-paths.json"
    legacy_snapshot = Path(legacy_state_dir) / "master-current-paths.json" if legacy_state_dir is not None else None
    if not snapshot_file.is_file() and legacy_snapshot is not None and legacy_snapshot.is_file():
        snapshot_file = legacy_snapshot
    snapshot = _json(snapshot_file)
    snapshot_paths = snapshot.get("paths", [])
    if _load_error(snapshot):
        rows.append(("Warder Master snapshot", "CHYBA načítania", _load_error(snapshot), str(snapshot_file)))
    else:
        rows.append(("Warder Master snapshot", "Dostupný" if snapshot_paths else "Zatiaľ nestiahnutý",
                     f"Commit {snapshot.get('commit', 'neznámy')} · {len(snapshot_paths)} schválených ciest" if snapshot_paths else "Predvolené je read-only porovnanie; snapshot vznikne pri spracovaní", str(snapshot_file)))
    local = Path(inbox)
    archives = sum(1 for _ in local.rglob("*.zip")) if local.is_dir() else 0
    pngs = sum(1 for _ in local.rglob("*.png")) if local.is_dir() else 0
    rows.append(("Lokálny inbox", "Dostupný" if local.is_dir() else "Zatiaľ nevytvorený",
                 f"{archives} ZIP · {pngs} PNG", str(local)))
    return rows


def latest_registry_items(reports: Path):
    path = latest_json(reports, "registry-matches-")
    data = _json(path) if path else {}
    if _load_error(data):
        return path, [{_JSON_ERROR: _load_error(data)}]
    return path, data.get("items", []) if isinstance(data.get("items", []), list) else []


def latest_master_registry(reports: Path):
    path = latest_json(reports, "warder-master-index-")
    data = _json(path) if path else {}
    services = data.get("services", {})
    services = services if isinstance(services, dict) else {}
    return path, data, services


def latest_run_stats(reports: Path):
    path = latest_json(reports, "report-")
    data = _json(path) if path else {}
    if _load_error(data):
        return path, {_JSON_ERROR: _load_error(data)}
    stats = data.get("stats")
    if path and not isinstance(stats, dict):
        return path, {_JSON_ERROR: "Report has no valid stats object"}
    return path, stats if isinstance(stats, dict) else {}


def finalization_rows(report_dir: Path, ledger_path: Path, legacy_ledger_path: Path | None = None):
    report_path, stats = latest_run_stats(report_dir)
    if _load_error(stats):
        error = "CHYBA načítania reportu: " + _load_error(stats)
        return [("Posledný report", error), ("NEW kandidáti zapísaní", error),
                ("Trojice už existovali", error), ("Konflikty chránené pred zápisom", error),
                ("Zablokované QA", error), ("Neplatné kandidáty", error),
                ("Ručné lokálne finalizácie", "Samostatný audit rozhodnutí môže byť dostupný")]
    final = stats.get("new_candidate_finalization", {})
    final = final if isinstance(final, dict) else {}
    from review_decisions import load_decisions
    ledger_error = None
    try:
        ledger = load_decisions(legacy_ledger_path, ledger_path)
    except (OSError, ValueError, TypeError) as exc:
        ledger = {}
        ledger_error = f"{type(exc).__name__}: {exc}"
    finalized = [(review_id, row) for review_id, row in ledger.items()
                 if isinstance(row, dict) and row.get("decision") == "FINALIZED_LOCALLY"]
    rows = [("Posledný report", str(report_path or "Zatiaľ bez reportu")),
            ("NEW kandidáti zapísaní", str(final.get("copied", 0))),
            ("Trojice už existovali", str(final.get("already_present", 0))),
            ("Konflikty chránené pred zápisom", str(final.get("conflicts", 0))),
            ("Zablokované QA", str(final.get("qa_blocked", 0))),
            ("Neplatné kandidáty", str(final.get("invalid", 0))),
            ("Ručné lokálne finalizácie", "CHYBA načítania: " + ledger_error if ledger_error else str(len(finalized)))]
    rows.extend((f"Audit {review_id}", str(entry.get("note", ""))) for review_id, entry in sorted(finalized))
    return rows


def latest_review_counts(reports: Path, *fallback_dirs: Path):
    from review_ui import latest_review
    path = latest_review(reports, *fallback_dirs)
    if path is None:
        return None, {"no_report": True}
    data = _json(path)
    if _load_error(data):
        return path, {"error": _load_error(data)}
    lanes = data.get("workstream_counts", {})
    return path, {"total": int(data.get("count", len(data.get("items", [])))), **{
        key: int(lanes.get(key, 0)) for key in ("IDENTITY_VERIFICATION", "ARTWORK_REVIEW", "TECHNICAL_QA")}}


def candidate_status(classification, reason="", has_master=False):
    raw = str(classification).upper()
    evidence = str(reason).casefold()
    if raw == "NEW":
        return "NEW"
    if raw == "IDENTICAL":
        return "EXISTING"
    if raw == "REVIEW":
        if any(word in evidence for word in ("conflict", "duplicate", "collision")):
            return "CONFLICT"
        return "EXISTING" if has_master else "AMBIGUOUS"
    return "AMBIGUOUS"


def parse_chocho_positions(raw: str):
    positions = [value.strip().upper() for value in raw.split(",") if value.strip()]
    if any(not re.fullmatch(r"\d{1,3}\.\d[EW]", value) for value in positions):
        raise ValueError("Use satellite positions such as 13.0E or 5.0W")
    return sorted(set(positions))


class FactoryWorkspace:
    """UI shell whose status panels read the application's real files/reports."""
    MAX_TABLE_ROWS = 500
    def __init__(self, app, root, paths):
        self.app, self.root, self.paths = app, root, paths
        # Preserve the diagnostic data models and background panels, but keep
        # the everyday operator interface on one screen.
        self.notebook = ttk.Notebook(root)
        self.workbench = ttk.Panedwindow(root, orient="horizontal")
        self.workbench.pack(fill="both", expand=True)
        self.operator_left = ttk.Frame(self.workbench)
        self.operator_right = ttk.Frame(self.workbench)
        self.workbench.add(self.operator_left, weight=1)
        self.workbench.add(self.operator_right, weight=1)
        self._build_dashboard()
        self._build_sources()
        self._build_registry()
        self._build_candidates()
        self._build_graphics()
        self._build_qa()
        self._build_review()
        self._build_finalization()
        self._build_settings()
        self._build_diagnostics()
        self._source_refreshing = False
        self.refresh_all()
        self.root.after(15000, self._refresh_timer)

    def _page(self, title):
        if title in ("Dashboard", "Výnimky / schvaľovanie"):
            parent = self.operator_left if title == "Dashboard" else self.operator_right
            frame = ttk.Frame(parent, padding=8)
            frame.pack(fill="both", expand=True)
            return frame
        # Advanced data views remain available to the engine and tests, but
        # are not ten distracting primary tabs in the operator workspace.
        frame = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(frame, text=title)
        return frame

    def _build_dashboard(self):
        page = self._page("Dashboard")
        ttk.Label(page, text="WARDER PICON FACTORY", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(page, text="Lokálne spracovanie; produkčný Master Registry a originály zostávajú chránené").pack(anchor="w", pady=(0, 10))
        self.app.version_label = ttk.Label(page, text="Nainštalovaná verzia: " + self.app.installed_version)
        self.app.version_label.pack(anchor="w")
        self.app.runtime_identity = tk.StringVar(value="Build: načítavam · EXE: zisťujem · dátový koreň: " + str(self.paths["root"]) + " · preflight: čaká")
        ttk.Label(page, textvariable=self.app.runtime_identity, wraplength=1380,
                  justify="left", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 8))
        self.app.production_label = ttk.Label(page, text="Finálne lokálne PNG: zisťujem...")
        self.app.production_label.pack(anchor="w")
        self.app.status = tk.StringVar(value="Pripravené")
        ttk.Label(page, textvariable=self.app.status, font=("Segoe UI", 11)).pack(anchor="w", pady=(8, 0))
        self.app.counts_status = tk.StringVar(value="Fronta: načítavam report")
        ttk.Label(page, textvariable=self.app.counts_status, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.summary = ttk.Label(page, text="Načítavam skutočný stav...")
        self.summary.pack(anchor="w", pady=8)
        cards = ttk.Frame(page); cards.pack(fill="x", pady=(4, 12))
        self.kpi_vars = {name: tk.StringVar(value="Načítavam…") for name in ("workspace", "sources", "queue", "final")}
        labels = (("workspace", "Pracovný priestor"), ("sources", "Zdroje"),
                  ("queue", "Fronta na kontrolu"), ("final", "Finálne lokálne PNG"))
        for column, (key, title) in enumerate(labels):
            card = ttk.LabelFrame(cards, text=title, padding=(14, 10))
            card.grid(row=column // 2, column=column % 2, sticky="nsew", padx=4, pady=2)
            ttk.Label(card, textvariable=self.kpi_vars[key], font=("Segoe UI", 10, "bold"), wraplength=280).pack(anchor="w")
            cards.columnconfigure(column % 2, weight=1, uniform="dashboard-kpi")
        self.kpi_vars["workspace"].set(str(self.paths["root"]))
        self.app.bar = ttk.Progressbar(page, mode="determinate")
        self.app.bar.pack(fill="x", pady=8)
        controls = ttk.Frame(page); controls.pack(fill="x", pady=4)
        first = ttk.Frame(controls); first.pack(fill="x")
        second = ttk.Frame(controls); second.pack(fill="x")
        ttk.Button(first, text="Spustiť spracovanie", command=self.app.start).pack(side="left", padx=2)
        ttk.Button(first, text="Zastaviť bezpečne", command=self.app.request_cancel).pack(side="left", padx=2)
        ttk.Button(first, text="Obnoviť", command=self.refresh_all).pack(side="left", padx=2)
        ttk.Button(second, text="Reporty", command=self.app.open_reports).pack(side="left", padx=2)
        ttk.Button(second, text="Export PNG", command=self.app.export_pending).pack(side="left", padx=2)
        ttk.Button(second, text="GitHub diagnostika", command=self.app.configure_github).pack(side="left", padx=2)
        ttk.Label(page, text=f"Inbox: {self.paths['inbox']} | Výstup: {self.paths['output']}", wraplength=650).pack(anchor="w", pady=4)
        log_frame = ttk.LabelFrame(page, text="Živý priebeh spracovania")
        log_frame.pack(fill="both", expand=True, pady=(5, 0))
        self.app.output = tk.Text(log_frame, wrap="word", font=("Consolas", 9), height=12)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.app.output.yview)
        self.app.output.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.app.output.pack(side="left", fill="both", expand=True)
        self.app.output.insert("end", "Factory pripravená. Čakám na bezpečný preflight.\n")

    def _tree_page(self, title, columns, headings):
        page = self._page(title)
        tree = ttk.Treeview(page, columns=columns, show="headings")
        for column, heading, width in headings:
            tree.heading(column, text=heading); tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(page, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(page, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        tree.pack(side="top", fill="both", expand=True); scroll.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        return page, tree

    def _build_sources(self):
        page, self.source_tree = self._tree_page("Zdroje", ("name", "status", "details", "path"),
            (("name", "Zdroj", 180), ("status", "Stav", 155), ("details", "Checkpoint / obsah", 410), ("path", "Súbor alebo priečinok", 460)))
        ttk.Button(page, text="Obnoviť stav zdrojov", command=self.refresh_sources).pack(anchor="w", pady=5)

    def _build_registry(self):
        page = self._page("Master Registry")
        bar = ttk.Frame(page); bar.pack(fill="x")
        ttk.Label(bar, text="Filtrovať service reference / identitu:").pack(side="left")
        self.registry_query = tk.StringVar(); entry = ttk.Entry(bar, textvariable=self.registry_query); entry.pack(side="left", fill="x", expand=True, padx=6)
        self.registry_query.trace_add("write", lambda *_: self.refresh_registry())
        self.registry_tree = ttk.Treeview(page, columns=("ref", "styles", "locations"), show="headings")
        for col, title, width in (("ref", "Service reference", 250), ("styles", "Štýly v Master Registry", 230), ("locations", "Pozície / provideri / cesty", 700)):
            self.registry_tree.heading(col, text=title); self.registry_tree.column(col, width=width, anchor="w")
        self.registry_tree.pack(fill="both", expand=True, pady=6)
        self.registry_info = ttk.Label(page, text="Read-only pohľad na posledný Warder Master index."); self.registry_info.pack(anchor="w")

    def _build_candidates(self):
        page, self.candidate_tree = self._tree_page("Kandidáti", ("type", "ref", "source", "reason"),
            (("type", "Stav", 150), ("ref", "Service reference", 220), ("source", "Zdroj", 420), ("reason", "Dôvod", 440)))
        ttk.Label(page, text="Kandidáti z posledného skutočného porovnania; táto obrazovka ich sama neschvaľuje.").pack(anchor="w", pady=5)

    def _build_qa(self):
        page, self.qa_tree = self._tree_page("QA", ("check", "value"), (("check", "Kontrola / metrika", 300), ("value", "Výsledok z posledného behu", 500)))
        self.qa_info = ttk.Label(page, text="Čaká sa na report spracovania."); self.qa_info.pack(anchor="w", pady=5)

    def _build_graphics(self):
        page, self.graphics_tree = self._tree_page("Grafický motor", ("metric", "value"),
            (("metric", "Motor / výstup", 320), ("value", "Skutočný stav", 900)))
        ttk.Label(page, text="Engine spracúva PNG do 220 × 132 RGBA; originál zostáva nedotknutý a tri varianty sa vytvárajú v pracovnom úložisku.").pack(anchor="w", pady=4)
        actions = ttk.Frame(page); actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="Spustiť grafický motor", command=self.app.start).pack(side="left", padx=(0, 5))
        ttk.Button(actions, text="Otvoriť pracovné výstupy", command=lambda: self._open_path(self.paths["output"])).pack(side="left", padx=5)
        ttk.Button(actions, text="Obnoviť report motora", command=self.refresh_graphics).pack(side="left", padx=5)
        self.graphics_info = ttk.Label(page, text="Čaká sa na report skutočného behu."); self.graphics_info.pack(anchor="w")

    def _build_finalization(self):
        page, self.finalization_tree = self._tree_page("Finalizácia", ("item", "value"),
            (("item", "Lokálna finalizácia / audit", 350), ("value", "Výsledok", 900)))
        ttk.Label(page, text="Výstup ostáva lokálny. Do finálneho priečinka sa zapisujú iba jednoznačné NEW kandidáty s čistým QA alebo položky schválené cez finálnu QA.").pack(anchor="w", pady=4)
        actions = ttk.Frame(page); actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="Obnoviť finalizácie", command=self.refresh_finalization).pack(side="left", padx=(0, 5))
        ttk.Button(actions, text="Otvoriť finálne PNG", command=lambda: self._open_path(self.paths["final"])).pack(side="left", padx=5)
        self.finalization_info = ttk.Label(page, text="História sa načíta z reportu motora a auditného registra."); self.finalization_info.pack(anchor="w")

    def _build_review(self):
        from review_gallery import ReviewGallery
        self.gallery = ReviewGallery(self._page("Výnimky / schvaľovanie"), self.paths["exceptions"], self.paths["ledger_path"], self.paths["output"], write_enabled=lambda: self.app.workspace_ready, legacy_report_dir=self.paths["reports"], legacy_ledger_path=self.paths["legacy_ledger"])
        # ttk.Notebook owns a frame; gallery fills it.
        self.gallery.pack(fill="both", expand=True)

    def _build_settings(self):
        from workspace_paths import DIRECTORIES
        page, self.settings_tree = self._tree_page("Nastavenia", ("key", "status", "details", "path"),
            (("key", "Kategória", 155), ("status", "Preflight", 135), ("details", "Inventár read-only", 360), ("path", "Pôvodná cesta", 610)))
        controls = ttk.Frame(page); controls.pack(fill="x", pady=5)
        self.path_choice = tk.StringVar(value="root")
        self.category_paths = {name: Path(self.paths["root"]) / name for name, _ in DIRECTORIES}
        self.category_paths["root"] = Path(self.paths["root"])
        ttk.Combobox(controls, textvariable=self.path_choice, state="readonly", values=tuple(self.category_paths), width=22).pack(side="left")
        ttk.Button(controls, text="Otvoriť vybraný priečinok", command=self.open_selected_folder).pack(side="left", padx=6)
        ttk.Button(controls, text="Spustiť read-only preflight", command=self.app.run_preflight).pack(side="left", padx=6)
        ttk.Label(page, text="Jediný povolený koreň je D:\\WARDER-PICON-FACTORY. Zápis sa odomkne až po kontrole všetkých 13 existujúcich kategórií; preflight nič nevytvára ani nemení.", wraplength=1200).pack(anchor="w", pady=8)
        self.preflight_info = ttk.Label(page, text="Preflight ešte neukončený; všetky zápisy sú zablokované.", wraplength=1200)
        self.preflight_info.pack(anchor="w", pady=4)
        positions = _json(self.paths["chocho_positions"]).get("positions", [])
        selection = ttk.LabelFrame(page, text="Chocholousek · aktívne satelitné pozície", padding=8)
        selection.pack(fill="x", pady=8)
        ttk.Label(selection, text="Zadaj iba pozície, ktoré používaš, napr. 13.0E, 19.2E. Prázdny výber znamená, že sa archívy nesťahujú.").pack(anchor="w")
        self.chocho_positions_var = tk.StringVar(value=", ".join(positions))
        ttk.Entry(selection, textvariable=self.chocho_positions_var).pack(fill="x", pady=5)
        ttk.Button(selection, text="Uložiť výber pozícií", command=self.save_chocho_positions).pack(anchor="e")
        self.chocho_selection_status = ttk.Label(selection, text=f"Konfigurácia: {self.paths['chocho_positions']}")
        self.chocho_selection_status.pack(anchor="w")

    def _build_diagnostics(self):
        # The live log already occupies the left half of the single-screen
        # operator view. Never replace its widget with a hidden notebook log.
        self._page("Diagnostika")

    def refresh_sources(self):
        # Counting can walk a large imported tree. Keep all filesystem work
        # off the Tk thread and publish only the finished immutable rows.
        if self._source_refreshing:
            return
        self._source_refreshing = True
        self.app.emit("source_inventory", None)

        def worker():
            try:
                rows = source_rows(self.paths["ingest"], self.paths["inbox"],
                                   self.paths["source_manifest"], self.paths["chocho_positions"],
                                   self.paths["master_paths"], self.paths["state"], self.paths["app_data"])
                self.app.emit("source_inventory_done", rows)
            except Exception as exc:
                self.app.emit("source_inventory_error", type(exc).__name__ + ": " + str(exc)[:240])

        threading.Thread(target=worker, name="factory-source-inventory", daemon=True).start()

    def show_sources(self, rows):
        self._source_refreshing = False
        self.source_tree.delete(*self.source_tree.get_children())
        for row in rows:
            self.source_tree.insert("", "end", values=row)
        if hasattr(self, "kpi_vars"):
            self.kpi_vars["sources"].set(f"{len(rows)} zdrojových stavov · {sum('Dostupný' in row[1] for row in rows)} dostupných")
        self._update_summary()

    def source_inventory_error(self, error):
        self._source_refreshing = False
        self.source_tree.delete(*self.source_tree.get_children())
        self.source_tree.insert("", "end", values=("Lokálny inventár", "Chyba", error, str(self.paths["inbox"])))

    def refresh_registry(self):
        path, registry, services = latest_master_registry(self.paths["reports"])
        candidate_path, items = latest_registry_items(self.paths["reports"])
        query = self.registry_query.get().strip().casefold()
        for tree in (self.registry_tree, self.candidate_tree): tree.delete(*tree.get_children())
        registry_matches = []
        if _load_error(registry) or (items and _load_error(items[0])):
            error = _load_error(registry) or _load_error(items[0])
            self.registry_info.configure(text=f"CHYBA načítania Registry/reportov: {error}")
            return
        for ref, entries in services.items():
            locations = "; ".join(f"{entry.get('position', '?')} / {entry.get('provider', '?')} / {entry.get('style', '?')}" for entry in entries if isinstance(entry, dict))
            styles = ", ".join(sorted({str(entry.get('style', '?')) for entry in entries if isinstance(entry, dict)}))
            if query and query not in " ".join((str(ref), styles, locations)).casefold(): continue
            registry_matches.append((str(ref), styles, locations))
        for row in registry_matches[:self.MAX_TABLE_ROWS]: self.registry_tree.insert("", "end", values=row)
        matches = []
        for item in items:
            ref = str(item.get("service_reference") or item.get("candidate_identity") or "")
            source = str(item.get("source") or item.get("candidate_source") or item.get("source_name") or "")
            classification = str(item.get("classification") or item.get("status") or "UNKNOWN").upper()
            reason = str(item.get("reason") or item.get("classification_reason") or "")
            digest = str(item.get("candidate_sha256") or item.get("sha256") or "")
            if query and query not in " ".join((ref, source, classification, reason, digest)).casefold(): continue
            matches.append((ref, classification, source, digest, reason, bool(item.get("master_locations"))))
        for ref, classification, source, digest, reason, has_master in matches[:self.MAX_TABLE_ROWS]:
            self.candidate_tree.insert("", "end", values=(candidate_status(classification, reason, has_master), ref, source, reason))
        collision_path = latest_json(self.paths["reports"], "identity-collisions-")
        collision_data = _json(collision_path) if collision_path else {}
        for conflict in collision_data.get("collisions", [])[:self.MAX_TABLE_ROWS]:
            ref = str(conflict.get("candidate_service_ref", ""))
            variants = conflict.get("variants", [])
            reason = "Viac rozdielnych grafík pre rovnakú identitu; ručné rozhodnutie je povinné"
            if query and query not in (ref + " CONFLICT " + reason).casefold():
                continue
            self.candidate_tree.insert("", "end", values=("CONFLICT", ref, f"{len(variants)} grafických variantov", reason))
        self.registry_info.configure(text=f"Read-only Master: {path if path else 'index zatiaľ nevznikol'} · {registry.get('service_count', len(services))} služieb / {registry.get('asset_count', 0)} assetov · zobrazených {min(len(registry_matches), self.MAX_TABLE_ROWS)}. Kandidáti: {candidate_path or 'bez porovnania'} · {len(matches)} záznamov")

    def refresh_qa(self):
        self.qa_tree.delete(*self.qa_tree.get_children())
        path = latest_json(self.paths["reports"], "report-")
        data = _json(path) if path else {}
        stats = data.get("stats", {})
        if _load_error(data):
            self.qa_info.configure(text="CHYBA načítania QA reportu: " + _load_error(data))
            return
        if not stats:
            self.qa_info.configure(text="QA report zatiaľ nie je dostupný; po prvom behu sa načítajú jeho skutočné výsledky.")
            return
        for key, value in sorted(stats.items()):
            self.qa_tree.insert("", "end", values=(str(key), json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)))
        self.qa_info.configure(text=f"QA report: {path}")

    def refresh_graphics(self):
        self.graphics_tree.delete(*self.graphics_tree.get_children())
        path, stats = latest_run_stats(self.paths["reports"])
        if _load_error(stats):
            rows = [("Posledný engine report", "CHYBA načítania: " + _load_error(stats)),
                    ("Stav spracovania", "Metriky nie sú dostupné")]
        else:
            rows = [("Posledný engine report", str(path or "Zatiaľ bez reportu")),
                ("Stav spracovania", "Report z reálneho behu je dostupný" if path else "Zatiaľ nespustený"),
                ("Rozmer", "220 × 132 RGBA PNG"),
                ("Varianty", "transparent · black · white"),
                ("Výstup", str(self.paths["output"]))]
            rows.extend((str(key), json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
                        for key, value in sorted(stats.items()))
        for key, value in rows[:self.MAX_TABLE_ROWS]: self.graphics_tree.insert("", "end", values=(key, value))
        self.graphics_info.configure(text=f"Report motora: {path or 'zatiaľ nevznikol'} · metriky {len(rows)} · renderer {'spustený v poslednom behu' if path else 'ešte nebol spustený'}")

    def refresh_finalization(self):
        self.finalization_tree.delete(*self.finalization_tree.get_children())
        rows = finalization_rows(self.paths["reports"], self.paths["ledger_path"], self.paths["legacy_ledger"])
        for key, value in rows[:self.MAX_TABLE_ROWS]: self.finalization_tree.insert("", "end", values=(key, value))
        self.finalization_info.configure(text=f"Finálne úložisko: {self.paths['final']} · auditné rozhodnutia: {self.paths['ledger_path']}")

    def _open_path(self, path):
        path = Path(path)
        if not path.exists():
            path = path.parent
        if not path.is_dir():
            messagebox.showinfo("Priečinok zatiaľ neexistuje", "Aplikácia nevytvorila pracovné priečinky pri otvorení. Spusť spracovanie v dostupnom pracovnom koreňi.", parent=self.root)
            return
        if os.name == "nt": os.startfile(str(path))
        elif sys_platform() == "darwin": subprocess.Popen(["open", str(path)])
        else: subprocess.Popen(["xdg-open", str(path)])

    def refresh_all(self):
        self.app._refresh_production_counts()
        self.refresh_sources(); self.refresh_registry(); self.refresh_graphics(); self.refresh_qa(); self.gallery.reload(); self.refresh_finalization()
        _, counts = latest_review_counts(self.paths["exceptions"], self.paths["reports"])
        if "error" in counts:
            message = "CHYBA načítania fronty: " + counts["error"]
            self.app.counts_status.set(message)
            self._update_summary(message)
        elif counts.get("no_report"):
            self.app.counts_status.set("Fronta: zatiaľ bez uloženého reportu")
            self._update_summary("bez uloženého reportu")
        else:
            self.app.counts_status.set(f"Fronta: {counts['total']} · identita {counts['IDENTITY_VERIFICATION']} · grafika {counts['ARTWORK_REVIEW']} · technické QA {counts['TECHNICAL_QA']}")
            self._update_summary(counts["total"])

    def _update_summary(self, pending=None):
        if pending is None:
            _, counts = latest_review_counts(self.paths["exceptions"], self.paths["reports"])
            pending = ("CHYBA načítania: " + counts["error"] if "error" in counts else
                       "bez uloženého reportu" if counts.get("no_report") else counts["total"])
        self.summary.configure(text=f"Zdrojov/checkpointov: {len(self.source_tree.get_children())} · Registry kandidátov: {len(self.registry_tree.get_children())} · Výnimiek na ručné posúdenie: {pending}")
        if hasattr(self, "kpi_vars"):
            self.kpi_vars["queue"].set((f"{pending:,} čakajúcich položiek".replace(",", " ")
                                        if isinstance(pending, int) else str(pending)))

    def save_chocho_positions(self):
        from source_registry import atomic_json
        if not self.app.workspace_ready:
            messagebox.showwarning("Preflight required", "Nastavenie sa nezapíše, kým read-only preflight neprejde.", parent=self.root)
            return
        raw = self.chocho_positions_var.get().strip()
        try:
            positions = parse_chocho_positions(raw)
        except ValueError:
            self.chocho_selection_status.configure(text="Neplatný formát. Použi napr. 13.0E alebo 5.0W.")
            return
        atomic_json(self.paths["chocho_positions"], {"schema": 1, "positions": positions})
        self.chocho_selection_status.configure(text=f"Uložené pozície: {', '.join(positions) if positions else 'žiadne'} · načíta sa pri ďalšom spustení synchronizácie")
        self.refresh_sources()

    def open_selected_folder(self):
        path = Path(self.category_paths[self.path_choice.get()])
        if not path.exists():
            path = path.parent
        if not path.is_dir():
            messagebox.showinfo("Priečinok zatiaľ neexistuje", "Priečinok sa nevytvoril, aby sa zachovala štruktúra existujúceho projektu.", parent=self.root)
            return
        if os.name == "nt": os.startfile(str(path))
        elif sys_platform() == "darwin": subprocess.Popen(["open", str(path)])
        else: subprocess.Popen(["xdg-open", str(path)])

    def show_preflight(self, result):
        from workspace_paths import DIRECTORIES
        self.settings_tree.delete(*self.settings_tree.get_children())
        inventory = result.inventory
        for name, purpose in DIRECTORIES:
            stats = inventory.get(name, {})
            if name in result.missing:
                state, details = "CHÝBA", "Zápis zablokovaný"
            elif result.unreadable:
                state, details = "CHYBA ČÍTANIA", purpose
            else:
                state = "READ-ONLY OK" if result.ok else "PREVERENÉ"
                details = f"{stats.get('files', 0)} súborov · {stats.get('png', 0)} PNG · {stats.get('archives', 0)} archívov · {stats.get('bytes', 0)} B"
            self.settings_tree.insert("", "end", values=(name, state, details, str(Path(result.root) / name)))
        self.preflight_info.configure(text=("ÚSPEŠNÝ PREFLIGHT · 13/13 kategórií · žiadne dáta nemenili" if result.ok else
            "ZÁPIS ZABLOKOVANÝ · " + " | ".join(result.findings)))
        self.kpi_vars["workspace"].set("13/13 kategórií overených" if result.ok else
                                       f"Zápis blokovaný · {len(result.missing)} kategórií chýba")

    def update_runtime_identity(self, result=None, error=None):
        if error:
            status = "CHYBA · zápis zablokovaný · " + error
        elif result is None:
            status = "preflight sa vykonáva · zápisy zablokované"
        else:
            status = "OK · zápisy povolené" if result.ok else "BLOKOVANÝ · zápisy zakázané"
        self.app.runtime_identity.set(
            f"Build commit: {self.app.build_commit} · Spustený EXE: {self.app.executable_path} · "
            f"Dátový koreň: {result.root if result is not None else self.paths['root']} · Preflight: {status}"
        )

    def _refresh_timer(self):
        if self.root.winfo_exists():
            if not self.app.running and not self.app.export_running:
                self.refresh_sources(); self.refresh_registry(); self.refresh_graphics(); self.refresh_qa(); self.gallery.reload(); self.refresh_finalization()
                self._update_summary()
            self.root.after(15000, self._refresh_timer)


def sys_platform():
    import sys
    return sys.platform
