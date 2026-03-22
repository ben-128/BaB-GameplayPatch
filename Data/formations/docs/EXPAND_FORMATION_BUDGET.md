# Expansion du budget formations — TOUTES APPROCHES ECHOUEES

**Statut : ABANDONNE — aucune methode viable trouvee (2026-03-22)**

Le budget formations ne peut PAS etre etendu. Toutes les approches testees
ont echoue. Ce document explique pourquoi.

## Contexte

Chaque area a un budget fixe `formation_area_bytes` (ex: 896 bytes pour
Cavern F1 A1 = max 27 slots). L'objectif etait d'augmenter ce budget pour
permettre plus de monstres par encounter.

## Approche 1 : Shift gap+ZS dans espace "libre" — ECHOUE

### Principe
Deplacer le gap + zone spawns vers la droite dans l'espace libre ZS pour
agrandir la zone formations.

### Cause d'echec : L'ESPACE LIBRE N'EXISTE PAS
L'extracteur de zone spawns ne capture que ~21% des vrais ZS records.
Les ~20,000 bytes "libres" apres `zs_used_end` contiennent des donnees
de spawn vivantes (87% non-zero).

Le shift ecrasait ces donnees → crash immediat.

| Area | JSON zs_bytes | Donnees reelles | Donnees cachees |
|------|--------------|-----------------|-----------------|
| Cavern F1 A1 | 5,416 B | 25,414 B | 79% invisible |
| Cavern F1 A2 | 3,016 B | 23,016 B | 87% invisible |
| Forest F1 A1 | 5,488 B | 25,488 B | 78% invisible |

### Tests effectues (tous crash)
- 90 offsets (structurels) → CRASH
- 112 offsets (+ gap sub-tables) → CRASH
- 114 offsets (+ bytecode confirmes) → CRASH
- 116 offsets (+ post-980) → CRASH
- 118 offsets (brute-force complet) → CRASH

Aucune combinaison d'offsets ne corrige le crash car le probleme
est la destruction des donnees ZS cachees, pas les offsets.

## Approche 2 : Scatter-write dans espace ZS — ECHOUE

### Principe
Ecrire les formations supplementaires dans l'espace ZS sans rien deplacer,
et modifier les pointeurs de la offset table.

### Cause d'echec : LE MOTEUR SCANNE SEQUENTIELLEMENT
- Les offsets individuels des 8 formations NE SONT PAS stockes dans
  le binaire (aucun uint32 correspondant trouve)
- Seul `fm_start` (offset 1376) existe a script+292
- Le moteur trouve les formations par scan sequentiel des marqueurs
  FFFFFFFF dans la zone FM contigue
- Les formations DOIVENT etre dans la zone FM, pas ailleurs

### Decouverte supplementaire
Les entrees Root[4]-Root[11] de la root table sont des pointeurs vers
des sous-tables du systeme d'encounters, PAS des offsets de formations.
`skip_offset_table_update: true` existait pour empecher leur corruption.

## Approche 3 : Recuperer le gap FM→ZS (420 bytes) — ECHOUE

### Principe
Le gap entre formations et zone spawns (420 bytes) pourrait etre
recupere pour agrandir la zone formations.

### Tests effectues
- Gap entier zero (420B) → CRASH au loading de la zone
- Moitie du gap zero (228B, +192 a +420) → loading tres long puis CRASH

Le gap contient des donnees structurees utilisees par le moteur :
- +0 a +192 : config/offset pairs (critique pour le loading)
- +192 a +420 : records spawn supplementaires (bytes 0x02/0xFF markers)

## Conclusion

Le budget `formation_area_bytes` est une **limite dure du moteur**.
Aucun espace contigu n'est recuperable dans la structure de l'area.

Pour depasser cette limite, il faudrait reverse-engineer le code
overlay MIPS pour modifier l'allocation memoire du moteur lui-meme.

## Script expand_formation_budget.py

Le script reste dans le repo a titre de reference mais est **desactive** :
- `AREA_EXPANSIONS = {}` (aucune area configuree)
- `DEFAULT_EXPANSION = 0` (skip toutes les areas)
- Le Step 6a du build pipeline ne fait rien
