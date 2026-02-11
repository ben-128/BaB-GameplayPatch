# R Field Investigation Scripts (2026-02-11)

Scripts d'analyse utilisés pour l'investigation complète du R field dans les assignment entries.

## Résultats de l'investigation

**Découverte principale** : Vanilla n'a PAS d'assignment entries (flag 0x40).
Les valeurs R dans vanilla sont des bytes aléatoires aux offsets (overlay code, strings, zone data).

**Documentation complète** :
- `Data/formations/R_FIELD_INVESTIGATION.md`
- `Data/formations/SPELL_LIST_HYPOTHESIS.md`

## Scripts inclus

### Extraction & Comparaison
- **`extract_vanilla_blaze.py`** : Extrait vanilla BLAZE.ALL du BIN source (LBA 163167)
- **`compare_vanilla_patched.py`** : Compare vanilla vs patched byte-à-byte

### Analyse Vanilla
- **`check_vanilla_R_values.py`** : Analyse R dans 4 zones échantillon
- **`analyze_all_vanilla_R.py`** : Analyse complète (109 monstres, 47 valeurs R uniques)
- **`check_monster_R_variations.py`** : Variations R pour même monstre (30/32 varient par zone)

### Tests d'hypothèses
- **`check_R_vs_casters.py`** : Corrélation R/spell casters (72% casters ont R≠0)
- **`test_R_as_spell_list_index.py`** : Test hypothèse R=spell_list_index (faible corrélation)

### Utilitaires
- **`restore_vanilla_R_values.py`** : Restaure tous les R aux bytes vanilla (98 changements)

## Usage

```bash
# Extraire vanilla BLAZE.ALL (46MB, non commité)
py -3 WIP/R_field_research/extract_vanilla_blaze.py

# Analyser toutes les valeurs R
py -3 WIP/R_field_research/analyze_all_vanilla_R.py

# Restaurer R aux valeurs vanilla
py -3 WIP/R_field_research/restore_vanilla_R_values.py
```

## Conclusions

1. **R est zone-spécifique**, pas monster-spécifique
2. **Distribution quasi-uniforme 0-7** dans patched JSONs (les 8 listes de sorts)
3. **Hypothèse R=spell_list_index** : corrélation faible (9.5%) mais distribution intéressante
4. **Action prise** : Tous les R restaurés aux bytes vanilla pour tests in-game

## Fichiers temporaires

- `vanilla_BLAZE.ALL` (46MB) : Non commité, regénérable avec extract_vanilla_blaze.py
