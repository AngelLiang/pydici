# coding:utf-8
"""
Staffing form setup
@author: Sébastien Renard <Sebastien.Renard@digitalfox.org>
@license: GPL v3 or newer
"""

from django import forms
from django.forms.models import BaseInlineFormSet

from ajax_select.fields import AutoCompleteSelectField

from pydici.staffing.models import Staffing

class ConsultantStaffingInlineFormset(BaseInlineFormSet):
    """Custom inline formset used to override fields"""
    def add_fields(self, form, index):
        """that adds the field in, overwriting the previous default field"""
        super(ConsultantStaffingInlineFormset, self).add_fields(form, index)
        form.fields["mission"] = AutoCompleteSelectField('mission', required=True) # Ajax it
        form.fields["mission"].widget.attrs.setdefault("size", 8) # Reduce default size
        form.fields["staffing_date"].widget.attrs.setdefault("size", 10) # Reduce default size
        form.fields["charge"].widget.attrs.setdefault("size", 3) # Reduce default size

class MissionStaffingInlineFormset(BaseInlineFormSet):
    """Custom inline formset used to override fields"""
    def add_fields(self, form, index):
        """that adds the field in, overwriting the previous default field"""
        super(MissionStaffingInlineFormset, self).add_fields(form, index)
        form.fields["consultant"] = AutoCompleteSelectField('consultant', required=True) # Ajax it
        form.fields["consultant"].widget.attrs.setdefault("size", 8) # Reduce default size
        form.fields["staffing_date"].widget.attrs.setdefault("size", 10) # Reduce default size
        form.fields["charge"].widget.attrs.setdefault("size", 3) # Reduce default size


class TimesheetForm(forms.Form):
    """Consultant timesheet form"""
    def __init__(self, *args, **kwargs):
        days = kwargs.pop("days", None)
        missions = kwargs.pop("missions", None)
        forecastTotal = kwargs.pop("forecastTotal", [])
        timesheetTotal = kwargs.pop("timesheetTotal", [])
        super(TimesheetForm, self).__init__(*args, **kwargs)

        for mission in missions:
            for day in days:
                key = "charge_%s_%s" % (mission.id, day.day)
                self.fields[key] = forms.DecimalField(required=False, min_value=0, max_value=1, decimal_places=1)
                self.fields[key].widget.attrs.setdefault("size", 2) # Reduce default size
                if day.day == 1: # Only show label for first day
                    self.fields[key].label = unicode(mission)
                else:
                    self.fields[key].label = ""
            # Add staffing total and forecast in hidden field
            hwidget = forms.HiddenInput()
            # Mission id is added to ensure field key is uniq.
            key = "%s %s %s" % (timesheetTotal[mission.id], mission.id, forecastTotal[mission.id])
            self.fields[key] = forms.CharField(widget=hwidget, required=False)
