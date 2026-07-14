import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(express.static(path.join(__dirname, 'templates')));

// Mock API endpoint to prevent UI crash in preview environment
app.post('/api/generate-video', (req, res) => {
    res.status(500).json({
        success: false,
        message: "This is a Python application for Render.com. The AI Studio preview only serves the static HTML. Please deploy the app.py to Render or run it locally with Python to use the API."
    });
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
    console.log(`Preview server running on port ${port}`);
});
