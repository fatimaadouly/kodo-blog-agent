import os
import json
import time
import base64
import requests
import schedule
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_KEY",    "")
WP_URL        = os.environ.get("WP_URL",        "https://www.kodo.fr/blog/wp-json/wp/v2")
WP_USER       = os.environ.get("WP_USER",       "IA blog")
WP_PASSWORD   = os.environ.get("WP_PASSWORD",   "")

WP_AUTH = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()

ANTHROPIC_HEADERS = {
    "x-api-key": ANTHROPIC_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Fichier pour mémoriser les sujets déjà publiés
HISTORIQUE_FILE = "sujets_publies.json"

SUJETS_POOL = [
    "Odoo 19 et l'intelligence artificielle : ce que ca change pour les PME",
    "Migration Odoo : les 7 erreurs a eviter absolument",
    "Odoo vs SAP Business One : quel ERP choisir pour une PME en 2026",
    "Module CRM Odoo : comment booster ses ventes et piloter son pipeline",
    "Odoo pour le secteur industriel : production, stocks et qualite",
    "ROI d'un projet Odoo : comment mesurer le retour sur investissement",
    "Formation Odoo : pourquoi former ses equipes pour reussir l'adoption",
    "Interconnexion Odoo : connecter son ERP avec ses outils metier",
    "Odoo et la gestion RH : conges, paie et recrutement dans un seul outil",
    "Comment bien choisir son integrateur Odoo en France",
    "Odoo pour le e-commerce : gerer boutique et logistique dans un seul ERP",
    "Tableau de bord Odoo : piloter son activite en temps reel",
    "Conduite du changement dans un projet ERP : les cles du succes",
    "Odoo et la gestion de projet : planifier, suivre et livrer",
    "Module comptabilite Odoo : automatiser sa gestion financiere",
    "Odoo pour les PME du batiment : devis, chantiers et facturation",
    "Pourquoi passer d'Excel a Odoo : le guide pour les dirigeants de PME",
    "Odoo et la supply chain : optimiser achats, stocks et livraisons",
    "Les modules Odoo indispensables pour une PME en croissance",
    "Accompagnement Odoo : pourquoi le support post-deploiement est crucial"
]

def charger_historique():
    if os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, "r") as f:
            return json.load(f)
    return []

def sauvegarder_historique(historique):
    with open(HISTORIQUE_FILE, "w") as f:
        json.dump(historique, f)

# ── Étape 1 : Choisir un sujet non répété ─────────────────────
def choisir_sujet():
    print(f"[{datetime.now()}] Choix du sujet...")
    historique = charger_historique()

    # Sujets non encore publiés
    sujets_disponibles = [s for s in SUJETS_POOL if s not in historique]

    # Si tout a été publié, on repart de zéro
    if not sujets_disponibles:
        sujets_disponibles = SUJETS_POOL
        sauvegarder_historique([])

    # Demander à Claude de choisir parmi les sujets disponibles
    liste_sujets = "\n".join([f"- {s}" for s in sujets_disponibles[:10]])

    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": (
                f"Tu es l'agent editorial de Kodo (www.kodo.fr/blog), expert Odoo et ERP pour PME francaises.\n"
                f"Choisis UN sujet parmi cette liste pour l'article d'aujourd'hui :\n{liste_sujets}\n\n"
                "Choisis le sujet le plus pertinent et actuel. "
                "Reponds UNIQUEMENT avec un objet JSON valide sans markdown sans backticks : "
                "{\"sujet\": \"le sujet choisi exactement comme dans la liste\", "
                "\"angle\": \"l angle differentiant en 1 phrase\", "
                "\"mot_cle\": \"mot-cle principal SEO\", "
                "\"image_keyword\": \"1 mot anglais simple ex: office team dashboard meeting\"}"
            )
        }]
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=ANTHROPIC_HEADERS, json=payload)
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    import re
    match = re.search(r'\{[\s\S]*\}', text)
    data = json.loads(match.group(0) if match else text)

    # Mémoriser le sujet
    historique.append(data.get("sujet", ""))
    sauvegarder_historique(historique)

    print(f"[{datetime.now()}] Sujet choisi : {data.get('sujet')}")
    return data

# ── Étape 2 : Récupérer une image Pexels ──────────────────────
def recuperer_image(keyword):
    print(f"[{datetime.now()}] Recherche image Pexels : {keyword}")
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": keyword, "per_page": 1, "orientation": "landscape"}
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if photos:
        url = photos[0]["src"].get("large2x") or photos[0]["src"].get("large")
    else:
        url = "https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg?auto=compress&cs=tinysrgb&w=1200"
    print(f"[{datetime.now()}] Image trouvee : {url}")
    return url

# ── Étape 3 : Uploader l'image sur WordPress ──────────────────
def uploader_image(image_url, keyword):
    print(f"[{datetime.now()}] Telechargement image...")
    img_data = requests.get(image_url).content
    filename = f"{keyword}-{int(time.time())}.jpg"
    headers = {
        "Authorization": f"Basic {WP_AUTH}",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "image/jpeg"
    }
    r = requests.post(f"{WP_URL}/media", headers=headers, data=img_data)
    r.raise_for_status()
    media_id = r.json()["id"]
    print(f"[{datetime.now()}] Image uploadee, ID : {media_id}")
    return media_id

# ── Étape 4 : Claude rédige l'article ─────────────────────────
def rediger_article(sujet, angle, mot_cle):
    print(f"[{datetime.now()}] Redaction de l'article...")
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 8000,
        "system": (
            "Tu es l agent editorial IA officiel de Kodo (www.kodo.fr/blog), expert en content marketing B2B, "
            "SEO editorial et Odoo ERP. Kodo est un integrateur Odoo expert en integration, migration, formation, "
            "accompagnement Odoo et conseil ERP. Cible : dirigeants PME, DSI, RAF, responsables supply chain, commerce, RH. "
            "Ton : expert, clair, pedagogique, credible, oriente benefices business. Pas promotionnel. "
            "Longueur : 1500 a 2200 mots. Style : paragraphes courts, H2 et H3 informatifs, listes quand utile, exemples concrets. "
            "Mentionner Kodo avec subtilite uniquement quand pertinent. Conclure par un appel a l action concret. "
            "Reponds UNIQUEMENT avec un objet JSON valide sans markdown sans backticks : "
            "{\"titre_seo\": \"...\", \"meta_description\": \"...\", \"slug\": \"...\", "
            "\"mot_cle_principal\": \"...\", \"tags\": [\"...\"], \"extrait\": \"...\", \"contenu_html\": \"...\"}"
        ),
        "messages": [{
            "role": "user",
            "content": (
                f"Redige un article de blog complet pour Kodo sur le sujet : {sujet}. "
                f"Angle : {angle}. Mot-cle : {mot_cle}. "
                "Le contenu_html doit avoir des balises h2 h3 p ul li strong et faire minimum 1500 mots. "
                "Ne pas inclure le H1."
            )
        }]
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=ANTHROPIC_HEADERS, json=payload)
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    import re
    match = re.search(r'\{[\s\S]*\}', text)
    article = json.loads(match.group(0) if match else text)
    print(f"[{datetime.now()}] Article redige : {article.get('titre_seo')}")
    return article

# ── Étape 5 : Publier sur WordPress ───────────────────────────
def publier_article(article, media_id):
    print(f"[{datetime.now()}] Publication sur WordPress...")
    headers = {
        "Authorization": f"Basic {WP_AUTH}",
        "Content-Type": "application/json"
    }
    payload = {
        "title":          article["titre_seo"],
        "content":        article["contenu_html"],
        "excerpt":        article.get("extrait", ""),
        "slug":           article.get("slug", ""),
        "status":         "publish",
        "featured_media": media_id
    }
    r = requests.post(f"{WP_URL}/posts", headers=headers, json=payload)
    r.raise_for_status()
    post = r.json()
    print(f"[{datetime.now()}] PUBLIE ! ID : {post['id']} — {post.get('link', '')}")
    return post

# ── Pipeline principal ─────────────────────────────────────────
def publier_article_automatique():
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] DEMARRAGE AGENT KODO BLOG")
    print(f"{'='*60}")
    try:
        sujet_data = choisir_sujet()
        image_url  = recuperer_image(sujet_data.get("image_keyword", "business"))
        media_id   = uploader_image(image_url, sujet_data.get("image_keyword", "kodo"))
        article    = rediger_article(sujet_data["sujet"], sujet_data["angle"], sujet_data["mot_cle"])
        publier_article(article, media_id)
        print(f"[{datetime.now()}] SUCCES - Article publie sur kodo.fr/blog")
    except Exception as e:
        print(f"[{datetime.now()}] ERREUR : {e}")

# ── Planification : lundi et jeudi à 9h ───────────────────────
schedule.every().monday.at("09:00").do(publier_article_automatique)
schedule.every().thursday.at("09:00").do(publier_article_automatique)

print(f"[{datetime.now()}] Agent Kodo Blog demarre - En attente lundi et jeudi a 9h")
print(f"[{datetime.now()}] Prochain declenchement planifie : lundi ou jeudi a 09:00")

# Boucle infinie - NE PAS lancer au démarrage
while True:
    schedule.run_pending()
    time.sleep(60)
