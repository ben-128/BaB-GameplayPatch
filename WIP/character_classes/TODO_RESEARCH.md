# Recherches à Effectuer - Données de Classes

## CONCLUSION IMPORTANTE

**Les stats de base et growth NE SONT PAS dans BLAZE.ALL.**
Elles sont probablement dans l'exécutable SLES_008.45.

Voir `FINDINGS_SUMMARY.md` pour le détail des recherches effectuées.

---

## Prochaines Étapes Prioritaires

### 1. Analyser l'Exécutable SLES_008.45
- [ ] Utiliser Ghidra ou IDA pour désassembler
- [ ] Chercher les routines de création de personnage
- [ ] Identifier les tables de stats hardcodées
- [ ] Chercher des références aux noms de classes

### 2. Analyse des Sauvegardes
- [ ] Créer 1 personnage par classe au niveau 1
- [ ] Extraire les données de sauvegarde
- [ ] Comparer les sauvegardes pour trouver les offsets de stats
- [ ] Chercher les valeurs correspondantes dans SLES_008.45

### 3. Tests In-Game
- [ ] Documenter les stats de départ de chaque classe
- [ ] Tester la montée de niveau et noter les gains de stats
- [ ] Vérifier les sorts disponibles par classe

### 4. Mapping Classe ↔ Sorts
**7 listes trouvées à 0x002CA424** dans BLAZE.ALL
- [ ] Créer un personnage de chaque classe
- [ ] Noter les sorts disponibles au niveau 1
- [ ] Mapper les listes aux classes

---

## Ce qui a été Analysé dans BLAZE.ALL

| Zone | Contenu | Résultat |
|------|---------|----------|
| 0x0090B6E8 - 0x0090B7C8 | Noms de classes | Labels UI uniquement |
| 0x0090E0D0 - 0x0090E240 | Tooltips stats | STR/INT/WIL/AGL/CON/POW/LCK descriptions |
| 0x00203000 - 0x00205000 | Tables numériques | Pas de stats de classe identifiées |
| 0x002CA424 - 0x002CA8E4 | Listes de sorts | 7 listes progressives |

---

## Fichiers de Référence

- `FINDINGS_SUMMARY.md` - Résumé complet des recherches
- `CLASS_DATA_LOCATIONS.md` - Emplacements connus
- `EQUIPMENT_BY_CLASS.md` - Équipements par classe
- `CLASS_STATS_ANALYSIS.txt` - Dumps d'analyse automatique
- `../spells/CLASS_DATA_ANALYSIS.md` - Analyse des listes de sorts
