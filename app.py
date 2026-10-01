import streamlit as st
import yt_dlp
import os
import uuid
import time
import glob

# ===== 1. 初始化 Session State =====
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

st.set_page_config(page_title="雙模式影片下載器", page_icon="🎬")
st.title("通用影片下載器 (雙引擎版)")
st.markdown("支援 YouTube/FB。提供伺服器深度轉檔 (最高 1080p) 與瀏覽器極速直連雙模式。")

# ===== 2. 自動清理機制 =====
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_old_files(directory, max_age_seconds=1800):
    now = time.time()
    files = glob.glob(os.path.join(directory, "*"))
    for filepath in files:
        if os.path.isfile(filepath):
            if (now - os.path.getmtime(filepath)) > max_age_seconds:
                try:
                    os.remove(filepath)
                except Exception:
                    pass

cleanup_old_files(DOWNLOAD_DIR, max_age_seconds=1800)

def reset_download_state():
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

# ===== 4. 步驟二：預覽與選擇下載模式 =====
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
    st.markdown("### 選擇您的下載方式")
    
    # 建立兩個切換分頁
    tab1, tab2 = st.tabs(["☁️ 伺服器完整下載 (支援 1080p / MP3)", "⚡ 極速直連模式 (免等待轉檔)"])

    # ------------------ 分頁 1：伺服器下載模式 ------------------
    with tab1:
        st.info("此模式由伺服器幫您下載並合併最高畫質/音質，適合需要 1080p 或 MP3 的使用者。")
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

        if st.button("🚀 2. 開始伺服器下載與轉檔"):
            task_id = str(uuid.uuid4())[:8]
            
            progress_bar = st.progress(0.0)
            status_text = st.empty()

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
                            status_text.info(f"⏳ 進度：{percent*100:.1f}% | ⚡ {speed} | ⏱️️ {eta}")
                    except Exception:
                        pass
                elif d['status'] == 'finished':
                    progress_bar.progress(1.0)
                    status_text.warning("✅ 下載完畢！準備進行影音合併轉檔 (這可能耗費數分鐘，請稍候...)")

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
                    
                    st.session_state.is_processed = True
                    st.session_state.file_path = os.path.join(DOWNLOAD_DIR, f"{task_id}.{ext}")
                    
                    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    if not safe_title: safe_title = "video_download"
                        
                    st.session_state.file_name = f"{safe_title}.{ext}"
                    st.session_state.mime_type = mime
                    
                    status_text.success("🎉 處理完全結束！請點擊下方按鈕下載。")
                    
                except Exception as e:
                    status_text.error(f"下載過程中發生錯誤：{e}")

        if st.session_state.is_processed and os.path.exists(st.session_state.file_path):
            with open(st.session_state.file_path, "rb") as file:
                st.download_button(
                    label=f"💾 儲存檔案：{st.session_state.file_name}",
                    data=file,
                    file_name=st.session_state.file_name,
                    mime=st.session_state.mime_type,
                    type="primary" 
                )

    # ------------------ 分頁 2：極速直連模式 ------------------
    with tab2:
        st.success("此模式不消耗伺服器資源！系統已為您尋找預先合併好影音的底層網址，最高畫質受限於 720p。")
        
        if st.button("⚡ 產生極速直連網址"):
            # 直接從已經解析過的 session_state 提取資料，無須等待！
            combined_formats = [
                f for f in info.get('formats', []) 
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none'
            ]
            
            if combined_formats:
                combined_formats = sorted(combined_formats, key=lambda x: x.get('height', 0), reverse=True)
                best_format = combined_formats[0]
                
                direct_url = best_format.get('url')
                resolution = best_format.get('height')
                ext_direct = best_format.get('ext')
                
                st.info(f"✅ 成功提取 {resolution}p {ext_direct} 格式網址！")
                
                # 產生直接下載按鈕
                st.markdown(
                    f"""
                    <a href="{direct_url}" target="_blank" download>
                        <button style="padding: 12px 24px; background-color: #00CC66; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;">
                            👉 點擊此處由瀏覽器直接下載 ({resolution}p)
                        </button>
                    </a>
                    <p style="margin-top: 10px; font-size: 14px; color: gray;">
                        提示：若點擊後是在瀏覽器中直接播放，請在影片畫面上點擊右鍵選擇「另存影片」。部分平台因版權保護可能阻擋跨區直連，若失敗請改用分頁一的伺服器下載。
                    </p>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.warning("⚠️ 找不到包含聲音與影像的直連網址，請回到「伺服器完整下載」模式由系統為您合併。")