import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_register_user_success(client):
    """Vérifie l'inscription réussie d'un utilisateur."""
    payload = {
        "username": "johndoe",
        "email": "john@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post(
        "/api/auth/register", data=payload, content_type="application/json"
    )

    assert response.status_code == 201
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert User.objects.filter(username="johndoe").exists()


@pytest.mark.django_db
def test_login_user_success(client):
    """Vérifie l'authentification et l'obtention des tokens JWT."""
    User.objects.create_user(
        username="janedoe", email="jane@example.com", password="Password123!"
    )
    payload = {"username": "janedoe", "password": "Password123!"}

    response = client.post(
        "/api/auth/login", data=payload, content_type="application/json"
    )

    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
