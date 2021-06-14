# Copyright 2021 Quartile Limited
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    phone = fields.Char()
