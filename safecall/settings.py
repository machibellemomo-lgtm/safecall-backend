import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';

function LigneParametre({ icone, couleurIcone, fondIcone, titre, sousTitre, droite, onPress }) {
  const Composant = onPress ? TouchableOpacity : View;
  return (
    <Composant style={styles.ligne} onPress={onPress} activeOpacity={0.7}>
      <View style={[styles.ligneIcone, { backgroundColor: fondIcone }]}>
        <Ionicons name={icone} size={18} color={couleurIcone} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.ligneTitre}>{titre}</Text>
        {sousTitre ? <Text style={styles.ligneSousTitre}>{sousTitre}</Text> : null}
      </View>
      {droite}
    </Composant>
  );
}

export default function SettingsScreen({ navigation }) {
  const { seDeconnecter } = useAuth();

  const [protectionActive, setProtectionActive] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [sons, setSons] = useState(true);
  const [afficherIdentiteParDefaut, setAfficherIdentiteParDefaut] = useState(false);
  const [modeSombre, setModeSombre] = useState(false);

  const confirmerDeconnexion = () => {
    Alert.alert('Se déconnecter', 'Voulez-vous vraiment vous déconnecter ?', [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Se déconnecter', style: 'destructive', onPress: seDeconnecter },
    ]);
  };

  const confirmerSuppression = () => {
    Alert.alert('Supprimer mon compte', "Cette action est irréversible. Contactez le support pour supprimer définitivement votre compte.", [{ text: 'Compris' }]);
  };

  return (
    <ScrollView style={styles.conteneur}>
      <View style={styles.entete}>
        <Text style={styles.titre}>Paramètres</Text>
      </View>

      <Text style={styles.sectionLabel}>Protection</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="shield-checkmark-outline" couleurIcone="#2ECC71" fondIcone="#E8F8EE"
          titre="Protection active" sousTitre="Activer la protection communautaire"
          droite={<Switch value={protectionActive} onValueChange={setProtectionActive} trackColor={{ true: '#2ECC71' }} />}
        />
      </View>

      <Text style={styles.sectionLabel}>Notifications</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="notifications-outline" couleurIcone="#1B4870" fondIcone="#E8F0FA"
          titre="Notifications" sousTitre="Recevoir des alertes de l'application"
          droite={<Switch value={notifications} onValueChange={setNotifications} trackColor={{ true: '#1B4870' }} />}
        />
        <View style={styles.separateur} />
        <LigneParametre
          icone="volume-high-outline" couleurIcone="#1B4870" fondIcone="#E8F0FA"
          titre="Sons" sousTitre="Jouer un son pour les alertes"
          droite={<Switch value={sons} onValueChange={setSons} trackColor={{ true: '#1B4870' }} />}
        />
      </View>

      <Text style={styles.sectionLabel}>Confidentialité</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="eye-outline" couleurIcone="#E67E22" fondIcone="#FDF3E7"
          titre="Afficher mon identité par défaut" sousTitre="Sur les nouveaux signalements"
          droite={<Switch value={afficherIdentiteParDefaut} onValueChange={setAfficherIdentiteParDefaut} trackColor={{ true: '#E67E22' }} />}
        />
      </View>

      <Text style={styles.sectionLabel}>Apparence</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="moon-outline" couleurIcone="#3A4A6B" fondIcone="#EEF1F6"
          titre="Mode sombre" sousTitre="Bientôt disponible"
          droite={<Switch value={modeSombre} onValueChange={setModeSombre} disabled trackColor={{ true: '#3A4A6B' }} />}
        />
      </View>

      <Text style={styles.sectionLabel}>Compte</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="person-outline" couleurIcone="#1B4870" fondIcone="#E8F0FA"
          titre="Modifier mon profil"
          onPress={() => navigation.navigate('MainTabs', { screen: 'Profil' })}
          droite={<Ionicons name="chevron-forward" size={18} color="#DDE3ED" />}
        />
        <View style={styles.separateur} />
        <LigneParametre
          icone="log-out-outline" couleurIcone="#E67E22" fondIcone="#FDF3E7"
          titre="Se déconnecter"
          onPress={confirmerDeconnexion}
          droite={<Ionicons name="chevron-forward" size={18} color="#DDE3ED" />}
        />
        <View style={styles.separateur} />
        <LigneParametre
          icone="trash-outline" couleurIcone="#C0392B" fondIcone="#FDEDEC"
          titre="Supprimer mon compte"
          onPress={confirmerSuppression}
          droite={<Ionicons name="chevron-forward" size={18} color="#DDE3ED" />}
        />
      </View>

      <Text style={styles.sectionLabel}>Aide</Text>
      <View style={styles.carte}>
        <LigneParametre
          icone="help-circle-outline" couleurIcone="#1B4870" fondIcone="#E8F0FA"
          titre="Comment utiliser SafeCall CM"
          onPress={() => Alert.alert('Aide', 'SafeCall CM vous permet de signaler et consulter les arnaques téléphoniques signalées par la communauté au Cameroun.')}
          droite={<Ionicons name="chevron-forward" size={18} color="#DDE3ED" />}
        />
        <View style={styles.separateur} />
        <LigneParametre
          icone="information-circle-outline" couleurIcone="#1B4870" fondIcone="#E8F0FA"
          titre="À propos" sousTitre="SafeCall CM v1.0"
          droite={null}
        />
      </View>

      <View style={{ height: 30 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  conteneur: { flex: 1, backgroundColor: '#F5F7FA' },
  entete: { padding: 20, paddingBottom: 10 },
  titre: { fontSize: 22, fontWeight: '800', color: '#1A2B4C' },
  sectionLabel: { fontSize: 12, fontWeight: '700', color: '#8A96AB', marginLeft: 24, marginTop: 20, marginBottom: 8, textTransform: 'uppercase' },
  carte: {
    backgroundColor: '#FFFFFF', marginHorizontal: 20, borderRadius: 14,
    shadowColor: '#0F2A4A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.04, shadowRadius: 8, elevation: 1,
  },
  separateur: { height: 1, backgroundColor: '#F0F2F6', marginLeft: 60 },
  ligne: { flexDirection: 'row', alignItems: 'center', padding: 14 },
  ligneIcone: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  ligneTitre: { fontSize: 13.5, fontWeight: '600', color: '#1A2B4C' },
  ligneSousTitre: { fontSize: 11.5, color: '#8A96AB', marginTop: 1 },
});