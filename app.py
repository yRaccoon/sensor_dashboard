import os
import glob
import io
import base64
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import pandas as pd
from collections import defaultdict

# 🔧 Set Matplotlib backend to non-interactive BEFORE importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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
@app.route('/api/sensor/<sensor_id>/plot')
def sensor_plot(sensor_id):
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        folder = os.path.join(os.path.dirname(__file__), 'data', 'sensors', sensor_id)
        if not os.path.isdir(folder):
            return jsonify({'error': f'Sensor folder not found: {sensor_id}'}), 404
        
        all_files = glob.glob(os.path.join(folder, '*.csv'))
        if not all_files:
            return jsonify({'error': 'No CSV files found in sensor folder'}), 404
        
        start_dt = datetime.fromisoformat(start_str) if start_str else None
        end_dt = datetime.fromisoformat(end_str) if end_str else None
        
        selected_files = []
        for f in all_files:
            base = os.path.splitext(os.path.basename(f))[0]
            try:
                file_date = datetime.strptime(base[:8], '%Y%m%d')
            except ValueError:
                selected_files.append(f)
                continue
            
            file_day_start = file_date.replace(hour=0, minute=0, second=0)
            file_day_end = file_date.replace(hour=23, minute=59, second=59)
            
            if start_dt and end_dt:
                if file_day_end >= start_dt and file_day_start <= end_dt:
                    selected_files.append(f)
            elif start_dt:
                if file_day_end >= start_dt:
                    selected_files.append(f)
            elif end_dt:
                if file_day_start <= end_dt:
                    selected_files.append(f)
            else:
                selected_files.append(f)
        
        if not selected_files:
            return jsonify({'error': 'No CSV files cover the selected time range'}), 404
        
        dfs = []
        for f in selected_files:
            try:
                df = pd.read_csv(f)
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {f}: {e}")
        
        if not dfs:
            return jsonify({'error': 'Could not read any CSV files'}), 500
        
        combined = pd.concat(dfs, ignore_index=True)
        combined['date_time'] = pd.to_datetime(combined['date_time'], errors='coerce')
        combined = combined.dropna(subset=['date_time'])
        combined = combined.sort_values('date_time')
        
        if start_dt:
            combined = combined[combined['date_time'] >= start_dt]
        if end_dt:
            combined = combined[combined['date_time'] <= end_dt]
        
        if combined.empty:
            return jsonify({'error': 'No data in selected time range'}), 404
        
        x_min = combined['date_time'].min()
        x_max = combined['date_time'].max()
        if start_dt:
            x_min = start_dt
        if end_dt:
            x_max = end_dt
        
        plt.figure(figsize=(12, 6))
        plt.plot(combined['date_time'], combined['value1'], color='#2563eb', linewidth=2)
        plt.axhline(y=5, color='#eab308', linestyle='--', linewidth=2)
        plt.axhline(y=20, color='#dc2626', linestyle='--', linewidth=2)
        plt.ylim(0, 100)
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.title(f'{sensor_id}')
        
        ax = plt.gca()
        ax.set_xlim(x_min, x_max)
        
        # Adaptive tick locator
        span_days = (x_max - x_min).total_seconds() / (24 * 3600)
        if span_days <= 1:
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        elif span_days <= 7:
            ax.xaxis.set_major_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return jsonify({'image': img_base64})
    
    except Exception as e:
        print(f"Plot generation error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
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