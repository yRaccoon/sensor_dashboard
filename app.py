from flask import Flask, render_template
import pandas as pd
import os
import re
import traceback

app = Flask(__name__)

# Configuration
DATA_FOLDER = 'data'
INVENTORY_FILE = os.path.join(DATA_FOLDER, 'DCP_Inventory_R1.csv')
STATUS_FILE = os.path.join(DATA_FOLDER, 'DCP_Status.csv')

# Status mapping with your requested colors:
# 0 = green (OK)
# 1,2 = yellow (WARN)
# 3 = red (CRITICAL)
# 4 = grey (UNKNOWN)
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
        print(f"Attempting to load inventory file: {INVENTORY_FILE}")
        print(f"Attempting to load status file: {STATUS_FILE}")
        
        # Check if files exist
        if not os.path.exists(INVENTORY_FILE):
            raise FileNotFoundError(f"Inventory file not found at: {INVENTORY_FILE}")
        if not os.path.exists(STATUS_FILE):
            raise FileNotFoundError(f"Status file not found at: {STATUS_FILE}")
        
        # Load CSV files
        inventory_df = pd.read_csv(INVENTORY_FILE)
        status_df = pd.read_csv(STATUS_FILE)
        
        print(f"Inventory loaded: {len(inventory_df)} rows")
        print(f"Status loaded: {len(status_df)} rows")
        
        # Merge dataframes on DCP Name
        merged_df = pd.merge(inventory_df, status_df, on='DCP Name', how='left')
        
        # Fill any NaN status values with 4 (UNKNOWN)
        merged_df['Status'] = merged_df['Status'].fillna(4)
        
        # Convert status codes to text
        merged_df['Status_Text'] = merged_df['Status'].map(STATUS_MAP)
        
        # Fill any remaining NaN in Status_Text with 'UNKNOWN'
        merged_df['Status_Text'] = merged_df['Status_Text'].fillna('UNKNOWN')
        
        return merged_df
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        print(traceback.format_exc())
        raise

def prepare_hsa_al_data(df):
    """Prepare HSA AL data in matrix format"""
    try:
        # Filter HSA AL data
        hsa_al_df = df[df['Line'].str.contains('ALHSA', na=False)].copy()
        
        if len(hsa_al_df) == 0:
            print("Warning: No HSA AL data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        hsa_al_df['Row'] = hsa_al_df['Line']
        hsa_al_df['Col'] = hsa_al_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        # Get unique rows and sort them numerically
        rows = sort_lines_numerically(hsa_al_df['Row'].unique())
        cols = sorted(hsa_al_df['Col'].unique(), key=int)
        
        # Create matrix
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = hsa_al_df[hsa_al_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    # Store details for tooltip
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
        print(f"Error in prepare_hsa_al_data: {str(e)}")
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}

def prepare_hsa_nl_data(df):
    """Prepare HSA NL data in matrix format"""
    try:
        # Filter HSA NL data
        hsa_nl_df = df[df['Line'].str.contains('NLHSA', na=False)].copy()
        
        if len(hsa_nl_df) == 0:
            print("Warning: No HSA NL data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        hsa_nl_df['Row'] = hsa_nl_df['Line']
        hsa_nl_df['Col'] = hsa_nl_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        # Get unique rows and sort them numerically
        rows = sort_lines_numerically(hsa_nl_df['Row'].unique())
        cols = sorted(hsa_nl_df['Col'].unique(), key=int)
        
        print(f"HSA NL rows found: {rows}")
        
        # Create matrix
        data_matrix = {}
        sensor_details = {}
        
        for row in rows:
            data_matrix[row] = {}
            row_data = hsa_nl_df[hsa_nl_df['Row'] == row]
            for col in cols:
                status_data = row_data[row_data['Col'] == col]
                if not status_data.empty:
                    data = status_data.iloc[0]
                    data_matrix[row][col] = data['Status_Text']
                    # Store details for tooltip
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
        print(f"Error in prepare_hsa_nl_data: {str(e)}")
        return {'rows': [], 'cols': [], 'data': {}, 'details': {}}

def prepare_dis_assy_data(df):
    """Prepare DIS-ASSY data in matrix format"""
    try:
        # Filter DIS-ASSY data
        dis_df = df[df['Process'] == 'DIS-ASSY'].copy()
        
        if len(dis_df) == 0:
            print("Warning: No DIS-ASSY data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        dis_df['Row'] = dis_df['Line']
        dis_df['Col'] = dis_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        # Get unique rows and sort them numerically
        rows = sort_lines_numerically(dis_df['Row'].unique())
        cols = sorted(dis_df['Col'].unique(), key=int)
        
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
                    # Store details for tooltip
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
        aoi_df = df[df['Process'] == 'AOI'].copy()
        aoi_list = []
        
        for _, row in aoi_df.iterrows():
            aoi_list.append({
                'LINE': str(row['Line']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        # Sort AOI list numerically
        aoi_list.sort(key=lambda x: extract_number(x['LINE']))
        
        return aoi_list
    except Exception as e:
        print(f"Error in prepare_aoi_data: {str(e)}")
        return []

def prepare_sm_data(df):
    """Prepare S Machine data as list"""
    try:
        sm_df = df[df['Process'] == 'S_MACHINE'].copy()
        sm_list = []
        
        for _, row in sm_df.iterrows():
            sm_list.append({
                'LINE': str(row['Line']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        # Sort SM list numerically
        sm_list.sort(key=lambda x: extract_number(x['LINE']))
        
        return sm_list
    except Exception as e:
        print(f"Error in prepare_sm_data: {str(e)}")
        return []

def prepare_wcs_data(df):
    """Prepare WCS data as list"""
    try:
        wcs_df = df[df['Process'] == 'WCS'].copy()
        wcs_list = []
        
        for _, row in wcs_df.iterrows():
            wcs_list.append({
                'LINE': str(row['Line']),
                'STATUS': str(row['Status_Text']),
                'DCP_NAME': str(row['DCP Name']),
                'DESCRIPTION': str(row['Description']),
                'LOCATION': str(row['Location_Code'])
            })
        
        # Sort WCS list numerically
        wcs_list.sort(key=lambda x: extract_number(x['LINE']))
        
        return wcs_list
    except Exception as e:
        print(f"Error in prepare_wcs_data: {str(e)}")
        return []

def prepare_hda_data(df):
    """Prepare HDA data in matrix format"""
    try:
        # Filter HDA data
        hda_df = df[df['Process'] == 'HDA'].copy()
        
        if len(hda_df) == 0:
            print("Warning: No HDA data found")
            return {'rows': [], 'cols': [], 'data': {}, 'details': {}}
        
        # Extract row (line) and column (station number)
        hda_df['Row'] = hda_df['Line']
        hda_df['Col'] = hda_df['Description'].str.extract(r'STN(\d+)').fillna('1')
        
        # Get unique rows and sort them numerically
        rows = sort_lines_numerically(hda_df['Row'].unique())
        cols = sorted(hda_df['Col'].unique(), key=int)
        
        # Create matrix
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
                    # Store details for tooltip
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

@app.route('/')
def index():
    """Main dashboard route"""
    try:
        print("Starting dashboard load...")
        
        # Load and merge data
        df = load_and_merge_data()
        
        print("Preparing HSA AL data...")
        hsa_al_data = prepare_hsa_al_data(df)
        
        print("Preparing HSA NL data...")
        hsa_nl_data = prepare_hsa_nl_data(df)
        
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
        
        print("Rendering template...")
        return render_template('sensor_dashboard.html',
                             hsa_al=hsa_al_data,
                             hsa_nl=hsa_nl_data,
                             dis=dis_assy_data,
                             aoi=aoi_data,
                             sm=sm_data,
                             wcs=wcs_data,
                             hda=hda_data)
    
    except Exception as e:
        error_msg = f"Error loading dashboard: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg, 500

if __name__ == '__main__':
    # Create data folder if it doesn't exist
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"Created data folder at: {DATA_FOLDER}")
        print("Please place your CSV files in the data folder:")
        print(f"  - {INVENTORY_FILE}")
        print(f"  - {STATUS_FILE}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)