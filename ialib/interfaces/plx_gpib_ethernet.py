import time
import random
import socket
import struct
from typing import List

import netifaces as ni  # type: ignore

__all__ = [
    "PlxGPIBEth",
    "PlxGPIBEthDevice",
    "plx_discover",
    "plx_get_first",
]

prologix_singleton = dict()

NETFINDER_SERVER_PORT = 3040

NF_IDENTIFY = 0
NF_IDENTIFY_REPLY = 1

NF_MAGIC = 0x5A

NF_IP_DYNAMIC = 0
NF_IP_STATIC = 1

HEADER_FMT = "!2cH6s2x"
IDENTIFY_FMT = HEADER_FMT
IDENTIFY_REPLY_FMT = "!H6c4s4s4s4s4s4s32s"


def _parse_identify_reply(msg):
    """
    Unpack identify reply.
    From NetFinder for Linux.

    :param msg: Message to parse
    :return: dict
    """
    hdrlen = struct.calcsize(HEADER_FMT)

    headr = struct.unpack(HEADER_FMT, msg[0:hdrlen])

    params = struct.unpack(IDENTIFY_REPLY_FMT, msg[hdrlen:])

    d = {
        "magic": ord(headr[0]),
        "id": ord(headr[1]),
        "sequence": headr[2],
        "eth_addr": "-".join(str(i) for i in headr[3]),
        "uptime_days": params[0],
        "uptime_hrs": ord(params[1]),
        "uptime_min": ord(params[2]),
        "uptime_secs": ord(params[3]),
        "mode": ord(params[4]),
        "alert": ord(params[5]),
        "ip_type": ord(params[6]),
        "ip_addr": ".".join(str(i) for i in params[7]),
        "ip_netmask": ".".join(str(i) for i in params[8]),
        "ip_gw": ".".join(str(i) for i in params[9]),
        "app_ver": ".".join(str(i) for i in params[10]),
        "boot_ver": ".".join(str(i) for i in params[11]),
        "hw_ver": ".".join(str(i) for i in params[12]),
        "name": params[13].decode(encoding="ascii", errors="ignore"),
    }
    return d


def plx_discover(timeout: float = 0.5) -> List[dict]:
    """
    Discover prologix devices connected to all PC interfaces.

    Based on NetFinder for Linux.

    :param timeout: Timeout to wait for devices to respond
    :return: list of device dicts
    """
    devices = dict()

    # Search all the interfaces on this PC
    for iface in ni.interfaces():
        # Sender socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.bind((ni.ifaddresses(iface)[ni.AF_INET][0]["addr"], 0))
        except KeyError:
            # Interface has no assigned IP
            continue

        # Receiver socket
        r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        r.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        r.setblocking(False)
        r.settimeout(0.100)
        r.bind(("", s.getsockname()[1]))

        seq = random.randint(1, 65535)
        msg = struct.pack(
            HEADER_FMT,
            bytes([NF_MAGIC]),
            bytes([NF_IDENTIFY]),
            seq,
            b"\xFF\xFF\xFF\xFF\xFF\xFF",
        )

        s.sendto(msg, ("<broadcast>", NETFINDER_SERVER_PORT))
        exp = time.time() + timeout
        while time.time() < exp:
            try:
                reply = r.recv(256)
                if len(reply) != struct.calcsize(HEADER_FMT) + struct.calcsize(
                    IDENTIFY_REPLY_FMT
                ):
                    continue
                d = _parse_identify_reply(reply)
                if d["magic"] != NF_MAGIC:
                    continue
                if d["id"] != NF_IDENTIFY_REPLY:
                    continue
                if d["sequence"] != seq:
                    continue
                devices[d["eth_addr"]] = d
            except socket.timeout:
                pass

    return [v for _, v in devices.items()]


def plx_get_first(timeout=0.5) -> str:
    """
    Discover the first prologix device connected to all PC interfaces.

    Based on NetFinder for Linux.

    :param timeout: Timeout to wait for devices to respond
    :return: list of device ip addresses
    """
    try:
        return plx_discover(timeout)[0]["ip_addr"]
    except IndexError:
        raise RuntimeError("No plx devices found!") from None


class PlxGPIBEthDevice:
    def __init__(self, host: str, address: int, timeout: float = 1):
        self.address = address
        self.gpib = PlxGPIBEth(host=host, timeout=timeout)
        self.connect()

    def connect(self):
        self.gpib.connect()
        self.gpib.select(self.address)

    def close(self):
        self.gpib.close()

    def write(self, *args):
        self.gpib.select(self.address)
        return self.gpib.write(*args)

    def read(self, *args):
        self.gpib.select(self.address)
        return self.gpib.read(*args)

    def query(self, *args, retry_limit=10):
        self.gpib.select(self.address)
        for _ in range(retry_limit - 1):
            try:
                return self.query(*args)
            except socket.timeout:
                pass
        return self.gpib.query(*args)

    def idn(self):
        self.gpib.select(self.address)
        return self.query("*IDN?")

    def reset(self):
        self.gpib.select(self.address)
        self.write("*RST")


class PlxGPIBEth:
    PORT = 1234

    def __init__(self, host, timeout: float = 1) -> None:
        # see user manual for details on accepted timeout values
        # https://prologix.biz/downloads/PrologixGpibEthernetManual.pdf#page=13
        if not 1e-3 <= timeout <= 3:
            raise ValueError("Timeout must be >= 1e-3 (1ms) and <= 3 (3s)")

        self.host = host
        self.timeout = timeout

        if host not in prologix_singleton:
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
            )
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.PORT))
            prologix_singleton[host] = self.socket
        else:
            self.socket = prologix_singleton[host]
        self.connect()

    def connect(self) -> None:
        self._setup()

    def close(self) -> None:
        self.socket.close()

    def select(self, addr: int):
        self._send(f"++addr {addr}")

    def write(self, cmd: str) -> None:
        self._send(cmd)

    def read(self, num_bytes: int = 1024) -> str:
        self._send("++read eoi")
        return self._recv(num_bytes)

    def query(self, cmd, buffer_size=1024 * 1024):
        self.write(cmd)
        return self.read(buffer_size)

    def _send(self, value):
        encoded_value = ("%s\n" % value).encode("ascii")
        self.socket.send(encoded_value)

    def _recv(self, byte_num):
        value = self.socket.recv(byte_num)
        return value.decode("ascii")

    def _setup(self):
        # set device to CONTROLLER mode
        self._send("++mode 1")

        # disable read after write
        self._send("++auto 0")

        # set GPIB timeout
        self._send(f"++read_tmo_ms {int(self.timeout * 1e3)}")

        # do not require CR or LF appended to GPIB data
        self._send("++eos 3")
