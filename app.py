import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
from sklearn.cluster import KMeans
from scipy import stats
import altair as alt
import requests
from io import BytesIO
import openpyxl
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.utils.dataframe import dataframe_to_rows
import base64
import json
import tempfile
import uuid

# Page Config
st.set_page_config(
    page_title="AI-Solutions Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Remove top space above title
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;  /* Small top padding */
        }
        .header-title {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 0;
        }
        .css-1v0mbdj.ef3psqc12 {  /* Fix for button alignment if needed */
            margin-top: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.username = None

# Flask API URL
FLASK_API_URL = "http://localhost:5000"

# Function to authenticate user
def authenticate_user(username, password):
    try:
        response = requests.post(
            f"{FLASK_API_URL}/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.logged_in = True
            st.session_state.token = data['token']
            st.session_state.role = data['role']
            st.session_state.username = username
            return True, data['message']
        else:
            return False, response.json()['message']
    except requests.exceptions.RequestException as e:
        return False, f"Error connecting to server: {str(e)}"

def show_login_page():
    st.markdown("""
        <style>
        .centered {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.9);
            padding: 2.5rem;
            border-radius: 1.5rem;
            box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            width: 100%;
            max-width: 400px;
            backdrop-filter: blur(10px);
            border: 1px solid #e1e1e1;
        }
        .login-header {
            font-size: 2rem;
            font-weight: 700;
            color: #003366;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .login-sub {
            font-size: 0.95rem;
            color: #444;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="centered">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712109.png", width=20)
        st.markdown('<div class="login-header">AI-Solutions Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Welcome back to your intelligent sales analytics platform</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                if username and password:
                    success, message = authenticate_user(username, password)
                    if success:
                        st.success(f" {message}")
                        st.rerun()
                    else:
                        st.error(f" {message}")
                else:
                    st.warning("⚠️ Please enter both username and password.")
        st.markdown('</div>', unsafe_allow_html=True)

# Logout Function
def logout():
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.username = None
    st.success("Logged out successfully!")
    st.rerun()

# Load Data
@st.cache_data
def load_data():
    data = pd.read_csv('product_sales_logs(1).csv')
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
    return data

# Function to generate Excel report
def generate_excel_report(report_data, filtered_df):
    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_charts = wb.create_sheet("Charts")

    # Summary Sheet: Metrics
    ws_summary.append(["AI-Solutions Sales Dashboard Report"])
    ws_summary.append([])
    ws_summary.append(["Metric", "Value"])
    ws_summary.append(["Date Range", f"{report_data['start_date']} to {report_data['end_date']}"])
    ws_summary.append(["Total Sales", f"P{report_data['total_sales']:,.0f}"])
    ws_summary.append(["Conversion Rate", f"{report_data['conversion_rate']:.1%}"])
    ws_summary.append(["Average Session Duration", f"{report_data['avg_session']:.0f}s"])
    ws_summary.append(["Top Product", report_data['top_product']])
    ws_summary.append([])

    # Top Products by Sales
    ws_summary.append(["Top Products by Sales"])
    top_products = filtered_df.groupby('Product Name')['Sales(P)'].sum().nlargest(5).reset_index()
    ws_summary.append(["Product Name", "Sales(P)"])
    for row in dataframe_to_rows(top_products, index=False, header=False):
        ws_summary.append(row)

    # Charts Sheet: Sales by Product (Bar Chart)
    ws_charts.append(["Top Products by Sales"])
    ws_charts.append(["Product Name", "Sales(P)"])
    for row in dataframe_to_rows(top_products, index=False, header=False):
        ws_charts.append(row)

    chart1 = BarChart()
    chart1.title = "Top Products by Sales"
    chart1.y_axis.title = "Sales(P)"
    chart1.x_axis.title = "Product Name"
    data = Reference(ws_charts, min_col=2, min_row=2, max_row=2+len(top_products) )
    cats = Reference(ws_charts, min_col=1, min_row=3, max_row=2+len(top_products))
    chart1.add_data(data, titles_from_data=True)
    chart1.set_categories(cats)
    ws_charts.add_chart(chart1, "A10")

    # Engagement Trends (Line Chart)
    start_row_engagement = 2 + len(top_products) + 2
    ws_charts.append([])
    ws_charts.append(["Engagement Trends Over Time"])
    weekly_engagement = (
        filtered_df.groupby([
            pd.Grouper(key='Timestamp', freq='W-MON'),
            'User Interaction'
        ])
        .size()
        .reset_index(name='Count')
    )
    pivot_engagement = weekly_engagement.pivot(index='Timestamp', columns='User Interaction', values='Count').fillna(0)
    pivot_engagement.reset_index(inplace=True)
    ws_charts.append(["Date"] + list(pivot_engagement.columns[1:]))
    for row in dataframe_to_rows(pivot_engagement, index=False, header=False):
        ws_charts.append([row[0].strftime('%Y-%m-%d') if isinstance(row[0], pd.Timestamp) else row[0]] + list(row[1:]))

    chart2 = LineChart()
    chart2.title = "Engagement Trends Over Time"
    chart2.y_axis.title = "Interaction Count"
    chart2.x_axis.title = "Date"
    data = Reference(ws_charts, min_col=2, min_row=start_row_engagement+1, max_row=start_row_engagement+1+len(pivot_engagement), max_col=1+len(pivot_engagement.columns)-1)
    cats = Reference(ws_charts, min_col=1, min_row=start_row_engagement+2, max_row=start_row_engagement+1+len(pivot_engagement))
    chart2.add_data(data, titles_from_data=True)
    chart2.set_categories(cats)
    ws_charts.add_chart(chart2, "A25")

    # Sales by Source Channel (Pie Chart)
    start_row_source = start_row_engagement + len(pivot_engagement) + 3
    ws_charts.append([])
    ws_charts.append(["Sales by Source Channel"])
    source_data = (
        filtered_df.groupby('Source Channel')['Sales(P)']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    ws_charts.append(["Source Channel", "Sales(P)"])
    for row in dataframe_to_rows(source_data, index=False, header=False):
        ws_charts.append(row)

    chart3 = PieChart()
    chart3.title = "Sales by Source Channel"
    data = Reference(ws_charts, min_col=2, min_row=start_row_source+1, max_row=start_row_source+1+len(source_data))
    cats = Reference(ws_charts, min_col=1, min_row=start_row_source+2, max_row=start_row_source+1+len(source_data))
    chart3.add_data(data, titles_from_data=True)
    chart3.set_categories(cats)
    ws_charts.add_chart(chart3, "A40")

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# Sales Team Dashboard (Unchanged)
def show_sales_team_dashboard():
    df = load_data()

    with st.sidebar:
        st.logo("images/AI-Solutions.jpg")
        st.markdown(f"**Logged in as:** {st.session_state.username} ({st.session_state.role})")
        if st.button("Logout"):
            logout()

    # CSS 
    st.markdown(
        """ <style>
        [data-testid="stSelectbox"], [data-baseweb="select"] {
            border: 2px solid lightblue !important;
            border-radius: 5px !important;
            background-color: white !important;
        }
        [data-testid="stMultiSelectTag"] {
            background-color: white !important;
            color: navy !important;
            border: 1px solid lightblue !important;
            border-radius: 5px !important;
            padding: 4px 8px !important;
        }
        [data-testid="stMultiSelectTag"]:hover {
            background-color: lightblue !important;
            color: navy !important;
        }
        [data-baseweb="popover"] {
            background-color: white !important;
            border: 1px solid lightblue !important;
            border-radius: 5px !important;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1) !important;
        }
        [data-baseweb="option"] {
            background-color: white !important;
            color: navy !important;
            padding: 8px 12px !important;
        }
        [data-baseweb="option"]:hover {
            background-color: lightblue !important;
            color: navy !important;
        }
        [data-testid="stSidebar"] * {
            color: navy !important;
        }
        .alert-popup {
            background-color: #f8f9fa;
            border: 1px solid #007bff;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
        }
        .alert-icon {
            margin-right: 10px;
            font-size: 1.2em;
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            padding: 10px 0;
        }
        .header-title {
            color: navy;
            font-size: 1.5rem;
            margin: 0;
        }
        .header-controls {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .notification-dropdown {
            background-color: white;
            border: 1px solid #007bff;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            width: 300px;
            max-height: 350px;
            overflow-y: auto;
            z-index: 1000;
            margin-top: 10px;
        }
        .notification-item {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .notification-item.unread {
            font-weight: bold;
            background-color: #f0f4f8;
        }
        .notification-item.read {
            color: #666;
        }
        .notification-item button {
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 3px 8px;
            cursor: pointer;
        }
        .notification-item button:hover {
            background-color: #0056b3;
        }
        .generate-report-btn {
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 3px 8px;
            cursor: pointer;
        }
        </style>
        """, unsafe_allow_html=True
    )

    # Initialize session state for notifications and dropdown
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    if 'show_dropdown' not in st.session_state:
        st.session_state.show_dropdown = False
    if 'excel_data' not in st.session_state:
        st.session_state.excel_data = None

    filtered_df = df.copy()
    filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'])
    filtered_df['Timestamp'] = filtered_df['Timestamp'].dt.date
    filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'], errors='coerce')
    filtered_df['Date'] = filtered_df['Timestamp'].dt.date

    # Dashboard Header with Buttons
    col1, col2 = st.columns([6, 2.5])
    with col1:
        st.markdown(
            '<h4 class="header-title">📊 AI-Solutions Sales Analytics Dashboard</h4>',
            unsafe_allow_html=True
        )
    with col2:
        col_btn1, col_btn2 = st.columns([0.1, 0.5])
        with col_btn1:
            if st.button("🔔"):
                st.session_state.show_dropdown = not st.session_state.show_dropdown
        with col_btn2:
            if st.button("📥 Generate Report", use_container_width=True):
                try:
                    response = requests.post(
                        f"{FLASK_API_URL}/api/generate-report",
                        json={
                            "start_date": filtered_df['Timestamp'].min().date().isoformat(),
                            "end_date": filtered_df['Timestamp'].max().date().isoformat()
                        },
                        headers={"Authorization": st.session_state.token}
                    )
                    if response.status_code == 200:
                        report_data = response.json()
                        st.session_state.excel_data = generate_excel_report(report_data, filtered_df)
                        st.success("Excel report generated successfully!")
                    else:
                        st.error("Failed to generate report from server.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error generating report: {str(e)}")

    # Sidebar Filters
    with st.sidebar:
        st.header("🔍 Filter Data")
        st.markdown("Use the filters below to customize your view.")
        select_customer = st.multiselect("👤 Select Customer", df["Customer Name"].unique())
        selected_country = st.multiselect("🌍 Select Country", df["Country"].unique())
        selected_product = st.multiselect("🖥️ Select Product", df["Product Name"].unique())
        selected_interaction = st.multiselect("🛠️ User Interaction ", df["User Interaction"].unique())
        selected_conversion = st.multiselect("🔄 Conversion Status", df['Conversion Status'].unique())
        start_date = st.date_input("📅 Start Date", value=df['Timestamp'].min().date())
        end_date = st.date_input("📅 End Date", value=df['Timestamp'].max().date())

    # Apply filters
    filtered_df = df[
        (df['Timestamp'].dt.date >= start_date) &
        (df['Timestamp'].dt.date <= end_date)
    ]
    if select_customer:
        filtered_df = filtered_df[filtered_df['Customer Name'].isin(select_customer)]
    if selected_country:
        filtered_df = filtered_df[filtered_df['Country'].isin(selected_country)]
    if selected_product:
        filtered_df = filtered_df[filtered_df['Product Name'].isin(selected_product)]
    if selected_interaction:
        filtered_df = filtered_df[filtered_df['User Interaction'].isin(selected_interaction)]
    if selected_conversion:
        filtered_df = filtered_df[filtered_df['Conversion Status'].isin(selected_conversion)]

# === Metric Calculations ===
    total_sales = filtered_df['Sales(P)'].sum()
    converted_sales = filtered_df[filtered_df['Conversion Status'] == 'Converted']['Sales(P)'].sum()
    conversion_rate = converted_sales / total_sales if total_sales > 0 else 0
    avg_sales_per_session = filtered_df.groupby('Session Duration(s)')['Sales(P)'].sum().mean() if not filtered_df.empty else 0
    top_product = filtered_df.groupby('Product Name')['Sales(P)'].sum().idxmax()

# === Baseline Targets (You can tune these based on business logic) ===
    baseline_metrics = {
     "Total Sales": 407000,  # e.g., daily or weekly target
     "Conversion Rate": 0.99, 
     "Avg. Session": 12000,  # seconds
}

# === Delta Calculations ===
    delta_sales = total_sales - baseline_metrics["Total Sales"]
    delta_conversion = conversion_rate - baseline_metrics["Conversion Rate"]
    delta_session = avg_sales_per_session - baseline_metrics["Avg. Session"]

# === Utility to Get Color and Arrow Based on Delta ===
    def get_style_and_icon(delta):
     if delta > 0:
        return "#4CAF50", "↑"  # green
     elif delta < 0:
        return "#F44336", "↓"  # red
     else:
        return "#FF8C00", "→"  # ember/orange

# === Custom Render Function ===
    def render_metric_card(title, value, delta, suffix="", is_percent=False):
     color, arrow = get_style_and_icon(delta)
     delta_display = f"{arrow} {delta:+.1%}" if is_percent else f"{arrow} {delta:+,.0f}"
     st.markdown(f"""
        <div style="
            border-radius: 12px;
            padding: 10px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e0eafc 100%);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            text-align: center;
            border: 1px solid #E0E0E0;
        ">
            <div style="font-size: 12px; color: #555; margin-bottom: 4px; font-weight: 500;">{title}</div>
            <div style="font-size: 18px; font-weight: bold; color: #1a1a1a;">{value}{suffix}</div>
            <div style="font-size: 13px; font-weight: 500; color: {color}; margin-top: 2px;">{delta_display}</div>
        </div>
    """, unsafe_allow_html=True)

# === Display Enhanced Metric Cards ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
     render_metric_card("Total Sales", f"P{total_sales:,.0f}", delta_sales, suffix="")

    with col2:
     render_metric_card("Conversions", f"{conversion_rate:.1%}", delta_conversion, is_percent=True)

    with col3:
     render_metric_card("Avg. Session", f"{avg_sales_per_session:.0f}", delta_session, suffix="s")

    with col4:
     render_metric_card("Top Product", top_product, 0)  # no delta for top product

    # Display Excel download link if report is generated
    if st.session_state.excel_data:
        st.download_button(
            label="Download Excel Report",
            data=st.session_state.excel_data,
            file_name="sales_dashboard_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Add spacing
    st.markdown(
        '<div style="margin-bottom: 20px;"></div>',
        unsafe_allow_html=True
    )

    # Generate notifications
    if 'notifications_generated' not in st.session_state:
        st.session_state.notifications_generated = True
        notifications = []
        weekly_engagement = (
            filtered_df.groupby([
                pd.Grouper(key='Timestamp', freq='W-MON'),
                'Product Name'
            ])
            .agg({
                'Is Demo Request': 'sum',
                'Is AI Assistant Used': 'sum'
            })
            .reset_index()
        )
        for product in weekly_engagement['Product Name'].unique():
            product_data = weekly_engagement[weekly_engagement['Product Name'] == product]
            for metric in ['Is Demo Request', 'Is AI Assistant Used']:
                if len(product_data) >= 2:
                    current = product_data[metric].iloc[-1]
                    previous = product_data[metric].iloc[-2]
                    if previous > 0:
                        change_pct = ((current - previous) / previous) * 100
                        if abs(change_pct) > 20:
                            status = "rise" if change_pct > 0 else "drop"
                            metric_name = "Demo Requests" if metric == 'Is Demo Request' else "AI Assistant Usage"
                            status_icon = "📈" if status == "rise" else "📉"
                            message = f"{status_icon} {product}: {metric_name} {status} by {abs(change_pct):.1f}% week-over-week."
                            notifications.append({
                                'id': f"engagement_{product}_{metric}",
                                'message': message,
                                'status': status,
                                'read': False
                            })
        user_engagement = (
            filtered_df.groupby('User ID')
            .agg({
                'Is Demo Request': 'sum',
                'Is AI Assistant Used': 'sum',
                'Session Duration(s)': 'sum'
            })
            .reset_index()
        )
        user_engagement['Total Interactions'] = user_engagement['Is Demo Request'] + user_engagement['Is AI Assistant Used']
        if len(user_engagement) >= 3:
            X = user_engagement[['Is Demo Request', 'Is AI Assistant Used', 'Total Interactions']].fillna(0)
            kmeans = KMeans(n_clusters=min(3, len(X)), random_state=42)
            user_engagement['Cluster'] = kmeans.fit_predict(X)
            cluster_summary = user_engagement.groupby('Cluster')['Total Interactions'].mean().reset_index()
            high_value_cluster = cluster_summary['Cluster'].iloc[cluster_summary['Total Interactions'].idxmax()]
            high_value_users = user_engagement[user_engagement['Cluster'] == high_value_cluster]
            if not high_value_users.empty:
                message = f"High-Value Customers: Identified {len(high_value_users)} users with high engagement (frequent demo requests/AI assistant usage)."
                notifications.append({
                    'id': 'high_value_users',
                    'message': message,
                    'status': 'high-value',
                    'read': False
                })
        weekly_sales = (
            filtered_df.groupby(pd.Grouper(key='Timestamp', freq='W-MON'))['Sales(P)']
            .sum()
            .reset_index()
        )
        if len(weekly_sales) >= 2:
            current_sales = weekly_sales['Sales(P)'].iloc[-1]
            previous_sales = weekly_sales['Sales(P)'].iloc[-2]
            if previous_sales > 0:
                sales_change_pct = ((current_sales - previous_sales) / previous_sales) * 100
                if abs(sales_change_pct) > 20:
                    status = "spike" if sales_change_pct > 0 else "drop"
                    status_icon = "📈" if status == "spike" else "📉"
                    message = f"{status_icon} Total Sales {status} by {abs(sales_change_pct):.1f}% week-over-week (P{current_sales:,.0f})."
                    notifications.append({
                        'id': f"sales_{status}",
                        'message': message,
                        'status': status,
                        'read': False
                    })
        total_sales_value = filtered_df['Sales(P)'].sum()
        product_sales = filtered_df.groupby('Product Name')['Sales(P)'].sum().reset_index()
        low_performing_threshold = total_sales_value * 0.05
        low_performing_products = product_sales[product_sales['Sales(P)'] < low_performing_threshold]
        if not low_performing_products.empty:
            message = f"Low-Performing Products: {len(low_performing_products)} products contribute less than P{low_performing_threshold:,.0f} in sales."
            notifications.append({
                'id': 'low_performing_products',
                'message': message,
                'status': 'low-performance',
                'read': False
            })
        if not filtered_df.empty:
            top_spenders = filtered_df.nlargest(5, 'Sales(P)')
            if not top_spenders.empty:
                message = f"Top Spenders: {len(top_spenders)} customers contributed P{top_spenders['Sales(P)'].sum():,.0f} in total sales."
                notifications.append({
                    'id': 'top_spenders',
                    'message': message,
                    'status': 'top-spenders',
                    'read': False
                })
        st.session_state.notifications = notifications

    # Display notification dropdown
    if st.session_state.show_dropdown:
        with st.container(border=True):
            for notif in st.session_state.notifications:
                notif_class = "unread" if not notif['read'] else "read"
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f'<div class="notification-item {notif_class}">{notif["message"]}</div>', unsafe_allow_html=True)
                with col2:
                    if st.button("Mark as Read", key=f"mark_read_{notif['id']}"):
                        notif['read'] = True
                        st.rerun()

    # Show dashboard tabs if notification dropdown is not visible
    if not st.session_state.show_dropdown:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Overview",          
            "⭐ Top Products",           
            "📈 Channel Breakdown",       
            "👥 User Engagement",         
            "🌍 Regional Insights",       
            "📅 Trend Analysis"        
        ])

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.markdown("#### Sales of Activities Over Time")
                    filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'])
                    filtered_df['Date'] = filtered_df['Timestamp'].dt.date
                    unique_dates = sorted(filtered_df['Date'].unique())
                    time_series_sales_df = pd.DataFrame({'Date': unique_dates})
                    sales_demo = (
                        filtered_df[filtered_df['Is Demo Request'] == 1]
                        .groupby('Date')['Sales(P)']
                        .sum()
                        .reindex(unique_dates, fill_value=0)
                        .values
                    )
                    sales_job = (
                        filtered_df[filtered_df['Is Job Posted'] == 1]
                        .groupby('Date')['Sales(P)']
                        .sum()
                        .reindex(unique_dates, fill_value=0)
                        .values
                    )
                    sales_ai = (
                        filtered_df[filtered_df['Is AI Assistant Used'] == 1]
                        .groupby('Date')['Sales(P)']
                        .sum()
                        .reindex(unique_dates, fill_value=0)
                        .values
                    )
                    time_series_sales_df['Demo Request'] = sales_demo
                    time_series_sales_df['Job Posted'] = sales_job
                    time_series_sales_df['AI Assistant Used'] = sales_ai
                    fig_line = px.line(
                        time_series_sales_df,
                        x='Date',
                        y=['Demo Request', 'Job Posted', 'AI Assistant Used'],
                        markers=True,
                        color_discrete_sequence=['#4C78A8', '#F58518', '#54A24B'],
                        height=350
                    )
                    fig_line.update_traces(line_width=2, marker_size=5)
                    fig_line.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Sales(P)",
                        legend_title="Activity",
                        margin=dict(l=20, r=20, t=20, b=20),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        hovermode="x unified"
                    )
                    avg_line = np.mean(
                        time_series_sales_df[['Demo Request', 'Job Posted', 'AI Assistant Used']].values
                    )
                    fig_line.add_hline(y=avg_line, line_color="red", line_width=2, line_dash="dash")
                    fig_line.add_annotation(
                        xref="paper", yref="y",
                        x=1.05, y=avg_line,
                        text="Average Sales (P)",
                        showarrow=True,
                        arrowhead=2,
                        ax=0, ay=-40,
                        font=dict(color="red"),
                        bgcolor="white",
                        bordercolor="red",
                        borderwidth=1,
                        borderpad=4
                    )
                    st.plotly_chart(fig_line, use_container_width=True)

            with col2:
                with st.container(border=True):
                    st.subheader("Top Products by Sales")
                    top_products = (
                        filtered_df.groupby('Product Name')['Sales(P)']
                        .sum()
                        .nlargest(5)
                        .reset_index()
                    )
                    fig_pie_products = px.pie(
                        top_products,
                        names='Product Name',
                        values='Sales(P)',
                        hole=0.5,
                        color_discrete_sequence=px.colors.qualitative.Set3,
                        height=340
                    )
                    fig_pie_products.update_traces(
                        textinfo='percent',
                        textposition='inside',
                        insidetextorientation='radial',
                        hovertemplate='<b>%{label}</b><br>Sales(P): %{value:,.2f}<br>Share: %{percent}',
                        marker=dict(line=dict(color='white', width=2))
                    )
                    fig_pie_products.update_layout(
                        showlegend=True,
                        legend_title=None,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(l=20, r=20, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig_pie_products, use_container_width=True)

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.subheader("Top Products by Sales")
                    top_products = filtered_df.groupby('Product Name')['Sales(P)'].sum().nlargest(5).reset_index()
                    fig = px.bar(
                        top_products,
                        y='Product Name',
                        x='Sales(P)',
                        orientation='h',
                        color='Product Name',
                        color_discrete_sequence=px.colors.sequential.Teal,
                        height=350
                    )
                    fig.update_traces(marker_line_width=1.5, marker_line_color='black')
                    fig.update_layout(
                        yaxis=dict(categoryorder='total ascending'),
                        showlegend=False,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=20, r=20, t=0, b=0),
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                with st.container(border=True):
                    st.subheader("Top Products by User Interactions")
                    interaction_data = (
                        filtered_df.groupby('Product Name')['User Interaction']
                        .count()
                        .nlargest(5)
                        .reset_index()
                        .rename(columns={'User Interaction': 'Interactions'})
                    )
                    fig = go.Figure(data=[go.Table(
                        columnwidth=[80, 40],
                        header=dict(
                            values=["<b>Product Name</b>", "<b>Interactions</b>"],
                            fill_color="#2a3f5f",
                            font=dict(color='white', size=14),
                            align="left",
                            height=65
                        ),
                        cells=dict(
                            values=[
                                interaction_data['Product Name'],
                                interaction_data['Interactions']
                            ],
                            fill_color=[['#f7f9fc', 'white']*3],
                            align="left",
                            font=dict(size=13),
                            height=60
                        )
                    )])
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=5, b=0),
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.subheader("Sales by Source Channel")
                    source_data = (
                        filtered_df.groupby('Source Channel')['Sales(P)']
                        .sum()
                        .sort_values(ascending=False)
                        .reset_index()
                    )
                    fig1 = px.pie(
                        source_data,
                        names='Source Channel',
                        values='Sales(P)',
                        color_discrete_sequence=px.colors.qualitative.Set3,
                        height=120
                    )
                    fig1.update_traces(textinfo='percent')
                    fig1.update_layout(
                        showlegend=True,
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                with st.container(border=True):
                    st.subheader("Referral Source Interactions")
                    referral_data = (
                        filtered_df.groupby('Referral Source')['User Interaction']
                        .count()
                        .sort_values(ascending=False)
                        .reset_index()
                        .rename(columns={'User Interaction': 'Interactions'})
                    )
                    fig2 = px.bar(
                        referral_data,
                        x='Referral Source',
                        y='Interactions',
                        color='Referral Source',
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        labels={'Referral Source': 'Referral Source'},
                        height=120
                    )
                    fig2.update_layout(
                        xaxis_title="Referral Source",
                        yaxis_title="Interactions",
                        showlegend=False,
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            with col2:
                with st.container(border=True):
                    st.subheader("Conversion Rate by Source Channel")
                    conversion_data = (
                        filtered_df.groupby('Source Channel')['Conversion Status']
                        .value_counts(normalize=True)
                        .unstack()
                        .fillna(0)
                        .reset_index()
                    )
                    fig3 = px.bar(
                        conversion_data,
                        x='Source Channel',
                        y=['Converted', 'Not Converted'],
                        barmode='group',
                        color_discrete_sequence=px.colors.qualitative.Set2,
                        labels={'value': 'Conversion Rate', 'Source Channel': 'Source Channel'},
                        height=350
                    )
                    fig3.update_layout(
                        xaxis_title="Source Channel",
                        yaxis_title="Conversion Rate",
                        showlegend=True,
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig3, use_container_width=True)

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.markdown("#### Engagement Trends Over Time")
                    interaction_types = filtered_df['User Interaction'].unique()
                    weekly_engagement = (
                        filtered_df.groupby([
                            pd.Grouper(key='Timestamp', freq='W-MON'),
                            'User Interaction'
                        ])
                        .size()
                        .reset_index(name='Count')
                    )
                    fig = px.line(
                        weekly_engagement,
                        x='Timestamp',
                        y='Count',
                        color='User Interaction',
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        labels={'Count': 'Interaction Count', 'Timestamp': 'Date'},
                        height=350
                    )
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Interaction Count",
                        legend_title="Interaction Type",
                        hovermode="x unified",
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(
                            tickformat="%b %d<br>%Y",
                            gridcolor='lightgrey'
                        ),
                        yaxis=dict(
                            gridcolor='lightgrey'
                        )
                    )
                    fig.update_traces(
                        mode='lines+markers',
                        marker=dict(size=8),
                        line=dict(width=2)
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                with st.container(border=True):
                    st.markdown("#### Total Engagements by Interaction")
                    total_interactions = (
                        df.groupby('User Interaction')
                        .agg({'User ID': 'count'})
                        .reset_index()
                        .rename(columns={'User ID': 'Count'})
                    )
                    fig_bar = px.bar(
                        total_interactions,
                        x='User Interaction',
                        y='Count',
                        color='User Interaction',
                        color_discrete_sequence=['#4C78A8', '#F58518', '#54A24B', '#E45756', '#B279A2'],
                        height=350
                    )
                    fig_bar.update_layout(
                        title=None,
                        xaxis_title="Interaction Type",
                        yaxis_title="Total Count",
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

        with tab5:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.markdown("#### Geographic Distribution of Sales")
                    country_data = filtered_df.groupby('Country').agg({
                        'Sales(P)': 'sum',
                        'User ID': 'nunique'
                    }).reset_index()
                    fig = px.choropleth(
                        country_data,
                        locations="Country",
                        locationmode="country names",
                        color="Sales(P)",
                        hover_name="Country",
                        hover_data=["User ID"],
                        color_continuous_scale=['#E8F4F3', '#2CA6A4'],
                        projection='natural earth',
                        title="Sales by Country"   
                    )
                    fig.update_layout(
                        title='',
                        height=365,
                        margin=dict(l=0, r=0, t=0, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                with st.container(border=True):
                    st.markdown("#### Top Countries by Engagement Volume")
                    country_engagement = (
                        filtered_df.groupby('Country')['User ID']
                        .nunique()
                        .sort_values(ascending=False)
                        .reset_index(name='Unique Users')
                    )
                    fig_bar = px.bar(
                        country_engagement.head(10),
                        x='Unique Users',
                        y='Country',
                        orientation='h',
                        color='Country',
                        title=None,
                        height=365
                    )
                    fig_bar.update_layout(
                        xaxis_title="Unique Engaged Users",
                        yaxis_title="Country",
                        showlegend=False,
                        plot_bgcolor='white',
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor='white'
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

        with tab6:
            with st.container(border=True):
                st.markdown("### 📅 Engagement Calendar")
                calendar_df = filtered_df.assign(
                    Date=filtered_df['Timestamp'].dt.date,
                    Weekday=filtered_df['Timestamp'].dt.day_name(),
                    Week=filtered_df['Timestamp'].dt.isocalendar().week,
                    Month=filtered_df['Timestamp'].dt.month_name(),
                    Month_Num=filtered_df['Timestamp'].dt.month
                )
                latest_month_num = calendar_df['Month_Num'].max()
                latest_month_name = calendar_df[calendar_df['Month_Num'] == latest_month_num]['Month'].iloc[0]
                calendar_data = (
                    calendar_df[calendar_df['Month_Num'] == latest_month_num]
                    .groupby(['Weekday', 'Week'])['User Interaction']
                    .count()
                    .reset_index()
                )
                fig = px.density_heatmap(
                    calendar_data,
                    x="Weekday",
                    y="Week",
                    z="User Interaction",
                    color_continuous_scale="Viridis",
                    height=350
                )
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                fig.update_xaxes(categoryorder='array', categoryarray=weekday_order)
                fig.update_layout(
                    yaxis_title="Week Number",
                    coloraxis_colorbar=dict(title="Interactions"),
                    margin=dict(l=0, r=0, t=0, b=0),
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("**Key Weekly Patterns:**")
                    weekly_patterns = (
                        calendar_df[calendar_df['Month_Num'] == latest_month_num]
                        .groupby('Weekday')['User Interaction']
                        .count()
                        .reindex(weekday_order)
                        .dropna()
                    )
                    total_interactions = weekly_patterns.sum()
                    for day, count in weekly_patterns.items():
                        st.write(f"- {day}: {count:,} interactions ({count / total_interactions * 100:.1f}%)")

# Individual Dashboard
def show_individual_dashboard():
    df = load_data()

    # Custom CSS for Individual Dashboard
    st.markdown(
    """ <style>
        .block-container {
        padding-top: 0rem !important;
    }
    .individual-header {
        color: navy;
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        margin-top: -3rem;
        margin-bottom: -3rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e0eafc 100%);
        border-radius: 12px;
        padding: 2px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        margin-bottom: 0rem;
    }
    .metric-card:hover {
        background: linear-gradient(135deg, #e0eafc 2%, #f5f7fa 100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    .metric-title {
        font-size: 1rem;
        color: #2874A6; /* Soft ocean blue */
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #154360; /* Strong navy */
    }
    .sidebar .sidebar-content {
        background-color: #D6EAF8; /* Pale baby blue */
    }
    [data-testid="stSelectbox"], [data-baseweb="select"] {
        border: 2px solid #AED6F1;
        border-radius: 5px;
        background-color: white;
    }
    [data-testid="stMultiSelectTag"] {
        background-color: #D4E6F1;
        color: #21618C;
        border: 1px solid #AED6F1;
        border-radius: 5px;
        padding: 4px 8px;
    }
    [data-testid="stMultiSelectTag"]:hover {
        background-color: #AED6F1;
    }
    </style>
    """, unsafe_allow_html=True
    )
    
    # Sidebar
    with st.sidebar:
        st.logo("images/AI-Solutions.jpg")
        st.markdown(f"**Logged in as:** {st.session_state.username} (Individual)")
        if st.button("Logout"):
            logout()

        st.header("🔍 My Data Filters")
        selected_customer = st.selectbox("👤 Select Customer", df["Customer Name"])
        selected_product = st.multiselect("🖥️ Select Product", df["Product Name"].unique())
        selected_interaction = st.multiselect("🛠️ User Interaction", df["User Interaction"].unique())
        aggregation = st.selectbox("📊 Sales Aggregation", ["Weekly", "Monthly"])
        start_date = st.date_input("📅 Start Date", value=df['Timestamp'].min().date())
        end_date = st.date_input("📅 End Date", value=df['Timestamp'].max().date())

    # Filter data for selected customer
    filtered_df = df[df['Customer Name'] == selected_customer]
    filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'])
    filtered_df['Date'] = filtered_df['Timestamp'].dt.date
    filtered_df = filtered_df[
        (filtered_df['Timestamp'].dt.date >= start_date) &
        (filtered_df['Timestamp'].dt.date <= end_date)
    ]
    if selected_product:
        filtered_df = filtered_df[filtered_df['Product Name'].isin(selected_product)]
    if selected_interaction:
        filtered_df = filtered_df[filtered_df['User Interaction'].isin(selected_interaction)]

    # Header
    st.markdown(f'<h1 class="individual-header">{selected_customer} Sales Dashboard</h1>', unsafe_allow_html=True)

    # Metrics
    total_sales = filtered_df['Sales(P)'].sum()
    total_interactions = filtered_df['User Interaction'].count()
    avg_session = filtered_df['Session Duration(s)'].mean() if not filtered_df.empty else 0
    conversion_rate = filtered_df[filtered_df['Conversion Status'] == 'Converted']['Sales(P)'].sum() / total_sales if total_sales > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Total Sales</div>
                <div class="metric-value">P{total_sales:,.0f}</div>
            </div>
            """, unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Total Interactions</div>
                <div class="metric-value">{total_interactions}</div>
            </div>
            """, unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Conversion Rate</div>
                <div class="metric-value">{conversion_rate:.1%}</div>
            </div>
            """, unsafe_allow_html=True
        )

    # Tabs for Individual Dashboard
    tab1, tab2, tab3 = st.tabs(["📈 Sales Trends", "🛠️ Interaction Breakdown", "🔍 Activity Details"]) 

    with tab1:
        with st.container(border=True):
            st.markdown("### Sales Over Time")
            if aggregation == "Weekly":
                sales_data = filtered_df.groupby(pd.Grouper(key='Timestamp', freq='W-MON'))['Sales(P)'].sum().reset_index()
                x_label = "Week"
            else:
                sales_data = filtered_df.groupby(pd.Grouper(key='Timestamp', freq='M'))['Sales(P)'].sum().reset_index()
                x_label = "Month"
                sales_data['Timestamp'] = sales_data['Timestamp'].dt.strftime('%b %Y')
            
            fig = px.area(
                sales_data,
                x='Timestamp',
                y='Sales(P)',
                color_discrete_sequence=["#4AC5B1"],
                height=350
            )
            fig.update_layout(
                xaxis_title=x_label,
                yaxis_title="Sales (P)",
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode="x unified"
            )
            fig.update_traces(fill='tozeroy', line=dict(width=2))
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("### Interactions by Type")
                interaction_data = filtered_df['User Interaction'].value_counts().reset_index()
                interaction_data.columns = ['User Interaction', 'Count']
                fig = px.bar(
                    interaction_data,
                    x='User Interaction',
                    y='Count',
                    color='User Interaction',
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    height=350
                )
                fig.update_layout(
                    xaxis_title="Interaction Type",
                    yaxis_title="Count",
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            with st.container(border=True):
                st.markdown("### Interaction Distribution")
                fig = px.pie(
                    interaction_data,
                    names='User Interaction',
                    values='Count',
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    height=350
                )
                fig.update_traces(textinfo='percent+label', pull=[0.1, 0, 0, 0])
                fig.update_layout(
                    showlegend=True,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        with st.container(border=True):
            st.markdown("### Activity Details")
            activity_data = filtered_df[['Timestamp', 'Product Name', 'User Interaction', 'Sales(P)', 'Conversion Status', 'Session Duration(s)']].copy()
            activity_data['Timestamp'] = activity_data['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=['Date', 'Product', 'Interaction', 'Sales (P)', 'Conversion', 'Session (s)'],
                    fill_color="#3E6D6D",
                    font=dict(color='white'),
                    align='left'
                ),
                cells=dict(
                    values=[
                        activity_data['Timestamp'],
                        activity_data['Product Name'],
                        activity_data['User Interaction'],
                        activity_data['Sales(P)'],
                        activity_data['Conversion Status'],
                        activity_data['Session Duration(s)']
                    ],
                    fill_color='white',
                    align='left'
                )
            )])
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # Remove Streamlit style
    hide_st_style = """ <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;} </style>
    """
    st.markdown(hide_st_style, unsafe_allow_html=True)

# Render Dashboard based on Role
if not st.session_state.logged_in:
    show_login_page()
else:
    if st.session_state.role == "sales_team":
        show_sales_team_dashboard()
    elif st.session_state.role == "individual":
        show_individual_dashboard()