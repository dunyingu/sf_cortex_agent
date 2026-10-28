import re
from abc import ABC
from typing import Dict, Optional, Union

# from .prompts import *
# from .utils import run_sql, return_sql_result, run_complete, run_async_sql_complete
from sql_eval_src.prompts import (
    AnswerRelevancy_prompt,
    Comprehensiveness_prompt,
    Correctness_prompt,
    Fix_prompt,
    SemanticEquivalence_prompt,
    SQLAccuracy_prompt,
)
from sql_eval_src.utils import return_sql_result, run_complete, run_sql


class Metadata:
    def __init__(
        self,
        # session: Session,
        ref_sql: str,
        gen_sql: str,
    ):
        self.session = None  # session
        self.ref_sql = ref_sql
        self.gen_sql = gen_sql

    def evaluate(self, session) -> Dict[str, int]:
        self.session = session
        df_ref = run_sql(self.session, self.ref_sql)
        df_gen = run_sql(self.session, self.gen_sql)

        if df_ref is not None:
            row_ref, col_ref = df_ref.shape
            df_ref_unique = df_ref.drop_duplicates()
            unirow_ref = df_ref_unique.shape[0]
        else:
            row_ref, unirow_ref, col_ref = 0, 0, 0

        if df_gen is not None:
            row_gen, col_gen = df_gen.shape
            df_gen_unique = df_gen.drop_duplicates()
            unirow_gen = df_gen_unique.shape[0]
        else:
            row_gen, unirow_gen, col_gen = 0, 0, 0

        return {
            "ROWCOUNT_REF": row_ref,
            "ROWCOUNT_GEN": row_gen,
            "UNIROWCOUNT_REF": unirow_ref,
            "UNIROWCOUNT_GEN": unirow_gen,
            "COLCOUNT_REF": col_ref,
            "COLCOUNT_GEN": col_gen,
        }


class Metric(ABC):
    def __init__(
        self,
        # session: Session,
        name: str,
        description: str,
        prompt: str,
        required: Dict[str, str],
    ):
        self.session = None  # session
        self.name = name
        self.description = description
        self.required = required
        self.prompt = prompt

    def get_prompt(
        self,
        **kwargs,
    ) -> Union[str, None]:
        if self.prompt is not None:
            try:
                return self.prompt.format(**kwargs)
            except ValueError as e:
                return f"Keyword argument missing in prompt: {e}"
        else:
            return None

    def evaluate(
        self,
        session,
        model: Optional[str] = None,
        **kwargs,
    ):
        self.session = session
        model_to_use = model if model else self.model
        try:
            prompt = self.get_prompt(**kwargs)

            response = run_complete(self.session, model_to_use, prompt)
            # response = run_async_sql_complete(self.session, model_to_use, prompt)
            rating = re.search(r"\d+", response)
            if rating:
                return int(rating.group())
        except Exception:
            return None
        else:
            return None

    def get_column(self):
        return self.name.replace(" ", "_").upper()


# Generated SQL Relevance to Question
class Relevance(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' #"llama3.1-8b"
    ):
        super().__init__(
            name="Relevance",
            description="""
Evaluates the relevance of the generated SQL to a user question on a scale of 1-5.
5 indicates the scorer strongly agrees that the response is relevant and 1 indicates strong disagreement.""",
            prompt=AnswerRelevancy_prompt,
            required={
                "question": "User question",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model


# Generated SQL Equivalence to Reference
class SemanticEquivalence(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' #"llama3.1-8b"
    ):
        super().__init__(
            name="Semantic Equivalence",
            description="""
Evaluates the similarity of the generated SQL to the reference SQL on a scale of 1-5.
5 indicates the scorer strongly agrees that the response is relevant and 1 indicates strong disagreement.""",
            prompt=SemanticEquivalence_prompt,
            required={
                "question": "User question",
                "ref_sql": "Reference SQL",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model


# SQL Correctness vs. Reference
class Correctness(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' #"llama3.1-8b"
    ):
        super().__init__(
            name="Correctness",
            description="""
Evaluates the correctness of the generated SQL compared to a reference SQL on a scale of 1-5.
5 indicates the scorer strongly agrees that the generated SQL is correct and 1 indicates strong disagreement.""",
            prompt=Correctness_prompt,
            required={
                "question": "User question",
                "ref_sql": "Reference SQL",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model


# SQL Comprehensiveness vs. Reference
class Comprehensiveness(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' #"llama3.1-8b"
    ):
        super().__init__(
            name="Comprehensiveness",
            description="""
Evaluates the thoroughness and comprehensiveness of the generated SQL compared to a reference answer on a scale of 1-5.
5 indicates the scorer strongly agrees that the response is thorough and comprehensive and 1 indicates strong disagreement.""",
            prompt=Comprehensiveness_prompt,
            required={
                "question": "User question",
                "ref_sql": "Reference SQL",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model


# Generated SQL Result Set Equivalence to Reference
class SQLResultsAccuracy(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' # "mistral-large2"
    ):
        super().__init__(
            name="Result Set Equivalence",
            description="""
Evaluates if 2 SQL queries return the same data set given a user question.
Output is a rating number on the scale of 1-5.
5 indicates the scorer strongly agrees that the generated SQL result set is correct and 1 indicates strong disagreement.
Questions are best designed when expected results have less than 100 rows.""",
            prompt=SQLAccuracy_prompt,
            required={
                "question": "User question",
                # "db_name": "Database where the sql is executed",
                # "schema_name": "Schema where the sql is executed",
                "ref_sql": "Reference SQL",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model

    def get_prompt(
        self,
        **kwargs,
    ) -> Union[str, None]:
        # self.session = session
        if self.prompt is not None:
            if "gen_sql" in kwargs:
                inference_data = return_sql_result(
                    self.session,  # kwargs["db_name"], kwargs["schema_name"],
                    kwargs["gen_sql"],
                )
            else:
                inference_data = "No data returned"
            if "ref_sql" in kwargs:
                expected_data = return_sql_result(
                    self.session,  # kwargs["db_name"], kwargs["schema_name"],
                    kwargs["ref_sql"],
                )
            else:
                expected_data = "No data returned"
            if "question" in kwargs:
                question = kwargs["question"]
            else:
                question = "No question provided"

            fstrings = {
                "question": question,
                "gen_js": inference_data,
                "ref_js": expected_data,
            }
            return self.prompt.format(**fstrings)
        else:
            return None


# Suggestions to improve generated SQL based on the reference SQL
class Fix(Metric):
    def __init__(
        self,
        model: str = "claude-4-sonnet",  # "claude-3-7-sonnet" #'openai-gpt-5' #"llama3.1-8b"
    ):
        super().__init__(
            name="Fix",
            description="""
Provide suggestions to the generated SQL based on the user question and reference SQL.""",
            prompt=Fix_prompt,
            required={
                "question": "User question",
                "ref_sql": "Reference SQL",
                "gen_sql": "Corten Anlyst/Agent generated SQL",
            },
        )
        self.model = model

    def evaluate(
        self,
        session,
        model: Optional[str] = None,
        **kwargs,
    ):
        self.session = session
        model_to_use = model if model else self.model
        try:
            prompt = self.get_prompt(**kwargs)

            response = run_complete(self.session, model_to_use, prompt)
            # response = run_async_sql_complete(self.session, model_to_use, prompt)
            if response:
                return response
        except Exception:
            return None
        else:
            return None


# All metrics
metrics_list = [
    Relevance(),
    SemanticEquivalence(),
    Correctness(),
    Comprehensiveness(),
    SQLResultsAccuracy(),
    Fix(),
    # ContextualRelevancy()
    # Hallucination(),
    # ConversationCohesiveness(),
]


models = [
    "claude-3-5-sonnet",
    "claude-3-7-sonnet",
    "claude-4-sonnet",
    "gemma-7b",
    "jamba-instruct",
    "jamba-1.5-mini",
    "jamba-1.5-large",
    "llama3.3-70b",
    "llama3.2-1b",
    "llama3.2-3b",
    "llama3.1-8b",
    "llama3.1-70b",
    "llama3.1-405b",
    "mistral-large2",
    "mixtral-8x7b",
    "mistral-7b",
    "openai-gpt-4.1",
    "openai-gpt-5",
    "openai-gpt-5-mini",
    "openai-gpt-5-nano",
    "openai-gpt-oss-120b",
    "openai-gpt-oss-20b",
    "reka-core",
    "reka-flash",
    "snowflake-arctic",
    "snowflake-llama-3.1-405b",
    "snowflake-llama-3.3-70b",
]
