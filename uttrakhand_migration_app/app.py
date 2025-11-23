from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import joblib
import os

app = Flask(__name__, static_folder='static', template_folder='templates')


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PIPE = os.path.join(MODEL_DIR, "best_pipeline.pkl")
FEATURES_PKL = os.path.join(MODEL_DIR, "feature_names.pkl")

DATA_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "Uttarakhand_Migration", "Cleaned_Migration_Data.xlsx"))

# Load model artifacts safely 
model = None
feature_names = []
try:
    model = joblib.load(MODEL_PIPE)
    feature_names = joblib.load(FEATURES_PKL)
    print("Model & features loaded.")
except Exception as e:
    print("Model load warning:", e)
    model = None
    feature_names = []

try:
    df = pd.read_excel(DATA_PATH)
    df['area_name'] = df['area_name'].astype(str)
except Exception as e:
    print("Data load warning:", e)
    # create an empty dataframe with minimal columns to avoid runtime KeyErrors
    df = pd.DataFrame(columns=['area_name', 'area_type', 'total_migrants_with_duration_0_9_person'])

# exclude any rows that look like the state totals
districts = sorted([d for d in df['area_name'].dropna().unique().tolist() if 'uttarakhand' not in d.lower()])

# Top-3 reason mapping per district (extendable)
district_reasons = {
    "Dehradun": ["Employment", "Education", "Urban facilities"],
    "Haridwar": ["Industrial jobs", "Infrastructure", "Family migration / Networks"],
    "Pithoragarh": ["Climate stress (crop failure, landslides)", "Agriculture distress", "Employment"],
    "Almora": ["Agriculture distress", "Climate stress (erratic rainfall)", "Limited local jobs / Employment"],
    "Nainital": ["Tourism jobs", "Education (higher studies)", "Employment (service sector)"],
    "Pauri_Garhwal": ["Outmigration for jobs", "Education (lack of higher education locally)", "Agriculture distress"],
    "Bageshwar": ["Agriculture & livestock distress", "Limited local employment", "Outmigration of youth for jobs"],
    "Chamoli": ["Disaster & climate vulnerability (floods/landslides)", "Hydropower/project displacement", "Seasonal tourism jobs"],
    "Champawat": ["Agricultural decline", "Lack of local industries/employment", "Education & youth outmigration"],
    "Rudraprayag": ["Natural hazard risk (floods/landslides)", "Pilgrimage/tourism seasonality (unstable income)", "Limited year-round employment"],
    "Tehri Garhwal": ["Hydropower project displacement & resettlement", "Tourism & pilgrimage-linked jobs", "Agriculture distress / smallholdings"],
    "Udham_Singh_Nagar": ["Industrial & factory jobs (inflow/outflow dynamics)", "Agricultural labour migration", "Urban housing & infrastructure pull factors"],
    "Uttarkashi": ["Climate & disaster risk (glacial/river impacts)", "Limited connectivity & services (push)", "Tourism/seasonal employment (pull)"]
}

def approx_reasons(d):
    # return mapped reasons if present, else a reasonable default list
    return district_reasons.get(d, ["Employment", "Education", "Climate stress (migration)"])


@app.route('/')
def home():
    # years options: 5,10,...50
    years_options = [5,10,15,20,25,30,35,40,45,50]
    return render_template('index.html', districts=districts, years_options=years_options)


@app.route('/predict', methods=['POST'])
def predict():
    try:
        payload = request.get_json() or request.form
        district = payload.get('district')
        years = int(payload.get('years', 5))

        # Filter dataset
        df_dist = df[df['area_name'] == district]
        inflow_base = None
        if not df_dist.empty and 'total_migrants_with_duration_0_9_person' in df_dist.columns:
            inflow_base = df_dist['total_migrants_with_duration_0_9_person'].mean()
            if np.isnan(inflow_base) or inflow_base == 0:
                inflow_base = None

        # Fallback: use saved ML model if available to estimate base
        if inflow_base is None:
            if model is not None and len(feature_names) > 0:
                X0 = pd.DataFrame([[0]*len(feature_names)], columns=feature_names)
                try:
                    inflow_base = float(model.predict(X0)[0])
                except Exception:
                    inflow_base = 1000.0
            else:
                inflow_base = 1000.0

        # Growth heuristic from area_type if available
        area_type = None
        if not df_dist.empty and 'area_type' in df_dist.columns and not df_dist['area_type'].isna().all():
            area_type = df_dist['area_type'].mode()[0]
        growth_rate = 0.06 if (isinstance(area_type, str) and area_type.lower() == 'urban') else 0.04

        # Build projections using the same formula (years 1..N)
        projections = []
        for y in range(1, years + 1):
            proj_in = inflow_base * (1 + growth_rate) ** (y / 5)
            proj_out = proj_in * 0.7
            projections.append({
                "year": int(y),
                "inflow": float(round(proj_in, 2)),
                "outflow": float(round(proj_out, 2))
            })

        inflow_pred = projections[-1]['inflow']
        outflow_pred = projections[-1]['outflow']

        # average growth (relative to first projected year)
        if len(projections) >= 2 and projections[0]['inflow'] != 0:
            avg_growth = round(((projections[-1]['inflow'] - projections[0]['inflow']) / projections[0]['inflow']) * 100, 2)
        else:
            avg_growth = 0.0

        reasons = approx_reasons(district)

        return jsonify({
            "district": district,
            "inflow_pred": int(round(inflow_pred)),
            "outflow_pred": int(round(outflow_pred)),
            "table_data": projections,
            "avg_growth": avg_growth,
            "reasons": reasons
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
