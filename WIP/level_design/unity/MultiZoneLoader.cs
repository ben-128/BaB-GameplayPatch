using UnityEngine;
using System.Collections.Generic;
using System.IO;

/// <summary>
/// Loads all zone coordinate files and displays them with different colors
/// </summary>
public class MultiZoneLoader : MonoBehaviour
{
    [System.Serializable]
    public class ZoneData
    {
        public string csvFileName;
        public Color color = Color.white;
        public bool enabled = true;
        [HideInInspector] public GameObject parentObject;
    }

    [Header("Zone Files")]
    public ZoneData[] zones = new ZoneData[]
    {
        new ZoneData { csvFileName = "coordinates_zone_1mb.csv", color = Color.red, enabled = true },
        new ZoneData { csvFileName = "coordinates_zone_2mb.csv", color = Color.green, enabled = true },
        new ZoneData { csvFileName = "coordinates_zone_3mb.csv", color = Color.blue, enabled = true },
        new ZoneData { csvFileName = "coordinates_zone_5mb.csv", color = Color.yellow, enabled = true },
        new ZoneData { csvFileName = "coordinates_zone_9mb.csv", color = Color.magenta, enabled = true }
    };

    [Header("Settings")]
    public float sphereScale = 0.1f;
    public float coordinateScale = 0.01f;
    public int maxPointsPerZone = 500;

    void Start()
    {
        LoadAllZones();
    }

    public void LoadAllZones()
    {
        foreach (ZoneData zone in zones)
        {
            if (zone.enabled)
            {
                LoadZone(zone);
            }
        }
    }

    void LoadZone(ZoneData zone)
    {
        string path = Path.Combine(Application.dataPath, zone.csvFileName);

        if (!File.Exists(path))
        {
            Debug.LogWarning($"Zone file not found: {path}");
            return;
        }

        // Create parent
        zone.parentObject = new GameObject($"Zone_{zone.csvFileName}");
        zone.parentObject.transform.SetParent(transform);

        // Load coordinates
        List<Vector3> coords = LoadCSV(path);

        Debug.Log($"Zone {zone.csvFileName}: Loaded {coords.Count} points");

        // Create visualization
        CreatePoints(zone, coords);
    }

    List<Vector3> LoadCSV(string path)
    {
        List<Vector3> coordinates = new List<Vector3>();
        string[] lines = File.ReadAllLines(path);

        for (int i = 1; i < lines.Length && i <= maxPointsPerZone; i++)
        {
            string[] values = lines[i].Split(',');

            if (values.Length >= 4)
            {
                try
                {
                    float x = float.Parse(values[1]) * coordinateScale;
                    float y = float.Parse(values[2]) * coordinateScale;
                    float z = float.Parse(values[3]) * coordinateScale;

                    coordinates.Add(new Vector3(x, y, z));
                }
                catch { }
            }
        }

        return coordinates;
    }

    void CreatePoints(ZoneData zone, List<Vector3> coordinates)
    {
        Mesh mesh = new Mesh();
        mesh.name = $"Zone_{zone.csvFileName}_Mesh";

        Vector3[] vertices = coordinates.ToArray();
        int[] indices = new int[vertices.Length];
        Color[] colors = new Color[vertices.Length];

        for (int i = 0; i < vertices.Length; i++)
        {
            indices[i] = i;
            colors[i] = zone.color;
        }

        mesh.vertices = vertices;
        mesh.colors = colors;
        mesh.SetIndices(indices, MeshTopology.Points, 0);

        GameObject meshObj = new GameObject("PointCloud");
        meshObj.transform.SetParent(zone.parentObject.transform);

        MeshFilter mf = meshObj.AddComponent<MeshFilter>();
        mf.mesh = mesh;

        MeshRenderer mr = meshObj.AddComponent<MeshRenderer>();
        Material mat = new Material(Shader.Find("Particles/Standard Unlit"));
        mat.SetColor("_Color", zone.color);
        mr.material = mat;
    }

    [ContextMenu("Clear All Zones")]
    public void ClearAllZones()
    {
        foreach (ZoneData zone in zones)
        {
            if (zone.parentObject != null)
            {
                DestroyImmediate(zone.parentObject);
                zone.parentObject = null;
            }
        }
    }

    [ContextMenu("Reload All Zones")]
    public void ReloadAllZones()
    {
        ClearAllZones();
        LoadAllZones();
    }
}
