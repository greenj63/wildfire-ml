from shared.evaluation import accuracy, rmse


def test_accuracy():
    assert accuracy([1, 0, 1, 1], [1, 0, 0, 1]) == 0.75


def test_rmse_zero_when_perfect():
    assert rmse([1.0, 2.0], [1.0, 2.0]) == 0.0
