#!/usr/bin/env python3
"""Simple TCP connectivity tester.

Usage:
  python connect_test.py <host> [port]

Example:
  python connect_test.py example.com 7779
"""
import socket
import sys
import time


def main():
    if len(sys.argv) < 2:
        print("Usage: python connect_test.py <host> [port]")
        sys.exit(2)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else 7779

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    start = time.time()
    try:
        sock.connect((host, port))
        elapsed = time.time() - start
        print(f"SUCCESS: connected to {host}:{port} (took {elapsed:.2f}s)")
        sock.close()
        sys.exit(0)
    except socket.timeout:
        print(f"FAIL: connection to {host}:{port} timed out")
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: could not connect to {host}:{port} — {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
