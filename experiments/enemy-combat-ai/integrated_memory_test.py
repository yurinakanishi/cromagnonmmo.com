"""One episodic store feeds both learned choices and evidence-based dialogue.

Synthetic outcome model only. No game, network, API or LLM. No separately
authored dialogue history, and no serialized learned-value cache.
"""
import copy
import json
import random
from collections import Counter
from pathlib import Path
from small_test import choose, candidates, ZERO
from learning_test import PERSONALITY, ACTIONS, ALPHA, DECAY, EPSILON

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'integrated-output'
# Assumptions of this toy world, not measurements of the game.
PAYOFF = {
    'thrust': {'attack': .1, 'retreat': .3, 'counter': .9},
    'flank': {'attack': .1, 'retreat': .9, 'counter': .2},
    'feint': {'attack': .9, 'retreat': .2, 'counter': .1},
}
TEXT = {'thrust': 'また、その間合いか。',
        'flank': '脇を空けるのを待っているのか。',
        'feint': 'また、こちらの出方を待つのか。',
        'changed': '……前とは違うな。'}


def dominant(events):
    if len(events) < 3:
        return None
    kind, count = Counter(e['observed'] for e in events).most_common(1)[0]
    return kind if count / len(events) >= .75 else None


class Boss:
    def __init__(self, rank='high', scope='room-A/session-A', boss='crow-boss'):
        self.rank, self.scope, self.boss = rank, scope, boss
        self.episodes = []
        self.active = None
        self.spoken = []

    def begin(self, encounter):
        if self.active is not None:
            raise ValueError('finish active encounter first')
        if any(r['id'] == encounter for r in self.episodes):
            raise ValueError('committed encounter cannot be reused')
        self.active = dict(id=encounter, scope=self.scope, boss=self.boss, events=[])

    def relevant(self, actor, include_active=True):
        records = self.episodes + ([self.active] if include_active and self.active else [])
        return [e for r in records if r['scope'] == self.scope and r['boss'] == self.boss
                for e in r['events'] if e['actor'] == actor]

    def learned_view(self, actor):
        # Derived entirely from the same events used by dialogue.
        values = {a: 0. for a in ACTIONS}
        events = self.relevant(actor)
        for e in events:
            for a in ACTIONS:
                values[a] *= DECAY
            a = e['action']
            values[a] += ALPHA * (e['reward'] - values[a])
        return values, [e['id'] for e in events]

    def decide(self, actor, step=0, seed=0, explore=False):
        values, evidence = self.learned_view(actor)
        cs = candidates(target=actor)
        for c in cs:
            c['learning'] = .08 * values[c['tactic']]
        winner, scores = choose(PERSONALITY, ZERO, cs)
        rng = random.Random(seed * 100000 + step)
        exploratory = explore and rng.random() < EPSILON
        action = rng.choice(ACTIONS) if exploratory else winner['tactic']
        return dict(action=action, policy_action=winner['tactic'],
                    exploratory=exploratory, values=values,
                    evidence=evidence, scores=scores)

    def record_result(self, event_id, actor, observed, action, reward):
        if self.active is None or not actor or observed not in PAYOFF or action not in ACTIONS or reward not in (-1,1):
            raise ValueError('invalid observed outcome')
        records = self.episodes + [self.active]
        if any(e['id'] == event_id for r in records for e in r['events']):
            return False
        if len(self.active['events']) >= 256:
            raise ValueError('prototype encounter capacity reached')
        self.active['events'].append(dict(id=event_id, encounter=self.active['id'],
            actor=actor, observed=observed, action=action, reward=reward))
        return True

    def speak(self, actor):
        if not self.active:
            return None
        key = [self.scope, self.boss, self.active['id']]
        if key in self.spoken:
            return None
        current = [e for e in self.active['events'] if e['actor'] == actor]
        now_kind = dominant(current)
        if now_kind is None:
            return None
        for old in reversed(self.episodes):
            if old['scope'] != self.scope or old['boss'] != self.boss:
                continue
            events = [e for e in old['events'] if e['actor'] == actor]
            old_kind = dominant(events)
            if old_kind is None:
                continue
            template = now_kind if now_kind == old_kind else 'changed'
            self.spoken = (self.spoken + [key])[-64:]
            return dict(text=TEXT[template], template=template, actor=actor,
                        prior_encounter=old['id'], current_encounter=self.active['id'],
                        prior_evidence=[e['id'] for e in events],
                        current_evidence=[e['id'] for e in current])
        return None

    def finish(self):
        if self.active and self.rank == 'high':
            self.episodes = (self.episodes + [copy.deepcopy(self.active)])[-8:]
        self.active = None

    def save(self, path):
        data = dict(version=1, rank=self.rank, scope=self.scope, boss=self.boss,
                    episodes=self.episodes, spoken=self.spoken)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
        tmp.replace(path)

    @classmethod
    def restore(cls, path):
        d = json.loads(path.read_text())
        if d['version'] != 1:
            raise ValueError('unsupported memory schema')
        obj = cls(d['rank'], d['scope'], d['boss'])
        obj.episodes, obj.spoken = d['episodes'], d['spoken']
        return obj


def battle(boss, style, encounter, seed, actor='player-A', steps=240, offset=0):
    boss.begin(encounter)
    rows, utterance = [], None
    for i in range(steps):
        step = offset + i
        decision = boss.decide(actor,step,seed,explore=True)
        # World resolves the result only after the decision. The agent does
        # not receive the hidden payoff table or counterfactual outcomes.
        rng = random.Random(90000000 + seed*100000 + step)
        reward = 1 if rng.random() < PAYOFF[style][decision['action']] else -1
        event_id = f'{encounter}:{actor}:{i}'
        boss.record_result(event_id,actor,style,decision['action'],reward)
        line = boss.speak(actor)
        if line:
            utterance = line
        rows.append(dict(step=step,action=decision['action'],reward=reward,
                         exploratory=decision['exploratory'],event=event_id))
    return rows, utterance


def main():
    OUT.mkdir(exist_ok=True)
    checks = []
    def check(name, condition):
        checks.append(dict(name=name,passed=bool(condition)))
        print('PASS' if condition else 'FAIL',name)

    boss=Boss()
    initial=boss.decide('player-A')
    first,first_line=battle(boss,'flank','battle-1',7)
    check('first_encounter_silent',first_line is None)
    boss.finish()
    checkpoint=OUT/'shared_memory.json'
    boss.save(checkpoint)
    restored=Boss.restore(checkpoint)
    learned=restored.decide('player-A')
    check('save_restore_preserves_shared_history',restored.episodes==boss.episodes)
    check('no_active_plan_restored',restored.active is None)
    check('experience_changes_policy',initial['action']=='counter' and learned['action']=='retreat')
    check('restored_policy_equals_uninterrupted',learned==boss.decide('player-A'))
    repeat,line=battle(restored,'flank','battle-2',7,steps=40,offset=240)
    check('rematch_line_matches_flank_memory',line is not None and line['text']==TEXT['flank'])
    check('decision_and_line_reference_same_previous_events',
          line is not None and set(line['prior_evidence'])==set(learned['evidence']))
    check('rematch_reuses_retreat',sum(r['action']=='retreat' for r in repeat)/40>=.7)
    check('one_line_per_encounter',restored.speak('player-A') is None)

    restored.save(OUT/'after_speech.json')
    speaking_reload=Boss.restore(OUT/'after_speech.json')
    _,repeated_line=battle(speaking_reload,'flank','battle-2',7,steps=4,offset=240)
    check('reload_does_not_repeat_line',repeated_line is None)

    # Removal of the sole shared memory removes both learning and recollection.
    blank=Boss.restore(checkpoint)
    blank.episodes=[]
    check('removing_shared_memory_removes_learned_preference',blank.decide('player-A')['action']==initial['action'])
    _,blank_line=battle(blank,'flank','no-memory',7,steps=4)
    check('removing_shared_memory_removes_recollection',blank_line is None)
    stranger=Boss.restore(checkpoint)
    check('other_identity_has_no_learned_preference',stranger.decide('player-B')['action']==initial['action'])
    _,stranger_line=battle(stranger,'flank','stranger',7,actor='player-B',steps=4)
    check('other_identity_has_no_recollection',stranger_line is None)
    for field,value in [('scope','different-room/session'),('boss','other-boss')]:
        other=Boss.restore(checkpoint)
        setattr(other,field,value)
        check('no_cross_'+field+'_learning',other.decide('player-A')['action']==initial['action'])
        _,other_line=battle(other,'flank','scope-test',7,steps=4)
        check('no_cross_'+field+'_speech',other_line is None)

    low=Boss('low')
    battle(low,'flank','low-1',7)
    low.finish()
    low.save(OUT/'low_memory.json')
    low=Boss.restore(OUT/'low_memory.json')
    check('low_rank_forgets_learned_preference',low.decide('player-A')['action']==initial['action'])
    _,low_line=battle(low,'flank','low-2',7,steps=4)
    check('low_rank_forgets_recollection',low_line is None)

    duplicate=Boss.restore(checkpoint)
    duplicate.begin('duplicate-test')
    before=duplicate.learned_view('player-A')
    event=duplicate.episodes[0]['events'][0]
    accepted=duplicate.record_result(event['id'],event['actor'],event['observed'],event['action'],event['reward'])
    check('saved_event_replay_not_learned_twice',not accepted and before==duplicate.learned_view('player-A'))

    # New encounter, new attack style, history retained.
    changed=Boss.restore(checkpoint)
    changed_rows,changed_line=battle(changed,'feint','changed',7,offset=240)
    check('different_style_gets_changed_line',changed_line is not None and changed_line['text']==TEXT['changed'])
    check('different_style_relearns_attack',sum(r['action']=='attack' for r in changed_rows[-80:])/80>=.7)
    changed.finish()
    changed.save(OUT/'changed_memory.json')
    next_boss=Boss.restore(OUT/'changed_memory.json')
    check('relearned_choice_survives_second_save',next_boss.decide('player-A')['action']=='attack')
    _,next_line=battle(next_boss,'feint','third',7,steps=4,offset=480)
    check('latest_committed_experience_drives_line',next_line is not None and next_line['template']=='feint'
          and next_line['prior_encounter']=='changed')

    trials=[]
    for seed in range(30):
        a=Boss()
        battle(a,'flank','old',seed)
        a.finish()
        path=OUT/f'trial-{seed}.json'
        a.save(path)
        b=Boss.restore(path)
        remembered=b.decide('player-A')['action']
        same,same_line=battle(b,'flank','same',seed,steps=40,offset=240)
        c=Boss.restore(path)
        switched,switched_line=battle(c,'feint','switch',seed,offset=240)
        trials.append(dict(seed=seed,remembered_action=remembered,
            same_line=same_line['template'] if same_line else None,
            same_retreat_rate=sum(r['action']=='retreat' for r in same)/40,
            changed_line=switched_line['template'] if switched_line else None,
            first40_attack_rate=sum(r['action']=='attack' for r in switched[:40])/40,
            last80_attack_rate=sum(r['action']=='attack' for r in switched[-80:])/80))
    summary=dict(seeds=30,remembered_retreat_count=sum(t['remembered_action']=='retreat' for t in trials),
        correct_same_line_count=sum(t['same_line']=='flank' for t in trials),
        correct_changed_line_count=sum(t['changed_line']=='changed' for t in trials),
        mean_same_retreat_rate=sum(t['same_retreat_rate'] for t in trials)/30,
        mean_first40_attack_rate=sum(t['first40_attack_rate'] for t in trials)/30,
        mean_last80_attack_rate=sum(t['last80_attack_rate'] for t in trials)/30,
        min_last80_attack_rate=min(t['last80_attack_rate'] for t in trials))
    check('all_seeds_have_evidence_based_lines',summary['correct_same_line_count']==30 and summary['correct_changed_line_count']==30)
    check('mean_same_style_retreat_above_75_percent',summary['mean_same_retreat_rate']>=.75)
    check('mean_changed_style_attack_above_75_percent',summary['mean_last80_attack_rate']>=.75)
    result=dict(passed=all(x['passed'] for x in checks),checks=checks,summary=summary,trials=trials,
        examples=dict(initial=initial['action'],remembered=learned['action'],rematch=line,changed=changed_line,third=next_line),
        assumptions=PAYOFF,parameters=dict(alpha=ALPHA,decay=DECAY,epsilon=EPSILON),
        scope='Shared synthetic episodic memory; no game integration.')
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'trace_seed7.json').write_text(json.dumps(dict(first=first,rematch=repeat,changed=changed_rows),ensure_ascii=False,indent=2)+'\n')
    print(summary)
    print('Overall:',result['passed'],'checks:',len(checks))
    return result['passed']


if __name__=='__main__':
    raise SystemExit(0 if main() else 1)
