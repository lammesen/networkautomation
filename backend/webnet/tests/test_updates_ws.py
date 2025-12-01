import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import AnonymousUser

from webnet.customers.models import Customer
from webnet.asgi import application

User = get_user_model()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_updates_ws_connects_for_authenticated_user():
    """Test that authenticated users can connect to the updates WebSocket."""
    customer = await sync_to_async(Customer.objects.create)(name="UpdatesTest")
    user = await sync_to_async(User.objects.create_user)(
        username="updates_user", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)

    communicator = WebsocketCommunicator(application, "/ws/updates/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_updates_ws_rejects_unauthenticated():
    """Test that unauthenticated users cannot connect to the updates WebSocket."""
    communicator = WebsocketCommunicator(application, "/ws/updates/")
    communicator.scope["user"] = AnonymousUser()
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_updates_ws_receives_entity_update():
    """Test that connected clients receive entity update broadcasts."""
    customer = await sync_to_async(Customer.objects.create)(name="BroadcastTest")
    user = await sync_to_async(User.objects.create_user)(
        username="broadcast_user", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)

    communicator = WebsocketCommunicator(application, "/ws/updates/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected

    # Simulate a broadcast to the customer group
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"updates_customer_{customer.id}",
        {
            "type": "entity_update",
            "data": {
                "type": "update",
                "entity": "job",
                "action": "updated",
                "id": 123,
                "status": "success",
            },
        },
    )

    response = await communicator.receive_json_from()
    assert response["type"] == "update"
    assert response["entity"] == "job"
    assert response["action"] == "updated"
    assert response["id"] == 123
    assert response["status"] == "success"

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_updates_ws_ping_pong():
    """Test that the WebSocket responds to ping with pong."""
    customer = await sync_to_async(Customer.objects.create)(name="PingTest")
    user = await sync_to_async(User.objects.create_user)(
        username="ping_user", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)

    communicator = WebsocketCommunicator(application, "/ws/updates/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"type": "ping"})
    response = await communicator.receive_json_from()
    assert response["type"] == "pong"

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_updates_ws_operator_only_sees_own_customer():
    """Test that operators only receive updates for their assigned customers."""
    c1 = await sync_to_async(Customer.objects.create)(name="CustomerA")
    c2 = await sync_to_async(Customer.objects.create)(name="CustomerB")

    # Operator assigned only to c1
    operator = await sync_to_async(User.objects.create_user)(
        username="op_user", password="secret123", role="operator"
    )
    await sync_to_async(operator.customers.add)(c1)

    communicator = WebsocketCommunicator(application, "/ws/updates/")
    communicator.scope["user"] = operator
    connected, _ = await communicator.connect()
    assert connected

    channel_layer = get_channel_layer()

    # Broadcast to c2 - operator should NOT receive this
    await channel_layer.group_send(
        f"updates_customer_{c2.id}",
        {
            "type": "entity_update",
            "data": {"type": "update", "entity": "device", "action": "created", "id": 1},
        },
    )

    # Broadcast to c1 - operator SHOULD receive this
    await channel_layer.group_send(
        f"updates_customer_{c1.id}",
        {
            "type": "entity_update",
            "data": {"type": "update", "entity": "device", "action": "created", "id": 2},
        },
    )

    # Should only receive the c1 update
    response = await communicator.receive_json_from()
    assert response["id"] == 2

    await communicator.disconnect()
