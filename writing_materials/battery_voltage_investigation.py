import pandas as pd
import matplotlib.pyplot as plt

# Convert the date limit to August 14
date_limit_aug14 = pd.to_datetime('2024-08-14')

# Filter the data to include only up to August 14
df_august_3_limited = df_august_3[df_august_3['TIMESTAMP'] <= date_limit_aug14]
df_august_4_limited = df_august_4[df_august_4['TIMESTAMP'] <= date_limit_aug14]

# Plot for the third dataset (Plot 5023)
fig, ax1 = plt.subplots(figsize=(10,6))

# Plot BatV on the left y-axis
ax1.set_xlabel('Date', fontsize=14)
ax1.set_ylabel('Battery Voltage (BatV)', color='blue', fontsize=14)
ax1.plot(df_august_3_limited['TIMESTAMP'], df_august_3_limited['BatV'], label='Battery Voltage (BatV)', color='blue')
ax1.tick_params(axis='y', labelcolor='blue', labelsize=12)
ax1.tick_params(axis='x', labelsize=12)

# Create a second y-axis for Solar Radiation
ax2 = ax1.twinx()
ax2.set_ylabel('Solar Radiation (Solar_2m_Avg)', color='orange', fontsize=14)
ax2.plot(df_august_3_limited['TIMESTAMP'], df_august_3_limited['Solar_2m_Avg'], label='Solar Radiation (Solar_2m_Avg)', color='orange')
ax2.tick_params(axis='y', labelcolor='orange', labelsize=12)

# Set the x-axis limit to August 14 and rotate labels
ax1.set_xlim([df_august_3_limited['TIMESTAMP'].min(), date_limit_aug14])
plt.xticks(rotation=45)

plt.title('Battery Voltage and Solar Radiation in August 2024 (Plot 5023) - up to August 14', fontsize=16)
fig.tight_layout()

plt.show()

# Plot for the fourth dataset (Plot 5003)
fig, ax1 = plt.subplots(figsize=(10,6))

# Plot BatV on the left y-axis
ax1.set_xlabel('Date', fontsize=14)
ax1.set_ylabel('Battery Voltage (BatV)', color='blue', fontsize=14)
ax1.plot(df_august_4_limited['TIMESTAMP'], df_august_4_limited['BatV'], label='Battery Voltage (BatV)', color='blue')
ax1.tick_params(axis='y', labelcolor='blue', labelsize=12)
ax1.tick_params(axis='x', labelsize=12)

# Create a second y-axis for Solar Radiation
ax2 = ax1.twinx()
ax2.set_ylabel('Solar Radiation (Solar_2m_Avg)', color='orange', fontsize=14)
ax2.plot(df_august_4_limited['TIMESTAMP'], df_august_4_limited['Solar_2m_Avg'], label='Solar Radiation (Solar_2m_Avg)', color='orange')
ax2.tick_params(axis='y', labelcolor='orange', labelsize=12)

# Set the x-axis limit to August 14 and rotate labels
ax1.set_xlim([df_august_4_limited['TIMESTAMP'].min(), date_limit_aug14])
plt.xticks(rotation=45)

plt.title('Battery Voltage and Solar Radiation in August 2024 (Plot 5003) - up to August 14', fontsize=16)
fig.tight_layout()

plt.show()
