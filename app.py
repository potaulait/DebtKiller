def courbe_evolution_valeur_actifs(df_inv, couleurs, selection=None):
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    def ensure_hist_list(hist):
        if isinstance(hist, list):
            return hist
        if pd.isnull(hist):
            return []
        try:
            import ast
            val = ast.literal_eval(hist)
            if isinstance(val, list):
                return val
            return []
        except Exception:
            return []

    def ensure_val_hist_list(valhist):
        if isinstance(valhist, list):
            return valhist
        if pd.isnull(valhist):
            return []
        try:
            import ast
            val = ast.literal_eval(valhist)
            if isinstance(val, list):
                return val
            return []
        except Exception:
            return []

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#181820")  # Fond sombre

    if selection is None:
        actifs = df_inv.groupby(["Nom", "Type"]).first().reset_index()
        selection = actifs['Nom'].tolist()

    for _, row in df_inv.iterrows():
        nom = row["Nom"]
        if nom not in selection:
            continue

        hist_apports = ensure_hist_list(row.get("Historique", []))
        hist_valeurs = ensure_val_hist_list(row.get("valeur_actuelle_hist", []))

        # Combine all events (apports and maj valeur) in a timeline, sorted by date
        timeline = []
        cumul = 0.0
        for h in hist_apports:
            date_ = to_date(h.get("date"))
            try:
                montant = float(h.get("montant", 0.0))
            except:
                montant = 0.0
            cumul += montant
            timeline.append({"date": date_, "valeur": cumul, "type": "apport"})
        # Valeurs réelles = maj de valeur
        for h in hist_valeurs:
            date_ = to_date(h.get("date"))
            try:
                valeur = float(h.get("valeur", 0.0))
            except:
                valeur = 0.0
            timeline.append({"date": date_, "valeur": valeur, "type": "maj_valeur"})
        # Trie la timeline par date croissante
        timeline = sorted(timeline, key=lambda x: x["date"])
        # Pour chaque point, si c'est un apport, cumule, si c'est une maj_valeur, remplace
        points = []
        current_val = 0.0
        for t in timeline:
            if t["type"] == "apport":
                current_val = t["valeur"]
            elif t["type"] == "maj_valeur":
                current_val = t["valeur"]
            points.append({"date": t["date"], "valeur": current_val})
        if len(points) >= 2:
            dates = [p["date"] for p in points]
            valeurs = [p["valeur"] for p in points]
            color = couleurs.get(nom, "#f5426f")
            ax.plot(
                dates, valeurs,
                marker="o", linestyle="-", color=color, linewidth=3,
                markersize=6, markerfacecolor="white", alpha=0.90, label=nom
            )
        elif len(points) == 1:
            # Juste un point unique
            p = points[0]
            color = couleurs.get(nom, "#f5426f")
            ax.plot([p["date"]], [p["valeur"]],
                    marker="o", linestyle="None", color=color,
                    markersize=7, markerfacecolor="white", alpha=0.90, label=nom)
    ax.set_facecolor("#181820")
    ax.grid(True, color="#333", linestyle="--", alpha=0.5)
    ax.spines['top'].set_color('#555')
    ax.spines['bottom'].set_color('#aaa')
    ax.spines['right'].set_color('#555')
    ax.spines['left'].set_color('#aaa')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(colors='white', labelsize=10)
    ax.set_title("Évolution de la valeur actuelle des actifs", fontsize=18, color="white", pad=20)
    ax.set_xlabel("Date", fontsize=14, color="white", labelpad=12)
    ax.set_ylabel(f"Valeur actuelle ({devise_affichage})", fontsize=14, color="white", labelpad=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
    fig.autofmt_xdate(rotation=20)
    ax.legend(loc="best", fontsize=13, frameon=True, facecolor="#24243a", edgecolor="#666")
    plt.tight_layout()
    return fig
import streamlit as st
import pandas as pd
from datetime import datetime, date
import matplotlib.pyplot as plt
import os

# ----------- PIE GLOSSY UTILITY -----------
def glossy_pie(ax, values, labels, colors, title):
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        startangle=90,
        colors=colors,
        autopct=lambda p: f'{p:.0f}%' if p > 5 else '',
        wedgeprops={"width": 0.45, "edgecolor": "white"},
        pctdistance=0.85,
        textprops={"fontsize": 10, "color": "black"}
    )
    # Ajout d’un highlight glossy (faux éclat circulaire en haut du donut)
    import matplotlib.patches as mpatches
    centre_circle = plt.Circle((0, 0), 0.63, color='white', fc='white', linewidth=0)
    ax.add_artist(centre_circle)
    highlight = plt.Circle((0, 0.13), 0.43, color='white', alpha=0.13, linewidth=0)
    ax.add_artist(highlight)
    ax.set_title(title, fontsize=11, pad=15)
    ax.axis('equal')
    # Légende propre à droite
    ax.legend(wedges, labels, title="Catégorie", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)

# ----------- LOCALE FR_CH EN TÊTE -----------
import locale
try:
    locale.setlocale(locale.LC_ALL, 'fr_CH.UTF-8')
except locale.Error:
    pass

st.set_page_config(page_title="Gestion Financière Premium", layout="centered")

# ----------- INITIALISATION SESSIONS -----------
if 'transactions' not in st.session_state:
    st.session_state['transactions'] = pd.DataFrame(columns=[
        "Date", "Type", "Catégorie", "Montant", "Description", "Dette liée", "Crédit lié", "Projet lié"
    ])
if 'dettes' not in st.session_state:
    st.session_state['dettes'] = pd.DataFrame(columns=[
        "ID", "Créancier", "Montant initial", "Montant restant", "Mensualité", "Date début",
        "Prochaine échéance", "Catégorie", "Statut", "Historique", "Couleur"
    ])
if 'dette_id' not in st.session_state:
    st.session_state['dette_id'] = 1

if 'credits' not in st.session_state:
    st.session_state['credits'] = pd.DataFrame(columns=[
        "ID", "Créancier", "Montant initial", "Montant restant", "Mensualité", "Date début",
        "Prochaine échéance", "Statut", "Historique", "Couleur"
    ])
if 'credit_id' not in st.session_state:
    st.session_state['credit_id'] = 1

if 'projets' not in st.session_state:
    st.session_state['projets'] = pd.DataFrame(columns=[
        "ID", "Nom", "Objectif", "Montant atteint", "Description", "Couleur"
    ])
if 'projet_id' not in st.session_state:
    st.session_state['projet_id'] = 1

if 'investissements' not in st.session_state:
    st.session_state['investissements'] = pd.DataFrame(columns=[
        "ID", "Type", "Nom", "Montant investi", "Valeur actuelle", "Intérêts reçus", "Date", "Historique", "Couleur"
    ])
if 'investissement_id' not in st.session_state:
    st.session_state['investissement_id'] = 1

# ----------- DATE FR ----------- 
def fr_date(dt):
    import pandas as pd
    import numpy as np
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%d/%m/%Y")
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    # Gestion pandas Timestamp
    if "Timestamp" in str(type(dt)):
        try:
            return pd.to_datetime(dt).strftime("%d/%m/%Y")
        except:
            pass
    # Gestion numpy.datetime64
    if "datetime64" in str(type(dt)):
        try:
            return pd.to_datetime(dt).strftime("%d/%m/%Y")
        except:
            pass
    if isinstance(dt, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(dt, fmt).strftime("%d/%m/%Y")
            except:
                continue
    return str(dt)

def to_date(dt):
    if isinstance(dt, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(dt, fmt).date()
            except:
                continue
        return datetime.today().date()
    if isinstance(dt, datetime):
        return dt.date()
    if isinstance(dt, date):
        return dt
    return datetime.today().date()

# ---------- SAUVEGARDE AUTO ----------
def save_dataframes(user_prefix="default"):
    st.session_state['transactions'].to_csv(f"{user_prefix}_transactions.csv", index=False)
    st.session_state['dettes'].to_csv(f"{user_prefix}_dettes.csv", index=False)
    st.session_state['credits'].to_csv(f"{user_prefix}_credits.csv", index=False)
    st.session_state['projets'].to_csv(f"{user_prefix}_projets.csv", index=False)
    st.session_state['investissements'].to_csv(f"{user_prefix}_investissements.csv", index=False)

def load_dataframes(user_prefix="default"):
    if os.path.exists(f"{user_prefix}_transactions.csv"):
        st.session_state['transactions'] = pd.read_csv(f"{user_prefix}_transactions.csv")
        # Force affichage date en français (jj/mm/aaaa)
        if "Date" in st.session_state['transactions'].columns:
            st.session_state['transactions']["Date"] = st.session_state['transactions']["Date"].apply(fr_date)
    if os.path.exists(f"{user_prefix}_dettes.csv"):
        st.session_state['dettes'] = pd.read_csv(f"{user_prefix}_dettes.csv")
        # Force affichage date en français (jj/mm/aaaa)
        if "Date début" in st.session_state['dettes'].columns:
            st.session_state['dettes']["Date début"] = st.session_state['dettes']["Date début"].apply(fr_date)
        if "Prochaine échéance" in st.session_state['dettes'].columns:
            st.session_state['dettes']["Prochaine échéance"] = st.session_state['dettes']["Prochaine échéance"].apply(fr_date)
    if os.path.exists(f"{user_prefix}_credits.csv"):
        st.session_state['credits'] = pd.read_csv(f"{user_prefix}_credits.csv")
        # Force affichage date en français (jj/mm/aaaa)
        if "Date début" in st.session_state['credits'].columns:
            st.session_state['credits']["Date début"] = st.session_state['credits']["Date début"].apply(fr_date)
        if "Prochaine échéance" in st.session_state['credits'].columns:
            st.session_state['credits']["Prochaine échéance"] = st.session_state['credits']["Prochaine échéance"].apply(fr_date)
    if os.path.exists(f"{user_prefix}_projets.csv"):
        st.session_state['projets'] = pd.read_csv(f"{user_prefix}_projets.csv")
        # Pas de colonne date à forcer ici
    if os.path.exists(f"{user_prefix}_investissements.csv"):
        st.session_state['investissements'] = pd.read_csv(f"{user_prefix}_investissements.csv")
        # Force affichage date en français (jj/mm/aaaa)
        if "Date" in st.session_state['investissements'].columns:
            st.session_state['investissements']["Date"] = st.session_state['investissements']["Date"].apply(fr_date)

# ---------- PROFIL UTILISATEUR ----------
st.sidebar.title("Paramètres & Sauvegarde")
user_prefix = st.sidebar.text_input("Nom du profil/compte", value="default")
# --- Choix devise ---
devise_affichage = st.sidebar.selectbox(
    "Devise d'affichage", ["CHF", "EUR", "USD"], index=0
)
# --- Taux de conversion simples ---
taux_conversion = {
    "CHF": {"CHF": 1, "EUR": 0.98, "USD": 1.12},
    "EUR": {"CHF": 1.02, "EUR": 1, "USD": 1.15},
    "USD": {"CHF": 0.90, "EUR": 0.87, "USD": 1},
}
def convertir(montant, depuis, vers):
    if depuis == vers:
        return montant
    return montant * taux_conversion[depuis][vers]

if st.sidebar.button("Charger ce profil"):
    # Vider tout l'état sauf le user_prefix
    keys = list(st.session_state.keys())
    for key in keys:
        if key != "user_prefix":
            del st.session_state[key]
    load_dataframes(user_prefix)
    st.success(f"Profil '{user_prefix}' chargé !")
    st.rerun()  # Force le refresh avec le bon profil

import matplotlib.dates as mdates

# ----------- INITIALISATION CASH ----------
if 'cash' not in st.session_state:
    st.session_state['cash'] = {
        "historique": pd.DataFrame(columns=["Date", "Type", "Montant", "Commentaire"]),
        "objectif": 1000.0
    }
    # Pour compatibilité, on stocke l'objectif dans la clé 'objectif'
if isinstance(st.session_state['cash'], dict):
    if "historique" not in st.session_state['cash']:
        st.session_state['cash']["historique"] = pd.DataFrame(columns=["Date", "Type", "Montant", "Commentaire"])
    if "objectif" not in st.session_state['cash']:
        st.session_state['cash']["objectif"] = 1000.0
else:
    # Migration ancienne version éventuelle
    st.session_state['cash'] = {
        "historique": pd.DataFrame(columns=["Date", "Type", "Montant", "Commentaire"]),
        "objectif": 1000.0
    }

# ----------- ONGLET PRINCIPAUX ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💸 Transactions",
    "💳 Dettes",
    "🏦 Crédits",
    "🎯 Projets",
    "📈 Investissement",
    "🩺 Santé du portefeuille",
    "📊 Pilotage prévisionnel"
])
# ============= PILOTAGE PREVISIONNEL =============
with tab7:
    st.title("📊 Pilotage prévisionnel")
    st.markdown("Planifie, anticipe, pilote… et valide chaque étape !")

    with st.expander("💰 Revenus prévisionnels", expanded=False):
        st.info("Ajoute ici tes revenus attendus sur la période souhaitée.")

    with st.expander("📤 Dépenses prévisionnelles", expanded=False):
        st.info("Liste ici toutes tes dépenses prévues : loyer, factures, charges fixes…")

    with st.expander("🏦 Remboursements de dettes", expanded=False):
        st.info("Prévoyance de chaque mensualité ou remboursement à venir.")

    with st.expander("💳 Paiements crédits", expanded=False):
        st.info("Prévois le paiement de tes crédits sur chaque période.")

    with st.expander("🎯 Objectifs/Projets à financer", expanded=False):
        st.info("Prévisions d’épargne pour objectifs, vacances, achats majeurs, etc.")

    with st.expander("📈 Investissements programmés", expanded=False):
        st.info("Investissements récurrents, DCA, ou apports prévus à venir.")

    with st.expander("🟣 État de l’épargne de précaution", expanded=False):
        st.info("Estime ton fonds d’urgence, prévois son évolution et sécurise ta trésorerie.")

    with st.expander("⚡ Alertes & rappels à venir", expanded=False):
        st.info("Configure des alertes automatiques pour chaque événement clé ou anomalie.")

    with st.expander("🧠 Visualisation dynamique", expanded=False):
        st.info("Bientôt ici : une visualisation de l’évolution de ton solde prévisionnel avec courbes, points-clés (remboursement total, objectif atteint…), et distinction des validations réelles/prévisionnelles.")

    with st.expander("🔎 Historique des prévisions et validations", expanded=False):
        st.info("Tu pourras revenir sur tous les écarts entre prévu/réalisé, modifier ou valider chaque point, et retrouver la trace de tes progrès.")

# ============= TRANSACTIONS =============
with tab1:
    st.title("💸 Suivi Transactions")

    # CATÉGORIES
    base_categories = {
        "Entrée": ["Salaire", "Remboursement", "Aide", "Vente", "Cash", "Autres"],
        "Sortie": ["Loyer", "Courses", "Assurance", "Électricité", "Abonnement", "Santé", "Transports", "Projet", "Investissement", "Cash", "Autres"],
        "Remboursement de dette": [],
        "Paiement crédit": [],
        "Transfert interne": ["Retrait cash", "Dépôt cash"]
    }

    st.header("Ajouter une transaction")
    col1, col2, col3 = st.columns([1, 1, 2])

    projets_liste = st.session_state['projets']["Nom"].tolist()

    with col1:
        type_transac = st.selectbox(
            "Type",
            ["Entrée", "Sortie", "Remboursement de dette", "Paiement crédit", "Transfert interne"]
        )

    dette_choisie, credit_choisi, projet_choisi = "", "", ""
    if type_transac == "Remboursement de dette":
        dettes_en_cours = st.session_state['dettes'][st.session_state['dettes']["Statut"] == "En cours"]
        options = dettes_en_cours["Créancier"].tolist()
        if options:
            dette_choisie = st.selectbox("Sélectionne la dette à rembourser", options, key="trans_dette_select")
        else:
            st.warning("Aucune dette à rembourser pour le moment.")
    elif type_transac == "Paiement crédit":
        credits_en_cours = st.session_state['credits'][st.session_state['credits']["Statut"] == "En cours"]
        options_credit = credits_en_cours["Créancier"].tolist()
        if options_credit:
            credit_choisi = st.selectbox("Sélectionne le crédit à payer", options_credit, key="trans_credit_select")
        else:
            st.warning("Aucun crédit à payer pour le moment.")
    elif type_transac == "Sortie" and projets_liste:
        projet_choisi = st.selectbox("Associer à un projet", projets_liste, key="trans_projet")

    # Ajout : gestion Investissement
    investissement_choisi = None
    show_ajout_actif_btn = False
    if type_transac == "Sortie" and 'investissements' in st.session_state:
        cat_list = base_categories["Sortie"]
        # On regarde la catégorie choisie
        if 'trans_cat' in st.session_state:
            cat_transac_val = st.session_state['trans_cat']
        elif 'trans_cat_transfert_interne' in st.session_state:
            cat_transac_val = st.session_state['trans_cat_transfert_interne']
        else:
            cat_transac_val = ""
        if cat_transac_val == "Investissement":
            inv_df = st.session_state['investissements']
            actifs_liste = inv_df["Nom"].tolist() if not inv_df.empty else []
            if actifs_liste:
                investissement_choisi = st.selectbox("Associer à un actif", actifs_liste, key="trans_invest_actif")
            else:
                show_ajout_actif_btn = True

    with col2:
        if type_transac == "Remboursement de dette":
            cat_transac = "Remboursement de dette"
        elif type_transac == "Paiement crédit":
            cat_transac = "Paiement crédit"
        elif type_transac == "Transfert interne":
            cat_transac = st.selectbox("Catégorie", base_categories[type_transac], key="trans_cat_transfert_interne")
        else:
            cat_transac = st.selectbox("Catégorie", base_categories[type_transac], key="trans_cat")

    with col3:
        montant = st.number_input("Montant (CHF : devise de référence)", min_value=0.0, step=1.0, format="%.2f", key="trans_montant")

    date_val = st.date_input("Date", value=datetime.today(), key="trans_date")
    description = st.text_input("Description (facultatif)", key="trans_desc")

    if show_ajout_actif_btn:
        st.warning("Aucun actif d'investissement n'existe encore.")
        if st.button("Ajouter un actif", key="btn_ajouter_actif_depuis_trans"):
            st.session_state['tab_to_focus'] = "Investissement"
            st.switch_page("app.py")

    if st.button("Ajouter", key="trans_ajouter"):
        if montant > 0:
            dette_liee, credit_lie, projet_lie = "", "", ""
            montant_effectif = montant if type_transac == "Entrée" else -montant
            # Gestion Transfert interne
            if type_transac == "Transfert interne":
                # On gère deux écritures
                cash_hist = st.session_state['cash']["historique"]
                if cat_transac == "Retrait cash":
                    # 1. Sortie du compte courant
                    new_row1 = {
                        "Date": fr_date(date_val),
                        "Type": "Sortie",
                        "Catégorie": "Transfert interne – Retrait cash",
                        "Montant": -abs(montant),
                        "Description": description,
                        "Dette liée": "",
                        "Crédit lié": "",
                        "Projet lié": ""
                    }
                    # 2. Entrée dans le cash dispo
                    new_row2 = {
                        "Date": fr_date(date_val),
                        "Type": "Entrée",
                        "Catégorie": "Transfert interne – Retrait cash",
                        "Montant": abs(montant),
                        "Description": description,
                        "Dette liée": "",
                        "Crédit lié": "",
                        "Projet lié": ""
                    }
                    st.session_state['transactions'] = pd.concat(
                        [pd.DataFrame([new_row1, new_row2]), st.session_state['transactions']], ignore_index=True
                    )
                    # Ajout au cash dispo
                    cash_row = {
                        "Date": fr_date(date_val),
                        "Type": "Ajout",
                        "Montant": abs(montant),
                        "Commentaire": f"Transfert interne – Retrait cash. {description}"
                    }
                    st.session_state['cash']["historique"] = pd.concat(
                        [pd.DataFrame([cash_row]), cash_hist], ignore_index=True
                    )
                    save_dataframes(user_prefix)
                    st.success("Transfert interne – Retrait cash enregistré !")
                elif cat_transac == "Dépôt cash":
                    # 1. Sortie du cash dispo
                    # Avant, vérifier que cash dispo suffisant !
                    cash_total = 0.0
                    if not cash_hist.empty:
                        cash_total = cash_hist.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1).sum()
                    if montant > cash_total:
                        st.error("Impossible : le montant du dépôt cash dépasse le cash disponible.")
                    else:
                        new_row1 = {
                            "Date": fr_date(date_val),
                            "Type": "Sortie",
                            "Catégorie": "Transfert interne – Dépôt cash",
                            "Montant": -abs(montant),
                            "Description": description,
                            "Dette liée": "",
                            "Crédit lié": "",
                            "Projet lié": ""
                        }
                        new_row2 = {
                            "Date": fr_date(date_val),
                            "Type": "Entrée",
                            "Catégorie": "Transfert interne – Dépôt cash",
                            "Montant": abs(montant),
                            "Description": description,
                            "Dette liée": "",
                            "Crédit lié": "",
                            "Projet lié": ""
                        }
                        st.session_state['transactions'] = pd.concat(
                            [pd.DataFrame([new_row2, new_row1]), st.session_state['transactions']], ignore_index=True
                        )
                        # Retrait du cash dispo
                        cash_row = {
                            "Date": fr_date(date_val),
                            "Type": "Retrait",
                            "Montant": abs(montant),
                            "Commentaire": f"Transfert interne – Dépôt cash. {description}"
                        }
                        st.session_state['cash']["historique"] = pd.concat(
                            [pd.DataFrame([cash_row]), cash_hist], ignore_index=True
                        )
                        save_dataframes(user_prefix)
                        st.success("Transfert interne – Dépôt cash enregistré !")
                else:
                    st.error("Veuillez choisir une sous-catégorie de transfert interne.")
            else:
                # Gestion Investissement : Sortie > Investissement
                if type_transac == "Sortie" and (
                    (('trans_cat' in st.session_state and st.session_state['trans_cat'] == "Investissement") or
                     ('trans_cat_transfert_interne' in st.session_state and st.session_state['trans_cat_transfert_interne'] == "Investissement"))
                ):
                    # Sélection actif obligatoire
                    inv_df = st.session_state['investissements']
                    actifs_liste = inv_df["Nom"].tolist() if not inv_df.empty else []
                    actif_cible = None
                    if 'trans_invest_actif' in st.session_state:
                        actif_cible = st.session_state['trans_invest_actif']
                    if not actifs_liste or not actif_cible:
                        st.error("Merci de sélectionner un actif d'investissement.")
                        st.stop()
                    idx_actif = inv_df[inv_df["Nom"] == actif_cible].index
                    if len(idx_actif) == 0:
                        st.error("Impossible de retrouver l'actif sélectionné.")
                        st.stop()
                    idx_actif = idx_actif[0]
                    # Historique d'apport
                    histo = inv_df.at[idx_actif, "Historique"]
                    # Conversion si string
                    import ast
                    if isinstance(histo, str):
                        try:
                            histo = ast.literal_eval(histo)
                        except Exception:
                            histo = []
                    if not isinstance(histo, list):
                        histo = []
                    histo.append({
                        "date": fr_date(date_val),
                        "montant": montant,
                        "commentaire": description
                    })
                    st.session_state['investissements'].at[idx_actif, "Historique"] = histo
                    # Cumule montant investi
                    montant_actuel = st.session_state['investissements'].at[idx_actif, "Montant investi"]
                    try:
                        montant_actuel = float(montant_actuel)
                    except Exception:
                        montant_actuel = 0.0
                    st.session_state['investissements'].at[idx_actif, "Montant investi"] = montant_actuel + montant
                    save_dataframes(user_prefix)
                    # Ajout transaction classique
                    new_row = {
                        "Date": fr_date(date_val),
                        "Type": type_transac,
                        "Catégorie": "Investissement",
                        "Montant": -montant,
                        "Description": description,
                        "Dette liée": "",
                        "Crédit lié": "",
                        "Projet lié": "",
                        "Actif lié": actif_cible
                    }
                    # On ajoute la colonne "Actif lié" si pas déjà présente
                    if "Actif lié" not in st.session_state['transactions'].columns:
                        st.session_state['transactions']["Actif lié"] = ""
                    st.session_state['transactions'] = pd.concat(
                        [pd.DataFrame([new_row]), st.session_state['transactions']], ignore_index=True
                    )
                    st.success(f"Apport de {montant:,.2f} CHF enregistré pour l'actif {actif_cible} !")
                    st.rerun()

                elif type_transac == "Remboursement de dette" and dette_choisie:
                    montant_effectif = -abs(montant)
                    dette_liee = dette_choisie
                    idx = st.session_state['dettes'][st.session_state['dettes']["Créancier"] == dette_choisie].index
                    if len(idx) > 0:
                        idx = idx[0]
                        dette = st.session_state['dettes'].loc[idx]
                        histo = dette["Historique"].copy() if isinstance(dette["Historique"], list) else []
                        histo.append({
                            "date": fr_date(date_val),
                            "montant": montant,
                            "commentaire": description
                        })
                        montant_restant = max(dette["Montant restant"] - montant, 0)
                        statut = "Terminée" if montant_restant <= 0.01 else "En cours"
                        st.session_state['dettes'].at[idx, "Montant restant"] = montant_restant
                        st.session_state['dettes'].at[idx, "Statut"] = statut
                        st.session_state['dettes'].at[idx, "Historique"] = histo
                        if statut == "Terminée":
                            st.success(f"🎉 Bravo ! Dette auprès de {dette_choisie} totalement remboursée.")
                        else:
                            st.success(f"Remboursement ajouté pour {dette_choisie}. Reste à payer : {montant_restant:,.2f} CHF.")

                if type_transac == "Paiement crédit" and credit_choisi:
                    montant_effectif = -abs(montant)
                    credit_lie = credit_choisi
                    idx = st.session_state['credits'][st.session_state['credits']["Créancier"] == credit_choisi].index
                    if len(idx) > 0:
                        idx = idx[0]
                        credit = st.session_state['credits'].loc[idx]
                        histo = credit["Historique"].copy() if isinstance(credit["Historique"], list) else []
                        histo.append({
                            "date": fr_date(date_val),
                            "montant": montant,
                            "commentaire": description
                        })
                        montant_restant = max(credit["Montant restant"] - montant, 0)
                        statut = "Terminée" if montant_restant <= 0.01 else "En cours"
                        st.session_state['credits'].at[idx, "Montant restant"] = montant_restant
                        st.session_state['credits'].at[idx, "Statut"] = statut
                        st.session_state['credits'].at[idx, "Historique"] = histo
                        if statut == "Terminée":
                            st.success(f"🎉 Bravo ! Crédit auprès de {credit_choisi} totalement remboursé.")
                        else:
                            st.success(f"Paiement crédit ajouté pour {credit_choisi}. Reste à payer : {montant_restant:,.2f} CHF.")

                if type_transac == "Sortie" and projet_choisi:
                    projet_lie = projet_choisi

                new_row = {
                    "Date": fr_date(date_val),
                    "Type": type_transac,
                    "Catégorie": cat_transac,
                    "Montant": montant_effectif,
                    "Description": description,
                    "Dette liée": dette_liee,
                    "Crédit lié": credit_lie,
                    "Projet lié": projet_lie
                }
                st.session_state['transactions'] = pd.concat(
                    [pd.DataFrame([new_row]), st.session_state['transactions']], ignore_index=True
                )
                # Si la transaction est une Sortie associée à un projet, incrémente le montant atteint du projet
                if type_transac == "Sortie" and projet_lie:
                    dfp = st.session_state['projets']
                    idx_proj = dfp[dfp["Nom"] == projet_lie].index
                    if len(idx_proj) > 0:
                        idx_proj = idx_proj[0]
                        # Additionne le montant à tous les versements associés au projet déjà présents
                        if pd.isna(dfp.at[idx_proj, "Montant atteint"]):
                            montant_courant = 0.0
                        else:
                            montant_courant = float(dfp.at[idx_proj, "Montant atteint"])
                        nouveau_montant = montant_courant + abs(montant)
                        st.session_state['projets'].at[idx_proj, "Montant atteint"] = nouveau_montant
                        save_dataframes(user_prefix)
                else:
                    save_dataframes(user_prefix)

                # --- Synchronisation Cash si catégorie "Cash" ---
                if cat_transac == "Cash":
                    cash_hist = st.session_state['cash']["historique"]
                    # Type = Entrée/Sortie, Montant positif, Date, Commentaire
                    cash_type = "Ajout" if type_transac == "Entrée" else "Retrait"
                    cash_row = {
                        "Date": fr_date(date_val),
                        "Type": cash_type,
                        "Montant": abs(montant),
                        "Commentaire": description
                    }
                    st.session_state['cash']["historique"] = pd.concat(
                        [pd.DataFrame([cash_row]), cash_hist], ignore_index=True
                    )

                if type_transac not in ["Remboursement de dette", "Paiement crédit"]:
                    st.success("Transaction ajoutée !")
        else:
            st.error("Le montant doit être supérieur à zéro.")

    # ------- IMPORT CSV BANCAIRE -------
    st.subheader("Importer un relevé bancaire (CSV)")
    csv_file = st.file_uploader("Sélectionner un fichier CSV", type=["csv"], key="import_csv")
    if csv_file is not None:
        import csv

        def detect_separator(csv_file):
            sample = csv_file.read(2048).decode(errors='ignore')
            csv_file.seek(0)
            sniffer = csv.Sniffer()
            try:
                sep = sniffer.sniff(sample).delimiter
            except Exception:
                sep = ","
            return sep

        try:
            sep = detect_separator(csv_file)
            df_import = pd.read_csv(csv_file, sep=sep, engine="python")
            # Nettoyage des colonnes vides
            df_import = df_import.dropna(axis=1, how='all')

            # Vérification des colonnes du format CSV bancaire
            if "DATE" in df_import.columns and ("DEBIT" in df_import.columns or "CREDIT" in df_import.columns):
                devise_sel = devise_affichage  # Prend la devise affichée dans la barre latérale (CHF, EUR, USD)
                lignes_avant = len(df_import)
                # On ne garde que les lignes où la devise de débit/crédit est bien la bonne (par défaut CHF)
                masque_debit = (df_import["DEBIT CURRENCY"].fillna("") == devise_sel)
                masque_credit = (df_import["CREDIT CURRENCY"].fillna("") == devise_sel)
                df_filtre = df_import[(masque_debit | masque_credit)]

                def get_montant(row):
                    if row.get("DEBIT CURRENCY") == devise_sel and pd.notnull(row.get("DEBIT")) and row["DEBIT"] != "":
                        try:
                            return -abs(float(row["DEBIT"]))
                        except:
                            return 0.0
                    elif row.get("CREDIT CURRENCY") == devise_sel and pd.notnull(row.get("CREDIT")) and row["CREDIT"] != "":
                        try:
                            return float(row["CREDIT"])
                        except:
                            return 0.0
                    else:
                        return 0.0

                df_filtre["Montant"] = df_filtre.apply(get_montant, axis=1)
                # Force affichage date en français (jj/mm/aaaa)
                df_filtre["Date"] = df_filtre["DATE"].apply(fr_date)
                if "ACTIVITY NAME" in df_filtre.columns:
                    df_filtre["Description"] = df_filtre["ACTIVITY NAME"]
                else:
                    df_filtre["Description"] = ""
                df_filtre["Type"] = df_filtre["Montant"].apply(lambda x: "Entrée" if x > 0 else "Sortie")
                df_filtre["Catégorie"] = "Import bancaire"
                df_filtre["Dette liée"] = ""
                df_filtre["Crédit lié"] = ""
                df_filtre["Projet lié"] = ""
                # Filtrer les lignes où le montant = 0 (bonus, etc.)
                df_filtre = df_filtre[df_filtre["Montant"] != 0]
                df_filtre = df_filtre[["Date", "Type", "Catégorie", "Montant", "Description", "Dette liée", "Crédit lié", "Projet lié"]]
                # Force affichage date en français (jj/mm/aaaa) pour la colonne Date
                df_filtre["Date"] = df_filtre["Date"].apply(fr_date)
                st.session_state['transactions'] = pd.concat(
                    [df_filtre, st.session_state['transactions']], ignore_index=True
                )
                lignes_ajoutees = len(df_filtre)
                lignes_ignorees = lignes_avant - lignes_ajoutees
                save_dataframes(user_prefix)
                st.success(f"{lignes_ajoutees} transactions importées en {devise_sel} !")
                if lignes_ignorees > 0:
                    st.info(f"{lignes_ignorees} lignes ont été ignorées car elles n'étaient pas en {devise_sel}.")
            else:
                st.error("Ton fichier doit contenir les colonnes 'DATE' et au moins 'DEBIT' ou 'CREDIT'.")
        except Exception as e:
            st.error(f"Erreur lors de l'import : {e}")

    # ----- HISTORIQUE & SOLDE -----
    st.subheader("Filtrer les transactions par date")
    filtre_date = st.date_input("Afficher le solde et l’historique jusqu’à cette date (inclus)", value=datetime.today(), key="filtre_date")
    date_limite = to_date(filtre_date)

    df = st.session_state['transactions'].copy()
    # Force affichage date en français (jj/mm/aaaa)
    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(fr_date)
    df["Date_dt"] = df["Date"].apply(to_date)
    # Filtrage transactions pour calcul du solde (hors transferts internes)
    df_filtre = df[df["Date_dt"] <= date_limite]
    # Exclure transferts internes du calcul du solde (patrimoine net)
    df_solde = df_filtre[~df_filtre["Catégorie"].astype(str).str.startswith("Transfert interne")]
    solde = df_solde["Montant"].sum() if not df_solde.empty else 0.0

    st.markdown(f"""
    ### 🧮 **Solde au {fr_date(date_limite)} :**  
    <span style='font-size:2em; color: {"green" if solde >= 0 else "red"}'>
    {convertir(solde, 'CHF', devise_affichage):,.2f} {devise_affichage}
    </span>
    """, unsafe_allow_html=True)

    st.header("📋 Historique des transactions (vue année/mois)")

    if df_filtre.empty:
        st.info("Aucune transaction enregistrée jusqu’à cette date.")
    else:
        # Tri/format
        df_affiche = df_filtre.copy()
        df_affiche["Date_dt"] = df_affiche["Date"].apply(to_date)
        df_affiche = df_affiche.sort_values("Date_dt", ascending=False)
        df_affiche["Année"] = df_affiche["Date_dt"].apply(lambda d: d.year)
        df_affiche["Mois"] = df_affiche["Date_dt"].apply(lambda d: d.strftime("%B"))
        annees = sorted(df_affiche["Année"].unique(), reverse=True)
        for annee in annees:
            with st.expander(f"Année {annee}", expanded=bool(annee == max(annees))):
                df_year = df_affiche[df_affiche["Année"] == annee]
                mois_list = df_year["Mois"].unique()
                mois_ordre = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
                mois_list = [m for m in mois_ordre if m.capitalize() in [x.capitalize() for x in mois_list]]
                for mois in mois_list:
                    df_mois = df_year[df_year["Mois"].str.lower() == mois]
                    with st.expander(f"{mois.capitalize()} {annee}", expanded=bool(annee == max(annees) and mois==mois_list[0])):
                        if df_mois.empty:
                            st.info("Aucune transaction ce mois.")
                        else:
                            for idx, row in df_mois.iterrows():
                                montant_conv = convertir(row['Montant'], 'CHF', devise_affichage)
                                # Mettre en évidence les transferts internes
                                cat_aff = row['Catégorie']
                                if str(cat_aff).startswith("Transfert interne"):
                                    cat_aff = f"🔄 {cat_aff}"
                                with st.expander(f"{row['Date']} - {row['Type']} - {cat_aff} - {montant_conv:,.2f} {devise_affichage}"):
                                    st.write(f"**Description :** {row['Description'] or '—'}")
                                    st.write(f"**Dette liée :** {row['Dette liée'] or '—'}")
                                    st.write(f"**Crédit lié :** {row['Crédit lié'] or '—'}")
                                    st.write(f"**Projet lié :** {row['Projet lié'] or '—'}")
                                    delete_key = f"delete_confirm_{row['Date']}_{row['Montant']}_{row['Description']}_{idx}"
                                    if st.button('🗑️ Supprimer cette transaction', key=f'del_trans_{delete_key}'):
                                        st.session_state[delete_key] = True

                                    if st.session_state.get(delete_key, False):
                                        st.warning("Êtes-vous sûr de vouloir supprimer cette transaction ? Cette action est irréversible.")
                                        colA, colB = st.columns(2)
                                        if colA.button("Oui, supprimer", key=f"confirm_suppr_{delete_key}"):
                                            idx_global = df[
                                                (df["Date"] == row["Date"]) &
                                                (df["Montant"] == row["Montant"]) &
                                                (df["Description"] == row["Description"])
                                            ].index
                                            if len(idx_global) > 0:
                                                idx_global = idx_global[0]
                                                # Gestion suppression projet lié etc. comme dans ta version
                                                if row["Type"] == "Sortie" and row["Projet lié"]:
                                                    dfp = st.session_state['projets']
                                                    idx_proj = dfp[dfp["Nom"] == row["Projet lié"]].index
                                                    if len(idx_proj) > 0:
                                                        idx_proj = idx_proj[0]
                                                        montant_courant = float(dfp.at[idx_proj, "Montant atteint"])
                                                        nouveau_montant = max(montant_courant - abs(float(row["Montant"])), 0)
                                                        st.session_state['projets'].at[idx_proj, "Montant atteint"] = nouveau_montant
                                                        save_dataframes(user_prefix)
                                                st.session_state['transactions'] = st.session_state['transactions'].drop(idx_global).reset_index(drop=True)
                                                save_dataframes(user_prefix)
                                                st.success("Transaction supprimée.")
                                            else:
                                                st.error("Impossible de retrouver la transaction à supprimer. (Vérifie la date, le montant et la description)")
                                            st.session_state[delete_key] = False
                                            st.rerun()
                                        if colB.button("Annuler", key=f"annule_suppr_{delete_key}"):
                                            st.session_state[delete_key] = False

    if not df.empty:
        # Force affichage date en français (jj/mm/aaaa) avant export
        df_export = df.drop(columns=["Date_dt"]).copy()
        if "Date" in df_export.columns:
            df_export["Date"] = df_export["Date"].apply(fr_date)
        st.download_button(
            label="📥 Exporter vers Excel",
            data=df_export.to_csv(index=False).encode('utf-8'),
            file_name=f'transactions_finances_{devise_affichage}.csv',
            mime='text/csv'
        )

    st.markdown("""
    ---
    > *“Chaque transaction, chaque remboursement, chaque crédit… tu construis ta liberté pierre par pierre.”*
    """)
    # ============= DETTES =============
with tab2:
    st.title("💳 Dettes KILLER")

    with st.expander("➕ Ajouter une nouvelle dette"):
        cols = st.columns(3)
        createur = cols[0].text_input("Créancier", key="dette_createur")
        montant_initial = cols[1].number_input("Montant initial", min_value=1.0, step=1.0, key="dette_montant_initial")
        mensualite = cols[2].number_input("Mensualité prévue", min_value=0.0, step=1.0, key="dette_mensualite")
        cols2 = st.columns(3)
        date_debut = cols2[0].date_input("Date de début", value=datetime.today(), key="dette_date_debut")
        prochaine_echeance = cols2[1].date_input("Prochaine échéance", value=datetime.today(), key="dette_prochaine_echeance")
        categorie = cols2[2].selectbox("Catégorie", ["Poursuite", "Majoration", "Crédit", "Autre"], key="dette_categorie")
        couleur = st.color_picker("Couleur du camembert", "#FF6384", key="dette_couleur")

        if st.button("Ajouter la dette", key="ajouter_dette"):
            if createur and montant_initial > 0:
                new_row = {
                    "ID": st.session_state['dette_id'],
                    "Créancier": createur,
                    "Montant initial": montant_initial,
                    "Montant restant": montant_initial,
                    "Mensualité": mensualite,
                    "Date début": fr_date(date_debut),
                    "Prochaine échéance": fr_date(prochaine_echeance),
                    "Catégorie": categorie,
                    "Statut": "En cours",
                    "Historique": [],
                    "Couleur": couleur
                }
                st.session_state['dettes'] = pd.concat(
                    [st.session_state['dettes'], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.session_state['dette_id'] += 1
                save_dataframes(user_prefix)
                st.success("Dette ajoutée !")

    st.header("📑 Liste de mes dettes")

    df_dettes = st.session_state['dettes'].copy()
    # Force affichage date en français (jj/mm/aaaa)
    if "Date début" in df_dettes.columns:
        df_dettes["Date début"] = df_dettes["Date début"].apply(fr_date)
    if "Prochaine échéance" in df_dettes.columns:
        df_dettes["Prochaine échéance"] = df_dettes["Prochaine échéance"].apply(fr_date)
    if df_dettes.empty:
        st.info("Aucune dette enregistrée.")
    else:
        for i, row in df_dettes.iterrows():
            col1, col2 = st.columns([3, 1])
            avec = f"{row['Créancier']} ({row['Catégorie']})"
            solde = f"Restant : {convertir(row['Montant restant'], 'CHF', devise_affichage):,.2f} / {convertir(row['Montant initial'], 'CHF', devise_affichage):,.2f} {devise_affichage}"
            statut = "✅" if row["Statut"] == "Terminée" else "⏳"
            pourcent_remb = 100 * (1 - row["Montant restant"] / row["Montant initial"])
            fig, ax = plt.subplots(figsize=(1.8,1.8))
            glossy_pie(
                ax,
                [max(pourcent_remb, 0), max(100 - pourcent_remb, 0)],
                [f"{pourcent_remb:.0f}% remboursé", ""],
                [row["Couleur"], "#eeeeee"],
                f"Dette"
            )
            with col1:
                st.markdown(f"**{avec}**  {statut}  \n{solde}")
                st.pyplot(fig)
                # Affichage de la date de clôture estimée
                import math
                from dateutil.relativedelta import relativedelta

                if row["Statut"] == "Terminée":
                    cloture_estimee = "Clôturée"
                elif row["Mensualité"] and float(row["Mensualité"]) > 0:
                    reste = float(row["Montant restant"])
                    mensu = float(row["Mensualité"])
                    mois_restant = math.ceil(reste / mensu)
                    try:
                        base_date = to_date(row["Prochaine échéance"])
                    except Exception:
                        base_date = date.today()
                    cloture_date = base_date + relativedelta(months=mois_restant-1)
                    cloture_estimee = cloture_date.strftime("%d/%m/%Y")
                else:
                    cloture_estimee = "Indéfini"

                st.markdown(f"<b>Date de clôture estimée :</b> {cloture_estimee}", unsafe_allow_html=True)
                histo = row["Historique"]
                if histo:
                    with st.expander("Voir l’historique des remboursements"):
                        histo_df = pd.DataFrame(histo)
                        # Force affichage date en français (jj/mm/aaaa)
                        if "date" in histo_df.columns:
                            histo_df["date"] = histo_df["date"].apply(fr_date)
                        histo_df_aff = histo_df.copy()
                        if "montant" in histo_df_aff.columns:
                            histo_df_aff["montant"] = histo_df_aff["montant"].apply(lambda x: convertir(x, 'CHF', devise_affichage))
                        st.dataframe(histo_df_aff, use_container_width=True, hide_index=True)
                if st.button("🗑️ Supprimer cette dette", key=f"del_dette_{i}"):
                    if st.confirm("Êtes-vous sûr de vouloir supprimer cette dette ? Cette action est irréversible."):
                        st.session_state['dettes'] = st.session_state['dettes'].drop(i).reset_index(drop=True)
                        save_dataframes(user_prefix)
                        st.success("Dette supprimée.")
                        st.rerun()
            with col2:
                st.write("")

    if not df_dettes.empty:
        total_initial = df_dettes["Montant initial"].sum()
        total_restant = df_dettes["Montant restant"].sum()
        total_remb = total_initial - total_restant
        pourcent_remb = 100 * total_remb / total_initial if total_initial > 0 else 0
        st.markdown("---")
        st.subheader("Progression globale de remboursement des dettes")
        fig2, ax2 = plt.subplots(figsize=(3.2,3.2))
        glossy_pie(
            ax2,
            [max(pourcent_remb, 0), max(100 - pourcent_remb, 0)],
            [f"{pourcent_remb:.0f}% remboursé", ""],
            ["#37d67a", "#cccccc"],
            "Remboursement dettes"
        )
        st.pyplot(fig2)
        st.markdown(f"**Total remboursé : {convertir(total_remb, 'CHF', devise_affichage):,.2f} {devise_affichage} / {convertir(total_initial, 'CHF', devise_affichage):,.2f} {devise_affichage}**")

    st.markdown("""
    ---
    > *Chaque dette remboursée, c’est une victoire de plus sur la liberté. Continue à avancer, tu es sur le bon chemin !*
    """)

# ============= CREDITS =============
with tab3:
    st.title("🏦 Suivi des crédits")

    with st.expander("➕ Ajouter un nouveau crédit"):
        cols = st.columns(3)
        createur = cols[0].text_input("Organisme / Banque", key="credit_createur")
        montant_initial = cols[1].number_input("Montant initial (CHF : devise de référence)", min_value=1.0, step=1.0, key="credit_montant_initial")
        mensualite = cols[2].number_input("Mensualité prévue (CHF : devise de référence)", min_value=0.0, step=1.0, key="credit_mensualite")
        cols2 = st.columns(2)
        date_debut = cols2[0].date_input("Date de début", value=datetime.today(), key="credit_date_debut")
        prochaine_echeance = cols2[1].date_input("Prochaine échéance", value=datetime.today(), key="credit_prochaine_echeance")
        couleur = st.color_picker("Couleur du camembert", "#40a1ff", key="credit_couleur")

        if st.button("Ajouter le crédit", key="ajouter_credit"):
            if createur and montant_initial > 0:
                new_row = {
                    "ID": st.session_state['credit_id'],
                    "Créancier": createur,
                    "Montant initial": montant_initial,
                    "Montant restant": montant_initial,
                    "Mensualité": mensualite,
                    "Date début": fr_date(date_debut),
                    "Prochaine échéance": fr_date(prochaine_echeance),
                    "Statut": "En cours",
                    "Historique": [],
                    "Couleur": couleur
                }
                st.session_state['credits'] = pd.concat(
                    [st.session_state['credits'], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.session_state['credit_id'] += 1
                save_dataframes(user_prefix)
                st.success("Crédit ajouté !")

    st.header("📑 Liste de mes crédits")

    df_credits = st.session_state['credits'].copy()
    # Force affichage date en français (jj/mm/aaaa)
    if "Date début" in df_credits.columns:
        df_credits["Date début"] = df_credits["Date début"].apply(fr_date)
    if "Prochaine échéance" in df_credits.columns:
        df_credits["Prochaine échéance"] = df_credits["Prochaine échéance"].apply(fr_date)
    if df_credits.empty:
        st.info("Aucun crédit enregistré.")
    else:
        for i, row in df_credits.iterrows():
            col1, col2 = st.columns([3, 1])
            avec = f"{row['Créancier']}"
            solde = f"Restant : {convertir(row['Montant restant'], 'CHF', devise_affichage):,.2f} / {convertir(row['Montant initial'], 'CHF', devise_affichage):,.2f} {devise_affichage}"
            statut = "✅" if row["Statut"] == "Terminée" else "⏳"
            pourcent_remb = 100 * (1 - row["Montant restant"] / row["Montant initial"])
            fig, ax = plt.subplots(figsize=(1.8,1.8))
            glossy_pie(
                ax,
                [max(pourcent_remb, 0), max(100 - pourcent_remb, 0)],
                [f"{pourcent_remb:.0f}% remboursé", ""],
                [row["Couleur"], "#eeeeee"],
                "Crédit"
            )
            with col1:
                st.markdown(f"**{avec}**  {statut}  \n{solde}")
                st.write(f"Début : {fr_date(row['Date début'])} • Échéance : {fr_date(row['Prochaine échéance'])}")
                st.pyplot(fig)
                histo = row["Historique"]
                if histo:
                    with st.expander("Voir l’historique des paiements"):
                        histo_df = pd.DataFrame(histo)
                        # Force affichage date en français (jj/mm/aaaa)
                        if "date" in histo_df.columns:
                            histo_df["date"] = histo_df["date"].apply(fr_date)
                        histo_df_aff = histo_df.copy()
                        if "montant" in histo_df_aff.columns:
                            histo_df_aff["montant"] = histo_df_aff["montant"].apply(lambda x: convertir(x, 'CHF', devise_affichage))
                        st.dataframe(histo_df_aff, use_container_width=True, hide_index=True)
                if st.button("🗑️ Supprimer ce crédit", key=f"del_credit_{i}"):
                    if st.confirm("Êtes-vous sûr de vouloir supprimer ce crédit ? Cette action est irréversible."):
                        st.session_state['credits'] = st.session_state['credits'].drop(i).reset_index(drop=True)
                        save_dataframes(user_prefix)
                        st.success("Crédit supprimé.")
                        st.rerun()
            with col2:
                st.write("")

    if not df_credits.empty:
        total_initial = df_credits["Montant initial"].sum()
        total_restant = df_credits["Montant restant"].sum()
        total_remb = total_initial - total_restant
        pourcent_remb = 100 * total_remb / total_initial if total_initial > 0 else 0
        st.markdown("---")
        st.subheader("Progression globale de remboursement des crédits")
        fig2, ax2 = plt.subplots(figsize=(3.2,3.2))
        glossy_pie(
            ax2,
            [max(pourcent_remb, 0), max(100 - pourcent_remb, 0)],
            [f"{pourcent_remb:.0f}% remboursé", ""],
            ["#40a1ff", "#cccccc"],
            "Remboursement crédits"
        )
        st.pyplot(fig2)
        st.markdown(f"**Total remboursé : {convertir(total_remb, 'CHF', devise_affichage):,.2f} {devise_affichage} / {convertir(total_initial, 'CHF', devise_affichage):,.2f} {devise_affichage}**")

    st.markdown("""
    ---
    > *Chaque paiement de crédit, c’est un pas de plus vers ta liberté financière. Continue, tu fais du super boulot !*
    """)

# ============= PROJETS =============
with tab4:
    st.title("🎯 Projets & Objectifs")

    with st.expander("➕ Créer un nouveau projet / objectif"):
        cols = st.columns(3)
        nom_projet = cols[0].text_input("Nom du projet", key="projet_nom")
        objectif = cols[1].number_input("Montant à atteindre (CHF : devise de référence)", min_value=1.0, step=1.0, key="projet_objectif")
        couleur = cols[2].color_picker("Couleur du camembert", "#faab1a", key="projet_couleur")
        desc = st.text_area("Description (facultatif)", key="projet_desc")

        if st.button("Ajouter ce projet", key="ajouter_projet"):
            if nom_projet and objectif > 0:
                new_row = {
                    "ID": st.session_state['projet_id'],
                    "Nom": nom_projet,
                    "Objectif": objectif,
                    "Montant atteint": 0,
                    "Description": desc,
                    "Couleur": couleur
                }
                st.session_state['projets'] = pd.concat(
                    [st.session_state['projets'], pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.session_state['projet_id'] += 1
                save_dataframes(user_prefix)
                st.success("Projet ajouté !")

    st.header("📑 Suivi visuel de mes projets")

    df_projets = st.session_state['projets'].copy()
    # Pas de colonne date
    df_tr = st.session_state['transactions'].copy()
    # Force affichage date en français (jj/mm/aaaa)
    if "Date" in df_tr.columns:
        df_tr["Date"] = df_tr["Date"].apply(fr_date)

    if df_projets.empty:
        st.info("Aucun projet créé pour l’instant.")
    else:
        for i, row in df_projets.iterrows():
            montant_atteint = row["Montant atteint"]
            objectif = row["Objectif"]
            montant_atteint_aff = convertir(montant_atteint, 'CHF', devise_affichage)
            objectif_aff = convertir(objectif, 'CHF', devise_affichage)
            pourcent = min(100 * montant_atteint / objectif if objectif > 0 else 0, 100)
            fig, ax = plt.subplots(figsize=(1.8,1.8))
            glossy_pie(
                ax,
                [max(pourcent, 0), max(100 - pourcent, 0)],
                [f"{pourcent:.0f}% atteint", ""],
                [row["Couleur"], "#eeeeee"],
                "Projet"
            )
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**🎯 {row['Nom']}**")
                st.markdown(f"Objectif : {objectif_aff:,.2f} {devise_affichage}")
                st.markdown(f"Déjà investi : {montant_atteint_aff:,.2f} {devise_affichage}")
                st.markdown(row["Description"] or "—")
                st.pyplot(fig)
            with col2:
                if st.button("🗑️ Supprimer ce projet", key=f"del_projet_{i}"):
                    st.session_state[f"confirm_suppr_projet_{i}"] = True

                if st.session_state.get(f"confirm_suppr_projet_{i}", False):
                    st.warning("Êtes-vous sûr de vouloir supprimer ce projet ? Cette action est irréversible.")
                    colA, colB = st.columns(2)
                    if colA.button("Oui, supprimer", key=f"confirm_suppr_projet_btn_{i}"):
                        st.session_state['projets'] = st.session_state['projets'].drop(i).reset_index(drop=True)
                        save_dataframes(user_prefix)
                        st.success("Projet supprimé.")
                        st.session_state[f"confirm_suppr_projet_{i}"] = False
                        st.rerun()
                    if colB.button("Annuler", key=f"annule_suppr_projet_btn_{i}"):
                        st.session_state[f"confirm_suppr_projet_{i}"] = False

    st.markdown("""
    ---
    > *“Chaque euro investi dans un rêve, c’est un futur qui devient concret. Tu bâtis ton chemin, étape après étape !”*
    """)
    # ============= INVESTISSEMENTS =============
with tab5:
    st.title("Investissement")
    st.header("Gestion des investissements")
    # Helper pour convertir string/list vers liste d'apports
    def ensure_hist_list(hist):
        if isinstance(hist, list):
            return hist
        if pd.isnull(hist):
            return []
        try:
            import ast
            val = ast.literal_eval(hist)
            if isinstance(val, list):
                return val
            return []
        except Exception:
            return []

    def ensure_val_hist_list(valhist):
        if isinstance(valhist, list):
            return valhist
        if pd.isnull(valhist):
            return []
        try:
            import ast
            val = ast.literal_eval(valhist)
            if isinstance(val, list):
                return val
            return []
        except Exception:
            return []

    if 'valeur_actuelle_hist' not in st.session_state:
        st.session_state['valeur_actuelle_hist'] = {}

    df_inv = st.session_state['investissements'].copy()
    # Force affichage date en français (jj/mm/aaaa)
    if "Date" in df_inv.columns:
        df_inv["Date"] = df_inv["Date"].apply(fr_date)
    if not df_inv.empty:
        df_inv["Historique"] = df_inv["Historique"].apply(ensure_hist_list)
        if "valeur_actuelle_hist" not in df_inv.columns:
            df_inv["valeur_actuelle_hist"] = [[] for _ in range(len(df_inv))]
        else:
            df_inv["valeur_actuelle_hist"] = df_inv["valeur_actuelle_hist"].apply(ensure_val_hist_list)

    with st.expander("➕ Ajouter un nouvel actif"):
        cols = st.columns(3)
        type_invest = cols[0].text_input("Type d'actif (ex : Crypto, Bourse, Immo, etc.)", key="inv_type")
        nom_invest = cols[1].text_input("Nom de l'actif", key="inv_nom")
        couleur = cols[2].color_picker("Couleur", "#f5426f", key="inv_couleur")
        if st.button("Créer l'actif", key="ajouter_actif"):
            if nom_invest:
                exists = not df_inv[(df_inv["Nom"] == nom_invest) & (df_inv["Type"] == type_invest)].empty
                if exists:
                    st.warning("Cet actif existe déjà.")
                else:
                    new_row = {
                        "ID": st.session_state['investissement_id'],
                        "Type": type_invest,
                        "Nom": nom_invest,
                        "Montant investi": 0.0,
                        "Valeur actuelle": 0.0,
                        "Intérêts reçus": 0.0,
                        "Date": fr_date(datetime.today()),
                        "Historique": [],
                        "valeur_actuelle_hist": [],
                        "Couleur": couleur
                    }
                    st.session_state['investissements'] = pd.concat(
                        [st.session_state['investissements'], pd.DataFrame([new_row])],
                        ignore_index=True
                    )
                    st.session_state['investissement_id'] += 1
                    save_dataframes(user_prefix)
                    st.success("Actif ajouté !")
                    st.rerun()

    # Message d'aide pour ajout d'apport
    st.info("Pour ajouter un nouvel apport, enregistre une transaction de type Sortie > Investissement dans l’onglet Transactions.")

    # SUPPRESSION/masquage formulaire d’ajout manuel d’apport : rien à faire, car il n’y en a pas ici

    st.header("Performances")
    st.header("📑 Mes actifs")
    df_inv = st.session_state['investissements']
    if df_inv.empty:
        st.info("Aucun actif enregistré pour l’instant.")
    else:
        actifs = df_inv.groupby(["Nom", "Type"]).first().reset_index()
        actifs['label'] = actifs['Nom'] + ' (' + actifs['Type'] + ')'
        actif_liste = actifs['Nom'].tolist()
        couleurs = {row['Nom']: row.get('Couleur', "#f5426f") for _, row in actifs.iterrows()}

        selection = st.multiselect(
            "Sélectionne un ou plusieurs actifs à comparer sur la courbe (par défaut : tous)",
            options=actif_liste, default=actif_liste
        )

        # -------- COURBE EVOLUTION --------
        st.markdown("#### Évolution de la valeur actuelle (multi-actif)")
        fig_courbe = courbe_evolution_valeur_actifs(df_inv, couleurs, selection)
        st.pyplot(fig_courbe)

        # -------- CAMEMBERT REPARTITION --------
        st.markdown("#### Répartition des actifs (valeur actuelle)")
        valeurs = []
        noms = []
        cols_c = []
        for i, row in df_inv.iterrows():
            valeur = float(row.get("Valeur actuelle", 0.0))
            if valeur > 0:
                valeurs.append(valeur)
                noms.append(row["Nom"])
                cols_c.append(row.get("Couleur", "#f5426f"))
        if sum(valeurs) > 0:
            fig_pie, ax_pie = plt.subplots(figsize=(2.6,2.6))
            glossy_pie(ax_pie, valeurs, noms, cols_c, "Répartition")
            st.pyplot(fig_pie)
        else:
            st.info("Aucune valeur actuelle positive enregistrée pour afficher un camembert.")

        # -------- Détail tableau actif --------
        st.markdown("#### Détail des actifs")
        for i, row in df_inv.iterrows():
            nom, type_ = row["Nom"], row["Type"]
            montant_investi = float(row.get("Montant investi", 0.0))
            valeur_actuelle = float(row.get("Valeur actuelle", 0.0))
            interets_recus = float(row.get("Intérêts reçus", 0.0))
            plus_value = valeur_actuelle + interets_recus - montant_investi
            rendement = 100 * plus_value / montant_investi if montant_investi > 0 else 0
            couleur = row.get("Couleur", "#f5426f")

            with st.expander(f"• {nom} ({type_})"):
                col1, col2 = st.columns([5,1])
                with col1:
                    st.markdown(f"- **Total investi** : {convertir(montant_investi, 'CHF', devise_affichage):,.2f} {devise_affichage}")
                    st.markdown(f"- **Valeur actuelle** : {convertir(valeur_actuelle, 'CHF', devise_affichage):,.2f} {devise_affichage}")
                    st.markdown(f"- **Intérêts reçus** : {convertir(interets_recus, 'CHF', devise_affichage):,.2f} {devise_affichage}")
                    st.markdown(f"- **Plus-value/moins-value** : {convertir(plus_value, 'CHF', devise_affichage):,.2f} {devise_affichage}")
                    st.markdown(f"- **Rendement** : {rendement:.2f} %")
                with col2:
                    st.color_picker("Couleur", value=couleur, key=f"colpick_{nom}_{type_}")

                # --------- Ajout champ MAJ valeur actuelle + historique ---------
                # Récupération de l'historique des valeurs actuelles
                val_hist = ensure_val_hist_list(row.get("valeur_actuelle_hist", []))
                # Dernière valeur actuelle connue
                last_val = valeur_actuelle
                if val_hist and isinstance(val_hist, list) and len(val_hist) > 0:
                    last_entry = sorted(val_hist, key=lambda x: to_date(x.get("date","")), reverse=True)[0]
                    last_val = float(last_entry.get("valeur", valeur_actuelle))
                maj_val_key = f"maj_valeur_actuelle_{nom}_{type_}"
                new_val = st.number_input("Mettre à jour la valeur actuelle (CHF)", min_value=0.0, value=float(last_val), step=1.0, key=maj_val_key)
                btn_key = f"valider_maj_valeur_{nom}_{type_}"
                if st.button("Valider la mise à jour", key=btn_key):
                    # Mettre à jour la valeur actuelle dans le DataFrame
                    idx = df_inv[(df_inv["Nom"] == nom) & (df_inv["Type"] == type_)].index
                    if len(idx) > 0:
                        idx = idx[0]
                        # Met à jour la colonne "Valeur actuelle"
                        st.session_state['investissements'].at[idx, "Valeur actuelle"] = new_val
                        # Ajoute à l'historique
                        old_val_hist = ensure_val_hist_list(st.session_state['investissements'].at[idx, "valeur_actuelle_hist"])
                        today_str = fr_date(datetime.today())
                        # Ajoute seulement si valeur/date différente ou si vide
                        if not old_val_hist or old_val_hist[0].get("valeur") != new_val or old_val_hist[0].get("date") != today_str:
                            old_val_hist = [{"date": today_str, "valeur": new_val}] + [h for h in old_val_hist if h.get("date") != today_str]
                        st.session_state['investissements'].at[idx, "valeur_actuelle_hist"] = old_val_hist
                        save_dataframes(user_prefix)
                        st.success("Valeur actuelle mise à jour et enregistrée !")
                        st.rerun()
                # Affiche la date de la dernière MAJ si dispo
                if val_hist and isinstance(val_hist, list) and len(val_hist) > 0:
                    last_entry = sorted(val_hist, key=lambda x: to_date(x.get("date","")), reverse=True)[0]
                    st.caption(f"Dernière mise à jour : {fr_date(last_entry.get('date'))}")
                # Affiche un expander pour l'historique des valeurs actuelles si dispo
                if val_hist and isinstance(val_hist, list) and len(val_hist) > 0:
                    with st.expander("Historique valeur actuelle", expanded=False):
                        hist_df = pd.DataFrame(val_hist)
                        if not hist_df.empty:
                            hist_df = hist_df.copy()
                            hist_df["date"] = hist_df["date"].apply(fr_date)
                            hist_df = hist_df.sort_values("date", ascending=False)
                            hist_df = hist_df.rename(columns={"date": "Date", "valeur": "Valeur (CHF)"})
                            st.dataframe(hist_df, use_container_width=True, hide_index=True)

                # --------- Historique des apports (expander par année/mois) ---------
                histo_apports = ensure_hist_list(row.get("Historique", []))
                if histo_apports and isinstance(histo_apports, list) and len(histo_apports) > 0:
                    # Convert dates and sort
                    apports = []
                    for h in histo_apports:
                        date_apport = to_date(h.get("date", ""))
                        montant = h.get("montant", 0.0)
                        commentaire = h.get("commentaire", "")
                        apports.append({"date": date_apport, "montant": montant, "commentaire": commentaire})
                    apports = sorted(apports, key=lambda x: x["date"], reverse=True)
                    # Grouper par année puis mois
                    from collections import defaultdict
                    apports_par_annee = defaultdict(list)
                    for apport in apports:
                        annee = apport["date"].year
                        apports_par_annee[annee].append(apport)
                    annees = sorted(apports_par_annee.keys(), reverse=True)
                    with st.expander("Historique des apports", expanded=False):
                        for annee in annees:
                            apports_annee = apports_par_annee[annee]
                            # Grouper par mois
                            apports_par_mois = defaultdict(list)
                            for apport in apports_annee:
                                mois = apport["date"].strftime("%B")
                                apports_par_mois[mois].append(apport)
                            # Trier mois dans l'ordre classique
                            mois_ordre = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
                            mois_present = [m for m in mois_ordre if m.capitalize() in [x.capitalize() for x in apports_par_mois.keys()]]
                            with st.expander(f"Année {annee}", expanded=(annee == max(annees))):
                                for mois in mois_present:
                                    apports_mois = [a for a in apports_par_mois if a.lower() == mois]
                                    # Correction : il faut trouver le bon mois (clé) pour chaque mois
                                    for key_mois in apports_par_mois:
                                        if key_mois.lower() == mois:
                                            apports_mois = apports_par_mois[key_mois]
                                            break
                                    if not apports_mois:
                                        continue
                                    with st.expander(f"{mois.capitalize()} {annee}", expanded=(annee == max(annees) and mois==mois_present[0])):
                                        # Afficher sous forme de tableau
                                        df_apports = []
                                        for a in apports_mois:
                                            df_apports.append({
                                                "Date": fr_date(a["date"]),
                                                "Montant": convertir(a["montant"], 'CHF', devise_affichage),
                                                "Commentaire": a["commentaire"] or "—"
                                            })
                                        st.dataframe(
                                            pd.DataFrame(df_apports),
                                            use_container_width=True,
                                            hide_index=True
                                        )
# ============= SANTÉ DU PORTEFEUILLE / CASH =============
with tab6:
    st.title("🩺 Santé du portefeuille")

    # --- Cockpit synthétique
    with st.container():
        st.markdown("### Synthèse cockpit")
        colA, colB, colC = st.columns(3)
        # --- Actifs
        cash_dispo = 0.0
        cash_hist = st.session_state['cash']["historique"]
        if not cash_hist.empty:
            cash_dispo = cash_hist.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1).sum()
        investissements = st.session_state['investissements']
        total_investissements = investissements["Valeur actuelle"].sum() if not investissements.empty else 0.0
        actifs = cash_dispo + total_investissements
        # --- Passifs
        dettes = st.session_state['dettes']
        credits = st.session_state['credits']
        total_dettes = dettes["Montant restant"].sum() if not dettes.empty else 0.0
        total_credits = credits["Montant restant"].sum() if not credits.empty else 0.0
        passifs = total_dettes + total_credits
        # --- Patrimoine net
        patrimoine_net = actifs - passifs

        colA.metric("💰 Actifs totaux", f"{actifs:,.2f} CHF", help="Cash disponible + valeur actuelle des investissements")
        colB.metric("🔻 Passifs totaux", f"{passifs:,.2f} CHF", help="Montant restant à rembourser (dettes + crédits)")
        colC.metric("🟣 Patrimoine net", f"{patrimoine_net:,.2f} CHF", help="Actifs - Passifs (ton vrai capital actuel)")

        # Graphe d’évolution patrimoine net (historique sur 30 derniers jours)
        import datetime
        hist = st.session_state.get("bilan_reel_hist", [])
        if not hist or hist[-1]["date"] != str(datetime.date.today()):
            hist.append({"date": str(datetime.date.today()), "valeur": patrimoine_net})
            st.session_state["bilan_reel_hist"] = hist
        if len(hist) > 1:
            import matplotlib.pyplot as plt
            dates = [datetime.datetime.strptime(h["date"], "%Y-%m-%d") for h in hist[-30:]]
            vals = [h["valeur"] for h in hist[-30:]]
            fig, ax = plt.subplots(figsize=(5, 2.2))
            ax.plot(dates, vals, color="#6c3bc4", marker="o")
            ax.set_title("Patrimoine net – 30 derniers jours", fontsize=10)
            ax.set_xlabel("")
            ax.set_ylabel("CHF")
            ax.grid(True, linestyle="--", color="#ccc", alpha=0.4)
            st.pyplot(fig)

        # Récap visuel en camembert (répartition Actifs / Passifs)
        labels = ["Cash", "Investissements", "Dettes", "Crédits"]
        values = [cash_dispo, total_investissements, -total_dettes, -total_credits]
        colors = ["#37d67a", "#faab1a", "#e74c3c", "#40a1ff"]
        total_val = sum([abs(x) for x in values])
        if total_val > 0:
            fig2, ax2 = plt.subplots(figsize=(3.2,3.2))
            glossy_pie(ax2, [abs(x) for x in values], labels, colors, "Répartition rapide")
            st.pyplot(fig2)
        else:
            st.info("Aucune donnée à afficher pour la répartition rapide (ajoute du cash ou des investissements pour commencer !)")


    st.markdown("## Fonds d’urgence")
    # Objectif personnalisable
    cash_obj = st.number_input(
        "Objectif fonds d’urgence (CHF)", min_value=0.0, value=float(st.session_state['cash'].get("objectif", 1000.0)),
        step=100.0, key="cash_objectif_input"
    )
    if cash_obj != st.session_state['cash'].get("objectif", 1000.0):
        st.session_state['cash']["objectif"] = cash_obj

    # Historique cash
    cash_hist = st.session_state['cash']["historique"]
    if isinstance(cash_hist, dict):
        # Migration si jamais
        cash_hist = pd.DataFrame(columns=["Date", "Type", "Montant", "Commentaire"])
        st.session_state['cash']["historique"] = cash_hist
    # Calcul cash disponible
    cash_total = 0.0
    if not cash_hist.empty:
        cash_total = cash_hist.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1).sum()
    pourcent = min(100 * cash_total / cash_obj if cash_obj > 0 else 0, 100)
    # Jauge violette
    st.markdown(
        f"""
        <div style="margin-bottom:10px;">
            <b>Progression du fonds d’urgence :</b>
            <div style="background:#ede6fa;border-radius:6px;height:32px;position:relative;">
                <div style="background:#a259e6;height:32px;width:{pourcent:.2f}%;border-radius:6px 0 0 6px;transition:width 0.5s;"></div>
                <div style="position:absolute;top:0;left:50%;transform:translateX(-50%);font-weight:600;color:#6c3bc4;line-height:32px;">
                    {pourcent:.1f}% atteint
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown(
        f"<b>Cash disponible actuel :</b> <span style='font-size:1.5em;color:#6c3bc4;font-weight:700'>{cash_total:,.2f} CHF</span>",
        unsafe_allow_html=True
    )

    st.markdown("## Cash disponible")
    st.markdown(f"<b>Montant actuel :</b> {cash_total:,.2f} CHF", unsafe_allow_html=True)
    if st.checkbox("Afficher l’historique mensuel du cash disponible", key="show_cash_hist_mois"):
        if not cash_hist.empty:
            # Grouper par mois/année
            cash_hist["Date_dt"] = cash_hist["Date"].apply(to_date)
            cash_hist_sorted = cash_hist.sort_values("Date_dt")
            cash_hist_sorted["YearMonth"] = cash_hist_sorted["Date_dt"].apply(lambda d: d.strftime("%Y-%m"))
            # Calculer cash cumulé à chaque date
            cash_hist_sorted["Delta"] = cash_hist_sorted.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1)
            cash_hist_sorted["Cash_cum"] = cash_hist_sorted["Delta"].cumsum()
            mois_cash = cash_hist_sorted.groupby("YearMonth")["Cash_cum"].last().reset_index()
            st.bar_chart(mois_cash.set_index("YearMonth")["Cash_cum"])
        else:
            st.info("Aucun mouvement de cash enregistré.")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Ajouter du cash", key="btn_ajout_cash"):
            st.session_state["popup_cash_ajout"] = True
    with colB:
        if st.button("Retirer du cash", key="btn_retrait_cash"):
            st.session_state["popup_cash_retrait"] = True

    # Popup ajout cash
    if st.session_state.get("popup_cash_ajout", False):
        with st.form("form_cash_ajout", clear_on_submit=True):
            st.markdown("### ➕ Ajouter du cash")
            montant_ajout = st.number_input("Montant à ajouter", min_value=0.0, step=1.0, key="input_cash_ajout")
            from datetime import date
            date_ajout = st.date_input("Date", value=date.today(), key="date_cash_ajout")
            commentaire_ajout = st.text_input("Commentaire (facultatif)", key="comment_cash_ajout")
            valider = st.form_submit_button("Valider")
            annuler = st.form_submit_button("Annuler")
            if valider and montant_ajout > 0:
                # Empêcher cash négatif (jamais possible à l'ajout)
                row = {
                    "Date": fr_date(date_ajout),
                    "Type": "Ajout",
                    "Montant": montant_ajout,
                    "Commentaire": commentaire_ajout
                }
                st.session_state['cash']["historique"] = pd.concat([pd.DataFrame([row]), st.session_state['cash']["historique"]], ignore_index=True)
                st.session_state["popup_cash_ajout"] = False
                st.success("Cash ajouté !")
                st.rerun()
            elif annuler:
                st.session_state["popup_cash_ajout"] = False
                st.rerun()
            elif valider and montant_ajout <= 0:
                st.warning("Le montant doit être supérieur à zéro.")

    # Popup retrait cash
    if st.session_state.get("popup_cash_retrait", False):
        with st.form("form_cash_retrait", clear_on_submit=True):
            st.markdown("### ➖ Retirer du cash")
            montant_retrait = st.number_input("Montant à retirer", min_value=0.0, step=1.0, key="input_cash_retrait")
            date_retrait = st.date_input("Date", value=datetime.today(), key="date_cash_retrait")
            commentaire_retrait = st.text_input("Commentaire (facultatif)", key="comment_cash_retrait")
            valider = st.form_submit_button("Valider")
            annuler = st.form_submit_button("Annuler")
            if valider and montant_retrait > 0:
                # Vérifier que cash dispo >= montant_retrait
                cash_hist = st.session_state['cash']["historique"]
                cash_total = 0.0
                if not cash_hist.empty:
                    cash_total = cash_hist.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1).sum()
                if montant_retrait > cash_total:
                    st.warning("Impossible : le montant du retrait dépasse le cash disponible.")
                else:
                    row = {
                        "Date": fr_date(date_retrait),
                        "Type": "Retrait",
                        "Montant": montant_retrait,
                        "Commentaire": commentaire_retrait
                    }
                    st.session_state['cash']["historique"] = pd.concat([pd.DataFrame([row]), st.session_state['cash']["historique"]], ignore_index=True)
                    st.session_state["popup_cash_retrait"] = False
                    st.success("Retrait de cash enregistré !")
                    st.rerun()
            elif annuler:
                st.session_state["popup_cash_retrait"] = False
                st.rerun()
            elif valider and montant_retrait <= 0:
                st.warning("Le montant doit être supérieur à zéro.")

    with st.expander("Historique des mouvements de cash", expanded=False):
        st.markdown("### Mouvements du cash")
        cash_hist = st.session_state['cash']["historique"]
        if not cash_hist.empty:
            cash_hist_aff = cash_hist.copy()
            cash_hist_aff["Date"] = cash_hist_aff["Date"].apply(fr_date)
            st.dataframe(cash_hist_aff, use_container_width=True, hide_index=True)
            # Nouveau graphique en "bougies" fines pour le cash (delta par jour + cash cumulé)
            cash_hist_aff["Date_dt"] = cash_hist_aff["Date"].apply(to_date)
            cash_hist_aff = cash_hist_aff.sort_values("Date_dt")
            cash_hist_aff["Delta"] = cash_hist_aff.apply(lambda row: row["Montant"] if row["Type"] == "Ajout" else -row["Montant"], axis=1)
            cash_hist_aff["Cash_cum"] = cash_hist_aff["Delta"].cumsum()

            fig, ax1 = plt.subplots(figsize=(7, 2.8))
            dates = cash_hist_aff["Date_dt"]
            deltas = cash_hist_aff["Delta"]
            cumuls = cash_hist_aff["Cash_cum"]

            # Affiche de fines bougies vertes (ajout) ou rouges (retrait)
            bar_colors = ['#37d67a' if v >= 0 else '#e74c3c' for v in deltas]
            ax1.bar(dates, deltas, width=0.5, color=bar_colors, align='center', edgecolor='none', zorder=2)

            # Courbe cumulée fine en surimpression
            ax1.plot(dates, cumuls, color="#6c3bc4", linewidth=1.2, marker='o', markersize=4, alpha=0.8, zorder=3)

            # Axe X discret, dates réduites et bien lisibles
            ax1.set_xlabel("")
            ax1.set_ylabel("Montant (CHF)", fontsize=9)
            ax1.set_title("Évolution journalière du cash (bougies)", fontsize=10)
            ax1.grid(True, linestyle="--", color="#ccc", alpha=0.3, zorder=1)
            ax1.tick_params(axis='x', labelsize=7, rotation=0)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("Aucun mouvement de cash enregistré.")