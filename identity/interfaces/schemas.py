from pydantic import BaseModel, EmailStr

class RegisterSchema(BaseModel):
    """Schéma pour l'inscription d'un nouvel utilisateur."""
    username: str
    email: EmailStr
    password: str


class LoginSchema(BaseModel):
    """Schéma pour la connexion d'un utilisateur."""
    username: str
    password: str


class TokenSchema(BaseModel):
    """Schéma de réponse contenant le couple de tokens JWT."""
    access: str
    refresh: str
    token_type: str = "bearer"