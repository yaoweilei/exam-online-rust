#!/usr/bin/env python3
"""
创建管理员用户脚本
"""

import json
import sys
from pathlib import Path
import bcrypt
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


def create_admin(username: str, password: str, email: str = None):
    """创建管理员用户"""
    users_file = settings.USER_DATA_DIR / "users.json"
    
    # 确保目录存在
    users_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载现有用户
    if users_file.exists():
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}
    
    # 检查用户名是否已存在
    if username in users:
        print(f"❌ 用户名 '{username}' 已存在")
        return False
    
    # 创建管理员用户
    user_id = f"admin_{len([u for u in users.values() if 'admin' in u.get('roles', [])])+1}"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    users[username] = {
        "id": user_id,
        "username": username,
        "password": hashed_password,
        "email": email,
        "roles": ["admin", "user"],
        "created_at": datetime.now().isoformat()
    }
    
    # 保存
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 管理员用户创建成功！")
    print(f"   用户名: {username}")
    print(f"   用户ID: {user_id}")
    print(f"   角色: admin, user")
    if email:
        print(f"   邮箱: {email}")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("创建管理员用户")
    print("=" * 60)
    print()
    
    # 交互式输入
    username = input("请输入管理员用户名: ").strip()
    if not username:
        print("❌ 用户名不能为空")
        sys.exit(1)
    
    password = input("请输入密码: ").strip()
    if not password or len(password) < 6:
        print("❌ 密码长度至少为 6 位")
        sys.exit(1)
    
    email = input("请输入邮箱（可选，直接回车跳过）: ").strip()
    email = email if email else None
    
    print()
    try:
        create_admin(username, password, email)
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
