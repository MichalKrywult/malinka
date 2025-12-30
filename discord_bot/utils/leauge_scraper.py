import aiohttp
from bs4 import BeautifulSoup

# Nagłówki, żeby OP.GG nie blokowało
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

async def fetch_rank_data(session: aiohttp.ClientSession,nick_tag: str):
    """Zwraca słownik z danymi o randze lub None w przypadku błędu."""
    name_tag = nick_tag.replace("#", "-")
    url = f"https://www.op.gg/lol/summoners/eune/{name_tag}"

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Logika wyciągania rangi 
            lp_span = None
            for s in soup.find_all("span"):
                if "LP" in s.get_text():
                    lp_span = s
                    break
            
            if not lp_span:
                return {"found": False}

            lp_text = lp_span.get_text(strip=True)
            parent_div = lp_span.find_parent("div")
            tier_text = "RANKED"
            if parent_div:
                tier_el = parent_div.find("strong")
                if tier_el:
                    tier_text = tier_el.get_text(strip=True)
            
            # Pobieranie obrazka rangi
            img_url = None
            for img in soup.find_all("img"):
                src = img.get('src')
                # Sprawdzamy, czy src istnieje i czy na pewno jest ciągiem znaków (str)
                if src and isinstance(src, str) and "medals_new" in src:
                    img_url = src if src.startswith('http') else f"https:{src}"
                    break

            return {
                "found": True,
                "tier": tier_text,
                "lp": lp_text,
                "img_url": img_url,
                "nick": nick_tag
            }

async def fetch_mastery_data(session: aiohttp.ClientSession,nick_tag: str):
    """Zwraca listę top mastery."""
    name_tag = nick_tag.replace("#", "-")
    url = f"https://www.op.gg/lol/summoners/eune/{name_tag}/mastery"

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            containers = soup.find_all("div", attrs={"data-tooltip-id": "opgg-tooltip"})
            
            results = []
            for container in containers:
                if len(results) >= 3:
                    break
                
                name_el = container.find("span", class_="text-gray-900")
                if not name_el: 
                    continue
                
                name = name_el.get_text(strip=True)
                if "Link" in name or "Total" in name: 
                    continue
                
                points_el = container.find("span", class_="text-gray-500")
                level_el = container.find("span", class_="text-2xs")
                
                pts = points_el.get_text(strip=True).replace('\xa0', ' ') if points_el else "?"
                lvl = level_el.get_text(strip=True) if level_el else "?"
                
                results.append(f"**{name}** (Lvl {lvl}) — `{pts} pkt`")
                
            return results