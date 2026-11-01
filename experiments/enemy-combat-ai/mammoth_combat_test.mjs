// Real combat helpers in a temporary bundle; no production source changes.
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { readFile, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath,pathToFileURL } from 'node:url';
import { CollisionWorld } from '../../dist/shared/collision.mjs';
import { createAnimals,updateAnimals } from '../../dist/shared/animals.mjs';
import { handleRidingAction } from '../../dist/shared/riding.mjs';
import { createBehemoth,updateBehemoths } from '../../dist/shared/violet-behemoth.mjs';
import { mammothNavigation } from '../../dist/shared/mammoth-navigation.mjs';
const root=fileURLToPath(new URL('../../',import.meta.url));
const temporary=await mkdtemp(path.join(tmpdir(),'mammoth-combat-'));
const checks=[];
function check(name,fn){fn();checks.push(name);}
try {
  const source=await readFile(path.join(root,'shared/combat.mts'),'utf8');
  const outfile=path.join(temporary,'combat.mjs');
  await build({stdin:{contents:source+'\nexport { applyHit, clearLine };',resolveDir:path.join(root,'shared'),loader:'ts'},outfile,bundle:true,platform:'node',format:'esm',plugins:[{name:'mts',setup(b){b.onResolve({filter:/\.mjs$/},a=>a.path.startsWith('.')?{path:path.resolve(a.resolveDir,a.path.replace(/\.mjs$/,'.mts'))}:undefined);}}]});
  const C=await import(pathToFileURL(outfile));
  function fixture(){
    const collision=new CollisionWorld([],{river:false});
    const animals=createAnimals(collision,0),a=animals[0];
    // Use an actual safe spawning location and body radii.
    const calf={...animals[1],id:'calf',x:a.x,z:a.z-6,radius:1,home:{x:a.x,z:a.z-6}};
    a.nextRoam=1e8;
    const boss=createBehemoth(collision,[],0);
    Object.assign(boss,{x:a.x,z:a.z+a.radius+boss.radius+.1,home:{x:a.x,z:a.z+8}});
    const room={collision,animals:[a,calf],enemies:[boss],players:new Map(),camp:{x:50,z:50}};
    const guard={x:calf.x,z:calf.z};
    return {room,a,calf,boss,guard};
  }
  const profiles={tusk:{key:'mammoth-tusk',damage:18,reach:.5,halfAngle:Math.PI/4,durationMs:1100,impactMs:800},bump:{key:'mammoth-bump',damage:22,reach:.3,halfAngle:Math.PI/4,durationMs:1100,impactMs:800}};
  class Adapter {
    constructor(f){Object.assign(this,f);this.pending=null;this.ready=0;this.results=[];}
    start(kind,target,now){
      if(this.pending||now<this.ready||this.a.riderId||this.a.phase!=='alive'||now<this.a.hitUntil)return false;
      if(!this.room.enemies.includes(target)||target.phase!=='alive'||!target.hostile)return false;
      if(C.combatDistance(this.a,this.guard)>8)return false;
      this.pending={kind,targetId:target.id,start:now,origin:{x:this.a.x,z:this.a.z},facing:Math.atan2(target.x-this.a.x,target.z-this.a.z),resolved:false};return true;
    }
    tick(now){
      const s=this.pending;if(!s)return;
      const target=this.room.enemies.find(e=>e.id===s.targetId);
      if(this.a.riderId||this.a.phase!=='alive'||now<this.a.hitUntil||!target||target.phase!=='alive'||C.combatDistance(this.a,this.guard)>8){this.pending=null;this.ready=now+500;return;}
      const elapsed=now-s.start;
      if(s.kind==='bump'&&elapsed>=600&&!s.resolved){
        const travel=Math.min(.5,(elapsed-600)/400*.5);
        const goal={x:s.origin.x+Math.sin(s.facing)*travel,z:s.origin.z+Math.cos(s.facing)*travel};
        if(C.combatDistance(goal,this.guard)>8){this.pending=null;this.ready=now+500;return;}
        const dynamic=[...this.room.animals.filter(a=>a!==this.a),...this.room.enemies,...this.room.players.values()].map(a=>({id:a.id,type:'circle',x:a.x,z:a.z,radius:a.radius}));
        Object.assign(this.a,mammothNavigation(this.room.collision).move(this.a,goal.x-this.a.x,goal.z-this.a.z,this.a.radius,dynamic));
      }
      if(elapsed>=800&&!s.resolved){
        s.resolved=true;const profile=profiles[s.kind];
        if(C.withinAttackReach(this.a,target,profile)&&C.inAttackArc(this.a,target,s.facing,profile)&&C.clearLine(this.room,this.a,target))
          this.results.push(C.applyHit(this.room,{target,kind:'enemy'},profile,now,this.a.id));
      }
      if(elapsed>=1100){this.pending=null;this.ready=now+500;}
    }
  }
  for(const kind of ['tusk','bump']){
    check(`${kind}: actual HP, hit state and exactly one damage`,()=>{
      const f=fixture(),d=new Adapter(f);assert.ok(d.start(kind,f.boss,1000));d.tick(1599);assert.equal(f.boss.health,300);
      for(let t=1600;t<=2500;t+=25)d.tick(t);
      assert.equal(f.boss.health,300-profiles[kind].damage);assert.equal(f.boss.hitSequence,1);assert.equal(d.results.length,1);
      assert.ok(C.combatDistance(f.a,f.guard)<=8);assert.equal(f.calf.health,100);
      assert.equal(d.start(kind,f.boss,2500),false);assert.equal(d.start(kind,f.boss,2700),true);
    });
    check(`${kind}: evade during telegraph means no damage`,()=>{
      const f=fixture(),d=new Adapter(f);d.start(kind,f.boss,1000);f.boss.x+=20;d.tick(1800);assert.equal(f.boss.health,300);
    });
    check(`${kind}: real wall occludes hit`,()=>{
      const f=fixture(),d=new Adapter(f);d.start(kind,f.boss,1000);
      f.room.collision=new CollisionWorld([{id:'wall',type:'box',x:f.a.x,z:f.a.z+f.a.radius+.05,hx:10,hz:.1,c:1,s:0,height:10}],{river:false});
      d.tick(1800);assert.equal(f.boss.health,300);
    });
    check(`${kind}: child movement cancels before impact`,()=>{
      const f=fixture(),d=new Adapter(f);d.start(kind,f.boss,1000);f.guard.z-=10;d.tick(1800);assert.equal(f.boss.health,300);assert.equal(d.pending,null);
    });
    check(`${kind}: actual mounting cancels without moving rider`,()=>{
      const f=fixture(),d=new Adapter(f);d.start(kind,f.boss,1000);
      const p={id:'rider',species:'cat',gender:'female',x:f.a.x+f.a.radius+.5,z:f.a.z,radius:.32,energy:88,inventory:{},path:[]};
      f.room.players.set(p.id,p);assert.equal(handleRidingAction(f.room,p,{action:'ride',targetId:f.a.id},1100).changed,true);
      const before={x:f.a.x,z:f.a.z};d.tick(1800);assert.equal(d.pending,null);assert.equal(f.boss.health,300);assert.deepEqual({x:f.a.x,z:f.a.z},before);assert.equal(p.mountId,f.a.id);
    });
  }
  check('companion defense and fleeing boss stay within escort bound',()=>{
    const f=fixture();const friend={id:'friend',x:f.guard.x,z:f.guard.z,radius:.32,energy:100};
    f.room.players.set(friend.id,friend);f.guard=friend;f.a.experimentalCompanions=['friend'];
    const d=new Adapter(f);const origin={x:f.a.x,z:f.a.z};d.start('bump',f.boss,1000);
    for(let t=1025;t<=3000;t+=25){f.boss.z+=.2;d.tick(t);assert.ok(C.combatDistance(f.a,friend)<=8);}
    assert.equal(f.boss.health,300);assert.equal(friend.energy,100);assert.ok(C.combatDistance(f.a,origin)<=.500001);
  });
  check('two allied attackers contribute damage without duplicate hits',()=>{
    const f=fixture(),b={...f.a,id:'ally-2',x:f.a.x+.1};f.room.animals.push(b);
    const first=new Adapter(f),second=new Adapter({...f,a:b});
    first.start('tusk',f.boss,1000);second.start('tusk',f.boss,1000);
    first.tick(1800);second.tick(1800);first.tick(1825);second.tick(1825);
    assert.equal(f.boss.health,264);assert.equal(f.boss.hitSequence,2);
  });
  check('rider movement matches baseline with dormant attack adapter',()=>{
    const a=fixture(),b=fixture(),d=new Adapter(b);
    for(const f of [a,b]){const p={id:'rider',species:'cat',gender:'female',x:f.a.x+f.a.radius+.5,z:f.a.z,radius:.32,energy:88,path:[]};f.room.players.set(p.id,p);handleRidingAction(f.room,p,{action:'ride',targetId:f.a.id},1000);f.a.dx=1;f.a.dz=0;}
    for(let t=1100;t<=1600;t+=100){for(const f of [a,b]){f.a.lastInput=t;updateAnimals(f.room,.1,t);}d.tick(t);assert.deepEqual(b.a,a.a);}
  });
  check('sealed enemy is not damaged by allied mammoth',()=>{const f=fixture(),d=new Adapter(f);f.boss.sealed=true;d.start('tusk',f.boss,1000);d.tick(1800);assert.equal(f.boss.health,300);assert.equal(d.results[0].sealed,true);});
  check('real death processing is retained',()=>{const f=fixture(),d=new Adapter(f);f.boss.health=10;d.start('tusk',f.boss,1000);d.tick(1800);assert.equal(f.boss.health,0);assert.equal(f.boss.phase,'dead');assert.equal(f.boss.alive,false);});
  check('current boss cannot acquire animal attacker: integration gap reproduced',()=>{
    const f=fixture(),d=new Adapter(f);d.start('tusk',f.boss,1000);d.tick(1800);assert.equal(f.boss.provokedBy,f.a.id);
    updateBehemoths(f.room,.025,1825,()=>{});assert.equal(f.boss.targetId,null);assert.equal(f.boss.provokedBy,null);
  });
  await writeFile(new URL('mammoth_combat_results.json',import.meta.url),JSON.stringify({passed:checks.length,checks},null,2)+'\n');
  console.log(JSON.stringify({passed:checks.length,checks},null,2));
}finally{await rm(temporary,{recursive:true,force:true});}
