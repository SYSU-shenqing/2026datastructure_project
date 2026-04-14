"""
Queue of Legends - 数据可视化脚本
读取JSON文件并生成海报所需的图表
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_data(json_path: str) -> dict:
    """加载JSON数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_gantt_chart(data: dict, save_path: str = "gantt_chart.png"):
    """
    绘制甘特图 - 展示技能执行时间轴
    """
    timeline = data['timeline']

    # 收集所有英雄
    heroes = {}
    for event in timeline:
        hero_name = event['champion_name']
        if hero_name and hero_name not in heroes:
            heroes[hero_name] = []

    hero_list = list(heroes.keys())
    hero_to_y = {h: i for i, h in enumerate(hero_list)}

    # 颜色映射
    event_colors = {
        '施放': '#3498db',  # 蓝色
        '开始执行': '#2ecc71',  # 绿色
        '执行结束': '#95a5a6',  # 灰色
        '打断': '#e74c3c',  # 红色
        '解控': '#f39c12',  # 橙色
    }

    fig, ax = plt.subplots(figsize=(16, len(hero_list) * 1.5 + 2))

    # 绘制事件
    skill_starts = {}
    for event in timeline:
        hero = event['champion_name']
        if not hero:
            continue

        y = hero_to_y[hero]
        time_val = event['time']
        event_type = event['event_type']
        skill_name = event['skill_name'].replace(hero + '_', '')

        color = event_colors.get(event_type, '#7f8c8d')

        if event_type == '开始执行':
            skill_starts[event['skill_name']] = (time_val, y, skill_name)
        elif event_type in ('执行结束', '打断'):
            if event['skill_name'] in skill_starts:
                start_time, start_y, skill = skill_starts[event['skill_name']]
                duration = time_val - start_time

                # 绘制技能条
                bar = Rectangle((start_time, y - 0.3), duration, 0.6,
                                facecolor=color, edgecolor='white', alpha=0.8)
                ax.add_patch(bar)

                # 添加技能标签
                if duration > 200:
                    ax.text(start_time + duration / 2, y, skill,
                            ha='center', va='center', fontsize=8, color='white', fontweight='bold')

                del skill_starts[event['skill_name']]

        elif event_type == '施放':
            ax.scatter(time_val, y, color=color, s=50, zorder=5, marker='s')

    # 标记关键事件
    key_events = [
        (4000, "艾希R命中奥拉夫\n(眩晕)"),
        (7004, "盲僧R打断\n卡特R"),
        (8007, "奥拉夫R\n解控"),
    ]
    for t, label in key_events:
        ax.axvline(x=t, color='#e74c3c', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(t, len(hero_list) - 0.5, label, rotation=90,
                va='top', ha='right', fontsize=8, color='#e74c3c')

    # 设置坐标轴
    ax.set_yticks(range(len(hero_list)))
    ax.set_yticklabels(hero_list, fontsize=11)
    ax.set_xlabel('时间 (毫秒)', fontsize=12)
    ax.set_title('Queue of Legends - 团战技能执行时间轴', fontsize=16, fontweight='bold')
    ax.set_xlim(0, 13000)
    ax.grid(axis='x', alpha=0.3)

    # 图例
    legend_elements = [mpatches.Patch(color=c, label=t) for t, c in event_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"甘特图已保存: {save_path}")


def plot_priority_pyramid(save_path: str = "priority_pyramid.png"):
    """
    绘制优先级金字塔 - 展示技能优先级层次
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    priorities = [
        (100, "解控", "奥拉夫 R\n诸神黄昏", "#e74c3c"),
        (90, "控制", "马尔扎哈 R\n盲僧 R", "#f39c12"),
        (20, "瞬发", "卡特琳娜 E\n闪现", "#3498db"),
        (15, "弹道", "卢锡安 R\n圣枪洗礼", "#2ecc71"),
        (10, "引导", "卡特琳娜 R\n死亡莲华", "#9b59b6"),
        (0, "普通", "艾希 W\n万箭齐发", "#95a5a6"),
    ]

    y_pos = 0
    for prio, name, examples, color in priorities:
        # 金字塔层
        width = prio + 10
        x = (110 - width) / 2
        rect = Rectangle((x, y_pos), width, 0.8,
                         facecolor=color, edgecolor='white', alpha=0.8)
        ax.add_patch(rect)

        # 标签
        ax.text(55, y_pos + 0.4, f"{name} ({prio})",
                ha='center', va='center', fontsize=12, fontweight='bold', color='white')
        ax.text(55, y_pos + 0.1, examples,
                ha='center', va='center', fontsize=9, color='white', alpha=0.9)

        y_pos += 1.2

    ax.set_xlim(0, 110)
    ax.set_ylim(0, y_pos)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title('技能优先级金字塔', fontsize=16, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"优先级金字塔已保存: {save_path}")


def plot_queue_depth(data: dict, save_path: str = "queue_depth.png"):
    """
    绘制队列深度变化曲线
    """
    timeline = data['timeline']

    times = []
    depths = []
    for event in timeline:
        if 'queue_depth' in event:
            times.append(event['time'])
            depths.append(event['queue_depth'])

    fig, ax = plt.subplots(figsize=(14, 4))

    ax.fill_between(times, depths, alpha=0.3, color='#3498db')
    ax.plot(times, depths, color='#3498db', linewidth=2)

    # 标记峰值
    max_depth = max(depths)
    max_idx = depths.index(max_depth)
    ax.scatter(times[max_idx], max_depth, color='#e74c3c', s=100, zorder=5)
    ax.annotate(f'峰值: {max_depth}',
                xy=(times[max_idx], max_depth),
                xytext=(times[max_idx] + 500, max_depth + 0.5),
                fontsize=10, color='#e74c3c',
                arrowprops=dict(arrowstyle='->', color='#e74c3c'))

    ax.set_xlabel('时间 (毫秒)', fontsize=12)
    ax.set_ylabel('队列深度', fontsize=12)
    ax.set_title('技能队列深度变化', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 13000)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"队列深度图已保存: {save_path}")


def plot_bullet_pool_stats(data: dict, save_path: str = "bullet_pool.png"):
    """
    绘制环形缓冲区统计图
    """
    pool_stats = data['stats']['pool_stats']

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左图：对象复用对比
    ax1 = axes[0]
    categories = ['环形缓冲区', '普通new/delete']
    values = [1, pool_stats['naive_allocations']]
    colors = ['#2ecc71', '#e74c3c']

    bars = ax1.bar(categories, values, color=colors, alpha=0.8, width=0.5)
    ax1.set_ylabel('内存分配次数', fontsize=12)
    ax1.set_title('内存分配次数对比', fontsize=14, fontweight='bold')

    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f'{val}次', ha='center', va='bottom', fontsize=12, fontweight='bold')

    # 右图：GC事件对比
    ax2 = axes[1]
    gc_values = [0, pool_stats['gc_events_saved']]
    bars = ax2.bar(categories, gc_values, color=colors, alpha=0.8, width=0.5)
    ax2.set_ylabel('GC触发次数', fontsize=12)
    ax2.set_title('GC事件对比', fontsize=14, fontweight='bold')

    for bar, val in zip(bars, gc_values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f'{val}次', ha='center', va='bottom', fontsize=12, fontweight='bold')

    # 添加统计信息
    fig.suptitle(f'环形缓冲区性能统计\n复用率: {pool_stats["reuse_ratio"]:.1%} | '
                 f'对象复用: {pool_stats["acquire_count"]}次',
                 fontsize=12, y=1.02)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"子弹池统计图已保存: {save_path}")


def plot_hero_stats(data: dict, save_path: str = "hero_stats.png"):
    """
    绘制英雄技能统计柱状图
    """
    timeline = data['timeline']

    # 统计每个英雄的技能使用情况
    hero_skills = {}
    for event in timeline:
        hero = event['champion_name']
        if not hero:
            continue

        if hero not in hero_skills:
            hero_skills[hero] = {'施放': 0, '打断': 0, '被控': 0, '解控': 0}

        if event['event_type'] == '施放':
            hero_skills[hero]['施放'] += 1
        elif event['event_type'] == '打断':
            hero_skills[hero]['打断'] += 1
        elif event['event_type'] == '解控':
            hero_skills[hero]['解控'] += 1

    heroes = list(hero_skills.keys())
    x = np.arange(len(heroes))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    # 施放次数
    cast_values = [hero_skills[h]['施放'] for h in heroes]
    bars1 = ax.bar(x - width, cast_values, width, label='施放技能', color='#3498db', alpha=0.8)

    # 打断次数
    interrupt_values = [hero_skills[h]['打断'] for h in heroes]
    bars2 = ax.bar(x, interrupt_values, width, label='打断', color='#e74c3c', alpha=0.8)

    # 解控次数
    cleanse_values = [hero_skills[h]['解控'] for h in heroes]
    bars3 = ax.bar(x + width, cleanse_values, width, label='解控', color='#f39c12', alpha=0.8)

    ax.set_xlabel('英雄', fontsize=12)
    ax.set_ylabel('次数', fontsize=12)
    ax.set_title('各英雄技能使用统计', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(heroes, fontsize=11)
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"英雄统计图已保存: {save_path}")


def generate_timeline_table(data: dict) -> str:
    """
    生成时间轴表格（Markdown格式）
    """
    timeline = data['timeline']

    lines = []
    lines.append("| 时间 | 英雄 | 事件类型 | 技能 | 优先级 |")
    lines.append("|------|------|---------|------|--------|")

    for event in timeline:
        time_str = f"{event['time']:.0f}ms"
        hero = event['champion_name']
        event_type = event['event_type']
        skill = event['skill_name'].replace(hero + '_', '') if hero else event['skill_name']
        priority = event['priority']

        # 图标映射
        icons = {'施放': '📥', '开始执行': '⚡', '执行结束': '✅', '打断': '💥', '解控': '🧹'}
        icon = icons.get(event_type, '•')

        lines.append(f"| {time_str} | {hero} | {icon} {event_type} | {skill} | {priority} |")

    return '\n'.join(lines)


def main():
    """主函数"""
    json_path = "showcase_full.json"  # 替换为你的JSON文件路径

    print("=" * 60)
    print("Queue of Legends - 数据可视化")
    print("=" * 60)

    # 加载数据
    data = load_data(json_path)

    # 打印摘要
    metrics = data['stats']['metrics']
    print(f"\n📊 仿真摘要:")
    print(f"  总事件数: {data['stats']['total_events']}")
    print(f"  施放次数: {metrics['total_push']}")
    print(f"  打断次数: {metrics['total_interrupt']}")
    print(f"  解控次数: {metrics['total_cleanse']}")
    print(f"  子弹发射: {metrics['total_bullet_acquire']}")

    # 生成图表
    print("\n🎨 生成图表...")

    plot_gantt_chart(data, "gantt_chart.png")
    plot_priority_pyramid("priority_pyramid.png")
    plot_queue_depth(data, "queue_depth.png")
    plot_bullet_pool_stats(data, "bullet_pool.png")
    plot_hero_stats(data, "hero_stats.png")

    # 生成时间轴表格
    table = generate_timeline_table(data)
    with open("timeline_table.md", "w", encoding="utf-8") as f:
        f.write("# Queue of Legends - 时间轴事件\n\n")
        f.write(table)
    print("\n📝 时间轴表格已保存: timeline_table.md")

    print("\n✅ 所有图表生成完成！")


if __name__ == "__main__":
    main()