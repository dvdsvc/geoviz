"use client";

import { useRef, useEffect, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { Sample } from "@/types";

interface GlobeViewProps {
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

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

export default function GlobeView({ samples, selectedIds, onSelect }: GlobeViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedIdsRef = useRef(selectedIds);
  selectedIdsRef.current = selectedIds;

  const geojson: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: samples.map((s) => ({
      type: "Feature",
      properties: {
        id: s.id,
        sampleId: s.sampleId,
        region: s.region,
        basin: s.basin,
        formation: s.formation,
        ageMa: s.ageMa,
        color: regionColors[s.region] || "#666",
      },
      geometry: { type: "Point", coordinates: [s.lng, s.lat] },
    })),
  };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    if (!TOKEN || TOKEN.includes("placeholder")) {
      // Fallback: show setup instructions
      return;
    }

    mapboxgl.accessToken = TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [105, 35],
      zoom: 1.5,
      projection: "globe",
      attributionControl: false,
      antialias: true,
    });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-right");

    map.on("style.load", () => {
      map.setFog({
        color: "rgba(15, 20, 30, 0.7)",
        "high-color": "rgba(30, 50, 80, 0.6)",
        "horizon-blend": 0.08,
        "space-color": "rgba(5, 8, 15, 1)",
        "star-intensity": 0.4,
      });

      // Add atmosphere glow
      map.addLayer({
        id: "sky",
        type: "sky",
        paint: {
          "sky-type": "atmosphere",
          "sky-atmosphere-sun": [0.0, 90.0],
          "sky-atmosphere-sun-intensity": 3,
        },
      });

      // Sample points source
      map.addSource("samples", { type: "geojson", data: geojson });

      // Outer glow
      map.addLayer({
        id: "samples-glow",
        type: "circle",
        source: "samples",
        paint: {
          "circle-radius": 10,
          "circle-color": ["get", "color"],
          "circle-opacity": 0.15,
          "circle-blur": 1,
        },
      });

      // Main dots
      const selectedLit = selectedIds.length > 0 ? ["literal", selectedIds] : ["literal", ["__none__"]];
      map.addLayer({
        id: "samples-circle",
        type: "circle",
        source: "samples",
        paint: {
          "circle-radius": [
            "case",
            ["in", ["get", "id"], selectedLit],
            8,
            5,
          ],
          "circle-color": ["get", "color"],
          "circle-stroke-color": "rgba(255,255,255,0.9)",
          "circle-stroke-width": [
            "case",
            ["in", ["get", "id"], selectedLit],
            2.5,
            1.5,
          ],
        },
      });

      // Labels for selected samples
      map.addLayer({
        id: "samples-label",
        type: "symbol",
        source: "samples",
        filter: selectedIds.length > 0
          ? ["in", ["get", "id"], selectedLit]
          : ["==", ["get", "id"], "__none__"],
        layout: {
          "text-field": ["get", "sampleId"],
          "text-size": 12,
          "text-offset": [0, -1.5],
          "text-anchor": "bottom",
          "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
        },
        paint: {
          "text-color": "#ffffff",
          "text-halo-color": "rgba(0,0,0,0.7)",
          "text-halo-width": 1.5,
        },
      });

      // Click handler
      map.on("click", "samples-circle", (e) => {
        if (!e.features?.length) return;
        const id = e.features[0].properties?.id;
        if (id) {
          const original = e.originalEvent as MouseEvent;
          onSelectRef.current(id, original.metaKey || original.ctrlKey);
        }
      });

      map.on("mouseenter", "samples-circle", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "samples-circle", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update selected state
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    try {
      const selectedLit = selectedIds.length > 0 ? ["literal", selectedIds] : ["literal", ["__none__"]];

      if (map.getLayer("samples-label")) {
        map.setFilter("samples-label",
          selectedIds.length > 0
            ? ["in", ["get", "id"], selectedLit]
            : ["==", ["get", "id"], "__none__"]
        );
      }
      if (map.getLayer("samples-circle")) {
        map.setPaintProperty("samples-circle", "circle-radius", [
          "case",
          ["in", ["get", "id"], selectedLit],
          8,
          5,
        ]);
      }

      // Fly to last selected sample
      if (selectedIds.length > 0) {
        const lastId = selectedIds[selectedIds.length - 1];
        const s = samples.find((s) => s.id === lastId);
        if (s) {
          map.flyTo({ center: [s.lng, s.lat], zoom: 4, duration: 1200, essential: true });
        }
      }
    } catch {
      // Layers not yet loaded
    }
  }, [selectedIds, samples]);

  // No token fallback
  if (!TOKEN || TOKEN.includes("placeholder")) {
    return (
      <div
        ref={containerRef}
        className="w-full h-full flex items-center justify-center"
        style={{ background: "#0f1419" }}
      >
        <div className="text-center px-8">
          <p className="text-[15px] text-white/80 font-medium mb-2">
            Mapbox Token Required
          </p>
          <p className="text-[13px] text-white/40 leading-relaxed max-w-md">
            Get a free access token at{" "}
            <span className="text-sky-400">account.mapbox.com</span>
            {" "}and set it in{" "}
            <code className="bg-white/10 px-1.5 py-0.5 rounded text-sky-300 text-[12px]">
              .env.local
            </code>
            {" "}as{" "}
            <code className="bg-white/10 px-1.5 py-0.5 rounded text-sky-300 text-[12px]">
              NEXT_PUBLIC_MAPBOX_TOKEN
            </code>
          </p>
        </div>
      </div>
    );
  }

  return <div ref={containerRef} className="w-full h-full" />;
}
