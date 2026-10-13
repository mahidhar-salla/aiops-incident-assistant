from aiops_assistant.backends import get_backend
from aiops_assistant.evaluate import run_eval
from aiops_assistant.evidence import build_pack
from aiops_assistant.loader import incident_dirs, load_incident
from aiops_assistant.prompt import render
from aiops_assistant.synth import SCENARIOS, build


def test_dataset_has_labelled_incidents(root):
    dirs = incident_dirs(root / "incidents")
    assert len(dirs) == len(SCENARIOS) >= 10
    for d in dirs:
        inc = load_incident(d, with_label=True)
        assert inc.label is not None
        ids = {x.id for x in inc.logs}
        assert set(inc.label.key_lines) <= ids


def test_committed_incidents_match_generator(root):
    for s in SCENARIOS:
        lines, *_ = build(s)
        assert (root / "incidents" / s.id / "logs.log").read_text() == "\n".join(lines) + "\n"


def test_prompt_is_redacted_and_has_no_labels(root, sections):
    for d in incident_dirs(root / "incidents"):
        inc = load_incident(d, with_label=True)
        prompt = render(build_pack(inc, sections))
        assert "@example.com" not in prompt and "4111 1111" not in prompt and "203.0.113." not in prompt
        assert inc.label is not None and inc.label.root_cause not in prompt


def test_mock_eval_scores(root, sections):
    s = run_eval(get_backend("mock"), root / "incidents", sections)
    assert s.n >= 10
    assert s.citation_validity == 1.0 and s.hallucination_free_rate == 1.0
    assert s.root_cause_accuracy >= 0.9
