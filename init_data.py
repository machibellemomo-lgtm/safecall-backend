import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safecall.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import TypeImpact

# ── Admin ──
u, created = User.objects.get_or_create(username='admin')
u.set_password('admin1234')
u.is_staff = True
u.is_superuser = True
u.save()
print('Admin OK')

# ── Types d'impact ──
types_impact = [
    ('perte_financiere', 'Perte financière'),
    ('vol_donnees', 'Vol de données personnelles'),
    ('piratage_compte', 'Piratage de compte'),
    ('vol_mot_de_passe', 'Vol de mot de passe'),
    ('aucun', 'Aucun impact (tentative échouée)'),
    ('autre', 'Autre'),
]
for code, libelle in types_impact:
    TypeImpact.objects.get_or_create(code=code, defaults={'libelle': libelle})
print('Types impact OK')