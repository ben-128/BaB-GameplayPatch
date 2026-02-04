using UnityEngine;
using System.Collections.Generic;
using System.IO;

/// <summary>
/// Blaze & Blade Level Design Coordinate Loader for Unity
/// Loads CSV coordinate data and creates visual representations
/// </summary>
public class CoordinateLoader : MonoBehaviour
{
    [Header("Data Files")]
    [Tooltip("Path to CSV file relative to Assets folder")]
    public string csvFileName = "coordinates_zone_5mb.csv";

    [Header("Visualization Settings")]
    public bool createSpheres = true;
    public bool createLines = false;
    public float sphereScale = 0.1f;
    public float coordinateScale = 0.01f; // PSX units to Unity units

    [Header("Color Coding")]
    public bool colorByHeight = true;
    public Gradient heightGradient;

    [Header("Performance")]
    public int maxPointsToLoad = 500;
    public bool useSingleMesh = true; // Better performance for many points

    private List<Vector3> coordinates = new List<Vector3>();
    private GameObject parentObject;

    void Start()
    {
        // Initialize gradient if not set
        if (heightGradient == null || heightGradient.colorKeys.Length == 0)
        {
            InitializeDefaultGradient();
        }

        LoadAndVisualize();
    }

    void InitializeDefaultGradient()
    {
        heightGradient = new Gradient();

        GradientColorKey[] colorKeys = new GradientColorKey[3];
        colorKeys[0] = new GradientColorKey(Color.blue, 0f);
        colorKeys[1] = new GradientColorKey(Color.green, 0.5f);
        colorKeys[2] = new GradientColorKey(Color.red, 1f);

        GradientAlphaKey[] alphaKeys = new GradientAlphaKey[2];
        alphaKeys[0] = new GradientAlphaKey(1f, 0f);
        alphaKeys[1] = new GradientAlphaKey(1f, 1f);

        heightGradient.SetKeys(colorKeys, alphaKeys);
    }

    public void LoadAndVisualize()
    {
        // Create parent object
        parentObject = new GameObject("Level_Coordinates");
        parentObject.transform.SetParent(transform);

        // Load CSV
        string path = Path.Combine(Application.dataPath, csvFileName);
        if (!File.Exists(path))
        {
            Debug.LogError($"CSV file not found: {path}");
            return;
        }

        LoadCSV(path);

        if (coordinates.Count == 0)
        {
            Debug.LogWarning("No coordinates loaded!");
            return;
        }

        Debug.Log($"Loaded {coordinates.Count} coordinates");

        // Visualize
        if (useSingleMesh)
        {
            CreateSingleMesh();
        }
        else if (createSpheres)
        {
            CreateSpherePoints();
        }

        if (createLines)
        {
            CreateLineConnections();
        }
    }

    void LoadCSV(string path)
    {
        coordinates.Clear();

        string[] lines = File.ReadAllLines(path);

        // Skip header
        for (int i = 1; i < lines.Length && i <= maxPointsToLoad; i++)
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
                catch (System.Exception e)
                {
                    Debug.LogWarning($"Failed to parse line {i}: {e.Message}");
                }
            }
        }
    }

    void CreateSpherePoints()
    {
        float minY = float.MaxValue;
        float maxY = float.MinValue;

        // Find Y bounds for color coding
        if (colorByHeight)
        {
            foreach (Vector3 coord in coordinates)
            {
                if (coord.y < minY) minY = coord.y;
                if (coord.y > maxY) maxY = coord.y;
            }
        }

        // Create sphere at each coordinate
        for (int i = 0; i < coordinates.Count; i++)
        {
            Vector3 pos = coordinates[i];

            GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.transform.position = pos;
            sphere.transform.localScale = Vector3.one * sphereScale;
            sphere.transform.SetParent(parentObject.transform);
            sphere.name = $"Point_{i}";

            // Color by height
            if (colorByHeight)
            {
                float t = (pos.y - minY) / (maxY - minY);
                Color color = heightGradient.Evaluate(t);

                Renderer renderer = sphere.GetComponent<Renderer>();
                renderer.material = new Material(Shader.Find("Standard"));
                renderer.material.color = color;
            }
        }

        Debug.Log($"Created {coordinates.Count} sphere points");
    }

    void CreateSingleMesh()
    {
        // More efficient for large point clouds
        Mesh mesh = new Mesh();
        mesh.name = "CoordinateCloud";

        Vector3[] vertices = coordinates.ToArray();
        int[] indices = new int[vertices.Length];
        for (int i = 0; i < indices.Length; i++)
        {
            indices[i] = i;
        }

        Color[] colors = new Color[vertices.Length];

        if (colorByHeight)
        {
            float minY = float.MaxValue;
            float maxY = float.MinValue;
            foreach (Vector3 v in vertices)
            {
                if (v.y < minY) minY = v.y;
                if (v.y > maxY) maxY = v.y;
            }

            for (int i = 0; i < vertices.Length; i++)
            {
                float t = (vertices[i].y - minY) / (maxY - minY);
                colors[i] = heightGradient.Evaluate(t);
            }
        }
        else
        {
            for (int i = 0; i < colors.Length; i++)
            {
                colors[i] = Color.white;
            }
        }

        mesh.vertices = vertices;
        mesh.colors = colors;
        mesh.SetIndices(indices, MeshTopology.Points, 0);

        GameObject meshObj = new GameObject("PointCloud_Mesh");
        meshObj.transform.SetParent(parentObject.transform);

        MeshFilter mf = meshObj.AddComponent<MeshFilter>();
        mf.mesh = mesh;

        MeshRenderer mr = meshObj.AddComponent<MeshRenderer>();
        mr.material = new Material(Shader.Find("Particles/Standard Unlit"));

        Debug.Log($"Created single mesh with {vertices.Length} vertices");
    }

    void CreateLineConnections()
    {
        // Connect nearby points with lines
        GameObject lineParent = new GameObject("LineConnections");
        lineParent.transform.SetParent(parentObject.transform);

        float connectionDistance = 5f * coordinateScale;

        for (int i = 0; i < coordinates.Count - 1; i++)
        {
            Vector3 p1 = coordinates[i];
            Vector3 p2 = coordinates[i + 1];

            if (Vector3.Distance(p1, p2) < connectionDistance)
            {
                GameObject lineObj = new GameObject($"Line_{i}");
                lineObj.transform.SetParent(lineParent.transform);

                LineRenderer line = lineObj.AddComponent<LineRenderer>();
                line.startWidth = 0.01f;
                line.endWidth = 0.01f;
                line.material = new Material(Shader.Find("Sprites/Default"));
                line.startColor = Color.cyan;
                line.endColor = Color.cyan;

                line.SetPosition(0, p1);
                line.SetPosition(1, p2);
            }
        }
    }

    // Editor helper
    [ContextMenu("Reload and Visualize")]
    public void ReloadData()
    {
        if (parentObject != null)
        {
            DestroyImmediate(parentObject);
        }
        LoadAndVisualize();
    }
}
