# Guide pas-a-pas : Projet Unity pour Blaze & Blade

## Etat des lieux

### Ce qui existe deja

- 3 scripts C# Unity prets (`CompleteVisualizationV2.cs`, `CoordinateLoader.cs`, `MultiZoneLoader.cs`)
- 5 fichiers CSV de coordonnees (geometrie 3D des niveaux)
- `chest_positions.csv` (100 chests)
- `door_positions.csv` (50 doors)
- Documentation complete

### Ce qui manque

- `spawn_positions.csv` n'existe PAS - les spawns sont en JSON par niveau, et **sans coordonnees x,y,z** (seulement des offsets + noms de monstres)
- Le fichier `CompleteVisualizationV2.cs` attend un `spawn_positions.csv` qui n'a jamais ete genere

---

## Etape 1 : Installer Unity

1. Telecharger **Unity Hub** depuis unity.com si pas deja fait
2. Dans Unity Hub, installer une version **Unity 2022 LTS** ou plus recente (la 3D standard suffit)
3. Cliquer **New Project** > template **3D (Core)** > Nom : `BlazeBladeViewer`
4. Choisir un emplacement (ex: `C:\Perso\BabLangue\BlazeBladeViewer`)
5. Cliquer **Create project**

---

## Etape 2 : Preparer la structure des dossiers

Dans l'explorateur Windows, aller dans le dossier `Assets/` du projet Unity et creer :

```
BlazeBladeViewer/
  Assets/
    Data/           <-- fichiers CSV
    Scripts/        <-- scripts C#
```

---

## Etape 3 : Copier les fichiers de donnees dans Assets/Data/

Copier ces fichiers depuis le projet GameplayPatch :

| Source (depuis GameplayPatch/) | Destination (dans Assets/) |
|-------------------------------|---------------------------|
| `WIP/level_design/coordinates/data/coordinates_zone_1mb.csv` | `Data/coordinates_zone_1mb.csv` |
| `WIP/level_design/coordinates/data/coordinates_zone_2mb.csv` | `Data/coordinates_zone_2mb.csv` |
| `WIP/level_design/coordinates/data/coordinates_zone_3mb.csv` | `Data/coordinates_zone_3mb.csv` |
| `WIP/level_design/coordinates/data/coordinates_zone_5mb.csv` | `Data/coordinates_zone_5mb.csv` |
| `WIP/level_design/coordinates/data/coordinates_zone_9mb.csv` | `Data/coordinates_zone_9mb.csv` |
| `WIP/level_design/chests/data/chest_positions.csv` | `Data/chest_positions.csv` |
| `WIP/level_design/doors/data/door_positions.csv` | `Data/door_positions.csv` |

---

## Etape 4 : Copier les scripts C# dans Assets/Scripts/

| Source (depuis GameplayPatch/) | Destination (dans Assets/) |
|-------------------------------|---------------------------|
| `WIP/level_design/unity/CompleteVisualizationV2.cs` | `Scripts/CompleteVisualization.cs` |
| `WIP/level_design/unity/CoordinateLoader.cs` | `Scripts/CoordinateLoader.cs` |
| `WIP/level_design/unity/MultiZoneLoader.cs` | `Scripts/MultiZoneLoader.cs` |

**Important** : renommer `CompleteVisualizationV2.cs` en `CompleteVisualization.cs` (le nom du fichier doit correspondre au nom de la classe).

---

## Etape 5 : Corriger les chemins dans les scripts

Les scripts cherchent les fichiers directement dans `Assets/` mais ils sont dans `Assets/Data/`.

### Option A : Modifier les chemins par defaut dans les scripts

Dans `CompleteVisualization.cs`, modifier les lignes au debut de la classe :

```csharp
public string geometryFile = "Data/coordinates_zone_5mb.csv";
public string chestsFile = "Data/chest_positions.csv";
public string spawnsFile = "Data/spawn_positions.csv";
public string doorsFile = "Data/door_positions.csv";
```

Dans `CoordinateLoader.cs` :

```csharp
public string csvFileName = "Data/coordinates_zone_5mb.csv";
```

Dans `MultiZoneLoader.cs`, modifier le tableau zones :

```csharp
new ZoneData { csvFileName = "Data/coordinates_zone_1mb.csv", color = Color.red, enabled = true },
new ZoneData { csvFileName = "Data/coordinates_zone_2mb.csv", color = Color.green, enabled = true },
new ZoneData { csvFileName = "Data/coordinates_zone_3mb.csv", color = Color.blue, enabled = true },
new ZoneData { csvFileName = "Data/coordinates_zone_5mb.csv", color = Color.yellow, enabled = true },
new ZoneData { csvFileName = "Data/coordinates_zone_9mb.csv", color = Color.magenta, enabled = true }
```

### Option B : Mettre les CSV directement dans Assets/ (plus simple)

Copier tous les CSV directement dans `Assets/` sans sous-dossier `Data/`. Aucune modification de script necessaire.

---

## Etape 6 : Configurer la scene Unity

1. Dans Unity, dans la **Hierarchy** (panneau gauche), clic droit > **Create Empty**
2. Renommer en `LevelVisualization`
3. Avec `LevelVisualization` selectionne, dans l'**Inspector** (panneau droit), cliquer **Add Component**
4. Taper `CompleteVisualization` et le selectionner
5. Configurer dans l'Inspector :

```
Data Files:
  Geometry File: Data/coordinates_zone_5mb.csv
  Chests File:   Data/chest_positions.csv
  Spawns File:   (laisser vide ou ignorer)
  Doors File:    Data/door_positions.csv

Visual Settings:
  Coordinate Scale: 0.01
  Show Geometry: cocher
  Show Chests:   cocher
  Show Spawns:   DECOCHER (pas de donnees CSV spawns)
  Show Doors:    cocher

Colors:
  Geometry Color: Gris (0.5, 0.5, 0.5, 0.3)
  Chest Color:    Jaune
  Door Color:     Bleu
  Portal Color:   Cyan

Sizes:
  Geometry Size: 0.05
  Chest Size:    0.3
  Door Size:     0.25

Labels:
  Show Chest Labels: cocher
  Show Door Labels:  cocher
  Label Size: 0.1
```

---

## Etape 7 : Ajouter un Camera Controller

Pour naviguer librement dans la scene 3D :

1. Dans `Assets/Scripts/`, creer un nouveau fichier `CameraController.cs`
2. Y mettre le code suivant :

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

        // Mouse rotation (Right-click held)
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

3. Dans Unity, selectionner **Main Camera** dans la Hierarchy
4. **Add Component** > taper `CameraController` > selectionner

---

## Etape 8 : Play!

1. Appuyer sur **Play** (triangle en haut au centre)
2. Ce qui devrait apparaitre :
   - **Points gris** = geometrie du niveau (nuage de points)
   - **Cubes jaunes** = coffres avec labels (nom item + quantite)
   - **Cylindres bleus** = portes avec labels (type + cle requise)
3. Navigation :
   - **Clic droit + souris** : tourner la camera
   - **Molette** : zoom avant/arriere
   - **WASD** : se deplacer
   - **Q/E** : monter/descendre
   - **Shift** : mode rapide

---

## Etape 9 : Essayer le MultiZoneLoader (optionnel)

Pour voir les 5 zones de coordonnees ensemble :

1. Dans la Hierarchy, clic droit > **Create Empty** > renommer en `MultiZoneLoader`
2. **Add Component** > `MultiZoneLoader`
3. Les 5 zones s'affichent avec des couleurs differentes :
   - Zone 1MB : Rouge
   - Zone 2MB : Vert
   - Zone 3MB : Bleu
   - Zone 5MB : Jaune (la plus interessante)
   - Zone 9MB : Magenta

**Note** : desactiver le `LevelVisualization` (decocher dans l'Inspector) pour eviter les doublons de geometrie.

---

## A propos des spawns (donnees manquantes)

Les spawns n'ont **pas de coordonnees 3D** dans les donnees actuelles. Les JSON de spawn (`castle_of_vamp.json`, `forest.json`, etc.) contiennent seulement :

- Un offset dans BLAZE.ALL (ex: `0x23FF1B4`)
- Les noms des monstres (ex: `Zombie`, `Harpy`, `Wolf`)
- Le nom de la zone/floor (ex: `Floor 1 - Area 1`)

Pour avoir les spawns affiches en 3D, il faudrait :

1. **Extraire les positions x,y,z** depuis le binaire BLAZE.ALL aux offsets indiques
2. **Generer un `spawn_positions.csv`** au format attendu par le script :

```csv
offset,zone,x,y,z,monster_id,monster_name,monster_type,spawn_chance,spawn_count
0x23FF1B4,castle_of_vamp,1024,256,512,12,Zombie,Normal,80,3
```

3. **Recocher Show Spawns** dans l'Inspector une fois le CSV genere

---

## Troubleshooting

### Rien ne s'affiche

1. Verifier la console Unity (Window > Console ou Ctrl+Shift+C)
2. Confirmer que les CSV sont au bon endroit
3. Verifier que `Coordinate Scale` n'est pas a 0
4. Verifier les messages de log : "Loaded X geometry points", "Loaded X chests", etc.

### Points trop petits / invisibles

```
Augmenter Coordinate Scale : 0.01 -> 0.1
Augmenter Geometry Size : 0.05 -> 0.5
Augmenter Chest Size : 0.3 -> 1.0
```

### Points trop grands / trop espaces

```
Diminuer Coordinate Scale : 0.01 -> 0.001
```

### Performance lente

- Activer `Use Single Mesh` dans CoordinateLoader
- Reduire `Max Points To Load` a 200-300
- Desactiver les labels si trop nombreux

### Beaucoup d'objets a (0,0,0)

Normal : ce sont des structures padding/invalides. Le script les ignore deja (`if (x == 0 && y == 0 && z == 0) continue;`).

### CSV non trouve (erreur dans la console)

Verifier le chemin dans l'Inspector. Si les CSV sont dans `Assets/Data/`, les chemins doivent etre `Data/chest_positions.csv` et non `chest_positions.csv`.

---

## Checklist

### Installation
- [ ] Unity Hub installe
- [ ] Unity 2022 LTS (ou +) installe
- [ ] Projet `BlazeBladeViewer` cree (template 3D)

### Fichiers
- [ ] 5 CSV coordonnees copies dans Assets/Data/
- [ ] chest_positions.csv copie dans Assets/Data/
- [ ] door_positions.csv copie dans Assets/Data/
- [ ] CompleteVisualization.cs copie dans Assets/Scripts/ (renomme)
- [ ] CoordinateLoader.cs copie dans Assets/Scripts/
- [ ] MultiZoneLoader.cs copie dans Assets/Scripts/
- [ ] CameraController.cs cree dans Assets/Scripts/
- [ ] Chemins corriges dans les scripts (si sous-dossier Data/)

### Scene
- [ ] GameObject `LevelVisualization` cree
- [ ] CompleteVisualization ajoute comme component
- [ ] Chemins configures dans l'Inspector
- [ ] Show Spawns decoche
- [ ] CameraController ajoute sur Main Camera

### Validation
- [ ] Play : geometrie visible (points gris)
- [ ] Play : coffres visibles (cubes jaunes avec labels)
- [ ] Play : portes visibles (cylindres bleus avec labels)
- [ ] Navigation camera fonctionnelle (WASD + souris)
