# app.py

import streamlit as st
from datetime import datetime
import threading
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from cryptography.fernet import Fernet

# -------------------------------
# 1️⃣ Barre supérieure avec ton nom et horloge dynamique
# -------------------------------

# Créer un placeholder pour afficher l'horloge
clock_placeholder = st.empty()

# Fonction qui met à jour l'horloge toutes les secondes
def update_clock():
    while True:
        now = datetime.now().strftime("%H:%M:%S")  # Format HH:MM:SS
        clock_placeholder.markdown(
            f"<h3 style='color:white;'>{now}</h3>", unsafe_allow_html=True
        )
        time.sleep(1)  # Met à jour toutes les secondes

# Barre supérieure HTML/CSS
st.markdown(
    """
    <div style="display:flex; justify-content:space-between; align-items:center; 
                background-color:#4CAF50; padding:10px; border-radius:5px;">
        <h2 style="color:white;">Guillaume Saucy - Dashboard Webscraping</h2>
        <div id='clock'></div>
    </div>
    """,
    unsafe_allow_html=True
)

# Lancer l’horloge dans un thread séparé
thread = threading.Thread(target=update_clock, daemon=True)
thread.start()

st.write("## Bienvenue sur le dashboard !")

# -------------------------------
# 2️⃣ Section de connexion Carlo Erba
# -------------------------------

st.write("### Connexion Carlo Erba")

# Entrée email et mot de passe
email = st.text_input("Email")
password = st.text_input("Mot de passe", type="password")

# Case à cocher pour se souvenir des identifiants
remember = st.checkbox("Se souvenir de moi")

# -------------------------------
# 3️⃣ Sélection des références à scraper
# -------------------------------

st.write("### Sélection des références")

# Option Excel, manuel ou les deux
search_option = st.radio(
    "Mode de recherche",
    ('Excel', 'Manuel', 'Excel + Manuel')
)

# Sélection fichier Excel si option choisie
excel_path = None
if search_option in ['Excel', 'Excel + Manuel']:
    excel_path = st.file_uploader("Choisir un fichier Excel", type=['xlsx', 'xls'])

# Entrée manuelle de références
manual_references = st.text_input("Références manuelles (séparées par une virgule)")

# -------------------------------
# 4️⃣ Fonction de scraping Carlo Erba
# -------------------------------

def carloerba_scraper(email, password, excel_path, manual_references, search_option):
    """Fonction principale de scraping Carlo Erba"""
    if not email or not password:
        st.warning("⚠️ Veuillez entrer vos identifiants.")
        return None

    # Créer session persistante
    session = requests.Session()

    # Étape 1 : Récupérer CSRF token
    login_page_url = "https://www.carloerbareagents.com/cerstorefront/cer-fr/login"
    resp = session.get(login_page_url)
    soup = BeautifulSoup(resp.text, "lxml")
    csrf_token = soup.find("input", {"name": "CSRFToken"})["value"]

    st.info(f"🔑 CSRFToken récupéré : {csrf_token}")

    # Étape 2 : Connexion
    payload = {
        "j_username": email,
        "j_password": password,
        "CSRFToken": csrf_token
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": login_page_url,
        "Origin": "https://www.carloerbareagents.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    login_url = "https://www.carloerbareagents.com/cerstorefront/cer-fr/j_spring_security_check"
    response = session.post(login_url, data=payload, headers=headers, allow_redirects=False)

    if response.status_code != 302:
        st.error("❌ Connexion échouée.")
        return None
    st.success("✅ Connexion réussie.")

    # -------------------------------
    # 3️⃣ Récupérer les références selon l’option choisie
    # -------------------------------

    references = []

    if search_option in ['Excel', 'Excel + Manuel'] and excel_path is not None:
        df_refs = pd.read_excel(excel_path)
        references.extend(df_refs['Référence'].dropna().astype(str).tolist())

    if search_option in ['Manuel', 'Excel + Manuel'] and manual_references:
        references.extend([ref.strip() for ref in manual_references.split(',')])

    if not references:
        st.warning("⚠️ Aucune référence à rechercher.")
        return None

    # -------------------------------
    # 4️⃣ Scraping des produits
    # -------------------------------

    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(references)
    for idx, ref in enumerate(references):
        status_text.text(f"🔍 Recherche de la référence : {ref} ({idx+1}/{total})")
        search_url = f"https://www.carloerbareagents.com/cerstorefront/cer-fr/search/?text={ref}"
        resp = session.get(search_url)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            products = soup.find_all('tr', class_='quickAddToCart')

            if not products:
                st.warning(f"❌ Aucun produit trouvé pour : {ref}")
                continue

            for product in products:
                try:
                    product_name = product.find('input', {'name': 'productNamePost'}).get('value')
                    conditionnement = product.find('td', class_='item__info--variantDescription').text.strip()
                    tds = product.find_all('td')
                    emballage = tds[2].text.strip() if len(tds) > 2 else ""
                    unite_vente = tds[3].text.strip() if len(tds) > 3 else ""
                    quantite_input = product.find('input', {'name': 'initialQuantityVariant'})
                    quantite = quantite_input.get('value') if quantite_input else ""
                    price = product.find('input', {'name': 'productPostPrice'}).get('value')
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

                    # Ajouter les données
                    data.append({
                        'Référence cherchée': ref,
                        'Produit': product_name,
                        'Cdt': conditionnement,
                        'Emballage': emballage,
                        'Unité de vente': unite_vente,
                        'Qté': quantite,
                        'Prix €': price,
                        'Disponibilité': disponibilite
                    })

                except Exception as e:
                    st.error(f"⚠️ Erreur pour {ref} : {e}")
                    continue

        else:
            st.error(f"❗ Erreur HTTP pour : {ref} (code {resp.status_code})")

        # Mise à jour barre de progression
        progress_bar.progress((idx + 1) / total)

    # -------------------------------
    # 5️⃣ Affichage des résultats
    # -------------------------------

    if data:
        df_resultats = pd.DataFrame(data)
        st.success("✅ Scraping terminé !")
        # Affichage avec couleurs selon disponibilité
        def color_availability(val):
            if val == "En stock":
                return 'background-color: lightgreen'
            elif val.startswith("Disponible"):
                return 'background-color: lightyellow'
            else:
                return 'background-color: lightcoral'

        st.dataframe(df_resultats.style.applymap(color_availability, subset=['Disponibilité']))

        # Export Excel automatique
        output_file = "resultats_scraping.xlsx"
        df_resultats.to_excel(output_file, index=False)
        st.info(f"Données enregistrées dans : {output_file}")
    else:
        st.warning("⚠️ Aucun produit trouvé.")

# -------------------------------
# 5️⃣ Bouton de lancement
# -------------------------------
if st.button("Lancer le scraping"):
    carloerba_scraper(email, password, excel_path, manual_references, search_option)
