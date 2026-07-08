from django.contrib import admin
from .models import (
    ProfilUtilisateur,
    NumeroCommunautaire,
    Signalement,
    CampagneArnaque,
    LienMalveillant,
    BlocageUtilisateur
)

@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['user', 'numero_telephone', 'ville', 'protection_active', 'date_inscription']
    search_fields = ['user__username', 'numero_telephone', 'ville']
    list_filter = ['protection_active', 'actif']

@admin.register(NumeroCommunautaire)
class NumeroCommunautaireAdmin(admin.ModelAdmin):
    list_display = ['numero', 'type_arnaque', 'niveau', 'nombre_signalements', 'score_confiance', 'confirme', 'dernier_signalement']
    search_fields = ['numero', 'description']
    list_filter = ['type_arnaque', 'niveau', 'confirme']
    list_editable = ['niveau', 'confirme']

@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display = ['numero_signale', 'type_arnaque', 'utilisateur', 'date_signalement', 'valide']
    search_fields = ['numero_signale', 'message_recu']
    list_filter = ['type_arnaque', 'valide']
    list_editable = ['valide']

@admin.register(CampagneArnaque)
class CampagneArnaqueAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_arnaque', 'nombre_signalements', 'active', 'date_detection']
    search_fields = ['nom', 'description']
    list_filter = ['type_arnaque', 'active']

@admin.register(LienMalveillant)
class LienMalveillantAdmin(admin.ModelAdmin):
    list_display = ['domaine', 'url', 'type_arnaque', 'niveau', 'nombre_signalements', 'actif']
    search_fields = ['domaine', 'url']
    list_filter = ['type_arnaque', 'niveau', 'actif']

@admin.register(BlocageUtilisateur)
class BlocageUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'numero_bloque', 'date_blocage', 'bloque_manuellement', 'exception']
    search_fields = ['numero_bloque']
    list_filter = ['bloque_manuellement', 'exception']