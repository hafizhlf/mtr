from datetime import datetime, timedelta
import logging
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from collections import OrderedDict

class ir_sequence(models.Model):
    _inherit = 'ir.sequence'

    def write_roman(self,num):

        roman = OrderedDict()
        roman[1000] = "M"
        roman[900] = "CM"
        roman[500] = "D"
        roman[400] = "CD"
        roman[100] = "C"
        roman[90] = "XC"
        roman[50] = "L"
        roman[40] = "XL"
        roman[10] = "X"
        roman[9] = "IX"
        roman[5] = "V"
        roman[4] = "IV"
        roman[1] = "I"

        def roman_num(num):
            for r in roman.keys():
                x, y = divmod(num, r)
                yield roman[r] * x
                num -= (r * x)
                if num > 0:
                    roman_num(num)
                else:
                    break

        return "".join([a for a in roman_num(num)])
    
    # def get_next_char(self, number_next):
    def _get_prefix_suffix(self):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(pytz.timezone(self._context.get('tz') or 'UTC'))
            # convert datetime to string
            now2 = now.strftime('%Y-%m-%d')
            if self._context.get('ir_sequence_date'):
                # effective_date = datetime.strptime(self._context.get('ir_sequence_date'), '%Y-%m-%d')
                effective_date = datetime.strptime(now2, '%Y-%m-%d')
            if self._context.get('ir_sequence_date_range'):
                # range_date = datetime.strptime(self._context.get('ir_sequence_date_range'), '%Y-%m-%d')
                range_date = datetime.strptime(now2, '%Y-%m-%d')

            sequences = {
                            'year': '%Y', 'month': '%m', 'day': '%d', 
            'y': '%y', 'doy': '%j', 'woy': '%W',
                            'weekday': '%w', 'h24': '%H', 'h12': '%I', 
            'min': '%M', 'sec': '%S',
                            #Additional dict for roman
                            'rom_year': '%Y', 'rom_month': '%m', 
            'rom_y': '%y', 'rom_day': '%d'
                        }
            res = {}
            for key, format in sequences.items():
                if "rom_" in key:  
                    #Convert to Roman
                    res[key] = self.write_roman(int(effective_date.strftime(format)))
                    res['range_' + key] = self.write_roman(int(range_date.strftime(format)))
                    res['current_' + key] = self.write_roman(int(now.strftime(format)))
                else:
                    res[key] = effective_date.strftime(format)
                    res['range_' + key] = range_date.strftime(format)
                    res['current_' + key] = now.strftime(format)
            return res
            
        d = _interpolation_dict()
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence \'%s\'') % (self.get('name')))
        # return interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix
        return interpolated_prefix, interpolated_suffix