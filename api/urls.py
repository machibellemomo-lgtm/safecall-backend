from django.urls import path
from . import views

urlpatterns = [
    # ── Authentification ──
    path('auth/inscription/', views.inscription, name='inscription'),
    path('auth/connexion/', views.connexion, name='connexion'),

    # ── Analyse ──
    path('analyser/message/', views.analyser_message_vue, name='analyser_message'),
    path('analyser/numero/', views.analyser_numero_vue, name='analyser_numero'),
    path('analyser/lien/', views.analyser_lien_vue, name='analyser_lien'),
    path('analyser/capture/', views.analyser_capture_vue, name='analyser_capture'),

    # ── Base communautaire ──
    path('communaute/liste/', views.liste_numeros_frauduleux, name='liste_numeros'),
    path('communaute/signaler/', views.signaler_arnaque, name='signaler'),
    path('communaute/types-impact/', views.liste_types_impact, name='liste_types_impact'),  # ← nouveau
    path('communaute/detail/', views.detail_numero_vue, name='detail_numero'),
    # ── Statistiques ──
    path('stats/', views.statistiques, name='statistiques'),

    # ── Blocage ──
    path('bloquer/', views.bloquer_numero, name='bloquer'),
    path('bloques/', views.liste_bloques, name='liste_bloques'),
]