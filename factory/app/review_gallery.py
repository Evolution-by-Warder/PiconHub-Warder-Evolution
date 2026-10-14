"""Embedded, read-only evidence gallery. Decisions never modify PNG or publish."""
import hashlib
import re
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from review_ui import latest_review
from review_queue import load_review_queue
from review_decision_groups import build_decision_groups
from final_qa_bridge import prepare_finalization, FinalizationNotReady


def format_git_sync_error(value):
    """Show the actual safe failure reason without leaking credentials."""
    text = re.sub(r"[\r\n\t]+", " ", str(value or "Unknown GitHub error")).strip()
    text = re.sub(r"(?i)(authorization|bearer|token|password)(\s*[:=]\s*)[^ ,;]+",
                  r"\1\2[redacted]", text)
    return text[:180] or "Unknown GitHub error"


def variant_paths(output_dir, item):
    """Resolve generated derivatives by digest; transparent is reference only."""
    digest = item.get('sha256')
    if not digest:
        digests = evidence_digests(item)
        digest = digests[0] if digests else ''
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()):
        return {}
    digest = digest.lower()
    base = Path(output_dir) / digest[:2] / digest
    return {name: base / (name + '.png') for name in ('transparent', 'black', 'white')}


def evidence_digests(item):
    evidence = []
    for field in ('source_evidence', 'variants'):
        entries = item.get(field)
        if isinstance(entries, (list, tuple)):
            evidence.extend(entries)
    values = [item.get('sha256')] + [entry.get('sha256') for entry in evidence if isinstance(entry, dict)]
    return sorted({value.lower() for value in values if isinstance(value, str) and len(value) == 64
                   and all(c in '0123456789abcdef' for c in value.lower())})


def matches_evidence_sha(path, digest):
    """Never display a source PNG as evidence for a different digest."""
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()):
        return False
    try:
        h = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest() == digest.lower()
    except (OSError, ValueError, TypeError):
        return False


def source_candidates(item, digest):
    """Enumerate original source candidates associated with an exact digest."""
    values = []
    evidence = []
    for field in ('source_evidence', 'variants'):
        entries = item.get(field)
        if isinstance(entries, (list, tuple)):
            evidence.extend(entries)
    for entry in evidence:
        if isinstance(entry, dict) and str(entry.get('sha256', '')).lower() == str(digest).lower():
            values.extend([entry.get('source'), entry.get('path')])
            sources = entry.get('sources')
            if isinstance(sources, (list, tuple)):
                values.extend(x for x in sources if isinstance(x, str))
    if str(item.get('sha256', '')).lower() == str(digest).lower():
        values.append(item.get('original'))
    return [value for value in values if isinstance(value, str)]


def pending_items(items, ledger_path, legacy_ledger_path=None):
    """Drop only evidence-identical, terminal decisions from the visible queue."""
    visible = [item for item in items if item.get('decision', 'PENDING') == 'PENDING']
    ledger_path = Path(ledger_path)
    try:
        from review_decisions import evidence_hash, load_decisions
        decisions = load_decisions(legacy_ledger_path, ledger_path)
        return [item for item in visible if not (
            item['review_id'] in decisions and
            decisions[item['review_id']].get('evidence_hash') == evidence_hash(item) and
            decisions[item['review_id']].get('decision') in
            ('APPROVED_FOR_REVIEW', 'REJECTED', 'FINALIZED_LOCALLY'))]
    except (ValueError, OSError, KeyError, TypeError):
        return visible


class ReviewGallery(ttk.Frame):
    """Ten review entries per page, scrollable in the main window."""
    def __init__(self, parent, report_dir, ledger_path, output_dir, write_enabled=None,
                 legacy_report_dir=None, legacy_ledger_path=None, master_root=None,
                 git_decision_loader=None, git_decision_writer=None, pending_git_path=None):
        super().__init__(parent)
        self.report_dir = Path(report_dir)
        self.legacy_report_dir = Path(legacy_report_dir) if legacy_report_dir is not None else None
        self.ledger_path = Path(ledger_path)
        self.legacy_ledger_path = Path(legacy_ledger_path) if legacy_ledger_path is not None else None
        self.output_dir = Path(output_dir)
        self.master_root = Path(master_root) if master_root else None
        self.write_enabled = write_enabled or (lambda: True)
        self.git_decision_loader = git_decision_loader
        self.git_decision_writer = git_decision_writer
        self.pending_git_path = Path(pending_git_path) if pending_git_path else None
        self.git_decision_events = []
        self.git_registry = None
        self.git_commit = None
        self.git_sync_ready = False
        self._git_syncing = False
        self._git_sync_generation = 0
        self._git_refresh_pending = False
        self._master_refresh_running = False
        self.selected_scopes = {}
        self.items = []
        self.page = 0
        toolbar = ttk.Frame(self); toolbar.pack(fill='x', pady=3)
        ttk.Label(toolbar, text='Schvaľovanie · 10 rozhodovacích skupín / dávka', font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.git_status = ttk.Label(toolbar, text='Git Master: synchronizujem…')
        self.git_status.pack(side='left', padx=10)
        self.batch_decision = tk.StringVar(value='APPROVED_FOR_REVIEW')
        ttk.Combobox(toolbar, textvariable=self.batch_decision, state='readonly', width=23,
                     values=('APPROVED_FOR_REVIEW', 'REJECTED', 'DEFERRED', 'IDENTITY_AMBIGUOUS', 'IDENTITY_CONFLICT')).pack(side='right', padx=3)
        ttk.Button(toolbar, text='Uložiť vybrané do Gitu', command=self.submit_selected_batch).pack(side='right', padx=3)
        ttk.Button(toolbar, text='Obnoviť', command=self.reload).pack(side='right', padx=3)
        ttk.Button(toolbar, text='Retry PENDING', command=self.retry_pending_batches).pack(side='right', padx=3)
        nav = ttk.Frame(self); nav.pack(fill='x')
        self.lane = tk.StringVar(value='ARTWORK_REVIEW')
        filter_box = ttk.Combobox(nav, textvariable=self.lane, state='readonly', width=21,
                                  values=('ARTWORK_REVIEW', 'IDENTITY_VERIFICATION', 'TECHNICAL_QA', 'ALL'))
        filter_box.pack(side='left'); filter_box.bind('<<ComboboxSelected>>', lambda _: self.reset_page())
        ttk.Button(nav, text='◀', width=3, command=lambda: self.turn(-1)).pack(side='left', padx=3)
        ttk.Button(nav, text='▶', width=3, command=lambda: self.turn(1)).pack(side='left')
        ttk.Button(nav, text='Prepočítať MASTER-first bez renderu',
                   command=self.refresh_master_first).pack(side='left', padx=8)
        self.refresh_status = ttk.Label(self, text='', anchor='w', wraplength=1350)
        self.refresh_status.pack(fill='x', padx=6, pady=(2, 4))
        self.counter = ttk.Label(nav, text=''); self.counter.pack(side='left', padx=5)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y'); self.canvas.pack(side='left', fill='both', expand=True)
        self.content = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor='nw')
        self.content.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.reload()

    def reload(self):
        try:
            path = latest_review(self.report_dir, *([self.legacy_report_dir] if self.legacy_report_dir else []))
            loaded = load_review_queue(path) if path else {"items": []}
            from warder_review_store import apply_git_review_decisions
            self.items = apply_git_review_decisions(loaded.get('items', []), self.git_decision_events) if path else []
            self.groups = build_decision_groups({"items": self.items})["groups"]
            self.load_error = None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.items = []
            self.groups = []
            self.load_error = f'{type(exc).__name__}: {exc}'
        self.page = 0
        self.render()
        self.refresh_git_state()

    def refresh_git_state(self):
        if self.git_decision_loader is None:
            return
        if self._git_syncing:
            self._git_refresh_pending = True
            return
        self._git_syncing = True
        self._git_sync_generation += 1
        generation = self._git_sync_generation
        self.git_status.configure(text='Git Master: synchronizujem…')
        def worker():
            try:
                value = self.git_decision_loader()
                self.after(0, lambda: self._git_sync_done(value, None, generation))
            except Exception as exc:
                detail = f'{type(exc).__name__}: {exc}'
                self.after(0, lambda: self._git_sync_done(None, detail, generation))
        import threading
        threading.Thread(target=worker, name='factory-review-git-read', daemon=True).start()

    def _git_sync_done(self, snapshot, error, generation):
        if generation != self._git_sync_generation:
            return
        self._git_syncing = False
        if self._git_refresh_pending:
            self._git_refresh_pending = False
            self.refresh_git_state()
            return
        if error or not isinstance(snapshot, dict):
            self.git_sync_ready = False
            detail = format_git_sync_error(error or "Git loader returned no snapshot")
            self.git_status.configure(text='Git Master: UNAVAILABLE · ' + detail)
            return
        self.git_sync_ready = True
        self.git_commit = snapshot.get('commit')
        self.git_registry = snapshot.get('registry')
        self.git_decision_events = list(snapshot.get('events', []))
        self.git_status.configure(text='Git Master: '+str(self.git_commit or 'HEAD neznámy')[:12])
        try:
            from warder_review_store import apply_git_review_decisions
            path = latest_review(self.report_dir, *([self.legacy_report_dir] if self.legacy_report_dir else []))
            loaded = load_review_queue(path) if path else {'items': []}
            self.items = apply_git_review_decisions(loaded.get('items', []), self.git_decision_events)
            self.groups = build_decision_groups({'items': self.items})['groups']
            self.render()
            self._maybe_refresh_master_first(snapshot)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.load_error = f'{type(exc).__name__}: {exc}'
            self.render()

    def _maybe_refresh_master_first(self, snapshot):
        if self._master_refresh_running:
            return
        try:
            path = latest_review(self.report_dir, *([self.legacy_report_dir] if self.legacy_report_dir else []))
            loaded = load_review_queue(path) if path else None
            marker = loaded.get('master_first_refresh', {}) if isinstance(loaded, dict) else {}
            if path and marker.get('master_commit') != snapshot.get('commit'):
                self._launch_master_first_refresh(snapshot)
        except (OSError, ValueError, KeyError, TypeError):
            return

    def refresh_master_first(self):
        """Explicitly retry a saved-queue refresh when the automatic attempt failed."""
        self._launch_master_first_refresh(None)

    def _launch_master_first_refresh(self, snapshot):
        """Reclassify the saved queue against a fresh Git Master without scanning or rendering."""
        if self._master_refresh_running:
            return
        if self.git_decision_loader is None:
            self.git_status.configure(text='Git Master: UNAVAILABLE · loader nie je nakonfigurovaný')
            return
        self._master_refresh_running = True
        self.git_status.configure(text='Git Master: obnovujem a prepočítavam uloženú frontu bez renderovania…')
        def worker():
            try:
                current = snapshot if isinstance(snapshot, dict) else self.git_decision_loader()
                source_path = latest_review(self.report_dir, *([self.legacy_report_dir] if self.legacy_report_dir else []))
                if source_path is None:
                    raise ValueError('Nie je dostupný uložený review queue report')
                loaded = load_review_queue(source_path)
                from master_coverage_refresh import recalculate_master_first, persist_master_first_refresh
                result = recalculate_master_first(loaded, current)
                saved = persist_master_first_refresh(self.report_dir, source_path, result)
                self.after(0, lambda: self._master_first_refresh_done(saved, None))
            except Exception as exc:
                detail = format_git_sync_error(type(exc).__name__ + ': ' + str(exc))
                self.after(0, lambda: self._master_first_refresh_done(None, detail))
        import threading
        threading.Thread(target=worker, name='factory-master-first-refresh', daemon=True).start()

    def _master_first_refresh_done(self, result, error):
        self._master_refresh_running = False
        if error:
            self.git_sync_ready = False
            self.refresh_status.configure(text='MASTER-first refresh FAILED · ' + error,
                                          foreground='#b00020')
            return
        self.git_sync_ready = True
        self.git_commit = result.get('master_commit')
        from master_coverage_refresh import format_master_refresh_result
        self.refresh_status.configure(text=format_master_refresh_result(result),
                                      foreground='#176b2c')
        try:
            from warder_review_store import apply_git_review_decisions
            loaded = load_review_queue(result['queue_path'])
            self.items = apply_git_review_decisions(loaded.get('items', []), self.git_decision_events)
            self.groups = build_decision_groups({'items': self.items})['groups']
            self.load_error = None
            self.page = 0
            self.render()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.refresh_status.configure(
                text='MASTER-first report was saved, but GUI could not reload it: '
                     + type(exc).__name__ + ': ' + str(exc), foreground='#b00020')

    def _scope(self, group):
        members = [item for item in self.items if item.get('review_id') in group.get('member_review_ids', [])]
        return {'decision_group_id': group.get('decision_group_id'),
                'group_evidence_sha256': group.get('group_evidence_hash'),
                'items': members}

    def _selection_box(self, frame, group):
        group_id = group.get('decision_group_id')
        variable = self.selected_scopes.get(group_id)
        if variable is None:
            variable = tk.BooleanVar(value=False)
            self.selected_scopes[group_id] = variable
        ttk.Checkbutton(frame, text='Zahrnúť túto presnú skupinu do Git dávky',
                        variable=variable).pack(anchor='w')

    def submit_selected_batch(self):
        from tkinter import messagebox
        if not self.write_enabled():
            messagebox.showwarning('Zápis zablokovaný', 'Read-only preflight musí úspešne overiť workspace.', parent=self)
            return
        scopes = [self._scope(group) for group in self.groups
                  if self.selected_scopes.get(group.get('decision_group_id')) is not None
                  and self.selected_scopes[group.get('decision_group_id')].get()]
        if not scopes:
            messagebox.showinfo('Git dávka', 'Vyber aspoň jednu zobrazenú rozhodovaciu skupinu.', parent=self)
            return
        if len(scopes) > 10:
            messagebox.showwarning('Rozsah dávky', 'Jedna Git transakcia môže obsahovať najviac 10 skupín.', parent=self)
            return
        decision = self.batch_decision.get()
        count = sum(len(scope['items']) for scope in scopes)
        if not messagebox.askyesno('Potvrdiť Git dávku',
                f'{len(scopes)} skupín, {count} položiek\nRozhodnutie: {decision}\n\n'
                'Rozsah sa uloží append-only do vývojového Git Mastera. Toto samo osebe nevytvára ani neschvaľuje Warder ID.',
                parent=self):
            return
        self._submit_scopes(scopes, decision)

    def _submit_scopes(self, scopes, decision, operation=None):
        if self.git_decision_writer is None or self.pending_git_path is None:
            self.git_status.configure(text='FAILED · Git writer alebo staging cesta nie je nakonfigurovaná')
            return
        try:
            from warder_review_store import build_review_batch, stage_pending_batch
            batch = build_review_batch(scopes, decision)
            if operation is not None:
                batch['operation'] = operation
            stage_pending_batch(self.pending_git_path, batch)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            self.git_status.configure(text='FAILED · '+str(exc)[:120])
            return
        self.git_status.configure(text='PENDING → VALIDATING → COMMITTING…')
        self.git_decision_writer(batch, self.git_commit, lambda result: self._git_write_done(batch, result))

    def _git_write_done(self, batch, result):
        status = result.get('status') if isinstance(result, dict) else 'FAILED'
        if status in ('COMMITTED_VERIFIED', 'ALREADY_COMMITTED'):
            try:
                from warder_review_store import clear_pending_batch, apply_git_review_decisions
                if self.pending_git_path:
                    clear_pending_batch(self.pending_git_path, batch['batch_id'])
                self.git_commit = result.get('commit', self.git_commit)
                self._git_sync_generation += 1
                self._git_syncing = False
                self._git_refresh_pending = False
                self.git_decision_events.extend(result.get('events', batch.get('events', [])))
                path = latest_review(self.report_dir, *([self.legacy_report_dir] if self.legacy_report_dir else []))
                loaded = load_review_queue(path) if path else {'items': []}
                self.items = apply_git_review_decisions(loaded.get('items', []), self.git_decision_events)
                self.groups = build_decision_groups({'items': self.items})['groups']
                self.selected_scopes.clear()
                suffix = (' · '+str(result.get('warder_id')) if result.get('warder_id') else '')
                self.git_status.configure(text='SAVED TO GIT · '+str(self.git_commit or '')[:12]+suffix)
                self.render()
                self.refresh_git_state()
            except (ValueError, OSError, TypeError, KeyError) as exc:
                self.git_status.configure(text='COMMITTED · readback/reload issue: '+str(exc)[:100])
            return
        if status == 'PENDING':
            self.git_status.configure(text='PENDING / UNSAVED · '+str(result.get('error', 'Git zapis čaká'))[:100])
        elif status == 'CONFLICT':
            self.git_status.configure(text='CONFLICT · refreshni Git Master a znovu potvrď dávku')
        else:
            self.git_status.configure(text='FAILED / UNSAVED · '+str(result.get('error', status))[:110])

    def retry_pending_batches(self):
        from tkinter import messagebox
        if not self.pending_git_path:
            return
        try:
            from warder_review_store import load_pending_batches
            batches = load_pending_batches(self.pending_git_path)
        except Exception as exc:
            self.git_status.configure(text='FAILED · pending staging: '+str(exc)[:90])
            return
        if not batches:
            self.git_status.configure(text='Git retry: nič PENDING')
            return
        if self.git_decision_writer is None:
            self.git_status.configure(text='PENDING / UNSAVED · Git writer nedostupný')
            return
        self.git_status.configure(text='PENDING → VALIDATING → COMMITTING · '+str(len(batches))+' dávok')
        for batch in batches:
            self.git_decision_writer(batch, self.git_commit,
                lambda result, current=batch: self._git_write_done(current, result))

    def reset_page(self):
        self.page = 0; self.render()

    def turn(self, step):
        self.page += step; self.render()

    def render(self):
        for child in self.content.winfo_children(): child.destroy()
        lane = self.lane.get()
        by_id = {item.get('review_id'): item for item in self.items}
        selected = [group for group in self.groups
                    if lane == 'ALL' or any(by_id.get(member, {}).get('workstream') == lane
                                            for member in group.get('member_review_ids', []))]
        pages = max(1, (len(selected) + 9) // 10)
        self.page = min(max(0, self.page), pages - 1)
        task_count = sum(group.get('review_tasks', 0) for group in selected)
        self.counter.configure(text=f'{self.page+1}/{pages} · rozhodnutia {len(selected)} · položky {task_count}' if not self.load_error else 'CHYBA načítania fronty')
        if self.load_error:
            ttk.Label(self.content, text=self.load_error, foreground='red', wraplength=700).pack(anchor='w', padx=8, pady=8)
        for group in selected[self.page*10:(self.page+1)*10]:
            members = [by_id[review_id] for review_id in group.get('member_review_ids', [])
                       if review_id in by_id]
            if len(members) == 1:
                self.add_row(members[0])
            elif members:
                self.add_group(group, members)
        self.canvas.yview_moveto(0)

    def add_group(self, group, members):
        refs = sorted({str(item.get('candidate_identity') or 'bez identity') for item in members})
        title = f"{group['decision_group_id']} · {group['scope']} · {len(members)} úloh · {len(refs)} služieb"
        frame = ttk.LabelFrame(self.content, text=title, padding=6)
        frame.pack(fill='x', padx=4, pady=4)
        self._selection_box(frame, group)
        ttk.Label(frame, text=group.get('grouping_reason', ''), wraplength=720).pack(anchor='w')
        ttk.Label(frame, text='Členovia: '+', '.join(group.get('member_review_ids', [])), wraplength=720).pack(anchor='w')
        ttk.Label(frame, text='Služby: '+', '.join(refs[:30])+(' …' if len(refs)>30 else ''), wraplength=720).pack(anchor='w')
        ttk.Label(frame, text='Kandidát pixel SHA: '+', '.join(group.get('common_candidate_pixel_sha256', []))+
                  '\nMaster pixel SHA: '+', '.join(group.get('common_master_pixel_sha256', [])), wraplength=720).pack(anchor='w')
        first = members[0]
        ttk.Label(frame, text='Dôvody: '+', '.join(first.get('reasons', []))+
                  ' · zdroje: '+', '.join(first.get('source_origins', [first.get('source_origin','unknown')])),
                  wraplength=720).pack(anchor='w')
        ttk.Label(frame, text='Master SHA: '+', '.join(sorted({str(entry.get('sha256')) for member in members
                  for entry in member.get('master_locations', []) if isinstance(entry, dict) and entry.get('sha256')})),
                  wraplength=720).pack(anchor='w')
        preview = ttk.Frame(frame); preview.pack(fill='x', pady=4)
        preview._photos = []
        candidate_shas = sorted({unit.get('representative_sha256')
                                 for member in members for unit in member.get('artwork_review_units', [])
                                 if isinstance(unit, dict) and isinstance(unit.get('representative_sha256'), str)})
        if not candidate_shas:
            candidate_shas = sorted({sha for member in members for sha in evidence_digests(member)})
        all_candidate_shas = sorted({sha for member in members for sha in evidence_digests(member)})
        ttk.Label(frame, text='Kandidát byte SHA (všetky): '+', '.join(all_candidate_shas[:20])+
                  (' …' if len(all_candidate_shas)>20 else ''), wraplength=720).pack(anchor='w')
        def show_preview(path, label):
            cell = ttk.Frame(preview); cell.pack(side='left', fill='both', expand=True, padx=2)
            ttk.Label(cell, text=label).pack()
            image_label = ttk.Label(cell, text='Náhľad nedostupný', anchor='center')
            image_label.pack(fill='both', expand=True)
            if path and Path(path).is_file():
                try:
                    from PIL import Image, ImageTk
                    with Image.open(path) as source:
                        image = source.convert('RGBA'); image.thumbnail((150, 84))
                    photo = ImageTk.PhotoImage(image, master=self)
                    image_label.configure(image=photo, text=''); image_label.image = photo
                    preview._photos.append(photo)
                except (OSError, ImportError, ValueError):
                    pass
        master_path = None
        if self.master_root:
            for entry in first.get('master_locations', []):
                if not isinstance(entry, dict) or entry.get('style') != 'transparent':
                    continue
                relative = entry.get('path')
                try:
                    candidate = (self.master_root / relative).resolve(strict=True)
                    if candidate.is_relative_to(self.master_root.resolve()) and candidate.is_file():
                        master_path = candidate; break
                except (OSError, TypeError, ValueError):
                    continue
        show_preview(master_path, 'Master · referencia')
        for digest in candidate_shas[:4]:
            source = next((Path(value) for member in members for value in source_candidates(member, digest)
                           if matches_evidence_sha(value, digest)), None)
            show_preview(source, 'Kandidát · '+digest[:12])
            paths = variant_paths(self.output_dir, {'sha256': digest})
            show_preview(paths.get('black'), 'Čierny · '+digest[:12])
            show_preview(paths.get('white'), 'Biely · '+digest[:12])
        if len(candidate_shas) > 4:
            ttk.Label(frame, text=f'Ďalších {len(candidate_shas)-4} kandidátnych SHA je v detaile; nič sa neskrýva z rozhodovacieho rozsahu.',
                      wraplength=720).pack(anchor='w')
        controls = ttk.Frame(frame); controls.pack(fill='x')
        for text, decision, note in (
            ('OK / Beriem skupinu', 'APPROVED_FOR_REVIEW', 'Explicitné rozhodnutie pre zobrazenú skupinu'),
            ('Zamietnuť skupinu', 'REJECTED', 'Explicitné zamietnutie zobrazenej skupiny'),
            ('Preskočiť skupinu', 'DEFERRED', 'Skupina odložená na neskoršiu kontrolu'),
        ):
            ttk.Button(controls, text=text, command=lambda d=decision,n=note,g=group:self.decide_group(g,d,n)).pack(side='left', padx=2)
        if first.get('workstream') == 'IDENTITY_VERIFICATION':
            ttk.Button(controls, text='Označiť AMBIGUOUS',
                       command=lambda g=group:self.decide_group(g,'IDENTITY_AMBIGUOUS','Ľudsky potvrdená nejednoznačná identita')).pack(side='left', padx=2)
            ttk.Button(controls, text='Označiť CONFLICT',
                       command=lambda g=group:self.decide_group(g,'IDENTITY_CONFLICT','Ľudsky potvrdená identitná kolízia')).pack(side='left', padx=2)
            if len({str(member.get('candidate_identity') or '') for member in members}) == 1:
                ttk.Button(controls, text='Potvrdiť identitu + Warder ID',
                           command=lambda g=group:self.approve_identity_to_master(g)).pack(side='left', padx=2)

    def decide_group(self, group, decision, note):
        if not self.write_enabled():
            messagebox.showwarning('Zápis zablokovaný', 'Read-only preflight musí úspešne overiť všetkých 13 adresárov.', parent=self)
            return
        fresh = build_decision_groups({"items": self.items})["groups"]
        current = next((candidate for candidate in fresh
                        if candidate.get('decision_group_id') == group.get('decision_group_id')), None)
        if current is None or current.get('group_evidence_hash') != group.get('group_evidence_hash'):
            messagebox.showwarning('Skupina sa zmenila', 'Dôkazy sa zmenili; načítaj aktuálnu frontu pred rozhodnutím.', parent=self)
            self.reload()
            return
        ids = group.get('member_review_ids', [])
        candidate_shas = sorted({unit.get('representative_sha256')
                                 for item in self.items if item.get('review_id') in set(ids)
                                 for unit in item.get('artwork_review_units', [])
                                 if isinstance(unit, dict) and isinstance(unit.get('representative_sha256'), str)})
        if not candidate_shas:
            candidate_shas = sorted({sha for item in self.items if item.get('review_id') in set(ids)
                                     for sha in evidence_digests(item)})
        if len(candidate_shas) > 4:
            messagebox.showwarning('Skupina vyžaduje detailnú kontrolu',
                                   'Skupinové rozhodnutie je zablokované, pretože skupina obsahuje viac než štyri grafiky.',
                                   parent=self)
            return
        if len(ids) < 2 or any(not any(item.get('review_id') == review_id for item in self.items) for review_id in ids):
            messagebox.showwarning('Neplatný rozsah skupiny', 'Rozsah rozhodnutia už nie je totožný s aktívnou frontou.', parent=self)
            return
        summary = (f"{group['decision_group_id']}\n{len(ids)} úloh, {group.get('service_count', 0)} služieb"
                   f"\nRozsah SHA-256 dôkazov: {group['group_evidence_hash']}\n\n{note}")
        if not messagebox.askyesno('Potvrdiť skupinové rozhodnutie', summary, parent=self):
            return
        # Every visible group action must pass through the same Git transaction
        # as the top-level batch action. Do not write the legacy local decision
        # ledger or remove items until _git_write_done confirms commit + readback.
        self._submit_scopes([self._scope(group)], decision)

    def add_row(self, item):
        frame = ttk.LabelFrame(self.content, text=f"{item['review_id']}  ·  {item.get('candidate_identity') or item.get('sha256') or 'Bez identity'}", padding=5)
        frame.pack(fill='x', padx=4, pady=4)
        group = next((value for value in self.groups if item['review_id'] in value.get('member_review_ids', [])), None)
        if group:
            self._selection_box(frame, group)
        ttk.Label(frame, text=', '.join(item.get('reasons', [])), wraplength=520).pack(anchor='w')
        previews = ttk.Frame(frame); previews.pack(fill='x')
        digests = evidence_digests(item)
        if item.get('workstream') == 'ARTWORK_REVIEW' and not digests:
            ttk.Label(frame, text='Chýba SHA-256 grafiky: rozhodnutie vyžaduje doplnenie dôkazov.').pack(anchor='w')
        if len(digests) > 1:
            ttk.Label(frame, text=f'{len(digests)} rozdielnych grafík: skontroluj každú pred rozhodnutím').pack(anchor='w')
        # Show one artwork triplet at a time to keep large evidence groups responsive.
        # Explicit navigation prevents silently hiding alternative source graphics.
        artwork_host = ttk.Frame(previews)
        artwork_host.pack(fill='x')
        if len(digests) > 1:
            nav = ttk.Frame(frame)
            nav.pack(fill='x')
            position = tk.IntVar(value=0)
            indicator = ttk.Label(nav)
            indicator.pack(side='left')
            def change_artwork(delta):
                position.set((position.get() + delta) % len(digests))
                show_artwork()
            ttk.Button(nav, text='◀ Grafika', command=lambda: change_artwork(-1)).pack(side='left', padx=3)
            ttk.Button(nav, text='Grafika ▶', command=lambda: change_artwork(1)).pack(side='left')
        def show_artwork():
            for child in artwork_host.winfo_children():
                child.destroy()
            # Discard old images when browsing alternatives; keep only live Tk references.
            artwork_host._photos = []
            index = position.get() if len(digests) > 1 else 0
            digest = digests[index] if digests else None
            if len(digests) > 1:
                indicator.configure(text=f'Grafika {index+1}/{len(digests)} · SHA {digest[:12]}')
            paths = variant_paths(self.output_dir, {'sha256': digest} if digest else item)
            # Never present a generated transparent derivative as the original source.
            paths.pop('transparent', None)
            # The transparent source is immutable and may live outside generated output.
            if digest:
                matching = source_candidates(item, digest)
                for source in matching:
                    if isinstance(source, str) and matches_evidence_sha(source, digest):
                        paths['transparent'] = Path(source)
                        break
            for name, label in [('transparent', 'Transparent · referencia 🔒'), ('black', 'Čierny'), ('white', 'Biely')]:
                cell = ttk.Frame(artwork_host)
                cell.pack(side='left', fill='both', expand=True)
                ttk.Label(cell, text=label).pack()
                preview = ttk.Label(cell, text='Náhľad nedostupný', anchor='center')
                preview.pack(fill='both', expand=True, pady=4)
                path = paths.get(name)
                if path and path.is_file():
                    try:
                        from PIL import Image, ImageTk
                        with Image.open(path) as src:
                            im = src.convert('RGBA')
                            im.thumbnail((165, 92))
                        photo = ImageTk.PhotoImage(im, master=self)
                        preview.configure(image=photo, text='')
                        preview.image = photo
                        artwork_host._photos.append(photo)
                    except (OSError, ImportError, ValueError):
                        pass
        show_artwork()
        controls = ttk.Frame(frame); controls.pack(fill='x')
        ttk.Button(controls, text='OK / Beriem', command=lambda i=item: self.decide(i, 'APPROVED_FOR_REVIEW', 'OK / Beriem')).pack(side='left', padx=2)
        ttk.Button(controls, text='Zamietnuť', command=lambda i=item: self.decide(i, 'REJECTED', 'Grafika alebo identita zamietnutá')).pack(side='left', padx=2)
        final_button = ttk.Button(controls, text='Finalizovať QA', command=lambda i=item: self.finalize_qa(i))
        final_button.pack(side='left', padx=2)
        try:
            prepare_finalization(self.output_dir, item)
        except (FinalizationNotReady, ValueError, OSError):
            final_button.configure(state='disabled')
        ttk.Button(controls, text='Opraviť', command=lambda i=item, f=frame: self.repair(f, i)).pack(side='left', padx=2)
        ttk.Button(controls, text='Preskočiť', command=lambda i=item: self.decide(i, 'DEFERRED', 'Preskočené')).pack(side='left', padx=2)
        if item.get('workstream') == 'IDENTITY_VERIFICATION':
            ttk.Button(controls, text='Označiť AMBIGUOUS',
                       command=lambda i=item:self.decide(i,'IDENTITY_AMBIGUOUS','Ľudsky potvrdená nejednoznačná identita')).pack(side='left', padx=2)
            ttk.Button(controls, text='Označiť CONFLICT',
                       command=lambda i=item:self.decide(i,'IDENTITY_CONFLICT','Ľudsky potvrdená identitná kolízia')).pack(side='left', padx=2)
            if group:
                ttk.Button(controls, text='Potvrdiť identitu + Warder ID',
                           command=lambda g=group:self.approve_identity_to_master(g)).pack(side='left', padx=2)
        if item.get('workstream') == 'ARTWORK_REVIEW':
            ttk.Button(controls, text='Schváliť triplet do Mastera',
                       command=lambda i=item:self.approve_artwork_to_master(i)).pack(side='left', padx=2)

    def approve_identity_to_master(self, group):
        from tkinter import simpledialog
        members = [item for item in self.items if item.get('review_id') in group.get('member_review_ids', [])]
        if not members or any(item.get('workstream') != 'IDENTITY_VERIFICATION' for item in members):
            self.git_status.configure(text='FAILED · nejde o identity review')
            return
        seed = str(members[0].get('candidate_identity') or '')
        identity_key = simpledialog.askstring('Nová Warder identita', 'Trvalý identity_key (nie názov loga):', parent=self)
        if not identity_key:
            return
        name = simpledialog.askstring('Nová Warder identita', 'Potvrdený názov stanice:', parent=self)
        if not name:
            return
        service_ref = simpledialog.askstring('Nová Warder identita', 'Potvrdený service reference:', initialvalue=seed, parent=self)
        if not service_ref:
            return
        operators = simpledialog.askstring('Väzby identity', 'Potvrdení provider/operatori, oddelení čiarkou (prázdne, ak neznáme):', parent=self)
        satellites = simpledialog.askstring('Väzby identity', 'Potvrdené satelitné pozície, oddelené čiarkou (prázdne, ak neznáme):', parent=self)
        if operators is None or satellites is None:
            return
        if not messagebox.askyesno('Potvrdiť identitu do Gitu',
                f'{group.get("decision_group_id")}\n{len(members)} položiek\n{name}\n{service_ref}\n\n'
                'Vytvorí sa ďalšie sekvenčné Warder ID. Toto rozhodnutie bude commitnuté do vývojovej vetvy.',
                parent=self):
            return
        identity = {
            'identity_key': identity_key.strip(), 'current_name': name.strip(),
            'canonical_identity': {'identity_key': identity_key.strip()},
            'service_references': [service_ref.strip()],
            'operator_links': sorted({value.strip() for value in operators.split(',') if value.strip()}),
            'satellite_positions': sorted({value.strip() for value in satellites.split(',') if value.strip()}),
            'source_provenance': ['review:' + str(members[0]['review_id'])],
            'first_seen': {'review_id': str(members[0]['review_id'])},
        }
        self._submit_scopes([self._scope(group)], 'APPROVED_FOR_REVIEW',
                            {'type':'IDENTITY_APPROVAL','identity':identity})

    def approve_artwork_to_master(self, item):
        from tkinter import simpledialog
        from warder_review_store import build_review_batch
        if not self.git_sync_ready or not isinstance(self.git_registry, dict):
            self.git_status.configure(text='PENDING · Git Registry nie je synchronizovaný')
            return
        digests = evidence_digests(item)
        if len(digests) != 1:
            messagebox.showwarning('Nejednoznačný artwork', 'Master approval vyžaduje presne jeden kandidátsky artwork.', parent=self)
            return
        digest = digests[0]
        sources = [path for path in source_candidates(item, digest) if matches_evidence_sha(path, digest)]
        if not sources:
            messagebox.showwarning('Chýba pôvod', 'Nie je dostupný zdrojový PNG so zodpovedajúcim SHA-256.', parent=self)
            return
        paths = variant_paths(self.output_dir, {'sha256': digest})
        if not all(paths.get(style) and paths[style].is_file() for style in ('transparent','black','white')):
            messagebox.showwarning('Chýba triplet', 'Transparentný, čierny a biely variant musia byť dostupné pred Master approval.', parent=self)
            return
        warder_id = simpledialog.askstring('Warder Master', 'Zadaj existujúce Warder ID zo synchronizovaného Git Registry:', parent=self)
        if not warder_id:
            return
        record = self.git_registry.get('records', {}).get(warder_id)
        if not isinstance(record, dict):
            messagebox.showwarning('Neznáme Warder ID', 'ID sa v aktuálnom Git Registry nenašlo; nič sa nezapísalo.', parent=self)
            return
        if record.get('artwork_current'):
            messagebox.showwarning('Rebranding vyžaduje samostatný dôkaz',
                'Schválený artwork sa nesmie prepísať. Tento tok vyžaduje samostatné overenie oficiálneho rebrandingu.', parent=self)
            return
        import hashlib
        variant_sha = {}
        for style in ('transparent','black','white'):
            data = paths[style].read_bytes()
            variant_sha[style] = hashlib.sha256(data).hexdigest()
        group = next((value for value in self.groups if item['review_id'] in value.get('member_review_ids', [])), None)
        if not group or len(group.get('member_review_ids', [])) != 1:
            messagebox.showwarning('Rozsah approval', 'Artwork do Mastera sa schvaľuje iba pre jednu presnú review úlohu.', parent=self)
            return
        batch = build_review_batch([self._scope(group)], 'APPROVED_FOR_REVIEW')
        batch['operation'] = {'type':'ARTWORK_APPROVAL','warder_id':warder_id,
                              'variant_sha256':variant_sha,'official_rebrand_confirmed':False}
        if not messagebox.askyesno('Potvrdiť artwork do Mastera',
                f'{item["review_id"]}\n{warder_id}\nSHA {digest}\n\n'
                'Uloží sa kompletný overený triplet, SHA a approval history do vývojového Gitu.',
                parent=self):
            return
        try:
            from warder_review_store import stage_pending_batch
            stage_pending_batch(self.pending_git_path, batch)
        except (ValueError, OSError, TypeError) as exc:
            self.git_status.configure(text='FAILED · '+str(exc)[:100])
            return
        self.git_status.configure(text='PENDING → VALIDATING → COMMITTING…')
        self.git_decision_writer(batch, self.git_commit,
            lambda result:self._git_write_done(batch, result))

    def finalize_qa(self, item):
        if not self.write_enabled():
            messagebox.showwarning('Zápis zablokovaný', 'Read-only preflight musí úspešne overiť všetkých 13 adresárov.', parent=self)
            return
        try:
            request = prepare_finalization(self.output_dir, item)
        except (FinalizationNotReady, ValueError, OSError) as exc:
            messagebox.showerror('Finálna QA nie je pripravená', str(exc), parent=self)
            return
        if not messagebox.askyesno('Finálne schválenie',
                f"{item['review_id']}\n\nOverené BLACK a WHITE, identita aj plastické šablóny.\n"
                'Zapísať do lokálneho finálneho úložiska? Bez GitHub zápisu.', parent=self):
            return
        try:
            from finalize_picons import finalize_triplet
            finalize_triplet(**request)
        except (ValueError, OSError, PermissionError) as exc:
            messagebox.showerror('Finálna QA zlyhala', str(exc), parent=self)
            return
        group = next((value for value in self.groups if item['review_id'] in value.get('member_review_ids', [])), None)
        if group:
            self._submit_scopes([self._scope(group)], 'FINALIZED_LOCALLY')
        else:
            messagebox.showerror('Git zápis zablokovaný', 'Review skupina sa zmenila; lokálny výstup ostal zachovaný, rozhodnutie nie je uložené do Gitu.', parent=self)

    def repair(self, frame, item):
        if not self.write_enabled():
            messagebox.showwarning('Zápis zablokovaný', 'Read-only preflight musí úspešne overiť všetkých 13 adresárov.', parent=self)
            return
        if getattr(frame, '_repair_open', False): return
        frame._repair_open = True
        options = ttk.Frame(frame); options.pack(fill='x', pady=5)
        black = tk.BooleanVar(value=False); white = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text='Opraviť čierny', variable=black).pack(side='left')
        ttk.Checkbutton(options, text='Opraviť biely', variable=white).pack(side='left')
        ttk.Label(frame, text='Čo treba opraviť (transparentný originál je uzamknutý):').pack(anchor='w')
        note = tk.Text(frame, height=3, wrap='word'); note.pack(fill='x')
        def save():
            chosen = [name for name, flag in [('black', black.get()), ('white', white.get())] if flag]
            comment = note.get('1.0', 'end').strip()
            if not chosen or not comment:
                messagebox.showwarning('Chýbajú údaje', 'Označ čierny alebo biely variant a napíš poznámku.', parent=self)
                return
            # DEFERRED preserves the item for re-review; explicit repair request is
            # stored separately so the current decision schema is not misrepresented.
            self.decide(item, 'DEFERRED', 'REPAIR_REQUESTED [' + ','.join(chosen) + ']: ' + comment)
        ttk.Button(frame, text='Uložiť požiadavku na opravu', command=save).pack(anchor='e', pady=3)

    def decide(self, item, decision, note):
        if not self.write_enabled():
            messagebox.showwarning('Zápis zablokovaný', 'Read-only preflight musí úspešne overiť všetkých 13 adresárov.', parent=self)
            return
        digests = evidence_digests(item)
        if item.get('workstream') == 'ARTWORK_REVIEW' and not digests and decision == 'APPROVED_FOR_REVIEW':
            messagebox.showwarning('Chýbajú grafické dôkazy', 'Bez overiteľného SHA-256 nemožno potvrdiť grafiku.', parent=self)
            return
        if len(digests) > 1 and decision == 'APPROVED_FOR_REVIEW':
            if not messagebox.askyesno('Kontrola všetkých grafík',
                    f'Úloha obsahuje {len(digests)} rôznych grafík. Skontroloval/a si všetky transparentné, čierne a biele varianty?',
                    parent=self):
                return
        if decision == 'APPROVED_FOR_REVIEW' and item.get('workstream') == 'ARTWORK_REVIEW':
            for digest in digests:
                if not any(matches_evidence_sha(path, digest) for path in source_candidates(item, digest)):
                    messagebox.showwarning('Chýba originál', 'Pre jednu z grafík chýba overiteľný pôvodný PNG. Schválenie je zablokované.', parent=self)
                    return
                variants = variant_paths(self.output_dir, {'sha256': digest})
                if not all(variants[name].is_file() for name in ('black', 'white')):
                    messagebox.showwarning('Chýbajú varianty', 'Nie sú dostupné čierny aj biely variant pre každú grafiku. Schválenie je zablokované.', parent=self)
                    return
        if not messagebox.askyesno('Potvrdiť', f"{item['review_id']}\n{note[:160]}\n\nRozhodnutie sa uloží do vývojového Git Mastera. Bez úprav PNG a bez publikovania.", parent=self):
            return
        group = next((value for value in self.groups if item['review_id'] in value.get('member_review_ids', [])), None)
        if not group:
            messagebox.showwarning('Skupina sa zmenila', 'Načítaj aktuálnu frontu pred rozhodnutím.', parent=self)
            self.reload()
            return
        self._submit_scopes([self._scope(group)], decision)
