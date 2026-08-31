const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const fs = require('fs');
const path = require('path');
const Groq = require('groq-sdk');

let GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE";

try {
    const secretsPath = path.join(__dirname, 'private', 'secrets.json');
    if (fs.existsSync(secretsPath)) {
        const secrets = JSON.parse(fs.readFileSync(secretsPath, 'utf8'));
        if (secrets.GROQ_API_KEY) GROQ_API_KEY = secrets.GROQ_API_KEY;
        // targetIdCache logic is handled further down
    }
} catch (e) {}

global.chatHistory = {};


const app = express();
app.use(express.json());

let client = null;
let isReady = false;
let isInitializing = false;
let initStartTime = null;      // When initialization started
let initAttempts = 0;           // How many times we've retried
let lastReadyTime = null;       // Last time the client was ready
let needsQRScan = false;        // Whether the session is expired
const MAX_INIT_ATTEMPTS = 3;
const INIT_TIMEOUT_MS = 90000;  // 90 seconds max for initialization

// =============================================
// SELF-HEALING: Clean stale Chrome lock files
// =============================================
function cleanStaleLocks() {
    const sessionDir = path.join(__dirname, '.wwebjs_auth', 'session');
    const lockFiles = ['SingletonLock', 'SingletonCookie', 'SingletonSocket'];
    
    for (const lockFile of lockFiles) {
        const lockPath = path.join(sessionDir, lockFile);
        try {
            if (fs.existsSync(lockPath)) {
                fs.unlinkSync(lockPath);
                console.log(`[HEAL] Removed stale lock: ${lockFile}`);
            }
        } catch (e) {
            // Ignore errors — file might be already gone
        }
    }
}

// =============================================
// SELF-HEALING: Kill orphaned chromium processes
// =============================================
function killOrphanedChromium() {
    try {
        const { execSync } = require('child_process');
        execSync('pkill -9 -f "chromium.*wwebjs" 2>/dev/null || true', { timeout: 5000 });
        execSync('pkill -9 -f "\\\\.wwebjs_auth/session" 2>/dev/null || true', { timeout: 5000 });
        console.log('[HEAL] Killed orphaned chromium processes');
    } catch (e) {
        // Ignore — no orphans to kill
    }
}

// =============================================
// SELF-HEALING: Destroy current client cleanly
// =============================================
async function destroyClient() {
    if (client) {
        try {
            await client.destroy();
            console.log('[HEAL] Client destroyed cleanly');
        } catch (e) {
            console.log('[HEAL] Client destroy failed, forcing cleanup');
        }
        client = null;
    }
    isReady = false;
    isInitializing = false;
    initStartTime = null;
}

let isStartingup = false; // Prevents race condition during the 2s wait
// =============================================
// SELF-HEALING: Full initialization with timeout
// =============================================
async function initializeClient() {
    if (isInitializing || isReady || isStartingup) return;
    isStartingup = true;
    
    initAttempts++;
    if (initAttempts > MAX_INIT_ATTEMPTS) {
        console.error(`[HEAL] Max init attempts (${MAX_INIT_ATTEMPTS}) reached. Giving up until next external trigger.`);
        initAttempts = 0;
        isInitializing = false;
        isStartingup = false;
        return;
    }
    
    console.log(`[HEAL] Init attempt ${initAttempts}/${MAX_INIT_ATTEMPTS}...`);
    
    // Step 1: Clean up before trying
    await destroyClient();
    killOrphanedChromium();
    cleanStaleLocks();
    
    // Step 2: Wait a beat for cleanup
    await new Promise(r => setTimeout(r, 2000));
    
    isInitializing = true;
    isStartingup = false;
    initStartTime = Date.now();
    needsQRScan = false;

    client = new Client({
        authStrategy: new LocalAuth(),
        puppeteer: {
            headless: true,
            protocolTimeout: 120000,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        }
    });

    client.on('qr', (qr) => {
        needsQRScan = true;
        console.log('\n--- SESSION EXPIRED: PLEASE SCAN QR CODE ---\n');
        qrcode.generate(qr, { small: true });
        
        // Save QR to file
        try {
            const QRCode = require('qrcode');
            QRCode.toFile('/tmp/whatsapp_qr.png', qr, {
                color: { dark: '#000000', light: '#ffffff' }
            });
            console.log('[+] Saved QR to image file for user to scan.');
        } catch(e) {
            console.error('Failed to save QR to file:', e);
        }
        
        // Send desktop notification so user knows
        try {
            const { execSync } = require('child_process');
            execSync('DISPLAY=:0 notify-send -u critical "⚠️ WhatsApp Session Expired" "Your WhatsApp link has expired. Please re-scan the QR code. Run: node wa_backend.js in terminal to see it."', { timeout: 5000 });
        } catch(e) {}
    });

    client.on('ready', () => {
        console.log('✅ WhatsApp Backend is logged in and ready!');
        isReady = true;
        isInitializing = false;
        initStartTime = null;
        lastReadyTime = Date.now();
        initAttempts = 0; // Reset on success
        needsQRScan = false;
    });

    const TESTING_GROUP_ID = "120363412144072406@g.us";

    client.on('message', async msg => {
        console.log(`[MSG_RCV] From: ${msg.from} | Author: ${msg.author} | Body: ${msg.body}`);
        
        if (msg.isStatus || msg.from === "status@broadcast") return;
        
        // ONLY forward messages from the testing group
        if (msg.from === TESTING_GROUP_ID) {
            try {
                const fetch = require('node-fetch');
                await fetch('http://localhost:4000/incoming', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ senderId: msg.from, messageText: msg.body })
                });
            } catch (err) {
                console.error("[-] Failed to forward message to Jarvis Webhook:", err);
            }
        }
    });

    client.on('message_create', async msg => {
        console.log(`[MSG_CREATE] From: ${msg.from} | To: ${msg.to} | Body: ${msg.body}`);

        // ONLY forward commands sent to the testing group
        if (msg.fromMe && msg.to === TESTING_GROUP_ID && !msg.body.startsWith("🤖") && !msg.body.startsWith("System Message:") && !msg.body.includes("Time Spend:")) {
            try {
                const fetch = require('node-fetch');
                await fetch('http://localhost:4000/incoming', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ senderId: msg.to, messageText: msg.body })
                });
            } catch (err) {
                console.error("[-] Failed to forward message to Jarvis Webhook:", err);
            }
        }
    });

    client.on('disconnected', () => {
        console.log('[-] WhatsApp disconnected.');
        client = null;
        isReady = false;
        isInitializing = false;
        initStartTime = null;
    });
    
    client.on('auth_failure', () => {
        console.error('[-] WhatsApp authentication failed! Session may be corrupt.');
        needsQRScan = true;
        isInitializing = false;
        initStartTime = null;
        
        try {
            const { execSync } = require('child_process');
            execSync('DISPLAY=:0 notify-send -u critical "🚨 WhatsApp Auth Failed" "WhatsApp authentication failed. You need to re-link your device."', { timeout: 5000 });
        } catch(e) {}
    });

    client.initialize()
        .then(() => console.log("[+] client.initialize() RESOLVED!"))
        .catch(err => {
            console.error("[-] Fatal error during WhatsApp initialization:", err);
            isInitializing = false;
            initStartTime = null;
            // Don't exit — let the watchdog retry
        });
}

// =============================================
// SELF-HEALING: Watchdog timer (runs every 30s)
// =============================================
setInterval(async () => {
    // If initializing and it's been too long, force restart
    if (isInitializing && initStartTime && !needsQRScan) {
        const elapsed = Date.now() - initStartTime;
        if (elapsed > INIT_TIMEOUT_MS) {
            console.error(`[WATCHDOG] Init stuck for ${Math.round(elapsed/1000)}s. Force restarting...`);
            await destroyClient();
            // Small delay before retry
            setTimeout(() => initializeClient(), 3000);
        }
    }
}, 30000);

// =============================================
// API ENDPOINTS
// =============================================

app.post('/start', async (req, res) => {
    console.log("JIT hit:", {hasClient: !!client, isInitializing, isReady, needsQRScan});
    
    if (isReady) {
        return res.json({ status: "already_ready" });
    }
    
    if (isInitializing || isStartingup) {
        // Check if it's been stuck
        if (initStartTime && (Date.now() - initStartTime > INIT_TIMEOUT_MS) && !needsQRScan) {
            console.log("[HEAL] /start called but init is stuck. Force restarting...");
            await destroyClient();
            killOrphanedChromium();
            cleanStaleLocks();
            await new Promise(r => setTimeout(r, 2000));
            initAttempts = 0; // Reset since this is an external trigger
            initializeClient();
            return res.json({ status: "force_restarting" });
        }
        return res.json({ status: "already_initializing" });
    }
    
    // Fresh start
    initAttempts = 0;
    initializeClient();
    res.json({ status: "initializing" });
});

app.post('/stop', async (req, res) => {
    if (!isReady && isInitializing && needsQRScan) {
        console.log("[*] JIT: /stop requested, but client is waiting for QR code. Ignoring stop request so user can scan it.");
        return res.json({ status: "ignored_for_qr_scan" });
    }
    console.log("[*] JIT: /stop requested. Cleaning up...");
    await destroyClient();
    res.json({ status: "stopped" });
});

app.get('/status', (req, res) => {
    res.json({
        ready: isReady,
        initializing: isInitializing,
        hasClient: client !== null,
        needsQRScan: needsQRScan,
        initElapsedMs: isInitializing && initStartTime ? Date.now() - initStartTime : null,
        lastReadyTime: lastReadyTime,
        initAttempts: initAttempts
    });
});

app.post('/force_restart', async (req, res) => {
    console.log("[HEAL] Force restart requested via API");
    initAttempts = 0;
    await destroyClient();
    killOrphanedChromium();
    cleanStaleLocks();
    await new Promise(r => setTimeout(r, 3000));
    initializeClient();
    res.json({ status: "force_restarting" });
});

app.get('/health', (req, res) => {
    res.json({
        alive: true,
        ready: isReady,
        needsQRScan: needsQRScan,
        uptimeSeconds: Math.round(process.uptime()),
        lastReadyTime: lastReadyTime
    });
});

let targetIdCache = {
    "YOUR_ALERT_GROUP": "1234567890@g.us",
    "YOUR_SUMMARY_GROUP": "0987654321@g.us"
};

try {
    const secretsPath = path.join(__dirname, 'private', 'secrets.json');
    if (fs.existsSync(secretsPath)) {
        const secrets = JSON.parse(fs.readFileSync(secretsPath, 'utf8'));
        if (secrets.WA_TARGET_ID_CACHE) {
            targetIdCache = { ...targetIdCache, ...secrets.WA_TARGET_ID_CACHE };
        }
    }
} catch (e) {
    console.log("[-] Could not load private/secrets.json");
}

async function resolveTargetId(target) {
    if (target.endsWith('@g.us') || target.endsWith('@c.us')) {
        return target;
    }

    // Check if it's a phone number (mostly digits and +)
    if (/^\+?[\d\s-]+$/.test(target)) {
        return target.replace(/[\+\s-]/g, '') + '@c.us';
    }

    if (targetIdCache[target]) {
        return targetIdCache[target];
    }

    // If it's a string name, search groups/chats by name
    const chats = await client.getChats();
    const foundChat = chats.find(c => c.name === target);

    if (foundChat) {
        targetIdCache[target] = foundChat.id._serialized;
        return targetIdCache[target];
    }

    throw new Error(`Could not find a chat or group named "${target}"`);
}

app.post('/send_alert', async (req, res) => {
    if (!isReady || !client) {
        return res.status(503).json({ error: "WhatsApp client is not ready yet.", needsQRScan });
    }

    const { number, message, image_path, audio_path, delete_locally } = req.body;

    if (!number || !message) {
        return res.status(400).json({ error: "Please provide 'number' and 'message' in the JSON body." });
    }

    try {
        const formattedNumber = await resolveTargetId(number);

        let sentMsg;
        let media = null;
        if (audio_path) {
            try {
                media = MessageMedia.fromFilePath(audio_path);
                sentMsg = await client.sendMessage(formattedNumber, media, { sendAudioAsVoice: true });
                console.log(`[+] Sent ALERT voice message to ${number} (Formatted: ${formattedNumber})`);
                if (message) {
                    await client.sendMessage(formattedNumber, message);
                }
            } catch (mediaErr) {
                console.error(`[-] Could not load audio from ${audio_path}:`, mediaErr.message);
                console.log(`[*] Falling back to sending alert text only.`);
                sentMsg = await client.sendMessage(formattedNumber, message);
            }
        } else if (image_path) {
            try {
                media = MessageMedia.fromFilePath(image_path);
                sentMsg = await client.sendMessage(formattedNumber, media, { caption: message });
                console.log(`[+] Sent ALERT image + message to ${number} (Formatted: ${formattedNumber})`);
            } catch (mediaErr) {
                console.error(`[-] Could not load image from ${image_path}:`, mediaErr.message);
                console.log(`[*] Falling back to sending alert without image.`);
                sentMsg = await client.sendMessage(formattedNumber, message);
            }
        } else {
            sentMsg = await client.sendMessage(formattedNumber, message);
            console.log(`[+] Sent ALERT message to ${number} (Formatted: ${formattedNumber})`);
        }

        if (delete_locally) {
            try {
                await sentMsg.delete(false);
                console.log(`[+] Deleted ALERT message locally so user cannot unsend it!`);
            } catch (delErr) { }
        } else {
            console.log(`[+] Kept ALERT message locally as requested.`);
        }

        res.json({ success: true, status: 'Alert Sent!' });
    } catch (err) {
        console.error("[-] Error sending alert:", err);
        console.log("ACTUAL ERROR STRING:", err.toString());
        res.status(500).json({ error: err.toString() });
        const errStr = err.stack ? err.stack : err.toString();
        console.log("ERRSTR IS:", errStr);
        if (errStr.includes("detached Frame") || errStr.includes("Protocol error") || errStr.includes("evaluate") || errStr.includes("r: r") || errStr.includes("r")) {
            console.error("[-] Critical Puppeteer error. Auto-recovering...");
            destroyClient().then(() => {
                if (errStr.includes("r: r")) {
                    console.log("[HEAL] r: r error detected. NOT wiping session because getChats is broken.");
                }
                setTimeout(() => { initAttempts = 0; initializeClient(); }, 3000);
            });
        }
    }
});

app.post('/send_summary', async (req, res) => {
    if (!isReady || !client) {
        return res.status(503).json({ error: "WhatsApp client is not ready yet.", needsQRScan });
    }

    const { number, message, image_path } = req.body;

    if (!number || !message) {
        return res.status(400).json({ error: "Please provide 'number' and 'message' in the JSON body." });
    }

    try {
        const formattedNumber = await resolveTargetId(number);

        let sentMsg;
        let media = null;
        if (image_path) {
            try {
                media = MessageMedia.fromFilePath(image_path);
            } catch (mediaErr) {
                console.error(`[-] Could not load image from ${image_path}:`, mediaErr.message);
                console.log(`[*] Falling back to sending summary without image.`);
            }
        }

        if (media) {
            sentMsg = await client.sendMessage(formattedNumber, media, { caption: message });
            console.log(`[+] Sent SUMMARY image + message to ${number} (Formatted: ${formattedNumber})`);
        } else {
            sentMsg = await client.sendMessage(formattedNumber, message);
            console.log(`[+] Sent SUMMARY message to ${number} (Formatted: ${formattedNumber})`);
        }
        console.log(`[+] Kept SUMMARY message locally as requested.`);

        res.json({ success: true, status: 'Summary Sent!' });
    } catch (err) {
        console.error("[-] Error sending summary:", err);
        const errStr = err.stack ? err.stack : err.toString();
        res.status(500).json({ error: errStr });
        console.log("ERRSTR IS:", errStr);
        if (errStr.includes("detached Frame") || errStr.includes("Protocol error") || errStr.includes("evaluate") || errStr.includes("r: r") || errStr.includes("r")) {
            console.error("[-] Critical Puppeteer error. Auto-recovering...");
            destroyClient().then(() => {
                if (errStr.includes("r: r")) {
                    console.log("[HEAL] r: r error detected. NOT wiping session because getChats is broken.");
                }
                setTimeout(() => { initAttempts = 0; initializeClient(); }, 3000);
            });
        }
    }
});

app.get('/get_groups', async (req, res) => {
    if (!isReady || !client) {
        return res.status(503).json({ error: "WhatsApp client is not ready. Call /start first." });
    }
    try {
        const chats = await client.getChats();
        const groups = chats.filter(chat => chat.isGroup).map(group => ({
            name: group.name,
            id: group.id._serialized
        }));
        res.json({ groups });
    } catch (err) {
        res.status(500).json({ error: err.toString() });
    }
});

app.post('/start', (req, res) => {
    initializeClient();
    res.json({ success: true });
});

app.get('/debug', async (req, res) => {
    try {
        let chat = await client.getChatById(req.query.id);
        res.json({ name: chat.name });
    } catch(e) {
        res.status(500).json({ error: e.toString() });
    }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`🚀 JIT WhatsApp Backend Daemon running on port ${PORT}`);
});

setInterval(() => {}, 1000 * 60 * 60);
