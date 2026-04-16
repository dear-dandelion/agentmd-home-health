# AgentMD Home Health Assistant

基于 AgentMD 思路实现的居家健康智能对话系统原型，当前包含：

- 多用户健康档案管理
- SQLite 持久化用户信息与评估历史
- 多轮对话状态机
- 意图识别、参数提取与工具选择
- 医疗计算器注册、优先级管理与质量验证
- 独立 Web 前端（HTML/CSS/JS）+ Python 后端

## 运行

```bash
pip install -r requirements.txt
python -m app.main
```

启动后访问 `http://127.0.0.1:7860` 即可进入系统界面。

如果 `7860` 端口已被占用，可以先设置环境变量再启动，例如：

```bash
set APP_PORT=7861
python -m app.main
```

## DeepSeek 配置

项目启动时会自动加载根目录下的 `.env` 文件。需要配置的字段如下：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

仓库中提供了 `.env.example` 作为模板。

如果未配置 DeepSeek API，系统仍可运行，但会回退到本地规则完成意图识别、参数提取和质量验证的兜底逻辑。

## 文献分类统计接口

系统新增了医疗计算器文献分类统计接口：

```bash
POST /api/literature/stats
Content-Type: application/json
```

示例请求：

```json
{
  "query": "CHA2DS2-VASc OR HAS-BLED OR FINDRISC OR PHQ-9 OR NEWS",
  "sources": ["pubmed", "sinomed"],
  "max_results_each": 20,
  "mindate": "2016/01/01",
  "maxdate": "2026/12/31"
}
```

返回内容包含：

- `categories`: 按心血管、代谢、老年、精神、呼吸、神经、综合 7 类输出匹配数量
- `target_total`: 论文目标分类总量，当前为 50
- `retrieved_total`: 实际检索到的文献数
- `provider_errors`: 各数据源失败原因
- `documents`: 单篇文献及其归类结果

### PubMed

PubMed 使用 NCBI E-utilities 直接检索，无需额外配置。若需更高配额，可设置：

```bash
NCBI_API_KEY=your_ncbi_api_key
NCBI_EMAIL=your_email@example.com
NCBI_TOOL=agentmd-home-health
```

### SinoMed

SinoMed 适配为可配置 REST 接口模式，需要按实际可用接口配置：

```bash
SINOMED_API_URL_TEMPLATE=https://your-sinomed-endpoint/search?q={query}&page={page}&pageSize={page_size}
SINOMED_AUTH_TOKEN=optional_token
SINOMED_COOKIE=optional_cookie
```

如果未配置 `SINOMED_API_URL_TEMPLATE`，接口仍可返回 PubMed 结果，并会在 `provider_errors` 中说明 SinoMed 未配置。
