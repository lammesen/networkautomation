import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from channels.testing import WebsocketCommunicator
from asgiref.sync import sync_to_async

from webnet.asgi import application
from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.api.ssh_consumer import SSHConsumer

User = get_user_model()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ssh_ws_rejects_unauthenticated():
    customer = await sync_to_async(Customer.objects.create)(name="Acme")
    cred = await sync_to_async(Credential.objects.create)(
        customer=customer, name="lab", username="u1"
    )
    cred.password = "pass"
    await sync_to_async(cred.save)()
    device = await sync_to_async(Device.objects.create)(
        customer=customer,
        hostname="routerx",
        mgmt_ip="192.0.2.50",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    communicator = WebsocketCommunicator(application, f"/ws/devices/{device.id}/ssh/")
    communicator.scope["user"] = AnonymousUser()
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()


class FakeSession:
    def __init__(self, stdout="hello out"):
        self.stdout = stdout

    async def run_command(self, command: str):
        class Result:
            def __init__(self, out):
                self.stdout = out
                self.stderr = ""
                self.exit_status = 0

        return Result(self.stdout)

    async def close(self):
        return


class FakeManager:
    def __init__(self, stdout="hello out"):
        self.stdout = stdout

    async def open_session(self, host: str, port: int, username: str, password: str):
        return FakeSession(self.stdout)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ssh_ws_authenticated_echo(monkeypatch):
    customer = await sync_to_async(Customer.objects.create)(name="Acme")
    user = await sync_to_async(User.objects.create_user)(
        username="wsuser3", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)
    cred = await sync_to_async(Credential.objects.create)(
        customer=customer, name="lab", username="u1"
    )
    cred.password = "pass"
    await sync_to_async(cred.save)()
    device = await sync_to_async(Device.objects.create)(
        customer=customer,
        hostname="routerz",
        mgmt_ip="192.0.2.51",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    monkeypatch.setattr(SSHConsumer, "manager_cls", FakeManager)

    communicator = WebsocketCommunicator(application, f"/ws/devices/{device.id}/ssh/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected
    # consume connected message
    await communicator.receive_json_from()
    await communicator.send_json_to({"type": "command", "command": "show version"})
    response = await communicator.receive_json_from()
    assert response.get("type") == "output", response
    assert response.get("stdout") == "hello out"
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ssh_ws_blocks_wrong_customer():
    c1 = await sync_to_async(Customer.objects.create)(name="Acme")
    c2 = await sync_to_async(Customer.objects.create)(name="Beta")
    cred = await sync_to_async(Credential.objects.create)(customer=c1, name="lab", username="u1")
    cred.password = "pass"
    await sync_to_async(cred.save)()
    device = await sync_to_async(Device.objects.create)(
        customer=c1,
        hostname="router-block",
        mgmt_ip="192.0.2.60",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    user = await sync_to_async(User.objects.create_user)(
        username="betauser", password="secret123", role="operator"
    )
    await sync_to_async(user.customers.add)(c2)

    communicator = WebsocketCommunicator(application, f"/ws/devices/{device.id}/ssh/")
    communicator.scope["user"] = user
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_ssh_ws_rejects_invalid_payload(monkeypatch):
    customer = await sync_to_async(Customer.objects.create)(name="Acme")
    user = await sync_to_async(User.objects.create_user)(
        username="wsuser4", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)
    cred = await sync_to_async(Credential.objects.create)(
        customer=customer, name="lab", username="u1"
    )
    cred.password = "pass"
    await sync_to_async(cred.save)()
    device = await sync_to_async(Device.objects.create)(
        customer=customer,
        hostname="routerbad",
        mgmt_ip="192.0.2.52",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    monkeypatch.setattr(SSHConsumer, "manager_cls", FakeManager)

    communicator = WebsocketCommunicator(application, f"/ws/devices/{device.id}/ssh/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()
    await communicator.send_json_to({"type": "not-command", "foo": "bar"})
    response = await communicator.receive_json_from()
    assert response.get("type") == "error"
    await communicator.disconnect()
