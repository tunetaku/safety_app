import streamlit as st
import json
from streamlit_local_storage import LocalStorage
import time

# Import getter functions
from db.getters import (
    get_sites_by_department,
    get_all_departments_with_ids # Need this to get ID and Name together
)

localS = LocalStorage()

# --- LocalStorage Keys (Updated) ---
LS_KEY_NAME = "safety_app_user_name"
LS_KEY_ROLE = "safety_app_user_role"
# Store department info as JSON: {"id": 1, "name": "Dept A"}
LS_KEY_DEPT_INFO = "safety_app_user_dept_info"
# Store site info as JSON: {"id": 10, "name": "Site X"} (Only for Site Manager)
LS_KEY_SITE_INFO = "safety_app_user_site_info"
# LS_KEY_DEPT = "safety_app_user_dept" # Old key - remove usage
# LS_KEY_SITES = "safety_app_user_sites" # Old key - remove usage

# --- Function to clear settings ---
def clear_settings_on_page():
    localS.removeItem(LS_KEY_NAME)
    localS.removeItem(LS_KEY_ROLE)
    localS.removeItem(LS_KEY_DEPT_INFO) # Remove new dept key
    localS.removeItem(LS_KEY_SITE_INFO) # Remove new site key

    # Clear relevant session state keys
    keys_to_clear = [
        'user_name', 'user_role',
        'current_department', # Clear new dept dict
        'current_site' # Clear new site dict
    ]
    # Include old keys just in case they linger, though ideally they shouldn't
    # keys_to_clear.extend(['user_department_name', 'user_site_names', 'current_site_id', 'current_site_name'])

    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.success("設定をクリアしました。")
    # Add a small delay and rerun for LocalStorage changes to reflect if needed
    time.sleep(0.5)
    st.rerun()


# --- Settings Page UI ---
def settings_page():
    st.title("ユーザー設定")
    st.caption("ここで設定した内容は、お使いのブラウザのLocalStorageに保存されます。")
    st.markdown("---")

    # --- Initialize Session State with new structure ---
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ""
    # Use dictionaries for department and site
    if "current_department" not in st.session_state:
        st.session_state.current_department = None # e.g., {"id": 1, "name": "Dept A"} or None
    if "current_site" not in st.session_state:
        st.session_state.current_site = None # e.g., {"id": 10, "name": "Site X"} or None

    # --- Load from LocalStorage ---
    loaded_name = localS.getItem(LS_KEY_NAME)
    loaded_role = localS.getItem(LS_KEY_ROLE)
    loaded_dept_info_json = localS.getItem(LS_KEY_DEPT_INFO)
    loaded_site_info_json = localS.getItem(LS_KEY_SITE_INFO)

    # --- Update Session State from LocalStorage ---
    # Use try-except for JSON parsing
    loaded_dept_info = None
    if loaded_dept_info_json:
        try:
            loaded_dept_info = json.loads(loaded_dept_info_json)
            if not isinstance(loaded_dept_info, dict) or 'id' not in loaded_dept_info or 'name' not in loaded_dept_info:
                print(f"Warning: Invalid department info format in LS: {loaded_dept_info_json}")
                loaded_dept_info = None # Reset if format is wrong
        except json.JSONDecodeError:
            print(f"Error decoding department info JSON from LS: {loaded_dept_info_json}")
            loaded_dept_info = None

    loaded_site_info = None
    if loaded_site_info_json:
        try:
            loaded_site_info = json.loads(loaded_site_info_json)
            if not isinstance(loaded_site_info, dict) or 'id' not in loaded_site_info or 'name' not in loaded_site_info:
                print(f"Warning: Invalid site info format in LS: {loaded_site_info_json}")
                loaded_site_info = None # Reset if format is wrong
        except json.JSONDecodeError:
            print(f"Error decoding site info JSON from LS: {loaded_site_info_json}")
            loaded_site_info = None

    # Populate session state if it's empty and LS has data
    if loaded_name is not None and not st.session_state.user_name:
        st.session_state.user_name = loaded_name
    if loaded_role is not None and not st.session_state.user_role:
        st.session_state.user_role = loaded_role
    if loaded_dept_info is not None and st.session_state.current_department is None:
        st.session_state.current_department = loaded_dept_info
    if loaded_site_info is not None and st.session_state.current_site is None:
        st.session_state.current_site = loaded_site_info


    # --- Get Data for Select Boxes ---
    try:
        # Get list of {"id": x, "name": "y"} dictionaries for departments
        departments_list = get_all_departments_with_ids()
        department_names = [d['name'] for d in departments_list] # For selectbox display
        roles = ["現場責任者", "部署責任者", "管理部門"]
    except Exception as e:
        st.error(f"部署リストの読み込み中にエラーが発生しました: {e}")
        departments_list = []
        department_names = ["エラー発生"]
        roles = ["エラー発生"]
        st.stop() # Stop execution if basic data fails

    # --- Get Current Values from Session State ---
    current_name = st.session_state.user_name
    current_role = st.session_state.user_role
    current_dept_info = st.session_state.current_department # This is a dict or None
    current_site_info = st.session_state.current_site       # This is a dict or None

    # Find indices for selectboxes based on current session state
    try:
        role_index = roles.index(current_role) if current_role in roles else 0
    except ValueError:
        role_index = 0

    current_dept_name = current_dept_info['name'] if current_dept_info else None
    try:
        dept_index = department_names.index(current_dept_name) if current_dept_name in department_names else 0
    except ValueError:
        dept_index = 0

    # --- Settings Form ---
    with st.form(key="settings_form"):
        st.subheader("基本情報")
        new_name = st.text_input("お名前 *", value=current_name, placeholder="例: 安全 太郎")
        new_role = st.selectbox("役割 *", roles, index=role_index)

        # Department Selection
        new_dept_name = st.selectbox("所属部署 *", department_names, index=dept_index)
        # Find the corresponding department dict (id and name) based on the selected name
        selected_dept_info = next((d for d in departments_list if d['name'] == new_dept_name), None)

        # Site Selection (only for Site Manager)
        selected_site_info = None # This will store {"id": x, "name": "y"}
        site_options_for_dept = [] # List of {"id": x, "name": "y"}
        site_names_for_selectbox = [] # List of names for display

        if new_role == "現場責任者":
            st.subheader("担当現場")
            if selected_dept_info: # Check if a valid department is selected
                try:
                    # get_sites_by_department expects dept_id
                    sites_in_dept_raw = get_sites_by_department(selected_dept_info['id'])
                    # sites_in_dept_raw is likely a list of dicts like {'id': ..., 'name': ...}
                    site_options_for_dept = sites_in_dept_raw # Keep the list of dicts
                    site_names_for_selectbox = [site['name'] for site in site_options_for_dept] # Names for selectbox

                    if not site_options_for_dept:
                        st.warning(f"部署「{new_dept_name}」には登録されている現場がありません。")
                    else:
                        # Determine index for site selectbox
                        current_site_name = current_site_info['name'] if current_site_info else None
                        try:
                            site_index = site_names_for_selectbox.index(current_site_name) if current_site_name in site_names_for_selectbox else 0
                        except ValueError:
                            site_index = 0

                        # Site selectbox uses names, but we'll find the ID later
                        selected_site_name = st.selectbox(
                            f"部署「{selected_dept_info['name']}」の担当現場を選択してください *",
                            site_names_for_selectbox,
                            index=site_index
                        )
                        # Find the full site info dict based on the selected name
                        selected_site_info_raw = next((s for s in site_options_for_dept if s['name'] == selected_site_name), None)
                        if selected_site_info_raw:
                            selected_site_info = {'id': selected_site_info_raw['id'], 'name': selected_site_info_raw['name']}

                except Exception as e:
                    st.error(f"現場情報の取得中にエラーが発生しました: {e}")
                    site_names_for_selectbox = ["エラー発生"]
            else:
                st.info("所属部署を選択すると、担当現場を選択できます。")

        st.markdown("(\* は必須項目)")
        submit_button = st.form_submit_button("設定を保存")

    # --- Handle Form Submission ---
    if submit_button:
        error = False
        # --- Validation ---
        if not new_name:
            st.error("お名前を入力してください。")
            error = True
        if not new_role:
            st.error("役割を選択してください。")
            error = True
        if not selected_dept_info: # Check if a valid department dict was found
            st.error("所属部署を選択してください。")
            error = True
        if new_role == "現場責任者":
            if not site_options_for_dept:
                 st.error(f"部署「{selected_dept_info['name'] if selected_dept_info else '選択されていません'}」には選択可能な現場がありません。")
                 error = True
            elif not selected_site_info: # Check if a valid site dict was found
                 st.error("現場責任者の場合、担当現場を選択してください。")
                 error = True

        # --- Save if No Errors ---
        if not error:
            # Prepare JSON strings for LocalStorage
            dept_info_json_to_save = json.dumps(selected_dept_info) if selected_dept_info else ""

            # Site info is only relevant for Site Manager
            site_info_json_to_save = ""
            if new_role == "現場責任者" and selected_site_info:
                site_info_json_to_save = json.dumps(selected_site_info)
            # For other roles, ensure site info is cleared
            final_site_info_to_set = selected_site_info if new_role == "現場責任者" else None


            # Save to LocalStorage
            localS.setItem(LS_KEY_NAME, new_name, key="ls_set_name")
            localS.setItem(LS_KEY_ROLE, new_role, key="ls_set_role")
            localS.setItem(LS_KEY_DEPT_INFO, dept_info_json_to_save, key="ls_set_dept_info")
            localS.setItem(LS_KEY_SITE_INFO, site_info_json_to_save, key="ls_set_site_info")

            # Save to Session State (using the dictionaries)
            st.session_state.user_name = new_name
            st.session_state.user_role = new_role
            st.session_state.current_department = selected_dept_info
            st.session_state.current_site = final_site_info_to_set # Use the site dict or None

            # Remove old session state keys if they exist (optional but clean)
            # st.session_state.pop('user_department_name', None)
            # st.session_state.pop('user_site_names', None)
            # st.session_state.pop('current_site_id', None)
            # st.session_state.pop('current_site_name', None)


            st.success("設定を保存しました。")
            # Rerun to reflect changes immediately in the UI if necessary
            time.sleep(0.5) # Short delay helps ensure LS write completes
            st.rerun()

    # --- Reset Settings Section ---
    st.markdown("---")
    st.subheader("設定のリセット")
    if st.button("現在の設定をクリア", key="clear_button_v2"):
        clear_settings_on_page() # This now calls rerun internally

# Run the page function
if __name__ == "__main__":
    settings_page()
