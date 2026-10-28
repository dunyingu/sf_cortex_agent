import logging
from dataclasses import asdict
from typing import Any, Dict, Optional

from src.agent.agent_request import (
    AgentInstructions,
    AgentModels,
    AgentOrchestrationConfig,
    AgentProfile,
    AgentRequest,
    Tool,
    ToolSpec,
    build_tool_resources,
)
from src.utils.constants import Constants
from src.utils.yaml_funcs import parse_yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
DEFAULT_CORTEX_TOOL_NAME = "retail_performane_analyst"


class AgentRequestBuilder:
    @staticmethod
    def read_agent_config(file_path: str):
        try:
            return parse_yaml(yaml_file_path=file_path)
        except Exception as e:
            logger.error(f"Error while reading the agent request file {e}")

    def build_agent_request_payload(
        file_path: str, tool_details: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        config_yaml_dict: Dict = AgentRequestBuilder.read_agent_config(
            file_path=file_path,
        )

        agent_profile = AgentProfile(**config_yaml_dict.get("profile"))
        models = AgentModels(**config_yaml_dict.get("models"))
        agent_instructions = AgentInstructions(**config_yaml_dict.get("instructions"))
        agent_orchestration = AgentOrchestrationConfig(
            **config_yaml_dict.get("orchestration")
        )

        tools = []
        tool_resources = {}

        for tool in config_yaml_dict.get("tools"):
            tool_info = tool.get("tool_spec")
            tool_name = (
                tool_details.get(Constants.NAME.value)
                if Constants.NAME.value in tool_details
                else DEFAULT_CORTEX_TOOL_NAME
            )
            tool_description = (
                tool_details.get(Constants.DESCRIPTION.value)
                if Constants.DESCRIPTION.value in tool_details
                else config_yaml_dict.get("comment")
            )

            tool_info[Constants.NAME.value] = tool_name
            tool_info[Constants.DESCRIPTION.value] = tool_description

            tools.append(Tool(tool_spec=ToolSpec(**tool_info)))
            tool_resources[tool_name] = build_tool_resources(
                template_config_dict=tool_info, update_info_dict=tool_details
            )

        return asdict(
            AgentRequest(
                name=config_yaml_dict.get(Constants.NAME.value),
                comment=config_yaml_dict.get("comment"),
                profile=agent_profile,
                models=models,
                instructions=agent_instructions,
                orchestration=agent_orchestration,
                tools=tools,
                tool_resources=tool_resources,
            ),
            dict_factory=lambda x: {k: v for (k, v) in x if v is not None},
        )
