from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field
from pydantic.dataclasses import dataclass


class ToolType(Enum):
    CORTEX_ANALYST_TEXT2SQL = "cortex_analyst_text_to_sql"
    CORTEX_SEARCH = "cortex_search"
    GENERIC = "generic"


class Config:
    arbitrary_types_allowed = True


@dataclass
class AgentProfile:
    display_name: str


@dataclass
class AgentModels:
    orchestration: Optional[str] = "claude-4-sonnet"


@dataclass
class AgentInstructions:
    response: str
    orchestration: str
    system: str


@dataclass
class AgentOrchestrationConfig:
    budget: Optional[Dict[str, int]] = Field(
        default_factory=lambda: {"seconds": 30, "tokens": 1600}
    )


@dataclass
class ToolSpec:
    type: str
    name: str
    description: str
    input_schema: Optional[Dict] = None


@dataclass
class Tool:
    tool_spec: ToolSpec


@dataclass
class SemanticModelToolResource:
    semantic_model_file: Optional[str] = None
    semantic_view: Optional[str] = None
    execution_environment: Optional[Dict] = None


@dataclass
class CortexSearchToolResource:
    search_service: str
    title_column: str
    id_column: str
    filter: Optional[Dict] = None


@dataclass
class GenericToolResource:
    type: str
    identifier: str
    execution_environment: Optional[Dict] = None


@dataclass(config=Config)
class AgentRequest:
    name: str
    profile: AgentProfile
    models: AgentModels
    instructions: AgentInstructions
    orchestration: AgentOrchestrationConfig
    tools: List[Tool]
    tool_resources: Dict[
        str, SemanticModelToolResource | CortexSearchToolResource | GenericToolResource
    ]
    comment: Optional[str] = None


# tool_type_map = {
#     ToolType.CORTEX_ANALYST_TEXT2SQL.value: SemanticModelToolResource,
#     ToolType.CORTEX_SEARCH.value: CortexSearchToolResource,
#     ToolType.GENERIC.value: GenericToolResource,
# }


def build_tool_resources(
    template_config_dict: Dict, update_info_dict: Dict
) -> SemanticModelToolResource | CortexSearchToolResource | GenericToolResource:
    resourec_obj = template_config_dict.get("tool_resources")
    resourec_obj["semantic_model_file"] = update_info_dict["semantic_model_file"]
    resourec_obj["execution_environment"]["warehouse"] = update_info_dict["warehouse"]
    return SemanticModelToolResource(**resourec_obj)

    # TODO: The passing of params to the the constructor
