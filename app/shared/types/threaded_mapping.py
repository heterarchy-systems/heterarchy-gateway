"""Bounded parallel mapping for pure transformations over stable values."""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

_PARALLEL_THRESHOLD = 8
_MAX_WORKERS = 4


def threaded_map[InputT, OutputT](
    function: Callable[[InputT], OutputT],
    values: Sequence[InputT],
) -> list[OutputT]:
    """Map a pure function synchronously or through a bounded thread pool.

    Args:
        function: Pure transformation that does not share mutable state.
        values: Stable sequence of values safe to read concurrently.
    Return:
        Results in the same order as the input sequence.
    """
    if len(values) < _PARALLEL_THRESHOLD:
        result = [function(value) for value in values]
        return result

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        result = list(executor.map(function, values, buffersize=_MAX_WORKERS))
    return result
