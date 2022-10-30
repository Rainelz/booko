import time
from collections import defaultdict

import requests
from datetime import date, timedelta, datetime, timezone
from math import sin, cos, sqrt, atan2, radians
from zoneinfo import ZoneInfo


DEFAULT_ADDR = "piazza duomo Milan"
MAX_DISTANCE = 10
MAX_PRICE = 30
MILAN_COORDS = (45.463910150000004, 9.190642626255652)
# approximate radius of earth in km
R = 6373.0


localtz = ZoneInfo("Europe/Rome")


def calc_distance(point_a: tuple[float, float], point_b: tuple[float, float]):
    lat1 = radians(point_a[0])
    lon1 = radians(point_a[1])
    lat2 = radians(point_b[0])
    lon2 = radians(point_b[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


def get_home_coords(
    address,
) -> tuple[float, float]:
    api_url = "https://nominatim.openstreetmap.org/search?q={query}&format=json"
    if not address:
        address = input(f"Insert your address. (Defaults to: {DEFAULT_ADDR}): ")
        print()
        if not address:
            address = DEFAULT_ADDR

    query_str = address.replace(" ", "+")
    res = requests.get(api_url.format(query=query_str))
    addresses = res.json()
    if not addresses:
        print("didn't find address")
        exit(1)
    if len(addresses) > 1:
        print(f"Found more than 1 result, going for:{addresses[0]['display_name']}")

    coords = float(addresses[0]["lat"]), float(addresses[0]["lon"])
    return coords


def get_tenants(
    home_coords: tuple[float, float], field_names: list|None, max_distance
) -> list:
    lat, lon = home_coords
    tenants_query = "https://playtomic.io/api/v1/tenants?user_id=me&playtomic_status=ACTIVE&with_properties=ALLOWS_CASH_PAYMENT&coordinate={latitude}%2C{longitude}&sport_id=TENNIS&radius=50000&size=100"
    res = requests.get(tenants_query.format(latitude=lat, longitude=lon))
    tenants = res.json()
    filtered_tenants = []
    if field_names:
        tenants = filter(
            lambda x: any(
                field_name.lower() in x["tenant_name"].lower()
                for field_name in field_names
            ),
            tenants,
        )

    for tenant in tenants:
        coords = (
            tenant["address"]["coordinate"]["lat"],
            tenant["address"]["coordinate"]["lon"],
        )
        distance_from_home = calc_distance(coords, home_coords)

        if distance_from_home <= max_distance:
            tenant.update(distance=distance_from_home)
            filtered_tenants.append(tenant)

    filtered_tenants.sort(key=lambda x: x["distance"])
    return filtered_tenants


def get_date_range():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    return [today.isoformat(), tomorrow.isoformat()]


def get_fields_for_tenant(tenant, date: date, start_hour: str):
    api_url = f"https://playtomic.io/api/v1/availability?user_id=me&tenant_id={tenant['tenant_id']}&sport_id=TENNIS&local_start_min={date}T{start_hour}%3A00%3A00&local_start_max={date}T23%3A59%3A59"
    res = requests.get(api_url)
    fields = res.json()

    return fields


def filter_fields(fields, max_price):
    filtered_fields = []

    for field in fields:
        filtered_slots = list(
            filter(
                lambda x: float(x["price"].replace("EUR", "").strip()) <= max_price,
                field["slots"],
            )
        )
        if filtered_slots:
            filtered_fields.append({**field, "slots": filtered_slots})
    return filtered_fields


def get_fields_filtered(
    coords, field_names, max_distance, start_hour, max_price, dates
):
    found_fields = defaultdict(list)

    tenants = get_tenants(coords, field_names, max_distance)
    dates = dates
    for date in dates:
        for tenant in tenants:
            fields = get_fields_for_tenant(tenant, date, start_hour)
            filtered_fields = filter_fields(fields, max_price)
            if not filtered_fields:
                continue
            tenant_result = {
                k: tenant[k]
                for k in ["tenant_name", "tenant_id", "address", "distance"]
            }
            tenant_result["fields"] = []
            for field in filtered_fields:
                # python has no find :(
                field_info = next(
                    (
                        field_info
                        for field_info in tenant["resources"]
                        if field["resource_id"] == field_info["resource_id"]
                    ),
                    None,  # default value if not found
                )

                tenant_result["fields"].append({**field_info, **field})
                # for slot in field["slots"]:
                #     start_h = datetime.strptime(slot["start_time"], "%H:%M:%S")
                #     start_h = datetime.combine(
                #         date, start_h.time(), tzinfo=timezone.utc
                #     )
                #     start_h = start_h.astimezone(localtz)

            found_fields[date].append(tenant_result)
    return found_fields


def format_results(found_fields: dict[str, dict]):
    result_str = ""
    for date, tenants in found_fields.items():
        result_str += f"Found fields for date: {date}\n"
        for tenant in tenants:
            result_str += f"{tenant['tenant_name']}\n"

            for field in tenant["fields"]:
                result_str += f"\tSlots for {field['name']} - {field['properties']['resource_type']}\n"
                for slot in field["slots"]:
                    start_h = datetime.strptime(slot["start_time"], "%H:%M:%S")
                    start_h = datetime.combine(
                        date, start_h.time(), tzinfo=timezone.utc
                    )
                    start_h = start_h.astimezone(localtz)
                    result_str += f"\t\tat {start_h.strftime('%H:%M')} duration: {slot['duration']} mins PRICE: {slot['price']}\n"

        result_str+= "=======================================\n"
    return result_str

def main(args):
    # Use a breakpoint in the code line below to debug your script.
    if not args.field_names:
        coords = get_home_coords(args.address)
    else:
        coords = MILAN_COORDS
    tenants = get_tenants(coords, args.field_names, args.max_distance)
    dates = args.dates

    found_fields = get_fields_filtered(
        coords,
        args.field_names,
        args.max_distance,
        args.start_hour,
        args.max_price,
        args.dates,
    )
    result = format_results(found_fields)
    print(result)


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    import argparse

    today = date.today()
    parser = argparse.ArgumentParser(description="")

    def parse_date(string):
        print(string)
        return string

    parser.add_argument(
        "-c",
        "--max-distance",
        type=int,
        default=10,
        required=False,
        help="max distance from address and fields",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default=None,
        required=False,
        help="address to lookup for coordinates",
    )
    parser.add_argument(
        "-p",
        "--max-price",
        required=False,
        type=int,
        help="max price to filter fields",
        default=30,
    )

    parser.add_argument(
        "-n",
        "--field-names",
        required=False,
        nargs="+",
        default=[],
        help="[OPTIONAL] name of centers to look for (space separated list). ",
    )
    parser.add_argument(
        "-t",
        "--start-hour",
        type=str,
        default="00",
        help="min hour of day for slots [00-24]",
    )
    parser.add_argument(
        "-d",
        "--dates",
        type=lambda x: date.fromisoformat(
            f"{today.year}-{x.split('-')[1]}-{x.split('-')[0]}"
        ),
        required=False,
        nargs="+",
        default=[today, today + timedelta(days=1)],
        help="[OPTIONAL] days [DD-MM] to look for (space separated list). ",
    )

    options = parser.parse_args()
    main(options)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
