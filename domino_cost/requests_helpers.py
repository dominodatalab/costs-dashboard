import logging
from typing import List

import requests

from domino_cost import config
from domino_cost.exceptions import TokenExpiredException

logger = logging.getLogger(__name__)


def get_token(auth_url: str) -> str:
    orgs_res = requests.get(auth_url)
    token = orgs_res.content.decode("utf-8")
    if token == "<ANONYMOUS>":
        raise TokenExpiredException("Your token has expired. Please redeploy your Domino Cost App.")
    return token


def get_cloud_cost_sum(selection: str, base_url: str, headers: dict) -> float:
    cloud_cost_url = f"{base_url}/cloudCost"

    parameters = {"window": selection, "aggregate": "invoiceEntityID"}

    cloud_cost_sum = 0

    try:
        response = requests.request("GET", cloud_cost_url, headers=headers, params=parameters)
        response.raise_for_status()

        cost_amortized = response.json()["data"]["sets"]
        invoice_entity_id = list(cost_amortized[0]["cloudCosts"].keys())[0]

        for cost in cost_amortized:
            if cost["cloudCosts"]:
                cloud_cost_sum += cost["cloudCosts"][invoice_entity_id]["amortizedNetCost"]["cost"]

        logger.info(f"cloud cost available: {cloud_cost_sum}")
        config.cloud_cost_available = True
        logger.info("setting cloud cost availability: %s", config.cloud_cost_available)
    except Exception as e:  # handle for users without cloud cost, or no data from cloudCost
        config.cloud_cost_available = False
        logger.warning("could not acquire cloud cost - not configured or no data to retrieve")
        logger.warning("setting cloud cost availability: %s", config.cloud_cost_available)
        logger.debug("exception received when trying to obtain cloud costs: %s", e)

    config.default_is_updated = True
    return cloud_cost_sum


def get_aggregated_allocations(selection: str, base_url: str, headers: dict) -> List:
    allocations_url = f"{base_url}/allocation"

    params = {
        "window": selection,
        "aggregate": (
            "label:dominodatalab.com/workload-type,"
            "label:dominodatalab.com/project-id,"
            "label:dominodatalab.com/project-name,"
            "label:dominodatalab.com/starting-user-username,"
            "label:dominodatalab.com/organization-name,"
            "label:dominodatalab.com/billing-tag,"
        ),
        "accumulate": False,
        "shareIdle": True,
        "shareTenancyCosts": True,
        "shareSplit": "weighted",
    }

    res = requests.get(allocations_url, params=params, headers=headers)

    res.raise_for_status()
    alloc_data = res.json()["data"]

    return alloc_data
