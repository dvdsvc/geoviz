"""
Knowledge graph for geological samples.
Builds a NetworkX graph with all sample attributes as nodes:

  Nodes:
    Sample, Formation, Group, Basin, Region, Province,
    RockType, DatingSystem, Technique, DatingMineral, AgeType,
    PhysicalMethod, Location, Reference

  Edges:
    Sample → Formation/Group/Location          (BELONGS_TO)
    Formation → Basin, Group → Basin           (IN_BASIN)
    Basin → Region, Region → Province          (IN_REGION / HAS_PROVINCE)
    Sample → RockType/DatingSystem/Technique/  (HAS_*)
             DatingMineral/AgeType/PhysicalMethod
    Sample → Reference                         (CITED_IN)
    Sample ↔ Sample                            (TEMPORALLY_NEAR, SAME_FORMATION)

Supports graph traversal queries:
  - Navigate hierarchy: Province→Region→Basin→Group/Formation→Sample
  - Faceted exploration: find samples by technique, mineral, rock type
  - Temporal/spatial correlation
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

import networkx as nx

# ── Node types ─────────────────────────────────────────────────────────────────

NODE_SAMPLE = "Sample"
NODE_FORMATION = "Formation"
NODE_GROUP = "Group"            # 群 (e.g., 天台群, 建德群)
NODE_BASIN = "Basin"
NODE_REGION = "Region"
NODE_PROVINCE = "Province"      # 省/区域 (e.g., 浙江省南部, 福建省)
NODE_ROCK_TYPE = "RockType"
NODE_DATING_SYSTEM = "DatingSystem"      # U-Pb, Ar-Ar
NODE_TECHNIQUE = "Technique"             # LA-ICP-MS, SIMS, SHRIMP
NODE_DATING_MINERAL = "DatingMineral"    # 锆石, etc.
NODE_AGE_TYPE = "AgeType"                # 加权平均, Concordia age
NODE_PHYSICAL_METHOD = "PhysicalMethod"  # Ablation / Spot
NODE_LOCATION = "Location"               # 具体采样点
NODE_REFERENCE = "Reference"

ALL_NODE_TYPES = [
    NODE_SAMPLE, NODE_FORMATION, NODE_GROUP, NODE_BASIN, NODE_REGION,
    NODE_PROVINCE, NODE_ROCK_TYPE, NODE_DATING_SYSTEM, NODE_TECHNIQUE,
    NODE_DATING_MINERAL, NODE_AGE_TYPE, NODE_PHYSICAL_METHOD,
    NODE_LOCATION, NODE_REFERENCE,
]

# ── Edge types ─────────────────────────────────────────────────────────────────

EDGE_FROM = "BELONGS_TO"          # Sample → Formation/Group/Location
EDGE_IN_BASIN = "IN_BASIN"         # Formation/Group/Location → Basin
EDGE_IN_REGION = "IN_REGION"       # Basin → Region
EDGE_IN_PROVINCE = "IN_PROVINCE"   # Region → Province
EDGE_ROCK = "HAS_ROCK_TYPE"        # Sample → RockType
EDGE_DATING_SYS = "USES_SYSTEM"    # Sample → DatingSystem
EDGE_TECHNIQUE = "USES_TECHNIQUE"  # Sample → Technique
EDGE_MINERAL = "USES_MINERAL"      # Sample → DatingMineral
EDGE_AGE_TYPE = "HAS_AGE_TYPE"     # Sample → AgeType
EDGE_PHYSICAL = "HAS_PHYSICAL_METHOD"  # Sample → PhysicalMethod
EDGE_CITED = "CITED_IN"            # Sample → Reference
EDGE_TEMPORAL = "TEMPORALLY_NEAR"  # Sample ↔ Sample (age diff ≤ 5 Ma)
EDGE_SAME_FM = "SAME_FORMATION"    # Sample ↔ Sample (same formation)


class KnowledgeGraph:
    def __init__(self, samples: list[dict]):
        self.G = nx.MultiDiGraph()
        self._samples = samples
        self._sample_index: dict[str, str] = {}
        self._indices: dict[str, dict[str, str]] = {
            NODE_FORMATION: {},
            NODE_GROUP: {},
            NODE_BASIN: {},
            NODE_REGION: {},
            NODE_PROVINCE: {},
            NODE_ROCK_TYPE: {},
            NODE_DATING_SYSTEM: {},
            NODE_TECHNIQUE: {},
            NODE_DATING_MINERAL: {},
            NODE_AGE_TYPE: {},
            NODE_PHYSICAL_METHOD: {},
            NODE_LOCATION: {},
            NODE_REFERENCE: {},
        }
        self._id_counters: dict[str, int] = defaultdict(int)
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _node_id(self, ntype: str, name: str) -> str:
        return f"{ntype}:{name}"

    def _ensure_node(self, ntype: str, name: str, **extra) -> str:
        """Get or create a node of given type. Returns node_id."""
        if not name or name.lower() in ("none", "null", "nan", ""):
            return ""
        idx = self._indices.get(ntype, {})
        if name in idx:
            return idx[name]
        nid = self._node_id(ntype, name)
        self.G.add_node(nid, type=ntype, name=name, **extra)
        idx[name] = nid
        return nid

    def _ensure_edge(self, src: str, dst: str, etype: str, **attrs):
        if src and dst:
            self.G.add_edge(src, dst, type=etype, **attrs)

    def _build(self):
        for s in self._samples:
            self._add_sample(s)

        # Hierarchy edges
        for basin_name, bid in self._indices[NODE_BASIN].items():
            # Basin → Region (via samples that have this basin+region)
            pass  # Region edges are created per-sample below

        for fm_name, fid in self._indices[NODE_FORMATION].items():
            # Formation → Basin is created per-sample
            pass

        self._add_temporal_edges()
        self._add_same_formation_edges()

    def _add_sample(self, s: dict):
        sid = s["sampleId"]
        if not sid:
            return

        # ── Create all attribute nodes ──
        region_nid = self._ensure_node(NODE_REGION, s.get("region", ""))
        basin_nid = self._ensure_node(NODE_BASIN, s.get("basin", ""))
        formation_nid = self._ensure_node(NODE_FORMATION, s.get("formation", ""))
        group_nid = self._ensure_node(NODE_GROUP, s.get("group", ""))
        province_nid = self._ensure_node(NODE_PROVINCE, s.get("regionProvince", ""))
        rock_nid = self._ensure_node(NODE_ROCK_TYPE, s.get("rockType", ""))
        system_nid = self._ensure_node(NODE_DATING_SYSTEM, s.get("datingSystem", ""))
        technique_nid = self._ensure_node(NODE_TECHNIQUE, s.get("technique", ""))
        mineral_nid = self._ensure_node(NODE_DATING_MINERAL, s.get("datingMineral", ""))
        age_type_nid = self._ensure_node(NODE_AGE_TYPE, s.get("ageType", ""))
        physical_nid = self._ensure_node(NODE_PHYSICAL_METHOD, s.get("physicalMethod", ""))
        location_nid = self._ensure_node(NODE_LOCATION, s.get("location", ""))
        ref_nid = self._ensure_node(NODE_REFERENCE, s.get("reference", ""))

        # ── Hierarchy edges ──
        if province_nid and region_nid:
            self._ensure_edge(region_nid, province_nid, EDGE_IN_PROVINCE)
        if region_nid and basin_nid:
            self._ensure_edge(basin_nid, region_nid, EDGE_IN_REGION)
        if basin_nid and formation_nid:
            self._ensure_edge(formation_nid, basin_nid, EDGE_IN_BASIN)
        if basin_nid and group_nid:
            self._ensure_edge(group_nid, basin_nid, EDGE_IN_BASIN)
        if basin_nid and location_nid:
            self._ensure_edge(location_nid, basin_nid, EDGE_IN_BASIN)

        # ── Sample node ──
        sample_nid = self._node_id(NODE_SAMPLE, sid)
        self.G.add_node(sample_nid, type=NODE_SAMPLE, **s)
        self._sample_index[sid] = sample_nid

        # ── Sample → attribute edges ──
        self._ensure_edge(sample_nid, formation_nid, EDGE_FROM)
        self._ensure_edge(sample_nid, group_nid, EDGE_FROM)
        self._ensure_edge(sample_nid, location_nid, EDGE_FROM)
        self._ensure_edge(sample_nid, rock_nid, EDGE_ROCK)
        self._ensure_edge(sample_nid, system_nid, EDGE_DATING_SYS)
        self._ensure_edge(sample_nid, technique_nid, EDGE_TECHNIQUE)
        self._ensure_edge(sample_nid, mineral_nid, EDGE_MINERAL)
        self._ensure_edge(sample_nid, age_type_nid, EDGE_AGE_TYPE)
        self._ensure_edge(sample_nid, physical_nid, EDGE_PHYSICAL)
        self._ensure_edge(sample_nid, ref_nid, EDGE_CITED)

    def _add_temporal_edges(self):
        """Connect samples with similar ages (±5 Ma) within same region."""
        samples_with_age = [(s["sampleId"], s["ageMa"], s.get("region", ""))
                            for s in self._samples if s.get("ageMa") is not None]
        for i in range(len(samples_with_age)):
            sid1, age1, region1 = samples_with_age[i]
            n1 = self._sample_index.get(sid1)
            if not n1:
                continue
            for j in range(i + 1, len(samples_with_age)):
                sid2, age2, region2 = samples_with_age[j]
                if abs(age1 - age2) <= 5 and region1 == region2:
                    n2 = self._sample_index.get(sid2)
                    if n2:
                        self.G.add_edge(n1, n2, type=EDGE_TEMPORAL, age_diff=abs(age1 - age2))

    def _add_same_formation_edges(self):
        """Connect samples in the same formation."""
        by_formation: dict[str, list[str]] = defaultdict(list)
        for s in self._samples:
            fm = s.get("formation", "")
            if fm:
                by_formation[fm].append(s["sampleId"])
        for fm, sids in by_formation.items():
            if len(sids) < 2:
                continue
            for i in range(len(sids)):
                for j in range(i + 1, len(sids)):
                    n1 = self._sample_index.get(sids[i])
                    n2 = self._sample_index.get(sids[j])
                    if n1 and n2:
                        self.G.add_edge(n1, n2, type=EDGE_SAME_FM)

    # ── Query helpers ──────────────────────────────────────────────────────────

    def _get_node(self, ntype: str, name: str) -> Optional[str]:
        return self._indices.get(ntype, {}).get(name)

    def _get_nodes_by_type(self, source_nid: str, ntype: str, reverse: bool = True) -> list[str]:
        """Get neighbor node IDs of a given type."""
        results = []
        if reverse:
            for pred in self.G.predecessors(source_nid):
                if self.G.nodes[pred].get("type") == ntype:
                    results.append(pred)
        else:
            for succ in self.G.successors(source_nid):
                if self.G.nodes[succ].get("type") == ntype:
                    results.append(succ)
        return results

    def _samples_from_node(self, nid: str) -> list[dict]:
        """Get all Sample nodes that point to nid."""
        return [dict(self.G.nodes[p]) for p in self.G.predecessors(nid)
                if self.G.nodes[p].get("type") == NODE_SAMPLE]

    def _samples_recursive(self, nid: str, visited: Optional[set] = None) -> list[dict]:
        """Recursively find all Sample nodes under a hierarchy node."""
        if visited is None:
            visited = set()
        if nid in visited:
            return []
        visited.add(nid)
        results = []
        for pred in self.G.predecessors(nid):
            if self.G.nodes[pred].get("type") == NODE_SAMPLE:
                results.append(dict(self.G.nodes[pred]))
            else:
                results.extend(self._samples_recursive(pred, visited))
        return results

    # ── Public query API ───────────────────────────────────────────────────────

    def get_sample(self, sample_id: str) -> Optional[dict]:
        node = self._sample_index.get(sample_id)
        if node is None:
            return None
        return dict(self.G.nodes[node])

    def get_samples_by(self, ntype: str, name: str) -> list[dict]:
        """Get all samples linked to a named entity."""
        nid = self._get_node(ntype, name)
        if nid is None:
            return []
        return self._samples_recursive(nid)

    def get_samples_by_formation(self, formation: str) -> list[dict]:
        return self.get_samples_by(NODE_FORMATION, formation)

    def get_samples_by_basin(self, basin: str) -> list[dict]:
        return self.get_samples_by(NODE_BASIN, basin)

    def get_samples_by_region(self, region: str) -> list[dict]:
        return self.get_samples_by(NODE_REGION, region)

    def get_samples_by_rock_type(self, rock_type: str) -> list[dict]:
        return self.get_samples_by(NODE_ROCK_TYPE, rock_type)

    def get_samples_by_technique(self, technique: str) -> list[dict]:
        return self.get_samples_by(NODE_TECHNIQUE, technique)

    def get_samples_by_dating_system(self, system: str) -> list[dict]:
        return self.get_samples_by(NODE_DATING_SYSTEM, system)

    def get_formations_in_basin(self, basin: str) -> list[str]:
        bid = self._get_node(NODE_BASIN, basin)
        if bid is None:
            return []
        return [self.G.nodes[n]["name"] for n in self.G.predecessors(bid)
                if self.G.nodes[n]["type"] == NODE_FORMATION]

    def get_basins_in_region(self, region: str) -> list[str]:
        rid = self._get_node(NODE_REGION, region)
        if rid is None:
            return []
        return [self.G.nodes[n]["name"] for n in self.G.predecessors(rid)
                if self.G.nodes[n]["type"] == NODE_BASIN]

    def get_temporally_near(self, sample_id: str, max_age_diff: float = 5) -> list[dict]:
        node = self._sample_index.get(sample_id)
        if node is None:
            return []
        results = []
        for neighbor in self.G.neighbors(node):
            for _, d in self.G.get_edge_data(node, neighbor).items():
                if d.get("type") == EDGE_TEMPORAL and d.get("age_diff", 999) <= max_age_diff:
                    if self.G.nodes[neighbor]["type"] == NODE_SAMPLE:
                        results.append(dict(self.G.nodes[neighbor]))
        return results

    def get_same_formation_samples(self, sample_id: str) -> list[dict]:
        node = self._sample_index.get(sample_id)
        if node is None:
            return []
        # Find the formation this sample belongs to
        for _, neighbor, d in self.G.out_edges(node, data=True):
            if d["type"] == EDGE_FROM and self.G.nodes[neighbor]["type"] == NODE_FORMATION:
                results = self._samples_from_node(neighbor)
                return [s for s in results if s.get("sampleId") != sample_id]
        return []

    def get_context_for_sample(self, sample_id: str) -> str:
        s = self.get_sample(sample_id)
        if s is None:
            return ""
        lines = [f"样品 {sample_id}: {s.get('rockType','')}，年龄 {s.get('ageMa','?')} Ma"]

        fm = s.get("formation", "")
        if fm:
            fm_samples = self.get_samples_by_formation(fm)
            fm_ages = [x["ageMa"] for x in fm_samples if x.get("ageMa") is not None]
            lines.append(f"所属地层: {fm}")
            if fm_ages:
                lines.append(f"  该组年龄范围: {min(fm_ages)}-{max(fm_ages)} Ma, n={len(fm_ages)}")

        basin = s.get("basin", "")
        if basin:
            formations = self.get_formations_in_basin(basin)
            lines.append(f"所属盆地: {basin}")
            lines.append(f"  盆地内地层组: {', '.join(formations[:10])}")

        temporal = self.get_temporally_near(sample_id, 10)
        if temporal:
            t_ids = [t["sampleId"] for t in temporal[:5]]
            lines.append(f"同期样品(±10Ma): {', '.join(t_ids)}")

        return "\n".join(lines)

    def traverse(self, start_type: str, start_name: str, target_type: str, max_hops: int = 4) -> list[dict]:
        """Generic traversal: from a named node, find all nodes of target_type within max_hops."""
        candidates = [n for n, d in self.G.nodes(data=True)
                      if d.get("type") == start_type and d.get("name") == start_name]
        if not candidates:
            return []
        start_node = candidates[0]
        results = []
        for node in self.G.nodes:
            if self.G.nodes[node]["type"] != target_type:
                continue
            try:
                path = nx.shortest_path(self.G, start_node, node)
                if len(path) - 1 <= max_hops:
                    results.append(dict(self.G.nodes[node]))
            except nx.NetworkXNoPath:
                pass
        return results

    # ── Stats ──────────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        type_counts: dict[str, int] = defaultdict(int)
        for _, d in self.G.nodes(data=True):
            type_counts[str(d.get("type", "?"))] += 1

        by_type_details = {}
        for ntype, idx in self._indices.items():
            names = sorted(idx.keys())
            if names:
                by_type_details[ntype] = names

        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "by_type": dict(type_counts),
            "details": by_type_details,
        }
