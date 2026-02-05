# Guide Complet - Visualisation Unity

## 🎯 Vue d'Ensemble

Ce guide vous permet de visualiser **TOUT** dans Unity:
- ✅ Géométrie des niveaux (floor/ceiling)
- ✅ Coffres avec leur contenu
- ✅ Spawns de monstres par zone
- ✅ Portes avec leurs clés et destinations

---

## 🚀 Installation Rapide

### 1. Créer Projet Unity

1. Ouvrir Unity Hub
2. Nouveau projet → **3D** (Core)
3. Nom: "BlazeBladeComplete"

### 2. Copier les Fichiers

**Dans `Assets/`:**
```
Assets/
├── coordinates_zone_5mb.csv    # Géométrie (100 points)
├── chest_positions.csv          # Coffres (données récentes)
├── spawn_positions.csv          # Spawns (150 points)
├── door_positions.csv           # Portes (50 points)
└── spawns_by_level.json         # Organisation par niveau
```

**Dans `Assets/Scripts/`:**
```
Assets/Scripts/
├── CompleteVisualization.cs     # Script principal
├── CoordinateLoader.cs          # Loader simple (optionnel)
└── MultiZoneLoader.cs           # Multi-zones (optionnel)
```

### 3. Setup Scene

1. Hierarchy → Clic droit → Create Empty
2. Renommer en **"LevelVisualization"**
3. Inspector → Add Component → **Complete Visualization**
4. Configurer les paramètres (voir ci-dessous)

### 4. Configuration Recommandée

Dans l'Inspector de `CompleteVisualization`:

```
Data Files:
  Geometry File: coordinates_zone_5mb.csv
  Chests File: chest_positions.csv
  Spawns File: spawn_positions.csv
  Doors File: door_positions.csv

Visual Settings:
  Coordinate Scale: 0.01
  Show Geometry: ✓
  Show Chests: ✓
  Show Spawns: ✓
  Show Doors: ✓

Colors:
  Geometry Color: Gris (0.5, 0.5, 0.5, 0.3)
  Chest Color: Jaune
  Spawn Color: Rouge
  Door Color: Bleu
  Portal Color: Cyan

Sizes:
  Geometry Size: 0.05
  Chest Size: 0.3
  Spawn Size: 0.2
  Door Size: 0.25

Labels:
  Show Chest Labels: ✓
  Show Spawn Labels: ✓
  Show Door Labels: ✓
  Label Size: 0.1
```

### 5. Lancer

**Play ▶️**

Vous verrez:
- Points gris = Géométrie du niveau
- Cubes jaunes = Coffres (avec nom item + quantité)
- Sphères rouges = Spawns ennemis (avec nom + % spawn)
- Cylindres bleus = Portes (avec type + key + destination)

---

## 🎮 Contrôles Navigation

### Caméra Standard Unity

- **Clic droit + Déplacer**: Tourner
- **Molette**: Zoom
- **Clic milieu + Déplacer**: Pan
- **WASD**: Déplacement (si FPS controller)

### Améliorer la Navigation

Créer **CameraController.cs** dans `Assets/Scripts/`:

```csharp
using UnityEngine;

public class CameraController : MonoBehaviour
{
    public float moveSpeed = 10f;
    public float rotateSpeed = 100f;
    public float zoomSpeed = 20f;

    void Update()
    {
        // WASD movement
        float h = Input.GetAxis("Horizontal");
        float v = Input.GetAxis("Vertical");
        transform.Translate(Vector3.right * h * moveSpeed * Time.deltaTime, Space.World);
        transform.Translate(Vector3.forward * v * moveSpeed * Time.deltaTime, Space.World);

        // Q/E up/down
        if (Input.GetKey(KeyCode.Q))
            transform.Translate(Vector3.up * moveSpeed * Time.deltaTime, Space.World);
        if (Input.GetKey(KeyCode.E))
            transform.Translate(Vector3.down * moveSpeed * Time.deltaTime, Space.World);

        // Mouse rotation (Right-click)
        if (Input.GetMouseButton(1))
        {
            float rotX = Input.GetAxis("Mouse X") * rotateSpeed * Time.deltaTime;
            float rotY = Input.GetAxis("Mouse Y") * rotateSpeed * Time.deltaTime;
            transform.Rotate(Vector3.up, rotX, Space.World);
            transform.Rotate(Vector3.right, -rotY, Space.Self);
        }

        // Scroll zoom
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        transform.Translate(Vector3.forward * scroll * zoomSpeed, Space.Self);

        // Shift = faster
        if (Input.GetKey(KeyCode.LeftShift))
            moveSpeed = 20f;
        else
            moveSpeed = 10f;
    }
}
```

Ajouter à la **Main Camera** → Add Component → Camera Controller

---

## 📊 Interprétation des Données

### Coffres (Cubes Jaunes)

**Label montre:**
```
[Item Name]
Qty: [Quantity]
```

**Exemple:**
```
Magic Sword
Qty: 1
```

**Positions:**
- Si coffre à (0, 0, 0) → Padding/non-utilisé
- Positions valides → Dans les niveaux

**Quantité:**
- 1 = Item unique
- 19, 46 = Valeurs suspectes (possiblement padding)
- 99 = Stack complet

### Spawns (Sphères Rouges/Magenta)

**Couleurs:**
- **Rouge**: Monster normal
- **Magenta**: Boss

**Label montre:**
```
[Monster Name]
[Spawn %]% ([Count])
```

**Exemple:**
```
Skeleton
80% (3)
```

**Interprétation:**
- **80%**: 80% de chance d'apparaître
- **(3)**: 3 monstres spawneront
- **0%**: Spawn désactivé ou conditionnel
- **100%**: Boss (always spawn)

**Positions (0,0,0):**
- Beaucoup de spawns à (0,0,0) = Padding ou structure invalide
- Ignorer visuellement

### Portes (Cylindres Bleus/Cyan)

**Couleurs:**
- **Bleu**: Porte normale/locked
- **Cyan**: Portal

**Label montre:**
```
[Type]
Key:[Key ID] -> [Dest ID]
```

**Exemple:**
```
Key Locked
Key:12 -> 5
```

**Types de portes:**
- **Unlocked (0)**: Ouverte (beaucoup de padding)
- **Key Locked (1)**: Nécessite clé
- **Magic Locked (2)**: Sort magique
- **Demon Engraved (3)**: Item démon
- **Ghost Engraved (4)**: Item fantôme
- **Event Locked (5)**: Boss battu, etc.

**Key ID:**
- ID de la clé requise
- 0 = Pas de clé

**Dest ID:**
- ID du niveau de destination
- 0 = Même niveau

---

## 🔍 Analyse dans Unity

### Toggle des Layers

Dans l'Inspector de `CompleteVisualization`, utilisez:

**Show Geometry:** Activer/désactiver le mesh de géométrie
**Show Chests:** Activer/désactiver les coffres
**Show Spawns:** Activer/désactiver les spawns
**Show Doors:** Activer/désactiver les portes

**Ou via Context Menu:**
- Clic droit sur script → **Toggle Chests**
- Clic droit sur script → **Toggle Spawns**
- Clic droit sur script → **Toggle Doors**

### Filtrer les Objets

Dans la Hierarchy:
```
LevelVisualization/
├── Geometry/
│   └── PointCloud
├── Chests/
│   ├── Chest_1
│   ├── Chest_2
│   └── ...
├── Spawns/
│   ├── Spawn_Skeleton
│   ├── Spawn_Zombie
│   └── ...
└── Doors/
    ├── Door_KeyLocked
    ├── Door_MagicLocked
    └── ...
```

**Sélectionner un parent** pour highlight tous ses enfants.

### Mesurer Distances

1. Sélectionner 2 objets (Shift + Clic)
2. Dans Scene view, voir la distance
3. Ou utiliser script de mesure:

```csharp
Vector3.Distance(object1.position, object2.position)
```

### Identifier Rooms

**Méthode visuelle:**
1. Activer uniquement **Geometry**
2. Chercher des clusters de points
3. Chaque cluster = Room probable

**Analyser densité:**
- Beaucoup de points = Zone dense (room/corridor)
- Points dispersés = Open area

---

## 📋 Spawns Par Niveau

### Fichier: spawns_by_level.json

**Structure:**
```json
{
  "zone_name": "Level Data 1-3MB",
  "total_spawns": 50,
  "monsters": [
    {
      "name": "Skeleton",
      "type": "Normal",
      "spawn_points": [
        {
          "position": {"x": 512, "y": 256, "z": 1024},
          "chance": 80,
          "count": 3,
          "offset": "0x100000"
        }
      ]
    }
  ]
}
```

### Rapport: SPAWNS_BY_LEVEL.md

Consulter ce fichier pour voir:
- Spawns groupés par zone
- Statistiques par monstre
- Positions détaillées

**Exemple de contenu:**
```
## Level Data 1-3MB
Total spawns: 50

### Skeleton (Normal)
  Spawn points: 10
  Avg spawn chance: 75.0%
  Avg spawn count: 2.5
  Positions:
    1. (512, 256, 1024) - 80% chance, count 3
    2. (768, 384, 1536) - 70% chance, count 2
```

---

## 🎨 Customization

### Changer les Couleurs

Dans l'Inspector:
```
Chest Color: RGB (255, 255, 0) = Jaune
Spawn Color: RGB (255, 0, 0) = Rouge
Door Color: RGB (0, 0, 255) = Bleu
Portal Color: RGB (0, 255, 255) = Cyan
```

**Rendre semi-transparent:**
- Geometry Color: Alpha = 0.3 (30%)
- Autre objets: Alpha = 1.0 (opaque)

### Changer les Tailles

```
Geometry Size: 0.05 (très petit, nuage de points)
Chest Size: 0.3 (moyen, visible)
Spawn Size: 0.2 (petit)
Door Size: 0.25 (moyen)
```

**Si objets trop petits:**
- Multiplier par 2-5
- Ex: Chest Size = 0.6 ou 1.0

### Changer les Labels

```
Label Size: 0.1 (taille des caractères)
Show Chest Labels: false (masquer)
Show Spawn Labels: true (afficher)
Show Door Labels: true (afficher)
```

**Position des labels:**
Modifier dans `CompleteVisualization.cs`:
```csharp
labelObj.transform.localPosition = Vector3.up * 0.6f; // Au-dessus
// ou
labelObj.transform.localPosition = Vector3.down * 0.3f; // En-dessous
```

---

## 🛠️ Debugging

### Problème: Rien ne s'affiche

**Solutions:**
1. Vérifier console Unity (Ctrl+Shift+C)
2. Confirmer CSV dans `Assets/`
3. Vérifier paths dans l'Inspector
4. Click droit → **Reload** sur le script

### Problème: Objets trop petits

**Solutions:**
```
Coordinate Scale = 0.1 (au lieu de 0.01)
// ou
Chest Size = 1.0 (au lieu de 0.3)
```

### Problème: Objets trop grands

**Solutions:**
```
Coordinate Scale = 0.001 (au lieu de 0.01)
// ou
Door Size = 0.1 (au lieu de 0.25)
```

### Problème: Beaucoup d'objets à (0,0,0)

**Normal:** Ce sont des structures padding/invalides

**Solution:**
Modifier script pour ignorer (0,0,0):
```csharp
// Déjà implémenté:
if (x == 0 && y == 0 && z == 0) continue;
```

### Problème: Labels illisibles

**Solutions:**
1. Augmenter `Label Size` à 0.2
2. Augmenter `fontSize` dans le code
3. Changer couleur des labels (plus contrasté)

---

## 📊 Statistiques Actuelles

### Données Chargées

| Type | Quantité | Fichier |
|------|----------|---------|
| Géométrie | 500 points | coordinates_zone_5mb.csv |
| Coffres | ~100 | chest_positions.csv |
| Spawns | 150 | spawn_positions.csv |
| Portes | 50 | door_positions.csv |

**Note:** Beaucoup d'entrées à (0,0,0) = Padding, pas affichées

### Zones Identifiées

- **Level Data 1-3MB**: 50 spawns
- **Level Data 5-7MB**: 50 spawns
- **Level Data 9-10MB**: 50 spawns

### Monstres Trouvés

- 5 types de monstres uniques
- Mix de Normal et Boss
- Spawns avec probabilités variées (0-100%)

---

## 🎯 Workflow Complet

### 1. Vue d'Ensemble

**Objectif:** Voir tout le niveau en une fois

**Étapes:**
1. Activer tous les layers (Geometry, Chests, Spawns, Doors)
2. Zoom out pour voir l'ensemble
3. Identifier les zones denses (rooms)

### 2. Analyse Coffres

**Objectif:** Localiser tous les coffres

**Étapes:**
1. Désactiver Geometry et Spawns
2. Activer uniquement Chests
3. Lire les labels pour voir contenu
4. Noter positions importantes

### 3. Analyse Spawns

**Objectif:** Comprendre distribution des ennemis

**Étapes:**
1. Activer uniquement Spawns
2. Filtrer par couleur (rouge=normal, magenta=boss)
3. Vérifier % de spawn et count
4. Consulter `SPAWNS_BY_LEVEL.md` pour détails

### 4. Analyse Portes

**Objectif:** Mapper les connexions entre niveaux

**Étapes:**
1. Activer uniquement Doors
2. Identifier types (bleu=locked, cyan=portal)
3. Noter Key IDs et Destinations
4. Créer map mentale du flow

### 5. Validation Gameplay

**Objectif:** Comparer avec le jeu réel

**Étapes:**
1. Lancer émulateur PS1
2. Aller dans un niveau connu
3. Compter coffres/spawns visibles
4. Comparer avec Unity

---

## 💡 Tips & Tricks

### Labels Plus Lisibles

```csharp
label.fontSize = 20; // Plus gros
label.color = Color.black; // Couleur contrastée
label.fontStyle = FontStyle.Bold; // Gras
```

### Grouper Par Type

Dans Hierarchy, renommer:
```
Chests/
├── Weapons/
│   ├── Chest_MagicSword
│   └── Chest_LegendarySword
└── Consumables/
    ├── Chest_Potion
    └── Chest_Elixir
```

### Export Screenshot

1. Scene view → Game view
2. Ajuster angle parfait
3. Screenshot (Unity Recorder ou Print Screen)
4. Documenter avec annotations

### Créer Minimap

1. Caméra Orthographic au-dessus
2. Render texture
3. Afficher dans UI Panel
4. Minimap temps réel!

---

## ✅ Checklist

### Installation
- [ ] Projet Unity créé
- [ ] 4 CSV copiés dans Assets/
- [ ] CompleteVisualization.cs copié
- [ ] GameObject créé avec script

### Configuration
- [ ] Paths configurés dans l'Inspector
- [ ] Coordinate Scale = 0.01
- [ ] Labels activés
- [ ] Couleurs ajustées

### Visualisation
- [ ] Play pressed
- [ ] Géométrie visible
- [ ] Coffres visible avec labels
- [ ] Spawns visibles avec labels
- [ ] Portes visibles avec labels

### Analyse
- [ ] Screenshots pris
- [ ] Spawns groupés par zone identifiés
- [ ] Coffres répertoriés
- [ ] Portes/connections mappées
- [ ] Comparaison gameplay effectuée

---

**Tout est prêt! Lancez Unity et explorez les niveaux en 3D! 🎮**
