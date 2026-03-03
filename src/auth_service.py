"""
认证服务 - 处理用户登录、注册和权限验证
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import secrets
from datetime import datetime, timedelta
import bcrypt
from src.logger import auth_logger
from src.exceptions import (
    InvalidCredentialsException,
    UserExistsException,
    TokenExpiredException,
    TokenInvalidException,
    DataLoadException,
    DataSaveException
)


class AuthService:
    """认证服务类"""
    
    def __init__(self, data_dir: Path):
        self.users_file = data_dir.parent / "user" / "users.json"
        self.roles_file = data_dir.parent / "user" / "roles.json"
        self.tokens = {}  # 简单的内存 token 存储，生产环境应该用 Redis
        
        # 确保文件存在
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.users_file.exists():
            self._init_users_file()
        if not self.roles_file.exists():
            self._init_roles_file()
    
    def _init_users_file(self):
        """初始化用户文件"""
        default_users = {
            "guest": {
                "id": "guest",
                "username": "guest",
                "password": self._hash_password("guest"),
                "roles": ["guest"],
                "created_at": datetime.now().isoformat()
            }
        }
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)
    
    def _init_roles_file(self):
        """初始化角色文件"""
        default_roles = {
            "guest": {
                "name": "guest",
                "permissions": ["view_exams", "submit_answers"],
                "description": "访客用户"
            },
            "user": {
                "name": "user",
                "permissions": ["view_exams", "submit_answers", "save_progress"],
                "description": "普通用户"
            },
            "admin": {
                "name": "admin",
                "permissions": ["*"],
                "description": "管理员"
            }
        }
        with open(self.roles_file, 'w', encoding='utf-8') as f:
            json.dump(default_roles, f, ensure_ascii=False, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """密码哈希 - 使用 bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            auth_logger.error(f"密码验证失败: {e}")
            return False
    
    def _generate_token(self) -> str:
        """生成随机 token"""
        return secrets.token_urlsafe(32)
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录成功返回用户信息和 token
            
        Raises:
            InvalidCredentialsException: 用户名或密码错误
            DataLoadException: 数据加载失败
        """
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception as e:
            auth_logger.error(f"加载用户数据失败: {e}")
            raise DataLoadException("用户数据", str(e))
        
        user = users.get(username)
        if not user:
            auth_logger.warning(f"登录失败: 用户不存在 - {username}")
            raise InvalidCredentialsException()
        
        # 验证密码
        if not self._verify_password(password, user.get("password", "")):
            auth_logger.warning(f"登录失败: 密码错误 - {username}")
            raise InvalidCredentialsException()
        
        # 生成 token
        token = self._generate_token()
        self.tokens[token] = {
            "user_id": user["id"],
            "username": username,
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        auth_logger.info(f"用户登录成功: {username}")
        
        return {
            "user_id": user["id"],
            "username": username,
            "roles": user.get("roles", []),
            "token": token
        }
    
    def register(self, username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱（可选）
            
        Returns:
            注册成功返回用户信息
            
        Raises:
            UserExistsException: 用户名已存在
            DataLoadException: 数据加载失败
            DataSaveException: 数据保存失败
        """
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception as e:
            auth_logger.error(f"加载用户数据失败: {e}")
            raise DataLoadException("用户数据", str(e))
        
        # 检查用户名是否已存在
        if username in users:
            auth_logger.warning(f"注册失败: 用户名已存在 - {username}")
            raise UserExistsException(username)
        
        # 创建新用户
        user_id = f"user_{len(users) + 1}"
        users[username] = {
            "id": user_id,
            "username": username,
            "password": self._hash_password(password),
            "email": email,
            "roles": ["user"],
            "created_at": datetime.now().isoformat()
        }
        
        # 保存
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            auth_logger.error(f"保存用户数据失败: {e}")
            raise DataSaveException("用户数据", str(e))
        
        auth_logger.info(f"用户注册成功: {username}")
        
        return {
            "user_id": user_id,
            "username": username,
            "roles": ["user"]
        }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证 token
        
        Args:
            token: 访问令牌
            
        Returns:
            有效返回用户信息
            
        Raises:
            TokenInvalidException: Token 无效
            TokenExpiredException: Token 已过期
        """
        token_data = self.tokens.get(token)
        if not token_data:
            auth_logger.warning("Token 验证失败: Token 不存在")
            raise TokenInvalidException()
        
        # 检查是否过期
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.now() > expires_at:
            del self.tokens[token]
            auth_logger.warning("Token 验证失败: Token 已过期")
            raise TokenExpiredException()
        
        return token_data
    
    def logout(self, token: str) -> bool:
        """
        用户登出
        
        Args:
            token: 访问令牌
            
        Returns:
            是否成功
        """
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """
        检查用户权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            是否有权限
        """
        try:
            # 获取用户角色
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            user = None
            for u in users.values():
                if u.get("id") == user_id:
                    user = u
                    break
            
            if not user:
                return False
            
            # 获取角色权限
            with open(self.roles_file, 'r', encoding='utf-8') as f:
                roles = json.load(f)
            
            user_roles = user.get("roles", [])
            for role_name in user_roles:
                role = roles.get(role_name)
                if not role:
                    continue
                
                permissions = role.get("permissions", [])
                if "*" in permissions or permission in permissions:
                    return True
            
            return False
        except Exception as e:
            print(f"权限检查失败: {e}")
            return False
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """
        获取用户角色
        
        Args:
            user_id: 用户ID
            
        Returns:
            角色列表
        """
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            for user in users.values():
                if user.get("id") == user_id:
                    return user.get("roles", [])
            
            return []
        except Exception as e:
            print(f"获取角色失败: {e}")
            return []
