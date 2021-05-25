#!/usr/bin/env python3

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from dateutil import rrule

import requests
from fake_useragent import UserAgent

LOG = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(process)s - %(levelname)s - %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
LOG.addHandler(sh)

BASE_URL = "https://www.recreation.gov"
AVAILABILITY_ENDPOINT = "/api/ticket/availability/facility/"
MAIN_PAGE_ENDPOINT = "/api/ticket/tour/"

INPUT_DATE_FORMAT = "%Y-%m-%d"

headers = {"User-Agent": UserAgent().random}

def send_request(url, params):
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            "failedRequest",
            "ERROR, {} code received from {}: {}".format(
                resp.status_code, url, resp.text
            ),
        )
    return resp.json()

def get_tour_availabilities(facility_id, tour_ids, start_date, end_date):
    """
    This function consumes the user intent, collects the necessary information
    from the recreation.gov API, and then presents it in a nice format for the
    rest of the program to work with. If the API changes in the future, this is
    the only function you should need to change.

    The only API to get availability information is the `monthlyAvailabilitySummaryView?` query
    on the availability endpoint.  This means if `start_date` and `end_date` cross a month
    boundary, we must hit the endpoint multiple times.

    The output of this function looks like this:

    {"<tour_id>": ["YYYY-MM-DD", "YYYY-MM-DD", ...]}

    Where the values are a list of date objects representing dates
    where the tour is available.
    """

    # Get each first of the month for months in the range we care about.
    start_of_month = datetime(start_date.year, start_date.month, 1)
    months = list(rrule.rrule(rrule.MONTHLY, dtstart=start_of_month, until=end_date))

    # Get data for each month.
    api_data = {}
    for month_date in months:
        params = {
            "year": month_date.year,
            "month": month_date.month,
            "inventoryBucket": "FIT"
        }
        LOG.debug("Querying for facility {} with these params: {}".format(facility_id, params))
        url = "{}{}{}/monthlyAvailabilitySummaryView?".format(BASE_URL, AVAILABILITY_ENDPOINT, facility_id)
        resp = send_request(url, params)
        api_data.update(resp["facility_availability_summary_view_by_local_date"])

    desired_dates = [start_date+timedelta(days=x) for x in range((end_date-start_date+timedelta(days=1)).days)]
    # Collapse the data into the described output format.
    # Filter by campsite_type if necessary.
    availabilities = {}
    for tour_id in tour_ids:
        availabilities[tour_id] = []
        for date in desired_dates:
            date_formatted = datetime.strftime(date, INPUT_DATE_FORMAT)
            if str(tour_id) not in api_data[date_formatted]["tour_availability_summary_view_by_tour_id"]:
                print("Tour id {} not found in facility with id {} on {}".format(tour_id, facility_id, date_formatted))
            elif api_data[date_formatted]["tour_availability_summary_view_by_tour_id"
                    ][str(tour_id)]["has_reservable"]:
                availabilities[tour_id].append(date_formatted)

    return availabilities

def get_tour_name(tour_id):
    url = "{}{}{}".format(BASE_URL, MAIN_PAGE_ENDPOINT, tour_id)
    resp = send_request(url, {})
    return resp["tour_name"]

def print_human_readable(availabilities):
    for tour_id, dates in availabilities.items():
        tour_name = get_tour_name(tour_id)
        if not dates:
            print("{}: No availabilities :(".format(tour_name))
        else:
            print("{}: Available on the following date(s):\n{}".format(tour_name,
            ", ".join(dates)))

def main(facility, tours, start_date, end_date):
    availabilities = get_tour_availabilities(facility, tours, start_date, end_date)
    LOG.debug(
            "Availabilities for tours: {}".format(
            json.dumps(availabilities, indent=2)
        )
    )
    print_human_readable(availabilities)
    if any(availabilities.values()):
        return 0
    else:
        return 1


def valid_date(s):
    try:
        return datetime.strptime(s, INPUT_DATE_FORMAT)
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", action="store_true", help="Debug log level")
    parser.add_argument(
        "--start-date", required=True, help="Start date [YYYY-MM-DD]", type=valid_date
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date [YYYY-MM-DD].",
        type=valid_date,
    )
    parser.add_argument(
        "--facility",
        help="Facility ID of the desired tours.",
        type=int,
    )
    parser.add_argument(
        "--tours", dest="tours", metavar="tour", nargs="+", help="Tour ID(s)", type=int
    )

    args = parser.parse_args()

    if args.debug:
        LOG.setLevel(logging.DEBUG)
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True


    try:
        code = main(args.facility, args.tours, args.start_date, args.end_date)
        sys.exit(code)
    except Exception:
        print("Something went wrong")
        LOG.exception("Something went wrong")
        raise
