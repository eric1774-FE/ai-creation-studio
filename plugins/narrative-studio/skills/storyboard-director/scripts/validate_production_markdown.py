#!/usr/bin/env python3
"""Validate the canonical director Markdown and an optional prompt matrix.

Only explicit declarations are checked; missing evidence fails closed. This is
not a natural-language interpreter or validation of rendered animation.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
import re

NUM = r"\d+(?:\.\d+)?"
SPAN = rf"t\s*=\s*({NUM})s?\s*[–—~-]\s*({NUM})s"
PALETTE = "Color Palette: warm pastel tones, 3200K studio warm lighting, consistent clay material index"
NEGATIVE = "2D, flat, realistic animal fur, text, watermark, subtitles, words, letters, deformed limbs"
PRESETS = {
    'Pip': 'tiny chubby green dragon figurine, two-head-tall proportions, smooth soft dough-like plasticine body, large pure black button eyes, short little tail',
    'Toby': 'chubby Shiba Inu figurine, yellow-and-white sculpted clay fur grooves, upright ears, curled tail, glossy black nose',
}
JUMP_ACTION = r'\b(?:jump(?:s|ed|ing)?|hop(?:s|ped|ping)?|leap(?:s|ed|ing)?|leapt)\b|腾空|跃起|起跳|跳起|蹦起|跳跃'
PROCESS_ACTION = r'\b(?:falling|bouncing|dropping|deflating|escaping|descending|stepping\s+away|flying)\b'
TEXT = re.compile(
    rf"触发点:\s*t=({NUM})s｜内容:\s*([^｜]+)｜视觉动效:\s*"
    rf"弹出保持\s*({NUM})s，t=({NUM})s\s*动效收拢，t=({NUM})s\s*消失"
)


def normalized(value):
    return ' '.join(value.casefold().split())


def affirmative_action(text, pattern, roles=()):
    """Finite clause/word rules, not an AST or a natural-language interpreter."""
    for role in sorted(roles, key=len, reverse=True):
        text = re.sub(r'(?<!\w)' + re.escape(role) + r'(?!\w)', 'subject', text, flags=re.I)
    text = re.sub(r'''["“‘'`]\s*(?:jump|hop|leap)[.!?]?\s*["”’'`]''', '', text, flags=re.I)
    text = re.sub(r'\bflying squirrel\b', 'squirrel', text, flags=re.I)
    clauses = re.split(r'<br>|[，,；;。!?！？\n]|(?<!\d)\.(?!\d)|\b(?:but|while|then|whereas)\b|\band\s+(?=subject\b)', text, flags=re.I)
    for clause in clauses:
        for action in re.finditer(pattern, clause, re.I):
            prefix = clause[:action.start()]
            # shortcut: negation is scoped to a clause; novel wording needs human review.
            if not re.search(r"\b(?:no|not|never|without|avoid|avoids|avoiding|cannot|can't|don't|doesn't|isn't|aren't)\b|不|未|没有|禁止|避免|不得|不可|无需|无须", prefix, re.I):
                return True
    return False


def validate_jump(motion, phases, name, roles, errors):
    declarations = re.findall(r'(?:^|<br>)跳跃声明[：:]\s*([^<\n]+)', motion)
    if len(declarations) != 1:
        errors.append(f'INPUT_FORMAT: {name} 须有唯一跳跃声明：无，或起跳/落地/缓冲结束秒点')
        return
    declaration = declarations[0].strip()
    prose = re.sub(r'(?:^|<br>)跳跃声明[：:][^<\n]+', '', motion)
    if declaration == '无':
        if affirmative_action(prose, JUMP_ACTION, roles):
            errors.append(f'UNDECLARED_JUMP_ACTION: {name} 正文含肯定性跳跃动作，但跳跃声明为无')
        return
    jump = re.fullmatch(rf'起跳:\s*t=({NUM})s；落地:\s*t=({NUM})s；缓冲结束:\s*t=({NUM})s', declaration)
    if not jump:
        errors.append(f'INPUT_FORMAT: {name} 跳跃声明缺少完整、可解析的起落及缓冲秒点')
        return
    if len(phases) == 3:
        takeoff, landing, settled = map(D, jump.groups())
        burst_start, burst_end = D(phases[1][1]), D(phases[1][2])
        if not burst_start <= takeoff < landing <= settled <= burst_end or landing - takeoff > 1:
            errors.append(f'ZERO_AIRBORNE_CUT: {name} 跳跃 {takeoff}–{settled}s 未在爆发段完成或滞空超过 1s')


def validate_text_gaps(shots, total, errors):
    events = sorted((shot['start'] + trigger, shot['start'] + clear, word, shot['name'])
                    for shot in shots for trigger, clear, word in shot['texts'])
    if not events:
        return
    pairs = list(zip(events, events[1:]))
    first = events[0]
    pairs.append((events[-1], (first[0] + total, first[1] + total, first[2], first[3])))
    for prev, nxt in pairs:
        if nxt[0] - prev[1] < D('.5'):
            errors.append(f'TEXT_OVERLAP: {prev[3]} {prev[2]} 全片消失 t={prev[1]}s 至 '
                          f'{nxt[3]} {nxt[2]} 全片触发 t={nxt[0]}s，间隔 {nxt[0]-prev[1]}s < 0.5s（含循环）')


def state_value(value, field=''):
    if isinstance(value, str):
        return normalized(value)
    if isinstance(value, dict):
        return {k: state_value(v, k) for k, v in value.items()}
    if isinstance(value, list):
        result = [state_value(v) for v in value]
        return sorted(result) if field == 'contacts' else result
    return value


def number_pair(value, position=False):
    return (isinstance(value, list) and len(value) == 2
            and all(isinstance(v, (int, D)) and not isinstance(v, bool) and D(v).is_finite()
                    and (not position or 0 <= v <= 100) for v in value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'重复 JSON 字段 {key}')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f'非有限 JSON 数值 {value}')


def loop_state(markdown, roles, errors, location):
    blocks = re.findall(r'(?ms)^```json[ \t]*\n(.*?)^```[ \t]*$', markdown)
    if len(blocks) != 1:
        errors.append(f'INPUT_FORMAT: {location} 须有唯一首尾状态 JSON 块')
        return None
    try:
        state = json.loads(blocks[0], parse_float=D, parse_int=D, object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except ValueError as exc:
        errors.append(f'INPUT_FORMAT: {location} 首尾状态 JSON 无效：{exc}')
        return None
    if not isinstance(state, dict) or set(state) != {'first_start', 'last_end'}:
        errors.append(f'INPUT_FORMAT: {location} 须声明 first_start 与 last_end')
        return None
    invalid = False
    for endpoint, frame in state.items():
        if not isinstance(frame, dict) or set(frame) != {'characters', 'prop', 'view'}:
            errors.append(f'INPUT_FORMAT: {location} {endpoint} 缺少 characters/prop/view 或含未知字段')
            invalid = True
            continue
        characters = frame['characters']
        if not isinstance(characters, dict) or set(characters) != set(roles):
            errors.append(f'INPUT_FORMAT: {location} {endpoint} 角色名单须与导演名单一致')
            invalid = True
            continue
        entities = [(name, details, False) for name, details in characters.items()]
        if frame['prop'] is not None:
            entities.append(('prop', frame['prop'], True))
        for entity, details, is_prop in entities:
            fields = ({'position', 'facing', 'pose', 'contacts', 'velocity', 'phase', 'secondary_motion'}
                      if not is_prop else {'position', 'orientation', 'shape', 'integrity', 'contacts', 'velocity', 'phase'})
            valid = isinstance(details, dict) and set(details) == fields
            if valid:
                valid = (number_pair(details['position'], position=True) and number_pair(details['velocity'])
                         and isinstance(details['contacts'], list)
                         and all(isinstance(v, str) and v.strip() for v in details['contacts'])
                         and all(isinstance(details[k], str) and details[k].strip()
                                 for k in fields - {'position', 'velocity', 'contacts'}))
            if not valid:
                errors.append(f'INPUT_FORMAT: {location} {endpoint}.{entity} 状态字段、位置、速度或接触列表无效')
                invalid = True
        view = frame['view']
        if not isinstance(view, dict) or set(view) != {'framing', 'camera', 'lighting', 'graphics'} or not all(isinstance(v, str) and v.strip() for v in view.values()):
            errors.append(f'INPUT_FORMAT: {location} {endpoint}.view 缺少取景、机位、光照或图形状态')
            invalid = True
    if invalid:
        return None
    if state_value(state['first_start']) != state_value(state['last_end']):
        errors.append(f'LOOP_STATE_MISMATCH: {location} first_start 与 last_end 状态不等价')
    return state


def character_anchors(assets, roles, errors):
    anchors = {}
    for role, source, description in re.findall(r'^- 角色\s+[AB]（([^）]+)）[：:]\s*\[(Built-in Golden Anchor|Dynamic Clay-Adapted Anchor)\]\s*(.+)$', assets, re.M):
        if role in anchors:
            errors.append(f'INPUT_FORMAT: 重复角色资产卡 {role}')
        anchors[role] = description.strip()
        if source == 'Built-in Golden Anchor' and (role not in PRESETS or normalized(description) != normalized(PRESETS[role])):
            errors.append(f'ANCHOR_MISSING: {role} 内置资产卡未完整保留其预设；自定义设计须标记 Dynamic Clay-Adapted Anchor')
    if set(anchors) != set(roles):
        errors.append('ANCHOR_MISSING: 资产卡须逐一声明导演名单中的角色、来源标签及完整英文锚点')
    return anchors


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
        validate_jump(motion, phases, name, roles, errors)
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
            trigger, word, text_hold, shrink, clear = D(m[1]), m[2].strip(), D(m[3]), D(m[4]), D(m[5])
            if not D('1.2') <= text_hold <= D('1.5') or shrink != trigger + text_hold or clear != shrink + D('.5'):
                errors.append(f"TEXT_TIMING: {name} {word} 保持/退场秒点不合规")
            if trigger + text_hold + D('.5') > duration or clear > duration:
                errors.append(f"SHOT_TIME_OVERFLOW: {name} {word} t={clear}s 超出镜长 {duration}s")
            if index == len(rows) and (trigger > duration - 3 or clear > duration - D('1.25')):
                errors.append(f"FINAL_CLEAR: {name} {word} 触发 {trigger}s / 消失 {clear}s 不满足末镜双重清屏")
            lifecycles.append((trigger, clear, word))
        lifecycles.sort()
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
    validate_text_gaps(shots, D(spec[2]), errors)
    loop_heading = re.search(r'^## .*Loop Check.*$', markdown, re.M)
    loop_section = re.split(r'^## ', markdown[loop_heading.end():], maxsplit=1, flags=re.M)[0] if loop_heading else ''
    state = loop_state(loop_section, roles, errors, f'Shot 1 首帧 / Shot {len(rows)} 尾帧 Loop Check')
    if shots:
        shots[0]['loop_state'] = state
    if state and shots:
        for endpoint, shot in (('first_start', shots[0]), ('last_end', shots[-1])):
            view = state[endpoint]['view']
            if normalized(view['framing'] + ' / ' + view['camera']) != normalized(shot['camera']):
                errors.append(f'LOOP_STATE_MISMATCH: {shot["name"]} {endpoint} 取景/机位与分镜列不一致')
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
    anchors = character_anchors(assets, roles, errors)
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
        if affirmative_action(t2i, PROCESS_ACTION, roles):
            errors.append(f'PROCESS_VERB_IN_T2I: {name} T2I 包含肯定性过程动作')
        visible = re.search(r'^- 入镜角色[：:][ \t]*(.+)$', outside, re.M)
        visible_roles = [r.strip() for r in re.split('[、，,]', visible[1])] if visible else roles
        if not visible_roles or len(set(visible_roles)) != len(visible_roles) or not set(visible_roles) <= set(roles):
            errors.append(f'INPUT_FORMAT: {name} 入镜角色须来自导演名单且不重复')
        for role in visible_roles:
            if role not in anchors or normalized(anchors[role]) not in normalized(t2i):
                errors.append(f'ANCHOR_MISSING: {name} T2I 未完整复用 {role} 的资产卡锚点')
            anchor = rf'{re.escape(role)}\s+x\s*=\s*({NUM})%'
            values = [re.search(anchor, text) for text in (outside, t2i, i2v)]
            if not all(values):
                errors.append(f'COORDINATE_LOCK: {name} 构图/T2I/I2V 缺少 {role} 数值 x 锚点')
            elif len({D(v[1]) for v in values}) != 1 or not 0 <= D(values[0][1]) <= 100:
                errors.append(f'COORDINATE_LOCK: {name} {role} 的 x 锚点不一致或越界')
            positions = [re.search(rf'{re.escape(role)}\s+x=({NUM})%[，,]\s*y=({NUM})%', text) for text in (outside, t2i)]
            if not all(positions) or len({(D(v[1]), D(v[2])) for v in positions if v}) != 1 or any(not 0 <= D(v[2]) <= 100 for v in positions if v):
                errors.append(f'COORDINATE_LOCK: {name} 构图/T2I 缺少或不一致的 {role} x/y 起始坐标')
            if number == 1 and shots and shots[0].get('loop_state') and role in roles and all(positions):
                target = shots[0]['loop_state']['first_start']['characters'][role]['position']
                if [D(positions[0][1]), D(positions[0][2])] != target:
                    errors.append(f'LOOP_STATE_MISMATCH: {name} {role} 首帧坐标与 first_start 不一致')
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
        if number == 1 and shots and shots[0].get('loop_state'):
            prop = shots[0]['loop_state']['first_start']['prop']
            prop_x = re.search(rf'prop\s+x=({NUM})%', t2i)
            if prop is None:
                if 'prop=none' not in t2i:
                    errors.append(f'LOOP_STATE_MISMATCH: {name} first_start 为零道具但 T2I 未声明 prop=none')
            elif not prop_x or not prop_y[1] or [D(prop_x[1]), D(prop_y[1][1])] != prop['position']:
                errors.append(f'LOOP_STATE_MISMATCH: {name} 道具首帧坐标与 first_start 不一致')
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
            state = loop_state(outside, roles, errors, f'{name} 末镜控制区')
            source_state = shots[0].get('loop_state') if shots else None
            if state is not None and source_state is not None and state_value(state) != state_value(source_state):
                errors.append(f'LOOP_STATE_MISMATCH: {name} 编译稿未完整保留导演首尾状态声明')
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
        print('PASS: 结构、时序与显式声明一致性通过；自由文本因果与生成媒体仍需复核')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
