"""Single-producer local exposure admission, independent of delivery sinks."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import sys
import tempfile

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
DIRECTIONS = ("BUY", "SELL")
NORMAL_MAX_AGE_HOURS = 24
HARD_MAX_AGE_HOURS = 168


def identity(pair, direction, timeframe, entry, sl, tp):
    pair, direction, timeframe = pair.upper(), direction.upper(), timeframe.upper()
    if pair not in PAIRS or direction not in DIRECTIONS or timeframe != "M15":
        raise ValueError("invalid_exposure_scope")
    levels = tuple(float(x) for x in (entry, sl, tp))
    if any(not math.isfinite(x) or x <= 0 for x in levels):
        raise ValueError("invalid_exposure_levels")
    return dict(pair=pair, direction=direction, timeframe=timeframe,
                entry_price=levels[0], stop_loss=levels[1], take_profit=levels[2])


def row_identity(row):
    return identity(row["pair"], row["direction"], row["timeframe"],
                    row["entry_price"], row["stop_loss"], row["take_profit"])


def record_path(directory, ident):
    return directory / (ident["pair"] + "-" + ident["direction"] + ".json")


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def locked(root):
    directory = Path(root) / "state" / "open_exposure"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    sync_dir(directory.parent)
    with (directory / ".lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield directory


def load(path):
    if path.is_symlink():
        raise ValueError("invalid_exposure_record")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if (not isinstance(record, dict) or record.get("version") != 1
            or type(record.get("admitted_epoch")) is not int
            or record["admitted_epoch"] <= 1000000000
            or record_path(path.parent, row_identity(record)) != path):
        raise ValueError("invalid_exposure_record")
    return record


def write(path, record):
    fd, temp = tempfile.mkstemp(prefix=".exposure-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def remove(path):
    path.unlink()
    sync_dir(path.parent)


def admit(root, ident, epoch, hard_max_age=HARD_MAX_AGE_HOURS):
    if epoch <= 1000000000 or hard_max_age <= 0:
        raise ValueError("invalid_exposure_clock_or_age")
    with locked(root) as directory:
        path = record_path(directory, ident)
        old = load(path)
        if old is not None:
            age = epoch - old["admitted_epoch"]
            if age < 0:
                raise ValueError("exposure_clock_regressed")
            if age < hard_max_age * 3600:
                return row_identity(old) == ident
            print(f"[EXPOSURE] hard_expiry:{ident['pair']}:{ident['direction']}", file=sys.stderr)
        write(path, dict(ident, version=1, admitted_epoch=epoch))
        return True


def release_closed(root, row):
    """Only a confirmed matching closure of this admission can clear its slot."""
    ident = row_identity(row)
    created = datetime.fromisoformat(row["created_at"])
    if created.tzinfo is None:
        raise ValueError("closure_clock_unavailable")
    with locked(root) as directory:
        path = record_path(directory, ident)
        record = load(path)
        if (record is None or row_identity(record) != ident
                or created.timestamp() < record["admitted_epoch"]):
            return False
        remove(path)
        return True


def expire_orphans(root, epoch, active_rows, usable_candles, normal_max_age, hard_max_age, pair_filter=None):
    """Normal age uses closer's candle coverage; hard age handles stuck slots.

    This is lifecycle maintenance, not admission and not delivery retry state.
    A represented ACTIVE row is left to the closer's normal confirmed-close path.
    """
    if not (0 < normal_max_age <= hard_max_age):
        raise ValueError("invalid_exposure_age_policy")
    directory = Path(root) / "state" / "open_exposure"
    if not directory.exists():
        return []
    with locked(root) as directory:
        expired = []
        for path in sorted(directory.glob("*.json")):
            record = load(path)
            if record is None or (pair_filter and record["pair"] != pair_filter.upper()):
                continue
            age = epoch - record["admitted_epoch"]
            if age < 0:
                raise ValueError("exposure_clock_regressed")
            ident = row_identity(record)
            # A database row is used only by the closer to identify an existing
            # lifecycle, never by the watcher admission decision.
            represented = any(row_identity(row) == ident for row in active_rows)
            if age >= hard_max_age * 3600 or (
                not represented and age >= normal_max_age * 3600 and usable_candles(record)
            ):
                remove(path)
                expired.append(f"{record['pair']}:{record['direction']}")
        return expired


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    parser.add_argument("--hard-max-age", type=int, default=HARD_MAX_AGE_HOURS)
    parser.add_argument("pair")
    parser.add_argument("direction")
    parser.add_argument("timeframe")
    parser.add_argument("entry")
    parser.add_argument("sl")
    parser.add_argument("tp")
    args = parser.parse_args()
    try:
        ident = identity(args.pair, args.direction, args.timeframe, args.entry, args.sl, args.tp)
        return 0 if admit(args.root, ident, args.epoch, args.hard_max_age) else 3
    except Exception as exc:
        print(f"[HEALTH_ALERT] exposure_admission:{type(exc).__name__}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
