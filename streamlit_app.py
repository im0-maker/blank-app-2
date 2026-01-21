import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time

st.set_page_config(layout="wide", page_title="思い出フォトマップ")

st.title("📸 どこでも思い出フォトマップ")
st.caption("GPS付きの写真は自動で、ない写真は地名検索で地図に残そう！")

# ------------------------------
# 1. 準備（セッションと住所検索機能）
# ------------------------------
# データ保存用（リロードしても消えないようにする）
if 'gps_data' not in st.session_state:
    st.session_state['gps_data'] = {}  # {ファイル名: {'lat': 0.0, 'lon': 0.0, 'type': 'auto/manual'}}

# 住所検索ツール (user_agentは自分のアプリ名にする)
geolocator = Nominatim(user_agent="my_travel_memory_app")

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
# 3. サイドバー：写真アップロード
# ------------------------------
with st.sidebar:
    st.header("1. 写真を追加")
    uploaded_files = st.file_uploader(
        "ここから写真をアップロード", 
        type=['jpg', 'jpeg'], 
        accept_multiple_files=True
    )
    
    # 未処理の写真があれば処理する
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            
            # まだ登録されていない写真だけ処理
            if file_name not in st.session_state['gps_data']:
                image = Image.open(uploaded_file)
                lat, lon = get_lat_lon(image)
                
                if lat and lon:
                    # GPSがあれば即座に登録
                    st.session_state['gps_data'][file_name] = {
                        'lat': lat, 'lon': lon, 'type': 'auto'
                    }

# ------------------------------
# 4. メイン画面レイアウト
# ------------------------------
col1, col2 = st.columns([2, 1])

# GPSがなかった写真（手動登録待ち）を探す
pending_files = []
if uploaded_files:
    for f in uploaded_files:
        if f.name not in st.session_state['gps_data']:
            pending_files.append(f)

# --- 左側：地図表示 ---
with col1:
    st.subheader("🌏 思い出マップ")
    
    # 登録されたデータの中心、なければ日本全体
    if st.session_state['gps_data']:
        # 登録済みのピンの平均位置を中心に地図を表示
        lats = [d['lat'] for d in st.session_state['gps_data'].values()]
        lons = [d['lon'] for d in st.session_state['gps_data'].values()]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        zoom = 8
    else:
        center_lat, center_lon = 35.68, 139.76 # 東京あたり
        zoom = 5

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    # ピンを立てる
    for name, data in st.session_state['gps_data'].items():
        # 自動は青、手動は赤
        color = "blue" if data['type'] == 'auto' else "red"
        type_text = "GPS自動検出" if data['type'] == 'auto' else "地名検索"
        
        popup_html = f"""
        <div style="width:200px">
            <b>{name}</b><br>
            <span style="color:gray; font-size:0.8em;">{type_text}</span>
        </div>
        """
        
        folium.Marker(
            [data['lat'], data['lon']], 
            popup=popup_html,
            tooltip=name,
            icon=folium.Icon(color=color, icon="camera")
        ).add_to(m)

    st_folium(m, height=500, use_container_width=True)

# --- 右側：手動登録フォーム ---
with col2:
    st.subheader("🔍 位置情報の登録")
    
    if pending_files:
        st.info(f"位置情報のない写真が {len(pending_files)} 枚あります。")
        st.write("撮影場所の名前を入力して登録してください。")
        
        # 1. 写真選択
        target_file = st.selectbox(
            "写真を選択", 
            pending_files, 
            format_func=lambda x: x.name
        )
        
        # プレビュー
        img = Image.open(target_file)
        st.image(img, caption=target_file.name, use_container_width=True)
        
        # 2. 地名入力（ここが新しい！）
        place_name = st.text_input("場所の名前（例: 熊本城、阿蘇山）", key="place_input")
        
        if st.button("検索して登録"):
            if place_name:
                with st.spinner(f"「{place_name}」を探しています..."):
                    try:
                        location = geolocator.geocode(place_name)
                        time.sleep(1) # 連打防止のマナーとして少し待つ
                        
                        if location:
                            st.success(f"発見！: {location.address}")
                            # データを保存
                            st.session_state['gps_data'][target_file.name] = {
                                'lat': location.latitude, 
                                'lon': location.longitude, 
                                'type': 'manual'
                            }
                            time.sleep(1)
                            st.rerun() # 画面更新してピンを表示
                        else:
                            st.error("場所が見つかりませんでした。別の名前や住所で試してください。")
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")
            else:
                st.warning("場所の名前を入力してください。")
    else:
        if st.session_state['gps_data']:
            st.success("すべての写真が地図に配置されました！")
            st.canvas("🎈") # お祝いのアニメーション
        else:
            st.write("👈 まずは左のサイドバーから写真をアップロードしてください。")
