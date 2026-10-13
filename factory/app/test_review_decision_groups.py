import json, tempfile, unittest
from pathlib import Path
from review_decision_groups import build_decision_groups, record_group_decision, apply_group_decisions, revoke_group_decision

def item(review_id, ref="service-a", candidate="a", pixel="1", master="9", lane="ARTWORK_REVIEW", verified_context=None):
    return {"review_id":review_id,"decision":"PENDING","workstream":lane,"category":"REGISTRY_MATCH",
      "candidate_identity":ref,"verified_identity_context":verified_context,
      "reasons":["EXISTING_SERVICE_DIFFERENT_ART"] if lane=="ARTWORK_REVIEW" else ["UNVERIFIED_REGISTRY_ID"],
      "source_origins":["openatv8"],"source_origin":"openatv8","sha256":candidate*64,
      "artwork_review_units":[{"representative_sha256":candidate*64,"pixel_sha256":pixel*64,
       "master_pixel_sha256":[master*64],"master_pixel_comparison":"NO_PIXEL_EXACT_SAME_SERVICE_MASTER"}] if lane=="ARTWORK_REVIEW" else [],
      "variants":[{"sha256":candidate*64,"sources":["openatv8/schema-3/a.png"]}]}

class DecisionGroupsTests(unittest.TestCase):
 def test_one_task_is_one_group(self):
  result=build_decision_groups({"items":[item("WR-ONE")]})
  self.assertEqual(result["summary"]["active_technical_items"],1);self.assertEqual(result["summary"]["user_decision_groups"],1)
 def test_ten_exact_same_context_tasks_form_one_group(self):
  result=build_decision_groups({"items":[item("WR-%02d"%n) for n in range(10)]})
  self.assertEqual(result["summary"]["user_decision_groups"],1);self.assertEqual(result["summary"]["potential_decisions_saved"],9)
  self.assertEqual(result["groups"][0]["scope"],"ARTWORK_ONLY");self.assertEqual(result["groups"][0]["review_tasks"],10)
 def test_different_candidate_artworks_do_not_merge(self):
  first=item("WR-A");second=item("WR-B",pixel="2")
  result=build_decision_groups({"items":[first,second]})
  self.assertEqual(result["summary"]["user_decision_groups"],2)
 def test_same_logo_different_services_do_not_merge(self):
  result=build_decision_groups({"items":[item("WR-A",ref="service-a"),item("WR-B",ref="service-b")]})
  self.assertEqual(result["summary"]["user_decision_groups"],2)
 def test_verified_common_artwork_context_can_group_not_identity(self):
  art=build_decision_groups({"items":[item("WR-A",ref="service-a",verified_context="ctx"),item("WR-B",ref="service-b",verified_context="ctx")]})
  self.assertEqual(art["summary"]["user_decision_groups"],1);self.assertEqual(art["groups"][0]["scope"],"ARTWORK_ONLY")
  ids=build_decision_groups({"items":[item("WR-IA",ref="service-a",lane="IDENTITY_VERIFICATION"),item("WR-IB",ref="service-b",lane="IDENTITY_VERIFICATION")]})
  self.assertEqual(ids["summary"]["user_decision_groups"],2)
 def test_candidate_and_master_change_invalidates_group(self):
  original=[item("WR-A"),item("WR-B")];group=build_decision_groups({"items":original})["groups"][0]
  self.assertNotEqual(group["decision_group_id"],build_decision_groups({"items":[item("WR-A"),item("WR-B",pixel="2")]})["groups"][0]["decision_group_id"])
  self.assertNotEqual(group["decision_group_id"],build_decision_groups({"items":[item("WR-A"),item("WR-B",master="8")]})["groups"][0]["decision_group_id"])
 def test_group_decision_is_fixed_audited_and_revocable(self):
  with tempfile.TemporaryDirectory() as tmp:
   ledger=Path(tmp)/"decisions.json";queue={"items":[item("WR-A"),item("WR-B")]}
   group=build_decision_groups(queue)["groups"][0]
   with self.assertRaises(PermissionError):record_group_decision(ledger,group,"APPROVED_FOR_REVIEW","reviewed",False)
   entry=record_group_decision(ledger,group,"APPROVED_FOR_REVIEW","exact artwork",True)
   self.assertEqual(entry["member_review_ids"],["WR-A","WR-B"])
   self.assertTrue(all(i["decision"]=="APPROVED_FOR_REVIEW" for i in apply_group_decisions(queue,ledger)["items"]))
   changed={"items":[item("WR-A"),item("WR-B",master="8")]}
   self.assertTrue(all(i["decision"]=="PENDING" for i in apply_group_decisions(changed,ledger)["items"]))
   revoke_group_decision(ledger,group["decision_group_id"],operator_confirmation=True)
   saved=json.loads(ledger.read_text());self.assertEqual(saved["group_decisions"][group["decision_group_id"]]["status"],"REVOKED")
   self.assertEqual(len(saved["group_decisions"][group["decision_group_id"]]["history"]),1)
