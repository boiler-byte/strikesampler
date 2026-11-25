'use strict';
// Isolated simulation of service worker install, activation and fetch events.
// This does not replace a real browser/service-worker integration test.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const meta = JSON.parse(fs.readFileSync(path.join(root,'boiler-room.json'),'utf8'));
const base = 'https://example.invalid/apps/strike/';
const prefix = `strike-shell:${base}:`;
const release = `${prefix}${meta.version}`;
const old = `${prefix}1`;
const other = 'strike-shell:https://example.invalid/apps/another/:1';
const stores = new Map([[old,new Map()],[other,new Map()]]);
const key = r => typeof r === 'string' ? r : r.url;
const caches = {
  keys: async () => [...stores.keys()],
  delete: async name => stores.delete(name),
  open: async name => {
    if (!stores.has(name)) stores.set(name,new Map());
    const map = stores.get(name);
    return { put:async(r,res)=>map.set(key(r),res.clone()), match:async r=>map.get(key(r))?.clone() };
  }
};
let offline=false, missing=null, claimed=false;
const handlers={};
const context = vm.createContext({URL, caches, Response, console,
  self: {registration:{scope:base}, clients:{claim:async()=>{claimed=true;}}, addEventListener:(type,fn)=>{handlers[type]=fn;}},
  fetch: async req => {
    if (offline) throw Error('offline');
    const file=key(req).slice(base.length);
    if (file===missing||!meta.files.includes(file)) return new Response('not found',{status:404});
    return new Response(fs.readFileSync(path.join(root,file)),{status:200});
  }
});
vm.runInContext(fs.readFileSync(path.join(root,'sw.js'),'utf8'),context);
const lifecycle = type => {let p; handlers[type]({waitUntil:x=>{p=x;}}); return p;};
const request = (url,mode='navigate',method='GET',range=false) => {
  let p; handlers.fetch({request:{url,mode,method,headers:{has:()=>range}},respondWith:x=>{p=x;}}); return p;
};
(async()=>{
  missing=meta.files.find(f=>f.endsWith('.png'));
  await assert.rejects(lifecycle('install')); assert.equal(stores.has(release),false); assert(stores.has(old));
  missing=null;
  await lifecycle('install'); assert(stores.has(old)); assert.equal(claimed,false);
  assert.deepEqual([...stores.get(release).keys()].sort(),meta.files.map(f=>base+f).sort());
  await lifecycle('activate'); assert(!stores.has(old)); assert(stores.has(other)); assert(claimed);
  offline=true;
  for(const url of [base,base+'?workspace=1',base+'index.html',base+'index.html?offline=1']) {
    const response=await request(url); assert.equal(await response.text(),fs.readFileSync(path.join(root,'index.html'),'utf8'));
  }
  for(const f of meta.files) assert((await request(base+f,'cors')).ok);
  assert.equal(request('https://example.invalid/apps/another/index.html'),undefined);
  assert.equal(request(base+'index.html','cors','POST'),undefined);
  assert.equal(request(base+'index.html','cors','GET',true),undefined);
  await assert.rejects(request(base+'uncached.html'));
  console.log('PASS: simulated incomplete install, complete cache, deferred activation, scoped cleanup, offline navigation and assets, request filtering');
})().catch(error=>{console.error(error);process.exitCode=1;});
