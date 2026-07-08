from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import (
    ProfilUtilisateur,
    NumeroCommunautaire,
    Signalement,
    CampagneArnaque,
    LienMalveillant,
    BlocageUtilisateur
)
from .detecteur import analyser_message, analyser_numero, analyser_lien
from django.utils import timezone
from django.db.models import Count

# ============================================================
# AUTHENTIFICATION
# ============================================================

@api_view(['POST'])
def inscription(request):
    """Créer un nouveau compte"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        numero = request.data.get('numero_telephone')
        ville = request.data.get('ville', '')

        if not username or not password or not numero:
            return Response({
                'succes': False,
                'message': 'Username, password et numéro requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({
                'succes': False,
                'message': 'Ce nom d\'utilisateur existe déjà'
            }, status=status.HTTP_400_BAD_REQUEST)

        if ProfilUtilisateur.objects.filter(numero_telephone=numero).exists():
            return Response({
                'succes': False,
                'message': 'Ce numéro est déjà enregistré'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        profil = ProfilUtilisateur.objects.create(
            user=user,
            numero_telephone=numero,
            ville=ville
        )

        return Response({
            'succes': True,
            'message': 'Compte créé avec succès',
            'user_id': user.id,
            'username': user.username
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def connexion(request):
    """Se connecter"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:
            profil = ProfilUtilisateur.objects.get(user=user)
            return Response({
                'succes': True,
                'message': 'Connexion réussie',
                'user_id': user.id,
                'username': user.username,
                'numero_telephone': profil.numero_telephone,
                'ville': profil.ville,
                'protection_active': profil.protection_active
            })
        else:
            return Response({
                'succes': False,
                'message': 'Username ou mot de passe incorrect'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# ANALYSE
# ============================================================

@api_view(['POST'])
def analyser_message_vue(request):
    """Analyser un message suspect"""
    try:
        message = request.data.get('message', '')
        expediteur = request.data.get('expediteur', '')

        if not message:
            return Response({
                'succes': False,
                'message': 'Message requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Analyse du message
        resultat = analyser_message(message, expediteur)

        # Vérifier si l'expéditeur est dans la base communautaire
        if expediteur:
            try:
                numero_db = NumeroCommunautaire.objects.get(numero=expediteur)
                resultat['dans_base_communautaire'] = True
                resultat['signalements_communaute'] = numero_db.nombre_signalements
                resultat['score'] = min(resultat['score'] + 20, 100)
                resultat['details'].append(
                    f"🚨 Numéro déjà signalé {numero_db.nombre_signalements} fois dans la communauté"
                )
            except NumeroCommunautaire.DoesNotExist:
                resultat['dans_base_communautaire'] = False

        return Response({
            'succes': True,
            'resultat': resultat
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyser_numero_vue(request):
    """Analyser un numéro de téléphone"""
    try:
        numero = request.data.get('numero', '')

        if not numero:
            return Response({
                'succes': False,
                'message': 'Numéro requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        resultat = analyser_numero(numero)

        # Vérifier dans la base communautaire
        try:
            numero_db = NumeroCommunautaire.objects.get(numero=numero)
            resultat['dans_base_communautaire'] = True
            resultat['type_arnaque'] = numero_db.type_arnaque
            resultat['nombre_signalements'] = numero_db.nombre_signalements
            resultat['score_confiance'] = numero_db.score_confiance
            resultat['niveau'] = numero_db.niveau
            resultat['confirme'] = numero_db.confirme
            resultat['details'].append(
                f"📋 Dans la base : {numero_db.nombre_signalements} signalements"
            )
        except NumeroCommunautaire.DoesNotExist:
            resultat['dans_base_communautaire'] = False

        return Response({
            'succes': True,
            'resultat': resultat
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyser_lien_vue(request):
    """Analyser un lien suspect"""
    try:
        url = request.data.get('url', '')

        if not url:
            return Response({
                'succes': False,
                'message': 'URL requise'
            }, status=status.HTTP_400_BAD_REQUEST)

        resultat = analyser_lien(url)

        # Vérifier dans la base des liens malveillants
        try:
            lien_db = LienMalveillant.objects.get(url=url)
            resultat['dans_base'] = True
            resultat['signalements'] = lien_db.nombre_signalements
            resultat['details'].append(
                f"🚨 Lien déjà signalé {lien_db.nombre_signalements} fois"
            )
        except LienMalveillant.DoesNotExist:
            resultat['dans_base'] = False

        return Response({
            'succes': True,
            'resultat': resultat
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# BASE COMMUNAUTAIRE
# ============================================================

@api_view(['GET'])
def liste_numeros_frauduleux(request):
    """Récupérer la liste des numéros frauduleux"""
    try:
        niveau = request.GET.get('niveau', None)
        type_arnaque = request.GET.get('type', None)
        recherche = request.GET.get('recherche', None)

        numeros = NumeroCommunautaire.objects.all().order_by('-nombre_signalements')

        if niveau:
            numeros = numeros.filter(niveau=niveau)
        if type_arnaque:
            numeros = numeros.filter(type_arnaque=type_arnaque)
        if recherche:
            numeros = numeros.filter(numero__icontains=recherche)

        data = []
        for n in numeros:
            data.append({
                'id': n.id,
                'numero': n.numero,
                'type_arnaque': n.type_arnaque,
                'niveau': n.niveau,
                'nombre_signalements': n.nombre_signalements,
                'score_confiance': n.score_confiance,
                'confirme': n.confirme,
                'description': n.description,
                'dernier_signalement': n.dernier_signalement,
            })

        return Response({
            'succes': True,
            'total': len(data),
            'numeros': data
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def signaler_arnaque(request):
    """Signaler une arnaque"""
    try:
        numero = request.data.get('numero_signale', '')
        type_arnaque = request.data.get('type_arnaque', '')
        message = request.data.get('message_recu', '')
        description = request.data.get('description', '')
        user_id = request.data.get('user_id', None)

        if not numero or not type_arnaque:
            return Response({
                'succes': False,
                'message': 'Numéro et type d\'arnaque requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer le profil utilisateur
        profil = None
        if user_id:
            try:
                profil = ProfilUtilisateur.objects.get(user__id=user_id)
            except ProfilUtilisateur.DoesNotExist:
                pass

        # Créer le signalement
        signalement = Signalement.objects.create(
            utilisateur=profil,
            numero_signale=numero,
            type_arnaque=type_arnaque,
            message_recu=message,
            description=description
        )

        # Mettre à jour ou créer dans la base communautaire
        numero_db, created = NumeroCommunautaire.objects.get_or_create(
            numero=numero,
            defaults={
                'type_arnaque': type_arnaque,
                'niveau': 1,
                'nombre_signalements': 1,
                'score_confiance': 30.0
            }
        )

        if not created:
            numero_db.nombre_signalements += 1
            # Calculer le niveau selon les signalements
            if numero_db.nombre_signalements >= 5:
                numero_db.niveau = 3
                numero_db.confirme = True
                numero_db.score_confiance = min(90 + numero_db.nombre_signalements, 99)
            elif numero_db.nombre_signalements >= 3:
                numero_db.niveau = 2
                numero_db.score_confiance = min(60 + numero_db.nombre_signalements * 5, 89)
            else:
                numero_db.niveau = 1
                numero_db.score_confiance = min(30 + numero_db.nombre_signalements * 10, 59)
            numero_db.save()

        return Response({
            'succes': True,
            'message': 'Arnaque signalée avec succès. Merci pour votre contribution !',
            'signalement_id': signalement.id,
            'numero_niveau': numero_db.niveau,
            'total_signalements': numero_db.nombre_signalements
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# STATISTIQUES
# ============================================================

@api_view(['GET'])
def statistiques(request):
    """Récupérer les statistiques générales"""
    try:
        total_numeros = NumeroCommunautaire.objects.count()
        total_confirmes = NumeroCommunautaire.objects.filter(confirme=True).count()
        total_signalements = Signalement.objects.count()
        total_utilisateurs = ProfilUtilisateur.objects.count()
        total_campagnes = CampagneArnaque.objects.filter(active=True).count()

        # Par type d'arnaque
        par_type = NumeroCommunautaire.objects.values('type_arnaque').annotate(
            total=Count('id')
        ).order_by('-total')

        # Par niveau
        par_niveau = {
            'suspect': NumeroCommunautaire.objects.filter(niveau=1).count(),
            'tres_suspect': NumeroCommunautaire.objects.filter(niveau=2).count(),
            'confirme': NumeroCommunautaire.objects.filter(niveau=3).count(),
        }

        return Response({
            'succes': True,
            'stats': {
                'total_numeros_frauduleux': total_numeros,
                'total_confirmes': total_confirmes,
                'total_signalements': total_signalements,
                'total_utilisateurs': total_utilisateurs,
                'total_campagnes_actives': total_campagnes,
                'par_type': list(par_type),
                'par_niveau': par_niveau,
            }
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# BLOCAGE UTILISATEUR
# ============================================================

@api_view(['POST'])
def bloquer_numero(request):
    """Bloquer un numéro pour un utilisateur"""
    try:
        user_id = request.data.get('user_id')
        numero = request.data.get('numero')

        profil = ProfilUtilisateur.objects.get(user__id=user_id)
        blocage, created = BlocageUtilisateur.objects.get_or_create(
            utilisateur=profil,
            numero_bloque=numero,
            defaults={'bloque_manuellement': True}
        )

        return Response({
            'succes': True,
            'message': f'Numéro {numero} bloqué avec succès'
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def liste_bloques(request):
    """Récupérer la liste des numéros bloqués d'un utilisateur"""
    try:
        user_id = request.GET.get('user_id')
        profil = ProfilUtilisateur.objects.get(user__id=user_id)
        bloques = BlocageUtilisateur.objects.filter(utilisateur=profil)

        data = [{
            'numero': b.numero_bloque,
            'date_blocage': b.date_blocage,
            'manuel': b.bloque_manuellement,
            'exception': b.exception
        } for b in bloques]

        return Response({
            'succes': True,
            'bloques': data
        })

    except Exception as e:
        return Response({
            'succes': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)