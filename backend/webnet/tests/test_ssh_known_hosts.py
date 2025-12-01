import pytest
from django.test import override_settings

from webnet.core.ssh import _resolve_known_hosts


@override_settings(DEBUG=True, SSH_STRICT_HOST_VERIFY=True)
def test_known_hosts_allows_debug_when_missing(tmp_path):
    missing = tmp_path / "nope"
    with override_settings(SSH_KNOWN_HOSTS_PATH=str(missing)):
        assert _resolve_known_hosts() is None


@override_settings(DEBUG=False, SSH_STRICT_HOST_VERIFY=True)
def test_known_hosts_raises_when_missing_and_strict(tmp_path):
    missing = tmp_path / "nope"
    with override_settings(SSH_KNOWN_HOSTS_PATH=str(missing)):
        with pytest.raises(Exception):
            _resolve_known_hosts()


@override_settings(DEBUG=False, SSH_STRICT_HOST_VERIFY=True)
def test_known_hosts_uses_path(tmp_path, monkeypatch):
    kh = tmp_path / "known_hosts"
    kh.write_text("example.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDc")
    monkeypatch.setenv("SSH_KNOWN_HOSTS_PATH", str(kh))
    # settings override won't pick env; ensure path passed via settings
    with override_settings(SSH_KNOWN_HOSTS_PATH=str(kh)):
        assert _resolve_known_hosts() == str(kh)
