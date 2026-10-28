import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Union

import _snowflake  # type: ignore
import pandas as pd

# import requests
from snowflake.cortex import Complete
from snowflake.snowpark import Session
from snowflake.snowpark.exceptions import SnowparkClientException, SnowparkSQLException

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SEMANTIC_MODEL_TYPE_MAP = {"FILE": "semantic_model_file", "VIEW": "semantic_view"}


def run_sql(
    session: Session,  # db_name:str, schema_name:str,
    sql_text: str,
) -> Union[pd.DataFrame, None]:
    # session.use_database(db_name)
    # session.use_schema(schema_name)
    try:
        df = session.sql(
            sql_text.replace(";", "")
        ).to_pandas()  # .collect() # a list of Row()
        return df
    except SnowparkSQLException as e:
        print(f"ERROR: Snowflake SQL Exception occurred: {e.message}")
        print(f"Query ID: {e.sfqid}")
        return None
    except SnowparkClientException as e:
        print(f"ERROR: Snowpark Client Exception occurred: {e.message}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        return None


def return_sql_result(
    session: Session,
    # db_name:str, schema_name:str,
    sql_text: str,
) -> Union[Dict[str, Dict[str, str]], None]:
    df = run_sql(session, sql_text)
    if df is not None:
        js_data = df.to_json(orient="records")  # a list of dict
        return js_data
    else:
        return None


def cortex_analyst_gen_sql(  # account:str, token:str,
    question: str, semantic_model_type: str, semantic_model_loc: str, api_timeout=600
) -> str:
    API_ENDPOINT = "/api/v2/cortex/analyst/message"
    # URL = f"https://{account}.snowflakecomputing.com{API_ENDPOINT}"

    # headers={"Authorization": f"Bearer {token}"
    # ,"Content-Type": "application/json"
    # ,"Accept": "application/json"
    # ,"X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN"}

    question_to_sql = (
        question + " Provide SQL only without comments/explanations/summaries/charts."
    )
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question_to_sql}]}
        ],
        # ,"semantic_model_file": f"@{st.session_state.semantic_model_file_path}",
        SEMANTIC_MODEL_TYPE_MAP.get(semantic_model_type): semantic_model_loc,
    }

    resp = _snowflake.send_snow_api_request(
        "POST",  # method
        API_ENDPOINT,  # path
        {},  # headers
        {},  # params
        request_body,  # body
        None,  # request_guid
        api_timeout,  # timeout in milliseconds
    )
    # resp = requests.post(URL, headers=headers, json=request_body, timeout=api_timeout)

    if resp["status"] < 400:  # == 200:
        logger.info(f"response ------> {resp['content']}")
        gen_sql = json.loads(resp["content"])["message"]["content"][1]["statement"]
        return gen_sql
    else:
        raise Exception(f"Failed request with status {resp['status']}: {resp}")


def cortex_agent_gen_sql(  # account:str, token:str,
    question: str,
    semantic_model_type: str,
    semantic_model_loc: str,
    agent_database: str,
    agent_schema: str,
    agent_name: str,
    custom_tools: Optional[Dict] = None,
    api_timeout=600,
) -> str:
    API_ENDPOINT = f"/api/v2/databases/{agent_database}/schemas/{agent_schema}/agents/{agent_name}:run"
    # URL = f"https://{account}.snowflakecomputing.com{API_ENDPOINT}"

    # headers={"Authorization": f"Bearer {token}"
    # ,"Content-Type": "application/json"
    # ,"Accept": "application/json"
    # ,"X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN"}

    question_to_sql = (
        question
        + " Provide SQL text only without any comments/explanations/summaries/charts/markdown annotations."
    )

    if custom_tools:
        request_body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question_to_sql}]}
            ],
            # ,"semantic_model_file": f"@{st.session_state.semantic_model_file_path}",
            SEMANTIC_MODEL_TYPE_MAP.get(semantic_model_type): semantic_model_loc,
            "tool_choice": custom_tools,
        }
    else:
        request_body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question_to_sql}]}
            ],
            # ,"semantic_model_file": f"@{st.session_state.semantic_model_file_path}",
            SEMANTIC_MODEL_TYPE_MAP.get(semantic_model_type): semantic_model_loc,
        }

    resp = _snowflake.send_snow_api_request(
        "POST",  # method
        API_ENDPOINT,  # path
        {},  # headers
        {},  # params
        request_body,  # body
        None,  # request_guid
        api_timeout,  # timeout in milliseconds
    )
    # resp = requests.post(URL, headers=headers, json=request_body, timeout=api_timeout)

    if resp["status"] < 400:  # == 200
        logger.info(f"response ------> {resp['content']}")
        # gen_sql = json.loads(resp["content"])["message"]["content"][1]["statement"]
        resp_js = json.loads(resp["content"])
        df_resp = pd.DataFrame(resp_js)
        gen_sql = df_resp[df_resp["event"] == "response.text"]["data"].iloc[0]["text"]
        return gen_sql
    else:
        raise Exception(f"Failed request with status {resp['status']}: {resp}")


def run_complete(session: Session, model: str, prompt: str) -> str:
    prompt = prompt.replace("'", "\\'")
    return Complete(model=model, prompt=prompt, session=session)


# in case snowflake.cortex.Complete() is deprecated in future
def run_async_sql_complete(session: Session, model: str, prompt: str) -> str:
    prompt = prompt.replace("'", "\\'")
    query = f"""SELECT
    TRIM(snowflake.cortex.complete('{model}',
    '{prompt}'))
    """
    return session.sql(query).collect_nowait().result()[0][0]


def upload_question_file(
    session: Session,
    # target_db: str,
    target_schema: str,
    target_stage: str,
    file_name: str,
) -> None:
    # session.use_database(target_db)
    session.use_schema(target_schema)

    session.sql(f"""
                CREATE STAGE IF NOT EXISTS {target_stage}
                """).collect()

    session.file.put(file_name, target_stage, auto_compress=False, overwrite=True)


def read_sql(sql_file_path, sql_file_name):
    if os.path.exists(os.path.join(str(Path.cwd()), sql_file_path, sql_file_name)):
        sql_file = open(
            os.path.join(str(Path.cwd()), sql_file_path, sql_file_name), "r"
        )
        sql_list = sql_file.readlines()

        sql_qry = "".join(sql_list)
        sql_qry = re.sub("/\\*(.*\n){1,}\\*/|/\\*.*\\*/|--.*\n", "", sql_qry)
    else:
        print("Cannot find file ", sql_file_name, ". Please check file name")
    return sql_qry
