import datetime

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    monthly_partner_id = fields.Many2one(
        "res.partner", string="Partner Monthly", ondelete="restrict"
    )
    date_delivered = fields.Date(
        "Delivered Date",
        compute="_compute_date_delivered",
        help="Indicates the date on which the delivery is assumed to have been "
        "received by the customer.",
    )

    def _compute_date_delivered(self):
        for line in self:
            if line.sale_line_ids:
                group = line.sale_line_ids[0].order_id.procurement_group_id
                if group:
                    pick = self.env["stock.picking"].search(
                        [("group_id", "=", group.id), ("state", "=", "done")]
                    )[:1]
                    if pick:
                        line.date_delivered = fields.Date.to_date(
                            fields.Datetime.context_timestamp(
                                self, pick.scheduled_date + datetime.timedelta(days=1)
                            )
                        )
            # If corresponding picking is not found, set date_delivered with the invoice
            # date (a tentative arrangement).
            if not line.date_delivered:
                line.date_delivered = line.move_id.invoice_date

    def _get_order_data(self, field_name):
        self.ensure_one()
        try:
            sale_order = self.env["sale.order"].search(
                [("name", "=", self.move_id[0].invoice_origin)]
            )[0]
            return sale_order[field_name]
        except Exception:
            return ""
