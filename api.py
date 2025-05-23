from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
import numpy as np
from functools import wraps

app = Flask(__name__)
CORS(app)

# Mock user database
users = {
    "sales_team": {"password": "team123", "role": "sales_team"},
    "individual": {"password": "ind123", "role": "individual"}
}

# Load data
df = pd.read_csv('product_sales_logs(1).csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or token not in users:
            return jsonify({'message': 'Token is missing or invalid!'}), 403
        return f(*args, **kwargs)
    return decorated

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username in users and users[username]['password'] == password:
        return jsonify({
            'message': 'Login successful',
            'token': username,
            'role': users[username]['role']
        })
    return jsonify({'message': 'Invalid credentials'}), 401

# Logout endpoint
@app.route('/logout', methods=['POST'])
@token_required
def logout():
    return jsonify({'message': 'Logout successful'})

# Customer data endpoint
@app.route('/api/customer-data', methods=['GET'])
@token_required
def get_customer_data():
    customer_name = request.args.get('customer_name')
    start_date = request.args.get('start_date', default=df['Timestamp'].min().date().isoformat())
    end_date = request.args.get('end_date', default=df['Timestamp'].max().date().isoformat())
    
    filtered_df = df[
        (df['Customer Name'] == customer_name) &
        (df['Timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
        (df['Timestamp'].dt.date <= pd.to_datetime(end_date).date())
    ]
    
    return jsonify({
        'customer_data': filtered_df.to_dict(orient='records')
    })

# Engagement alerts endpoint
@app.route('/api/engagement-alerts', methods=['GET'])
@token_required
def get_engagement_alerts():
    start_date = request.args.get('start_date', default=df['Timestamp'].min().date().isoformat())
    end_date = request.args.get('end_date', default=df['Timestamp'].max().date().isoformat())
    
    filtered_df = df[
        (df['Timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
        (df['Timestamp'].dt.date <= pd.to_datetime(end_date).date())
    ]
    
    engagement_trends = []
    for product in filtered_df['Product Name'].unique():
        product_data = filtered_df[filtered_df['Product Name'] == product]
        weekly_data = product_data.groupby(pd.Grouper(key='Timestamp', freq='W')).size()
        if len(weekly_data) > 1:
            trend = (weekly_data.iloc[-1] - weekly_data.iloc[-2]) / weekly_data.iloc[-2] * 100
            engagement_trends.append({
                'product': product,
                'trend_percent': trend,
                'last_week': int(weekly_data.iloc[-1]),
                'previous_week': int(weekly_data.iloc[-2]),
                'alert': 'rising' if trend > 20 else 'dropping' if trend < -20 else 'stable'
            })
    
    return jsonify({'engagement_trends': engagement_trends})

# High value customers endpoint
@app.route('/api/high-value-customers', methods=['GET'])
@token_required
def get_high_value_customers():
    start_date = request.args.get('start_date', default=df['Timestamp'].min().date().isoformat())
    end_date = request.args.get('end_date', default=df['Timestamp'].max().date().isoformat())
    
    filtered_df = df[
        (df['Timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
        (df['Timestamp'].dt.date <= pd.to_datetime(end_date).date())
    ]
    
    customer_data = filtered_df.groupby('User ID').agg({
        'User Interaction': 'count',
        'Sales(P)': 'sum',
        'Session Duration(s)': 'mean'
    }).sort_values('Sales(P)', ascending=False).head(10)
    
    if len(customer_data) > 1:
        kmeans = KMeans(n_clusters=3, random_state=42)
        customer_data['segment'] = kmeans.fit_predict(customer_data[['User Interaction', 'Sales(P)']])
    
    return jsonify({
        'customers': customer_data.reset_index().to_dict(orient='records')
    })

# Report generation endpoint
@app.route('/api/generate-report', methods=['POST'])
@token_required
def generate_report():
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    filtered_df = df[
        (df['Timestamp'].dt.date >= pd.to_datetime(start_date).date()) &
        (df['Timestamp'].dt.date <= pd.to_datetime(end_date).date())
    ]
    
    total_sales = filtered_df['Sales(P)'].sum()
    conversion_rate = filtered_df['Conversion Status'].value_counts(normalize=True).get('Converted', 0)
    avg_session = filtered_df['Session Duration(s)'].mean()
    top_product = filtered_df.groupby('Product Name')['Sales(P)'].sum().idxmax()
    
    return jsonify({
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'conversion_rate': conversion_rate,
        'avg_session': avg_session,
        'top_product': top_product
    })

if __name__ == '__main__':
    app.run(debug=True)