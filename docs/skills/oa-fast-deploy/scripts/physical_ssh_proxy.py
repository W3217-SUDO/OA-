#!/usr/bin/env python3
"""为 Windows SSH 连接指定物理网卡出口，保留 OpenSSH 的认证和主机校验。"""

import argparse
import ipaddress
import os
import socket
import struct
import sys
import threading


def main():
    if os.name != "nt":
        raise RuntimeError("此连接助手仅用于 Windows 的物理网卡出口选择")
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", required=True, type=ipaddress.IPv4Address)
    parser.add_argument("--interface", required=True, type=int)
    parser.add_argument("--host", required=True, type=ipaddress.IPv4Address)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    if not 0 < args.interface < 2**24 or not 0 < args.port < 65536:
        parser.error("网卡索引或端口无效")

    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        # IP_UNICAST_IF 要求网卡索引使用网络字节序；只影响当前套接字。
        connection.setsockopt(socket.IPPROTO_IP, 31, struct.pack("!I", args.interface))
        connection.bind((str(args.bind), 0))
        connection.settimeout(10)
        connection.connect((str(args.host), args.port))
        connection.settimeout(None)

        def send_input():
            while data := os.read(sys.stdin.fileno(), 65536):
                connection.sendall(data)
            connection.shutdown(socket.SHUT_WR)

        sender = threading.Thread(target=send_input, daemon=True)
        sender.start()
        while data := connection.recv(65536):
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
