"""
Zeptranslated text
translated textAgenttranslated textZeptranslated text
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """Agenttranslated text"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        """
        translated textZeptranslated text
        
        translated text，translated textZeptranslated text
        translated text，translated text
        """
        # translated text
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }
        
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        
        # translated text "agenttranslated text: translated text" translated text，translated text
        return f"{self.agent_name}: {description}"
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"translated text：「{content}」"
        return "translated text"
    
    def _describe_like_post(self) -> str:
        """translated text - translated text"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"translated text{post_author}translated text：「{post_content}」"
        elif post_content:
            return f"translated text：「{post_content}」"
        elif post_author:
            return f"translated text{post_author}translated text"
        return "translated text"
    
    def _describe_dislike_post(self) -> str:
        """translated text - translated text"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"translated text{post_author}translated text：「{post_content}」"
        elif post_content:
            return f"translated text：「{post_content}」"
        elif post_author:
            return f"translated text{post_author}translated text"
        return "translated text"
    
    def _describe_repost(self) -> str:
        """translated text - translated text"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        
        if original_content and original_author:
            return f"translated text{original_author}translated text：「{original_content}」"
        elif original_content:
            return f"translated text：「{original_content}」"
        elif original_author:
            return f"translated text{original_author}translated text"
        return "translated text"
    
    def _describe_quote_post(self) -> str:
        """translated text - translated text、translated text"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")
        
        base = ""
        if original_content and original_author:
            base = f"translated text{original_author}translated text「{original_content}」"
        elif original_content:
            base = f"translated text「{original_content}」"
        elif original_author:
            base = f"translated text{original_author}translated text"
        else:
            base = "translated text"
        
        if quote_content:
            base += f"，translated text：「{quote_content}」"
        return base
    
    def _describe_follow(self) -> str:
        """translated text - translated text"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"translated text「{target_user_name}」"
        return "translated text"
    
    def _describe_create_comment(self) -> str:
        """translated text - translated text"""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if content:
            if post_content and post_author:
                return f"translated text{post_author}translated text「{post_content}」translated text：「{content}」"
            elif post_content:
                return f"translated text「{post_content}」translated text：「{content}」"
            elif post_author:
                return f"translated text{post_author}translated text：「{content}」"
            return f"translated text：「{content}」"
        return "translated text"
    
    def _describe_like_comment(self) -> str:
        """translated text - translated text"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"translated text{comment_author}translated text：「{comment_content}」"
        elif comment_content:
            return f"translated text：「{comment_content}」"
        elif comment_author:
            return f"translated text{comment_author}translated text"
        return "translated text"
    
    def _describe_dislike_comment(self) -> str:
        """translated text - translated text"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"translated text{comment_author}translated text：「{comment_content}」"
        elif comment_content:
            return f"translated text：「{comment_content}」"
        elif comment_author:
            return f"translated text{comment_author}translated text"
        return "translated text"
    
    def _describe_search(self) -> str:
        """translated text - translated text"""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"translated text「{query}」" if query else "translated text"
    
    def _describe_search_user(self) -> str:
        """translated text - translated text"""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"translated text「{query}」" if query else "translated text"
    
    def _describe_mute(self) -> str:
        """translated text - translated text"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"translated text「{target_user_name}」"
        return "translated text"
    
    def _describe_generic(self) -> str:
        # translated text，translated text
        return f"translated text{self.action_type}translated text"


class ZepGraphMemoryUpdater:
    """
    Zeptranslated text
    
    translated textactionstranslated text，translated textagenttranslated textZeptranslated text。
    translated text，translated textBATCH_SIZEtranslated textZep。
    
    translated textZep，action_argstranslated text：
    - translated text/translated text
    - translated text/translated text
    - translated text/translated text
    - translated text/translated text
    """
    
    # translated text（translated text）
    BATCH_SIZE = 5
    
    # translated text（translated text）
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'translated text1',
        'reddit': 'translated text2',
    }
    
    # translated text（translated text），translated text
    SEND_INTERVAL = 0.5
    
    # translated text
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # translated text
    
    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        """
        translated text
        
        Args:
            graph_id: Zeptranslated textID
            api_key: Zep API Key（translated text，translated text）
        """
        self.graph_id = graph_id
        self.api_key = api_key or Config.ZEP_API_KEY
        
        if not self.api_key:
            raise ValueError("ZEP_API_KEYtranslated text")
        
        self.client = Zep(api_key=self.api_key)
        
        # translated text
        self._activity_queue: Queue = Queue()
        
        # translated text（translated textBATCH_SIZEtranslated text）
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()
        
        # translated text
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # translated text
        self._total_activities = 0  # translated text
        self._total_sent = 0        # translated textZeptranslated text
        self._total_items_sent = 0  # translated textZeptranslated text
        self._failed_count = 0      # translated text
        self._skipped_count = 0     # translated text（DO_NOTHING）
        
        logger.info(f"ZepGraphMemoryUpdater translated text: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")
    
    def _get_platform_display_name(self, platform: str) -> str:
        """translated text"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        """translated text"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"ZepMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"ZepGraphMemoryUpdater translated text: graph_id={self.graph_id}")
    
    def stop(self):
        """translated text"""
        self._running = False
        
        # translated text
        self._flush_remaining()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        
        logger.info(f"ZepGraphMemoryUpdater translated text: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")
    
    def add_activity(self, activity: AgentActivity):
        """
        translated textagenttranslated text
        
        translated text，translated text：
        - CREATE_POST（translated text）
        - CREATE_COMMENT（translated text）
        - QUOTE_POST（translated text）
        - SEARCH_POSTS（translated text）
        - SEARCH_USER（translated text）
        - LIKE_POST/DISLIKE_POST（translated text/translated text）
        - REPOST（translated text）
        - FOLLOW（translated text）
        - MUTE（translated text）
        - LIKE_COMMENT/DISLIKE_COMMENT（translated text/translated text）
        
        action_argstranslated text（translated text、translated text）。
        
        Args:
            activity: Agenttranslated text
        """
        # translated textDO_NOTHINGtranslated text
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(f"translated textZeptranslated text: {activity.agent_name} - {activity.action_type}")
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        translated text
        
        Args:
            data: translated textactions.jsonltranslated text
            platform: translated text (twitter/reddit)
        """
        # translated text
        if "event_type" in data:
            return
        
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        self.add_activity(activity)
    
    def _worker_loop(self):
        """translated text - translated textZep"""
        while self._running or not self._activity_queue.empty():
            try:
                # translated text（translated text1translated text）
                try:
                    activity = self._activity_queue.get(timeout=1)
                    
                    # translated text
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        # translated text
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # translated text
                            self._send_batch_activities(batch, platform)
                            # translated text，translated text
                            time.sleep(self.SEND_INTERVAL)
                    
                except Empty:
                    pass
                    
            except Exception as e:
                logger.error(f"translated text: {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        translated textZeptranslated text（translated text）
        
        Args:
            activities: Agenttranslated text
            platform: translated text
        """
        if not activities:
            return
        
        # translated text，translated text
        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)
        
        # translated text
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text
                )
                
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"translated text {len(activities)} translated text{display_name}translated text {self.graph_id}")
                logger.debug(f"translated text: {combined_text[:200]}...")
                return
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"translated textZeptranslated text (translated text {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"translated textZeptranslated text，translated text{self.MAX_RETRIES}translated text: {e}")
                    self._failed_count += 1
    
    def _flush_remaining(self):
        """translated text"""
        # translated text，translated text
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        # translated text（translated textBATCH_SIZEtranslated text）
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"translated text{display_name}translated text {len(buffer)} translated text")
                    self._send_batch_activities(buffer, platform)
            # translated text
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """translated text"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # translated text
            "batches_sent": self._total_sent,            # translated text
            "items_sent": self._total_items_sent,        # translated text
            "failed_count": self._failed_count,          # translated text
            "skipped_count": self._skipped_count,        # translated text（DO_NOTHING）
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # translated text
            "running": self._running,
        }


class ZepGraphMemoryManager:
    """
    translated textZeptranslated text
    
    translated text
    """
    
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        """
        translated text
        
        Args:
            simulation_id: translated textID
            graph_id: Zeptranslated textID
            
        Returns:
            ZepGraphMemoryUpdatertranslated text
        """
        with cls._lock:
            # translated text，translated text
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            
            updater = ZepGraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            
            logger.info(f"translated text: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        """translated text"""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        """translated text"""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"translated text: simulation_id={simulation_id}")
    
    # translated text stop_all translated text
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        """translated text"""
        # translated text
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"translated text: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("translated text")
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """translated text"""
        return {
            sim_id: updater.get_stats() 
            for sim_id, updater in cls._updaters.items()
        }
