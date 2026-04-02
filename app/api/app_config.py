from fastapi import APIRouter

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/bootstrap")
def get_bootstrap_config():
    """
    获取引导配置
    """
    return {
        "force_show_onboarding": False
    }