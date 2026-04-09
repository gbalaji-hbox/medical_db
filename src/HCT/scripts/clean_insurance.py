import pandas as pd

# Load the Excel file
file_path = r'd:\Work_Folder\medical_db\src\HCT\patient-insurance.xlsx'
df = pd.read_excel(file_path, header=None)  # No header, we'll set later

# Find the header row (row with 'Name' in column 2)
header_row = None
for i, row in df.iterrows():
    if row[2] == 'Name':
        header_row = i
        break

if header_row is None:
    print("Header row not found")
    exit()

# Set the header
df.columns = df.iloc[header_row]
df = df[header_row + 1:].reset_index(drop=True)

# Remove completely empty rows
df = df.dropna(how='all')

# Remove duplicates based on all columns
df_cleaned = df.drop_duplicates()

# Save cleaned file
cleaned_path = r'd:\Work_Folder\medical_db\src\HCT\patient-insurance-cleaned.xlsx'
df_cleaned.to_excel(cleaned_path, index=False)

print(f"Original rows: {len(df)}")
print(f"Cleaned rows: {len(df_cleaned)}")
print(f"Duplicates removed: {len(df) - len(df_cleaned)}")

# Now analyze insurance coverage
# Group by 'Name' and count unique 'Enc Cob' values
insurance_counts = df_cleaned.groupby('Name')['Enc Cob'].nunique()

# Count how many patients have at least 2 insurances
at_least_2 = (insurance_counts >= 2).sum()
at_least_3 = (insurance_counts >= 3).sum()

print(f"\nInsurance Coverage Analysis:")
print(f"Total unique patients: {len(insurance_counts)}")
print(f"Patients with at least 2 insurances: {at_least_2}")
print(f"Patients with 3 insurances: {at_least_3}")

# Show distribution
print("\nDistribution of insurance count per patient:")
print(insurance_counts.value_counts().sort_index())