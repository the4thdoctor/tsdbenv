# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from unittest.mock import patch, MagicMock
import socket
import ipaddress
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

def test_is_ip_on_subnet_ipv6():
    """Test IP on subnet with IPv6 addresses."""
    result = NetworkValidator.is_ip_on_subnet("2001:db8::1", "2001:db8::/32")
    assert result is True

def test_get_subnet_from_gateway():
    """Test subnet extraction from gateway IP."""
    subnet = NetworkValidator.get_subnet("192.168.1.1")
    assert "192.168.1" in subnet

def test_get_subnet_single_octet():
    """Test subnet extraction with single octet (edge case)."""
    subnet = NetworkValidator.get_subnet("192")
    assert "/32" in subnet

def test_localhost_validation():
    """Test that localhost is always valid."""
    is_valid, msg = NetworkValidator.validate_bind_ip("127.0.0.1")
    assert is_valid is True
    assert msg is None

def test_localhost_string_validation():
    """Test that 'localhost' string is always valid."""
    is_valid, msg = NetworkValidator.validate_bind_ip("localhost")
    assert is_valid is True
    assert msg is None

def test_invalid_ip_validation():
    """Test validation of IP not on local network."""
    is_valid, msg = NetworkValidator.validate_bind_ip("10.0.0.1")
    assert isinstance(is_valid, bool)
    if not is_valid:
        assert msg is not None
        assert "not on your LAN" in msg or "unable to determine" in msg.lower()

@patch('socket.socket')
def test_get_network_gateway_exception(mock_socket):
    """Test get_network_gateway with socket exception."""
    mock_socket.return_value.connect.side_effect = Exception("Connection failed")
    result = NetworkValidator.get_network_gateway()
    assert result is None

@patch('socket.gethostbyname_ex')
def test_get_local_ips_exception(mock_gethostbyname):
    """Test get_local_ips with socket exception."""
    mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")
    result = NetworkValidator.get_local_ips()
    assert "127.0.0.1" in result

@patch('socket.gethostname')
@patch('socket.gethostbyname_ex')
def test_get_local_ips_socket_error(mock_gethostbyname, mock_gethostname):
    """Test get_local_ips with socket.error exception."""
    mock_gethostbyname.side_effect = socket.error("Socket error")
    result = NetworkValidator.get_local_ips()
    assert "127.0.0.1" in result

@patch('tsdbenv.network_validator.NetworkValidator.get_network_gateway')
def test_validate_bind_ip_no_gateway(mock_gateway):
    """Test validate_bind_ip when gateway detection fails."""
    mock_gateway.return_value = None
    is_valid, msg = NetworkValidator.validate_bind_ip("192.168.1.100")
    assert is_valid is True
    assert msg is not None
    assert "Unable to detect network gateway" in msg
