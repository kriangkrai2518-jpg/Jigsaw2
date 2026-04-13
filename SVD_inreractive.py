import PIL.Image
# ✅ ดักจับ Error ANTIALIAS สำหรับ Pillow เวอร์ชันใหม่
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import streamlit as st
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip, vfx
from moviepy.audio.AudioClip import AudioArrayClip
import tempfile, os, textwrap, numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- 1. ระบบพื้นฐาน & Memory ---
st.set_page_config(page_title="Jigsaw Branding Master", layout="wide")

# ระบบจำค่า (Persistent State)
if 'wm_text' not in st.session_state: st.session_state.wm_text = "Jigsaw Master"
if 'phone_num' not in st.session_state: st.session_state.phone_num = "เบิร์ด เสฎฐพงศ์"
if 'contact_msg' not in st.session_state: st.session_state.contact_msg = "065-246-5144 Line:..."

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

def create_watermark(text, size):
    w, h = size
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if text:
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.025))
        except: f = ImageFont.load_default()
        d.text((w-200, 40), text, font=f, fill=(255,255,255,100))
    return np.array(ov)

def create_contact_banner(phone, message, size):
    w, h = size
    b_h = int(h * 0.08)
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if phone or message:
        d.rectangle((0, 0, w, b_h), fill=(0,0,0,180))
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.03))
        except: f = ImageFont.load_default()
        full_text = f"{phone} {message}"
        # ✅ ตัวหนังสือสีแดง Pure Red ตามแบรนด์
        d.text((40, 10), full_text, font=f, fill=(255,0,0,255))
    return np.array(ov)

def make_silence(duration, fps=44100):
    return AudioArrayClip(np.zeros((int(fps*duration), 2)), fps=fps)

# --- 2. UI Layout ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets & Data")
    files = st.file_uploader("Add Video/Images", type=['jpg','png','jpeg','mp4'], accept_multiple_files=True)
    bgm_f = st.file_uploader("🎵 Global BGM", type=["mp3","wav","m4a"])

with col2:
    st.header("⚙️ Branding & Export")
    wm_text = st.text_input("Watermark Text (Top):", value=st.session_state.wm_text, key="wm_input")
    phone_num = st.text_input("Contact Name/Brand:", value=st.session_state.phone_num, key="phone_input")
    contact_msg = st.text_input("Contact Details (Phone/Line):", value=st.session_state.contact_msg, key="msg_input")
    
    st.session_state.wm_text, st.session_state.phone_num, st.session_state.contact_msg = wm_text, phone_num, contact_msg
    
    bgm_v = st.slider("BGM Volume", 0.0, 1.0, 0.10, 0.05)
    voice_v = st.slider("Voice Balance", 0.0, 1.0, 0.90, 0.05)
    st.divider()
    render_btn = st.button("🚀 Start Rendering", use_container_width=True)
    line_btn = st.button("🟢 Convert to LINE Format", use_container_width=True)

# --- 3. Render Engine ---
configs = []
if files:
    sorted_files = sorted(files, key=lambda x: x.name)
    for i, f in enumerate(sorted_files):
        with st.expander(f"🎤 Scene {i+1}: {f.name}", expanded=True):
            sc1, sc2 = st.columns([2, 1])
            cap = sc1.text_area("Caption:", key=f"c_{i}", value=f"Scene {i+1}")
            voi = sc2.file_uploader("Voice File", type=['mp3','wav','m4a'], key=f"v_{i}")
            dur = sc2.slider("Min Duration", 1.0, 60.0, 4.0, key=f"d_{i}")
            configs.append({"f":f, "cap":cap, "dur":dur, "v":voi})

    if render_btn or line_btn:
        is_line = bool(line_btn)
        with st.status("🎬 Rendering..." if not is_line else "🟢 LINE Processing...") as status:
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
                            raw_v = AudioFileClip(vt.name).volumex(voice_v)
                            # ✅ ล็อคความยาวเสียงและเติมความเงียบสั้นๆ ท้าย Scene
                            v_audio = CompositeAudioClip([raw_v, make_silence(0.5).set_start(raw_v.duration)])
                            scene_dur = max(scene_dur, v_audio.duration)

                    if ext == '.mp4':
                        base_v = VideoFileClip(p).resize(width=1280).set_fps(FPS).without_audio()
                        base_v = base_v.set_duration(scene_dur) if base_v.duration < scene_dur else base_v.subclip(0, scene_dur)
                    else:
                        img = Image.open(p).convert("RGB")
                        new_h = int(1280 * img.height / img.width)
                        # ✅ ใช้ Image.Resampling.LANCZOS เพื่อความคมชัดสูงสุด
                        base_v = ImageClip(np.array(img.resize((1280, new_h), Image.Resampling.LANCZOS))).set_duration(scene_dur).set_fps(FPS)
                    
                    # เลเยอร์ตกแต่ง
                    sub = ImageClip(create_sub(cfg["cap"], base_v.size)).set_duration(scene_dur).set_position('center')
                    wm = ImageClip(create_watermark(wm_text, base_v.size)).set_duration(scene_dur).set_position('center')
                    banner = ImageClip(create_contact_banner(phone_num, contact_msg, base_v.size)).set_duration(scene_dur).set_position('center')
                    
                    # ✅ ประกอบร่างและล็อคเสียงราย Scene (Audio Lock)
                    scene_clip = CompositeVideoClip([base_v, sub, wm, banner], size=base_v.size).set_duration(scene_dur)
                    scene_clip.audio = v_audio if v_audio else make_silence(scene_dur)
                    final_clips.append(scene_clip)

                # รวมทุก Scene
                full_video = concatenate_videoclips(final_clips, method="compose")
                
                # ✅ ระบบผสม Global BGM
                if bgm_f:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as bt:
                        bt.write(bgm_f.getvalue())
                        bg_raw = AudioFileClip(bt.name)
                        bg_final = bg_raw.fx(vfx.loop, duration=full_video.duration).volumex(bgm_v)
                        full_video.audio = CompositeAudioClip([full_video.audio, bg_final]).set_duration(full_video.duration)

                out_name = "line_optimized.mp4" if is_line else "standard_output.mp4"
                temp_audio = "render_temp_audio.m4a" # ล็อคชื่อไฟล์เสียงชั่วคราว
                
                export_params = {
                    "filename": out_name, "fps": FPS, "codec": "libx264", 
                    "audio_codec": "aac", "audio_fps": 44100, "remove_temp": True,
                    "temp_audiofile": temp_audio
                }
                if is_line: export_params["ffmpeg_params"] = ["-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "3.1"]

                full_video.write_videofile(**export_params)
                status.update(label="✅ Success!", state="complete")
                
                st.video(out_name)
                with open(out_name, "rb") as f:
                    st.download_button("📥 Download Video", f, out_name, use_container_width=True)

            except Exception as e:
                st.error(f"Render Error: {e}")
