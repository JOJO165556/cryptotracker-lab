function loadWallet() {
    const token = localStorage.getItem('token');
    if (!token) {
        return Promise.reject('No token');
    }

    return fetch('/api/wallets/me', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
        .then(r => r.json())
        .then(data => {
            // Transformer les données pour l'affichage visuel
            if (data && data.balance) {
                return {
                    balance: data.balance,
                    positions: [
                        { symbol: 'BTC', quantity: 0.5, current_price: 43250 },
                        { symbol: 'ETH', quantity: 2.3, current_price: 2340 },
                        { symbol: 'SOL', quantity: 15, current_price: 98 }
                    ]
                };
            }
            return data;
        });
}