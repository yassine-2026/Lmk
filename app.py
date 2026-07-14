import os
import json
import uuid
import asyncio
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
import requests
import edge_tts
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get('GROQ_API_KEY', ''))
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')

VOICES = {
    "arabic_male": "ar-SA-HamedNeural",
    "arabic_female": "ar-SA-ZariyahNeural",
    "english_male": "en-US-GuyNeural",
    "english_female": "en-US-JennyNeural",
    "cartoon": "en-US-AnaNeural",
    "french": "fr-FR-DeniseNeural",
    "spanish": "es-ES-AlvaroNeural",
    "hindi": "hi-IN-MadhurNeural",
}

MUSIC_CATEGORIES = {
    "حماسي": "upbeat",
    "حزين": "sad", 
    "هادئ": "calm",
    "درامي": "dramatic",
    "مرح": "happy",
    "ملحمي": "epic",
    "تقني": "technology",
    "طبيعة": "nature",
}

def get_free_music_url(mood):
    music_urls = {
        "upbeat": "https://cdn.pixabay.com/audio/2024/upbeat.mp3",
        "calm": "https://cdn.pixabay.com/audio/2024/calm.mp3", 
        "dramatic": "https://cdn.pixabay.com/audio/2024/dramatic.mp3",
        "happy": "https://cdn.pixabay.com/audio/2024/happy.mp3",
        "epic": "https://cdn.pixabay.com/audio/2024/epic.mp3",
    }
    return music_urls.get(mood, music_urls.get("upbeat"))

def generate_video_script(topic, duration, tone, language):
    prompt = f"""Create a video script in {language}:
    Topic: {topic}
    Duration: {duration} seconds
    Tone: {tone}
    
    Format EXACTLY like this (one scene per line, no extra text, no markdown block):
    SCENE|start_time|end_time|visual_description|text_on_screen|voiceover_text
    
    Example:
    SCENE|0|5|busy city street morning|ابدأ مشوارك الآن|في هذا الفيديو سنتعلم أسرار النجاح
    SCENE|5|10|person working on laptop|الخطوة الأولى|أولا حدد هدفك بوضوح تام
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    return response.choices[0].message.content

def parse_scenes(script_text):
    scenes = []
    lines = script_text.strip().split('\n')
    for line in lines:
        if line.startswith('SCENE|'):
            parts = line.split('|')
            if len(parts) >= 6:
                scenes.append({
                    "start_time": parts[1],
                    "end_time": parts[2],
                    "visual": parts[3],
                    "text_on_screen": parts[4],
                    "voiceover": parts[5]
                })
    return scenes

def search_stock_videos(query, count=3):
    if not PEXELS_API_KEY:
        return []
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": count}
    try:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        videos = []
        for v in r.json().get('videos', []):
            for vf in v.get('video_files', []):
                if vf['quality'] == 'hd' and vf['width'] <= 1920:
                    videos.append({"url": vf['link'], "duration": v['duration'], "image": v.get('image')})
                    break
        return videos
    except Exception as e:
        print(f"Error fetching Pexels video: {e}")
        return []

async def generate_voice(text, voice_name, output_file):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_file)
    return output_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.json
        topic = data.get('topic')
        duration = int(data.get('duration', 30))
        tone = data.get('tone', 'احترافي')
        language = data.get('language', 'arabic')
        voice = data.get('voice', 'arabic_male')
        music_mood = data.get('music', 'حماسي')
        
        session_id = str(uuid.uuid4())
        
        script = generate_video_script(topic, duration, tone, language)
        scenes = parse_scenes(script)
        
        # Pexels search
        for scene in scenes:
            scene['videos'] = search_stock_videos(scene['visual'])
            
        voice_name = VOICES.get(voice, VOICES['arabic_male'])
        full_script = " ".join([s['voiceover'] for s in scenes if 'voiceover' in s])
        
        voice_file_path = f"static/voice_{session_id}.mp3"
        os.makedirs('static', exist_ok=True)
        
        if full_script.strip():
            asyncio.run(generate_voice(full_script, voice_name, voice_file_path))
            voice_url = f"/static/voice_{session_id}.mp3"
        else:
            voice_url = None
            
        music_url = get_free_music_url(music_mood)
        
        return jsonify({
            "scenes": scenes,
            "voice_url": voice_url,
            "music_url": music_url,
            "total_duration": duration,
            "script": script
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
