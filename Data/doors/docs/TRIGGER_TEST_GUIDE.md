# 🧪 Guide de Test des Triggers - Identification des Portes

**Objectif**: Identifier quels triggers dans LEVELS.DAT correspondent à des portes en les désactivant par groupes et en observant les changements en jeu.

---

## 📊 État Actuel

**✅ Extraction Complète**:
- **500 triggers** extraits de LEVELS.DAT
- **5 patches de test** créés (groupes de 20 triggers)
- Base de données: `trigger_tests/triggers_database.json`

**Fichiers de test créés**:
```
trigger_tests/
├── triggers_database.json        (Base de données complète)
├── LEVELS_TEST_GROUP1.DAT        (Triggers 1-20 désactivés)
├── LEVELS_TEST_GROUP2.DAT        (Triggers 21-40 désactivés)
├── LEVELS_TEST_GROUP3.DAT        (Triggers 41-60 désactivés)
├── LEVELS_TEST_GROUP4.DAT        (Triggers 61-80 désactivés)
├── LEVELS_TEST_GROUP5.DAT        (Triggers 81-100 désactivés)
└── test_groupN_notes.txt         (Notes pour chaque groupe)
```

---

## 🎯 Méthodologie de Test

### Phase 1: Test par Groupes (Rapide)

**But**: Identifier rapidement quels groupes contiennent des portes

**Procédure pour chaque groupe**:

1. **Backup**: Sauvegarder le BIN original
2. **Patcher**: Remplacer LEVELS.DAT dans le BIN
3. **Tester**: Lancer le jeu et explorer
4. **Noter**: Quelles portes ont disparu ou sont inaccessibles
5. **Comparer**: Avec le jeu vanilla

**Commande de patch** (voir section Scripts ci-dessous)

### Phase 2: Test Individuels (Précis)

Une fois les groupes identifiés, tester les triggers individuellement:

```bash
py -3 test_triggers_system.py disable <ID>
```

---

## 🛠️ Scripts et Commandes

### Extraire les Triggers (Déjà Fait)
```bash
cd Data/doors
py -3 test_triggers_system.py extract
```

### Créer un Patch de Groupe
```bash
py -3 test_triggers_system.py patch 1    # Groupe 1
py -3 test_triggers_system.py patch 2    # Groupe 2
# etc.
```

### Désactiver un Trigger Spécifique
```bash
py -3 test_triggers_system.py disable 42  # Désactive trigger #42
```

### Voir les Infos
```bash
py -3 test_triggers_system.py info
```

---

## 📝 Template de Notes de Test

Pour chaque groupe testé, noter:

```
=== TEST GROUPE N ===
Date: [date]
Version: LEVELS_TEST_GROUPN.DAT

ZONES TESTÉES:
□ Cavern of Death - Floor 1
□ Cavern of Death - Floor 2
□ Forest of Despair
□ Castle of Vamp
□ etc.

PORTES AFFECTÉES:
□ Porte [description] dans [zone] - DISPARUE
□ Porte [description] dans [zone] - TOUJOURS LÀ
□ etc.

AUTRES EFFETS:
- [noter tout changement: spawn points, collisions, etc.]

CONCLUSION:
- Triggers de portes probables: [IDs]
- Faux positifs: [IDs]
```

---

## 🔧 Remplacement de LEVELS.DAT dans le BIN

### Méthode Manuelle

1. Extraire le BIN actuel (si pas déjà fait)
2. Remplacer `extract/LEVELS.DAT` par le fichier de test
3. Reconstruire le BIN

### Script Automatique (À créer)

Créer `apply_trigger_test.bat`:
```batch
@echo off
set GROUP=%1
if "%GROUP%"=="" (
    echo Usage: apply_trigger_test.bat N  ^(N=1-5^)
    exit /b
)

echo Applying trigger test group %GROUP%...
copy /Y "Data\doors\trigger_tests\LEVELS_TEST_GROUP%GROUP%.DAT" "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT"
echo Rebuilding BIN...
call build.bat
echo Done! Test with group %GROUP% ready.
```

Usage:
```bash
apply_trigger_test.bat 1   # Test groupe 1
```

---

## 📋 Checklist de Test

### Préparation
- [x] Triggers extraits (500)
- [x] 5 patches de groupe créés
- [ ] Script d'application créé
- [ ] Backup du BIN original

### Phase 1: Tests de Groupes
- [ ] Groupe 1 (Triggers 1-20) testé
- [ ] Groupe 2 (Triggers 21-40) testé
- [ ] Groupe 3 (Triggers 41-60) testé
- [ ] Groupe 4 (Triggers 61-80) testé
- [ ] Groupe 5 (Triggers 81-100) testé

### Phase 2: Tests Individuels
- [ ] Triggers identifiés comme portes
- [ ] Tests individuels effectués
- [ ] Database mise à jour avec résultats

### Phase 3: Documentation
- [ ] Liste des triggers de portes confirmée
- [ ] JSON des portes mis à jour
- [ ] Guide de modification créé

---

## 🎮 Zones à Tester en Priorité

**Zones faciles d'accès** (pour tests rapides):

1. **Cavern of Death - Floor 1**
   - Portes connues: Entrée, sortie, portes latérales
   - Facile à tester rapidement

2. **Forest of Despair**
   - Plusieurs portes visibles
   - Zone assez rapide

3. **Castle of Vamp**
   - Beaucoup de portes (château)
   - Portes verrouillées connues

**Stratégie**:
- Tester d'abord ces 3 zones pour chaque groupe
- Si des portes disparaissent, noter les IDs
- Approfondir ensuite si nécessaire

---

## 📊 Résultats Attendus

### Si un trigger est une porte:
- ✅ La porte **disparaît** visuellement
- ✅ La porte devient **intraversable**
- ✅ Le changement est **reproductible**

### Si un trigger n'est PAS une porte:
- ❌ Aucun changement visible de portes
- ⚠️ Peut affecter autre chose (spawn, collision, cutscene)

### Analyse:
- **Comparer les 5 groupes** entre eux
- **Identifier les patterns** (mêmes zones affectées?)
- **Croiser avec les données BLAZE.ALL** (types de portes)

---

## 🎯 Objectif Final

**Créer une table de correspondance**:
```json
{
  "door_triggers": [
    {
      "trigger_id": 42,
      "offset": "0x12345",
      "zone": "Cavern of Death",
      "area": "Floor 1",
      "door_type": "magic_locked",
      "position": {"x": 150, "y": 0, "z": 200},
      "notes": "Porte principale nord"
    }
  ]
}
```

**Puis**:
- Mettre à jour les JSON par area
- Créer un patcher de portes fonctionnel
- Documenter le système

---

## 💡 Conseils

1. **Tester méthodiquement**: Un groupe à la fois
2. **Prendre des screenshots**: Des portes affectées
3. **Noter précisément**: Zone, position approximative
4. **Comparer**: Vanilla vs Patché côte à côte si possible
5. **Être patient**: 500 triggers = beaucoup de tests potentiels

---

## 📞 Support

**Commandes utiles**:
```bash
# Voir tous les triggers
py -3 test_triggers_system.py info

# Créer tous les patches
for /L %i in (1,1,5) do py -3 test_triggers_system.py patch %i

# Désactiver un trigger spécifique
py -3 test_triggers_system.py disable 42
```

**Fichiers de référence**:
- `triggers_database.json`: Tous les triggers
- `test_groupN_notes.txt`: Détails de chaque groupe
- `EXPLORATION_GUIDE.md`: Guide général

---

**Bonne chance avec les tests !** 🚀
