from flask import Flask, render_template, jsonify
import pandas as pd
import os
import re
import traceback
from datetime import datetime

app = Flask(__name__)

# Configuration
DATA_FOLDER = 'data'
INVENTORY_FILE = os.path.join(DATA_FOLDER, 'DCP_Inventory_R1.csv')
STATUS_FILE = os.path.join(DATA_FOLDER, 'DCP_Status.csv')

# Status mapping
STATUS_MAP = {
    0: 'OK',
    1: 'WARN',
    2: 'WARN',
    3: 'CRITICAL',
    4: 'UNKNOWN'
}

def extract_number(text):
    """Extract number from string for natural sorting"""
    numbers = re.findall(r'\d+', text)
    return int(numbers[0]) if numbers else 0

def natural_sort_key(text):
    """Create a key for natural sorting"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

def sort_lines_numerically(lines):
    """Sort lines naturally by their numbers"""
    return sorted(lines, key=natural_sort_key)

def load_and_merge_data():
    """Load inventory and status data, merge them, and add status text"""
    try:
        if not os.path.exists(INVENTORY_FILE):
            raise FileNotFoundError(f"Inventory file not found at: {INVENTORY_FILE}")
        if not os.path.exists(STATUS_FILE):
            raise FileNotFoundError(f"Status file not found at: {STATUS_FILE}")
        
        inventory_df = pd.read_csv(INVENTORY_FILE)
        status_df = pd.read_csv(STATUS_FILE)
        
        print(f"Inventory columns: {inventory_df.columns.tolist()}")
        print(f"Status columns: {status_df.columns.tolist()}")
        print(f"Inventory Process values: {inventory_df['Process'].unique()}")
        
        merged_df = pd.merge(inventory_df, status_df, on='DCP Name', how='left')
        merged_df['Status'] = merged_df['Status'].fillna(4)
        merged_df['Status_Text'] = merged_df['Status'].map(STATUS_MAP).fillna('UNKNOWN')
        
        return merged_df
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        print(traceback.format_exc())
        raise

def prepare_hsa_data(df):
    """Combine ALHSA and NLHSA data into one unified HSA table"""
    try:
        # Filter HSA data (Process contains HSA)
        hsa_df = df[df['Process'].str.contains('HSA', na=False, case=False)].copy()
        
        if len(hsa_df) == 0:
            print("Warning: No HSA data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        hsa_df['Row'] = hsa_df['Line_no']
        hsa_df['Col'] = hsa_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        # Get unique rows and sort them numerically
        all_rows = sort_lines_numerically(hsa_df['Row'].unique())
        
        # Sort: AL lines first, then NL lines
        al_rows = [r for r in all_rows if 'ALHSA' in r]
        nl_rows = [r for r in all_rows if 'NLHSA' in r]
        rows = al_rows + nl_rows
        
        cols = sorted(hsa_df['Col'].unique(), key=int)
        
        print(f"HSA rows found: {rows}")
        print(f"HSA columns found: {cols}")
        
        # Create matrix
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = hsa_df[hsa_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    key = f"{row}_{col}"
                    sensor_details[key] = {
                        'dcp_name': str(data['DCP Name']),
                        'description': str(data['Description']),
                        'location': str(data['Location_Code']),
                        'status': str(data['Status_Text']),
                        'line': str(data['Line_no'])
                    }
                else:
                    data_matrix[row][col] = 'UNKNOWN'
        
        return {
            'rows': rows,
            'cols': cols,
            'data': data_matrix,
            'details': sensor_details
        }
    except Exception as e:
        print(f"Error in prepare_hsa_data: {str(e)}")
        print(traceback.format_exc())
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}

def prepare_dis_assy_data(df):
    """Prepare DIS-ASSY data in matrix format"""
    try:
        # Filter DIS-ASSY data - look for ALDA or NLDA specifically, not just 'DA'
        dis_df = df[df['Process'].str.contains('ALDA|NLDA', na=False, case=False)].copy()
        
        if len(dis_df) == 0:
            print("Warning: No DIS-ASSY data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        dis_df['Row'] = dis_df['Line_no']
        dis_df['Col'] = dis_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        rows = sort_lines_numerically(dis_df['Row'].unique())
        cols = sorted(dis_df['Col'].unique(), key=int)
        
        print(f"DIS-ASSY rows found: {rows}")
        print(f"DIS-ASSY columns found: {cols}")
        
        # Create matrix
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = dis_df[dis_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    key = f"{row}_{col}"
                    sensor_details[key] = {
                        'dcp_name': str(data['DCP Name']),
                        'description': str(data['Description']),
                        'location': str(data['Location_Code']),
                        'status': str(data['Status_Text'])
                    }
                else:
                    data_matrix[row][col] = 'UNKNOWN'
        
        return {
            'rows': rows,
            'cols': cols,
            'data': data_matrix,
            'details': sensor_details
        }
    except Exception as e:
        print(f"Error in prepare_dis_assy_data: {str(e)}")
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
    """Prepare DIS-ASSY data in matrix format"""
    try:
        # Filter DIS-ASSY data (Process contains DA or DIS-ASSY)
        dis_df = df[df['Process'].str.contains('DA|DIS', na=False, case=False)].copy()
        
        if len(dis_df) == 0:
            print("Warning: No DIS-ASSY data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        dis_df['Row'] = dis_df['Line_no']
        dis_df['Col'] = dis_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        rows = sort_lines_numerically(dis_df['Row'].unique())
        cols = sorted(dis_df['Col'].unique(), key=int)
        
        print(f"DIS-ASSY rows found: {rows}")
        print(f"DIS-ASSY columns found: {cols}")
        
        # Create matrix
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = dis_df[dis_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    key = f"{row}_{col}"
                    sensor_details[key] = {
                        'dcp_name': str(data['DCP Name']),
                        'description': str(data['Description']),
                        'location': str(data['Location_Code']),
                        'status': str(data['Status_Text'])
                    }
                else:
                    data_matrix[row][col] = 'UNKNOWN'
        
        return {
            'rows': rows,
            'cols': cols,
            'data': data_matrix,
            'details': sensor_details
        }
    except Exception as e:
        print(f"Error in prepare_dis_assy_data: {str(e)}")
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}

def prepare_aoi_data(df):
    """Prepare AOI data as list"""
    try:
        # Filter AOI data (Process contains STW and Description contains AOI)
        aoi_df = df[df['Process'].str.contains('STW', na=False, case=False)].copy()
        
        # Further filter to only AOI sensors
        aoi_df = aoi_df[aoi_df['Description'].str.contains('AOI', na=False, case=False)]
        
        aoi_list = []
        
        for _, row in aoi_df.iterrows():
            aoi_list.append({
                'LINE': str(row['Line_no']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        aoi_list.sort(key=lambda x: extract_number(x['LINE']))
        print(f"AOI data found: {len(aoi_list)} items")
        return aoi_list
    except Exception as e:
        print(f"Error in prepare_aoi_data: {str(e)}")
        return []

def prepare_sm_data(df):
    """Prepare S Machine data as list"""
    try:
        # Filter SM data (Process contains STW and Description contains SENSOR, but not AOI)
        sm_df = df[df['Process'].str.contains('STW', na=False, case=False)].copy()
        
        # Filter out AOI sensors, keep only SM sensors
        sm_df = sm_df[sm_df['Description'].str.contains('SM', na=False, case=False)]
        
        sm_list = []
        
        for _, row in sm_df.iterrows():
            sm_list.append({
                'LINE': str(row['Line_no']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        sm_list.sort(key=lambda x: extract_number(x['LINE']))
        print(f"SM data found: {len(sm_list)} items")
        return sm_list
    except Exception as e:
        print(f"Error in prepare_sm_data: {str(e)}")
        return []

def prepare_wcs_data(df):
    """Prepare WCS data as list"""
    try:
        # Filter WCS data (Process contains WCS)
        wcs_df = df[df['Process'].str.contains('WCS', na=False, case=False)].copy()
        
        wcs_list = []
        
        for _, row in wcs_df.iterrows():
            wcs_list.append({
                'LINE': str(row['Line_no']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        wcs_list.sort(key=lambda x: extract_number(x['LINE']))
        print(f"WCS data found: {len(wcs_list)} items")
        return wcs_list
    except Exception as e:
        print(f"Error in prepare_wcs_data: {str(e)}")
        print(traceback.format_exc())
        return []

def prepare_hda_data(df):
    """Prepare HDA data in matrix format"""
    try:
        # Filter HDA data (Process contains HDA)
        hda_df = df[df['Process'].str.contains('HDA', na=False, case=False)].copy()
        
        if len(hda_df) == 0:
            print("Warning: No HDA data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        hda_df['Row'] = hda_df['Line_no']
        hda_df['Col'] = hda_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        rows = sort_lines_numerically(hda_df['Row'].unique())
        cols = sorted(hda_df['Col'].unique(), key=int)
        
        print(f"HDA rows found: {rows}")
        
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = hda_df[hda_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    key = f"{row}_{col}"
                    sensor_details[key] = {
                        'dcp_name': str(data['DCP Name']),
                        'description': str(data['Description']),
                        'location': str(data['Location_Code']),
                        'status': str(data['Status_Text'])
                    }
                else:
                    data_matrix[row][col] = 'UNKNOWN'
        
        return {
            'rows': rows,
            'cols': cols,
            'data': data_matrix,
            'details': sensor_details
        }
    except Exception as e:
        print(f"Error in prepare_hda_data: {str(e)}")
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}

def get_status_counts(df):
    """Get counts for each status type"""
    counts = {
        'OK': len(df[df['Status_Text'] == 'OK']),
        'WARN': len(df[(df['Status_Text'] == 'WARN')]),
        'CRITICAL': len(df[df['Status_Text'] == 'CRITICAL']),
        'UNKNOWN': len(df[df['Status_Text'] == 'UNKNOWN'])
    }
    return counts

@app.route('/')
def index():
    """Main dashboard route"""
    try:
        print("Starting dashboard load...")
        
        # Load and merge data
        df = load_and_merge_data()
        
        print("Preparing combined HSA data...")
        hsa_data = prepare_hsa_data(df)
        
        print("Preparing DIS-ASSY data...")
        dis_assy_data = prepare_dis_assy_data(df)
        
        print("Preparing AOI data...")
        aoi_data = prepare_aoi_data(df)
        
        print("Preparing SM data...")
        sm_data = prepare_sm_data(df)
        
        print("Preparing WCS data...")
        wcs_data = prepare_wcs_data(df)
        
        print("Preparing HDA data...")
        hda_data = prepare_hda_data(df)
        
        # Get status counts for initial load
        status_counts = get_status_counts(df)
        
        print(f"Final counts - HSA: {len(hsa_data.get('rows', []))} rows, DIS: {len(dis_assy_data.get('rows', []))} rows, AOI: {len(aoi_data)} items, SM: {len(sm_data)} items, WCS: {len(wcs_data)} items, HDA: {len(hda_data.get('rows', []))} rows")
        
        print("Rendering template...")
        return render_template('sensor_dashboard.html',
                             hsa=hsa_data,
                             dis=dis_assy_data,
                             aoi=aoi_data,
                             sm=sm_data,
                             wcs=wcs_data,
                             hda=hda_data,
                             status_counts=status_counts,
                             now=datetime.now())
    
    except Exception as e:
        error_msg = f"Error loading dashboard: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg, 500

@app.route('/api/sensor-data')
def get_sensor_data():
    """API endpoint to get updated sensor data without page refresh"""
    try:
        df = load_and_merge_data()
        
        # Prepare all data sections
        data = {
            'hsa': prepare_hsa_data(df),
            'dis': prepare_dis_assy_data(df),
            'aoi': prepare_aoi_data(df),
            'sm': prepare_sm_data(df),
            'wcs': prepare_wcs_data(df),
            'hda': prepare_hda_data(df),
            'status_counts': get_status_counts(df),
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        return jsonify(data)
    except Exception as e:
        print(f"Error in API: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"Created data folder at: {DATA_FOLDER}")
        print("Please place your CSV files in the data folder:")
        print(f"  - {INVENTORY_FILE}")
        print(f"  - {STATUS_FILE}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)