# MiroFish Five Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all five features from the 2026-06-04 design spec: i18n, pre-run limits, stop/resume/reset report, LLM token/cost tracking, and project listing fix.

**Architecture:** Backend is Flask (Python) with file-based persistence under `backend/uploads/`. Frontend is Vue 3 with `<script setup>`. All new features are additive — no breaking changes to existing API shapes. A singleton reactive composable (`useLocale.js`) drives i18n across all Vue files. A new `UsageTracker` service accumulates per-project LLM spend, written to `uploads/usage/<project_id>.json`. Report cancellation uses a module-level `threading.Event` dict in `report_agent.py`.

**Tech Stack:** Python 3.11, Flask, Vue 3 (Composition API), Vite, OpenAI-SDK-compatible LLM calls, file-based JSON persistence.

---

## File Map

### New files
| Path | Purpose |
|---|---|
| `frontend/src/composables/useLocale.js` | Singleton reactive locale composable |
| `frontend/src/locales/zh.js` | Chinese translations (flat key-value) |
| `frontend/src/locales/en.js` | English translations (same keys) |
| `frontend/src/components/UsageCounter.vue` | Live token/cost counter widget |
| `backend/app/services/usage_tracker.py` | Thread-safe per-project LLM usage accumulator |
| `backend/app/api/usage.py` | `GET /api/usage/<project_id>` Flask blueprint |

### Modified files
| Path | What changes |
|---|---|
| `backend/app/api/__init__.py` | Register `usage_bp` |
| `backend/app/__init__.py` | Mount `usage_bp` at `/api/usage` |
| `backend/app/models/project.py` | Add `limits: dict` field to `Project` dataclass |
| `backend/app/utils/llm_client.py` | Add optional `project_id`, capture `response.usage` |
| `backend/app/services/report_agent.py` | Add `CANCELLED`/`BUDGET_EXCEEDED` to `ReportStatus`; add `_cancellation_events` + `request_stop`/`clear_stop` to `ReportManager`; add cancellation + budget checks to `generate_report()` section loop |
| `backend/app/api/report.py` | 3 new routes: stop, resume, reset |
| `backend/app/api/graph.py` | Pass `limits` from form data to project; `list_projects()` enriched with usage + derived status; post-build `limits_hit` flag |
| `backend/app/api/simulation.py` | Clamp persona list to `max_personas` |
| `frontend/src/store/pendingUpload.js` | Add `limits` field |
| `frontend/src/App.vue` | Fixed-position locale toggle button |
| `frontend/src/views/Home.vue` | Collapsible limits panel + i18n |
| `frontend/src/components/Step4Report.vue` | Stop/Resume/Reset buttons + i18n |
| `frontend/src/components/HistoryDatabase.vue` | Pulsing status badge, usage footer, smart routing, polling, i18n |
| `frontend/src/views/Process.vue` | UsageCounter + pass limits on API call + i18n |
| All other 9 Vue files | i18n string replacement only |

---

## Task 1: i18n Composable + Locale Files

**Files:**
- Create: `frontend/src/composables/useLocale.js`
- Create: `frontend/src/locales/zh.js`
- Create: `frontend/src/locales/en.js`

- [ ] **Step 1: Create `useLocale.js`**

```js
// frontend/src/composables/useLocale.js
import { ref } from 'vue'
import zh from '../locales/zh.js'
import en from '../locales/en.js'

const MAPS = { zh, en }
const locale = ref(localStorage.getItem('mirofish_locale') || 'zh')

export function useLocale() {
  const t = (key) => MAPS[locale.value]?.[key] ?? key
  const setLocale = (lang) => {
    locale.value = lang
    localStorage.setItem('mirofish_locale', lang)
  }
  return { locale, t, setLocale }
}
```

- [ ] **Step 2: Create `zh.js` with all Chinese strings**

```js
// frontend/src/locales/zh.js
export default {
  // nav
  'nav.github': '访问我们的Github主页',
  // home hero
  'home.tag': '简洁通用的群体智能引擎',
  'home.version': '/ v0.1-预览版',
  'home.titleLine1': '上传任意报告',
  'home.titleLine2': '即刻推演未来',
  'home.heroDesc1': '即使只有一段文字，MiroFish 也能基于其中的现实种子，全自动生成与之对应的至多百万级Agent构成的平行世界。通过上帝视角注入变量，在复杂的群体交互中寻找动态环境下的"局部最优解"',
  'home.heroDesc2': '让未来在 Agent 群中预演，让决策在百战后胜出',
  // home left panel
  'home.systemStatus': '系统状态',
  'home.ready': '准备就绪',
  'home.readyDesc': '预测引擎待命中，可上传多份非结构化数据以初始化模拟序列',
  'home.lowCost': '低成本',
  'home.lowCostDesc': '常规模拟平均5$/次',
  'home.highAvail': '高可用',
  'home.highAvailDesc': '最多百万级Agent模拟',
  'home.workflowSeq': '工作流序列',
  'home.step1Title': '图谱构建',
  'home.step1Desc': '现实种子提取 & 个体与群体记忆注入 & GraphRAG构建',
  'home.step2Title': '环境搭建',
  'home.step2Desc': '实体关系抽取 & 人设生成 & 环境配置Agent注入仿真参数',
  'home.step3Title': '开始模拟',
  'home.step3Desc': '双平台并行模拟 & 自动解析预测需求 & 动态更新时序记忆',
  'home.step4Title': '报告生成',
  'home.step4Desc': 'ReportAgent拥有丰富的工具集与模拟后环境进行深度交互',
  'home.step5Title': '深度互动',
  'home.step5Desc': '与模拟世界中的任意一位进行对话 & 与ReportAgent进行对话',
  // home console
  'home.seedLabel': '01 / 现实种子',
  'home.seedFormats': '支持格式: PDF, MD, TXT',
  'home.uploadDrag': '拖拽文件上传',
  'home.uploadClick': '或点击浏览文件系统',
  'home.promptLabel': '>_ 02 / 模拟提示词',
  'home.promptPlaceholder': '// 用自然语言输入模拟或预测需求（例.武大若发布撤销肖某处分的公告，会引发什么舆情走向）',
  'home.engineBadge': '引擎: MiroFish-V1.0',
  'home.startEngine': '启动引擎',
  'home.initializing': '初始化中...',
  'home.inputParams': '输入参数',
  // home advanced limits
  'home.advancedSettings': '▸ Advanced Settings',
  'home.advancedSettingsOpen': '▾ Advanced Settings',
  'home.maxNodes': 'Max graph nodes',
  'home.maxRelations': 'Max graph edges',
  'home.maxPersonas': 'Max agents',
  'home.maxLlmCalls': 'Max LLM calls',
  'home.limitsHitWarning': 'Graph build hit a size limit — results are partial.',
  // history
  'history.title': '推演记录',
  'history.noFiles': '暂无文件',
  'history.moreFiles': '个文件',
  'history.noProjects': '暂无推演记录',
  'history.startFirst': '在上方启动第一个推演',
  'history.statusBuilding': '构建图谱中...',
  'history.statusSimulating': '运行模拟中...',
  'history.statusReporting': '生成报告中...',
  'history.statusDone': '已完成',
  'history.statusFailed': '失败',
  'history.statusCancelled': '已取消',
  // process
  'process.navTitle': 'MIROFISH',
  'process.graphPanel': '实时知识图谱',
  'process.nodes': '节点',
  'process.relations': '关系',
  // report step
  'report.stop': '停止生成',
  'report.resume': '继续生成',
  'report.reset': '重新生成',
  'report.resetConfirm': '确认重新生成？这会删除已完成的章节。',
  'report.generating': '正在生成',
  'report.waitingAgent': '等待 Report Agent...',
  // usage counter
  'usage.tokens': '令牌',
  'usage.cost': '估计费用',
  'usage.calls': '调用次数',
}
```

- [ ] **Step 3: Create `en.js` with matching English strings**

```js
// frontend/src/locales/en.js
export default {
  // nav
  'nav.github': 'Visit our GitHub',
  // home hero
  'home.tag': 'Simple universal collective intelligence engine',
  'home.version': '/ v0.1-preview',
  'home.titleLine1': 'Upload any report',
  'home.titleLine2': 'Simulate the future',
  'home.heroDesc1': 'Even from a single paragraph, MiroFish auto-generates a parallel world of up to millions of Agents seeded from reality. Inject variables from a god\'s-eye view and find the "local optimum" in complex collective dynamics.',
  'home.heroDesc2': 'Let the future play out in Agent crowds. Let decisions win after a hundred battles.',
  // home left panel
  'home.systemStatus': 'System Status',
  'home.ready': 'Ready',
  'home.readyDesc': 'Prediction engine standing by. Upload unstructured data to initialize the simulation sequence.',
  'home.lowCost': 'Low Cost',
  'home.lowCostDesc': 'Average $5 per standard simulation',
  'home.highAvail': 'High Capacity',
  'home.highAvailDesc': 'Up to millions of agents',
  'home.workflowSeq': 'Workflow Sequence',
  'home.step1Title': 'Graph Build',
  'home.step1Desc': 'Reality seed extraction & memory injection & GraphRAG construction',
  'home.step2Title': 'Env Setup',
  'home.step2Desc': 'Entity extraction & persona generation & simulation config injection',
  'home.step3Title': 'Simulation',
  'home.step3Desc': 'Dual-platform parallel simulation & auto-parse prediction goals & dynamic memory updates',
  'home.step4Title': 'Report',
  'home.step4Desc': 'ReportAgent uses a rich toolset to deeply interact with the post-simulation environment',
  'home.step5Title': 'Deep Interaction',
  'home.step5Desc': 'Chat with any agent from the simulation & chat with the ReportAgent',
  // home console
  'home.seedLabel': '01 / Reality Seed',
  'home.seedFormats': 'Formats: PDF, MD, TXT',
  'home.uploadDrag': 'Drag files here',
  'home.uploadClick': 'or click to browse',
  'home.promptLabel': '>_ 02 / Simulation Prompt',
  'home.promptPlaceholder': '// Describe your simulation or prediction goal in natural language',
  'home.engineBadge': 'Engine: MiroFish-V1.0',
  'home.startEngine': 'Start Engine',
  'home.initializing': 'Initializing...',
  'home.inputParams': 'Parameters',
  // home advanced limits
  'home.advancedSettings': '▸ Advanced Settings',
  'home.advancedSettingsOpen': '▾ Advanced Settings',
  'home.maxNodes': 'Max graph nodes',
  'home.maxRelations': 'Max graph edges',
  'home.maxPersonas': 'Max agents',
  'home.maxLlmCalls': 'Max LLM calls',
  'home.limitsHitWarning': 'Graph build hit a size limit — results are partial.',
  // history
  'history.title': 'Simulation Records',
  'history.noFiles': 'No files',
  'history.moreFiles': 'files',
  'history.noProjects': 'No simulations yet',
  'history.startFirst': 'Start your first simulation above',
  'history.statusBuilding': 'Building graph...',
  'history.statusSimulating': 'Running simulation...',
  'history.statusReporting': 'Generating report...',
  'history.statusDone': 'Done',
  'history.statusFailed': 'Failed',
  'history.statusCancelled': 'Cancelled',
  // process
  'process.navTitle': 'MIROFISH',
  'process.graphPanel': 'Live Knowledge Graph',
  'process.nodes': 'nodes',
  'process.relations': 'edges',
  // report step
  'report.stop': 'Stop',
  'report.resume': 'Resume',
  'report.reset': 'Reset',
  'report.resetConfirm': 'Confirm reset? This will delete completed sections.',
  'report.generating': 'Generating',
  'report.waitingAgent': 'Waiting for Report Agent...',
  // usage counter
  'usage.tokens': 'Tokens',
  'usage.cost': 'Est. cost',
  'usage.calls': 'Calls',
}
```

- [ ] **Step 4: Verify the composable works by importing in the browser console (after App.vue toggle is added in Task 2)**

Manual check: open browser devtools, run `import('/src/composables/useLocale.js').then(m => console.log(m.useLocale()))` — should log `{ locale: Ref, t: fn, setLocale: fn }`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useLocale.js frontend/src/locales/zh.js frontend/src/locales/en.js
git commit -m "feat(i18n): add useLocale composable and zh/en locale files"
```

---

## Task 2: Language Toggle in App.vue

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add locale toggle to `App.vue`**

Replace the entire `App.vue` with:

```vue
<template>
  <router-view />
  <button class="locale-toggle" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">
    {{ locale === 'zh' ? 'EN' : '中' }}
  </button>
</template>

<script setup>
import { useLocale } from './composables/useLocale.js'
const { locale, setLocale } = useLocale()
</script>

<style>
/* Global style reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #000000;
  background-color: #ffffff;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #000000; }
::-webkit-scrollbar-thumb:hover { background: #333333; }
button { font-family: inherit; }

.locale-toggle {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  width: 40px;
  height: 40px;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  transition: all 0.2s;
}
.locale-toggle:hover {
  background: #000;
  color: #fff;
  border-color: #000;
}
</style>
```

- [ ] **Step 2: Start dev server and verify toggle renders**

```bash
cd /home/mario/Dev/MiroFish/frontend && npm run dev
```

Open `http://localhost:5173`. A small `EN` button should be fixed at the bottom-right. Clicking it should change to `中`. Refreshing should remember the choice.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(i18n): add fixed-position locale toggle to App.vue"
```

---

## Task 3: Project Model — `limits` Field

**Files:**
- Modify: `backend/app/models/project.py`

- [ ] **Step 1: Add `limits` field to `Project` dataclass**

In `project.py` at line 48, after `chunk_overlap: int = 50`, add:

```python
    # Pre-run limits (optional, empty dict = no limits)
    limits: Dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 2: Add `limits` to `to_dict()`**

In the `to_dict()` method (around line 57), add `"limits": self.limits` to the returned dict (anywhere in the dict is fine, after `"error"`):

```python
            "error": self.error,
            "limits": self.limits
```

- [ ] **Step 3: Add `limits` to `from_dict()`**

In `from_dict()` (around line 96), add `limits=data.get('limits', {})` to the `cls(...)` call:

```python
            error=data.get('error'),
            limits=data.get('limits', {})
```

- [ ] **Step 4: Verify existing project JSON still loads**

```bash
cd /home/mario/Dev/MiroFish/backend
python -c "
from app.models.project import ProjectManager
projects = ProjectManager.list_projects()
print(f'Loaded {len(projects)} projects, first limits: {projects[0].limits if projects else None}')
"
```

Expected: prints without error, `limits` is `{}` for the existing project.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/project.py
git commit -m "feat(limits): add limits field to Project dataclass"
```

---

## Task 4: UsageTracker Service

**Files:**
- Create: `backend/app/services/usage_tracker.py`

- [ ] **Step 1: Create `usage_tracker.py`**

```python
# backend/app/services/usage_tracker.py
import os
import json
import threading
from typing import Dict, Optional
from ..config import Config


class UsageTracker:
    """Thread-safe per-project LLM usage accumulator.

    Persists totals to uploads/usage/<project_id>.json.
    """

    RATE_TABLE = {
        'gpt-4o':      (5.00, 15.00),
        'gpt-4o-mini': (0.15,  0.60),
        'qwen-plus':   (0.50,  1.50),
        'qwen-turbo':  (0.30,  0.90),
        'claude':      (3.00, 15.00),
    }
    DEFAULT_RATE = (1.00, 3.00)

    _locks: Dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    USAGE_DIR = os.path.join(Config.UPLOAD_FOLDER, 'usage')

    @classmethod
    def _get_lock(cls, project_id: str) -> threading.Lock:
        with cls._locks_lock:
            if project_id not in cls._locks:
                cls._locks[project_id] = threading.Lock()
            return cls._locks[project_id]

    @classmethod
    def _get_path(cls, project_id: str) -> str:
        os.makedirs(cls.USAGE_DIR, exist_ok=True)
        return os.path.join(cls.USAGE_DIR, f"{project_id}.json")

    @classmethod
    def _load(cls, project_id: str) -> dict:
        path = cls._get_path(project_id)
        if not os.path.exists(path):
            return {"call_count": 0, "prompt_tokens": 0, "completion_tokens": 0}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def _save(cls, project_id: str, data: dict) -> None:
        path = cls._get_path(project_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    @classmethod
    def _rate_for(cls, model_name: str):
        name = (model_name or '').lower()
        for prefix, rate in cls.RATE_TABLE.items():
            if name.startswith(prefix):
                return rate
        return cls.DEFAULT_RATE

    @classmethod
    def record(cls, project_id: str, prompt_tokens: int, completion_tokens: int, model_name: str = '') -> None:
        if not project_id:
            return
        lock = cls._get_lock(project_id)
        try:
            with lock:
                data = cls._load(project_id)
                data['call_count'] = data.get('call_count', 0) + 1
                data['prompt_tokens'] = data.get('prompt_tokens', 0) + (prompt_tokens or 0)
                data['completion_tokens'] = data.get('completion_tokens', 0) + (completion_tokens or 0)
                data['model_name'] = model_name
                cls._save(project_id, data)
        except Exception:
            pass  # never crash the caller over tracking

    @classmethod
    def get_usage(cls, project_id: str) -> dict:
        data = cls._load(project_id)
        prompt = data.get('prompt_tokens', 0)
        completion = data.get('completion_tokens', 0)
        model = data.get('model_name', '')
        input_rate, output_rate = cls._rate_for(model)
        cost = (prompt / 1_000_000) * input_rate + (completion / 1_000_000) * output_rate
        return {
            "project_id": project_id,
            "call_count": data.get('call_count', 0),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "estimated_cost_usd": round(cost, 4),
        }

    @classmethod
    def reset(cls, project_id: str) -> None:
        lock = cls._get_lock(project_id)
        with lock:
            path = cls._get_path(project_id)
            if os.path.exists(path):
                os.remove(path)
```

- [ ] **Step 2: Verify usage tracker works**

```bash
cd /home/mario/Dev/MiroFish/backend
python -c "
from app.services.usage_tracker import UsageTracker
UsageTracker.record('test_proj', 1000, 500, 'gpt-4o')
print(UsageTracker.get_usage('test_proj'))
UsageTracker.reset('test_proj')
print(UsageTracker.get_usage('test_proj'))
"
```

Expected: first print shows call_count=1, total_tokens=1500, estimated_cost_usd > 0. Second print shows all zeros.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/usage_tracker.py
git commit -m "feat(usage): add UsageTracker service for per-project LLM cost accumulation"
```

---

## Task 5: LLMClient Usage Hook

**Files:**
- Modify: `backend/app/utils/llm_client.py`

- [ ] **Step 1: Add `project_id` parameter and usage recording to `LLMClient`**

Replace the entire `llm_client.py` with:

```python
"""
LLM client wrapper — uniform OpenAI-format calls with optional usage tracking.
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.project_id = project_id

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _record_usage(self, response) -> None:
        if not self.project_id:
            return
        try:
            usage = getattr(response, 'usage', None)
            if usage:
                from ..services.usage_tracker import UsageTracker
                UsageTracker.record(
                    project_id=self.project_id,
                    prompt_tokens=getattr(usage, 'prompt_tokens', 0) or 0,
                    completion_tokens=getattr(usage, 'completion_tokens', 0) or 0,
                    model_name=self.model,
                )
        except Exception:
            pass

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        self._record_usage(response)
        content = response.choices[0].message.content
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {cleaned}")
```

- [ ] **Step 2: Verify the change didn't break existing LLMClient construction**

```bash
cd /home/mario/Dev/MiroFish/backend
python -c "from app.utils.llm_client import LLMClient; c = LLMClient(); print('OK, model:', c.model)"
```

Expected: `OK, model: <whatever model is in .env>` (no exception).

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/llm_client.py
git commit -m "feat(usage): add project_id + usage recording to LLMClient"
```

---

## Task 6: Usage API Endpoint

**Files:**
- Create: `backend/app/api/usage.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/__init__.py`

- [ ] **Step 1: Create `usage.py`**

```python
# backend/app/api/usage.py
from flask import jsonify
from . import usage_bp
from ..services.usage_tracker import UsageTracker
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.usage')


@usage_bp.route('/<project_id>', methods=['GET'])
def get_usage(project_id: str):
    try:
        data = UsageTracker.get_usage(project_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"get_usage failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: Register `usage_bp` in `__init__.py`**

In `backend/app/api/__init__.py`, add `usage_bp` after `report_bp`:

```python
from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
usage_bp = Blueprint('usage', __name__)

from . import graph       # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report      # noqa: E402, F401
from . import usage       # noqa: E402, F401
```

- [ ] **Step 3: Mount `usage_bp` in the Flask app factory**

In `backend/app/__init__.py`, after the line `app.register_blueprint(report_bp, url_prefix='/api/report')`, add:

```python
    from .api import usage_bp
    app.register_blueprint(usage_bp, url_prefix='/api/usage')
```

Also update the existing import line at line 66 to include `usage_bp`:

```python
    from .api import graph_bp, simulation_bp, report_bp, usage_bp
```

- [ ] **Step 4: Verify the endpoint responds**

Start the backend:
```bash
cd /home/mario/Dev/MiroFish/backend && python run.py &
```
Test:
```bash
curl -s http://localhost:5000/api/usage/test_proj | python -m json.tool
```

Expected: `{"success": true, "data": {"project_id": "test_proj", "call_count": 0, ...}}`

```bash
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/usage.py backend/app/api/__init__.py backend/app/__init__.py
git commit -m "feat(usage): add GET /api/usage/<project_id> endpoint"
```

---

## Task 7: Report Cancellation Mechanism

**Files:**
- Modify: `backend/app/services/report_agent.py`

This task adds three things to `report_agent.py`:
1. `CANCELLED` and `BUDGET_EXCEEDED` values to `ReportStatus`
2. `_cancellation_events` dict + `request_stop` + `clear_stop` to `ReportManager`
3. Cancellation + budget check at the start of each section iteration in `generate_report()`

- [ ] **Step 1: Extend `ReportStatus` enum (line 388)**

Change:
```python
class ReportStatus(str, Enum):
    """报告状态"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
```
To:
```python
class ReportStatus(str, Enum):
    """报告状态"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXCEEDED = "budget_exceeded"
```

- [ ] **Step 2: Add `CancellationError` and `BudgetExceededError` exception classes**

After the `ReportStatus` class (before `ReportSection`), add:

```python
class CancellationError(Exception):
    """Raised when report generation is cooperatively cancelled."""


class BudgetExceededError(Exception):
    """Raised when the max_llm_calls budget is consumed."""
```

- [ ] **Step 3: Add cancellation support to `ReportManager`**

At the top of `ReportManager` class body (right after `REPORTS_DIR = ...`), add:

```python
    # module-level cancellation events keyed by report_id
    _cancellation_events: Dict[str, 'threading.Event'] = {}
    _events_lock = threading.Lock()

    @classmethod
    def request_stop(cls, report_id: str) -> None:
        import threading as _threading
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = _threading.Event()
            cls._cancellation_events[report_id].set()

    @classmethod
    def clear_stop(cls, report_id: str) -> None:
        import threading as _threading
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = _threading.Event()
            cls._cancellation_events[report_id].clear()

    @classmethod
    def get_cancellation_event(cls, report_id: str):
        import threading as _threading
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = _threading.Event()
            return cls._cancellation_events[report_id]
```

You also need to add `import threading` at the top of `report_agent.py` if it's not already there. Check with:
```bash
grep -n "^import threading" /home/mario/Dev/MiroFish/backend/app/services/report_agent.py
```
If absent, add `import threading` after the existing imports (e.g., after `from enum import Enum`).

- [ ] **Step 4: Add cancellation + budget check to the section loop in `generate_report()`**

The section loop begins at approximately line 1636:
```python
            for i, section in enumerate(outline.sections):
```

Add the cancellation and budget check at the start of the loop body (right after `section_num = i + 1`):

```python
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                
                # Cooperative cancellation check
                cancellation_event = ReportManager.get_cancellation_event(report_id)
                if cancellation_event.is_set():
                    report.status = ReportStatus.CANCELLED
                    report.error = "Stopped by user request"
                    ReportManager.save_report(report)
                    ReportManager.update_progress(
                        report_id, "cancelled", 
                        20 + int((i / len(outline.sections)) * 70),
                        "已停止生成",
                        completed_sections=completed_section_titles
                    )
                    raise CancellationError("Stopped by user request")
                
                # Budget check
                if hasattr(self, '_calls_remaining') and self._calls_remaining is not None:
                    if self._calls_remaining <= 0:
                        report.status = ReportStatus.BUDGET_EXCEEDED
                        report.error = "LLM call budget exhausted"
                        ReportManager.save_report(report)
                        raise BudgetExceededError("LLM call budget exhausted")
```

- [ ] **Step 5: Initialise `_calls_remaining` from limits in `ReportAgent`**

Find the `ReportAgent.__init__` method (search for `class ReportAgent`). Add `limits: dict = None` parameter and initialise `_calls_remaining`:

```bash
grep -n "class ReportAgent\|def __init__" /home/mario/Dev/MiroFish/backend/app/services/report_agent.py | head -10
```

In `ReportAgent.__init__`, add at the end:
```python
        max_calls = (limits or {}).get('max_llm_calls', None)
        self._calls_remaining = int(max_calls) if max_calls else None
```

Also decrement `_calls_remaining` in `_generate_section_react` — add these two lines right before any `self.llm.chat(...)` call inside that method:
```python
        if self._calls_remaining is not None:
            self._calls_remaining -= 1
```

(You only need to add it once per LLM call site in `_generate_section_react`. Search for `self.llm.chat` in that method to locate each one.)

- [ ] **Step 6: Handle `CancellationError` and `BudgetExceededError` in `generate_report()` exception handler**

Find the `except Exception as e:` block at the end of `generate_report()` (around line 1728+). Change it to:

```python
        except CancellationError:
            ReportManager.save_report(report)
            if progress_callback:
                progress_callback("cancelled", 
                    20 + int((len(completed_section_titles) / max(len(outline.sections if report.outline else [1]), 1)) * 70),
                    "已停止生成")
            return report
        
        except BudgetExceededError:
            ReportManager.save_report(report)
            if progress_callback:
                progress_callback("budget_exceeded", 
                    20 + int((len(completed_section_titles) / max(len(outline.sections if report.outline else [1]), 1)) * 70),
                    "LLM调用次数已达上限")
            return report
        
        except Exception as e:
            # ... existing except block unchanged ...
```

- [ ] **Step 7: Verify the enum values are importable**

```bash
cd /home/mario/Dev/MiroFish/backend
python -c "
from app.services.report_agent import ReportStatus, ReportManager
print(ReportStatus.CANCELLED, ReportStatus.BUDGET_EXCEEDED)
e = ReportManager.get_cancellation_event('test_report')
ReportManager.request_stop('test_report')
print('is_set:', e.is_set())
ReportManager.clear_stop('test_report')
print('after clear:', e.is_set())
"
```

Expected:
```
cancelled budget_exceeded
is_set: True
after clear: False
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/report_agent.py
git commit -m "feat(report): add CANCELLED/BUDGET_EXCEEDED statuses and cooperative cancellation"
```

---

## Task 8: Report Stop / Resume / Reset API Routes

**Files:**
- Modify: `backend/app/api/report.py`

- [ ] **Step 1: Add the three control routes to `report.py`**

At the very end of `report.py`, append:

```python
# ============== Report control: stop / resume / reset ==============

@report_bp.route('/<report_id>/stop', methods=['POST'])
def stop_report(report_id: str):
    """Request cooperative cancellation of a running report generation."""
    try:
        ReportManager.request_stop(report_id)
        return jsonify({"success": True, "message": f"Stop requested for {report_id}"})
    except Exception as e:
        logger.error(f"stop_report failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/resume', methods=['POST'])
def resume_report(report_id: str):
    """Resume a cancelled report from the last completed section."""
    import uuid, threading
    try:
        ReportManager.clear_stop(report_id)

        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report not found: {report_id}"}), 404

        # Determine how many sections are already done
        completed_sections = ReportManager.get_generated_sections(report_id)
        start_section_index = len(completed_sections)

        if start_section_index == 0:
            message = "Starting from beginning (no completed sections found)"
        else:
            message = f"Resuming from section {start_section_index + 1}"

        # Get simulation + project info to reconstruct the agent
        manager = SimulationManager()
        state = manager.get_simulation(report.simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation not found: {report.simulation_id}"}), 404

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project not found: {state.project_id}"}), 404

        graph_id = state.graph_id or project.graph_id
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_resume",
            metadata={"report_id": report_id, "start_section": start_section_index}
        )

        def run_resume():
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0, message=message)
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=report.simulation_id,
                    simulation_requirement=report.simulation_requirement,
                )
                def progress_callback(stage, progress, msg):
                    task_manager.update_task(task_id, progress=progress, message=f"[{stage}] {msg}")

                resumed = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id,
                    start_section_index=start_section_index,
                )
                ReportManager.save_report(resumed)
                task_manager.complete_task(task_id, result={"report_id": report_id, "status": resumed.status.value})
            except Exception as ex:
                logger.error(f"resume_report background failed: {ex}")
                task_manager.fail_task(task_id, str(ex))

        thread = threading.Thread(target=run_resume, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {"report_id": report_id, "task_id": task_id, "message": message}
        })

    except Exception as e:
        logger.error(f"resume_report failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/reset', methods=['POST'])
def reset_report(report_id: str):
    """Delete all section files + state for a report and regenerate from scratch."""
    import threading
    try:
        ReportManager.clear_stop(report_id)

        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report not found: {report_id}"}), 404

        # Delete all section files
        report_folder = ReportManager._get_report_folder(report_id)
        import glob
        for section_file in glob.glob(os.path.join(report_folder, 'section_*.md')):
            os.remove(section_file)
        outline_path = ReportManager._get_outline_path(report_id)
        if os.path.exists(outline_path):
            os.remove(outline_path)

        # Reset report status
        report.status = ReportStatus.PENDING
        report.outline = None
        report.markdown_content = ""
        report.error = None
        report.completed_at = ""
        ReportManager.save_report(report)

        # Get simulation + project info
        manager = SimulationManager()
        state = manager.get_simulation(report.simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation not found: {report.simulation_id}"}), 404

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project not found: {state.project_id}"}), 404

        graph_id = state.graph_id or project.graph_id
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_reset",
            metadata={"report_id": report_id}
        )

        def run_reset():
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0, message="Regenerating report from scratch...")
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=report.simulation_id,
                    simulation_requirement=report.simulation_requirement,
                )
                def progress_callback(stage, progress, msg):
                    task_manager.update_task(task_id, progress=progress, message=f"[{stage}] {msg}")

                regenerated = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id,
                )
                ReportManager.save_report(regenerated)
                task_manager.complete_task(task_id, result={"report_id": report_id, "status": regenerated.status.value})
            except Exception as ex:
                logger.error(f"reset_report background failed: {ex}")
                task_manager.fail_task(task_id, str(ex))

        thread = threading.Thread(target=run_reset, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {"report_id": report_id, "task_id": task_id, "message": "Regenerating from scratch"}
        })

    except Exception as e:
        logger.error(f"reset_report failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: Add `start_section_index` parameter to `generate_report()`**

The `resume` route calls `agent.generate_report(..., start_section_index=N)`. You need to add this parameter to `generate_report()`. Find the method signature:

```bash
grep -n "def generate_report" /home/mario/Dev/MiroFish/backend/app/services/report_agent.py
```

Change the signature to accept `start_section_index: int = 0`:
```python
    def generate_report(
        self,
        progress_callback: Optional[Callable] = None,
        report_id: Optional[str] = None,
        start_section_index: int = 0,
    ) -> 'Report':
```

Then in the section loop, skip already-completed sections:
```python
            for i, section in enumerate(outline.sections):
                if i < start_section_index:
                    # already done — include in context but skip generation
                    section_path = ReportManager._get_section_path(report_id, i + 1)
                    if os.path.exists(section_path):
                        with open(section_path, 'r', encoding='utf-8') as f:
                            section.content = f.read()
                        generated_sections.append(f"## {section.title}\n\n{section.content}")
                        completed_section_titles.append(section.title)
                    continue
                section_num = i + 1
                # ... rest of loop unchanged
```

- [ ] **Step 3: Test the stop endpoint manually**

```bash
cd /home/mario/Dev/MiroFish/backend && python run.py &
# In another terminal:
curl -s -X POST http://localhost:5000/api/report/test_report_id/stop | python -m json.tool
```

Expected: `{"success": true, "message": "Stop requested for test_report_id"}`

```bash
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/report.py backend/app/services/report_agent.py
git commit -m "feat(report): add stop/resume/reset API routes with cooperative cancellation"
```

---

## Task 9: Pre-run Limits Enforcement — Backend

**Files:**
- Modify: `backend/app/api/graph.py` (save limits from form data + limits_hit in task result)
- Modify: `backend/app/api/simulation.py` (clamp personas)

### 9a: Store limits when creating project

- [ ] **Step 1: In `graph.py` `generate_ontology()`, extract limits from the form and save to project**

After `project.simulation_requirement = simulation_requirement` (around line 177), add:

```python
        # Store pre-run limits if provided
        project.limits = {
            k: int(v) for k, v in {
                'max_nodes': request.form.get('max_nodes'),
                'max_relations': request.form.get('max_relations'),
                'max_personas': request.form.get('max_personas'),
                'max_llm_calls': request.form.get('max_llm_calls'),
            }.items() if v is not None
        }
```

### 9b: Return `limits_hit` after graph build

- [ ] **Step 2: In `graph.py` `build_task()`, check node/edge counts against limits and set `limits_hit`**

After `graph_data = builder.get_graph_data(graph_id)` (around line 465), before the `project.status = ProjectStatus.GRAPH_COMPLETED` line, add:

```python
                # Check limits
                limits = project.limits or {}
                limits_hit = []
                max_nodes = limits.get('max_nodes')
                max_relations = limits.get('max_relations')
                if max_nodes and node_count >= max_nodes:
                    limits_hit.append('max_nodes')
                if max_relations and edge_count >= max_relations:
                    limits_hit.append('max_relations')
```

Then in the task completion call, add `limits_hit` to the result:

```python
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="图谱构建完成",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks,
                        "limits_hit": limits_hit,
                    }
                )
```

### 9c: Clamp personas in simulation prepare

- [ ] **Step 3: In `simulation.py` `run_prepare()`, clamp agents to `max_personas`**

Find the `prepare_simulation` function's inner `run_prepare()`. Before `result_state = manager.prepare_simulation(...)`, add the entity count clamping. Actually this is trickier because the clamping happens inside `manager.prepare_simulation()`. 

Instead, modify the `parallel_profile_count` or pass max_personas through. Since `SimulationManager.prepare_simulation()` reads entities from Zep and iterates, we need to pass a `max_personas` limit. 

Check `simulate.py` for `prepare_simulation` call and add `max_personas` kwarg:

```bash
grep -n "def prepare_simulation\|max_personas" /home/mario/Dev/MiroFish/backend/app/services/simulation_manager.py | head -10
```

If `SimulationManager.prepare_simulation()` doesn't accept `max_personas`, add it to its signature and use it to truncate `entities` before profile generation:
```python
def prepare_simulation(self, ..., max_personas: int = None, ...):
    ...
    # After getting filtered entities:
    if max_personas and len(entities) > max_personas:
        entities = entities[:max_personas]
        logger.warning(f"Clamped to max_personas={max_personas}")
```

Then in `simulation.py` `prepare_simulation()` route handler, extract the limit and pass it:
```python
        project = ProjectManager.get_project(state.project_id)
        max_personas = (project.limits or {}).get('max_personas') if project else None
        # ...
        result_state = manager.prepare_simulation(
            ...,
            max_personas=max_personas,
        )
```

- [ ] **Step 4: Verify limits are stored on project after ontology generation**

After starting the backend, create a project with limits via curl:
```bash
cd /home/mario/Dev/MiroFish/backend && python run.py &
curl -s -X POST http://localhost:5000/api/graph/ontology/generate \
  -F "simulation_requirement=test" \
  -F "max_nodes=50" \
  -F "files=@/dev/null;type=text/plain" 2>&1 | python -m json.tool | head -5
# (will fail file validation but we just want to see if form parsing works)
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/graph.py backend/app/api/simulation.py backend/app/services/simulation_manager.py
git commit -m "feat(limits): enforce max_nodes/relations/personas/llm_calls in backend pipeline"
```

---

## Task 10: Enrich Project List API

**Files:**
- Modify: `backend/app/api/graph.py`

The existing `GET /api/graph/project/list` returns basic project data. We need to enrich each item with: `simulation_id`, `report_id`, derived `status` (from simulation + run state), and `usage`.

- [ ] **Step 1: Replace `list_projects()` in `graph.py` with enriched version**

Find the existing `list_projects()` route (lines 54-66). Replace it:

```python
@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """List all projects, enriched with simulation status and usage data."""
    import json
    from ..services.simulation_manager import SimulationManager
    from ..services.simulation_runner import SimulationRunner
    from ..services.report_agent import ReportManager
    from ..services.usage_tracker import UsageTracker

    limit = request.args.get('limit', 20, type=int)
    projects = ProjectManager.list_projects(limit=limit)

    result = []
    sim_manager = SimulationManager()

    for project in projects:
        item = project.to_dict()

        # Find most-recent simulation for this project
        simulations = sim_manager.list_simulations(project_id=project.project_id)
        sim = simulations[0] if simulations else None

        item['simulation_id'] = sim.simulation_id if sim else None

        # Find report for that simulation
        report_id = None
        if sim:
            report = ReportManager.get_report_by_simulation(sim.simulation_id)
            report_id = report.report_id if report else None
        item['report_id'] = report_id

        # Derive unified status string
        if sim:
            run_state = SimulationRunner.get_run_state(sim.simulation_id) if sim else None
            sim_status = sim.status.value if hasattr(sim.status, 'value') else str(sim.status)
            if run_state and getattr(run_state, 'runner_status', None):
                runner_status = run_state.runner_status.value
            else:
                runner_status = 'idle'

            if runner_status == 'running':
                derived_status = 'simulating'
            elif report_id:
                report_obj = ReportManager.get_report(report_id)
                rep_status = report_obj.status.value if report_obj else 'unknown'
                if rep_status == 'generating':
                    derived_status = 'reporting'
                elif rep_status == 'completed':
                    derived_status = 'done'
                elif rep_status in ('cancelled', 'budget_exceeded', 'failed'):
                    derived_status = rep_status
                else:
                    derived_status = sim_status
            elif sim_status in ('preparing', 'ready', 'running', 'paused', 'completed'):
                derived_status = 'simulating' if sim_status in ('preparing', 'running') else sim_status
            elif project.status.value == 'graph_building':
                derived_status = 'building'
            else:
                derived_status = project.status.value
        else:
            status_map = {
                'graph_building': 'building',
                'graph_completed': 'building',
                'ontology_generated': 'building',
            }
            derived_status = status_map.get(project.status.value, project.status.value)

        item['status'] = derived_status

        # Usage data
        item['usage'] = UsageTracker.get_usage(project.project_id)

        result.append(item)

    return jsonify({
        "success": True,
        "data": result,
        "count": len(result)
    })
```

- [ ] **Step 2: Verify enriched list returns correctly**

```bash
cd /home/mario/Dev/MiroFish/backend && python run.py &
curl -s http://localhost:5000/api/graph/project/list | python -m json.tool | head -30
kill %1
```

Expected: each project item has `simulation_id`, `report_id`, `status`, and `usage` fields.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/graph.py
git commit -m "feat(listing): enrich GET /api/graph/project/list with status, simulation_id, report_id, usage"
```

---

## Task 11: UsageCounter.vue Component

**Files:**
- Create: `frontend/src/components/UsageCounter.vue`

- [ ] **Step 1: Create `UsageCounter.vue`**

```vue
<template>
  <div v-if="usage" class="usage-counter">
    <span class="usage-item">{{ t('usage.tokens') }}: {{ usage.total_tokens.toLocaleString() }}</span>
    <span class="usage-sep">|</span>
    <span class="usage-item">{{ t('usage.cost') }}: ${{ usage.estimated_cost_usd }}</span>
    <span class="usage-sep">|</span>
    <span class="usage-item">{{ t('usage.calls') }}: {{ usage.call_count }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useLocale } from '../composables/useLocale.js'

const props = defineProps({
  projectId: { type: String, default: null },
  active: { type: Boolean, default: true },
})

const { t } = useLocale()
const usage = ref(null)
let timer = null

async function fetchUsage() {
  if (!props.projectId) return
  try {
    const res = await fetch(`/api/usage/${props.projectId}`)
    const json = await res.json()
    if (json.success) usage.value = json.data
  } catch { /* ignore — counter shows nothing on failure */ }
}

function start() {
  fetchUsage()
  timer = setInterval(fetchUsage, 3000)
}

function stop() {
  clearInterval(timer)
  timer = null
}

onMounted(() => { if (props.active && props.projectId) start() })
onUnmounted(() => stop())

watch(() => [props.active, props.projectId], ([active, pid]) => {
  stop()
  if (active && pid) start()
})
</script>

<style scoped>
.usage-counter {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #666;
  padding: 6px 12px;
  background: #f5f5f5;
  border: 1px solid #e5e5e5;
}
.usage-sep { color: #ccc; }
.usage-item { white-space: nowrap; }
</style>
```

- [ ] **Step 2: Verify it renders with a known project_id**

In a Vue file that has a known project ID, temporarily add `<UsageCounter project-id="proj_b878ab75ea2d" :active="true" />` and start the dev server. Confirm the counter appears and polls every 3 seconds (watch Network tab).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/UsageCounter.vue
git commit -m "feat(usage): add UsageCounter.vue polling component"
```

---

## Task 12: Home.vue — Limits Panel + i18n

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/store/pendingUpload.js`

### 12a: Add `limits` to the pending upload store

- [ ] **Step 1: Update `pendingUpload.js`**

Replace the entire file:

```js
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  limits: {},
  isPending: false
})

export function setPendingUpload(files, requirement, limits = {}) {
  state.files = files
  state.simulationRequirement = requirement
  state.limits = limits
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    limits: state.limits,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.limits = {}
  state.isPending = false
}

export default state
```

### 12b: Update Home.vue

- [ ] **Step 2: Add i18n + limits panel to `Home.vue`**

At the top of `<script setup>`, add:
```js
import { useLocale } from '../composables/useLocale.js'
const { t } = useLocale()
```

Add reactive limits state and advanced settings toggle:
```js
const showAdvanced = ref(false)
const limits = ref({
  max_nodes: 500,
  max_relations: 2000,
  max_personas: 20,
  max_llm_calls: 200,
})
```

Update `startSimulation()` to pass limits:
```js
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, limits.value)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}
```

In the template, replace the hardcoded Chinese strings with `t('...')` calls (using the keys from Task 1). For example:
- `访问我们的Github主页` → `{{ t('nav.github') }}`
- `启动引擎` → `{{ t('home.startEngine') }}`
- `初始化中...` → `{{ t('home.initializing') }}`

Add the advanced settings panel **inside `.console-box`** right before the `<!-- 启动按钮 -->` section:

```html
<!-- Advanced Settings toggle -->
<div class="console-section advanced-section">
  <button class="advanced-toggle" @click="showAdvanced = !showAdvanced">
    {{ showAdvanced ? t('home.advancedSettingsOpen') : t('home.advancedSettings') }}
  </button>
  <div v-if="showAdvanced" class="limits-grid">
    <label class="limit-label">
      {{ t('home.maxNodes') }}
      <input type="number" v-model.number="limits.max_nodes" min="50" max="5000" class="limit-input" />
    </label>
    <label class="limit-label">
      {{ t('home.maxRelations') }}
      <input type="number" v-model.number="limits.max_relations" min="100" max="20000" class="limit-input" />
    </label>
    <label class="limit-label">
      {{ t('home.maxPersonas') }}
      <input type="number" v-model.number="limits.max_personas" min="2" max="200" class="limit-input" />
    </label>
    <label class="limit-label">
      {{ t('home.maxLlmCalls') }}
      <input type="number" v-model.number="limits.max_llm_calls" min="10" max="2000" class="limit-input" />
    </label>
  </div>
</div>
```

Add the warning banner in `.console-box` (above the upload zone) — it shows only when `limitsHitWarning` is truthy (set this from Process.vue via a store or query param in a later task):
```html
<div v-if="limitsHitWarning" class="limits-warning">{{ t('home.limitsHitWarning') }}</div>
```

Add styles to `<style scoped>`:
```css
.advanced-toggle {
  background: none;
  border: none;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
  cursor: pointer;
  padding: 0;
  text-align: left;
}
.limits-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.limit-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
}
.limit-input {
  border: 1px solid #ddd;
  padding: 6px 8px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  width: 100%;
}
.limits-warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 8px 12px;
  font-size: 0.8rem;
  margin-bottom: 8px;
}
```

- [ ] **Step 3: Verify the limits panel toggles**

```bash
cd /home/mario/Dev/MiroFish/frontend && npm run dev
```

Open `http://localhost:5173`. Click "▸ Advanced Settings" — four number inputs should appear. Change values. Click "启动引擎" with a file and requirement — should navigate to Process page.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/Home.vue frontend/src/store/pendingUpload.js
git commit -m "feat(home): add collapsible limits panel and i18n to Home.vue"
```

---

## Task 13: Step4Report.vue — Stop / Resume / Reset Buttons + i18n

**Files:**
- Modify: `frontend/src/components/Step4Report.vue`

- [ ] **Step 1: Add stop/resume/reset API functions to `frontend/src/api/report.js`**

```bash
cat /home/mario/Dev/MiroFish/frontend/src/api/report.js | head -20
```

Append to `report.js`:
```js
export const stopReport = (reportId) =>
  service.post(`/api/report/${reportId}/stop`)

export const resumeReport = (reportId) =>
  service.post(`/api/report/${reportId}/resume`)

export const resetReport = (reportId) =>
  service.post(`/api/report/${reportId}/reset`)
```

- [ ] **Step 2: Add reactive `reportStatus` and control buttons to `Step4Report.vue`**

In `<script setup>`, add imports:
```js
import { useLocale } from '../composables/useLocale.js'
import { stopReport, resumeReport, resetReport } from '../api/report.js'
const { t } = useLocale()
```

Find where `reportStatus` or report `status` is tracked in the component. If not already tracked, add:
```js
const reportStatus = computed(() => {
  // read from the existing report polling logic
  return props.reportData?.status ?? 'pending'
})
```

Add control button handlers:
```js
async function handleStop() {
  if (!props.reportId) return
  await stopReport(props.reportId)
}

async function handleResume() {
  if (!props.reportId) return
  await resumeReport(props.reportId)
}

async function handleReset() {
  if (!props.reportId) return
  if (!confirm(t('report.resetConfirm'))) return
  await resetReport(props.reportId)
}
```

In the template, add the three conditional action buttons. Insert them in the report panel header area (near the existing status indicator), before the report outline section:

```html
<!-- Report control buttons -->
<div class="report-controls">
  <button
    v-if="reportStatus === 'generating'"
    class="ctrl-btn ctrl-stop"
    @click="handleStop"
  >{{ t('report.stop') }}</button>

  <button
    v-if="reportStatus === 'cancelled' || reportStatus === 'failed' || reportStatus === 'budget_exceeded'"
    class="ctrl-btn ctrl-resume"
    @click="handleResume"
  >{{ t('report.resume') }}</button>

  <button
    v-if="reportStatus !== 'generating'"
    class="ctrl-btn ctrl-reset"
    @click="handleReset"
  >{{ t('report.reset') }}</button>
</div>
```

Add styles:
```css
.report-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.ctrl-btn {
  padding: 6px 14px;
  border: 1px solid #000;
  background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}
.ctrl-stop:hover { background: #fee2e2; border-color: #ef4444; }
.ctrl-resume:hover { background: #d1fae5; border-color: #10b981; }
.ctrl-reset:hover { background: #f3f4f6; }
```

Also replace the Chinese string `正在生成{{ section.title }}...` with:
```html
<span class="loading-text">{{ t('report.generating') }} {{ section.title }}...</span>
```

And `Waiting for Report Agent...` with `{{ t('report.waitingAgent') }}`.

- [ ] **Step 3: Verify buttons render**

Start dev server, navigate to a project at Step 4. Verify the Reset button is visible. If the report is generating, Stop should be visible.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Step4Report.vue frontend/src/api/report.js
git commit -m "feat(report): add stop/resume/reset control buttons to Step4Report.vue"
```

---

## Task 14: HistoryDatabase.vue — Enriched Cards + Polling + i18n

**Files:**
- Modify: `frontend/src/components/HistoryDatabase.vue`

- [ ] **Step 1: Add i18n import and polling logic**

At the top of `<script setup>`:
```js
import { useLocale } from '../composables/useLocale.js'
const { t } = useLocale()
```

Find where `projects` data is loaded. If it currently polls via `onMounted`, change polling to:
```js
const TERMINAL_STATUSES = ['done', 'failed', 'cancelled', 'budget_exceeded', 'completed']
let pollTimer = null

async function loadProjects() {
  try {
    const res = await fetch('/api/graph/project/list')
    const json = await res.json()
    if (json.success) {
      projects.value = json.data
    }
    // stop polling if all terminal
    const hasActive = (json.data || []).some(p => !TERMINAL_STATUSES.includes(p.status))
    if (!hasActive && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  loadProjects()
  pollTimer = setInterval(loadProjects, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
```

- [ ] **Step 2: Add status badge to each card**

In the existing card template, add a status badge after the card header:

```html
<!-- Status badge: pulsing if active -->
<div
  class="status-badge"
  :class="[`status-${project.status}`, { 'is-active': !['done','failed','cancelled'].includes(project.status) }]"
>
  <span v-if="project.status === 'building'">{{ t('history.statusBuilding') }}</span>
  <span v-else-if="project.status === 'simulating'">{{ t('history.statusSimulating') }}</span>
  <span v-else-if="project.status === 'reporting'">{{ t('history.statusReporting') }}</span>
  <span v-else-if="project.status === 'done'">{{ t('history.statusDone') }}</span>
  <span v-else-if="project.status === 'failed'">{{ t('history.statusFailed') }}</span>
  <span v-else-if="project.status === 'cancelled'">{{ t('history.statusCancelled') }}</span>
</div>
```

- [ ] **Step 3: Add usage footer to each card**

Below the existing card content, before the closing `</div>` of the card:

```html
<!-- Usage footer -->
<div class="card-usage" v-if="project.usage && project.usage.total_tokens > 0">
  <span>{{ project.usage.total_tokens.toLocaleString() }} tokens</span>
  <span class="usage-cost">${{ project.usage.estimated_cost_usd }}</span>
</div>
```

- [ ] **Step 4: Update `navigateToProject()` to route to correct step based on `status`**

Find existing `navigateToProject(project)`. Replace with smart routing:

```js
function navigateToProject(project) {
  if (!project.simulation_id && !project.project_id) return
  const status = project.status
  if (status === 'done' && project.report_id) {
    router.push({ path: `/report/${project.report_id}` })
  } else if (status === 'reporting' && project.report_id) {
    router.push({ path: `/report/${project.report_id}` })
  } else if (project.simulation_id) {
    router.push({ name: 'Process', params: { projectId: project.project_id } })
  } else {
    router.push({ name: 'Process', params: { projectId: project.project_id } })
  }
}
```

- [ ] **Step 5: Add empty state when `projects.length === 0`**

In the section header area, add:
```html
<div v-if="projects.length === 0 && !loading" class="empty-state">
  <p>{{ t('history.noProjects') }}</p>
  <p class="empty-hint">{{ t('history.startFirst') }}</p>
</div>
```

Add styles:
```css
.status-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  padding: 2px 6px;
  border: 1px solid currentColor;
  display: inline-block;
}
.is-active { animation: pulse-status 1.5s ease-in-out infinite; }
@keyframes pulse-status {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.status-done { color: #10b981; }
.status-building, .status-simulating, .status-reporting { color: #f59e0b; }
.status-failed, .status-cancelled { color: #ef4444; }
.card-usage {
  display: flex;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #999;
  padding: 6px 0 2px;
  border-top: 1px solid #eee;
  margin-top: 8px;
}
.usage-cost { color: #666; }
.empty-state { text-align: center; padding: 40px; color: #999; }
.empty-hint { font-size: 0.85rem; margin-top: 8px; }
```

Also replace `推演记录` with `{{ t('history.title') }}` and `暂无文件` with `{{ t('history.noFiles') }}`.

- [ ] **Step 6: Verify enriched cards and polling**

Start dev server. Navigate to Home page. Cards should show status badges. Open devtools Network tab — should see `/api/graph/project/list` requests every 5 seconds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/HistoryDatabase.vue
git commit -m "feat(history): enrich cards with status, usage, polling, smart routing, and i18n"
```

---

## Task 15: Process.vue — UsageCounter Injection + Limits Pass-through + i18n

**Files:**
- Modify: `frontend/src/views/Process.vue`

- [ ] **Step 1: Import and inject `UsageCounter`**

In `<script setup>`:
```js
import UsageCounter from '../components/UsageCounter.vue'
import { useLocale } from '../composables/useLocale.js'
const { t } = useLocale()
```

Find `projectId` or `projectData.project_id` — this is already available in Process.vue from the route params and project API call. Confirm:
```bash
grep -n "projectId\|project_id\|projectData" /home/mario/Dev/MiroFish/frontend/src/views/Process.vue | head -10
```

In the template, add `<UsageCounter>` at the top of the active step panel (inside the main content area, above the step component). Find where the step components are rendered:
```bash
grep -n "Step1\|Step2\|Step3\|step-component\|currentStep\|activeStep" /home/mario/Dev/MiroFish/frontend/src/views/Process.vue | head -10
```

Add just above the first step component:
```html
<UsageCounter
  :project-id="projectData?.project_id"
  :active="!terminalStatus"
/>
```

Where `terminalStatus` is `computed(() => ['done', 'failed', 'cancelled'].includes(derivedStatus.value))`.

- [ ] **Step 2: Pass limits from `pendingUpload` to the `generateOntology` API call**

Find the `handleNewProject()` function (around line 567). After `formDataObj.append('simulation_requirement', pending.simulationRequirement)`, add:
```js
    // Pass limits as form fields
    const limits = pending.limits || {}
    if (limits.max_nodes) formDataObj.append('max_nodes', limits.max_nodes)
    if (limits.max_relations) formDataObj.append('max_relations', limits.max_relations)
    if (limits.max_personas) formDataObj.append('max_personas', limits.max_personas)
    if (limits.max_llm_calls) formDataObj.append('max_llm_calls', limits.max_llm_calls)
```

- [ ] **Step 3: Replace visible Chinese strings in Process.vue with `t()` calls**

Run:
```bash
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/Process.vue | head -30
```

For each Chinese string, add its key to `zh.js`/`en.js` (Task 1) and replace with `{{ t('process.xyz') }}`. Key strings to replace:
- `实时知识图谱` → `{{ t('process.graphPanel') }}`
- `节点` → `{{ t('process.nodes') }}`
- `关系` → `{{ t('process.relations') }}`
- Other strings found by the grep above

- [ ] **Step 4: Verify UsageCounter appears on the Process page**

Start dev server. Start a new simulation or load an existing project. The UsageCounter bar should appear above the step panels and update every 3 seconds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Process.vue
git commit -m "feat(process): inject UsageCounter, pass limits to API, add i18n"
```

---

## Task 16: i18n Sweep — Remaining Vue Files

**Files:**
- Modify: `frontend/src/views/MainView.vue`
- Modify: `frontend/src/views/SimulationRunView.vue`
- Modify: `frontend/src/views/SimulationView.vue`
- Modify: `frontend/src/views/ReportView.vue`
- Modify: `frontend/src/views/InteractionView.vue`
- Modify: `frontend/src/components/Step1GraphBuild.vue`
- Modify: `frontend/src/components/Step2EnvSetup.vue`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`

For each file, follow the same pattern:

- [ ] **Step 1: Find all Chinese strings in the file**

```bash
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/MainView.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/SimulationRunView.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/SimulationView.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/ReportView.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/views/InteractionView.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/components/Step1GraphBuild.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/components/Step2EnvSetup.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/components/Step3Simulation.vue
grep -n '[^\x00-\x7F]' /home/mario/Dev/MiroFish/frontend/src/components/Step5Interaction.vue
```

- [ ] **Step 2: For each Chinese string found, add a key to `zh.js` and `en.js`**

Use namespace prefixes:
- `sim.*` for simulation-related strings
- `step1.*` for Step1GraphBuild
- `step2.*` for Step2EnvSetup
- `step3.*` for Step3Simulation
- `step5.*` for Step5Interaction
- `main.*` for MainView
- `interaction.*` for InteractionView
- `report.*` (already started) for ReportView

- [ ] **Step 3: In each file, add `useLocale` import and replace strings**

Standard pattern for every file:
```js
// in <script setup>
import { useLocale } from '../composables/useLocale.js'  // adjust path if in components/
const { t } = useLocale()
```
Then replace each hardcoded Chinese string `"中文字符串"` with `t('namespace.key')`.

- [ ] **Step 4: Verify no Chinese strings remain in the 9 files**

```bash
for f in \
  frontend/src/views/MainView.vue \
  frontend/src/views/SimulationRunView.vue \
  frontend/src/views/SimulationView.vue \
  frontend/src/views/ReportView.vue \
  frontend/src/views/InteractionView.vue \
  frontend/src/components/Step1GraphBuild.vue \
  frontend/src/components/Step2EnvSetup.vue \
  frontend/src/components/Step3Simulation.vue \
  frontend/src/components/Step5Interaction.vue
do
  count=$(grep -c '[^\x00-\x7F]' "/home/mario/Dev/MiroFish/$f" 2>/dev/null || echo 0)
  echo "$f: $count non-ASCII chars"
done
```

Expected: all counts are 0 (or very close — the regex also matches non-Chinese Unicode in comments; inspect residuals manually).

- [ ] **Step 5: Do a full UI smoke test**

Start dev server. Toggle locale to EN. Navigate through: Home → start a project → Process page steps → HistoryDatabase. All visible text should switch to English. Toggle back to 中 — all text switches back.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/locales/zh.js frontend/src/locales/en.js \
  frontend/src/views/MainView.vue \
  frontend/src/views/SimulationRunView.vue \
  frontend/src/views/SimulationView.vue \
  frontend/src/views/ReportView.vue \
  frontend/src/views/InteractionView.vue \
  frontend/src/components/Step1GraphBuild.vue \
  frontend/src/components/Step2EnvSetup.vue \
  frontend/src/components/Step3Simulation.vue \
  frontend/src/components/Step5Interaction.vue
git commit -m "feat(i18n): translate all remaining Vue files to support EN/ZH toggle"
```

---

## Task 17: Wire Up ReportAgent `project_id` + `limits`

**Files:**
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/services/report_agent.py`

- [ ] **Step 1: Pass `project_id` and `limits` to `ReportAgent` from `report.py`**

In the `generate_report()` route (report.py), the `ReportAgent` is instantiated inside `run_generate()`. Update:

```python
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    project_id=state.project_id,
                    limits=project.limits or {},
                )
```

- [ ] **Step 2: Add `project_id` and `limits` to `ReportAgent.__init__`**

```bash
grep -n "def __init__" /home/mario/Dev/MiroFish/backend/app/services/report_agent.py | head -5
```

Update the `ReportAgent.__init__` signature:

```python
    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        project_id: Optional[str] = None,
        limits: Optional[Dict[str, Any]] = None,
    ):
```

Add to `__init__` body:
```python
        self.project_id = project_id
        self.limits = limits or {}
        
        max_calls = self.limits.get('max_llm_calls', None)
        self._calls_remaining = int(max_calls) if max_calls else None
```

Also update `LLMClient` instantiation inside `ReportAgent.__init__` to pass `project_id`:
```bash
grep -n "LLMClient(" /home/mario/Dev/MiroFish/backend/app/services/report_agent.py | head -5
```

Change `LLMClient(...)` to `LLMClient(..., project_id=self.project_id)`.

- [ ] **Step 3: Verify the report agent can be instantiated with limits**

```bash
cd /home/mario/Dev/MiroFish/backend
python -c "
from app.services.report_agent import ReportAgent
a = ReportAgent(
  graph_id='test', simulation_id='test', simulation_requirement='test',
  project_id='proj_test', limits={'max_llm_calls': 5}
)
print('calls_remaining:', a._calls_remaining)
"
```

Expected: `calls_remaining: 5`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/report.py backend/app/services/report_agent.py
git commit -m "feat(report): wire project_id and limits through to ReportAgent for usage tracking and budget control"
```

---

## Self-Review Checklist

After completing all tasks:

- [ ] **Feature 1 — i18n**: `useLocale.js` works; toggle button visible; all 14 Vue files use `t()` for UI strings; locale persists on refresh
- [ ] **Feature 2 — Pre-run limits**: Advanced settings panel in Home.vue; limits stored on `Project.limits`; passed as form fields to `generateOntology`; `limits_hit` returned in graph task result; personas clamped; budget applied to report agent
- [ ] **Feature 3 — Stop/Resume/Reset**: `ReportStatus.CANCELLED` and `BUDGET_EXCEEDED` exist; `ReportManager.request_stop/clear_stop` work; stop/resume/reset routes return 200; buttons appear in `Step4Report.vue` based on `reportStatus`
- [ ] **Feature 4 — Usage tracking**: `UsageTracker.record()` called after every LLM completion; `GET /api/usage/<project_id>` returns live totals; `UsageCounter.vue` polls and renders; card footers show usage in HistoryDatabase
- [ ] **Feature 5 — Project listing**: `/api/graph/project/list` returns `simulation_id`, `report_id`, `status`, `usage` per item; HistoryDatabase polls every 5 seconds; pulsing badge for active projects; smart navigation; empty state shown
