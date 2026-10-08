"""Pluggable sold-data providers.

Status (2026-10):
- manual / CSV / JSON import: WORKING (see ingestion/comps_import.py).
- eBay Marketplace Insights API (official sold data, 90-day lookback): LIMITED RELEASE; requires eBay approval.
  Interface implemented; activates when EBAY_CLIENT_ID/SECRET are set and your keyset has been granted access.
- eBay Browse API (ACTIVE listings only): available to any eBay developer account. Results are imported as
  comp_type='active' and NEVER feed the valuation.
"""
from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from ..config import get_secrets
from ..ingestion.comps_import import CompIn

log = logging.getLogger(__name__)


class SoldDataProvider:
    name = "base"
    sold_data = False

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def search(self, query: str, limit: int = 20) -> list[CompIn]:
        raise NotImplementedError


class EbayBase(SoldDataProvider):
    token_url = "https://api.ebay.com/identity/v1/oauth2/token"

    def _token(self, scope: str) -> str:
        s = get_secrets()
        if not (s.ebay_client_id and s.ebay_client_secret):
            raise RuntimeError("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET not set")
        auth = base64.b64encode(f"{s.ebay_client_id}:{s.ebay_client_secret}".encode()).decode()
        r = httpx.post(self.token_url, headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
                       data={"grant_type": "client_credentials", "scope": scope}, timeout=20)
        r.raise_for_status()
        return r.json()["access_token"]


class EbayMarketplaceInsights(EbayBase):
    name = "ebay_marketplace_insights"
    sold_data = True

    def available(self) -> tuple[bool, str]:
        s = get_secrets()
        if not (s.ebay_client_id and s.ebay_client_secret):
            return False, "requires EBAY_CLIENT_ID/EBAY_CLIENT_SECRET and eBay approval for the Marketplace Insights API (limited release)"
        return True, "credentials present; access depends on eBay approval"

    def search(self, query: str, limit: int = 20) -> list[CompIn]:
        token = self._token("https://api.ebay.com/oauth/api_scope/buy.marketplace.insights")
        r = httpx.get("https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search",
                      params={"q": query, "limit": limit}, headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}, timeout=30)
        if r.status_code in (401, 403):
            raise RuntimeError("eBay rejected the request: your keyset is not approved for Marketplace Insights.")
        r.raise_for_status()
        out = []
        for it in r.json().get("itemSales", []):
            price = (it.get("lastSoldPrice") or {}).get("value")
            out.append(CompIn(
                title=it.get("title", "")[:500], marketplace="ebay", url=it.get("itemWebUrl"), sold_date=it.get("lastSoldDate"),
                price=float(price) if price else None, is_sold=True, comp_type="category", similarity=0.5,
                evidence_quality="medium", condition=it.get("condition"), source="provider:ebay_marketplace_insights",
            ))
        return out


class EbayBrowseActive(EbayBase):
    name = "ebay_browse_active"
    sold_data = False

    def available(self) -> tuple[bool, str]:
        s = get_secrets()
        if not (s.ebay_client_id and s.ebay_client_secret):
            return False, "requires EBAY_CLIENT_ID/EBAY_CLIENT_SECRET (any eBay developer account)"
        return True, "active listings only (asking prices); never used for valuation"

    def search(self, query: str, limit: int = 20) -> list[CompIn]:
        token = self._token("https://api.ebay.com/oauth/api_scope")
        r = httpx.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params={"q": query, "limit": limit},
                      headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}, timeout=30)
        r.raise_for_status()
        out = []
        for it in r.json().get("itemSummaries", []):
            price = (it.get("price") or {}).get("value")
            out.append(CompIn(
                title=it.get("title", "")[:500], marketplace="ebay", url=it.get("itemWebUrl"), price=float(price) if price else None,
                is_sold=False, comp_type="active", similarity=0.4, evidence_quality="low", condition=it.get("condition"),
                source="provider:ebay_browse_active",
            ))
        return out


PROVIDERS: dict[str, SoldDataProvider] = {p.name: p for p in (EbayMarketplaceInsights(), EbayBrowseActive())}


def provider_status() -> list[dict[str, Any]]:
    out = [{"name": "manual_entry", "sold_data": True, "available": True, "note": "manual / CSV / JSON comparable entry (always on)"}]
    for p in PROVIDERS.values():
        ok, note = p.available()
        out.append({"name": p.name, "sold_data": p.sold_data, "available": ok, "note": note})
    return out
