"""
Reusable Django-admin sidebar filters shared across apps.

Two problems these solve:

* Foreign-key list filters render *every* related row in the sidebar. With
  regions/zones/territories spread over several companies that becomes an
  unusable wall of links, so `related_search_filter()` swaps the list for a
  small text box.
* `date_hierarchy` (and the `__date` lookup) compile to MySQL CONVERT_TZ(),
  which fails on servers without the timezone tables loaded. `DateRangeFilter`
  computes day boundaries in Python instead, and adds Today / This week /
  This month shortcuts.
"""

import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.filters import ListFilter
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.functional import cached_property

TEXT_INPUT_TEMPLATE = 'admin/filters/filter_text_input.html'
DATE_RANGE_TEMPLATE = 'admin/filters/filter_date_range.html'


class TextInputFilter(admin.SimpleListFilter):
    """
    Base for free-text sidebar filters: renders a text box instead of a
    dropdown, so it stays usable with thousands of distinct values.

    Subclasses set `title`, `parameter_name` and implement `filter_queryset`.
    """

    template = TEXT_INPUT_TEMPLATE
    input_placeholder = ''
    # Set by related_search_filter(); enables type-ahead on this box. The
    # admin site only suggests for fields a filter actually declares here,
    # so the endpoint can't be used to read arbitrary columns.
    suggest_field = None

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        self._get_items = list(request.GET.lists())
        self.suggest_app = model._meta.app_label
        self.suggest_model = model._meta.model_name

    @property
    def other_get_items(self):
        skip = {self.parameter_name, 'p'}
        return [(k, v) for k, v in self._get_items if k not in skip]

    def lookups(self, request, model_admin):
        return ()

    def has_output(self):
        return True

    def choices(self, changelist):
        # The template renders its own input; suppress Django's All/Any list.
        return []

    def filter_queryset(self, queryset, value):
        raise NotImplementedError

    def queryset(self, request, queryset):
        value = (self.value() or '').strip()
        if not value:
            return queryset
        return self.filter_queryset(queryset, value)


def related_search_filter(field_path, title, placeholder='', parameter_name=None):
    """
    Build a text-box filter for a (possibly related) field.

    e.g. related_search_filter('region_fk__name', 'region') replaces the
    full-list "By region fk" dropdown with a search box.
    """
    param = parameter_name or (field_path.split('__')[0] + '_q')

    def filter_queryset(self, queryset, value):
        return queryset.filter(**{f'{field_path}__icontains': value})

    return type(
        f'{field_path.title().replace("_", "").replace("__", "")}SearchFilter',
        (TextInputFilter,),
        {
            'title': title,
            'parameter_name': param,
            'input_placeholder': placeholder or f'search {title}',
            'filter_queryset': filter_queryset,
            'suggest_field': field_path,
        },
    )


class RelatedValuesFilter(TextInputFilter):
    """
    Best-of-both filter for region / zone / territory style columns.

    A plain FK list filter renders every related row (all regions of every
    company), which is unusable. This lists only the values that actually
    occur in *this* table, with row counts:

      * few distinct values  -> a dropdown you can just browse
      * many distinct values -> the text box + type-ahead

    Subclasses set `field_path` (e.g. 'region_fk__name') and `title`.
    """

    template = 'admin/filters/filter_related_values.html'
    field_path = None
    # A <select> collapses to a single line however many options it holds (and
    # browsers let you type to jump), unlike Django's default filter which
    # renders one inline <a> per value. So this can be generous; beyond it we
    # fall back to the type-ahead search box.
    max_choices = 300
    # Sentinel for "this column is empty" - lets an admin find incomplete
    # records, which a plain value list can never surface.
    NONE_SENTINEL = '__none__'
    none_label = '(not set)'

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        self._request = request
        self._model_admin = model_admin

    def _resolve_related(self):
        """('region_fk__name') -> (Region model, 'name'). (None, None) if N/A."""
        parts = (self.field_path or '').split('__')
        if len(parts) < 2:
            return None, None
        try:
            field = self._model_admin.model._meta.get_field(parts[0])
            return field.related_model, '__'.join(parts[1:])
        except Exception:
            return None, None

    @staticmethod
    def _assignment_attr(related_model):
        """The SalesStaffProfile M2M that assigns this model to a user."""
        try:
            from accounts.models import SalesStaffProfile
            for field in SalesStaffProfile._meta.many_to_many:
                if field.related_model is related_model:
                    return field.name
        except Exception:
            pass
        return None

    @cached_property
    def scope_values(self):
        """
        The values this user is allowed to filter by: the regions / zones /
        territories assigned to their sales profile. Superusers - and staff
        with no assignment - get the full list. None means "couldn't scope",
        and the caller falls back to values present in the table.
        """
        related_model, value_field = self._resolve_related()
        if related_model is None:
            return None

        user = getattr(self._request, 'user', None)
        assigned = None
        if user is not None and not getattr(user, 'is_superuser', False):
            profile = getattr(user, 'sales_profile', None)
            attr = self._assignment_attr(related_model)
            if profile is not None and attr:
                candidate = getattr(profile, attr).all()
                if candidate.exists():
                    assigned = candidate

        queryset = assigned if assigned is not None else related_model.objects.all()
        try:
            return list(
                queryset.exclude(**{f'{value_field}__isnull': True})
                        .exclude(**{f'{value_field}__exact': ''})
                        .values_list(value_field, flat=True)
                        .distinct()
                        .order_by(value_field)[: self.max_choices + 1]
            )
        except Exception:
            return None

    @cached_property
    def available_choices(self):
        """
        [(value, row_count)] to offer in the sidebar.

        Values come from the user's assigned hierarchy, so an admin can filter
        by any area they own - including ones with no records yet (count 0).
        """
        if not self.field_path:
            return []
        try:
            queryset = self._model_admin.get_queryset(self._request)
            used = {
                row[self.field_path]: row['_n']
                for row in (
                    queryset
                    .exclude(**{f'{self.field_path}__isnull': True})
                    .exclude(**{f'{self.field_path}__exact': ''})
                    .values(self.field_path)
                    .annotate(_n=Count('pk'))
                )
            }
        except Exception:
            used = {}

        scope = self.scope_values
        if scope is None:
            # Couldn't resolve the assignment - fall back to values in use.
            return sorted(used.items())

        choices = [(value, used.get(value, 0)) for value in scope]
        # Anything present in the data but outside the user's assignment is
        # still shown, otherwise those rows would be unfilterable.
        for value, count in sorted(used.items()):
            if value not in scope:
                choices.append((value, count))
        return choices

    @cached_property
    def none_count(self):
        """How many rows have this column empty/unset."""
        if not self.field_path:
            return 0
        try:
            queryset = self._model_admin.get_queryset(self._request)
            return queryset.filter(
                Q(**{f'{self.field_path}__isnull': True}) |
                Q(**{f'{self.field_path}__exact': ''})
            ).count()
        except Exception:
            return 0

    @property
    def use_dropdown(self):
        return 0 < len(self.available_choices) <= self.max_choices

    @property
    def choice_rows(self):
        """Rows for the template, flagging the selected one."""
        current = (self.value() or '').strip()
        rows = [
            {'value': value, 'count': count, 'selected': value == current}
            for value, count in self.available_choices
        ]
        # Offer "(not set)" only when such rows exist, so it never adds noise.
        if self.none_count:
            rows.append({
                'value': self.NONE_SENTINEL,
                'label': self.none_label,
                'count': self.none_count,
                'selected': current == self.NONE_SENTINEL,
            })
        return rows

    def filter_queryset(self, queryset, value):
        if value == self.NONE_SENTINEL:
            return queryset.filter(
                Q(**{f'{self.field_path}__isnull': True}) |
                Q(**{f'{self.field_path}__exact': ''})
            )
        # Exact match when the value came from the dropdown, so "North" doesn't
        # also drag in "North East"; substring match for free-typed text.
        known = {choice for choice, _count in self.available_choices}
        lookup = 'exact' if value in known else 'icontains'
        return queryset.filter(**{f'{self.field_path}__{lookup}': value})


def related_values_filter(field_path, title, max_choices=None, parameter_name=None):
    """Build a RelatedValuesFilter bound to a specific related field."""
    return type(
        f'{field_path.title().replace("_", "")}ValuesFilter',
        (RelatedValuesFilter,),
        {
            'title': title,
            'parameter_name': parameter_name or (field_path.split('__')[0] + '_q'),
            'input_placeholder': f'search {title}',
            'field_path': field_path,
            'suggest_field': field_path,
            # None -> inherit RelatedValuesFilter.max_choices
            **({'max_choices': max_choices} if max_choices is not None else {}),
        },
    )


class DateRangeFilter(ListFilter):
    """
    From/To date pickers plus Today / This week / This month shortcuts.

    Works for both DateField and DateTimeField. Boundaries are built in Python
    and compared with plain >= / <, so no timezone conversion happens in SQL
    (see the module docstring for why that matters).

    Subclasses set `field_name` (and usually `title`).
    """

    template = DATE_RANGE_TEMPLATE
    field_name = None
    title = 'date range'

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        if not self.field_name:
            raise ValueError('DateRangeFilter requires a field_name.')
        self.from_param = f'{self.field_name}_from'
        self.to_param = f'{self.field_name}_to'

        # DateTimeField subclasses DateField, so test the narrower type first.
        try:
            model_field = model._meta.get_field(self.field_name)
            self.is_datetime = isinstance(model_field, models.DateTimeField)
        except Exception:
            self.is_datetime = True

        # Claim our params so ChangeList doesn't treat them as ORM lookups.
        for param in self.expected_parameters():
            if param in params:
                value = params.pop(param)
                if isinstance(value, (list, tuple)):
                    value = value[-1] if value else ''
                self.used_parameters[param] = value
        self._get_items = list(request.GET.lists())

    def expected_parameters(self):
        return [self.from_param, self.to_param]

    @property
    def from_value(self):
        return self.used_parameters.get(self.from_param) or ''

    @property
    def to_value(self):
        return self.used_parameters.get(self.to_param) or ''

    @property
    def other_get_items(self):
        skip = {self.from_param, self.to_param, 'p'}
        return [(k, v) for k, v in self._get_items if k not in skip]

    @property
    def today(self):
        """Today's date - used as the inputs' max and by the presets."""
        return timezone.localdate().isoformat()

    def _preset_url(self, start, end):
        """Build a changelist URL for a preset range, keeping other filters."""
        pairs = [(k, v) for k, vlist in self.other_get_items for v in vlist]
        pairs.append((self.from_param, start.isoformat()))
        pairs.append((self.to_param, end.isoformat()))
        return '?' + urlencode(pairs)

    @property
    def presets(self):
        """Quick ranges: Today / This week / This month."""
        today = timezone.localdate()
        ranges = (
            ('Today', today, today),
            ('This week', today - datetime.timedelta(days=today.weekday()), today),
            ('This month', today.replace(day=1), today),
        )
        return [
            {
                'label': label,
                'url': self._preset_url(start, end),
                'active': (self.from_value == start.isoformat()
                           and self.to_value == end.isoformat()),
            }
            for label, start, end in ranges
        ]

    def has_output(self):
        return True

    def choices(self, changelist):
        # The template renders its own inputs.
        return []

    def _bound(self, day, end_of_day=False):
        """Turn a date into the right boundary type for the target field."""
        if end_of_day:
            day = day + datetime.timedelta(days=1)
        if not self.is_datetime:
            return day
        stamp = datetime.datetime.combine(day, datetime.time.min)
        if settings.USE_TZ and timezone.is_naive(stamp):
            try:
                stamp = timezone.make_aware(stamp)
            except Exception:
                pass
        return stamp

    def queryset(self, request, queryset):
        start = parse_date(self.from_value) if self.from_value else None
        end = parse_date(self.to_value) if self.to_value else None
        if start:
            queryset = queryset.filter(**{f'{self.field_name}__gte': self._bound(start)})
        if end:
            # Exclusive upper bound at the start of the next day, so the whole
            # "to" day is included regardless of time-of-day.
            queryset = queryset.filter(
                **{f'{self.field_name}__lt': self._bound(end, end_of_day=True)}
            )
        return queryset


def date_range_filter(field_name, title='date range'):
    """Build a DateRangeFilter bound to a specific field."""
    return type(
        f'DateRange{field_name.title().replace("_", "")}Filter',
        (DateRangeFilter,),
        {'field_name': field_name, 'title': title},
    )
