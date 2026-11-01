"""Offline numerical experiment; no game code, network, dependencies or LLM."""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Axes: aggression, preservation, caution, opportunity.
TACTICS = {
    'attack': (1, -.4, -.5, .2),
    'retreat': (-.5, 1, .6, -.2),
    'counter': (.2, .1, .3, 1),
}
WEIGHTS = (.4, .2, .4)  # personality, mood, observed context: experimental only
ZERO = (0, 0, 0, 0)
BOLD = (1, .1, .1, .1)
CAUTIOUS = (.1, 1, .9, .1)


def bound(x, low, high):
    if not math.isfinite(x):
        raise ValueError('nonfinite value')
    return max(low, min(high, x))


def vector(v):
    if len(v) != 4 or any(not math.isfinite(x) or not 0 <= x <= 1 for x in v):
        raise ValueError('expected four finite unit values')
    return v


def query(p, m, o, old=False):
    for v in (p, m, o):
        vector(v)
    return tuple(min(1, sum(t)) if old else sum(w*x for w, x in zip(WEIGHTS, t))
                 for t in zip(p, m, o))


def alignment(q, tactic):
    a = TACTICS[tactic]
    norm = math.sqrt(sum(x*x for x in a))
    return sum(x*y/norm for x, y in zip(q, a))/2


def choose(p, m, candidates, current=None):
    rows = []
    for c in candidates:
        if not c.get('legal', True):
            continue
        q = query(p, m, c['context'])
        base = alignment(q, c['tactic'])
        learning = bound(c.get('learning', 0), -.08, .08)
        hate = .08 * bound(c.get('hate', 0), 0, 1)
        continuity = .03 if c['target'] == current else 0
        rows.append({**c, 'base': base, 'learning_term': learning,
                     'hate_term': hate, 'continuity_term': continuity,
                     'score': base+learning+hate+continuity})
    # Stable ties independent of input order.
    rows.sort(key=lambda r: (-r['score'], r['target'], r['tactic']))
    return (rows[0] if rows else None), rows


def candidates(context=ZERO, target='A'):
    return [dict(target=target, tactic=t, context=context) for t in TACTICS]


def run():
    cases = []
    def record(name, p, m, cs, expected=None, current=None):
        win, rows = choose(p, m, cs, current)
        selected = None if win is None else (win['target'], win['tactic'])
        passed = selected == expected
        cases.append(dict(name=name, expected=expected, selected=selected,
                          passed=passed, scores=rows))
        return win

    record('same_scene_bold', BOLD, ZERO, candidates(), ('A', 'attack'))
    record('same_scene_cautious', CAUTIOUS, ZERO, candidates(), ('A', 'retreat'))
    record('surrounded_bold', BOLD, ZERO, candidates((.2, 1, .9, .1)), ('A', 'retreat'))
    record('observed_opening', BOLD, ZERO, candidates((.1, .2, .3, 1)), ('A', 'counter'))
    illegal = candidates(target='illegal')
    for c in illegal:
        c.update(legal=False, hate=1000)
    record('illegal_target_high_hate', BOLD, ZERO,
           illegal+candidates(target='legal'), ('legal', 'attack'))
    record('no_legal_candidate', BOLD, ZERO, illegal, None)
    two = candidates(target='A')+candidates(target='B')
    for c in two:
        c['hate'] = .9 if c['target'] == 'B' else .1
    record('hate_selects_target', BOLD, ZERO, two, ('B', 'attack'))
    record('continuity_resists_small_hate_difference', BOLD, ZERO,
           [dict(c, hate=.2 if c['target']=='B' else .1) for c in two],
           ('A', 'attack'), current='A')
    scarred = candidates((.1, .2, .3, 1))
    for c in scarred:
        c['learning'] = -.08 if c['tactic']=='counter' else 0
    record('old_failure_does_not_forbid_new_opportunity', BOLD, ZERO,
           scarred, ('A', 'counter'))

    # Compare only aggregation, holding the tactic matrix fixed.
    m = o = (.8, .8, .8, .8)
    old_a, old_b = query(BOLD,m,o,True), query(CAUTIOUS,m,o,True)
    new_a, new_b = query(BOLD,m,o), query(CAUTIOUS,m,o)
    saturation = dict(old_bold=old_a, old_cautious=old_b,
                      new_bold=new_a, new_cautious=new_b,
                      old_lost_difference=old_a==old_b,
                      new_preserved_difference=new_a!=new_b)

    rng = random.Random(20261101)
    invariants = True
    for _ in range(1000):
        p,m,o = [tuple(rng.random() for _ in range(4)) for _ in range(3)]
        cs = candidates(o)
        for c in cs:
            c.update(hate=rng.uniform(-5,5), learning=rng.uniform(-2,2),
                     legal=rng.random()>.3)
        win, rows = choose(p,m,cs)
        shuffled = list(cs)
        rng.shuffle(shuffled)
        again,_ = choose(p,m,shuffled)
        invariants &= win==again
        invariants &= all(r['legal'] and math.isfinite(r['score']) and
                          -.08<=r['learning_term']<=.08 and 0<=r['hate_term']<=.08
                          for r in rows)
    invalid_rejected = False
    try:
        choose((float('nan'),0,0,0), ZERO, candidates())
    except ValueError:
        invalid_rejected = True
    result = dict(cases=cases, saturation=saturation, random_cases=1000,
                  invariants_passed=invariants, invalid_rejected=invalid_rejected,
                  scope='Numerical selector only; no game simulation or persistence.')
    result['passed'] = (all(c['passed'] for c in cases) and invariants and
                        invalid_rejected and saturation['old_lost_difference'] and
                        saturation['new_preserved_difference'])
    (ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for c in cases:
        print(('PASS' if c['passed'] else 'FAIL'), c['name'], c['selected'])
    print('Aggregation:', saturation)
    print('1000 invariant cases:', invariants, 'invalid input rejected:', invalid_rejected)
    print('Overall:', result['passed'])
    return result


if __name__ == '__main__':
    raise SystemExit(0 if run()['passed'] else 1)
