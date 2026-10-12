"""Optional exception-only review. Does not write or publish production assets."""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from review_queue import load_review_queue
from review_decisions import record_decision


def latest_review(report_dir, *fallback_dirs):
    files = []
    for folder in (report_dir, *fallback_dirs):
        try:
            files.extend(Path(folder).glob('review-queue-*.json'))
        except OSError:
            continue
    files = sorted(files, key=lambda p: (p.stat().st_mtime_ns, p.name) if p.exists() else (0, p.name), reverse=True)
    return files[0] if files else None


class ReviewWindow(tk.Toplevel):
    def __init__(self, parent, report_dir, ledger_path, output_dir=None, legacy_report_dir=None):
        super().__init__(parent)
        self.title('WARDER — výnimky vyžadujúce rozhodnutie')
        self.geometry('1280x800')
        self.ledger_path = Path(ledger_path)
        self.output_dir = Path(output_dir) if output_dir else None
        self._photos = []
        path = latest_review(report_dir, *([legacy_report_dir] if legacy_report_dir else []))
        self.items = load_review_queue(path)['items'] if path else []
        self.pending = [i for i in self.items if i.get('decision', 'PENDING') == 'PENDING']
        self.visible = list(self.pending)
        self.page_size = 10
        self.page = 0
        self.selected = None
        frame = ttk.Frame(self, padding=12); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Nevyriešené výnimky: {len(self.pending)} / {len(self.items)}. Schválenie výnimky NIE JE publikovanie.',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        filters = ttk.Frame(frame); filters.pack(fill='x', pady=5)
        ttk.Label(filters, text='Pracovná fronta:').pack(side='left')
        self.lane = tk.StringVar(value='ARTWORK_REVIEW')
        self.lane_filter = ttk.Combobox(filters, textvariable=self.lane, state='readonly', width=26, values=('TECHNICAL_QA', 'ARTWORK_REVIEW', 'IDENTITY_VERIFICATION', 'ALL'))
        self.lane_filter.pack(side='left', padx=8)
        self.lane_filter.bind('<<ComboboxSelected>>', self.change_lane)
        ttk.Button(filters, text='◀ Predchádzajúca', command=self.previous_page).pack(side='left', padx=3)
        ttk.Button(filters, text='Nasledujúca ▶', command=self.next_page).pack(side='left', padx=3)
        self.page_label = ttk.Label(filters, text='')
        self.page_label.pack(side='left', padx=8)
        columns = ('category', 'reasons', 'identity')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=13)
        for col, title, width in [('category','Kategória',170),('reasons','Dôvod',410),('identity','Identita / SHA',320)]:
            self.tree.heading(col, text=title); self.tree.column(col, width=width)
        self.tree.pack(fill='both', expand=True, pady=8)
        self.tree.bind('<<TreeviewSelect>>', self.show_selected)
        preview = ttk.LabelFrame(frame, text='Originál a varianty', padding=6)
        preview.pack(fill='x', pady=(0, 6))
        self.preview_labels = {}
        for name, title in [('original', 'Zdroj'), ('transparent', 'Transparentný'),
                            ('black', 'Čierne pozadie'), ('white', 'Biele pozadie')]:
            cell = ttk.Frame(preview); cell.pack(side='left', fill='both', expand=True, padx=4)
            ttk.Label(cell, text=title).pack()
            image_label = ttk.Label(cell, text='Náhľad nie je dostupný', anchor='center')
            image_label.pack(fill='both', expand=True)
            self.preview_labels[name] = image_label
        self.details = tk.Text(frame, height=5, wrap='word', state='disabled'); self.details.pack(fill='x')
        ttk.Label(frame, text='Poznámka k rozhodnutiu:').pack(anchor='w', pady=(8, 0))
        self.note = ttk.Entry(frame); self.note.pack(fill='x')
        actions = ttk.Frame(frame); actions.pack(fill='x', pady=8)
        ttk.Button(actions, text='Odložiť', command=lambda:self.decide('DEFERRED')).pack(side='left', padx=4)
        ttk.Button(actions, text='Zamietnuť', command=lambda:self.decide('REJECTED')).pack(side='left', padx=4)
        ttk.Button(actions, text='Schváliť iba na ďalšie posúdenie', command=lambda:self.decide('APPROVED_FOR_REVIEW')).pack(side='left', padx=4)
        ttk.Button(actions, text='Zavrieť', command=self.destroy).pack(side='right')
        self.refresh_list()
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])
            self.show_selected()

    def change_lane(self, _event=None):
        self.page = 0
        self.refresh_list()

    def _select_first(self):
        rows = self.tree.get_children()
        if rows:
            self.tree.selection_set(rows[0])
            self.show_selected()

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh_list()
        self._select_first()

    def next_page(self):
        self.page += 1
        self.refresh_list()
        self._select_first()

    def refresh_list(self, _event=None):
        lane = self.lane.get()
        self.visible = [item for item in self.pending if lane == 'ALL' or item.get('workstream', {'TECHNICAL_QA':'TECHNICAL_QA', 'IDENTITY_COLLISION':'IDENTITY_VERIFICATION'}.get(item.get('category'), 'ARTWORK_REVIEW')) == lane]
        total = len(self.visible)
        max_page = max(0, (total - 1) // self.page_size)
        self.page = min(self.page, max_page)
        self.visible = self.visible[self.page * self.page_size:(self.page + 1) * self.page_size]
        self.page_label.configure(text=f'Strana {self.page + 1}/{max_page + 1} · spolu {total}')
        self.tree.delete(*self.tree.get_children())
        self.selected = None
        for index, item in enumerate(self.visible):
            self.tree.insert('', 'end', iid=str(index), values=(item['category'], ', '.join(item['reasons']), item.get('candidate_identity') or item.get('sha256') or ''))

    def show_selected(self, _event=None):
        selection = self.tree.selection()
        self.selected = int(selection[0]) if selection else None
        self._photos = []
        for label in self.preview_labels.values():
            label.configure(image='', text='Náhľad nie je dostupný')
        self.details.configure(state='normal'); self.details.delete('1.0', 'end')
        if self.selected is not None:
            import json
            item = self.visible[self.selected]
            self.details.insert('end', json.dumps(item, ensure_ascii=False, indent=2))
            self._show_previews(item)
        self.details.configure(state='disabled')

    def _show_previews(self, item):
        """Render existing evidence; never create or approve picons."""
        candidates = []
        def add(slot, value):
            if not value or not isinstance(value, (str, Path)):
                return
            path = Path(value)
            if path.suffix.lower() == '.png':
                candidates.append((slot, path))

        add('original', item.get('original'))
        for variant in item.get('variants') or []:
            if isinstance(variant, dict):
                add('original', variant.get('source') or variant.get('path'))
        for entry in item.get('source_evidence') or []:
            if isinstance(entry, dict):
                add('original', entry.get('source'))
            elif isinstance(entry, str):
                add('original', entry)
        for entry in item.get('master_locations') or []:
            if isinstance(entry, str):
                add('transparent', entry)
            elif isinstance(entry, dict):
                for key in ('path', 'source', 'location', 'transparent'):
                    add('transparent', entry.get(key))
                for key in ('black', 'white'):
                    add(key, entry.get(key))
        if self.output_dir:
            hashes = [item.get('sha256')]
            hashes.extend(v.get('sha256') for v in item.get('variants', []) if isinstance(v, dict))
            hashes.extend(v.get('sha256') for v in item.get('source_evidence') or [] if isinstance(v, dict))
            hashes.extend(v.get('representative_sha256') for v in item.get('artwork_review_units') or [] if isinstance(v, dict))
            for digest in dict.fromkeys(h for h in hashes if isinstance(h, str)):
                if len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest.lower()):
                    continue
                folder = self.output_dir / digest[:2] / digest
                for name in ('transparent', 'black', 'white'):
                    add(name, folder / (name + '.png'))
        try:
            from PIL import Image, ImageTk
        except ImportError:
            return
        used = set()
        for slot, path in candidates:
            if slot in used or not path.is_file():
                continue
            try:
                with Image.open(path) as source:
                    source.load()
                    image = source.convert('RGBA')
                    image.thumbnail((240, 125))
                photo = ImageTk.PhotoImage(image, master=self)
            except (OSError, ValueError):
                continue
            label = self.preview_labels[slot]
            label.configure(image=photo, text='')
            label.image = photo
            self._photos.append(photo)
            used.add(slot)

    def decide(self, decision):
        if self.selected is None: return
        item = self.visible[self.selected]
        if not messagebox.askyesno('Potvrdiť rozhodnutie',
                                  f'{decision}\n{item["review_id"]}\n\nToto nepublikuje nič na GitHub.', parent=self):
            return
        try:
            record_decision(self.ledger_path, item, decision, self.note.get(), operator_confirmation=True)
        except (OSError, ValueError, PermissionError) as exc:
            messagebox.showerror('Zápis zlyhal', str(exc), parent=self); return
        self.pending = [entry for entry in self.pending if entry['review_id'] != item['review_id']]
        self.refresh_list()
        self._select_first()
        self.note.delete(0, 'end')
        self.details.configure(state='normal'); self.details.delete('1.0','end'); self.details.configure(state='disabled')
