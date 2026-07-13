from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from datetime import datetime
from .detecteur import analyser_message, analyser_numero, analyser_lien, detecter_operateur, extraire_info_capture

from .models import (
    ProfilUtilisateur,
    NumeroCommunautaire,
    Signalement,
    CampagneArnaque,
    LienMalveillant,
    BlocageUtilisateur,
    TypeImpact,
)
from .detecteur import analyser_message, analyser_numero, analyser_lien, detecter_operateur


# ============================================================
# AUTHENTIFICATION (inchangé)
# ============================================================

@api_view(['POST'])
def inscription(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        numero = request.data.get('numero_telephone')
        ville = request.data.get('ville', '')

        if not username or not password or not numero:
            return Response({'succes': False, 'message': 'Username, password et numéro requis'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'succes': False, 'message': "Ce nom d'utilisateur existe déjà"}, status=status.HTTP_400_BAD_REQUEST)

        if ProfilUtilisateur.objects.filter(numero_telephone=numero).exists():
            return Response({'succes': False, 'message': 'Ce numéro est déjà enregistré'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        ProfilUtilisateur.objects.create(user=user, numero_telephone=numero, ville=ville)

        return Response({
            'succes': True, 'message': 'Compte créé avec succès',
            'user_id': user.id, 'username': user.username
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def connexion(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user:
            profil = ProfilUtilisateur.objects.get(user=user)
            return Response({
                'succes': True, 'message': 'Connexion réussie',
                'user_id': user.id, 'username': user.username,
                'numero_telephone': profil.numero_telephone,
                'ville': profil.ville, 'protection_active': profil.protection_active
            })
        return Response({'succes': False, 'message': 'Username ou mot de passe incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# ANALYSE
# ============================================================

@api_view(['POST'])
def analyser_message_vue(request):
    """Analyser un message suspect (texte collé ou extrait par OCR)."""
    try:
        message = request.data.get('message', '')
        expediteur = request.data.get('expediteur', '')

        if not message:
            return Response({'succes': False, 'message': 'Message requis'}, status=status.HTTP_400_BAD_REQUEST)

        resultat = analyser_message(message, expediteur)
        resultat['operateur_detecte'] = detecter_operateur(expediteur) if expediteur else None

        if expediteur:
            try:
                numero_db = NumeroCommunautaire.objects.get(numero=expediteur)
                resultat['dans_base_communautaire'] = True
                resultat['signalements_communaute'] = numero_db.nombre_signalements
                resultat['score'] = min(resultat['score'] + 20, 100)
                resultat['details'].append(f"🚨 Numéro déjà signalé {numero_db.nombre_signalements} fois dans la communauté")
            except NumeroCommunautaire.DoesNotExist:
                resultat['dans_base_communautaire'] = False

        return Response({'succes': True, 'resultat': resultat})

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyser_numero_vue(request):
    """Vérifier un numéro (aussi utilisé pour un appel entrant)."""
    try:
        numero = request.data.get('numero', '')
        if not numero:
            return Response({'succes': False, 'message': 'Numéro requis'}, status=status.HTTP_400_BAD_REQUEST)

        resultat = analyser_numero(numero)

        try:
            numero_db = NumeroCommunautaire.objects.get(numero=numero)
            resultat['dans_base_communautaire'] = True
            resultat['operateur'] = numero_db.operateur
            resultat['nom_precis'] = numero_db.nom_precis
            resultat['type_arnaque'] = numero_db.type_arnaque
            resultat['nombre_signalements'] = numero_db.nombre_signalements
            resultat['score_confiance'] = numero_db.score_confiance
            resultat['niveau'] = numero_db.niveau
            resultat['confirme'] = numero_db.confirme
            resultat['details'].append(f"📋 Dans la base : {numero_db.nombre_signalements} signalements")
        except NumeroCommunautaire.DoesNotExist:
            resultat['dans_base_communautaire'] = False

        return Response({'succes': True, 'resultat': resultat})

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyser_lien_vue(request):
    try:
        url = request.data.get('url', '')
        if not url:
            return Response({'succes': False, 'message': 'URL requise'}, status=status.HTTP_400_BAD_REQUEST)

        resultat = analyser_lien(url)

        try:
            lien_db = LienMalveillant.objects.get(url=url)
            resultat['dans_base'] = True
            resultat['signalements'] = lien_db.nombre_signalements
            resultat['details'].append(f"🚨 Lien déjà signalé {lien_db.nombre_signalements} fois")
        except LienMalveillant.DoesNotExist:
            resultat['dans_base'] = False

        return Response({'succes': True, 'resultat': resultat})

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# BASE COMMUNAUTAIRE
# ============================================================

@api_view(['GET'])
def liste_numeros_frauduleux(request):
    """Liste triée par pourcentage de dangerosité (le plus suspect en premier)."""
    try:
        operateur = request.GET.get('operateur', None)
        niveau = request.GET.get('niveau', None)
        type_arnaque = request.GET.get('type', None)
        recherche = request.GET.get('recherche', None)

        numeros = NumeroCommunautaire.objects.all()

        if operateur:
            numeros = numeros.filter(operateur=operateur)
        if niveau:
            numeros = numeros.filter(niveau=niveau)
        if type_arnaque:
            numeros = numeros.filter(type_arnaque=type_arnaque)
        if recherche:
            numeros = numeros.filter(numero__icontains=recherche)

        total_signalements_global = Signalement.objects.count() or 1  # évite division par zéro

        data = []
        for n in numeros:
            pourcentage = round((n.nombre_signalements / total_signalements_global) * 100, 1)
            data.append({
                'id': n.id,
                'numero': n.numero,
                'operateur': n.operateur,
                'nom_precis': n.nom_precis,
                'type_arnaque': n.type_arnaque,
                'niveau': n.niveau,
                'nombre_signalements': n.nombre_signalements,
                'score_confiance': n.score_confiance,
                'pourcentage': pourcentage,
                'confirme': n.confirme,
                'description': n.description,
                'dernier_signalement': n.dernier_signalement,
            })

        # Tri par pourcentage décroissant : le plus suspect en premier
        data.sort(key=lambda x: x['pourcentage'], reverse=True)

        return Response({'succes': True, 'total': len(data), 'numeros': data})

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def detail_numero_vue(request):
    """Détail complet d'un numéro : agrégat + historique de tous les signalements individuels."""
    try:
        numero = request.GET.get('numero', '')
        if not numero:
            return Response({'succes': False, 'message': 'Numéro requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            numero_db = NumeroCommunautaire.objects.get(numero=numero)
        except NumeroCommunautaire.DoesNotExist:
            return Response({'succes': False, 'message': 'Numéro non trouvé dans la base communautaire'}, status=status.HTTP_404_NOT_FOUND)

        total_signalements_global = Signalement.objects.count() or 1
        pourcentage = round((numero_db.nombre_signalements / total_signalements_global) * 100, 1)

        signalements = Signalement.objects.filter(numero_signale=numero).order_by('-date_incident')

        data_signalements = []
        for s in signalements:
            item = {
                'type_arnaque': s.type_arnaque,
                'moyen_utilise': s.moyen_utilise,
                'date_incident': s.date_incident,
                'heure_incident': s.heure_incident,
                'date_approximative': s.date_approximative,
                'attaque_reussie': s.attaque_reussie,
                'types_impact': [t.libelle for t in s.types_impact.all()],
                'montant_perdu': s.montant_perdu,
                'description_impact': s.description_impact,
                'description': s.description,
                'message_recu': s.message_recu,
            }
            if s.afficher_identite:
                item['nom_declarant'] = s.nom_declarant
                item['numero_declarant'] = s.numero_declarant
                item['ville_incident'] = s.ville_incident
                item['region_incident'] = s.region_incident
            data_signalements.append(item)

        return Response({
            'succes': True,
            'numero': {
                'numero': numero_db.numero,
                'operateur': numero_db.operateur,
                'nom_precis': numero_db.nom_precis,
                'niveau': numero_db.niveau,
                'nombre_signalements': numero_db.nombre_signalements,
                'pourcentage': pourcentage,
                'confirme': numero_db.confirme,
                'premier_signalement': numero_db.premier_signalement,
                'dernier_signalement': numero_db.dernier_signalement,
            },
            'signalements': data_signalements,
        })
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def signaler_arnaque(request):
    """
    Créer ou mettre à jour un signalement.
    Un même compte ne peut signaler qu'une fois le même numéro
    (une nouvelle tentative met à jour son signalement existant).
    """
    try:
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'succes': False, 'message': 'Vous devez être connecté pour signaler'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            profil = ProfilUtilisateur.objects.get(user__id=user_id)
        except ProfilUtilisateur.DoesNotExist:
            return Response({'succes': False, 'message': 'Profil utilisateur introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # ── Champs obligatoires ──
        numero = request.data.get('numero_signale', '').strip()
        operateur = request.data.get('operateur', '')
        type_arnaque = request.data.get('type_arnaque', '')
        moyen_utilise = request.data.get('moyen_utilise', '')
        date_incident_str = request.data.get('date_incident', '')
        attaque_reussie = request.data.get('attaque_reussie', False)

        champs_manquants = []
        if not numero: champs_manquants.append('numero_signale')
        if not operateur: champs_manquants.append('operateur')
        if not type_arnaque: champs_manquants.append('type_arnaque')
        if not moyen_utilise: champs_manquants.append('moyen_utilise')
        if not date_incident_str: champs_manquants.append('date_incident')

        description = request.data.get('description', '').strip()
        if type_arnaque == 'autre' and not description:
            champs_manquants.append('description (obligatoire pour le type "autre")')

        if champs_manquants:
            return Response({
                'succes': False,
                'message': f"Champs obligatoires manquants : {', '.join(champs_manquants)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        date_incident = parse_date(date_incident_str)
        if not date_incident:
            return Response({'succes': False, 'message': 'Format de date_incident invalide (attendu YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        heure_incident_str = request.data.get('heure_incident', '')
        heure_incident = parse_time(heure_incident_str) if heure_incident_str else None

        # ── Création ou mise à jour (dédoublonnage par utilisateur+numéro) ──
        signalement, created = Signalement.objects.update_or_create(
            utilisateur=profil,
            numero_signale=numero,
            defaults={
                'nom_declarant': request.data.get('nom_declarant', ''),
                'numero_declarant': request.data.get('numero_declarant', ''),
                'afficher_identite': request.data.get('afficher_identite', False),
                'operateur': operateur,
                'nom_precis': request.data.get('nom_precis', ''),
                'type_arnaque': type_arnaque,
                'moyen_utilise': moyen_utilise,
                'date_incident': date_incident,
                'heure_incident': heure_incident,
                'date_approximative': request.data.get('date_approximative', False),
                'ville_incident': request.data.get('ville_incident', ''),
                'region_incident': request.data.get('region_incident', ''),
                'attaque_reussie': attaque_reussie,
                'montant_perdu': request.data.get('montant_perdu') or None,
                'description_impact': request.data.get('description_impact', ''),
                'message_recu': request.data.get('message_recu', ''),
                'description': description,
            }
        )

        # ── Types d'impact (plusieurs possibles) ──
        codes_impact = request.data.get('types_impact', [])  # ex: ['perte_financiere', 'vol_donnees']
        if codes_impact:
            types_impact_objs = TypeImpact.objects.filter(code__in=codes_impact)
            signalement.types_impact.set(types_impact_objs)
        else:
            signalement.types_impact.clear()

        # ── Mise à jour de la base communautaire agrégée ──
        # Le nombre de signalements = nombre de comptes distincts ayant signalé ce numéro
        nombre_reel = Signalement.objects.filter(numero_signale=numero).values('utilisateur').distinct().count()

        numero_db, num_created = NumeroCommunautaire.objects.get_or_create(
            numero=numero,
            defaults={
                'operateur': operateur,
                'nom_precis': request.data.get('nom_precis', ''),
                'type_arnaque': type_arnaque,
                'niveau': 1,
                'nombre_signalements': nombre_reel,
                'score_confiance': 30.0,
            }
        )

        if not num_created:
            numero_db.operateur = operateur
            numero_db.nom_precis = request.data.get('nom_precis', '') or numero_db.nom_precis
            numero_db.nombre_signalements = nombre_reel

        if nombre_reel >= 5:
            numero_db.niveau = 3
            numero_db.confirme = True
            numero_db.score_confiance = min(90 + nombre_reel, 99)
        elif nombre_reel >= 3:
            numero_db.niveau = 2
            numero_db.score_confiance = min(60 + nombre_reel * 5, 89)
        else:
            numero_db.niveau = 1
            numero_db.score_confiance = min(30 + nombre_reel * 10, 59)
        numero_db.save()

        return Response({
            'succes': True,
            'message': 'Signalement enregistré avec succès. Merci pour votre contribution !' if created else 'Votre signalement pour ce numéro a été mis à jour.',
            'signalement_id': signalement.id,
            'nouveau': created,
            'numero_niveau': numero_db.niveau,
            'total_signalements': numero_db.nombre_signalements,
        })

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def liste_types_impact(request):
    """Pour peupler les cases à cocher côté app mobile."""
    try:
        types = TypeImpact.objects.all()
        data = [{'code': t.code, 'libelle': t.libelle} for t in types]
        return Response({'succes': True, 'types_impact': data})
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# STATISTIQUES
# ============================================================

@api_view(['GET'])
def statistiques(request):
    """
    Vue d'ensemble : totaux, répartition par opérateur, par canal,
    par type d'arnaque, et évolution dans le temps.
    Paramètre optionnel : ?periode=jour|semaine|mois|annee (défaut: mois)
    """
    try:
        total_numeros = NumeroCommunautaire.objects.count()
        total_confirmes = NumeroCommunautaire.objects.filter(confirme=True).count()
        total_signalements = Signalement.objects.count()
        total_utilisateurs = ProfilUtilisateur.objects.count()

        # ── Répartition par opérateur (diagramme en bâton) ──
        par_operateur = list(
            Signalement.objects.values('operateur').annotate(total=Count('id')).order_by('-total')
        )

        # ── Répartition par moyen utilisé (diagramme en cercle) ──
        par_moyen = list(
            Signalement.objects.values('moyen_utilise').annotate(total=Count('id')).order_by('-total')
        )

        # ── Répartition par type d'arnaque (diagramme en bâton) ──
        par_type = list(
            Signalement.objects.values('type_arnaque').annotate(total=Count('id')).order_by('-total')
        )

        # ── Répartition par niveau ──
        par_niveau = {
            'suspect': NumeroCommunautaire.objects.filter(niveau=1).count(),
            'tres_suspect': NumeroCommunautaire.objects.filter(niveau=2).count(),
            'confirme': NumeroCommunautaire.objects.filter(niveau=3).count(),
        }

        # ── Évolution dans le temps (courbe) ──
        periode = request.GET.get('periode', 'mois')
        trunc_fn = {'jour': TruncDate, 'semaine': TruncWeek, 'mois': TruncMonth, 'annee': TruncYear}.get(periode, TruncMonth)

        evolution = list(
            Signalement.objects
            .annotate(periode=trunc_fn('date_incident'))
            .values('periode')
            .annotate(total=Count('id'))
            .order_by('periode')
        )
        evolution = [{'periode': e['periode'].isoformat() if e['periode'] else None, 'total': e['total']} for e in evolution]

        return Response({
            'succes': True,
            'stats': {
                'total_numeros_frauduleux': total_numeros,
                'total_confirmes': total_confirmes,
                'total_signalements': total_signalements,
                'total_utilisateurs': total_utilisateurs,
                'par_operateur': par_operateur,
                'par_moyen_utilise': par_moyen,
                'par_type': par_type,
                'par_niveau': par_niveau,
                'evolution': evolution,
                'periode_utilisee': periode,
            }
        })

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# BLOCAGE UTILISATEUR (inchangé)
# ============================================================

@api_view(['POST'])
def bloquer_numero(request):
    try:
        user_id = request.data.get('user_id')
        numero = request.data.get('numero')
        profil = ProfilUtilisateur.objects.get(user__id=user_id)
        BlocageUtilisateur.objects.get_or_create(
            utilisateur=profil, numero_bloque=numero, defaults={'bloque_manuellement': True}
        )
        return Response({'succes': True, 'message': f'Numéro {numero} bloqué avec succès'})
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def liste_bloques(request):
    try:
        user_id = request.GET.get('user_id')
        profil = ProfilUtilisateur.objects.get(user__id=user_id)
        bloques = BlocageUtilisateur.objects.filter(utilisateur=profil)
        data = [{
            'numero': b.numero_bloque, 'date_blocage': b.date_blocage,
            'manuel': b.bloque_manuellement, 'exception': b.exception
        } for b in bloques]
        return Response({'succes': True, 'bloques': data})
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyser_capture_vue(request):
    """Analyser une capture d'écran : extraction via Gemini puis scoring par nos règles."""
    try:
        image_base64 = request.data.get('image_base64', '')
        mime_type = request.data.get('mime_type', 'image/jpeg')

        if not image_base64:
            return Response({'succes': False, 'message': 'Image requise'}, status=status.HTTP_400_BAD_REQUEST)

        extraction = extraire_info_capture(image_base64, mime_type)

        if extraction['erreur']:
            return Response({'succes': False, 'message': extraction['erreur']}, status=status.HTTP_502_BAD_GATEWAY)

        if not extraction['message']:
            return Response({
                'succes': False,
                'message': "Aucun texte n'a pu être extrait de cette image. Essayez une capture plus nette."
            }, status=status.HTTP_400_BAD_REQUEST)

        expediteur = extraction['expediteur']
        resultat = analyser_message(extraction['message'], expediteur)
        resultat['operateur_detecte'] = detecter_operateur(expediteur) if expediteur else None
        resultat['texte_extrait'] = extraction['message']
        resultat['expediteur_extrait'] = expediteur

        if expediteur:
            try:
                numero_db = NumeroCommunautaire.objects.get(numero=expediteur)
                resultat['dans_base_communautaire'] = True
                resultat['signalements_communaute'] = numero_db.nombre_signalements
                resultat['score'] = min(resultat['score'] + 20, 100)
                resultat['details'].append(f"🚨 Numéro déjà signalé {numero_db.nombre_signalements} fois dans la communauté")
            except NumeroCommunautaire.DoesNotExist:
                resultat['dans_base_communautaire'] = False

        return Response({'succes': True, 'resultat': resultat})

    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def gestion_blocage_vue(request):
    """Numéros Très suspects/Confirmés + décision actuelle de l'utilisateur pour chacun."""
    try:
        user_id = request.GET.get('user_id')
        profil = ProfilUtilisateur.objects.get(user__id=user_id)

        numeros = NumeroCommunautaire.objects.filter(niveau__gte=2).order_by('-niveau', '-nombre_signalements')
        decisions = {b.numero_bloque: b for b in BlocageUtilisateur.objects.filter(utilisateur=profil)}

        data = []
        for n in numeros:
            decision = decisions.get(n.numero)
            if decision:
                bloque = decision.bloque_manuellement and not decision.exception
            else:
                bloque = (n.niveau == 3)  # Confirmé = coché par défaut ; Très suspect = décoché par défaut

            data.append({
                'numero': n.numero,
                'operateur': n.operateur,
                'nom_precis': n.nom_precis,
                'niveau': n.niveau,
                'nombre_signalements': n.nombre_signalements,
                'bloque': bloque,
            })

        return Response({'succes': True, 'numeros': data})
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def definir_blocage_vue(request):
    """Définit si l'utilisateur veut bloquer ou faire une exception pour un numéro."""
    try:
        user_id = request.data.get('user_id')
        numero = request.data.get('numero')
        bloquer = request.data.get('bloquer', True)

        profil = ProfilUtilisateur.objects.get(user__id=user_id)

        blocage, created = BlocageUtilisateur.objects.get_or_create(
            utilisateur=profil,
            numero_bloque=numero,
            defaults={'bloque_manuellement': bloquer, 'exception': not bloquer}
        )
        if not created:
            blocage.bloque_manuellement = bloquer
            blocage.exception = not bloquer
            blocage.save()

        return Response({'succes': True, 'message': 'Préférence enregistrée'})
    except Exception as e:
        return Response({'succes': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)