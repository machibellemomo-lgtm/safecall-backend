import re

# ============================================================
# MOTS-CLÉS — CONFIRMATION ABSOLUE (faux conseiller)
# Aucun agent légitime ne demande jamais ça → score maximal direct
# ============================================================
MOTS_CONFIRMATION = [
    "tapez votre code",
    "entrez votre pin",
    "confirmez votre code",
    "votre code secret",
    "taper le code",
    "composer le",
    "valider avec votre",
    "code de confirmation",
    "entrer votre code",
    "saisir votre pin",
    "votre mot de passe",
    "code pin",
    "taper *",
    "composez le",
    "envoyez votre",
    "donnez votre code",
    "communiquez votre code",
]

# ============================================================
# MOTS-CLÉS FAUSSE LOTERIE / GAIN
# ============================================================
MOTS_LOTERIE = [
    "vous avez gagné", "vous avez gagne", "félicitations", "felicitations",
    "gagnant", "loterie", "tombola", "tirage au sort",
    "prix a gagner", "prix à gagner", "cadeau", "récompense", "recompense",
]

# ============================================================
# MOTS-CLÉS SUSPECTS GÉNÉRAUX
# ============================================================
MOTS_SUSPECTS = [
    "cliquez ici", "cliquer ici", "bit.ly", "tinyurl",
    "dépêchez", "depechez", "urgent", "immédiatement", "immediatement",
    "offre limitée", "offre limitee", "anniversaire", "gratuit",
    "confirmer", "vérifier votre", "verifier votre", "votre compte",
    "suspendu", "bloqué", "bloque", "expiré", "expire", "transfert",
]

# ============================================================
# NUMÉROS/SHORT CODES OFFICIELS (MTN/Orange/Camtel Cameroun)
# ============================================================
NUMEROS_OFFICIELS = [
    "8787", "8900", "8706", 
]

EXPEDITEURS_MOBILE_MONEY_OFFICIELS = [
    "orangemoney",
    "mobilemoney",
]
EXPEDITEURS_BANQUES_OFFICIELS = [
    "afb", "afriland",
    "bicec",
    "sgc", "societegenerale",
    "uba",
    "scb",
    "cbc",
    "ecobank",
    "stanchart",
    "bacm",
    "bgfi",
]

# ============================================================
# DOMAINES SUSPECTS
# ============================================================
DOMAINES_SUSPECTS = [
    "bit.ly", "tinyurl.com", "goo.gl", "t.co",
    "ow.ly", "is.gd", "buff.ly", "adf.ly", "tiny.cc",
]

# ============================================================
# PRÉFIXES OPÉRATEURS — approximatif, à confirmer avec de vrais numéros
# ============================================================
PREFIXES_OPERATEURS = {
    'mtn':    ['650', '651', '652', '653', '654', '67', '680', '681', '682', '683', '684'],
    'orange': ['655', '656', '657', '658', '659', '69', '685', '686', '687', '688', '689'],
    'camtel': ['62', '66'],
}


def detecter_operateur(numero):
    """
    Tente de détecter l'opérateur depuis le préfixe.
    Retourne le code opérateur détecté, ou None si non reconnu
    (dans ce cas l'app mobile doit proposer un choix manuel).
    """
    if not numero:
        return None
    numero_propre = re.sub(r'\D', '', numero)
    if numero_propre.startswith('237'):
        numero_propre = numero_propre[3:]
    for operateur, prefixes in PREFIXES_OPERATEURS.items():
        for prefixe in prefixes:
            if numero_propre.startswith(prefixe):
                return operateur
    return None


def est_numero_officiel(numero):
    """Un numéro/short code officiel, ou un nom d'expéditeur Mobile Money/banque reconnu."""
    if not numero:
        return False
    numero_normalise = numero.strip().lower().replace(" ", "").replace("-", "")
    if any(numero.startswith(n) or numero == n for n in NUMEROS_OFFICIELS):
        return True
    if numero_normalise in EXPEDITEURS_MOBILE_MONEY_OFFICIELS:
        return True
    if numero_normalise in EXPEDITEURS_BANQUES_OFFICIELS:
        return True
    return False

def est_numero_telephone_ordinaire(numero):
    """Un numéro camerounais standard (9 chiffres, commence par 6)."""
    if not numero:
        return False
    return bool(re.match(r'^(\+?237)?6\d{8}$', numero.strip()))


# ============================================================
# MOTEUR PRINCIPAL
# ============================================================

def analyser_message(message, expediteur=""):
    """
    Analyse un message et retourne un score + le type d'arnaque probable.
    Score : 0-100 | Niveau : 0=sûr, 1=Suspect, 2=Très suspect, 3=Confirmé
    """
    message_lower = message.lower()

    # ── Règle absolue : demande de code/PIN/mot de passe ──
    for mot in MOTS_CONFIRMATION:
        if mot in message_lower:
            return {
                "score": 100,
                "niveau": 3,
                "niveau_label": "🔴 ARNAQUE CONFIRMÉE",
                "type_detecte": "faux_conseiller",
                "recommandation": "Ne communiquez jamais votre code PIN, mot de passe ou code de confirmation. Aucun agent légitime ne le demande. Bloquez ce numéro immédiatement.",
                "details": [f"🚨 Demande de code/PIN/mot de passe détectée : '{mot}' — signal absolu de fraude"],
            }

    score = 0
    details = []
    type_detecte = None

    # ── Expéditeur non reconnu comme officiel ──
    if expediteur:
        if est_numero_officiel(expediteur):
            details.append("✅ Expéditeur reconnu comme un numéro/short code officiel")
        else:
            score += 80
            type_detecte = "faux_depot"
            if est_numero_telephone_ordinaire(expediteur):
                details.append("🚨 Expéditeur est un numéro de téléphone ordinaire, pas un expéditeur officiel — signal fort de faux dépôt/faux message bancaire")
            else:
                details.append("🚨 Expéditeur non reconnu comme officiel (ni numéro, ni nom légitime) — possible usurpation d'identité")

    # ── Liens ──
    liens = re.findall(r'http[s]?://\S+|www\.\S+|bit\.ly\S*|tinyurl\S*', message_lower)
    if liens:
        score += 25
        type_detecte = type_detecte or "lien_suspect"
        details.append("🔗 Lien détecté dans le message")
        for lien in liens:
            for domaine in DOMAINES_SUSPECTS:
                if domaine in lien:
                    score += 15
                    details.append(f"🚨 Lien raccourci dangereux : {domaine}")
                    break

    # ── Erreur de calcul (indice complémentaire, vérifiable mathématiquement) ──
    montants = re.findall(r'\d+(?:\s?\d+)*(?:\s?fcfa|\s?f\.?cfa|\s?xaf)?', message_lower)
    if len(montants) >= 2:
        try:
            nombres = [int(re.sub(r'\D', '', m)) for m in montants if re.sub(r'\D', '', m)]
            nombres = [n for n in nombres if n > 100]
            if len(nombres) >= 2 and nombres[1] < nombres[0]:
                score += 10
                details.append("🧮 Erreur de calcul détectée (solde incohérent) — indice supplémentaire")
        except Exception:
            pass

    score = min(score, 100)

    if score >= 70:
        niveau, niveau_label, recommandation = 3, "🔴 ARNAQUE CONFIRMÉE", "Bloquez ce numéro immédiatement et ne répondez pas"
    elif score >= 40:
        niveau, niveau_label, recommandation = 2, "🟠 TRÈS SUSPECT", "Soyez très prudent, évitez de répondre ou de cliquer"
    elif score >= 20:
        niveau, niveau_label, recommandation = 1, "🟡 SUSPECT", "Restez vigilant avec ce message"
    else:
        niveau, niveau_label, recommandation = 0, "🟢 PROBABLEMENT SÛR", "Ce message semble légitime"

    return {
        "score": score,
        "niveau": niveau,
        "niveau_label": niveau_label,
        "type_detecte": type_detecte or "autre",
        "recommandation": recommandation,
        "details": details or ["Aucun signal fiable détecté"],
    }


def analyser_numero(numero):
    """
    Vérification directe d'un numéro (aussi utilisée pour un appel entrant :
    la seule chose qui compte pour un appel est sa présence dans la base
    communautaire, vérifiée séparément côté vue).
    """
    details = []
    operateur_detecte = detecter_operateur(numero)

    if est_numero_officiel(numero):
        return {
            "score": 0, "niveau": 0,
            "niveau_label": "🟢 NUMÉRO OFFICIEL",
            "operateur_detecte": operateur_detecte,
            "recommandation": "Ce numéro semble être un numéro/short code officiel",
            "details": ["✅ Numéro court officiel reconnu"],
        }

    score = 5 if est_numero_telephone_ordinaire(numero) else 0
    if score:
        details.append("📱 Numéro camerounais ordinaire — vérifiez son historique dans la base communautaire")

    return {
        "score": score,
        "niveau": 1 if score > 0 else 0,
        "niveau_label": "🟡 À VÉRIFIER" if score > 0 else "🟢 INCONNU",
        "operateur_detecte": operateur_detecte,
        "recommandation": "Consultez la base communautaire pour voir si ce numéro a déjà été signalé",
        "details": details or ["Aucune information disponible sur ce numéro"],
    }


def analyser_lien(url):
    """Analyse un lien (utilisé pour lien_suspect ET whatsapp, selon le canal)."""
    score = 0
    details = []
    url_lower = url.lower()

    for domaine in DOMAINES_SUSPECTS:
        if domaine in url_lower:
            score += 50
            details.append(f"🚨 Domaine dangereux détecté : {domaine}")
            break

    for mot in ['gagner', 'gagne', 'prix', 'cadeau', 'gratuit', 'anniversaire', 'offre', 'promo']:
        if mot in url_lower:
            score += 20
            details.append(f"⚠️ Mot suspect dans l'URL : '{mot}'")

    if len(url) > 100:
        score += 10
        details.append("⚠️ URL anormalement longue")

    score = min(score, 100)

    if score >= 70:
        niveau, niveau_label, recommandation = 3, "🔴 LIEN DANGEREUX", "Ne cliquez surtout pas sur ce lien"
    elif score >= 40:
        niveau, niveau_label, recommandation = 2, "🟠 LIEN TRÈS SUSPECT", "Évitez de cliquer sur ce lien"
    elif score >= 20:
        niveau, niveau_label, recommandation = 1, "🟡 LIEN SUSPECT", "Soyez prudent avec ce lien"
    else:
        niveau, niveau_label, recommandation = 0, "🟢 LIEN PROBABLEMENT SÛR", "Ce lien semble légitime"

    return {
        "score": score, "niveau": niveau, "niveau_label": niveau_label,
        "recommandation": recommandation,
        "details": details or ["Aucun signal suspect détecté"],
    }


# ============================================================
# ANALYSE PAR IMAGE (via Gemini) — extraction expéditeur + message
# ============================================================

import requests as _requests
from django.conf import settings


def extraire_info_capture(image_base64, mime_type="image/jpeg"):
    """
    Envoie une capture d'écran à Gemini pour en extraire :
    - le nom/numéro de l'expéditeur visible
    - le texte du message
    Retourne un dict {'expediteur': str, 'message': str, 'erreur': str|None}
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {'expediteur': '', 'message': '', 'erreur': 'Clé API Gemini non configurée sur le serveur'}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    prompt = (
        "Tu regardes une capture d'écran d'un SMS, d'une notification WhatsApp ou d'un message. "
        "Extrait UNIQUEMENT deux informations et réponds STRICTEMENT en JSON, sans aucun texte autour : "
        '{"expediteur": "le nom ou numéro de l\'expéditeur tel qu\'affiché", "message": "le texte complet du message"}. '
        "Si tu ne trouves pas l'expéditeur, mets une chaîne vide. "
        "Ne résume pas le message, recopie-le exactement tel qu'il apparaît."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": image_base64}}
            ]
        }]
    }

    try:
        response = _requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        texte_reponse = data["candidates"][0]["content"]["parts"][0]["text"]

        # Nettoyage : Gemini répond parfois avec ```json ... ``` autour
        texte_reponse = texte_reponse.strip()
        if texte_reponse.startswith("```"):
            texte_reponse = texte_reponse.split("```")[1]
            if texte_reponse.startswith("json"):
                texte_reponse = texte_reponse[4:]

        import json
        resultat = json.loads(texte_reponse.strip())

        return {
            'expediteur': resultat.get('expediteur', '').strip(),
            'message': resultat.get('message', '').strip(),
            'erreur': None,
        }

    except Exception as e:
        print(f"[GEMINI ERREUR] {type(e).__name__}: {str(e)}")
        if 'response' in dir(e) and hasattr(e, 'response') and e.response is not None:
            print(f"[GEMINI REPONSE BRUTE] {e.response.text[:500]}")
        return {'expediteur': '', 'message': '', 'erreur': f"Erreur lors de l'analyse de l'image : {str(e)}"}