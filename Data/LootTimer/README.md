# Loot Timer - Guide d'utilisation

## Description

Modifie la durée avant disparition des coffres lâchés par les monstres.

- **Défaut original** : 20 secondes
- **Patch actuel** : Coffres permanents (timer gelé)

## Configuration

Éditer `loot_timer.json` :

```json
{
    "chest_despawn_seconds": 0
}
```

- `0` = Timer gelé, coffres permanents ✓ (solution actuelle)
- `>0` = Timer configuré (ex: 60s) - **PAS ENCORE IMPLÉMENTÉ**

## Activation/Désactivation

**Le patch est ACTIVÉ par défaut** depuis la découverte v5 (2026-02-09).

Pour désactiver temporairement, éditer `build_gameplay_patch.bat` ligne 8 :
```batch
set PATCH_LOOT_TIMER=0   REM 0=désactivé, 1=activé
```

## Comment ça marche

Le jeu utilise un compteur (`entity+0x14`) qui décrémente de 1 par frame :
- Original : 1000 frames / 50fps PAL = 20 secondes
- Patch v5 : NOP tous les décrements → timer gelé → coffres permanents

v5 détecte et patche **68 patterns de décrémentation** dans le code overlay,
incluant toutes les variantes de registres (`$v0`, `$v1`, `$a2`, `$a3`, `$s0`, etc.)

v4 et versions précédentes ne trouvaient que 35 patterns, donc les coffres
continuaient de disparaître.

## Développement futur

Pour implémenter un timer configurable (ex: 60s au lieu de 20s), il faudra :
1. Trouver où `entity+0x14` est **initialisé** lors du spawn du coffre
2. Modifier la valeur initiale au lieu de NOP le décrement
3. Mettre à jour `patch_loot_timer_v5.py` pour gérer `chest_despawn_seconds > 0`

Voir `RESEARCH.md` pour les détails techniques.
