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
    loadDashboardGraphQL();
    loadAnalytics();
    window.connectWebSocket(authToken);
    window.connectSSE(authToken);
}

function loadDashboardGraphQL() {
    if (!authToken) return;

    window.loadDashboard()
        .then(data => {
            if (data && data.dashboard) {
                const dashboard = data.dashboard;

                // Mise à jour KPI portefeuille
                const kpiPortfolio = document.getElementById('kpi-portfolio');
                if (kpiPortfolio && dashboard.balance) {
                    kpiPortfolio.textContent = '$' + parseFloat(dashboard.balance).toLocaleString();
                }

                // Mise à jour positions wallet (GraphQL)
                const walletPositions = document.getElementById('wallet-positions');
                if (walletPositions && dashboard.assets) {
                    if (dashboard.assets.length > 0) {
                        walletPositions.innerHTML = dashboard.assets.map(asset => `
                            <div class="position-card">
                                <div class="position-symbol">${asset.symbol}</div>
                                <div class="position-quantity">${parseFloat(asset.quantity).toFixed(4)}</div>
                                <div class="position-value">$${parseFloat(asset.value || 0).toLocaleString()}</div>
                            </div>
                        `).join('');
                    } else {
                        walletPositions.innerHTML = '<div class="empty-state">Aucune position</div>';
                    }
                }
            }
        })
        .catch(err => {
            console.error('Erreur GraphQL dashboard:', err);
        });
}

function loadWallet() {
    if (!authToken) return;

    window.loadWallet()
        .then(data => {
            const walletPositions = document.getElementById('wallet-positions');
            if (walletPositions) {
                if (data && data.positions && data.positions.length > 0) {
                    walletPositions.innerHTML = data.positions.map(pos => `
                        <div class="position-card">
                            <div class="position-symbol">${pos.asset_symbol}</div>
                            <div class="position-quantity">${parseFloat(pos.quantity).toFixed(4)}</div>
                            <div class="position-value">Position</div>
                        </div>
                    `).join('');
                } else {
                    walletPositions.innerHTML = '<div class="empty-state">Aucune position</div>';
                }
            }

            if (data && data.balance) {
                const kpiPortfolio = document.getElementById('kpi-portfolio');
                if (kpiPortfolio) {
                    kpiPortfolio.textContent = '$' + parseFloat(data.balance).toLocaleString();
                }
            }
        })
        .catch(err => {
            console.error('Erreur wallet:', err);
            const walletPositions = document.getElementById('wallet-positions');
            if (walletPositions) {
                walletPositions.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
            }
        });
}

function loadAnalytics() {
    if (!authToken) return;

    window.loadAnalytics()
        .then(data => {
            if (data && data.result) {
                const result = data.result;

                // Volume de trading
                const kpiVolume = document.getElementById('kpi-volume');
                if (kpiVolume && result.volume) {
                    kpiVolume.textContent = '$' + parseFloat(result.volume.total_volume_usd || 0).toLocaleString();
                }

                // Statistiques ordres
                const kpiOrders = document.getElementById('kpi-orders');
                if (kpiOrders && result.orders) {
                    const pending = result.orders.pending_orders || 0;
                    kpiOrders.textContent = pending.toString();
                }

                // Alertes - chargé via REST séparément
                const kpiAlerts = document.getElementById('kpi-alerts');
                if (kpiAlerts) {
                    // On charge les alertes via REST
                    fetch('/api/notifications/alerts/', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    })
                        .then(r => r.json())
                        .then(alertsData => {
                            if (kpiAlerts) {
                                const alerts = alertsData.alerts || alertsData;
                                kpiAlerts.textContent = (alerts && alerts.length) ? alerts.length.toString() : '0';
                            }
                        })
                        .catch(err => console.error('Erreur alertes KPI:', err));
                }
            }
        })
        .catch(err => {
            console.error('Erreur analytics:', err);
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
                const orders = data.results || data;
                if (orders && orders.length > 0) {
                    tbody.innerHTML = orders.map(order => `
                    <tr>
                        <td><span class="order-id">#${order.id.toString().slice(0, 8)}</span></td>
                        <td><span class="asset-badge">${order.symbol || 'BTC'}</span></td>
                        <td><span class="order-type ${order.side === 'BUY' ? 'buy' : 'sell'}">${order.side === 'BUY' ? 'Achat' : 'Vente'}</span></td>
                        <td>$${parseFloat(order.price || 0).toLocaleString()}</td>
                        <td>${parseFloat(order.quantity).toFixed(4)}</td>
                        <td><span class="status-badge ${order.status === 'FILLED' ? 'filled' : 'pending'}">${order.status === 'FILLED' ? 'Exécuté' : order.status}</span></td>
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
                const assets = data.assets || data;
                if (assets && assets.length > 0) {
                    tbody.innerHTML = assets.map(asset => `
                    <tr>
                        <td><span class="asset-badge">${asset.symbol}</span></td>
                        <td>${asset.name}</td>
                        <td><span class="price">$${parseFloat(asset.current_price || 0).toLocaleString()}</span></td>
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
            const alertsList = document.getElementById('alerts-list');
            if (alertsList) {
                const alerts = data.alerts || data;
                if (alerts && alerts.length > 0) {
                    alertsList.innerHTML = alerts.map(alert => `
                        <div class="alert-card">
                            <div class="alert-symbol">${alert.asset_symbol}</div>
                            <div class="alert-target">Cible: $${parseFloat(alert.target_price).toLocaleString()}</div>
                            <div class="alert-direction ${alert.direction === 'ABOVE' ? 'positive' : 'negative'}">${alert.direction === 'ABOVE' ? 'Au-dessus' : 'En dessous'}</div>
                        </div>
                    `).join('');
                } else {
                    alertsList.innerHTML = '<div class="empty-state">Aucune alerte</div>';
                }
            }
        })
        .catch(err => {
            console.error('Erreur alertes:', err);
            const alertsList = document.getElementById('alerts-list');
            if (alertsList) {
                alertsList.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
            }
        });
}

function createBankAccount() {
    window.createBankAccount()
        .then(data => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                if (data && data.includes('Account created')) {
                    soapData.innerHTML = '<div class="success-message">Compte bancaire créé avec succès</div>';
                } else {
                    soapData.textContent = data;
                }
            }
        })
        .catch(err => {
            const soapData = document.getElementById('soap-data');
            if (soapData) {
                soapData.innerHTML = '<div class="error-message">Erreur: ' + err.message + '</div>';
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
                soapData.innerHTML = '<div class="error-message">Erreur: ' + err.message + '</div>';
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