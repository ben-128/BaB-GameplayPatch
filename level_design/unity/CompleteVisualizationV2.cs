using UnityEngine;
using System.Collections.Generic;
using System.IO;
using System.Linq;

/// <summary>
/// Complete Level Visualization - Chests, Spawns, Doors
/// Shows all level elements with labels and colors
/// </summary>
public class CompleteVisualization : MonoBehaviour
{
    [Header("Data Files")]
    public string geometryFile = "coordinates_zone_5mb.csv";
    public string chestsFile = "chest_positions.csv";
    public string spawnsFile = "spawn_positions.csv";
    public string doorsFile = "door_positions.csv";

    [Header("Visual Settings")]
    public float coordinateScale = 0.01f;
    public bool showGeometry = true;
    public bool showChests = true;
    public bool showSpawns = true;
    public bool showDoors = true;

    [Header("Colors")]
    public Color geometryColor = new Color(0.5f, 0.5f, 0.5f, 0.3f);
    public Color chestColor = Color.yellow;
    public Color spawnColor = Color.red;
    public Color doorColor = Color.blue;
    public Color portalColor = Color.cyan;

    [Header("Sizes")]
    public float geometrySize = 0.05f;
    public float chestSize = 0.3f;
    public float spawnSize = 0.2f;
    public float doorSize = 0.25f;

    [Header("Labels")]
    public bool showChestLabels = true;
    public bool showSpawnLabels = true;
    public bool showDoorLabels = true;
    public float labelSize = 0.1f;

    private GameObject geometryParent;
    private GameObject chestsParent;
    private GameObject spawnsParent;
    private GameObject doorsParent;

    void Start()
    {
        LoadAndVisualize();
    }

    public void LoadAndVisualize()
    {
        // Create parent objects
        geometryParent = new GameObject("Geometry");
        geometryParent.transform.SetParent(transform);

        chestsParent = new GameObject("Chests");
        chestsParent.transform.SetParent(transform);

        spawnsParent = new GameObject("Spawns");
        spawnsParent.transform.SetParent(transform);

        doorsParent = new GameObject("Doors");
        doorsParent.transform.SetParent(transform);

        // Load each layer
        if (showGeometry) LoadGeometry();
        if (showChests) LoadChests();
        if (showSpawns) LoadSpawns();
        if (showDoors) LoadDoors();

        Debug.Log("Complete visualization loaded!");
    }

    void LoadGeometry()
    {
        string path = Path.Combine(Application.dataPath, geometryFile);
        if (!File.Exists(path))
        {
            Debug.LogWarning($"Geometry file not found: {path}");
            return;
        }

        string[] lines = File.ReadAllLines(path);
        List<Vector3> coords = new List<Vector3>();

        for (int i = 1; i < lines.Length; i++)
        {
            string[] values = lines[i].Split(',');
            if (values.Length >= 4)
            {
                try
                {
                    float x = float.Parse(values[1]) * coordinateScale;
                    float y = float.Parse(values[2]) * coordinateScale;
                    float z = float.Parse(values[3]) * coordinateScale;
                    coords.Add(new Vector3(x, y, z));
                }
                catch { }
            }
        }

        // Create point cloud
        Mesh mesh = new Mesh();
        mesh.vertices = coords.ToArray();
        mesh.colors = Enumerable.Repeat(geometryColor, coords.Count).ToArray();
        int[] indices = Enumerable.Range(0, coords.Count).ToArray();
        mesh.SetIndices(indices, MeshTopology.Points, 0);

        GameObject meshObj = new GameObject("PointCloud");
        meshObj.transform.SetParent(geometryParent.transform);
        meshObj.AddComponent<MeshFilter>().mesh = mesh;

        Material mat = new Material(Shader.Find("Particles/Standard Unlit"));
        mat.SetColor("_Color", geometryColor);
        meshObj.AddComponent<MeshRenderer>().material = mat;

        Debug.Log($"Loaded {coords.Count} geometry points");
    }

    void LoadChests()
    {
        string path = Path.Combine(Application.dataPath, chestsFile);
        if (!File.Exists(path))
        {
            Debug.LogWarning($"Chests file not found: {path}");
            return;
        }

        string[] lines = File.ReadAllLines(path);
        int chestCount = 0;

        for (int i = 1; i < lines.Length; i++)
        {
            string[] values = lines[i].Split(',');
            if (values.Length >= 8)
            {
                try
                {
                    float x = float.Parse(values[1]) * coordinateScale;
                    float y = float.Parse(values[2]) * coordinateScale;
                    float z = float.Parse(values[3]) * coordinateScale;

                    // Skip invalid positions
                    if (x == 0 && y == 0 && z == 0) continue;

                    string itemId = values[4];
                    string itemName = values[5];
                    string quantity = values[6];

                    // Create chest visual
                    GameObject chest = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    chest.name = $"Chest_{i}";
                    chest.transform.position = new Vector3(x, y, z);
                    chest.transform.localScale = Vector3.one * chestSize;
                    chest.transform.SetParent(chestsParent.transform);

                    // Set color
                    Renderer renderer = chest.GetComponent<Renderer>();
                    Material mat = new Material(Shader.Find("Standard"));
                    mat.color = chestColor;
                    renderer.material = mat;

                    // Add label
                    if (showChestLabels)
                    {
                        GameObject labelObj = new GameObject("Label");
                        labelObj.transform.SetParent(chest.transform);
                        labelObj.transform.localPosition = Vector3.up * 0.6f;

                        TextMesh label = labelObj.AddComponent<TextMesh>();
                        label.text = $"{itemName}\nQty: {quantity}";
                        label.characterSize = labelSize;
                        label.anchor = TextAnchor.MiddleCenter;
                        label.alignment = TextAlignment.Center;
                        label.color = Color.yellow;
                        label.fontSize = 14;
                    }

                    chestCount++;
                }
                catch (System.Exception e)
                {
                    Debug.LogWarning($"Failed to parse chest line {i}: {e.Message}");
                }
            }
        }

        Debug.Log($"Loaded {chestCount} chests");
    }

    void LoadSpawns()
    {
        string path = Path.Combine(Application.dataPath, spawnsFile);
        if (!File.Exists(path))
        {
            Debug.LogWarning($"Spawns file not found: {path}");
            return;
        }

        string[] lines = File.ReadAllLines(path);
        int spawnCount = 0;

        for (int i = 1; i < lines.Length; i++)
        {
            string[] values = lines[i].Split(',');
            if (values.Length >= 10)
            {
                try
                {
                    float x = float.Parse(values[2]) * coordinateScale;
                    float y = float.Parse(values[3]) * coordinateScale;
                    float z = float.Parse(values[4]) * coordinateScale;

                    // Skip invalid positions
                    if (x == 0 && y == 0 && z == 0) continue;

                    string monsterName = values[6];
                    string monsterType = values[7];
                    string spawnChance = values[8];
                    string spawnCountVal = values[9];

                    // Create spawn visual
                    GameObject spawn = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    spawn.name = $"Spawn_{monsterName}";
                    spawn.transform.position = new Vector3(x, y, z);
                    spawn.transform.localScale = Vector3.one * spawnSize;
                    spawn.transform.SetParent(spawnsParent.transform);

                    // Set color based on type
                    Renderer renderer = spawn.GetComponent<Renderer>();
                    Material mat = new Material(Shader.Find("Standard"));
                    mat.color = monsterType == "Boss" ? Color.magenta : spawnColor;
                    renderer.material = mat;

                    // Add label
                    if (showSpawnLabels)
                    {
                        GameObject labelObj = new GameObject("Label");
                        labelObj.transform.SetParent(spawn.transform);
                        labelObj.transform.localPosition = Vector3.up * 0.5f;

                        TextMesh label = labelObj.AddComponent<TextMesh>();
                        label.text = $"{monsterName}\n{spawnChance}% ({spawnCountVal})";
                        label.characterSize = labelSize;
                        label.anchor = TextAnchor.MiddleCenter;
                        label.alignment = TextAlignment.Center;
                        label.color = Color.red;
                        label.fontSize = 12;
                    }

                    spawnCount++;
                }
                catch (System.Exception e)
                {
                    Debug.LogWarning($"Failed to parse spawn line {i}: {e.Message}");
                }
            }
        }

        Debug.Log($"Loaded {spawnCount} spawns");
    }

    void LoadDoors()
    {
        string path = Path.Combine(Application.dataPath, doorsFile);
        if (!File.Exists(path))
        {
            Debug.LogWarning($"Doors file not found: {path}");
            return;
        }

        string[] lines = File.ReadAllLines(path);
        int doorCount = 0;

        for (int i = 1; i < lines.Length; i++)
        {
            string[] values = lines[i].Split(',');
            if (values.Length >= 9)
            {
                try
                {
                    float x = float.Parse(values[1]) * coordinateScale;
                    float y = float.Parse(values[2]) * coordinateScale;
                    float z = float.Parse(values[3]) * coordinateScale;

                    // Skip invalid positions
                    if (x == 0 && y == 0 && z == 0) continue;

                    string doorType = values[4];
                    string typeDesc = values[5];
                    string keyId = values[6];
                    string destId = values[7];

                    // Create door visual
                    GameObject door = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                    door.name = $"Door_{typeDesc}";
                    door.transform.position = new Vector3(x, y, z);
                    door.transform.localScale = new Vector3(doorSize, doorSize * 2, doorSize);
                    door.transform.SetParent(doorsParent.transform);

                    // Set color based on type
                    Renderer renderer = door.GetComponent<Renderer>();
                    Material mat = new Material(Shader.Find("Standard"));
                    mat.color = typeDesc.Contains("Locked") ? doorColor : portalColor;
                    renderer.material = mat;

                    // Add label
                    if (showDoorLabels)
                    {
                        GameObject labelObj = new GameObject("Label");
                        labelObj.transform.SetParent(door.transform);
                        labelObj.transform.localPosition = Vector3.up * 0.6f;

                        TextMesh label = labelObj.AddComponent<TextMesh>();
                        label.text = $"{typeDesc}\nKey:{keyId} -> {destId}";
                        label.characterSize = labelSize;
                        label.anchor = TextAnchor.MiddleCenter;
                        label.alignment = TextAlignment.Center;
                        label.color = Color.cyan;
                        label.fontSize = 10;
                    }

                    doorCount++;
                }
                catch (System.Exception e)
                {
                    Debug.LogWarning($"Failed to parse door line {i}: {e.Message}");
                }
            }
        }

        Debug.Log($"Loaded {doorCount} doors");
    }

    [ContextMenu("Clear All")]
    public void ClearAll()
    {
        if (geometryParent != null) DestroyImmediate(geometryParent);
        if (chestsParent != null) DestroyImmediate(chestsParent);
        if (spawnsParent != null) DestroyImmediate(spawnsParent);
        if (doorsParent != null) DestroyImmediate(doorsParent);
    }

    [ContextMenu("Reload")]
    public void Reload()
    {
        ClearAll();
        LoadAndVisualize();
    }

    [ContextMenu("Toggle Chests")]
    public void ToggleChests()
    {
        if (chestsParent != null)
            chestsParent.SetActive(!chestsParent.activeSelf);
    }

    [ContextMenu("Toggle Spawns")]
    public void ToggleSpawns()
    {
        if (spawnsParent != null)
            spawnsParent.SetActive(!spawnsParent.activeSelf);
    }

    [ContextMenu("Toggle Doors")]
    public void ToggleDoors()
    {
        if (doorsParent != null)
            doorsParent.SetActive(!doorsParent.activeSelf);
    }
}
