"""Embedded, read-only evidence gallery. Decisions never modify PNG or publish."""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from review_ui import latest_review
from review_queue import load_review_queue
from review_decisions import record_decision
from final_qa_bridge import prepare_finalization, FinalizationNotReady


def variant_paths(output_dir, item):
    """Resolve generated derivatives by digest; transparent is reference only."""
    digest = item.get('sha256')
    if not digest:
        evidence = item.get('source_evidence') or item.get('variants') or []
        digests = sorted({x.get('sha256', '') for x in evidence if isinstance(x, dict)})
        digest = digests[0] if digests else ''
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()):
        return {}
    base = Path(output_dir) / digest[:2] / digest
    return {name: base / (name + '.png') for name in ('transparent', 'black', 'white')}


def evidence_digests(item):
    evidence = item.get('source_evidence') or item.get('variants') or []
    values = [item.get('sha256')] + [entry.get('sha256') for entry in evidence if isinstance(entry, dict)]
    return sorted({value.lower() for value in values if isinstance(value, str) and len(value) == 64
                   and all(c in '0123456789abcdef' for c in value.lower())})


class ReviewGallery(ttk.Frame):
    """Ten review entries per page, scrollable in the main window."""
    def __init__(self, parent, report_dir, ledger_path, output_dir):
        super().__init__(parent)
        self.report_dir = Path(report_dir)
        self.ledger_path = Path(ledger_path)
        self.output_dir = Path(output_dir)
        self.items = []
        self.page = 0
        self.photos = []
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
        path = latest_review(self.report_dir)
        self.items = [x for x in load_review_queue(path)['items'] if x.get('decision', 'PENDING') == 'PENDING'] if path else []
        # Respect decisions made in this session even before the next engine scan.
        if self.ledger_path.exists():
            import json
            from review_decisions import evidence_hash
            try:
                decisions = json.loads(self.ledger_path.read_text(encoding='utf-8')).get('decisions', {})
                self.items = [x for x in self.items if not (x['review_id'] in decisions and decisions[x['review_id']].get('evidence_hash') == evidence_hash(x))]
            except (ValueError, OSError, KeyError, TypeError):
                pass
        self.render()

    def reset_page(self):
        self.page = 0; self.render()

    def turn(self, step):
        self.page += step; self.render()

    def render(self):
        for child in self.content.winfo_children(): child.destroy()
        self.photos.clear()
        lane = self.lane.get()
        selected = [x for x in self.items if lane == 'ALL' or x.get('workstream') == lane]
        pages = max(1, (len(selected) + 9) // 10)
        self.page = min(max(0, self.page), pages - 1)
        self.counter.configure(text=f'{self.page+1}/{pages} · čaká {len(selected)}')
        for item in selected[self.page*10:(self.page+1)*10]:
            self.add_row(item)
        self.canvas.yview_moveto(0)

    def add_row(self, item):
        frame = ttk.LabelFrame(self.content, text=f"{item['review_id']}  ·  {item.get('candidate_identity') or item.get('sha256') or 'Bez identity'}", padding=5)
        frame.pack(fill='x', padx=4, pady=4)
        ttk.Label(frame, text=', '.join(item.get('reasons', [])), wraplength=520).pack(anchor='w')
        previews = ttk.Frame(frame); previews.pack(fill='x')
        digests = evidence_digests(item)
        if len(digests) > 1:
            ttk.Label(frame, text=f'{len(digests)} rozdielnych grafík: skontroluj každú pred rozhodnutím').pack(anchor='w')
        for artwork_index, digest in enumerate(digests or [None], 1):
            triplet = ttk.Frame(previews)
            triplet.pack(fill='x', pady=3)
            if len(digests) > 1:
                ttk.Label(previews, text=f'Grafika {artwork_index}/{len(digests)} · SHA {digest[:12]}').pack(anchor='w')
            paths = variant_paths(self.output_dir, {'sha256': digest} if digest else item)
            for name, label in [('transparent', 'Transparent · referencia 🔒'), ('black', 'Čierny'), ('white', 'Biely')]:
                cell = ttk.Frame(triplet); cell.pack(side='left', fill='both', expand=True)
                ttk.Label(cell, text=label).pack()
                preview = ttk.Label(cell, text='Náhľad nedostupný', anchor='center')
                preview.pack(fill='both', expand=True, pady=4)
                path = paths.get(name)
                if path and path.is_file():
                    try:
                        from PIL import Image, ImageTk
                        with Image.open(path) as src:
                            im = src.convert('RGBA'); im.thumbnail((165, 92))
                        photo = ImageTk.PhotoImage(im, master=self)
                        preview.configure(image=photo, text='')
                        self.photos.append(photo)
                    except (OSError, ImportError, ValueError):
                        pass
        controls = ttk.Frame(frame); controls.pack(fill='x')
        ttk.Button(controls, text='OK / Beriem', command=lambda i=item: self.decide(i, 'APPROVED_FOR_REVIEW', 'OK / Beriem')).pack(side='left', padx=2)
        final_button = ttk.Button(controls, text='Finalizovať QA', command=lambda i=item: self.finalize_qa(i))
        final_button.pack(side='left', padx=2)
        try:
            prepare_finalization(self.output_dir, item)
        except (FinalizationNotReady, ValueError, OSError):
            final_button.configure(state='disabled')
        ttk.Button(controls, text='Opraviť', command=lambda i=item, f=frame: self.repair(f, i)).pack(side='left', padx=2)
        ttk.Button(controls, text='Preskočiť', command=lambda i=item: self.decide(i, 'DEFERRED', 'Preskočené')).pack(side='left', padx=2)

    def finalize_qa(self, item):
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
            messagebox.showerror('Finalizácia zlyhala', str(exc), parent=self)
            return
        messagebox.showinfo('Finálna QA', 'BLACK a WHITE sú uložené vo finálnom úložisku.', parent=self)
        self.items = [x for x in self.items if x['review_id'] != item['review_id']]
        self.render()

    def repair(self, frame, item):
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
        digests = evidence_digests(item)
        if len(digests) > 1 and decision == 'APPROVED_FOR_REVIEW':
            if not messagebox.askyesno('Kontrola všetkých grafík',
                    f'Úloha obsahuje {len(digests)} rôznych grafík. Skontroloval/a si všetky transparentné, čierne a biele varianty?',
                    parent=self):
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
