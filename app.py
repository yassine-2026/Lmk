import os
import json
import requests
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from groq import Groq
import time
import uuid

app = Flask(__name__)
CORS(app)

# Environment variables
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search-videos', methods=['POST'])
def search_videos():
    data = request.json
    query = data.get('query', '')
    
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
    r = requests.get(url, headers=PEXELS_HEADERS)
    
    return jsonify(r.json())

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.get_json(force=True)
        topic = data.get('topic', '')
        duration = data.get('duration', 30)
        tone = data.get('tone', 'professional')
        language = data.get('language', 'arabic')
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Step 1: Generate script with Groq
        script_parts = []
        video_scenes = []
        
        if groq_client:
            prompt = f"""Create a {duration} second video script about: {topic}
            Tone: {tone}
            Language: {language}
            
            Return ONLY valid JSON array:
            [
                {{"scene":1,"start":0,"end":5,"visual":"description","text":"text on screen","voice":"voiceover text"}},
                {{"scene":2,"start":5,"end":10,"visual":"description","text":"text on screen","voice":"voiceover text"}}
            ]
            """
            
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            script_text = response.choices[0].message.content
            
            # Try to parse JSON from response
            try:
                # Extract JSON from response
                start = script_text.find('[')
                end = script_text.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = script_text[start:end]
                    video_scenes = json.loads(json_str)
            except:
                # Fallback: parse manually
                lines = script_text.strip().split('\n')
                for i, line in enumerate(lines):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 6:
                            video_scenes.append({
                                "scene": i+1,
                                "start": int(parts[1]) if parts[1].isdigit() else i*5,
                                "end": int(parts[2]) if parts[2].isdigit() else (i+1)*5,
                                "visual": parts[3].strip(),
                                "text": parts[4].strip(),
                                "voice": parts[5].strip()
                            })
        
        # If no scenes generated, create default
        if not video_scenes:
            video_scenes = [
                {"scene":1,"start":0,"end":5,"visual":"opening scene","text":topic,"voice":f"Welcome to {topic}"},
                {"scene":2,"start":5,"end":10,"visual":"main content","text":"Key points","voice":"Learn the key points"},
                {"scene":3,"start":10,"end":15,"visual":"closing","text":"Thank you","voice":"Thanks for watching"}
            ]
        
        # Step 2: Get stock videos from Pexels
        for scene in video_scenes:
            try:
                if PEXELS_API_KEY:
                    url = f"https://api.pexels.com/videos/search?query={scene['visual']}&per_page=3"
                    headers = {"Authorization": PEXELS_API_KEY}
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        scene['videos'] = []
                        for v in data.get('videos', [])[:2]:
                            for vf in v['video_files']:
                                if vf['quality'] == 'hd':
                                    scene['videos'].append({
                                        "url": vf['link'],
                                        "width": vf['width'],
                                        "height": vf['height']
                                    })
                                    break
            except:
                scene['videos'] = []
        
        # Step 3: Generate full voiceover script
        full_voiceover = ' '.join([s.get('voice', '') for s in video_scenes])
        
        # Step 4: Music recommendations
        music = {
            "حماسي": {"name": "Upbeat Motivational", "query": "upbeat motivational"},
            "هادئ": {"name": "Calm Background", "query": "calm ambient"},
            "درامي": {"name": "Dramatic Epic", "query": "dramatic epic"},
            "مرح": {"name": "Happy Fun", "query": "happy fun"},
            "احترافي": {"name": "Corporate Professional", "query": "corporate professional"}
        }.get(tone, {"name": "Background", "query": "background"})
        
        # Return complete video package
        result = {
            "success": True,
            "scenes": video_scenes,
            "total_scenes": len(video_scenes),
            "total_duration": duration,
            "voiceover_text": full_voiceover,
            "music_suggestion": music,
            "hashtags": f"#{topic.replace(' ', '')} #video #content #{tone}",
            "download_links": {
                "script": f"/api/download-script/{uuid.uuid4()}",
                "assets": f"/api/download-assets/{uuid.uuid4()}"
            }
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "حدث خطأ. تأكد من المفاتيح والمحاولة مرة أخرى"
        }), 500

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "groq": bool(GROQ_API_KEY),
        "pexels": bool(PEXELS_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
