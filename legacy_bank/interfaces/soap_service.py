from decimal import Decimal
from defusedxml.ElementTree import fromstring
from xml.etree import ElementTree as ET
from django.http import HttpResponse

from legacy_bank.application.use_cases import LegacyBankService


class LegacyBankSOAPService:
    """Service SOAP simulant LegacyBank"""

    def __init__(self):
        self.bank_service = LegacyBankService()

    def handle_request(self, request_body: str) -> HttpResponse:
        """Traite une requête SOAP et retourne une réponse SOAP"""
        try:
            # Parser la requête SOAP avec defusedxml (sécurisé contre XXE)
            root = fromstring(request_body)
            body = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body")

            if body is None:
                return self._soap_fault("Client", "Body SOAP manquant")

            # Extraire le nom de l'opération
            operation = (
                body[0].tag.split("}")[-1] if "}" in body[0].tag else body[0].tag
            )

            # Router vers la méthode appropriée
            result = self._dispatch_operation(operation, body[0])

            # Construire la réponse SOAP
            return self._soap_response(operation, result)

        except Exception as e:
            return self._soap_fault("Server", f"Erreur interne: {str(e)}")

    def _dispatch_operation(self, operation: str, element):
        """Route l'opération vers la méthode appropriée"""
        if operation == "CreateAccount":
            account_number = element.findtext("account_number")
            owner_name = element.findtext("owner_name")
            initial_balance = Decimal(element.findtext("initial_balance") or "0")
            return self.bank_service.create_account(
                account_number, owner_name, initial_balance
            )

        elif operation == "GetAccount":
            account_number = element.findtext("account_number")
            return self.bank_service.get_account(account_number)

        elif operation == "Deposit":
            account_number = element.findtext("account_number")
            amount = Decimal(element.findtext("amount"))
            return self.bank_service.deposit(account_number, amount)

        elif operation == "Withdraw":
            account_number = element.findtext("account_number")
            amount = Decimal(element.findtext("amount"))
            return self.bank_service.withdraw(account_number, amount)

        elif operation == "Transfer":
            from_account = element.findtext("from_account")
            to_account = element.findtext("to_account")
            amount = Decimal(element.findtext("amount"))
            return self.bank_service.transfer(from_account, to_account, amount)

        elif operation == "CheckBalance":
            account_number = element.findtext("account_number")
            return self.bank_service.get_balance(account_number)

        else:
            raise ValueError(f"Opération inconnue: {operation}")

    def _soap_response(self, operation: str, result) -> HttpResponse:
        """Construit une réponse SOAP"""
        envelope = ET.Element("soap:Envelope")
        envelope.set("xmlns:soap", "http://schemas.xmlsoap.org/soap/envelope/")
        envelope.set("xmlns:tns", "legacybank.soap")

        body = ET.SubElement(envelope, "soap:Body")
        response = ET.SubElement(body, f"tns:{operation}Response")

        if isinstance(result, str):
            ET.SubElement(response, "return").text = result
        elif hasattr(result, "__dict__"):
            for key, value in result.__dict__.items():
                ET.SubElement(response, key).text = str(value)
        else:
            ET.SubElement(response, "return").text = str(result)

        xml_str = ET.tostring(envelope, encoding="unicode")
        return HttpResponse(xml_str, content_type="text/xml")

    def _soap_fault(self, fault_code: str, fault_string: str) -> HttpResponse:
        """Construit une réponse SOAP Fault"""
        envelope = ET.Element("soap:Envelope")
        envelope.set("xmlns:soap", "http://schemas.xmlsoap.org/soap/envelope/")

        body = ET.SubElement(envelope, "soap:Body")
        fault = ET.SubElement(body, "soap:Fault")

        ET.SubElement(fault, "faultcode").text = fault_code
        ET.SubElement(fault, "faultstring").text = fault_string

        xml_str = ET.tostring(envelope, encoding="unicode")
        return HttpResponse(xml_str, content_type="text/xml", status=500)


def soap_endpoint(request):
    """Endpoint Django pour le service SOAP"""
    if request.method == "POST":
        service = LegacyBankSOAPService()
        return service.handle_request(request.body.decode("utf-8"))
    elif request.method == "GET" and "wsdl" in request.GET:
        # Retourner un WSDL simplifié
        wsdl = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="legacybank.soap"
             targetNamespace="legacybank.soap">
    <message name="CreateAccountRequest">
        <part name="account_number" type="xsd:string"/>
        <part name="owner_name" type="xsd:string"/>
        <part name="initial_balance" type="xsd:decimal"/>
    </message>
    <message name="CreateAccountResponse">
        <part name="return" type="xsd:string"/>
    </message>
    <portType name="LegacyBankPortType">
        <operation name="CreateAccount">
            <input message="tns:CreateAccountRequest"/>
            <output message="tns:CreateAccountResponse"/>
        </operation>
    </portType>
    <binding name="LegacyBankBinding" type="tns:LegacyBankPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="CreateAccount">
            <soap:operation soapAction="legacybank.soap/CreateAccount"/>
            <input><soap:body use="encoded"/></input>
            <output><soap:body use="encoded"/></output>
        </operation>
    </binding>
    <service name="LegacyBankService">
        <port name="LegacyBankPort" binding="tns:LegacyBankBinding">
            <soap:address location="http://localhost:8000/legacybank/soap/"/>
        </port>
    </service>
</definitions>"""
        return HttpResponse(wsdl, content_type="application/xml")
    else:
        return HttpResponse("Méthode non supportée", status=405)
