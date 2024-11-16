import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter


def load_cdf_data(file_path):
    """
    Load the CDF data from a CSV file and update column names.

    Parameters
    ----------
    file_path : str
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame with the loaded data.
    """
    cdf_data = pd.read_csv(file_path, skiprows=1, delimiter=";")
    cdf_data.columns = ["Distance from Plane / pm", "Angle / Degree", "Occurrence"]
    return cdf_data


def create_pivot_table(cdf_data):
    """
    Create a pivot table for contour plotting.

    Parameters
    ----------
    cdf_data : pd.DataFrame
        Pandas DataFrame with the CDF data.

    Returns
    -------
    tuple of np.ndarray
        Meshgrid arrays X, Y and Z values for contour plotting.
    """
    pivot_table = cdf_data.pivot_table(
        index="Angle / Degree", columns="Distance from Plane / pm", values="Occurrence", fill_value=0
    )
    X = pivot_table.columns.values
    Y = pivot_table.index.values
    X, Y = np.meshgrid(X, Y)
    Z = pivot_table.values
    return X, Y, Z


def smooth_data(Z, sigma=1.0):
    """
    Smooth the Z data using a Gaussian filter.

    Parameters
    ----------
    Z : np.ndarray
        2D array of values to be smoothed.
    sigma : float, optional
        Smoothing factor for the Gaussian filter (default is 1.0).

    Returns
    -------
    np.ndarray
        Smoothed Z values.
    """
    return gaussian_filter(Z, sigma=sigma)


def plot_contour(X, Y, Z, title, cmap="jet", levels_filled=50, xlim=(-5200, 5200), save_path=None):
    """
    Plot a contour plot with filled contours and contour lines.

    Parameters
    ----------
    X : np.ndarray
        Meshgrid array for the x-axis.
    Y : np.ndarray
        Meshgrid array for the y-axis.
    Z : np.ndarray
        2D array of values for contour plotting.
    title : str
        Title of the plot.
    cmap : str, optional
        Colormap for filled contours (default is 'jet').
    levels_filled : int, optional
        Number of levels for filled contours (default is 50).
    xlim : tuple, optional
        Limits for the x-axis (default is (-5000, 5000)).
    save_path : str, optional
        Path to save the plot as an image (default is None, which does not save the plot).
    """
    plt.figure(figsize=(10, 8))
    contour_filled = plt.contourf(X, Y, Z, levels=levels_filled, cmap=cmap, alpha=0.8)
    plt.colorbar(contour_filled, label="Occurrence")
    plt.xlabel("Distance from Plane (pm)")
    plt.ylabel("Angle (Degree)")
    plt.title(title)
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    plt.xticks(np.arange(-5200, 5200, 1000))
    plt.yticks(np.arange(0, 190, 45))
    plt.xlim(xlim)

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()


def process_cdf(file_path, output_dir=None):
    """
    Process a CDF file and generate contour plots for raw and smoothed data.

    Parameters
    ----------
    file_path : str
        Path to the CDF CSV file.
    output_dir : str, optional
        Directory to save the resulting plots. If None, plots are shown but not saved.
    """
    # Create output directory if it does not exist and if output_dir is provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Load data
    cdf_data = load_cdf_data(file_path)

    # Create pivot table and meshgrid for plotting
    X, Y, Z = create_pivot_table(cdf_data)

    # Plot raw data
    raw_plot_path = os.path.join(output_dir, "cdf_raw.png") if output_dir else None
    plot_contour(
        X,
        Y,
        Z,
        title="Combined Distribution Function Contour Plot (Raw Data)",
        cmap="viridis",
        levels_filled=50,
        save_path=raw_plot_path,
    )

    # Smooth data and plot
    Z_smoothed = smooth_data(Z, sigma=1.0)
    smoothed_plot_path = os.path.join(output_dir, "cdf_smoothed.png") if output_dir else None
    plot_contour(
        X,
        Y,
        Z_smoothed,
        title="Combined Distribution Function Contour Plot (Smoothed Data)",
        cmap="viridis",
        levels_filled=50,
        save_path=smoothed_plot_path,
    )


def load_density_profile(file_path):
    """
    Load the z-density profile from a CSV file.

    Parameters
    ----------
    file_path : str
        Path to the z-density profile CSV file.

    Returns
    -------
    tuple
        A tuple (z_values, density_values) where z_values are the z-coordinates
        and density_values are the corresponding density values.
    """
    data = pd.read_csv(file_path, delimiter=";")
    z_values = data.iloc[:, 0]
    density_values = data.iloc[:, 2]
    return z_values, density_values


def find_analysis_types(base_dir):
    """
    Dynamically find all analysis folders in the CONAN directory.

    Parameters
    ----------
    base_dir : str
        Base directory containing the production runs (e.g., prod1, prod2, prod3).

    Returns
    -------
    list of str
        List of analysis folder names found in the CONAN directory.
    """
    prod1_conan_dir = os.path.join(base_dir, "prod1", "output", "CONAN")
    if not os.path.exists(prod1_conan_dir):
        print(f"CONAN directory not found: {prod1_conan_dir}")
        return []

    return [folder for folder in os.listdir(prod1_conan_dir) if os.path.isdir(os.path.join(prod1_conan_dir, folder))]


def plot_z_density_profiles(base_dir, analysis_type, output_dir):
    """
    Plot z-density profiles for all production runs (prod1, prod2, prod3) for a specific analysis type.

    Parameters
    ----------
    base_dir : str
        Base directory containing the production runs (e.g., prod1, prod2, prod3).
    analysis_type : str
        The specific analysis folder name (e.g., 'analysis_all').
    output_dir : str
        Directory to save the resulting plot.
    """
    prod_dirs = ["prod1", "prod2", "prod3"]
    colors = ["blue", "green", "pink"]
    plt.figure(figsize=(10, 6))

    for prod, color in zip(prod_dirs, colors):
        analysis_path = os.path.join(base_dir, prod, "output", "CONAN", analysis_type, "z_dens_profile.csv")
        if not os.path.exists(analysis_path):
            print(f"File not found: {analysis_path}")
            continue

        z_values, density_values = load_density_profile(analysis_path)
        plt.plot(z_values, density_values, label=f"{prod}", color=color, alpha=0.7)

    plt.title(f"z-Density Profile - {analysis_type}", fontsize=14)
    plt.xlabel("z [Å]", fontsize=12)
    plt.ylabel("Density [g/cm³]", fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.6)

    # Save the plot to the output directory
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{analysis_type}_z_density_profile.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Plot saved to {output_file}")


def cdf_analysis():
    # Define input file and output directory
    file_path = (
        "/home/sarah/Desktop/Master AMP/Masterarbeit/mnt/marie/simulations/sim_master_thesis/prod1/output/Travis/"
        "cdf/cdf_2_pldf[C306r_C307r_C305r]_#2o_adf[C306r_C307r_C305r]-[C2o_C1o]_triples.csv"
    )
    output_dir = "analysis_outputs"

    # Create output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Process the CDF file
    process_cdf(file_path, output_dir)


def axial_density_analysis():
    base_dir = "/home/sarah/Desktop/Master AMP/Masterarbeit/mnt/marie/simulations/sim_master_thesis"
    output_dir = "analysis_outputs"

    # Dynamically find analysis folders in the CONAN directory
    analysis_types = find_analysis_types(base_dir)

    if not analysis_types:
        print("No analysis types found. Exiting.")
        return

    for analysis_type in analysis_types:
        plot_z_density_profiles(base_dir, analysis_type, output_dir)


def main():
    """
    Main function to process and visualize data to analyze.
    """

    cdf_analysis()

    # axial_density_analysis()


if __name__ == "__main__":
    main()
