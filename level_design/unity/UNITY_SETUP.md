# Unity Setup Guide - Blaze & Blade Level Visualization

## 📦 Installation Rapide

### Étape 1: Créer un Projet Unity

1. Ouvrir Unity Hub
2. Créer un nouveau projet 3D
3. Nom suggéré: "BlazeBladeViewer"

### Étape 2: Copier les Fichiers

1. **Copier les CSV dans Assets/**
   ```
   Assets/
   ├── coordinates_zone_1mb.csv
   ├── coordinates_zone_2mb.csv
   ├── coordinates_zone_3mb.csv
   ├── coordinates_zone_5mb.csv
   └── coordinates_zone_9mb.csv
   ```

2. **Copier les scripts C# dans Assets/Scripts/**
   ```
   Assets/Scripts/
   ├── CoordinateLoader.cs
   └── MultiZoneLoader.cs
   ```

### Étape 3: Configuration de la Scène

#### Option A: Une Seule Zone (Recommandé pour débuter)

1. Dans la Hierarchy, créer un GameObject vide (Clic droit → Create Empty)
2. Renommer en "LevelLoader"
3. Dans l'Inspector, cliquer "Add Component"
4. Sélectionner "CoordinateLoader"
5. Dans les paramètres:
   - **CSV File Name**: `coordinates_zone_5mb.csv` (zone la plus prometteuse)
   - **Sphere Scale**: 0.1
   - **Coordinate Scale**: 0.01
   - **Max Points To Load**: 500
   - **Use Single Mesh**: ✓ (coché pour performance)

#### Option B: Toutes les Zones (Vue d'ensemble)

1. Créer un GameObject vide nommé "MultiZoneLoader"
2. Add Component → "MultiZoneLoader"
3. Les 5 zones seront chargées automatiquement avec des couleurs différentes:
   - Zone 1MB: Rouge
   - Zone 2MB: Vert
   - Zone 3MB: Bleu
   - Zone 5MB: Jaune ⭐
   - Zone 9MB: Magenta

### Étape 4: Lancer la Visualisation

1. Appuyer sur Play ▶️
2. Les coordonnées 3D apparaîtront dans la scène
3. Utiliser la souris pour naviguer:
   - **Clic droit + déplacer**: Tourner la caméra
   - **Molette**: Zoom
   - **Clic milieu + déplacer**: Pan

---

## 🎨 Paramètres Avancés

### CoordinateLoader - Paramètres Détaillés

| Paramètre | Description | Valeur Recommandée |
|-----------|-------------|-------------------|
| **CSV File Name** | Nom du fichier CSV | `coordinates_zone_5mb.csv` |
| **Create Spheres** | Créer des sphères individuelles | ✓ (si < 200 points) |
| **Create Lines** | Connecter les points proches | Optionnel |
| **Sphere Scale** | Taille des sphères | 0.05 - 0.2 |
| **Coordinate Scale** | Échelle PSX → Unity | 0.01 (1 unité PSX = 0.01 Unity) |
| **Color By Height** | Gradient par hauteur | ✓ Recommandé |
| **Max Points To Load** | Limite de points | 500 (performance) |
| **Use Single Mesh** | Mesh unique (rapide) | ✓ Pour > 100 points |

### Ajuster l'Échelle

Si les coordonnées sont trop grandes/petites:

**Trop petit:**
```csharp
Coordinate Scale = 0.1 ou 1.0
```

**Trop grand:**
```csharp
Coordinate Scale = 0.001 ou 0.005
```

---

## 🔍 Analyse Visuelle

### Ce que Vous Devriez Voir

#### Zone 5MB (Floor/Ceiling Geometry)
- **Pattern attendu**: Grille régulière ou mesh structuré
- **Forme**: Rooms rectangulaires, corridors
- **Hauteur**: Variation Y représente étages/niveaux

#### Zone 9MB (Camera/Spawns)
- **Pattern attendu**: Points dispersés
- **Range**: Large (±8192)
- **Signification**: Positions de caméras fixes ou spawns

### Questions d'Analyse

Pendant la visualisation, demandez-vous:

1. **Y a-t-il des formes reconnaissables?**
   - Rectangles = Rooms
   - Lignes = Corridors
   - Grilles = Niveau structuré

2. **Y a-t-il des clusters de points?**
   - Groupes = Zones spécifiques
   - Isolés = Spawns ou triggers

3. **Y a-t-il de la symétrie?**
   - Symétrie = Architecture délibérée
   - Pattern répétitif = Tiles ou modules

---

## 🛠️ Fonctionnalités Avancées

### Filtrage Interactif

Modifier `CoordinateLoader.cs` pour ajouter des filtres:

```csharp
// Filtrer par hauteur
if (coord.y > minHeight && coord.y < maxHeight)
{
    // Afficher seulement ce niveau
}

// Filtrer par zone
if (coord.x > xMin && coord.x < xMax)
{
    // Afficher seulement cette zone
}
```

### Export Unity → OBJ

Pour sauvegarder le mesh visualisé:

1. Installer "ProBuilder" (Unity Package Manager)
2. Sélectionner le mesh généré
3. ProBuilder → Export → OBJ
4. Importer dans Blender/3ds Max

### Ajout de Labels

Pour afficher les offsets comme labels:

```csharp
// Dans CreateSpherePoints()
TextMesh label = sphere.AddComponent<TextMesh>();
label.text = $"0x{offset}";
label.characterSize = 0.1f;
label.anchor = TextAnchor.MiddleCenter;
```

---

## 📸 Screenshots Recommandés

Prenez des screenshots de:

1. **Vue d'ensemble** (toutes zones)
2. **Zone 5MB en détail** (floor/ceiling)
3. **Vue de dessus** (Top view)
4. **Vue de profil** (Side view)
5. **Clusters identifiés** (zoom sur patterns)

---

## 🐛 Troubleshooting

### Problème: Rien ne s'affiche

**Solution:**
1. Vérifier la console Unity pour erreurs
2. Confirmer que les CSV sont dans `Assets/`
3. Vérifier que `Coordinate Scale` n'est pas 0
4. Augmenter `Max Points To Load`

### Problème: Points trop petits

**Solution:**
```csharp
Sphere Scale = 0.5 ou plus
```

### Problème: Performance lente

**Solution:**
1. Activer `Use Single Mesh` = true
2. Réduire `Max Points To Load` à 200-300
3. Désactiver `Create Lines`

### Problème: CSV non trouvé

**Solution:**
```csharp
// Chemin complet dans l'Inspector:
Assets/coordinates_zone_5mb.csv

// Ou modifier le code:
string path = Application.dataPath + "/coordinates_zone_5mb.csv";
```

---

## 🎯 Workflow Recommandé

### Pour Identifier Floor/Ceiling

1. Charger `zone_5mb.csv` uniquement
2. Activer `Color By Height` = true
3. Observer le gradient de couleur:
   - Bleu = Sol (Y bas)
   - Rouge = Plafond (Y haut)
4. Prendre screenshots vue de dessus

### Pour Identifier Spawns

1. Charger `zone_9mb.csv`
2. Désactiver `Color By Height`
3. Appliquer couleur unique (ex: rouge)
4. Comparer avec les noms de niveaux connus

### Pour Vue d'Ensemble

1. Utiliser `MultiZoneLoader`
2. Activer les 5 zones
3. Comparer les overlaps
4. Identifier les zones partagées

---

## 📊 Analyse Comparative

### Comparaison avec Gameplay

Pour valider les coordonnées:

1. **Lancer le jeu** (émulateur PS1)
2. **Faire screenshots** des niveaux
3. **Comparer** avec les patterns Unity
4. **Mesurer distances** (ruler tool Unity)

### Export pour Analyse

```csharp
// Sauvegarder les bounds détectés
Debug.Log($"X: {minX} to {maxX}");
Debug.Log($"Y: {minY} to {maxY}");
Debug.Log($"Z: {minZ} to {maxZ}");
```

---

## 🔗 Ressources Supplémentaires

### Scripts Utilitaires

**CameraController.cs** (Navigation fluide):
```csharp
// Ajouter à Main Camera pour meilleure navigation
public class CameraController : MonoBehaviour
{
    public float moveSpeed = 10f;
    public float rotateSpeed = 100f;

    void Update()
    {
        // WASD movement
        float h = Input.GetAxis("Horizontal");
        float v = Input.GetAxis("Vertical");
        transform.Translate(Vector3.forward * v * moveSpeed * Time.deltaTime);
        transform.Translate(Vector3.right * h * moveSpeed * Time.deltaTime);

        // Q/E up/down
        if (Input.GetKey(KeyCode.Q))
            transform.Translate(Vector3.up * moveSpeed * Time.deltaTime);
        if (Input.GetKey(KeyCode.E))
            transform.Translate(Vector3.down * moveSpeed * Time.deltaTime);

        // Mouse rotation
        if (Input.GetMouseButton(1))
        {
            float rotX = Input.GetAxis("Mouse X") * rotateSpeed * Time.deltaTime;
            float rotY = Input.GetAxis("Mouse Y") * rotateSpeed * Time.deltaTime;
            transform.Rotate(Vector3.up, rotX, Space.World);
            transform.Rotate(Vector3.right, -rotY, Space.Self);
        }
    }
}
```

### Unity Packages Utiles

- **ProBuilder**: Modeling et export
- **ProGrids**: Snap to grid
- **Cinemachine**: Meilleures caméras

---

## ✅ Checklist de Validation

- [ ] Projet Unity créé
- [ ] 5 fichiers CSV copiés dans Assets/
- [ ] 2 scripts C# copiés dans Assets/Scripts/
- [ ] GameObject avec CoordinateLoader créé
- [ ] Play → Points visibles à l'écran
- [ ] Screenshots pris (vue ensemble + détails)
- [ ] Patterns identifiés et documentés
- [ ] Comparaison avec gameplay effectuée

---

**Prêt pour l'analyse!** 🚀

Une fois les coordonnées visualisées, passez aux étapes 2-4 (coffres, spawns, portes).
