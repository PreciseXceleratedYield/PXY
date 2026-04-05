const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80; // use setcap to allow port 80 without sudo

// Serve static files
app.use(express.static(__dirname));

// WebSocket: stream tmux npxy session output
wss.on('connection', (ws) => {
    const tmuxCmd = 'tmux capture-pane -t npxy -p -J -e && tmux pipe-pane -t npxy -o "cat > /tmp/tmux_pipe"';
    // Spawn a loop to read tmux pane periodically
    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -p -J -e', (err, stdout, stderr) => {
            if (err) {
                ws.send(`Error reading tmux session: ${stderr || err.message}`);
                clearInterval(interval);
                return;
            }
            ws.send(stdout);
        });
    }, 500); // update every 0.5s

    ws.on('close', () => clearInterval(interval));
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});
