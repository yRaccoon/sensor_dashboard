from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

def map_status(status_code):
    """Convert numeric status to CSS class based on new rules."""
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
    
    inv_path = os.path.join(base_dir, 'DCP_Inventory_R1.csv')
    stat_path = os.path.join(base_dir, 'DCP_Status.csv')

    try:
        df_inv = pd.read_csv(inv_path)
        df_stat = pd.read_csv(stat_path)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return {}

    df = pd.merge(df_inv, df_stat, on='DCP Name', how='left')
    df['Status'] = df['Status'].fillna(0)

    sensor_map = {}

    for _, row in df.iterrows():
        process = row['Process']
        desc = row['Description']
        line_no_col = str(row['Line_no']).strip()
        
        section = None
        if process in ['ALHSA', 'NLHSA']: section = 'hsa'
        elif process in ['ALDA', 'NLDA']: section = 'disassy'
        elif process == 'NLHDA': section = 'hda'
        elif process == 'WCS': section = 'wcs'
        elif process == 'STW':
            if 'AOI' in desc: section = 'aoi'
            else: section = 'smachine'

        if not section: continue

        data = {
            'id': row['DCP Name'],
            'desc': desc,
            'loc': row['Location_Code'],
            'status': map_status(row['Status']),
            'stop': int(row.get('Stop_Count', 0)),
            'l1': int(row.get('CheckL1_Count', 0)),
            'l2': int(row.get('CheckL2_Count', 0)),
            'line_no': line_no_col
        }

        if section in ['hsa', 'disassy', 'hda']:
            parts = str(desc).split()
            suffix = parts[-1] if parts else ''
            
            if line_no_col:
                key = f"{section}-{line_no_col}-{suffix}"
                sensor_map[key] = data
        
        else:
            if section not in sensor_map: sensor_map[section] = []
            sensor_map[section].append(data)

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