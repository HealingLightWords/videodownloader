import streamlit as st
import yt_dlp
import os
import uuid
import time
import glob

# ===== 1. 初始化 Session State =====
# 確保網頁重新載入時，這些變數不會被清空
if 'video_info' not in st.session_state:
    st.session_state.video_info = None
if 'is_processed' not in st.session_state:
    st.session_state.is_processed = False
if 'file_path' not in st.session_state:
    st.session_state.file_path = ""
if 'file_name' not in st.session_state:
    st.session_state.file_name = ""
if 'mime_type' not in st.session_state:
    st.session_state.mime_type = ""

st.set_page_config(page_title="通用影片下載器", page_icon="🎬")
st.title("通用影片下載器 (完整進化版)")
st.markdown("支援 YouTube、Facebook 等平台，具備進度條與自動清理機制。")

# ===== 2. 自動清理機制 =====
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_old_files(directory, max_age_seconds=1800):
    """清理超過 30 分鐘的暫存檔案，保護伺服器硬碟空間"""
    now = time.time()
    files = glob.glob(os.path.join(directory, "*"))
    for filepath in files:
        if os.path.isfile(filepath):
            if (now - os.path.getmtime(filepath)) > max_age_seconds:
                try:
                    os.remove(filepath)
                except Exception:
                    pass

# 每次互動時自動檢查並清理
cleanup_old_files(DOWNLOAD_DIR, max_age_seconds=1800)

def reset_download_state():
    """當網址或格式改變時，隱藏前一次的下載按鈕"""
    st.session_state.is_processed = False

# ===== 3. 步驟一：輸入與解析 =====
url = st.text_input("請輸入 YouTube 或 Facebook 影片網址：", on_change=reset_download_state)

if st.button("🔍 1. 解析影片網址"):
    if url:
        with st.spinner("正在獲取影片資訊，請稍候..."):
            ydl_opts_info = {'quiet': True}
            try:
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    info = ydl.extract_info(url, download=False)
                    st.session_state.video_info = info
                    st.session_state.is_processed = False 
            except Exception as e:
                st.error(f"解析失敗，請確認網址是否正確或為私人影片：{e}")
    else:
        st.warning("⚠️ 請先輸入網址！")

# ===== 4. 步驟二：預覽與選擇格式 =====
if st.session_state.video_info:
    info = st.session_state.video_info
    title = info.get('title', '未命名影片')
    thumbnail = info.get('thumbnail')
    
    st.success(f"✅ 成功解析：{title}")
    
    with st.expander("👁️ 點擊展開預覽畫面", expanded=True):
        try:
            st.video(url)
        except Exception:
            if thumbnail:
                st.image(thumbnail, use_container_width=True, caption="影片封面預覽")
    
    st.markdown("---")
    
    mode = st.selectbox(
        "請選擇下載格式與品質：", 
        [
            "影片 - HD 高畫質 (最高至 1080p)", 
            "影片 - SD 標準畫質 (最高至 480p)", 
            "音訊 - 320K MP3 (高音質)", 
            "音訊 - 128K MP3 (標準音質)"
        ],
        on_change=reset_download_state
    )

    # ===== 5. 步驟三：開始處理與下載 =====
    if st.button("🚀 2. 開始下載與轉檔"):
        task_id = str(uuid.uuid4())[:8]
        
        # 準備動態 UI 佔位符
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        # 自訂進度回呼函式
        def download_hook(d):
            if d['status'] == 'downloading':
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = min(downloaded / total, 1.0)
                        progress_bar.progress(percent)
                        
                        speed = d.get('_speed_str', '未知')
                        eta = d.get('_eta_str', '未知')
                        status_text.info(f"⏳ 下載進度：{percent*100:.1f}% | ⚡ 速度：{speed} | ⏱️ 剩餘：{eta}")
                except Exception:
                    pass
            elif d['status'] == 'finished':
                progress_bar.progress(1.0)
                status_text.warning("✅ 下載完畢！準備進行影音合併轉檔 (這可能耗費數分鐘，請稍候...)")

        # 根據選擇設定 yt-dlp 參數
        if "影片 - HD" in mode:
            ext, mime = "mp4", "video/mp4"
            ydl_format = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            postprocessors = []
        elif "影片 - SD" in mode:
            ext, mime = "mp4", "video/mp4"
            ydl_format = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'
            postprocessors = []
        elif "音訊 - 320K" in mode:
            ext, mime = "mp3", "audio/mpeg"
            ydl_format = 'bestaudio/best'
            postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
        elif "音訊 - 128K" in mode:
            ext, mime = "mp3", "audio/mpeg"
            ydl_format = 'bestaudio/best'
            postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]

        ydl_opts_download = {
            'format': ydl_format,
            'outtmpl': os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s"),
            'merge_output_format': 'mp4' if "影片" in mode else None,
            'postprocessors': postprocessors if postprocessors else [],
            'quiet': True,
            'progress_hooks': [download_hook]
        }

        with st.spinner("啟動下載引擎中..."):
            try:
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    ydl.download([url])
                
                # 紀錄處理完成的檔案資訊
                st.session_state.is_processed = True
                st.session_state.file_path = os.path.join(DOWNLOAD_DIR, f"{task_id}.{ext}")
                
                # 清除標題中的特殊符號，避免作業系統存檔時發生錯誤
                safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                if not safe_title: 
                    safe_title = "video_download"
                    
                st.session_state.file_name = f"{safe_title}.{ext}"
                st.session_state.mime_type = mime
                
                status_text.success("🎉 處理完全結束！請點擊下方按鈕下載。")
                
            except Exception as e:
                status_text.error(f"下載過程中發生錯誤：{e}")

    # ===== 6. 步驟四：提供本機下載按鈕 =====
    if st.session_state.is_processed and os.path.exists(st.session_state.file_path):
        st.markdown("---")
        with open(st.session_state.file_path, "rb") as file:
            st.download_button(
                label=f"💾 儲存檔案：{st.session_state.file_name}",
                data=file,
                file_name=st.session_state.file_name,
                mime=st.session_state.mime_type,
                type="primary" # 將按鈕設置為醒目的主色調
            )