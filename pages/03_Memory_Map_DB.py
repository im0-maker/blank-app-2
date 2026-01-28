import streamlit as st
from supabase import create_client, Client
import pandas as pd
from geopy.geocoders import Nominatim

# ページ設定
st.set_page_config(page_title="みんなの思い出マップ", layout="wide")

st.title("📍 みんなの思い出マップ (DB版)")

# 1. Supabaseへの接続
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Secretsの設定が見つかりません。")
    st.stop()

# --- サイドバー：登録フォーム ---
with st.sidebar:
    st.header("新しい場所を登録")

    # --- ステップ1: 場所検索 ---
    st.subheader("1. 場所を検索")
    search_query = st.text_input("住所や建物名を入力", placeholder="例: 東京タワー")
    search_pressed = st.button("📍 座標を検索する")

    # セッションステート初期化
    if 'search_lat' not in st.session_state: st.session_state.search_lat = 32.789
    if 'search_lon' not in st.session_state: st.session_state.search_lon = 130.689
    if 'place_name' not in st.session_state: st.session_state.place_name = ""

    if search_pressed and search_query:
        geolocator = Nominatim(user_agent="my_map_app_v2")
        try:
            location = geolocator.geocode(search_query)
            if location:
                st.session_state.search_lat = location.latitude
                st.session_state.search_lon = location.longitude
                st.session_state.place_name = search_query
                st.success(f"見つかりました！: {location.address}")
            else:
                st.error("場所が見つかりませんでした。")
        except Exception as e:
            st.error(f"検索エラー: {e}")

    st.divider()

    # --- ステップ2: 保存 ---
    st.subheader("2. 保存する")
    with st.form("save_form", clear_on_submit=True):
        name = st.text_input("場所の名前", value=st.session_state.place_name)
        lat = st.number_input("緯度", value=st.session_state.search_lat, format="%.6f")
        lon = st.number_input("経度", value=st.session_state.search_lon, format="%.6f")
        comment = st.text_area("ひとことコメント")
        
        submitted = st.form_submit_button("💾 保存")

        if submitted:
            if not name:
                st.error("名前を入れてください")
            else:
                data = {"place_name": name, "latitude": lat, "longitude": lon, "comment": comment}
                try:
                    supabase.table("memory_map").insert(data).execute()
                    st.success(f"「{name}」を保存しました！")
                    st.rerun() # 地図を更新
                except Exception as e:
                    st.error(f"保存エラー: {e}")

# --- メイン画面：地図表示 ---
try:
    # データベースから全データを取得
    response = supabase.table("memory_map").select("*").order("created_at", desc=True).execute()
    rows = response.data
    
    if rows:
        df = pd.DataFrame(rows)
        
        # 地図の表示
        st.subheader(f"🗺️ 登録されたスポット ({len(df)}件)")
        st.map(df, latitude="latitude", longitude="longitude")
        
        # データ一覧の表示
        with st.expander("📝 リストで見る"):
            st.dataframe(df[["place_name", "comment", "created_at"]])
    else:
        st.info("データがまだありません。サイドバーから登録してみよう！")
        
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
