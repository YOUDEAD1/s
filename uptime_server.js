const express = require('express');
const app = express();
const port = 3000;

// Simple route for Uptime Robot to ping
app.get('/', (req, res) => {
  res.send('Bot is alive!');
});

// Status route with more information
app.get('/status', (req, res) => {
  res.json({
    status: 'running',
    version: 'Telegram Bot v20.3',
    timestamp: new Date().toISOString()
  });
});

// Start the server
app.listen(port, '0.0.0.0', () => {
  console.log(`Uptime server running at http://localhost:${port}`);
  console.log('Add this URL to Uptime Robot to keep your bot running');
});
