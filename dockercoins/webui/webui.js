import express from 'express';
import morgan from 'morgan';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createClient } from 'redis';

var REDIS_URL = process.env.REDIS_URL || 'redis://redis';
var PORT = Number(process.env.PORT || 80);
var hostname = os.hostname();

// Connect in the background, so that the web server starts (and can
// report the problem in the browser) even when Redis is not up yet.
var client = createClient({
  url: REDIS_URL,
  socket: {
    family: 0
  }
})
    .on('error', function (err) {
        console.error('Redis error', err.message);
    });
client.connect().catch(function (err) {
    console.error('Redis connection failed', err.message);
});

var app = express();

app.use(morgan('common'));

app.get('/', function (req, res) {
    res.redirect('/index.html');
});

app.get('/json', async (req, res) => {
    res.set('Cache-Control', 'no-store');
    if (!client.isReady) {
        return res.status(503).json({ error: 'Redis is not connected', hostname: hostname });
    }
    try {
        var [coins, hashes] = await Promise.all([
            client.hLen('wallet'),
            client.get('hashes')
        ]);
        res.json({
            coins: coins,
            hashes: Number(hashes) || 0,
            now: Date.now() / 1000,
            hostname: hostname
        });
    } catch (err) {
        res.status(503).json({ error: err.message, hostname: hostname });
    }
});

app.use(express.static(fileURLToPath(new URL('files', import.meta.url))));

var server = app.listen(PORT, function () {
    console.log('WEBUI running on port ' + PORT);
});

// Node ignores SIGTERM when it runs as PID 1, so stop explicitly.
// Without this, "docker stop" and pod deletion wait for the KILL timeout.
function shutdown(signal) {
    console.log(signal + ' received, shutting down');
    server.close(function () {
        process.exit(0);
    });
    server.closeIdleConnections();
    setTimeout(function () { process.exit(0); }, 2000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
