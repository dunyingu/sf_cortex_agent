import logging
import multiprocessing
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Union

import pandas as pd
from joblib import Parallel, delayed
from snowflake.snowpark import Session
from snowflake.snowpark.dataframe import DataFrame
from snowflake.snowpark.types import StringType, StructField, StructType

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_eval_src.metrics import Metadata, metrics_list
from sql_eval_src.utils import (
    cortex_agent_gen_sql,
    cortex_analyst_gen_sql,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_eval(
    session: Session,
    semantic_model_type: str,
    semantic_model_loc: str,
    question: str,
    ref_sql: str,
    agent_database: Optional[str] = None,
    agent_schema: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> Dict[str, Union[int, str]]:
    if agent_name:
        gen_sql = cortex_agent_gen_sql(
            question=question,
            semantic_model_type=semantic_model_type,
            semantic_model_loc=semantic_model_loc,
            agent_database=agent_database,
            agent_schema=agent_schema,
            agent_name=agent_name,
        )
    else:
        gen_sql = cortex_analyst_gen_sql(
            question=question,
            semantic_model_type=semantic_model_type,
            semantic_model_loc=semantic_model_loc,
        )

    logger.info("Generating metadata..")
    metadata = Metadata(ref_sql, gen_sql).evaluate(session=session)

    params = {"question": question, "ref_sql": ref_sql, "gen_sql": gen_sql}

    logger.info("Collecting eval metrics..")
    llm_metrics = [
        {  # "LLM_JUDGE": metric.model,
            f"LLM_{metric.get_column()}": metric.evaluate(session=session, **params)
        }
        for metric in metrics_list
    ]
    llm_metrics_dict = {k: v for d in llm_metrics for k, v in d.items()}

    result = (
        {"GENERATED_SQL": gen_sql}
        | metadata
        | {"LLM_JUDGE": metrics_list[0].model}
        | llm_metrics_dict
    )
    return result


def batch_eval(
    session: Session,
    schema_name: str,
    stage_name: str,
    question_file_path: str,
    log_table_name: str,
) -> DataFrame:
    session.use_schema(schema_name)

    stage_path = f"@{stage_name}/{question_file_path}"
    csv_schema = StructType(
        [
            StructField("RUN_ID", StringType()),  # IntegerType()
            StructField("SEMANTIC_MODEL_TYPE", StringType()),
            StructField("SEMANTIC_NAME", StringType()),
            StructField("AGENT_DATABASE", StringType()),
            StructField("AGENT_SCHEMA", StringType()),
            StructField("AGENT_NAME", StringType()),
            StructField("USER_QUESTION", StringType()),
            StructField("REFERENCE_SQL", StringType()),
        ]
    )
    input_snowpark_df = (
        session.read.option("header", "true")
        .option("FIELD_OPTIONALLY_ENCLOSED_BY", '"')
        .option("ESCAPE_UNENCLOSED_FIELD", None)
        .schema(csv_schema)
        .csv(stage_path)
    )

    df_input = input_snowpark_df.to_pandas()

    logger.info("Begin Evalution..")
    df_input["EVAL_RESULT"] = Parallel(
        multiprocessing.cpu_count(), backend="threading"
    )(
        delayed(run_eval)(
            session,
            row["SEMANTIC_MODEL_TYPE"],
            row["SEMANTIC_NAME"],
            row["USER_QUESTION"],
            row["REFERENCE_SQL"],
            row["AGENT_DATABASE"],
            row["AGENT_SCHEMA"],
            row["AGENT_NAME"],
        )
        for _, row in df_input.iterrows()
    )

    df_eval_results = pd.json_normalize(df_input["EVAL_RESULT"])
    df_final = pd.concat(
        [df_input.drop(columns=["EVAL_RESULT"]), df_eval_results], axis=1
    )
    df_final["EVAL_TIMESTAMP"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    snowpark_df_final = session.create_dataframe(df_final)
    snowpark_df_final.write.save_as_table(
        log_table_name, mode="append", create_temp_table=False
    )

    logger.info("eval completed.")

    return snowpark_df_final
