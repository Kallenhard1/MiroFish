"""
Report Agent service
Uses LangChain + Zep to generate simulation reports with a ReACT workflow.

Features:
1. Generate reports from simulation requirements and Zep graph information
2. Plan the outline first, then generate sections incrementally
3. Use multi-turn ReACT reasoning and reflection for each section
4. Support user chat and autonomous retrieval tool calls during the conversation
"""

import os
import json
import time
import re
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Report Agent translated text
    
    translated text agent_log.jsonl translated text，translated text。
    translated text JSON translated text，translated text、translated text、translated text。
    """
    
    def __init__(self, report_id: str):
        """
        translated text
        
        Args:
            report_id: translated textID，translated text
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """translated text"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """translated text（translated text）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        translated text
        
        Args:
            action: translated text，translated text 'start', 'tool_call', 'llm_response', 'section_complete' translated text
            stage: translated text，translated text 'planning', 'generating', 'completed'
            details: translated text，translated text
            section_title: translated text（translated text）
            section_index: translated text（translated text）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # translated text JSONL translated text
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """translated text"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "translated text"
            }
        )
    
    def log_planning_start(self):
        """translated text"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "translated text"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """translated text"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "translated text",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """translated text"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "translated text",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """translated text"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"translated text: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """translated text ReACT translated text"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT translated text{iteration}translated text"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """translated text"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"translated text: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """translated text（translated text，translated text）"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # translated text，translated text
                "result_length": len(result),
                "message": f"translated text {tool_name} translated text"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """translated text LLM translated text（translated text，translated text）"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # translated text，translated text
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM translated text (translated text: {has_tool_calls}, translated text: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """translated text（translated text，translated text）"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # translated text，translated text
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"translated text {section_title} translated text"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        translated text

        translated text，translated text
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"translated text {section_title} translated text"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """translated text"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "translated text"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """translated text"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"translated text: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent translated text
    
    translated text（INFO、WARNINGtranslated text）translated text console_log.txt translated text。
    translated text agent_log.jsonl translated text，translated text。
    """
    
    def __init__(self, report_id: str):
        """
        translated text
        
        Args:
            report_id: translated textID，translated text
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """translated text"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """translated text，translated text"""
        import logging
        
        # translated text
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # translated text
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # translated text report_agent translated text logger
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # translated text
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """translated text logger translated text"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """translated text"""
        self.close()


class ReportStatus(str, Enum):
    """translated text"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXCEEDED = "budget_exceeded"


class CancellationError(Exception):
    """Raised when report generation is cooperatively cancelled."""


class BudgetExceededError(Exception):
    """Raised when the max_llm_calls budget is consumed."""


@dataclass
class ReportSection:
    """translated text"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """translated textMarkdowntranslated text"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """translated text"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """translated textMarkdowntranslated text"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """translated text"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt translated text
# ═══════════════════════════════════════════════════════════════

# ── translated text ──

TOOL_DESC_INSIGHT_FORGE = """\
[Deep Insight Retrieval - Powerful Retrieval Tool]
This is our powerful retrieval function, designed for deep analysis. It will:
1. Automatically break your question into multiple sub-questions
2. Retrieve information from the simulation graph across multiple dimensions
3. Combine results from semantic search, entity analysis, and relationship-chain tracing
4. Return the most comprehensive and in-depth retrieval content

[Use Cases]
- You need to analyze a topic deeply
- You need to understand multiple aspects of an event
- You need rich source material to support a report section

[Returns]
- Relevant original facts (ready to quote)
- Core entity insights
- Relationship-chain analysis"""

TOOL_DESC_PANORAMA_SEARCH = """\
[Panorama Search - Full View]
This tool retrieves the complete view of simulation results and is especially useful for understanding how events evolve. It will:
1. Retrieve all relevant nodes and relationships
2. Distinguish currently valid facts from historical/expired facts
3. Help you understand how public opinion evolved

[Use Cases]
- You need the full development arc of an event
- You need to compare public-opinion changes across stages
- You need comprehensive entity and relationship information

[Returns]
- Currently valid facts (latest simulation results)
- Historical/expired facts (evolution records)
- All involved entities"""

TOOL_DESC_QUICK_SEARCH = """\
[Quick Search]
A lightweight quick retrieval tool for simple, direct information queries.

[Use Cases]
- You need to quickly find a specific piece of information
- You need to verify a fact
- You need a simple information lookup

[Returns]
- A list of facts most relevant to the query"""

TOOL_DESC_INTERVIEW_AGENTS = """\
[Deep Interview - Real Agent Interviews (Dual Platform)]
Calls the OASIS simulation interview API to interview running simulation Agents.
This is not an LLM simulation; it calls the real interview interface to obtain raw answers from simulation Agents.
By default, it interviews on both Twitter and Reddit to gather more complete viewpoints.

Workflow:
1. Automatically read persona files and understand all simulation Agents
2. Select the Agents most relevant to the interview topic, such as students, media, or officials
3. Automatically generate interview questions
4. Call the /api/simulation/interview/batch endpoint to conduct real dual-platform interviews
5. Integrate all interview results into multi-perspective analysis

[Use Cases]
- You need to understand an event from different role perspectives, such as students, media, or officials
- You need to collect multiple opinions and positions
- You need real answers from simulation Agents in the OASIS environment
- You want the report to be more vivid and include interview excerpts

[Returns]
- Identity information for interviewed Agents
- Each Agent's interview answers on Twitter and Reddit
- Key quotations ready to quote
- Interview summary and viewpoint comparison

[Important] The OASIS simulation environment must be running to use this feature."""

# ── translated text prompt ──

PLAN_SYSTEM_PROMPT = """\
You are an expert writer of future-prediction reports with an omniscient view of the simulation world. You can observe every Agent's behavior, statements, and interactions in the simulation.

[Core Idea]
We created a simulation world and injected a specific simulation requirement as a variable. The evolution of that world is a prediction of what may happen in the future. You are not observing "experimental data"; you are observing a "future rehearsal".

[Your Task]
Write a future-prediction report that answers:
1. Under the conditions we set, what happened in the future?
2. How did different types of Agents or populations react and act?
3. What future trends and risks does this simulation reveal?

[Report Positioning]
- This is a simulation-based future-prediction report that reveals "if this happens, what will the future look like".
- Focus on predicted outcomes: event trajectory, group reactions, emergent phenomena, and potential risks.
- Agent statements and actions in the simulation are predictions of future human behavior.
- Do not analyze the current real-world situation.
- Do not write a generic public-opinion summary.

[Section Count Limit]
- At least 2 sections and at most 5 sections
- No subsections are needed; each section should contain complete content directly
- Keep the content concise and focused on core predictive findings
- Design the section structure yourself based on the prediction results

Output the report outline as JSON in this format:
{
    "title": "Report title",
    "summary": "Report summary (one sentence summarizing the core predictive finding)",
    "sections": [
        {
            "title": "Section title",
            "description": "Section content description"
        }
    ]
}

Note: the sections array must contain at least 2 and at most 5 items."""

PLAN_USER_PROMPT_TEMPLATE = """\
[Prediction Scenario]
The variable injected into the simulation world (simulation requirement): {simulation_requirement}

[Simulation World Scale]
- Number of entities participating in the simulation: {total_nodes}
- Number of relationships generated among entities: {total_edges}
- Entity type distribution: {entity_types}
- Number of active Agents: {total_entities}

[Sample Future Facts Predicted by the Simulation]
{related_facts_json}

Review this future rehearsal from an omniscient perspective:
1. Under the conditions we set, what state did the future reach?
2. How did different groups or Agents react and act?
3. What future trends worth attention does this simulation reveal?

Design the most suitable report section structure based on the prediction results.

[Reminder] Report section count: at least 2 and at most 5. Keep the content concise and focused on core predictive findings."""

# ── translated text prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert writer of future-prediction reports, currently writing one section of the report.

Report title: {report_title}
Report summary: {report_summary}
Prediction scenario (simulation requirement): {simulation_requirement}

Current section to write: {section_title}

===============================================================
[Core Idea]
===============================================================

The simulation world is a rehearsal of the future. We injected specific conditions (the simulation requirement) into the simulation world.
Agent behavior and interactions in the simulation are predictions of future human behavior.

Your task is to:
- Reveal what happens in the future under the specified conditions
- Predict how different groups or Agents react and act
- Identify future trends, risks, and opportunities worth attention

Do not write an analysis of the current real-world situation.
Focus on "what the future will look like"; the simulation results are the predicted future.

===============================================================
[Most Important Rules - Must Follow]
===============================================================

1. [You must call tools to observe the simulation world]
   - You are observing a future rehearsal from an omniscient perspective
   - All content must come from events and Agent statements/actions in the simulation world
   - Do not use your own knowledge to write report content
   - Each section must call tools at least 3 times and at most 5 times to observe the simulated world, which represents the future

2. [You must quote original Agent statements and actions]
   - Agent speech and behavior are predictions of future human behavior
   - Use quote formatting in the report, for example:
     > "A certain group may say: original text..."
   - These quotations are the core evidence for the simulation prediction

3. [Language consistency - quoted content must be translated into the report language]
   - Tool results may contain English or mixed English and Chinese expressions
   - If the simulation requirement and source material are in Chinese, the report must be written entirely in Chinese
   - When quoting English or mixed-language tool results, translate them into fluent Chinese before putting them into the report
   - Preserve the original meaning and make the expression natural
   - This rule applies to both body text and quote blocks (> format)

4. [Faithfully present the prediction results]
   - Report content must reflect simulation results that represent the future in the simulation world
   - Do not add information that does not exist in the simulation
   - If information is insufficient in some area, state that honestly

===============================================================
[Format Rules - Extremely Important]
===============================================================

[One Section = Minimum Content Unit]
- Each section is the smallest block in the report
- Do not use any Markdown headings inside the section (#, ##, ###, ####, etc.)
- Do not add the section's main title at the start of the content
- The system adds the section title automatically; write body text only
- Use **bold**, paragraph breaks, quotations, and lists to organize content, but do not use headings

[Correct Example]
```
This section analyzes the public-opinion propagation pattern of the event. Through in-depth analysis of the simulation data, we found...

**Initial Trigger Stage**

Weibo served as the first scene of public opinion and played the core role in initial information release:

> "Weibo contributed 68% of the initial volume..."

**Emotional Amplification Stage**

The Douyin platform further amplified the event's influence:

- Strong visual impact
- High emotional resonance
```

[Incorrect Example]
```
## Executive Summary          <- Wrong. Do not add any heading.
### 1. Initial Stage          <- Wrong. Do not use ### subsections.
#### 1.1 Detailed Analysis    <- Wrong. Do not use #### subdivisions.

This section analyzes...
```

===============================================================
[Available Retrieval Tools] (call 3-5 times per section)
===============================================================

{tools_description}

[Tool Use Suggestions - Mix different tools, do not use only one]
- insight_forge: deep insight analysis; automatically decomposes questions and retrieves facts and relationships across dimensions
- panorama_search: wide-angle panorama search; understand the full event picture, timeline, and evolution
- quick_search: quickly verify a specific information point
- interview_agents: interview simulation Agents and obtain first-person viewpoints and real reactions from different roles

===============================================================
[Workflow]
===============================================================

Each reply may do exactly one of the following two things, never both:

Option A - Call a tool:
Output your thought, then call a tool in this format:
<tool_call>
{{"name": "tool_name", "parameters": {{"parameter_name": "parameter_value"}}}}
</tool_call>
The system will execute the tool and return the result. You do not need to and must not fabricate tool results yourself.

Option B - Output final content:
When you have obtained enough information through tools, start with "Final Answer:" and output the section content.

Strictly forbidden:
- Do not include both a tool call and Final Answer in a single reply
- Do not fabricate tool results (Observation); all tool results are injected by the system
- Call at most one tool per reply

===============================================================
[Section Content Requirements]
===============================================================

1. Content must be based on simulation data retrieved by tools
2. Quote original text extensively to show the simulation effect
3. Use Markdown formatting, but do not use headings:
   - Use **bold text** for emphasis, replacing subsection headings
   - Use lists (- or 1. 2. 3.) to organize points
   - Use blank lines between paragraphs
   - Do not use #, ##, ###, ####, or any other heading syntax
4. [Quote Format Rule - Quotes Must Be Separate Paragraphs]
   Quotes must stand alone as paragraphs with a blank line before and after. They cannot be mixed into a paragraph:

   Correct format:
   ```
   The school's response was considered lacking in substance.

   > "The school's response pattern appears rigid and slow in the fast-moving social media environment."

   This assessment reflects broad public dissatisfaction.
   ```

   Incorrect format:
   ```
   The school's response was considered lacking in substance.> "The school's response pattern..." This assessment reflects...
   ```
5. Maintain logical continuity with other sections
6. [Avoid Repetition] Read the completed sections below carefully and do not repeat the same information
7. [Reminder] Do not add any headings. Use **bold** instead of subsection titles."""

SECTION_USER_PROMPT_TEMPLATE = """\
Completed section content (read carefully to avoid repetition):
{previous_content}

===============================================================
[Current Task] Write section: {section_title}
===============================================================

[Important Reminders]
1. Read the completed sections above carefully and avoid repeating the same content.
2. Before starting, you must call a tool to obtain simulation data.
3. Mix different tools; do not use only one.
4. Report content must come from retrieved results. Do not use your own knowledge.

[Format Warning - Must Follow]
- Do not write any heading (#, ##, ###, #### are all forbidden)
- Do not start with "{section_title}"
- The system adds the section title automatically
- Write body text directly and use **bold** instead of subsection titles

Start now:
1. First think (Thought) about what information this section needs
2. Then call a tool (Action) to obtain simulation data
3. After collecting enough information, output Final Answer (body text only, no headings)"""

# ── ReACT translated text ──

REACT_OBSERVATION_TEMPLATE = """\
Observation (retrieval result):

=== Tool {tool_name} returned ===
{result}

===============================================================
Tool calls made: {tool_calls_count}/{max_tool_calls} (used: {used_tools_str}){unused_hint}
- If information is sufficient: start with "Final Answer:" and output the section content (must quote the original text above)
- If more information is needed: call one tool to continue retrieval
==============================================================="""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "【translated text】translated text{tool_calls_count}translated text，translated text{min_tool_calls}translated text。"
    "translated text，translated text Final Answer。{unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "translated text {tool_calls_count} translated text，translated text {min_tool_calls} translated text。"
    "translated text。{unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "translated text（{tool_calls_count}/{max_tool_calls}），translated text。"
    'translated text，translated text "Final Answer:" translated text。'
)

REACT_UNUSED_TOOLS_HINT = "\n💡 translated text: {unused_list}，translated text"

REACT_FORCE_FINAL_MSG = "translated text，translated text Final Answer: translated text。"

# ── Chat prompt ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
You are a concise and efficient simulation prediction assistant.

[Background]
Prediction condition: {simulation_requirement}

[Generated Analysis Report]
{report_content}

[Rules]
1. Prefer answering based on the report content above
2. Answer directly and avoid long reasoning discussions
3. Call tools to retrieve more data only when the report content is insufficient
4. Keep answers concise, clear, and well structured

[Available Tools] (use only when needed; at most 1-2 calls)
{tools_description}

[Tool Call Format]
<tool_call>
{{"name": "tool_name", "parameters": {{"parameter_name": "parameter_value"}}}}
</tool_call>

[Answer Style]
- Concise and direct; do not be verbose
- Use > format for key quotations
- State the conclusion first, then explain the reason"""

CHAT_OBSERVATION_SUFFIX = "\n\ntranslated text。"


# ═══════════════════════════════════════════════════════════════
# ReportAgent translated text
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - translated textAgent

    translated textReACT（Reasoning + Acting）translated text：
    1. translated text：translated text，translated text
    2. translated text：translated text，translated text
    3. translated text：translated text
    """
    
    # translated text（translated text）
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # translated text
    MAX_REFLECTION_ROUNDS = 3
    
    # translated text
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None,
        project_id: Optional[str] = None,
        limits: Optional[Dict[str, Any]] = None,
    ):
        """
        translated textReport Agent
        
        Args:
            graph_id: translated textID
            simulation_id: translated textID
            simulation_requirement: translated text
            llm_client: LLMtranslated text（translated text）
            zep_tools: Zeptranslated text（translated text）
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.project_id = project_id
        self.limits = limits or {}
        max_calls = self.limits.get('max_llm_calls', None)
        self._calls_remaining = int(max_calls) if max_calls else None

        self.llm = llm_client or LLMClient(project_id=self.project_id)
        self.zep_tools = zep_tools or ZepToolsService()
        
        # translated text
        self.tools = self._define_tools()
        
        # translated text（translated text generate_report translated text）
        self.report_logger: Optional[ReportLogger] = None
        # translated text（translated text generate_report translated text）
        self.console_logger: Optional[ReportConsoleLogger] = None

        logger.info(f"ReportAgent translated text: graph_id={graph_id}, simulation_id={simulation_id}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """translated text"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "translated text",
                    "report_context": "translated text（translated text，translated text）"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "translated text，translated text",
                    "include_expired": "translated text/translated text（translated textTrue）"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "translated text",
                    "limit": "translated text（translated text，translated text10）"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "translated text（translated text：'translated text'）",
                    "max_agents": "translated textAgenttranslated text（translated text，translated text5，translated text10）"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        translated text
        
        Args:
            tool_name: translated text
            parameters: translated text
            report_context: translated text（translated textInsightForge）
            
        Returns:
            translated text（translated text）
        """
        logger.info(f"translated text: {tool_name}, translated text: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # translated text - translated text
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # translated text - translated text
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # translated text - translated textOASIStranslated textAPItranslated textAgenttranslated text（translated text）
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== translated text（translated text） ==========
            
            elif tool_name == "search_graph":
                # translated text quick_search
                logger.info("search_graph translated text quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # translated text insight_forge，translated text
                logger.info("get_simulation_context translated text insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"translated text: {tool_name}。translated text: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(f"translated text: {tool_name}, translated text: {str(e)}")
            return f"translated text: {str(e)}"
    
    # translated text，translated text JSON translated text
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        translated textLLMtranslated text

        translated text（translated text）：
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. translated text JSON（translated text JSON）
        """
        tool_calls = []

        # translated text1: XMLtranslated text（translated text）
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # translated text2: translated text - LLM translated text JSON（translated text <tool_call> translated text）
        # translated text1translated text，translated text JSON
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # translated text + translated text JSON，translated text JSON translated text
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """translated text JSON translated text"""
        # translated text {"name": ..., "parameters": ...} translated text {"tool": ..., "params": ...} translated text
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # translated text name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """translated text"""
        desc_parts = ["translated text："]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  translated text: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        translated text
        
        translated textLLMtranslated text，translated text
        
        Args:
            progress_callback: translated text
            
        Returns:
            ReportOutline: translated text
        """
        logger.info("translated text...")
        
        if progress_callback:
            progress_callback("planning", 0, "translated text...")
        
        # translated text
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "translated text...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "translated text...")
            
            # translated text
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "translated text"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, "translated text")
            
            logger.info(f"translated text: {len(sections)} translated text")
            return outline
            
        except Exception as e:
            logger.error(f"translated text: {str(e)}")
            # translated text（3translated text，translated textfallback）
            return ReportOutline(
                title="translated text",
                summary="translated text",
                sections=[
                    ReportSection(title="translated text"),
                    ReportSection(title="translated text"),
                    ReportSection(title="translated text")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        translated textReACTtranslated text
        
        ReACTtranslated text：
        1. Thought（translated text）- translated text
        2. Action（translated text）- translated text
        3. Observation（translated text）- translated text
        4. translated text
        5. Final Answer（translated text）- translated text
        
        Args:
            section: translated text
            outline: translated text
            previous_sections: translated text（translated text）
            progress_callback: translated text
            section_index: translated text（translated text）
            
        Returns:
            translated text（Markdowntranslated text）
        """
        logger.info(f"ReACTtranslated text: {section.title}")
        
        # translated text
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # translated textprompt - translated text4000translated text
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # translated text4000translated text
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "（translated text）"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACTtranslated text
        tool_calls_count = 0
        max_iterations = 5  # translated text
        min_tool_calls = 3  # translated text
        conflict_retries = 0  # translated textFinal Answertranslated text
        used_tools = set()  # translated text
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # translated text，translated textInsightForgetranslated text
        report_context = f"translated text: {section.title}\ntranslated text: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"translated text ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # translated textLLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # translated text LLM translated text None（API translated text）
            if response is None:
                logger.warning(f"translated text {section.title} translated text {iteration + 1} translated text: LLM translated text None")
                # translated text，translated text
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "（translated text）"})
                    messages.append({"role": "user", "content": "translated text。"})
                    continue
                # translated text None，translated text
                break

            logger.debug(f"LLMtranslated text: {response[:200]}...")

            # translated text，translated text
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── translated text：LLM translated text Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"translated text {section.title} translated text {iteration+1} translated text: "
                    f"LLM translated text Final Answer（translated text {conflict_retries} translated text）"
                )

                if conflict_retries <= 2:
                    # translated text：translated text，translated text LLM translated text
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【translated text】translated text Final Answer，translated text。\n"
                            "translated text：\n"
                            "- translated text（translated text <tool_call> translated text，translated text Final Answer）\n"
                            "- translated text（translated text 'Final Answer:' translated text，translated text <tool_call>）\n"
                            "translated text，translated text。"
                        ),
                    })
                    continue
                else:
                    # translated text：translated text，translated text，translated text
                    logger.warning(
                        f"translated text {section.title}: translated text {conflict_retries} translated text，"
                        "translated text"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # translated text LLM translated text
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── translated text1：LLM translated text Final Answer ──
            if has_final_answer:
                # translated text，translated text
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"（translated text，translated text: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # translated text
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"translated text {section.title} translated text（translated text: {tool_calls_count}translated text）")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── translated text2：LLM translated text ──
            if has_tool_calls:
                # translated text → translated text，translated text Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # translated text
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM translated text {len(tool_calls)} translated text，translated text: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # translated text
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── translated text3：translated text，translated text Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # translated text，translated text
                unused_tools = all_tools - used_tools
                unused_hint = f"（translated text，translated text: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # translated text，LLM translated text "Final Answer:" translated text
            # translated text，translated text
            logger.info(f"translated text {section.title} translated text 'Final Answer:' translated text，translated textLLMtranslated text（translated text: {tool_calls_count}translated text）")
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # translated text，translated text
        logger.warning(f"translated text {section.title} translated text，translated text")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # translated text LLM translated text None
        if response is None:
            logger.error(f"translated text {section.title} translated text LLM translated text None，translated text")
            final_answer = f"（translated text：LLM translated text，translated text）"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # translated text
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None,
        start_section_index: int = 0,
    ) -> Report:
        """
        translated text（translated text）
        
        translated text，translated text。
        translated text：
        reports/{report_id}/
            meta.json       - translated text
            outline.json    - translated text
            progress.json   - translated text
            section_01.md   - translated text1translated text
            section_02.md   - translated text2translated text
            ...
            full_report.md  - translated text
        
        Args:
            progress_callback: translated text (stage, progress, message)
            report_id: translated textID（translated text，translated text）
            
        Returns:
            Report: translated text
        """
        import uuid
        
        # translated text report_id，translated text
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # translated text（translated text）
        completed_section_titles = []
        
        try:
            # translated text：translated text
            ReportManager._ensure_report_folder(report_id)


            # translated text（translated text agent_log.jsonl）
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # translated text（console_log.txt）
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "translated text...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # translated text1: translated text（resumetranslated text）
            outline = None
            if start_section_index > 0:
                outline_path = ReportManager._get_outline_path(report_id)
                if os.path.exists(outline_path):
                    with open(outline_path, 'r', encoding='utf-8') as _f:
                        outline_data = json.load(_f)
                    sections = [
                        ReportSection(title=s['title'], content=s.get('content', ''))
                        for s in outline_data.get('sections', [])
                    ]
                    outline = ReportOutline(
                        title=outline_data['title'],
                        summary=outline_data['summary'],
                        sections=sections,
                    )
                    logger.info(f"Resume: loaded saved outline ({len(sections)} sections) for {report_id}")

            if outline is None:
                report.status = ReportStatus.PLANNING
                ReportManager.update_progress(
                    report_id, "planning", 5, "translated text...",
                    completed_sections=[]
                )
                self.report_logger.log_planning_start()
                if progress_callback:
                    progress_callback("planning", 0, "translated text...")

                outline = self.plan_outline(
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(stage, prog // 5, msg) if progress_callback else None
                )
                self.report_logger.log_planning_complete(outline.to_dict())
                ReportManager.save_outline(report_id, outline)
                ReportManager.update_progress(
                    report_id, "planning", 15, f"translated text，translated text{len(outline.sections)}translated text",
                    completed_sections=[]
                )
                logger.info(f"translated text: {report_id}/outline.json")

            report.outline = outline
            ReportManager.save_report(report)
            
            # translated text2: translated text（translated text）
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # translated text
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1

                # Skip already-completed sections when resuming
                if i < start_section_index:
                    section_path = ReportManager._get_section_path(report_id, section_num)
                    if os.path.exists(section_path):
                        with open(section_path, 'r', encoding='utf-8') as _f:
                            section.content = _f.read()
                        generated_sections.append(f"## {section.title}\n\n{section.content}")
                        completed_section_titles.append(section.title)
                    continue

                # Cooperative cancellation check
                cancellation_event = ReportManager.get_cancellation_event(report_id)
                if cancellation_event.is_set():
                    report.status = ReportStatus.CANCELLED
                    report.error = "Stopped by user request"
                    ReportManager.save_report(report)
                    ReportManager.update_progress(
                        report_id, "cancelled",
                        20 + int((i / total_sections) * 70),
                        "translated text",
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

                base_progress = 20 + int((i / total_sections) * 70)
                
                # translated text
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"translated text: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"translated text: {section.title} ({section_num}/{total_sections})"
                    )
                
                # translated text
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # translated text
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # translated text
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"translated text: {report_id}/section_{section_num:02d}.md")
                
                # translated text
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"translated text {section.title} translated text",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # translated text3: translated text
            if progress_callback:
                progress_callback("generating", 95, "translated text...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "translated text...",
                completed_sections=completed_section_titles
            )
            
            # translated textReportManagertranslated text
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # translated text
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # translated text
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # translated text
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "translated text",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "translated text")
            
            logger.info(f"translated text: {report_id}")
            
            # translated text
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report

        except CancellationError:
            ReportManager.save_report(report)
            if progress_callback:
                outline_sections = report.outline.sections if report.outline else []
                pct = 20 + int((len(completed_section_titles) / max(len(outline_sections), 1)) * 70)
                progress_callback("cancelled", pct, "translated text")
            return report

        except BudgetExceededError:
            outline_sections = report.outline.sections if report.outline else []
            pct = 20 + int((len(completed_section_titles) / max(len(outline_sections), 1)) * 70)
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "budget_exceeded", pct, "LLMtranslated text",
                completed_sections=completed_section_titles
            )
            if progress_callback:
                progress_callback("budget_exceeded", pct, "LLMtranslated text")
            return report

        except Exception as e:
            logger.error(f"translated text: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)

            # translated text
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")

            # translated text
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"translated text: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # translated text

            # translated text
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        translated textReport Agenttranslated text
        
        translated textAgenttranslated text
        
        Args:
            message: translated text
            chat_history: translated text
            
        Returns:
            {
                "response": "Agenttranslated text",
                "tool_calls": [translated text],
                "sources": [translated text]
            }
        """
        logger.info(f"Report Agenttranslated text: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # translated text
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # translated text，translated text
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [translated text] ..."
        except Exception as e:
            logger.warning(f"translated text: {e}")
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "（translated text）",
            tools_description=self._get_tools_description(),
        )

        # translated text
        messages = [{"role": "system", "content": system_prompt}]
        
        # translated text
        for h in chat_history[-10:]:  # translated text
            messages.append(h)
        
        # translated text
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACTtranslated text（translated text）
        tool_calls_made = []
        max_iterations = 2  # translated text
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # translated text
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # translated text，translated text
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # translated text（translated text）
            tool_results = []
            for call in tool_calls[:1]:  # translated text1translated text
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # translated text
                })
                tool_calls_made.append(call)
            
            # translated text
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']}translated text]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # translated text，translated text
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # translated text
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    translated text
    
    translated text
    
    translated text（translated text）：
    reports/
      {report_id}/
        meta.json          - translated text
        outline.json       - translated text
        progress.json      - translated text
        section_01.md      - translated text1translated text
        section_02.md      - translated text2translated text
        ...
        full_report.md     - translated text
    """
    
    # translated text
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')

    # module-level cancellation events keyed by report_id
    _cancellation_events: Dict[str, threading.Event] = {}
    _events_lock = threading.Lock()

    @classmethod
    def request_stop(cls, report_id: str) -> None:
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = threading.Event()
            cls._cancellation_events[report_id].set()

    @classmethod
    def clear_stop(cls, report_id: str) -> None:
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = threading.Event()
            cls._cancellation_events[report_id].clear()

    @classmethod
    def get_cancellation_event(cls, report_id: str) -> threading.Event:
        with cls._events_lock:
            if report_id not in cls._cancellation_events:
                cls._cancellation_events[report_id] = threading.Event()
            return cls._cancellation_events[report_id]

    @classmethod
    def _ensure_reports_dir(cls):
        """translated text"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """translated text"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """translated text"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """translated text"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """translated textMarkdowntranslated text"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """translated text"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """translated text"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """translated textMarkdowntranslated text"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """translated text Agent translated text"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """translated text"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        translated text
        
        translated text（INFO、WARNINGtranslated text），
        translated text agent_log.jsonl translated text。
        
        Args:
            report_id: translated textID
            from_line: translated text（translated text，0 translated text）
            
        Returns:
            {
                "logs": [translated text],
                "total_lines": translated text,
                "from_line": translated text,
                "has_more": translated text
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # translated text，translated text
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # translated text
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        translated text（translated text）
        
        Args:
            report_id: translated textID
            
        Returns:
            translated text
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        translated text Agent translated text
        
        Args:
            report_id: translated textID
            from_line: translated text（translated text，0 translated text）
            
        Returns:
            {
                "logs": [translated text],
                "total_lines": translated text,
                "from_line": translated text,
                "has_more": translated text
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # translated text
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # translated text
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        translated text Agent translated text（translated text）
        
        Args:
            report_id: translated textID
            
        Returns:
            translated text
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        translated text
        
        translated text
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"translated text: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        translated text

        translated text，translated text

        Args:
            report_id: translated textID
            section_index: translated text（translated text1translated text）
            section: translated text

        Returns:
            translated text
        """
        cls._ensure_report_folder(report_id)

        # translated textMarkdowntranslated text - translated text
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # translated text
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"translated text: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        translated text
        
        1. translated textMarkdowntranslated text
        2. translated text ### translated text
        
        Args:
            content: translated text
            section_title: translated text
            
        Returns:
            translated text
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # translated textMarkdowntranslated text
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # translated text（translated text5translated text）
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # translated text（#, ##, ###, ####translated text）translated text
                # translated text，translated text
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # translated text
                continue
            
            # translated text，translated text，translated text
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # translated text
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # translated text
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # translated text
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        translated text
        
        translated textprogress.jsontranslated text
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """translated text"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        translated text
        
        translated text
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # translated text
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        translated text
        
        translated text，translated text
        """
        folder = cls._get_report_folder(report_id)
        
        # translated text
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # translated text
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # translated text：translated text
        md_content = cls._post_process_report(md_content, outline)
        
        # translated text
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"translated text: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        translated text
        
        1. translated text
        2. translated text(#)translated text(##)，translated text(###, ####translated text)
        3. translated text
        
        Args:
            content: translated text
            outline: translated text
            
        Returns:
            translated text
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # translated text
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # translated text
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # translated text（translated text5translated text）
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # translated text
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # translated text：
                # - # (level=1) translated text
                # - ## (level=2) translated text
                # - ### translated text (level>=3) translated text
                
                if level == 1:
                    if title == outline.title:
                        # translated text
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # translated text#，translated text##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # translated text
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # translated text
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # translated text
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### translated text
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # translated text
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # translated text
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # translated text（translated text2translated text）
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """translated text"""
        cls._ensure_report_folder(report.report_id)
        
        # translated textJSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # translated text
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # translated textMarkdowntranslated text
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"translated text: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """translated text"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # translated text：translated textreportstranslated text
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # translated textReporttranslated text
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # translated textmarkdown_contenttranslated text，translated textfull_report.mdtranslated text
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """translated textIDtranslated text"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # translated text：translated text
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # translated text：JSONtranslated text
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 20) -> List[Report]:
        """translated text"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # translated text：translated text
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # translated text：JSONtranslated text
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # translated text
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """translated text（translated text）"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # translated text：translated text
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"translated text: {report_id}")
            return True
        
        # translated text：translated text
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
