"""
用户服务 - 处理用户查询和管理
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from src.logger import Logger
from src.exceptions import DataLoadException, UserNotFoundException

logger = Logger.get_logger("user")


class UserService:
    """用户服务类"""
    
    def __init__(self, data_dir: Path):
        self.users_file = data_dir.parent / "user" / "users.json"
        self.roles_file = data_dir.parent / "user" / "roles.json"
        self._users_cache = None
        self._roles_cache = None
    
    def _load_users(self) -> Dict[str, Any]:
        """加载用户数据"""
        if self._users_cache is not None:
            return self._users_cache
        
        try:
            if not self.users_file.exists():
                logger.warning("用户文件不存在")
                return {}
            
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self._users_cache = json.load(f)
                logger.debug(f"加载了 {len(self._users_cache)} 个用户")
                return self._users_cache
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            raise DataLoadException("用户数据", str(e))
    
    def _load_roles(self) -> Dict[str, Any]:
        """加载角色数据"""
        if self._roles_cache is not None:
            return self._roles_cache
        
        try:
            if not self.roles_file.exists():
                logger.warning("角色文件不存在")
                return {}
            
            with open(self.roles_file, 'r', encoding='utf-8') as f:
                self._roles_cache = json.load(f)
                logger.debug(f"加载了 {len(self._roles_cache)} 个角色")
                return self._roles_cache
        except Exception as e:
            logger.error(f"加载角色数据失败: {e}")
            raise DataLoadException("角色数据", str(e))
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        获取单个用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息
            
        Raises:
            UserNotFoundException: 用户不存在
        """
        users = self._load_users()
        
        for user in users.values():
            if user.get("id") == user_id:
                return user
        
        raise UserNotFoundException(user_id)
    
    def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """
        获取指定角色的用户列表
        
        Args:
            role_id: 角色ID
            
        Returns:
            用户列表
        """
        users = self._load_users()
        result = []
        
        for user in users.values():
            user_roles = user.get("roleIds", []) or user.get("roles", [])
            
            if role_id == "guest":
                # 访客：没有角色的用户
                if not user_roles:
                    result.append(user)
            else:
                # 其他角色：包含指定角色的用户
                if role_id in user_roles:
                    result.append(user)
        
        logger.info(f"角色 {role_id} 有 {len(result)} 个用户")
        return result
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户权限信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            权限信息，包含可见的功能和区域
        """
        user = self.get_user(user_id)
        user_roles = user.get("roleIds", []) or user.get("roles", [])
        
        # 定义功能权限
        features = self._get_visible_features(user_roles)
        
        # 定义区域权限
        sections = self._get_visible_sections(user_roles)
        
        return {
            "user_id": user_id,
            "roles": user_roles,
            "features": features,
            "sections": sections
        }
    
    def _get_visible_features(self, user_roles: List[str]) -> List[Dict[str, Any]]:
        """获取用户可见的功能列表"""
        
        # 定义所有功能及其权限要求
        all_features = [
            {
                "id": "recharge",
                "title": "充值",
                "icon": "💰",
                "required_roles": ["student", "teacher", "reviewer", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "redeem",
                "title": "兑换",
                "icon": "🎁",
                "required_roles": ["student", "teacher", "reviewer", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "coupons",
                "title": "卡券",
                "icon": "🎫",
                "required_roles": ["student", "teacher", "reviewer", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "profile",
                "title": "个人信息",
                "icon": "👤",
                "required_roles": None  # 所有登录用户
            },
            {
                "id": "community",
                "title": "加入社群",
                "icon": "💬",
                "required_roles": None  # 所有登录用户
            },
            {
                "id": "checkin",
                "title": "集点打卡",
                "icon": "🗓️",
                "required_roles": ["student", "teacher", "systemAdmin", "superAdmin"]
            },
            {
                "id": "questions",
                "title": "题目管理",
                "icon": "🗂️",
                "required_roles": ["teacher", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "approvals",
                "title": "角色审批",
                "icon": "🛂",
                "required_roles": ["systemAdmin", "superAdmin"]
            },
            {
                "id": "stats",
                "title": "统计",
                "icon": "📊",
                "required_roles": ["systemAdmin", "superAdmin"]
            },
            {
                "id": "review",
                "title": "阅卷审核",
                "icon": "📝",
                "required_roles": ["reviewer", "systemAdmin", "superAdmin"]
            },
            {
                "id": "sysFlags",
                "title": "系统开关",
                "icon": "⚙️",
                "required_roles": ["superAdmin"]
            },
            {
                "id": "auditLogs",
                "title": "审计日志",
                "icon": "📜",
                "required_roles": ["superAdmin"]
            },
            {
                "id": "maintenance",
                "title": "维护模式",
                "icon": "🛠️",
                "required_roles": ["superAdmin"]
            }
        ]
        
        # 过滤用户可见的功能
        visible_features = []
        for feature in all_features:
            if feature["required_roles"] is None:
                # 所有登录用户可见
                visible_features.append(feature)
            elif any(role in user_roles for role in feature["required_roles"]):
                # 用户有所需角色
                visible_features.append(feature)
        
        return visible_features
    
    def _get_visible_sections(self, user_roles: List[str]) -> List[Dict[str, Any]]:
        """获取用户可见的区域列表"""
        
        # 定义所有区域及其权限要求
        all_sections = [
            {
                "id": "dashboard",
                "title": "概览",
                "required_roles": None  # 所有登录用户
            },
            {
                "id": "profile",
                "title": "个人资料",
                "required_roles": None
            },
            {
                "id": "roles",
                "title": "角色权限",
                "required_roles": None
            },
            {
                "id": "community",
                "title": "社群",
                "required_roles": None
            },
            {
                "id": "balance",
                "title": "账户",
                "required_roles": ["student", "teacher", "reviewer", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "admin-hub",
                "title": "管理面板",
                "required_roles": ["teacher", "reviewer", "academicAdmin", "systemAdmin", "superAdmin"]
            },
            {
                "id": "logout",
                "title": "退出登录",
                "required_roles": None
            }
        ]
        
        # 过滤用户可见的区域
        visible_sections = []
        for section in all_sections:
            if section["required_roles"] is None:
                visible_sections.append(section)
            elif any(role in user_roles for role in section["required_roles"]):
                visible_sections.append(section)
        
        return visible_sections
    
    def get_all_roles(self) -> Dict[str, Any]:
        """获取所有角色定义"""
        return self._load_roles()
    
    def clear_cache(self):
        """清除缓存"""
        self._users_cache = None
        self._roles_cache = None
        logger.debug("用户和角色缓存已清除")
