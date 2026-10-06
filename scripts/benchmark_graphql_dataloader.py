"""
Benchmark GraphQL DataLoader anti-N+1.

Objectif: Compter les requêtes SQL pour dashboard avec N positions.
"""
import time
import requests


GRAPHQL_URL = "http://localhost:8000/graphql/"


def benchmark_graphql_dataloader():
    """Benchmark DataLoader vs sans DataLoader."""
    # Authentification
    response = requests.post("http://localhost:8000/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access"]
    headers = {"Authorization": f"Bearer {token}"}

    query = """
    query Dashboard {
      dashboard {
        balance
        assets {
          symbol
          quantity
          value
        }
      }
    }
    """

    # Mesurer la latence
    start = time.time()
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)
    end = time.time()

    print(f"GraphQL avec DataLoader:")
    print(f"  Latence: {(end - start) * 1000:.2f}ms")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")


if __name__ == "__main__":
    print("=== Benchmark GraphQL DataLoader ===")
    benchmark_graphql_dataloader()
