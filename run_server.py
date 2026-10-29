"""Starts the web app so a phone on the same Wi-Fi can use it.

Phones only allow camera access on HTTPS pages, so by default this creates a
self-signed certificate (once) and serves over HTTPS on all network interfaces.

Usage:
    python run_server.py            # https://<laptop-ip>:8000 for phones
    python run_server.py --http     # http://localhost:8000, laptop browser only
"""

import argparse
import datetime
import ipaddress
import socket

import uvicorn

import config


def lan_ip() -> str:
    """The laptop's address on the local network (no packets are actually sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def ensure_certificate(ip: str):
    """Creates certs/key.pem and certs/cert.pem valid for localhost and this IP."""
    key_file, cert_file = config.CERT_DIR / "key.pem", config.CERT_DIR / "cert.pem"
    marker = config.CERT_DIR / "ip.txt"
    if key_file.exists() and cert_file.exists() and marker.exists() and marker.read_text() == ip:
        return key_file, cert_file

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    config.CERT_DIR.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Actionable Guidance (local)")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            x509.IPAddress(ipaddress.ip_address(ip)),
        ]), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                           serialization.NoEncryption()))
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    marker.write_text(ip)
    return key_file, cert_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Plain HTTP on localhost only")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.http:
        print(f"Open http://localhost:{args.port} on this laptop.")
        uvicorn.run("server:app", host="127.0.0.1", port=args.port)
        return

    ip = lan_ip()
    key_file, cert_file = ensure_certificate(ip)
    print("=" * 60)
    print(f"On your phone (same Wi-Fi), open:  https://{ip}:{args.port}")
    print("The browser warns about the certificate the first time: choose")
    print("'Advanced' -> 'Proceed' (Chrome) or 'Show details' -> 'visit this website' (Safari).")
    print("=" * 60)
    uvicorn.run("server:app", host="0.0.0.0", port=args.port,
                ssl_keyfile=str(key_file), ssl_certfile=str(cert_file))


if __name__ == "__main__":
    main()
