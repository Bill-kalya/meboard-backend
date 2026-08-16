from fastapi import APIRouter

from ..schemas import VisualizeRequest, VisualizationSpec
from ..semantic.visualize import build_visualization

router = APIRouter()


@router.post("/visualize", response_model=VisualizationSpec)
async def visualize(request: VisualizeRequest) -> VisualizationSpec:
    spec = build_visualization(request.content)
    if spec is None:
        return VisualizationSpec(
            category="none",
            plot_type="none",
            expression=str(request.content or ""),
        )
    return spec
