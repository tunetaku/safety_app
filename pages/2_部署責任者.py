import streamlit as st
import datetime as dt
from db.getters import (
    get_sites_by_department, get_log_by_site_and_date,
    get_plan_by_site_and_date,
    get_site_dates # 
)
from db.setters import (
    add_site, update_approval_status,
    update_site_dates, # 
)

#   === Page Logic Starts Here ===

# 1. Get User Info from Session State (0_設定.py の形式に合わせる)
current_user_name = st.session_state.get("user_name")
current_user_role = st.session_state.get("user_role")
current_department_info = st.session_state.get("current_department") # 辞書を取得

# 2. Validate User Info and Role (新しい形式に合わせる)
validation_passed = False
if current_user_name and current_user_role and current_department_info and isinstance(current_department_info, dict) and 'id' in current_department_info:
    # 役割チェック
    if current_user_role == "部署責任者":
        validation_passed = True
        # 検証が通ったらIDと名前を取得
        current_department_id = current_department_info['id']
        current_department_name = current_department_info.get('name', '不明な部署') # 名前も取得
    else:
        st.error("このページへのアクセス権限がありません。部署責任者としてログインしてください。")
else:
    # 不足情報の案内
    missing_items = []
    if not current_user_name: missing_items.append("お名前")
    if not current_user_role: missing_items.append("役割")
    if not current_department_info or not isinstance(current_department_info, dict) or 'id' not in current_department_info:
        missing_items.append("所属部署")
    st.warning(f"ユーザー設定が不足しています: {', '.join(missing_items)}")
    st.info("サイドバーの「設定」ページで必要な情報をすべて設定してください。")
    if st.button("設定ページへ移動"):
        st.switch_page("pages/0_設定.py")

# 検証が通らなかった場合は停止
if not validation_passed:
    st.stop()

st.title(f"{current_department_name}")

tab_overview, tab_register = st.tabs(["現場状況確認", "現場新規登録"]) 

# --- Helper Function (曜日取得) ---
def get_japanese_weekday(date_obj):
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return weekdays[date_obj.weekday()]

# --- モーダルダイアログ定義 --- ★
@st.dialog("承認・コメント入力")
def approval_dialog(plan_data, log_data, site_name, selected_date_str, current_user_name):
    st.subheader(f"{site_name} - {selected_date_str}")

    plan_id = plan_data['id'] if plan_data else None
    log_id = log_data['id'] if log_data else None

    # --- 2カラムレイアウト ---
    col1, col2 = st.columns(2)

    with col1:
        # --- 予定表示 ---
        st.markdown("**予定 (RKY)**")
        if plan_data:
            plan_task = plan_data['task'] if plan_data['task'] else '未登録'
            plan_personnel = (plan_data['employee_workers'] or 0) + (plan_data['partner_workers'] or 0)
            plan_comment = plan_data['comment'] or '' # 承認コメント
            created_by = plan_data['created_by'] or '不明'
            is_plan_approved = plan_data['approved'] == 1
            plan_approver = plan_data['approver'] or ''

            st.write(f"**タスク:** {plan_task}")
            st.write(f"**人員:** {plan_personnel} 名")
            st.text_area("作成者コメント", value=plan_data['risk_action'] or '-', height=80, disabled=True, key=f"dialog_plan_risk_{plan_id}", help="現場責任者が入力したリスク対策等")
            st.write(f"作成者: {created_by}")
            st.write(f"承認状況: {'<font color="green">承認済み</font>' if is_plan_approved else '<font color="orange">未承認</font>'}", unsafe_allow_html=True)
            if is_plan_approved and plan_approver:
                 st.caption(f"承認者: {plan_approver}")
            # 承認者コメントは共通欄に表示するためここでは表示しない
        else:
            st.write("予定データなし")

    with col2:
        # --- 実績表示 ---
        st.markdown("**実績**")
        if log_data:
            log_task = log_data['task'] if log_data['task'] else '未登録'
            log_personnel = (log_data['employee_workers'] or 0) + (log_data['partner_workers'] or 0)
            author = log_data['author'] or '不明'
            image_path = log_data['image_path']

            st.write(f"**タスク:** {log_task}")
            st.write(f"**人員:** {log_personnel} 名")
            st.text_area("現場コメント", value=log_data['action_check'] or '-', height=80, disabled=True, key=f"dialog_log_action_{log_id}", help="現場責任者が入力した点検項目等")
            st.write(f"記録者: {author}")

            if image_path and os.path.exists(image_path):
                st.image(image_path, caption="実績写真", width=200)
            elif image_path:
                st.caption("写真 (パスは存在するがファイルが見つかりません)")
            else:
                st.caption("写真なし")
        else:
            st.write("実績データなし")

    # --- カラムの外 (共通部分) ---
    st.divider()

    # --- 承認者コメント --- # 予定・実績で共通のコメントと承認者とする
    # どちらかのデータから既存のコメントを読み込む (実績優先)
    existing_comment = ""
    if log_data and log_data['comment']:
        existing_comment = log_data['comment'] or ''
    elif plan_data and plan_data['comment']:
        existing_comment = plan_data['comment'] or ''

    approver_comment = st.text_area("承認コメント", value=existing_comment, key=f"approver_comment_{plan_id}_{log_id}")

    # --- ボタン --- #
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        # 承認ボタン（両方もしくはいずれかのデータが存在する場合のみ有効）
        approve_disabled = not (plan_id or log_id)
        if st.button("承認", key=f"dialog_approve_{plan_id}_{log_id}", disabled=approve_disabled):
            success = update_approval_status(plan_id, log_id, True, approver_comment, current_user_name)
            if success:
                st.toast(f"{site_name} の予定/実績を承認しました。", icon="✅")
                st.rerun()
            else:
                st.error("承認処理中にエラーが発生しました。")
    with col2:
        # 保留ボタン（両方もしくはいずれかのデータが存在する場合のみ有効）
        pending_disabled = not (plan_id or log_id)
        if st.button("保留", key=f"dialog_pending_{plan_id}_{log_id}", disabled=pending_disabled):
            success = update_approval_status(plan_id, log_id, False, approver_comment, current_user_name)
            if success:
                st.toast(f"{site_name} の予定/実績を保留としました。", icon="⚠️")
                st.rerun()
            else:
                st.error("保留処理中にエラーが発生しました。")
    # 閉じるボタンはst.dialogでは不要

# --- ★追加: 現場の日付編集モーダル --- #
@st.dialog("現場管理期間 編集")
def edit_site_dates_dialog(site_id, site_name):
    st.subheader(f"{site_name} の管理期間")

    current_dates = get_site_dates(site_id)
    current_start_date_str = current_dates.get('start_date')
    current_end_date_str = current_dates.get('end_date')

    # 文字列から date オブジェクトへ変換 (None の場合は None のまま)
    current_start_date = dt.datetime.strptime(current_start_date_str, '%Y-%m-%d').date() if current_start_date_str else None
    current_end_date = dt.datetime.strptime(current_end_date_str, '%Y-%m-%d').date() if current_end_date_str else None

    new_start_date = st.date_input("管理開始日", value=current_start_date)
    new_end_date = st.date_input("管理終了日", value=current_end_date)

    # Noneを許容する場合のバリデーション (例: 終了日 < 開始日はNG)
    if new_start_date and new_end_date and new_end_date < new_start_date:
        st.error("管理終了日は管理開始日より後に設定してください。")
        save_disabled = True
    else:
        save_disabled = False

    if st.button("保存", key=f"save_dates_{site_id}", disabled=save_disabled):
        # date オブジェクトから文字列へ変換 (None はそのまま None)
        new_start_date_str = new_start_date.strftime('%Y-%m-%d') if new_start_date else None
        new_end_date_str = new_end_date.strftime('%Y-%m-%d') if new_end_date else None

        success = update_site_dates(site_id, new_start_date_str, new_end_date_str)
        if success:
            st.toast("管理期間を更新しました。", icon="✅")
            st.rerun()
        else:
            st.error("期間の更新に失敗しました。")

with tab_overview:

    # --- シンプルな日付選択コンポーネント --- #
    # セッション状態で選択日を管理 (初回は今日)
    if 'selected_calendar_date_dept' not in st.session_state:
        st.session_state.selected_calendar_date_dept = dt.date.today().strftime('%Y-%m-%d')

    selected_date_str = st.session_state.selected_calendar_date_dept

    # 日付文字列を日付オブジェクトに変換 (エラーハンドリング付き)
    try:
        selected_date_obj = dt.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        # 不正な日付形式の場合、今日の日付にリセット
        selected_date_str = dt.date.today().strftime('%Y-%m-%d')
        st.session_state.selected_calendar_date_dept = selected_date_str
        selected_date_obj = dt.date.today()
        st.warning("日付形式が不正だったため、今日の日付にリセットしました。")

    # 前日/今日/翌日ボタンと日付表示
    col1, col2, col3, col4 = st.columns([1, 1, 3, 1])
    with col1:
        if st.button("< 前日", key="prev_day_dept", use_container_width=True):
            new_date = selected_date_obj - dt.timedelta(days=1)
            st.session_state.selected_calendar_date_dept = new_date.strftime('%Y-%m-%d')
            st.rerun()
    with col2:
        if st.button("今日", key="today_dept", use_container_width=True):
            today_str = dt.date.today().strftime('%Y-%m-%d')
            if st.session_state.selected_calendar_date_dept != today_str:
                st.session_state.selected_calendar_date_dept = today_str
                st.rerun()
    with col3:
        st.markdown(f"<h4 style='text-align: center; margin-bottom: 0;'>{selected_date_str} ({get_japanese_weekday(selected_date_obj)})</h4>", unsafe_allow_html=True)
    with col4:
        if st.button("翌日 >", key="next_day_dept", use_container_width=True):
            new_date = selected_date_obj + dt.timedelta(days=1)
            st.session_state.selected_calendar_date_dept = new_date.strftime('%Y-%m-%d')
            st.rerun()


    # --- 選択された日付の現場状況テーブル --- #
    sites_in_dept = get_sites_by_department(current_department_id, selected_date_str)

    if not sites_in_dept:
        st.info(f"{current_department_name}には登録されている現場はありません。")
    else:
        # テーブルヘッダー
        cols = st.columns([2, 3, 3, 1]) # 現場名 | 予定(タスク/人員/状況) | 実績(タスク/人員/状況) | アクション
        with cols[0]:
            st.markdown("**現場名**")
        with cols[1]:
            st.markdown("**予定 (タスク/人員/状況)**")
        with cols[2]:
            st.markdown("**実績 (タスク/人員/状況)**")
        with cols[3]:
            st.markdown("**アクション**")
        st.markdown("--- ")

        # 各現場のデータを表示
        for site in sites_in_dept:
            site_id = site['id']
            site_name = site['name']

            log_data = get_log_by_site_and_date(site_id, selected_date_str)
            plan_data = get_plan_by_site_and_date(site_id, selected_date_str)

            cols = st.columns([2, 3, 3, 1])

            with cols[0]: # 現場名
                # ★変更: 現場名の下に編集ボタンを表示
                st.write(site_name)
                if st.button("⚙️", key=f"edit_dates_{site_id}", help="管理期間を編集"):
                    edit_site_dates_dialog(site_id, site_name)

            with cols[1]: # 予定
                if plan_data:
                    task = plan_data['task'] if plan_data['task'] else 'タスク未登録'
                    personnel = (plan_data['employee_workers'] or 0) + (plan_data['partner_workers'] or 0) # None の場合に 0 を使う
                    approved = plan_data['approved'] == 1
                    status_color = "green" if approved else "orange"
                    status_text = "承認済" if approved else "未承認"
                    st.markdown(f"**T:** {task}<br>**P:** {personnel}名<br>**状況:** <font color='{status_color}'>{status_text}</font>", unsafe_allow_html=True)
                else:
                    st.caption("予定なし")

            with cols[2]: # 実績
                if log_data:
                    task = log_data['task'] if log_data['task'] else 'タスク未登録'
                    personnel = (log_data['employee_workers'] or 0) + (log_data['partner_workers'] or 0) # None の場合に 0 を使う
                    approved = log_data['approved'] == 1
                else:
                    st.caption("実績なし")

            with cols[3]: # アクション
                button_key = f"details_{site_id}_{selected_date_str}"
                if st.button("確認する", key=button_key):
                    approval_dialog(plan_data, log_data, site_name, selected_date_str, current_user_name)

            st.markdown("--- ") # 各行の区切り

with tab_register:
    st.header("現場の新規登録")
    with st.form("new_site_form", clear_on_submit=True):
        site_name_new = st.text_input("現場名")
        # department_id is automatically taken from the logged-in user's session state
        st.write(f"所属部署: {current_department_name}") # Display department
        start_date_new = st.date_input("管理開始日", dt.date.today())
        end_date_new = st.date_input("管理終了日 (任意)", value=None)
        emp_workers_new = st.number_input("デフォルト作業員数（社員）", min_value=0, value=0)
        part_workers_new = st.number_input("デフォルト作業員数（協力会社）", min_value=0, value=0)
        job_nos_new = st.text_input("作業番号 (カンマ区切りで複数入力可)")

        submitted = st.form_submit_button("現場を登録")
        if submitted:
            if not site_name_new:
                st.warning("現場名を入力してください。")
            else:
                start_date_str = start_date_new.strftime('%Y-%m-%d')
                end_date_str = end_date_new.strftime('%Y-%m-%d') if end_date_new else None

                try:
                    new_site_id = add_site(
                        site_name_new, current_department_id, start_date_str, end_date_str,
                        emp_workers_new, part_workers_new, job_nos_new
                    )
                    if new_site_id:
                        st.success(f"現場「{site_name_new}」を登録しました。ページを更新すると承認タブのリストに表示されます。")
                        # Consider rerun or clearing cache if needed immediately
                    else:
                        st.error("現場の登録に失敗しました。データベースを確認してください。")
                except Exception as e:
                    st.error(f"現場登録中にエラーが発生しました: {e}")
