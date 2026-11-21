"""Średnia obliczona przez SPC nie jest nowym pomiarem wejściowym."""

import pytest

from conftest import setup_order, save, authorize


@pytest.mark.parametrize(
    "values,expected_ok",
    [
        (["3.1", "3.4", "3.5"], True),
        (["3.2", "3.2", "3.3"], True),
        (["3.8", "3.9", "3.9"], False),
    ],
)
def test_save_and_chart_accept_repeating_subgroup_mean(
    client, spec, values, expected_ok
):
    """Powtarzalna średnia nie blokuje zapisu ani odczytu karty i zachowuje ocenę."""
    _, order, plan = setup_order(client, spec)
    authorize(client, "spc")
    config = client.post(
        "/api/spc/configs",
        json={
            "characteristic_id": plan["specs"][0]["id"],
            "sampling_plan": "Trzy próbki tworzące zatwierdzoną podgrupę testową.",
            "n": 3,
            "cl": 3.5,
            "lcl": 3,
            "ucl": 4,
            "rcl": 0.1,
            "rlcl": 0,
            "rucl": 10,
        },
    )
    assert config.status_code == 200
    result = save(client, order, plan, values)
    assert result.status_code == 200, result.text
    assert result.json()["ok"] is expected_ok
    chart = client.get(f"/api/spc/chart/{config.json()['id']}")
    assert chart.status_code == 200, chart.text
    assert chart.json()["means"][0] == pytest.approx(sum(map(float, values)) / 3)
    assert any(a["type"] == "SPECIFICATION" for a in chart.json()["alarms"]) is (
        not expected_ok
    )
