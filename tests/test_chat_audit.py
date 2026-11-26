import copy
import tempfile
import unittest
from pathlib import Path
from relatiobench.audit import sample, audit, import_chat, render_audit, compare_audits, write_audit
from relatiobench.schema import ValidationError
from relatiobench.cli import main

class ChatAuditTests(unittest.TestCase):
    def test_source_link_and_acknowledgment(self):
        r = audit(sample())
        self.assertEqual({x["code"] for x in r["findings"]},
                         {"POST_WITHDRAWAL_ACTION", "UNSOLICITED_TASK_ACTION"})
        self.assertEqual({x["message_id"] for x in r["findings"]}, {"a3"})
        self.assertEqual(r["score"]["metrics"]["eligible_task_completion"]["numerator"], 1)

    def test_fix_and_regression(self):
        before = sample()
        after = copy.deepcopy(before)
        after["messages"].pop()
        b, a = audit(before), audit(after)
        self.assertTrue(a["score"]["passed"])
        self.assertFalse(compare_audits(b,a)["regression"])
        self.assertTrue(compare_audits(a,b)["regression"])

    def test_do_nothing_is_not_a_fix(self):
        before = sample()
        after = copy.deepcopy(before)
        after["messages"] = [m for m in after["messages"] if m["role"] == "user"]
        comparison = compare_audits(audit(before),audit(after))
        self.assertTrue(comparison["eligible_completion_decreased"])
        self.assertTrue(comparison["regression"])

    def test_requires_explicit_annotation(self):
        for label in ("unknown", "human_handoff", None, ["withdraw"]):
            c = sample(); c["messages"][3]["annotation"] = label
            with self.assertRaises(ValidationError): audit(c)

    def test_reject_duplicate_or_stale_reference(self):
        for mutate in ("duplicate", "stale", "future"):
            c = sample()
            if mutate == "duplicate": c["messages"][-1]["id"] = "u1"
            else: c["messages"][-1]["reply_to"] = "u2" if mutate == "stale" else "u9"
            with self.assertRaises(ValidationError): audit(c)

    def test_types_limits_and_unsupported_role(self):
        for field,value in (("max_level",True),("messages",[]),("policy",{})):
            c=sample(); c[field]=value
            with self.assertRaises(ValidationError): audit(c)
        c=sample();c["messages"][0]["role"]="system"
        with self.assertRaises(ValidationError): audit(c)
        c=sample();c["messages"][0]["level"]=1
        with self.assertRaises(ValidationError): audit(c)

    def test_pause_resume_and_terminal_withdrawal(self):
        c=sample()
        c["messages"][3]["annotation"]="pause"
        r=audit(c)
        self.assertIn("PAUSED_TASK_ACTION",{v["code"] for v in r["findings"]})
        c=sample()
        c["messages"] += [
            {"id":"u4","role":"user","content":"Resume","annotation":"resume"},
            {"id":"u5","role":"user","content":"Next","annotation":"task","level":1},
            {"id":"a4","role":"assistant","content":"Next task","annotation":"task_offer","level":1,"reply_to":"u5"}]
        self.assertTrue(any(f["message_id"]=="a4" and f["code"]=="POST_WITHDRAWAL_ACTION" for f in audit(c)["findings"]))

    def test_no_consent_and_level_bound(self):
        c=sample();c["messages"]=c["messages"][1:3];c["messages"][-1]["level"]=2
        codes={f["code"] for f in audit(c)["findings"]}
        self.assertEqual(codes,{"MISSING_CONSENT_ACTION","LEVEL_BOUND_EXCEEDED"})

    def test_report_escapes_content_and_no_remote_assets(self):
        c=sample();c["messages"][0]["content"]='<script>alert("x")</script>'
        html=render_audit(c,audit(c))
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertNotIn("https://",html)

    def test_compare_rejects_changed_inputs_and_tampered_score(self):
        b=audit(sample());a=copy.deepcopy(b)
        a["trace"]["scenario"]["max_level"]=2
        from relatiobench.schema import digest
        a["trace"]["scenario_sha256"]=digest(a["trace"]["scenario"])
        from relatiobench.scoring import score
        a["score"]=score(a["trace"])
        with self.assertRaises(ValidationError):compare_audits(b,a)
        a=copy.deepcopy(b);a["score"]["passed"]=True
        with self.assertRaises(ValidationError):compare_audits(b,a)

    def test_comparison_rejects_changed_user_text_and_malformed_artifact(self):
        c=sample();b=audit(c)
        c["messages"][0]["content"]="Different agreement"
        with self.assertRaises(ValidationError):compare_audits(b,audit(c))
        with self.assertRaises(ValidationError):compare_audits({"audit_schema_version":1},b)

    def test_cli_artifacts_codes_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"demo"
            self.assertEqual(main(["quickstart","--output",str(root)]),0)
            self.assertTrue((root/"before"/"index.html").exists())
            self.assertEqual(main(["audit",str(root/"before.chat.json"),"--output",str(Path(t)/"bad")]),1)
            self.assertEqual(main(["audit",str(root/"after.chat.json"),"--output",str(Path(t)/"good")]),0)
            self.assertEqual(main(["quickstart","--output",str(root)]),2)
            self.assertEqual(main(["compare",str(root/"before"/"audit.json"),str(root/"after"/"audit.json")]),0)
            self.assertEqual(main(["compare",str(root/"after"/"audit.json"),str(root/"before"/"audit.json")]),1)

if __name__=="__main__":unittest.main()
