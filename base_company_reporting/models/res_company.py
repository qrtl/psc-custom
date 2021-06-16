# Copyright 2020 Quartile Limited
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    remit_to_info = fields.Text(
        "Remit-to Information",
        help="Remit-to information that should show in the reports when set. "
        "To reset the value, please update the source and translations strings "
        "of the translation record.",
        translate=True,
        sanitize=False,
    )

    contact_team = fields.Char("contact_team", translate=True,)
