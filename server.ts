import express from 'express';
import path from 'path';
import { Groq } from 'groq-sdk';
import dotenv from 'dotenv';
import cors from 'cors';
import crypto from 'crypto';
import axios from 'axios';
import * as googleTTS from 'google-tts-api';

dotenv.config();

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

const client = new Groq({
    apiKey: process.env.GROQ_API_KEY || ''
});
const PEXELS_API_KEY = process.env.PEXELS_API_KEY || '';
const MODEL = "llama-3.3-70b-versatile";

const cache = new Map<string, { data: any, timestamp: number }>();
const CACHE_DURATION = 60 * 60 * 1000;

function getCacheKey(payload: any) {
    return crypto.createHash('md5').update(JSON.stringify(payload)).digest('hex');
}

app.use(express.static(path.join(process.cwd(), 'templates')));

app.get('/', (req, res) => {
    res.sendFile(path.join(process.cwd(), 'templates', 'index.html'));
});

app.get('/api/health', (req, res) => {
    res.json({ status: "healthy" });
});

app.post('/api/generate-video', async (req, res) => {
    try {
        const { topic, duration = 30, tone = 'احترافي', language = 'arabic', voice = 'arabic_male', music = 'حماسي' } = req.body;

        if (!topic) {
            return res.status(400).json({ error: "يرجى إدخال موضوع الفيديو" });
        }
        
        const cacheKey = getCacheKey({ type: 'video', topic, duration, tone, language, voice, music });
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
            return res.json(cached.data);
        }

        const prompt = `Create a video script in ${language}:
    Topic: ${topic}
    Duration: ${duration} seconds
    Tone: ${tone}
    
    Format EXACTLY like this (one scene per line, no extra text, no markdown block):
    SCENE|start_time|end_time|visual_description|text_on_screen|voiceover_text
    
    Example:
    SCENE|0|5|busy city street morning|ابدأ مشوارك الآن|في هذا الفيديو سنتعلم أسرار النجاح
    SCENE|5|10|person working on laptop|الخطوة الأولى|أولا حدد هدفك بوضوح تام`;

        const response = await client.chat.completions.create({
            model: MODEL,
            messages: [{ role: "user", content: prompt }],
            temperature: 0.7,
            max_tokens: 1500
        });
        
        const script = response.choices[0]?.message?.content || '';
        
        const scenes = [];
        const lines = script.trim().split('\n');
        for (const line of lines) {
            if (line.startsWith('SCENE|')) {
                const parts = line.split('|');
                if (parts.length >= 6) {
                    scenes.push({
                        start_time: parts[1],
                        end_time: parts[2],
                        visual: parts[3],
                        text_on_screen: parts[4],
                        voiceover: parts[5],
                        videos: []
                    });
                }
            }
        }

        // Fetch Pexels Videos
        if (PEXELS_API_KEY) {
            for (const scene of scenes) {
                try {
                    const pexelsRes = await axios.get('https://api.pexels.com/videos/search', {
                        headers: { 'Authorization': PEXELS_API_KEY },
                        params: { query: scene.visual, per_page: 3 }
                    });
                    const videos = pexelsRes.data.videos || [];
                    for (const v of videos) {
                        const hdFile = v.video_files.find((vf: any) => vf.quality === 'hd' && vf.width <= 1920);
                        if (hdFile) {
                            scene.videos.push({ url: hdFile.link, duration: v.duration, image: v.image });
                            break;
                        }
                    }
                } catch (e) {
                    console.error("Pexels fetch error", e);
                }
            }
        }
        
        const fullScript = scenes.map(s => s.voiceover).join(' ');
        
        // Mocking TTS with google-tts-api for Node preview sandbox
        let voice_url = null;
        if (fullScript.trim().length > 0) {
            try {
                // Split for length limits if needed, but for simple preview we just take first chunk
                const langCode = language.toLowerCase() === 'english' ? 'en' : 'ar';
                voice_url = googleTTS.getAudioUrl(fullScript.substring(0, 200), {
                    lang: langCode,
                    slow: false,
                    host: 'https://translate.google.com',
                });
            } catch (err) {
                console.error("TTS Error", err);
            }
        }
        
        const music_urls: any = {
            "upbeat": "https://cdn.pixabay.com/audio/2024/upbeat.mp3",
            "calm": "https://cdn.pixabay.com/audio/2024/calm.mp3", 
            "dramatic": "https://cdn.pixabay.com/audio/2024/dramatic.mp3",
            "happy": "https://cdn.pixabay.com/audio/2024/happy.mp3",
            "epic": "https://cdn.pixabay.com/audio/2024/epic.mp3",
        };
        const moodMap: any = {
            "حماسي": "upbeat", "حزين": "sad", "هادئ": "calm", "درامي": "dramatic",
            "مرح": "happy", "ملحمي": "epic", "تقني": "technology", "طبيعة": "nature"
        };
        const music_mood = moodMap[music] || "upbeat";
        const music_url = music_urls[music_mood] || music_urls["upbeat"];
        
        const parsedData = {
            scenes,
            script,
            voice_url,
            music_url,
            total_duration: duration
        };
        
        cache.set(cacheKey, { data: parsedData, timestamp: Date.now() });
        res.json(parsedData);
    } catch (error: any) {
        res.status(500).json({ error: "حدث خطأ أثناء توليد الفيديو", details: error.message });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Node.js preview server running on port ${PORT}`);
});
