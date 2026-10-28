import asyncio
import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from glom import PathAccessError, glom
from pydantic.dataclasses import dataclass
from snowflake.snowpark import AsyncJob
from snowflake.snowpark.session import Session

from src.utils.constants import Constants
from src.utils.yaml_funcs import parse_yaml, update_yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


CONFIG_OBJECT: Dict[str, bool] = "{'describe_columns': true, 'use_table_data': false}"
TABLE_DESC_SPROC = "CALL AI_GENERATE_TABLE_DESC('{object_name}', {config})"
POLL_INTERVAL = 0.5  # in seconds
ANALYST = "analyst"


@dataclass
class Result:
    name: str
    description: str


class Config:
    arbitrary_types_allowed = True


@dataclass(config=Config)
class SemanticDescAsyncExecutor:
    session: Session
    yaml_config: Dict
    yaml_file_path: str

    def _extract_obj_names(self) -> List[Dict[str, str]]:
        return [
            {
                Constants.DATABASE.value: obj.get(Constants.BASE_TABLE.value).get(
                    Constants.DATABASE.value
                ),
                Constants.SCHEMA.value: obj.get(Constants.BASE_TABLE.value).get(
                    Constants.SCHEMA.value
                ),
                Constants.OBJECT_NAME.value: obj.get(Constants.BASE_TABLE.value).get(
                    Constants.TABLE.value
                ),
            }
            for obj in self.yaml_config.get(Constants.TABLES.value)
        ]

    @staticmethod
    def _build_column_description_map(
        columns_data: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        col_descriptions = {}
        for col in columns_data:
            col_name = col.get(Constants.NAME.value)
            if col_name:
                col_descriptions[f'"{col_name}"'] = col.get(Constants.DESCRIPTION.value)
        return col_descriptions

    @staticmethod
    def _find_target_table_in_source(
        source_tables: List[Dict[str, Any]],
        target_table_name: str,
    ) -> Optional[Any]:
        for table in source_tables:
            base_table = table.get(Constants.BASE_TABLE.value).get(
                Constants.TABLE.value
            )
            if base_table == target_table_name:
                return table
        return None

    @staticmethod
    def _get_dimensions(target_table_item: Any):
        dimension_expressions = set()
        try:
            dimension_expressions = set(
                glom(
                    target_table_item,
                    (Constants.DIMENSIONS.value, [Constants.EXPR.value]),
                    default=[],
                )
            )
        except (PathAccessError, KeyError):
            pass

        return dimension_expressions

    def _update_dimensions(
        self, item: Dict[str, Any], column_descriptions: Dict[str, str]
    ) -> set:
        dimensions = item.get(Constants.DIMENSIONS.value, [])
        dimension_expressions = set()

        for dim in dimensions:
            expr = dim.get(Constants.EXPR.value)
            if expr:
                dimension_expressions.add(expr)
                if (
                    expr in column_descriptions
                    and dim.get(Constants.DESCRIPTION.value) is None
                ):
                    dim[Constants.DESCRIPTION.value] = column_descriptions[expr]

        return dimension_expressions

    def _update_facts(
        self,
        item: Dict[str, Any],
        column_descriptions: Dict[str, str],
        dimension_expressions: set,
    ) -> None:
        facts = item.get(Constants.FACTS.value, [])
        if not facts:
            return

        for fact in facts:
            expr = fact.get(Constants.EXPR.value)
            if (
                expr
                and expr in column_descriptions
                and expr not in dimension_expressions
                and fact.get(Constants.DESCRIPTION.value) is None
            ):
                fact[Constants.DESCRIPTION.value] = column_descriptions[expr]

    def _update_semantic_model(
        self, generated_description: Dict[str, Any]
    ) -> Dict[str, Any]:
        source_tables = self.yaml_config.get(Constants.TABLES.value)
        target_table_name = generated_description.get(Constants.OBJECT_NAME.value)
        result_data = generated_description.get(Constants.RESULT.value)
        table_description = result_data.get("TABLE", [{}])[0].get(
            Constants.DESCRIPTION.value
        )
        columns_data = result_data.get("COLUMNS", [])

        if not columns_data and not target_table_name:
            return

        col_description_map = SemanticDescAsyncExecutor._build_column_description_map(
            columns_data=columns_data
        )

        found_target_table_item = (
            SemanticDescAsyncExecutor._find_target_table_in_source(
                source_tables=source_tables,
                target_table_name=target_table_name,
            )
        )

        if (
            found_target_table_item
            and table_description
            and (found_target_table_item.get(Constants.DESCRIPTION.value) is None)
        ):
            found_target_table_item[Constants.DESCRIPTION.value] = table_description

        dimension_expressions = self._update_dimensions(
            item=found_target_table_item, column_descriptions=col_description_map
        )
        self._update_facts(
            item=found_target_table_item,
            column_descriptions=col_description_map,
            dimension_expressions=dimension_expressions,
        )

        return found_target_table_item

    @staticmethod
    async def _wait_for_job_completion(job: AsyncJob, object_name: str) -> List[Any]:
        while not job.is_done():
            logger.info(f"Waiting for AI to complete description for {object_name} ")
            await asyncio.sleep(POLL_INTERVAL)

        if job.is_done():
            completed_desc = job.result()
            logger.info(
                f"completed generating descriptions for query_id {job.query_id}"
            )
            return completed_desc

    async def _execute_sproc_async(
        self, object_details: Dict[str, str]
    ) -> Dict[str, Any]:
        try:
            object_name_param = f"{object_details.get(Constants.DATABASE.value)}.{object_details.get(Constants.SCHEMA.value)}.{object_details.get(Constants.OBJECT_NAME.value)}"

            async_job: AsyncJob = self.session.sql(
                TABLE_DESC_SPROC.format(
                    object_name=object_name_param, config=CONFIG_OBJECT
                )
            ).collect_nowait()

            result = await SemanticDescAsyncExecutor._wait_for_job_completion(
                job=async_job,
                object_name=object_details.get(Constants.OBJECT_NAME.value),
            )

            result = json.loads(result[0][0])

            return object_details | {
                Constants.RESULT.value: result,
                Constants.STATUS.value: "success",
            }

        except Exception as e:
            return object_details | {
                Constants.RESULT.value: None,
                Constants.STATUS.value: Constants.ERROR.value,
                Constants.ERROR.value: str(e),
            }

    async def _execture_completions_in_parallel(self) -> List[Dict[str, str]]:
        object_list = self._extract_obj_names()
        results = await asyncio.gather(
            *(self._execute_sproc_async(object_details=obj) for obj in object_list),
            return_exceptions=True,
        )
        return results

    async def main(self):
        try:
            # call ai generate descriptions for all views/tables in the current semantic view
            generated_descriptions = await self._execture_completions_in_parallel()

            # use the generated descriptions to update the descriptions of all the objects in the semantic value.
            self.yaml_config[Constants.TABLES.value] = [
                self._update_semantic_model(generated_description=generated_description)
                for generated_description in generated_descriptions
            ]

            # update the semantic model yaml file and validate
            update_yaml(yaml_dict=self.yaml_config, yaml_file_path=self.yaml_file_path)
            parse_yaml(yaml_file_path=self.yaml_file_path, validate=True)

            tables_desc_info = glom(
                self.yaml_config,
                ("tables", [{"name": "name", "description": "description"}]),
            )

            combined_desc = "\n\n\n".join(
                [
                    f"{table_info.get('name')} \n {table_info.get('description')}"
                    for table_info in tables_desc_info
                ]
            )

            return asdict(
                Result(
                    name=f"{self.yaml_config.get('name')}_{ANALYST}",
                    description=combined_desc,
                )
            )

        except Exception as e:
            logger.error(f"Exception : {e}")
            raise
