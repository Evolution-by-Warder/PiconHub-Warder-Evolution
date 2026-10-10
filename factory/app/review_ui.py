"""Optional exception-only review. Does not write or publish production assets."""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from review_queue import load_review_queue
from review_decisions import record_decision


def latest_review(report_dir):
    files = sorted(Path(report_dir).glob('review-queue-*.json'), reverse=True)
    return files[0] if files else None


class ReviewWindow(tk.Toplevel):
    def __init__(self, parent, report_dir, ledger_path, output_dir=None):
        super().__init__(parent)
        self.title('WARDER — výnimky vyžadujúce rozhodnutie')
        self.geometry('1280x800')
        self.ledger_path = Path(ledger_path)
        self.output_dir = Path(output_dir) if output_dir else None
        self._photos = []
        path = latest_review(report_dir)
        self.items = load_review_queue(path)['items'] if path else []
        self.pending = [i for i in self.items if i.get('decision', 'PENDING') == 'PENDING']
        self.visible = list(self.pending)
        self.page_size = 200
        self.page = 0
        self.selected = None
        frame = ttk.Frame(self, padding=12); frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Nevyriešené výnimky: {len(self.pending)} / {len(self.items)}. Schválenie výnimky NIE JE publikovanie.',
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        filters = ttk.Frame(frame); filters.pack(fill='x', pady=5)
        ttk.Label(filters, text='Pracovná fronta:').pack(side='left')
        self.lane = tk.StringVar(value='TECHNICAL_QA')
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
        self.refresh_list()
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

    def change_lane(self, _event=None):
        self.page = 0
        self.refresh_list()

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh_list()

    def next_page(self):
        self.page += 1
        self.refresh_list()

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
        """Display review evidence only; previews never approve or modify an asset."""
        if not self.output_dir:
            return
        candidates = []
        original = item.get('original')
        if original:
            candidates.append(('original', Path(original)))
        hashes = [item.get('sha256', '')]
        hashes.extend(v.get('sha256', '') for v in item.get('variants', []) if isinstance(v, dict))
        seen = set()
        for digest in hashes:
            if len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest.lower()) or digest in seen:
                continue
            seen.add(digest)
            folder = self.output_dir / digest[:2] / digest
            for name in ('transparent', 'black', 'white'):
                candidates.append((name, folder / (name + '.png')))
        try:
            from PIL import Image, ImageTk
        except ImportError:
            return
        used = set()
        for slot, path in candidates:
            if slot not in self.preview_labels or slot in used or not path.is_file():
                continue
            try:
                with Image.open(path) as source:
                    source.load(); image = source.convert('RGBA'); image.thumbnail((240, 125))
                photo = ImageTk.PhotoImage(image, master=self)
            except Exception:
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
        self.note.delete(0, 'end')
        self.details.configure(state='normal'); self.details.delete('1.0','end'); self.details.configure(state='disabled')
