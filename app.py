import streamlit as st
import yt_dlp
import os
import uuid

# 初始化 Session State，用來記憶下載完成的檔案狀態
if 'is_processed' not in st.session_state:
    st.session_state.is_processed = False
    st.session_state.file_path = ""
    st.session_state.file_name = ""
    st.session_state.mime_type = ""

st.set_page_config(page_title="通用影片下載器", page_icon="🎬")
st.title("通用影片下載器 (Streamlit 版)")

# 建立暫存資料夾
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 步驟 1: 網址輸入
url = st.text_input("請輸入 YouTube 或 Facebook 影片網址：")

# 當網址改變時，重置下載狀態，避免顯示上一個影片的下載按鈕
def reset_state():
    st.session_state.is_processed = False

if url:
    try:
        # 解析影片名稱 (不實際下載)
        ydl_opts_info = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', '未命名影片')
            
        st.success(f"✅ 準備下載：{title}")
        
        # 步驟 2: 選擇格式
        mode = st.radio("請選擇下載格式：", ["高畫質影片 (MP4)", "純音訊 (MP3)"], on_change=reset_state)
        
        # 步驟 3: 觸發伺服器端下載
        if st.button("開始處理 (載入至伺服器)"):
            task_id = str(uuid.uuid4())[:8] # 產生隨機短碼避免檔名重複
            
            if mode == "高畫質影片 (MP4)":
                ext = "mp4"
                mime = "video/mp4"
                ydl_opts_download = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s"),
                    'merge_output_format': 'mp4',
                    'quiet': True
                }
            else:
                ext = "mp3"
                mime = "audio/mpeg"
                ydl_opts_download = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s"),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True
                }

            with st.spinner("伺服器正在下載與轉檔，請稍候... (需依賴 FFmpeg)"):
                # 執行 yt-dlp 下載
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    ydl.download([url])
                
                # 下載完成後，更新 Session State
                st.session_state.is_processed = True
                st.session_state.file_path = os.path.join(DOWNLOAD_DIR, f"{task_id}.{ext}")
                st.session_state.file_name = f"{title}.{ext}"
                st.session_state.mime_type = mime

        # 步驟 4: 顯示實體下載按鈕 (綁定 Session State)
        # 這樣一來，即便使用者點擊下載導致畫面重整，按鈕也不會消失
        if st.session_state.is_processed and os.path.exists(st.session_state.file_path):
            st.info("🎉 伺服器處理完成！請點擊下方按鈕將檔案儲存至您的電腦。")
            
            # 使用 open() 直接傳遞檔案物件，避免大型影片將記憶體塞滿
            with open(st.session_state.file_path, "rb") as file:
                st.download_button(
                    label=f"💾 儲存 {st.session_state.file_name}",
                    data=file,
                    file_name=st.session_state.file_name,
                    mime=st.session_state.mime_type
                )
                
    except Exception as e:
        st.error(f"發生錯誤：{e}")