import os
import glob
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import pandas as pd
from collections import defaultdict

app = Flask(__name__)

def map_status(status_code):
    try:
        code = int(status_code)
        if code == 0: return 'active'
        if code == 1: return 'l1'
        if code == 2: return 'l2'
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

@app.route('/api/sensor/<sensor_id>/raw')
def sensor_raw_data(sensor_id):
    """Return raw data (date_time, value1) for the given sensor and date range."""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')

        folder = os.path.join(os.path.dirname(__file__), 'data', 'sensors', sensor_id)
        if not os.path.isdir(folder):
            return jsonify({'error': f'Sensor folder not found: {sensor_id}'}), 404

        all_files = glob.glob(os.path.join(folder, '*.csv'))
        if not all_files:
            return jsonify({'error': 'No CSV files found'}), 404

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
            return jsonify({'error': 'No data in selected range'}), 404

        dfs = []
        for f in selected_files:
            try:
                df = pd.read_csv(f)
                if 'date_time' not in df.columns or 'value1' not in df.columns:
                    print(f"Skipping {f}: missing required columns")
                    continue
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {f}: {e}")

        if not dfs:
            return jsonify({'error': 'No valid data found in CSV files'}), 404

        combined = pd.concat(dfs, ignore_index=True)
        
        def parse_datetime(val):
            if pd.isna(val) or val == '':
                return pd.NaT
            val_str = str(val).strip()
            formats = [
                '%Y-%m-%d %H:%M:%S.%f',  # with milliseconds
                '%Y-%m-%d %H:%M:%S',      # without milliseconds
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(val_str, fmt)
                except ValueError:
                    continue
            return pd.NaT
        
        combined['date_time'] = combined['date_time'].apply(parse_datetime)
        combined['value1'] = pd.to_numeric(combined['value1'], errors='coerce')
        combined = combined.dropna(subset=['date_time', 'value1'])

        if combined.empty:
            return jsonify({'error': 'No valid data after cleaning'}), 404

        combined = combined.drop_duplicates(subset=['date_time'], keep='first')
        combined = combined.sort_values('date_time')

        if start_dt:
            combined = combined[combined['date_time'] >= start_dt]
        if end_dt:
            combined = combined[combined['date_time'] <= end_dt]

        if combined.empty:
            return jsonify({'error': 'No data in selected time range after filtering'}), 404

        result = combined[['date_time', 'value1']].copy()
        result['date_time'] = result['date_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        data = result.to_dict(orient='records')

        return jsonify({'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/archive/data_by_date/<date_str>')
def api_archive_data_by_date(date_str):
    """Load LMS_YYYYMMDD_DS.csv and LMS_YYYYMMDD_NS.csv for a given date (YYYY-MM-DD)."""
    try:
        date_dt = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYY-MM-DD'}), 400

    date_compact = date_dt.strftime('%Y%m%d')
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    files_to_load = [
        os.path.join(data_dir, f'LMS_{date_compact}_DS.csv'),
        os.path.join(data_dir, f'LMS_{date_compact}_NS.csv')
    ]

    dfs = []
    for f in files_to_load:
        if os.path.isfile(f):
            # Determine shift from filename (e.g. LMS_20260410_DS.csv → DS)
            file_shift = os.path.basename(f).split('_')[-1].replace('.csv', '')  # 'DS' or 'NS'
            try:
                df = pd.read_csv(f, dtype={'Alarm Code': str})
                df['Shift'] = file_shift        
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {f}: {e}")

    combined = pd.concat(dfs, ignore_index=True).fillna('')

    # Parse & sort by Date_Time
    def parse_date_time(val):
        if pd.isna(val) or val == '':
            return pd.NaT
        val_str = str(val).strip()
        for fmt in ('%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue
        return pd.NaT

    combined['_dt'] = combined['Date_Time'].apply(parse_date_time)
    combined = combined.dropna(subset=['_dt'])
    combined = combined.sort_values('_dt')
    combined = combined.drop('_dt', axis=1)

    data = combined.to_dict(orient='records')
    columns = combined.columns.tolist()
    return jsonify({'columns': columns, 'data': data})

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/archive')
def archive():
    return render_template('archive.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/data')
def api_data():
    return jsonify(load_data())

if __name__ == '__main__':
    app.run(debug=True, port=5000)