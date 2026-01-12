const http = require('http');

const hostIp = '172.25.192.1'; // Detected WSL host IP
const targets = ['127.0.0.1', hostIp];

function checkTarget(ip) {
    return new Promise((resolve) => {
        const options = {
            hostname: ip,
            port: 9222,
            path: '/json/version',
            method: 'GET',
            timeout: 2000
        };

        console.log(`\nChecking CDP on http://${options.hostname}:${options.port}${options.path}...`);

        const req = http.request(options, (res) => {
            console.log(`SUCCESS [${ip}]: STATUS ${res.statusCode}`);
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                console.log(`BODY: ${data}`);
                resolve(true);
            });
        });

        req.on('error', (e) => {
            console.error(`FAILED [${ip}]: ${e.message}`);
            resolve(false);
        });

        req.on('timeout', () => {
            console.error(`TIMEOUT [${ip}]: Connection timed out`);
            req.destroy();
            resolve(false);
        });

        req.end();
    });
}

(async () => {
    for (const ip of targets) {
        await checkTarget(ip);
    }

    console.log('\n--- Diagnostic Tips ---');
    console.log('If both failed:');
    console.log('1. Ensure Chrome is running on Windows with: --remote-debugging-port=9222');
    console.log('2. Check Windows Firewall: It might be blocking port 9222 from WSL (Public vs Private profile).');
    console.log('3. In Chrome, check if it listens only on 127.0.0.1. Try adding: --remote-debugging-address=0.0.0.0');
})();
