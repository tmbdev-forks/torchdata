# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
import random
from typing import Any, Dict, Iterator

from torchdata.datapipes import functional_datapipe
from torchdata.datapipes.iter import IterDataPipe


def _pick(buf, rng):
    k = rng.randint(0, len(buf) - 1)
    sample = buf[k]
    buf[k] = buf[-1]
    buf.pop()
    return sample


@functional_datapipe("incshuffle")
class IncrementalShufflerIterDataPipe(IterDataPipe[Dict]):
    r"""
    Perform incremental shuffling on a stream of data.

    This initially reads `initial` samples. Subsequently, an output sample
    is generated by randomly selecting an input sample from the buffer and
    replacing it with another sample from the input stream. If the shuffle
    buffer is smaller than `buffer_size`, an additional sample is used to fill
    up the shuffle buffer.

    This shuffle function allows the user to make a tradeoff between startup
    latency and randomness.

    Args:
        source_datapipe: a DataPipe yielding a stream of samples
        rng: user supplied random number generator
        initial: initial buffer size (10)
        buffer_size: buffer size for shuffling (1000)

    Returns:
        a DataPipe yielding a stream of tuples
    """

    def __init__(self, source_datapipe: IterDataPipe[Any], rng=None, initial=10, buffer_size=1000):
        super().__init__()
        self.source_datapipe: IterDataPipe[Any] = source_datapipe
        self.rng = rng or random.Random(os.urandom(8))
        self.initial = initial
        self.buffer_size = buffer_size

    def __iter__(self) -> Iterator[Any]:
        initial = min(self.initial, self.buffer_size)
        buf = []
        data = iter(self.source_datapipe)
        for sample in data:
            buf.append(sample)
            if len(buf) < self.buffer_size:
                try:
                    buf.append(next(data))  # skipcq: PYL-R1708
                except StopIteration:
                    pass
            if len(buf) >= initial:
                yield _pick(buf, self.rng)
        while len(buf) > 0:
            yield _pick(buf, self.rng)

    def __len__(self) -> int:
        return len(self.source_datapipe)