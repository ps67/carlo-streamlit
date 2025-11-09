# excel_manager.py
"""
Module Excel + Scraper Carlo Erba intégré.
- ExcelFrame: interface pour ouvrir un fichier Excel, afficher un aperçu et lancer le scraping.
- CarloScraperThread: adapte ton code de scraping pour s'exécuter dans un thread (non bloquant).
"""

import os
import threading
import time
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

# ----------------------------
# Worker de scraping (thread)
# ----------------------------
class CarloScraperThread(threading.Thread):
    """
    Thread pour exécuter le scraping sans bloquer l'interface.
    Appelle les callbacks pour logger / mettre à jour la progression.
    """

    def __init__(self, email, password, references, output_folder,
                 log_callback=None, progress_callback=None, finished_callback=None, rate_delay=0.4):
        super().__init__(daemon=True)
        self.email = email
        self.password = password
        self.references = references
        self.output_folder = output_folder
        self.log = log_callback or (lambda msg: None)
        self.progress = progress_callback or (lambda current, total: None)
        self.finished = finished_callback or (lambda success, path_or_msg: None)
        self.rate_delay = rate_delay
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        """Exécute le scraping en se basant sur le code fourni par l'utilisateur."""
        try:
            session = requests.Session()
            # Setup retry pour tolérance réseau
            retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500,502,503,504])
            session.mount("https://", HTTPAdapter(max_retries=retries))
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (compatible; UnivScraper/1.0)"
            })

            # 1) Récupérer CSRF token
            login_page_url = "https://www.carloerbareagents.com/cerstorefront/cer-fr/login"
            self.log(f"➡️ Requête page login : {login_page_url}")
            resp = session.get(login_page_url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            token_input = soup.find("input", {"name": "CSRFToken"})
            if not token_input:
                self.log("❌ Impossible de trouver le CSRFToken sur la page de login.")
                self.finished(False, "CSRFToken introuvable")
                return
            csrf_token = token_input.get("value", "")
            self.log("🔑 CSRFToken récupéré.")

            # 2) Formulaire de connexion
            payload = {"j_username": self.email, "j_password": self.password, "CSRFToken": csrf_token}
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": login_page_url,
                "Origin": "https://www.carloerbareagents.com",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            login_url = "https://www.carloerbareagents.com/cerstorefront/cer-fr/j_spring_security_check"
            login_resp = session.post(login_url, data=payload, headers=headers, allow_redirects=False, timeout=15)
            if login_resp.status_code not in (302, 200):
                self.log(f"❌ Échec de la connexion (HTTP {login_resp.status_code}).")
                self.finished(False, f"Échec de connexion HTTP {login_resp.status_code}")
                return
            self.log("✅ Connexion réussie.")

            # 3) Préparer la liste de références et exécuter les recherches
            total = len(self.references)
            self.log(f"ℹ️ {total} références à rechercher.")
            results = []
            for idx, ref in enumerate(self.references, start=1):
                if self._stop_flag:
                    self.log("⏹️ Scraping interrompu par l'utilisateur.")
                    self.finished(False, "Interrompu")
                    return

                self.progress(idx, total)   # callback mise à jour progress bar
                self.log(f"\n🔍 Recherche ({idx}/{total}) : {ref}")

                search_url = f"https://www.carloerbareagents.com/cerstorefront/cer-fr/search/?text={ref}"
                try:
                    r = session.get(search_url, timeout=15)
                except Exception as e:
                    self.log(f"❗ Erreur réseau pour {ref} : {e}")
                    time.sleep(self.rate_delay)
                    continue

                if r.status_code != 200:
                    self.log(f"❗ HTTP {r.status_code} pour {ref}")
                    time.sleep(self.rate_delay)
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                products = soup.find_all('tr', class_='quickAddToCart')

                if not products:
                    self.log(f"⚠️ Aucun produit trouvé pour : {ref}")
                    time.sleep(self.rate_delay)
                    continue

                for product in products:
                    try:
                        product_name = product.find('input', {'name': 'productNamePost'}).get('value', '')
                        cond_elem = product.find('td', class_='item__info--variantDescription')
                        conditionnement = cond_elem.text.strip() if cond_elem else ""
                        tds = product.find_all('td')
                        emballage = tds[2].text.strip() if len(tds) > 2 else ""
                        unite_vente = tds[3].text.strip() if len(tds) > 3 else ""
                        quantite_input = product.find('input', {'name': 'initialQuantityVariant'})
                        quantite = quantite_input.get('value') if quantite_input else ""
                        price_input = product.find('input', {'name': 'productPostPrice'})
                        price = price_input.get('value') if price_input else ""

                        availability_icon = product.find('i')
                        availability_title = availability_icon.get('title') if availability_icon else None
                        if availability_title == "Produit en stock":
                            disponibilite = "En stock"
                        elif availability_title == "Disponible sous 15 jours":
                            disponibilite = "Disponible sous 15 jours"
                        elif availability_title == "Disponible en plus de 30 jours":
                            disponibilite = "Disponible en plus de 30 jours"
                        else:
                            disponibilite = "Non précisé"

                        item = {
                            'Référence cherchée': ref,
                            'Produit': product_name,
                            'Cdt': conditionnement,
                            'Emballage': emballage,
                            'Unité de vente': unite_vente,
                            'Qté': quantite,
                            'Prix €': price,
                            'Disponibilité': disponibilite
                        }
                        results.append(item)

                        # Log plus détaillé
                        self.log(f"  📦 {product_name} — {price}€ — {disponibilite}")
                    except Exception as e:
                        self.log(f"⚠️ Erreur d'extraction pour {ref} : {e}")
                        continue

                time.sleep(self.rate_delay)

            # 4) Exporter résultats si présents
            if results:
                os.makedirs(self.output_folder, exist_ok=True)
                output_file = os.path.join(self.output_folder, "resultats_scraping.xlsx")
                df = pd.DataFrame(results)
                df.to_excel(output_file, index=False)
                self.log(f"\n✅ Données enregistrées dans : {output_file}")
                self.finished(True, output_file)
            else:
                self.log("\n⚠️ Aucun produit trouvé pour les références fournies.")
                self.finished(False, "Aucun résultat")

        except Exception as e:
            self.log(f"❌ Exception durant le scraping : {e}")
            self.finished(False, str(e))


# ----------------------------
# ExcelFrame : UI pour Excel + Scraper
# ----------------------------
class ExcelFrame(ctk.CTkFrame):
    """
    CTkFrame contenant :
    - bouton pour ouvrir un fichier Excel (lecture des références),
    - aperçu (Treeview) du fichier Excel,
    - zone pour entrer identifiants (email / mdp) et options,
    - bouton pour lancer le scraping Carlo Erba,
    - zone de logs + barre de progression.
    """

    def __init__(self, parent):
        super().__init__(parent)
        # Layout : colonne principale (top controls) + aperçu + logs
        self.pack(fill="both", expand=True, padx=10, pady=10)

        # Variables & state
        self.df = None
        self.excel_path = None
        self.scraper_thread = None

        # --- Titre ---
        title = ctk.CTkLabel(self, text="📊 Module Excel et Scraper Carlo Erba", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(6, 10))

        # --- Row : ouverture fichier Excel + aperçu colonne référence ---
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", pady=6, padx=6)

        self.btn_open = ctk.CTkButton(top_frame, text="📂 Ouvrir un fichier Excel", command=self.open_excel_file)
        self.btn_open.grid(row=0, column=0, padx=6, pady=6, sticky="w")

        self.lbl_path = ctk.CTkLabel(top_frame, text="Aucun fichier sélectionné", anchor="w")
        self.lbl_path.grid(row=0, column=1, padx=6, sticky="we")
        top_frame.grid_columnconfigure(1, weight=1)

        # --- Identifiants utilisateur pour Carlo Erba (email / password) ---
        creds_frame = ctk.CTkFrame(self)
        creds_frame.pack(fill="x", padx=6, pady=(6, 12))

        self.email_entry = ctk.CTkEntry(creds_frame, placeholder_text="Email (carloerba)")
        self.email_entry.grid(row=0, column=0, padx=6, pady=6, sticky="we")
        self.password_entry = ctk.CTkEntry(creds_frame, placeholder_text="Mot de passe", show="*")
        self.password_entry.grid(row=0, column=1, padx=6, pady=6, sticky="we")
        creds_frame.grid_columnconfigure(0, weight=1)
        creds_frame.grid_columnconfigure(1, weight=1)

        # --- Options : chercher dans fichier / manuellement / les 2 ---
        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", padx=6, pady=(0, 12))

        self.search_var = ctk.StringVar(value="excel")  # "excel", "manual", "both"
        # radio-like implementation simple
        rb1 = ctk.CTkRadioButton(options_frame, text="Chercher dans le fichier Excel", variable=self.search_var, value="excel")
        rb1.grid(row=0, column=0, padx=6, pady=6, sticky="w")
        rb2 = ctk.CTkRadioButton(options_frame, text="Chercher manuellement", variable=self.search_var, value="manual")
        rb2.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        rb3 = ctk.CTkRadioButton(options_frame, text="Excel + manuel", variable=self.search_var, value="both")
        rb3.grid(row=0, column=2, padx=6, pady=6, sticky="w")

        # Champ manuelle
        self.manual_entry = ctk.CTkEntry(self, placeholder_text="Références manuelles, séparées par des virgules")
        self.manual_entry.pack(fill="x", padx=6, pady=(0, 12))

        # --- Boutons d'action : Lancer / Arrêter, Exporter aperçu ---
        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(fill="x", padx=6, pady=(0, 12))

        self.btn_run = ctk.CTkButton(actions_frame, text="▶ Lancer le scraping", fg_color="green", command=self.start_scraping)
        self.btn_run.grid(row=0, column=0, padx=6, pady=6)

        self.btn_stop = ctk.CTkButton(actions_frame, text="⏹ Arrêter", fg_color="orange", command=self.stop_scraping)
        self.btn_stop.grid(row=0, column=1, padx=6, pady=6)
        self.btn_stop.configure(state="disabled")

        self.btn_export_preview = ctk.CTkButton(actions_frame, text="💾 Exporter aperçu", command=self.export_preview)
        self.btn_export_preview.grid(row=0, column=2, padx=6, pady=6)

        # --- Aperçu du fichier Excel (Treeview) ---
        preview_frame = ctk.CTkFrame(self)
        preview_frame.pack(fill="both", expand=True, padx=6, pady=6)

        # On utilise ttk.Treeview (widget tkinter natif) pour le tableau
        self.tree = ttk.Treeview(preview_frame, show="headings")
        self.tree.pack(fill="both", expand=True, side="left")
        # Ajouter scrollbar
        vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        # --- Zone logs et progression en bas ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=6, pady=6)

        self.progress = ctk.CTkProgressBar(bottom_frame)
        self.progress.pack(fill="x", padx=6, pady=(6, 4))
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(bottom_frame, height=140)
        self.log_box.pack(fill="x", padx=6, pady=(4, 6))

    # ----------------------------
    # Fonctions UI / I/O
    # ----------------------------
    def open_excel_file(self):
        """Ouvre un fichier Excel et affiche un aperçu dans le Treeview."""
        path = filedialog.askopenfilename(title="Choisir fichier Excel", filetypes=[("Excel", "*.xlsx *.xls")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire le fichier Excel : {e}")
            return

        self.df = df
        self.excel_path = path
        self.lbl_path.configure(text=os.path.basename(path))
        self.display_preview(df)

    def display_preview(self, df, max_rows=200):
        """Affiche un aperçu du DataFrame dans le Treeview (limité)."""
        # vider l'ancienne table
        for col in self.tree.get_children():
            self.tree.delete(col)
        self.tree["columns"] = list(df.columns)

        # configure headings & column widths
        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        rows = df.head(max_rows).itertuples(index=False, name=None)
        for r in rows:
            self.tree.insert("", "end", values=r)

    def export_preview(self):
        """Export simple du DataFrame chargé (si présent)."""
        if self.df is None:
            messagebox.showinfo("Aucun fichier", "Aucun fichier Excel chargé.")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if save_path:
            try:
                self.df.to_excel(save_path, index=False)
                messagebox.showinfo("Exporté", f"Fichier exporté : {save_path}")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    # ----------------------------
    # Scraping orchestration
    # ----------------------------
    def start_scraping(self):
        """Prépare la liste de références et lance le thread de scraping."""
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        option = self.search_var.get()
        manual_text = self.manual_entry.get().strip()

        # Valider les champs selon l'option sélectionnée
        if option in ("excel", "both") and not self.excel_path and not manual_text:
            messagebox.showwarning("Champs manquants", "Sélectionne un fichier Excel contenant la colonne 'Référence' ou saisis des références manuellement.")
            return
        if not email or not password:
            messagebox.showwarning("Identifiants", "Renseigne ton email et mot de passe pour Carlo Erba.")
            return

        # Construire la liste de références
        refs = []
        if option in ("excel", "both"):
            # On s'attend à une colonne 'Référence' dans l'excel ; sinon on prend toute la première colonne
            try:
                df = pd.read_excel(self.excel_path)
                if 'Référence' in df.columns:
                    refs.extend(df['Référence'].dropna().astype(str).tolist())
                else:
                    # fallback : première colonne
                    first_col = df.columns[0]
                    refs.extend(df[first_col].dropna().astype(str).tolist())
            except Exception as e:
                messagebox.showerror("Erreur lecture Excel", str(e))
                return

        if option in ("manual", "both") and manual_text:
            refs.extend([r.strip() for r in manual_text.split(",") if r.strip()])

        if not refs:
            messagebox.showinfo("Aucune référence", "Aucune référence à rechercher.")
            return

        # Désactiver bouton run & activer stop
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log_box.delete("0.0", "end")
        self.progress.set(0)

        # Dossier de sortie situé à côté du fichier Excel s'il existe, sinon dossier courant
        output_folder = os.path.dirname(self.excel_path) if self.excel_path else os.getcwd()

        # Instancier et démarrer le thread
        self.scraper_thread = CarloScraperThread(
            email=email,
            password=password,
            references=refs,
            output_folder=output_folder,
            log_callback=self._thread_log,
            progress_callback=self._thread_progress,
            finished_callback=self._thread_finished,
            rate_delay=0.4
        )
        self.scraper_thread.start()

    def stop_scraping(self):
        """Demande l'arrêt du thread de scraping."""
        if self.scraper_thread:
            self.scraper_thread.stop()
            self._log("⏹️ Arrêt demandé...")

    # ----------------------------
    # Callbacks du thread -> mises à jour UI
    # ----------------------------
    def _thread_log(self, msg):
        """Callback utilisé par le thread pour envoyer un message de log."""
        # on utilise after pour garantir exécution dans thread principal (safe UI)
        self.after(0, lambda: self._log(msg))

    def _log(self, msg):
        """Affiche un message dans la zone de log (UI thread)."""
        self.log_box.insert("end", msg + "\n")
        # scroll automatique
        self.log_box.see("end")

    def _thread_progress(self, current, total):
        """Callback de progression du thread -> met à jour la progressbar."""
        self.after(0, lambda: self._set_progress(current/total if total else 0))

    def _set_progress(self, fraction):
        try:
            self.progress.set(fraction)
        except Exception:
            pass

    def _thread_finished(self, success, path_or_msg):
        """Callback lorsqu'un thread a terminé (succès ou échec)."""
        def finish_ui():
            if success:
                messagebox.showinfo("Terminé", f"Scraping terminé. Fichier enregistré :\n{path_or_msg}")
            else:
                messagebox.showwarning("Terminé", f"Fin: {path_or_msg}")
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.progress.set(0)
        self.after(0, finish_ui)
