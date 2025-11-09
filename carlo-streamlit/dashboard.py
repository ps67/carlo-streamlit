import customtkinter as ctk
import datetime
import threading
from tkinter import messagebox
import requests
from bs4 import BeautifulSoup

# === MODULES INTERNES ===
# Ici tu pourras importer tes futurs modules :
# from module_excel import ExcelModule
# from module_calendrier import CalendrierModule

# === CLASSE PRINCIPALE ===
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ==== CONFIGURATION FENÊTRE ====
        self.title("Outil de gestion - Guillaume Saucy")
        self.geometry("1100x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ==== STRUCTURE PRINCIPALE ====
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Barre du haut
        self.topbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self._create_topbar()

        # Menu latéral
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=1, column=0, sticky="nswe")
        self._create_sidebar()

        # Zone principale (tableau de bord)
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=1, column=1, sticky="nsew")
        self.show_dashboard()

    # ==== BARRE SUPÉRIEURE ====
    def _create_topbar(self):
        self.topbar.grid_columnconfigure(0, weight=1)

        # Nom de l’application
        self.app_label = ctk.CTkLabel(
            self.topbar,
            text="Magasin Chimie - Tableau de bord",
            font=("Roboto Bold", 18)
        )
        self.app_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Horloge dynamique ⏰
        self.clock_label = ctk.CTkLabel(self.topbar, text="", font=("Roboto", 16))
        self.clock_label.grid(row=0, column=1, padx=20, sticky="e")
        self.update_clock()

    def update_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=now)
        self.after(1000, self.update_clock)  # actualise chaque seconde

    # ==== MENU LATÉRAL ====
    def _create_sidebar(self):
        title = ctk.CTkLabel(self.sidebar, text="Navigation", font=("Roboto Bold", 16))
        title.pack(pady=10)

        btn_dashboard = ctk.CTkButton(self.sidebar, text="🏠 Tableau de bord", command=self.show_dashboard)
        btn_dashboard.pack(pady=5)

        btn_excel = ctk.CTkButton(self.sidebar, text="📊 Module Excel", command=self.show_excel)
        btn_excel.pack(pady=5)

        btn_calendar = ctk.CTkButton(self.sidebar, text="🗓️ Calendrier (.ics)", command=self.show_calendar)
        btn_calendar.pack(pady=5)

        btn_scraping = ctk.CTkButton(self.sidebar, text="🧾 Scraping produits", command=self.show_scraping)
        btn_scraping.pack(pady=5)

        btn_quit = ctk.CTkButton(self.sidebar, text="🚪 Quitter", fg_color="red", command=self.destroy)
        btn_quit.pack(pady=30)

    # ==== TABLEAU DE BORD ====
    def show_dashboard(self):
        self._clear_main_frame()

        title = ctk.CTkLabel(self.main_frame, text="Tableau de bord d’accueil", font=("Roboto Bold", 20))
        title.pack(pady=20)

        # --- Cartes de statistiques ---
        stats_frame = ctk.CTkFrame(self.main_frame)
        stats_frame.pack(pady=10)

        cards = [
            ("📦 Articles en stock", "620"),
            ("📅 Livraisons du jour", "4"),
            ("⚠️ Alertes à vérifier", "2"),
            ("👥 Utilisateurs actifs", "10")
        ]

        for text, value in cards:
            card = ctk.CTkFrame(stats_frame, width=200, height=100, corner_radius=10)
            card.pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(card, text=text, font=("Roboto", 14)).pack(pady=5)
            ctk.CTkLabel(card, text=value, font=("Roboto Bold", 24)).pack()

    # ==== MODULE EXCEL ====
    def show_excel(self):
        self._clear_main_frame()
        label = ctk.CTkLabel(self.main_frame, text="Module Excel (à intégrer)", font=("Roboto Bold", 20))
        label.pack(pady=20)
        # Tu pourras ici intégrer ton module Excel directement

    # ==== MODULE CALENDRIER ====
    def show_calendar(self):
        self._clear_main_frame()
        label = ctk.CTkLabel(self.main_frame, text="Module Calendrier (.ics)", font=("Roboto Bold", 20))
        label.pack(pady=20)

        info = ctk.CTkLabel(self.main_frame, text="Lecture du fichier calendrier.ics :", font=("Roboto", 14))
        info.pack(pady=10)

        btn_load = ctk.CTkButton(self.main_frame, text="Charger calendrier", command=self.load_calendar)
        btn_load.pack(pady=10)

    def load_calendar(self):
        try:
            with open("calendrier.ics", "r", encoding="utf-8") as f:
                content = f.read()
                # TODO : gérer les fichiers multiples si nécessaire avec parse_multiple()
            messagebox.showinfo("Calendrier chargé", f"Fichier lu avec succès ({len(content)} caractères)")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire le fichier : {e}")

    # ==== MODULE SCRAPING ====
    def show_scraping(self):
        self._clear_main_frame()
        label = ctk.CTkLabel(self.main_frame, text="Scraping produits en ligne", font=("Roboto Bold", 20))
        label.pack(pady=20)

        btn_scrape = ctk.CTkButton(self.main_frame, text="Lancer le scraping", command=self.run_scraping)
        btn_scrape.pack(pady=10)

        self.scrape_output = ctk.CTkTextbox(self.main_frame, width=800, height=400)
        self.scrape_output.pack(pady=10)

    def run_scraping(self):
        def task():
            self.scrape_output.delete("1.0", "end")
            self.scrape_output.insert("end", "Chargement...\n")

            # Exemple : scraping fictif sur une URL
            url = "https://books.toscrape.com/"
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                books = soup.find_all("article", class_="product_pod")

                for b in books[:10]:
                    title = b.h3.a["title"]
                    price = b.find("p", class_="price_color").text
                    stock = b.find("p", class_="instock availability").text.strip()

                    self.scrape_output.insert("end", f"📗 {title}\n💰 {price}\n📦 {stock}\n\n")
            except Exception as e:
                self.scrape_output.insert("end", f"❌ Erreur : {e}\n")

        threading.Thread(target=task).start()

    # ==== OUTILS ====
    def _clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()


# ==== LANCEMENT ====
if __name__ == "__main__":
    app = App()
    app.mainloop()
