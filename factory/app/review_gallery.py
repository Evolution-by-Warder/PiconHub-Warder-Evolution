"""Embedded, read-only evidence gallery. Decisions never modify PNG or publish."""
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from review_ui import latest_review
from review_queue import load_review_queue
from review_decisions import record_decision
from review_decision_groups import build_decision_groups, record_group_decision, apply_group_decisions
from final_qa_bridge import prepare_finalization, FinalizationNotReady


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
                 legacy_report_dir=None, legacy_ledger_path=None, master_root=None):
        super().__init__(parent)
        self.report_dir = Path(report_dir)
        self.legacy_report_dir = Path(legacy_report_dir) if legacy_report_dir is not None else None
        self.ledger_path = Path(ledger_path)
        self.legacy_ledger_path = Path(legacy_ledger_path) if legacy_ledger_path is not None else None
        self.output_dir = Path(output_dir)
        self.master_root = Path(master_root) if master_root else None
        self.write_enabled = write_enabled or (lambda: True)
        self.items = []
        self.page = 0
        toolbar = ttk.Frame(self); toolbar.pack(fill='x', pady=3)
        ttk.Label(toolbar, text='Schvaľovanie · 10 staníc / dávka', font=('Segoe UI', 10, 'bold')).pack(side='left')
        ttk.Button(toolbar, text='Obnoviť', command=self.reload).pack(side='right')
        nav = ttk.Frame(self); nav.pack(fill='x')
        self.lane = tk.StringVar(value='ARTWORK_REVIEW')
        filter_box = ttk.Combobox(nav, textvariable=self.lane, state='readonly', width=21,
                                  values=('ARTWORK_REVIEW', 'IDENTITY_VERIFICATION', 'TECHNICAL_QA', 'ALL'))
        filter_box.pack(side='left'); filter_box.bind('<<ComboboxSelected>>', lambda _: self.reset_page())
        ttk.Button(nav, text='◀', width=3, command=lambda: self.turn(-1)).pack(side='left', padx=3)
        ttk.Button(nav, text='▶', width=3, command=lambda: self.turn(1)).pack(side='left')
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
            loaded = apply_group_decisions(loaded, self.ledger_path)
            self.items = pending_items(loaded['items'], self.ledger_path,
                                       self.legacy_ledger_path) if path else []
            self.groups = build_decision_groups({"items": self.items})["groups"]
            self.load_error = None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.items = []
            self.groups = []
            self.load_error = f'{type(exc).__name__}: {exc}'
        self.page = 0
        self.render()

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
        try:
            record_group_decision(self.ledger_path, group, decision, note, operator_confirmation=True)
        except (ValueError, OSError, PermissionError) as exc:
            messagebox.showerror('Zápis zlyhal', str(exc), parent=self)
            return
        self.items = [item for item in self.items if item.get('review_id') not in set(ids)]
        self.groups = build_decision_groups({"items": self.items})["groups"]
        self.render()

    def add_row(self, item):
        frame = ttk.LabelFrame(self.content, text=f"{item['review_id']}  ·  {item.get('candidate_identity') or item.get('sha256') or 'Bez identity'}", padding=5)
        frame.pack(fill='x', padx=4, pady=4)
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
            record_decision(self.ledger_path, item, 'FINALIZED_LOCALLY',
                            'Lokálne finalizované po úspešnej finálnej QA; bez publikovania.',
                            operator_confirmation=True)
        except (ValueError, OSError, PermissionError) as exc:
            messagebox.showerror('Finalizácia alebo auditný zápis zlyhal', str(exc), parent=self)
            return
        messagebox.showinfo('Finálna QA', 'BLACK a WHITE sú uložené vo finálnom úložisku.', parent=self)
        self.items = [x for x in self.items if x['review_id'] != item['review_id']]
        self.render()

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
        if not messagebox.askyesno('Potvrdiť', f"{item['review_id']}\n{note[:160]}\n\nBez úprav PNG a bez publikovania.", parent=self):
            return
        try:
            record_decision(self.ledger_path, item, decision, note[:2000], operator_confirmation=True)
        except (ValueError, OSError, PermissionError) as exc:
            messagebox.showerror('Zápis zlyhal', str(exc), parent=self)
            return
        self.items = [x for x in self.items if x['review_id'] != item['review_id']]
        self.render()
