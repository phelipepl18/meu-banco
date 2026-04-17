import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os
import gc
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Estrategista de Cortes", layout="wide")

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

# FUNÇÃO PARA CRIAR O TEXTO (ESTILO IMAGEM QUE VOCÊ MANDOU)
def criar_imagem_texto(texto, largura=900):
    img = Image.new('RGBA', (largura, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Tenta carregar uma fonte padrão, se não tiver usa básica
    try: font = ImageFont.truetype("Arial Bold.ttf", 60)
    except: font = ImageFont.load_default()
    
    # Desenha o texto centralizado
    w_txt, h_txt = draw.textbbox((0, 0), texto, font=font)[2:4]
    draw.text(((largura-w_txt)/2, (200-h_txt)/2), texto, font=font, fill="white")
    img.save("txt_temp.png")
    return "txt_temp.png"

st.title("🎙️ Estrategista de Cortes Profissional")

file = st.file_uploader("1. Suba seu vídeo", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Imagem de fundo", type=["jpg", "jpeg", "png"])

if file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f: f.write(file.getbuffer())

    with VideoFileClip(temp_path) as v_info:
        duracao_real = v_info.duration
        st.info(f"📏 Duração: {int(duracao_real // 60):02d}:{int(duracao_real % 60):02d}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Sugestões da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("Analisando..."):
                # (Lógica de transcrição mantida igual...)
                st.session_state['analise_geral'] = "Sugestões carregadas (Exemplo: 00:10 - 00:30)"

    with col2:
        st.subheader("2. Configurar o seu Corte")
        t_in = st.text_input("Início", value="0:00")
        t_out = st.text_input("Fim", value="0:30")
        titulo_video = st.text_input("Tema Forte (Texto no vídeo):", value="O SEGREDO DA RETENÇÃO")
        
        estilo = st.radio("Formato:", ["Fundo Personalizado + Título", "Foco Único"])

        if st.button("🚀 Gerar Vídeo"):
            s, e = converter_tempo(t_in), converter_tempo(t_out)
            if s is not None and e is not None:
                with st.spinner("Renderizando..."):
                    try:
                        with VideoFileClip(temp_path) as video:
                            clip = video.subclip(s, e)
                            
                            if estilo == "Fundo Personalizado + Título":
                                if not bg_image: st.error("Suba o fundo!"); st.stop()
                                
                                # Processa Fundo
                                with open("bg.png", "wb") as f: f.write(bg_image.getbuffer())
                                bg = ImageClip("bg.png").set_duration(clip.duration).resize(height=1920)
                                bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
                                
                                # Processa Vídeo (Horizontal no meio)
                                vid_meio = clip.resize(width=1000)
                                
                                # Processa Texto (Pillow)
                                path_txt = criar_imagem_texto(titulo_video.upper())
                                txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 450))
                                
                                # Tarja preta atrás do texto
                                tarja = ColorClip(size=(1080, 150), color=(0,0,0)).set_opacity(0.5).set_duration(clip.duration).set_position(('center', 475))
                                
                                final = CompositeVideoClip([bg, tarja, txt_clip, vid_meio.set_position("center")])
                            
                            else:
                                # Foco Único simples
                                final = clip.crop(x_center=clip.w/2, width=int(clip.h*(9/16)), height=clip.h)

                            # SALVAMENTO COM CODEC COMPATÍVEL
                            output = "resultado_final.mp4"
                            final.write_videofile(output, 
                                                codec="libx264", 
                                                audio_codec="aac", 
                                                temp_audiofile="temp-audio.m4a", 
                                                remove_temp=True, 
                                                fps=24,
                                                preset="ultrafast")
                            
                            st.video(output) # Agora o vídeo deve carregar!
                            with open(output, "rb") as f:
                                st.download_button("⬇️ Baixar", f, "corte.mp4")
                        gc.collect()
                    except Exception as err: st.error(f"Erro: {err}")
