import argparse
import asyncio
import logging
import os
from typing import Any, Dict, Optional

from snowflake import snowpark

from src.agent.agent_request_builder import AgentRequestBuilder
from src.api_client import send_request
from src.semantic_model.semantic_desc_async_executor import (
    SemanticDescAsyncExecutor,
)
from src.utils.yaml_funcs import parse_yaml, push_semantic_model_yml_to_stage

ANALYST_DATABASE = "EDP_PROD"
ANALYST_SCHEMA = "PRES"
ANALYST_STAGE = "SEMANTIC_MODELS"
ANALYST_WAREHOUSE = "ANALYTICS_ANALYSIS_SANDPIT_WH"

AGENT_DATABASE = "SNOWFLAKE_INTELLIGENCE"
AGENT_SCHEMA = "AGENTS"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def argparser():
    parser = argparse.ArgumentParser(prog="AI agent creation pipeline")

    parser.add_argument(
        "--analyst_database",
        type=str,
        default=ANALYST_DATABASE,
        help="The database where the semantic model will be uploaded to",
    )
    parser.add_argument(
        "--analyst_schema",
        type=str,
        default=ANALYST_SCHEMA,
        help="The schema where the semantic model will be uploaded to",
    )
    parser.add_argument(
        "--analyst_stage",
        type=str,
        default=ANALYST_STAGE,
        help="The stage where the semantic model will be uploaded to",
    )
    parser.add_argument(
        "--analyst_warehouse",
        type=str,
        default=ANALYST_WAREHOUSE,
        help="The warehouse the analyst's sql will be executed with",
    )

    parser.add_argument(
        "--agent_database",
        type=str,
        help="database where the agent would be created at",
        default=AGENT_DATABASE,
    )
    parser.add_argument(
        "--agent_schema",
        type=str,
        help="schema where the agent would be created at",
        default=AGENT_SCHEMA,
    )

    parser.add_argument(
        "--enrich_semantic_model",
        action=argparse.BooleanOptionalAction,
        help="if set to true the descriptions of the table and columns will be genereated by AI, will be skipped otherwise",
        default=True,
    )

    return parser.parse_args()


def main(session):
    table_desc_info: Optional[Dict] = {}
    args = argparser()

    # create paths for config files
    root_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_file_path: str = os.path.join(root_dir, "assets", "retail_performance.yaml")
    agent_req_config_path: str = os.path.join(
        root_dir, "assets", "agent_request_config.yaml"
    )
    if args.enrich_semantic_model:
        semantic_model_config: Dict = parse_yaml(yaml_file_path=yaml_file_path)
        semantic_desc_async = SemanticDescAsyncExecutor(
            session=session,
            yaml_config=semantic_model_config,
            yaml_file_path=yaml_file_path,
        )
        table_desc_info = asyncio.run(semantic_desc_async.main())

    uploaded_semantic_model_file_path: str = push_semantic_model_yml_to_stage(
        session=session,
        database=args.analyst_database,
        schema=args.analyst_schema,
        stage=args.analyst_stage,
        local_file_path=yaml_file_path,
    )

    table_desc_info = table_desc_info | {
        "semantic_model_file": uploaded_semantic_model_file_path,
        "warehouse": args.analyst_warehouse,
    }

    agent_request_payload: Dict[str, Any] = (
        AgentRequestBuilder.build_agent_request_payload(
            file_path=agent_req_config_path, tool_details=table_desc_info
        )
    )

    resp = send_request(
        jwt_auth_token=os.getenv("JWT_TOKEN"),
        request_payload=agent_request_payload,
        database=args.agent_database,
        schema=args.agent_schema,
    )

    logger.info(f"Response of agent creation : {resp}")


if __name__ == "__main__":
    session = snowpark.Session.builder.configs(
        {
            "account": os.getenv("ACCOUNT"),
            "user": os.getenv("USER"),
            "password": os.getenv("PASSWORD"),
            "role": os.getenv("ROLE"),
            "warehouse": os.getenv("WAREHOUSE"),
            "database": os.getenv("DATABASE"),
            "schema": os.getenv("SCHEMA"),
        }
    ).create()

    main(session)
