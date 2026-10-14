"""trading_crab_lib.platform: the monthly platform, one flat module per job.

``paths`` and ``config`` find the checkout and its settings, ``code_version`` names the code that ran,
``checkpoints`` stores frames behind the holdout fence, ``ingest`` builds the data and ``report`` writes the
weekly page. Run it through the ``tradingcrab`` command.
"""

from __future__ import annotations
