"""Offline, source-backed template dialogue experiment. No generated prose/API.

Observations are explicit synthetic events, not inferred from the numerical
learning test: that test does not yet store identities or attack evidence.
"""
import copy
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STYLES = {'thrust', 'flank', 'feint'}
LINES = {'same_thrust': 'また、その間合いか。',
         'same_flank': '脇を空けるのを待っているのか。',
         'changed': '……前とは違うな。'}


def pattern(events):
    if len(events) < 3:
        return None
    counts = Counter(e['kind'] for e in events)
    kind, count = counts.most_common(1)[0]
    return kind if count / len(events) >= .75 else None


class Voice:
    def __init__(self, scope='room-A/session-A', boss='crow-boss', rank='high'):
        self.scope, self.boss, self.rank = scope, boss, rank
        self.history = []
        self.spoken = []
        self.current = None

    def begin(self, battle):
        self.current = {'battle': battle, 'events': []}

    def observe(self, event_id, actor, kind):
        if self.current is None or kind not in STYLES:
            raise ValueError('invalid encounter/observation')
        if any(e['id'] == event_id for e in self.current['events']):
            return False
        self.current['events'].append(dict(id=event_id, actor=actor, kind=kind))
        return True

    def finish(self):
        if self.current is None:
            return
        if self.rank == 'high':
            record = dict(scope=self.scope, boss=self.boss, **copy.deepcopy(self.current))
            self.history = [r for r in self.history if r['battle'] != record['battle']]
            self.history = (self.history + [record])[-16:]
        self.current = None

    def speak(self, actor, can_speak=True):
        if not can_speak or self.current is None or not actor:
            return None
        key = [self.scope, self.boss, self.current['battle']]
        if key in self.spoken:  # At most one memory line per encounter in this prototype.
            return None
        now = [e for e in self.current['events'] if e['actor'] == actor]
        current_kind = pattern(now)
        if not current_kind:
            return None
        old = None
        old_events = []
        for record in reversed(self.history):
            if (record['scope'] != self.scope or record['boss'] != self.boss
                    or record['battle'] == self.current['battle']):
                continue
            events = [e for e in record['events'] if e['actor'] == actor]
            if pattern(events):
                old, old_events = record, events
                break
        if old is None:
            return None
        previous_kind = pattern(old_events)
        template = ('changed' if previous_kind != current_kind else
                    {'thrust': 'same_thrust', 'flank': 'same_flank'}.get(current_kind))
        if template is None:
            return None
        self.spoken = (self.spoken + [key])[-64:]
        return dict(text=LINES[template], template=template, recipient=actor,
                    previous_battle=old['battle'], current_battle=self.current['battle'],
                    previous_evidence=[e['id'] for e in old_events],
                    current_evidence=[e['id'] for e in now])

    def save(self, path):
        # Current observation/action state is deliberately not persisted.
        path.write_text(json.dumps(dict(version=1, scope=self.scope, boss=self.boss,
                                        rank=self.rank, history=self.history,
                                        spoken=self.spoken), ensure_ascii=False, indent=2)+'\n')

    @classmethod
    def restore(cls, path):
        data = json.loads(path.read_text())
        if data['version'] != 1:
            raise ValueError('unsupported memory schema')
        obj = cls(data['scope'], data['boss'], data['rank'])
        obj.history, obj.spoken = data['history'], data['spoken']
        return obj


def observations(voice, actor='player-A', kind='thrust', count=4):
    for n in range(count):
        voice.observe(f"{voice.current['battle']}:{actor}:{n}", actor, kind)


def main():
    results=[]
    def check(name, actual, expected):
        passed = actual == expected
        results.append(dict(name=name, actual=actual, expected=expected, passed=passed))
        print('PASS' if passed else 'FAIL', name, actual)

    path=ROOT/'dialogue_memory.json'
    original=Voice()
    original.begin('fight-1')
    observations(original)
    check('first_encounter_has_no_recollection', original.speak('player-A'), None)
    original.finish()
    original.save(path)
    v=Voice.restore(path)
    check('saved_history_roundtrip',v.history,original.history)
    check('no_current_encounter_restored',v.current,None)
    v.begin('fight-2')
    observations(v)
    utterance=v.speak('player-A')
    check('rematch_same_thrust',utterance['text'] if utterance else None,LINES['same_thrust'])
    check('evidence_points_to_previous_battle',utterance['previous_battle'] if utterance else None,'fight-1')
    check('same_encounter_repetition_suppressed',v.speak('player-A'),None)
    v.save(ROOT/'dialogue_after_speech.json')
    reload=Voice.restore(ROOT/'dialogue_after_speech.json')
    reload.begin('fight-2')
    observations(reload)
    check('same_encounter_reload_does_not_repeat',reload.speak('player-A'),None)

    v=Voice.restore(path)
    v.begin('fight-3')
    observations(v,kind='flank')
    changed=v.speak('player-A')
    check('changed_attack_after_restore',changed['text'] if changed else None,LINES['changed'])

    # New identity despite possibly identical display name (names are never inputs).
    v=Voice.restore(path)
    v.begin('fight-new-person')
    observations(v,actor='player-B')
    check('different_id_no_personal_recollection',v.speak('player-B'),None)

    for field,value in [('scope','room-B/session-B'),('boss','different-boss')]:
        v=Voice.restore(path)
        setattr(v,field,value)
        v.begin('fight-other-scope')
        observations(v)
        check('no_cross_'+field+'_memory',v.speak('player-A'),None)

    v=Voice.restore(path)
    v.begin('fight-1')
    observations(v)
    check('same_battle_is_not_previous_battle',v.speak('player-A'),None)
    v.begin('fight-uncertain')
    observations(v,count=1)
    check('insufficient_current_evidence_is_silent',v.speak('player-A'),None)
    for i,k in enumerate(['thrust','flank','flank']):
        v.observe(f'mixed:{i}','player-A',k)
    check('ambiguous_current_pattern_is_silent',v.speak('player-A'),None)

    weak=Voice()
    weak.begin('weak-old')
    observations(weak,count=1)
    weak.finish()
    weak.save(ROOT/'dialogue_weak_memory.json')
    weak=Voice.restore(ROOT/'dialogue_weak_memory.json')
    weak.begin('weak-new')
    observations(weak)
    check('insufficient_old_evidence_is_silent',weak.speak('player-A'),None)

    low=Voice(rank='low')
    low.begin('low-old')
    observations(low)
    low.finish()
    low.save(ROOT/'dialogue_low_memory.json')
    low=Voice.restore(ROOT/'dialogue_low_memory.json')
    low.begin('low-new')
    observations(low)
    check('low_rank_does_not_recall_previous_battle',low.speak('player-A'),None)

    v=Voice.restore(path)
    v.begin('cannot-speak')
    observations(v)
    check('ability_disabled_is_silent',v.speak('player-A',False),None)
    v=Voice.restore(path)
    v.history=[]
    v.begin('history-missing')
    observations(v)
    check('history_missing_is_silent',v.speak('player-A'),None)

    v=Voice()
    v.begin('duplicate')
    for _ in range(8):
        v.observe('single-event','player-A','thrust')
    check('duplicate_observation_not_extra_evidence',len(v.current['events']),1)

    # Per-player observations are not combined to fabricate a trend.
    v=Voice.restore(path)
    v.begin('multiplayer')
    observations(v,actor='player-B',kind='flank')
    observations(v,actor='player-A')
    check('new_player_silent_despite_known_player_present',v.speak('player-B'),None)
    multi=v.speak('player-A')
    check('known_player_keeps_own_pattern',multi['text'] if multi else None,LINES['same_thrust'])
    check('speech_recipient_is_known_player',multi['recipient'] if multi else None,'player-A')

    result=dict(cases=results,passed=all(x['passed'] for x in results),
                sample_rematch=utterance,sample_changed=changed,
                scope='Synthetic event memory and template selection only; no game integration.')
    (ROOT/'dialogue_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Overall:',result['passed'], 'cases:',len(results))
    return result['passed']


if __name__=='__main__':
    raise SystemExit(0 if main() else 1)
