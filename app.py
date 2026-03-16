from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

def process_data():
    # Read the CSV file from the file system
    # Assuming sensor_data.csv is in the same directory as app.py
    if not os.path.exists('sensor_data.csv'):
        print("Error: sensor_data.csv not found.")
        return {}

    # Read CSV with separator ' | ' and strip spaces
    df = pd.read_csv('sensor_data.csv', sep='|', skipinitialspace=True)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Clean string values in all columns
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Helper to create matrix structure for Jinja
    def create_section_data(data_frame):
        # Pivot: Index=LINE, Cols=STATION (from DESCRIPTION), Values=STATUS
        # Extract Station number/name
        data_frame = data_frame.copy() # Avoid SettingWithCopyWarning
        data_frame['STATION'] = data_frame['DESCRIPTION'].str.extract(r'(STN\d+)')
        
        pivot = data_frame.pivot(index='LINE', columns='STATION', values='STATUS')
        
        # Sort columns naturally (STN1, STN2... STN10...)
        cols = sorted(pivot.columns, key=lambda x: int(x.replace('STN', '')))
        pivot = pivot[cols]
        
        # Sort rows
        pivot = pivot.sort_index()
        
        # Convert to list of dicts for Jinja
        return {
            'rows': pivot.index.tolist(),
            'cols': pivot.columns.tolist(),
            'data': pivot.to_dict('index')
        }

    # 1. HSA (AL)
    hsa_al_df = df[df['LINE'].str.startswith('ALHSA')]
    hsa_al = create_section_data(hsa_al_df)

    # 2. HSA (NL)
    hsa_nl_df = df[df['LINE'].str.startswith('NLHSA')]
    hsa_nl = create_section_data(hsa_nl_df)

    # 3. DIS-ASSY
    dis_df = df[df['LINE'].str.contains('DIS-ASSY')]
    dis = create_section_data(dis_df)

    # 4. AOI
    aoi_df = df[df['LINE'].str.startswith('AOI')]
    aoi = aoi_df[['LINE', 'STATUS']].to_dict('records')

    # 5. S MACHINE
    sm_df = df[df['LINE'].str.startswith('SM')]
    sm = sm_df[['LINE', 'STATUS']].to_dict('records')

    # 6. WCS
    wcs_df = df[df['LINE'].str.startswith('WCS')]
    wcs = wcs_df[['LINE', 'STATUS']].to_dict('records')

    # 7. HDA
    hda_df = df[df['LINE'].str.startswith('NLHDA')]
    hda = create_section_data(hda_df)

    return {
        'hsa_al': hsa_al,
        'hsa_nl': hsa_nl,
        'dis': dis,
        'aoi': aoi,
        'sm': sm,
        'wcs': wcs,
        'hda': hda
    }

@app.route('/')
def index():
    data = process_data()
    return render_template('index.html', **data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
