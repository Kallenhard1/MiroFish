"""
translated text
translated textLLMtranslated text、translated text、translated text
translated text，translated text

translated text，translated text：
1. translated text
2. translated text
3. translated textAgenttranslated text
4. translated text
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.simulation_config')

# translated text（translated text）
CHINA_TIMEZONE_CONFIG = {
    # translated text（translated text）
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # translated text（translated text）
    "morning_hours": [6, 7, 8],
    # translated text
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # translated text（translated text）
    "peak_hours": [19, 20, 21, 22],
    # translated text（translated text）
    "night_hours": [23],
    # translated text
    "activity_multipliers": {
        "dead": 0.05,      # translated text
        "morning": 0.4,    # translated text
        "work": 0.7,       # translated text
        "peak": 1.5,       # translated text
        "night": 0.5       # translated text
    }
}


@dataclass
class AgentActivityConfig:
    """translated textAgenttranslated text"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # translated text (0.0-1.0)
    activity_level: float = 0.5  # translated text
    
    # translated text（translated text）
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # translated text（24translated text，0-23）
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # translated text（translated text，translated text：translated text）
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # translated text (-1.0translated text1.0，translated text)
    sentiment_bias: float = 0.0
    
    # translated text（translated text）
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # translated text（translated textAgenttranslated text）
    influence_weight: float = 1.0


@dataclass  
class TimeSimulationConfig:
    """translated text（translated text）"""
    # translated text（translated text）
    total_simulation_hours: int = 72  # translated text72translated text（3translated text）
    
    # translated text（translated text）- translated text60translated text（1translated text），translated text
    minutes_per_round: int = 60
    
    # translated textAgenttranslated text
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # translated text（translated text19-22translated text，translated text）
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # translated text（translated text0-5translated text，translated text）
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # translated text
    
    # translated text
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # translated text
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """translated text"""
    # translated text（translated text）
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    # translated text（translated text）
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # translated text
    hot_topics: List[str] = field(default_factory=list)
    
    # translated text
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """translated text"""
    platform: str  # twitter or reddit
    
    # translated text
    recency_weight: float = 0.4  # translated text
    popularity_weight: float = 0.3  # translated text
    relevance_weight: float = 0.3  # translated text
    
    # translated text（translated text）
    viral_threshold: int = 10
    
    # translated text（translated text）
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """translated text"""
    # translated text
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # translated text
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agenttranslated text
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # translated text
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # translated text
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    
    # LLMtranslated text
    llm_model: str = ""
    llm_base_url: str = ""
    
    # translated text
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLMtranslated text
    
    def to_dict(self) -> Dict[str, Any]:
        """translated text"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """translated textJSONtranslated text"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    translated text
    
    translated textLLMtranslated text、translated text、translated text，
    translated text
    
    translated text：
    1. translated text（translated text）
    2. translated textAgenttranslated text（translated text10-20translated text）
    3. translated text
    """
    
    # translated text
    MAX_CONTEXT_LENGTH = 50000
    # translated textAgenttranslated text
    AGENTS_PER_BATCH = 15
    
    # translated text（translated text）
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # translated text
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # translated text
    ENTITY_SUMMARY_LENGTH = 300          # translated text
    AGENT_SUMMARY_LENGTH = 300           # Agenttranslated text
    ENTITIES_PER_TYPE_DISPLAY = 20       # translated text
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY translated text")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        translated text（translated text）
        
        Args:
            simulation_id: translated textID
            project_id: translated textID
            graph_id: translated textID
            simulation_requirement: translated text
            document_text: translated text
            entities: translated text
            enable_twitter: translated textTwitter
            enable_reddit: translated textReddit
            progress_callback: translated text(current_step, total_steps, message)
            
        Returns:
            SimulationParameters: translated text
        """
        logger.info(f"translated text: simulation_id={simulation_id}, translated text={len(entities)}")
        
        # translated text
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # translated text + translated text + Ntranslated textAgent + translated text
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. translated text
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        reasoning_parts = []
        
        # ========== translated text1: translated text ==========
        report_progress(1, "translated text...")
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"translated text: {time_config_result.get('reasoning', 'translated text')}")
        
        # ========== translated text2: translated text ==========
        report_progress(2, "translated text...")
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"translated text: {event_config_result.get('reasoning', 'translated text')}")
        
        # ========== translated text3-N: translated textAgenttranslated text ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                f"translated textAgenttranslated text ({start_idx + 1}-{end_idx}/{len(entities)})..."
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(f"Agenttranslated text: translated text {len(all_agent_configs)} translated text")
        
        # ========== translated text Agent ==========
        logger.info("translated text Agent...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(f"translated text: {assigned_count} translated text")
        
        # ========== translated text: translated text ==========
        report_progress(total_steps, "translated text...")
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        # translated text
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"translated text: {len(params.agent_configs)} translated textAgenttranslated text")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """translated textLLMtranslated text，translated text"""
        
        # translated text
        entity_summary = self._summarize_entities(entities)
        
        # translated text
        context_parts = [
            f"## translated text\n{simulation_requirement}",
            f"\n## translated text ({len(entities)}translated text)\n{entity_summary}",
        ]
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # translated text500translated text
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(translated text)"
            context_parts.append(f"\n## translated text\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """translated text"""
        lines = []
        
        # translated text
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)}translated text)")
            # translated text
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... translated text {len(type_entities) - display_count} translated text")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """translated textLLMtranslated text，translated textJSONtranslated text"""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # translated text
                    # translated textmax_tokens，translated textLLMtranslated text
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # translated text
                if finish_reason == 'length':
                    logger.warning(f"LLMtranslated text (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # translated textJSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSONtranslated text (attempt {attempt+1}): {str(e)[:80]}")
                    
                    # translated textJSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLMtranslated text (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLMtranslated text")
    
    def _fix_truncated_json(self, content: str) -> str:
        """translated textJSON"""
        content = content.strip()
        
        # translated text
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # translated text
        if content and content[-1] not in '",}]':
            content += '"'
        
        # translated text
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """translated textJSON"""
        import re
        
        # translated text
        content = self._fix_truncated_json(content)
        
        # translated textJSONtranslated text
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # translated text
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                # translated text
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """translated text"""
        # translated text
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        # translated text（80%translated textagenttranslated text）
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""translated text，translated text。

{context_truncated}

## translated text
translated textJSON。

### translated text（translated text，translated text）：
- translated text，translated text
- translated text0-5translated text（translated text0.05）
- translated text6-8translated text（translated text0.4）
- translated text9-18translated text（translated text0.7）
- translated text19-22translated text（translated text1.5）
- 23translated text（translated text0.5）
- translated text：translated text、translated text、translated text、translated text
- **translated text**：translated text，translated text、translated text
  - translated text：translated text21-23translated text；translated text；translated text
  - translated text：translated text，off_peak_hours translated text

### translated textJSONtranslated text（translated textmarkdown）

translated text：
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "translated text"
}}

translated text：
- total_simulation_hours (int): translated text，24-168translated text，translated text、translated text
- minutes_per_round (int): translated text，30-120translated text，translated text60translated text
- agents_per_hour_min (int): translated textAgenttranslated text（translated text: 1-{max_agents_allowed}）
- agents_per_hour_max (int): translated textAgenttranslated text（translated text: 1-{max_agents_allowed}）
- peak_hours (inttranslated text): translated text，translated text
- off_peak_hours (inttranslated text): translated text，translated text
- morning_hours (inttranslated text): translated text
- work_hours (inttranslated text): translated text
- reasoning (string): translated text"""

        system_prompt = "translated text。translated textJSONtranslated text，translated text。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"translated textLLMtranslated text: {e}, translated text")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """translated text（translated text）"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # translated text1translated text，translated text
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "translated text（translated text1translated text）"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """translated text，translated textagents_per_hourtranslated textagenttranslated text"""
        # translated text
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        # translated text：translated textagenttranslated text
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) translated textAgenttranslated text ({num_entities})，translated text")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) translated textAgenttranslated text ({num_entities})，translated text")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # translated text min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max，translated text {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # translated text1translated text
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # translated text
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """translated text"""
        
        # translated text，translated text LLM translated text
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # translated text
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # translated text
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""translated text，translated text。

translated text: {simulation_requirement}

{context_truncated}

## translated text
{type_info}

## translated text
translated textJSON：
- translated text
- translated text
- translated text，**translated text poster_type（translated text）**

**translated text**: poster_type translated text"translated text"translated text，translated text Agent translated text。
translated text：translated text Official/University translated text，translated text MediaOutlet translated text，translated text Student translated text。

translated textJSONtranslated text（translated textmarkdown）：
{{
    "hot_topics": ["translated text1", "translated text2", ...],
    "narrative_direction": "<translated text>",
    "initial_posts": [
        {{"content": "translated text", "poster_type": "translated text（translated text）"}},
        ...
    ],
    "reasoning": "<translated text>"
}}"""

        system_prompt = "translated text。translated textJSONtranslated text。translated text poster_type translated text。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"translated textLLMtranslated text: {e}, translated text")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "translated text"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """translated text"""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        translated text Agent
        
        translated text poster_type translated text agent_id
        """
        if not event_config.initial_posts:
            return event_config
        
        # translated text agent translated text
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # translated text（translated text LLM translated text）
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # translated text agent translated text，translated text agent
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # translated text agent
            matched_agent_id = None
            
            # 1. translated text
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. translated text
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. translated text，translated text agent
            if matched_agent_id is None:
                logger.warning(f"translated text '{poster_type}' translated text Agent，translated text Agent")
                if agent_configs:
                    # translated text，translated text
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f"translated text: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """translated textAgenttranslated text"""
        
        # translated text（translated text）
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f"""translated text，translated text。

translated text: {simulation_requirement}

## translated text
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## translated text
translated text，translated text：
- **translated text**：translated text0-5translated text，translated text19-22translated text
- **translated text**（University/GovernmentAgency）：translated text(0.1-0.3)，translated text(9-17)translated text，translated text(60-240translated text)，translated text(2.5-3.0)
- **translated text**（MediaOutlet）：translated text(0.4-0.6)，translated text(8-23)，translated text(5-30translated text)，translated text(2.0-2.5)
- **translated text**（Student/Person/Alumni）：translated text(0.6-0.9)，translated text(18-23)，translated text(1-15translated text)，translated text(0.8-1.2)
- **translated text/translated text**：translated text(0.4-0.6)，translated text(1.5-2.0)

translated textJSONtranslated text（translated textmarkdown）：
{{
    "agent_configs": [
        {{
            "agent_id": <translated text>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <translated text>,
            "comments_per_hour": <translated text>,
            "active_hours": [<translated text，translated text>],
            "response_delay_min": <translated text>,
            "response_delay_max": <translated text>,
            "sentiment_bias": <-1.0translated text1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <translated text>
        }},
        ...
    ]
}}"""

        system_prompt = "translated text。translated textJSON，translated text。"
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agenttranslated textLLMtranslated text: {e}, translated text")
            llm_configs = {}
        
        # translated textAgentActivityConfigtranslated text
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # translated textLLMtranslated text，translated text
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """translated textAgenttranslated text（translated text）"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # translated text：translated text，translated text，translated text
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # translated text：translated text，translated text，translated text
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # translated text/translated text：translated text+translated text，translated text
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # translated text：translated text，translated text
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # translated text+translated text
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # translated text：translated text
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # translated text+translated text
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # translated text：translated text
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # translated text+translated text
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

