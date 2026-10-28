import logging
import os
from typing import Dict, List, Optional

import yaml
from snowflake.core import Root
from snowflake.core.stage import Stage, StageCollection, StageResource
from snowflake.snowpark.session import Session

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_yaml(
    yaml_file_path: str, validate: Optional[bool] = False
) -> Dict[str, str | List | Dict]:
    try:
        with open(yaml_file_path, "r") as f:
            content = f.read()
        config = yaml.safe_load(content)
        variables = config.get("variables", {})
        for key, value in variables.items():
            content = content.replace(f"${{{key}}}", str(value))
        if validate:
            logger.info("The yaml file is syntactially valid")
        return yaml.safe_load(content)
    except FileNotFoundError as e:
        logger.error(f"File not found at {yaml_file_path}", e)


def update_yaml(yaml_dict: Dict, yaml_file_path: str) -> None:
    try:
        with open(yaml_file_path, "w") as f:
            yaml.dump(yaml_dict, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Error while dumping the updated yaml {e}")


def push_semantic_model_yml_to_stage(
    session: Session, database: str, schema: str, stage: str, local_file_path: str
) -> str:
    try:
        root = Root(session)
        # stages in the current database, schema context
        stages: StageCollection = root.databases[database].schemas[schema].stages
        new_stage: Stage = Stage(
            name=stage, comment="Stage to store semantic models for agents"
        )

        # creates a stage if not exists
        stg_reference: StageResource = stages.create(new_stage, mode="ifNotExists")

        # use the stage reference to upload the semantic model to stage
        stg_reference.put(
            local_file_name=local_file_path,
            stage_location="/",
            auto_compress=False,
            overwrite=True,
        )
        return (
            f"@{stg_reference.fully_qualified_name}/{os.path.basename(local_file_path)}"
        )
    except FileNotFoundError | Exception as e:
        logger.error(f"Error while pushing the file to stage {e}")
