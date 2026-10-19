"""Candidate-only exact frontier retirement; no sampling or engine changes.

All local components and joins are performed by the unmodified
ConnectedAccumulator. Only after add_chunk succeeds can a boundary key retire:
none of its six neighbors outside its owner belongs to an unprocessed scheduled
owner. A removed key therefore cannot participate in any subsequent join.
DSU nodes (including closed disconnected components), sizes and totals are never
compacted, summarized, or dropped.

The caller must pin the COMPLETE authoritative ownership plan before processing,
using plan_digest(full_owned_lows, edge) from its immutable checkpoint identity.
Never compute the expected digest from a possibly truncated resume payload.
Legacy adoption additionally trusts the completed ownership set obtained from
validated committed chunk records. A legacy accumulator has no provenance for
empty/interior-only chunks, so it cannot reconstruct that set by itself.

For existing engines, keep serialize_connected(frontier.accumulator) in the
original connected field and frontier.metadata() in a separate sibling mapping.
restore_projection joins them without changing their schemas or the store.
snapshot() is an optional standalone versioned wrapper containing both. Restore
always requires the caller's independently known full plan AND completed set;
restoring just the connected projection loses the frontier coverage contract.

Owners are equal, axis-aligned, zero-lattice cubes, as produced by
chunk_enumeration.enumerate_paint_chunks; arbitrary processing order is allowed.
This is not wired into any compiler, production checkpoint, or launch path.
"""
import hashlib
import json

from connected_constraints import ConnectedAccumulator
from checkpoint_store import restore_connected, serialize_connected


SCHEMA = 'riverstone.house_detail.connected_frontier.v4'
PLAN_SCHEMA = 'riverstone.house_detail.connected_frontier_plan.v4'


class FrontierError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise FrontierError(message)


def _point(value, name):
    _require(type(value) in (list, tuple) and len(value) == 3 and
             all(type(n) is int and -(2 ** 63) <= n < 2 ** 63 for n in value),
             name + ' must be three signed 64-bit integers')
    return tuple(value)


def _lows(values, edge, name):
    _require(type(edge) is int and 0 < edge < 2 ** 63, 'Positive integer edge required')
    result = []
    for value in values:
        low = _point(value, name)
        _require(all(n % edge == 0 and n + edge < 2 ** 63 for n in low),
                 name + ' must use non-overlapping zero-lattice owned cubes')
        result.append(low)
    _require(len(set(result)) == len(result), 'Duplicate ' + name)
    return tuple(sorted(result))


def _digest(lows, edge):
    data = {'schema': PLAN_SCHEMA, 'edge': edge, 'owned_lows': lows}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def plan_digest(owned_lows, edge):
    """Pin the complete trusted schedule, independent of traversal order."""
    return _digest(_lows(owned_lows, edge, 'scheduled owner'), edge)


class ConnectedFrontierV4:
    def __init__(self, owned_lows, edge, *, expected_plan_sha256, max_boundary_cells=500000):
        self.owned_lows = _lows(owned_lows, edge, 'scheduled owner')
        self.edge = edge
        self.plan_sha256 = _digest(self.owned_lows, edge)
        _require(self.plan_sha256 == expected_plan_sha256, 'Full ownership plan digest mismatch')
        _require(type(max_boundary_cells) is int and max_boundary_cells >= 0,
                 'Invalid boundary budget')
        self._scheduled = frozenset(self.owned_lows)
        self._completed = set()
        self._pending = set(self._scheduled)
        self._by_owner = {}
        self._accumulator = ConnectedAccumulator(max_boundary_cells)
        self.retired_boundary_cells = 0
        self._failed = False

    @property
    def completed_lows(self):
        return frozenset(self._completed)

    @property
    def accumulator(self):
        """Unchanged v1 projection for checkpoint_store; callers must not mutate it.

        Use this wrapper's result(), rather than the projection's result(), for
        the final decision so incomplete coverage cannot report global PASS.
        """
        self._healthy()
        return self._accumulator

    @property
    def coverage_complete(self):
        return not self._pending and not self._failed

    def _healthy(self):
        _require(not self._failed, 'Failed frontier add requires restoration of the last committed snapshot')

    def _owner(self, point):
        return tuple(n // self.edge * self.edge for n in point)

    def _is_boundary(self, point, low):
        return any(point[j] == low[j] or point[j] == low[j] + self.edge - 1 for j in range(3))

    def _neighbor_owners(self, low):
        for axis in range(3):
            for sign in (-1, 1):
                neighbor = list(low)
                neighbor[axis] += sign * self.edge
                yield tuple(neighbor)

    def _touches_pending(self, point, low):
        # These face tests enumerate exactly the six-neighbor addresses outside
        # this owner, including both opposite faces when edge == 1.
        for axis in range(3):
            if point[axis] == low[axis]:
                neighbor = list(low)
                neighbor[axis] -= self.edge
                if tuple(neighbor) in self._pending:
                    return True
            if point[axis] == low[axis] + self.edge - 1:
                neighbor = list(low)
                neighbor[axis] += self.edge
                if tuple(neighbor) in self._pending:
                    return True
        return False

    def _retire_owner(self, low):
        keys = self._by_owner.get(low)
        if not keys:
            return
        dead = [point for point in keys if not self._touches_pending(point, low)]
        for point in dead:
            del self._accumulator.boundary[point]
            keys.remove(point)
        self.retired_boundary_cells += len(dead)
        if not keys:
            del self._by_owner[low]

    @classmethod
    def _adopt(cls, accumulator, owned_lows, edge, completed_lows, expected_plan_sha256):
        result = cls(owned_lows, edge, expected_plan_sha256=expected_plan_sha256,
                     max_boundary_cells=accumulator.max_boundary_cells)
        completed = set(_lows(completed_lows, edge, 'completed owner'))
        _require(completed <= result._scheduled, 'Completed owner missing from full plan')
        _require(accumulator.total <= len(completed) * edge ** 3,
                 'Selected cell count exceeds completed ownership coverage')
        result._completed = completed
        result._pending.difference_update(completed)
        result._accumulator = accumulator
        if accumulator.first_point is not None:
            _require(result._owner(accumulator.first_point) in completed,
                     'First selected point is not owned by a completed chunk')
        for point in accumulator.boundary:
            low = result._owner(point)
            _require(low in completed, 'Boundary owner is not completed')
            _require(result._is_boundary(point, low), 'Retained key is not a chunk boundary point')
            result._by_owner.setdefault(low, set()).add(point)
        return result

    @classmethod
    def from_accumulator(cls, accumulator, owned_lows, edge, completed_lows, *, expected_plan_sha256):
        """Copy and prune an original accumulator; never modify the input.

        completed_lows must come from independently validated committed records,
        including completed chunks with zero selected points.
        """
        _require(type(accumulator) is ConnectedAccumulator, 'An original ConnectedAccumulator is required')
        copied = restore_connected(serialize_connected(accumulator))
        result = cls._adopt(copied, owned_lows, edge, completed_lows, expected_plan_sha256)
        for low in tuple(result._by_owner):
            result._retire_owner(low)
        return result

    def add_chunk(self, points, lo, hi=None):
        """Run unchanged local connectivity before retiring unreachable keys.

        Wrong/duplicate ownership and malformed points are rejected before any
        mutation. Point duplicates retain the original set semantics. No caller
        cell rows are edited and no geometry is sampled.
        """
        self._healthy()
        low = _point(lo, 'Chunk low')
        _require(low in self._scheduled, 'Chunk owner is not in the full scheduled plan')
        _require(low not in self._completed, 'Duplicate completed chunk owner')
        high = tuple(n + self.edge for n in low)
        if hi is not None:
            _require(_point(hi, 'Chunk high') == high, 'Chunk high disagrees with pinned ownership edge')
        selected = set()
        keys = set()
        for point in points:
            point = _point(point, 'Connectivity point')
            _require(all(low[j] <= point[j] < high[j] for j in range(3)),
                     'Connectivity point violates chunk ownership')
            selected.add(point)
            if self._is_boundary(point, low):
                keys.add(point)
        # Fail without poisoning the committed state on the existing temporary
        # boundary budget. The unchanged add_chunk still has its original check.
        _require(len(self._accumulator.boundary) + len(keys) <= self._accumulator.max_boundary_cells,
                 'Connected constraint boundary budget exceeded; pending without fallback')
        try:
            self._accumulator.add_chunk(selected, low, high)
        except Exception:
            self._failed = True
            raise
        self._completed.add(low)
        self._pending.remove(low)
        if keys:
            self._by_owner[low] = keys
        self._retire_owner(low)
        # Only these owners can have lost a last unprocessed face neighbor.
        for neighbor in self._neighbor_owners(low):
            self._retire_owner(neighbor)

    def result(self):
        """Return exact original connectivity semantics only after full coverage."""
        self._healthy()
        _require(self.coverage_complete, 'Incomplete ownership coverage: final connectivity is pending')
        return self._accumulator.result()

    def progress(self):
        """Prefix diagnostics deliberately have no global pass field."""
        self._healthy()
        result = self._accumulator.result()
        result['selected_prefix_connected'] = result.pop('pass')
        result.update(coverage_complete=self.coverage_complete,
                      completed_chunks=len(self._completed), scheduled_chunks=len(self._scheduled),
                      remaining_chunks=len(self._pending), retired_boundary_cells=self.retired_boundary_cells)
        return result

    def metadata(self):
        """Separate v4 coverage metadata, with no connected payload or cell rows."""
        self._healthy()
        return {'schema': SCHEMA, 'edge': self.edge, 'plan_sha256': self.plan_sha256,
                'owned_lows': [list(low) for low in self.owned_lows],
                'completed_lows': [list(low) for low in sorted(self._completed)],
                'retired_boundary_cells': self.retired_boundary_cells}

    def snapshot(self):
        """Optional combined wrapper suitable for an unchanged checkpoint_store.Store."""
        return {**self.metadata(), 'connected': serialize_connected(self.accumulator)}

    @classmethod
    def restore_projection(cls, connected_record, metadata, owned_lows, edge, completed_lows,
                           *, expected_plan_sha256):
        """Resume the v1 connected field plus a separately persisted v4 mapping."""
        _require(type(metadata) is dict and 'connected' not in metadata,
                 'Malformed separate frontier metadata')
        return cls.restore({**metadata, 'connected': connected_record}, owned_lows, edge,
                           completed_lows, expected_plan_sha256=expected_plan_sha256)

    @classmethod
    def restore(cls, record, owned_lows, edge, completed_lows, *, expected_plan_sha256):
        """Restore only when the external trusted plan and exact coverage match."""
        _require(type(record) is dict and set(record) == {
            'schema', 'edge', 'plan_sha256', 'owned_lows', 'completed_lows',
            'retired_boundary_cells', 'connected'}, 'Malformed frontier snapshot')
        _require(record['schema'] == SCHEMA, 'Unknown frontier snapshot schema')
        expected_lows = _lows(owned_lows, edge, 'scheduled owner')
        expected_completed = _lows(completed_lows, edge, 'completed owner')
        _require(type(record['edge']) is int and record['edge'] == edge,
                 'Snapshot edge differs from trusted plan')
        _require(type(record['owned_lows']) is list and
                 _lows(record['owned_lows'], edge, 'snapshot scheduled owner') == expected_lows,
                 'Snapshot full ownership plan changed or is incomplete')
        _require(type(record['completed_lows']) is list and
                 _lows(record['completed_lows'], edge, 'snapshot completed owner') == expected_completed,
                 'Snapshot completed coverage differs from committed chunks')
        _require(record['plan_sha256'] == expected_plan_sha256, 'Snapshot plan digest mismatch')
        accumulator = restore_connected(record['connected'])
        result = cls._adopt(accumulator, expected_lows, edge, expected_completed, expected_plan_sha256)
        retired = record['retired_boundary_cells']
        _require(type(retired) is int and retired >= 0 and retired + len(accumulator.boundary) <= accumulator.total,
                 'Invalid retired boundary count')
        _require(all(result._touches_pending(point, low) for low, keys in result._by_owner.items() for point in keys),
                 'Snapshot has a non-frontier boundary key')
        result.retired_boundary_cells = retired
        return result
