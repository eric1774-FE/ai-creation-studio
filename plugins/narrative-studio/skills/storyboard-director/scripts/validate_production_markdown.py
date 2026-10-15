#!/usr/bin/env python3
"""Validate the canonical director Markdown and an optional prompt matrix.

Only explicit declarations are checked; missing evidence fails closed. This is
not a natural-language interpreter or validation of rendered animation.
"""
import argparse
from decimal import Decimal as D
from pathlib import Path
import re

NUM = r"\d+(?:\.\d+)?"
SPAN = rf"t\s*=\s*({NUM})s?\s*[–—~-]\s*({NUM})s"
PALETTE = "Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index"
NEGATIVE = "2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs"
TEXT = re.compile(
    rf"触发点:\s*t=({NUM})s｜内容:\s*([^｜]+)｜视觉动效:\s*"
    rf"弹出保持\s*({NUM})s，t=({NUM})s\s*动效收拢，t=({NUM})s\s*消失"
)


def table_rows(markdown, heading, columns, errors):
    lines = markdown.splitlines()
    starts = [i for i, line in enumerate(lines)
              if line.startswith("|") and line.strip("| ").split("|")[0].strip() == heading]
    if len(starts) != 1:
        errors.append(f"INPUT_FORMAT: 应有一张 {heading} {columns} 列表格")
        return []
    start = starts[0]
    rows = []
    for i, line in enumerate(lines[start:], start + 1):
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != columns:
            errors.append(f"INPUT_FORMAT: 第 {i} 行应为 {columns} 列，实际 {len(cells)}")
        elif i > start + 2:
            rows.append(cells)
    if not rows:
        errors.append("INPUT_FORMAT: 表格无数据行")
    return rows


def clock(value):
    parts = value.split(":")
    return D(parts[0]) * 60 + D(parts[1])


def validate_director(markdown):
    errors = []
    rows = table_rows(markdown, "镜头号", 8, errors)
    roles_match = re.search(r"^- 出场角色[：:]\s*(.+)$", markdown, re.M)
    climax_match = re.search(r"^- 高潮节拍[：:]\s*Beat\s+(\d+)\s*$", markdown, re.M)
    spec = re.search(rf"总镜头数[：:]\s*(\d+)\s*镜[，,]\s*总时长[：:]\s*({NUM})\s*秒", markdown)
    if not roles_match or not climax_match or not spec:
        return errors + ["INPUT_FORMAT: 缺少出场角色、高潮节拍或总镜头数/总时长"], [], []
    roles = [r.strip() for r in re.split("[、，,]", roles_match[1])]
    if not 1 <= len(roles) <= 2 or len(set(roles)) != len(roles):
        errors.append("INPUT_FORMAT: 出场角色须为一至两个不重复名称")
    if int(spec[1]) != len(rows):
        errors.append("SHOT_TIME_OVERFLOW: 总镜头数与表格行数不一致")
    shots, foreground, named_sounds = [], [], {}
    cursor = D(0)
    for index, row in enumerate(rows, 1):
        name, beat, timeline, camera, motion, dialogue, sounds, typography = row
        if name != f"Shot {index}" or not re.fullmatch(r"Beat \d+", beat):
            errors.append(f"INPUT_FORMAT: {name} 镜号须连续，对应节拍须为 Beat N")
        tm = re.fullmatch(rf"(\d+:\d+(?:\.\d+)?)\s*[–—-]\s*(\d+:\d+(?:\.\d+)?)\s*\(({NUM})s\)", timeline)
        if not tm:
            errors.append(f"INPUT_FORMAT: {name} 时间轴不可解析")
            continue
        start, end, duration = clock(tm[1]), clock(tm[2]), D(tm[3])
        if start != cursor or end - start != duration or not D('2.5') <= duration <= D('4.5'):
            errors.append(f"SHOT_TIME_OVERFLOW: {name} 时间轴 {timeline} 不连续、时长不符或超出 2.5–4.5s")
        cursor = end
        phases = re.findall(rf"\[([^\]]+)\]\s*{SPAN}", motion)
        if len(phases) != 3 or not all(k in p[0] for k, p in zip(('Anticipation', 'Squash & Stretch', 'Hold'), phases)):
            errors.append(f"INPUT_FORMAT: {name} 缺少有序的三阶段及完整区间")
        else:
            intervals = [(D(p[1]), D(p[2])) for p in phases]
            if intervals[0][0] != 0 or intervals[-1][1] != duration or any(a >= b for a, b in intervals) or any(intervals[i][1] != intervals[i+1][0] for i in (0, 1)):
                errors.append(f"SHOT_TIME_OVERFLOW: {name} 三阶段未连续覆盖 0–{duration}s")
            if not D('.5') <= intervals[0][1] <= 1 or not 1 <= intervals[2][1] - intervals[2][0] <= D('1.5'):
                errors.append(f"PHASE_DURATION: {name} 蓄力或动力学 Hold 时长不合规")
            jump = [re.search(rf"{label}:\s*t=({NUM})s", motion) for label in ('起跳', '落地', '缓冲结束')]
            if any(jump):
                if not all(jump):
                    errors.append(f"INPUT_FORMAT: {name} 跳跃缺少起跳/落地/缓冲结束秒点")
                else:
                    takeoff, landing, settled = [D(j[1]) for j in jump]
                    if not intervals[1][0] <= takeoff < landing <= settled <= intervals[1][1] or landing - takeoff > 1:
                        errors.append(f"ZERO_AIRBORNE_CUT: {name} 跳跃 {takeoff}–{settled}s 未在爆发段完成或滞空超过 1s")
        for label in ('首帧接地', 'Hold接地'):
            match = re.search(rf"{label}[：:]\s*([^；。<\n]+)", motion)
            if not match:
                errors.append(f"INPUT_FORMAT: {name} 缺少 {label} 声明")
                continue
            contacts = dict(re.findall(r"([^=，,]+)=([^，,]+)", match[1]))
            contacts = {k.strip(): v.strip() for k, v in contacts.items()}
            for role in roles:
                value = contacts.get(role)
                if value is None:
                    errors.append(f"INPUT_FORMAT: {name} {label} 缺少 {role}")
                elif value not in ('双脚', '单脚', '臀部', '双手'):
                    errors.append(f"ZERO_AIRBORNE_CUT: {name} {label} {role}={value}，须有实际地面支点")
        lifecycles = []
        for item in typography.split('<br>'):
            content = re.split(r"；字幕[：:]", item.strip(), maxsplit=1)
            m = TEXT.fullmatch(content[0])
            if len(content) == 2 and not content[1].endswith("（与花字同生命周期）"):
                errors.append(f"INPUT_FORMAT: {name} 配套字幕须与花字共用生命周期")
            if not m:
                if item.strip() not in ('无花字、无字幕', f'独立镜尾核验：t={duration.normalize()}s 无花字、无字幕'):
                    errors.append(f"INPUT_FORMAT: {name} 花字须为标准单行生命周期或无花字、无字幕：{item}")
                continue
            trigger, word, hold, shrink, clear = D(m[1]), m[2].strip(), D(m[3]), D(m[4]), D(m[5])
            if not D('1.2') <= hold <= D('1.5') or shrink != trigger + hold or clear != shrink + D('.5'):
                errors.append(f"TEXT_TIMING: {name} {word} 保持/退场秒点不合规")
            if trigger + hold + D('.5') > duration or clear > duration:
                errors.append(f"SHOT_TIME_OVERFLOW: {name} {word} t={clear}s 超出镜长 {duration}s")
            if index == len(rows) and (trigger > duration - 3 or clear > duration - D('1.25')):
                errors.append(f"FINAL_CLEAR: {name} {word} 触发 {trigger}s / 消失 {clear}s 不满足末镜双重清屏")
            lifecycles.append((trigger, clear, word))
        lifecycles.sort()
        for prev, nxt in zip(lifecycles, lifecycles[1:]):
            if nxt[0] - prev[1] < D('.5'):
                errors.append(f"TEXT_OVERLAP: {name} {prev[2]} 消失 {prev[1]}s 至 {nxt[2]} 触发 {nxt[0]}s 不足 0.5s")
        for column in (dialogue, sounds):
            for item in column.split('<br>'):
                if item.strip() == '无':
                    continue
                spans = re.findall(SPAN, item)
                if len(spans) != 1:
                    errors.append(f"INPUT_FORMAT: {name} 声音需单一起止区间：{item}")
                    continue
                left, right = map(D, spans[0])
                if not 0 <= left < right <= duration:
                    errors.append(f"SHOT_TIME_OVERFLOW: {name} 声音 {left}–{right}s 超出镜长")
                if column == sounds and not re.match(r'(主要 SFX|环境微声)[：:]', item):
                    errors.append(f"INPUT_FORMAT: {name} SFX 缺少主要/环境分类")
                if not item.startswith('环境微声'):
                    foreground.append((start + left, start + right))
                sound_name = re.split(r'[，,；;]|t\s*=', item)[0].strip()
                interval = (start + left, start + right)
                for old_start, old_end in named_sounds.get(sound_name, []):
                    if max(old_start, interval[0]) < min(old_end, interval[1]):
                        errors.append(f"SOUND_RETRIGGER: {name} {sound_name} 在持续覆盖区间内重复触发 t={left}s")
                named_sounds.setdefault(sound_name, []).append(interval)
        shots.append({'name': name, 'beat': beat, 'start': start, 'end': end, 'camera': camera, 'phases': phases, 'texts': lifecycles})
    if cursor != D(spec[2]):
        errors.append(f"SHOT_TIME_OVERFLOW: 总时间轴 {cursor}s 与总览 {spec[2]}s 不符")
    if not any(s['beat'] == f'Beat {climax_match[1]}' for s in shots):
        errors.append("INPUT_FORMAT: 高潮节拍未出现在表格中")
    for i, shot in enumerate(shots):
        if i in (0, len(shots)-1) and shot['camera'] != '中全景 / Static':
            errors.append(f"CAMERA_RULE: {shot['name']} 首末镜须为中全景 / Static")
    # Compute gaps on the whole timeline; a cut must not reset the silence clock.
    cursor = D(0)
    gaps = []
    for left, right in sorted(foreground):
        if left > cursor:
            gaps.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < D(spec[2]):
        gaps.append((cursor, D(spec[2])))
    for left, right in gaps:
        touches_ordinary = any(s['beat'] != f'Beat {climax_match[1]}' and
                               max(left, s['start']) < min(right, s['end']) for s in shots)
        limit = D('1.5') if touches_ordinary else D(2)
        if right - left > limit:
            errors.append(f"SOUND_GAP: 全片 t={left}–{right}s 前景空白 {right-left}s > {limit}s")
    return errors, shots, roles


def validate_prompts(markdown, shots, roles):
    errors = []
    assets = markdown.split('### Shot ')[0].replace('**', '')
    if PALETTE not in assets:
        errors.append('PALETTE_LOCK: 全局资产卡缺少完整 Palette Lock')
    if re.search(r'(气球|balloon|充气|inflatable|flexible open neck)', assets, re.I) and re.search(r'\b(tied[ -]off|sealed|knotted|self-sealing)\b', assets, re.I):
        errors.append('OPEN_PROP: 全局未封闭道具资产卡含永久封闭禁词')
    cards = re.split(r'^### Shot (\d+)\s*$', markdown, flags=re.M)
    numbers = [int(cards[i]) for i in range(1, len(cards), 2)]
    if numbers != list(range(1, len(shots)+1)):
        errors.append('INPUT_FORMAT: 制作矩阵须逐镜覆盖导演稿且镜号连续')
    for i in range(1, len(cards), 2):
        number, body = int(cards[i]), cards[i+1]
        # A card ends before the assembly sheet, which has no prompt code blocks.
        body = body.split('## 【后期音画装配清单')[0]
        name = f'Shot {number}'
        blocks = re.findall(r'(?ms)^(```|~~~)text\s*\n(.*?)^\1\s*$', body)
        if len(blocks) != 2:
            errors.append(f'INPUT_FORMAT: {name} 须有 T2I/I2V 两段 text 代码块')
            continue
        t2i, i2v = [b[1].strip() for b in blocks]
        outside = re.sub(r'(?ms)^(```|~~~)text\s*\n.*?^\1\s*$', '', body).replace('**', '')
        for field in ('Negative Prompt', 'Motion Strength', 'Camera Mode', 'Start-Frame', 'End-Frame'):
            if len(re.findall(rf'^- {field}:[ \t]*\S[^\n]*$', outside, re.M)) != 1:
                errors.append(f'CONTROL_FIELD: {name} {field} 必须独立单列且非空')
            if re.search(rf'\b{field}\b', t2i + '\n' + i2v):
                errors.append(f'CONTROL_FIELD: {name} {field} 泄漏进正文')
        if re.search(r'\bKeyframe Control\b', t2i + '\n' + i2v):
            errors.append(f'CONTROL_FIELD: {name} Keyframe Control 泄漏进正文')
        if not re.search(r'^- Negative Prompt: ' + re.escape(NEGATIVE) + r'\s*$', outside, re.M):
            errors.append(f'CONTROL_FIELD: {name} Negative Prompt 九项词不完整')
        if not t2i.endswith(PALETTE + ' --ar 9:16'):
            errors.append(f'PALETTE_LOCK: {name} T2I 尾部缺少完整 Palette Lock / --ar 9:16')
        if re.search(r'\b(falling|bouncing|deflating|escaping|descending)\b', t2i, re.I):
            errors.append(f'T2I_SNAPSHOT: {name} T2I 包含过程动作')
        visible = re.search(r'^- 入镜角色[：:][ \t]*(.+)$', outside, re.M)
        visible_roles = [r.strip() for r in re.split('[、，,]', visible[1])] if visible else roles
        if not visible_roles or len(set(visible_roles)) != len(visible_roles) or not set(visible_roles) <= set(roles):
            errors.append(f'INPUT_FORMAT: {name} 入镜角色须来自导演名单且不重复')
        for role in visible_roles:
            anchor = rf'{re.escape(role)}\s+x\s*=\s*({NUM})%'
            values = [re.search(anchor, text) for text in (outside, t2i, i2v)]
            if not all(values):
                errors.append(f'COORDINATE_LOCK: {name} 构图/T2I/I2V 缺少 {role} 数值 x 锚点')
            elif len({D(v[1]) for v in values}) != 1 or not 0 <= D(values[0][1]) <= 100:
                errors.append(f'COORDINATE_LOCK: {name} {role} 的 x 锚点不一致或越界')
        for anchor, minimum, maximum in (
            (rf'(?:道具|prop)\s+x=({NUM})%', D(35), D(65)),
            (rf'(?:脚底基线|sole baseline)\s+y=({NUM})%', D(0), D(100)),
        ):
            values = [re.search(anchor, text) for text in (outside, t2i, i2v)]
            zero_props = 'prop' in anchor and '道具=无' in outside and 'prop=none' in t2i and 'prop=none' in i2v
            if zero_props:
                continue
            if not all(values):
                errors.append(f'COORDINATE_LOCK: {name} 构图/T2I/I2V 缺少道具/脚底基线数值锚点')
            elif len({D(v[1]) for v in values}) != 1 or not minimum <= D(values[0][1]) <= maximum:
                errors.append(f'COORDINATE_LOCK: {name} 道具走廊/脚底基线不一致或越界')
        prop_y = [re.search(rf'(?:道具|prop)\s+x={NUM}%[，,]\s*y=({NUM})%', text) for text in (outside, t2i)]
        if not ('道具=无' in outside and 'prop=none' in t2i):
            if not all(prop_y) or len({D(v[1]) for v in prop_y if v}) != 1 or not 0 <= D(prop_y[0][1]) <= 100:
                errors.append(f'COORDINATE_LOCK: {name} 构图/T2I 道具 y 锚点缺失、不一致或越界')
        if re.search(r'(气球|balloon|充气|inflatable|flexible open neck)', body, re.I) and re.search(r'\b(tied[ -]off|sealed|knotted|self-sealing)\b', t2i + '\n' + i2v, re.I):
            errors.append(f'OPEN_PROP: {name} 未封闭道具包含永久封闭禁词')
        if 1 <= number <= len(shots):
            source_phases = [(D(p[1]), D(p[2])) for p in shots[number-1]['phases']]
            prompt_phases = re.findall(rf'\[[^\]]+\]\s*{SPAN}', i2v)
            if [(D(a), D(b)) for a, b in prompt_phases] != source_phases:
                errors.append(f'SHOT_TIME_OVERFLOW: {name} I2V 阶段时间与导演稿不一致')
        stages = re.split(r'\[[^\]]+\]', i2v)[1:]
        if len(stages) != 3 or 'aftermotion decays' not in stages[-1]:
            errors.append(f'I2V_ALIVE: {name} 缺少三阶段或 Hold 残余弹性衰减')
        if len(visible_roles) == 2 and any(' while ' not in stage for stage in stages):
            errors.append(f'I2V_ALIVE: {name} 双角色阶段缺少 while 保活')
        if number == len(shots):
            if re.search(r'\b(?:step|steps|stepping|walk|walks|walking)\s+away\b', i2v, re.I):
                errors.append(f'FINAL_RESET: {name} 末镜含多余离场位移')
            for field in ('- End-Frame: Shot 1 Start Keyframe', '- Keyframe Control: First-Last Frame Mode'):
                if not re.search(r'^' + re.escape(field) + r'\s*$', outside, re.M):
                    errors.append(f'CONTROL_FIELD: {name} 缺少 {field}')
    assembly = table_rows(markdown, '镜头号', 6, errors)
    for shot in shots:
        actual = []
        for row in assembly:
            if row[0] == shot['name']:
                for m in TEXT.finditer(row[5]):
                    actual.append((D(m[1]), D(m[5]), m[2].strip()))
        if actual != shot['texts']:
            errors.append(f'TEXT_TIMING: {shot["name"]} 后期表花字生命周期与导演稿不一致或拆行/遗漏')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('director', type=Path)
    parser.add_argument('prompts', type=Path, nargs='?')
    args = parser.parse_args()
    try:
        errors, shots, roles = validate_director(args.director.read_text(encoding='utf-8'))
        if args.prompts:
            errors += validate_prompts(args.prompts.read_text(encoding='utf-8'), shots, roles)
    except (OSError, UnicodeError) as exc:
        print(f'INPUT_FORMAT: {exc}')
        return 1
    for error in errors:
        print(error)
    if not errors:
        print('PASS: 显式接地、时间、声音与花字规则通过' + ('；提示词硬规则通过' if args.prompts else ''))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
