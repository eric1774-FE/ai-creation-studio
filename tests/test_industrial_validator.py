"""Behavioral regression tests for production-document rejection boundaries."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/narrative-studio/skills/storyboard-director/scripts/validate_production_markdown.py'
FIXTURES = ROOT / 'tests/fixtures/industrial-upgrade'
spec = importlib.util.spec_from_file_location('validator', SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
GOLDEN = (FIXTURES / 'golden-director.md').read_text()
PROMPTS = (FIXTURES / 'golden-prompts.md').read_text()


def errors_for(director=GOLDEN, prompts=None):
    errors, shots, roles = validator.validate_director(director)
    if prompts is not None:
        errors += validator.validate_prompts(prompts, shots, roles)
    return errors


class ProductionValidationTests(unittest.TestCase):
    def test_cli_fixtures(self):
        cases = [('golden-director.md', None), ('bad-airborne.md', 'ZERO_AIRBORNE_CUT'),
                 ('bad-text-overlap.md', 'TEXT_OVERLAP'), ('bad-time-overflow.md', 'SHOT_TIME_OVERFLOW')]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                result = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURES / filename)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1 if expected else 0, result.stdout + result.stderr)
                if expected:
                    self.assertIn(expected + ':', result.stdout)
                    self.assertIn('Shot ', result.stdout)

    def test_golden_director_and_matrix(self):
        self.assertEqual(errors_for(prompts=PROMPTS), [])

    def test_missing_evidence_is_not_a_pass(self):
        for old in ('- 出场角色：Pip、Toby', '- 高潮节拍：Beat 2',
                    '首帧接地：Pip=双脚，Toby=双脚；', '[蓄力 Anticipation] t=0–0.75s：'):
            with self.subTest(old=old):
                self.assertTrue(any(e.startswith('INPUT_FORMAT:') for e in errors_for(GOLDEN.replace(old, '', 1))))

    def test_text_hold_and_exit_boundaries(self):
        original = '弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失'
        for hold, shrink, clear, valid in [('1.2', '1.95', '2.45', True), ('1.5', '2.25', '2.75', True),
                                           ('1.19', '1.94', '2.44', False), ('1.51', '2.26', '2.76', False),
                                           ('1.5', '2.25', '2.74', False)]:
            with self.subTest(hold=hold, clear=clear):
                changed = GOLDEN.replace(original, f'弹出保持 {hold}s，t={shrink}s 动效收拢，t={clear}s 消失', 1)
                self.assertEqual(not errors_for(changed), valid)

    def test_text_clear_gap_boundary(self):
        old = '触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失'
        for trigger, shrink, clear, valid in [('2.2', '3.4', '3.9', True), ('2.19', '3.39', '3.89', False)]:
            replacement = ('触发点: t=0s｜内容: High｜视觉动效: 弹出保持 1.2s，t=1.2s 动效收拢，t=1.7s 消失'
                           f'<br>触发点: t={trigger}s｜内容: Low｜视觉动效: 弹出保持 1.2s，t={shrink}s 动效收拢，t={clear}s 消失')
            with self.subTest(trigger=trigger):
                self.assertEqual(not errors_for(GOLDEN.replace(old, replacement, 1)), valid)

    def test_final_trigger_and_clear_are_separate_constraints(self):
        old = '触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失'
        for replacement in [
            '触发点: t=1.01s｜内容: High｜视觉动效: 弹出保持 1.2s，t=2.21s 动效收拢，t=2.71s 消失',
            '触发点: t=1s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.5s 动效收拢，t=3s 消失',
        ]:
            changed = GOLDEN.rsplit(old, 1)
            self.assertIn('FINAL_CLEAR', '\n'.join(errors_for(replacement.join(changed))))

    def test_phase_overflow_and_same_shot_jump(self):
        self.assertIn('SHOT_TIME_OVERFLOW', '\n'.join(errors_for(GOLDEN.replace('t=2.75–4s', 't=2.75–4.5s', 1))))
        for jump, valid in [('起跳: t=1s；落地: t=2s；缓冲结束: t=2.5s', True),
                            ('起跳: t=1s；落地: t=2.01s；缓冲结束: t=2.5s', False),
                            ('起跳: t=1s；落地: t=2s；缓冲结束: t=2.76s', False)]:
            changed = GOLDEN.replace('首帧接地：', jump + '<br>首帧接地：', 1)
            self.assertEqual(not errors_for(changed), valid)

    def test_foreground_coverage_and_no_retrigger(self):
        for end, valid in [('2.5', True), ('2.49', False)]:
            changed = GOLDEN.replace('Squeak，t=0–2.75s', f'Squeak，t=0–{end}s', 1)
            self.assertEqual(not errors_for(changed), valid)
        # A room tone cannot fill a foreground gap; a continuous SFX needs no periodic trigger.
        self.assertIn('SOUND_GAP', '\n'.join(errors_for(GOLDEN.replace('主要 SFX：Squeak，t=0–2.75s', '环境微声：Room，t=0–4s', 1))))
        retrigger = GOLDEN.replace('Squeak，t=0–2.75s', 'Squeak，t=0–2.75s<br>主要 SFX：Squeak，t=1–2s', 1)
        self.assertIn('SOUND_RETRIGGER', '\n'.join(errors_for(retrigger)))
        self.assertEqual(errors_for(GOLDEN.replace('Squeak，t=0–2.75s', 'Squeak，t=0–4s', 1)), [])
        for end, valid in [('2', True), ('1.99', False)]:
            changed = GOLDEN.replace('Squish，t=0–3s', f'Squish，t=0–{end}s', 1)
            self.assertEqual(not errors_for(changed), valid)
        # 1.3s tail + 0.3s head across a cut is one ordinary gap of 1.6s.
        changed = GOLDEN.replace('Squeak，t=0–2.75s', 'Squeak，t=0–2.7s', 1).replace('Squeak，t=0–4s', 'Squeak，t=0.3–4s', 1)
        self.assertIn('SOUND_GAP', '\n'.join(errors_for(changed)))

    def test_prompt_banned_words_palette_and_controls(self):
        cases = [
            ('poised at rest', 'falling', 'T2I_SNAPSHOT'),
            (validator.PALETTE + ' --ar', 'Color Palette: blue --ar', 'PALETTE_LOCK'),
            ('- **Motion Strength:** 6/10', '', 'CONTROL_FIELD'),
            ('Handmade 3D clay style.', 'Handmade 3D clay style. Camera Mode: Static.', 'CONTROL_FIELD'),
            ('Pip x=30%', 'Pip on the left', 'COORDINATE_LOCK'),
            ('while Toby', 'and Toby', 'I2V_ALIVE'),
            ('aftermotion decays', 'jiggles forever', 'I2V_ALIVE'),
            ('- **End-Frame:** Shot 1 Start Keyframe', '- **End-Frame:** Shot 3 Start Keyframe', 'CONTROL_FIELD'),
        ]
        for before, after, code in cases:
            with self.subTest(code=code):
                self.assertIn(code, '\n'.join(errors_for(prompts=PROMPTS.replace(before, after))))
        final = PROMPTS.rsplit('aftermotion decays.', 1)
        self.assertIn('FINAL_RESET', '\n'.join(errors_for(prompts='aftermotion decays. Walk away.'.join(final))))

    def test_coordinates_phase_identity_and_assembly_copy(self):
        for x in ('35', '65'):
            changed = PROMPTS.replace('prop x=50%', f'prop x={x}%')
            self.assertEqual(errors_for(prompts=changed), [])
        for x in ('34.9', '65.1'):
            changed = PROMPTS.replace('prop x=50%', f'prop x={x}%')
            self.assertIn('COORDINATE_LOCK', '\n'.join(errors_for(prompts=changed)))
        mismatched = PROMPTS.replace('Pip x=30%', 'Pip x=31%', 1)
        self.assertIn('COORDINATE_LOCK', '\n'.join(errors_for(prompts=mismatched)))
        self.assertIn('SHOT_TIME_OVERFLOW', '\n'.join(errors_for(prompts=PROMPTS.replace('t=2.75-4s', 't=2.75-4.5s', 1))))
        self.assertIn('TEXT_TIMING', '\n'.join(errors_for(prompts=PROMPTS.replace('t=2.75s 消失', 't=2.85s 消失', 1))))
        self.assertIn('CONTROL_FIELD', '\n'.join(errors_for(prompts=PROMPTS.replace('- **Motion Strength:** 6/10', '- **Motion Strength:**', 1))))

    def test_zero_props_and_single_visible_role(self):
        # Single-role cards must not be forced to invent another character's anchor or while clause.
        first = PROMPTS.split('### Shot 2', 1)
        first[0] = first[0].replace('### Shot 1', '### Shot 1\n\n- **入镜角色:** Pip')
        first[0] = first[0].replace('Toby x=70%,', '').replace('Toby x=70%，', '').replace(' while ', ' and ')
        self.assertEqual(errors_for(prompts='### Shot 2'.join(first)), [])
        # An explicitly prop-free document keeps only character and floor coordinates.
        changed = PROMPTS.replace('prop x=50%，y=35%', '道具=无').replace('prop x=50%，y=79%', '道具=无')
        changed = changed.replace('prop x=50%, y=35%', 'prop=none').replace('prop x=50%, y=79%', 'prop=none').replace('prop x=50%', 'prop=none')
        self.assertEqual(errors_for(prompts=changed), [])

    def test_subtitle_lifecycle_is_explicit(self):
        changed = GOLDEN.replace('t=2.75s 消失 |', 't=2.75s 消失；字幕：High/高处（与花字同生命周期） |', 1)
        self.assertEqual(errors_for(changed), [])
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(changed.replace('（与花字同生命周期）', '', 1))))

    def test_open_prop_dictionary_and_legal_nouns(self):
        for term in ('tied-off', 'sealed', 'knotted', 'not sealed'):
            with self.subTest(term=term):
                changed = PROMPTS.replace('one clay ball', f'one balloon with {term} neck')
                self.assertIn('OPEN_PROP', '\n'.join(errors_for(prompts=changed)))
        changed = PROMPTS.replace('one clay ball', 'one unknotted balloon with flexible open neck and open passage').replace('poised at rest', 'poised at rest, soft lighting around the opening')
        self.assertEqual(errors_for(prompts=changed), [])
        assets_only = PROMPTS.replace('- Prop: one clay ball', '- Prop: one sealed balloon', 1)
        self.assertIn('OPEN_PROP', '\n'.join(errors_for(prompts=assets_only)))


if __name__ == '__main__':
    unittest.main()
