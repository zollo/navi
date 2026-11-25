"""Custom domain sync: `python -m app.domain_sync` (the chart runs it as a CronJob).

One pass:
1. Checks DNS for pending domains and re-checks verified ones
   (domain_service.recheck_due).
2. In Kubernetes, makes one Ingress per verified domain (TLS from cert-manager via
   the Ingress annotations, typically an HTTP-01 issuer) and deletes Ingresses of
   domains that are gone or no longer verified.

Each custom-domain Ingress only routes what a public page needs: the SPA, its
assets, `/api/pages/*`, `/api/backgrounds/*` and `/api/domains/lookup` (the rest of /api goes to the
SPA's nginx and fails there). Sign-in and editing stay on Navi's own hostname.

The Kubernetes part talks to the API server with the pod's service account
(Role: ingresses in its own namespace) and is skipped outside a cluster or when
NAVI_SYNC_INGRESSES=false.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx2
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db import AsyncSessionLocal
from app.services import domain_service

log = logging.getLogger("navi.domain_sync")

SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")
MANAGED_BY = "navi-domain-sync"
# On every Ingress this job creates; cluster policies can key on it.
DOMAIN_LABEL = "navi.zollo.net/custom-domain"
HOST_ANNOTATION = "navi.zollo.net/hostname"
HASH_ANNOTATION = "navi.zollo.net/spec-hash"
# Not app.kubernetes.io/instance: GitOps tools (Argo CD label tracking) treat that
# label as "part of my app" and would prune Ingresses they didn't render.
INSTANCE_LABEL = "navi.zollo.net/instance"


class SyncSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    manage_ingresses: bool = Field(default=True, alias="NAVI_SYNC_INGRESSES")
    # Release fullname: prefix of the Ingress names and value of INSTANCE_LABEL.
    instance: str = Field(default="navi", alias="NAVI_SYNC_INSTANCE")
    namespace: str = Field(default="", alias="NAVI_SYNC_NAMESPACE")
    ingress_class: str = Field(default="", alias="NAVI_SYNC_INGRESS_CLASS")
    # JSON objects.
    annotations: str = Field(default="{}", alias="NAVI_SYNC_INGRESS_ANNOTATIONS")
    labels: str = Field(default="{}", alias="NAVI_SYNC_INGRESS_LABELS")
    tls: bool = Field(default=True, alias="NAVI_SYNC_TLS")
    backend_service: str = Field(default="navi-backend", alias="NAVI_SYNC_BACKEND_SERVICE")
    frontend_service: str = Field(default="navi-frontend", alias="NAVI_SYNC_FRONTEND_SERVICE")


def ingress_name(instance: str, hostname: str) -> str:
    return f"{instance}-domain-{hashlib.sha256(hostname.encode()).hexdigest()[:12]}"


def _backend(service: str) -> dict[str, Any]:
    return {"service": {"name": service, "port": {"name": "http"}}}


def build_ingress(cfg: SyncSettings, hostname: str) -> dict[str, Any]:
    """The Ingress for one verified custom domain."""
    name = ingress_name(cfg.instance, hostname)
    paths = [
        {"path": "/api/pages", "pathType": "Prefix", "backend": _backend(cfg.backend_service)},
        # Curated background images (GET /api/backgrounds/{id}/image).
        {
            "path": "/api/backgrounds",
            "pathType": "Prefix",
            "backend": _backend(cfg.backend_service),
        },
        {
            "path": "/api/domains/lookup",
            "pathType": "Exact",
            "backend": _backend(cfg.backend_service),
        },
        {"path": "/", "pathType": "Prefix", "backend": _backend(cfg.frontend_service)},
    ]
    spec: dict[str, Any] = {"rules": [{"host": hostname, "http": {"paths": paths}}]}
    if cfg.ingress_class:
        spec["ingressClassName"] = cfg.ingress_class
    if cfg.tls:
        spec["tls"] = [{"hosts": [hostname], "secretName": f"{name}-tls"}]
    annotations = {str(k): str(v) for k, v in json.loads(cfg.annotations or "{}").items()}
    labels = {str(k): str(v) for k, v in json.loads(cfg.labels or "{}").items()}
    labels.update(
        {
            "app.kubernetes.io/name": "navi",
            INSTANCE_LABEL: cfg.instance,
            "app.kubernetes.io/component": "custom-domain",
            "app.kubernetes.io/managed-by": MANAGED_BY,
            DOMAIN_LABEL: "true",
        }
    )
    spec_hash = hashlib.sha256(
        json.dumps([spec, annotations, labels], sort_keys=True).encode()
    ).hexdigest()[:16]
    annotations.update({HOST_ANNOTATION: hostname, HASH_ANNOTATION: spec_hash})
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": name, "labels": labels, "annotations": annotations},
        "spec": spec,
    }


class KubeIngresses:
    """The few Ingress calls the sync needs, against the in-cluster API server."""

    def __init__(self, client: httpx2.AsyncClient, namespace: str):
        self.client = client
        self.base = f"/apis/networking.k8s.io/v1/namespaces/{namespace}/ingresses"

    @classmethod
    def in_cluster(cls, namespace: str) -> KubeIngresses:
        host = os.environ["KUBERNETES_SERVICE_HOST"]
        port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        if ":" in host:
            host = f"[{host}]"
        token = (SA_DIR / "token").read_text().strip()
        client = httpx2.AsyncClient(
            base_url=f"https://{host}:{port}",
            headers={"Authorization": f"Bearer {token}"},
            verify=str(SA_DIR / "ca.crt"),
            timeout=15,
        )
        return cls(client, namespace)

    async def list(self, selector: str) -> list[dict[str, Any]]:
        resp = await self.client.get(self.base, params={"labelSelector": selector})
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def apply(self, ingress: dict[str, Any]) -> None:
        resp = await self.client.patch(
            f"{self.base}/{ingress['metadata']['name']}",
            params={"fieldManager": MANAGED_BY, "force": "true"},
            content=json.dumps(ingress),
            headers={"Content-Type": "application/apply-patch+yaml"},
        )
        resp.raise_for_status()

    async def delete(self, name: str) -> None:
        resp = await self.client.delete(f"{self.base}/{name}")
        if resp.status_code != 404:
            resp.raise_for_status()


async def reconcile(kube: KubeIngresses, cfg: SyncSettings, hostnames: list[str]) -> dict:
    """Make the custom-domain Ingresses match `hostnames`. Returns what changed."""
    selector = f"app.kubernetes.io/managed-by={MANAGED_BY},{INSTANCE_LABEL}={cfg.instance}"
    existing = {i["metadata"]["name"]: i for i in await kube.list(selector)}
    desired = {ingress_name(cfg.instance, h): build_ingress(cfg, h) for h in hostnames}
    applied, deleted = [], []
    for name, ingress in desired.items():
        current = existing.get(name, {}).get("metadata", {}).get("annotations", {})
        if current.get(HASH_ANNOTATION) != ingress["metadata"]["annotations"][HASH_ANNOTATION]:
            await kube.apply(ingress)
            applied.append(ingress["metadata"]["annotations"][HOST_ANNOTATION])
    for name, ingress in existing.items():
        if name not in desired:
            await kube.delete(name)
            deleted.append(ingress["metadata"].get("annotations", {}).get(HOST_ANNOTATION, name))
    return {"applied": applied, "deleted": deleted}


def _namespace(cfg: SyncSettings) -> str:
    if cfg.namespace:
        return cfg.namespace
    return (SA_DIR / "namespace").read_text().strip()


async def run_once() -> None:
    cfg = SyncSettings()
    async with AsyncSessionLocal() as db:
        checked = await domain_service.recheck_due(db)
        hostnames = await domain_service.active_hostnames(db)
    log.info("Checked %d domain(s); %d verified", checked, len(hostnames))

    if not cfg.manage_ingresses:
        return
    if "KUBERNETES_SERVICE_HOST" not in os.environ:
        log.info("Not in Kubernetes; skipping Ingresses")
        return
    kube = KubeIngresses.in_cluster(_namespace(cfg))
    async with kube.client:
        changes = await reconcile(kube, cfg, hostnames)
    log.info(
        "Ingresses applied: %s; deleted: %s", changes["applied"] or "-", changes["deleted"] or "-"
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(run_once())
    except httpx2.HTTPStatusError as exc:
        log.error("Kubernetes API: %s %s", exc.response.status_code, exc.response.text[:500])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
