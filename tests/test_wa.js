const { Client, LocalAuth } = require('whatsapp-web.js');
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    }
});
client.on('qr', (qr) => console.log('QR RECEIVED'));
client.on('ready', () => console.log('READY'));
client.initialize().catch(console.error);
