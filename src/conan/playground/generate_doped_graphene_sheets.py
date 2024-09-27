import os
import random
from itertools import combinations
from typing import Dict, List, Tuple

from conan.playground.doping_experiment import GrapheneSheet
from conan.playground.graph_utils import NitrogenSpecies, write_xyz


def create_graphene_sheets(
    num_sheets: int = 100, output_folder: str = "graphene_sheets", sheet_sizes: List[Tuple[int, int]] = None
):
    """
    Create a specified number of doped graphene sheets with varying sizes, total doping percentages, relative doping
    percentages and doping species.

    Parameters
    ----------
    num_sheets : int, optional
        Number of graphene sheets to generate. Default is 100.
    output_folder : str, optional
        Directory where the generated sheets will be saved. Default is 'graphene_sheets'.
    sheet_sizes : List[Tuple[int, int]], optional
        List of sheet sizes (width, height) to choose from. If None, default sizes are used.
    """
    # Create the output folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Default sheet sizes if none provided
    if sheet_sizes is None:
        sheet_sizes = [(20, 20), (30, 30), (40, 40)]

    # Available nitrogen species  # ToDo: Verbessern, sind einfach alle Spezies!
    available_species = [
        # NitrogenSpecies.GRAPHITIC,
        NitrogenSpecies.PYRIDINIC_1,
        NitrogenSpecies.PYRIDINIC_2,
        NitrogenSpecies.PYRIDINIC_3,
        NitrogenSpecies.PYRIDINIC_4,
    ]

    # Generate possible combinations of species (from 1 to all species)
    species_combinations = []
    for r in range(1, len(available_species) + 1):
        combinations_r = list(combinations(available_species, r))
        species_combinations.extend(combinations_r)

    # # Filter out combinations with only GRAPHITIC_N
    # species_combinations = [
    #     combo for combo in species_combinations if not (len(combo) == 1 and NitrogenSpecies.GRAPHITIC in combo)
    # ]

    for i in range(num_sheets):
        # Randomly select parameters
        size = random.choice(sheet_sizes)
        total_percentage = random.uniform(5.0, 15.0)  # Random doping percentage between 5% and 15%
        species_combination = random.choice(species_combinations)

        # Create a graphene sheet with the selected size
        graphene = GrapheneSheet(bond_distance=1.42, sheet_size=size)

        # Generate percentages for each species in the combination
        species_percentages = generate_species_percentages(species_combination, total_percentage)

        # Prepare the percentages dict for add_nitrogen_doping
        percentages = {species: pct for species, pct in species_percentages.items()}

        # Add nitrogen doping
        graphene.add_nitrogen_doping(total_percentage=total_percentage, percentages=percentages, adjust_positions=False)

        # Generate an informative filename
        size_str = f"{size[0]}x{size[1]}"
        total_pct_str = f"{total_percentage:.1f}percent"
        species_percentage_str = "_".join(
            [
                f"{species.value.replace(' ', '').replace('-', '')}{percentage_per_species:.1f}percent"
                for species, percentage_per_species in percentages.items()
            ]
        )
        filename = os.path.join(
            output_folder, f"graphene_{i + 1}_{size_str}_{total_pct_str}_{species_percentage_str}.xyz"
        )

        # Save the graphene sheet as an XYZ file
        write_xyz(graphene.graph, filename)

    print(
        f"\n{num_sheets} graphene sheets with varying sizes, nitrogen doping percentages, "
        f"and species combinations have been created and saved in '{output_folder}'."
    )


def generate_species_percentages(species_combination, total_percentage) -> Dict[NitrogenSpecies, float]:
    """
    Generate random percentages for each species in the combination, ensuring the total adds up to total_percentage.

    Parameters
    ----------
    species_combination : List[NitrogenSpecies]
        List of nitrogen species to include.
    total_percentage : float
        Total doping percentage.

    Returns
    -------
    Dict[NitrogenSpecies, float]
        Dictionary mapping each species to its assigned percentage.
    """
    random_factors = [random.uniform(0.1, 1.0) for _ in species_combination]
    total_factors = sum(random_factors)
    species_percentages = {
        species: (factor / total_factors) * total_percentage
        for species, factor in zip(species_combination, random_factors)
    }
    return species_percentages


if __name__ == "__main__":
    # Create 1000 graphene sheets with varying nitrogen doping
    create_graphene_sheets(num_sheets=5)
