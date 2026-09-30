let eventSource = null;

function connectSSE(token) {
    if (eventSource) {
        disconnectSSE();
    }

    const sseUrl = `/api/notifications/stream?token=${token}`;
    eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
        console.log('SSE connected');
    };

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (typeof onSSENotification === 'function') {
            onSSENotification(data);
        }
    };

    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
    };
}

function disconnectSSE() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}