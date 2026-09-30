function loadAnalytics() {
    const token = localStorage.getItem('token');
    if (!token) {
        return Promise.reject('No token');
    }

    const request = {
        jsonrpc: '2.0',
        method: 'get_portfolio_value',
        params: {},
        id: 1
    };

    return fetch('/api/analytics/rpc', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(request)
    })
        .then(r => r.json());
}