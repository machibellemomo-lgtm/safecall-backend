from django.db import models
from django.contrib.auth.models import User

# ============================================================
# CHOIX FIXES
# ============================================================

OPERATEURS = [
    ('mtn', 'MTN Cameroun'),
    ('orange', 'Orange Cameroun'),
    ('camtel', 'Camtel'),
    ('banque', 'Banque'),
    ('autre', 'Autre / Inconnu'),
]

TYPE_ARNAQUE = [
    ('faux_depot', 'Faux dépôt'),
    ('faux_conseiller', 'Faux conseiller / agent'),
    ('lien_suspect', 'Lien suspect'),
    ('fausse_loterie', 'Fausse loterie / faux gain'),
    ('faux_bancaire', 'Faux message bancaire'),
    ('appel_frauduleux', 'Appel frauduleux (numéro déjà signalé)'),
    ('autre', 'Autre'),
]

MOYENS_UTILISES = [
    ('sms', 'SMS'),
    ('appel', 'Appel téléphonique'),
    ('whatsapp', 'WhatsApp'),
    ('email', 'Email'),
    ('autre', 'Autre'),
]

NIVEAU_DANGER = [
    (1, 'Suspect'),
    (2, 'Très suspect'),
    (3, 'Confirmé'),
]


# ============================================================
# PROFIL UTILISATEUR
# ============================================================

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


# ============================================================
# TYPES D'IMPACT (plusieurs possibles par signalement)
# ============================================================

class TypeImpact(models.Model):
    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=100)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Type d'impact"
        verbose_name_plural = "Types d'impact"


# ============================================================
# NUMÉROS FRAUDULEUX (base communautaire agrégée)
# ============================================================

class NumeroCommunautaire(models.Model):
    numero = models.CharField(max_length=20, unique=True)
    operateur = models.CharField(max_length=20, choices=OPERATEURS)
    nom_precis = models.CharField(max_length=100, blank=True)  # nom banque ou opérateur "autre"
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    niveau = models.IntegerField(choices=NIVEAU_DANGER, default=1)
    nombre_signalements = models.IntegerField(default=0)
    score_confiance = models.FloatField(default=0.0)
    description = models.TextField(blank=True)
    premier_signalement = models.DateTimeField(auto_now_add=True)
    dernier_signalement = models.DateTimeField(auto_now=True)
    confirme = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.numero} - {self.get_type_arnaque_display()} - Niveau {self.niveau}"

    class Meta:
        verbose_name = "Numéro Frauduleux"
        verbose_name_plural = "Numéros Frauduleux"
        ordering = ['-nombre_signalements']


# ============================================================
# SIGNALEMENTS (le formulaire complet)
# ============================================================

class Signalement(models.Model):
    # Lien interne obligatoire (dédoublonnage : 1 signalement par compte par numéro)
    utilisateur = models.ForeignKey(
        ProfilUtilisateur,
        on_delete=models.CASCADE,
        related_name='signalements'
    )

    # Identité affichée publiquement — FACULTATIVE
    nom_declarant = models.CharField(max_length=100, blank=True)
    numero_declarant = models.CharField(max_length=20, blank=True)
    afficher_identite = models.BooleanField(default=False)

    # Infos sur l'arnaqueur — OBLIGATOIRE
    numero_signale = models.CharField(max_length=20)
    operateur = models.CharField(max_length=20, choices=OPERATEURS)
    nom_precis = models.CharField(max_length=100, blank=True)  # nom de la banque si operateur='banque'
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    moyen_utilise = models.CharField(max_length=20, choices=MOYENS_UTILISES)

    # Date/heure de l'INCIDENT (différente de la date de signalement)
    date_incident = models.DateField()
    heure_incident = models.TimeField(null=True, blank=True)
    date_approximative = models.BooleanField(default=False)

    # Localisation (champ simple, texte libre)
    ville_incident = models.CharField(max_length=100, blank=True)
    region_incident = models.CharField(max_length=100, blank=True)

    # Résultat et impact
    attaque_reussie = models.BooleanField(default=False)
    types_impact = models.ManyToManyField(TypeImpact, blank=True, related_name='signalements')
    montant_perdu = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    description_impact = models.TextField(blank=True)

    # Contenu original
    message_recu = models.TextField(blank=True)
    description = models.TextField(blank=True)

    # Méta
    date_signalement = models.DateTimeField(auto_now_add=True)
    valide = models.BooleanField(default=False)

    def __str__(self):
        return f"Signalement {self.numero_signale} ({self.get_type_arnaque_display()}) - {self.date_signalement:%d/%m/%Y}"

    class Meta:
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"
        unique_together = ['utilisateur', 'numero_signale']
        ordering = ['-date_signalement']


# ============================================================
# CAMPAGNES D'ARNAQUE (inchangé)
# ============================================================

class CampagneArnaque(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField()
    type_arnaque = models.CharField(max_length=50, choices=TYPE_ARNAQUE)
    date_detection = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    nombre_signalements = models.IntegerField(default=0)
    numeros = models.ManyToManyField(NumeroCommunautaire, blank=True)

    def __str__(self):
        return f"{self.nom} - {self.get_type_arnaque_display()}"

    class Meta:
        verbose_name = "Campagne d'Arnaque"
        verbose_name_plural = "Campagnes d'Arnaque"


# ============================================================
# LIENS MALVEILLANTS (inchangé)
# ============================================================

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


# ============================================================
# BLOCAGES UTILISATEUR (inchangé)
# ============================================================

class BlocageUtilisateur(models.Model):
    utilisateur = models.ForeignKey(ProfilUtilisateur, on_delete=models.CASCADE)
    numero_bloque = models.CharField(max_length=20)
    date_blocage = models.DateTimeField(auto_now_add=True)
    bloque_manuellement = models.BooleanField(default=False)
    exception = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.utilisateur} bloque {self.numero_bloque}"

    class Meta:
        verbose_name = "Blocage"
        unique_together = ['utilisateur', 'numero_bloque']