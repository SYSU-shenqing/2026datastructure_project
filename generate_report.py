"""
Queue of Legends - HTML可视化报告生成器
不需要安装任何第三方库，纯Python标准库
"""

import json
import os
from html import escape
from string import Template


def load_data(json_path: str) -> dict:
    """加载JSON数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_html_report(data: dict, output_path: str = "report.html"):
    """生成完整的HTML可视化报告"""

    timeline = data['timeline']
    stats = data['stats']
    metrics = stats['metrics']
    pool_stats = stats['pool_stats']
    queue_stats = stats['queue_stats']

    # 收集英雄列表
    heroes = []
    hero_skills = {}
    for event in timeline:
        hero = event['champion_name']
        if hero and hero not in heroes:
            heroes.append(hero)
            hero_skills[hero] = []

    # 为每个英雄收集技能
    for event in timeline:
        hero = event['champion_name']
        if hero and event['event_type'] == '开始执行':
            skill_name = event['skill_name'].replace(hero + '_', '')
            hero_skills[hero].append({
                'skill': skill_name,
                'start': event['time'],
                'duration': 0,
                'priority': event['priority']
            })
        elif hero and event['event_type'] in ('执行结束', '打断'):
            for skill in hero_skills[hero]:
                if skill['skill'] in event['skill_name'] and skill['duration'] == 0:
                    skill['duration'] = event['time'] - skill['start']
                    skill['interrupted'] = (event['event_type'] == '打断')
                    break

    # 生成时间轴表格HTML
    timeline_rows = []
    icons = {'施放': '📥', '开始执行': '⚡', '执行结束': '✅', '打断': '💥', '解控': '🧹'}
    for event in timeline:
        hero = event['champion_name'] or '-'
        event_type = event['event_type']
        icon = icons.get(event_type, '•')
        skill = event['skill_name'].replace(hero + '_', '') if hero != '-' else event['skill_name']
        priority = event['priority']
        time_str = f"{event['time']:.0f}"
        timeline_rows.append(f"""
        <tr>
            <td>{time_str}ms</td>
            <td>{hero}</td>
            <td>{icon} {event_type}</td>
            <td>{skill}</td>
            <td><span class="priority priority-{priority}">{priority}</span></td>
        </tr>
        """)

    # 生成甘特图数据（用于SVG绘制）
    max_time = data['config']['duration']
    gantt_bars = []
    colors = {'normal': '#2ecc71', 'interrupted': '#e74c3c'}

    for hero in heroes:
        y_offset = heroes.index(hero) * 50 + 30
        for skill in hero_skills[hero]:
            if skill['duration'] > 0:
                start_percent = (skill['start'] / max_time) * 100
                width_percent = (skill['duration'] / max_time) * 100
                color = colors['interrupted'] if skill.get('interrupted') else colors['normal']
                gantt_bars.append(f"""
                <div class="gantt-bar" style="
                    left: {start_percent}%;
                    width: {width_percent}%;
                    top: {y_offset}px;
                    background: {color};
                " title="{hero} - {skill['skill']} ({skill['duration']:.0f}ms)">
                    {skill['skill']}
                </div>
                """)

    # 生成英雄统计
    hero_stats_html = ""
    for hero in heroes:
        cast_count = sum(1 for e in timeline if e['champion_name'] == hero and e['event_type'] == '施放')
        interrupt_count = sum(1 for e in timeline if e['champion_name'] == hero and e['event_type'] == '打断')
        cleanse_count = sum(1 for e in timeline if e['champion_name'] == hero and e['event_type'] == '解控')
        hero_stats_html += f"""
        <div class="hero-stat-card">
            <div class="hero-name">{hero}</div>
            <div class="stat-row"><span>📥 施放</span><span>{cast_count}</span></div>
            <div class="stat-row"><span>💥 打断</span><span>{interrupt_count}</span></div>
            <div class="stat-row"><span>🧹 解控</span><span>{cleanse_count}</span></div>
        </div>
        """

    # 生成环形缓冲区统计卡片
    bullet_html = f"""
    <div class="stat-card">
        <h3>🔄 环形缓冲区统计</h3>
        <div class="stat-row"><span>对象池容量</span><span>{pool_stats['capacity']}</span></div>
        <div class="stat-row"><span>对象复用次数</span><span>{pool_stats['acquire_count']}</span></div>
        <div class="stat-row"><span>避免的内存分配</span><span>{pool_stats['naive_allocations']}次</span></div>
        <div class="stat-row"><span>避免的GC事件</span><span>{pool_stats['gc_events_saved']}次</span></div>
        <div class="stat-row highlight"><span>复用率</span><span>{pool_stats['reuse_ratio']:.1%}</span></div>
    </div>
    """

    # 生成性能指标卡片
    perf_html = f"""
    <div class="stat-card">
        <h3>⚡ 性能指标</h3>
        <div class="stat-row"><span>总施放次数</span><span>{metrics['total_push']}</span></div>
        <div class="stat-row"><span>总执行次数</span><span>{metrics['total_pop']}</span></div>
        <div class="stat-row"><span>打断次数</span><span>{metrics['total_interrupt']}</span></div>
        <div class="stat-row"><span>解控次数</span><span>{metrics['total_cleanse']}</span></div>
        <div class="stat-row"><span>最大队列深度</span><span>{metrics['max_queue_depth']}</span></div>
        <div class="stat-row"><span>平均PUSH耗时</span><span>{queue_stats['avg_push_us']:.2f}μs</span></div>
        <div class="stat-row"><span>平均POP耗时</span><span>{queue_stats['avg_pop_us']:.2f}μs</span></div>
    </div>
    """

    # 完整的HTML模板
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Queue of Legends - 仿真报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #1a1f2e 100%);
            color: #e6edf3;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #f39c12, #e74c3c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .subtitle {{
            text-align: center;
            color: #8b949e;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: rgba(22, 27, 34, 0.9);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #30363d;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}

        .stat-card h3 {{
            color: #f39c12;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 1px solid #30363d;
            padding-bottom: 10px;
        }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
        }}

        .stat-row:last-child {{
            border-bottom: none;
        }}

        .stat-row.highlight {{
            color: #2ecc71;
            font-weight: bold;
        }}

        .hero-stats-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }}

        .hero-stat-card {{
            background: rgba(22, 27, 34, 0.9);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid #30363d;
        }}

        .hero-stat-card .hero-name {{
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #58a6ff;
        }}

        .hero-stat-card .stat-row {{
            justify-content: space-around;
        }}

        .gantt-section {{
            background: rgba(22, 27, 34, 0.9);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
        }}

        .gantt-section h2 {{
            color: #f39c12;
            margin-bottom: 15px;
        }}

        .gantt-container {{
            position: relative;
            min-height: 300px;
            margin: 20px 0;
            padding-left: 100px;
        }}

        .gantt-labels {{
            position: absolute;
            left: 0;
            top: 0;
            width: 90px;
        }}

        .gantt-label {{
            height: 50px;
            line-height: 50px;
            font-weight: bold;
            color: #58a6ff;
        }}

        .gantt-area {{
            position: relative;
            height: 300px;
            background: rgba(13, 17, 23, 0.5);
            border-radius: 8px;
            border-left: 2px solid #30363d;
        }}

        .gantt-bar {{
            position: absolute;
            height: 30px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            color: white;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            padding: 0 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .gantt-bar:hover {{
            transform: scaleY(1.1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 10;
        }}

        .gantt-timeline {{
            display: flex;
            margin-top: 10px;
            padding-left: 100px;
        }}

        .gantt-timeline span {{
            flex: 1;
            text-align: center;
            color: #8b949e;
            font-size: 12px;
        }}

        .priority-pyramid {{
            background: rgba(22, 27, 34, 0.9);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
        }}

        .pyramid-levels {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            margin: 20px 0;
        }}

        .pyramid-level {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            padding: 12px 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .timeline-table-section {{
            background: rgba(22, 27, 34, 0.9);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #30363d;
            overflow-x: auto;
        }}

        .timeline-table-section h2 {{
            color: #f39c12;
            margin-bottom: 15px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th {{
            background: #21262d;
            color: #f39c12;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #30363d;
        }}

        tr:hover {{
            background: rgba(56, 139, 253, 0.1);
        }}

        .priority {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
        }}

        .priority-100 {{ background: #e74c3c; color: white; }}
        .priority-90 {{ background: #f39c12; color: white; }}
        .priority-20 {{ background: #3498db; color: white; }}
        .priority-15 {{ background: #2ecc71; color: white; }}
        .priority-10 {{ background: #9b59b6; color: white; }}
        .priority-5 {{ background: #1abc9c; color: white; }}
        .priority-0 {{ background: #95a5a6; color: white; }}

        .legend {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #8b949e;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Queue of Legends</h1>
        <div class="subtitle">数据结构性能仿真报告 · 优先队列模式 · {data['config']['duration'] / 1000:.1f}秒团战</div>

        <!-- 统计卡片 -->
        <div class="stats-grid">
            {perf_html}
            {bullet_html}
            <div class="stat-card">
                <h3>📊 队列统计</h3>
                <div class="stat-row"><span>队列类型</span><span>{data['config']['queue_type']}</span></div>
                <div class="stat-row"><span>总事件数</span><span>{data['stats']['total_events']}</span></div>
                <div class="stat-row"><span>PUSH次数</span><span>{queue_stats['push_count']}</span></div>
                <div class="stat-row"><span>POP次数</span><span>{queue_stats['pop_count']}</span></div>
                <div class="stat-row"><span>REMOVE次数</span><span>{queue_stats['remove_count']}</span></div>
            </div>
        </div>

        <!-- 英雄统计 -->
        <div class="hero-stats-grid">
            {hero_stats_html}
        </div>

        <!-- 优先级金字塔 -->
        <div class="priority-pyramid">
            <h2>⚡ 技能优先级金字塔</h2>
            <div class="pyramid-levels">
                <div class="pyramid-level" style="background: #e74c3c; width: 100%;">100 · 解控 · 奥拉夫 R (诸神黄昏)</div>
                <div class="pyramid-level" style="background: #f39c12; width: 90%;">90 · 控制 · 马尔扎哈 R / 盲僧 R</div>
                <div class="pyramid-level" style="background: #3498db; width: 70%;">20 · 瞬发 · 卡特琳娜 E</div>
                <div class="pyramid-level" style="background: #2ecc71; width: 50%;">15 · 弹道 · 卢锡安 R (圣枪洗礼)</div>
                <div class="pyramid-level" style="background: #9b59b6; width: 35%;">10 · 引导 · 卡特琳娜 R (死亡莲华)</div>
                <div class="pyramid-level" style="background: #95a5a6; width: 20%;">0 · 普通 · 艾希 W (万箭齐发)</div>
            </div>
        </div>

        <!-- 甘特图 -->
        <div class="gantt-section">
            <h2>📅 技能执行时间轴</h2>
            <div class="legend">
                <div class="legend-item"><span class="legend-color" style="background: #2ecc71;"></span> 正常完成</div>
                <div class="legend-item"><span class="legend-color" style="background: #e74c3c;"></span> 被打断</div>
                <div class="legend-item"><span class="legend-item">💥 关键打断时刻</span></div>
            </div>
            <div class="gantt-container">
                <div class="gantt-labels">
                    {''.join(f'<div class="gantt-label">{h}</div>' for h in heroes)}
                </div>
                <div class="gantt-area" style="height: {len(heroes) * 50}px;">
                    {''.join(gantt_bars)}
                </div>
            </div>
            <div class="gantt-timeline">
                <span>0s</span><span>2s</span><span>4s</span><span>6s</span><span>8s</span><span>10s</span><span>12s</span><span>13s</span>
            </div>
            <p style="margin-top: 20px; color: #8b949e;">
                <strong>🔑 关键时刻：</strong> 
                4.0s 艾希R命中奥拉夫(眩晕) → 
                7.0s 盲僧R打断卡特R → 
                8.0s 奥拉夫R解控(优先级100)
            </p>
        </div>

        <!-- 时间轴表格 -->
        <div class="timeline-table-section">
            <h2>📋 完整时间轴</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>英雄</th>
                        <th>事件</th>
                        <th>技能</th>
                        <th>优先级</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(timeline_rows)}
                </tbody>
            </table>
        </div>

        <div class="footer">
            Queue of Legends · 数据结构性能模拟器 · 三结构对比版<br>
            控制链：引导(10) < 控制(90) < 解控(100)
        </div>
    </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"✅ HTML报告已生成: {output_path}")
    print(f"   用浏览器打开即可查看可视化报告！")


def generate_text_report(data: dict, output_path: str = "report.txt"):
    """生成纯文本报告"""
    timeline = data['timeline']
    stats = data['stats']
    metrics = stats['metrics']
    pool_stats = stats['pool_stats']
    queue_stats = stats['queue_stats']

    lines = []
    lines.append("=" * 70)
    lines.append("Queue of Legends - 仿真报告")
    lines.append("=" * 70)
    lines.append(f"\n仿真名称: {data['config']['name']}")
    lines.append(f"队列类型: {data['config']['queue_type']}")
    lines.append(f"仿真时长: {data['config']['duration'] / 1000:.1f}秒")

    lines.append("\n" + "-" * 50)
    lines.append("📊 性能指标")
    lines.append("-" * 50)
    lines.append(f"  总施放次数: {metrics['total_push']}")
    lines.append(f"  总执行次数: {metrics['total_pop']}")
    lines.append(f"  打断次数: {metrics['total_interrupt']}")
    lines.append(f"  解控次数: {metrics['total_cleanse']}")
    lines.append(f"  子弹发射数: {metrics['total_bullet_acquire']}")
    lines.append(f"  最大队列深度: {metrics['max_queue_depth']}")
    lines.append(f"  平均PUSH耗时: {queue_stats['avg_push_us']:.3f}μs")
    lines.append(f"  平均POP耗时: {queue_stats['avg_pop_us']:.3f}μs")

    lines.append("\n" + "-" * 50)
    lines.append("🔄 环形缓冲区统计")
    lines.append("-" * 50)
    lines.append(f"  对象复用次数: {pool_stats['acquire_count']}")
    lines.append(f"  避免的内存分配: {pool_stats['naive_allocations']}次")
    lines.append(f"  避免的GC事件: {pool_stats['gc_events_saved']}次")
    lines.append(f"  复用率: {pool_stats['reuse_ratio']:.1%}")

    lines.append("\n" + "-" * 50)
    lines.append("📅 时间轴事件")
    lines.append("-" * 50)

    icons = {'施放': '📥', '开始执行': '⚡', '执行结束': '✅', '打断': '💥', '解控': '🧹'}
    for event in timeline:
        time_str = f"{event['time']:7.1f}ms"
        hero = event['champion_name'] or '-'
        icon = icons.get(event['event_type'], '•')
        event_type = event['event_type']
        skill = event['skill_name'].replace(hero + '_', '') if hero != '-' else event['skill_name']
        priority = event['priority']
        lines.append(f"  {time_str}  {icon} {hero:<10} {event_type:<8} {skill:<15} 优先级:{priority}")

    lines.append("\n" + "=" * 70)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✅ 文本报告已生成: {output_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("Queue of Legends - 可视化报告生成器")
    print("=" * 60)

    # 查找JSON文件
    json_files = [f for f in os.listdir('.') if f.endswith('.json') and 'showcase' in f.lower()]

    if not json_files:
        json_path = input("请输入JSON文件路径: ").strip()
    else:
        print("\n找到以下JSON文件:")
        for i, f in enumerate(json_files):
            print(f"  {i + 1}. {f}")
        choice = input(f"选择文件 (1-{len(json_files)}) 或输入路径: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(json_files):
            json_path = json_files[int(choice) - 1]
        else:
            json_path = choice

    if not os.path.exists(json_path):
        print(f"❌ 文件不存在: {json_path}")
        return

    # 加载数据
    print(f"\n📂 加载数据: {json_path}")
    data = load_data(json_path)

    # 生成报告
    print("\n🎨 生成可视化报告...")

    # HTML报告
    generate_html_report(data, "queue_of_legends_report.html")

    # 文本报告
    generate_text_report(data, "queue_of_legends_report.txt")

    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)
    print("\n生成的文件:")
    print("  📄 queue_of_legends_report.html - 用浏览器打开查看可视化报告")
    print("  📄 queue_of_legends_report.txt - 纯文本报告")
    print("\n提示: 双击HTML文件即可在浏览器中查看交互式图表！")


if __name__ == "__main__":
    main()