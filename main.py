import os
import json
import time
import base64
import requests
import schedule
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "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")
PEXELS_KEY    = os.environ.get("PEXELS_KEY",    "ZRymppu6gsDcHPfG2IrgM0EAviOihfpajg8raicsasyqJc2vI9shGD63")
WP_URL        = os.environ.get("WP_URL",        "https://www.kodo.fr/blog/wp-json/wp/v2")
WP_USER       = os.environ.get("WP_USER",       "IA blog")
WP_PASSWORD   = os.environ.get("WP_PASSWORD",   "RzvY nbNb vV3g YUoB mGc3 qqYd")

WP_AUTH = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()

ANTHROPIC_HEADERS = {
    "x-api-key": ANTHROPIC_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# ── Étape 1 : Claude choisit le sujet ──────────────────────────
def choisir_sujet():
    print(f"[{datetime.now()}] Choix du sujet...")
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": (
                "Tu es l'agent editorial de Kodo (www.kodo.fr/blog), expert Odoo et ERP pour PME francaises. "
                "Choisis UN sujet d'article de blog pertinent. Le sujet doit etre lie a Odoo, ERP, migration Odoo, "
                "formation Odoo, actualites Odoo, modules Odoo, facturation electronique, ROI ERP, conduite du changement. "
                "Reponds UNIQUEMENT avec un objet JSON valide sans markdown sans backticks : "
                "{\"sujet\": \"le sujet de l article\", \"angle\": \"l angle differentiant\", "
                "\"mot_cle\": \"mot-cle principal SEO\", \"image_keyword\": \"1 mot anglais simple ex: office team dashboard\"}"
            )
        }]
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=ANTHROPIC_HEADERS, json=payload)
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    import re
    match = re.search(r'\{[\s\S]*\}', text)
    data = json.loads(match.group(0) if match else text)
    print(f"[{datetime.now()}] Sujet choisi : {data.get('sujet')}")
    return data

# ── Étape 2 : Récupérer une image Pexels ───────────────────────
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

# ── Étape 3 : Uploader l'image sur WordPress ───────────────────
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
    lien = post.get("link", "")
    print(f"[{datetime.now()}] PUBLIE ! ID : {post['id']} — {lien}")
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

print(f"[{datetime.now()}] Agent Kodo Blog demarre - Publication lundi et jeudi a 9h")

# Lancer immédiatement au démarrage pour tester
publier_article_automatique()

# Boucle infinie
while True:
    schedule.run_pending()
    time.sleep(60)
