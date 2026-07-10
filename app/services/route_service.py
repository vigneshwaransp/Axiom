"""
Accessibility-aware, crowd-weighted routing engine.
Uses Dijkstra's algorithm to calculate the optimal path through the stadium graph.
"""

import heapq
from typing import Dict, List, Tuple, Optional
from app.services.crowd_sensor import stadium_graph, Node, Edge
from app.schemas import RouteStep

class RouteService:
    @staticmethod
    def calculate_route(
        start_id: str, 
        destination_id: str, 
        wheelchair_accessible: bool = False
    ) -> Tuple[bool, List[str], List[RouteStep], float, float]:
        """
        Computes the shortest path using Dijkstra's algorithm.
        Incorporates dynamic congestion weights and accessibility constraints.
        
        Returns:
            Tuple of:
            - route_found (bool)
            - path_taken (List[str])
            - steps (List[RouteStep])
            - total_distance_meters (float)
            - total_time_minutes (float)
        """
        # Validate node existence
        if start_id not in stadium_graph.nodes or destination_id not in stadium_graph.nodes:
            return False, [], [], 0.0, 0.0

        # Dijkstra states: distances[node_id] = (cost, path)
        # We minimize time/effort cost, where weight = distance * node_congest_multiplier
        pq: List[Tuple[float, str, List[str]]] = [(0.0, start_id, [start_id])]
        visited: Set[str] = set()
        
        # Track path distances and times separately for metrics
        min_costs: Dict[str, float] = {start_id: 0.0}

        path_taken: List[str] = []
        route_found = False
        final_cost = 0.0

        while pq:
            cost, current_id, path = heapq.heappop(pq)

            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id == destination_id:
                path_taken = path
                route_found = True
                final_cost = cost
                break

            neighbors = stadium_graph.get_neighbors(current_id, wheelchair_accessible=wheelchair_accessible)
            for edge in neighbors:
                neighbor_id = edge.target_id
                neighbor_node = stadium_graph.nodes[neighbor_id]
                
                # Calculate cost penalty based on congestion
                step_weight = edge.distance_meters * neighbor_node.get_weight_multiplier()
                total_cost = cost + step_weight

                if neighbor_id not in min_costs or total_cost < min_costs[neighbor_id]:
                    min_costs[neighbor_id] = total_cost
                    heapq.heappush(pq, (total_cost, neighbor_id, path + [neighbor_id]))

        if not route_found:
            return False, [], [], 0.0, 0.0

        # Construct step-by-step instructions and metrics
        steps: List[RouteStep] = []
        total_distance = 0.0
        total_seconds = 0.0
        base_speed = 1.4  # Average walking speed is 1.4 m/s

        for i in range(len(path_taken) - 1):
            curr_id = path_taken[i]
            next_id = path_taken[i+1]
            
            # Find the corresponding edge
            edge_obj: Optional[Edge] = None
            for edge in stadium_graph.edges:
                if edge.source_id == curr_id and edge.target_id == next_id:
                    edge_obj = edge
                    break
            
            if not edge_obj:
                continue
                
            next_node = stadium_graph.nodes[next_id]
            multiplier = next_node.get_weight_multiplier()
            
            # Distance accumulation
            total_distance += edge_obj.distance_meters
            
            # Time calculation: distance / walking speed * congestion multiplier
            step_seconds = int((edge_obj.distance_meters / base_speed) * multiplier)
            total_seconds += step_seconds

            # Determine dynamic instruction template based on destination node type
            instruction = ""
            congested = next_node.crowd_density in ["MEDIUM", "HIGH"]
            
            node_name = next_node.name
            if next_node.type == "ELEVATOR":
                instruction = f"Take {node_name} to move levels."
            elif next_node.type == "STAIRS":
                instruction = f"Use {node_name} to descend to ground level."
            elif next_node.type == "ESCALATOR":
                instruction = f"Take {node_name} down to the main floor."
            elif next_node.type == "GATE":
                instruction = f"Head to exit gate {node_name}."
            elif next_node.type == "TRANSIT":
                instruction = f"Walk to your final transit location: {node_name}."
            else:
                instruction = f"Walk along the pathway towards {node_name}."

            if congested:
                instruction += f" (Caution: Crowd level is currently {next_node.crowd_density.lower()})"

            steps.append(RouteStep(
                step_number=i + 1,
                instruction=instruction,
                congested=congested,
                estimated_seconds=step_seconds
            ))

        total_time_minutes = round(total_seconds / 60.0, 1)

        return True, path_taken, steps, total_distance, total_time_minutes
