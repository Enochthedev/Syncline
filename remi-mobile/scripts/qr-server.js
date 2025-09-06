#!/usr/bin/env node

/**
 * Simple QR Code server for R.E.M.I Mobile
 * Generates QR codes for easy phone testing
 */

const http = require('http');
const { exec } = require('child_process');
const os = require('os');

// Get local IP address
function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const devName in interfaces) {
        const iface = interfaces[devName];
        for (let i = 0; i < iface.length; i++) {
            const alias = iface[i];
            if (alias.family === 'IPv4' && alias.address !== '127.0.0.1' && !alias.internal) {
                return alias.address;
            }
        }
    }
    return 'localhost';
}

// Generate ASCII QR code using qrencode (if available)
function generateQR(url) {
    return new Promise((resolve) => {
        exec(`which qrencode`, (error) => {
            if (error) {
                resolve(`
┌─────────────────────────────────────┐
│  QR Code Tools Not Installed       │
│                                     │
│  To generate QR codes, install:     │
│  brew install qrencode               │
│                                     │
│  Or manually enter this URL:        │
│  ${url}                             │
└─────────────────────────────────────┘
        `);
            } else {
                exec(`qrencode -t UTF8 "${url}"`, (error, stdout) => {
                    if (error) {
                        resolve(`URL: ${url}\n(QR generation failed)`);
                    } else {
                        resolve(stdout);
                    }
                });
            }
        });
    });
}

// Create a simple web server to display QR code
function createQRServer(metroUrl) {
    const server = http.createServer(async (req, res) => {
        if (req.url === '/') {
            const qrCode = await generateQR(metroUrl);

            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(`
<!DOCTYPE html>
<html>
<head>
    <title>R.E.M.I Mobile - QR Code</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Courier New', monospace; 
            background: #1a1a1a; 
            color: #00ff00; 
            padding: 20px; 
            text-align: center;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .qr-code { 
            background: white; 
            color: black; 
            padding: 20px; 
            border-radius: 10px; 
            margin: 20px 0; 
            font-size: 12px;
            white-space: pre;
            overflow-x: auto;
        }
        .url { 
            background: #333; 
            padding: 10px; 
            border-radius: 5px; 
            word-break: break-all;
            margin: 10px 0;
        }
        .instructions {
            text-align: left;
            background: #2a2a2a;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        h1 { color: #00ffff; }
        .step { margin: 10px 0; padding: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 R.E.M.I Mobile QR Code</h1>
        
        <div class="qr-code">${qrCode}</div>
        
        <div class="url">
            <strong>Metro URL:</strong><br>
            ${metroUrl}
        </div>
        
        <div class="instructions">
            <h3>📋 Setup Instructions:</h3>
            <div class="step">1. Install "Expo Go" app on your phone</div>
            <div class="step">2. Make sure phone and computer are on same WiFi</div>
            <div class="step">3. Scan QR code above OR manually enter the Metro URL</div>
            <div class="step">4. App should load on your phone!</div>
        </div>
        
        <div class="instructions">
            <h3>🔗 App Store Links:</h3>
            <div class="step">📱 iOS: <a href="https://apps.apple.com/app/expo-go/id982107779" target="_blank">Expo Go on App Store</a></div>
            <div class="step">📱 Android: <a href="https://play.google.com/store/apps/details?id=host.exp.exponent" target="_blank">Expo Go on Play Store</a></div>
        </div>
        
        <div style="margin-top: 30px; font-size: 12px; opacity: 0.7;">
            Refresh this page if the QR code doesn't load properly
        </div>
    </div>
</body>
</html>
      `);
        } else {
            res.writeHead(404);
            res.end('Not Found');
        }
    });

    return server;
}

// Main execution
if (require.main === module) {
    const localIP = getLocalIP();
    const metroPort = process.argv[2] || '8081';
    const qrPort = process.argv[3] || '3000';
    const metroUrl = `http://${localIP}:${metroPort}`;

    console.log(`\n🚀 R.E.M.I Mobile QR Code Server`);
    console.log(`📱 Metro bundler: ${metroUrl}`);
    console.log(`🔗 QR code page: http://localhost:${qrPort}`);
    console.log(`🌐 QR code page (network): http://${localIP}:${qrPort}`);

    const server = createQRServer(metroUrl);

    server.listen(qrPort, () => {
        console.log(`\n✅ QR Code server running on port ${qrPort}`);
        console.log(`\nOpen in browser: http://localhost:${qrPort}`);
        console.log(`Or on your phone: http://${localIP}:${qrPort}`);
        console.log(`\nPress Ctrl+C to stop\n`);
    });
}

module.exports = { createQRServer, getLocalIP };

