import random
from dataclasses import dataclass
from enum import Enum
from math import cos, pi, sin
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.spatial import KDTree


@dataclass
class NitrogenSpeciesProperties:
    """
    Define data class for nitrogen species properties.

    Attributes
    ----------
    half_bond_lengths : List[float]
        A list of bond lengths for half the structure due to symmetry.
    half_angles : List[float]
        A list of bond angles for half the structure due to symmetry.
    """

    half_bond_lengths: List[float]
    half_angles: List[float]


class NitrogenSpecies(Enum):
    GRAPHITIC = "Graphitic-N"
    # PYRIDINIC = "pyridinic"
    PYRIDINIC_1 = "Pyridinic-N 1"
    PYRIDINIC_2 = "Pyridinic-N 2"
    PYRIDINIC_3 = "Pyridinic-N 3"
    PYRIDINIC_4 = "Pyridinic-N 4"
    # PYRROLIC = "pyrrolic"
    # PYRAZOLE = "pyrazole"


class GrapheneGraph:
    def __init__(self, bond_distance: float, sheet_size: Tuple[float, float]):
        """
        Initialize the GrapheneGraph with given bond distance and sheet size.

        Parameters
        ----------
        bond_distance : float
            The bond distance between carbon atoms in the graphene sheet.
        sheet_size : Tuple[float, float]
            The size of the graphene sheet in the x and y directions.
        """
        self.bond_distance = bond_distance
        """The bond distance between carbon atoms in the graphene sheet."""
        self.sheet_size = sheet_size
        """The size of the graphene sheet in the x and y directions."""
        self.graph = nx.Graph()
        """The networkx graph representing the graphene sheet structure."""
        self._build_graphene_sheet()

        self.possible_carbon_atoms = [node for node, data in self.graph.nodes(data=True) if data["element"] == "C"]
        """A list of all possible carbon atoms in the graphene sheet for nitrogen doping."""

        self.species_properties = self._initialize_species_properties()
        """A dictionary mapping each NitrogenSpecies to its corresponding NitrogenSpeciesProperties.
        This includes bond lengths and angles characteristic to each species."""

        # Initialize positions and KDTree for efficient neighbor search
        self._positions = np.array([self.graph.nodes[node]["position"] for node in self.graph.nodes])
        """The positions of atoms in the graphene sheet."""
        self._kdtree = KDTree(self._positions)  # ToDo: Solve problem with periodic boundary conditions
        """The KDTree data structure for efficient nearest neighbor search. A KDTree is particularly efficient for
        spatial queries, such as searching for neighbors within a certain Euclidean distance. Such queries are often
        computationally intensive when performed over a graph, especially when dealing with direct distance rather than
        path lengths in the graph."""

    @property
    def positions(self):
        return self._positions

    @positions.setter
    def positions(self, new_positions):
        """Update the positions of atoms and rebuild the KDTree for efficient spatial queries."""
        self._positions = new_positions
        self._kdtree = KDTree(new_positions)

    @property
    def cc_x_distance(self):
        """Calculate the distance between atoms in the x direction."""
        return self.bond_distance * sin(pi / 6)

    @property
    def cc_y_distance(self):
        """Calculate the distance between atoms in the y direction."""
        return self.bond_distance * cos(pi / 6)

    @property
    def num_cells_x(self):
        """Calculate the number of unit cells in the x direction based on sheet size and bond distance."""
        return int(self.sheet_size[0] // (2 * self.bond_distance + 2 * self.cc_x_distance))

    @property
    def num_cells_y(self):
        """Calculate the number of unit cells in the y direction based on sheet size and bond distance."""
        return int(self.sheet_size[1] // (2 * self.cc_y_distance))

    def _build_graphene_sheet(self):
        """
        Build the graphene sheet structure by creating nodes and edges (using graph theory via networkx).

        This method iterates over the entire sheet, adding nodes and edges for each unit cell.
        It also connects adjacent unit cells and adds periodic boundary conditions.
        """
        index = 0
        for y in range(self.num_cells_y):
            for x in range(self.num_cells_x):
                x_offset = x * (2 * self.bond_distance + 2 * self.cc_x_distance)
                y_offset = y * (2 * self.cc_y_distance)

                # Add nodes and edges for the unit cell
                self._add_unit_cell(index, x_offset, y_offset)

                # Add horizontal bonds between adjacent unit cells
                if x > 0:
                    self.graph.add_edge(index - 1, index, bond_length=self.bond_distance)

                # Add vertical bonds between unit cells in adjacent rows
                if y > 0:
                    self.graph.add_edge(index - 4 * self.num_cells_x + 1, index, bond_length=self.bond_distance)
                    self.graph.add_edge(index - 4 * self.num_cells_x + 2, index + 3, bond_length=self.bond_distance)

                index += 4

        # Add periodic boundary conditions
        self._add_periodic_boundaries()

    def _add_unit_cell(self, index: int, x_offset: float, y_offset: float):
        """
        Add nodes and internal bonds within a unit cell.

        Parameters
        ----------
        index : int
            The starting index for the nodes in the unit cell.
        x_offset : float
            The x-coordinate offset for the unit cell.
        y_offset : float
            The y-coordinate offset for the unit cell.
        """
        # Define relative positions of atoms within the unit cell
        unit_cell_positions = [
            (x_offset, y_offset),
            (x_offset + self.cc_x_distance, y_offset + self.cc_y_distance),
            (x_offset + self.cc_x_distance + self.bond_distance, y_offset + self.cc_y_distance),
            (x_offset + 2 * self.cc_x_distance + self.bond_distance, y_offset),
        ]

        # Add nodes with positions and element type (carbon)
        nodes = [(index + i, {"element": "C", "position": pos}) for i, pos in enumerate(unit_cell_positions)]
        self.graph.add_nodes_from(nodes)

        # Add internal bonds within the unit cell
        edges = [
            (index + i, index + i + 1, {"bond_length": self.bond_distance}) for i in range(len(unit_cell_positions) - 1)
        ]
        self.graph.add_edges_from(edges)

    def _add_periodic_boundaries(self):
        """
        Add periodic boundary conditions to the graphene sheet.

        This method connects the edges of the sheet to simulate an infinite sheet.
        """
        num_nodes_x = self.num_cells_x * 4

        # Generate base indices for horizontal boundaries
        base_indices_y = np.arange(self.num_cells_y) * num_nodes_x
        right_edge_indices = base_indices_y + (self.num_cells_x - 1) * 4 + 3
        left_edge_indices = base_indices_y

        # Add horizontal periodic boundary conditions
        self.graph.add_edges_from(
            zip(right_edge_indices, left_edge_indices), bond_length=self.bond_distance, periodic=True
        )

        # Generate base indices for vertical boundaries
        top_left_indices = np.arange(self.num_cells_x) * 4
        bottom_left_indices = top_left_indices + (self.num_cells_y - 1) * num_nodes_x + 1
        bottom_right_indices = top_left_indices + (self.num_cells_y - 1) * num_nodes_x + 2

        # Add vertical periodic boundary conditions
        self.graph.add_edges_from(
            zip(bottom_left_indices, top_left_indices), bond_length=self.bond_distance, periodic=True
        )
        self.graph.add_edges_from(
            zip(bottom_right_indices, top_left_indices + 3), bond_length=self.bond_distance, periodic=True
        )

    @staticmethod
    def _initialize_species_properties() -> Dict[NitrogenSpecies, NitrogenSpeciesProperties]:
        pyridinic_4_properties = NitrogenSpeciesProperties(
            half_bond_lengths=[1.45, 1.34, 1.32, 1.47, 1.32, 1.34, 1.45],
            half_angles=[120.26, 121.02, 119.3, 119.3, 121.02, 120.26, 122.91],
        )

        # Initialize other species similarly
        species_properties = {
            NitrogenSpecies.PYRIDINIC_4: pyridinic_4_properties,
            # Add other species here
        }
        return species_properties

    def add_nitrogen_doping(self, total_percentage: float = None, percentages: dict = None):
        """
        Add nitrogen doping to the graphene sheet.

        This method replaces a specified percentage of carbon atoms with nitrogen atoms in the graphene sheet.
        If specific percentages for different nitrogen species are provided, it ensures the sum does not exceed the
        total percentage. The remaining percentage is distributed equally among the available nitrogen species.

        Parameters
        ----------
        total_percentage : float, optional
            The total percentage of carbon atoms to replace with nitrogen atoms. Default is 10 if not specified.
        percentages : dict, optional
            A dictionary specifying the percentages for each nitrogen species. Keys should be NitrogenSpecies enum
            values and values should be the percentages for the corresponding species.

        Raises
        ------
        ValueError
            If the specific percentages exceed the total percentage.

        Notes
        -----
        - If no total percentage is provided, a default of 10% is used.
        - If specific percentages are provided and their sum exceeds the total percentage, a ValueError is raised.
        - Remaining percentages are distributed equally among the available nitrogen species.
        - Nitrogen species are added in a predefined order: PYRIDINIC_4, PYRIDINIC_3, PYRIDINIC_2, PYRIDINIC_1,
        GRAPHITIC.
        """
        # Validate specific percentages and calculate the remaining percentage
        if percentages:
            if total_percentage is None:
                total_percentage = sum(percentages.values())  # Set total to sum of specific percentages if not provided
            else:
                specific_total_percentage = sum(percentages.values())  # Sum of provided specific percentages
                if specific_total_percentage > total_percentage:
                    # Raise an error if the sum of specific percentages exceeds the total percentage
                    raise ValueError(
                        f"The total specific percentages {specific_total_percentage}% are higher than the "
                        f"total_percentage {total_percentage}%. Please adjust your input so that the sum of the "
                        f"'percentages' is less than or equal to 'total_percentage'."
                    )
        else:
            # Set a default total percentage if not provided
            if total_percentage is None:
                total_percentage = 10  # Default total percentage
            percentages = {}  # Initialize an empty dictionary if no specific percentages are provided

        # Calculate the remaining percentage for other species
        remaining_percentage = total_percentage - sum(percentages.values())

        if remaining_percentage > 0:
            # Determine available species not included in the specified percentages
            available_species = [species for species in NitrogenSpecies if species not in percentages]
            # Distribute the remaining percentage equally among available species
            default_distribution = {
                species: remaining_percentage / len(available_species) for species in available_species
            }
            # Add the default distribution to the specified percentages
            for species, pct in default_distribution.items():
                if species not in percentages:
                    percentages[species] = pct

        # Calculate the number of nitrogen atoms to add based on the given percentage
        num_atoms = self.graph.number_of_nodes()
        specific_num_nitrogen = {species: int(num_atoms * pct / 100) for species, pct in percentages.items()}

        # Dictionary to keep track of actually added nitrogen atoms
        added_nitrogen_counts = {species: 0 for species in NitrogenSpecies}

        # Define the order of nitrogen doping insertion based on the species
        for species in [
            NitrogenSpecies.PYRIDINIC_4,
            NitrogenSpecies.PYRIDINIC_3,
            NitrogenSpecies.PYRIDINIC_2,
            NitrogenSpecies.PYRIDINIC_1,
            NitrogenSpecies.GRAPHITIC,
        ]:
            if species in specific_num_nitrogen:
                num_nitrogen_atoms = specific_num_nitrogen[species]
                added_nitrogen_counts[species] += self._add_nitrogen_atoms(num_nitrogen_atoms, species)

        # Calculate the actual percentages of added nitrogen species
        total_atoms = self.graph.number_of_nodes()
        actual_percentages = {
            species: round((count / total_atoms) * 100, 2) if total_atoms > 0 else 0
            for species, count in added_nitrogen_counts.items()
        }

        # Display the results in a DataFrame and add the total doping percentage
        total_doping_percentage = sum(actual_percentages.values())
        doping_percentages_df = pd.DataFrame.from_dict(
            actual_percentages, orient="index", columns=["Actual Percentage"]
        )
        doping_percentages_df.index.name = "Nitrogen Species"
        doping_percentages_df.reset_index(inplace=True)
        total_row = pd.DataFrame([{"Nitrogen Species": "Total Doping", "Actual Percentage": total_doping_percentage}])
        doping_percentages_df = pd.concat([doping_percentages_df, total_row], ignore_index=True)
        print(f"\n{doping_percentages_df}")

    def _add_nitrogen_atoms(self, num_nitrogen: int, nitrogen_species: NitrogenSpecies):
        """
        Add nitrogen atoms of a specific species to the graphene sheet.

        Parameters
        ----------
        num_nitrogen : int
            The number of nitrogen atoms to add.
        nitrogen_species : NitrogenSpecies
            The type of nitrogen doping to add.

        Returns
        -------
        int
            The number of nitrogen atoms of the species actually added.

        Notes
        -----
        This method randomly replaces carbon atoms with nitrogen atoms of the specified species.
        """

        # Initialize an empty list to store the chosen atoms for nitrogen doping
        chosen_atoms = []

        # Shuffle the list of possible carbon atoms
        possible_carbon_atoms_shuffled = random.sample(self.possible_carbon_atoms, len(self.possible_carbon_atoms))

        while len(chosen_atoms) < num_nitrogen and possible_carbon_atoms_shuffled:
            # Randomly select a carbon atom from the shuffled list without replacement
            atom_id = possible_carbon_atoms_shuffled.pop(0)

            if atom_id not in self.possible_carbon_atoms or not self._valid_doping_position(nitrogen_species, atom_id):
                continue

            # Get the position of the selected atom (used for integrating doping via periodic boundary conditions)
            # ToDo: Noch nicht sicher, ob diese Variable benötigt wird; evtl. wieder überall entfernen
            reference_node_position = self.graph.nodes[atom_id]["position"]

            # Atom is valid, proceed with nitrogen doping
            neighbors = self.get_neighbors_via_edges(atom_id)

            # Implement species-specific changes for nitrogen doping
            if nitrogen_species == NitrogenSpecies.GRAPHITIC:
                # Add the selected atom to the list of chosen atoms
                chosen_atoms.append(atom_id)
                # Update the selected atom's element to nitrogen and set its nitrogen species
                self.graph.nodes[atom_id]["element"] = "N"
                self.graph.nodes[atom_id]["nitrogen_species"] = nitrogen_species
                # Remove the selected atom and its neighbors from the list of potential carbon atoms
                self.possible_carbon_atoms.remove(atom_id)
                for neighbor in neighbors:
                    if neighbor in self.possible_carbon_atoms:
                        self.possible_carbon_atoms.remove(neighbor)

            elif nitrogen_species in {
                NitrogenSpecies.PYRIDINIC_1,
                NitrogenSpecies.PYRIDINIC_2,
                NitrogenSpecies.PYRIDINIC_3,
            }:
                # Add a flag to control the flow
                invalid_neighbor_found = False
                for neighbor in neighbors:
                    if neighbor not in self.possible_carbon_atoms:
                        invalid_neighbor_found = True
                        break  # Exit the for loop as soon as an invalid neighbor is found

                if invalid_neighbor_found:
                    continue  # Skip the rest of the while loop iteration and proceed to the next one

                # Remove the selected atom from the graph
                self.graph.remove_node(atom_id)

                # Find the specific cycle that includes all neighbors that should be removed from the possible
                # carbon atoms
                nodes_to_exclude = self.find_min_cycle_including_neighbors(neighbors)
                # Remove the selected atom and the atoms in the cycle from the list of potential carbon atoms
                self.possible_carbon_atoms.remove(atom_id)
                # invalid_positions.add(atom_id)
                for node in nodes_to_exclude:
                    if node in self.possible_carbon_atoms:
                        self.possible_carbon_atoms.remove(node)

                if nitrogen_species == NitrogenSpecies.PYRIDINIC_1:
                    # Replace 1 carbon atom to form pyridinic nitrogen structure
                    selected_neighbor = random.choice(neighbors)
                    self.graph.nodes[selected_neighbor]["element"] = "N"
                    self.graph.nodes[selected_neighbor]["nitrogen_species"] = nitrogen_species
                    # Add the selected atom to the list of chosen atoms
                    chosen_atoms.append(selected_neighbor)

                    # Remove the selected neighbor from the list of neighbors
                    neighbors.remove(selected_neighbor)

                    # Insert a new binding between the `neighbors_of_neighbor`
                    self.graph.add_edge(neighbors[0], neighbors[1], bond_length=self.bond_distance)

                elif nitrogen_species == NitrogenSpecies.PYRIDINIC_2:
                    # Replace 2 carbon atoms to form pyridinic nitrogen structure
                    selected_neighbors = random.sample(neighbors, 2)
                    for neighbor in selected_neighbors:
                        self.graph.nodes[neighbor]["element"] = "N"
                        self.graph.nodes[neighbor]["nitrogen_species"] = nitrogen_species
                        # Add the neighbor to the list of chosen atoms
                        chosen_atoms.append(neighbor)

                elif nitrogen_species == NitrogenSpecies.PYRIDINIC_3:
                    # Replace 3 carbon atoms to form pyridinic nitrogen structure
                    for neighbor in neighbors:
                        self.graph.nodes[neighbor]["element"] = "N"
                        self.graph.nodes[neighbor]["nitrogen_species"] = nitrogen_species
                        # Add the neighbor to the list of chosen atoms
                        chosen_atoms.append(neighbor)

            elif nitrogen_species == NitrogenSpecies.PYRIDINIC_4:

                # ToDo: Die folgenden Zeilen sind nur zu Testzwecken und müssen dringend wieder entfernt werden!
                atom_id = 45
                reference_node_position = self.graph.nodes[atom_id]["position"]
                neighbors = self.get_neighbors_via_edges(atom_id)

                # Iterate over the neighbors of the selected atom to find a direct neighbor that has a valid position
                selected_neighbor = None
                temp_neighbors = neighbors.copy()
                while temp_neighbors and not selected_neighbor:
                    # Find a direct neighbor that also needs to be removed randomly
                    temp_neighbor = random.choice(temp_neighbors)
                    temp_neighbors.remove(temp_neighbor)

                    # Check if the selected neighbor is a valid doping position
                    if temp_neighbor not in self.possible_carbon_atoms or not self._valid_doping_position(
                        nitrogen_species, atom_id, temp_neighbor
                    ):
                        continue

                    # Valid neighbor found
                    selected_neighbor = temp_neighbor

                if not selected_neighbor:
                    # No valid neighbor found
                    continue

                # Remove the selected atom from the graph
                self.graph.remove_node(atom_id)
                # Remove the selected neighbor from the list of neighbors
                neighbors.remove(selected_neighbor)
                # Get direct neighbors of the selected neighbor excluding the selected atom
                neighbors += self.get_neighbors_via_edges(selected_neighbor)
                # Remove the selected neighbor from the graph
                self.graph.remove_node(selected_neighbor)

                # Find the specific cycle that includes all neighbors that should be removed from the possible
                # carbon atoms
                nodes_to_exclude = self.find_min_cycle_including_neighbors(neighbors)
                # Remove the selected atom and its neighbor as well as the atoms in the cycle from the list of
                # potential carbon atoms
                self.possible_carbon_atoms.remove(atom_id)
                self.possible_carbon_atoms.remove(selected_neighbor)
                for node in nodes_to_exclude:
                    if node in self.possible_carbon_atoms:
                        self.possible_carbon_atoms.remove(node)

                # Replace 4 carbon atoms to form pyridinic nitrogen structure
                for neighbor in neighbors:
                    self.graph.nodes[neighbor]["element"] = "N"
                    self.graph.nodes[neighbor]["nitrogen_species"] = nitrogen_species
                    # Add the neighbor to the list of chosen atoms
                    chosen_atoms.append(neighbor)

                # Adjust the positions of atoms in the cycle to optimize the structure
                self._adjust_atom_positions(nodes_to_exclude, reference_node_position, nitrogen_species)

        # Warn if not all requested nitrogen atoms could be placed
        if len(chosen_atoms) < num_nitrogen:
            warning_message = (
                f"\nWarning: Only {len(chosen_atoms)} nitrogen atoms of species {nitrogen_species} could "
                f"be placed due to proximity constraints."
            )
            print_warning(warning_message)

        return len(chosen_atoms)

    # def _adjust_atom_positions(self, cycle: List[int]):
    #     """
    #     Adjust the positions of atoms in a cycle to optimize the structure.
    #
    #     Parameters
    #     ----------
    #     cycle : List[int]
    #         The list of atom IDs forming the cycle.
    #
    #     Notes
    #     -----
    #     This method adjusts the positions of atoms in a cycle to optimize the structure.
    #     """
    #     # Create a subgraph including all nodes in the cycle
    #     subgraph = self.graph.subgraph(cycle).copy()
    #
    #     # Add edges to neighbors outside the cycle
    #     for node in cycle:
    #         for neighbor in self.graph.neighbors(node):
    #             if neighbor not in cycle:
    #                 subgraph.add_edge(node, neighbor, **self.graph.get_edge_data(node, neighbor))
    #
    #     # Define bond lengths for specific edges
    #     bond_lengths = {
    #         (97, 112): 1.34,
    #         (112, 113): 1.45,
    #         (113, 114): 1.45,
    #         (114, 115): 1.34,
    #         (115, 116): 1.32,
    #         (116, 101): 1.47,
    #         (101, 100): 1.32,
    #         (100, 85): 1.34,
    #         (85, 84): 1.45,
    #         (84, 83): 1.45,
    #         (83, 82): 1.34,
    #         (82, 81): 1.32,
    #         (81, 96): 1.47,
    #         (96, 97): 1.32,
    #         (84, 69): 1.428,
    #         (83, 66): 1.431,
    #         (81, 80): 1.423,
    #         (96, 111): 1.423,
    #         (112, 127): 1.431,
    #         (113, 0): 1.428,
    #         (114, 3): 1.431,
    #         (116, 117): 1.423,
    #         (101, 102): 1.423,
    #         (85, 86): 1.431,
    #     }
    #
    #     # Define the angles (in degrees) between consecutive bonds in the cycle
    #     angles = {
    #         (97, 112, 113): 120.26,
    #         (112, 113, 114): 122.92,
    #         (113, 114, 115): 120.26,
    #         (114, 115, 116): 121.02,
    #         (115, 116, 101): 119.3,
    #         (116, 101, 100): 119.3,
    #         (101, 100, 85): 121.02,
    #         (100, 85, 84): 120.26,
    #         (85, 84, 83): 122.91,
    #         (84, 83, 82): 120.26,
    #         (83, 82, 81): 121.02,
    #         (82, 81, 96): 119.3,
    #         (81, 96, 97): 119.3,
    #         (96, 97, 112): 121.02,
    #     }
    #
    #     # Initial positions (use existing positions if available)
    #     positions = {node: self.graph.nodes[node]["position"] for node in subgraph.nodes}
    #
    #     # Adjust positions for periodic boundary conditions
    #     positions_adjusted = self._adjust_for_periodic_boundaries(positions, subgraph)
    #
    #     # Sort nodes so that cycle nodes come first, followed by non-cycle nodes
    #     sorted_nodes = cycle + [node for node in subgraph.nodes if node not in cycle]
    #
    #     # Flatten initial positions for optimization, ensuring cycle order is preserved
    #     x0 = np.array([coord for node in sorted_nodes for coord in positions_adjusted[node]])
    #
    #     def bond_energy(x):
    #         """
    #         Calculate the bond energy for the given positions.
    #
    #         Parameters
    #         ----------
    #         x : ndarray
    #             Flattened array of positions of all atoms in the cycle.
    #
    #         Returns
    #         -------
    #         energy : float
    #             The total bond energy.
    #         """
    #         energy = 0.0
    #         for (i, j), length in bond_lengths.items():
    #             # Extract the coordinates of atoms i and j from the flattened array
    #             xi, yi = x[2 * sorted_nodes.index(i)], x[2 * sorted_nodes.index(i) + 1]
    #             xj, yj = x[2 * sorted_nodes.index(j)], x[2 * sorted_nodes.index(j) + 1]
    #
    #             # Calculate the distance between the atoms
    #             dist = np.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)
    #             # Calculate the energy contribution for this bond
    #             energy += 0.5 * ((dist - length) ** 2)
    #         return energy
    #
    #     def angle_energy(x):
    #         """
    #         Calculate the angle energy for the given positions.
    #
    #         Parameters
    #         ----------
    #         x : ndarray
    #             Flattened array of positions of all atoms in the cycle.
    #
    #         Returns
    #         -------
    #         energy : float
    #             The total angle energy.
    #         """
    #         energy = 0.0
    #         for (i, j, k), angle in angles.items():
    #             # Extract the coordinates of atoms i, j, and k from the flattened array
    #             xi, yi = x[2 * cycle.index(i)], x[2 * cycle.index(i) + 1]
    #             xj, yj = x[2 * cycle.index(j)], x[2 * cycle.index(j) + 1]
    #             xk, yk = x[2 * cycle.index(k)], x[2 * cycle.index(k) + 1]
    #             # Calculate vectors from j to i and from j to k
    #             v1 = np.array([xi - xj, yi - yj])
    #             v2 = np.array([xk - xj, yk - yj])
    #             # Calculate the cosine of the angle between the vectors
    #             cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    #             # Calculate the actual angle in radians
    #             theta = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    #             # Calculate the energy contribution for this angle
    #             energy += 0.5 * ((theta - np.radians(angle)) ** 2)
    #         return energy
    #
    #     def total_energy(x):
    #         """
    #         Calculate the total energy (bond energy + angle energy).
    #
    #         Parameters
    #         ----------
    #         x : ndarray
    #             Flattened array of positions of all atoms in the cycle.
    #
    #         Returns
    #         -------
    #         energy : float
    #             The total energy.
    #         """
    #         return bond_energy(x) + angle_energy(x)
    #
    #     # Optimize positions to minimize energy
    #     result = minimize(total_energy, x0, method="L-BFGS-B")
    #
    #     # Reshape the 1D array result to 2D coordinates and update positions in the graph
    #     optimized_positions = result.x.reshape(-1, 2)
    #
    #     # Calculate the displacement vectors for nodes not in the cycle
    #     displacement_vectors = {}
    #     for idx, node in enumerate(sorted_nodes[len(cycle) :]):
    #         original_idx = 2 * (len(cycle) + idx)
    #         original_position = x0[original_idx], x0[original_idx + 1]
    #         optimized_position = optimized_positions[len(cycle) + idx]
    #         displacement_vectors[node] = np.array(optimized_position) - np.array(original_position)
    #
    #     # Update positions in the original graph
    #     for idx, node in enumerate(sorted_nodes):
    #         if node in cycle:
    #             self.graph.nodes[node]["position"] = optimized_positions[idx]
    #         else:
    #             adjusted_position = np.array(self.graph.nodes[node]["position"]) + displacement_vectors[node]
    #             self.graph.nodes[node]["position"] = (adjusted_position[0], adjusted_position[1])
    #
    #     # ToDo: bond_distance edge attribute muss noch angepasst werden

    def _adjust_atom_positions(self, cycle: List[int], reference_position: Tuple[int, int], species: NitrogenSpecies):
        """
        Adjust the positions of atoms in a cycle to optimize the structure.

        Parameters
        ----------
        cycle : List[int]
            The list of atom IDs forming the cycle.
        reference_position: Tuple[int, int]
            The reference position of the atom id that was used to find the cycle.
        species: NitrogenSpecies
            The nitrogen doping species that was inserted.

        Notes
        -----
        This method adjusts the positions of atoms in a cycle to optimize the structure.
        """
        # Create a subgraph including all nodes in the cycle
        subgraph = self.graph.subgraph(cycle).copy()

        # Get species properties for the given cycle
        properties = self.species_properties[species]

        # Combine half_bond_lengths and half_angles to full lists
        bond_lengths = properties.half_bond_lengths + properties.half_bond_lengths
        angles = properties.half_angles + properties.half_angles

        # Initial positions (use existing positions if available)
        positions = {node: self.graph.nodes[node]["position"] for node in subgraph.nodes}

        # Adjust positions for periodic boundary conditions
        positions_adjusted = self._adjust_for_periodic_boundaries(positions, subgraph, reference_position)

        # Initialize a starting node to ensure a consistent iteration order through the cycle, matching the bond lengths
        # and angles correctly
        start_node = None
        if species == NitrogenSpecies.PYRIDINIC_4:
            # Find the starting node that has no "N" neighbors within the cycle and is not "N" itself
            for node in cycle:
                # Skip the node if it is already a nitrogen atom
                if self.graph.nodes[node]["element"] == "N":
                    continue
                # Get the neighbors of the current node
                neighbors = self.get_neighbors_via_edges(node)
                # Check if none of the neighbors of the node are nitrogen atoms, provided the neighbor is within the
                # cycle
                if all(self.graph.nodes[neighbor]["element"] != "N" for neighbor in neighbors if neighbor in cycle):
                    # If the current node meets all conditions, set it as the start node
                    start_node = node
                    break
        # Raise an error if no suitable start node is found
        if start_node is None:
            raise ValueError("No suitable starting node found in the cycle.")

        # Order the cycle nodes starting from the identified start_node
        ordered_cycle = self._order_cycle_nodes(cycle, start_node)

        # Flatten initial positions for optimization, ensuring cycle order is preserved
        x0 = np.array([coord for node in ordered_cycle for coord in positions_adjusted[node]])

        def bond_energy(x):
            """
            Calculate the bond energy for the given positions.

            Parameters
            ----------
            x : ndarray
                Flattened array of positions of all atoms in the cycle.

            Returns
            -------
            energy : float
                The total bond energy.
            """
            energy = 0.0
            for (i, j), length in zip(zip(ordered_cycle, ordered_cycle[1:]), bond_lengths):
                # Extract the coordinates of atoms i and j from the flattened array
                xi, yi = x[2 * ordered_cycle.index(i)], x[2 * ordered_cycle.index(i) + 1]
                xj, yj = x[2 * ordered_cycle.index(j)], x[2 * ordered_cycle.index(j) + 1]

                # Calculate the distance between the atoms
                dist = np.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)
                # Calculate the energy contribution for this bond
                energy += 0.5 * ((dist - length) ** 2)
            return energy

        def angle_energy(x):
            """
            Calculate the angle energy for the given positions.

            Parameters
            ----------
            x : ndarray
                Flattened array of positions of all atoms in the cycle.

            Returns
            -------
            energy : float
                The total angle energy.
            """
            energy = 0.0
            for (i, j, k), angle in zip(zip(ordered_cycle, ordered_cycle[1:], ordered_cycle[2:]), angles):
                # Extract the coordinates of atoms i, j, and k from the flattened array
                xi, yi = x[2 * ordered_cycle.index(i)], x[2 * ordered_cycle.index(i) + 1]
                xj, yj = x[2 * ordered_cycle.index(j)], x[2 * ordered_cycle.index(j) + 1]
                xk, yk = x[2 * ordered_cycle.index(k)], x[2 * ordered_cycle.index(k) + 1]
                # Calculate vectors from j to i and from j to k
                v1 = np.array([xi - xj, yi - yj])
                v2 = np.array([xk - xj, yk - yj])
                # Calculate the cosine of the angle between the vectors
                cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                # Calculate the actual angle in radians
                theta = np.arccos(np.clip(cos_theta, -1.0, 1.0))
                # Calculate the energy contribution for this angle
                energy += 0.5 * ((theta - np.radians(angle)) ** 2)
            return energy

        def total_energy(x):
            """
            Calculate the total energy (bond energy + angle energy).

            Parameters
            ----------
            x : ndarray
                Flattened array of positions of all atoms in the cycle.

            Returns
            -------
            energy : float
                The total energy.
            """
            return bond_energy(x) + angle_energy(x)

        # Optimize positions to minimize energy
        result = minimize(total_energy, x0, method="L-BFGS-B")

        # Reshape the 1D array result to 2D coordinates and update positions in the graph
        optimized_positions = result.x.reshape(-1, 2)

        # Calculate the displacement vectors for nodes not in the cycle
        displacement_vectors = {}
        for idx, node in enumerate(ordered_cycle):
            original_position = x0[2 * idx], x0[2 * idx + 1]
            optimized_position = optimized_positions[idx]
            displacement_vectors[node] = np.array(optimized_position) - np.array(original_position)

        # Update positions in the original graph
        for idx, node in enumerate(ordered_cycle):
            adjusted_position = np.array(self.graph.nodes[node]["position"]) + displacement_vectors[node]
            self.graph.nodes[node]["position"] = (adjusted_position[0], adjusted_position[1])

        # ToDo: bond_distance edge attribute muss noch angepasst werden

    # def _adjust_for_periodic_boundaries(self, positions, subgraph):
    #     """
    #     Adjust positions for periodic boundary conditions.
    #
    #     Parameters
    #     ----------
    #     positions : dict
    #         Dictionary of positions of atoms.
    #     subgraph : nx.Graph
    #         The subgraph containing the cycle.
    #
    #     Returns
    #     -------
    #     dict
    #         Dictionary of adjusted positions.
    #     """
    #     adjusted_positions = positions.copy()
    #     for edge in subgraph.edges(data=True):
    #         if edge[2].get("periodic"):
    #             node1, node2 = edge[0], edge[1]
    #             pos1, pos2 = np.array(positions[node1]), np.array(positions[node2])
    #             diff = pos2 - pos1
    #             if (
    #                 np.linalg.norm(diff)
    #                 > self.bond_distance
    #                 # ToDo: Hier muss wahrscheinlich noch Fehlertoleranz hinzugefügt werden, da sich die
    #                 # Bindungslängen geringfügig ändern
    #             ):
    #                 # Adjust the position for periodic boundary
    #                 if abs(diff[0]) > self.bond_distance:
    #                     pos2[0] = pos1[0] - np.sign(diff[0]) * self.bond_distance
    #                 if abs(diff[1]) > self.bond_distance:
    #                     pos2[1] = pos1[1] - np.sign(diff[1]) * self.cc_y_distance
    #                 adjusted_positions[node2] = (pos2[0], pos2[1])
    #     return adjusted_positions

    # def _adjust_for_periodic_boundaries(self, positions, subgraph, reference_position):
    #     """
    #     Adjust positions for periodic boundary conditions.
    #
    #     Parameters
    #     ----------
    #     positions : dict
    #         Dictionary of positions of atoms.
    #     subgraph : nx.Graph
    #         The subgraph containing the cycle.
    #     reference_position : tuple
    #         The position of the reference node before deletion.
    #
    #     Returns
    #     -------
    #     dict
    #         Dictionary of adjusted positions.
    #     """
    #     adjusted_positions = positions.copy()
    #     adjusted_nodes = set()
    #     nodes_to_adjust = set()
    #
    #     # Step 1: Adjust positions for direct periodic boundaries
    #     for edge in subgraph.edges(data=True):
    #         if edge[2].get("periodic"):
    #             node1, node2 = edge[0], edge[1]
    #             pos1, pos2 = np.array(adjusted_positions[node1]), np.array(adjusted_positions[node2])
    #             diff = pos2 - pos1
    #
    #             if np.linalg.norm(diff) > self.bond_distance:
    #                 if abs(diff[0]) > self.bond_distance:
    #                     pos2[0] = pos1[0] - np.sign(diff[0]) * self.bond_distance
    #                 if abs(diff[1]) > self.bond_distance:
    #                     pos2[1] = pos1[1] - np.sign(diff[1]) * self.cc_y_distance
    #
    #                 adjusted_positions[node2] = (pos2[0], pos2[1])
    #                 adjusted_nodes.add(node2)
    #
    #     # Step 2: Find nodes that need to be adjusted due to indirect periodic boundaries
    #     for node in adjusted_nodes:
    #         for neighbor in subgraph.neighbors(node):
    #             if neighbor not in adjusted_positions:
    #                 neighbor_pos = np.array(self.graph.nodes[neighbor]["position"])
    #                 node_pos = np.array(adjusted_positions[node])
    #                 diff = neighbor_pos - node_pos
    #
    #                 if abs(diff[0]) > self.bond_distance:
    #                     nodes_to_adjust.add(neighbor)
    #                 if abs(diff[1]) > self.bond_distance:
    #                     nodes_to_adjust.add(neighbor)
    #
    #     # Step 3: Recursively adjust connected nodes within the subgraph
    #     for node in nodes_to_adjust:
    #         for neighbor in self.graph.neighbors(node):
    #             if neighbor not in adjusted_positions:
    #                 neighbor_pos = np.array(self.graph.nodes[neighbor]["position"])
    #                 node_pos = np.array(adjusted_positions[node])
    #                 diff = neighbor_pos - node_pos
    #
    #                 if abs(diff[0]) > self.bond_distance:
    #                     neighbor_pos[0] = node_pos[0] + np.sign(diff[0]) * self.bond_distance
    #                 if abs(diff[1]) > self.bond_distance:
    #                     neighbor_pos[1] = node_pos[1] + np.sign(diff[1]) * self.cc_y_distance
    #
    #                 adjusted_positions[neighbor] = (neighbor_pos[0], neighbor_pos[1])
    #
    #     return adjusted_positions

    def _adjust_for_periodic_boundaries(self, positions, subgraph, reference_position):
        """
        Adjust positions for periodic boundary conditions.

        Parameters
        ----------
        positions : dict
            Dictionary of positions of atoms.
        subgraph : nx.Graph
            The subgraph containing the cycle.
        reference_position : tuple
            The position of the reference node before deletion.

        Returns
        -------
        dict
            Dictionary of adjusted positions.
        """
        adjusted_positions = positions.copy()
        adjusted_nodes = set()
        nodes_to_adjust = set()

        # Step 1: Adjust positions for direct periodic boundaries
        for edge in subgraph.edges(data=True):
            if edge[2].get("periodic"):
                node1, node2 = edge[0], edge[1]

                # Ensure node1 is always the node with the smaller ID
                if node1 > node2:
                    node1, node2 = node2, node1

                pos1, pos2 = np.array(adjusted_positions[node1]), np.array(adjusted_positions[node2])
                boundary = self.determine_boundary(reference_position, pos1, pos2)

                if boundary == "left":
                    adjusted_positions[node2] = self.adjust_position(pos1, pos2, boundary)
                    adjusted_nodes.add(node2)
                elif boundary == "right":
                    adjusted_positions[node1] = self.adjust_position(pos2, pos1, boundary)
                    adjusted_nodes.add(node1)
                elif boundary == "top":
                    adjusted_positions[node1] = self.adjust_position(pos2, pos1, boundary)
                    adjusted_nodes.add(node1)
                elif boundary == "bottom":
                    adjusted_positions[node2] = self.adjust_position(pos1, pos2, boundary)
                    adjusted_nodes.add(node2)

        # Step 2: Find nodes that need to be adjusted due to indirect periodic boundaries via a depth-first search
        def dfs(node, visited):
            stack = [node]
            while stack:
                current_node = stack.pop()
                if current_node not in visited:
                    visited.add(current_node)
                    for neighbor in subgraph.neighbors(current_node):
                        if neighbor not in visited and not subgraph.edges[current_node, neighbor].get("periodic"):
                            stack.append(neighbor)
                            if neighbor not in adjusted_nodes:
                                nodes_to_adjust.add(neighbor)

        visited = set()
        for node in adjusted_nodes:
            if node not in visited:
                dfs(node, visited)

        # Step 3: Adjust the positions of the nodes in nodes_to_adjust
        for node in nodes_to_adjust:
            node_pos = np.array(adjusted_positions[node])
            for neighbor in subgraph.neighbors(node):
                neighbor_pos = adjusted_positions[neighbor]
                diff = node_pos - neighbor_pos
                if abs(diff[0]) > self.bond_distance:
                    node_pos[0] = neighbor_pos[0] - np.sign(diff[0]) * self.cc_x_distance
                if abs(diff[1]) > self.bond_distance:
                    node_pos[1] = neighbor_pos[1] - np.sign(diff[1]) * self.bond_distance
                adjusted_positions[node] = (node_pos[0], node_pos[1])

        return adjusted_positions

    def adjust_position(self, pos1, pos2, boundary):
        diff = pos2 - pos1
        if boundary in ["left", "right"] and abs(diff[0]) > self.bond_distance:
            pos2[0] = pos1[0] - np.sign(diff[0]) * self.bond_distance
        if boundary in ["top", "bottom"] and abs(diff[1]) > self.cc_y_distance:
            pos2[1] = pos1[1] - np.sign(diff[1]) * self.cc_y_distance
        return pos2

    def determine_boundary(self, reference_position, pos1, pos2):
        left, right = (pos1, pos2) if pos2[0] > pos1[0] else (pos2, pos1)
        down, up = (pos1, pos2) if pos2[1] > pos1[1] else (pos2, pos1)

        x_diff = abs(reference_position[0] - left[0]) - abs(reference_position[0] - right[0])
        y_diff = abs(reference_position[1] - down[1]) - abs(reference_position[1] - up[1])

        if abs(x_diff) > abs(y_diff):
            if x_diff < 0:
                return "left"
            else:
                return "right"
        else:
            if y_diff < 0:
                return "bottom"
            else:
                return "top"

    def _order_cycle_nodes(self, cycle: List[int], start_node: int) -> List[int]:
        """
        Order the nodes in the cycle starting from the given start_node.

        Parameters
        ----------
        cycle : List[int]
            The list of atom IDs forming the cycle.
        start_node : int
            The starting node for the cycle.

        Returns
        -------
        List[int]
            The ordered list of atom IDs forming the cycle.
        """
        # Initialize the list to store the ordered cycle and a set to track visited nodes
        ordered_cycle = []
        current_node = start_node
        visited = set()

        # Continue ordering nodes until all nodes in the cycle are included
        while len(ordered_cycle) < len(cycle):
            # Add the current node to the ordered list and mark it as visited
            ordered_cycle.append(current_node)
            visited.add(current_node)

            # Find the neighbors of the current node that are in the cycle and not yet visited
            neighbors = [node for node in self.graph.neighbors(current_node) if node in cycle and node not in visited]

            # If there are unvisited neighbors, move to the next neighbor; otherwise, break the loop
            if neighbors:
                current_node = neighbors[0]
            else:
                break

        return ordered_cycle

    def _valid_doping_position(
        self, nitrogen_species: NitrogenSpecies, atom_id: int, neighbor_id: Optional[int] = None
    ) -> bool:

        # Check the proximity constraints
        if nitrogen_species == NitrogenSpecies.GRAPHITIC:
            # Get the direct neighbors of the selected atom
            neighbors = self.get_neighbors_via_edges(atom_id)
            neighbor_elements = [
                (self.graph.nodes[neighbor]["element"], self.graph.nodes[neighbor].get("nitrogen_species"))
                for neighbor in neighbors
            ]
            return all(elem != "N" for elem, _ in neighbor_elements)

        elif nitrogen_species in {
            NitrogenSpecies.PYRIDINIC_1,
            NitrogenSpecies.PYRIDINIC_2,
            NitrogenSpecies.PYRIDINIC_3,
        }:
            neighbors_len_3 = self.get_neighbors_via_edges(atom_id, depth=3, inclusive=True)
            return all(elem != "N" for elem in [self.graph.nodes[neighbor]["element"] for neighbor in neighbors_len_3])

        elif nitrogen_species == NitrogenSpecies.PYRIDINIC_4:
            neighbors_len_3 = self.get_neighbors_via_edges(atom_id, depth=3, inclusive=True)
            if neighbor_id:
                neighbors_len_3 += self.get_neighbors_via_edges(neighbor_id, depth=3, inclusive=True)
            return all(elem != "N" for elem in [self.graph.nodes[neighbor]["element"] for neighbor in neighbors_len_3])

        return False

    def find_min_cycle_including_neighbors(self, neighbors: List[int]):
        """
        Find the shortest cycle in the graph that includes all the given neighbors.

        This method uses an iterative approach to expand the subgraph starting from the given neighbors. In each
        iteration, it expands the subgraph by adding edges of the current nodes until a cycle containing all neighbors
        is found.
        The cycle detection is done using the `cycle_basis` method, which is efficient for small subgraphs that are
        incrementally expanded.

        Parameters
        ----------
        neighbors : List[int]
            A list of nodes that should be included in the cycle.

        Returns
        -------
        List[int]
            The shortest cycle that includes all the given neighbors, if such a cycle exists. Otherwise, an empty list.
        """
        # Initialize the subgraph with the neighbors and their edges
        subgraph = nx.Graph()
        subgraph.add_nodes_from(neighbors)

        # Add edges from each neighbor to the subgraph
        for node in neighbors:
            subgraph.add_edges_from(self.graph.edges(node))

        # Keep track of visited edges to avoid unwanted cycles
        visited_edges: Set[Tuple[int, int]] = set(subgraph.edges)

        # Expand the subgraph until the cycle is found
        while True:
            # Find all cycles in the current subgraph
            cycles: List[List[int]] = list(nx.cycle_basis(subgraph))
            for cycle in cycles:
                # Check if the current cycle includes all the neighbors
                if all(neighbor in cycle for neighbor in neighbors):
                    return cycle

            # If no cycle is found, expand the subgraph by adding neighbors of the current subgraph
            new_edges: Set[Tuple[int, int]] = set()
            for node in subgraph.nodes:
                new_edges.update(self.graph.edges(node))

            # Only add new edges that haven't been visited
            new_edges.difference_update(visited_edges)
            if not new_edges:
                return []

            # Add the new edges to the subgraph and update the visited edges
            subgraph.add_edges_from(new_edges)
            visited_edges.update(new_edges)

    def get_neighbors_within_distance(self, atom_id: int, distance: float) -> List[int]:
        """
        Find all neighbors within a given distance from the specified atom.

        Parameters
        ----------
        atom_id : int
            The ID of the atom (node) from which distances are measured.
        distance : float
            The maximum distance to search for neighbors.

        Returns
        -------
        List[int]
            A list of IDs representing the neighbors within the given distance from the source node.
        """
        atom_position = self.graph.nodes[atom_id]["position"]
        indices = self._kdtree.query_ball_point(atom_position, distance)
        return [list(self.graph.nodes)[index] for index in indices]

    def get_neighbors_via_edges(self, atom_id: int, depth: int = 1, inclusive: bool = False) -> List[int]:
        """
        Get connected neighbors of a given atom up to a certain depth.

        Parameters
        ----------
        atom_id : int
            The ID of the atom (node) whose neighbors are to be found.
        depth : int, optional
            The depth up to which neighbors are to be found (default is 1).
        inclusive : bool, optional
            If True, return all neighbors up to the specified depth. If False, return only the neighbors
            at the exact specified depth (default is False).

        Returns
        -------
        List[int]
            A list of IDs representing the neighbors of the specified atom up to the given depth.

        Notes
        -----
        - If `depth` is 1, this method uses the `neighbors` function from networkx to find the immediate neighbors.
        - If `depth` is greater than 1:
          The function uses `nx.single_source_shortest_path_length(self.graph, atom_id, cutoff=depth)` from networkx.
          This function computes the shortest path lengths from the source node (atom_id) to all other nodes in the
          graph,up to the specified cutoff depth.

          - If `inclusive` is True, the function returns all neighbors up to the specified depth, meaning it includes
            neighbors at depth 1, 2, ..., up to the given depth.
          - If `inclusive` is False, the function returns only the neighbors at the exact specified depth.
        """

        if depth == 1:
            # Get immediate neighbors (directly connected nodes)
            return list(self.graph.neighbors(atom_id))
        else:
            # Get neighbors up to the specified depth using shortest path lengths
            paths = nx.single_source_shortest_path_length(self.graph, atom_id, cutoff=depth)
            if inclusive:
                # Include all neighbors up to the specified depth
                return [node for node in paths.keys() if node != atom_id]  # Exclude the atom itself (depth 0)
            else:
                # Include only neighbors at the exact specified depth
                return [node for node, length in paths.items() if length == depth]

    def get_neighbors_paths(self, atom_id: int, depth: int = 1) -> List[Tuple[int, int]]:
        """
        Get edges of paths to connected neighbors up to a certain depth.

        Parameters
        ----------
        atom_id : int
            The ID of the atom (node) whose neighbors' paths are to be found.
        depth : int, optional
            The depth up to which neighbors' paths are to be found (default is 1).

        Returns
        -------
        List[Tuple[int, int]]
            A list of tuples representing the edges of paths to neighbors up to the given depth.

        Notes
        -----
        This method uses the `single_source_shortest_path` function from networkx to find
        all paths up to the specified depth and then extracts the edges from these paths.
        """
        paths = nx.single_source_shortest_path(self.graph, atom_id, cutoff=depth)
        edges = []
        for path in paths.values():
            edges.extend([(path[i], path[i + 1]) for i in range(len(path) - 1)])
        return edges

    def get_shortest_path_length(self, source: int, target: int) -> float:
        """
        Get the shortest path length between two connected atoms based on bond lengths.

        Parameters
        ----------
        source : int
            The ID of the source atom (node).
        target : int
            The ID of the target atom (node).

        Returns
        -------
        float
            The shortest path length between the source and target atoms.

        Notes
        -----
        This method uses the Dijkstra algorithm implemented in networkx to find the shortest path length.
        """
        return nx.dijkstra_path_length(self.graph, source, target, weight="bond_length")

    def get_shortest_path(self, source: int, target: int) -> List[int]:
        """
        Get the shortest path between two connected atoms based on bond lengths.

        Parameters
        ----------
        source : int
            The ID of the source atom (node).
        target : int
            The ID of the target atom (node).

        Returns
        -------
        List[int]
            A list of IDs representing the nodes in the shortest path from the source to the target atom.

        Notes
        -----
        This method uses the Dijkstra algorithm implemented in networkx to find the shortest path.
        """
        return nx.dijkstra_path(self.graph, source, target, weight="bond_length")

    def get_color(self, element: str, nitrogen_species: NitrogenSpecies = None) -> str:
        """
        Get the color based on the element and type of nitrogen.

        Parameters
        ----------
        element : str
            The chemical element of the atom (e.g., 'C' for carbon, 'N' for nitrogen).
        nitrogen_species : NitrogenSpecies, optional
            The type of nitrogen doping (default is None).

        Returns
        -------
        str
            The color associated with the element and nitrogen species.

        Notes
        -----
        The color mapping is defined for different elements and nitrogen species to visually
        distinguish them in plots.
        """
        colors = {"C": "black"}
        nitrogen_colors = {
            # NitrogenSpecies.PYRIDINIC: "blue",
            NitrogenSpecies.PYRIDINIC_1: "purple",
            NitrogenSpecies.PYRIDINIC_2: "orange",
            NitrogenSpecies.PYRIDINIC_3: "green",
            NitrogenSpecies.PYRIDINIC_4: "blue",
            NitrogenSpecies.GRAPHITIC: "red",
            # NitrogenSpecies.PYRROLIC: "cyan",
            # NitrogenSpecies.PYRAZOLE: "green",
        }
        if nitrogen_species in nitrogen_colors:
            return nitrogen_colors[nitrogen_species]
        return colors.get(element, "pink")

    def plot_graphene(self, with_labels: bool = False, visualize_periodic_bonds: bool = True):
        """
        Plot the graphene structure using networkx and matplotlib.

        Parameters
        ----------
        with_labels : bool, optional
            Whether to display labels on the nodes (default is False).
        visualize_periodic_bonds : bool, optional
            Whether to visualize periodic boundary condition edges (default is True).

        Notes
        -----
        This method visualizes the graphene structure, optionally with labels indicating the
        element type and node ID. Nodes are colored based on their element type and nitrogen species.
        Periodic boundary condition edges are shown with dashed lines if visualize_periodic_bonds is True.
        """
        # Get positions and elements of nodes
        pos = nx.get_node_attributes(self.graph, "position")
        elements = nx.get_node_attributes(self.graph, "element")

        # Determine colors for nodes, considering nitrogen species if present
        colors = [
            self.get_color(elements[node], self.graph.nodes[node].get("nitrogen_species"))
            for node in self.graph.nodes()
        ]

        # Separate periodic edges and regular edges
        regular_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if not d.get("periodic")]
        periodic_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get("periodic")]

        # Initialize plot
        plt.figure(figsize=(12, 12))

        # Draw the regular edges
        nx.draw(self.graph, pos, edgelist=regular_edges, node_color=colors, node_size=200, with_labels=False)

        # Draw periodic edges with dashed lines if visualize_periodic_bonds is True
        if visualize_periodic_bonds:
            nx.draw_networkx_edges(self.graph, pos, edgelist=periodic_edges, style="dashed", edge_color="gray")

        # Add legend
        unique_colors = set(colors)
        legend_elements = []
        for species in NitrogenSpecies:
            color = self.get_color("N", species)
            if color in unique_colors:
                legend_elements.append(
                    plt.Line2D(
                        [0], [0], marker="o", color="w", label=species.value, markersize=10, markerfacecolor=color
                    )
                )

        plt.legend(handles=legend_elements, title="Nitrogen Doping Species")

        # Add labels if specified
        if with_labels:
            labels = {node: f"{elements[node]}{node}" for node in self.graph.nodes()}
            nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=10, font_color="cyan", font_weight="bold")

        # Show plot
        plt.show()

    def plot_graphene_with_path(self, path: List[int], visualize_periodic_bonds: bool = True):
        """
        Plot the graphene structure with a highlighted path.

        This method plots the entire graphene structure and highlights a specific path
        between two nodes using a different color.

        Parameters
        ----------
        path : List[int]
            A list of node IDs representing the path to be highlighted.
        visualize_periodic_bonds : bool, optional
            Whether to visualize periodic boundary condition edges (default is True).

        Notes
        -----
        The path is highlighted in yellow, while the rest of the graphene structure
        is displayed in its default colors. Periodic boundary condition edges are
        shown with dashed lines if visualize_periodic_bonds is True.
        """
        # Get positions and elements of nodes
        pos = nx.get_node_attributes(self.graph, "position")
        elements = nx.get_node_attributes(self.graph, "element")

        # Determine colors for nodes, considering nitrogen species if present
        colors = [
            self.get_color(elements[node], self.graph.nodes[node].get("nitrogen_species"))
            for node in self.graph.nodes()
        ]
        labels = {node: f"{elements[node]}{node}" for node in self.graph.nodes()}

        # Separate periodic edges and regular edges
        regular_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if not d.get("periodic")]
        periodic_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get("periodic")]

        # Initialize plot
        plt.figure(figsize=(12, 12))

        # Draw the regular edges
        nx.draw(self.graph, pos, edgelist=regular_edges, node_color=colors, node_size=200, with_labels=False)

        # Draw periodic edges with dashed lines if visualize_periodic_bonds is True
        if visualize_periodic_bonds:
            nx.draw_networkx_edges(self.graph, pos, edgelist=periodic_edges, style="dashed", edge_color="gray")

        # Highlight the nodes and edges in the specified path
        path_edges = list(zip(path, path[1:]))
        nx.draw_networkx_nodes(self.graph, pos, nodelist=path, node_color="yellow", node_size=300)
        nx.draw_networkx_edges(self.graph, pos, edgelist=path_edges, edge_color="yellow", width=2)

        # Draw labels for nodes
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=10, font_color="cyan", font_weight="bold")

        plt.show()

    def plot_graphene_with_depth_neighbors_based_on_bond_length(
        self, atom_id: int, max_distance: float, visualize_periodic_bonds: bool = True
    ):
        """
        Plot the graphene structure with neighbors highlighted based on bond length.

        This method plots the entire graphene structure and highlights nodes that are within
        a specified maximum distance from a given atom, using the bond length as the distance metric.

        Parameters
        ----------
        atom_id : int
            The ID of the atom from which distances are measured.
        max_distance : float
            The maximum bond length distance within which neighbors are highlighted.
        visualize_periodic_bonds : bool, optional
            Whether to visualize periodic boundary condition edges (default is True).

        Notes
        -----
        The neighbors within the specified distance are highlighted in yellow, while the rest
        of the graphene structure is displayed in its default colors. Periodic boundary condition edges are
        shown with dashed lines if visualize_periodic_bonds is True.
        """
        # Get positions and elements of nodes
        pos = nx.get_node_attributes(self.graph, "position")
        elements = nx.get_node_attributes(self.graph, "element")

        # Determine colors for nodes, considering nitrogen species if present
        colors = [
            self.get_color(elements[node], self.graph.nodes[node].get("nitrogen_species"))
            for node in self.graph.nodes()
        ]
        labels = {node: f"{elements[node]}{node}" for node in self.graph.nodes()}

        # Separate periodic edges and regular edges
        regular_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if not d.get("periodic")]
        periodic_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get("periodic")]

        # Initialize plot
        plt.figure(figsize=(12, 12))

        # Draw the regular edges
        nx.draw(self.graph, pos, edgelist=regular_edges, node_color=colors, node_size=200, with_labels=False)

        # Draw periodic edges with dashed lines if visualize_periodic_bonds is True
        if visualize_periodic_bonds:
            nx.draw_networkx_edges(self.graph, pos, edgelist=periodic_edges, style="dashed", edge_color="gray")

        # Compute shortest path lengths from the specified atom using bond lengths
        paths = nx.single_source_dijkstra_path_length(self.graph, atom_id, cutoff=max_distance, weight="bond_length")

        # Identify neighbors within the specified maximum distance
        depth_neighbors = [node for node, length in paths.items() if length <= max_distance]
        path_edges = [(u, v) for u in depth_neighbors for v in self.graph.neighbors(u) if v in depth_neighbors]

        # Highlight the identified neighbors and their connecting edges
        nx.draw_networkx_nodes(self.graph, pos, nodelist=depth_neighbors, node_color="yellow", node_size=300)
        nx.draw_networkx_edges(self.graph, pos, edgelist=path_edges, edge_color="yellow", width=2)

        # Draw labels for nodes
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=10, font_color="cyan", font_weight="bold")

        # Show plot
        plt.show()

    def plot_nodes_within_distance(self, nodes_within_distance: List[int], visualize_periodic_bonds: bool = True):
        """
        Plot the graphene structure with neighbors highlighted based on distance.

        This method plots the entire graphene structure and highlights nodes that are within
        a specified maximum distance from a given atom, using the bond length as the distance metric.

        Parameters
        ----------
        nodes_within_distance : List[int]
            A list of node IDs representing the neighbors within the given distance.
        visualize_periodic_bonds : bool, optional
            Whether to visualize periodic boundary condition edges (default is True).

        Notes
        -----
        The neighbors within the specified distance are highlighted in yellow, while the rest
        of the graphene structure is displayed in its default colors. Periodic boundary condition edges are
        shown with dashed lines if visualize_periodic_bonds is True.
        """
        # Get positions and elements of nodes
        pos = nx.get_node_attributes(self.graph, "position")
        elements = nx.get_node_attributes(self.graph, "element")

        # Determine colors for nodes, considering nitrogen species if present
        colors = [
            self.get_color(elements[node], self.graph.nodes[node].get("nitrogen_species"))
            for node in self.graph.nodes()
        ]
        labels = {node: f"{elements[node]}{node}" for node in self.graph.nodes()}

        # Separate periodic edges and regular edges
        regular_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if not d.get("periodic")]
        periodic_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get("periodic")]

        # Initialize plot
        plt.figure(figsize=(12, 12))

        # Draw the regular edges
        nx.draw(self.graph, pos, edgelist=regular_edges, node_color=colors, node_size=200, with_labels=False)

        # Draw periodic edges with dashed lines if visualize_periodic_bonds is True
        if visualize_periodic_bonds:
            nx.draw_networkx_edges(self.graph, pos, edgelist=periodic_edges, style="dashed", edge_color="gray")

        # Compute edges within the specified distance
        path_edges = [
            (u, v) for u in nodes_within_distance for v in self.graph.neighbors(u) if v in nodes_within_distance
        ]

        # Highlight the identified neighbors and their connecting edges
        nx.draw_networkx_nodes(self.graph, pos, nodelist=nodes_within_distance, node_color="yellow", node_size=300)
        nx.draw_networkx_edges(self.graph, pos, edgelist=path_edges, edge_color="yellow", width=2)

        # Draw labels for nodes
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=10, font_color="cyan", font_weight="bold")

        # Show plot
        plt.show()


def write_xyz(graph, filename):
    with open(filename, "w") as file:
        file.write(f"{graph.number_of_nodes()}\n")
        file.write("XYZ file generated from GrapheneGraph\n")
        for node_id, node_data in graph.nodes(data=True):
            x, y = node_data["position"]
            element = node_data["element"]
            file.write(f"{element} {x:.3f} {y:.3f} 0.000\n")


def print_warning(message: str):
    # ANSI escape code for red color
    RED = "\033[91m"
    # ANSI escape code to reset color
    RESET = "\033[0m"
    print(f"{RED}{message}{RESET}")


def main():
    # Set seed for reproducibility
    # random.seed(42)
    # random.seed(2)
    # random.seed(6)
    random.seed(2)

    graphene = GrapheneGraph(bond_distance=1.42, sheet_size=(20, 20))

    # write_xyz(graphene.graph, 'graphene.xyz')
    # graphene.plot_graphene(with_labels=True)

    # Find direct neighbors of a node (depth=1)
    direct_neighbors = graphene.get_neighbors_via_edges(atom_id=0, depth=1)
    print(f"Direct neighbors of C_0: {direct_neighbors}")

    # Find neighbors of a node at an exact depth (depth=2)
    depth_neighbors = graphene.get_neighbors_via_edges(atom_id=0, depth=2)
    print(f"Neighbors of C_0 at depth 2: {depth_neighbors}")

    # Find neighbors of a node up to a certain depth (inclusive=True)
    inclusive_neighbors = graphene.get_neighbors_via_edges(atom_id=0, depth=2, inclusive=True)
    print(f"Neighbors of C_0 up to depth 2 (inclusive): {inclusive_neighbors}")

    # graphene.add_nitrogen_doping_old(10, NitrogenSpecies.GRAPHITIC)
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(percentages={NitrogenSpecies.PYRIDINIC_2: 20})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(percentages={NitrogenSpecies.PYRIDINIC_3: 20})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(
    #     percentages={NitrogenSpecies.PYRIDINIC_2: 10, NitrogenSpecies.PYRIDINIC_3: 10, NitrogenSpecies.GRAPHITIC: 20}
    # )
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(
    #     percentages={
    #         NitrogenSpecies.PYRIDINIC_2: 3,
    #         NitrogenSpecies.PYRIDINIC_3: 3,
    #         NitrogenSpecies.GRAPHITIC: 20,
    #         NitrogenSpecies.PYRIDINIC_4: 5,
    #         NitrogenSpecies.PYRIDINIC_1: 5,
    #     }
    # )
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(percentages={NitrogenSpecies.GRAPHITIC: 20, NitrogenSpecies.PYRIDINIC_4: 20})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    graphene.add_nitrogen_doping(percentages={NitrogenSpecies.PYRIDINIC_4: 3})
    graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(percentages={NitrogenSpecies.PYRIDINIC_1: 50})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(total_percentage=20, percentages={NitrogenSpecies.GRAPHITIC: 10})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    # graphene.add_nitrogen_doping(percentages={NitrogenSpecies.GRAPHITIC: 10, NitrogenSpecies.PYRIDINIC_3: 5})
    # graphene.plot_graphene(with_labels=True, visualize_periodic_bonds=False)

    write_xyz(graphene.graph, "graphene_doping_PYRIDINIC_4.xyz")

    source = 0
    target = 10
    path = graphene.get_shortest_path(source, target)
    print(f"Shortest path from C_{source} to C_{target}: {path}")
    graphene.plot_graphene_with_path(path)

    graphene.plot_graphene_with_depth_neighbors_based_on_bond_length(0, 4)

    # Find nodes within a certain distance from a source node
    atom_id = 5
    max_distance = 5
    nodes_within_distance = graphene.get_neighbors_within_distance(atom_id, max_distance)
    print(f"Nodes within {max_distance} distance from node {atom_id}: {nodes_within_distance}")

    # Plot the nodes within the specified distance
    graphene.plot_nodes_within_distance(nodes_within_distance)


if __name__ == "__main__":
    main()
