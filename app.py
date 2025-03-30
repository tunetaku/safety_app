import streamlit as st
import os
import pandas as pd
import json
from PIL import Image
import datetime
from streamlit_js_eval import streamlit_js_eval
from streamlit_local_storage import LocalStorage

# --- Project Imports ---
import config
from db.connection import initialize_database, get_db_connection
from db.getters import get_departments, get_sites_by_department, get_sites_by_ids, get_site_ids_by_names

# --- Initialize DB ---
initialize_database()

# Define LocalStorage keys (should match settings page)
LS_KEY_NAME = "safety_app_user_name"
LS_KEY_ROLE = "safety_app_user_role"
LS_KEY_DEPT_INFO = "safety_app_user_dept_info" # New key for dept dict
LS_KEY_SITE_INFO = "safety_app_user_site_info" # New key for site dict

# Initialize LocalStorage
localS = LocalStorage()

# --- Function to Load Settings from LocalStorage ---
def load_settings():
    # Initialize session state if keys don't exist
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'user_role' not in st.session_state:
        st.session_state.user_role = ""
    if 'current_department' not in st.session_state:
        st.session_state.current_department = None # Will store {"id": ..., "name": ...}
    if 'current_site' not in st.session_state:
        st.session_state.current_site = None # Will store {"id": ..., "name": ...}

    # Load from LocalStorage
    loaded_name = localS.getItem(LS_KEY_NAME)
    loaded_role = localS.getItem(LS_KEY_ROLE)
    loaded_dept_info_json = localS.getItem(LS_KEY_DEPT_INFO)
    loaded_site_info_json = localS.getItem(LS_KEY_SITE_INFO)

    # --- Department Info Loading ---
    loaded_dept_info = None
    if loaded_dept_info_json:
        try:
            loaded_dept_info = json.loads(loaded_dept_info_json)
            # Basic validation
            if not isinstance(loaded_dept_info, dict) or 'id' not in loaded_dept_info or 'name' not in loaded_dept_info:
                print(f"App Load Warning: Invalid department info format in LS: {loaded_dept_info_json}")
                loaded_dept_info = None
        except json.JSONDecodeError:
            print(f"App Load Error: Decoding department info JSON from LS: {loaded_dept_info_json}")
            loaded_dept_info = None

    # --- Site Info Loading ---
    loaded_site_info = None
    if loaded_site_info_json:
        try:
            loaded_site_info = json.loads(loaded_site_info_json)
            # Basic validation
            if not isinstance(loaded_site_info, dict) or 'id' not in loaded_site_info or 'name' not in loaded_site_info:
                print(f"App Load Warning: Invalid site info format in LS: {loaded_site_info_json}")
                loaded_site_info = None
        except json.JSONDecodeError:
            print(f"App Load Error: Decoding site info JSON from LS: {loaded_site_info_json}")
            loaded_site_info = None

    # --- Update Session State (only if session state is currently empty/None) ---
    if loaded_name is not None and not st.session_state.user_name:
        st.session_state.user_name = loaded_name
        print(f"Loaded name from LS: {loaded_name}") # Debug print
    if loaded_role is not None and not st.session_state.user_role:
        st.session_state.user_role = loaded_role
        print(f"Loaded role from LS: {loaded_role}") # Debug print
    if loaded_dept_info is not None and st.session_state.current_department is None:
        st.session_state.current_department = loaded_dept_info
        print(f"Loaded dept info from LS: {loaded_dept_info}") # Debug print
    if loaded_site_info is not None and st.session_state.current_site is None:
        st.session_state.current_site = loaded_site_info
        print(f"Loaded site info from LS: {loaded_site_info}") # Debug print

# --- Load settings at the start of the app ---
load_settings()

# --- Function to clear settings from LocalStorage and session_state ---
def clear_settings():
    js_clear_commands = [
        f"localStorage.removeItem('{LS_KEY_NAME}')",
        f"localStorage.removeItem('{LS_KEY_ROLE}')",
        f"localStorage.removeItem('{LS_KEY_DEPT_INFO}')",
        f"localStorage.removeItem('{LS_KEY_SITE_INFO}')"
    ]
    streamlit_js_eval(js_expressions=js_clear_commands, key="clear_storage")

    keys_to_clear = ['user_name', 'user_role', 'current_department', 'current_site', 'user_settings_loaded']
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.success("設定をクリアしました。ページを更新してください。")

# --- Main App Logic ---
def main():
    st.set_page_config(layout="wide")
    st.title("安全管理アプリ")

    if 'user_settings_loaded' not in st.session_state:
        st.session_state.user_settings_loaded = True

    if st.session_state.get('user_settings_loaded', False):
        user_name = st.session_state.user_name
        user_role = st.session_state.user_role
        user_dept = st.session_state.current_department
        user_site = st.session_state.current_site

        st.sidebar.success(f"設定済: {user_name} ({user_role})")
        st.sidebar.info(f"所属: {user_dept['name'] if user_dept else ''}")
        if user_role == '現場責任者':
            st.sidebar.info(f"担当現場: {user_site['name'] if user_site else ''}")

        if st.sidebar.button("設定をクリア", key="clear_settings_button"):
            clear_settings()
            st.rerun()

        st.info("左のサイドバーから各機能ページを選択してください。")
        st.markdown("--- ")
        st.markdown("### 注意事項")
        st.warning("このアプリはLocalStorageに設定を保存します。ブラウザの開発者ツールで設定内容を書き換えることが可能です。機密性の高い情報の管理には使用しないでください。")

    else:
        st.warning("ユーザー設定が読み込まれていません。")
        st.info("サイドバーの **`pages/0_設定.py`** ページで、お名前、役割、部署、担当現場を設定してください。")

if __name__ == "__main__":
    main()
