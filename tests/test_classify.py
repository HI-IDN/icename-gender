import pytest

from kyngreinir import Register, classify, explain

# A tiny register, so the tests do not depend on the bundled snapshot's contents.
REGISTER = Register(
    [
        {"icelandicName": "anna", "type": "ST", "status": "Sam"},
        {"icelandicName": "lísa", "type": "ST", "status": "Sam"},
        {"icelandicName": "jón", "type": "DR", "status": "Sam"},
        {"icelandicName": "alex", "type": "DR", "status": "Sam"},
        {"icelandicName": "alex", "type": "ST", "status": "Sam"},
        {"icelandicName": "þór", "type": "MI", "status": "Sam"},
        {"icelandicName": "gústa", "type": "ST", "status": "Haf"},
    ]
)


@pytest.mark.parametrize(
    "name, gender, rule",
    [
        ("Guðrún Jónsdóttir", "female", "dottir"),
        # -dóttir decides even when the given name is unknown to the register.
        ("Xyz Pétursdóttir", "female", "dottir"),
        # A -son family name on a woman: the given name decides before -son is considered.
        ("Anna Thorsteinsson", "female", "given_name"),
        ("Jón Thorsteinsson", "male", "given_name"),
        # -son only when no given name decides.
        ("Xyz Jónsson", "male", "son"),
        # Unisex and middle names are passed over for the next given name.
        ("Alex Jón Smith", "male", "given_name"),
        ("Þór Anna Smith", "female", "given_name"),
        # A hyphenated given name is looked up part by part.
        ("Xyz-Lísa Smith", "female", "given_name"),
        ("Alex Smith", None, None),
        ("", None, None),
    ],
)
def test_classify(name, gender, rule):
    est = classify(name, REGISTER)
    assert (est.gender, est.rule) == (gender, rule)


def test_single_name_is_its_own_given_name():
    assert classify("Anna", REGISTER).gender == "female"


def test_rejected_names_count_unless_approved_only():
    assert REGISTER.gender_of("Gústa") == "female"
    strict = Register([{"icelandicName": "gústa", "type": "ST", "status": "Haf"}],
                      approved_only=True)
    assert strict.gender_of("Gústa") == "unknown"


def test_bundled_snapshot_loads():
    reg = Register()
    assert reg.gender_of("Guðrún") == "female"
    assert reg.gender_of("Guðmundur") == "male"


@pytest.mark.parametrize(
    "name, agreement, female, male",
    [
        # The case -son-after-given-names exists for: the evidence conflicts, the given name wins.
        ("Anna Thorsteinsson", "conflicting", 1, 1),
        ("Anna Jónsdóttir", "unanimous", 2, 0),
        ("Xyz Jónsson", "unanimous", 0, 1),
        ("Alex Smith", "none", 0, 0),
    ],
)
def test_explain_counts_and_agreement(name, agreement, female, male):
    ex = explain(name, REGISTER)
    assert (ex.agreement, ex.female, ex.male) == (agreement, female, male)


def test_explain_keeps_the_estimate():
    ex = explain("Anna Thorsteinsson", REGISTER)
    assert ex.estimate == classify("Anna Thorsteinsson", REGISTER)
    assert [(e.part, e.source, e.says) for e in ex.evidence] == [
        ("Anna", "register", "female"),
        ("Thorsteinsson", "suffix", "male"),
    ]
