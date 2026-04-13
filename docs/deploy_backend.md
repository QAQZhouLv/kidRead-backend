# KidRead 后端部署说明

## 1. 环境要求
- Python 3.12
- FastAPI
- SQLite
- 已配置 `.env` 中的 LLM / ASR / TTS 参数

## 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 3. 数据库迁移
本次优化新增了故事上下文字段和会话调试字段，首次拉取改版代码后请执行：

```bash
python migrate_story_context_20260410.py
```

## 4. 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. 验证方式
- 健康检查：`/health`
- Swagger：`/docs`
- 流式聊天：`/ws/chat/stream`
- 静态资源：`/static`

## 6. 本次改造重点
- 新增 StorySpec / StoryState / StorySummary 三层上下文
- 新增年龄分级规则库与内容安全检查
- 聊天接口改为优先从数据库回填故事上下文
- 归档和续写后自动刷新结构化故事信息
