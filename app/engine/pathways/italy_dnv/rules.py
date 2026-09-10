MINIMUM_ANNUAL_INCOME_EUR = 25500
MINIMUM_PRIOR_EXPERIENCE_MONTHS = 6
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3
CONSULAR_REVIEW_PASSPORT_VALIDITY_MONTHS = 15

VALID_WORKER_CATEGORIES = {
    "self_employed_freelance",
    "employee_or_collaborator",
}

VALID_HIGHLY_QUALIFIED_BASES = {
    "university_degree",
    "licensed_professional",
    "at_least_5_years_experience",
    "at_least_3_years_senior_tech_experience",
}

# NOTE: the following live questions were removed during the canonical
# cleanup (questions_dnv.md) because they test document/evidence readiness,
# filing procedure, or dead intake data rather than facts needed to
# determine INITIAL eligibility, and all eligibility consequences tied
# solely to them were removed alongside them:
#   identity.nationality (never evaluated; no eligibility consequence)
#   role.digital_nomad.self_employment_proof_available
#     (digital_nomad_self_employment_proof_unavailable / _needs_review) --
#     self-employed status is already represented by
#     routing.worker_category == "self_employed_freelance"; documentary
#     proof of that status belongs downstream.
#   financial.income_evidence_types (income_evidence_needs_review)
#   routing.passport_blank_pages
#     (passport_blank_pages_needs_review / _below_minimum) -- a
#     consulate-specific (New York), normally-fixable filing-logistics
#     detail, not a substantive disqualifier.
#   routing.family_documents_available (family_documents_needs_review) --
#     the substantive family-category fact remains represented by
#     routing.family_reunification_intent.
#   routing.additional_information (required: false; no eligibility
#     consequence)
# financial.income_from_remote_work_confirmed and
# financial.non_remote_income_source (income_source_needs_review,
# passive_income_not_accepted) were consolidated into
# financial.annual_work_income_eur itself: the canonical question asks
# specifically for income "from the remote work you will perform," so the
# amount collected is already scoped to qualifying work-derived income --
# passive income is excluded by the question's own wording rather than by a
# separate source-confirmation gate. See the MoveWise Review Notes in the
# implementation report for the open legal/product questions this
# consolidation and these removals raise.
# routing.health_insurance_status and housing.accommodation_status were
# simplified from 3-way status fields (have_it/will_obtain/cannot_obtain and
# have_qualifying_accommodation/will_secure_before_travel/not_available) to
# factual Yes/No questions asking whether the requirement WILL be satisfied
# -- the former "will_obtain"/"will_secure_before_travel" needs_review
# states are intentionally collapsed into "Yes" (pass).
#
# role.digital_nomad.partita_iva_acknowledged,
# compliance.permesso_8_day_acknowledged, and
# compliance.tax_social_security_acknowledged remain inert in
# questions.json's post_eligibility_checklist block and are not emitted
# here.
HARD_FAILURES = {
    "accommodation_unavailable",
    "adult_children_or_parents_family_route_not_supported",
    "eu_citizen_status",
    "health_insurance_unavailable",
    "highly_qualified_basis_not_met",
    "income_below_minimum",
    "passport_validity_below_minimum",
    "prior_experience_below_minimum",
    "remote_technological_work_not_confirmed",
    "remote_worker_contract_unavailable",
    "remote_worker_employer_clean_record_unavailable",
}


def _get_dotted(answers, key, default=None):
    current = answers
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _is_yes(value):
    return value is True or value == "yes"


def _is_no(value):
    return value is False or value == "no"


def _evaluate_route(answers, failed_requirements, routing):
    worker_category = _get_dotted(answers, "routing.worker_category")
    routing["worker_category"] = worker_category

    if worker_category not in VALID_WORKER_CATEGORIES:
        failed_requirements.append("worker_category_missing_or_unrecognized")
        return

    if worker_category == "employee_or_collaborator":
        contract_available = _get_dotted(
            answers, "role.remote_worker.contract_available"
        )
        declaration_available = _get_dotted(
            answers, "role.remote_worker.employer_clean_record_declaration_available"
        )

        if _is_no(contract_available):
            failed_requirements.append("remote_worker_contract_unavailable")
        elif not _is_yes(contract_available):
            failed_requirements.append("remote_worker_contract_needs_review")

        if _is_no(declaration_available):
            failed_requirements.append(
                "remote_worker_employer_clean_record_unavailable"
            )
        elif not _is_yes(declaration_available):
            failed_requirements.append(
                "remote_worker_employer_clean_record_needs_review"
            )


def _evaluate_core_eligibility(answers, failed_requirements):
    remote_work_confirmed = _get_dotted(answers, "work.remote_work_confirmed")
    if _is_no(remote_work_confirmed):
        failed_requirements.append("remote_technological_work_not_confirmed")
    elif not _is_yes(remote_work_confirmed):
        failed_requirements.append("remote_technological_work_needs_review")

    eu_citizen_status = _get_dotted(answers, "identity.eu_citizen_status")
    if _is_yes(eu_citizen_status):
        failed_requirements.append("eu_citizen_status")
    elif eu_citizen_status != "no":
        failed_requirements.append("eu_citizen_status_needs_review")

    highly_qualified_basis = _get_dotted(answers, "work.highly_qualified_basis")
    if highly_qualified_basis == "none_of_these":
        failed_requirements.append("highly_qualified_basis_not_met")
    elif highly_qualified_basis not in VALID_HIGHLY_QUALIFIED_BASES:
        failed_requirements.append("highly_qualified_basis_needs_review")

    prior_experience_months = _as_int(
        _get_dotted(answers, "work.prior_experience_months")
    )
    if prior_experience_months is None:
        failed_requirements.append("prior_experience_needs_review")
    elif prior_experience_months < MINIMUM_PRIOR_EXPERIENCE_MONTHS:
        failed_requirements.append("prior_experience_below_minimum")


def _evaluate_financials(answers, failed_requirements):
    annual_income = _as_float(_get_dotted(answers, "financial.annual_work_income_eur"))
    if annual_income is None:
        failed_requirements.append("income_needs_review")
    elif annual_income < MINIMUM_ANNUAL_INCOME_EUR:
        failed_requirements.append("income_below_minimum")


def _evaluate_documents_and_compliance(answers, failed_requirements):
    health_insurance_status = _get_dotted(answers, "routing.health_insurance_status")
    if _is_no(health_insurance_status):
        failed_requirements.append("health_insurance_unavailable")
    elif not _is_yes(health_insurance_status):
        failed_requirements.append("health_insurance_needs_review")

    accommodation_status = _get_dotted(answers, "housing.accommodation_status")
    if _is_no(accommodation_status):
        failed_requirements.append("accommodation_unavailable")
    elif not _is_yes(accommodation_status):
        failed_requirements.append("accommodation_needs_review")

    passport_validity_months = _as_int(
        _get_dotted(answers, "routing.passport_validity_months")
    )
    if passport_validity_months is None:
        failed_requirements.append("passport_validity_needs_review")
    elif passport_validity_months < MINIMUM_PASSPORT_VALIDITY_MONTHS:
        failed_requirements.append("passport_validity_below_minimum")
    elif passport_validity_months < CONSULAR_REVIEW_PASSPORT_VALIDITY_MONTHS:
        failed_requirements.append("passport_validity_consular_threshold_needs_review")


def _evaluate_family_route(answers, failed_requirements, routing):
    family_intent = _get_dotted(answers, "routing.family_reunification_intent")
    routing["family_reunification_intent"] = family_intent

    if family_intent in (None, ""):
        failed_requirements.append("family_reunification_needs_review")
        return

    if family_intent == "no_one_else":
        return

    if family_intent == "adult_children_or_parents":
        failed_requirements.append("adult_children_or_parents_family_route_not_supported")
        return


def evaluate_eligibility(answers):
    failed_requirements = []
    routing = {}

    _evaluate_route(answers, failed_requirements, routing)
    _evaluate_core_eligibility(answers, failed_requirements)
    _evaluate_financials(answers, failed_requirements)
    _evaluate_documents_and_compliance(answers, failed_requirements)
    _evaluate_family_route(answers, failed_requirements, routing)

    if any(requirement in HARD_FAILURES for requirement in failed_requirements):
        eligibility_status = "not_eligible"
    elif failed_requirements:
        eligibility_status = "needs_review"
    else:
        eligibility_status = "eligible"

    return {
        "eligibility_status": eligibility_status,
        "failed_requirements": failed_requirements,
        "pathway": "italy_dnv",
        "visa_type": "Italy Digital Nomad / Remote Worker Visa",
        "minimum_annual_income_eur": MINIMUM_ANNUAL_INCOME_EUR,
        "routing": routing,
    }
