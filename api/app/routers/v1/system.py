from fastapi import APIRouter
from sqlmodel import func, select

from app.dependencies.db import SessionDep
from app.models.user import User, UserType

system_router = APIRouter(prefix="/system")


@system_router.get("/status")
def get_system_status(session: SessionDep):
    """
    获取系统初始化状态

    功能说明:
    仅返回系统是否需要初始化的基本信息，不暴露具体的用户数量等敏感数据
    主要用于前端判断是否显示初始化引导页面

    返回:
    - is_initialized: 系统是否已完成初始化（有管理员即为已初始化）
    """
    # 检查是否有管理员（系统初始化的关键指标）
    admin_count = session.exec(select(func.count(User.id)).where(User.user_type == UserType.ADMIN)).first() or 0

    # 系统已初始化的标准：至少有一个管理员
    is_initialized = admin_count > 0

    return {
        "is_initialized": is_initialized,
    }
