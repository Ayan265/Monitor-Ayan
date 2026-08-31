const { Client, LocalAuth } = require('whatsapp-web.js');
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    }
});

client.on('qr', () => console.log('QR Code received'));
client.on('ready', () => { console.log('Ready!'); process.exit(0); });
client.on('loading_screen', (percent, message) => console.log('LOADING', percent, message));
client.on('auth_failure', msg => console.error('AUTH FAILURE', msg));

setTimeout(async () => {
    if (client.pupPage) {
        await client.pupPage.screenshot({path: '/tmp/wa_debug.png'});
        console.log('Saved screenshot to /tmp/wa_debug.png');
    }
    process.exit(1);
}, 20000);

client.initialize().catch(console.error);
