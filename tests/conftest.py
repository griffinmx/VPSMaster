"""Unit fixtures exercise direct transports; real CLI enables process guards."""
import pytest

@pytest.fixture(autouse=True)
def direct_mockable_transports(monkeypatch):
    monkeypatch.setenv('PROXYDOCTOR_NETWORK_WORKERS','0')
