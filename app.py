import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from groq import Groq
import requests
import json

app = Flask(__name__)
CORS(app)

# Initialize Groq
groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

# Initialize Pexels
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    data = request.json
    topic = data.get('topic', '')
    tone = data.get('tone', 'professional')
    duration = data.get('duration', 30)
    
    prompt = f"Create a {duration}s video script about: {topic}. Tone: {tone}. Format: SCENE|start|end|visual|text|voiceover"
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    
    script = response.choices[0].message.content
    return jsonify({"script": script})

@app.route('/api/search-videos', methods=['POST'])
def search_videos():
    data = request.json
    query = data.get('query', '')
    
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
    r = requests.get(url, headers=PEXELS_HEADERS)
    
    return jsonify(r.json())

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
