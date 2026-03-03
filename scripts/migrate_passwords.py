#!/usr/bin/env python3
"""
密码迁移脚本 - 将旧的 SHA256 密码迁移到 bcrypt
"""

import json
import sys
from pathlib import Path
import bcrypt

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


def migrate_passwords():
    """迁移密码"""
    users_file = settings.USER_DATA_DIR / "users.json"
    
    if not users_file.exists():
        print("❌ 用户文件不存在，无需迁移")
        return
    
    # 备份原文件
    backup_file = users_file.with_suffix('.json.backup')
    print(f"📦 备份原文件到: {backup_file}")
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    # 迁移密码
    migrated_count = 0
    for username, user_data in users.items():
        old_password = user_data.get("password", "")
        
        # 检查是否已经是 bcrypt 格式（以 $2b$ 开头）
        if old_password.startswith("$2b$"):
            print(f"⏭️  跳过 {username}: 已经是 bcrypt 格式")
            continue
        
        # 对于旧的 SHA256 密码，我们无法直接转换
        # 需要用户重新设置密码，或者使用默认密码
        print(f"⚠️  {username}: 旧密码格式无法直接迁移")
        print(f"   建议: 1) 让用户重置密码，或 2) 设置临时密码")
        
        # 这里我们设置一个临时密码（与用户名相同）
        temp_password = username
        hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_data["password"] = hashed
        user_data["password_reset_required"] = True  # 标记需要重置密码
        
        print(f"✅ {username}: 已设置临时密码（与用户名相同），请提醒用户修改")
        migrated_count += 1
    
    # 保存更新后的用户数据
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 迁移完成！共迁移 {migrated_count} 个用户")
    print(f"📝 备份文件: {backup_file}")
    print(f"\n⚠️  重要提醒:")
    print(f"   - 所有迁移的用户临时密码已设置为其用户名")
    print(f"   - 请通知用户登录后立即修改密码")


if __name__ == "__main__":
    print("=" * 60)
    print("密码迁移工具 - SHA256 → bcrypt")
    print("=" * 60)
    print()
    
    try:
        migrate_passwords()
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
