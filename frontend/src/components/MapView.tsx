"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Sample } from "@/types";

interface MapViewProps {
  samples: Sample[];
  selectedIds: string[];
  onSelect: (id: string, multi?: boolean) => void;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

function createIcon(color: string, selected: boolean) {
  const size = selected ? 18 : 11;
  const border = selected ? 3 : 2;
  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;
      background:${color};
      border:${border}px solid ${selected ? "#1c1c1e" : "rgba(255,255,255,0.9)"};
      border-radius:50%;
      box-shadow:0 2px 8px rgba(0,0,0,0.25);
      transition:all .2s ease;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createClusterIcon(count: number) {
  let size = 28;
  let fontSize = 12;
  if (count >= 100) { size = 40; fontSize = 14; }
  else if (count >= 10) { size = 34; fontSize = 13; }

  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;
      background:rgba(0,122,255,0.85);
      color:#fff;
      border-radius:50%;
      display:flex;
      align-items:center;
      justify-content:center;
      font-weight:600;
      font-size:${fontSize}px;
      font-family:Inter,-apple-system,sans-serif;
      box-shadow:0 2px 8px rgba(0,122,255,0.35);
      border:2px solid rgba(255,255,255,0.9);
    ">${count}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function MapView({ samples, selectedIds, onSelect }: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const clusterLayersRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;
    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: true,
    }).setView([35, 108], 5);

    L.tileLayer(process.env.NEXT_PUBLIC_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: process.env.NEXT_PUBLIC_TILE_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    const clusterLayers = L.layerGroup().addTo(map);
    clusterLayersRef.current = clusterLayers;
    mapInstance.current = map;

    return () => {
      map.remove();
      mapInstance.current = null;
      clusterLayersRef.current = null;
    };
  }, []);

  // Build/rebuild markers when samples change
  useEffect(() => {
    const map = mapInstance.current;
    const clusterLayers = clusterLayersRef.current;
    if (!map || !clusterLayers) return;

    // Clear existing
    markersRef.current.forEach((m) => clusterLayers.removeLayer(m));
    markersRef.current.clear();
    clusterLayers.clearLayers();

    const zoom = map.getZoom();
    const shouldCluster = zoom <= 7;

    if (shouldCluster) {
      // Simple distance-based clustering
      const clusters: Array<{ lat: number; lng: number; ids: string[]; samples: Sample[] }> = [];
      const CLUSTER_DISTANCE_DEG = 1.5; // approximate degrees at low zoom

      for (const s of samples) {
        let added = false;
        for (const c of clusters) {
          const d = Math.sqrt((s.lat - c.lat) ** 2 + (s.lng - c.lng) ** 2);
          if (d < CLUSTER_DISTANCE_DEG) {
            c.ids.push(s.id);
            c.samples.push(s);
            c.lat = c.samples.reduce((sum, x) => sum + x.lat, 0) / c.samples.length;
            c.lng = c.samples.reduce((sum, x) => sum + x.lng, 0) / c.samples.length;
            added = true;
            break;
          }
        }
        if (!added) {
          clusters.push({ lat: s.lat, lng: s.lng, ids: [s.id], samples: [s] });
        }
      }

      for (const c of clusters) {
        if (c.ids.length === 1) {
          const s = c.samples[0];
          const color = regionColors[s.region] || "#666";
          const selected = selectedIds.includes(s.id);
          const marker = L.marker([s.lat, s.lng], {
            icon: createIcon(color, selected),
            zIndexOffset: selected ? 1000 : 0,
          });
          setupPopup(marker, s);
          setupClick(marker, s.id, onSelect);
          markersRef.current.set(s.id, marker);
          clusterLayers.addLayer(marker);
        } else {
          const selected = c.ids.some((id) => selectedIds.includes(id));
          const marker = L.marker([c.lat, c.lng], {
            icon: createClusterIcon(c.ids.length),
            zIndexOffset: selected ? 1000 : 0,
          });
          const html = `
            <div style="min-width:180px">
              <div style="font-weight:600;font-size:14px;margin-bottom:4px">${c.ids.length} samples</div>
              <div style="color:#8e8e93;font-size:12px">${c.samples.map((s) => s.sampleId).join(", ")}</div>
            </div>
          `;
          marker.bindPopup(html, { closeButton: false, offset: [0, -6] });
          marker.on("click", () => {
            map.flyTo([c.lat, c.lng], 9, { duration: 0.6 });
          });
          clusterLayers.addLayer(marker);
        }
      }
    } else {
      for (const s of samples) {
        const color = regionColors[s.region] || "#666";
        const selected = selectedIds.includes(s.id);
        const marker = L.marker([s.lat, s.lng], {
          icon: createIcon(color, selected),
          zIndexOffset: selected ? 1000 : 0,
        });
        setupPopup(marker, s);
        setupClick(marker, s.id, onSelect);
        markersRef.current.set(s.id, marker);
        clusterLayers.addLayer(marker);
      }
    }
  }, [samples, onSelect]);

  // Update selected state without rebuilding markers
  useEffect(() => {
    const clusterLayers = clusterLayersRef.current;
    if (!clusterLayers) return;

    markersRef.current.forEach((marker, id) => {
      const sample = samples.find((s) => s.id === id);
      if (!sample) return;
      const color = regionColors[sample.region] || "#666";
      const selected = selectedIds.includes(id);
      marker.setIcon(createIcon(color, selected));
      marker.setZIndexOffset(selected ? 1000 : 0);
    });
  }, [selectedIds, samples]);

  // Fly to last selected sample
  useEffect(() => {
    const map = mapInstance.current;
    if (!map || selectedIds.length === 0) return;
    const lastId = selectedIds[selectedIds.length - 1];
    const marker = markersRef.current.get(lastId);
    if (marker) {
      map.flyTo(marker.getLatLng(), 10, { duration: 0.6 });
      marker.openPopup();
    }
  }, [selectedIds]);

  return <div ref={mapRef} className="w-full h-full" />;
}

function setupPopup(marker: L.Marker, s: Sample) {
  const popupHtml = `
    <div style="min-width:160px">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">${s.sampleId}</div>
      <div style="color:#8e8e93;font-size:12px">${s.basin} · ${s.formation}</div>
      ${s.ageMa
        ? `<div style="margin-top:6px;font-size:13px;color:#007aff;font-weight:500">
            ${s.ageMa} Ma${s.error ? " ± " + s.error : ""}
          </div>`
        : ""
      }
    </div>
  `;
  marker.bindPopup(popupHtml, { closeButton: false, offset: [0, -6] });
}

function setupClick(marker: L.Marker, id: string, onSelect: (id: string, multi?: boolean) => void) {
  marker.on("click", (e) => {
    const original = e.originalEvent as MouseEvent;
    onSelect(id, original.metaKey || original.ctrlKey);
  });
}
