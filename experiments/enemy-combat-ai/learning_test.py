"""Toy nonstationary combat experiment, not the actual game simulation.

Agent receives constant visible context, never the hidden attack style or payoff
table. It learns only the outcome of its selected action. Seeded exploration
lets it retry previously unsuccessful actions.
"""
import json
import random
from pathlib import Path
from collections import Counter
from small_test import choose, candidates, ZERO

ROOT = Path(__file__).resolve().parent
PERSONALITY = (.6, .4, .3, .2)
ACTIONS = ('attack', 'retreat', 'counter')
ALPHA, DECAY, EPSILON = .2, .995, .15
PHASE_LENGTH = 240
# Explicit synthetic outcome assumptions, not measured gameplay probabilities.
WORLD = {
    'repeated_thrust': {'attack': .1, 'retreat': .3, 'counter': .9},
    'feint_and_wait': {'attack': .9, 'retreat': .2, 'counter': .1},
    'group_rush': {'attack': .1, 'retreat': .9, 'counter': .2},
}
PLAN = ('repeated_thrust', 'feint_and_wait', 'group_rush', 'repeated_thrust')


class Agent:
    def __init__(self, rank='high', learning=True):
        self.rank = rank
        self.learning = learning
        self.memory = {a: {'mean': 0., 'count': 0} for a in ACTIONS}
        self.last_event = -1

    def decide(self, step, seed):
        cs = candidates()
        for c in cs:
            c['learning'] = .08*self.memory[c['tactic']]['mean']
        winner, scores = choose(PERSONALITY, ZERO, cs)
        rng = random.Random(seed*100000+step)
        explore = rng.random() < EPSILON
        action = rng.choice(ACTIONS) if explore else winner['tactic']
        return action, explore, scores

    def observe(self, event, action, reward):
        if event <= self.last_event:
            return False
        self.last_event = event
        if not self.learning:
            return True
        for row in self.memory.values():
            row['mean'] *= DECAY
        row = self.memory[action]
        row['mean'] += ALPHA*(reward-row['mean'])
        row['count'] += 1
        return True

    def end_battle(self):
        if self.rank == 'low':
            self.memory = {a: {'mean': 0., 'count': 0} for a in ACTIONS}
        # No current target, hate or pending attack is serialized in this model.

    def save(self, path):
        path.write_text(json.dumps({'version': 1, 'rank': self.rank,
                                    'memory': self.memory}, indent=2)+'\n')

    @classmethod
    def restore(cls, path):
        data = json.loads(path.read_text())
        if data['version'] != 1:
            raise ValueError('unsupported memory version')
        obj = cls(data['rank'])
        obj.memory = data['memory']
        return obj


def outcome(style, action, step, seed):
    rng = random.Random(90000000+seed*100000+step)
    return 1 if rng.random() < WORLD[style][action] else -1


def simulate(seed, learning=True):
    agent = Agent(learning=learning)
    phases, trace = [], []
    for phase, style in enumerate(PLAN):
        rows = []
        best = max(WORLD[style], key=WORLD[style].get)
        for local in range(PHASE_LENGTH):
            step = phase*PHASE_LENGTH+local
            action, explore, scores = agent.decide(step, seed)
            reward = outcome(style, action, step, seed)
            agent.observe(step, action, reward)
            rows.append(dict(step=step, style=style, action=action,
                             explore=explore, reward=reward, scores=scores,
                             means={a:v['mean'] for a,v in agent.memory.items()}))
        def window(part):
            return dict(counts=dict(Counter(r['action'] for r in part)),
                        best_rate=sum(r['action']==best for r in part)/len(part),
                        success_rate=sum(r['reward']==1 for r in part)/len(part))
        phases.append(dict(style=style, best=best, first40=window(rows[:40]),
                           last80=window(rows[-80:])))
        trace.extend(rows)
    return phases, trace


def main():
    trials = []
    for seed in range(30):
        adaptive,_ = simulate(seed)
        frozen,_ = simulate(seed, learning=False)
        trials.append(dict(seed=seed, adaptive=adaptive, frozen=frozen))
    summary=[]
    for i,style in enumerate(PLAN):
        rates=[t['adaptive'][i]['last80']['best_rate'] for t in trials]
        summary.append(dict(style=style, best=max(WORLD[style],key=WORLD[style].get),
                            mean_best_rate=sum(rates)/30, min_best_rate=min(rates),
                            seeds_above_70_percent=sum(x>=.7 for x in rates),
                            mean_success=sum(t['adaptive'][i]['last80']['success_rate'] for t in trials)/30,
                            frozen_success=sum(t['frozen'][i]['last80']['success_rate'] for t in trials)/30))

    # Save/read actual file, verify decisions resume identically without RNG state.
    high=Agent()
    for step in range(PHASE_LENGTH):
        a,_,_=high.decide(step,7)
        high.observe(step,a,outcome('feint_and_wait',a,step,7))
    before=json.loads(json.dumps(high.memory))
    high.end_battle()
    high.save(ROOT/'memory_checkpoint.json')
    restored=Agent.restore(ROOT/'memory_checkpoint.json')
    persistent = restored.memory==before
    continuation=True
    for step in range(PHASE_LENGTH,PHASE_LENGTH+120):
        a,_,_=high.decide(step,7)
        b,_,_=restored.decide(step,7)
        continuation &= a==b
        reward=outcome('group_rush',a,step,7)
        high.observe(step,a,reward)
        restored.observe(step,b,reward)
        continuation &= high.memory==restored.memory
    low=Agent('low')
    low.memory=json.loads(json.dumps(before))
    low.end_battle()
    low.save(ROOT/'low_rank_checkpoint.json')
    low_reset=Agent.restore(ROOT/'low_rank_checkpoint.json').memory==Agent('low').memory
    snapshot=json.loads(json.dumps(high.memory))
    duplicate_ignored=not high.observe(PHASE_LENGTH+119,'attack',1) and high.memory==snapshot
    # Limitation: duplicate prevention is per running encounter, not restart-safe.
    checks=dict(high_rank_memory_preserved=persistent,
                restored_continuation_identical=continuation,
                low_rank_memory_cleared=low_reset,
                duplicate_in_current_encounter_ignored=duplicate_ignored,
                each_phase_mean_best_rate_at_least_75_percent=all(s['mean_best_rate']>=.75 for s in summary),
                changed_style_improves_over_frozen=all(summary[i]['mean_success']>summary[i]['frozen_success']+.2 for i in (1,2)))
    _,trace=simulate(7)
    result=dict(parameters=dict(alpha=ALPHA,decay=DECAY,epsilon=EPSILON,
                                 phase_length=PHASE_LENGTH,seeds=30),
                synthetic_world=WORLD,summary=summary,checks=checks,trials=trials)
    (ROOT/'learning_results.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'learning_trace_seed7.json').write_text(json.dumps(trace,indent=2)+'\n')
    for s in summary:
        print(s)
    print(checks)
    return all(checks.values())


if __name__=='__main__':
    raise SystemExit(0 if main() else 1)
