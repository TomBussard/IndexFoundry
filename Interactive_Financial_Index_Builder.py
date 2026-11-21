from index_math import construct_index

import streamlit as st
import pandas as pd
import os
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import smtplib
from io import BytesIO
import zipfile
import urllib.parse
import shutil
import requests

# Titre de l'application
st.title("📊 Analyse et Création Interactive d'Indices Financiers")

# Explication introductive
st.markdown("""
Bienvenue dans cette application interactive dédiée à l'analyse et à la création d'indices financiers.  
Vous pourrez explorer, filtrer, et construire des indices basés sur des entreprises américaines (**SPX**) et européennes (**SXXP**) par **secteurs** et **sous-secteurs**.

### Objectifs :
1. **Analyse sectorielle** : Identifiez les entreprises pertinentes dans le secteur de votre choix.
2. **Création d'indices** : Construisez et visualisez des indices sectoriels adaptés à vos critères.
3. **Comparaison avec benchmarks** : Évaluez les performances des indices en les comparant à des benchmarks globaux comme SPX et SXXP.

Grâce à cette plateforme, vous pourrez également explorer des indices basés sur des styles d'investissement spécifiques (Momentum, Solidité Financière) pour mieux comprendre les dynamiques de marché.

**👉 Commencez dès maintenant en sélectionnant un secteur à analyser via le panneau latéral.**
""")

# Chargement des données avec mise en cache

@st.cache_data
def charger_donnees():
    url = "https://www.dropbox.com/scl/fi/aazc2gnzofqjee5fsc9sm/Data-projet-indices-python.xlsx?rlkey=6vyz3mbazfqx4c665ud6mnesj&st=9vzw1bf8&dl=1"
    local_path = "Data projet indices python.xlsx"

    if not os.path.exists(local_path):
        r = requests.get(url)
        with open(local_path, 'wb') as f:
            f.write(r.content)

    index_data = pd.read_excel(local_path, sheet_name='Index', engine='openpyxl')
    forex_data = pd.read_excel(local_path, sheet_name="Forex", engine='openpyxl')
    members_data = pd.read_excel(local_path, sheet_name='Members', engine='openpyxl')
    spx_prices = pd.read_excel(local_path, sheet_name='SPX_PX_LAST', engine='openpyxl')
    sxxp_prices = pd.read_excel(local_path, sheet_name='SXXP_PX_LAST', engine='openpyxl')
    qualitativ_2018 = pd.read_excel(local_path, sheet_name="Qualitativ_2018", engine='openpyxl')
    qualitativ_2019 = pd.read_excel(local_path, sheet_name="Qualitativ_2019", engine='openpyxl')
    qualitativ_2020 = pd.read_excel(local_path, sheet_name="Qualitativ_2020", engine='openpyxl')

    return {
        'index_data': index_data,
        'forex_data': forex_data,
        'members_data': members_data,
        'spx_prices': spx_prices,
        'sxxp_prices': sxxp_prices,
        'qualitativ_2018': qualitativ_2018,
        'qualitativ_2019': qualitativ_2019,
        'qualitativ_2020': qualitativ_2020,
    }

donnees = charger_donnees()


def dataframe_to_image(df, filename, decimals=2):
    """
    Convertit un DataFrame en image PNG et l'enregistre avec le nom spécifié.

    Args:
        df (pd.DataFrame): Le DataFrame à convertir.
        filename (str): Le chemin du fichier PNG de sortie.
        decimals (int): Nombre de décimales pour arrondir les valeurs numériques.
    """
    # Arrondir les valeurs numériques
    df_rounded = df.round(decimals)

    # Création de l'image
    fig, ax = plt.subplots(figsize=(min(15, 5 + 0.5 * len(df_rounded.columns)), 0.5 * len(df_rounded) + 1))
    ax.axis('off')  # Pas d'axes
    ax.axis('tight')
    table = ax.table(cellText=df_rounded.values, colLabels=df_rounded.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(df_rounded.columns))))  # Ajuste la largeur des colonnes

    plt.savefig(filename, format='png', bbox_inches='tight')
    plt.close(fig)


# Fonction pour sauvegarder un graphique en PNG
def save_figure(fig, filename):
    """
    Enregistre un graphique en PNG avec le nom spécifié.
    """
    temp_dir = "temp_reports"
    os.makedirs(temp_dir, exist_ok=True)
    filepath = os.path.join(temp_dir, filename)
    fig.savefig(filepath, format="png", bbox_inches="tight")
    plt.close(fig)

# Fonction pour sauvegarder un fichier ZIP avec tous les résultats
def create_zip():
    """
    Crée un fichier ZIP contenant tous les fichiers enregistrés dans le répertoire temporaire.
    """
    temp_dir = "temp_reports"
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                zf.write(os.path.join(root, file), arcname=file)
    return zip_buffer

# Nettoyer le dossier temporaire au démarrage
def clear_temp_folder(temp_dir="temp_reports"):
    """
    Supprime le contenu du dossier temporaire s'il existe.
    """
    if os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                try:
                    os.unlink(os.path.join(root, file))  # Supprime les fichiers
                except PermissionError:
                    print(f"Impossible de supprimer le fichier : {file}. Il est en cours d'utilisation.")
        shutil.rmtree(temp_dir, ignore_errors=True)  # Supprime le dossier
    os.makedirs(temp_dir, exist_ok=True)  # Recrée un dossier vide

# Appel de la fonction au démarrage
clear_temp_folder()

# Section Indice Sectoriel
st.title("📈 Création d'un Indice Sectoriel")

st.markdown("""
Les indices sectoriels sont des outils essentiels pour analyser les performances des entreprises appartenant à des secteurs économiques spécifiques.  
Ils permettent d’évaluer les dynamiques sectorielles, d’identifier les tendances clés et de mieux comprendre les moteurs de performance des marchés financiers.

### Objectif de cette analyse
Dans cette section, nous allons construire un **indice sectoriel** en filtrant et pondérant les entreprises américaines (**SPX**) et européennes (**SXXP**) d’un secteur choisi.  
Cet indice permettra de :
1. Analyser la performance des entreprises au sein d’un secteur spécifique.
2. Comparer les dynamiques sectorielles entre les marchés américains et européens.
3. Créer une base d’étude pour des stratégies d’investissement spécifiques.

### Méthodologie
1. **Filtrage par secteur** : 
   - Sélection des entreprises basées sur des secteurs et sous-secteurs définis.  
   - Analyse des entreprises disponibles dans les indices SPX et SXXP.
2. **Traitement des données** :
   - Nettoyage et préparation des données historiques de prix pour garantir leur qualité et leur cohérence.
   - Conversion des données européennes (SXXP) en USD pour assurer une base de comparaison homogène.
3. **Pondération par capitalisation boursière** : 
   - Les entreprises sélectionnées sont pondérées en fonction de leur capitalisation boursière, reflétant leur poids relatif dans le secteur.
4. **Création de l'indice** :
   - Les prix des entreprises sont normalisés sur une base de 100 pour faciliter la comparaison.  
   - Une série temporelle est construite pour représenter l’évolution de l’indice sectoriel au fil du temps.
5. **Benchmarking** :
   - L’indice sectoriel sera comparé à des benchmarks globaux comme le SPX (marché américain) et le SXXP (marché européen en USD).

### Pourquoi un indice sectoriel ?
Les indices sectoriels permettent de mieux comprendre les performances d’un secteur donné, en mettant en évidence :
- Les secteurs moteurs de la croissance économique.
- Les impacts de facteurs macroéconomiques ou géopolitiques sur des secteurs spécifiques.
- Les opportunités d’investissement à l’intérieur d’un secteur particulier.

### Résultat attendu
L’indice sectoriel ainsi construit nous permettra de visualiser :
- L'évolution des performances d’un secteur donné sur une période spécifique.
- Une comparaison avec les benchmarks pour évaluer les performances relatives des entreprises du secteur.
- Une base solide pour des analyses plus approfondies, comme le rebalancement d’indice ou l’identification de sous-secteurs porteurs.

### Suivez les étapes interactives
- Commencez par sélectionner un **secteur** et des **sous-secteurs** via le panneau latéral.
- Explorez les données des entreprises disponibles.
- Construisez et visualisez l’indice sectoriel pour analyser ses performances.
""")

# Gestion des données manquantes ou erreurs
if 'members_data' not in donnees or donnees['members_data'] is None:
    st.error("Les données 'Members' ne sont pas disponibles. Vérifiez le fichier Excel.")
    st.stop()

members_data = donnees['members_data']
spx_prices = donnees.get('spx_prices', None)
sxxp_prices = donnees.get('sxxp_prices', None)

if spx_prices is None or sxxp_prices is None:
    st.error("Les données de prix pour SPX ou SXXP ne sont pas disponibles. Vérifiez le fichier Excel.")
    st.stop()

# Liste unique des secteurs disponibles
secteurs_disponibles = members_data['BICS_LEVEL_1_SECTOR_NAME'].dropna().unique()

# Sélection du secteur par l'utilisateur
st.sidebar.header("🔍 Filtrer par secteur")
secteur_choisi = st.sidebar.selectbox("Choisissez un secteur :", options=secteurs_disponibles)

# Filtrer les entreprises par secteur choisi
entreprises_filtrees = members_data[members_data['BICS_LEVEL_1_SECTOR_NAME'] == secteur_choisi]

# Liste unique des sous-secteurs disponibles pour le secteur choisi
sous_secteurs_disponibles = entreprises_filtrees['SPX_BICS_LEVEL_4_SUB_INDUSTRY_NAME'].dropna().unique()

# Sélection des sous-secteurs
sous_secteurs_choisis = st.sidebar.multiselect("Sélectionnez les sous-secteurs :", options=sous_secteurs_disponibles)

# Filtrer les entreprises par sous-secteurs choisis
if sous_secteurs_choisis:
    entreprises_filtrees = entreprises_filtrees[
        entreprises_filtrees['SPX_BICS_LEVEL_4_SUB_INDUSTRY_NAME'].isin(sous_secteurs_choisis)
    ]

# Afficher les résultats filtrés
st.subheader(f"📊 Entreprises filtrées pour le secteur '{secteur_choisi}'")
st.write("**Entreprises sélectionnées :**")
st.dataframe(entreprises_filtrees)

# Affichage des tickers uniques pour SPX et SXXP
spx_tickers = entreprises_filtrees['SPX Index'].dropna().unique()
sxxp_tickers = entreprises_filtrees['SXXP Index'].dropna().unique()

st.write("**Tickers américains (SPX) :**", spx_tickers)
st.write("**Tickers européens (SXXP) :**", sxxp_tickers)

# Fonction pour filtrer les prix
def filter_prices(sheet_prices, tickers, start_date, end_date, max_consecutive_nans=10, min_valid_ratio=0.5, verbose=False):
    """
    Filtre les prix pour les tickers donnés et dans une plage de dates spécifiée.
    Inclut uniquement les colonnes qui respectent les critères :
    - Proportion minimale de données valides.
    - Nombre maximal de NaN consécutifs.
    """
    sheet_prices['Dates'] = pd.to_datetime(sheet_prices['Dates'])

    # Filtrer par plage de dates
    filtered_prices = sheet_prices[
        (sheet_prices['Dates'] >= pd.to_datetime(start_date)) & 
        (sheet_prices['Dates'] <= pd.to_datetime(end_date))
    ].copy()

    columns = ['Dates']  # Colonne Dates incluse
    excluded_tickers = []  # Liste des tickers exclus

    for ticker in tickers:
        if ticker in filtered_prices.columns:
            # Vérifier la proportion de données valides
            valid_data_ratio = filtered_prices[ticker].notna().sum() / len(filtered_prices[ticker])

            # Exclure les tickers avec trop peu de données valides
            if valid_data_ratio < min_valid_ratio:
                excluded_tickers.append((ticker, f"Moins de {min_valid_ratio * 100}% de données valides"))
                if verbose:
                    st.write(f"❌ {ticker} exclu - Raison : Moins de {min_valid_ratio * 100}% de données valides")
                continue

            # Vérifier les NaN consécutifs
            nan_count = filtered_prices[ticker].isna().astype(int).rolling(window=max_consecutive_nans).sum()
            if (nan_count >= max_consecutive_nans).any():
                excluded_tickers.append((ticker, f"Plus de {max_consecutive_nans} NaN consécutifs"))
                if verbose:
                    st.write(f"❌ {ticker} exclu - Raison : Plus de {max_consecutive_nans} NaN consécutifs")
                continue

            # Ajoute le ticker s'il respecte les critères
            columns.append(ticker)

    # Filtrer les colonnes valides
    filtered_prices = filtered_prices[columns]

    # Remplir les NaN restants par des valeurs connues (forward et backward fill)
    filtered_prices = filtered_prices.fillna(method='ffill').fillna(method='bfill')

    if verbose:
        st.write(f"✅ Nombre d'entreprises incluses : {len(columns) - 1}")
        st.write(f"❌ Tickers exclus ({len(excluded_tickers)}) : {excluded_tickers}")

    return filtered_prices, excluded_tickers

# Sélection des dates interactives
st.subheader("📈 Construction de l'indice sur la base des prix")

start_date = st.date_input("Date de début", value=pd.to_datetime('2010-04-01'), key="start_date")
end_date = st.date_input("Date de fin", value=pd.to_datetime('2018-12-28'), key="end_date")


# Application de la fonction pour SPX
spx_energy_prices, spx_excluded = filter_prices(spx_prices, spx_tickers, start_date, end_date)
sxxp_energy_prices, sxxp_excluded = filter_prices(sxxp_prices, sxxp_tickers, start_date, end_date)

# Affichage des résultats pour SPX
st.subheader("Prix filtrés pour SPX")
with st.expander("Afficher les colonnes exclues pour SPX"):
    st.write("**Colonnes exclues pour SPX :**", spx_excluded)
with st.expander("Afficher les prix filtrés pour SPX"):
    st.dataframe(spx_energy_prices)

# Affichage des résultats pour SXXP
st.subheader("Prix filtrés pour SXXP")
with st.expander("Afficher les colonnes exclues pour SXXP"):
    st.write("**Colonnes exclues pour SXXP :**", sxxp_excluded)
with st.expander("Afficher les prix filtrés pour SXXP"):
    st.dataframe(sxxp_energy_prices)


# Fonction pour convertir les prix SXXP en dollars
def convert_usd(index_prices, forex_data):
    """
    Convertit les prix SXXP en dollars en utilisant le taux de change EUR/USD correspondant à chaque date.
    """
    # Formatage des dates
    index_prices['Dates'] = pd.to_datetime(index_prices['Dates'])
    forex_data['Dates'] = pd.to_datetime(forex_data['Dates'])

    # Fusion à gauche sur les dates
    merged_data = pd.merge(index_prices, forex_data[['Dates', 'EURUSD']], on='Dates', how='left')

    # Vérification des taux de change manquants
    if merged_data['EURUSD'].isna().any():
        st.warning("Certaines dates n'ont pas de taux de change correspondant.")

    # Conversion des prix
    numeric_cols = merged_data.select_dtypes(include='number').columns.drop('EURUSD')
    for col in numeric_cols:
        merged_data[col] = merged_data[col] * merged_data['EURUSD']

    # Suppression de la colonne EURUSD
    merged_data.drop(columns=['EURUSD'], inplace=True)

    return merged_data

# Fonction pour fusionner les prix SPX et SXXP
def merge_dates(spx_prices, sxxp_prices):
    """
    Fusionne deux DataFrames sur les dates communes.
    """
    # Formatage des dates
    spx_prices['Dates'] = pd.to_datetime(spx_prices['Dates'])
    sxxp_prices['Dates'] = pd.to_datetime(sxxp_prices['Dates'])

    # Fusion sur les dates
    merged_data_frame = pd.merge(spx_prices, sxxp_prices, on="Dates", how="inner")

    return merged_data_frame

# Conversion des prix SXXP en dollars
st.subheader("💵 Conversion des prix SXXP en dollars")
forex_data = donnees['forex_data']
sxxp_energy_prices_usd = convert_usd(sxxp_energy_prices, forex_data)
st.write("**Prix SXXP convertis en dollars :**")
st.dataframe(sxxp_energy_prices_usd)

# Fusion des données pour créer l'indice
st.subheader("📊 Fusion des prix SPX et SXXP pour l'indice")
index_energy_prices = merge_dates(spx_energy_prices, sxxp_energy_prices_usd)
st.write(f"**Données fusionnées de l'indice '{secteur_choisi}' :**")
st.dataframe(index_energy_prices)

st.subheader("💱 Conversion des prix en d'autres devises")
st.markdown("""
Nous allons créer une fonction interactive qui permet de convertir un DataFrame des prix en dollars 
dans d'autres devises rapidement. Vous pourrez choisir la devise cible grâce à une liste interactive.
""")

# Fonction pour convertir les prix en dollars dans une autre devise
def convert_usd_currency(prices_df, forex_data):
    """
    Convertit les prix en dollars dans une devise choisie.
    prices_df: DataFrame contenant les prix, avec une première colonne 'Dates' et les colonnes suivantes pour les prix en USD.
    """
    prices_df['Dates'] = pd.to_datetime(prices_df['Dates'])
    forex_data['Dates'] = pd.to_datetime(forex_data['Dates'])

    # Dictionnaire des devises et leurs colonnes de taux de change
    currency_options = {
        'GBP': 'USDGBP',
        'JPY': 'USDJPY',
        'CNY': 'USDCNY',
        'CAD': 'USDCAD',
        'EUR': 'EURUSD'
    }

    def convert(target_currency):
        """
        Sous-fonction pour effectuer la conversion selon la devise sélectionnée.
        """
        if target_currency not in currency_options:
            raise ValueError(f"Devise cible '{target_currency}' non supportée. Choisissez parmi {list(currency_options.keys())}.")

        rate_column = currency_options[target_currency]

        # Vérification de la disponibilité du taux de change
        if rate_column not in forex_data.columns:
            raise ValueError(f"La colonne '{rate_column}' est absente de forex_data.")

        # Fusion avec les taux de change
        merged_data = pd.merge(prices_df, forex_data[['Dates', rate_column]], on='Dates', how='left')

        # Vérification des données manquantes
        if merged_data[rate_column].isna().any():
            st.warning(f"Certaines dates n'ont pas de taux de change pour '{rate_column}'.")

        # Conversion des prix
        for col in merged_data.columns[1:-1]:  # Exclure 'Dates' et 'rate_column'
            if target_currency == 'EUR':  # Conversion USD -> EUR
                merged_data[col] = merged_data[col] / merged_data[rate_column]
            else:  # Conversion USD -> Autres devises
                merged_data[col] = merged_data[col] * merged_data[rate_column]

        # Suppression de la colonne des taux de change
        merged_data.drop(columns=[rate_column], inplace=True)

        return merged_data

    # Liste interactive
    target_currency = st.selectbox("Sélectionnez une devise cible :", list(currency_options.keys()))
    converted_df = convert(target_currency)
    st.write(f"**Conversion effectuée vers la devise : {target_currency}**")
    st.dataframe(converted_df)

    return converted_df

# Application de la conversion
forex_data = donnees['forex_data']
converted_prices = convert_usd_currency(index_energy_prices, forex_data)

# Explication pour normalisation
st.subheader("📏 Normalisation des prix")
st.markdown("""
En continuant avec les prix en dollars, nous allons créer une fonction réutilisable 
pour normaliser les prix des titres sur la période.
""")

# Fonction pour normaliser les prix
def normalize_prices(dataframe):
    """
    Normalise les colonnes d'un DataFrame 
    en divisant chaque valeur par la première valeur non NaN de la colonne.
    """
    normalize_df = dataframe.copy()
    for col in normalize_df.columns:
        if col != 'Dates':
            first_value = normalize_df[col].dropna().iloc[0]
            normalize_df[col] = normalize_df[col] / first_value
    return normalize_df

# Application de la normalisation
normalized_prices = normalize_prices(index_energy_prices)
st.write("**Données normalisées :**")
st.dataframe(normalized_prices)

# Explication de la pondération
st.subheader("📊 Calcul des pondérations basées sur la capitalisation boursière")
st.markdown("""
Nous allons associer la capitalisation boursière des entreprises de notre indice avec les données qualitatives 
(**Qualitativ_2018**). Ensuite, nous calculons les pondérations en fonction des capitalisations pour les entreprises présentes.
""")

# Fonction pour calculer les pondérations
def market_cap_weights(index_prices, qualitativ_data):
    """
    Associe la capitalisation boursière des entreprises avec les données qualitatives 
    et calcule les pondérations en fonction des capitalisations.
    """
    qualitativ_data['Ticker'] = qualitativ_data.iloc[:, 0]  # La première colonne correspond aux tickers
    tickers = index_prices.columns[1:]  # Exclue la colonne 'Dates'
    filtered_qualitativ = qualitativ_data[qualitativ_data['Ticker'].isin(tickers)]
    merged_data = filtered_qualitativ[['Ticker', 'CUR_MKT_CAP']].copy()

    # Calcul des pondérations
    merged_data['Weight'] = merged_data['CUR_MKT_CAP'] / merged_data['CUR_MKT_CAP'].sum()

    return merged_data[['Ticker', 'Weight']]

# Application de la fonction pour les pondérations
qualitativ_2018 = donnees['qualitativ_2018']
qualitativ_2019 = donnees['qualitativ_2019']
marketcap_weights = market_cap_weights(index_energy_prices, qualitativ_2018)
st.write("**Pondérations basées sur la capitalisation boursière :**")
st.dataframe(marketcap_weights)

# Explication de la construction de l'indice
st.subheader("⚙️ Construction de l'indice sectoriel")
st.markdown("""
Nous allons maintenant construire un indice sectoriel en combinant les prix normalisés des entreprises 
avec les pondérations calculées précédemment.
""")

# Application de la fonction pour construire l'indice
index_energy = construct_index(index_energy_prices, marketcap_weights)
st.write(f"**Indice sectoriel {secteur_choisi.lower()} construit :**")
st.dataframe(index_energy)

# Chargement des données nécessaires 
index_data = donnees['index_data']  # Feuille "Index"
forex_data = donnees['forex_data']  # Feuille "Forex"

# Fonction pour préparer les benchmarks 
def prepare_reference_index(index_data, column_name, date_column="PX_LAST"):
    """
    Prépare un indice de référence en sélectionnant les colonnes nécessaires,
    convertissant les dates et les valeurs.
    """
    if date_column in index_data.columns and column_name in index_data.columns:
        reference_index = index_data[[date_column, column_name]].rename(
            columns={date_column: "Dates", column_name: "Index_Value"}
        )
        reference_index['Dates'] = pd.to_datetime(reference_index['Dates'], format='%d/%m/%Y', errors='coerce')
        reference_index.dropna(subset=['Dates', 'Index_Value'], inplace=True)
        reference_index['Index_Value'] = reference_index['Index_Value'].replace(',', '.', regex=True).astype(float)
        return reference_index
    else:
        raise ValueError(f"Les colonnes '{date_column}' et/ou '{column_name}' sont absentes.")

# Prépare les benchmarks 
spx_index = prepare_reference_index(index_data, "SPX Index")  # Benchmark SPX
sxxp_index = prepare_reference_index(index_data, "SXXP Index")  # Benchmark SXXP

# Convertie et normalise le benchmark SXXP en USD
sxxp_index_usd = convert_usd(sxxp_index, forex_data)  # Conversion en USD

# Fusionne les benchmarks avec l'indice sectoriel 
index_with_benchmarks = pd.merge(index_energy, spx_index, on='Dates', how='inner', suffixes=('', '_SPX'))
index_with_benchmarks = pd.merge(index_with_benchmarks, sxxp_index_usd, on='Dates', how='inner', suffixes=('', '_SXXP'))

# Fonction pour ajuster la première valeur à 100
def adjust_to_base_100(df, columns):
    """
    Ajuste les colonnes spécifiées d'un DataFrame pour commencer exactement à 100.
    """
    adjusted_df = df.copy()
    for col in columns:
        first_value = adjusted_df[col].iloc[0]
        adjusted_df[col] = (adjusted_df[col] / first_value) * 100
    return adjusted_df

# Ajuste les colonnes de l'indice et des benchmarks
columns_to_adjust = ['Index_Value', 'Index_Value_SPX', 'Index_Value_SXXP']
index_with_benchmarks = adjust_to_base_100(index_with_benchmarks, columns_to_adjust)

# Visualisation
st.subheader(f"📈 Indice sectoriel '{secteur_choisi.lower()}' avec Benchmarks")
fig, ax = plt.subplots(figsize=(12, 6))

# Trace l'indice sectoriel
ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value'], label=f"Indice Sectoriel '{secteur_choisi}'", linewidth=2, color="blue")

# Trace le benchmark SPX
ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value_SPX'], label="Benchmark SPX", linestyle="--", color="orange")

# Trace le benchmark SXXP
ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value_SXXP'], label="Benchmark SXXP (en USD)", linestyle=":", color="green")

# Configurations du graphique
ax.set_title(f"Indice Sectoriel '{secteur_choisi}' avec Benchmarks (Normalisés à 100)", fontsize=16)
ax.set_xlabel("Dates", fontsize=12)
ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
ax.legend(fontsize=12)
ax.grid(True, linestyle='--', alpha=0.6)

# Sauvegarde automatique dans le répertoire temporaire
save_figure(fig, f"indice_sectoriel_{secteur_choisi.lower().replace(' ', '_')}_avec_benchmark.png")

# Affiche le graphique
st.pyplot(fig)

# Fonction pour construire un indice par pays
def construct_index_pays(prices, weights, qualitativ_data):
    """
    Construit un indice sectoriel en fonction des pays sélectionnés dans une interface interactive.
    """
    ticker_column = weights.columns[0]

    # Liste des options de pays
    country_options = ['All'] + qualitativ_data['COUNTRY'].dropna().unique().tolist()

    # Sélection multiple interactive des pays
    selected_countries = st.multiselect(
        "Sélectionnez les pays pour filtrer l'indice :",
        options=country_options,
        default=['All']
    )

    # Filtrage des pays
    if 'All' in selected_countries:
        filtered_weights = weights
    else:
        ticker_countries = qualitativ_data[[qualitativ_data.columns[0], 'COUNTRY']]
        filtered_weights = pd.merge(
            weights,
            ticker_countries,
            left_on=ticker_column,
            right_on=qualitativ_data.columns[0],
            how='inner'
        )
        filtered_weights = filtered_weights[filtered_weights['COUNTRY'].isin(selected_countries)]

    # Vérification des données après filtrage
    if filtered_weights.empty:
        st.warning("Aucun ticker ne correspond aux pays sélectionnés.")
        return pd.DataFrame({'Dates': [], 'Index_Value': []})  # DataFrame vide

    # Fusion des pondérations avec les prix
    merged_data = pd.melt(prices, id_vars=['Dates'], var_name='Ticker', value_name='Price')
    merged_data = pd.merge(merged_data, filtered_weights, left_on='Ticker', right_on=ticker_column, how='inner')

    # Calcul des prix pondérés
    merged_data['Weighted_Price'] = merged_data['Price'] * merged_data[weights.columns[1]]

    # Calcul de la somme pondérée pour chaque date
    index = merged_data.groupby('Dates')['Weighted_Price'].sum().reset_index()

    # Renommer et normaliser l'indice
    index.rename(columns={'Weighted_Price': 'Index_Value'}, inplace=True)
    index['Index_Value'] = (index['Index_Value'] / index['Index_Value'].iloc[0]) * 100

    return index, selected_countries

# Application de la fonction
st.subheader("🌍 Construction d'un indice sectoriel par pays")
st.markdown("""
Nous allons maintenant construire un indice sectoriel basé sur les prix des entreprises et les pondérations
attribuées, tout en permettant une sélection dynamique des pays.
""")

# Application interactive de la sélection des pays
index_energy_pays, selected_countries = construct_index_pays(index_energy_prices, marketcap_weights, qualitativ_2018)

# Affichage du DataFrame résultant
if not index_energy_pays.empty:
    st.write("**Indice sectoriel filtré par pays :**")
    st.dataframe(index_energy_pays)

    # Réajuste les benchmarks SPX et SXXP pour commencer exactement à 100
    spx_index_normalized = adjust_to_base_100(spx_index, ['Index_Value'])
    sxxp_index_usd_normalized = adjust_to_base_100(sxxp_index_usd, ['Index_Value'])

    # Fusionne les benchmarks normalisés avec l'indice sectoriel par pays
    index_with_benchmarks_pays = pd.merge(
        index_energy_pays, spx_index_normalized, on='Dates', how='inner', suffixes=('', '_SPX')
    )
    index_with_benchmarks_pays = pd.merge(
        index_with_benchmarks_pays, sxxp_index_usd_normalized, on='Dates', how='inner', suffixes=('', '_SXXP')
    )

    # Réajuste l'indice sectoriel par pays pour commencer à 100
    index_with_benchmarks_pays = adjust_to_base_100(
        index_with_benchmarks_pays, ['Index_Value', 'Index_Value_SPX', 'Index_Value_SXXP']
    )

    # Visualisation 
    st.subheader(f"📈 Indice sectoriel '{secteur_choisi}' par Pays avec Benchmarks")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Trace l'indice sectoriel par pays
    ax.plot(
        index_with_benchmarks_pays['Dates'],
        index_with_benchmarks_pays['Index_Value'],
        label=f"Indice Sectoriel '{secteur_choisi}' par Pays",
        linewidth=2,
        color="blue",
    )


    # Trace le benchmark SPX
    ax.plot(
        index_with_benchmarks_pays['Dates'],
        index_with_benchmarks_pays['Index_Value_SPX'],
        label="Benchmark SPX",
        linestyle="--",
        color="orange",
    )

    # Trace le benchmark SXXP
    ax.plot(
        index_with_benchmarks_pays['Dates'],
        index_with_benchmarks_pays['Index_Value_SXXP'],
        label="Benchmark SXXP (en USD)",
        linestyle=":",
        color="green",
    )

    # Configurations du graphique
    ax.set_title(f"Indice Sectoriel '{secteur_choisi}' par Pays avec Benchmarks (Normalisés à 100)", fontsize=16)
    ax.set_xlabel("Dates", fontsize=12)
    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)

    save_figure(fig, f"indice_sectoriel_{secteur_choisi.lower().replace(' ', '_')}_par_pays_avec_benchmarks.png")

    # Affiche le graphique 
    st.pyplot(fig)
else:
    st.warning("L'indice sectoriel par pays est vide. Veuillez vérifier les sélections.")

def prepare_reference_index(index_data, column_name, date_column="PX_LAST"):
    """
    Prépare un indice de référence en sélectionnant les colonnes nécessaires,
    convertissant les dates et les valeurs, et normalisant les données.
    """
    if date_column in index_data.columns and column_name in index_data.columns:
        reference_index = index_data[[date_column, column_name]].rename(
            columns={date_column: "Dates", column_name: "Index_Value"}
        )
        reference_index['Dates'] = pd.to_datetime(reference_index['Dates'], format='%d/%m/%Y', errors='coerce')
        reference_index.dropna(subset=['Dates', 'Index_Value'], inplace=True)
        reference_index['Index_Value'] = reference_index['Index_Value'].replace(',', '.', regex=True).astype(float)
        reference_index['Index_Value'] = (reference_index['Index_Value'] / reference_index['Index_Value'].iloc[0]) * 100
        return reference_index
    else:
        st.error(f"Les colonnes '{date_column}' et/ou '{column_name}' sont absentes.")
        return None

# Charge les données
index_data = donnees['index_data']  # Chargement depuis la feuille "Index"

# Prépare les indices SPX et SXXP
spx_index = prepare_reference_index(index_data, "SPX Index")
sxxp_index = prepare_reference_index(index_data, "SXXP Index")

# Sélection interactive de l'indice de référence
st.subheader("📊 Calculer les statistiques d'un indice sectoriel")
risk_free_rate = st.number_input("Taux sans risque (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.1) / 100
use_reference = st.checkbox("Utiliser un indice de référence pour l'Alpha ?", value=False)

reference_index = None
if use_reference:
    st.markdown("**Sélectionnez un indice de référence** (SPX ou SXXP) pour le calcul de l'Alpha :")
    selected_reference = st.selectbox("Indice de référence :", options=["SPX", "SXXP"], index=0)
    if selected_reference == "SPX":
        reference_index = spx_index
    elif selected_reference == "SXXP":
        reference_index = sxxp_index

# Fonction pour calculer les statistiques principales
def stats_index(index, reference_index=None, risk_free_rate=0.0):
    """
    Calcule et affiche les statistiques principales d'un indice.

    Args:
        index (pd.DataFrame): Données de l'indice cible (avec colonnes 'Dates' et 'Index_Value').
        reference_index (pd.DataFrame, optional): Données de l'indice de référence (avec colonnes 'Dates' et 'Index_Value').
        risk_free_rate (float, optional): Taux sans risque pour calculer l'Alpha et le Ratio de Sharpe.

    Returns:
        tuple: (stats_df, alpha, beta, merged_data) :
               - stats_df : Résumé des statistiques de l'indice
               - alpha : Valeur de l'Alpha (float)
               - beta : Valeur du Bêta (float)
               - merged_data : Données fusionnées des indices cible et référence
    """
    if index is None or index.empty:
        st.error("Les données de l'indice sont vides ou invalides.")
        return None, None, None, None

    required_columns = ['Dates', 'Index_Value']
    if not all(col in index.columns for col in required_columns):
        st.error(f"L'indice doit contenir les colonnes suivantes : {required_columns}")
        return None, None, None, None

    try:
        # Calculs de base
        start_value = index['Index_Value'].iloc[0]
        end_value = index['Index_Value'].iloc[-1]
        total_return = ((end_value - start_value) / start_value) * 100
        annualized_return = (end_value / start_value) ** (1 / (len(index) / 252)) - 1
        volatility = index['Index_Value'].pct_change().std() * (252 ** 0.5)

        # Max Drawdown
        cumulative_returns = (1 + index['Index_Value'].pct_change()).cumprod()
        rolling_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        # Ratio de Sharpe
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility

        # Alpha et Beta (si une référence est fournie)
        alpha = None
        beta = None
        merged = None
        if reference_index is not None:
            merged = pd.merge(
                index[['Dates', 'Index_Value']],
                reference_index[['Dates', 'Index_Value']],
                on='Dates',
                suffixes=('_target', '_reference')
            )
            if not merged.empty:
                target_return = merged['Index_Value_target'].pct_change()
                reference_return = merged['Index_Value_reference'].pct_change()
                beta = np.cov(target_return.dropna(), reference_return.dropna())[0, 1] / np.var(reference_return.dropna())
                alpha = (annualized_return - (risk_free_rate + beta * (reference_return.mean() - risk_free_rate)))

        # Résumé des statistiques
        stats_data = {
            "Valeur Initiale": [start_value],
            "Valeur Finale": [end_value],
            "Rendement Total (%)": [total_return],
            "Rendement Annualisé (%)": [annualized_return * 100],
            "Volatilité Annualisée (%)": [volatility * 100],
            "Max Drawdown (%)": [max_drawdown],
            "Ratio de Sharpe": [sharpe_ratio],
        }
        if alpha is not None and beta is not None:
            stats_data["Alpha"] = [alpha]
            stats_data["Beta"] = [beta]

        st.write("**Résumé des Statistiques de l'Indice :**")
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df)

        return stats_df, alpha, beta, merged

    except Exception as e:
        st.error(f"Erreur lors du calcul des statistiques : {e}")
        return None, None, None, None


# Fonction pour analyser les statistiques principales et les Alphas/Bêtas
def analyze_statistics_and_alpha(stats_df, filename, merged_data=None, alpha_value=None, beta_value=None):
    """
    Analyse les statistiques principales et, si disponibles, les Alphas et Bêtas.

    Args:
        stats_df (pd.DataFrame): DataFrame contenant les statistiques principales calculées pour l'indice.
        filename (str): Chemin du fichier pour sauvegarder les statistiques sous forme d'image.
        merged_data (pd.DataFrame, optional): Données fusionnées pour l'analyse Alpha/Beta.
        alpha_value (float, optional): Valeur de l'Alpha calculée.
        beta_value (float, optional): Valeur du Bêta calculée.
    """
    st.subheader("📊 Analyse complète des Statistiques de l'Indice")

    # Analyse des statistiques principales
    if stats_df is not None and not stats_df.empty:
        # Extraction des valeurs
        total_return = stats_df.at[0, "Rendement Total (%)"]
        annualized_return = stats_df.at[0, "Rendement Annualisé (%)"]
        volatility = stats_df.at[0, "Volatilité Annualisée (%)"]
        max_drawdown = stats_df.at[0, "Max Drawdown (%)"]
        sharpe_ratio = stats_df.at[0, "Ratio de Sharpe"]

        # Sauvegarde des statistiques dans un fichier PNG
        dataframe_to_image(stats_df, filename)

        # Conclusions basées sur les statistiques
        st.subheader("📋 Conclusions basées sur les Statistiques")
        st.write("✔️ **Rendement Total élevé :** L'indice a généré plus du double de son capital initial."
                 if total_return > 100 else 
                 "❌ **Rendement Total faible :** L'indice a généré des gains limités.")
        st.write("📈 **Volatilité élevée :** L'indice est sujet à des fluctuations importantes."
                 if volatility > 20 else 
                 "📉 **Volatilité modérée :** L'indice montre un bon équilibre entre stabilité et performance.")
        st.write("❌ **Max Drawdown élevé :** L'indice a subi une perte significative par rapport à son pic."
                 if max_drawdown < -30 else 
                 "✔️ **Max Drawdown faible :** L'indice est resté relativement stable.")
        st.write("✔️ **Ratio de Sharpe satisfaisant :** L'indice offre un bon équilibre entre risque et rendement."
                if sharpe_ratio > 1 else 
                "⚠️ **Ratio de Sharpe modéré :** Les rendements compensent tout juste le risque pris."
                if 0.5 <= sharpe_ratio <= 1 else 
         "❌ **Ratio de Sharpe faible :** Les rendements ne compensent pas suffisamment le risque.")

    else:
        st.error("❌ Les statistiques principales sont indisponibles.")

    # Analyse des Alphas et Bêtas
    if isinstance(merged_data, pd.DataFrame) and not merged_data.empty:
        required_columns = ['Index_Value_target', 'Index_Value_reference']
        if all(col in merged_data.columns for col in required_columns):
            # Calculs journaliers
            merged_data['Daily_Return_Target'] = merged_data['Index_Value_target'].pct_change()
            merged_data['Daily_Return_Reference'] = merged_data['Index_Value_reference'].pct_change()

            # Affichage des statistiques descriptives
            st.subheader("📋 Analyse des Alphas et Bêtas")

            if alpha_value is not None:
                st.write(f"**Alpha :** {alpha_value/100:.4f}")
            else:
                st.write("**Alpha :** Non calculé")

            if beta_value is not None:
                st.write(f"**Beta :** {beta_value:.4f}")
            else:
                st.write("**Beta :** Non calculé")

            # Conclusions basées sur Alpha
            if alpha_value is not None:
                st.write("### Conclusion sur l'Alpha :")
                if alpha_value > 0:
                    st.write("✔️ **Alpha positif :** L'indice cible surperforme l'indice de référence après ajustement pour le risque.")
                elif alpha_value < 0:
                    st.write("❌ **Alpha négatif :** L'indice cible sous-performe l'indice de référence après ajustement pour le risque.")
                else:
                    st.write("⚖️ **Alpha nul :** L'indice cible a une performance équivalente à celle de l'indice de référence après ajustement pour le risque.")
            else:
                st.warning("⚠️ L'Alpha n'est pas disponible pour cette analyse.")

            # Conclusions basées sur Beta
            if beta_value is not None:
                st.write("### Conclusion sur le Beta :")
                if beta_value > 1:
                    st.write("📈 **Beta > 1 :** L'indice cible est plus volatil que l'indice de référence.")
                elif beta_value < 1:
                    st.write("📉 **Beta < 1 :** L'indice cible est moins volatil que l'indice de référence.")
                else:
                    st.write("🔄 **Beta ≈ 1 :** L'indice cible suit de près la volatilité de l'indice de référence.")
            else:
                st.warning("⚠️ Le Beta n'est pas disponible pour cette analyse.")


            # Graphique des rendements comparés
            st.subheader("📈 Comparaison des Rendements Journaliers")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(merged_data['Dates'], merged_data['Daily_Return_Target'], label='Rendements Cible', alpha=0.7)
            ax.plot(merged_data['Dates'], merged_data['Daily_Return_Reference'], label='Rendements Référence', alpha=0.7)
            ax.set_title("Comparaison des Rendements Journaliers", fontsize=14)
            ax.set_xlabel("Dates", fontsize=12)
            ax.set_ylabel("Rendements (%)", fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(fontsize=12)
            st.pyplot(fig)
        else:
            st.warning("⚠️ Les colonnes nécessaires pour l'analyse Alpha/Beta sont absentes des données fusionnées.")
    else:
        st.warning("⚠️ Les données pour l'analyse Alpha/Beta sont indisponibles.")

# Appel de l'analyse détaillée avec conclusion complète
if reference_index is not None:
    stats_df, alpha, beta, merged_data = stats_index(
        index_energy, reference_index=reference_index, risk_free_rate=risk_free_rate
    )
    if stats_df is not None:
        # Définit un fichier unique pour enregistrer les statistiques
        stats_filename_reference = f"temp_reports/Statistiques_Indice_{secteur_choisi.lower().replace(' ', '_')}.png"

        analyze_statistics_and_alpha(
            stats_df=stats_df,
            filename=stats_filename_reference,
            merged_data=merged_data,
            alpha_value=alpha * 100 if alpha is not None else None,
            beta_value=beta if beta is not None else None
        )
    else:
        st.warning("❗ Les statistiques principales ou les Alphas/Bêtas n'ont pas pu être calculés pour les données fournies.")
else:
    st.warning("⚠️ Aucun indice de référence sélectionné. Analyse des Alphas et Bêtas ignorée.")

# Titre principal
st.title("🛠️ Rebalancement d'un Indice Sectoriel")
st.markdown("""
Dans cette section, nous allons aborder le **rebalancement interactif de l'indice sectoriel**.
Vous pouvez sélectionner une année pour effectuer le traitement des prix, le rebalancement, et analyser les statistiques associées.
""")

# Fonction pour traiter les prix pour une année donnée
def process_prices_year(spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year):
    spx_prices['Dates'] = pd.to_datetime(spx_prices['Dates'])
    sxxp_prices['Dates'] = pd.to_datetime(sxxp_prices['Dates'])

    # Filtre les données pour l'année spécifiée
    spx_year_data = spx_prices[(spx_prices['Dates'] >= f"{year}-01-01") & (spx_prices['Dates'] <= f"{year}-12-31")]
    sxxp_year_data = sxxp_prices[(sxxp_prices['Dates'] >= f"{year}-01-01") & (sxxp_prices['Dates'] <= f"{year}-12-31")]

    # Détermine les plages de dates communes
    start_date = max(spx_year_data['Dates'].min(), sxxp_year_data['Dates'].min())
    end_date = min(spx_year_data['Dates'].max(), sxxp_year_data['Dates'].max())

    # Filtre les données et applique les transformations
    spx_filtered, _ = filter_prices(spx_prices, spx_tickers, start_date, end_date)
    sxxp_filtered, _ = filter_prices(sxxp_prices, sxxp_tickers, start_date, end_date)
    sxxp_usd = convert_usd(sxxp_filtered, forex_data)
    combined_prices = merge_dates(spx_filtered, sxxp_usd)
    normalized_prices = normalize_prices(combined_prices)

    return normalized_prices

def rebalance_index(previous_index, processed_prices, qualitativ_data):
    """
    Rebalance l'indice en assurant la continuité avec l'année précédente.
    
    Args:
    - previous_index (pd.DataFrame): L'indice précédent.
    - processed_prices (pd.DataFrame): Les prix traités pour l'année en cours.
    - qualitativ_data (pd.DataFrame): Données qualitatives (pondérations des tickers).
    
    Returns:
    - pd.DataFrame: Indice rebalancé.
    """
    weights = market_cap_weights(processed_prices, qualitativ_data)
    tickers = processed_prices.columns[1:]  # Exclure la colonne Dates

    # Vérifie que les pondérations couvrent tous les tickers
    if set(weights['Ticker']) != set(tickers):
        missing_tickers = set(tickers) - set(weights['Ticker'])
        st.error(f"Les tickers suivants manquent dans les pondérations : {missing_tickers}")
        raise ValueError("Pondérations manquantes pour certains tickers.")

    # Calcul des valeurs rebalancées
    index_values = (processed_prices.iloc[:, 1:] * weights['Weight'].values).sum(axis=1)

    # Normalisation par rapport à la dernière valeur de l'indice précédent
    last_value_previous = previous_index['Index_Value'].iloc[-1]
    normalized_index_values = (index_values / index_values.iloc[0]) * last_value_previous

    # Création du DataFrame rebalancé
    rebalanced_index = pd.DataFrame({
        'Dates': processed_prices['Dates'],
        'Index_Value': normalized_index_values
    })

    # Concaténer avec l'indice précédent
    return pd.concat([previous_index, rebalanced_index]).reset_index(drop=True)


def rebalance_multiple_years(
    initial_index, end_year, spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, qualitativ_data_by_year
):
    """
    Rebalance l'indice sectoriel successivement pour toutes les années jusqu'à l'année sélectionnée.
    
    Args:
    - initial_index (pd.DataFrame): L'indice initial avant le rebalancement.
    - end_year (int): Année sélectionnée pour le rebalancement.
    - spx_prices, sxxp_prices (pd.DataFrame): Données des prix SPX et SXXP.
    - spx_tickers, sxxp_tickers (list): Tickers des indices SPX et SXXP.
    - forex_data (pd.DataFrame): Données Forex pour la conversion des devises.
    - qualitativ_data_by_year (dict): Données qualitatives par année.
    
    Returns:
    - pd.DataFrame: Indice sectoriel rebalancé.
    """
    index = initial_index.copy()
    start_year = index['Dates'].iloc[-1].year + 1  # Première année non encore rebalancée

    for year in range(start_year, end_year + 1):

        # Récupére les prix pour l'année
        prices_for_year = process_prices_year(spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year)
        qualitativ_for_year = qualitativ_data_by_year.get(year)

        if prices_for_year.empty:
            # Passe l'année si les données sont manquantes
            continue

        # Applique le rebalancement pour l'année
        index = rebalance_index(index, prices_for_year, qualitativ_for_year)

    return index

# Charger les données qualitatives par année 
qualitativ_data_by_year = {}
available_years = [2019, 2020] 

for year in available_years:
    try:
        qualitativ_data_by_year[year] = donnees[f'qualitativ_{year}'] 
    except KeyError:
        st.warning(f"Les données qualitatives pour l'année {year} ne sont pas disponibles.")
        qualitativ_data_by_year[year] = None  

# Interface Interactive 
st.subheader("⚖️ Rebalancement Dynamique de l'Indice")
selected_year = st.selectbox(
    "Choisissez une année pour le rebalancement :",
    options=range(2010, 2021),  # Plage d'années disponibles
    index=10  # Par défaut : 2020
)

# Rebalancement pour l'année sélectionnée
st.subheader(f"📈 Rebalancement de l'Indice jusqu'à l'année {selected_year}")

# Vérifie les données qualitatives nécessaires
if any(qualitativ_data_by_year[year] is None for year in range(2010, selected_year + 1) if year in available_years):
    st.error("Certaines données qualitatives nécessaires pour le rebalancement ne sont pas disponibles.")
else:
    # Applique le rebalancement multiple
    index_energy_rebalanced = rebalance_multiple_years(
        index_energy, selected_year, 
        spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, qualitativ_data_by_year
    )

    # Visualisation
    st.subheader(f"📈 Évolution de l'Indice sectoriel '{secteur_choisi}' après Rebalancement ({selected_year})")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        index_energy_rebalanced['Dates'],
        index_energy_rebalanced['Index_Value'],
        label=f"Indice sectoriel '{secteur_choisi}' Rebalancé",
        color="purple",
        linewidth=2
    )
    ax.set_title(f"Évolution de l'Indice sectoriel '{secteur_choisi}' pour l'année ({selected_year})", fontsize=16)
    ax.set_xlabel("Dates", fontsize=12)
    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    st.pyplot(fig)

    # Enregistrement du graphique
    filename = f"indice_sectoriel_{secteur_choisi.replace(' ', '_').lower()}_rebalancement_{selected_year}.png"
    save_figure(fig, filename)


# Titre principal
st.title("🏆 Création et Analyse d'un Indice de Solidité Financière")

st.markdown("""
Dans cette section, nous allons construire un **indice de solidité financière** basé sur les fondamentaux des entreprises.  
Cet indice sera calculé en attribuant un **score composite** à chaque entreprise, en tenant compte de plusieurs métriques financières clés, 
telles que les ratios financiers et les rendements. L'objectif est d'évaluer la robustesse financière des entreprises et d'analyser les tendances associées.
""")

# Objectif de l'analyse
st.subheader("🎯 Objectif")
st.markdown("""
L'objectif de cette analyse est de créer un indice sectoriel reflétant la **solidité financière** des entreprises sélectionnées.  
En étudiant cet indice, nous pourrons :
- Identifier les entreprises les plus solides financièrement.
- Analyser la performance et la volatilité des entreprises les plus stables.
- Comparer les tendances de solidité financière au sein d'un secteur donné.
""")

# Méthodologie et Formules
st.subheader("📚 Méthodologie et Formules")
st.markdown(r"""
Nous utilisons les métriques suivantes pour calculer un **score composite** :  

1. **PX_TO_BOOK (Price-to-Book Ratio)** :  
   $$ 
   \text{Norm\_PX\_TO\_BOOK}_i = 
   \frac{\text{PX\_TO\_BOOK}_i - \min(\text{PX\_TO\_BOOK})}
        {\max(\text{PX\_TO\_BOOK}) - \min(\text{PX\_TO\_BOOK})} 
   $$

2. **PE_RATIO (Price-to-Earnings Ratio)** :  
   Nous utilisons l'inverse de ce ratio pour privilégier les entreprises sous-évaluées :  
   $$ 
   \text{Norm\_PE\_RATIO\_Inv}_i = 
   \frac{\frac{1}{\text{PE\_RATIO}_i} - \min\left(\frac{1}{\text{PE\_RATIO}}\right)}
        {\max\left(\frac{1}{\text{PE\_RATIO}}\right) - \min\left(\frac{1}{\text{PE\_RATIO}}\right)} 
   $$

3. **CUR_MKT_CAP (Capitalisation Boursière)** :  
   $$ 
   \text{Norm\_CUR\_MKT\_CAP}_i = 
   \frac{\text{CUR\_MKT\_CAP}_i - \min(\text{CUR\_MKT\_CAP})}
        {\max(\text{CUR\_MKT\_CAP}) - \min(\text{CUR\_MKT\_CAP})} 
   $$

4. **EQY_DVD_YLD (Rendement des Dividendes)** :  
   $$ 
   \text{Norm\_EQY\_DVD\_YLD}_i = 
   \frac{\text{EQY\_DVD\_YLD}_i - \min(\text{EQY\_DVD\_YLD})}
        {\max(\text{EQY\_DVD\_YLD}) - \min(\text{EQY\_DVD\_YLD})} 
   $$

### Formule du Score :
$$
\text{Score}_i = 
0.25 \cdot \text{Norm\_PX\_TO\_BOOK}_i + 
0.25 \cdot \text{Norm\_PE\_RATIO\_Inv}_i + 
0.30 \cdot \text{Norm\_CUR\_MKT\_CAP}_i + 
0.20 \cdot \text{Norm\_EQY\_DVD\_YLD}_i
$$
""")


st.markdown("""### Étapes clés de l'analyse
1. **Filtrage des entreprises** : Les entreprises avec des données manquantes pour les métriques clés sont exclues.
2. **Calcul des scores normalisés** : Chaque métrique est normalisée entre 0 et 1 pour assurer une pondération équitable.
3. **Construction de l'indice** : Les scores composites sont utilisés pour calculer les pondérations des entreprises dans l'indice.
4. **Analyse des performances** : L'indice est analysé pour évaluer ses rendements, sa volatilité et sa stabilité par rapport aux benchmarks.
""")

# Fonction pour calculer les scores et afficher les résultats 
def calcul_score(qualitativ_data, px_to_book, pe_ratio, cur_mkcap, eqy_dvd):
    """
    Calcule le score basé sur les fondamentaux pour chaque entreprise de la feuille "qualitativ_data".
    Exclut les entreprises ayant des critères manquants et affiche combien d'entreprises sont exclues.

    Arguments :
    qualitativ_data : DataFrame contenant les données fondamentales (PX_TO_BOOK, PE_RATIO, etc.).
    px_to_book, pe_ratio, cur_mkcap, eqy_dvd : Valeurs entre 0 et 1 pour pondérer le score à notre guise.
    
    Retour :
    DataFrame contenant les tickers et leurs scores, avec affichage des exclusions dans Streamlit.
    """

    # Renomme les colonnes pour correspondre aux attentes
    qualitativ_data.rename(columns={
        'PX_TO_BOOK': 'PX_TO_BOOK_RATIO',
        'EQY_DVD_YLD': 'EQY_DVD_YLD_IND',
        'Ticker': 'Ticker' 
    }, inplace=True)

    # Remplace les virgules par des points et convertir en numérique
    cols_to_convert = ['PX_TO_BOOK_RATIO', 'PE_RATIO', 'CUR_MKT_CAP', 'EQY_DVD_YLD_IND']
    for col in cols_to_convert:
        qualitativ_data[col] = qualitativ_data[col].replace(',', '.', regex=True).replace('#N/A N/A', None)
        qualitativ_data[col] = pd.to_numeric(qualitativ_data[col], errors='coerce')

    # Vérification et filtrage des colonnes manquantes
    columns = ['Ticker', 'PX_TO_BOOK_RATIO', 'PE_RATIO', 'CUR_MKT_CAP', 'EQY_DVD_YLD_IND']
    filtered_data = qualitativ_data.dropna(subset=columns).copy()
    excluded_count = len(qualitativ_data) - len(filtered_data)
    st.write(f"📉 **Nombre d'entreprises exclues pour critères manquants :** {excluded_count}")

    # Calcul des normalisations pour chaque critère
    filtered_data['Norm_PX_TO_BOOK'] = (
        (filtered_data['PX_TO_BOOK_RATIO'] - filtered_data['PX_TO_BOOK_RATIO'].min()) /
        (filtered_data['PX_TO_BOOK_RATIO'].max() - filtered_data['PX_TO_BOOK_RATIO'].min())
    )

    filtered_data['Norm_PE_RATIO_Inv'] = (
        (1 / filtered_data['PE_RATIO'] - (1 / filtered_data['PE_RATIO']).min()) /
        ((1 / filtered_data['PE_RATIO']).max() - (1 / filtered_data['PE_RATIO']).min())
    )

    filtered_data['Norm_CUR_MKT_CAP'] = (
        (filtered_data['CUR_MKT_CAP'] - filtered_data['CUR_MKT_CAP'].min()) /
        (filtered_data['CUR_MKT_CAP'].max() - filtered_data['CUR_MKT_CAP'].min())
    )

    filtered_data['Norm_EQY_DVD_YLD_IND'] = (
        (filtered_data['EQY_DVD_YLD_IND'] - filtered_data['EQY_DVD_YLD_IND'].min()) /
        (filtered_data['EQY_DVD_YLD_IND'].max() - filtered_data['EQY_DVD_YLD_IND'].min())
    )

    # Calcul des scores
    filtered_data['Score'] = (
        px_to_book * filtered_data['Norm_PX_TO_BOOK'] +
        pe_ratio * filtered_data['Norm_PE_RATIO_Inv'] +
        cur_mkcap * filtered_data['Norm_CUR_MKT_CAP'] +
        eqy_dvd * filtered_data['Norm_EQY_DVD_YLD_IND']
    )

    # Tri des résultats
    result = filtered_data[['Ticker', 'Score']].sort_values(by="Score", ascending=False)

    # Affichage du résultat
    st.write("🔢 **Scores calculés pour les entreprises :**")
    st.dataframe(result)

    return result

# Fonction pour calculer les poids
def weights_scores(score_data, top_n='all'):
    """
    Calcule les poids normalisés basés sur les scores calculés pour chaque entreprise.
    Peut limiter le nombre d'entreprises conservées aux top_n scores les plus élevés.
    """
    if top_n != 'all':
        score_data = score_data.nlargest(top_n, 'Score')

    total_score = score_data['Score'].sum()
    score_data['Weight'] = score_data['Score'] / total_score

    return score_data[['Ticker', 'Weight']].sort_values(by="Weight", ascending=False)

# Initialisation des poids par défaut
default_weights = {"PX_TO_BOOK": 0.25, "PE_RATIO": 0.25, "CUR_MKT_CAP": 0.30, "EQY_DVD_YLD": 0.20}

# Section interactive pour les poids
st.subheader("⚖️ Définir les poids pour le calcul des scores")
st.markdown("""
Personnalisez les poids pour chaque critère. La somme des poids doit être égale à 1.  
Par défaut, les valeurs sont :  
- PX_TO_BOOK : 0.25  
- PE_RATIO : 0.25  
- CUR_MKT_CAP : 0.30  
- EQY_DVD_YLD : 0.20
""")

reset_clicked = st.button("🔄 Réinitialiser aux valeurs par défaut")

if reset_clicked:
    px_to_book = default_weights["PX_TO_BOOK"]
    pe_ratio = default_weights["PE_RATIO"]
    cur_mkcap = default_weights["CUR_MKT_CAP"]
    eqy_dvd = default_weights["EQY_DVD_YLD"]
    st.success("Les poids ont été réinitialisés aux valeurs par défaut.")
else:
    px_to_book = st.slider("Poids pour PX_TO_BOOK (Price-to-Book Ratio)", 0.0, 1.0, default_weights["PX_TO_BOOK"], step=0.01)
    pe_ratio = st.slider("Poids pour PE_RATIO (Price-to-Earnings Ratio)", 0.0, 1.0, default_weights["PE_RATIO"], step=0.01)
    cur_mkcap = st.slider("Poids pour CUR_MKT_CAP (Capitalisation Boursière)", 0.0, 1.0, default_weights["CUR_MKT_CAP"], step=0.01)
    eqy_dvd = st.slider("Poids pour EQY_DVD_YLD (Rendement des Dividendes)", 0.0, 1.0, default_weights["EQY_DVD_YLD"], step=0.01)

# Vérification des poids
total_weights = px_to_book + pe_ratio + cur_mkcap + eqy_dvd
if not np.isclose(total_weights, 1.0, rtol=0, atol=1e-9):
    st.error(f"La somme des poids doit être égale à 1. Actuellement : {total_weights:.2f}")
    st.stop()

# Calcul des scores
st.success(f"Les poids définis sont valides. La somme des poids est {total_weights:.2f}.")
score = calcul_score(donnees['qualitativ_2018'], px_to_book, pe_ratio, cur_mkcap, eqy_dvd)

# Section interactive pour le nombre d'entreprises
st.subheader("⚙️ Paramètres de sélection des entreprises")
total_companies = len(score)
top_n = st.slider(
    "Nombre d'entreprises à sélectionner (Top N)",
    min_value=10,
    max_value=total_companies,
    value=10,
    step=1
)
if top_n == total_companies:
    st.write("⚠️ Toutes les entreprises disponibles seront incluses dans l'indice.")
else:
    st.write(f"Les {top_n} meilleures entreprises seront sélectionnées.")

# Calcul des poids pour les entreprises sélectionnées
weight_score = weights_scores(score, top_n=top_n)
st.write("⚖️ **Poids des entreprises sélectionnées :**")
st.dataframe(weight_score)

# Titre principal de l'application
st.title("📈 Analyse et Rebalancement Dynamique ")

# Chargement des données essentielles
forex_data = donnees['forex_data']
spx_prices = donnees['spx_prices']
sxxp_prices = donnees['sxxp_prices']

# Étape 1 : Filtrage des entreprises avec tous les fondamentaux disponibles
st.subheader("🔍 Filtrage des entreprises valides")

# Récupère les tickers avec des scores calculés
tickers_score = list(weight_score.iloc[:, 0])

# Section interactive pour afficher ou masquer les tickers sélectionnés
with st.expander("Afficher les tickers sélectionnés"):
    st.write("**Tickers sélectionnés :**")
    st.write(tickers_score)


# Étape 2 : Filtrer les prix en fonction des tickers et des dates
st.subheader("📊 Filtrage des prix sur une période donnée")
start_date = st.date_input("Sélectionnez une date de début :", value=pd.to_datetime('2010-04-01'))
end_date = st.date_input("Sélectionnez une date de fin :", value=pd.to_datetime('2018-12-28'))

# Filtrage des prix pour SPX
spx_score_prices, spx_excluded = filter_prices(spx_prices, tickers_score, start_date, end_date)

with st.expander("Afficher les tickers exclus pour SPX"):
    st.write("**Tickers exclus pour SPX :**", spx_excluded)

with st.expander("Afficher les prix filtrés pour SPX"):
    st.write("**Prix filtrés pour SPX :**")
    st.dataframe(spx_score_prices)

# Filtrage des prix pour SXXP
sxxp_score_prices, sxxp_excluded = filter_prices(sxxp_prices, tickers_score, start_date, end_date)
with st.expander("Afficher les tickers exclus pour SXXP"):
    st.write("**Tickers exclus pour SXXP :**", sxxp_excluded)

with st.expander("Afficher les prix filtrés pour SXXP"):
    st.write("**Prix filtrés pour SXXP :**")
    st.dataframe(sxxp_score_prices) 


# Étape 3 : Conversion des prix SXXP en dollars
st.subheader("💵 Conversion des prix SXXP en dollars")
sxxp_score_prices_usd = convert_usd(sxxp_score_prices, forex_data)
st.write("**Prix convertis en dollars :**")
st.dataframe(sxxp_score_prices_usd)

# Étape 4 : Fusion des prix SPX et SXXP
st.subheader("🔗 Fusion des prix SPX et SXXP")
score_prices = merge_dates(spx_score_prices, sxxp_score_prices_usd)
st.write("**Prix fusionnés :**")
st.dataframe(score_prices)

# Étape 5 : Normalisation des prix
st.subheader("📏 Normalisation des prix")
score_prices_normalize = normalize_prices(score_prices)
st.write("**Prix normalisés :**")
st.dataframe(score_prices_normalize)

# Étape 6 : Construction de l'indice basé sur les scores
st.subheader("⚙️ Construction de l'indice basé sur les scores")
index_score = construct_index(score_prices_normalize, weight_score)
st.write("**Indice de style construit :**")
st.dataframe(index_score)

# Visualisation de l'indice avant rebalancement
st.subheader("📈 Visualisation de l'indice avant rebalancement")
fig_before, ax_before = plt.subplots(figsize=(10, 5))
ax_before.plot(index_score['Dates'], index_score['Index_Value'], label='Indice Avant Rebalancement', color="blue", linewidth=2)
ax_before.set_title("Indice Avant Rebalancement", fontsize=14)
ax_before.set_xlabel("Dates", fontsize=12)
ax_before.set_ylabel("Valeur de l'Indice", fontsize=12)
ax_before.legend(fontsize=12)
ax_before.grid(True, linestyle='--', alpha=0.6)

# Affichage 
st.pyplot(fig_before)

# Enregistrement du graphique avant rebalancement
filename_before = "indiceII_avant_rebalancement.png"
save_figure(fig_before, filename_before)

st.subheader("📊 Analyse des statistiques de l'indice avant rebalancement")
stats_df, alpha, beta, merged_data = stats_index(index_score)

if stats_df is not None:
    # Enregistrer les statistiques dans un fichier PNG
    stats_filename_before = "temp_reports/Statistiques_IndiceII_Avant_Rebalancement.png"

    # Appel unique avec tous les arguments
    analyze_statistics_and_alpha(
        stats_df=stats_df,
        filename=stats_filename_before,
        merged_data=merged_data,
        alpha_value=alpha,
        beta_value=beta
    )
else:
    st.error("❌ Impossible de calculer les statistiques avant rebalancement.")

# Étape 8 : Rebalancement dynamique de l'indice
st.subheader(f"📈 Rebalancement de l'Indice jusqu'à l'année {selected_year}")
if selected_year not in available_years:
    st.error(f"Données qualitatives indisponibles pour l'année {selected_year}. Veuillez sélectionner une autre année.")
else:
    index_energy_rebalanced = rebalance_multiple_years(
        index_score, selected_year, 
        spx_prices, sxxp_prices, tickers_score, tickers_score, forex_data, qualitativ_data_by_year
    )
    st.write(f"**Indice rebalancé jusqu'à l'année {selected_year} :**")
    
    # Visualisation de l'indice après rebalancement
    st.subheader("📈 Visualisation de l'indice après rebalancement")
    fig_after, ax_after = plt.subplots(figsize=(10, 5))
    ax_after.plot(index_energy_rebalanced['Dates'], index_energy_rebalanced['Index_Value'], label='Indice Après Rebalancement', color="green", linewidth=2)
    ax_after.set_title("Indice Après Rebalancement", fontsize=14)
    ax_after.set_xlabel("Dates", fontsize=12)
    ax_after.set_ylabel("Valeur de l'Indice", fontsize=12)
    ax_after.legend(fontsize=12)
    ax_after.grid(True, linestyle='--', alpha=0.6)

    # Affichage 
    st.pyplot(fig_after)
    # Enregistrement du graphique après rebalancement
filename_after = "indiceII_apres_rebalancement.png"
save_figure(fig_after, filename_after)
st.dataframe(index_energy_rebalanced)

# Étape 9 : Analyse des statistiques après rebalancement
st.subheader("📊 Analyse des statistiques de l'indice après rebalancement")
stats_df_rebalanced, alpha_rebalanced, beta_rebalanced, merged_data_rebalanced = stats_index(index_energy_rebalanced)

if stats_df_rebalanced is not None:
    stats_filename_after = "temp_reports/Statistiques_IndiceII_Apres_Rebalancement.png"
    analyze_statistics_and_alpha(
        stats_df=stats_df_rebalanced,
        filename=stats_filename_after, 
        merged_data=merged_data_rebalanced,
        alpha_value=alpha_rebalanced,
        beta_value=beta_rebalanced
    )
else:
    st.error("❌ Impossible de calculer les statistiques après rebalancement.")

# Fonction pour rebalancer les années disponibles à partir de 2019
def rebalance_multiple_years(initial_index, end_year, spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, qualitativ_data_by_year):
    """
    Rebalance l'indice sectoriel successivement pour les années disponibles, en commençant à partir de 2019.
    
    Args:
    - initial_index (pd.DataFrame): L'indice initial avant le rebalancement.
    - end_year (int): Année sélectionnée pour le rebalancement.
    - spx_prices, sxxp_prices (pd.DataFrame): Données des prix SPX et SXXP.
    - spx_tickers, sxxp_tickers (list): Tickers des indices SPX et SXXP.
    - forex_data (pd.DataFrame): Données Forex pour la conversion des devises.
    - qualitativ_data_by_year (dict): Données qualitatives disponibles par année.
    
    Returns:
    - pd.DataFrame: Indice sectoriel rebalancé.
    """
    index = initial_index.copy()

    for year in sorted(qualitativ_data_by_year.keys()):
        if year < 2019:  # Ignorer les années avant 2019
            continue
        if year > end_year:
            break  # Stop si on dépasse l'année sélectionnée

        qualitativ_for_year = qualitativ_data_by_year.get(year)
        if qualitativ_for_year is None:
            st.warning(f"Données qualitatives manquantes pour l'année {year}.")
            continue

        # Traite les prix pour l'année en cours
        prices_for_year = process_prices_year(spx_prices, sxxp_prices, spx_tickers, sxxp_tickers, forex_data, year)
        if prices_for_year.empty:
            st.warning(f"Pas de données disponibles pour les prix de l'année {year}.")
            continue

        # Applique le rebalancement pour l'année
        index = rebalance_index(index, prices_for_year, qualitativ_for_year)

    return index

# Vérification et application du rebalancement
if selected_year not in available_years:
    st.error(f"Données qualitatives indisponibles pour l'année {selected_year}. Veuillez sélectionner une autre année.")
else:
    # Utiliser l'indice jusqu'à fin 2018 comme point de départ
    index_energy_rebalanced = rebalance_multiple_years(
        index_score, selected_year,  # Utilise `index_score` comme base, inchangé avant 2019
        spx_prices, sxxp_prices, tickers_score, tickers_score, forex_data, qualitativ_data_by_year
    )


# Analyse des Résultats
st.subheader("📝 Analyse des Résultats de l'Indice")

# Avant le Rebalancement
with st.expander("🔍 Avant le Rebalancement", expanded=False):
    st.markdown("""
    Avant le rebalancement, l’indice initial montre une croissance notable sur la période 2010-2019, 
    avec un **rendement total de 159,08%** et un **rendement annualisé de 11,7%**. Cependant, cette performance est accompagnée 
    d’une **volatilité annualisée élevée de 16,12%**, reflétant une exposition aux entreprises de tous secteurs, sensibles 
    aux fluctuations des marchés globaux.
    
    La baisse significative observée en 2018 reflète des tensions macroéconomiques majeures, notamment :
    - **Guerre commerciale sino-américaine** : L'administration Trump a initié des hausses de droits de douane, suscitant des incertitudes.
    - **Craintes d'un ralentissement économique mondial** : Les marchés ont anticipé un essoufflement de l'économie, influençant négativement les indices.
    - **Politiques monétaires restrictives** : La Réserve fédérale américaine a relevé ses taux d'intérêt, renforçant l'aversion au risque.

    Ces facteurs ont contribué à une volatilité accrue et à une baisse des marchés financiers en 2018.
    """)

# Après le Rebalancement
with st.expander("🔍 Après le Rebalancement", expanded=False):
    st.markdown("""
    Après le rebalancement en 2019, l’indice gagne en stabilité et affiche une **performance renforcée**. En se concentrant 
    sur les **10 meilleures entreprises** sélectionnées parmi tous les secteurs, le rendement total passe à **264,19%**, 
    avec un **rendement annualisé de 13,01%**. 
    
    La **volatilité annualisée** augmente légèrement à **18,24%**, mais cela s’accompagne d’une amélioration des rendements. 
    Ce résultat montre que l’approche basée sur les fondamentaux reste robuste même face à une sélection restreinte.
    """)

st.subheader("📊 Résumé Visuel")
with st.expander("📈 Visualisation des Graphiques", expanded=False):
    st.markdown("""
    Les graphiques affichés plus haut montrent l’évolution de l’indice avant et après rebalancement.  
    Avant 2019, l’indice présente des fluctuations importantes avec des pics et des creux marqués, notamment une chute significative en 2018.  
    Cependant, juste après cette chute, les cours montrent une reprise rapide, illustrant la résilience du marché et les opportunités 
    offertes par les fondamentaux solides des entreprises.

    Après le rebalancement, la trajectoire devient plus régulière, indiquant que les ajustements basés sur les fondamentaux des entreprises 
    ont permis une meilleure capture des opportunités de marché tout en limitant les impacts des fluctuations importantes.
    """)


# Conclusion
st.subheader("📈 Conclusion")
st.markdown("""
En conclusion, l’analyse des **10 meilleures entreprises**, indépendamment du secteur, montre que le rebalancement a permis 
d'améliorer les rendements de l'indice tout en gérant efficacement les risques associés. Cela met en lumière l’importance 
de sélectionner des entreprises solides financièrement, avec des pondérations dynamiques, pour optimiser les performances d’un indice global.
""")


# Section Momentum
st.title("📈 Création d'un Indice de Style Momentum")
st.markdown("""
Le style d’investissement **Momentum** repose sur l'idée selon laquelle les entreprises qui ont récemment surperformé continueront à générer de bonnes performances dans un futur proche. 
Ce style s’appuie sur un principe clé des marchés financiers : les tendances peuvent persister, notamment grâce au comportement des investisseurs qui suivent ces mouvements.

### Objectif de cette analyse
Dans cette section, nous allons construire un **indice de style Momentum**, en identifiant les entreprises qui ont obtenu les meilleurs rendements au cours d’une période donnée. 
Les étapes principales comprennent :
1. La sélection des entreprises en fonction de leurs rendements cumulés.
2. L’attribution de pondérations basées soit sur des scores proportionnels au rendement, soit de manière équivalente.
3. La création d’un indice qui reflète la performance de ces entreprises Momentum.

### Méthodologie
1. **Calcul des rendements cumulés** : Nous utilisons les prix historiques des entreprises pour calculer leurs rendements cumulés sur une période donnée (paramétrable). Ces rendements serviront de base pour sélectionner les entreprises Momentum.
2. **Sélection des meilleures entreprises** : Un pourcentage des entreprises ayant les meilleurs rendements sera retenu pour construire l’indice.
3. **Pondérations des entreprises** :
    - **Pondération équivalente** : Chaque entreprise sélectionnée contribue de manière égale à l’indice.
    - **Pondération basée sur les scores Momentum** : Les entreprises ayant des rendements plus élevés obtiennent une pondération plus importante.
4. **Benchmarking** : L’indice Momentum sera comparé aux benchmarks globaux SPX et SXXP pour évaluer sa performance relative.

### Pourquoi le Momentum ?
Le style Momentum est particulièrement intéressant dans des marchés caractérisés par des tendances fortes. Il est souvent utilisé dans des stratégies quantitatives car il repose sur des calculs objectifs et reproductibles. Cependant, ce style peut être sensible aux retournements soudains de marché, ce qui en fait une stratégie dynamique nécessitant une gestion rigoureuse.

### Résultat attendu
L’indice Momentum ainsi créé nous permettra de visualiser :
- La capacité des entreprises Momentum à surperformer sur une période donnée.
- La comparaison avec des benchmarks pour juger de la pertinence de cette stratégie dans différents contextes de marché.
""")


# Paramètres interactifs pour l'indice Momentum
momentum_period = st.number_input(
    "Période de calcul du Momentum (en mois) :", min_value=1, max_value=24, value=6, key="momentum_period"
)
top_percent = st.slider(
    "Pourcentage des entreprises à inclure dans l'indice :", min_value=10, max_value=100, value=30, key="momentum_top_percent"
)
start_date = st.date_input("Date de début", value=pd.to_datetime('2010-04-01'), key="momentum_start_date")
end_date = st.date_input("Date de fin", value=pd.to_datetime('2018-12-28'), key="momentum_end_date")

try:
    # Étape 1 : Applique filter_prices à toutes les entreprises
    all_spx_tickers = spx_prices.columns[1:]  # Tous les tickers SPX (exclut la colonne Dates)
    all_sxxp_tickers = sxxp_prices.columns[1:]  # Tous les tickers SXXP (exclut la colonne Dates)

    spx_filtered, spx_excluded = filter_prices(spx_prices, all_spx_tickers, start_date, end_date)
    sxxp_filtered, sxxp_excluded = filter_prices(sxxp_prices, all_sxxp_tickers, start_date, end_date)

    if spx_filtered.empty or sxxp_filtered.empty:
        st.error("Les données filtrées pour SPX ou SXXP sont vides. Vérifiez vos dates ou tickers.")
        st.stop()

    # Vérification des doublons dans les colonnes des DataFrames filtrés
    spx_filtered = spx_filtered.loc[:, ~spx_filtered.columns.duplicated()]
    sxxp_filtered = sxxp_filtered.loc[:, ~sxxp_filtered.columns.duplicated()]

    # Étape 2 : Conversion des prix SXXP en dollars
    sxxp_usd = convert_usd(sxxp_filtered, forex_data)

    # Vérification des doublons après conversion
    sxxp_usd = sxxp_usd.loc[:, ~sxxp_usd.columns.duplicated()]

    # Étape 3 : Fusionner les prix SPX et SXXP
    combined_prices = merge_dates(spx_filtered, sxxp_usd)

    # Suppression des colonnes dupliquées dans les données fusionnées
    if combined_prices.columns.duplicated().any():
        st.warning("Des colonnes dupliquées ont été détectées et supprimées.")
        combined_prices = combined_prices.loc[:, ~combined_prices.columns.duplicated()]

    if combined_prices.empty:
        st.error("Les données combinées pour SPX et SXXP sont vides. Vérifiez vos filtres ou données d'entrée.")
        st.stop()

    # Étape 4 : Normalisation des prix
    normalized_prices = normalize_prices(combined_prices)

    # Vérification des données après normalisation
    st.write("📊 **Aperçu des données après traitement et normalisation :**")
    st.dataframe(normalized_prices.head())

    # Gestion des colonnes constantes ou dupliquées
    constant_cols = normalized_prices.loc[:, (normalized_prices.nunique() <= 1)]
    if not constant_cols.empty:
        st.warning(f"Certaines colonnes sont constantes (ou vides) : {list(constant_cols.columns)}")
        normalized_prices = normalized_prices.drop(columns=constant_cols.columns)

    if normalized_prices.columns.duplicated().any():
        st.warning("Des colonnes dupliquées ont été détectées et supprimées dans les données normalisées.")
        normalized_prices = normalized_prices.loc[:, ~normalized_prices.columns.duplicated()]

    if normalized_prices.shape[1] <= 1:
        st.error("Aucune colonne valide disponible après la normalisation. Vérifiez les données d'entrée.")
        st.stop()

    # Étape 5 : Calcul des rendements cumulés
    st.subheader("📊 Calcul des rendements cumulés")
    try:
        momentum_returns = normalized_prices.set_index('Dates').copy()

        if momentum_returns.empty:
            raise ValueError("Les données normalisées sont vides. Impossible de calculer les rendements.")

        daily_returns = momentum_returns.pct_change().add(1)
        daily_returns = daily_returns.fillna(1)

        rolling_returns = daily_returns.rolling(window=momentum_period * 21, min_periods=1)
        momentum_cum_returns = rolling_returns.apply(np.prod, raw=True) - 1

        if momentum_cum_returns.isna().all(axis=None):
            raise ValueError("Toutes les colonnes des rendements cumulés sont None. Vérifiez les données.")

        st.write("🔍 **Rendements cumulés calculés :**")
        st.dataframe(momentum_cum_returns.head())

    except Exception as e:
        st.error(f"Erreur : {e}")
        st.stop()

    # Étape 6 : Sélection des entreprises Momentum
    st.subheader("⚖️ Sélection des entreprises Momentum")
    if not momentum_cum_returns.empty:
        momentum_sorted = momentum_cum_returns.iloc[-1].sort_values(ascending=False)
        st.write("🔍 **Scores Momentum triés :**")
        st.dataframe(momentum_sorted)

        top_n = int(len(momentum_sorted) * (top_percent / 100))
        if top_n <= 0:
            st.error("Le pourcentage des entreprises sélectionnées est trop faible. Augmentez le pourcentage.")
            st.stop()

        selected_tickers = list(dict.fromkeys(momentum_sorted.head(top_n).index.tolist()))
        st.write(f"**Entreprises sélectionnées ({top_percent}% des meilleures performances) :**")
        st.write(selected_tickers)

        # Étape 7 : Calcul des pondérations Momentum
        st.subheader("📏 Calcul des pondérations Momentum")

        if not momentum_sorted.empty:
            selected_scores = momentum_sorted.loc[selected_tickers]

            valid_tickers = list(set(selected_scores.index) & set(momentum_returns.columns))
            if not valid_tickers:
                st.error("Aucun ticker valide trouvé pour construire l'indice Momentum.")
                st.stop()

            selected_scores = selected_scores.loc[valid_tickers]
            st.write(f"📊 **Tickers valides après filtrage** : {len(valid_tickers)} entreprises.")
            st.dataframe(selected_scores)

            weighting_strategy = st.radio(
                "Stratégie de pondération",
                ("Pondération équivalente", "Pondération basée sur le score Momentum"),
                index=1
            )

            weights = pd.Series(1 / len(selected_scores), index=selected_scores.index) if weighting_strategy == "Pondération équivalente" else selected_scores / selected_scores.sum()

            try:
                momentum_prices = momentum_returns[valid_tickers]
                momentum_index_values = (momentum_prices * weights.values).sum(axis=1)
                momentum_index = pd.DataFrame({
                    'Dates': momentum_prices.index,
                    'Index_Value': (momentum_index_values / momentum_index_values.iloc[0]) * 100
                }).reset_index(drop=True)

                st.subheader("📈 Visualisation de l'indice Momentum avec Benchmarks")

                try:
                    index_data = donnees['index_data']
                    forex_data = donnees['forex_data']

                    spx_index = prepare_reference_index(index_data, "SPX Index")
                    sxxp_index = prepare_reference_index(index_data, "SXXP Index")
                    sxxp_index_usd = convert_usd(sxxp_index, forex_data)

                    index_with_benchmarks = pd.merge(momentum_index, spx_index, on='Dates', how='inner', suffixes=('', '_SPX'))
                    index_with_benchmarks = pd.merge(index_with_benchmarks, sxxp_index_usd, on='Dates', how='inner', suffixes=('', '_SXXP'))

                    columns_to_adjust = ['Index_Value', 'Index_Value_SPX', 'Index_Value_SXXP']
                    index_with_benchmarks = adjust_to_base_100(index_with_benchmarks, columns_to_adjust)

                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value'], label="Indice Momentum", linewidth=2, color="blue")
                    ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value_SPX'], label="Benchmark SPX", linestyle="--", color="orange")
                    ax.plot(index_with_benchmarks['Dates'], index_with_benchmarks['Index_Value_SXXP'], label="Benchmark SXXP (en USD)", linestyle=":", color="green")

                    ax.set_title("Indice Momentum avec Benchmarks (Normalisés à 100)", fontsize=16)
                    ax.set_xlabel("Dates", fontsize=12)
                    ax.set_ylabel("Valeur Normalisée (Base 100)", fontsize=12)
                    ax.legend(fontsize=12)
                    ax.grid(True, linestyle='--', alpha=0.6)

                    save_figure(fig, "Indice_Momentum_Avec_Benchmark.png")
                    st.pyplot(fig)

                except Exception as e:
                    st.error(f"Erreur lors de la création du graphique avec benchmarks : {e}")

            except Exception as e:
                st.error(f"Erreur lors de la construction de l'indice Momentum : {e}")

    else:
        st.error("Les rendements cumulés sont vides. Impossible de calculer les pondérations Momentum.")

except Exception as e:
    st.error(f"Erreur générale : {e}")
# Étape 9 : Analyse des statistiques de l'indice Momentum
try:
    stats_df_momentum, alpha_momentum, beta_momentum, merged_data_momentum = stats_index(momentum_index)

    if stats_df_momentum is not None:
        st.write("✔️ Les statistiques principales de l'indice Momentum ont été calculées.")
    else:
        st.error("❌ Impossible de calculer les statistiques de l'indice Momentum.")

    # Étape 10 : Analyse approfondie des statistiques
    st.subheader("📊 Analyse approfondie des statistiques de l'indice Momentum")
    analyze_statistics_and_alpha(
        stats_df=stats_df_momentum,
        filename="temp_reports/Statistiques_Indice_Momentum.png",
        merged_data=merged_data_momentum,
        alpha_value=alpha_momentum,
        beta_value=beta_momentum
    )

except Exception as e:
    st.error(f"Erreur lors de l'analyse des statistiques : {e}")

# Analyse des Résultats de l'Indice Momentum
st.subheader("📝 Analyse des Résultats de l'Indice Momentum")

# Performances de l'Indice Momentum
with st.expander("🔍 Performances de l'Indice Momentum", expanded=False):
    st.markdown("""
    L'indice Momentum, construit sur la période 2010-2019, affiche des performances remarquables :  
    - **Rendement total : 217,89%**  
    - **Rendement annualisé : 14,39%**  
    - **Volatilité annualisée : 13,53%**  

    Cette performance est accompagnée d'un **Ratio de Sharpe de 1,06**, indiquant que l'indice offre des rendements satisfaisants par rapport aux risques encourus.

    En termes de risques, le **Max Drawdown** est limité à **-19,36%**, ce qui reflète une résilience significative face aux baisses de marché. Les entreprises sélectionnées, caractérisées par des tendances de performance solides, ont contribué à cette stabilité.
    """)

# Comparaison avec les Benchmarks
with st.expander("🔍 Comparaison avec les Benchmarks", expanded=False):
    st.markdown("""
    L'analyse comparative avec les benchmarks **SPX** et **SXXP** montre que l'indice Momentum surperforme ces derniers :  
    - **Benchmark SPX** : L'indice Momentum dépasse constamment le SPX en termes de performance totale et annualisée.  
    - **Benchmark SXXP (en USD)** : Bien que le SXXP ait une volatilité plus faible, ses rendements sont significativement inférieurs.  
      
    Ces résultats démontrent la pertinence de la stratégie Momentum pour capturer les entreprises à forte dynamique de croissance, tout en gérant efficacement les risques.
    """)

# Résumé Visuel
st.subheader("📊 Résumé Visuel")
with st.expander("📈 Visualisation des Graphiques", expanded=False):
    st.markdown("""
    Le graphique affiché plus haut illustre l'évolution de l'indice Momentum en comparaison avec les benchmarks :  
    - **Indice Momentum** : Une croissance marquée avec une surperformance claire sur l'ensemble de la période.  
    - **SPX et SXXP** : Bien que ces indices suivent une trajectoire ascendante, leur performance est inférieure à celle de l'indice Momentum.  

    L'indice Momentum montre également une meilleure résilience après les périodes de correction, mettant en évidence l'importance d'une sélection rigoureuse des entreprises.
    """)

# Conclusion
st.subheader("📈 Conclusion")
st.markdown("""
En conclusion, l'indice Momentum offre des performances robustes grâce à une stratégie basée sur les entreprises ayant une forte dynamique.  
En surperformant les benchmarks traditionnels, il met en lumière la pertinence d'une stratégie active pour optimiser les rendements tout en gérant efficacement les risques.
""")

st.title("📤 Envoi d'analyse financière par email")
st.subheader("✉️ Préparation et pré-envoi de l'email")

# Variables pour l'email
destinataire = st.text_input("Adresse email du destinataire :", "destinataire@example.com")
sujet = "Analyse Financière Personnalisée"
corps_message = f"""
Bonjour,

Voici l'analyse pour le secteur sélectionné : **{secteur_choisi}** 
et les sous-secteurs suivants : **{', '.join(sous_secteurs_choisis) or 'Aucun sous-secteur sélectionné'}**.

Partie 1 : Indices Sectoriels
- Indice sectoriel : Construit sur la base des données historiques normalisées à une base de 100.
- Analyse par pays (optionnelle) : 
  Les pays sélectionnés pour cette analyse sont :  
  {', '.join(selected_countries) or 'Tous les pays inclus'}.
  Cet indice met en avant les performances spécifiques à chaque région géographique.

Partie 2 : Indice de Solidité Financière
Cet indice est calculé pour l'ensemble des entreprises, en se basant sur les critères fondamentaux suivants :  
- Ratio Prix/Actif Net (Price-to-Book Ratio).  
- Ratio Cours/Bénéfices inversé (Inverse Price-to-Earnings Ratio).  
- Rendement des Dividendes.  
- Capitalisation Boursière.  

Partie 3 : Indice Momentum
Cet indice est construit pour l'ensemble des entreprises, en identifiant celles ayant les meilleures performances passées sur une période définie.  
Les pondérations des entreprises sélectionnées sont calculées en fonction de leurs rendements cumulés.

Cordialement,  
"""

# Encode l'URL pour le lien mailto
mailto_link = f"mailto:{destinataire}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps_message)}"

if st.button("📤 Ouvrir l'application de messagerie"):
    st.markdown(f"[Cliquez ici pour préparer l'email]({mailto_link})", unsafe_allow_html=True)

if st.button("📥 Télécharger les graphiques et résultats"):
    zip_buffer = create_zip()
    zip_buffer.seek(0)

    st.download_button(
        label="📁 Télécharger les résultats (.zip)",
        data=zip_buffer,
        file_name="analyse_financiere.zip",
        mime="application/zip"
    )

