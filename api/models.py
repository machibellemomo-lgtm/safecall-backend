from django.db import models
from django.contrib.auth.models import User

# Types d'arnaque
TYPE_ARNAQUE = [
    ('faux_depot', 'Faux dépôt MTN/Orange'),
    ('appel_frauduleux', 'Appel frauduleux'),
    ('lien_suspect', 'Lien suspect'),
    ('faux_bank', 'Faux message bancaire'),
    ('whatsapp', 'Arnaque WhatsApp'),
    ('autre', 'Autre'),
]

# Niveaux de danger
NIVEAU_DANGER = [
    (1, 'Suspect'),
    (2, 'Très suspect'),
    (3, 'Confirmé'),
]

# Profil utilisateur
class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    numero_telephone = models.CharField(max_length=20, unique=True)
    ville = models.CharField(max_length=100, blank=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    protection_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.numero_telephone}"

    class Meta:
        verbose_name = "Profil Utilisateur"

# Numéros frauduleux
class NumeroCommunautaire(models.Model):
    numero = models.CharField(max_length=20, unique=True)
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    niveau = models.IntegerField(choices=NIVEAU_DANGER, default=1)
    nombre_signalements = models.IntegerField(default=1)
    score_confiance = models.FloatField(default=0.0)
    description = models.TextField(blank=True)
    premier_signalement = models.DateTimeField(auto_now_add=True)
    dernier_signalement = models.DateTimeField(auto_now=True)
    confirme = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.numero} - {self.type_arnaque} - Niveau {self.niveau}"

    class Meta:
        verbose_name = "Numéro Frauduleux"
        verbose_name_plural = "Numéros Frauduleux"

# Signalements
class Signalement(models.Model):
    utilisateur = models.ForeignKey(
        ProfilUtilisateur,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    numero_signale = models.CharField(max_length=20)
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    message_recu = models.TextField(blank=True)
    description = models.TextField(blank=True)
    date_signalement = models.DateTimeField(auto_now_add=True)
    valide = models.BooleanField(default=False)

    def __str__(self):
        return f"Signalement {self.numero_signale} - {self.date_signalement}"

    class Meta:
        verbose_name = "Signalement"

# Campagnes d'arnaque
class CampagneArnaque(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField()
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    date_detection = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    nombre_signalements = models.IntegerField(default=0)
    numeros = models.ManyToManyField(NumeroCommunautaire, blank=True)

    def __str__(self):
        return f"{self.nom} - {self.type_arnaque}"

    class Meta:
        verbose_name = "Campagne d'Arnaque"
        verbose_name_plural = "Campagnes d'Arnaque"

# Liens malveillants
class LienMalveillant(models.Model):
    url = models.URLField(max_length=500)
    domaine = models.CharField(max_length=200)
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    nombre_signalements = models.IntegerField(default=1)
    niveau = models.IntegerField(choices=NIVEAU_DANGER, default=1)
    date_detection = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.domaine} - Niveau {self.niveau}"

    class Meta:
        verbose_name = "Lien Malveillant"
        verbose_name_plural = "Liens Malveillants"

# Blocages utilisateur
class BlocageUtilisateur(models.Model):
    utilisateur = models.ForeignKey(
        ProfilUtilisateur,
        on_delete=models.CASCADE
    )
    numero_bloque = models.CharField(max_length=20)
    date_blocage = models.DateTimeField(auto_now_add=True)
    bloque_manuellement = models.BooleanField(default=False)
    exception = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.utilisateur} bloque {self.numero_bloque}"

    class Meta:
        verbose_name = "Blocage"
        unique_together = ['utilisateur', 'numero_bloque']