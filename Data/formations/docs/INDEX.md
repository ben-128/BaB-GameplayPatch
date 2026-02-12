# Formation System - Documentation Index

## Guide principal
**→ Voir `../README.md` à la racine**

## Documentation technique

### CUSTOM_FORMATIONS_WORKING.md
**Guide complet des formations custom**
- Comment créer des formations custom
- Fonctionnement du synthetic path
- Vérification des bytes générés
- Exemples Cavern F1 A1

### FILLER_FIX.md
**Explication technique: fillers synthétiques**
- Pourquoi fillers synthétiques au lieu de vanilla round-robin
- Budget calculation et contraintes
- Duplicate offsets et offset table
- Fix du problème BLAZE.ALL size alignment

### ALL_ZONES_FIXED.md
**Corrections apportées aux 70 areas**
- Fix zero padding pour areas avec gaps (Hall of Demons, Tower)
- Fix exclusion fichiers _user_backup.json
- Résultats roundtrip test

### VANILLA_EXTRACTION_COMPLETE.md
**Process d'extraction des vanilla bytes**
- Scripts utilisés (extract_vanilla_bytes_v2.py)
- Structure des fichiers _vanilla.json
- Format des records (32 bytes hex strings)
- 41 areas extraites

### FORMATIONS_STRUCTURE_RESEARCH.md
**Historique: recherche bug Shaman FireBullet**
- Tests effectués (byte[8], byte[16:18])
- Découverte: formation records = descriptions complètes
- Root cause: patcher corrompait vanilla bytes
- Solution: extraction + utilisation vanilla bytes exacts

## Utilisation

Pour créer des formations custom:
1. Lire `../README.md` (guide complet)
2. Voir `CUSTOM_FORMATIONS_WORKING.md` pour exemples
3. Consulter `FILLER_FIX.md` si problèmes de budget

Pour comprendre le système:
1. Lire `FORMATIONS_STRUCTURE_RESEARCH.md` (historique)
2. Voir `VANILLA_EXTRACTION_COMPLETE.md` (vanilla bytes)
3. Consulter `ALL_ZONES_FIXED.md` (corrections)

## Notes

Tous ces documents sont à jour (2026-02-12) et reflètent l'état actuel du système après corrections.
