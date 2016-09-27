# -*- coding: utf-8 -*-

"""
Has the filter that allows to filter by price range.
"""

from django import forms
from django.contrib import admin
from django.db import models
from django.utils.translation import ugettext as _

# TODO is it necessary?
from django.contrib.admin.widgets import AdminIntegerFieldWidget

try:
    from django.utils.html import format_html
except ImportError:
    from django.utils.html import conditional_escape, mark_safe

    def format_html(format_string, *args, **kwargs):
        args_safe = map(conditional_escape, args)
        kwargs_safe = dict((k, conditional_escape(v)) for (k, v) in kwargs.items())
        return mark_safe(format_string.format(*args_safe, **kwargs_safe))


# Django doesn't deal well with filter params that look like queryset lookups.
FILTER_PREFIX = 'prf__'


def clean_input_prefix(input_):
    return dict((key.split(FILTER_PREFIX)[1] if key.startswith(FILTER_PREFIX) else key, val)
                for (key, val) in input_.items())


class PriceRangeFilterBaseForm(forms.Form):
    def __init__(self, request, *args, **kwargs):
        super(PriceRangeFilterBaseForm, self).__init__(*args, **kwargs)
        self.request = request


class PriceRangeForm(PriceRangeFilterBaseForm):

    def __init__(self, *args, **kwargs):
        field_name = kwargs.pop('field_name')
        super(PriceRangeForm, self).__init__(*args, **kwargs)

        self.fields['%s%s__gte' % (FILTER_PREFIX, field_name)] = forms.FloatField(
            label='',
            widget=AdminIntegerFieldWidget(
                attrs={'placeholder': _('From')}
            ),
            localize=True,
            required=False
        )

        self.fields['%s%s__lte' % (FILTER_PREFIX, field_name)] = forms.FloatField(
            label='',
            widget=AdminIntegerFieldWidget(
                attrs={'placeholder': _('To')}
            ),
            localize=True,
            required=False,
        )


class PriceRangeFilter(admin.filters.FieldListFilter):
    template = 'price_range_filter/filter.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_since = '%s%s__gte' % (FILTER_PREFIX, field_path)
        self.lookup_kwarg_upto = '%s%s__lte' % (FILTER_PREFIX, field_path)
        super(PriceRangeFilter, self).__init__(
            field, request, params, model, model_admin, field_path)
        self.form = self.get_form(request)

    def choices(self, cl):
        """
        Pop the original parameters, and return the price filter & other filter
        parameters.
        """

        cl.params.pop(self.lookup_kwarg_since, None)
        cl.params.pop(self.lookup_kwarg_upto, None)
        return ({
            'get_query': cl.params,
        }, )

    def expected_parameters(self):
        return [self.lookup_kwarg_since, self.lookup_kwarg_upto]

    def get_form(self, request):
        return PriceRangeForm(request, data=self.used_parameters,
                             field_name=self.field_path)

    def queryset(self, request, queryset):
        if self.form.is_valid():
            # get no null params
            filter_params = clean_input_prefix(dict(filter(lambda x: bool(x[1]), self.form.cleaned_data.items())))

            lookup_since = self.lookup_kwarg_since.lstrip(FILTER_PREFIX)
            if filter_params.get(lookup_since) is not None:
                lookup_kwarg_since_value = int(filter_params.pop(lookup_since) * 100)
                filter_params['%s__gte' % self.field_path] = lookup_kwarg_since_value

            lookup_upto = self.lookup_kwarg_upto.lstrip(FILTER_PREFIX)
            if filter_params.get(lookup_upto) is not None:
                lookup_kwarg_upto_value = int(filter_params.pop(lookup_upto) * 100)
                # filter by upto included
                filter_params['%s__lte' % self.field_path] = lookup_kwarg_upto_value

            return queryset.filter(**filter_params)
        else:
            return queryset

# register the filters
admin.filters.FieldListFilter.register(
    lambda f: isinstance(f, models.FloatField), PriceRangeFilter)
