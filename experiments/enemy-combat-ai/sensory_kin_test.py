"""Synthetic sensory/recruitment experiment. Standard library; no game or API."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import unittest

CROW = (.9, .8, .1)
BEAST = (.4, .7, .9)
VISUAL = (1., .2, 0.)
RANGES = (10., 12., 8.)
THRESHOLD = .3


@dataclass(frozen=True)
class Signal:
    event: str
    kin: str
    channel: int  # vision, hearing, smell
    position: tuple
    time: float = 0.
    strength: float = 1.
    actor: str | None = None  # visible identity only; ignored for sound/smell
    damage: float = 0.


@dataclass
class Enemy:
    senses: tuple = CROW
    kin: str = 'crow'
    position: tuple = (4., 0.)
    goal: tuple | None = None
    hate: dict = field(default_factory=dict)
    credited: set = field(default_factory=set)
    observations: list = field(default_factory=list)

    def receive(self, signal, now=0., transmission=1.):
        """Caller supplies synthetic visibility/acoustic attenuation, not real geometry."""
        if len(self.senses) != 3 or any(not math.isfinite(x) or not 0 <= x <= 1
                                        for x in self.senses):
            raise ValueError('invalid senses')
        if not 0 <= signal.channel < 3:
            raise ValueError('invalid channel')
        if any(not math.isfinite(x) for x in (*self.position, *signal.position,
                                             signal.time, now, signal.strength,
                                             transmission, signal.damage)):
            raise ValueError('nonfinite input')
        if not 0 <= signal.strength <= 1 or not 0 <= transmission <= 1 or signal.damage < 0:
            raise ValueError('invalid stimulus')
        age = now - signal.time
        ttl = (2., 2., 10.)[signal.channel]
        if signal.kin != self.kin or age < 0 or age >= ttl:
            return False
        distance = math.dist(self.position, signal.position)
        reach = max(0., 1 - distance / RANGES[signal.channel])
        intensity = self.senses[signal.channel] * signal.strength * transmission * reach * (1-age/ttl)
        if intensity < THRESHOLD:
            return False
        actor = signal.actor if signal.channel == 0 else None
        self.observations.append({'channel': signal.channel, 'position': signal.position,
                                  'time': signal.time, 'actor': actor, 'intensity': intensity})
        self.goal = signal.position
        if actor is not None and signal.damage > 0 and signal.event not in self.credited:
            self.hate[actor] = min(1., self.hate.get(actor, 0.) + .5 * signal.damage)
            self.credited.add(signal.event)
        return True

    def step(self, dt=.5):
        """Open-plane movement at 1 unit/s, never teleporting; not game pathfinding."""
        if self.goal is None:
            return
        distance = math.dist(self.position, self.goal)
        if distance == 0:
            return
        fraction = min(1., dt / distance)
        self.position = tuple(a + fraction*(b-a) for a, b in zip(self.position, self.goal))

    def decay(self, dt):
        self.hate = {actor: max(0., value - .1*dt) for actor, value in self.hate.items()}


def attack_signals(event='hit-1', actor='player-A', position=(0., 0.)):
    # Alarm is emitted by the struck individual. It carries no attacker identity.
    return (Signal(event, 'crow', 0, position, actor=actor, damage=.4),
            Signal(event, 'crow', 1, position))


def gather(enemy, signals):
    start = enemy.position
    for signal in signals:
        enemy.receive(signal)
    path = [enemy.position]
    for _ in range(8):
        enemy.step()
        path.append(enemy.position)
    return {'start': start, 'end': enemy.position, 'path': path,
            'hate': enemy.hate, 'observations': enemy.observations}


class SensoryKinTests(unittest.TestCase):
    def test_multiple_allies_gather_selectively(self):
        allies = [Enemy(position=(4., 0.)), Enemy(position=(0., 4.), senses=(0., .8, 0.)),
                  Enemy(position=(20., 0.)), Enemy(position=(4., 0.), kin='other')]
        results = [gather(ally, attack_signals()) for ally in allies]
        self.assertEqual([r['end'] for r in results], [(0., 0.), (0., 0.), (20., 0.), (4., 0.)])
        self.assertEqual([ally.hate for ally in allies], [{'player-A': .2}, {}, {}, {}])

    def test_visual_recruits_and_shares_hate(self):
        enemy = Enemy(senses=(.9, 0., 0.))
        result = gather(enemy, attack_signals())
        self.assertEqual(result['end'], (0., 0.))
        self.assertEqual(enemy.hate, {'player-A': .2})
        self.assertTrue(all(math.dist(a, b) <= .5 for a, b in zip(result['path'], result['path'][1:])))

    def test_alarm_recruits_without_identity(self):
        enemy = Enemy(senses=(0., .8, 0.))
        self.assertEqual(gather(enemy, attack_signals())['end'], (0., 0.))
        self.assertEqual(enemy.hate, {})
        self.assertIsNone(enemy.observations[0]['actor'])

    def test_sound_cannot_leak_identity(self):
        enemy = Enemy()
        enemy.receive(Signal('x', 'crow', 1, (0., 0.), actor='hidden', damage=1.))
        self.assertEqual(enemy.hate, {})
        self.assertIsNone(enemy.observations[0]['actor'])

    def test_same_sound_different_senses(self):
        alarm = attack_signals()[1]
        self.assertTrue(Enemy(senses=CROW).receive(alarm))
        visual = Enemy(senses=VISUAL)
        self.assertFalse(visual.receive(alarm))
        self.assertIsNone(visual.goal)

    def test_same_scent_different_senses(self):
        scent = Signal('trail', 'crow', 2, (0., 0.))
        self.assertTrue(Enemy(senses=BEAST).receive(scent))
        self.assertFalse(Enemy(senses=CROW).receive(scent))

    def test_zero_senses_do_not_move(self):
        self.assertEqual(gather(Enemy(senses=(0., 0., 0.)), attack_signals())['end'], (4., 0.))

    def test_out_of_range_does_not_move(self):
        self.assertEqual(gather(Enemy(position=(20., 0.)), attack_signals())['end'], (20., 0.))

    def test_occluded_vision_but_audible_alarm(self):
        enemy = Enemy()
        vision, alarm = attack_signals()
        self.assertFalse(enemy.receive(vision, transmission=0.))
        self.assertTrue(enemy.receive(alarm))
        self.assertEqual(enemy.hate, {})

    def test_no_transmission_no_response(self):
        enemy = Enemy()
        for signal in attack_signals():
            self.assertFalse(enemy.receive(signal, transmission=0.))
        self.assertIsNone(enemy.goal)

    def test_other_kin_not_recruited(self):
        self.assertEqual(gather(Enemy(kin='other'), attack_signals())['end'], (4., 0.))

    def test_duplicate_and_dual_channel_not_double_counted(self):
        enemy = Enemy()
        for _ in range(10):
            for signal in attack_signals():
                enemy.receive(signal)
        self.assertEqual(enemy.hate, {'player-A': .2})

    def test_hearing_then_visual_identification(self):
        enemy = Enemy()
        vision, alarm = attack_signals()
        enemy.receive(alarm)
        self.assertEqual(enemy.hate, {})
        enemy.receive(vision)
        self.assertEqual(enemy.hate, {'player-A': .2})

    def test_multiple_attackers_separate(self):
        enemy = Enemy()
        enemy.receive(attack_signals()[0])
        enemy.receive(attack_signals('hit-2', 'player-B')[0])
        self.assertEqual(enemy.hate, {'player-A': .2, 'player-B': .2})

    def test_hate_cap_and_decay(self):
        enemy = Enemy()
        for i in range(20):
            enemy.receive(attack_signals(str(i))[0])
        self.assertEqual(enemy.hate['player-A'], 1.)
        enemy.decay(4.)
        self.assertAlmostEqual(enemy.hate['player-A'], .6)

    def test_stale_scent_not_current_position(self):
        enemy = Enemy(senses=BEAST)
        trace = Signal('trail', 'crow', 2, (0., 0.), actor='hidden')
        self.assertTrue(enemy.receive(trace, now=1.))
        self.assertEqual(enemy.goal, (0., 0.))
        self.assertIsNone(enemy.observations[-1]['actor'])
        self.assertFalse(Enemy(senses=BEAST).receive(trace, now=10.))

    def test_zero_stimulus_and_expired_alarm(self):
        enemy = Enemy()
        self.assertFalse(enemy.receive(Signal('x', 'crow', 1, (0., 0.), strength=0.)))
        self.assertFalse(enemy.receive(attack_signals()[1], now=2.))

    def test_invalid_sensitivity(self):
        with self.assertRaises(ValueError):
            Enemy(senses=(math.nan, 1., 1.)).receive(attack_signals()[0])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SensoryKinTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    demonstrations = {
        'visual_only': gather(Enemy(senses=(.9, 0., 0.)), attack_signals()),
        'alarm_only': gather(Enemy(senses=(0., .8, 0.)), attack_signals()),
        'weak_hearing': gather(Enemy(senses=VISUAL), [attack_signals()[1]]),
        'scent_tracker': gather(Enemy(senses=BEAST), [Signal('trail', 'crow', 2, (0., 0.))]),
    }
    output = {'tests': result.testsRun, 'passed': result.wasSuccessful(), 'scenarios': demonstrations}
    Path(__file__).with_name('sensory_kin_results.json').write_text(json.dumps(output, indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
