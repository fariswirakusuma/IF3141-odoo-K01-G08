from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestPilarPo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base_group = cls.env.ref("base.group_user")
        sales_group = cls.env.ref("pilar_po.group_po_sales")
        director_group = cls.env.ref("pilar_po.group_po_director")

        cls.sales_user = cls.env["res.users"].create({
            "name": "Sales Uji",
            "login": "po_sales_test",
            "email": "po_sales_test@example.com",
            "groups_id": [(6, 0, [base_group.id, sales_group.id])],
        })
        cls.director_user = cls.env["res.users"].create({
            "name": "Director Uji",
            "login": "po_director_test",
            "email": "po_director_test@example.com",
            "groups_id": [(6, 0, [base_group.id, director_group.id])],
        })

        cls.customer = cls.env["pilar.customer"].create({
            "customer_name": "Pelanggan Uji",
            "customer_type": "mbg",
            "contact_name": "Kontak Uji",
            "contact_phone": "0800-0000-0000",
        })
        cls.po = cls.env["pilar.po"].create({
            "customer_id": cls.customer.id,
            "delivery_date": fields.Date.today() + timedelta(days=3),
            "delivery_address": "Jl. Uji No. 1, Bandung",
            "telegram_sender": "Admin Uji",
        })
        cls.env["pilar.po.item"].create({
            "po_id": cls.po.id,
            "commodity_name": "Beras Premium",
            "quantity": 10,
            "unit_name": "kg",
            "quality_specification": "Beras premium",
        })

    def _prepare_decision(self):
        self.po.action_start_check()
        self.po.action_validate()
        self.po.action_submit_decision()
        self.assertEqual(self.po.state, "menunggu_keputusan")

    def test_name_from_sequence(self):
        self.assertNotEqual(self.po.name, "New")
        self.assertTrue(self.po.name)

    def test_workflow_happy_path(self):
        self.assertEqual(self.po.state, "bukti_diterima")
        self.po.action_start_check()
        self.assertEqual(self.po.state, "dalam_pemeriksaan")

        self.po.action_validate()
        self.assertEqual(self.po.validation_result, "lolos")
        self.assertTrue(self.po.validation_ids)

        self.po.action_submit_decision()
        self.assertEqual(self.po.state, "menunggu_keputusan")

        self.po.with_user(self.director_user).action_approve()
        self.po.invalidate_recordset()
        self.assertEqual(self.po.state, "disahkan")
        decision = self.po.approval_ids.filtered(
            lambda item: item.decision_type == "setuju"
        )
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.user_id, self.director_user)
        self.assertTrue(self.po.audit_ids)

    def test_validation_blocks_incomplete_po(self):
        po = self.env["pilar.po"].create({"customer_id": self.customer.id})
        po.action_validate()
        self.assertEqual(po.validation_result, "bermasalah")
        self.assertIn("Alamat pengiriman", po.validation_message)

        with self.assertRaises(UserError):
            po.action_submit_decision()

    def test_return_and_resubmit_creates_new_version(self):
        self.po.action_start_check()
        original_version = self.po.current_version_id
        self.po.return_reason = "data_tidak_lengkap"
        self.po.return_note = "Lengkapi alamat pengiriman."
        self.po.action_return()
        self.assertEqual(self.po.state, "dikembalikan")

        self.po.action_resubmit()
        self.po.invalidate_recordset()
        self.assertEqual(self.po.state, "dalam_pemeriksaan")
        self.assertEqual(
            self.po.current_version_id.version_number,
            original_version.version_number + 1,
        )
        self.assertEqual(len(self.po.current_version_id.item_ids), 1)

    def test_only_director_can_approve(self):
        self._prepare_decision()
        with self.assertRaises(UserError):
            self.po.with_user(self.sales_user).action_approve()

    def test_sales_cannot_unlink_po(self):
        with self.assertRaises(AccessError):
            self.po.with_user(self.sales_user).unlink()

    def _approve(self):
        self._prepare_decision()
        self.po.with_user(self.director_user).action_approve()
        self.po.invalidate_recordset()
        self.assertEqual(self.po.state, "disahkan")

    def test_change_after_approval_creates_new_version(self):
        self._approve()
        original_version = self.po.current_version_id
        self.po.change_reason = "Pelanggan menambah 5 kg beras."
        self.po.with_user(self.sales_user).action_request_change()
        self.po.invalidate_recordset()

        self.assertEqual(self.po.state, "dalam_pemeriksaan")
        self.assertEqual(
            self.po.current_version_id.version_number,
            original_version.version_number + 1,
        )
        self.assertTrue(original_version.exists())
        self.assertIn(original_version, self.po.version_ids)
        self.assertFalse(original_version.is_current)
        self.assertEqual(len(self.po.current_version_id.item_ids), 1)
        self.assertFalse(self.po.change_reason)
        self.assertEqual(self.po.validation_result, "pending")
        with self.assertRaises(UserError):
            self.po.action_submit_decision()
        self.assertTrue(self.po.audit_ids.filtered(
            lambda log: log.action_type == "Perubahan pesanan pada PO sah"
        ))

    def test_change_requires_approved_state_and_reason(self):
        self.po.change_reason = "Perubahan sebelum disahkan."
        with self.assertRaises(UserError):
            self.po.action_request_change()

        self._approve()
        self.po.change_reason = False
        with self.assertRaises(UserError):
            self.po.action_request_change()
        self.assertEqual(self.po.state, "disahkan")

    def test_director_can_cancel_approved_po(self):
        self._approve()
        self.po.cancel_reason = "Pelanggan membatalkan pesanan."
        self.po.with_user(self.director_user).action_cancel()
        self.po.invalidate_recordset()
        self.assertEqual(self.po.state, "dibatalkan")
        self.assertTrue(self.po.approval_ids.filtered(
            lambda item: item.decision_type == "batal"
        ))

    def test_sales_cannot_cancel_approved_po(self):
        self._approve()
        self.po.cancel_reason = "Pelanggan membatalkan pesanan."
        with self.assertRaises(UserError):
            self.po.with_user(self.sales_user).action_cancel()
        self.po.invalidate_recordset()
        self.assertEqual(self.po.state, "disahkan")
