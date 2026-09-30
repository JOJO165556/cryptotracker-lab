let ws = null;

function connectWebSocket(token) {
    if (ws) {
        disconnectWebSocket();
    }

    const wsUrl = `ws://${window.location.host}/ws/market/BTC?token=${token}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (typeof onWebSocketPriceUpdate === 'function') {
            onWebSocketPriceUpdate(data);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };
}

function disconnectWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }
}