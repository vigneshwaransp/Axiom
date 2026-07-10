"""
Stadium Graph representation and live Sensor Management Service.
Simulates and tracks crowd density levels and facility operational status (e.g., elevators).
"""

from typing import Dict, List, Optional, Set
import threading

class Node:
    def __init__(self, node_id: str, name: str, node_type: str, is_accessible: bool = True) -> None:
        self.id: str = node_id
        self.name: str = name
        self.type: str = node_type  # 'SECTION', 'GATE', 'ELEVATOR', 'ESCALATOR', 'STAIRS', 'WALKWAY', 'TRANSIT'
        self.is_accessible: bool = is_accessible
        self.crowd_density: str = "LOW"  # 'LOW', 'MEDIUM', 'HIGH'
        self.operational: bool = True    # Used for escalators/elevators

    def get_weight_multiplier(self) -> float:
        """Returns weight penalty factor based on crowd density or operational status."""
        if not self.operational:
            return float('inf')
        
        # Penalize congested paths significantly to redirect fans
        multipliers = {
            "LOW": 1.0,
            "MEDIUM": 2.5,
            "HIGH": 6.0
        }
        return multipliers.get(self.crowd_density, 1.0)

class Edge:
    def __init__(self, source_id: str, target_id: str, distance_meters: float, base_factor: float = 1.0) -> None:
        self.source_id: str = source_id
        self.target_id: str = target_id
        self.distance_meters: float = distance_meters
        self.base_factor: float = base_factor

class StadiumGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._lock = threading.Lock()
        self._initialize_default_stadium()

    def _initialize_default_stadium(self) -> None:
        """Sets up a realistic layout of a large 80,000-seat stadium (e.g., MetLife Stadium)."""
        # --- NODES ---
        # Seating Sections (Upper Level 300, Mid Level 200, Lower Level 100)
        sections = [
            # Upper Deck
            Node("sec_301", "Upper Section 301", "SECTION"),
            Node("sec_304", "Upper Section 304", "SECTION"),
            # Mid Deck
            Node("sec_201", "Mid Section 201", "SECTION"),
            Node("sec_204", "Mid Section 204", "SECTION"),
            # Lower Deck
            Node("sec_101", "Lower Section 101", "SECTION"),
            Node("sec_104", "Lower Section 104", "SECTION"),
        ]
        
        # Transit Exits & Concourse Gates
        gates = [
            Node("gate_a", "MetLife Gate A (East)", "GATE"),
            Node("gate_b", "Verizon Gate B (North)", "GATE"),
            Node("gate_c", "Pepsi Gate C (West)", "GATE"),
            Node("gate_d", "HCLTech Gate D (South)", "GATE"),
        ]
        
        # External Transportation Hubs
        transit = [
            Node("train_station", "MetLife Sports Complex Train Station", "TRANSIT"),
            Node("rideshare_hub", "Uber/Rideshare Pickup Lot", "TRANSIT"),
            Node("parking_lot_a", "East Parking Lot A", "TRANSIT"),
            Node("parking_lot_b", "West Parking Lot B", "TRANSIT"),
        ]

        # Connectors (stairs are NOT wheelchair accessible)
        connectors = [
            Node("stairs_east", "Stairs East (Level 3 to 1)", "STAIRS", is_accessible=False),
            Node("stairs_west", "Stairs West (Level 3 to 1)", "STAIRS", is_accessible=False),
            Node("elevator_east", "Concourse Elevator East", "ELEVATOR", is_accessible=True),
            Node("elevator_west", "Concourse Elevator West", "ELEVATOR", is_accessible=True),
            Node("escalator_north", "Main Escalator North (Level 2 to 1)", "ESCALATOR", is_accessible=False),
            Node("walkway_concourse", "Main Concourse Ring Road", "WALKWAY"),
        ]

        for node in sections + gates + transit + connectors:
            self.nodes[node.id] = node

        # --- EDGES (Bidirectional representation) ---
        raw_edges = [
            # Connect upper sections to vertical connectors
            Edge("sec_301", "stairs_east", 40.0),
            Edge("sec_301", "elevator_east", 60.0),
            Edge("sec_304", "stairs_west", 45.0),
            Edge("sec_304", "elevator_west", 55.0),

            # Connect mid sections to vertical connectors
            Edge("sec_201", "stairs_east", 30.0),
            Edge("sec_201", "elevator_east", 35.0),
            Edge("sec_201", "escalator_north", 50.0),
            Edge("sec_204", "stairs_west", 35.0),
            Edge("sec_204", "elevator_west", 30.0),
            Edge("sec_204", "escalator_north", 55.0),

            # Connect lower sections to gates
            Edge("sec_101", "gate_a", 25.0),
            Edge("sec_101", "gate_b", 40.0),
            Edge("sec_104", "gate_c", 30.0),
            Edge("sec_104", "gate_d", 35.0),

            # Connect vertical connectors to lower concourse/gates
            Edge("stairs_east", "gate_a", 20.0),
            Edge("elevator_east", "gate_a", 15.0),
            Edge("stairs_west", "gate_c", 25.0),
            Edge("elevator_west", "gate_c", 20.0),
            Edge("escalator_north", "gate_b", 15.0),

            # Concourse connection ring connecting gates
            Edge("gate_a", "walkway_concourse", 10.0),
            Edge("gate_b", "walkway_concourse", 10.0),
            Edge("gate_c", "walkway_concourse", 10.0),
            Edge("gate_d", "walkway_concourse", 10.0),
            
            # Connect concourse/gates to external transit hubs
            Edge("gate_a", "train_station", 120.0),
            Edge("gate_b", "rideshare_hub", 200.0),
            Edge("gate_a", "parking_lot_a", 150.0),
            Edge("gate_c", "parking_lot_b", 160.0),
            Edge("gate_d", "train_station", 180.0),
        ]

        # Register bidirectionally
        for edge in raw_edges:
            self.edges.append(edge)
            self.edges.append(Edge(edge.target_id, edge.source_id, edge.distance_meters, edge.base_factor))

    def update_sensor(self, node_id: str, crowd_density: str, elevator_operational: Optional[bool] = None) -> bool:
        """Thread-safe update of node properties based on physical sensor feeds."""
        with self._lock:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            if crowd_density in ["LOW", "MEDIUM", "HIGH"]:
                node.crowd_density = crowd_density
            
            if elevator_operational is not None and node.type in ["ELEVATOR", "ESCALATOR"]:
                node.operational = elevator_operational
            return True

    def get_neighbors(self, node_id: str, wheelchair_accessible: bool = False) -> List[Edge]:
        """Retrieve neighboring edges that satisfy accessibility constraints."""
        with self._lock:
            if node_id not in self.nodes:
                return []
            
            neighbors = []
            for edge in self.edges:
                if edge.source_id == node_id:
                    target_node = self.nodes.get(edge.target_id)
                    if not target_node:
                        continue
                    
                    # Enforce accessibility checks
                    if wheelchair_accessible and not target_node.is_accessible:
                        continue
                    
                    # Enforce operational checks
                    if not target_node.operational:
                        continue
                        
                    neighbors.append(edge)
            return neighbors

# Singleton instance
stadium_graph = StadiumGraph()
