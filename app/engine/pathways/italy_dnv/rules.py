MINIMUM_ANNUAL_INCOME_EUR = 25500
MINIMUM_PRIOR_EXPERIENCE_MONTHS = 6
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3
CONSULAR_REVIEW_PASSPORT_VALIDITY_MONTHS = 15
MINIMUM_BLANK_PASSPORT_PAGES = 2

VALID_WORKER_CATEGORIES = {
    "self_employed_freelance",
    "employee_or_collaborator",
}

VALID_HIGHLY_QUALIFIED_BASES = {
    "have_a_relevant_degree",
    "certified_in_a_regulated_profession",
    "5plus_years_professional_experience",
    "3plus_years_it_executive_or_specialist_experience",
}

VALID_INCOME_EVIDENCE_TYPES = {
    "payslips",
    "tax_return",
    "w2",
    "bank_statements",
    "invoices",
    "income_proof",
}

# permesso_acknowledgement_missing and tax_social_security_acknowledgement_missing
# were removed from HARD_FAILURES (and from the eligibility flow entirely, see
# _evaluate_documents_and_compliance below) because they describe post-entry
# compliance steps, not pre-visa eligibility facts. See questions.json's
# "post_eligibility_checklist" block for the preserved question content.
HARD_FAILURES = {
    "adult_children_or_parents_family_route_not_supported",
    "accommodation_unavailable",
    "digital_nomad_self_employment_proof_unavailable",
    "eu_citizen_status",
    "health_insurance_unavailable",
    "highly_qualified_basis_not_met",
    "income_below_minimum",
    "passive_income_not_accepted",
    "passport_blank_pages_below_minimum",
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


def _as_values(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


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

    if worker_category == "self_employed_freelance":
        proof_available = _get_dotted(
            answers, "role.digital_nomad.self_employment_proof_available"
        )

        if _is_no(proof_available):
            failed_requirements.append(
                "digital_nomad_self_employment_proof_unavailable"
            )
        elif not _is_yes(proof_available):
            failed_requirements.append("digital_nomad_self_employment_proof_needs_review")

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
    eu_citizen_status = _get_dotted(answers, "identity.eu_citizen_status")
    if _is_yes(eu_citizen_status):
        failed_requirements.append("eu_citizen_status")
    elif eu_citizen_status != "no":
        failed_requirements.append("eu_citizen_status_needs_review")

    remote_tools_confirmed = _get_dotted(
        answers, "work.remote_technological_tools_confirmed"
    )
    if _is_no(remote_tools_confirmed):
        failed_requirements.append("remote_technological_work_not_confirmed")
    elif not _is_yes(remote_tools_confirmed):
        failed_requirements.append("remote_technological_work_needs_review")

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

    income_source_type = _get_dotted(answers, "financial.income_source_type")
    if income_source_type == "passive_income":
        failed_requirements.append("passive_income_not_accepted")
    elif income_source_type != "remote_work_from_italy":
        failed_requirements.append("income_source_needs_review")

    evidence_types = set(
        _as_values(_get_dotted(answers, "financial.income_evidence_types"))
    )
    if not evidence_types.intersection(VALID_INCOME_EVIDENCE_TYPES):
        failed_requirements.append("income_evidence_needs_review")


def _evaluate_documents_and_compliance(answers, failed_requirements):
    health_insurance_status = _get_dotted(answers, "routing.health_insurance_status")
    if health_insurance_status == "cannot_obtain":
        failed_requirements.append("health_insurance_unavailable")
    elif health_insurance_status != "have_it":
        failed_requirements.append("health_insurance_needs_review")

    accommodation_status = _get_dotted(answers, "housing.accommodation_status")
    if accommodation_status == "not_available":
        failed_requirements.append("accommodation_unavailable")
    elif accommodation_status != "have_qualifying_accommodation":
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

    # Severity intentionally unchanged (still hard) per current cleanup scope.
    passport_blank_pages = _as_int(_get_dotted(answers, "routing.passport_blank_pages"))
    if passport_blank_pages is None:
        failed_requirements.append("passport_blank_pages_needs_review")
    elif passport_blank_pages < MINIMUM_BLANK_PASSPORT_PAGES:
        failed_requirements.append("passport_blank_pages_below_minimum")

    # NOTE: permesso_8_day and tax_social_security acknowledgements were removed
    # from this function (and from questions.json's live flow) because they are
    # post-entry compliance steps, not pre-visa eligibility facts. See
    # questions.json's "post_eligibility_checklist" block and clarifications.json
    # for the preserved question/requirement content.


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

    family_documents_available = _get_dotted(
        answers, "routing.family_documents_available"
    )
    if _is_no(family_documents_available):
        failed_requirements.append("family_documents_needs_review")
    elif not _is_yes(family_documents_available):
        failed_requirements.append("family_documents_needs_review")


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
