"""Static handoff-contract checks; these helpers do not assess story semantics.

The parser below is a test oracle for fixtures and SKILL templates, not a new
production gate. Director enforces this contract through its skill instructions.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'plugins/narrative-studio/skills'
FIXTURES = ROOT / 'tests/fixtures/story-reviewer'
H2 = [
    '【剧本硬线与雷达体检】',
    '【手术级打磨建议（Surgery Notes）】',
    '【重写润色后的 4 拍大纲（Polished Version）】',
]
STORY_HEADINGS = [
    '【规格设定】',
    '【选定戏剧母题】',
    '【教学与 TPR 映射】',
    '【剧情节拍大纲（Beat Outline）】',
    '【家长端动作指引（CTA）】',
]
ERROR_CODES = [
    'VOCAB_GROUNDING_MISMATCH',
    'UNCLOSED_AIRBORNE_ACTION',
    'TEACHING_POLLUTION_AT_END',
    'MAGIC_RESET',
]
PASS = '- **红线筛查**：全部通过'
REFUSAL = '- **状态**：拒绝下游稿，未生成 Golden 4 拍。'
DIMENSIONS = ('道具玩具化', '橡皮泥身体喜剧', '教学无歧义', '四拍递进因果')
SURGERY = ('道具升级方案', '包袱强化方案', '时序与教学防呆')


def visible_text(markdown):
    return re.sub(r'(?ms)^```[^\n]*\n.*?^```[ \t]*$', '', markdown)


def headings(markdown, level):
    return re.findall(rf'^{level} (.+)$', markdown, re.M)


def sections(markdown, level, expected):
    parts = re.split(rf'(?m)^{level} (.+)$', markdown)
    if parts[0].strip() or parts[1::2] != expected:
        raise ValueError('missing, extra, misplaced or reordered headings')
    bodies = [body.strip() for body in parts[2::2]]
    if any(not body for body in bodies):
        raise ValueError('empty section')
    return bodies


def planner_contract(markdown):
    sections(visible_text(markdown), '##', STORY_HEADINGS)


def review_contract(markdown):
    """Return downstream eligibility; raise ValueError for malformed output."""
    visible = visible_text(markdown)
    report, notes, polished = sections(visible, '##', H2)
    status = report.splitlines()[0]
    status_lines = [line for line in visible.splitlines() if '**红线筛查**' in line]
    if status_lines != [status]:
        raise ValueError('missing, duplicate or misplaced status')
    for label in DIMENSIONS:
        if label + '：' not in report:
            raise ValueError('missing diagnostic dimension')
    for label in SURGERY:
        if f'- **{label}**：' not in notes:
            raise ValueError('missing surgery note')
    if status == PASS:
        if REFUSAL in visible:
            raise ValueError('contradictory refusal')
        story = sections(polished, '###', STORY_HEADINGS)
        if headings(visible, '###') != STORY_HEADINGS:
            raise ValueError('story sections outside polished version')
        beats = sections(story[3], '####', headings(story[3], '####'))
        numbers = re.findall(r'^#### Beat (\d+)（[^\n]+）$', story[3], re.M)
        if numbers != ['1', '2', '3', '4'] or len(beats) != 4:
            raise ValueError('expected four continuous beats with bodies')
        if '- 节拍数量：4 拍' not in story[0]:
            raise ValueError('inconsistent beat count')
        return True
    failure = re.fullmatch(r'- \*\*红线筛查\*\*：未通过 - 触发错误码: `([A-Z_]+)`', status)
    if not failure or failure[1] not in ERROR_CODES:
        raise ValueError('invalid redline status')
    if (REFUSAL not in polished or 'kids-story-planner' not in polished
            or 'kids-story-reviewer' not in polished):
        raise ValueError('failure must refuse and request resubmission')
    if headings(polished, '###') or headings(polished, '####') or re.search(r'\bBeat [1-4]\b', polished):
        raise ValueError('failure leaked a downstream outline')
    return False


class StoryReviewerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skills = {path.parent.name: path.read_text(encoding='utf-8')
                      for path in SKILLS.glob('*/SKILL.md')}
        cls.reviewer = cls.skills['kids-story-reviewer']
        cls.director = cls.skills['storyboard-director']
        cls.golden = (FIXTURES / 'golden-review.md').read_text(encoding='utf-8')
        bad = (FIXTURES / 'bad-cases.md').read_text(encoding='utf-8')
        cls.cases = re.findall(
            r'(?ms)^### ([\w-]+)\n\n- 类型：(planner|review|variant)\n- 预期：(invalid|blocked)'
            r'\n\n```(?:markdown|json)\n(.*?)^```', bad)

    def test_all_four_skills_have_frontmatter(self):
        self.assertEqual(set(self.skills), {'kids-story-planner', 'kids-story-reviewer',
                                           'storyboard-director', 'ai-prompt-generator'})
        for name, content in self.skills.items():
            with self.subTest(skill=name):
                frontmatter = re.match(r'\A---\n(.*?)\n---\n', content, re.S)
                self.assertIsNotNone(frontmatter)
                fields = dict(line.split(': ', 1) for line in frontmatter[1].splitlines())
                self.assertEqual(fields['name'], name)
                self.assertTrue(fields['description'])

    def test_golden_and_output_template_pass(self):
        self.assertTrue(review_contract(self.golden))
        templates = re.findall(r'(?ms)^```markdown\n(.*?)^```', self.reviewer)
        self.assertEqual(len(templates), 2)
        self.assertTrue(review_contract(templates[0]))
        failure = next(content for name, _, _, content in self.cases if name == 'magic-reset')
        failure = failure.split(f'## {H2[2]}', 1)[0] + templates[1]
        self.assertFalse(review_contract(failure))
        self.assertEqual(headings(self.golden, '##'), H2)
        self.assertEqual(headings(self.golden, '###'), STORY_HEADINGS)

    def test_polished_headings_match_planner_template(self):
        planner = self.skills['kids-story-planner']
        template = re.search(r'(?ms)^```markdown\n(.*?)^```', planner)[1]
        self.assertEqual(headings(template, '##'), STORY_HEADINGS)
        planner_contract(template)
        for title in STORY_HEADINGS:
            with self.subTest(missing=title):
                with self.assertRaises(ValueError):
                    planner_contract(template.replace('## ' + title, '', 1))

    def test_all_bad_fixtures_are_exercised(self):
        self.assertEqual(len(self.cases), 11)
        self.assertEqual(len({case[0] for case in self.cases}), 11)
        for case_id, kind, expected, content in self.cases:
            with self.subTest(case=case_id):
                if kind == 'variant':
                    change = json.loads(content)
                    self.assertEqual(self.golden.count(change['old']), 1)
                    content = self.golden.replace(change['old'], change['new'], 1)
                if expected == 'blocked':
                    self.assertFalse(review_contract(content))
                else:
                    with self.assertRaises(ValueError):
                        (planner_contract if kind == 'planner' else review_contract)(content)

    def test_status_variants_quotes_duplicates_and_wrong_scope_reject(self):
        replacements = (
            '- **红线筛查**：无违规，全部通过。',
            '- **红线筛查**：全部通过（已修复）',
            '> ' + PASS,
            '```markdown\n' + PASS + '\n```',
            PASS + '\n' + PASS,
            '',
            '- **红线筛查**：未通过 - 触发错误码: `UNKNOWN`',
        )
        for status in replacements:
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    review_contract(self.golden.replace(PASS, status, 1))
        wrong_scope = self.golden.replace(PASS, '', 1).replace('### 【规格设定】', PASS + '\n\n### 【规格设定】', 1)
        with self.assertRaises(ValueError):
            review_contract(wrong_scope)

    def test_section_order_missing_empty_and_extra_beats_reject(self):
        changes = [
            (f'## {H2[0]}', f'## {H2[1]}'),
            ('### 【规格设定】', '## 【规格设定】'),
            ('#### Beat 4（物理回弹复位）', '#### Beat 5（物理回弹复位）'),
            ('- 节拍数量：4 拍', '- 节拍数量：3 拍'),
        ]
        for old, new in changes:
            with self.subTest(change=old):
                with self.assertRaises(ValueError):
                    review_contract(self.golden.replace(old, new, 1))
        for title in STORY_HEADINGS:
            with self.subTest(empty=title):
                empty = re.sub(r'(?ms)(^### ' + re.escape(title) + r'\n).*?(?=^### |\Z)', r'\1\n', self.golden)
                with self.assertRaises(ValueError):
                    review_contract(empty)

    def test_failed_report_cannot_contain_any_outline(self):
        failure = next(content for name, kind, expected, content in self.cases
                       if name == 'magic-reset')
        self.assertFalse(review_contract(failure))
        for leak in ('### 【规格设定】\n故事。', '#### Beat 1（示范）\n故事。', '- Beat 1：示范。'):
            with self.subTest(leak=leak):
                with self.assertRaises(ValueError):
                    review_contract(failure + '\n' + leak)
        for removed in (REFUSAL, 'kids-story-planner', 'kids-story-reviewer'):
            with self.subTest(missing=removed):
                with self.assertRaises(ValueError):
                    review_contract(failure.replace(removed, '', 1))

    def test_raw_planner_cannot_skip_gate(self):
        raw = self.golden.split(f'## {H2[2]}', 1)[1].strip()
        raw = re.sub(r'^### ', '## ', raw, flags=re.M)
        planner_contract(raw)
        with self.assertRaises(ValueError):
            review_contract(raw)

    def test_redline_dictionary_and_gate_are_declared(self):
        for name in ('kids-story-planner', 'kids-story-reviewer', 'storyboard-director'):
            rows = re.findall(r'^\| `([A-Z_]+)` \|', self.skills[name], re.M)
            with self.subTest(skill=name):
                self.assertTrue(set(ERROR_CODES).issubset(rows))
        for name, _, _, content in self.cases:
            if name in ('vocab-grounding', 'unclosed-airborne', 'end-pollution-v1', 'magic-reset'):
                self.assertRegex(content, r'红线定位.*Beat [1-4]')
        self.assertIn('原始 `kids-story-planner` 输出不能绕过 reviewer', self.director)
        self.assertIn(PASS, self.director)
        self.assertIn('REVIEW_GATE_MISSING', self.director)
        for title in STORY_HEADINGS:
            self.assertIn('### ' + title, self.director)
        self.assertIn('Reviewer Golden 固定四拍', self.director)


if __name__ == '__main__':
    unittest.main()
