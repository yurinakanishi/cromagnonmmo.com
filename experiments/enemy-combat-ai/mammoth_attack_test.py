"""Point-model defense attacks. No game modifications; parameters are illustrative."""
import math
import json
import unittest
from pathlib import Path
from mammoth_herd_test import Mammoth, distance, step_toward, tick, fixture


class Defense:
    def __init__(self, animal, protected):
        self.a, self.protected = animal, protected
        self.attack = None
        self.ready = 0
        self.hits = []

    def start(self, kind, target, now):
        if kind not in ('tusk', 'bump') or self.attack or now < self.ready:
            return False
        if self.a.retreating or self.a.rider or not self.a.alive or self.a.child or self.a.target != target.id:
            return False
        d = distance(self.a, target)
        if d == 0 or d > (1.5 if kind == 'tusk' else 3):
            return False
        if distance(target, self.protected) > 4:
            return False
        self.attack = {'kind': kind, 'target': target.id, 'at': now, 'origin': (self.a.x,self.a.z),
                       'direction': ((target.x-self.a.x)/d,(target.z-self.a.z)/d), 'resolved': False}
        return True

    def update(self, now, target, blocked=False):
        s = self.attack
        if s is None:
            # A fleeing enemy never becomes a navigation goal here.
            if not self.a.retreating and not self.a.rider and distance(self.a,self.protected)>2:
                step_toward(self.a,self.protected,.1)
            return
        if self.a.retreating or self.a.rider or not self.a.alive or target.id != s['target'] or not target.alive:
            self.attack=None;self.ready=now+.5;return
        if distance(target,self.protected)>4 or distance(self.a,self.protected)>2:
            self.attack=None;self.ready=now+.5;return
        elapsed=now-s['at']
        if elapsed<.6:
            return
        if s['kind']=='bump':
            travel=min(1.,max(0.,elapsed-.6)*2)
            x=s['origin'][0]+s['direction'][0]*travel
            z=s['origin'][1]+s['direction'][1]*travel
            if blocked or math.hypot(x-self.protected.x,z-self.protected.z)>2:
                self.attack=None;self.ready=now+.5;return
            self.a.x,self.a.z=x,z
        dx,dz=target.x-self.a.x,target.z-self.a.z
        front=dx*s['direction'][0]+dz*s['direction'][1]
        side=abs(dx*s['direction'][1]-dz*s['direction'][0])
        if not s['resolved'] and (s['kind']=='bump' or elapsed>=.8):
            if not blocked and 0<=front<=1.5 and side<=.5:
                self.hits.append((target.id,s['kind'],now))
                s['resolved']=True
            if s['kind']=='tusk':
                s['resolved']=True
        if elapsed>=1.1:
            self.attack=None;self.ready=now+.5


def run(kind, protect_friend=False, flee=False):
    herd=fixture();enemy=Mammoth('enemy',2.4,herd='human')
    protected=Mammoth('friend',0,herd='human') if protect_friend else herd[0]
    for a in herd[1:3]: a.companions.add('friend')
    tick(herd,enemy,protected,{'mother','ally'})
    fighter=herd[1]
    defense=Defense(fighter,protected)
    assert defense.start(kind,enemy,0)
    path=[]
    for i in range(1,61):
        now=i*.05
        if flee: enemy.x+=.2
        defense.update(now,enemy)
        path.append((fighter.x,fighter.z))
    return defense,path


class AttackTests(unittest.TestCase):
    def test_retreat_cancels_both_attacks_and_prevents_restart(self):
        for kind in ('tusk','bump'):
            a=Mammoth('a',1,target='enemy');e=Mammoth('enemy',2)
            d=Defense(a,Mammoth('child',0));self.assertTrue(d.start(kind,e,0))
            a.retreating=True;d.update(.8,e)
            self.assertEqual(d.hits,[]);self.assertIsNone(d.attack)
            self.assertFalse(d.start(kind,e,2))

    def test_both_attacks_defend_calf_and_companion(self):
        for kind in ('tusk','bump'):
            for friend in (False,True):
                with self.subTest(kind=kind,friend=friend):
                    d,path=run(kind,friend)
                    self.assertEqual(len(d.hits),1)
                    self.assertTrue(all(math.hypot(x,y)<=2.000001 for x,y in path))

    def test_fleeing_enemy_not_chased(self):
        for kind in ('tusk','bump'):
            for friend in (False,True):
                d,path=run(kind,friend,True)
                self.assertEqual(d.hits,[])
                self.assertTrue(all(math.hypot(x,y)<=2.000001 for x,y in path))

    def test_telegraph_and_cooldown(self):
        for kind in ('tusk','bump'):
            a=Mammoth('a',1,target='enemy');p=Mammoth('calf',0);e=Mammoth('enemy',2)
            d=Defense(a,p);self.assertTrue(d.start(kind,e,0))
            d.update(.59,e);self.assertEqual(a.x,1);self.assertEqual(d.hits,[])
            self.assertFalse(d.start('tusk',e,.59))
            for i in range(12,23):d.update(i*.05,e)
            self.assertEqual(len(d.hits),1)
            self.assertFalse(d.start(kind,e,1.2))
            e.x=a.x+.5  # Keep a valid nonzero aim after the bump reaches the old target.
            self.assertTrue(d.start(kind,e,1.7))

    def test_sidestep_does_not_home(self):
        for kind in ('tusk','bump'):
            a=Mammoth('a',1,target='enemy');p=Mammoth('calf',0);e=Mammoth('enemy',2)
            d=Defense(a,p);d.start(kind,e,0);e.z=1.5
            for i in range(1,25):d.update(i*.05,e)
            self.assertEqual(a.z,0);self.assertEqual(d.hits,[])

    def test_wall_blocks_hit_and_bump(self):
        for kind in ('tusk','bump'):
            a=Mammoth('a',1,target='enemy');p=Mammoth('calf',0);e=Mammoth('enemy',2)
            d=Defense(a,p);d.start(kind,e,0)
            for i in range(1,25):d.update(i*.05,e,blocked=True)
            self.assertEqual(a.x,1);self.assertEqual(d.hits,[])

    def test_riding_cancels_autonomous_attack(self):
        a=Mammoth('a',1,target='enemy');e=Mammoth('enemy',2);d=Defense(a,Mammoth('child',0))
        d.start('bump',e,0);a.rider='rider';d.update(.8,e)
        self.assertEqual(a.x,1);self.assertEqual(d.hits,[])
        self.assertFalse(d.start('tusk',e,2))

    def test_moving_protected_actor_breaks_off_attack(self):
        for kind in ('tusk','bump'):
            a=Mammoth('a',1,target='enemy');p=Mammoth('child',0);e=Mammoth('enemy',2)
            d=Defense(a,p);d.start(kind,e,0);p.x=-3;d.update(.7,e)
            self.assertIsNone(d.attack);self.assertEqual(d.hits,[])
            for i in range(8,60):d.update(i*.1,e)
            self.assertLessEqual(distance(a,p),2)

    def test_no_automatic_attack_on_companion_or_unknown(self):
        a=Mammoth('a',1,companions={'friend'});d=Defense(a,Mammoth('child',0))
        self.assertFalse(d.start('tusk',Mammoth('friend',2),0))
        self.assertFalse(d.start('bump',Mammoth('unknown',2),0))


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AttackTests))
    traces={kind:run(kind)[1] for kind in ('tusk','bump')}
    Path(__file__).with_name('mammoth_attack_results.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'traces':traces},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
