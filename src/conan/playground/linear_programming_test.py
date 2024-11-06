# import pulp
# import numpy as np
#
# # Define the initial parameters
# T_initial = 576  # Total initial atoms
# P_desired = 8.0  # Desired nitrogen percentage
# D = 5  # Number of doping types
#
# # Constants for each doping type
# ci = [0, 1, 1, 1, 2]  # Carbon atoms removed
# ri = [1, 1, 2, 3, 4]  # Nitrogen atoms added (replaced)
# names = ["Graphitic-N", "Pyridinic-N1", "Pyridinic-N2", "Pyridinic-N3", "Pyridinic-N4"]
#
# # Scale factors to convert to integers
# scale_factor = 100
# P_desired_fraction = P_desired / 100.0
#
# # Calculate ki and RHS
# # ki values (coefficients) are weights that represent the change in the nitrogen and carbon content through the
# # application of a specific doping type i
# ki = [scale_factor * ri_i + scale_factor * P_desired_fraction * ci_i for ri_i, ci_i in zip(ri, ci)]
# # RHS is the right-hand side of the equation, representing the desired nitrogen content related to the overall
# structure
# RHS = P_desired_fraction * T_initial * scale_factor
#
# # Initialize the problem
# prob = pulp.LpProblem("Nitrogen_Doping_Optimization", pulp.LpMinimize)
#
# # Decision variables
# xi = [pulp.LpVariable(f"x_{i}", lowBound=0, cat='Integer') for i in range(D)]
# z = pulp.LpVariable("z", lowBound=0, cat='Continuous')
#
# # Objective function
# prob += z, "Minimize absolute difference"
#
# # Constraints for the absolute value linearization
# prob += pulp.lpSum([ki[i] * xi[i] for i in range(D)]) - RHS <= z, "Upper bound constraint"
# prob += RHS - pulp.lpSum([ki[i] * xi[i] for i in range(D)]) <= z, "Lower bound constraint"
#
# # Solve the problem
# prob.solve()
#
# # Retrieve the solution
# xi_values = [int(xi[i].varValue) for i in range(D)]
# z_value = pulp.value(prob.objective)
#
# # Compute the actual nitrogen percentage
# N_total = sum([ri[i] * xi_values[i] for i in range(D)])
# C_removed = sum([ci[i] * xi_values[i] for i in range(D)])
# T_final = T_initial - C_removed
# P_actual = (N_total / T_final) * 100
#
# # Compute nitrogen distribution variance
# N_contributions = [ri[i] * xi_values[i] for i in range(D)]
# mean_N = np.mean(N_contributions)
# variance_N = np.var(N_contributions)
#
# # Print the results
# print("Doping Results:")
# print("|Nitrogen Species | Actual Percentage | Nitrogen Atom Count | Doping Structure Count |")
# for i in range(D):
#     species = names[i]
#     N_atom_count = N_contributions[i]
#     doping_structure_count = xi_values[i]
#     actual_percentage = (N_atom_count / T_final) * 100
#     print(f"{i:<6}{species:<15}{actual_percentage:>17.2f}{N_atom_count:>22}{doping_structure_count:>25}")
# print(f"{'Total Doping':<21}{P_actual:>17.2f}{N_total:>22}{sum(xi_values):>25}")


# import pulp
#
# # Define the initial parameters
# T_initial = 576  # Total initial atoms
# P_desired = 8.0  # Desired nitrogen percentage
# D = 5  # Number of doping types
#
# # Constants for each doping type
# ci = [0, 1, 1, 1, 2]  # Carbon atoms removed
# ri = [1, 1, 2, 3, 4]  # Nitrogen atoms added (replaced)
# names = ["Graphitic-N", "Pyridinic-N1", "Pyridinic-N2", "Pyridinic-N3", "Pyridinic-N4"]
#
# # Compute ki values
# P_desired_fraction = P_desired / 100.0
# ki = [ri_i + P_desired_fraction * ci_i for ri_i, ci_i in zip(ri, ci)]
# RHS = P_desired_fraction * T_initial
#
# # Initialize the problem
# prob = pulp.LpProblem("Nitrogen_Doping_Optimization", pulp.LpMinimize)
#
# # Decision variables
# xi = [pulp.LpVariable(f"x_{i}", lowBound=0, cat="Integer") for i in range(D)]
# x_avg = pulp.LpVariable("x_avg", lowBound=0, cat="Continuous")
# di = [pulp.LpVariable(f"d_{i}", lowBound=0, cat="Continuous") for i in range(D)]
# z1 = pulp.LpVariable("z1", lowBound=0, cat="Continuous")
# z2 = pulp.LpVariable("z2", lowBound=0, cat="Continuous")
#
# # Objective function
# w1 = 1  # Weight for deviation from desired nitrogen percentage
# w2 = 1000  # Weight for deviation from equal distribution
# prob += w1 * z1 + w2 * z2, "Minimize total deviation"
#
# # Constraints for the nitrogen percentage
# prob += pulp.lpSum([ki[i] * xi[i] for i in range(D)]) - RHS <= z1, "Upper bound constraint"
# prob += RHS - pulp.lpSum([ki[i] * xi[i] for i in range(D)]) <= z1, "Lower bound constraint"
#
# # Constraint for average calculation
# prob += x_avg * D == pulp.lpSum([xi[i] for i in range(D)]), "Average constraint"
#
# # Constraints for deviations from average
# for i in range(D):
#     prob += di[i] >= xi[i] - x_avg, f"Deviation_positive_{i}"
#     prob += di[i] >= x_avg - xi[i], f"Deviation_negative_{i}"
# prob += z2 == pulp.lpSum([di[i] for i in range(D)]), "Total deviation"
#
# # Solve the problem
# prob.solve()
#
# # Retrieve the solution
# xi_values = [int(xi[i].varValue) for i in range(D)]
# x_avg_value = x_avg.varValue
# di_values = [di[i].varValue for i in range(D)]
# z1_value = z1.varValue
# z2_value = z2.varValue
#
# # Compute the actual nitrogen percentage
# N_total = sum([ri[i] * xi_values[i] for i in range(D)])
# C_removed = sum([ci[i] * xi_values[i] for i in range(D)])
# T_final = T_initial - C_removed
# P_actual = (N_total / T_final) * 100
#
# # Print the results
# print("Doping Results:")
# print("|Nitrogen Species | Actual Percentage | Nitrogen Atom Count | Doping Structure Count |")
# for i in range(D):
#     species = names[i]
#     N_atom_count = ri[i] * xi_values[i]
#     doping_structure_count = xi_values[i]
#     actual_percentage = (N_atom_count / T_final) * 100
#     print(f"{i:<6}{species:<15}{actual_percentage:>17.2f}{N_atom_count:>22}{doping_structure_count:>25}")
# print(f"{'Total Doping':<21}{P_actual:>17.2f}{N_total:>22}{sum(xi_values):>25}")

import pulp

# Define the initial parameters
T_initial = 576  # Total initial atoms
P_desired = 8.0  # Desired nitrogen percentage
D = 5  # Number of doping types

# Constants for each doping type
ci = [0, 1, 1, 1, 2]  # Carbon atoms removed
ri = [1, 1, 2, 3, 4]  # Nitrogen atoms added (replaced)
names = ["Graphitic-N", "Pyridinic-N1", "Pyridinic-N2", "Pyridinic-N3", "Pyridinic-N4"]

# Compute ki values
P_desired_fraction = P_desired / 100.0
ki = [ri_i + P_desired_fraction * ci_i for ri_i, ci_i in zip(ri, ci)]
RHS = P_desired_fraction * T_initial

# Initialize the problem
prob = pulp.LpProblem("Nitrogen_Doping_Optimization", pulp.LpMinimize)

# Decision variables
xi = [pulp.LpVariable(f"x_{i}", lowBound=0, cat="Integer") for i in range(D)]
N_avg = pulp.LpVariable("N_avg", lowBound=0, cat="Continuous")
# di = [pulp.LpVariable(f"d_{i}", lowBound=0, cat="Continuous") for i in range(D)]
P_di = [pulp.LpVariable(f"P_d_{i}", lowBound=0, cat="Continuous") for i in range(D)]
N_di = [pulp.LpVariable(f"N_d_{i}", lowBound=0, cat="Continuous") for i in range(D)]
P = pulp.LpVariable("P_i", lowBound=0, cat="Continuous")
N = pulp.LpVariable("N_i", lowBound=0, cat="Continuous")
z1 = pulp.LpVariable("z1", lowBound=0, cat="Continuous")
z2 = pulp.LpVariable("z2", lowBound=0, cat="Continuous")

# Objective function
w1 = 1000  # Weight for deviation from desired nitrogen percentage
w2 = 1  # Weight for deviation from equal distribution of nitrogen atoms
prob += w1 * z1 + w2 * z2, "Minimize total deviation"

# # Constraints for the nitrogen percentage
# prob += pulp.lpSum([ki[i] * xi[i] for i in range(D)]) - RHS <= z1, "Upper bound constraint"
# prob += RHS - pulp.lpSum([ki[i] * xi[i] for i in range(D)]) <= z1, "Lower bound constraint"

# Nitrogen percentage constraint (replacing upper and lower bound constraints)
prob += pulp.lpSum([ki[i] * xi[i] for i in range(D)]) + P - N == RHS, "Nitrogen deviation constraint"
prob += z1 == P + N, "Absolute deviation constraint"

# Constraint for average nitrogen atoms calculation
prob += N_avg == pulp.lpSum([ri[i] * xi[i] for i in range(D)]) / D, "Average nitrogen atoms constraint"

# # Constraints for deviations in nitrogen atoms from the average
# for i in range(D):
#     prob += di[i] >= ri[i] * xi[i] - N_avg, f"Deviation_positive_{i}"
#     prob += di[i] >= N_avg - ri[i] * xi[i], f"Deviation_negative_{i}"
# prob += z2 == pulp.lpSum([di[i] for i in range(D)]), "Total deviation in nitrogen atoms"

# Constraints for deviations in nitrogen atoms from the average without di
# for i in range(D):
#     prob += ri[i] * xi[i] - N_avg == P_di[i] - N_di[i], f"Nitrogen deviation for type {i}"
for i in range(D):
    prob += ri[i] * xi[i] + P_di[i] - N_di[i] == N_avg, f"Nitrogen deviation for type {i}"

# Total deviation in nitrogen atoms (z2) as the sum of P_di and N_di
prob += z2 == pulp.lpSum([P_di[i] + N_di[i] for i in range(D)]), "Total deviation in nitrogen atoms"

# Solve the problem
prob.solve()

# Retrieve the solution
xi_values = [int(xi[i].varValue) for i in range(D)]
N_avg_value = N_avg.varValue
P_value = P.varValue
N_value = N.varValue
# di_values = [di[i].varValue for i in range(D)]
P_di_values = [P_di[i].varValue for i in range(D)]
N_di_values = [N_di[i].varValue for i in range(D)]
z1_value = z1.varValue
z2_value = z2.varValue

# Compute the actual nitrogen percentage
N_total = sum([ri[i] * xi_values[i] for i in range(D)])
C_removed = sum([ci[i] * xi_values[i] for i in range(D)])
T_final = T_initial - C_removed
P_actual = (N_total / T_final) * 100

# Scale the actual deviation in nitrogen percentage (z1) with T_final
z1_percentage = z1_value / (T_final / 100)

# Print the results
print("Doping Results:")
print("|Nitrogen Species | Actual Percentage | Nitrogen Atom Count | Doping Structure Count |")
for i in range(D):
    species = names[i]
    N_atom_count = ri[i] * xi_values[i]
    doping_structure_count = xi_values[i]
    actual_percentage = (N_atom_count / T_final) * 100
    print(f"{i:<6}{species:<15}{actual_percentage:>17.2f}{N_atom_count:>22}{doping_structure_count:>25}")
print(f"{'Total Doping':<21}{P_actual:>17.2f}{N_total:>22}{sum(xi_values):>25}")

# Output the final objective value with scaled z1
print(f"Objective value (z1 + z2): {prob.objective.value()}")
print(f"Actual deviation in nitrogen percentage (scaled z1): {z1_percentage}")
print("\nDone")


import matplotlib.pyplot as plt

# Visualization of nitrogen percentage deviation per species
species = names
actual_percentages = [(ri[i] * xi_values[i] / T_final) * 100 for i in range(D)]
desired_percentage_per_species = [P_actual / D] * D

plt.figure(figsize=(10, 6))
plt.bar(species, actual_percentages, color="skyblue", label="Actual Nitrogen Percentage per Species")
plt.axhline(y=P_desired / D, color="r", linestyle="--", label="Desired Nitrogen Percentage per Species")
plt.xlabel("Nitrogen Species", fontsize=14)
plt.ylabel("Nitrogen Percentage (%)", fontsize=14)
plt.title("Nitrogen Percentage per Species", fontsize=16)
plt.legend()
plt.grid(True)
plt.show()

# Visualization of nitrogen atoms deviation from average per species
N_avg_value = N_total / D
actual_atoms_per_species = [ri[i] * xi_values[i] for i in range(D)]
deviations = [abs(N_avg_value - actual_atoms_per_species[i]) for i in range(D)]

plt.figure(figsize=(10, 6))
plt.bar(species, actual_atoms_per_species, color="lightgreen", label="Actual Nitrogen Atoms per Species")
plt.axhline(y=N_avg_value, color="r", linestyle="--", label="Average Nitrogen Atoms per Species")
plt.xlabel("Nitrogen Species", fontsize=14)
plt.ylabel("Nitrogen Atom Count", fontsize=14)
plt.title("Deviation from Average Nitrogen Atoms per Species", fontsize=16)
plt.legend()
plt.grid(True)
plt.show()

# Visualization of deviations z1 and z2
deviations_values = [z1_value, z2_value]
deviations_labels = ["z1: Nitrogen Percentage Deviation", "z2: Equal Distribution Deviation"]

plt.figure(figsize=(8, 6))
plt.bar(deviations_labels, deviations_values, color=["blue", "green"])
plt.ylabel("Deviation Magnitude", fontsize=14)
plt.title("Objective Function Components", fontsize=16)
plt.grid(True)
plt.show()
