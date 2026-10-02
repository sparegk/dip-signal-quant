import numpy as np
import pytest

from src.exit_research import atr_scaled_barriers


def test_atr_barriers_scale_to_signal_time_volatility():
    calm = atr_scaled_barriers(100, 2, stop_atr_multiple=2, target_atr_multiple=3)
    volatile = atr_scaled_barriers(100, 5, stop_atr_multiple=2, target_atr_multiple=3)
    assert calm == {"stop_price": 96, "target_price": 106,
                    "stop_fraction": .04, "target_fraction": .06}
    assert volatile["stop_price"] == 90
    assert volatile["target_price"] == 115
    assert volatile["stop_fraction"] == .1


@pytest.mark.parametrize("values", [
    (0, 2, 2, 3), (100, 0, 2, 3), (100, 2, 0, 3), (100, 2, 2, np.inf),
    (True, 2, 2, 3), (1, 2, 1, 1),
])
def test_atr_barriers_reject_invalid_or_nonpositive_levels(values):
    with pytest.raises(ValueError):
        atr_scaled_barriers(values[0], values[1], stop_atr_multiple=values[2],
                            target_atr_multiple=values[3])
