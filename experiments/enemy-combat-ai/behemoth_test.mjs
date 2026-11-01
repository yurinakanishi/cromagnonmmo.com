// Experimental decision hook in a temporary bundle; production sources are never written.
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const source = await readFile(path.join(root, 'shared/violet-behemoth.mts'), 'utf8');
const anchor = '    if (\n      distance(e, target) >= R.spitMinRange';
assert.equal(source.split(anchor).length, 2, 'decision boundary changed: review hook');
const hook = `    const requested = room.experimentalChoice?.(e, target, now);
    const d = distance(e, target);
    const legal = clear(room, e, target) && (
      requested === 'charge' ||
      (requested === 'bite' && d <= e.radius + target.radius + R.biteReach) ||
      (requested === 'tail' && d <= R.tailReach + target.radius) ||
      (requested === 'poison' && d >= R.spitMinRange && d <= R.spitRange && now >= e.nextSpitAt));
    if (requested && legal) {
      if ((requested === 'bite' || requested === 'tail') &&
          Math.abs(angleDifference(angleTo(e, target), e.facing)) <= Math.PI / 2) e.meleeIndex++;
      e.facing = angleTo(e, target);
      begin(e, requested, now);
      if (requested === 'poison') {
        e.pendingAttack.aim = {x: target.x, z: target.z,
          y: projectileHeight(target.x, target.z, room.collision.surfaceHeight?.(target) ?? 0)
             + (target.species === 'bear' ? 0.45 : 0.85)};
        e.nextSpitAt = now + R.spitCooldownMs;
      }
      changed = true;
      continue;
    }
`;
const temporary = await mkdtemp(path.join(tmpdir(), 'cromag-behemoth-'));
const checks = [];
const check = (name, fn) => { fn(); checks.push(name); };
try {
  const modules = [];
  for (const [name, text] of [['baseline', source], ['hook', source.replace(anchor, hook + anchor)]]) {
    const outfile = path.join(temporary, name + '.mjs');
    await build({stdin: {contents: text + '\nexport { R };', resolveDir: path.join(root, 'shared'), loader: 'ts'},
      outfile, bundle: true, platform: 'node', format: 'esm', plugins: [{name: 'mts-source', setup(b) {
        b.onResolve({filter: /\.mjs$/}, args => args.path.startsWith('.')
          ? {path: path.resolve(args.resolveDir, args.path.replace(/\.mjs$/, '.mts'))} : undefined);
      }}]});
    modules.push(await import(pathToFileURL(outfile)));
  }
  const [base, adapted] = modules, R = base.R;
  function fixture(api, range=5.5, meleeIndex=0, choice=()=>null) {
    const collision = {nearestFree: p=>({x:p.x,z:p.z}), free:()=>true, segmentFree:()=>true,
      nearby:()=>[], surfaceHeight:()=>0, path:(_e,p)=>[{x:p.x,z:p.z}], move:(e,dx,dz)=>({x:e.x+dx,z:e.z+dz})};
    const e = api.createBehemoth(collision, [], 0);
    const p = {id:'p', x:e.x, z:e.z+range, radius:.5, energy:100, species:'cro'};
    Object.assign(e, {targetId:'p', facing:0, aggroAfter:0, meleeIndex});
    const room = {collision, enemies:[e], players:new Map([['p',p]]), animals:[], camp:{x:50,z:50}, experimentalChoice:choice};
    const hits=[];
    const tick = now => api.updateBehemoths(room,.025,now,(_e,p,at,amount)=>{p.energy-=amount;hits.push({at,amount,id:p.id});});
    const snapshot=()=>JSON.parse(JSON.stringify({e,p,hits,shots:room.poisonShots,splashes:room.poisonSplashes}));
    return {e,p,room,hits,tick,snapshot};
  }
  // Fixed preference plus bounded exponential moving averages of observed success.
  class Learner {
    values={charge:0,bite:0,tail:0,poison:0};
    observe(action, reward) { this.values[action] += .25*(reward-this.values[action]); }
    choose(legal) { return [...legal].sort((a,b)=>this.score(b)-this.score(a)||a.localeCompare(b))[0]; }
    score(a) { return ({charge:.04,bite:.03,tail:.02,poison:.01}[a]) + .08*this.values[a]; }
  }
  const learner = new Learner();
  function train(rewards) { for(let i=0;i<16;i++) for(const [a,r] of Object.entries(rewards)) learner.observe(a,r); }
  const history=[];
  check('repeated rear pressure favors tail',()=>{train({tail:1,bite:0,charge:0,poison:0}); history.push(learner.choose(['tail','bite','charge']));assert.equal(history.at(-1),'tail');});
  check('changed close frontal approach favors bite',()=>{train({tail:0,bite:1,charge:0,poison:0});history.push(learner.choose(['tail','bite','charge']));assert.equal(history.at(-1),'bite');});
  check('changed ranged approach favors poison',()=>{train({tail:0,bite:0,charge:0,poison:1});history.push(learner.choose(['poison','charge']));assert.equal(history.at(-1),'poison');});
  check('changed approach again favors charge',()=>{train({tail:0,bite:0,charge:1,poison:0});history.push(learner.choose(['poison','charge']));assert.equal(history.at(-1),'charge');});
  for(const [kind,range,index] of [['bite',5.5,0],['tail',5.5,1],['poison',18,0],['charge',11.6,0]]) {
    check(`${kind}: same choice has identical full timeline`,()=>{
      const a=fixture(base,range,index), b=fixture(adapted,range,index,()=>kind);
      for(let t=1000;t<=5000;t+=25){a.tick(t);b.tick(t);
        assert.deepEqual(b.snapshot(),a.snapshot());
        // Compare first attack and its whole recovery, before next selection differs.
        if(a.e.behavior==='recover' && t>=a.e.nextAttackAt-25) break;
      }
      assert.equal(a.e.attackSequence,1);
      assert.equal(a.hits.length,1, `${kind} must actually hit in this fixture`);
      assert.equal(a.hits[0].amount, R[({bite:'biteDamage',tail:'tailDamage',poison:'spitDamage',charge:'chargeDamage'})[kind]]);
    });
    check(`${kind}: adversarial changes cannot interrupt active attack/recovery`,()=>{
      let calls=0;
      const a=fixture(base,range,index), b=fixture(adapted,range,index,()=>{calls++;return 'tail';});
      // Start through original selection, then enable hostile decision requests.
      b.room.experimentalChoice=()=>null;
      a.tick(1000);b.tick(1000);
      b.room.experimentalChoice=()=>{calls++;return 'tail';};
      for(let t=1025;t<=5000;t+=25){
        if(!a.e.pendingAttack && t>=a.e.nextAttackAt)break;
        a.tick(t);b.tick(t);assert.deepEqual(b.snapshot(),a.snapshot());
      }
      assert.equal(calls,0);
    });
  }
  check('learned choice really changes next attack',()=>{
    const l=new Learner();for(let i=0;i<16;i++)l.observe('tail',1);
    const f=fixture(adapted,5.5,0,()=>l.choose(['bite','tail']));f.tick(1000);
    assert.equal(f.e.pendingAttack.kind,'tail');
    for(let i=0;i<20;i++){l.observe('tail',0);l.observe('bite',1);}
    for(let t=1025;t<=f.e.attackLockUntil+R.recoveryMs;t+=25){
      f.tick(t); if(f.e.pendingAttack?.kind==='bite')break;
    }
    // Advance to next legal decision boundary if loop stopped at end of recovery.
    f.tick(f.e.nextAttackAt);
    assert.equal(f.e.pendingAttack.kind,'bite');
  });
  for(const kind of ['bite','tail','poison'])check(`${kind}: illegal request falls back to existing selection`,()=>{
    const range=kind==='poison'?5.5:18;
    const a=fixture(base,range),b=fixture(adapted,range,0,()=>kind);
    a.tick(1000);b.tick(1000);assert.deepEqual(b.snapshot(),a.snapshot());
  });
  for(const condition of ['hit','outside','protected','provoked','cooldown','wall'])check(`${condition}: existing restrictions preserved`,()=>{
    const a=fixture(base,18),b=fixture(adapted,18,0,()=> 'poison');
    for(const f of [a,b]) {
      if(condition==='hit')f.e.hitUntil=2000;
      if(condition==='outside')f.p.z=f.e.home.z+40;
      if(condition==='protected')f.p.invulnerableUntil=2000;
      if(condition==='provoked')f.e.provokedBy='p';
      if(condition==='cooldown')f.e.nextSpitAt=10000;
      if(condition==='wall')f.room.collision.segmentFree=()=>false;
    }
    a.tick(1000);b.tick(1000);assert.deepEqual(b.snapshot(),a.snapshot());
  });
  const report={passed:checks.length, checks, adaptation:history, source:'shared/violet-behemoth.mts', limitations:'Synthetic reward observations and flat collision fixture; not live game or network.'};
  await writeFile(new URL('behemoth_results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
} finally { await rm(temporary,{recursive:true,force:true}); }
