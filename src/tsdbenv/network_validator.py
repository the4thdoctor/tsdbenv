# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import ipaddress
import socket
from typing import List, Optional, Tuple


class NetworkValidator:
    """Validates and detects local network IPs."""

    @staticmethod
    def get_local_ips() -> List[str]:
        """Get all local network IPs on the machine."""
        ips = []
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
        except (socket.gaierror, socket.error):
            pass

        if "127.0.0.1" not in ips:
            ips.insert(0, "127.0.0.1")

        return ips

    @staticmethod
    def get_network_gateway() -> Optional[str]:
        """Detect LAN gateway IP (e.g., 192.168.1.1)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            parts = local_ip.rsplit(".", 1)
            if len(parts) == 2:
                return f"{parts[0]}.1"
        except Exception:
            pass

        return None

    @staticmethod
    def get_subnet(gateway_ip: str) -> str:
        """Extract subnet from gateway IP."""
        parts = gateway_ip.rsplit(".", 1)
        if len(parts) == 2:
            return f"{parts[0]}.0/24"
        return f"{gateway_ip}/32"

    @staticmethod
    def is_ip_on_subnet(ip: str, subnet: str) -> bool:
        """Check if IP is on given subnet."""
        try:
            ip_addr = ipaddress.ip_address(ip)
            subnet_net = ipaddress.ip_network(subnet, strict=False)
            return ip_addr in subnet_net
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return False

    @staticmethod
    def validate_bind_ip(bind_ip: str) -> Tuple[bool, Optional[str]]:
        """Validate bind IP against LAN gateway."""
        if bind_ip == "127.0.0.1" or bind_ip == "localhost":
            return (True, None)

        gateway = NetworkValidator.get_network_gateway()
        if gateway is None:
            return (
                True,
                "⚠️  Unable to detect network gateway. IP may not be reachable.",
            )

        subnet = NetworkValidator.get_subnet(gateway)
        if not NetworkValidator.is_ip_on_subnet(bind_ip, subnet):
            warning = f"⚠️  IP {bind_ip} is not on your LAN (gateway: {gateway}, subnet: {subnet}). You may not be able to access the container."
            return (False, warning)

        return (True, None)
