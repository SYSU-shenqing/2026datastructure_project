"""
英雄联盟3v3技能施法系统 - 数据结构性能模拟器（完整展示版·修正）
====================================================================
对比三种数据结构：链表 vs 优先队列（堆） vs 二叉搜索树（BST）

控制链：引导(10) < 控制(90) < 解控(100)

特色场景：艾希R飞行0.8秒命中奥拉夫（眩晕2.5秒）→ 0.5秒后奥拉夫开R解控
         卡特R引导 → 盲僧R打断（技能终止，不再恢复）
"""

import heapq
import json
import time
import random
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Callable, Set
from enum import Enum, IntEnum
import os

# Python 3.6 兼容性补丁
if not hasattr(time, 'perf_counter_ns'):
    time.perf_counter_ns = lambda: int(time.perf_counter() * 1e9)


# ============================================================================
# 第一部分：枚举与常量定义
# ============================================================================

class SkillType(Enum):
    """技能类型枚举"""
    INSTANT = "instant"          # 瞬发
    CHANNEL = "channel"          # 引导
    PROJECTILE = "projectile"    # 弹道
    CONTROL = "control"          # 控制/打断
    CLEANSE = "cleanse"          # 解控


class SkillPriority(IntEnum):
    """技能优先级 - 数值越大优先级越高"""
    NORMAL = 0           # 普通技能
    MOVEMENT = 5         # 移动指令
    CHANNEL = 10         # 引导技能（可被打断）
    PROJECTILE = 15      # 弹道技能（高频）
    INSTANT = 20         # 瞬发技能
    CONTROL = 90         # 控制技能（打断引导）
    CLEANSE = 100        # 解控技能（最高优先级）


class ChampionID(IntEnum):
    """英雄ID枚举"""
    LUCIAN = 1      # 卢锡安 - 环形缓冲区代言人
    ASHE = 2        # 艾希 - 普通队列代言人
    OLAF = 3        # 奥拉夫 - 优先队列代言人（解控）
    KATARINA = 4    # 卡特琳娜 - 引导测试（被打断方）
    MALZAHAR = 5    # 马尔扎哈 - 控制压力（打断方）
    LEE_SIN = 6     # 盲僧 - 高频操作+控制


class Team(Enum):
    """队伍枚举"""
    BLUE = "蓝队"
    RED = "红队"


class ControlStatus(Enum):
    """控制状态枚举"""
    NONE = "无"
    STUNNED = "眩晕"
    SUPPRESSED = "压制"
    KNOCKED_UP = "击飞"
    SILENCED = "沉默"


# ============================================================================
# 英雄和技能中英文对照表
# ============================================================================

HERO_NAMES = {
    ChampionID.LUCIAN: "卢锡安",
    ChampionID.ASHE: "艾希",
    ChampionID.OLAF: "奥拉夫",
    ChampionID.KATARINA: "卡特琳娜",
    ChampionID.MALZAHAR: "马尔扎哈",
    ChampionID.LEE_SIN: "盲僧",
}

SKILL_FULL_NAMES = {
    "卢锡安_R": "圣枪洗礼(R)", "卢锡安_Q": "透体圣光(Q)", "卢锡安_E": "冷酷追击(E)",
    "艾希_W": "万箭齐发(W)", "艾希_R": "魔法水晶箭(R)", "艾希_Q": "射手的专注(Q)",
    "奥拉夫_R": "诸神黄昏(R)", "奥拉夫_E": "鲁莽挥击(E)", "奥拉夫_Q": "逆流投掷(Q)",
    "卡特琳娜_R": "死亡莲华(R)", "卡特琳娜_E": "瞬步(E)",
    "马尔扎哈_R": "冥府之握(R)", "马尔扎哈_Q": "虚空召唤(Q)",
    "盲僧_Q": "天音波(Q)", "盲僧_Q2": "回音击(二段Q)", "盲僧_W": "金钟罩(W)",
    "盲僧_E": "天雷破(E)", "盲僧_R": "猛龙摆尾(R)",
}

SKILL_SHORT_NAMES = {
    "卢锡安_R": "圣枪洗礼", "卢锡安_Q": "透体圣光", "卢锡安_E": "冷酷追击",
    "艾希_W": "万箭齐发", "艾希_R": "魔法水晶箭", "艾希_Q": "射手的专注",
    "奥拉夫_R": "诸神黄昏", "奥拉夫_E": "鲁莽挥击", "奥拉夫_Q": "逆流投掷",
    "卡特琳娜_R": "死亡莲华", "卡特琳娜_E": "瞬步",
    "马尔扎哈_R": "冥府之握", "马尔扎哈_Q": "虚空召唤",
    "盲僧_Q": "天音波", "盲僧_Q2": "回音击", "盲僧_W": "金钟罩",
    "盲僧_E": "天雷破", "盲僧_R": "猛龙摆尾",
}


def format_game_time(ms: float) -> str:
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    if minutes > 0:
        return f"{minutes}分{seconds:.1f}秒"
    else:
        return f"{seconds:.1f}秒"


def get_skill_full_name(skill_name: str) -> str:
    if skill_name in SKILL_FULL_NAMES:
        return SKILL_FULL_NAMES[skill_name]
    return skill_name


def get_skill_short_name(skill_name: str) -> str:
    if skill_name in SKILL_SHORT_NAMES:
        return SKILL_SHORT_NAMES[skill_name]
    return skill_name


# ============================================================================
# 第二部分：数据结构定义 (RTL层)
# ============================================================================

@dataclass
class SkillEvent:
    """技能事件"""
    timestamp: float
    champion_id: int
    caster_id: int
    skill_name: str
    skill_type: SkillType
    base_priority: int
    duration: float = 0.0
    target_id: Optional[int] = None
    bullet_count: int = 1
    applies_control: Optional[ControlStatus] = None
    control_duration: float = 0.0
    interrupts_channel: bool = False
    cleanses_self: bool = False
    actual_start_time: float = 0.0
    actual_end_time: float = 0.0
    was_interrupted: bool = False
    interrupted_by: Optional[int] = None
    is_projectile: bool = False
    projectile_hit_time: float = 0.0

    def get_dynamic_priority(self, current_time: float = 0) -> int:
        return self.base_priority

    def __lt__(self, other):
        if not isinstance(other, SkillEvent):
            return NotImplemented
        return self.base_priority < other.base_priority


@dataclass
class ProjectileObject:
    """弹道对象"""
    id: int
    owner_champion_id: int = 0
    is_active: bool = False
    created_at: float = 0.0
    target_id: Optional[int] = None
    source_skill: Optional[SkillEvent] = None
    hit_time: float = 0.0

    def reset(self) -> None:
        self.owner_champion_id = 0
        self.is_active = False
        self.created_at = 0.0
        self.target_id = None
        self.source_skill = None
        self.hit_time = 0.0


# ============================================================================
# 2.1 优先队列实现
# ============================================================================

class PrioritySkillQueue:
    def __init__(self, name: str = "优先队列"):
        self.name = name
        self._heap: List[Tuple[int, int, SkillEvent]] = []
        self._counter = 0
        self.push_count = 0
        self.pop_count = 0
        self.remove_count = 0
        self.total_push_time_ns = 0
        self.total_pop_time_ns = 0
        self.total_remove_time_ns = 0

    def push(self, event: SkillEvent) -> float:
        start = time.perf_counter_ns()
        priority = -event.get_dynamic_priority()
        heapq.heappush(self._heap, (priority, self._counter, event))
        self._counter += 1
        self.push_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_push_time_ns += cost_ns
        return cost_ns / 1_000_000

    def pop(self) -> Tuple[Optional[SkillEvent], float]:
        start = time.perf_counter_ns()
        if not self._heap:
            return None, 0
        event = heapq.heappop(self._heap)[2]
        self.pop_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_pop_time_ns += cost_ns
        return event, cost_ns / 1_000_000

    def __len__(self) -> int:
        return len(self._heap)

    def get_stats(self) -> Dict:
        return {
            "name": self.name, "push_count": self.push_count, "pop_count": self.pop_count,
            "avg_push_us": (self.total_push_time_ns / max(self.push_count, 1)) / 1000,
            "avg_pop_us": (self.total_pop_time_ns / max(self.pop_count, 1)) / 1000,
            "current_depth": len(self._heap)
        }


# ============================================================================
# 2.2 链表实现
# ============================================================================

class LinkedListSkillQueue:
    def __init__(self, name: str = "链表"):
        self.name = name
        self._queue: List[SkillEvent] = []
        self.push_count = 0
        self.pop_count = 0
        self.total_push_time_ns = 0
        self.total_pop_time_ns = 0

    def push(self, event: SkillEvent) -> float:
        start = time.perf_counter_ns()
        self._queue.append(event)
        self.push_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_push_time_ns += cost_ns
        return cost_ns / 1_000_000

    def insert_priority(self, event: SkillEvent) -> float:
        start = time.perf_counter_ns()
        priority = event.get_dynamic_priority()
        inserted = False
        for i, e in enumerate(self._queue):
            if e.get_dynamic_priority() < priority:
                self._queue.insert(i, event)
                inserted = True
                break
        if not inserted:
            self._queue.append(event)
        self.push_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_push_time_ns += cost_ns
        return cost_ns / 1_000_000

    def pop(self) -> Tuple[Optional[SkillEvent], float]:
        start = time.perf_counter_ns()
        if not self._queue:
            return None, 0
        event = self._queue.pop(0)
        self.pop_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_pop_time_ns += cost_ns
        return event, cost_ns / 1_000_000

    def __len__(self) -> int:
        return len(self._queue)

    def get_stats(self) -> Dict:
        return {
            "name": self.name, "push_count": self.push_count, "pop_count": self.pop_count,
            "avg_push_us": (self.total_push_time_ns / max(self.push_count, 1)) / 1000,
            "avg_pop_us": (self.total_pop_time_ns / max(self.pop_count, 1)) / 1000,
            "current_depth": len(self._queue)
        }


# ============================================================================
# 2.3 BST实现
# ============================================================================

class BSTNode:
    def __init__(self, event: SkillEvent):
        self.event = event
        self.priority = event.get_dynamic_priority()
        self.left: Optional['BSTNode'] = None
        self.right: Optional['BSTNode'] = None
        self.parent: Optional['BSTNode'] = None


class BSTSkillQueue:
    def __init__(self, name: str = "二叉搜索树"):
        self.name = name
        self.root: Optional[BSTNode] = None
        self._size: int = 0
        self.push_count = 0
        self.pop_count = 0
        self.total_push_time_ns = 0
        self.total_pop_time_ns = 0

    def push(self, event: SkillEvent) -> float:
        start = time.perf_counter_ns()
        new_node = BSTNode(event)
        self._size += 1
        self.push_count += 1

        if self.root is None:
            self.root = new_node
            cost_ns = time.perf_counter_ns() - start
            self.total_push_time_ns += cost_ns
            return cost_ns / 1_000_000

        current = self.root
        while True:
            if event.base_priority < current.priority:
                if current.left is None:
                    current.left = new_node
                    new_node.parent = current
                    break
                current = current.left
            else:
                if current.right is None:
                    current.right = new_node
                    new_node.parent = current
                    break
                current = current.right

        cost_ns = time.perf_counter_ns() - start
        self.total_push_time_ns += cost_ns
        return cost_ns / 1_000_000

    def _find_max(self) -> Optional[BSTNode]:
        if self.root is None:
            return None
        current = self.root
        while current.right is not None:
            current = current.right
        return current

    def _remove_node(self, node: BSTNode) -> None:
        if node.left is None and node.right is None:
            if node.parent is None:
                self.root = None
            elif node.parent.left == node:
                node.parent.left = None
            else:
                node.parent.right = None
        elif node.left is None:
            if node.parent is None:
                self.root = node.right
                node.right.parent = None
            elif node.parent.left == node:
                node.parent.left = node.right
                node.right.parent = node.parent
            else:
                node.parent.right = node.right
                node.right.parent = node.parent
        elif node.right is None:
            if node.parent is None:
                self.root = node.left
                node.left.parent = None
            elif node.parent.left == node:
                node.parent.left = node.left
                node.left.parent = node.parent
            else:
                node.parent.right = node.left
                node.left.parent = node.parent
        else:
            predecessor = node.left
            while predecessor.right is not None:
                predecessor = predecessor.right
            node.event = predecessor.event
            node.priority = predecessor.priority
            self._remove_node(predecessor)
            return
        self._size -= 1

    def pop(self) -> Tuple[Optional[SkillEvent], float]:
        start = time.perf_counter_ns()
        max_node = self._find_max()
        if max_node is None:
            return None, 0
        event = max_node.event
        self._remove_node(max_node)
        self.pop_count += 1
        cost_ns = time.perf_counter_ns() - start
        self.total_pop_time_ns += cost_ns
        return event, cost_ns / 1_000_000

    def __len__(self) -> int:
        return self._size

    def get_stats(self) -> Dict:
        return {
            "name": self.name, "push_count": self.push_count, "pop_count": self.pop_count,
            "avg_push_us": (self.total_push_time_ns / max(self.push_count, 1)) / 1000,
            "avg_pop_us": (self.total_pop_time_ns / max(self.pop_count, 1)) / 1000,
            "current_depth": self._size
        }


# ============================================================================
# 2.4 环形缓冲区
# ============================================================================

class RingBufferPool:
    def __init__(self, capacity: int = 60, name: str = "环形缓冲区"):
        self.name = name
        self.capacity = capacity
        self.pool: List[ProjectileObject] = []
        for i in range(capacity):
            self.pool.append(ProjectileObject(id=i))
        self.write_index = 0
        self.acquire_count = 0
        self.release_count = 0
        self.naive_allocation_count = 0

    def acquire(self, champion_id: int, current_time: float,
                target_id: Optional[int] = None,
                source_skill: Optional[SkillEvent] = None,
                flight_time: float = 500) -> Tuple[ProjectileObject, float]:
        start = time.perf_counter_ns()
        for _ in range(self.capacity):
            obj = self.pool[self.write_index]
            if not obj.is_active:
                obj.is_active = True
                obj.owner_champion_id = champion_id
                obj.created_at = current_time
                obj.target_id = target_id
                obj.source_skill = source_skill
                obj.hit_time = current_time + flight_time
                self.acquire_count += 1
                self.naive_allocation_count += 1
                cost_ns = time.perf_counter_ns() - start
                return obj, cost_ns / 1_000_000
            self.write_index = (self.write_index + 1) % self.capacity

        obj = self.pool[self.write_index]
        obj.reset()
        obj.is_active = True
        obj.owner_champion_id = champion_id
        obj.created_at = current_time
        obj.target_id = target_id
        obj.source_skill = source_skill
        obj.hit_time = current_time + flight_time
        self.acquire_count += 1
        self.naive_allocation_count += 1
        cost_ns = time.perf_counter_ns() - start
        return obj, cost_ns / 1_000_000

    def release(self, obj: ProjectileObject) -> None:
        obj.is_active = False
        self.release_count += 1

    def get_stats(self) -> Dict:
        return {
            "name": self.name, "capacity": self.capacity,
            "acquire_count": self.acquire_count, "release_count": self.release_count,
            "naive_allocations": self.naive_allocation_count,
            "gc_events_saved": self.naive_allocation_count // 100,
            "reuse_ratio": self.acquire_count / max(self.naive_allocation_count, 1)
        }


# ============================================================================
# 2.5 控制状态管理器
# ============================================================================

class ControlStateManager:
    """控制状态管理器 - 支持控制自动过期，被打断的技能不再恢复"""

    def __init__(self):
        self.hero_control_status: Dict[int, ControlStatus] = {}
        self.hero_control_source: Dict[int, SkillEvent] = {}
        self.hero_control_end_time: Dict[int, float] = {}
        self.channeling_heroes: Dict[int, SkillEvent] = {}
        self.control_immune_heroes: Set[int] = set()
        self.control_immune_end_time: Dict[int, float] = {}
        self.interrupted_skills: Set[str] = set()

    def update(self, current_time: float) -> List[int]:
        expired_heroes = []
        for hero_id, end_time in list(self.hero_control_end_time.items()):
            if current_time >= end_time:
                self.remove_control(hero_id)
                expired_heroes.append(hero_id)
        for hero_id, end_time in list(self.control_immune_end_time.items()):
            if current_time >= end_time:
                self.control_immune_heroes.discard(hero_id)
                del self.control_immune_end_time[hero_id]
        return expired_heroes

    def apply_control(self, target_id: int, control_type: ControlStatus,
                      source_skill: SkillEvent, current_time: float) -> bool:
        if target_id in self.control_immune_heroes:
            return False
        if target_id in self.channeling_heroes:
            channel_skill = self.channeling_heroes[target_id]
            channel_skill.was_interrupted = True
            channel_skill.interrupted_by = source_skill.caster_id
            self.interrupted_skills.add(channel_skill.skill_name)
            del self.channeling_heroes[target_id]
        self.hero_control_status[target_id] = control_type
        self.hero_control_source[target_id] = source_skill
        if source_skill.control_duration > 0:
            self.hero_control_end_time[target_id] = current_time + source_skill.control_duration
        return True

    def remove_control(self, target_id: int) -> bool:
        if target_id in self.hero_control_status:
            del self.hero_control_status[target_id]
            if target_id in self.hero_control_source:
                del self.hero_control_source[target_id]
            if target_id in self.hero_control_end_time:
                del self.hero_control_end_time[target_id]
            return True
        return False

    def apply_cleanse(self, caster_id: int, current_time: float,
                      immune_duration: float = 6000) -> Tuple[bool, List[SkillEvent], Optional[str]]:
        removed_controls = []
        had_control = caster_id in self.hero_control_status
        cleansed_skill_name = None
        if had_control:
            if caster_id in self.hero_control_source:
                source = self.hero_control_source[caster_id]
                removed_controls.append(source)
                cleansed_skill_name = get_skill_short_name(source.skill_name)
            self.remove_control(caster_id)
        self.control_immune_heroes.add(caster_id)
        self.control_immune_end_time[caster_id] = current_time + immune_duration
        return had_control, removed_controls, cleansed_skill_name

    def is_skill_interrupted(self, skill_name: str) -> bool:
        return skill_name in self.interrupted_skills

    def start_channel(self, hero_id: int, skill: SkillEvent) -> bool:
        if hero_id in self.hero_control_status:
            skill.was_interrupted = True
            return False
        if skill.skill_name in self.interrupted_skills:
            skill.was_interrupted = True
            return False
        self.channeling_heroes[hero_id] = skill
        return True

    def end_channel(self, hero_id: int) -> None:
        if hero_id in self.channeling_heroes:
            del self.channeling_heroes[hero_id]

    def is_channeling(self, hero_id: int) -> bool:
        return hero_id in self.channeling_heroes


# ============================================================================
# 第三部分：英雄定义与工厂
# ============================================================================

@dataclass
class HeroConfig:
    id: int
    name: str
    team: Team
    role: str
    data_structure: str
    data_structure_icon: str
    test_focus: str
    skills: Dict[str, Dict]
    special_mechanic: Dict[str, str]


class HeroFactory:
    HERO_CONFIGS: Dict[int, HeroConfig] = {
        ChampionID.LUCIAN: HeroConfig(
            id=ChampionID.LUCIAN, name="卢锡安", team=Team.BLUE, role="射手",
            data_structure="环形缓冲区", data_structure_icon="🔄", test_focus="子弹对象池复用",
            skills={
                "R": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.PROJECTILE.value,
                      "bullet_count": 34, "duration": 3000, "description": "在3秒内发射34发子弹"},
                "Q": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.NORMAL.value,
                      "bullet_count": 1, "description": "发射穿透子弹"},
                "E": {"type": SkillType.INSTANT, "base_priority": SkillPriority.MOVEMENT.value,
                      "description": "短距离位移"}
            },
            special_mechanic={"name": "子弹对象池复用", "description": "R技能34发子弹复用环形缓冲区"}
        ),
        ChampionID.ASHE: HeroConfig(
            id=ChampionID.ASHE, name="艾希", team=Team.BLUE, role="辅助",
            data_structure="链表/队列", data_structure_icon="📋", test_focus="先进先出基线",
            skills={
                "W": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.NORMAL.value,
                      "description": "发射扇形箭矢"},
                "R": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.NORMAL.value,
                      "applies_control": ControlStatus.STUNNED, "control_duration": 2500,
                      "is_projectile": True, "flight_time": 800,
                      "description": "发射远程眩晕水晶箭"},
                "Q": {"type": SkillType.CHANNEL, "base_priority": SkillPriority.CHANNEL.value,
                      "duration": 4000, "description": "增加攻速"}
            },
            special_mechanic={"name": "先进先出序列验证", "description": "技能严格按顺序执行"}
        ),
        ChampionID.OLAF: HeroConfig(
            id=ChampionID.OLAF, name="奥拉夫", team=Team.BLUE, role="前排",
            data_structure="优先队列", data_structure_icon="⚡", test_focus="解控优先级",
            skills={
                "R": {"type": SkillType.CLEANSE, "base_priority": SkillPriority.CLEANSE.value,
                      "duration": 6000, "cleanses_self": True, "description": "移除控制并免疫控制6秒"},
                "E": {"type": SkillType.INSTANT, "base_priority": SkillPriority.INSTANT.value,
                      "description": "真实伤害"},
                "Q": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.NORMAL.value,
                      "description": "扔斧头"}
            },
            special_mechanic={"name": "最高优先级解控", "description": "R技能优先级100，被控时瞬间插队解控"}
        ),
        ChampionID.KATARINA: HeroConfig(
            id=ChampionID.KATARINA, name="卡特琳娜", team=Team.RED, role="中单",
            data_structure="引导目标", data_structure_icon="🎯", test_focus="引导被打断测试",
            skills={
                "R": {"type": SkillType.CHANNEL, "base_priority": SkillPriority.CHANNEL.value,
                      "duration": 2500, "description": "持续引导2.5秒，可被控制打断"},
                "E": {"type": SkillType.INSTANT, "base_priority": SkillPriority.INSTANT.value,
                      "description": "瞬移到匕首位置"}
            },
            special_mechanic={"name": "引导技能测试", "description": "测试引导技能被控制打断"}
        ),
        ChampionID.MALZAHAR: HeroConfig(
            id=ChampionID.MALZAHAR, name="马尔扎哈", team=Team.RED, role="法师",
            data_structure="控制源", data_structure_icon="🔒", test_focus="控制打断",
            skills={
                "R": {"type": SkillType.CONTROL, "base_priority": SkillPriority.CONTROL.value,
                      "duration": 2500, "applies_control": ControlStatus.SUPPRESSED,
                      "control_duration": 2500, "interrupts_channel": True,
                      "description": "压制目标2.5秒，可打断引导"},
                "Q": {"type": SkillType.CONTROL, "base_priority": SkillPriority.CONTROL.value - 5,
                      "applies_control": ControlStatus.SILENCED, "control_duration": 2000,
                      "interrupts_channel": True, "description": "沉默目标"}
            },
            special_mechanic={"name": "控制打断", "description": "高优先级控制技能可打断引导"}
        ),
        ChampionID.LEE_SIN: HeroConfig(
            id=ChampionID.LEE_SIN, name="盲僧", team=Team.RED, role="打野",
            data_structure="高频操作", data_structure_icon="👊", test_focus="高频连招",
            skills={
                "Q": {"type": SkillType.PROJECTILE, "base_priority": SkillPriority.NORMAL.value,
                      "description": "发射音波"},
                "Q2": {"type": SkillType.INSTANT, "base_priority": SkillPriority.INSTANT.value,
                       "description": "突进到目标"},
                "W": {"type": SkillType.INSTANT, "base_priority": SkillPriority.MOVEMENT.value,
                      "description": "位移并获得护盾"},
                "E": {"type": SkillType.INSTANT, "base_priority": SkillPriority.NORMAL.value,
                      "description": "范围伤害"},
                "R": {"type": SkillType.CONTROL, "base_priority": SkillPriority.CONTROL.value,
                      "applies_control": ControlStatus.KNOCKED_UP, "control_duration": 1000,
                      "interrupts_channel": True, "description": "击退目标，可打断引导"}
            },
            special_mechanic={"name": "高频连招+控制打断", "description": "快速连招中插入控制技能"}
        )
    }

    @classmethod
    def get_config(cls, champion_id: int) -> Optional[HeroConfig]:
        return cls.HERO_CONFIGS.get(champion_id)

    @classmethod
    def create_skill_event(cls, champion_id: int, skill_key: str,
                           timestamp: float, target_id: Optional[int] = None) -> Optional[SkillEvent]:
        config = cls.get_config(champion_id)
        if not config or skill_key not in config.skills:
            return None
        skill_data = config.skills[skill_key]
        return SkillEvent(
            timestamp=timestamp, champion_id=champion_id, caster_id=champion_id,
            skill_name=f"{config.name}_{skill_key}", skill_type=skill_data["type"],
            base_priority=skill_data["base_priority"], duration=skill_data.get("duration", 0.0),
            target_id=target_id, bullet_count=skill_data.get("bullet_count", 1),
            applies_control=skill_data.get("applies_control"),
            control_duration=skill_data.get("control_duration", 0.0),
            interrupts_channel=skill_data.get("interrupts_channel", False),
            cleanses_self=skill_data.get("cleanses_self", False),
            is_projectile=skill_data.get("is_projectile", False),
            projectile_hit_time=timestamp + skill_data.get("flight_time", 0)
        )


# ============================================================================
# 第四部分：时间轴事件与指标采集
# ============================================================================

@dataclass
class TimelineEvent:
    time: float
    event_type: str
    champion_id: int
    champion_name: str
    skill_name: str
    priority: int
    queue_depth: int
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    total_push: int = 0
    total_pop: int = 0
    total_interrupt: int = 0
    total_cleanse: int = 0
    total_bullet_acquire: int = 0
    max_queue_depth: int = 0
    push_times_us: List[float] = field(default_factory=list)
    pop_times_us: List[float] = field(default_factory=list)

    def record_push(self, cost_us: float, champion_id: int) -> None:
        self.total_push += 1
        self.push_times_us.append(cost_us)

    def record_pop(self, cost_us: float, champion_id: int) -> None:
        self.total_pop += 1
        self.pop_times_us.append(cost_us)

    def record_interrupt(self) -> None:
        self.total_interrupt += 1

    def record_cleanse(self) -> None:
        self.total_cleanse += 1

    def get_avg_push_time(self) -> float:
        return sum(self.push_times_us) / len(self.push_times_us) if self.push_times_us else 0.0


# ============================================================================
# 第五部分：仿真驱动器
# ============================================================================

class QueueType(Enum):
    LINKED_LIST = "链表"
    PRIORITY_QUEUE = "优先队列"
    BST = "二叉搜索树"


class SimulationDriver:
    def __init__(self, queue_type: QueueType, name: str = "仿真", verbose: bool = True):
        self.name = name
        self.queue_type = queue_type
        self.verbose = verbose

        if queue_type == QueueType.PRIORITY_QUEUE:
            self.skill_queue = PrioritySkillQueue(f"{name}_优先队列")
        elif queue_type == QueueType.BST:
            self.skill_queue = BSTSkillQueue(f"{name}_BST")
        else:
            self.skill_queue = LinkedListSkillQueue(f"{name}_链表")

        self.bullet_pool = RingBufferPool(capacity=60)
        self.control_manager = ControlStateManager()

        self.current_time: float = 0.0
        self.events: List[SkillEvent] = []
        self.active_skills: Dict[str, SkillEvent] = {}
        self.active_projectiles: List[ProjectileObject] = []
        self.pending_control_events: List[Tuple[float, SkillEvent]] = []

        self.timeline: List[TimelineEvent] = []
        self.metrics = PerformanceMetrics()

        self.frame_interval = 16.6
        self.last_frame_time = 0.0

    def _log(self, icon: str, msg: str) -> None:
        if self.verbose:
            print(f"[{format_game_time(self.current_time):>10}] {icon} {msg}")

    def load_events(self, events: List[SkillEvent]) -> None:
        self.events = sorted(events, key=lambda e: e.timestamp)
        print(f"\n[{self.name}] 加载 {len(self.events)} 个技能事件")
        if self.verbose:
            print("\n" + "=" * 70)
            print(f"🎮 开始仿真 - {self.name} (数据结构: {self.queue_type.value})")
            print("=" * 70)
            print("\n📌 场景说明：")
            print("   艾希R飞行0.8秒命中奥拉夫（眩晕2.5秒）→ 0.5秒后奥拉夫开R解控")
            print("   卡特R引导 → 盲僧R打断（技能终止，不再恢复）")
            print("   " + "─" * 55 + "\n")

    def run(self, duration_ms: float) -> None:
        print(f"[{self.name}] 仿真持续 {format_game_time(duration_ms)}\n")
        start_wall = time.perf_counter()
        event_index = 0

        while self.current_time < duration_ms:
            self.control_manager.update(self.current_time)
            self._process_pending_controls()

            while event_index < len(self.events) and self.events[event_index].timestamp <= self.current_time:
                self._inject_event(self.events[event_index])
                event_index += 1

            if self.current_time - self.last_frame_time >= self.frame_interval:
                self._process_frame()
                self.last_frame_time = self.current_time

            self._update_active_skills()
            self._update_projectiles()
            self.current_time += 1.0

        wall_time = time.perf_counter() - start_wall

        if self.verbose:
            print("\n" + "=" * 70)
            print("🏁 仿真完成")
            print("=" * 70)

        print(f"\n[{self.name}] 仿真完成")
        print(f"  模拟时间: {format_game_time(duration_ms)}, 实际耗时: {wall_time:.3f}秒")
        print(f"  总事件: 施放={self.metrics.total_push}, 执行={self.metrics.total_pop}")
        print(f"  打断次数: {self.metrics.total_interrupt}, 解控次数: {self.metrics.total_cleanse}")

    def _process_pending_controls(self) -> None:
        ready = []
        remaining = []
        for hit_time, event in self.pending_control_events:
            if self.current_time >= hit_time:
                ready.append((hit_time, event))
            else:
                remaining.append((hit_time, event))
        self.pending_control_events = remaining
        for hit_time, event in ready:
            self._apply_control_effect(event, hit_time)

    def _apply_control_effect(self, event: SkillEvent, hit_time: float) -> None:
        if not event.applies_control or not event.target_id:
            return
        target_config = HeroFactory.get_config(event.target_id)
        target_name = target_config.name if target_config else "未知"
        hero_name = HERO_NAMES.get(event.champion_id, "未知")
        control_name = event.applies_control.value
        was_channeling = self.control_manager.is_channeling(event.target_id)

        success = self.control_manager.apply_control(
            event.target_id, event.applies_control, event, hit_time
        )

        if success:
            self._log('🎯', f"【命中】{hero_name} 的 {get_skill_full_name(event.skill_name)} 命中了 {target_name}！")
            self._log('💫', f"       {target_name} 被{control_name}了！持续{event.control_duration/1000:.1f}秒")

            # 记录命中事件
            self.timeline.append(TimelineEvent(
                time=hit_time, event_type="命中", champion_id=event.champion_id,
                champion_name=hero_name, skill_name=event.skill_name,
                priority=event.base_priority, queue_depth=len(self.skill_queue),
                extra={"target": event.target_id, "control": control_name}
            ))

            # 添加被控制状态到目标英雄
            self.timeline.append(TimelineEvent(
                time=hit_time, event_type="被控制", champion_id=event.target_id,
                champion_name=target_name, skill_name="",
                priority=0, queue_depth=len(self.skill_queue),
                extra={"control_type": control_name, "source": hero_name, "source_skill": get_skill_short_name(event.skill_name)}
            ))

            if was_channeling:
                self.metrics.record_interrupt()
                self._log('💥', f"【打断】{hero_name} 打断了 {target_name} 的引导技能！")
                self.timeline.append(TimelineEvent(
                    time=hit_time, event_type="打断", champion_id=event.champion_id,
                    champion_name=hero_name, skill_name=event.skill_name,
                    priority=event.base_priority, queue_depth=len(self.skill_queue),
                    extra={"interrupted_target": event.target_id}
                ))

    def _inject_event(self, event: SkillEvent) -> None:
        hero_name = HERO_NAMES.get(event.champion_id, "未知")
        skill_full_name = get_skill_full_name(event.skill_name)

        if self.queue_type == QueueType.LINKED_LIST:
            if event.base_priority >= SkillPriority.CONTROL.value:
                cost_ms = self.skill_queue.insert_priority(event)
                self._log('📥', f"【施放·插队】{hero_name} 使用 {skill_full_name} (优先级 {event.base_priority})")
            else:
                cost_ms = self.skill_queue.push(event)
                self._log('📥', f"【施放】{hero_name} 使用 {skill_full_name} (优先级 {event.base_priority})")
        else:
            cost_ms = self.skill_queue.push(event)
            if event.base_priority >= SkillPriority.CONTROL.value:
                self._log('📥', f"【施放·高优先级】{hero_name} 使用 {skill_full_name} (优先级 {event.base_priority})")
            else:
                self._log('📥', f"【施放】{hero_name} 使用 {skill_full_name} (优先级 {event.base_priority})")

        self.metrics.record_push(cost_ms * 1000, event.champion_id)

        self.timeline.append(TimelineEvent(
            time=self.current_time, event_type="施放", champion_id=event.champion_id,
            champion_name=hero_name, skill_name=event.skill_name,
            priority=event.base_priority, queue_depth=len(self.skill_queue),
            extra={"push_cost_us": cost_ms * 1000}
        ))

        # 如果是弹道技能，记录射出事件
        if event.is_projectile and event.target_id:
            flight_time = event.projectile_hit_time - event.timestamp
            projectile, _ = self.bullet_pool.acquire(
                event.champion_id, self.current_time, event.target_id, event, flight_time
            )
            self.active_projectiles.append(projectile)
            self.pending_control_events.append((event.projectile_hit_time, event))

            # 记录射出事件
            self.timeline.append(TimelineEvent(
                time=self.current_time, event_type="射出", champion_id=event.champion_id,
                champion_name=hero_name, skill_name=event.skill_name,
                priority=event.base_priority, queue_depth=len(self.skill_queue),
                extra={"flight_time": flight_time, "target": event.target_id, "hit_time": event.projectile_hit_time}
            ))

            self._log('🏹', f"【射出】{hero_name} 射出 {skill_full_name}，预计 {flight_time/1000:.1f} 秒后命中")

    def _process_frame(self) -> None:
        if len(self.skill_queue) == 0:
            return

        event, cost_ms = self.skill_queue.pop()
        if event is None:
            return

        self.metrics.record_pop(cost_ms * 1000, event.champion_id)
        event.actual_start_time = self.current_time

        hero_name = HERO_NAMES.get(event.champion_id, "未知")
        skill_full_name = get_skill_full_name(event.skill_name)
        config = HeroFactory.get_config(event.champion_id)
        skill_data = config.skills.get(event.skill_name.split('_')[-1], {})
        skill_desc = skill_data.get('description', '')

        # 处理解控技能
        if event.cleanses_self:
            had_control, removed, cleansed_name = self.control_manager.apply_cleanse(
                event.caster_id, self.current_time, event.duration
            )
            if had_control:
                self.metrics.record_cleanse()
                self._log('🧹', f"【解控】{hero_name} 的 {skill_full_name} 解除了 {cleansed_name} 的控制！")
                self._log('✨', f"       {hero_name} 现在免疫所有控制效果，持续{event.duration/1000:.0f}秒！")
                self.timeline.append(TimelineEvent(
                    time=self.current_time, event_type="解控", champion_id=event.champion_id,
                    champion_name=hero_name, skill_name=event.skill_name,
                    priority=event.base_priority, queue_depth=len(self.skill_queue),
                    extra={"removed_control": cleansed_name}
                ))
                # 记录控制被移除
                self.timeline.append(TimelineEvent(
                    time=self.current_time, event_type="控制结束", champion_id=event.caster_id,
                    champion_name=hero_name, skill_name="",
                    priority=0, queue_depth=len(self.skill_queue),
                    extra={"reason": "解控", "removed": cleansed_name}
                ))
            else:
                self._log('⚡', f"【施放】{hero_name} 使用 {skill_full_name} - {skill_desc}")

        # 处理非弹道的控制技能
        if event.applies_control and event.target_id and not event.is_projectile:
            self._apply_control_effect(event, self.current_time)

        # 记录开始执行
        if not event.cleanses_self:
            if event.skill_type == SkillType.CHANNEL:
                can_start = self.control_manager.start_channel(event.caster_id, event)
                if can_start:
                    self._log('⚡', f"【引导】{hero_name} 开始引导 {skill_full_name} - {skill_desc} (持续 {event.duration/1000:.1f}秒)")
                else:
                    self._log('❌', f"【中断】{hero_name} 的 {skill_full_name} 无法开始（已被控制或打断）")
                    event.was_interrupted = True
            elif event.skill_type == SkillType.PROJECTILE and event.bullet_count > 1:
                self._log('⚡', f"【施放】{hero_name} 使用 {skill_full_name} - {skill_desc} (共{event.bullet_count}发子弹)")
                for i in range(event.bullet_count):
                    self.bullet_pool.acquire(event.champion_id, self.current_time)
                    self.metrics.total_bullet_acquire += 1
                    if i % 10 == 0:
                        self._log('🔫', f"【子弹】{hero_name} 第{i+1}发子弹")
            else:
                self._log('⚡', f"【施放】{hero_name} 使用 {skill_full_name} - {skill_desc}")

        self.timeline.append(TimelineEvent(
            time=self.current_time, event_type="开始执行", champion_id=event.champion_id,
            champion_name=hero_name, skill_name=event.skill_name,
            priority=event.base_priority, queue_depth=len(self.skill_queue),
            extra={"duration": event.duration, "target": event.target_id}
        ))

        if event.duration > 0 and not event.was_interrupted:
            self.active_skills[event.skill_name] = event

    def _update_active_skills(self) -> None:
        completed = []
        for skill_name, skill in self.active_skills.items():
            if skill.was_interrupted:
                completed.append(skill_name)
                hero_name = HERO_NAMES.get(skill.champion_id, "未知")
                self._log('❌', f"【中断】{hero_name} 的 {get_skill_full_name(skill.skill_name)} 被打断！")
                self.timeline.append(TimelineEvent(
                    time=self.current_time, event_type="执行结束", champion_id=skill.champion_id,
                    champion_name=hero_name, skill_name=skill.skill_name,
                    priority=skill.base_priority, queue_depth=len(self.skill_queue),
                    extra={"interrupted": True, "interrupted_by": skill.interrupted_by}
                ))
                self.control_manager.end_channel(skill.caster_id)
                continue

            elapsed = self.current_time - skill.actual_start_time
            if elapsed >= skill.duration:
                skill.actual_end_time = self.current_time
                completed.append(skill_name)
                hero_name = HERO_NAMES.get(skill.champion_id, "未知")
                self._log('✅', f"【完成】{hero_name} 的 {get_skill_full_name(skill.skill_name)} 施放完成")
                self.timeline.append(TimelineEvent(
                    time=self.current_time, event_type="执行结束", champion_id=skill.champion_id,
                    champion_name=hero_name, skill_name=skill.skill_name,
                    priority=skill.base_priority, queue_depth=len(self.skill_queue),
                    extra={"completed": True}
                ))
                if skill.skill_type == SkillType.CHANNEL:
                    self.control_manager.end_channel(skill.caster_id)

        for skill_name in completed:
            del self.active_skills[skill_name]

    def _update_projectiles(self) -> None:
        expired = []
        for p in self.active_projectiles:
            if self.current_time >= p.hit_time:
                expired.append(p)
        for p in expired:
            self.bullet_pool.release(p)
            self.active_projectiles.remove(p)

    def get_stats(self) -> Dict:
        queue_stats = self.skill_queue.get_stats()
        pool_stats = self.bullet_pool.get_stats()
        return {
            "simulation_name": self.name, "queue_type": self.queue_type.value,
            "total_events": len(self.events), "simulation_duration": self.current_time,
            "queue_stats": queue_stats, "pool_stats": pool_stats,
            "metrics": {
                "total_push": self.metrics.total_push, "total_pop": self.metrics.total_pop,
                "total_interrupt": self.metrics.total_interrupt, "total_cleanse": self.metrics.total_cleanse,
                "total_bullet_acquire": self.metrics.total_bullet_acquire,
                "max_queue_depth": self.metrics.max_queue_depth,
                "avg_push_us": self.metrics.get_avg_push_time(),
            }
        }

    def get_timeline_data(self) -> List[Dict]:
        return [asdict(e) for e in self.timeline]


# ============================================================================
# 第六部分：场景生成器（修改后：只射奥拉夫一次）
# ============================================================================

class ScenarioGenerator:
    @staticmethod
    def generate_team_fight() -> List[SkillEvent]:
        return ScenarioGenerator.generate_showcase_scene()

    @staticmethod
    def generate_showcase_scene() -> List[SkillEvent]:
        """
        时间线：
        0.0秒:   艾希 W
        0.5秒:   艾希 Q
        3.0秒:   卢锡安 E
        3.5秒:   卢锡安 R (34发子弹)
        4.0秒:   艾希 R 射出 → 目标奥拉夫（飞行0.8秒，4.8秒命中，眩晕2.5秒）
        5.0秒:   卡特琳娜 E
        5.3秒:   奥拉夫 R 解控（艾希R命中后0.5秒，解除魔法水晶箭的控制）
        5.5秒:   卡特琳娜 R 开始引导
        6.0秒:   盲僧 Q
        6.5秒:   盲僧 Q2
        7.0秒:   盲僧 R (打断卡特，技能终止不再恢复)
        7.5秒:   马尔扎哈 R (压制盲僧)
        """
        events = []
        events.append(HeroFactory.create_skill_event(ChampionID.ASHE, "W", 0))
        events.append(HeroFactory.create_skill_event(ChampionID.ASHE, "Q", 500))
        events.append(HeroFactory.create_skill_event(ChampionID.LUCIAN, "E", 3000))
        events.append(HeroFactory.create_skill_event(ChampionID.LUCIAN, "R", 3500))
        # 艾希R射出，飞行0.8秒，4.8秒命中奥拉夫
        events.append(HeroFactory.create_skill_event(ChampionID.ASHE, "R", 4000, target_id=ChampionID.OLAF))
        events.append(HeroFactory.create_skill_event(ChampionID.KATARINA, "E", 5000))
        # 奥拉夫R解控，在命中后0.5秒（5.3秒）
        events.append(HeroFactory.create_skill_event(ChampionID.OLAF, "R", 5300))
        events.append(HeroFactory.create_skill_event(ChampionID.KATARINA, "R", 5500))
        events.append(HeroFactory.create_skill_event(ChampionID.LEE_SIN, "Q", 6000, target_id=ChampionID.KATARINA))
        events.append(HeroFactory.create_skill_event(ChampionID.LEE_SIN, "Q2", 6500))
        # 盲僧R打断卡特
        events.append(HeroFactory.create_skill_event(ChampionID.LEE_SIN, "R", 7000, target_id=ChampionID.KATARINA))
        events.append(HeroFactory.create_skill_event(ChampionID.MALZAHAR, "R", 7500, target_id=ChampionID.LEE_SIN))
        # ========== 删除第二次艾希R ==========
        return [e for e in events if e is not None]

    @staticmethod
    def generate_lucian_stress_test(bullet_storms: int = 3) -> List[SkillEvent]:
        events = []
        for i in range(bullet_storms):
            events.append(HeroFactory.create_skill_event(ChampionID.LUCIAN, "R", i * 60000))
        return [e for e in events if e is not None]


# ============================================================================
# 第七部分：三结构对比实验运行器
# ============================================================================

class ThreeWayComparisonRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.ll_driver: Optional[SimulationDriver] = None
        self.pq_driver: Optional[SimulationDriver] = None
        self.bst_driver: Optional[SimulationDriver] = None
        self.ll_stats: Dict = {}
        self.pq_stats: Dict = {}
        self.bst_stats: Dict = {}

    def run_comparison(self, scenario_generator: Callable[[], List[SkillEvent]],
                       duration_ms: float = 13000) -> Dict:
        print("\n" + "=" * 80)
        print("开始三结构对比实验：链表 vs 优先队列(堆) vs 二叉搜索树(BST)")
        print("=" * 80)

        events = scenario_generator()
        print(f"场景事件数: {len(events)}")

        print("\n[1/3] 运行链表模式...")
        self.ll_driver = SimulationDriver(QueueType.LINKED_LIST, name="链表仿真", verbose=self.verbose)
        self.ll_driver.load_events(events)
        self.ll_driver.run(duration_ms)
        self.ll_stats = self.ll_driver.get_stats()
        Visualizer(self.ll_driver).export_json("teamfight_linked_list.json")

        print("\n[2/3] 运行优先队列模式...")
        self.pq_driver = SimulationDriver(QueueType.PRIORITY_QUEUE, name="优先队列仿真", verbose=self.verbose)
        self.pq_driver.load_events(events)
        self.pq_driver.run(duration_ms)
        self.pq_stats = self.pq_driver.get_stats()
        Visualizer(self.pq_driver).export_json("teamfight_priority_queue.json")

        print("\n[3/3] 运行二叉搜索树模式...")
        self.bst_driver = SimulationDriver(QueueType.BST, name="二叉搜索树仿真", verbose=self.verbose)
        self.bst_driver.load_events(events)
        self.bst_driver.run(duration_ms)
        self.bst_stats = self.bst_driver.get_stats()
        Visualizer(self.bst_driver).export_json("teamfight_bst.json")

        return self._generate_comparison_report()

    def _generate_comparison_report(self) -> Dict:
        ll_q = self.ll_stats.get("queue_stats", {})
        pq_q = self.pq_stats.get("queue_stats", {})
        bst_q = self.bst_stats.get("queue_stats", {})
        return {
            "linked_list": self.ll_stats, "priority_queue": self.pq_stats, "bst": self.bst_stats,
            "comparison": {
                "ll_push_us": ll_q.get("avg_push_us", 0),
                "pq_push_us": pq_q.get("avg_push_us", 0),
                "bst_push_us": bst_q.get("avg_push_us", 0),
                "pq_push_speedup": ll_q.get("avg_push_us", 0) / max(pq_q.get("avg_push_us", 0.001), 0.001),
                "bst_push_speedup": ll_q.get("avg_push_us", 0) / max(bst_q.get("avg_push_us", 0.001), 0.001),
            }
        }

    def print_comparison_table(self) -> None:
        if not self.ll_stats or not self.pq_stats or not self.bst_stats:
            print("请先运行 run_comparison()")
            return
        comp = self._generate_comparison_report()["comparison"]
        print("\n" + "=" * 80)
        print("三结构性能对比报告：链表 vs 优先队列(堆) vs 二叉搜索树(BST)")
        print("=" * 80)
        print(f"{'指标':<25} {'链表':<15} {'优先队列':<15} {'BST':<15}")
        print("-" * 80)
        print(f"{'平均施放耗时 (微秒)':<25} {comp['ll_push_us']:<15.3f} {comp['pq_push_us']:<15.3f} {comp['bst_push_us']:<15.3f}")
        print("-" * 80)
        print(f"{'施放提升倍数 (vs 链表)':<25} {'1.0x (基线)':<15} {comp['pq_push_speedup']:<15.2f}x {comp['bst_push_speedup']:<15.2f}x")
        print("=" * 80)
        print("\n📊 数据结构选型建议:")
        print("   • 链表：实现简单，适合事件量小、无优先级需求的场景")
        print("   • 优先队列(堆)：取最高优先级O(1)，适合LOL团战 ⭐推荐")
        print("   • BST：删除O(log n)，适合打断频繁的场景")


# ============================================================================
# 第八部分：可视化导出器
# ============================================================================

class Visualizer:
    def __init__(self, driver: SimulationDriver):
        self.driver = driver

    def export_json(self, path: str) -> None:
        data = {
            "config": {"name": self.driver.name, "queue_type": self.driver.queue_type.value,
                       "duration": self.driver.current_time},
            "stats": self.driver.get_stats(),
            "timeline": self.driver.get_timeline_data()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[可视化] 数据已导出到 {path}")

    def print_summary(self) -> None:
        stats = self.driver.get_stats()
        metrics = stats["metrics"]
        queue_stats = stats["queue_stats"]
        pool_stats = stats["pool_stats"]
        print("\n" + "=" * 60)
        print(f"仿真报告 - {self.driver.name} ({self.driver.queue_type.value})")
        print("=" * 60)
        print(f"总事件数: {stats['total_events']}")
        print(f"仿真时长: {format_game_time(stats['simulation_duration'])}")
        print(f"施放次数: {metrics['total_push']}")
        print(f"打断次数: {metrics['total_interrupt']}")
        print(f"解控次数: {metrics['total_cleanse']}")
        print(f"子弹发射数: {metrics['total_bullet_acquire']}")
        print(f"平均施放耗时: {queue_stats['avg_push_us']:.3f} 微秒")
        print("=" * 60)
        if pool_stats:
            print("\n📊 环形缓冲区统计:")
            print(f"  对象复用次数: {pool_stats['acquire_count']}")
            print(f"  复用率: {pool_stats['reuse_ratio']:.2%}")


# ============================================================================
# 第九部分：主程序入口
# ============================================================================

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║         🎮 英雄联盟 · 数据结构模拟器 · 修正版 🎮                           ║
║                                                                          ║
║         特色场景：艾希R飞行0.8秒命中奥拉夫（眩晕2.5秒）                      ║
║                   → 0.5秒后奥拉夫开R解控（解除魔法水晶箭）                   ║
║                   卡特R引导 → 盲僧R打断（技能终止，不再恢复）                ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()

    print("\n请选择运行模式：")
    print("=" * 60)
    print("1. 链表模式 - 展示场景")
    print("2. 优先队列模式 - 展示场景")
    print("3. BST模式 - 展示场景")
    print("4. 三结构完整对比实验 (静默模式) ⭐生成所有对比数据")
    print("5. 🆕 完整展示场景 - 艾希R命中奥拉夫 → 0.5秒后解控 ⭐推荐")
    print("=" * 60)

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == "1":
        driver = SimulationDriver(QueueType.LINKED_LIST, name="链表展示", verbose=True)
        events = ScenarioGenerator.generate_showcase_scene()
        driver.load_events(events)
        driver.run(13000)
        Visualizer(driver).export_json("teamfight_linked_list.json")

    elif choice == "2":
        driver = SimulationDriver(QueueType.PRIORITY_QUEUE, name="优先队列展示", verbose=True)
        events = ScenarioGenerator.generate_showcase_scene()
        driver.load_events(events)
        driver.run(13000)
        Visualizer(driver).export_json("teamfight_priority_queue.json")

    elif choice == "3":
        driver = SimulationDriver(QueueType.BST, name="BST展示", verbose=True)
        events = ScenarioGenerator.generate_showcase_scene()
        driver.load_events(events)
        driver.run(13000)
        Visualizer(driver).export_json("teamfight_bst.json")

    elif choice == "4":
        print("\n" + "=" * 70)
        print("🎮 运行三结构完整对比实验")
        print("   使用修正后的展示场景")
        print("=" * 70)
        runner = ThreeWayComparisonRunner(verbose=False)
        runner.run_comparison(lambda: ScenarioGenerator.generate_showcase_scene(), duration_ms=13000)
        runner.print_comparison_table()
        print("\n✅ 三结构对比实验完成！")
        print("\n📁 生成的文件：")
        print("  ✅ teamfight_linked_list.json")
        print("  ✅ teamfight_priority_queue.json")
        print("  ✅ teamfight_bst.json")

    elif choice == "5":
        print("\n" + "=" * 70)
        print("🎮 运行完整展示场景")
        print("   艾希R飞行0.8秒命中奥拉夫 → 0.5秒后奥拉夫开R解控")
        print("   卡特R引导 → 盲僧R打断（技能终止）")
        print("=" * 70)
        driver = SimulationDriver(QueueType.PRIORITY_QUEUE, name="完整展示场景", verbose=True)
        events = ScenarioGenerator.generate_showcase_scene()
        driver.load_events(events)
        driver.run(13000)
        viz = Visualizer(driver)
        viz.print_summary()
        viz.export_json("showcase_full.json")
        print("\n✅ 完整展示场景运行完成！")
        print("\n📌 场景亮点：")
        print("   • 4.0秒：艾希射出魔法水晶箭(R)")
        print("   • 4.8秒：魔法水晶箭命中奥拉夫，眩晕2.5秒！")
        print("   • 5.3秒：奥拉夫开启诸神黄昏(R)，解除魔法水晶箭的控制并免疫控制")
        print("   • 5.5秒：卡特琳娜开始引导死亡莲华")
        print("   • 7.0秒：盲僧R打断卡特琳娜，技能终止不再恢复")

    else:
        print("无效选项")


if __name__ == "__main__":
    main()