import pandas as pd
import random
import os  # Add this import

def generate_sensor_files():
    data_inventory = []
    data_status = []
    
    # Helper to generate DCP Name (Random P-Number)
    def get_dcp_name():
        return f"P{random.randint(10000, 99999)}"

    # Helper to get random status code
    # 0 = OK, 1/2 = Warn, 3 = Critical, 4 = Unknown
    def get_status_code():
        return random.choices([0, 1, 2, 3, 4], weights=[70, 10, 10, 5, 5])[0]

    # --- Section Definitions ---
    
    sections = [
        # HSA (AL)
        {'lines': [f'ALHSA{i}' for i in range(1, 6)], 'stations': 5, 'loc_prefix': 'CIP-ALH', 'process': 'HSA', 'type': 'table'},
        # HSA (NL)
        {'lines': [f'NLHSA{i}' for i in range(1, 17)], 'stations': 5, 'loc_prefix': 'CIP-NLH', 'process': 'HSA', 'type': 'table'},
        # DIS-ASSY (AL)
        {'lines': [f'ALDIS-ASSY{i}' for i in range(1, 3)], 'stations': 5, 'loc_prefix': 'CIP-ALD', 'process': 'DIS-ASSY', 'type': 'table'},
        # DIS-ASSY (NL)
        {'lines': [f'NLDIS-ASSY{i}' for i in range(1, 10)], 'stations': 5, 'loc_prefix': 'CIP-NLD', 'process': 'DIS-ASSY', 'type': 'table'},
        # HDA
        {'lines': [f'NLHDA{i}' for i in range(1, 15)], 'stations': 18, 'loc_prefix': 'CIP-NLH', 'process': 'HDA', 'type': 'table'},
        # AOI
        {'lines': ['AOI'], 'stations': 10, 'loc_prefix': 'CIP-AOI', 'process': 'AOI', 'type': 'list'},
        # S MACHINE
        {'lines': ['SM'], 'stations': 10, 'loc_prefix': 'CIP-SM', 'process': 'S_MACHINE', 'type': 'list'},
        # WCS
        {'lines': ['WCS'], 'stations': 21, 'loc_prefix': 'CIP-WCS', 'process': 'WCS', 'type': 'list'},
    ]

    for section in sections:
        process = section['process']
        loc_prefix = section['loc_prefix']
        stn_count = section['stations']
        
        # List type sensors (AOI, SM, WCS)
        if section['type'] == 'list':
            line_name = section['lines'][0]
            for i in range(1, stn_count + 1):
                dcp = get_dcp_name()
                desc = f"{line_name}{i} SENSOR"
                loc_code = f"{loc_prefix}{i}" if process != 'S_MACHINE' else f"{loc_prefix}{i}" # Adjust logic if needed
                
                # Inventory Row
                # Format: DCP Name, Description, Location_Code, Line, Process
                data_inventory.append([dcp, desc, loc_code, f"{line_name}{i}", process])
                
                # Status Row
                status = get_status_code()
                data_status.append([dcp, status])
        
        # Table type sensors (HSA, DIS, HDA)
        else:
            for line in section['lines']:
                for i in range(1, stn_count + 1):
                    dcp = get_dcp_name()
                    desc = f"{line} STN{i}"
                    loc_code = loc_prefix
                    
                    # Inventory Row
                    data_inventory.append([dcp, desc, loc_code, line, process])
                    
                    # Status Row
                    status = get_status_code()
                    data_status.append([dcp, status])

    # Create DataFrames
    df_inventory = pd.DataFrame(data_inventory, columns=['DCP Name', 'Description', 'Location_Code', 'Line', 'Process'])
    df_status = pd.DataFrame(data_status, columns=['DCP Name', 'Status'])

    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Save to CSV in the data folder
    inventory_path = os.path.join(data_dir, 'DCP_Inventory_R1.csv')
    status_path = os.path.join(data_dir, 'DCP_Status.csv')
    
    df_inventory.to_csv(inventory_path, index=False)
    df_status.to_csv(status_path, index=False)
    
    print(f"Generated {len(df_inventory)} sensor entries.")
    print(f"Files saved in: {data_dir}")
    print(f"  - {inventory_path}")
    print(f"  - {status_path}")

if __name__ == "__main__":
    generate_sensor_files()