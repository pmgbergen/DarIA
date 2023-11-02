"""Quadrature rules for numerical integration."""

import numpy as np


def gauss(dim: int, order: int) -> tuple[np.ndarray, np.ndarray]:
    """Return the Gauss points and weights for the given dimension and order.

    These are the Gauss points and weights for the reference element [-1, 1]^dim.

    Args:
        dim (int): Dimension of the Gauss points.
        order (int): order of the Gauss points.

    Returns:
        tuple[np.ndarray, np.ndarray]: Gauss points and weights.

    """
    if dim == 1:
        if order == 0:
            return np.array([0.0]), np.array([2.0])
        elif order == 1:
            return np.array([-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)]), np.array(
                [1.0, 1.0]
            )
        elif order == 2:
            return (
                np.array([-np.sqrt(3.0 / 5.0), 0.0, np.sqrt(3.0 / 5.0)]),
                np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0]),
            )
        elif order == 3:
            return (
                np.array(
                    [
                        -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                    ]
                ),
                np.array(
                    [
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                    ]
                ),
            )
        elif order == 4:
            return (
                np.array(
                    [
                        0.0,
                        -1.0 / 3.0 * np.sqrt(5.0 - 2.0 * np.sqrt(10.0 / 7.0)),
                        1.0 / 3.0 * np.sqrt(5.0 - 2.0 * np.sqrt(10.0 / 7.0)),
                        -1.0 / 3.0 * np.sqrt(5.0 + 2.0 * np.sqrt(10.0 / 7.0)),
                        1.0 / 3.0 * np.sqrt(5.0 + 2.0 * np.sqrt(10.0 / 7.0)),
                    ]
                ),
                np.array(
                    [
                        128.0 / 225.0,
                        (322.0 + 13.0 * np.sqrt(70.0)) / 900.0,
                        (322.0 + 13.0 * np.sqrt(70.0)) / 900.0,
                        (322.0 - 13.0 * np.sqrt(70.0)) / 900.0,
                        (322.0 - 13.0 * np.sqrt(70.0)) / 900.0,
                    ]
                ),
            )
        else:
            raise NotImplementedError(
                f"Gauss points of order {order} not implemented for dimension {dim}."
            )
    elif dim == 2:
        if order == 0:
            return (
                np.array([[0.0, 0.0]]),
                np.array([4.0]),
            )
        elif order == 1:
            return (
                np.array(
                    [
                        [-1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                        [-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                    ]
                ),
                np.array([1.0, 1.0, 1.0, 1.0]),
            )
        elif order == 2:
            return (
                np.array(
                    [
                        [-np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [0.0, -np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), 0.0],
                        [0.0, 0.0],
                        [np.sqrt(3.0 / 5.0), 0.0],
                        [-np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [0.0, np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                    ]
                ),
                np.array(
                    [
                        25.0 / 81.0,
                        40.0 / 81.0,
                        25.0 / 81.0,
                        40.0 / 81.0,
                        64.0 / 81.0,
                        40.0 / 81.0,
                        25.0 / 81.0,
                        40.0 / 81.0,
                        25.0 / 81.0,
                    ]
                ),
            )
        elif order == 3:
            return (
                np.array(
                    [
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                    ]
                ),
                np.array(
                    [
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                    ]
                ),
            )
        else:
            raise NotImplementedError(
                f"Gauss points of order {order} not implemented for dimension {dim}."
            )
    elif dim == 3:
        if order == 0:
            return (
                np.array([[0.0, 0.0, 0.0]]),
                np.array([8.0]),
            )
        elif order == 1:
            return (
                np.array(
                    [
                        [-1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)],
                        [-1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                        [1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                        [-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
                    ]
                ),
                np.array(
                    [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                ),
            )
        elif order == 2:
            return (
                np.array(
                    [
                        [-np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [0.0, -np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), 0.0, -np.sqrt(3.0 / 5.0)],
                        [0.0, 0.0, -np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), 0.0, -np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [0.0, np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), 0.0],
                        [0.0, -np.sqrt(3.0 / 5.0), 0.0],
                        [np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), 0.0],
                        [-np.sqrt(3.0 / 5.0), 0.0, 0.0],
                        [0.0, 0.0, 0.0],
                        [np.sqrt(3.0 / 5.0), 0.0, 0.0],
                        [-np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), 0.0],
                        [0.0, np.sqrt(3.0 / 5.0), 0.0],
                        [np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), 0.0],
                        [-np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [0.0, -np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), -np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), 0.0, np.sqrt(3.0 / 5.0)],
                        [0.0, 0.0, np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), 0.0, np.sqrt(3.0 / 5.0)],
                        [-np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [0.0, np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                        [np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0), np.sqrt(3.0 / 5.0)],
                    ]
                ),
                np.array(
                    [
                        125.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        320.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        320.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        320.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        320.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                        200.0 / 729.0,
                        125.0 / 729.0,
                    ]
                ),
            )
        elif order == 3:
            raise NotImplementedError
            return (
                np.array(
                    [
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                        [
                            -np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 - 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                            np.sqrt(3.0 / 7.0 + 2.0 / 7.0 * np.sqrt(6.0 / 5.0)),
                        ],
                    ]
                ),
                np.array(
                    [
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 - np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                        (18.0 + np.sqrt(30.0)) / 36.0,
                    ]
                ),
            )
        else:
            raise NotImplementedError(
                f"Gauss points of order {order} not implemented for dimension {dim}."
            )
    else:
        raise NotImplementedError(
            f"Gauss points of order {order} not implemented for dimension {dim}."
        )


def gauss_reference_cell(dim: int, order: int) -> tuple[np.ndarray, np.ndarray]:
    """Convert Gauss points to a quadrature rule for the unit cube.

    Args:
        dim (int): Dimension of the Gauss points.
        order (int): order of the Gauss points.

    Returns:
        tuple[np.ndarray, np.ndarray]: Quadrature points and weights.

    """
    pts, weights = gauss(dim, order)
    pts = (pts + 1.0) / 2.0
    weights = weights / np.sum(weights)
    return pts, weights
