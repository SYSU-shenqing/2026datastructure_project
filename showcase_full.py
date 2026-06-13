"""
Queue of Legends - 数据可视化脚本（报告版）
读取JSON文件并生成报告所需的图表
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_data(json_path: str) -> dict:
    """加载JSON数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_load_data(json_path: str) -> dict:
    """安全加载JSON数据，文件不存在时返回None"""
    if os.path.exists(json_path):
        return load_data(json_path)
    else:
        print(f"⚠️ 文件不存在: {json_path}")
        return None


def plot_performance_comparison(ll_data: dict, pq_data: dict, bst_data: dict,
                                 save_path: str = "performance_comparison.png"):
    """
    图1：三种数据结构平均耗时对比柱状图
    """
    # 提取数据
    ll_push = ll_data['stats']['queue_stats']['avg_push_us'] if ll_data else 0
    pq_push = pq_data['stats']['queue_stats']['avg_push_us'] if pq_data else 0
    bst_push = bst_data['stats']['queue_stats']['avg_push_us'] if bst_data else 0

    ll_pop = ll_data['stats']['queue_stats']['avg_pop_us'] if ll_data else 0
    pq_pop = pq_data['stats']['queue_stats']['avg_pop_us'] if pq_data else 0
    bst_pop = bst_data['stats']['queue_stats']['avg_pop_us'] if bst_data else 0

    # 计算加速比
    pq_speedup = ll_push / pq_push if pq_push > 0 else 0
    bst_speedup = ll_push / bst_push if bst_push > 0 else 0

    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))

    # 数据结构名称
    structures = ['链表\n(LinkedList)', '优先队列\n(堆)', '二叉搜索树\n(BST)']

    # 柱状图参数
    x = np.arange(len(structures))
    width = 0.35

    # 绘制PUSH耗时柱状图
    push_values = [ll_push, pq_push, bst_push]
    bars1 = ax.bar(x - width/2, push_values, width,
                   label='平均入队耗时 (PUSH)',
                   color=['#95a5a6', '#2ecc71', '#9b59b6'],
                   alpha=0.85, edgecolor='white', linewidth=1.5)

    # 绘制POP耗时柱状图
    pop_values = [ll_pop, pq_pop, bst_pop]
    bars2 = ax.bar(x + width/2, pop_values, width,
                   label='平均出队耗时 (POP)',
                   color=['#bdc3c7', '#27ae60', '#8e44ad'],
                   alpha=0.85, edgecolor='white', linewidth=1.5)

    # 在柱子上标注数值
    for bar, val in zip(bars1, push_values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{val:.1f}μs', ha='center', va='bottom', fontsize=11, fontweight='bold')

    for bar, val in zip(bars2, pop_values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{val:.1f}μs', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 添加加速比标注
    if pq_speedup > 0:
        ax.annotate(f'加速 {pq_speedup:.1f}x',
                    xy=(1, pq_push), xytext=(1, pq_push + max(push_values)*0.3),
                    fontsize=10, color='#e74c3c', fontweight='bold',
                    ha='center',
                    arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.5))

    # 设置坐标轴
    ax.set_xticks(x)
    ax.set_xticklabels(structures, fontsize=12)
    ax.set_ylabel('耗时 (微秒 μs)', fontsize=13)
    ax.set_title('三种数据结构核心操作耗时对比', fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # 添加说明文字
    textstr = f'测试场景：英雄联盟团战技能调度\n单位：微秒 (μs)\n基线：链表'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.98, 0.97, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.show()
    print(f"✅ 耗时对比柱状图已保存: {save_path}")

    # 返回数据供报告使用
    return {
        'll_push': ll_push, 'pq_push': pq_push, 'bst_push': bst_push,
        'll_pop': ll_pop, 'pq_pop': pq_pop, 'bst_pop': bst_pop,
        'pq_speedup': pq_speedup, 'bst_speedup': bst_speedup
    }


def plot_queue_depth_curve(data: dict, save_path: str = "queue_depth_curve.png"):
    """
    图2：队列深度随时间变化曲线图
    """
    if not data:
        print("⚠️ 无数据，跳过队列深度图")
        return None

    timeline = data['timeline']

    # 提取队列深度数据
    times = []
    depths = []
    for event in timeline:
        if 'queue_depth' in event:
            times.append(event['time'])
            depths.append(event['queue_depth'])

    if not times:
        print("⚠️ 未找到队列深度数据")
        return None

    fig, ax = plt.subplots(figsize=(14, 5))

    # 绘制面积图 + 折线图
    ax.fill_between(times, depths, alpha=0.25, color='#3498db')
    ax.plot(times, depths, color='#3498db', linewidth=2.5, marker='o', markersize=3, markerfacecolor='#2980b9')

    # 标记峰值
    max_depth = max(depths)
    max_idx = depths.index(max_depth)
    max_time = times[max_idx]
    ax.scatter(max_time, max_depth, color='#e74c3c', s=120, zorder=5, edgecolors='white', linewidth=2)
    ax.annotate(f'峰值: {max_depth}',
                xy=(max_time, max_depth),
                xytext=(max_time + 800, max_depth + 0.3),
                fontsize=11, color='#e74c3c', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.5, connectionstyle='arc3,rad=0.3'))

    # 标注关键时间点
    key_times = {
        4000: '艾希R射出',
        4800: '命中奥拉夫',
        5300: '奥拉夫解控',
        7000: '盲僧R打断'
    }
    for t, label in key_times.items():
        if t <= max(times):
            ax.axvline(x=t, color='#95a5a6', linestyle='--', alpha=0.4, linewidth=1)
            ax.text(t, max_depth * 1.05, label, rotation=90, va='bottom', ha='right',
                    fontsize=8, color='#7f8c8d')

    # 设置坐标轴
    ax.set_xlabel('仿真时间 (毫秒 ms)', fontsize=13)
    ax.set_ylabel('队列深度（待执行技能数）', fontsize=13)
    ax.set_title('技能队列深度随时间变化曲线', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlim(0, max(times) * 1.02)
    ax.set_ylim(0, max_depth * 1.3)
    ax.grid(alpha=0.3, linestyle='--')

    # 添加统计信息
    avg_depth = sum(depths) / len(depths) if depths else 0
    stats_text = f'最大队列深度: {max_depth}  |  平均队列深度: {avg_depth:.2f}'
    ax.text(0.5, -0.12, stats_text, transform=ax.transAxes, fontsize=10,
            ha='center', color='#555', style='italic')

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.show()
    print(f"✅ 队列深度曲线图已保存: {save_path}")

    return {
        'max_depth': max_depth,
        'avg_depth': avg_depth,
        'peak_time': max_time
    }


def plot_bullet_pool_comparison(data: dict, save_path: str = "bullet_pool_comparison.png"):
    """
    图3：环形缓冲区对象池统计图
    """
    if not data or 'pool_stats' not in data.get('stats', {}):
        print("⚠️ 无环形缓冲区数据")
        return None

    pool_stats = data['stats']['pool_stats']

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # ========== 左图：内存分配次数对比 ==========
    ax1 = axes[0]
    categories = ['环形缓冲区\n(对象池)', '普通方式\n(new/delete)']
    values = [1, pool_stats.get('naive_allocations', 0)]
    colors = ['#2ecc71', '#e74c3c']

    bars1 = ax1.bar(categories, values, color=colors, alpha=0.85, width=0.5, edgecolor='white', linewidth=1.5)
    ax1.set_ylabel('内存分配次数', fontsize=13)
    ax1.set_title('内存分配次数对比', fontsize=14, fontweight='bold')

    for bar, val in zip(bars1, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.03,
                 f'{val} 次', ha='center', va='bottom', fontsize=13, fontweight='bold')

    # 添加节省比例
    if values[1] > 0:
        saved_pct = (1 - 1/values[1]) * 100
        ax1.annotate(f'节省 {saved_pct:.1f}%',
                    xy=(0.5, 0.5), fontsize=18, color='#27ae60', fontweight='bold',
                    ha='center', va='center')

    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # ========== 右图：对象池详细统计 ==========
    ax2 = axes[1]
    stat_labels = ['对象池容量', '总申请次数', '总回收次数', '避免GC次数']
    stat_values = [
        pool_stats.get('capacity', 0),
        pool_stats.get('acquire_count', 0),
        pool_stats.get('release_count', 0),
        pool_stats.get('gc_events_saved', 0)
    ]
    colors2 = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']

    bars2 = ax2.barh(stat_labels, stat_values, color=colors2, alpha=0.85, edgecolor='white', linewidth=1.5)
    ax2.set_xlabel('次数', fontsize=13)
    ax2.set_title('环形缓冲区运行统计', fontsize=14, fontweight='bold')

    for bar, val in zip(bars2, stat_values):
        ax2.text(bar.get_width() + max(stat_values)*0.02, bar.get_y() + bar.get_height()/2,
                 str(val), va='center', fontsize=12, fontweight='bold')

    ax2.grid(axis='x', alpha=0.3, linestyle='--')

    # 总标题
    reuse_ratio = pool_stats.get('reuse_ratio', 0) * 100
    fig.suptitle(f'环形缓冲区（弹道对象池）性能统计\n'
                 f'对象复用率: {reuse_ratio:.1f}%  |  '
                 f'GC事件避免: {pool_stats.get("gc_events_saved", 0)} 次',
                 fontsize=13, y=1.03, color='#2c3e50')

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.show()
    print(f"✅ 环形缓冲区统计图已保存: {save_path}")

    return pool_stats


def generate_summary_report(perf_data: dict, queue_data: dict, pool_data: dict,
                            output_path: str = "data_summary.txt"):
    """
    生成数据汇总文本报告
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Queue of Legends - 实验数据汇总报告")
    lines.append("=" * 70)
    lines.append(f"生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 表1：三种数据结构耗时对比
    lines.append("-" * 50)
    lines.append("【表格1】三种数据结构核心操作耗时对比表")
    lines.append("-" * 50)
    if perf_data:
        lines.append(f"{'数据结构':<20} {'平均入队耗时(μs)':<18} {'平均出队耗时(μs)':<18} {'入队加速比':<12}")
        lines.append("-" * 70)
        lines.append(f"{'链表(LinkedList)':<20} {perf_data['ll_push']:<18.3f} {perf_data['ll_pop']:<18.3f} {'1.00 (基线)':<12}")
        lines.append(f"{'优先队列(堆)':<20} {perf_data['pq_push']:<18.3f} {perf_data['pq_pop']:<18.3f} {perf_data['pq_speedup']:<12.2f}x")
        lines.append(f"{'二叉搜索树(BST)':<20} {perf_data['bst_push']:<18.3f} {perf_data['bst_pop']:<18.3f} {perf_data['bst_speedup']:<12.2f}x")
    lines.append("")

    # 表2：理论复杂度（固定内容）
    lines.append("-" * 50)
    lines.append("【表格2】数据结构理论时间复杂度对照表")
    lines.append("-" * 50)
    lines.append(f"{'数据结构':<20} {'插入操作':<12} {'删除/取队首':<15} {'查找优先级':<12} {'适用场景':<20}")
    lines.append("-" * 80)
    lines.append(f"{'链表':<20} {'O(n)':<12} {'O(1)':<15} {'O(n)':<12} {'简单FIFO、无优先级':<20}")
    lines.append(f"{'优先队列(堆)':<20} {'O(log n)':<12} {'O(log n)':<15} {'O(1)':<12} {'动态优先级调度':<20}")
    lines.append(f"{'二叉搜索树(BST)':<20} {'O(log n)':<12} {'O(log n)':<15} {'O(log n)':<12} {'频繁增删、有序检索':<20}")
    lines.append("")

    # 表3：队列深度数据
    if queue_data:
        lines.append("-" * 50)
        lines.append("【队列深度分析】")
        lines.append("-" * 50)
        lines.append(f"  最大队列深度: {queue_data['max_depth']}")
        lines.append(f"  平均队列深度: {queue_data['avg_depth']:.2f}")
        lines.append(f"  峰值时间: {queue_data['peak_time']:.0f}ms")
        lines.append("")

    # 表4：环形缓冲区数据
    if pool_data:
        lines.append("-" * 50)
        lines.append("【表格5】环形缓冲区（弹道对象池）性能统计表")
        lines.append("-" * 50)
        lines.append(f"{'统计指标':<20} {'数值':<10}")
        lines.append("-" * 32)
        lines.append(f"{'缓冲区总容量':<20} {pool_data.get('capacity', 0):<10}")
        lines.append(f"{'对象总申请次数':<20} {pool_data.get('acquire_count', 0):<10}")
        lines.append(f"{'对象总回收次数':<20} {pool_data.get('release_count', 0):<10}")
        lines.append(f"{'对象复用率':<20} {pool_data.get('reuse_ratio', 0)*100:<10.1f}%")
        lines.append(f"{'避免GC触发次数':<20} {pool_data.get('gc_events_saved', 0):<10}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("报告生成完毕")
    lines.append("=" * 70)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✅ 数据汇总报告已保存: {output_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("Queue of Legends - 实验报告图表生成")
    print("=" * 60)

    # 加载三个对比数据文件
    print("\n📂 加载数据文件...")

    ll_data = safe_load_data("teamfight_linked_list.json")
    pq_data = safe_load_data("teamfight_priority_queue.json")
    bst_data = safe_load_data("teamfight_bst.json")
    showcase_data = safe_load_data("showcase_full.json")

    # 检查数据完整性
    if ll_data:
        print(f"  ✅ teamfight_linked_list.json")
    if pq_data:
        print(f"  ✅ teamfight_priority_queue.json")
    if bst_data:
        print(f"  ✅ teamfight_bst.json")
    if showcase_data:
        print(f"  ✅ showcase_full.json")

    print("\n🎨 生成报告图表...\n")

    # 图1：三种数据结构耗时对比柱状图
    perf_data = None
    if ll_data and pq_data and bst_data:
        perf_data = plot_performance_comparison(ll_data, pq_data, bst_data,
                                                  "performance_comparison.png")
    else:
        print("⚠️ 缺少对比数据，跳过耗时对比图")
        print("   请先运行 main.py 选项4 生成对比数据")

    # 图2：队列深度变化曲线图
    queue_data = None
    if showcase_data:
        queue_data = plot_queue_depth_curve(showcase_data, "queue_depth_curve.png")
    else:
        print("⚠️ 缺少展示数据，跳过队列深度图")
        print("   请先运行 main.py 选项5 生成展示数据")

    # 图3：环形缓冲区统计图
    pool_data = None
    if showcase_data:
        pool_data = plot_bullet_pool_comparison(showcase_data, "bullet_pool_comparison.png")

    # 生成数据汇总报告
    generate_summary_report(perf_data, queue_data, pool_data, "data_summary.txt")

    print("\n" + "=" * 60)
    print("✅ 所有图表生成完成！")
    print("=" * 60)
    print("\n📁 生成的文件：")
    print("  📊 performance_comparison.png  - 三种结构耗时对比柱状图")
    print("  📊 queue_depth_curve.png       - 队列深度变化曲线图")
    print("  📊 bullet_pool_comparison.png  - 环形缓冲区统计图")
    print("  📝 data_summary.txt            - 数据汇总文本报告")
    print("\n💡 提示：")
    print("  如果缺少对比数据文件，请先运行：")
    print("    python main.py → 选项4 (生成对比数据)")
    print("    python main.py → 选项5 (生成展示数据)")


if __name__ == "__main__":
    main()