import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from supabase import create_client, Client
import time

st.set_page_config(layout="wide", page_title="思い出フォトマップ (DB版)")

st.title("📸 どこでも思い出フォトマップ (Supabase保存版)")
st.caption("写真をアップすると自動でデータベースに場所が記録されます！")

# ------------------------------
# 1. Supabase接続設定
# ------------------------------
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Secretsの設定が見つかりません。")
    st.stop()

# 住所検索ツール
geolocator = Nominatim(user_agent="my_photo_map_db")

# ------------------------------
# 2. 関数定義（Exif読み取り用）
# ------------------------------
def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    return -(degrees + minutes + seconds) if ref in ['S', 'W'] else degrees + minutes + seconds

def get_lat_lon(image):
    try:
        exif_data = image._getexif()
        if not exif_data: return None, None
        
        gps_info = {}
        for tag, value in exif_data.items():
            if TAGS.get(tag) == "GPSInfo":
                for t in value:
                    gps_info[GPSTAGS.get(t, t)] = value[t]
        
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = get_decimal_from_dms(gps_info["GPSLatitude"], gps_info["GPSLatitudeRef"])
            lon = get_decimal_from_dms(gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"])
            return lat, lon
    except:
        pass
    return None, None

# ------------------------------
# 3. サイドバー：登録機能
# ------------------------------
with st.sidebar:
    st.header("📍 新しい場所を追加")

    # --- A. 写真から自動登録 ---
    st.subheader("A. 写真をアップロード")
    uploaded_files = st.file_uploader("GPS付き写真をアップ", type=['jpg', 'jpeg'], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("写真をデータベースに登録"):
            count = 0
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                lat, lon = get_lat_lon(image)
                
                if lat and lon:
                    # DBに保存するデータ
                    data = {
                        "place_name": uploaded_file.name, # ファイル名を場所に
                        "latitude": lat,
                        "longitude": lon,
                        "comment": "写真から自動登録"
                    }
                    try:
                        supabase.table("memory_map").insert(data).execute()
                        count += 1
                    except Exception as e:
                        st.error(f"エラー: {e}")
                else:
                    st.warning(f"「{uploaded_file.name}」にはGPSがありませんでした。下の検索を使ってね。")
            
            if count > 0:
                st.success(f"{count} 件の写真をDBに保存しました！")
                time.sleep(1)
                st.rerun()

    st.divider()

    # --- B. 地名検索で手動登録 ---
    st.subheader("B. 地名で検索して登録")
    place_name = st.text_input("場所の名前（例: 熊本城）")
    
    if st.button("検索して保存"):
        if place_name:
            try:
                location = geolocator.geocode(place_name)
                if location:
                    # DBに保存
                    data = {
                        "place_name": place_name,
                        "latitude": location.latitude,
                        "longitude": location.longitude,
                        "comment": "地名検索で登録"
                    }
                    supabase.table("memory_map").insert(data).execute()
                    st.success(f"「{place_name}」をDBに保存しました！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("場所が見つかりませんでした。")
            except Exception as e:
                st.error(f"エラー: {e}")

# ------------------------------
# 4. メイン画面：地図表示（DBから読み込み）
# ------------------------------
col1, col2 = st.columns([3, 1])

# DBからデータを取得
try:
    response = supabase.table("memory_map").select("*").order("created_at", desc=True).execute()
    db_data = response.data
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    db_data = []

with col1:
    st.subheader(f"🌏 みんなの地図 ({len(db_data)}件)")
    
    if db_data:
        # 地図の中心を決定（最新のデータの場所、なければ東京）
        last_item = db_data[0]
        m = folium.Map(location=[last_item['latitude'], last_item['longitude']], zoom_start=6)

        # ピンを立てるループ
        for item in db_data:
            lat = item['latitude']
            lon = item['longitude']
            name = item['place_name']
            comment = item.get('comment', '')
            
            # 自動登録(写真)と手動登録で色を変える演出
            color = "blue" if "写真" in comment else "red"
            
            popup_html = f"<b>{name}</b><br><span style='font-size:0.8em'>{comment}</span>"
            folium.Marker(
                [lat, lon],
                popup=popup_html,
                tooltip=name,
                icon=folium.Icon(color=color, icon="camera")
            ).add_to(m)

        st_folium(m, height=500, use_container_width=True)
    else:
        st.info("データがありません。サイドバーから登録してください。")

# データ一覧表示（確認用）
with col2:
    st.write("📋 登録リスト")
    for item in db_data:
        st.text(f"📍 {item['place_name']}")
