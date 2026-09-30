function loadWallet() {
    const token = localStorage.getItem('token');
    if (!token) {
        return Promise.reject('No token');
    }

    return fetch('/api/wallets/', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
        .then(r => r.json());
}