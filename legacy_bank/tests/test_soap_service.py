from decimal import Decimal
import pytest
from django.test import Client
from legacy_bank.interfaces.soap_service import LegacyBankSOAPService


def test_soap_service_create_account():
    """Test la création d'un compte via le service SOAP"""
    service = LegacyBankSOAPService()

    # Créer une requête SOAP manuelle
    soap_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(soap_request)

    assert response.status_code == 200
    assert "CreateAccountResponse" in response.content.decode()


def test_soap_service_get_account():
    """Test la récupération d'un compte via le service SOAP"""
    service = LegacyBankSOAPService()

    # D'abord créer un compte
    create_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request)

    # Récupérer le compte
    get_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:GetAccount>
            <account_number>123456789</account_number>
        </tns:GetAccount>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(get_request)

    assert response.status_code == 200
    assert "GetAccountResponse" in response.content.decode()
    assert "John Doe" in response.content.decode()


def test_soap_service_deposit():
    """Test le dépôt via le service SOAP"""
    service = LegacyBankSOAPService()

    # Créer un compte
    create_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request)

    # Effectuer un dépôt
    deposit_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:Deposit>
            <account_number>123456789</account_number>
            <amount>500.00</amount>
        </tns:Deposit>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(deposit_request)

    assert response.status_code == 200
    assert "DepositResponse" in response.content.decode()


def test_soap_service_withdraw():
    """Test le retrait via le service SOAP"""
    service = LegacyBankSOAPService()

    # Créer un compte
    create_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request)

    # Effectuer un retrait
    withdraw_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:Withdraw>
            <account_number>123456789</account_number>
            <amount>500.00</amount>
        </tns:Withdraw>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(withdraw_request)

    assert response.status_code == 200
    assert "WithdrawResponse" in response.content.decode()


def test_soap_service_transfer():
    """Test le virement via le service SOAP"""
    service = LegacyBankSOAPService()

    # Créer deux comptes
    create_request1 = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request1)

    create_request2 = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>987654321</account_number>
            <owner_name>Jane Doe</owner_name>
            <initial_balance>500.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request2)

    # Effectuer un virement
    transfer_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:Transfer>
            <from_account>123456789</from_account>
            <to_account>987654321</to_account>
            <amount>300.00</amount>
        </tns:Transfer>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(transfer_request)

    assert response.status_code == 200
    assert "TransferResponse" in response.content.decode()


def test_soap_service_check_balance():
    """Test la vérification du solde via le service SOAP"""
    service = LegacyBankSOAPService()

    # Créer un compte
    create_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CreateAccount>
            <account_number>123456789</account_number>
            <owner_name>John Doe</owner_name>
            <initial_balance>1000.00</initial_balance>
        </tns:CreateAccount>
    </soap:Body>
</soap:Envelope>"""
    service.handle_request(create_request)

    # Vérifier le solde
    balance_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:CheckBalance>
            <account_number>123456789</account_number>
        </tns:CheckBalance>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(balance_request)

    assert response.status_code == 200
    assert "CheckBalanceResponse" in response.content.decode()
    assert "1000.00" in response.content.decode()


def test_soap_service_fault():
    """Test qu'une erreur retourne un SOAP Fault"""
    service = LegacyBankSOAPService()

    # Requête avec une opération inconnue
    invalid_request = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="legacybank.soap">
    <soap:Body>
        <tns:UnknownOperation>
            <account_number>123456789</account_number>
        </tns:UnknownOperation>
    </soap:Body>
</soap:Envelope>"""

    response = service.handle_request(invalid_request)

    assert response.status_code == 500
    assert "Fault" in response.content.decode()
