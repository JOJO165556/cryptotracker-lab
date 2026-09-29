from decimal import Decimal
import pytest
from django.test import Client


@pytest.mark.django_db
def test_soap_endpoint_integration():
    """Test d'intégration de l'endpoint SOAP réel via HTTP"""
    client = Client()

    # Créer un compte via l'endpoint SOAP
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

    response = client.post(
        "/legacybank/soap/",
        data=soap_request,
        content_type="text/xml",
    )

    assert response.status_code == 200
    assert "CreateAccountResponse" in response.content.decode()


@pytest.mark.django_db
def test_soap_wsdl_endpoint():
    """Test que le WSDL est accessible"""
    client = Client()

    response = client.get("/legacybank/soap/?wsdl")

    assert response.status_code == 200
    assert "definitions" in response.content.decode()
    assert "LegacyBankService" in response.content.decode()


@pytest.mark.django_db
def test_soap_endpoint_fault_on_invalid_xml():
    """Test que l'endpoint retourne un SOAP Fault sur XML invalide"""
    client = Client()

    invalid_xml = "<invalid>xml</invalid>"

    response = client.post(
        "/legacybank/soap/",
        data=invalid_xml,
        content_type="text/xml",
    )

    assert response.status_code == 500
    assert "Fault" in response.content.decode()


@pytest.mark.django_db
def test_soap_endpoint_get_method_not_allowed():
    """Test que la méthode GET sans ?wsdl est refusée"""
    client = Client()

    response = client.get("/legacybank/soap/")

    assert response.status_code == 405
    assert "Méthode non supportée" in response.content.decode()