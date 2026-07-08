import re

# ============================================================
# MOTS-CLÉS CRITIQUES — Score très élevé
# ============================================================
MOTS_CRITIQUES = [
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
]

# ============================================================
# MOTS-CLÉS SUSPECTS — Score moyen
# ============================================================
MOTS_SUSPECTS = [
    "vous avez reçu",
    "vous avez recu",
    "félicitations",
    "felicitations",
    "vous avez gagné",
    "vous avez gagne",
    "cliquez ici",
    "cliquer ici",
    "bit.ly",
    "tinyurl",
    "dépêchez",
    "depechez",
    "urgent",
    "immédiatement",
    "immediatement",
    "offre limitée",
    "offre limitee",
    "anniversaire",
    "gratuit",
    "cadeau",
    "récompense",
    "recompense",
    "confirmer",
    "vérifier votre",
    "verifier votre",
    "votre compte",
    "suspendu",
    "bloqué",
    "bloque",
    "expiré",
    "expire",
    "gagnant",
    "loterie",
    "prix",
    "transfert",
]

# ============================================================
# NUMÉROS OFFICIELS MTN/ORANGE CAMEROUN
# ============================================================
NUMEROS_OFFICIELS = [
    "1212",
    "1313",
    "8686",
    "655",
    "699",
    "677",
    "676",
    "222",
    "8181",
    "1010",
]

# ============================================================
# DOMAINES SUSPECTS
# ============================================================
DOMAINES_SUSPECTS = [
    "bit.ly",
    "tinyurl.com",
    "goo.gl",
    "t.co",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "adf.ly",
    "tiny.cc",
]

# ============================================================
# MOTEUR DE DÉTECTION PRINCIPAL
# ============================================================

def analyser_message(message, expediteur=""):
    """
    Analyse un message et retourne un score de risque
    Score : 0 à 100
    Niveau : 1=Suspect, 2=Très suspect, 3=Confirmé arnaque
    """
    score = 0
    details = []
    message_lower = message.lower()

    # ── Règle 1 : Expéditeur numéro ordinaire ──
    if expediteur:
        est_officiel = False
        for num in NUMEROS_OFFICIELS:
            if expediteur.startswith(num) or expediteur == num:
                est_officiel = True
                break
        
        if not est_officiel and re.match(r'^\+?237?6\d{8}$', expediteur):
            score += 40
            details.append("⚠️ Expéditeur est un numéro ordinaire (non officiel)")
        elif est_officiel:
            details.append("✅ Expéditeur semble officiel")

    # ── Règle 2 : Mots-clés critiques ──
    for mot in MOTS_CRITIQUES:
        if mot in message_lower:
            score += 35
            details.append(f"🚨 Mot critique détecté : '{mot}'")
            break  # Un seul suffit

    # ── Règle 3 : Mots-clés suspects ──
    mots_trouves = []
    for mot in MOTS_SUSPECTS:
        if mot in message_lower:
            mots_trouves.append(mot)
    
    if mots_trouves:
        score += min(len(mots_trouves) * 5, 25)
        details.append(f"⚠️ Mots suspects trouvés : {', '.join(mots_trouves[:3])}")

    # ── Règle 4 : Présence de liens ──
    liens = re.findall(r'http[s]?://\S+|www\.\S+|bit\.ly\S*|tinyurl\S*', message_lower)
    if liens:
        score += 20
        details.append(f"🔗 Lien suspect détecté dans le message")
        
        for lien in liens:
            for domaine in DOMAINES_SUSPECTS:
                if domaine in lien:
                    score += 15
                    details.append(f"🚨 Lien raccourci dangereux : {domaine}")
                    break

    # ── Règle 5 : Erreur de calcul ──
    montants = re.findall(r'\d+(?:\s?\d+)*(?:\s?fcfa|\s?f\.?cfa|\s?xaf)?', message_lower)
    if len(montants) >= 2:
        try:
            nombres = [int(re.sub(r'\D', '', m)) for m in montants if re.sub(r'\D', '', m)]
            nombres = [n for n in nombres if n > 100]
            if len(nombres) >= 2:
                if nombres[1] < nombres[0]:
                    score += 15
                    details.append("🧮 Erreur de calcul détectée (solde incohérent)")
        except:
            pass

    # ── Règle 6 : Montant trop élevé suspect ──
    if any(word in message_lower for word in ['500000', '1000000', '5000000', '10000000']):
        score += 10
        details.append("💰 Montant anormalement élevé")

    # ── Règle 7 : Urgence ──
    mots_urgence = ['urgent', 'immédiatement', 'immediatement', 'maintenant', 'vite', 'dépêchez', 'depechez', 'expire dans']
    for mot in mots_urgence:
        if mot in message_lower:
            score += 10
            details.append("⏰ Message d'urgence artificielle détecté")
            break

    # ── Score final ──
    score = min(score, 100)

    # ── Déterminer le niveau ──
    if score >= 70:
        niveau = 3
        niveau_label = "🔴 ARNAQUE CONFIRMÉE"
        recommandation = "Bloquer immédiatement ce numéro et ne pas répondre"
    elif score >= 40:
        niveau = 2
        niveau_label = "🟠 TRÈS SUSPECT"
        recommandation = "Soyez très prudent, évitez de répondre ou de cliquer"
    elif score >= 20:
        niveau = 1
        niveau_label = "🟡 SUSPECT"
        recommandation = "Restez vigilant avec ce message"
    else:
        niveau = 0
        niveau_label = "🟢 PROBABLEMENT SÛR"
        recommandation = "Ce message semble légitime"

    return {
        "score": score,
        "niveau": niveau,
        "niveau_label": niveau_label,
        "recommandation": recommandation,
        "details": details,
    }


def analyser_numero(numero):
    """
    Analyse un numéro de téléphone
    """
    score = 0
    details = []

    # Vérifier si numéro officiel
    est_officiel = False
    for num in NUMEROS_OFFICIELS:
        if numero.startswith(num) or numero == num:
            est_officiel = True
            break

    if est_officiel:
        return {
            "score": 0,
            "niveau": 0,
            "niveau_label": "🟢 NUMÉRO OFFICIEL",
            "recommandation": "Ce numéro semble être un numéro officiel MTN/Orange",
            "details": ["✅ Numéro court officiel reconnu"],
        }

    # Numéro camerounais ordinaire
    if re.match(r'^\+?237?6\d{8}$', numero):
        score += 10
        details.append("📱 Numéro camerounais ordinaire")

    return {
        "score": score,
        "niveau": 1 if score > 0 else 0,
        "niveau_label": "🟡 SUSPECT" if score > 0 else "🟢 INCONNU",
        "recommandation": "Vérifiez ce numéro dans la base communautaire",
        "details": details,
    }


def analyser_lien(url):
    """
    Analyse un lien/URL
    """
    score = 0
    details = []
    url_lower = url.lower()

    # Vérifier domaines suspects
    for domaine in DOMAINES_SUSPECTS:
        if domaine in url_lower:
            score += 50
            details.append(f"🚨 Domaine dangereux détecté : {domaine}")
            break

    # Vérifier mots suspects dans l'URL
    mots_url_suspects = ['gagner', 'gagne', 'prix', 'cadeau', 'gratuit', 'anniversaire', 'offre', 'promo']
    for mot in mots_url_suspects:
        if mot in url_lower:
            score += 20
            details.append(f"⚠️ Mot suspect dans l'URL : '{mot}'")

    # URL trop longue et bizarre
    if len(url) > 100:
        score += 10
        details.append("⚠️ URL anormalement longue")

    score = min(score, 100)

    if score >= 70:
        niveau = 3
        niveau_label = "🔴 LIEN DANGEREUX"
        recommandation = "Ne cliquez surtout pas sur ce lien"
    elif score >= 40:
        niveau = 2
        niveau_label = "🟠 LIEN TRÈS SUSPECT"
        recommandation = "Évitez de cliquer sur ce lien"
    elif score >= 20:
        niveau = 1
        niveau_label = "🟡 LIEN SUSPECT"
        recommandation = "Soyez prudent avec ce lien"
    else:
        niveau = 0
        niveau_label = "🟢 LIEN PROBABLEMENT SÛR"
        recommandation = "Ce lien semble légitime"

    return {
        "score": score,
        "niveau": niveau,
        "niveau_label": niveau_label,
        "recommandation": recommandation,
        "details": details,
    }