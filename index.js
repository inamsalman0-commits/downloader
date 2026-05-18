const express = require('express');
const cors = require('cors');
const YTDlpWrap = require('yt-dlp-wrap').default;
const path = require('path');
const app = express();

app.use(express.json());

// CORS: Apne Blogger ka URL yahan lagayein
app.use(cors({
    origin: ["https://YOUR-BLOG.blogspot.com", "http://127.0.0.1:5500"]
}));

// Automatic binary downloader for yt-dlp inside Vercel node container
const ytDlpBinaryPath = path.join('/tmp', 'yt-dlp');
let ytDlpWrap;

async function initYtdlp() {
    if (!ytDlpWrap) {
        try {
            await YTDlpWrap.downloadFromGithub(ytDlpBinaryPath);
            ytDlpWrap = new YTDlpWrap(ytDlpBinaryPath);
        } catch (e) {
            console.error("Binary download failed, using fallback");
        }
    }
}

app.get('/', (req, res) => {
    res.json({ status: "Node High-Speed Server Live" });
});

app.post('/fetch', async (req, res) => {
    const videoUrl = req.body.url;
    if (!videoUrl) return res.json({ error: "URL khali hai!" });

    await initYtdlp();

    try {
        // High-speed Embedded Android Arguments via Node Stream
        let stdout = await ytDlpWrap.execPromise([
            videoUrl,
            '-j',
            '--no-playlist',
            '--geo-bypass',
            '--extractor-args', 'youtube:client=android_embedded,tv_embedded;skip=dash,hls'
        ]);

        let info = JSON.parse(stdout);
        let ui_formats = [];
        let seen_res = new Set();

        info.formats.forEach(fmt => {
            if (fmt.ext === 'mp4' && fmt.height && fmt.url) {
                if (seen_res.has(fmt.height)) return;
                seen_res.add(fmt.height);

                let sizeBytes = fmt.filesize || fmt.filesize_approx || 0;
                let sizeStr = sizeBytes ? `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB` : "Direct Link";

                ui_formats.push({
                    quality: `${fmt.height}p`,
                    ext: 'mp4',
                    size: sizeStr,
                    type: 'video',
                    url: fmt.url
                });
            }
        });

        // Audio Track
        let audioFmt = info.formats.find(fmt => !fmt.vcodec || fmt.vcodec === 'none' && fmt.url);
        if (audioFmt) {
            ui_formats.push({
                quality: 'Audio Track (High MP3/M4A)',
                ext: 'mp3',
                size: 'Direct Stream',
                type: 'audio',
                url: audioFmt.url
            });
        }

        // Sort descending
        let videoItems = ui_formats.filter(f => f.type === 'video').sort((a, b) => parseInt(b.quality) - parseInt(a.quality));
        let audioItems = ui_formats.filter(f => f.type === 'audio');

        res.json({
            title: info.title || "YouTube Video",
            formats: [...videoItems, ...audioItems]
        });

    } catch (error) {
        res.json({ error: "YouTube security bypass failed. Please try again in a moment." });
    }
});

module.exports = app;