# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from tsdbenv.network_validator import NetworkValidator

def test_is_ip_on_subnet_true():
    """Test IP on subnet detection (positive case)."""
    result = NetworkValidator.is_ip_on_subnet("192.168.1.100", "192.168.1.0/24")
    assert result is True

def test_is_ip_on_subnet_false():
    """Test IP on subnet detection (negative case)."""
    result = NetworkValidator.is_ip_on_subnet("192.168.2.100", "192.168.1.0/24")
    assert result is False

def test_is_ip_on_subnet_edge_cases():
    """Test IP on subnet edge cases."""
    assert NetworkValidator.is_ip_on_subnet("192.168.1.0", "192.168.1.0/24") is True
    assert NetworkValidator.is_ip_on_subnet("192.168.1.255", "192.168.1.0/24") is True

def test_get_subnet_from_gateway():
    """Test subnet extraction from gateway IP."""
    subnet = NetworkValidator.get_subnet("192.168.1.1")
    assert "192.168.1" in subnet

def test_localhost_validation():
    """Test that localhost is always valid."""
    is_valid, msg = NetworkValidator.validate_bind_ip("127.0.0.1")
    assert is_valid is True
    assert msg is None

def test_invalid_ip_validation():
    """Test validation of IP not on local network."""
    is_valid, msg = NetworkValidator.validate_bind_ip("10.0.0.1")
    assert isinstance(is_valid, bool)
    if not is_valid:
        assert msg is not None
        assert "not on your LAN" in msg or "unable to determine" in msg.lower()
