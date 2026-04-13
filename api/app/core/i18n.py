"""
多语言配置文件
支持中文（zh）和英文（en）
"""

from enum import Enum
from typing import Any, Dict


class Language(str, Enum):
    """支持的语言"""

    ZH = "zh"
    EN = "en"


# Multi-language message configuration
MESSAGES: Dict[str, Dict[str, str]] = {
    "zh": {
        # General messages
        "success": "操作成功",
        "error": "操作失败",
        "not_found": "未找到",
        "invalid_params": "参数无效",
        "unauthorized": "未授权",
        "forbidden": "禁止访问",
        "internal_error": "内部服务器错误",
        # User related
        "user_exists": "用户已存在",
        "user_created": "用户创建成功",
        "user_updated": "用户更新成功",
        "user_deleted": "用户删除成功",
        "user_restored": "用户恢复成功",
        "username_required": "用户名不能为空",
        "username_length_error": "用户名长度必须在2-20字符之间",
        "username_format_error": "用户名只能包含字母、数字、下划线和中文字符",
        "password_required": "密码不能为空",
        "password_length_error": "密码长度至少6位",
        "password_invalid": "密码错误",
        "email_required": "邮箱不能为空",
        "email_invalid": "邮箱格式不正确",
        "field_required": "必填字段不能为空",
        "cannot_delete_self": "不能删除自己的账户",
        # Verification code related
        "verification_code_sent": "验证码已发送",
        "verification_code_invalid": "验证码无效",
        "verification_code_expired": "验证码已过期",
        "verification_code_error": "验证码错误",
        # Authentication related
        "login_success": "登录成功",
        "login_failed": "登录失败",
        "logout_success": "退出成功",
        "register_success": "注册成功",
        "register_failed": "注册失败",
        "token_invalid": "令牌无效",
        "token_expired": "令牌已过期",
        "password_reset_success": "密码重置成功",
        "password_reset_failed": "密码重置失败",
        # Chat related
        "chat_not_found": "对话不存在",
        "chat_created": "对话创建成功",
        "chat_updated": "对话更新成功",
        "chat_deleted": "对话删除成功",
        "message_created": "消息创建成功",
        "message_not_found": "消息不存在",
        "chat_access_denied": "无权限访问该对话",
        # Agent related
        "agent_not_found": "智能助手不存在",
        "agent_inactive": "智能助手已停用",
        "agent_deleted": "智能助手已删除",
        "agent_not_found_or_inactive": "智能助手不存在或已停用",
        "agent_test_failed": "智能助手测试失败",
        "agent_connection_error": "智能助手连接错误",
        # Admin related
        "admin_required": "需要管理员权限",
        "not_admin": "非管理员用户",
        "admin_dashboard_data": "管理员仪表板数据",
        "user_list_retrieved": "用户列表获取成功",
        "chat_list_retrieved": "对话列表获取成功",
        # File related
        "file_not_found": "文件不存在",
        "file_upload_success": "文件上传成功",
        "file_upload_failed": "文件上传失败",
        "file_delete_success": "文件删除成功",
        # System related
        "system_status": "系统状态",
        "database_error": "数据库错误",
        "network_error": "网络错误",
        "service_unavailable": "服务不可用",
        # Membership upgrade related
        "upgrade_success": "会员升级成功",
        "upgrade_failed": "会员升级失败",
        "already_premium_member": "您已经是付费会员",
        "already_member": "您已经是该类型会员",
        "plan_not_available": "会员计划当前不可用",
        "invalid_plan": "无效的套餐类型",
        "cannot_upgrade_monthly_to_yearly": "月度会员期间无法开通年付会员，请等待当前会员到期后再升级",
        "cannot_upgrade_yearly_to_monthly": "年付会员期间无法开通月度会员，请等待当前会员到期后再升级",
        "downgrade_not_allowed": "不允许降级会员套餐",
        # Usage limit related
        "daily_message_limit_reached": "今日消息发送次数已达上限，请升级会员或明天再试",
        "daily_token_limit_reached": "今日Token使用量已达上限，请升级会员或明天再试",
        "conversation_turn_limit_reached": "当前对话轮次已达上限，请开始新对话或升级会员",
        "usage_limit_reached": "使用限制已达上限",
        "can_send_message": "可以发送消息",
        # Membership plan related
        "membership_plan_not_found": "会员计划不存在",
        "create_membership_plan_failed": "创建会员计划失败",
        "record_usage_failed": "记录使用情况失败",
        "usage_recorded_success": "使用情况记录成功",
        "membership_stats_success": "获取会员分布统计成功",
        "initialize_plans_failed": "初始化默认会员计划失败",
        "initialize_plans_success": "默认会员计划初始化成功",
        # Dify API related
        "dify_api_request_failed": "Dify API 请求失败",
        "dify_api_error": "Dify API 错误",
        "user_message_not_found": "未找到用户消息",
        "update_chat_others_failed": "更新 chat others 字段失败",
        "unknown_error": "未知错误",
        "dify_agent_connection_normal": "Dify Agent 连接正常",
        "dify_agent_response_empty": "Dify Agent 响应为空",
        "api_key_invalid": "API Key 无效或已过期",
        "api_endpoint_not_found": "API 端点不存在或 URL 配置错误",
        "api_rate_limit": "API 调用频率超限",
        "dify_server_error": "Dify 服务器内部错误",
        "request_timeout": "请求超时，请检查网络连接",
        "connection_failed": "无法连接到 Dify API 服务器",
        "test_failed": "测试失败",
        # CRUD related
        "update_user_stats_failed": "更新用户使用统计失败",
        "create_free_user_membership_failed": "创建免费用户会员记录失败",
        "email_already_exists": "邮箱已存在",
        "username_already_exists": "用户名已存在",
        "user_not_found": "用户不存在",
        "user_already_deleted": "用户已被删除",
        "user_not_deleted": "用户未被删除，无需恢复",
        "invalid_operation_type": "无效的操作类型",
        # Service related
        "record_usage_service_failed": "记录使用情况失败",
        "initialize_default_plans_service_failed": "初始化默认会员计划失败",
        "update_user_membership_type_failed": "更新用户会员类型失败",
        "get_user_usage_stats_service_failed": "获取用户使用统计失败",
        "membership_plan_not_exists": "会员计划不存在",
        "create_default_membership_plan": "创建默认会员计划",
        # Agent/LLM related
        "agent_connection_normal": "Agent 连接正常",
        "agent_response_empty": "Agent 响应为空",
    },
    "en": {
        # General messages
        "success": "Operation successful",
        "error": "Operation failed",
        "not_found": "Not found",
        "invalid_params": "Invalid parameters",
        "unauthorized": "Unauthorized",
        "forbidden": "Forbidden",
        "internal_error": "Internal server error",
        # User related
        "user_exists": "User already exists",
        "user_created": "User created successfully",
        "user_updated": "User updated successfully",
        "user_deleted": "User deleted successfully",
        "user_restored": "User restored successfully",
        "username_required": "Username is required",
        "username_length_error": "Username length must be between 2-20 characters",
        "username_format_error": "Username can only contain letters, numbers, underscores and Chinese characters",
        "password_required": "Password is required",
        "password_length_error": "Password must be at least 6 characters",
        "password_invalid": "Invalid password",
        "email_required": "Email is required",
        "email_invalid": "Invalid email format",
        "field_required": "Required field cannot be empty",
        "cannot_delete_self": "Cannot delete your own account",
        # Verification code related
        "verification_code_sent": "Verification code sent",
        "verification_code_invalid": "Invalid verification code",
        "verification_code_expired": "Verification code expired",
        "verification_code_error": "Verification code error",
        # Authentication related
        "login_success": "Login successful",
        "login_failed": "Login failed",
        "logout_success": "Logout successful",
        "register_success": "Registration successful",
        "register_failed": "Registration failed",
        "token_invalid": "Invalid token",
        "token_expired": "Token expired",
        "password_reset_success": "Password reset successful",
        "password_reset_failed": "Password reset failed",
        # Chat related
        "chat_not_found": "Chat not found",
        "chat_created": "Chat created successfully",
        "chat_updated": "Chat updated successfully",
        "chat_deleted": "Chat deleted successfully",
        "message_created": "Message created successfully",
        "message_not_found": "Message not found",
        "chat_access_denied": "Access denied to this chat",
        # Agent related
        "agent_not_found": "Agent not found",
        "agent_inactive": "Agent is inactive",
        "agent_deleted": "Agent is deleted",
        "agent_not_found_or_inactive": "Agent not found or inactive",
        "agent_test_failed": "Agent test failed",
        "agent_connection_error": "Agent connection error",
        # Admin related
        "admin_required": "Admin privileges required",
        "not_admin": "Not an admin user",
        "admin_dashboard_data": "Admin dashboard data",
        "user_list_retrieved": "User list retrieved successfully",
        "chat_list_retrieved": "Chat list retrieved successfully",
        # File related
        "file_not_found": "File not found",
        "file_upload_success": "File uploaded successfully",
        "file_upload_failed": "File upload failed",
        "file_delete_success": "File deleted successfully",
        # System related
        "system_status": "System status",
        "database_error": "Database error",
        "network_error": "Network error",
        "service_unavailable": "Service unavailable",
        # Membership upgrade related
        "upgrade_success": "Membership upgraded successfully",
        "upgrade_failed": "Membership upgrade failed",
        "already_premium_member": "You are already a premium member",
        "already_member": "You are already a member of this type",
        "plan_not_available": "Membership plan is currently unavailable",
        "invalid_plan": "Invalid plan type",
        "cannot_upgrade_monthly_to_yearly": "Cannot upgrade to yearly plan while monthly membership is active. Please wait until current membership expires.",
        "cannot_upgrade_yearly_to_monthly": "Cannot upgrade to monthly plan while yearly membership is active. Please wait until current membership expires.",
        "downgrade_not_allowed": "Membership downgrade is not allowed",
        # Usage limit related
        "daily_message_limit_reached": "Daily message limit reached, please upgrade membership or try again tomorrow",
        "daily_token_limit_reached": "Daily token limit reached, please upgrade membership or try again tomorrow",
        "conversation_turn_limit_reached": "Conversation turn limit reached, please start a new conversation or upgrade membership",
        "usage_limit_reached": "Usage limit reached",
        "can_send_message": "Can send message",
        # Membership plan related
        "membership_plan_not_found": "Membership plan not found",
        "create_membership_plan_failed": "Failed to create membership plan",
        "record_usage_failed": "Failed to record usage",
        "usage_recorded_success": "Usage recorded successfully",
        "membership_stats_success": "Membership statistics retrieved successfully",
        "initialize_plans_failed": "Failed to initialize default membership plans",
        "initialize_plans_success": "Default membership plans initialized successfully",
        # Dify API related
        "dify_api_request_failed": "Dify API request failed",
        "dify_api_error": "Dify API error",
        "user_message_not_found": "User message not found",
        "update_chat_others_failed": "Failed to update chat others field",
        "unknown_error": "Unknown error",
        "dify_agent_connection_normal": "Dify Agent connection is normal",
        "dify_agent_response_empty": "Dify Agent response is empty",
        "api_key_invalid": "API Key is invalid or expired",
        "api_endpoint_not_found": "API endpoint not found or URL configuration error",
        "api_rate_limit": "API rate limit exceeded",
        "dify_server_error": "Dify server internal error",
        "request_timeout": "Request timeout, please check network connection",
        "connection_failed": "Unable to connect to Dify API server",
        "test_failed": "Test failed",
        # CRUD related
        "update_user_stats_failed": "Failed to update user usage statistics",
        "create_free_user_membership_failed": "Failed to create free user membership record",
        "email_already_exists": "Email already exists",
        "username_already_exists": "Username already exists",
        "user_not_found": "User not found",
        "user_already_deleted": "User is already deleted",
        "user_not_deleted": "User is not deleted, no need to restore",
        "invalid_operation_type": "Invalid operation type",
        # Service related
        "record_usage_service_failed": "Failed to record usage",
        "initialize_default_plans_service_failed": "Failed to initialize default membership plans",
        "update_user_membership_type_failed": "Failed to update user membership type",
        "get_user_usage_stats_service_failed": "Failed to get user usage statistics",
        "membership_plan_not_exists": "Membership plan does not exist",
        "create_default_membership_plan": "Create default membership plan",
        # Agent/LLM related
        "agent_connection_normal": "Agent connection is normal",
        "agent_response_empty": "Agent response is empty",
    },
}


def get_message(key: str, lang: str = "zh") -> str:
    """
    Get multi-language message

    Args:
        key: Message key
        lang: Language code, default is Chinese

    Returns:
        Message text in corresponding language
    """
    # Ensure language code is valid
    if lang not in MESSAGES:
        lang = "zh"  # Default to Chinese

    # Get message, if not exists return key itself
    return MESSAGES[lang].get(key, key)


def get_error_message(key: str, lang: str = "zh") -> str:
    """
    Get error message (wrapper function)

    Args:
        key: Message key
        lang: Language code, default is Chinese

    Returns:
        Error message text
    """
    return get_message(key, lang)


def create_response_message(key: str, lang: str = "zh", **kwargs) -> Dict[str, Any]:
    """
    Create standardized response message

    Args:
        key: Message key
        lang: Language code
        **kwargs: Other data to include in response

    Returns:
        Dictionary containing message and data
    """
    message = get_message(key, lang)
    response = {"message": message}
    response.update(kwargs)
    return response
