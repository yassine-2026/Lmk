import os
import json
import hashlib
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Groq client
# This requires GROQ_API_KEY to be set in the environment (.env file or Render secrets)
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
MODEL = "llama-3.3-70b-versatile"

# Simple in-memory cache
cache = {}
CACHE_DURATION = 3600 # 1 hour in seconds

def get_cache_key(payload):
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    try:
        data = request.json
        topic = data.get('topic')
        tone = data.get('tone')
        duration = data.get('duration')
        language = data.get('language', 'Arabic')

        if not topic:
            return jsonify({"error": "يرجى إدخال موضوع الفيديو"}), 400

        cache_key = get_cache_key({"type": "script", "topic": topic, "tone": tone, "duration": duration, "language": language})
        if cache_key in cache and (time.time() - cache[cache_key]['timestamp'] < CACHE_DURATION):
            return jsonify(cache[cache_key]['data'])

        prompt = f"""Generate a professional video script in {language}:
        Topic: {topic}
        Tone: {tone}
        Duration: {duration}
        
        Format the output EXACTLY as a JSON object with the following structure. Do not include any other text or markdown:
        {{
            "script": "Full script text here",
            "scenes": [
                {{
                    "time": "0-5s",
                    "visual": "Visual description",
                    "text": "Text on screen or spoken words"
                }}
            ],
            "hashtags": ["#tag1", "#tag2"],
            "music_suggestion": "music genre or vibe"
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        parsed_data = json.loads(response.choices[0].message.content)
        cache[cache_key] = {"data": parsed_data, "timestamp": time.time()}
        
        return jsonify(parsed_data)
    except Exception as e:
        return jsonify({"error": "حدث خطأ أثناء توليد السكريبت", "details": str(e)}), 500

@app.route('/api/generate-hooks', methods=['POST'])
def generate_hooks():
    try:
        data = request.json
        topic = data.get('topic')
        niche = data.get('niche', 'عام')

        if not topic:
            return jsonify({"error": "يرجى إدخال موضوع الفيديو"}), 400

        cache_key = get_cache_key({"type": "hooks", "topic": topic, "niche": niche})
        if cache_key in cache and (time.time() - cache[cache_key]['timestamp'] < CACHE_DURATION):
            return jsonify(cache[cache_key]['data'])

        prompt = f"""Generate 5 viral hooks in Arabic for a video about:
        Topic: {topic}
        Niche: {niche}
        
        Format the output EXACTLY as a JSON object:
        {{
            "hooks": ["hook 1", "hook 2", "hook 3", "hook 4", "hook 5"]
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        parsed_data = json.loads(response.choices[0].message.content)
        cache[cache_key] = {"data": parsed_data, "timestamp": time.time()}
        
        return jsonify(parsed_data)
    except Exception as e:
        return jsonify({"error": "حدث خطأ أثناء توليد الخطافات", "details": str(e)}), 500

@app.route('/api/generate-cta', methods=['POST'])
def generate_cta():
    try:
        data = request.json
        topic = data.get('topic')
        goal = data.get('goal', 'تفاعل')

        if not topic:
            return jsonify({"error": "يرجى إدخال موضوع الفيديو"}), 400

        cache_key = get_cache_key({"type": "cta", "topic": topic, "goal": goal})
        if cache_key in cache and (time.time() - cache[cache_key]['timestamp'] < CACHE_DURATION):
            return jsonify(cache[cache_key]['data'])

        prompt = f"""Generate a Call to Action (CTA) in Arabic for a video about:
        Topic: {topic}
        Goal: {goal}
        
        Format the output EXACTLY as a JSON object:
        {{
            "cta_text": "Main CTA text",
            "cta_variations": ["Variation 1", "Variation 2", "Variation 3"]
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        parsed_data = json.loads(response.choices[0].message.content)
        cache[cache_key] = {"data": parsed_data, "timestamp": time.time()}
        
        return jsonify(parsed_data)
    except Exception as e:
        return jsonify({"error": "حدث خطأ أثناء توليد CTA", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
