# INO Master Library

This repository contains a development KiCad database library with symbols, footprints, 3D Models, and the database build scripts for simple use.

## INO Library Setup Instructions

### 1. Install Prerequisites
Download and install the following:
- **Python** 
- **KiCad** 

### 2. Setup Library Files
Download the library ZIP file (or Clone this repository). Extract the contents directly to your C: drive so the path is:
`C:\INO_Master_Library\`

### 3. Build the Database
Navigate to the library folder and run the `build_kicad_library.py` script.
*(This automatically generates the `.db` and `.kicad_dbl` files based on the CSVs).*

### 4. Configure KiCad
**Add Symbols:**
1. Open KiCad and go to **Preferences > Manage Symbol Libraries**.
2. Click the folder icon and select `INO_Components.kicad_dbl` (from the main folder).
3. Click the folder icon again and select `INO_Symbols.kicad_sym` (located inside the Symbols subfolder).

**Add Footprints:**
1. Go to **Preferences > Manage Footprint Libraries**.
2. Click the folder icon and select the `INO_Footprints.pretty` folder (located inside the Footprints subfolder).

### 5. Test
Create a new project, open the Schematic Editor, and press **'A'**. Verify that your library appears and components can be placed.

---

## How to Add a New Component

### Case 1: Adding a component using existing symbols and footprints
*Use this when the symbol (e.g., Resistor) and footprint (e.g., 0603) already exist in the library.*

1. Navigate to the **Database** folder.
2. Open the CSV file matching the component type (e.g., `resistors.csv`).
3. Add a new row and fill in the component details.
4. Save the CSV file.
5. Run the `build_kicad_library.py` script.
6. Restart the KiCad Schematic Editor to refresh the library.
7. The component is now ready to use.

### Case 2: Adding a component from scratch
*Use this when you need to draw a new symbol or create a new footprint.*

1. Create the new Symbol and save it to the `INO_Symbols.kicad_sym` library.
2. Create the new Footprint and save it to the `INO_Footprints.pretty` library.
3. Navigate to the **Database** folder and open the relevant CSV file to the corresponding type of component.
4. Add a new row, referencing the names of the Symbol and Footprint you just created.
5. Save the CSV file.
6. Run the `build_kicad_library.py` script.
7. Restart the KiCad Schematic Editor.
8. The component is now ready to use.

---

## How to Add a New Component Category
*Use this to create a new library section (e.g., "Sensors", "Microcontrollers").*

1. Navigate to the **Database** folder.
2. Create a new CSV file. **Note:** The filename will become the category name in KiCad (e.g., `sensors.csv` becomes "Sensors").
3. Add the required header row. It **must** include at least these four columns:
    * `part_id` (Must be the first column)
    * `value`
    * `symbol`
    * `footprint`
4. Add at least one row of component data to test the file.
5. Run the `build_kicad_library.py` script.
6. Restart the KiCad Schematic Editor.
7. The new category will appear in the library list.