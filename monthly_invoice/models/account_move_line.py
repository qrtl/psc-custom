import datetime

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    monthly_partner_id = fields.Many2one(
        "res.partner", string="Partner Monthly", ondelete="restrict"
    )

    def _get_order_data(self, field_name):
        try:
            if field_name == "scheduled_date":
                delivery = self.env["stock.picking"].search(
                    [
                        ("origin", "=", self.move_id[0].invoice_origin),
                        ("state", "!=", "cancel"),
                    ]
                )[0]
                return delivery[field_name] + datetime.timedelta(days=1)

            sale_order = self.env["sale.order"].search(
                [("name", "=", self.move_id[0].invoice_origin)]
            )[0]
            return sale_order[field_name]

        except:
            return ""
