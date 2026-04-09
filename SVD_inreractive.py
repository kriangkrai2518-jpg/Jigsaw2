import streamlit as st
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip
import tempfile, os, textwrap, numpy as np
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Jigsaw Master", layout="wide")

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

if 'v_path' not in st.session_state: st.session_state.v_path = None

st.title("🎬 Jigsaw Master (Voice Sync)")
col1, col2 = st.columns(2)
with col1:
    files = st.file_uploader("Assets", type=['jpg','png','mp4'], accept_multiple_files=True)
    bgm_f = st.file_uploader("🎵 BGM", type=["mp3","wav","m4a"])
with col2:
    bgm_v = st.slider("BGM Vol", 0.0, 1.0, 0.15)
    voice_v = st.slider("Voice Vol", 0.0, 1.0, 0.90)

configs = []
if files:
    for i, f in enumerate(sorted(files, key=lambda x: x.name)):
        with st.expander(f"Scene {i+1}"):
            c1, c2 = st.columns(2)
            cap = c1.text_area("Subtitle", key=f"c_{i}", value=f"Scene {i+1}")
            voi = c2.file_uploader("Voice", type=['mp3','wav','m4a'], key=f"v_{i}")
            dur = c2.slider("Min Duration (Sec)", 1.0, 30.0, 4.0, key=f"d_{i}")
            configs.append({"f":f, "cap":cap, "dur":dur, "v":voi})

    if st.button("🚀 Render Video (Voice Priority)"):
        with st.status("Rendering...") as status:
            try:
                clips = []
                for cfg in configs:
                    ext = os.path.splitext(cfg["f"].name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as t:
                        t.write(cfg["f"].getvalue())
                        p = t.name
                    
                    # 1. จัดการเสียงพากย์เพื่อหา Duration ที่แท้จริง
                    v_audio = None
                    final_dur = cfg["dur"]
                    
                    if cfg["v"]:
                        v_ext = os.path.splitext(cfg["v"].name)[1].lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=v_ext) as vt:
                            vt.write(cfg["v"].getvalue())
                            vt.flush()
                            os.fsync(vt.fileno())
                            v_p = vt.name
                        v_audio = AudioFileClip(v_p).volumex(voice_v)
                        # ✅ บังคับให้ภาพยาวเท่าเสียงพากย์ (ถ้าเสียงพากย์ยาวกว่าค่าที่ตั้งไว้)
                        final_dur = max(cfg["dur"], v_audio.duration + 0.5) # เผื่อเวลาหายใจ 0.5 วิ

                    # 2. สร้าง Visual Clip ตาม Duration ที่คำนวณใหม่
                    if ext == '.mp4':
                        v = VideoFileClip(p).resize(width=1280).set_fps(24).without_audio()
                        # ถ้าวิดีโอสั้นกว่าเสียงพากย์ ให้ค้างเฟรมสุดท้ายไว้ (Loop/Freeze)
                        if v.duration < final_dur:
                            v = v.set_duration(final_dur)
                        else:
                            v = v.subclip(0, final_dur)
                    else:
                        img = Image.open(p).convert("RGB")
                        v = ImageClip(np.array(img.resize((1280, int(1280*img.height/img.width))))).set_duration(final_dur).set_fps(24)
                    
                    # 3. รวม Subtitle และ Audio
                    sub = ImageClip(create_sub(cfg["cap"], v.size)).set_duration(v.duration).set_position('center')
                    clip = CompositeVideoClip([v, sub])
                    
                    if v_audio:
                        clip = clip.set_audio(v_audio.set_duration(final_dur))
                    
                    clips.append(clip)

                # 4. Mix กับ BGM
                full = concatenate_videoclips(clips, method="compose").set_fps(24)
                tracks = [full.audio] if full.audio else []
                
                if bgm_f:
                    b_ext = os.path.splitext(bgm_f.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=b_ext) as bt:
                        bt.write(bgm_f.getvalue())
                        bt.flush()
                        os.fsync(bt.fileno())
                        b_p = bt.name
                    tracks.append(AudioFileClip(b_p).volumex(bgm_v).set_duration(full.duration))
                
                if tracks: full.audio = CompositeAudioClip(tracks)
                
                out = "voice_priority_final.mp4"
                full.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", audio_fps=44100, remove_temp=True)
                st.session_state.v_path = out
                status.update(label="✅ Render Success!", state="complete")
            except Exception as e: st.error(f"Render Error: {e}")

if st.session_state.v_path:
    st.video(st.session_state.v_path)
    with open(st.session_state.v_path, "rb") as f:
        st.download_button("📥 Download Video", f, "final_video.mp4")
