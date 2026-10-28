import json
import logging
from typing import Any, Dict

import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

HOST = "WOGZDTJ-SIGMAHEALTHCARE.snowflakecomputing.com"
HTTP_METHOD = "POST"
API_ENDPOINT = "/api/v2/databases/{database}/schemas/{schema}/agents"
CREATE_MODE = "ifNotExists"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _build_headers_and_query_params(jwt_auth_token: str):
    headers = {
        "Authorization": f"Bearer {jwt_auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
    }

    query_params = {"createMode": CREATE_MODE}

    return headers, query_params


def send_request(
    jwt_auth_token: str, request_payload: Dict[str, Any], database: str, schema: str
):
    try:
        headers, query_params = _build_headers_and_query_params(
            jwt_auth_token=jwt_auth_token
        )

        req_url = (
            f"https://{HOST}{API_ENDPOINT.format(database=database, schema=schema)}"
        )

        resp = requests.request(
            method=HTTP_METHOD,
            url=req_url,
            headers=headers,
            params=query_params,
            json=request_payload,
        )

        return json.loads(resp.content)

    except ConnectionError as e:
        logger.error(f"Encountered a connection error : {e}")
        raise
    except HTTPError as e:
        logger.error(f"Encountered a http error : {e}")
        raise
    except Timeout as e:
        logger.error(f"The request has timed out : {e}")
        raise
    except RequestException as e:
        logger.error(f"General request exception : {e}")
        raise
