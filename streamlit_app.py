import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Supabaseへの接続
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Secretsの設定が見つかりません。Streamlit管理画面でSUPABASE_URLとSUPABASE_KEYを設定してください。")
    st.stop()

st.title("📍 みんなの思い出マップ (App-2)")
st.write("データが消えない地図アプリです。")

# --- サイドバー：データ入力フォーム ---
with st.sidebar:
    st.header("新しい場所を登録")
    with st.form("input_form", clear_on_submit=True):
        name = st.text_input("場所の名前（例：熊本城）")
        # デフォルト値は熊本駅あたり
        lat = st.number_input("緯度", value=32.789, format="%.6f")
        lon = st.number_input("経度", value=130.689, format="%.6f")
        comment = st.text_area("ひとことコメント")
        
        submitted = st.form_submit_button("保存する")

        if submitted:
            if not name:
                st.error("場所の名前を入れてください！")
            else:
                data = {
                    "place_name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "comment": comment
                }
                try:
                    supabase.table("memory_map").insert(data).execute()
                    st.success(f"「{name}」を保存しました！")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

# --- メイン画面：地図とデータの表示 ---
try:
    response = supabase.table("memory_map").select("*").execute()
    rows = response.data

    if rows:
        df = pd.DataFrame(rows)
        # 地図表示
        st.map(df, latitude="latitude", longitude="longitude")
        
        # リスト表示
        st.write("📝 登録リスト")
        st.dataframe(df[["place_name", "comment", "created_at"]])
    else:
        st.info("データがまだありません。サイドバーから登録してね！")
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
