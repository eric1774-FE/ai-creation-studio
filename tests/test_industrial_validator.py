"""Behavioral regression tests for production-document rejection boundaries."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/narrative-studio/skills/storyboard-director/scripts/validate_production_markdown.py'
FIXTURES = ROOT / 'tests/fixtures/industrial-upgrade'
spec = importlib.util.spec_from_file_location('validator', SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
GOLDEN = (FIXTURES / 'golden-director.md').read_text()
PROMPTS = (FIXTURES / 'golden-prompts.md').read_text()
STATE = json.loads(re.search(r'(?ms)^```json\n(.*?)^```', GOLDEN)[1])


def with_state(document, state):
    return re.sub(r'(?ms)^```json\n.*?^```', lambda _: '```json\n' + json.dumps(state, ensure_ascii=False, indent=2) + '\n```', document)


def state_copy():
    return json.loads(json.dumps(STATE))


def first_t2i_replace(before, after):
    return re.sub(r'(?ms)^```text\n(.*?)^```', lambda m: '```text\n' + m[1].replace(before, after) + '```', PROMPTS, count=1)


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
                            ('起跳: t=0.5s；落地: t=1s；缓冲结束: t=2s', False),
                            ('起跳: t=1s；落地: t=2.01s；缓冲结束: t=2.5s', False),
                            ('起跳: t=1s；落地: t=2s；缓冲结束: t=2.76s', False)]:
            changed = GOLDEN.replace('跳跃声明：无', '跳跃声明：' + jump, 1)
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
            ('poised at rest', 'falling', 'PROCESS_VERB_IN_T2I'),
            (validator.PALETTE + ' --ar', 'Color Palette: blue --ar', 'PALETTE_LOCK'),
            ('- **Motion Strength:** 6/10', '', 'CONTROL_FIELD'),
            ('Current snapshot:', 'Current snapshot: Camera Mode: Static.', 'CONTROL_FIELD'),
            ('Pip x=30%', 'Pip on the left', 'COORDINATE_LOCK'),
            ('while Toby', 'and Toby', 'I2V_ALIVE'),
            ('aftermotion decays', 'jiggles forever', 'I2V_ALIVE'),
            ('- **End-Frame:** Shot 1 Start Keyframe', '- **End-Frame:** Shot 3 Start Keyframe', 'CONTROL_FIELD'),
        ]
        for before, after, code in cases:
            with self.subTest(code=code):
                self.assertIn(code, '\n'.join(errors_for(prompts=PROMPTS.replace(before, after))))

    def test_coordinates_phase_identity_and_assembly_copy(self):
        for x in ('35', '65'):
            changed = PROMPTS.replace('prop x=50%', f'prop x={x}%')
            state = state_copy()
            for frame in state.values():
                frame['prop']['position'][0] = int(x)
            self.assertEqual(errors_for(with_state(GOLDEN, state), with_state(changed, state)), [])
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
        first[0] = first[0].replace('- **入镜角色:** Pip、Toby', '- **入镜角色:** Pip')
        first[0] = first[0].replace('Toby x=70%, y=68%,', '').replace('Toby x=70%，y=68%，', '').replace(' while ', ' and ')
        # Remove Toby's visual identity from this shot; the full-film asset card stays.
        first[0] = first[0].replace('; Toby is a ' + validator.PRESETS['Toby'], '', 1)
        self.assertEqual(errors_for(prompts='### Shot 2'.join(first)), [])
        # An explicitly prop-free document keeps only character and floor coordinates.
        changed = PROMPTS.replace('prop x=50%，y=35%', '道具=无').replace('prop x=50%，y=79%', '道具=无')
        changed = changed.replace('prop x=50%, y=35%', 'prop=none').replace('prop x=50%, y=79%', 'prop=none').replace('prop x=50%', 'prop=none')
        state = state_copy()
        for frame in state.values():
            frame['prop'] = None
        self.assertEqual(errors_for(with_state(GOLDEN, state), with_state(changed, state)), [])

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
        assets_only = PROMPTS.replace('[Dynamic Clay-Adapted Anchor] one clay ball', '[Dynamic Clay-Adapted Anchor] one sealed balloon', 1)
        self.assertIn('OPEN_PROP', '\n'.join(errors_for(prompts=assets_only)))

    def test_cross_shot_text_gap_boundaries(self):
        first = '触发点: t=0.75s｜内容: High｜视觉动效: 弹出保持 1.5s，t=2.25s 动效收拢，t=2.75s 消失'
        second = '触发点: t=1.25s｜内容: Low｜视觉动效: 弹出保持 1.2s，t=2.45s 动效收拢，t=2.95s 消失'
        for gap, valid in [('0', False), ('0.49', False), ('0.5', True)]:
            trigger = validator.D(gap)
            replacement = f'触发点: t={trigger}s｜内容: Low｜视觉动效: 弹出保持 1.2s，t={trigger+validator.D("1.2")}s 动效收拢，t={trigger+validator.D("1.7")}s 消失'
            changed = GOLDEN.replace(first, '触发点: t=2s｜内容: High｜视觉动效: 弹出保持 1.5s，t=3.5s 动效收拢，t=4s 消失', 1).replace(second, replacement, 1)
            changed = changed.replace('t=0.75–1.15s Pip: High!', 't=2–2.4s Pip: High!', 1)
            changed = changed.replace('t=1.25–1.65s Toby: Low!', f't={trigger}–{trigger+validator.D("0.4")}s Toby: Low!', 1)
            with self.subTest(gap=gap):
                errors = errors_for(changed)
                self.assertEqual(not errors, valid, errors)
                if not valid:
                    self.assertTrue(any(e.startswith('TEXT_OVERLAP:') and 'Shot 1' in e and 'Shot 2' in e for e in errors))

    def test_loop_text_gap_uses_next_playback_absolute_time(self):
        # Test the shared gap calculation independently of the stricter final-clear rule.
        for clear, valid in [('15.51', False), ('15.5', True)]:
            shots = [dict(start=validator.D(0), name='Shot 1', texts=[(validator.D(0), validator.D(2), 'High')]),
                     dict(start=validator.D(12), name='Shot 4', texts=[(validator.D(1), validator.D(clear)-12, 'Low')])]
            errors = []
            validator.validate_text_gaps(shots, validator.D(16), errors)
            self.assertEqual(not errors, valid)
            if not valid:
                self.assertIn('Shot 4', errors[0])
                self.assertIn('t=16s', errors[0])

    def test_jump_declaration_required_and_positive_scan(self):
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(GOLDEN.replace('<br>跳跃声明：无', '', 1))))
        for prose in ('Pip jumps and lands', 'Pip hops', 'Pip leaps', 'Pip 跃起再落地', 'Toby 腾空后落地', 'Pip 完成跳跃', 'Pip does not jump and Toby hops'):
            changed = GOLDEN.replace('球保持高处', prose + '，球保持高处', 1)
            self.assertIn('UNDECLARED_JUMP_ACTION', '\n'.join(errors_for(changed)), prose)
        for prose in ('Pip does not jump', 'Toby never hops', 'Pip is not jumping and hopping', '禁止腾空', 'Pip 未跃起', '教学词 “Jump”', '辅助口令 \'Hop\''):
            changed = GOLDEN.replace('球保持高处', prose + '，球保持高处', 1)
            self.assertEqual(errors_for(changed), [], prose)
        self.assertEqual(errors_for(GOLDEN.replace('Pip', 'Jump')), [])
        malformed = GOLDEN.replace('跳跃声明：无', '跳跃声明：起跳: t=1s；落地: t=2s', 1)
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(malformed)))
        duplicate = GOLDEN.replace('跳跃声明：无', '跳跃声明：无<br>跳跃声明：无', 1)
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(duplicate)))

    def test_identity_is_required_in_each_visible_t2i(self):
        for role, anchor in validator.PRESETS.items():
            changed = first_t2i_replace(anchor, role)
            self.assertIn('ANCHOR_MISSING', '\n'.join(errors_for(prompts=changed)), role)
        weakened = PROMPTS.replace(validator.PRESETS['Pip'], 'small green dragon')
        self.assertIn('ANCHOR_MISSING', '\n'.join(errors_for(prompts=weakened)))
        changed = first_t2i_replace(validator.PRESETS['Pip'], validator.PRESETS['Pip'].upper().replace(', ', ',  '))
        self.assertEqual(errors_for(prompts=changed), [])

    def test_custom_anchor_does_not_inherit_pip_features(self):
        custom = 'small blue clay flying squirrel figurine, amber eyes, broad membrane flaps, short round body'
        director = GOLDEN.replace('Pip', 'Milo')
        prompts = PROMPTS.replace(validator.PRESETS['Pip'], custom).replace('Pip', 'Milo')
        prompts = prompts.replace('角色 A（Milo）**：[Built-in Golden Anchor]', '角色 A（Milo）**：[Dynamic Clay-Adapted Anchor]')
        self.assertEqual(errors_for(director, prompts), [])
        missing = re.sub(r'(?ms)^```text\n(.*?)^```', lambda m: '```text\n' + m[1].replace(custom, 'Milo') + '```', prompts, count=1)
        self.assertIn('ANCHOR_MISSING', '\n'.join(errors_for(director, missing)))

    def test_t2i_process_words_and_static_exemptions(self):
        for word in ('falling', 'bouncing', 'dropping', 'deflating', 'escaping', 'descending', 'stepping away', 'flying'):
            self.assertIn('PROCESS_VERB_IN_T2I', '\n'.join(errors_for(prompts=first_t2i_replace('poised at rest', word))), word)
        for phrase in ('holding a handle', 'leaning left', 'standing', 'resting', 'soft lighting around the opening', 'not falling'):
            self.assertEqual(errors_for(prompts=first_t2i_replace('poised at rest', phrase)), [], phrase)

    def test_loop_state_missing_and_invalid_json(self):
        missing = re.sub(r'(?ms)^```json\n.*?^```', '', GOLDEN)
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(missing)))
        for replacement in ('{', '{"first_start": NaN, "last_end": null}', '{"first_start": {}, "first_start": {}, "last_end": {}}'):
            changed = re.sub(r'(?ms)^```json\n.*?^```', lambda _: '```json\n' + replacement + '\n```', GOLDEN)
            self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(changed)))
        for key in ('position', 'pose', 'contacts', 'velocity', 'phase', 'secondary_motion'):
            state = state_copy()
            del state['last_end']['characters']['Pip'][key]
            self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(with_state(GOLDEN, state))))
        state = state_copy()
        state['last_end']['characters']['Unknown'] = state['last_end']['characters'].pop('Pip')
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(with_state(GOLDEN, state))))
        moved = GOLDEN.replace('## 【首尾无缝循环衔接验证（Loop Check）】', '## 其他说明')
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(moved)))
        for value in (['30', 65], [True, 65], [101, 65], None):
            state = state_copy()
            state['first_start']['characters']['Pip']['position'] = value
            self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(with_state(GOLDEN, state))))

    def test_malformed_documents_return_cli_errors_without_tracebacks(self):
        # Missing shot records must not crash the subsequent loop or compiler checks.
        invalid = GOLDEN.replace('00:00–00:04 (4s)', 'unparseable timeline').replace('00:04–00:08 (4s)', 'unparseable timeline')
        invalid = invalid.replace('00:08–00:12 (4s)', 'unparseable timeline').replace('00:12–00:16 (4s)', 'unparseable timeline')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.md'
            path.write_text(invalid, encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), str(FIXTURES / 'golden-prompts.md')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('INPUT_FORMAT', result.stdout)
            self.assertNotIn('Traceback', result.stderr)
        unknown = PROMPTS.replace('- **入镜角色:** Pip、Toby', '- **入镜角色:** Unknown', 1).replace('Pip x=30%', 'Unknown x=30%')
        self.assertIn('INPUT_FORMAT', '\n'.join(errors_for(prompts=unknown)))

    def test_state_labels_normalize_whitespace_case_and_contact_order(self):
        state = state_copy()
        character = state['last_end']['characters']['Pip']
        character['pose'] = ' UPRIGHT-OVERHEAD-GRIP '
        character['contacts'].reverse()
        self.assertEqual(errors_for(with_state(GOLDEN, state)), [])
        # A custom character name must not be confused with the reserved prop field.
        self.assertEqual(errors_for(GOLDEN.replace('Pip', 'prop')), [])

    def test_loop_state_mismatch_per_physical_dimension(self):
        changes = {'position': [31, 65], 'facing': 'left', 'pose': 'arms-at-sides', 'contacts': ['feet:floor'],
                   'velocity': [0.5, 0], 'phase': 'moving-down', 'secondary_motion': 'tail-swing-peak'}
        for key, value in changes.items():
            state = state_copy()
            state['last_end']['characters']['Pip'][key] = value
            with self.subTest(key=key):
                self.assertIn('LOOP_STATE_MISMATCH', '\n'.join(errors_for(with_state(GOLDEN, state))))
        for key, value in (('shape', 'oval'), ('contacts', []), ('position', [50, 79])):
            state = state_copy()
            state['last_end']['prop'][key] = value
            self.assertIn('LOOP_STATE_MISMATCH', '\n'.join(errors_for(with_state(GOLDEN, state))))

    def test_compiler_preserves_state_and_allows_return_motion(self):
        self.assertIn('prop x=50%, y=79%', PROMPTS.split('### Shot 4')[1])
        self.assertEqual(errors_for(prompts=PROMPTS), [])  # Last start differs from the loop endpoint.
        state = state_copy()
        for frame in state.values():
            frame['characters']['Pip']['phase'] = 'moving-up'
            frame['characters']['Pip']['velocity'] = [0, -0.5]
        self.assertEqual(errors_for(with_state(GOLDEN, state), with_state(PROMPTS, state)), [])
        self.assertIn('LOOP_STATE_MISMATCH', '\n'.join(errors_for(prompts=with_state(PROMPTS, state))))
        final = PROMPTS.rsplit('The existing upward tension restores Pip', 1)
        final[1] = final[1].replace('and the ball to the opening high position', 'and the ball to the opening high position; Pip takes a step away from the compressed stance and returns to the opening mark before Hold', 1)
        self.assertEqual(errors_for(prompts='The existing upward tension restores Pip'.join(final)), [])

    def test_first_frame_coordinates_must_match_declared_loop_start(self):
        state = state_copy()
        for frame in state.values():
            frame['characters']['Pip']['position'][0] = 31
        self.assertIn('LOOP_STATE_MISMATCH', '\n'.join(errors_for(with_state(GOLDEN, state), with_state(PROMPTS, state))))

    def test_emotion_does_not_truncate_existing_teaching_text(self):
        changed = GOLDEN.replace('t=0.75–1.15s Pip: High! |', 't=0.75–1.15s Pip: High!<br>t=1.6–1.9s Toby: Oops! |', 1)
        changed = changed.replace('t=1–1.5s Pip: Oops!（唯一 Level-0 情绪锚点，不配花字）', '无')
        self.assertEqual(errors_for(changed), [])

    def test_builtin_preset_dictionary_matches_skill(self):
        skill = (ROOT / 'plugins/narrative-studio/skills/ai-prompt-generator/SKILL.md').read_text()
        for role, anchor in validator.PRESETS.items():
            self.assertIn(f'| {role} | {anchor} |', skill)


if __name__ == '__main__':
    unittest.main()
