function loadDashboard() {
    const token = localStorage.getItem('token');
    if (!token) {
        return Promise.reject('No token');
    }

    const query = `
        query {
            dashboard {
                portfolioValue
                activeOrders
                totalAlerts
            }
        }
    `;

    return fetch('/graphql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query })
    })
        .then(r => r.json());
}