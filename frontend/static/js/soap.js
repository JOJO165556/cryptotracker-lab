function createBankAccount() {
    const accountNumber = document.getElementById('account-number').value;
    const ownerName = document.getElementById('owner-name').value;
    const initialBalance = document.getElementById('initial-balance').value;

    const soapRequest = `<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>${accountNumber}</account_number>
            <owner_name>${ownerName}</owner_name>
            <initial_balance>${initialBalance}</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>`;

    return fetch('/legacybank/soap/', {
        method: 'POST',
        headers: { 'Content-Type': 'text/xml' },
        body: soapRequest
    })
        .then(r => r.text());
}

function getBankAccount() {
    const accountNumber = document.getElementById('account-number').value;

    const soapRequest = `<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:GetAccount>
            <account_number>${accountNumber}</account_number>
        </tns:GetAccount>
    </soap:Body>
</soap:Envelope>`;

    return fetch('/legacybank/soap/', {
        method: 'POST',
        headers: { 'Content-Type': 'text/xml' },
        body: soapRequest
    })
        .then(r => r.text());
}