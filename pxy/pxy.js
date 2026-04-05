// pxy.js
const express = require('express');
const path = require('path');
const WebSocket = require('ws');
const { exec } = require('child_process');

const app = express();

// Serve static files
app.use('/xterm', express.static(path.join(__dirname, 'node_modules/@xterm/xterm')));
app.use(express.static(path.join(__dirname)));

// Serve HTML
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// HTTP server
const server = app.listen(80, '0.0.0.0', () => {
    console.log('Server running on port 80');
});

// WebSocket server
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    console.log('Browser connected via WebSocket');

    // Attach to running npxy tmux session
    const tmuxAttach = exec('tmux capture-pane -t npxy -p -J -e', (err, stdout, stderr) => {
        if (err) {
            ws.send(`Error attaching to tmux session: ${err.message}`);
            return;
        }
        ws.send(stdout); // send initial content
    });

    // Stream live output using "tmux pipe-pane"
    const liveStream = exec(`tmux pipe-pane -t npxy 'cat >&2'`);
    
    liveStream.stderr.on('data', (data) => {
        ws.send(data.toString());
    });

    ws.on('close', () => {
        liveStream.kill(); // stop piping when client disconnects
    });
});
