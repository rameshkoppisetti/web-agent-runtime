from .registry import ToolRegistry
from .navigation import NavigateTool
from .dom import ClickTool, WaitForSelectorTool, GetTextTool
from .forms import FillTool, SelectOptionTool
from .overlays import DismissOverlaysTool
from .screenshots import ScreenshotTool
from .extraction import ExtractPageTool, ExtractLinksTool



def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(NavigateTool())
    registry.register(ClickTool())
    registry.register(WaitForSelectorTool())
    registry.register(GetTextTool())
    registry.register(FillTool())
    registry.register(DismissOverlaysTool())
    registry.register(SelectOptionTool())
    registry.register(ScreenshotTool())
    registry.register(ExtractPageTool())
    registry.register(ExtractLinksTool())

    return registry