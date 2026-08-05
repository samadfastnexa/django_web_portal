"""Resolve where a portal user works from SAP, rather than from client input.

A client posting local Region/Zone/Territory ids is guessing at data SAP already
owns - and for a company whose hierarchy was never imported there are no ids to
guess with. This runs the other way: user -> employee code -> B4_EMP -> OTER.

What comes back is SAP's own names and ids, verbatim. Nothing is written to the
portal's Region/Zone/Territory tables: those were imported from SAP once and have
drifted since (ORANG's regions were renamed, AGRI's hierarchy is empty), so
mirroring into them would duplicate master data rather than correct it. Callers
store these values in their own columns - see Meeting.sap_* .
"""

import logging

from django.core.cache import cache

from FieldAdvisoryService.models import Company
from sap_integration.hana_connect import employee_geo_scoped

logger = logging.getLogger(__name__)

# The SAP round trip costs ~1.5s per company and sits on the meeting write path,
# so a field officer filing a day's reports would otherwise pay it on every POST.
# A staff member's SAP territory does not move within a shift.
_GEO_TTL = 15 * 60
# One company's `name` is not a real HANA schema at all, so without this every
# POST would spend a connect attempt discovering that again.
_SCHEMA_DOWN_TTL = 5 * 60


def sap_geo_for_user(user, company=None):
    """Where SAP says this user works, as SAP's own names and ids.

    The chain is portal user -> SalesStaffProfile -> employee code -> SAP: the
    code is the one already held locally on the profile (or on the company
    membership, when that is filled in), so nothing about the user has to be
    posted beyond their id.

    `company` pins the lookup to one company (and therefore one HANA schema);
    without it every company the user belongs to is tried until SAP recognises
    one of their codes, because a code is only unique within a schema.

    `region` / `zone` / `territory` list everything the employee is assigned,
    comma separated - one assignment reads as a plain name, several give the
    whole coverage. `territory_id` is set only when there is exactly one.
    `territories` carries each assignment with its own zone and region, so a
    caller can offer the employee a shortlist and settle all three levels from
    whichever they pick. `note` explains anything the caller should act on.

    Never raises for SAP's sake: an unknown code, an unmapped employee or an
    outage all come back as empty values with an explanatory note.
    """
    result = {
        'company': None, 'region': None, 'zone': None, 'territory': None,
        'territory_id': None, 'territories': [], 'employee_code': None,
        'schema': None, 'territory_count': 0, 'note': None,
    }

    profile = getattr(user, 'sales_profile', None) if user is not None else None
    if profile is None:
        result['note'] = 'User has no sales staff profile, so there is no SAP employee code to look up.'
        return result

    candidates = _candidates(profile, company)
    if not candidates:
        result['note'] = 'No SAP employee code is recorded for this user.'
        return result

    unreachable = []
    for candidate_company, employee_codes in candidates:
        schema = (candidate_company.name or '').strip()
        geo = _cached_lookup(schema, employee_codes)
        if geo is None:
            # Could not ask: unusable schema name, or HANA is down.
            unreachable.append(schema)
            continue
        if not geo.get('territory_count'):
            # Asked and answered: this schema does not hold these codes.
            continue

        result.update({
            'company': candidate_company,
            'region': geo['region'],
            'zone': geo['zone'],
            'territory': geo['territory'],
            'territory_id': geo['territory_id'],
            'territories': geo.get('territories') or [],
            'employee_code': geo['employee_code'],
            'schema': schema,
            'territory_count': geo['territory_count'],
            'note': _shortfall_note(geo),
        })
        return result

    # Notes name no employee code and no schema: a caller may file a meeting
    # under someone else's user id, and these strings go back in that response.
    # The code and schema are returned separately, to their owner only; the
    # schemas that failed are in the warning employee_geo_scoped already logged.
    if len(unreachable) == len(candidates):
        # Never blame SAP master data for what is really an outage - the two
        # need very different people to fix them.
        result['note'] = (
            "SAP could not be reached, so region, zone and territory were left blank. "
            "The meeting was saved; re-save it once SAP is back, or pass the ids explicitly."
        )
    else:
        result['note'] = (
            "SAP has no territory for this employee code. An employee only appears in "
            "B4_EMP once their Team/Area (OHEM.U_TA) is assigned in SAP."
        )
    return result


def _cached_lookup(schema, employee_codes):
    """employee_geo_scoped() with a short cache in front of it.

    Definite answers are cached. A failure is not - caching "no territory" for a
    schema that was merely unreachable would pin a wrong answer in place - but
    the schema is marked down for a few minutes so one dead schema does not cost
    every POST a connect attempt.
    """
    key = 'sapgeo:%s:%s' % (schema, ','.join(employee_codes))
    cached = cache.get(key)
    if cached is not None:
        return cached
    if cache.get('sapgeo:down:%s' % schema):
        return None

    geo = employee_geo_scoped(schema, employee_codes)
    if geo is None:
        cache.set('sapgeo:down:%s' % schema, True, _SCHEMA_DOWN_TTL)
    else:
        cache.set(key, geo, _GEO_TTL)
    return geo


def primary_company_for_user(user):
    """The user's own company, for when SAP cannot place them at all."""
    profile = getattr(user, 'sales_profile', None) if user is not None else None
    if profile is None:
        return None
    membership = (
        profile.company_memberships.filter(is_active=True)
        .select_related('company')
        .order_by('-is_primary', 'id')
        .first()
    )
    return membership.company if membership else profile.companies.first()


def _candidates(profile, company):
    """(company, [employee_code, ...]) pairs to try, most specific first.

    A user carries up to two codes: the one on their SalesStaffProfile and, if
    the company membership was filled in, a company-specific one. Both are tried
    per company - the membership code first because it is the more specific of
    the two, then the profile code, which is the one the SAP employee import
    actually populates.
    """
    profile_code = (profile.employee_code or '').strip()

    memberships = list(
        profile.company_memberships.filter(is_active=True)
        .select_related('company')
        .order_by('-is_primary', 'id')
    )

    if company is not None:
        membership = next((m for m in memberships if m.company_id == company.pk), None)
        companies = [(company, (membership.employee_code if membership else '') or '')]
    elif memberships:
        companies = [(m.company, m.employee_code or '') for m in memberships]
    elif profile_code:
        # No membership rows to narrow it down - the code will only resolve in
        # the one schema that actually holds this employee.
        companies = [(c, '') for c in Company.objects.filter(is_active=True)]
    else:
        return []

    pairs = []
    for candidate_company, membership_code in companies:
        codes = [c for c in (str(membership_code).strip(), profile_code) if c]
        # dict.fromkeys keeps order while dropping the duplicate when a
        # membership simply repeats the profile code.
        codes = list(dict.fromkeys(codes))
        if candidate_company is not None and codes:
            pairs.append((candidate_company, codes))
    return pairs


def _shortfall_note(geo):
    """Say so when the recorded location is the employee's coverage, not one place."""
    count = geo.get('territory_count') or 0
    if count <= 1:
        return None
    return (
        f"Employee is assigned {count} SAP territories, all listed above. To record "
        f"the single territory this meeting was actually in, post sap_territory_id - "
        f"GET my-territories/ lists the employee's own, and naming one narrows zone "
        f"and region to match."
    )
