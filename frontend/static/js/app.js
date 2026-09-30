let authToken = null;
let currentUser = null;

function init() {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
        authToken = savedToken;
        currentUser = localStorage.getItem('username') || 'Utilisateur';
        updateAuthUI();
        loadDashboardData();
    }

    setupNavigation();
    setupMobileMenu();
}

function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach((item) => {
        item.onclick = function (e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            if (section) {
                showSection(section);
            }
        };
    });
}

function setupMobileMenu() {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('mobile-overlay');

    if (menuToggle && sidebar && overlay) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }
}

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });

    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    const sectionElement = document.getElementById('section-' + sectionName);
    const navElement = document.querySelector(`[data-section="${sectionName}"]`);

    if (sectionElement) {
        sectionElement.classList.add('active');
    }
    if (navElement) {
        navElement.classList.add('active');
    }

    const titles = {
        dashboard: 'Dashboard',
        trading: 'Trading',
        market: 'Marché',
        wallet: 'Portefeuille',
        alerts: 'Alertes',
        legacy: 'Legacy Bank'
    };
    const titleElement = document.getElementById('page-title');
    if (titleElement && titles[sectionName]) {
        titleElement.textContent = titles[sectionName];
    }

    if (sectionName === 'trading') {
        loadOrders();
    } else if (sectionName === 'market') {
        loadMarket();
    } else if (sectionName === 'wallet') {
        loadWallet();
    } else if (sectionName === 'alerts') {
        loadAlerts();
    }

    // Fermer le menu mobile après sélection
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('mobile-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
}

function updateAuthUI() {
    if (authToken) {
        const userName = currentUser || 'Utilisateur';
        document.getElementById('user-name').textContent = userName;
        document.getElementById('user-avatar').textContent = userName.charAt(0).toUpperCase();
        document.querySelector('.user-action').textContent = 'Déconnexion';
        document.querySelector('.user-action').href = '#';
        document.querySelector('.user-action').addEventListener('click', logout);

        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        if (statusDot) {
            statusDot.classList.remove('offline');
            statusDot.classList.add('online');
        }
        if (statusText) {
            statusText.textContent = 'Connecté';
        }
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    authToken = null;
    currentUser = null;

    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('mobile-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');

    window.location.href = '/login/';
}

function loadDashboardData() {
    loadWallet();
    loadAnalytics();
    window.connectWebSocket(authToken);
    window.connectSSE(authToken);
}

function loadWallet() {
    if (!authToken) return;

    window.loadWallet()
        .then(data => {
            const walletData = document.getElementById('wallet-data');
            if (walletData) {
                walletData.textContent = JSON.stringify(data, null, 2);
            }

            if (data && data.balance) {
                const kpiPortfolio = document.getElementById('kpi-portfolio');
                if (kpiPortfolio) {
                    kpiPortfolio.textContent = '$' + data.balance;
                }
            }
        })
        .catch(err => {
            console.error('Erreur wallet:', err);
            const walletData = document.getElementById('wallet-data');
            if (walletData) {
                walletData.textContent = 'Erreur: ' + err.message;
            }
        });
}

function loadAnalytics() {
    if (!authToken) return;

    window.loadAnalytics()
        .then(data => {
            const alertsData = document.getElementById('alerts-data');
            if (alertsData) {
                alertsData.textContent = JSON.stringify(data, null, 2);
            }

            if (data && data.result) {
                const kpiVolume = document.getElementById('kpi-volume');
                const kpiOrders = document.getElementById('kpi-orders');
                const kpiAlerts = document.getElementById('kpi-alerts');

                if (kpiVolume) kpiVolume.textContent = '$' + (data.result.volume || '--');
                if (kpiOrders) kpiOrders.textContent = data.result.orders || '--';
                if (kpiAlerts) kpiAlerts.textContent = data.result.alerts || '--';
            }
        })
        .catch(err => {
            console.error('Erreur analytics:', err);
            const alertsData = document.getElementById('alerts-data');
            if (alertsData) {
                alertsData.textContent = 'Erreur: ' + err.message;
            }
        });
}

function loadOrders() {
    if (!authToken) return;

    fetch('/api/trading/orders/', {
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('orders-table');
            if (tbody) {
                if (data && data.length > 0) {
                    tbody.innerHTML = data.map(order => `
                    <tr>
                        <td>${order.id}</td>
                        <td>${order.asset_symbol || 'BTC'}</td>
                        <td>${order.order_type}</td>
                        <td>$${order.price}</td>
                        <td>${order.quantity}</td>
                        <td>${order.status}</td>
                    </tr>
                `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Aucun ordre</td></tr>';
                }
            }
        })
        .catch(err => {
            console.error('Erreur ordres:', err);
            const tbody = document.getElementById('orders-table');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Erreur de chargement</td></tr>';
            }
        });
}

function loadMarket() {
    if (!authToken) return;

    fetch('/api/market/assets/', {
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('market-table');
            if (tbody) {
                if (data && data.length > 0) {
                    tbody.innerHTML = data.map(asset => `
                    <tr>
                        <td>${asset.symbol}</td>
                        <td>${asset.name}</td>
                        <td>$${asset.current_price}</td>
                        <td class="positive">+2.5%</td>
                    </tr>
                `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Aucune donnée</td></tr>';
                }
            }
        })
        .catch(err => {
            console.error('Erreur marché:', err);
            const tbody = document.getElementById('market-table');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Erreur de chargement</td></tr>';
            }
        });
}

function loadAlerts() {
    if (!authToken) return;

    fetch('/api/notifications/alerts/', {
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
        .then(r => r.json())
        .then(data => {
            const alertsData = document.getElementById('alerts-data');
            if (alertsData) {
                alertsData.textContent = JSON.stringify(data, null, 2);
            }
        })
        .catch(err => {
            console.error('Erreur alertes:', err);
            const alertsData = document.getElementById('alerts-data');
            if (alertsData) {
                alertsData.textContent = 'Erreur: ' + err.message;
            }
        });
}

function createBankAccount() {
    window.createBankAccount()
        .then(data => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                soapData.textContent = data;
            }
        })
        .catch(err => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                soapData.textContent = 'Erreur: ' + err.message;
            }
        });
}

function getBankAccount() {
    window.getBankAccount()
        .then(data => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                soapData.textContent = data;
            }
        })
        .catch(err => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                soapData.textContent = 'Erreur: ' + err.message;
            }
        });
}

// Mise à jour prix WebSocket
function onWebSocketPriceUpdate(data) {
    if (data && data.price) {
        const btcPrice = document.getElementById('btc-price');
        const btcUpdate = document.getElementById('btc-update');
        if (btcPrice) {
            btcPrice.textContent = '$' + data.price;
        }
        if (btcUpdate) {
            btcUpdate.textContent = new Date().toLocaleTimeString();
        }
    }
}

// Notification SSE
function onSSENotification(data) {
    console.log('Notification:', data);
}

// Initialisation au chargement
document.addEventListener('DOMContentLoaded', init);