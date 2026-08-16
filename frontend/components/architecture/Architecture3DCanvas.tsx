"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import {
  Database,
  UploadCloud,
  Binary,
  BarChart3,
  BrainCircuit,
  LayoutDashboard,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Zap,
  Activity,
  ShieldCheck,
  Maximize2,
  RotateCcw,
  Sliders
} from "lucide-react";

interface LayerDetail {
  id: number;
  name: string;
  subtitle: string;
  color: string;
  icon: any;
  components: string[];
  metrics: { label: string; value: string }[];
  description: string;
}

const LAYERS_DATA: LayerDetail[] = [
  {
    id: 1,
    name: "Data Sources Layer",
    subtitle: "Enterprise Ingestion Connectors",
    color: "#6366f1", // Indigo
    icon: Database,
    components: ["CSV File Streams", "Excel Spreadsheets", "Parquet Columnar Files", "PostgreSQL / Enterprise SQL"],
    metrics: [
      { label: "Supported Formats", value: "CSV, XLSX, Parquet, SQL" },
      { label: "Max File Size", value: "Multi-GB Streaming" },
      { label: "Ingestion SLA", value: "Sub-Second Handshake" }
    ],
    description: "Accepts raw enterprise datasets from multi-source connectors without requiring pre-formatting or manual schema preparation."
  },
  {
    id: 2,
    name: "Data Ingestion Layer",
    subtitle: "Streaming Parquet Conversion",
    color: "#0284c7", // Sky Blue
    icon: UploadCloud,
    components: ["Parquet Storage Manager", "DuckDB Chunked Streaming", "Schema Validator", "Raw Byte Storage"],
    metrics: [
      { label: "Engine", value: "DuckDB / PyArrow / Polars" },
      { label: "Memory Overhead", value: "<5% RAM Footprint" },
      { label: "Conversion Speed", value: "100K rows/sec" }
    ],
    description: "Streams incoming file bytes directly into compressed columnar Parquet files, eliminating OOM server crashes."
  },
  {
    id: 3,
    name: "Data Intelligence Layer",
    subtitle: "Semantic Schema Classifier",
    color: "#0d9488", // Teal
    icon: Binary,
    components: ["Semantic Data Profiler", "Measures & Dimensions Classifier", "Data Quality Health Scoring", "Dataset Domain Detector"],
    metrics: [
      { label: "Classification", value: "Domain Agnostic" },
      { label: "Health Score", value: "0 - 100 Scale" },
      { label: "Schema Confidence", value: "95%+ Accuracy" }
    ],
    description: "Automatically analyzes data types, distinct values, and column distributions to classify fields into Quantitative Measures, Dimensions, Temporal fields, and Identifiers."
  },
  {
    id: 4,
    name: "Analytics Engine Layer",
    subtitle: "In-Memory OLAP Aggregations",
    color: "#f59e0b", // Amber
    icon: BarChart3,
    components: ["Semantic Analytics Engine", "Dynamic KPI Engine", "Statistical Trend Aggregator", "Dimension Slicing Engine"],
    metrics: [
      { label: "Query Speed", value: "<15ms Execution" },
      { label: "Aggregation Types", value: "SUM, AVG, MIN, MAX, %" },
      { label: "OLAP Engine", value: "DuckDB In-Process SQL" }
    ],
    description: "Computes sub-millisecond aggregations and multi-dimensional group-bys directly over Parquet files in memory."
  },
  {
    id: 5,
    name: "AI Intelligence Layer",
    subtitle: "Statistical Anomalies & AI Narrative",
    color: "#8b5cf6", // Purple
    icon: BrainCircuit,
    components: ["Statistical Anomaly Engine (Z-Score)", "Variance Decomposition (Pareto 80/20)", "AutoInsights Narrative Generator", "Concentration Risk Detector"],
    metrics: [
      { label: "Anomaly Model", value: "Rolling Z-Score (2.0σ)" },
      { label: "Attribution Rule", value: "Pareto 80/20 Driver Analysis" },
      { label: "Narrative Output", value: "Executive Business Summary" }
    ],
    description: "Identifies statistical spikes/dips, primary growth drivers, and concentration risks to generate natural language executive business stories."
  },
  {
    id: 6,
    name: "Visualization Layer",
    subtitle: "Dynamic Dashboards & Recharts",
    color: "#10b981", // Emerald
    icon: LayoutDashboard,
    components: ["Dynamic Chart Spec Generator", "Recharts Interactive Area & Bar Visuals", "Health Score KPI Badges", "Decision Recommendations"],
    metrics: [
      { label: "Render Engine", value: "Next.js / Recharts" },
      { label: "UI Response", value: "60 FPS Interactive" },
      { label: "Chart Types", value: "Area, Bar, Pie, Metric Cards" }
    ],
    description: "Translates dynamic analytical specs into interactive enterprise dashboards with visual charts, health indicators, and recommendations."
  }
];

export default function Architecture3DCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);
  const [selectedLayer, setSelectedLayer] = useState<LayerDetail>(LAYERS_DATA[0]);
  const [activeLayerId, setActiveLayerId] = useState<number>(1);
  const [isRotating, setIsRotating] = useState<boolean>(true);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#090d16"); // Dark Slate Background
    scene.fog = new THREE.FogExp2("#090d16", 0.015);

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 18, 38);

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight("#ffffff", 0.8);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight("#6366f1", 1.8);
    dirLight1.position.set(20, 40, 20);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight("#10b981", 1.2);
    dirLight2.position.set(-20, -10, -20);
    scene.add(dirLight2);

    // 5. Grid Floor
    const gridHelper = new THREE.GridHelper(60, 60, "#1e293b", "#0f172a");
    gridHelper.position.y = -6;
    scene.add(gridHelper);

    // 6. Build 6 Architectural Layer Platforms
    const platforms: THREE.Group[] = [];
    const particlesGroup = new THREE.Group();
    scene.add(particlesGroup);

    const layerSpacing = 5.8;
    const startX = -((LAYERS_DATA.length - 1) * layerSpacing) / 2;

    LAYERS_DATA.forEach((layer, idx) => {
      const platformGroup = new THREE.Group();
      const posX = startX + idx * layerSpacing;
      const posY = Math.sin(idx * 0.5) * 0.8;
      const posZ = (idx % 2 === 0 ? -1.2 : 1.2);

      platformGroup.position.set(posX, posY, posZ);

      // Base Platform Mesh (Rounded Box / Cylinder)
      const geom = new THREE.CylinderGeometry(2.4, 2.6, 0.4, 32);
      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(layer.color),
        roughness: 0.2,
        metalness: 0.7,
        emissive: new THREE.Color(layer.color),
        emissiveIntensity: 0.25
      });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.receiveShadow = true;
      mesh.castShadow = true;
      mesh.userData = { layerId: layer.id };
      platformGroup.add(mesh);

      // Glowing Rim Ring
      const ringGeom = new THREE.TorusGeometry(2.65, 0.06, 16, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(layer.color),
        wireframe: false
      });
      const ringMesh = new THREE.Mesh(ringGeom, ringMat);
      ringMesh.rotation.x = Math.PI / 2;
      ringMesh.position.y = 0.22;
      platformGroup.add(ringMesh);

      // Inner Node Core
      const coreGeom = new THREE.OctahedronGeometry(0.7, 1);
      const coreMat = new THREE.MeshStandardMaterial({
        color: "#ffffff",
        emissive: new THREE.Color(layer.color),
        emissiveIntensity: 0.8,
        wireframe: true
      });
      const coreMesh = new THREE.Mesh(coreGeom, coreMat);
      coreMesh.position.y = 1.2;
      coreMesh.name = "nodeCore";
      platformGroup.add(coreMesh);

      scene.add(platformGroup);
      platforms.push(platformGroup);
    });

    // 7. Interconnecting Beams & Data Flow Particles
    const particlePoints: { mesh: THREE.Mesh; progress: number; speed: number; path: THREE.CatmullRomCurve3 }[] = [];

    for (let i = 0; i < platforms.length - 1; i++) {
      const p1 = platforms[i].position;
      const p2 = platforms[i + 1].position;

      const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      midPoint.y += 2.2;

      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(p1.x, p1.y + 0.3, p1.z),
        midPoint,
        new THREE.Vector3(p2.x, p2.y + 0.3, p2.z)
      ]);

      // Curve Tube Mesh
      const tubeGeom = new THREE.TubeGeometry(curve, 32, 0.04, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: "#38bdf8",
        transparent: true,
        opacity: 0.4
      });
      const tubeMesh = new THREE.Mesh(tubeGeom, tubeMat);
      scene.add(tubeMesh);

      // Add Data Flow Particles along Curve
      for (let k = 0; k < 3; k++) {
        const pGeom = new THREE.SphereGeometry(0.12, 12, 12);
        const pMat = new THREE.MeshBasicMaterial({ color: "#38bdf8" });
        const pMesh = new THREE.Mesh(pGeom, pMat);
        particlesGroup.add(pMesh);

        particlePoints.push({
          mesh: pMesh,
          progress: k * 0.33,
          speed: 0.008 + Math.random() * 0.004,
          path: curve
        });
      }
    }

    // 8. Mouse Interaction (Raycasting & Orbit Orbit Simulation)
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerDown = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(scene.children, true);

      for (const hit of intersects) {
        let parent = hit.object.parent;
        while (parent && !parent.userData.layerId) {
          parent = parent.parent;
        }
        if (parent && parent.userData.layerId) {
          const lId = parent.userData.layerId;
          const found = LAYERS_DATA.find((l) => l.id === lId);
          if (found) {
            setSelectedLayer(found);
            setActiveLayerId(found.id);
          }
          break;
        }
      }
    };

    renderer.domElement.addEventListener("pointerdown", onPointerDown);

    // 9. Animation Loop
    let reqId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      reqId = requestAnimationFrame(animate);
      const time = clock.getElapsedTime();

      // Slow Orbit Rotation
      if (isRotating) {
        camera.position.x = Math.sin(time * 0.15) * 38;
        camera.position.z = Math.cos(time * 0.15) * 38;
        camera.lookAt(0, 0, 0);
      }

      // Rotate Platform Cores
      platforms.forEach((p, idx) => {
        const core = p.getObjectByName("nodeCore");
        if (core) {
          core.rotation.y = time * 0.8 + idx;
          core.rotation.x = time * 0.4;
        }
      });

      // Animate Data Particles along Bezier Curves
      particlePoints.forEach((pt) => {
        pt.progress += pt.speed;
        if (pt.progress > 1) pt.progress = 0;
        const pos = pt.path.getPoint(pt.progress);
        pt.mesh.position.copy(pos);
      });

      renderer.render(scene, camera);
    };

    animate();

    // 10. Responsive Window Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener("resize", handleResize);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [isRotating]);

  return (
    <div className="relative w-full h-[780px] rounded-2xl overflow-hidden border border-border-color bg-background shadow-2xl">
      {/* 3D WebGL Canvas Viewport */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Header Overlay */}
      <div className="absolute top-6 left-6 right-6 flex flex-col md:flex-row md:items-center justify-between gap-4 pointer-events-none">
        <div className="bg-background/90 backdrop-blur-md px-5 py-3 rounded-xl border border-border-color pointer-events-auto flex items-center gap-3">
          <div className="p-2 bg-primary-500/20 text-primary-400 rounded-lg">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-text-primary tracking-wide">
              DecisionLens 3D Enterprise Architecture
            </h2>
            <p className="text-xs text-text-muted">
              Interactive 6-Layer End-to-End Decision Intelligence Stream
            </p>
          </div>
        </div>

        {/* Controls Toolbar */}
        <div className="flex items-center gap-2 bg-background/90 backdrop-blur-md p-2 rounded-xl border border-border-color pointer-events-auto">
          <button
            onClick={() => setIsRotating(!isRotating)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              isRotating ? "bg-primary-600 text-white" : "bg-surface-muted text-text-muted hover:text-text-primary"
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {isRotating ? "Orbit Rotating" : "Paused"}
          </button>
          <div className="h-4 w-px bg-surface-muted" />
          <span className="text-xs font-mono text-success-400 px-2 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 animate-pulse" /> 60 FPS | DuckDB Vector Active
          </span>
        </div>
      </div>

      {/* Layer Navigation Tabs */}
      <div className="absolute bottom-6 left-6 right-6 md:right-auto bg-background/90 backdrop-blur-md p-2 rounded-xl border border-border-color flex flex-wrap gap-1.5 z-10">
        {LAYERS_DATA.map((layer) => {
          const Icon = layer.icon;
          const isActive = layer.id === activeLayerId;
          return (
            <button
              key={layer.id}
              onClick={() => {
                setSelectedLayer(layer);
                setActiveLayerId(layer.id);
              }}
              className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                isActive
                  ? "bg-primary-600 text-white shadow-lg shadow-primary-600/30 scale-105"
                  : "bg-surface-muted/80 text-text-muted hover:bg-surface-muted hover:text-text-primary"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>Layer {layer.id}</span>
            </button>
          );
        })}
      </div>

      {/* Selected Layer Info Modal / Drawer */}
      <div className="absolute top-24 right-6 w-96 max-h-[620px] bg-background/95 backdrop-blur-md border border-border-color rounded-2xl p-6 shadow-2xl text-text-primary overflow-y-auto space-y-5 z-20">
        <div className="flex items-center justify-between border-b border-border-color pb-4">
          <div className="flex items-center gap-3">
            <div
              className="p-2.5 rounded-xl text-white"
              style={{ backgroundColor: selectedLayer.color }}
            >
              {React.createElement(selectedLayer.icon, { className: "w-5 h-5" })}
            </div>
            <div>
              <span className="text-xs font-mono text-text-muted uppercase tracking-wider">
                Layer {selectedLayer.id} of 6
              </span>
              <h3 className="text-base font-bold text-text-primary">{selectedLayer.name}</h3>
            </div>
          </div>
        </div>

        <p className="text-xs text-text-muted leading-relaxed">{selectedLayer.description}</p>

        {/* Sub-Components List */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2.5 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-primary-400" />
            Core Architectural Modules
          </h4>
          <div className="space-y-1.5">
            {selectedLayer.components.map((comp, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-xs text-text-secondary bg-surface-muted/60 px-3 py-2 rounded-lg border border-border-color/50"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-success-400 flex-shrink-0" />
                <span>{comp}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Technical Performance Specs */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2.5 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-success-400" />
            Performance & SLA Metrics
          </h4>
          <div className="grid grid-cols-1 gap-2">
            {selectedLayer.metrics.map((m, i) => (
              <div key={i} className="flex justify-between items-center bg-surface-muted/40 px-3 py-2 rounded-lg border border-border-color text-xs">
                <span className="text-text-muted">{m.label}:</span>
                <span className="font-semibold text-success-400 font-mono">{m.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-2 border-t border-border-color flex justify-between items-center text-xs text-text-muted">
          <span>Click any 3D node to inspect</span>
          <span className="text-primary-400 flex items-center gap-1 font-semibold">
            DuckDB Pipeline <ArrowRight className="w-3 h-3" />
          </span>
        </div>
      </div>
    </div>
  );
}
