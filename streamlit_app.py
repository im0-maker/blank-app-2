import streamlit as st
from supabase import create_client, Client
import pandas as pd
from geopy.geocoders import Nominatim

# 1. Supabaseへの接続
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Secretsの設定が見つかりません。")
    st.stop()

st.title("📍 みんなの思い出マップ (App-2)")

# --- サイドバー ---
with st.sidebar:
    st.header("新しい場所を登録")

    # --- ステップ1: まず場所を検索 (フォームの外に配置) ---
    st.subheader("1. 場所を検索")
    search_query = st.text_input("住所や建物名を入力", placeholder="例: 東京タワー")
    search_pressed = st.button("📍 座標を検索する")

    # 検索結果を保持する変数を初期化
    if 'search_lat' not in st.session_state: st.session_state.search_lat = 32.789
    if 'search_lon' not in st.session_state: st.session_state.search_lon = 130.689
    if 'place_name' not in st.session_state: st.session_state.place_name = ""

    if search_pressed and search_query:
        geolocator = Nominatim(user_agent="my_map_app")
        try:
            location = geolocator.geocode(search_query)
            if location:
                # 検索できたら、保存用の変数（セッションステート）を上書きする
                st.session_state.search_lat = location.latitude
                st.session_state.search_lon = location.longitude
                st.session_state.place_name = search_query # 名前もコピー
                st.success(f"見つかりました！: {location.address}")
            else:
                st.error("場所が見つかりませんでした。")
        except Exception as e:
            st.error(f"検索エラー: {e}")

    st.divider() # 区切り線

    # --- ステップ2: 保存フォーム ---
    st.subheader("2. 保存する")
    with st.form("save_form", clear_on_submit=True):
        # 検索結果が value に入るように設定
        name = st.text_input("場所の名前", value=st.session_state.place_name)
        lat = st.number_input("緯度", value=st.session_state.search_lat, format="%.6f")
        lon = st.number_input("経度", value=st.session_state.search_lon, format="%.6f")
        comment = st.text_area("ひとことコメント")
        
        submitted = st.form_submit_button("💾 この内容で保存")

        if submitted:
            if not name:
                st.error("名前を入れてください")
            else:
                data = {"place_name": name, "latitude": lat, "longitude": lon, "comment": comment}
                try:
                    supabase.table("memory_map").insert(data).execute()
                    st.success(f"「{name}」を保存しました！")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

# --- メイン画面：地図表示 ---
try:
    response = supabase.table("memory_map").select("*").execute()
    rows = response.data
    if rows:
        df = pd.DataFrame(rows)
        st.map(df, latitude="latitude", longitude="longitude")
        
        with st.expander("📝 登録リストを見る"):
            st.dataframe(df[["place_name", "comment", "created_at"]])
    else:
        st.info("データがまだありません。")
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
