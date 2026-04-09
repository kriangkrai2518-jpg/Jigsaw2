import streamlit as st
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip, vfx
from moviepy.audio.AudioClip import AudioArrayClip # นำเข้าเพื่อสร้างเสียงเงียบ
import tempfile, os, textwrap, numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- 1. ระบบพื้นฐาน ---
st.set_page_config(page_title="Jigsaw Universal Assembler", layout="wide")

def create_sub(text, size):
    w, h = size
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if text:
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.04))
        except: f = ImageFont.load_default()
        wt = textwrap.fill(text, width=40)
        bx = d.multiline_textbbox((0,0), wt, font=f)
        tw, th = bx[2]-bx[0], bx[3]-bx[1]
        d.multiline_text(((w-tw)/2, h-th-80), wt, font=f, fill=(255,255,255,255), align="center", stroke_width=2, stroke_fill=(0,0,0,255))
    return np.array(ov)

# ฟังก์ชันสร้างเสียงเงียบเพื่อเป็น Buffer
def make_silence(duration, fps=44100):
    return AudioArrayClip(np.zeros((int(fps*duration), 2)), fps=fps)

if 'v_path' not in st.session_state: 
    st.session_state.v_path = None

st.title("🎬 Jigsaw Master (Final Buffer Fix)")

# --- 2. UI Layout ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets")
    files = st.file_uploader("Add Images/MP4", type=['jpg','png','jpeg','mp4'], accept_multiple_files=True)
    bgm_f = st.file_uploader("🎵 Global BGM", type=["mp3","wav","m4a"])

with col2:
    st.header("🖥️ Terminal & Music Hub")
    bgm_v = st.slider("BGM Volume", 0.0, 1.0, 0.15, 0.05)
    voice_v = st.slider("Voiceover Volume", 0.0, 1.0, 0.90, 0.05)
    st.markdown("### 🛡️ Safe Music Hub")
    m_col1, m_col2 = st.columns(2)
    with m_col1: st.link_button("🎵 FB Sound Collection", "https://www.facebook.com/sound/collection/")
    with m_col2: st.link_button("📺 YT Audio Library", "https://www.youtube.com/audiolibrary")

st.divider()

# --- 3. Render Engine ---
configs = []
if files:
    sorted_files = sorted(files, key=lambda x: x.name)
    for i, f in enumerate(sorted_files):
        with st.expander(f"🎤 Scene {i+1}: {f.name}", expanded=True):
            sc1, sc2 = st.columns([2, 1])
            cap = sc1.text_area("Subtitle:", key=f"c_{i}", value=f"Scene {i+1}")
            voi = sc2.file_uploader("Voiceover", type=['mp3','wav','m4a'], key=f"v_{i}")
            dur = sc2.slider("Min Duration (Sec)", 1.0, 60.0, 4.0, key=f"d_{i}")
            configs.append({"f":f, "cap":cap, "dur":dur, "v":voi})

    if st.button("🚀 Start Final Render"):
        with st.status("🎬 Anti-Glitch Rendering...") as status:
            try:
                final_clips = []
                FPS = 24
                
                for cfg in configs:
                    ext = os.path.splitext(cfg["f"].name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
                        t.write(cfg["f"].getvalue())
                        p = t.name
                    
                    v_audio = None
                    scene_dur = cfg["dur"]
                    
                    if cfg["v"]:
                        v_ext = os.path.splitext(cfg["v"].name)[1].lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=v_ext) as vt:
                            vt.write(cfg["v"].getvalue())
                            vt.flush()
                            # ✅ สร้าง Voice + Silence 1 วินาทีกันพลาด
                            raw_v = AudioFileClip(vt.name).volumex(voice_v)
                            v_audio = CompositeAudioClip([raw_v, make_silence(1.0).set_start(raw_v.duration)])
                            scene_dur = max(scene_dur, raw_v.duration + 0.3)

                    if ext == '.mp4':
                        base_v = VideoFileClip(p).resize(width=1280).set_fps(FPS).without_audio()
                        base_v = base_v.set_duration(scene_dur) if base_v.duration < scene_dur else base_v.subclip(0, scene_dur)
                    else:
                        img = Image.open(p).convert("RGB")
                        new_h = int(1280 * img.height / img.width)
                        base_v = ImageClip(np.array(img.resize((1280, new_h)))).set_duration(scene_dur).set_fps(FPS)
                    
                    sub = ImageClip(create_sub(cfg["cap"], base_v.size)).set_duration(scene_dur).set_position('center')
                    clip = CompositeVideoClip([base_v, sub])
                    if v_audio: clip.audio = v_audio.set_duration(scene_dur)
                    final_clips.append(clip)

                full_video = concatenate_videoclips(final_clips, method="compose").set_fps(FPS)
                
                if bgm_f:
                    b_ext = os.path.splitext(bgm_f.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=b_ext) as bt:
                        bt.write(bgm_f.getvalue())
                        bt.flush()
                        os.fsync(bt.fileno())
                        
                        # ✅ สร้าง BGM Loop ที่มี Padding เสียงเงียบต่อท้าย 2 วินาที
                        bg_raw = AudioFileClip(bt.name)
                        bg_looped = bg_raw.fx(vfx.loop, duration=full_video.duration + 2.0)
                        bg_final = CompositeAudioClip([bg_looped, make_silence(2.0).set_start(bg_looped.duration)]).volumex(bgm_v)
                        
                        audio_tracks = [full_video.audio] if full_video.audio else []
                        audio_tracks.append(bg_final)
                        full_video.audio = CompositeAudioClip(audio_tracks).set_duration(full_video.duration)

                out = "final_jigsaw_ultra_stable.mp4"
                full_video.write_videofile(out, fps=FPS, codec="libx264", audio_codec="aac", audio_fps=44100)
                st.session_state.v_path = out
                status.update(label="✅ Success!", state="complete")
                
            except Exception as e:
                st.error(f"Render Error: {e}")

# --- 4. แสดงผล ---
if st.session_state.v_path:
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.video(st.session_state.v_path)
        with open(st.session_state.v_path, "rb") as f:
            st.download_button("📥 Download", f, "final_jigsaw.mp4", use_container_width=True)
    with res2:
        st.subheader("🚀 Share")
        st.link_button("🔵 Facebook Reels", "https://www.facebook.com/reels/create/")
        st.link_button("⚫ TikTok", "https://www.tiktok.com/upload")
