import streamlit as st
import pandas as pd
import datetime
import json
import os
import sys

# --- Project Imports ---
# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

import config # Import config for potential future use
from db.getters import (
    get_all_safety_logs_with_details,
    get_all_safety_plans_with_details
)


# If validation passes, proceed
st.title(f"管理部門スタッフ向けページ")
st.write("全社の日誌・予定の閲覧、フィルタリング、CSV出力が可能です。誰でも見れます。")

# 3. Fetch Data
logs_data = []
plans_data = []
try:
    logs_data = get_all_safety_logs_with_details()
    plans_data = get_all_safety_plans_with_details()
except Exception as e:
    st.error(f"全データ取得中にエラーが発生しました: {e}")
    st.stop()

if not logs_data and not plans_data:
    st.info("登録されている実績・予定データがありません。")
    st.stop()

# --- DataFrameに変換 ---
logs_df = pd.DataFrame([dict(row) for row in logs_data]) if logs_data else pd.DataFrame()
plans_df = pd.DataFrame([dict(row) for row in plans_data]) if plans_data else pd.DataFrame()

# --- Data Cleaning & Preparation (Before Filtering) ---
# Convert date columns
if not logs_df.empty and 'date' in logs_df.columns:
    logs_df['date'] = pd.to_datetime(logs_df['date'], errors='coerce')
if not plans_df.empty and 'planned_date' in plans_df.columns:
    plans_df['planned_date'] = pd.to_datetime(plans_df['planned_date'], errors='coerce')

# Define min/max dates for filters AFTER converting to datetime
all_dates = pd.concat([
    logs_df['date'] if not logs_df.empty else pd.Series(dtype='datetime64[ns]'),
    plans_df['planned_date'] if not plans_df.empty else pd.Series(dtype='datetime64[ns]')
]).dropna()

min_date = all_dates.min().date() if not all_dates.empty else datetime.date.today()
max_date = all_dates.max().date() if not all_dates.empty else datetime.date.today()

# --- Sidebar Filters ---
st.sidebar.header("表示フィルタ")

# Date range filter
start_date = st.sidebar.date_input("開始日", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("終了日", max_date, min_value=min_date, max_value=max_date)

# Department filter
all_departments_logs = logs_df['department_name'].dropna().unique() if not logs_df.empty else []
all_departments_plans = plans_df['department_name'].dropna().unique() if not plans_df.empty else []
all_departments = sorted(list(set(list(all_departments_logs)) | set(list(all_departments_plans)))) # Combine and sort
selected_departments = st.sidebar.multiselect("部署", all_departments, default=all_departments)

# Site filter (dynamic based on selected departments)
available_sites_query = pd.Series(dtype=str)
if selected_departments:
    sites_in_logs = logs_df[logs_df['department_name'].isin(selected_departments)]['site_name'].dropna().unique() if not logs_df.empty else []
    sites_in_plans = plans_df[plans_df['department_name'].isin(selected_departments)]['site_name'].dropna().unique() if not plans_df.empty else []
    combined_sites = sorted(list(set(list(sites_in_logs)) | set(list(sites_in_plans)))) # Combine and sort
    available_sites_query = pd.Series(combined_sites)

selected_sites = st.sidebar.multiselect("現場", available_sites_query.tolist(), default=available_sites_query.tolist())

# --- Apply Filters ---
filtered_logs_df = logs_df.copy()
filtered_plans_df = plans_df.copy()

# Filter by date (handle NaT)
start_datetime = pd.to_datetime(start_date)
end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) # Include end date fully

if not filtered_logs_df.empty:
    filtered_logs_df = filtered_logs_df[
        (filtered_logs_df['date'] >= start_datetime) &
        (filtered_logs_df['date'] < end_datetime) &
        (filtered_logs_df['date'].notna())
    ]
if not filtered_plans_df.empty:
    filtered_plans_df = filtered_plans_df[
        (filtered_plans_df['planned_date'] >= start_datetime) &
        (filtered_plans_df['planned_date'] < end_datetime) &
        (filtered_plans_df['planned_date'].notna())
    ]

# Filter by department
if selected_departments:
    if not filtered_logs_df.empty:
        filtered_logs_df = filtered_logs_df[filtered_logs_df['department_name'].isin(selected_departments)]
    if not filtered_plans_df.empty:
        filtered_plans_df = filtered_plans_df[filtered_plans_df['department_name'].isin(selected_departments)]

# Filter by site
if selected_sites:
    if not filtered_logs_df.empty:
        filtered_logs_df = filtered_logs_df[filtered_logs_df['site_name'].isin(selected_sites)]
    if not filtered_plans_df.empty:
        filtered_plans_df = filtered_plans_df[filtered_plans_df['site_name'].isin(selected_sites)]

# --- Display Data --- #
tab_logs, tab_plans = st.tabs([f"実績 ({len(filtered_logs_df)}件)", f"予定 ({len(filtered_plans_df)}件)"])

with tab_logs:
    st.subheader("実績データ (Safety Logs)")
    if not filtered_logs_df.empty:
        display_df_logs = filtered_logs_df.copy()
        # Format for display
        display_df_logs['date'] = display_df_logs['date'].dt.strftime('%Y-%m-%d')
        display_df_logs['approved'] = display_df_logs['approved'].map({1: '済', 0: '未'}).fillna('未')
        # Simplify action check display
        def format_action_check(x):
            try: return ", ".join(json.loads(x)) if isinstance(x, str) else '-'
            except: return 'エラー'
        display_df_logs['action_check'] = display_df_logs['action_check'].apply(format_action_check)
        # Select and reorder columns
        display_cols_logs = [
            'date', 'site_name', 'department_name', 'employee_workers',
            'partner_workers', 'task', 'action_check', 'author',
            'approved', 'approver', 'comment', 'image_path'
        ]
        # Filter columns that actually exist in the DataFrame
        display_cols_logs_exist = [col for col in display_cols_logs if col in display_df_logs.columns]
        st.dataframe(display_df_logs[display_cols_logs_exist], hide_index=True)

        # CSV Download
        csv_log = display_df_logs[display_cols_logs_exist].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="実績データをCSVダウンロード",
            data=csv_log,
            file_name=f'safety_logs_{start_date}_to_{end_date}.csv',
            mime='text/csv',
        )
    else:
        st.info("該当する実績データはありません。")

with tab_plans:
    st.subheader("予定データ (Safety Plans)")
    if not filtered_plans_df.empty:
        display_df_plans = filtered_plans_df.copy()
        # Format for display
        display_df_plans['planned_date'] = display_df_plans['planned_date'].dt.strftime('%Y-%m-%d')
        display_df_plans['approved'] = display_df_plans['approved'].map({1: '済', 0: '未'}).fillna('未')
        # Extract risk level
        def extract_risk_level(x):
            try: return json.loads(x).get('level', '-') if isinstance(x, str) else '-'
            except: return 'エラー'
        display_df_plans['risk_level'] = display_df_plans['risk_check'].apply(extract_risk_level)
        # Select and reorder columns
        display_cols_plans = [
            'planned_date', 'site_name', 'department_name', 'employee_workers',
            'partner_workers', 'task', 'risk_level', 'risk_action',
            'created_by', 'approved', 'approver', 'comment'
        ]
         # Filter columns that actually exist in the DataFrame
        display_cols_plans_exist = [col for col in display_cols_plans if col in display_df_plans.columns]
        st.dataframe(display_df_plans[display_cols_plans_exist], hide_index=True)

        # CSV Download
        csv_plan = display_df_plans[display_cols_plans_exist].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="予定データをCSVダウンロード",
            data=csv_plan,
            file_name=f'safety_plans_{start_date}_to_{end_date}.csv',
            mime='text/csv',
        )
    else:
        st.info("該当する予定データはありません。")
