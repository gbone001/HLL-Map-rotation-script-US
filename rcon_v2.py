
# Minimal RCON v2 client
# Based on HLL RCON v2 PDF specification
# XOR + handshake + simple command execution

import socket
import logging
from config import get_env

log = logging.getLogger(__name__)

class RconV2:
    def __init__(self):
        self.host = get_env("RCON_HOST")
        self.port = int(get_env("RCON_PORT", "0"))
        self.password = get_env("RCON_PASSWORD")

    def xor_crypt(self, data: bytes, key: bytes) -> bytes:
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    def send_cmd(self, command: str) -> str:
        if not self.host or not self.port or not self.password:
            raise Exception("Missing RCON fallback settings")

        log.debug("RCONv2 connecting fallback")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)

        try:
            s.connect((self.host, self.port))

            # Send password (PDF spec uses XOR obfuscation)
            key = b"#B"  # simple XOR key for demo
            p = self.xor_crypt(self.password.encode(), key)
            s.sendall(p)

            # Send command packet
            cmd = self.xor_crypt(command.encode(), key)
            s.sendall(cmd)

            data = s.recv(4096)
            out = self.xor_crypt(data, key).decode(errors="ignore")
            return out

        except Exception as e:
            log.error(f"RCONv2 error: {e}")
            raise

        finally:
            s.close()
