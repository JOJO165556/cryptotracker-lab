# 03 — Setup & configuration

> Setup minimal justifié par un besoin réel — pas de CI ni de conteneurisation de
> Django à ce stade (voir "Décisions" ci-dessous). Ce document sera complété quand
> une nouvelle brique (CI, Docker pour Django...) sera réellement nécessaire.

## Décisions de ce setup

| Sujet | Choix | Pourquoi maintenant |
|---|---|---|
| Architecture | Monolithe modulaire | Pas de problème réseau/déploiement à résoudre → pas de microservices |
| Docker | Postgres + Redis uniquement | Évite une install locale de DB à gérer ; Django reste en local pour itérer vite |
| CI | Pas encore | Rien à protéger tant qu'il n'y a pas de premier test (arrive en phase 7) |
| API REST | Django Ninja (pas DRF) | Type hints, OpenAPI auto-généré, cohérent avec FastAPI utilisé en phase 10 (Order Engine) |

## 1. Structure des dossiers

```
cryptotracker-lab/
├── core/                  # settings Django, urls racine
├── identity/
├── wallet/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── interfaces/
├── market/
├── trading/
├── analytics/
├── notification/
├── payment/
├── docs/
│   ├── 00_vision_roadmap.md
│   ├── 01_project_definition.md
│   ├── 02_domain_model.md
│   ├── api-contracts.md
│   └── adr/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── manage.py
└── requirements.txt
```

Chaque module (`wallet`, `market`...) garde ses 4 sous-dossiers dès le départ, même
vides — ça force à réfléchir "cette ligne de code, c'est du domaine, de
l'infrastructure ou de l'interface ?" avant de l'écrire.

## 2. .gitignore

```
venv/
__pycache__/
*.pyc
.env
db.sqlite3
*.log
.DS_Store
```

## 3. Environnement Python

```bash
python -m venv venv
source venv/bin/activate          # ou venv\Scripts\activate sous Windows
pip install django psycopg2-binary django-ninja django-environ
django-admin startproject core .
pip freeze > requirements.txt
```

## 4. docker-compose.yml (Postgres + Redis uniquement)

```yaml
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: cryptotracker
      POSTGRES_USER: cryptotracker
      POSTGRES_PASSWORD: cryptotracker
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    restart: unless-stopped
    ports:
      - "6379:6379"

volumes:
  db_data:
```

```bash
docker compose up -d
```

## 5. .env.example

```
DEBUG=True
SECRET_KEY=change-me
DB_NAME=cryptotracker
DB_USER=cryptotracker
DB_PASSWORD=cryptotracker
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

Copier en `.env` (jamais committé) et adapter si besoin.

## 6. core/settings.py — lecture de la config

```python
import environ

env = environ.Env()
environ.Env.read_env()

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
}

INSTALLED_APPS = [
    # ... apps Django par défaut
    # django-ninja n'a pas besoin d'être listé dans INSTALLED_APPS
    "wallet",
    "market",
    "trading",
    # ajouter chaque module au fur et à mesure de sa création
]
```

## 7. Première app + migration

```bash
python manage.py startapp wallet
# placer le modèle Wallet (voir 02_domain_model.md) dans wallet/models.py
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## 8. Checklist avant de passer à la phase REST (Wallet)

- [ ] `docker compose up -d` lance Postgres + Redis sans erreur
- [ ] `.env` local créé et non committé (vérifier `git status`)
- [ ] `python manage.py migrate` passe sans erreur contre Postgres (pas SQLite)
- [ ] `python manage.py runserver` répond sur `/admin`
- [ ] Premier commit poussé avec la structure + les docs

## À ajouter plus tard (pas maintenant)

- **CI** : dès qu'un premier test existe (phase 7, module Wallet en REST)
- **Docker pour Django lui-même** : quand on voudra reproduire un environnement proche
  de "prod" (ex. juste avant la phase Performance/Résilience)
