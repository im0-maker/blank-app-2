import streamlit as st
import folium
from streamlit_folium import st_folium
from PIL import Image, ExifTags
from geopy.geocoders import Nominatim
import sqlite3
import pandas as pd
import os

# --- ページ設定 ---
st.set_page_config(page_title="思い出フォトマップ", page_icon="📸", layout="wide")

# --- SQLite3 データベース設定 ---
DB_NAME = "photo_map.db"

def init_db():
    """データベースとテーブルの初期化"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_memory(location_name, latitude, longitude, comment):
    """新しい思い出データを保存"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO memories (location_name, latitude, longitude, comment)
        VALUES (?, ?, ?, ?)
    ''', (location_name, latitude, longitude, comment))
    conn.commit()
    conn.close()

def fetch_all_memories():
    """保存されたすべての思い出を取得"""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM memories ORDER BY created_at DESC", conn)
    conn.close()
    return df

# DB初期化を実行
init_db()

# --- Exifから緯度・経度を取得する補助関数 ---
def get_exif_location(image):
    try:
        exif = image._getexif()
        if not exif:
            return None, None

        gps_info = {}
        for key, value in exif.items():
            decode = ExifTags.TAGS.get(key, key)
            if decode == "GPSInfo":
                for t in value:
                    sub_decode = ExifTags.GPSTAGS.get(t, t)
                    gps_info[sub_decode] = value[t]

        if not gps_info:
            return None, None

        def convert_to_degrees(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)

        lat = convert_to_degrees(gps_info["GPSLatitude"])
        if gps_info.get("GPSLatitudeRef") != "N":
            lat = -lat

        lon = convert_to_degrees(gps_info["GPSLongitude"])
        if gps_info.get("GPSLongitudeRef") != "E":
            lon = -lon

        return lat, lon
    except Exception:
        return None, None

# --- UI構築 ---
st.title("📸 どこでも思い出フォトマップ")
st.caption("旅行の写真や思い出の場所を地図上に記録・保存できるアプリです（SQLite3 動作版）")

col_form, col_map = st.columns([1, 1])

with col_form:
    st.subheader("📍 新しい思い出を追加")
    
    reg_type = st.radio("登録方法を選択", ["写真から自動取得 (GPS)", "地名・キーワード検索"])
    
    lat = None
    lon = None
    default_name = ""

    if reg_type == "写真から自動取得 (GPS)":
        uploaded_file = st.file_uploader("写真をアップロード", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="アップロードされた写真", use_container_width=True)
            
            lat, lon = get_exif_location(image)
            if lat is not None and lon is not None:
                st.success(f"GPS位置情報を取得しました: 緯度 {lat:.4f}, 経度 {lon:.4f}")
            else:
                st.warning("写真にGPS情報が含まれていませんでした。地名検索で登録してください。")

    else:
        search_query = st.text_input("地名やスポット名を入力（例：熊本城、東京タワー）")
        if search_query:
            geolocator = Nominatim(user_agent="photo_map_app")
            try:
                location = geolocator.geocode(search_query)
                if location:
                    lat, lon = location.latitude, location.longitude
                    default_name = search_query
                    st.success(f"場所が見つかりました: {location.address}")
                else:
                    st.error("場所が見つかりませんでした。別の名称を試してください。")
            except Exception as e:
                st.error("検索中にエラーが発生しました。時間を置いて再度お試しください。")

    with st.form("memory_form"):
        location_name = st.text_input("場所の名称・見出し", value=default_name)
        comment = st.text_area("思い出コメント・感想")
        submitted = st.form_submit_button("地図に記録する")

        if submitted:
            if not location_name:
                st.warning("場所の名称を入力してください。")
            elif lat is None or lon is None:
                st.warning("位置情報（緯度・経度）が取得できていません。")
            else:
                insert_memory(location_name, lat, lon, comment)
                st.success(f"「{location_name}」を記録しました！")
                st.rerun()

with col_map:
    st.subheader("🗺️ 思い出マップ")
    memories_df = fetch_all_memories()

    # 地図の中心座標設定（データがあれば最新の登録地点、なければ熊本駅付近）
    if not memories_df.empty:
        center_lat = memories_df.iloc[0]["latitude"]
        center_lon = memories_df.iloc[0]["longitude"]
    else:
        center_lat, center_lon = 32.7898, 130.6888  # 熊本駅付近デフォルト

    m = folium.Map(location=[center_lat, center_lon], zoom_start=9)

    # 登録データのピン立て
    for _, row in memories_df.iterrows():
        popup_html = f"<b>{row['location_name']}</b><br>{row['comment'] if row['comment'] else ''}<br><small>{row['created_at']}</small>"
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row["location_name"],
            icon=folium.Icon(color="red", icon="camera")
        ).add_to(m)

    st_folium(m, width="100%", height=500)

# --- 登録一覧テーブル ---
st.divider()
st.subheader("📋 記録された思い出一覧")
if not memories_df.empty:
    st.dataframe(
        memories_df[["location_name", "latitude", "longitude", "comment", "created_at"]],
        use_container_width=True
    )
else:
    st.info("まだ思い出が登録されていません。左側のフォームから追加してみてください。")
