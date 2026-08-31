const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

console.log("Starting WhatsApp Client to generate QR code...");

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    }
});

client.on('qr', (qr) => {
    console.log('\n--- PLEASE SCAN THIS QR CODE WITH YOUR WHATSAPP ---\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('\n✅ WhatsApp Backend is logged in and ready!');
    console.log('You can now press Ctrl+C to exit this script. The background service will take over.');
    setTimeout(() => process.exit(0), 3000);
});

client.initialize();
