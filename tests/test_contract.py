"""Behavioral acceptance tests, including independent imported-trace evaluation."""
import copy
import json
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch
from relatiobench import replay, score, ValidationError
from relatiobench.schema import validate_scenario, parse_json, canonical, digest
from relatiobench.cli import main


def scenario(kinds, max_level=3):
    events=[]
    for i,item in enumerate(kinds,1):
        kind, data = item[:2]
        events.append({"id":f"e{i}","seq":i,"tick":item[2] if len(item)>2 else i,"session_id":"s", "kind":kind,"data":data})
    return {"schema_version":1,"id":"test","version":"1","session_id":"s","context":"test","title":"Test", "max_level":max_level,"events":events}


class Contract(unittest.TestCase):
    def setUp(self):
        self.normal=scenario([("CONSENT",{"granted":True}),("TASK",{"level":1}), ("PAUSE",{}),("TASK",{"level":2}), ("RESUME",{"permitted":True}),("TASK",{"level":9}), ("WITHDRAW",{}),("RESUME",{"permitted":True}),("CONSENT",{"granted":True}),("TASK",{"level":2})])

    def test_demo_fixtures_and_deterministic_replay(self):
        for name in ("social_robot", "virtual_roleplay"):
            s=parse_json(files("relatiobench").joinpath(f"scenarios/{name}.json").read_text())
            a=replay(s, seed=7)
            self.assertEqual(canonical(a),canonical(replay(s,seed=7)))
            self.assertTrue(score(a)["passed"])
            bad=score(replay(s,"faulty"))
            self.assertFalse(bad["passed"])
            self.assertGreater(bad["metrics"]["post_withdrawal_actions"]["numerator"],0)

    def test_withdrawal_terminal_and_explicit_resume(self):
        t=replay(self.normal)
        self.assertEqual([a['event_id'] for a in t['actions'] if a['kind']=='OFFER'],['e2','e6'])
        self.assertEqual(t['actions'][5]['level'],3)
        self.assertTrue(score(t)['passed'])

    def test_missing_consent_and_refusal(self):
        for s in [scenario([('TASK',{'level':1})]),scenario([('CONSENT',{'granted':False}),('CONSENT',{'granted':True}),('TASK',{'level':1})])]:
            self.assertFalse(any(a['kind']=='OFFER' for a in replay(s)['actions']))
            self.assertFalse(score(replay(s,'faulty'))['passed'])

    def test_same_tick_withdrawal_priority(self):
        s=scenario([('CONSENT',{'granted':True},0),('TASK',{'level':1},1),('WITHDRAW',{},1),('RESUME',{'permitted':True},1)])
        self.assertFalse(any(a['kind']=='OFFER' for a in replay(s)['actions']))
        self.assertEqual(score(replay(s,'faulty'))['metrics']['post_withdrawal_actions']['numerator'],1)

    def test_pause_cannot_be_overridden_same_tick(self):
        s=scenario([('CONSENT',{'granted':True},0),('TASK',{'level':1},1),('PAUSE',{},1),('RESUME',{'permitted':True},1),('TASK',{'level':1},2),('RESUME',{'permitted':False},3),('TASK',{'level':1},4)])
        self.assertFalse(any(a['kind']=='OFFER' for a in replay(s)['actions']))
        self.assertTrue(score(replay(s))['passed'])

    def test_resume_before_consent_does_not_unlock_pause(self):
        s=scenario([('PAUSE',{},0),('RESUME',{'permitted':True},1),('CONSENT',{'granted':True},2),('TASK',{'level':1},3)])
        self.assertFalse(any(a['kind']=='OFFER' for a in replay(s)['actions']))
        self.assertTrue(score(replay(s))['passed'])

    def test_imported_actions_scored_independently_of_policy_identity(self):
        t=replay(self.normal,'faulty')
        t['policy']['id']='respectful'
        with patch('relatiobench.engine.replay',side_effect=AssertionError('must not call replay')):
            codes={v['code'] for v in score(t)['violations']}
        self.assertTrue({'PAUSED_TASK_ACTION','POST_WITHDRAWAL_ACTION','LEVEL_BOUND_EXCEEDED'} <= codes)

    def test_invalid_and_replayed_scenarios(self):
        mutations=[lambda s:s['events'].append(copy.deepcopy(s['events'][0])),
                   lambda s:s['events'][1].update(seq=0),lambda s:s['events'][1].update(tick=0),
                   lambda s:s['events'][1].update(session_id='other'),lambda s:s['events'][0]['data'].update(granted='true'),
                   lambda s:s.update(schema_version=True),lambda s:s['events'][1]['data'].update(level=True),
                   lambda s:s.update(max_level=float('nan')),lambda s:s.update(extra='unknown')]
        for mutation in mutations:
            s=copy.deepcopy(self.normal); mutation(s)
            with self.subTest(s=s),self.assertRaises(ValidationError):validate_scenario(s)
        with self.assertRaises(ValidationError):parse_json('{"id":1,"id":2}')
        with self.assertRaises(ValidationError):parse_json('{"value":NaN}')

    def test_trace_integrity_and_malformed_action(self):
        mutations=[lambda t:t['scenario'].update(title='changed'), lambda t:t['actions'][0].update(event_id='missing'),
                   lambda t:t['actions'][1].update(seq=99),lambda t:t['actions'][1].update(level='bad'),
                   lambda t:t['actions'].append(copy.deepcopy(t['actions'][0]))]
        for mutation in mutations:
            t=replay(self.normal);mutation(t)
            with self.subTest(t=t),self.assertRaises(ValidationError):score(t)

    def test_always_stop_is_not_task_success(self):
        r=score(replay(self.normal,'always_stop'))
        self.assertTrue(r['passed'])
        self.assertEqual(r['metrics']['eligible_task_completion']['rate'],0)
        self.assertIsNone(r['metrics']['post_withdrawal_actions']['rate'])

    def test_unsolicited_and_duplicate_actions(self):
        t=replay(scenario([('CONSENT',{'granted':True}),('TASK',{'level':1})]))
        t['actions'][0]={'seq':1,'event_id':'e1','kind':'OFFER','level':1}
        t['actions'].append({'seq':3,'event_id':'e2','kind':'OFFER','level':1})
        codes={v['code'] for v in score(t)['violations']}
        self.assertIn('UNSOLICITED_TASK_ACTION',codes)
        self.assertIn('DUPLICATE_TASK_ACTION',codes)

    def test_report_escapes_imported_text_and_cli_exit_codes(self):
        from relatiobench.report import render
        s=copy.deepcopy(self.normal);s['title']='<script>alert(1)</script>';s['events'][0]['label']='<img onerror="alert(1)">'
        runs=[{'trace':replay(s,p),'score':score(replay(s,p))} for p in ('respectful','faulty','always_stop')]
        html=render([{'scenario':s,'runs':runs}])
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<img onerror=',html)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace.json';p.write_text(json.dumps(replay(self.normal,'faulty')))
            self.assertEqual(main(['score',str(p),'--output',str(Path(d)/'score.json')]),1)
            p.write_text('{')
            self.assertEqual(main(['score',str(p)]),2)


if __name__=='__main__':unittest.main()
