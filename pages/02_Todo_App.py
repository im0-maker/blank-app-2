import streamlit as st
from supabase import create_client, Client

st.title("📝 Supabase連携 ToDoリスト")

# Secretsから鍵を取得（まだ設定していないとエラーになります）
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Supabaseの接続情報が見つかりません。StreamlitのSecretsを設定してください。")
    st.stop()

# --- 1. タスクの追加 ---
with st.form("add_task_form", clear_on_submit=True):
    new_task = st.text_input("新しいタスクを入力")
    submitted = st.form_submit_button("追加")
    
    if submitted and new_task:
        # DBに送信
        data = {"task": new_task, "is_complete": False}
        try:
            supabase.table("todos").insert(data).execute()
            st.success("タスクを追加しました！")
            st.rerun()
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

# --- 2. タスクの表示と削除 ---
try:
    # DBから受信
    response = supabase.table("todos").select("*").order("created_at", desc=True).execute()
    todos = response.data

    st.subheader("現在のタスク一覧")

    if not todos:
        st.info("タスクはまだありません。")
    else:
        for todo in todos:
            col1, col2 = st.columns([4, 1])
            with col1:
                status = "✅" if todo['is_complete'] else "⬜"
                st.write(f"{status} {todo['task']}")
            with col2:
                if st.button("削除", key=todo['id']):
                    supabase.table("todos").delete().eq("id", todo['id']).execute()
                    st.rerun()
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
