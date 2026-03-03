# 在线试卷系统

基于原 exam-viewer VSCode 扩展改造的独立 Web 应用，保持原有精美样式。

## 技术栈

- **前端**: HTML5 + CSS3 + JavaScript (模块化架构)
- **后端**: Python 3.9+ + FastAPI
- **数据验证**: Pydantic
- **密码加密**: bcrypt
- **数据存储**: JSON 文件

## 功能特性

- ✅ 响应式设计，支持手机/平板/电脑
- ✅ 用户认证系统（注册/登录/权限管理）
- ✅ 试卷列表浏览和管理
- ✅ 在线答题和自动评分
- ✅ 学习进度跟踪
- ✅ 统计分析和薄弱点识别
- ✅ 音频播放（听力题）
- ✅ 振假名支持（日语）
- ✅ 答题卡功能
- ✅ 统一的错误处理和日志系统

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

重要配置项：
- `SECRET_KEY`: 生产环境请修改为随机字符串
- `DEBUG`: 生产环境设置为 False
- `CORS_ORIGINS`: 生产环境设置为实际域名
- `LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR）

### 3. 启动服务器

开发环境：
```bash
python server.py
```

生产环境：
```bash
ENV=production python server.py
```

或使用 uvicorn：
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4. 访问应用

打开浏览器访问: http://localhost:8000

## 项目结构

```
exam-online/
├── server.py                 # FastAPI 主服务器
├── requirements.txt          # Python 依赖
├── .env.example             # 环境变量示例
├── src/                     # 后端源码
│   ├── config.py           # 配置管理
│   ├── models.py           # Pydantic 数据模型
│   ├── exceptions.py       # 自定义异常
│   ├── middleware.py       # 中间件（异常处理/日志）
│   ├── logger.py           # 日志系统
│   ├── exam_service.py     # 试卷服务
│   ├── answer_service.py   # 答案服务
│   ├── auth_service.py     # 认证服务
│   ├── furigana_service.py # 振假名服务
│   └── statistics_service.py # 统计服务
├── static/                  # 前端静态文件
│   ├── index.html          # 主页面
│   ├── style.css           # 样式文件
│   ├── core/               # 核心模块
│   ├── managers/           # 管理器模块
│   ├── renderers/          # 渲染器模块
│   ├── utils/              # 工具模块
│   └── resource/           # 资源文件
├── templates/               # Jinja2 模板
└── data/                    # 数据目录
    ├── paper/              # 试卷数据
    │   └── jlpt/          # JLPT 试卷
    └── user/               # 用户数据
        ├── users.json      # 用户信息
        ├── roles.json      # 角色权限
        └── answers/        # 用户答案
```

## API 文档

启动服务器后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

主要 API 端点：

### 认证
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/verify` - 验证 Token

### 试卷
- `GET /api/exams` - 获取试卷列表
- `GET /api/exams/{exam_id}` - 获取试卷详情
- `POST /api/exams` - 创建试卷
- `DELETE /api/exams/{exam_id}` - 删除试卷

### 答案
- `POST /api/answers/submit` - 提交答案
- `GET /api/answers/{user_id}/{exam_id}` - 获取用户答案
- `GET /api/progress/{user_id}` - 获取学习进度

### 统计
- `GET /api/statistics/{user_id}` - 获取用户统计
- `GET /api/statistics/{user_id}/weak-points` - 获取薄弱点
- `GET /api/statistics/{user_id}/learning-curve` - 获取学习曲线

## 安全特性

- ✅ bcrypt 密码加密
- ✅ Token 认证机制
- ✅ 请求参数验证（Pydantic）
- ✅ 统一异常处理
- ✅ CORS 配置
- ✅ 日志记录

## 开发建议

1. **环境隔离**: 使用虚拟环境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **代码检查**: 使用 pylint 或 flake8
   ```bash
   pip install pylint
   pylint src/
   ```

3. **日志查看**: 设置 LOG_FILE 环境变量启用文件日志

## 生产部署建议

1. 修改 `.env` 配置：
   - 设置强密码的 `SECRET_KEY`
   - `DEBUG=False`
   - 配置实际的 `CORS_ORIGINS`
   - 设置 `LOG_FILE` 路径

2. 使用进程管理器（如 systemd、supervisor）

3. 配置反向代理（Nginx）

4. 启用 HTTPS

5. 定期备份数据目录

## 许可证

MIT License
