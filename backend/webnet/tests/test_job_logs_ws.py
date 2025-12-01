import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import AnonymousUser

from webnet.jobs.models import Job
from webnet.customers.models import Customer
from webnet.asgi import application

User = get_user_model()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_job_logs_ws_receives_broadcast():
    customer = await sync_to_async(Customer.objects.create)(name="Acme")
    user = await sync_to_async(User.objects.create_user)(
        username="wsuser", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)
    job = await sync_to_async(Job.objects.create)(
        type="run_commands", status="running", user=user, customer=customer
    )

    communicator = WebsocketCommunicator(application, f"/ws/jobs/{job.id}/")
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"job_{job.id}", {"type": "job_log", "data": {"message": "hello ws"}}
    )
    response = await communicator.receive_json_from()

    assert response.get("message") == "hello ws"
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_job_logs_ws_rejects_unauthenticated():
    customer = await sync_to_async(Customer.objects.create)(name="Acme")
    user = await sync_to_async(User.objects.create_user)(
        username="wsuser2", password="secret123", role="admin"
    )
    await sync_to_async(user.customers.add)(customer)
    job = await sync_to_async(Job.objects.create)(
        type="run_commands", status="running", user=user, customer=customer
    )
    communicator = WebsocketCommunicator(application, f"/ws/jobs/{job.id}/")
    communicator.scope["user"] = AnonymousUser()
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_job_logs_ws_blocks_wrong_customer():
    c1 = await sync_to_async(Customer.objects.create)(name="Acme")
    c2 = await sync_to_async(Customer.objects.create)(name="Beta")
    owner = await sync_to_async(User.objects.create_user)(
        username="owner", password="secret123", role="admin"
    )
    await sync_to_async(owner.customers.add)(c1)
    job = await sync_to_async(Job.objects.create)(
        type="run_commands", status="running", user=owner, customer=c1
    )
    other = await sync_to_async(User.objects.create_user)(
        username="other", password="secret123", role="operator"
    )
    await sync_to_async(other.customers.add)(c2)

    communicator = WebsocketCommunicator(application, f"/ws/jobs/{job.id}/")
    communicator.scope["user"] = other
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
async def test_job_logs_ws_missing_job_is_rejected():
    user = await sync_to_async(User.objects.create_user)(
        username="ghost", password="secret123", role="admin"
    )
    communicator = WebsocketCommunicator(application, "/ws/jobs/99999/")
    communicator.scope["user"] = user
    connected, code = await communicator.connect()
    assert not connected
    await communicator.disconnect()
