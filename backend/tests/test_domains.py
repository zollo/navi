"""Custom domains: claiming, DNS verification, lookup and the Kubernetes sync."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import domain_sync
from app.config import settings
from app.db import AsyncSessionLocal
from app.models.domain import CustomDomain
from app.services import domain_service

TARGET = "navi.example.net"
NAVI_IP = "203.0.113.10"


class FakeDns:
    def __init__(self) -> None:
        self.txt_records: dict[str, list[str]] = {}
        self.a_records: dict[str, set[str]] = {TARGET: {NAVI_IP}}
        self.fail = False

    async def txt(self, name: str) -> list[str]:
        if self.fail:
            raise domain_service.DnsError(f"DNS lookup for {name} failed (Timeout)")
        return self.txt_records.get(name, [])

    async def addresses(self, name: str) -> set[str]:
        if self.fail:
            raise domain_service.DnsError(f"DNS lookup for {name} failed (Timeout)")
        return self.a_records.get(name, set())

    def publish(self, domain: dict, ip: str = NAVI_IP) -> None:
        txt = next(r for r in domain["records"] if r["type"] == "TXT")
        self.txt_records[txt["name"]] = [txt["value"]]
        self.a_records[domain["hostname"]] = {ip}


@pytest.fixture
def fake_dns(monkeypatch) -> FakeDns:
    fake = FakeDns()
    monkeypatch.setattr(domain_service, "dns_client", fake)
    monkeypatch.setattr(settings, "custom_domains_enabled", True)
    monkeypatch.setattr(settings, "custom_domain_target", TARGET)
    monkeypatch.setattr(settings, "custom_domain_ips", "")
    monkeypatch.setattr(settings, "custom_domain_blocked", "example.net")
    return fake


def make_page(client, headers, handle: str) -> None:
    resp = client.put("/api/pages/me", headers=headers, json={"handle": handle})
    assert resp.status_code == 201, resp.text


def test_config_and_disabled(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "custom_domains_enabled", False)
    cfg = client.get("/api/domains/config").json()
    assert cfg["enabled"] is False
    make_page(client, alice, "alice")
    resp = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    assert resp.status_code == 403
    assert client.get("/api/domains/lookup", params={"domain": "www.alice.test"}).status_code == 404


def test_claim_verify_lookup_and_delete(client, alice, fake_dns):
    assert client.put(
        "/api/domains/me", headers=alice, json={"hostname": "www.alice.test"}
    ).status_code == 404  # no page yet
    make_page(client, alice, "alice")
    assert client.get("/api/domains/me", headers=alice).status_code == 404

    resp = client.put(
        "/api/domains/me", headers=alice, json={"hostname": "https://WWW.Alice.Test./links"}
    )
    assert resp.status_code == 201, resp.text
    domain = resp.json()
    assert domain["hostname"] == "www.alice.test"
    assert domain["status"] == "pending"
    types = {r["type"]: r for r in domain["records"]}
    assert types["TXT"]["name"] == "_navi-challenge.www.alice.test"
    assert types["TXT"]["value"].startswith("navi-verify=")
    assert types["CNAME"] == {
        "type": "CNAME",
        "name": "www.alice.test",
        "value": TARGET,
        "purpose": "Sends visitors to Navi.",
    }
    # Same hostname again: unchanged, same token.
    again = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    assert again.status_code == 200
    assert again.json()["records"] == domain["records"]

    # Nothing published yet.
    resp = client.post("/api/domains/me/verify", headers=alice)
    assert resp.json()["status"] == "pending"
    assert "TXT record _navi-challenge.www.alice.test" in resp.json()["last_error"]
    assert client.get("/api/domains/lookup", params={"domain": "www.alice.test"}).status_code == 404

    # TXT but pointing elsewhere.
    fake_dns.publish(domain, ip="198.51.100.1")
    resp = client.post("/api/domains/me/verify", headers=alice).json()
    assert resp["status"] == "pending"
    assert "points at 198.51.100.1" in resp["last_error"]

    fake_dns.publish(domain)
    resp = client.post("/api/domains/me/verify", headers=alice).json()
    assert resp["status"] == "active"
    assert resp["last_error"] is None and resp["verified_at"]

    found = client.get("/api/domains/lookup", params={"domain": "WWW.alice.test"})
    assert found.status_code == 200
    assert found.json() == {
        "hostname": "www.alice.test",
        "handle": "alice",
        "primary_url": settings.public_url.rstrip("/"),
    }
    # The page keeps its domain when the handle changes.
    client.put("/api/pages/me", headers=alice, json={"handle": "alice2"})
    lookup = client.get("/api/domains/lookup", params={"domain": "www.alice.test"})
    assert lookup.json()["handle"] == "alice2"

    assert client.delete("/api/domains/me", headers=alice).status_code == 204
    assert client.get("/api/domains/me", headers=alice).status_code == 404
    assert client.get("/api/domains/lookup", params={"domain": "www.alice.test"}).status_code == 404


@pytest.mark.parametrize(
    "hostname",
    ["localhost", "203.0.113.5", "-bad-.test", "a..b.test", "x.123", "navi.example.net",
     "www.example.net", "a" * 64 + ".test", "exa mple.com"],
)
def test_rejects_bad_hostnames(client, alice, fake_dns, hostname):
    make_page(client, alice, "alice")
    resp = client.put("/api/domains/me", headers=alice, json={"hostname": hostname})
    assert resp.status_code == 422, resp.text


def test_unicode_hostname_is_punycoded(client, alice, fake_dns):
    make_page(client, alice, "alice")
    resp = client.put("/api/domains/me", headers=alice, json={"hostname": "bücher.test"})
    assert resp.json()["hostname"] == "xn--bcher-kva.test"


def test_apex_domain_gets_a_records(client, alice, fake_dns, monkeypatch):
    monkeypatch.setattr(settings, "custom_domain_ips", f"{NAVI_IP}")
    make_page(client, alice, "alice")
    domain = client.put("/api/domains/me", headers=alice, json={"hostname": "alice.test"}).json()
    assert [(r["type"], r["value"]) for r in domain["records"][1:]] == [("A", NAVI_IP)]
    fake_dns.publish(domain)
    assert client.post("/api/domains/me/verify", headers=alice).json()["status"] == "active"


def test_claims_are_not_exclusive_until_verified(client, alice, bob, fake_dns):
    make_page(client, alice, "alice")
    make_page(client, bob, "bob")
    # Bob claims Alice's domain first, but can't prove it.
    bobs = client.put("/api/domains/me", headers=bob, json={"hostname": "www.alice.test"}).json()
    alices = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    assert alices.status_code == 201
    fake_dns.publish(alices.json())
    assert client.post("/api/domains/me/verify", headers=alice).json()["status"] == "active"

    # Bob's token isn't published; and even if it were, the domain is taken now.
    fake_dns.publish(bobs)
    resp = client.post("/api/domains/me/verify", headers=bob).json()
    assert resp["status"] == "pending"
    assert resp["last_error"] == domain_service.IN_USE
    # Bob's existing claim stays (and stays pending); a fresh claim is refused.
    resp = client.put("/api/domains/me", headers=bob, json={"hostname": "www.alice.test."})
    assert resp.status_code == 200
    client.delete("/api/domains/me", headers=bob)
    resp = client.put("/api/domains/me", headers=bob, json={"hostname": "www.alice.test"})
    assert resp.status_code == 409


def test_new_claim_of_verified_domain_conflicts(client, alice, bob, fake_dns):
    make_page(client, alice, "alice")
    make_page(client, bob, "bob")
    domain = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    fake_dns.publish(domain.json())
    client.post("/api/domains/me/verify", headers=alice)
    resp = client.put("/api/domains/me", headers=bob, json={"hostname": "www.alice.test"})
    assert resp.status_code == 409


def test_deleting_page_deletes_domain(client, alice, fake_dns):
    make_page(client, alice, "alice")
    domain = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    fake_dns.publish(domain.json())
    client.post("/api/domains/me/verify", headers=alice)
    assert client.delete("/api/pages/me", headers=alice).status_code == 204
    assert client.get("/api/domains/lookup", params={"domain": "www.alice.test"}).status_code == 404
    assert asyncio.run(_count_domains()) == 0


async def _count_domains() -> int:
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count()).select_from(CustomDomain))).scalar_one()


async def _age_checks(delta: timedelta) -> None:
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(CustomDomain).values(last_checked_at=datetime.now(UTC) - delta)
        )
        await db.commit()


async def _recheck() -> int:
    async with AsyncSessionLocal() as db:
        return await domain_service.recheck_due(db)


async def _active() -> list[str]:
    async with AsyncSessionLocal() as db:
        return await domain_service.active_hostnames(db)


def test_recheck_verifies_pending_and_retires_lapsed(client, alice, fake_dns):
    make_page(client, alice, "alice")
    domain = client.put("/api/domains/me", headers=alice, json={"hostname": "www.alice.test"})
    assert asyncio.run(_recheck()) == 1  # never checked: due
    assert asyncio.run(_recheck()) == 0  # just checked: not due
    fake_dns.publish(domain.json())
    asyncio.run(_age_checks(timedelta(minutes=10)))
    assert asyncio.run(_recheck()) == 1
    assert asyncio.run(_active()) == ["www.alice.test"]

    # Verified domains are re-checked every few hours, not every run.
    asyncio.run(_age_checks(timedelta(minutes=10)))
    assert asyncio.run(_recheck()) == 0

    # The records disappear: a few failures in a row switch the domain off.
    fake_dns.fail = True
    for _ in range(domain_service.MAX_FAILURES - 1):
        asyncio.run(_age_checks(timedelta(hours=7)))
        assert asyncio.run(_recheck()) == 1
        assert asyncio.run(_active()) == ["www.alice.test"]
    asyncio.run(_age_checks(timedelta(hours=7)))
    asyncio.run(_recheck())
    assert asyncio.run(_active()) == []
    mine = client.get("/api/domains/me", headers=alice).json()
    assert mine["status"] == "pending"
    assert mine["last_error"].startswith("Switched off")


# --- Kubernetes sync ---------------------------------------------------------------

CFG = domain_sync.SyncSettings(
    NAVI_SYNC_INSTANCE="navi",
    NAVI_SYNC_INGRESS_CLASS="traefik",
    NAVI_SYNC_INGRESS_ANNOTATIONS=json.dumps({"cert-manager.io/cluster-issuer": "le-http01"}),
    NAVI_SYNC_BACKEND_SERVICE="navi-backend",
    NAVI_SYNC_FRONTEND_SERVICE="navi-frontend",
)


def test_build_ingress():
    ing = domain_sync.build_ingress(CFG, "www.alice.test")
    meta = ing["metadata"]
    assert meta["name"].startswith("navi-domain-") and len(meta["name"]) == len("navi-domain-") + 12
    assert meta["labels"][domain_sync.DOMAIN_LABEL] == "true"
    assert meta["annotations"]["cert-manager.io/cluster-issuer"] == "le-http01"
    assert meta["annotations"][domain_sync.HOST_ANNOTATION] == "www.alice.test"
    assert ing["spec"]["ingressClassName"] == "traefik"
    tls = [{"hosts": ["www.alice.test"], "secretName": meta["name"] + "-tls"}]
    assert ing["spec"]["tls"] == tls
    rule_paths = ing["spec"]["rules"][0]["http"]["paths"]
    paths = {p["path"]: p["backend"]["service"]["name"] for p in rule_paths}
    assert paths == {
        "/api/pages": "navi-backend",
        "/api/domains/lookup": "navi-backend",
        "/": "navi-frontend",
    }


def test_reconcile_creates_updates_and_deletes():
    store: dict[str, dict] = {}
    stale = domain_sync.build_ingress(CFG, "old.example.org")
    store[stale["metadata"]["name"]] = stale
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[-1]
        calls.append((request.method, name))
        if request.method == "GET":
            assert "managed-by=navi-domain-sync" in request.url.params["labelSelector"]
            return httpx.Response(200, json={"items": list(store.values())})
        if request.method == "PATCH":
            assert request.headers["content-type"] == "application/apply-patch+yaml"
            store[name] = json.loads(request.content)
            return httpx.Response(200, json=store[name])
        if request.method == "DELETE":
            store.pop(name, None)
            return httpx.Response(200, json={})
        return httpx.Response(405)

    async def run(hosts: list[str]) -> dict:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://k8s")
        async with client:
            kube = domain_sync.KubeIngresses(client, "navi-prod")
            return await domain_sync.reconcile(kube, CFG, hosts)

    changes = asyncio.run(run(["www.alice.test", "bob.test"]))
    assert sorted(changes["applied"]) == ["bob.test", "www.alice.test"]
    assert changes["deleted"] == ["old.example.org"]
    assert len(store) == 2

    # Nothing changed: no writes.
    calls.clear()
    assert asyncio.run(run(["www.alice.test", "bob.test"])) == {"applied": [], "deleted": []}
    assert [m for m, _ in calls] == ["GET"]
