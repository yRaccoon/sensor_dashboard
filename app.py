from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
from collections import defaultdict
import glob
from datetime import datetime

app = Flask(__name__)

def map_status(status_code):
    try:
        code = int(status_code)
        if code == 0: return 'active'  
        if code in [1, 2]: return 'warn'
        if code == 3: return 'critical'
        if code == 4: return 'stale'
        return 'unknown'
    except:
        return 'unknown'

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inv_path = os.path.join(base_dir, 'data', 'DCP_Inventory_R1.csv')
    stat_path = os.path.join(base_dir,'data', 'DCP_Status.csv')

    try:
        df_inv = pd.read_csv(inv_path)
        df_stat = pd.read_csv(stat_path)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return {}

    df = pd.merge(df_inv, df_stat, on='DCP Name', how='left')
    df['Status'] = df['Status'].fillna(0)
    df['Average'] = df['Average'].fillna(0)
    df['Stop_Cnt'] = df['Stop_Cnt'].fillna(0)
    df['Check_L1_Cnt'] = df['Check_L1_Cnt'].fillna(0)
    df['Check_L2_Cnt'] = df['Check_L2_Cnt'].fillna(0)

    grouped_data = defaultdict(lambda: defaultdict(list))
    list_data = defaultdict(list)

    for _, row in df.iterrows():
        process = str(row['Process']).strip()
        desc = row['Description']
        line_no = str(row['Line_no']).strip()

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

        if not section:
            continue

        status_code = int(row.get('Status', 0))
        data = {
            'id': row['DCP Name'],
            'desc': desc,
            'loc': row['Location_Code'],
            'process': process,          
            'status': map_status(status_code),
            'status_code': status_code,
            'stop': int(row.get('Stop_Cnt', 0)),
            'l1': int(row.get('Check_L1_Cnt', 0)),
            'l2': int(row.get('Check_L2_Cnt', 0)),
            'average': float(row.get('Average', 0)),
            'line_no': line_no
        }

        if is_list_section:
            list_data[section].append(data)
        else:
            grouped_data[section][line_no].append(data)

    sensor_map = {}
    for section, lines in grouped_data.items():
        for line_no, items in lines.items():
            for idx, item in enumerate(items):
                key = f"{section}-{line_no}-{idx}"
                sensor_map[key] = item
    for section, items in list_data.items():
        sensor_map[section] = items

    return sensor_map

@app.route('/api/sensor/<sensor_id>/data')
def sensor_data(sensor_id):
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    folder = os.path.join(os.path.dirname(__file__), 'data', 'sensors', sensor_id)
    if not os.path.isdir(folder):
        return jsonify({'error': 'Sensor folder not found'}), 404
    
    csv_files = glob.glob(os.path.join(folder, '*.csv'))
    if not csv_files:
        return jsonify({'error': 'No CSV files found'}), 404
    
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    if not dfs:
        return jsonify({'error': 'Could not read any CSV files'}), 500
    
    combined = pd.concat(dfs, ignore_index=True)
    combined['date_time'] = pd.to_datetime(combined['date_time'])
    combined = combined.sort_values('date_time')
    
    if start_str:
        start_dt = datetime.fromisoformat(start_str)
        combined = combined[combined['date_time'] >= start_dt]
    if end_str:
        end_dt = datetime.fromisoformat(end_str)
        combined = combined[combined['date_time'] <= end_dt]
    
    times = combined['date_time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    values = combined['value1'].tolist()
    
    return jsonify({'times': times, 'values': values})

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/data')
def api_data():
    return jsonify(load_data())

if __name__ == '__main__':
    app.run(debug=True, port=5000)