#!/usr/bin/env python3
"""Finite structural checks, not a model of Collect, ballots, or Go execution."""
from itertools import product
import json
from pathlib import Path
import random


def make_records(layout, n, rng=None):
    records, known, counters = {}, [set() for _ in range(n)], [0] * n
    for owner, key in layout:
        if rng is not None:
            for other in records:
                if rng.random() < .25:
                    known[owner] |= initial_closure(records, other)
        counters[owner] += 1
        x = owner, counters[owner]
        d0 = tuple(max((j for r, j in known[owner] if r == p and records[r, j]['key'] == key), default=0)
                   for p in range(n))
        records[x] = dict(key=key, d0=d0)
        known[owner].add(x)
    return records


def initial_closure(records, x):
    seen, todo = set(), [x]
    while todo:
        y = todo.pop()
        if y in seen:
            continue
        seen.add(y)
        todo.extend((r, j) for r, j in enumerate(records[y]['d0']) if j)
    return seen


def options(records, x, n):
    return [[j for j in [0] + sorted(y[1] for y in records if y[0] == r and records[y]['key'] == records[x]['key'])
             if j >= records[x]['d0'][r]] for r in range(n)]


def graphs(records, final):
    full, sparse, heads_only = {}, {}, {}
    for x, record in records.items():
        full[x] = {y for y in records if y != x and records[y]['key'] == record['key']
                   and y[1] <= final[x][y[0]]}
        heads_only[x] = {(r, j) for r, j in enumerate(final[x]) if j and (r, j) != x}
        sparse[x] = heads_only[x].copy()
        previous = record['d0'][x[0]]
        if previous:
            sparse[x].add((x[0], previous))
    return full, sparse, heads_only


def reachable(graph, start):
    seen, todo = set(), [start]
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        todo.extend(graph[x] - seen)
    return seen


def check_graph(records, final, check_executed=False):
    full, sparse, _ = graphs(records, final)
    closure = {x: reachable(full, x) for x in records}
    assert all(closure[x] == reachable(sparse, x) for x in records)
    checked = 0
    if check_executed:
        ids = list(records)
        for bits in product((False, True), repeat=len(ids)):
            done = {x for x, bit in zip(ids, bits) if bit}
            if any(not closure[x] <= done for x in done):
                continue
            a = {x: edges - done for x, edges in full.items() if x not in done}
            b = {x: edges - done for x, edges in sparse.items() if x not in done}
            assert all(reachable(a, x) == reachable(b, x) for x in a)
            checked += 1
    return checked


def chain_interval(records, x, r, lower, upper):
    result, j = set(), upper
    while j > lower:
        y = r, j
        assert records[y]['key'] == records[x]['key']
        if y != x:
            result.add(y)
        previous = records[y]['d0'][r]
        assert previous < j
        j = previous
    return result


def check_intervals(records, n):
    checked = 0
    for x in records:
        for r, choices in enumerate(options(records, x, n)):
            for upper in choices:
                lower = records[x]['d0'][r]
                expected = {y for y in records if y != x and y[0] == r
                            and lower < y[1] <= upper and records[y]['key'] == records[x]['key']}
                assert chain_interval(records, x, r, lower, upper) == expected
                checked += 1
    return checked


def examples():
    # A lost, unrelated earlier ordinal is not part of the required data closure.
    records = {(0, 1): dict(key='a', d0=(0, 0)),
               (0, 2): dict(key='b', d0=(0, 0)),
               (1, 1): dict(key='b', d0=(2, 0))}
    survivors = {x: v for x, v in records.items() if x != (0, 1)}
    assert initial_closure(survivors, (1, 1)) == {(1, 1), (0, 2)}
    assert {(0, j) for j in range(1, 3)} - survivors.keys() == {(0, 1)}
    try:
        initial_closure({(1, 1): records[1, 1]}, (1, 1))
    except KeyError:
        pass
    else:
        raise AssertionError('An actual missing dependency must not be skipped')

    # A newer final representative can hide the original predecessor in a cycle.
    records = make_records([(0, 'a')] * 3, 1)
    final = {(0, 1): (0,), (0, 2): (3,), (0, 3): (2,)}
    full, sparse, heads_only = graphs(records, final)
    assert reachable(full, (0, 2)) != reachable(heads_only, (0, 2))
    assert reachable(full, (0, 2)) == reachable(sparse, (0, 2))

    # Validating only the highest representative omits an older witness.
    records = {(0, 1): dict(key='a', d0=(0, 0)),
               (1, 1): dict(key='a', d0=(0, 0)),
               (1, 2): dict(key='a', d0=(1, 1))}
    inspected = chain_interval(records, (0, 1), 1, 0, 2)
    assert inspected == {(1, 1), (1, 2)}
    assert records[1, 2]['d0'][0] >= 1 and records[1, 1]['d0'][0] == 0

    # A finite prefix of an expanding closure has a genuinely undecided tail.
    # After admission pauses, deciding that tail closes the finite SCC.
    for length in (2, 5, 20):
        records = make_records([(0, 'a')] * length, 1)
        final = {(0, i): (i+1,) for i in range(1, length)}
        assert (0, length) in records and (0, length) not in final
        final[0, length] = (length-1,)
        full, sparse, _ = graphs(records, final)
        assert reachable(sparse, (0, 1)) == set(records)
        assert reachable(full, (0, 1)) == reachable(sparse, (0, 1))


def main():
    counts = dict(exhaustive_graphs=0, executed_closed_sets=0, validation_intervals=0,
                  random_graphs=0, seed=20261116)
    for layout in product(product(range(2), range(2)), repeat=4):
        records = make_records(layout, 2)
        counts['validation_intervals'] += check_intervals(records, 2)
        choices = [list(product(*options(records, x, 2))) for x in records]
        for selected in product(*choices):
            counts['executed_closed_sets'] += check_graph(records, dict(zip(records, selected)), True)
            counts['exhaustive_graphs'] += 1
    rng = random.Random(counts['seed'])
    for _ in range(3000):
        n, size = rng.randint(2, 7), rng.randint(5, 50)
        records = make_records([(rng.randrange(n), rng.randrange(4)) for _ in range(size)], n, rng)
        final = {x: tuple(rng.choice(values) for values in options(records, x, n)) for x in records}
        check_graph(records, final)
        counts['validation_intervals'] += check_intervals(records, n)
        counts['random_graphs'] += 1
    examples()
    counts.update(status='passed', examples=['unrelated_hole', 'missing_actual_dependency',
        'initial_predecessor_required', 'validation_must_visit_predecessors', 'finite_closure_after_admission_pause'],
        scope='Dependency-graph refinement and validation-set equivalence under class-based conflicts. '
              'Not a proof or simulation of voting, timing, crash recovery, or real Node scheduling.')
    path = Path(__file__).with_name('results.json')
    path.write_text(json.dumps(counts, indent=2) + '\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
