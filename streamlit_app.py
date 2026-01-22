import streamlit as st
from supabase import create_client, Client
import pandas as pd
from geopy.geocoders import Nominatim # 住所検索用のライブラリ

# 1. Supabaseへの接続
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Secretsの設定が見つかりません。")
    st.stop()

st.title("📍 みんなの思い出マップ (App-2)")

# --- サイドバー：データ入力フォーム ---
with st.sidebar:
    st.header("新しい場所を登録")
    
    # セッション状態の初期化（検索した座標を覚えておくため）
    if 'lat' not in st.session_state: st.session_state.lat = 32.789
    if 'lon' not in st.session_state: st.session_state.lon = 130.689

    with st.form("input_form", clear_on_submit=False): # 検索しても消えないようにFalseに変更
        name = st.text_input("場所の名前（検索したい住所）")
        
        # 検索ボタン
        search_pressed = st.form_submit_button("📍 住所から座標を検索")
        
        if search_pressed and name:
            geolocator = Nominatim(user_agent="my_map_app")
            try:
                location = geolocator.geocode(name)
                if location:
                    st.session_state.lat = location.latitude
                    st.session_state.lon = location.longitude
                    st.success(f"見つかりました！: {location.address}")
                else:
                    st.error("場所が見つかりませんでした。")
            except Exception as e:
                st.error(f"検索エラー: {e}")

        # 座標入力（検索結果が自動で入る）
        lat = st.number_input("緯度", value=st.session_state.lat, format="%.6f", key="lat_input")
        lon = st.number_input("経度", value=st.session_state.lon, format="%.6f", key="lon_input")
        comment = st.text_area("ひとことコメント")
        
        # 保存ボタン
        save_pressed = st.form_submit_button("💾 保存する")

        if save_pressed:
            if not name:
                st.error("場所の名前を入れてください！")
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
        st.write("📝 登録リスト")
        st.dataframe(df[["place_name", "comment", "created_at"]])
    else:
        st.info("データがまだありません。")
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
