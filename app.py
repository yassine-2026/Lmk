import os
import json
import requests
import subprocess
import tempfile
import uuid
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from groq import Groq
from gtts import gTTS

app = Flask(__name__)
CORS(app)

# API Keys
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')

# Initialize Groq
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Output directory
OUTPUT_DIR = 'static/videos'
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.get_json(force=True)
        topic = data.get('topic', '')
        duration = data.get('duration', 30)
        tone = data.get('tone', 'professional')
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Generate script with Groq
        prompt = f"""Create a {duration} second video about: {topic}. Tone: {tone}.
        Return JSON array:
        [{{"scene":1,"start":0,"end":5,"visual":"description","text":"text on screen","voice":"voiceover in Arabic"}}]
        Return ONLY the JSON array, no other text."""
        
        scenes = []
        if groq_client:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            script_text = response.choices[0].message.content
            
            # Extract JSON
            try:
                start = script_text.find('[')
                end = script_text.rfind(']') + 1
                if start >= 0 and end > start:
                    scenes = json.loads(script_text[start:end])
            except:
                scenes = []
        
        # Default scenes if generation fails
        if not scenes:
            scenes = [
                {"scene":1,"start":0,"end":5,"visual":"opening","text":topic,"voice":f"مرحبا بكم في هذا الفيديو عن {topic}"},
                {"scene":2,"start":5,"end":10,"visual":"main content","text":"معلومات مهمة","voice":"سنستعرض معكم أهم المعلومات"},
                {"scene":3,"start":10,"end":15,"visual":"closing","text":"شكراً","voice":"شكراً لمشاهدتكم"}
            ]
        
        # Get stock videos from Pexels
        for scene in scenes:
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
                                if vf['quality'] == 'hd' and vf['width'] <= 1920:
                                    scene['videos'].append({"url": vf['link'], "width": vf['width'], "height": vf['height']})
                                    break
            except:
                scene['videos'] = []
        
        # Generate full voiceover
        full_voiceover = ' '.join([s.get('voice', '') for s in scenes])
        
        return jsonify({
            "success": True,
            "scenes": scenes,
            "voiceover_text": full_voiceover,
            "total_duration": duration
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create-video', methods=['POST'])
def create_video():
    try:
        data = request.get_json(force=True)
        scenes = data.get('scenes', [])
        
        if not scenes:
            return jsonify({"error": "No scenes provided"}), 400
        
        video_id = uuid.uuid4().hex[:8]
        work_dir = tempfile.mkdtemp()
        temp_files = []
        scene_files = []
        
        for i, scene in enumerate(scenes):
            # Download stock video or create black screen
            video_file = os.path.join(work_dir, f"video_{i}.mp4")
            if scene.get('videos') and len(scene['videos']) > 0:
                video_url = scene['videos'][0]['url']
                r = requests.get(video_url, timeout=30)
                with open(video_file, 'wb') as f:
                    f.write(r.content)
            else:
                # Create black screen video
                duration = scene['end'] - scene['start']
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'lavfi',
                    '-i', f'color=c=black:s=1080x1920:d={duration}',
                    '-c:v', 'libx264', '-preset', 'ultrafast',
                    video_file
                ], capture_output=True)
            temp_files.append(video_file)
            
            # Generate voiceover
            voice_file = os.path.join(work_dir, f"voice_{i}.mp3")
            tts = gTTS(text=scene.get('voice', ''), lang='ar', slow=False)
            tts.save(voice_file)
            temp_files.append(voice_file)
            
            # Add text overlay to video
            text = scene.get('text', '').replace(':', '\\:').replace("'", "\\'")
            duration = scene['end'] - scene['start']
            output_file = os.path.join(work_dir, f"scene_{i}.mp4")
            
            # FFmpeg command: video + text + audio
            cmd = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-i', voice_file,
                '-filter_complex',
                f"[0:v]trim=0:{duration},setpts=PTS-STARTPTS,drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10[v];[1:a]atrim=0:{duration}[a]",
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'ultrafast',
                '-c:a', 'aac', '-shortest',
                output_file
            ]
            subprocess.run(cmd, capture_output=True)
            scene_files.append(output_file)
            temp_files.append(output_file)
        
        # Concatenate all scenes
        concat_file = os.path.join(work_dir, 'concat.txt')
        with open(concat_file, 'w') as f:
            for sf in scene_files:
                f.write(f"file '{sf}'\n")
        
        final_output = os.path.join(OUTPUT_DIR, f"video_{video_id}.mp4")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file, '-c', 'copy', final_output
        ], capture_output=True)
        
        # Clean up
        shutil.rmtree(work_dir, ignore_errors=True)
        
        return jsonify({
            "success": True,
            "video_url": f"/{final_output}",
            "download_url": f"/{final_output}"
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "groq": bool(GROQ_API_KEY),
        "pexels": bool(PEXELS_API_KEY),
        "ffmpeg": os.path.exists('/usr/bin/ffmpeg')
    })

@app.route('/static/videos/<filename>')
def serve_video(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
