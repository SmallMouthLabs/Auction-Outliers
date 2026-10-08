"""OPTIONAL, OFF BY DEFAULT: adapter for the unofficial ShopGoodwill buyer API endpoints documented by the
GPL-3.0 project scottmconway/shopgoodwill-scripts (search + item detail only; no login, no bidding).

ShopGoodwill's Terms of Use restrict automated access. This adapter exists so that an *authorized* user
(for example after obtaining permission from ShopGoodwill, or for occasional single-item refreshes) can plug
it in without changing the rest of the system. It is disabled unless OUTLIER_ENABLE_UNOFFICIAL_SGW_API=true.
It identifies itself honestly, is rate limited, and never spoofs a browser or automates an account.
The endpoint shapes are based on the reference project and could not be verified from this environment.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from ..config import get_settings
from ..services.listings import ListingIn
from .common import parse_datetime

API_ROOT = "https://buyerapi.shopgoodwill.com/api"
_lock = threading.Lock()
_last_call = 0.0

DEFAULT_QUERY = {
    "isSize": False, "isWeddingCatagory": "false", "isMultipleCategoryIds": False, "isFromHeaderMenuTab": False,
    "layout": "", "searchText": "", "selectedGroup": "", "selectedCategoryIds": "", "selectedSellerIds": "",
    "lowPrice": "0", "highPrice": "999999", "searchBuyNowOnly": "", "searchPickupOnly": "false", "searchNoPickupOnly": "false",
    "searchOneCentShippingOnly": "false", "searchDescriptions": "false", "searchClosedAuctions": "false",
    "closedAuctionEndingDate": "1/1/1", "closedAuctionDaysBack": "7", "searchCanadaShipping": "false",
    "searchInternationalShippingOnly": "false", "sortColumn": "1", "sortDescending": "false", "savedSearchId": 0,
    "useBuyerPrefs": "true", "searchUSOnlyShipping": "false", "categoryLevelNo": "1", "categoryLevel": 1, "categoryId": 0,
    "partNumber": "", "catIds": "", "page": 1, "pageSize": 40,
}


class UnofficialDisabled(RuntimeError):
    pass


def _ensure_enabled() -> None:
    if not get_settings().enable_unofficial_sgw_api:
        raise UnofficialDisabled(
            "The unofficial ShopGoodwill adapter is disabled. Read docs/research.md (terms of use) and set "
            "OUTLIER_ENABLE_UNOFFICIAL_SGW_API=true only if you are authorized to use it."
        )


def _throttle() -> None:
    global _last_call
    s = get_settings()
    with _lock:
        wait = s.sgw_min_request_interval_seconds - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()


def _client() -> httpx.Client:
    return httpx.Client(timeout=30, headers={"User-Agent": get_settings().sgw_user_agent, "Accept": "application/json"})


def item_to_listing(d: dict[str, Any]) -> ListingIn:
    item_id = str(d.get("itemId") or d.get("id") or "")
    imgs = []
    for k in ("imageUrlString", "imageURL", "imageUrl"):
        v = d.get(k)
        if isinstance(v, str):
            imgs += [u for u in v.split(";") if u.startswith("http")]
    for im in d.get("imageServer") or []:
        if isinstance(im, dict) and im.get("imageUrl"):
            imgs.append(im["imageUrl"])
    return ListingIn(
        source="sgw_unofficial", source_item_id=item_id or None, source_url=f"https://shopgoodwill.com/item/{item_id}" if item_id else None,
        extraction_method="unofficial_buyer_api", title=str(d.get("title") or "Untitled"), description=d.get("description"),
        category=d.get("categoryName") or d.get("categoryParentName"), seller=d.get("sellerName") or d.get("sellerDisplayName"),
        current_bid=d.get("currentPrice") or d.get("price"), num_bids=d.get("numberOfBids") or d.get("numBids"),
        buy_now_price=d.get("buyNowPrice"), ends_at=parse_datetime(d.get("endTime") or d.get("remainingTime")),
        shipping_cost=d.get("shippingPrice"), handling_fee=d.get("handlingPrice"), condition_text=d.get("condition"),
        image_urls=imgs, raw={k: v for k, v in d.items() if isinstance(v, (str, int, float, bool)) or v is None},
    )


def get_item(item_id: int) -> ListingIn:
    _ensure_enabled()
    _throttle()
    with _client() as c:
        r = c.get(f"{API_ROOT}/itemDetail/GetItemDetailModelByItemId/{item_id}")
        r.raise_for_status()
        return item_to_listing(r.json())


def search(search_text: str, *, category_ids: str = "", max_pages: int = 2) -> list[ListingIn]:
    _ensure_enabled()
    out: list[ListingIn] = []
    q = {**DEFAULT_QUERY, "searchText": search_text.replace('"', ""), "selectedCategoryIds": category_ids}
    with _client() as c:
        for page in range(1, max_pages + 1):
            _throttle()
            q["page"] = page
            r = c.post(f"{API_ROOT}/Search/ItemListing", json=q)
            r.raise_for_status()
            js = r.json()
            items = (js.get("searchResults") or {}).get("items") or []
            if not items:
                break
            out += [item_to_listing(i) for i in items]
            if len(out) >= int((js.get("searchResults") or {}).get("itemCount") or 0):
                break
    return out
