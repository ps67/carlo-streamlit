# calendar_manager.py
"""
Module Calendrier (CTkFrame).
- Permet de charger un fichier .ics, afficher les événements et ajouter un événement simple.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
from ics import Calendar as ICSCalendar, Event
import datetime
import os

class CalendarFrame(ctk.CTkFrame):
    """Frame pour gérer un calendrier .ics simple."""
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True, padx=10, pady=10)

        self.ics_path = None

        title = ctk.CTkLabel(self, text="📅 Module Calendrier", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(6, 10))

        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", padx=6, pady=6)

        self.btn_load = ctk.CTkButton(controls, text="📂 Charger fichier .ics", command=self.load_ics)
        self.btn_load.grid(row=0, column=0, padx=6, pady=6, sticky="w")

        self.lbl_path = ctk.CTkLabel(controls, text="Aucun fichier sélectionné")
        self.lbl_path.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        # Calendar widget (tkcalendar)
        cal_frame = ctk.CTkFrame(self)
        cal_frame.pack(pady=10)
        # Note: tkcalendar.Calendar is a Tk widget; on CTk we can place it inside the CTkFrame
        self.tk_calendar = Calendar(cal_frame, selectmode='day')
        self.tk_calendar.pack()

        # Event entry
        self.title_entry = ctk.CTkEntry(self, placeholder_text="Titre de l'événement")
        self.title_entry.pack(fill="x", padx=6, pady=(8, 4))
        self.btn_add = ctk.CTkButton(self, text="➕ Ajouter l'événement au .ics (09:00)", command=self.add_event)
        self.btn_add.pack(padx=6, pady=(2, 12))

        # Textbox pour lister les événements
        self.events_box = ctk.CTkTextbox(self, height=160)
        self.events_box.pack(fill="both", expand=True, padx=6, pady=6)

    def load_ics(self):
        """Charge un fichier .ics et affiche ses événements."""
        path = filedialog.askopenfilename(title="Choisir fichier .ics", filetypes=[("iCalendar", "*.ics")])
        if not path:
            return
        self.ics_path = path
        self.lbl_path.configure(text=os.path.basename(path))
        self.refresh_events()

    def refresh_events(self):
        """Lit le .ics et affiche les événements dans la textbox."""
        if not self.ics_path:
            messagebox.showinfo("Aucun fichier", "Aucun fichier .ics chargé.")
            return
        try:
            with open(self.ics_path, "r", encoding="utf-8") as f:
                ics_content = f.read()
            cal = ICSCalendar(ics_content)
            self.events_box.delete("0.0", "end")
            for ev in sorted(cal.events, key=lambda e: e.begin):
                try:
                    begin_str = ev.begin.to('local').format("DD/MM/YYYY HH:mm")
                except Exception:
                    begin_str = str(ev.begin)
                self.events_box.insert("end", f"{begin_str} — {ev.name}\n")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire le fichier .ics : {e}")

    def add_event(self):
        """Ajoute un événement simple (heure fixe 09:00) au fichier .ics chargé."""
        if not self.ics_path:
            messagebox.showwarning("Aucun fichier", "Charge d'abord un fichier .ics.")
            return
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Titre manquant", "Renseigne un titre pour l'événement.")
            return
        selected = self.tk_calendar.selection_get()
        # créer événement à 09:00 du jour sélectionné
        dt = datetime.datetime.combine(selected, datetime.time(9, 0))
        try:
            with open(self.ics_path, "r", encoding="utf-8") as f:
                cal = ICSCalendar(f.read())
        except Exception:
            cal = ICSCalendar()

        ev = Event(name=title, begin=dt)
        cal.events.add(ev)
        with open(self.ics_path, "w", encoding="utf-8") as f:
            f.writelines(cal.serialize_iter())
        messagebox.showinfo("Ajouté", f"Événement ajouté : {title} — {dt.strftime('%d/%m/%Y %H:%M')}")
        self.refresh_events()
