"""Synthetic herd/guardian model; no game imports, API, damage or taming changes."""
import json
import math
import unittest
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Mammoth:
    id: str
    x: float
    z: float = 0
    herd: str = 'A'
    child: bool = False
    alive: bool = True
    rider: str | None = None
    companions: set = field(default_factory=set)
    role: str = 'idle'
    target: str | None = None
    guardian: str | None = None
    retreating: bool = False


def distance(a, b):
    return math.hypot(a.x-b.x, a.z-b.z)


def step_toward(a, goal, amount=.5):
    d = distance(a, goal)
    if d:
        f = min(1, amount/d)
        a.x += (goal.x-a.x)*f
        a.z += (goal.z-a.z)*f


def tick(animals, threat, victim, informed, attacked=True):
    """One threat, one calf per herd. Informed IDs stand in for sensed events.

    Guardian selection is deterministic and is recalculated when availability changes.
    No collision geometry; companions relations are experimental inputs, not game ownership.
    """
    # Authoritative simplified death event; persists after the calf is removed.
    retreating_herds = {a.herd for a in animals if a.retreating or (a.child and not a.alive)}
    for a in animals:
        if a.herd in retreating_herds:
            a.retreating = True
    children = [a for a in animals if a.child and a.alive and not a.retreating]
    guardians = {}
    for child in children:
        candidates = [a for a in animals if not a.child and a.alive and not a.rider and a.herd == child.herd]
        if candidates:
            if child.guardian not in {a.id for a in candidates}:
                child.guardian = min(candidates, key=lambda a: (distance(a, child), a.id)).id
            guardians[child.id] = child.guardian
        else:
            child.guardian = None
    for a in animals:
        a.target = None
        if not a.alive:
            a.role = 'dead'
            continue
        if a.retreating:
            a.guardian = None
            if a.rider:
                a.role = 'retreat-pending-rider'
            else:
                a.role = 'retreat'
                step_toward(a, Mammoth('refuge', -10, 0))
            continue
        if a.rider:
            a.role = 'rider-control'
            continue
        if a.child:
            a.role = 'shelter'
            continue
        child = next((c for c in children if c.herd == a.herd), None)
        known = a.id in informed and (victim.herd == a.herd or victim.id in a.companions)
        hostile = known and attacked
        if child and guardians.get(child.id) == a.id:
            a.role = 'guard'
            if hostile:
                a.target = threat.id
                # Interpose near calf; never pursue the attacker beyond the escort band.
                d = distance(child, threat)
                goal = Mammoth('interpose', child.x, child.z)
                if d:
                    goal.x += (threat.x-child.x)*min(2., d)/d
                    goal.z += (threat.z-child.z)*min(2., d)/d
            else:
                goal = child
            step_toward(a, goal)
        elif hostile:
            if child and distance(threat, child) > 6:
                a.role = 'return'
                step_toward(a, child)
            else:
                a.role = 'assist'
                a.target = threat.id
                step_toward(a, threat)
        elif known and threat.id not in a.companions:
            a.role = 'warn'
        else:
            a.role = 'idle'
    return guardians


def fixture():
    return [Mammoth('calf',0,child=True), Mammoth('mother',1), Mammoth('ally',3), Mammoth('other',3,herd='B')]


class HerdTests(unittest.TestCase):
    def test_calf_death_latches_herd_retreat(self):
        herd=fixture();herd[0].alive=False;threat=Mammoth('enemy',20)
        tick(herd,threat,herd[0],{'mother','ally'})
        self.assertEqual([a.role for a in herd],['dead','retreat','retreat','idle'])
        victim=herd.pop(0)
        for _ in range(40):
            tick(herd,threat,victim,{'mother','ally'})
            self.assertTrue(all(a.target is None for a in herd))
        self.assertEqual([a.x for a in herd[:2]],[-10,-10])

    def test_retreat_overrides_tamed_companion_assistance(self):
        herd=fixture();herd[0].alive=False
        for a in herd: a.companions.add('friend')
        tick(herd,Mammoth('enemy',5),Mammoth('friend',4,herd='human'),{'mother','ally'})
        self.assertEqual(herd[1].role,'retreat')
        self.assertEqual(herd[2].role,'retreat')

    def test_retreat_persists_through_riding_and_dismount(self):
        herd=fixture();herd[0].alive=False;herd[1].rider='rider';before=herd[1].x
        tick(herd,Mammoth('enemy',5),herd[0],{'mother','ally'})
        self.assertEqual(herd[1].role,'retreat-pending-rider')
        self.assertEqual(herd[1].x,before)
        herd[1].rider=None
        tick(herd,Mammoth('enemy',5),herd[0],{'mother','ally'})
        self.assertEqual(herd[1].role,'retreat')
        self.assertLess(herd[1].x,before)

    def test_calf_guard_and_herd_assistance(self):
        herd=fixture(); threat=Mammoth('player',5)
        tick(herd,threat,herd[0],{'mother','ally','other'})
        self.assertEqual([a.role for a in herd],['shelter','guard','assist','idle'])
        self.assertEqual([herd[1].target,herd[2].target],['player','player'])
        self.assertLess(herd[2].x,threat.x)
        self.assertGreater(herd[2].x,3)

    def test_fleeing_attacker_does_not_draw_every_adult_away(self):
        herd=fixture(); threat=Mammoth('player',4)
        for _ in range(80):
            threat.x+=.3
            tick(herd,threat,herd[0],{'mother','ally'})
            self.assertLessEqual(distance(herd[1],herd[0]),2.000001)
        self.assertEqual(herd[2].role,'return')
        self.assertLessEqual(distance(herd[2],herd[0]),.5)

    def test_lone_adult_stays_guard(self):
        herd=fixture()[:2]
        tick(herd,Mammoth('player',20),herd[0],{'mother'})
        self.assertEqual(herd[1].role,'guard')
        self.assertLessEqual(distance(herd[1],herd[0]),2)

    def test_adult_victim_also_receives_support(self):
        herd=fixture();tick(herd,Mammoth('player',5),herd[1],{'mother','ally'})
        self.assertEqual(herd[2].role,'assist')
        self.assertEqual(herd[1].role,'guard')

    def test_uninformed_ally_does_not_attack(self):
        herd=fixture();tick(herd,Mammoth('player',5),herd[0],{'mother'})
        self.assertEqual(herd[2].role,'idle')
        self.assertIsNone(herd[2].target)

    def test_approach_is_not_attack(self):
        herd=fixture();tick(herd,Mammoth('visitor',5),herd[0],{'mother','ally'},attacked=False)
        self.assertEqual(herd[2].role,'warn')
        self.assertTrue(all(a.target is None for a in herd))

    def test_companionship_is_individual_not_herd_wide(self):
        herd=fixture();herd[2].companions.add('visitor')
        tick(herd,Mammoth('visitor',5),herd[0],{'mother','ally'},attacked=False)
        self.assertEqual(herd[2].role,'idle')
        self.assertEqual(herd[1].companions,set())
        # Familiarity cannot suppress defense after an actual attack on a calf.
        tick(herd,Mammoth('visitor',5),herd[0],{'mother','ally'})
        self.assertEqual(herd[2].role,'assist')

    def test_tamed_companion_is_defended_without_abandoning_calf(self):
        herd=fixture(); friend=Mammoth('friend',4,herd='human')
        for a in herd[1:3]: a.companions.add('friend')
        threat=Mammoth('attacker',5,herd='human')
        tick(herd,threat,friend,{'mother','ally','other'})
        self.assertEqual(herd[1].role,'guard')
        self.assertEqual(herd[2].role,'assist')
        self.assertEqual(herd[3].role,'idle')
        for _ in range(40):
            threat.x+=.5
            tick(herd,threat,friend,{'mother','ally'})
            self.assertLessEqual(distance(herd[1],herd[0]),2.000001)
        self.assertEqual(herd[2].role,'return')
        self.assertIn('friend',herd[2].companions)

    def test_riding_does_not_create_companionship(self):
        herd=fixture();herd[1].rider='rider'
        tick(herd,Mammoth('attacker',5),Mammoth('rider',4,herd='human'),{'ally'})
        self.assertIsNone(herd[2].target)
        self.assertEqual(herd[1].companions,set())

    def test_ridden_adult_is_not_overridden(self):
        herd=fixture();herd[1].rider='rider';before=(herd[1].x,herd[1].z)
        tick(herd,Mammoth('player',5),herd[0],{'mother','ally'})
        self.assertEqual(herd[1].role,'rider-control')
        self.assertEqual((herd[1].x,herd[1].z),before)
        self.assertEqual(herd[2].role,'guard')
        self.assertEqual(herd[1].companions,set())

    def test_dead_guard_reassigned(self):
        herd=fixture();herd[1].alive=False
        tick(herd,Mammoth('player',5),herd[0],{'ally'})
        self.assertEqual(herd[2].role,'guard')

    def test_no_available_guard_is_explicit(self):
        herd=fixture()[:2];herd[1].rider='rider'
        guardians=tick(herd,Mammoth('player',5),herd[0],{'mother'})
        self.assertEqual(guardians,{})  # No false guarantee; rider policy remains unresolved.

    def test_guard_tracks_retreating_calf(self):
        herd=fixture();threat=Mammoth('player',10)
        for _ in range(40):
            herd[0].x-=.2
            tick(herd,threat,herd[0],{'mother','ally'})
            self.assertLessEqual(distance(herd[1],herd[0]),2.000001)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HerdTests))
    Path(__file__).with_name('mammoth_herd_results.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
