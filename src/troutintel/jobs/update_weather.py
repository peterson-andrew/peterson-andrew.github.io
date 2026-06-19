import asyncio

import httpx

from troutintel.config import load_river_config
from troutintel.io import save_json
from troutintel.sources.nws import (
    get_weather_bundle,
    normalize_current_weather,
)


async def process_river(
    client: httpx.AsyncClient,
    river_name: str,
    river: dict,
) -> None:

    lat = river["noaa"].get("lat")
    lon = river["noaa"].get("lon")

    if lat is None or lon is None:

        print(
            f"Skipping {river_name}: no NOAA coordinates"
        )

        return

    weather_bundle = await get_weather_bundle(
        client=client,
        lat=lat,
        lon=lon,
    )

    weather = normalize_current_weather(
        weather_bundle
    )

    save_json(
        weather,
        f"data/weather/{river_name}.json",
    )

    print(
        f"Wrote {river_name} weather"
    )


async def main():

    rivers = load_river_config()

    async with httpx.AsyncClient(
        headers={
            "User-Agent": (
                "georgiatroutfishing.com, "
                "admin@georgiatroutfishing.com"
            )
        },
        timeout=20.0,
    ) as client:

        tasks = [
            process_river(
                client,
                river_name,
                river,
            )

            for river_name, river
            in rivers.items()
        ]

        await asyncio.gather(*tasks)


if __name__ == "__main__":

    asyncio.run(main())
