import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, TextClip
from groq import Groq
import os
import gc
import PIL.Image

# Correção Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

st.set_page_config(page_title="Estrategista de Cortes Profissional", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets!")

def converter_tempo(texto):
    try:
        texto = texto.strip().replace(",", ".")
        if ":" in texto:
            partes = texto.split(":")
            return (int(partes[0]) * 60) + float(partes[1])
        return float(texto)
    except: return None

st.title("🎙️ Estrategista de Cortes Profissional")

# Uploads
file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Suba a imagem de fundo (Obrigatório para o layout da imagem)", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f: f.write(file.getbuffer())

    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        st.warning(f"📏 Duração: {int(duracao_real // 60):02d}:{int(duracao_real % 60):02d}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Sugestões da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("Analisando..."):
                try:
                    with VideoFileClip(temp_path) as video_full:
                        video_full.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    with open("audio_temp.mp3", "rb") as a:
                        trans = client.audio.transcriptions.create(file=("audio_temp.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                    st.session_state['transcricao'] = trans
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": f"Sugira 3 cortes em MM:SS até {duracao_real}s: {trans}"}],
                        model="llama-3.1-8b-instant"
                    )
                    st.session_state['analise_geral'] = res.choices[0].message.content
                except Exception as e: st.error(f"Erro: {e}")
        if 'analise_geral' in st.session_state: st.info(st.session_state['analise_geral'])

    with col2:
        st.subheader("2. Configurar o seu Corte")
        t_in = st.text_input("Início (ex: 1:30)", value="0:00")
        t_out = st.text_input("Fim (ex: 2:00)", value="0:30")
        
        # Título que vai aparecer NO VÍDEO
        titulo_video = st.text_input("Texto para o vídeo (Tema Forte):", placeholder="Ex: O SEGREDO DA RETENÇÃO")

        if st.button("💡 Gerar Tema Forte com IA"):
            if 'transcricao' in st.session_state:
                res_tema = client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Crie um título curto e viral para o trecho {t_in} a {t_out}: {st.session_state['transcricao']}"}],
                    model="llama-3.1-8b-instant"
                )
                st.session_state['tema_sugerido'] = res_tema.choices[0].message.content.replace('"', '')
                st.success(f"Sugestão: {st.session_state['tema_sugerido']}")
            else: st.error("Analise o vídeo primeiro.")

        estilo = st.radio("Formato:", ["Fundo Personalizado + Título", "Foco Único", "Split Screen"])

        if st.button("🚀 Gerar Vídeo Final"):
            s, e = converter_tempo(t_in), converter_tempo(t_out)
            if s is not None and e is not None and s < e:
                with st.spinner("Criando composição profissional..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(s, e)
                            
                            if estilo == "Fundo Personalizado + Título":
                                if not bg_image: st.error("Suba a imagem de fundo!"); st.stop()
                                
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                
                                vid_meio = clip.resize(width=1000) # Deixa uma bordinha nas laterais
                                
                                # CRIAÇÃO DO TEXTO (Usando TextClip)
                                txt = TextClip(
                                    titulo_video if titulo_video else "Corte Viral",
                                    fontsize=70, color='white', font='Arial-Bold',
                                    method='caption', size=(900, None)
                                ).set_duration(clip.duration).set_position(('center', 400)) # Posição acima do vídeo
                                
                                # Tarja preta atrás do texto para ler melhor
                                bg_txt = ColorClip(size=(1080, 200), color=(0,0,0)).set_opacity(0.6).set_duration(clip.duration).set_position(('center', 350))
                                
                                final = CompositeVideoClip([bg, bg_txt, txt, vid_meio.set_position("center")])
                            
                            # (Outros estilos omitidos aqui para brevidade, mas mantidos no seu código original)
                            
                            final.write_videofile("final.mp4", codec="libx264", audio_codec="aac", fps=24)
                            st.video("final.mp4")
                            with open("final.mp4", "rb") as f: st.download_button("⬇️ Baixar", f, "corte.mp4")
                        gc.collect()
                    except Exception as err: st.error(f"Erro: {err}. Nota: Textos requerem ImageMagick no servidor.")
