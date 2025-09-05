from typing import Any, List
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools.mind_map_center import MindMapCenterTool
from tools.mind_map_horizontal import MindMapHorizontalTool
from tools.mind_map_vertical import MindMapVerticalTool
from tools.mind_map_fishbone import MindMapFishboneTool
from tools.mind_map_orgchart import MindMapOrgChartTool
from tools.mind_map_timeline import MindMapTimelineTool
from tools.mind_map_circular import MindMapCircularTool


class MindMapProvider(ToolProvider):
    """Mind map generator tool provider"""
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        验证凭据（此工具不需要特殊凭据）
        """
        pass
    
    def _get_tools(self) -> List[Any]:
        """
        返回可用的工具列表
        """
        return [
            MindMapCenterTool, 
            MindMapHorizontalTool,
            MindMapVerticalTool,
            MindMapFishboneTool,
            MindMapOrgChartTool,
            MindMapTimelineTool,
            MindMapCircularTool
        ]


# 创建provider实例
mind_map_provider = MindMapProvider()
