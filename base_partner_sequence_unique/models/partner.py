# Copyright 2004-2009 Tiny SPRL (<http://tiny.be>).
# Copyright 2013 initOS GmbH & Co. KG (<http://www.initos.com>).
# Copyright 2016 Tecnativa - Vicent Cubells
# Copyright 2016 Camptocamp - Akim Juillerat (<http://www.camptocamp.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# from odoo import api, models
from odoo import api, fields, models


class ResPartner(models.Model):
    """Assigns 'ref' from a sequence on creation and copying"""

    _inherit = "res.partner"

    ref = fields.Char(copy=False, help="Non-duplicate numbers for all customers")

    _sql_constraints = [
        ("ref_uniq", "UNIQUE (ref)", "ref must be unique.  Please enter another code.",)
    ]

    def _get_next_ref(self, vals=None):
        return self.env["ir.sequence"].next_by_code("res.partner")

    @api.model
    def create(self, vals):
        if not vals.get("ref"):
            vals["ref"] = self._get_next_ref(vals=vals)
        return super(ResPartner, self).create(vals)

    def copy(self, default=None):
        default = default or {}
        default["ref"] = self._get_next_ref()
        return super(ResPartner, self).copy(default)

    def write(self, vals):
        for partner in self:
            partner_vals = vals.copy()
            if not partner_vals.get("ref") and not partner.ref:
                partner_vals["ref"] = partner._get_next_ref(vals=partner_vals)
            super(ResPartner, partner).write(partner_vals)
        return True
