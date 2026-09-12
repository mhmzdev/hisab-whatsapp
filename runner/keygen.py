"""One-time runner keypair generation. Run with: python -m runner.keygen"""
from .crypto import generate_keypair

if __name__ == "__main__":
    public_b64, private_b64 = generate_keypair()
    print("Public key (portal build-time constant, safe to embed):")
    print(public_b64)
    print()
    print("Private key (runner's .env as RUNNER_PRIVATE_KEY — never commit this):")
    print(private_b64)
