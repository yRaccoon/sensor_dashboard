from flask import Flask, render_template, jsonify
import pandas as pd
import os
from collections import defaultdict

app = Flask(__name__)

def map_status(status_code):
    """Convert numeric status to CSS class."""
    try:
        code = int(status_code)
        if code == 0: return 'ok'           # Green
        if code in [1, 2]: return 'warn'    # Orange
        if code == 3: return 'critical'     # Red
        if code == 4: return 'unknown'      # Grey
        return 'unknown'
    except:
        return 'unknown'

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    inv_path = os.path.join(base_dir, 'data', 'DCP_Inventory_R1.csv')
    stat_path = os.path.join(base_dir, 'data', 'DCP_Status.csv')

    try:
        df_inv = pd.read_csv(inv_path)
        df_stat = pd.read_csv(stat_path)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return {}

    # Merge Inventory with Status
    df = pd.merge(df_inv, df_stat, on='DCP Name', how='left')
    df['Status'] = df['Status'].fillna(0)
    
    # Fill NaN values for new columns
    df['Average'] = df['Average'].fillna(0)
    df['Stop_Cnt'] = df['Stop_Cnt'].fillna(0)
    df['Check_L1_Cnt'] = df['Check_L1_Cnt'].fillna(0)
    df['Check_L2_Cnt'] = df['Check_L2_Cnt'].fillna(0)

    # Dictionary to hold data grouped by Line_no for table sections
    # Structure: { 'hsa': { 'NLHSA_Line2': [ {info}, {info}... ] } }
    grouped_data = defaultdict(lambda: defaultdict(list))
    
    # Dictionary for list sections (WCS, AOI, SM)
    list_data = defaultdict(list)

    for _, row in df.iterrows():
        process = str(row['Process']).strip()
        desc = row['Description']
        line_no = str(row['Line_no']).strip()
        
        # Determine Section
        section = None
        is_list_section = False
        
        if process in ['ALHSA', 'NLHSA']: section = 'hsa'
        elif process in ['ALDA', 'NLDA']: section = 'disassy'
        elif process in ['ALHDA', 'NLHDA']: section = 'hda'
        elif process == 'WCS': 
            section = 'wcs'
            is_list_section = True
        elif process == 'STW':
            if 'AOI' in desc: 
                section = 'aoi'
                is_list_section = True
            else: 
                section = 'smachine'
                is_list_section = True

        if not section: continue

        # Create Data Object with new fields
        data = {
            'id': row['DCP Name'],
            'desc': desc,
            'loc': row['Location_Code'],
            'status': map_status(row['Status']),
            'stop': int(row.get('Stop_Cnt', 0)),
            'l1': int(row.get('Check_L1_Cnt', 0)),
            'l2': int(row.get('Check_L2_Cnt', 0)),
            'average': float(row.get('Average', 0)),  # New field
            'line_no': line_no
        }

        if is_list_section:
            list_data[section].append(data)
        else:
            # For table sections, group by line number to assign columns later
            grouped_data[section][line_no].append(data)

    # Flatten grouped data into the sensor_map format expected by frontend
    sensor_map = {}

    for section, lines in grouped_data.items():
        for line_no, items in lines.items():
            # Sort items if necessary (assuming CSV order is correct, or sort by description)
            # items.sort(key=lambda x: x['desc']) # Optional sort
            
            for idx, item in enumerate(items):
                # Key format: "section-line_no-index"
                # e.g., "hsa-NLHSA_Line2-0"
                key = f"{section}-{line_no}-{idx}"
                sensor_map[key] = item

    # Add list sections to the map
    for section, items in list_data.items():
        sensor_map[section] = items

    return sensor_map

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    data = load_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)