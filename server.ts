import express from 'express';
import path from 'path';
import { Groq } from 'groq-sdk';
import dotenv from 'dotenv';
import cors from 'cors';
import crypto from 'crypto';

dotenv.config();

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// Initialize Groq client using standard Node.js SDK
const client = new Groq({
    apiKey: process.env.GROQ_API_KEY || ''
});
const MODEL = "llama-3.3-70b-versatile";

// Simple in-memory cache
const cache = new Map<string, { data: any, timestamp: number }>();
const CACHE_DURATION = 60 * 60 * 1000; // 1 hour

function getCacheKey(payload: any) {
    return crypto.createHash('md5').update(JSON.stringify(payload)).digest('hex');
}

// Serve the same HTML requested by the user from the templates directory
app.use(express.static(path.join(process.cwd(), 'templates')));

app.get('/', (req, res) => {
    res.sendFile(path.join(process.cwd(), 'templates', 'index.html'));
});

app.get('/api/health', (req, res) => {
    res.json({ status: "healthy" });
});

app.post('/api/generate-script', async (req, res) => {
    try {
        const { topic, tone, duration, language = 'Arabic' } = req.body;

        if (!topic) {
            return res.status(400).json({ error: "يرجى إدخال موضوع الفيديو" });
        }
        
        const cacheKey = getCacheKey({ type: 'script', topic, tone, duration, language });
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
            return res.json(cached.data);
        }

        const prompt = `Generate a professional video script in ${language}:
        Topic: ${topic}
        Tone: ${tone}
        Duration: ${duration}
        
        Format the output EXACTLY as a JSON object with the following structure. Do not include any other text or markdown:
        {
            "script": "Full script text here",
            "scenes": [
                {
                    "time": "0-5s",
                    "visual": "Visual description",
                    "text": "Text on screen or spoken words"
                }
            ],
            "hashtags": ["#tag1", "#tag2"],
            "music_suggestion": "music genre or vibe"
        }`;
        
        const response = await client.chat.completions.create({
            model: MODEL,
            messages: [{ role: "user", content: prompt }],
            temperature: 0.8,
            max_tokens: 2000,
            response_format: { type: "json_object" }
        });
        
        const content = response.choices[0]?.message?.content || '{}';
        const parsedData = JSON.parse(content);
        
        cache.set(cacheKey, { data: parsedData, timestamp: Date.now() });
        res.json(parsedData);
    } catch (error: any) {
        res.status(500).json({ error: "حدث خطأ أثناء توليد السكريبت", details: error.message });
    }
});

app.post('/api/generate-hooks', async (req, res) => {
    try {
        const { topic, niche = 'عام' } = req.body;

        if (!topic) {
            return res.status(400).json({ error: "يرجى إدخال موضوع الفيديو" });
        }
        
        const cacheKey = getCacheKey({ type: 'hooks', topic, niche });
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
            return res.json(cached.data);
        }

        const prompt = `Generate 5 viral hooks in Arabic for a video about:
        Topic: ${topic}
        Niche: ${niche}
        
        Format the output EXACTLY as a JSON object:
        {
            "hooks": ["hook 1", "hook 2", "hook 3", "hook 4", "hook 5"]
        }`;
        
        const response = await client.chat.completions.create({
            model: MODEL,
            messages: [{ role: "user", content: prompt }],
            temperature: 0.8,
            max_tokens: 1000,
            response_format: { type: "json_object" }
        });
        
        const content = response.choices[0]?.message?.content || '{}';
        const parsedData = JSON.parse(content);
        
        cache.set(cacheKey, { data: parsedData, timestamp: Date.now() });
        res.json(parsedData);
    } catch (error: any) {
        res.status(500).json({ error: "حدث خطأ أثناء توليد الخطافات", details: error.message });
    }
});

app.post('/api/generate-cta', async (req, res) => {
    try {
        const { topic, goal = 'تفاعل' } = req.body;

        if (!topic) {
            return res.status(400).json({ error: "يرجى إدخال موضوع الفيديو" });
        }
        
        const cacheKey = getCacheKey({ type: 'cta', topic, goal });
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
            return res.json(cached.data);
        }

        const prompt = `Generate a Call to Action (CTA) in Arabic for a video about:
        Topic: ${topic}
        Goal: ${goal}
        
        Format the output EXACTLY as a JSON object:
        {
            "cta_text": "Main CTA text",
            "cta_variations": ["Variation 1", "Variation 2", "Variation 3"]
        }`;
        
        const response = await client.chat.completions.create({
            model: MODEL,
            messages: [{ role: "user", content: prompt }],
            temperature: 0.8,
            max_tokens: 1000,
            response_format: { type: "json_object" }
        });
        
        const content = response.choices[0]?.message?.content || '{}';
        const parsedData = JSON.parse(content);
        
        cache.set(cacheKey, { data: parsedData, timestamp: Date.now() });
        res.json(parsedData);
    } catch (error: any) {
        res.status(500).json({ error: "حدث خطأ أثناء توليد CTA", details: error.message });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Node.js preview server running on port ${PORT}`);
});
